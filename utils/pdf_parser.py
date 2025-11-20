"""
Modulo per il parsing di PDF degli Ordini di Acquisto.

Supporta l'estrazione di:
- Metadati ordine (numero PO, data, fornitore, etc.)
- Righe prodotto (codice, descrizione, quantità, prezzo)
- Validazione e normalizzazione dati
"""

import pdfplumber
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PDFParseError(Exception):
    """Eccezione custom per errori di parsing PDF"""
    pass


class PurchaseOrderParser:
    """
    Parser per PDF di Ordini di Acquisto.

    Supporta diversi formati di PO cercando pattern comuni.
    """

    # Pattern regex per identificare campi chiave
    PO_NUMBER_PATTERNS = [
        r'(?:PO|P\.O\.|Purchase\s+Order|Ordine)\s*[#:N°]?\s*([A-Z0-9\-\/]+)',
        r'(?:Numero|Number|N°)\s*[:]?\s*([A-Z0-9\-\/]+)',
    ]

    DATE_PATTERNS = [
        r'(?:Date|Data)\s*[:]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
    ]

    SUPPLIER_PATTERNS = [
        r'(?:Supplier|Fornitore|Vendor)\s*[:]?\s*([A-Z][A-Za-z\s&\.]+)',
        r'(?:To|A)\s*[:]?\s*([A-Z][A-Za-z\s&\.]+)',
    ]

    # Colonne tipiche nelle tabelle prodotti
    PRODUCT_COLUMNS = {
        'code': ['code', 'codice', 'item', 'part', 'sku', 'articolo'],
        'description': ['description', 'descrizione', 'desc', 'name', 'nome'],
        'quantity': ['qty', 'quantity', 'quantità', 'qta', 'q.tà'],
        'unit_price': ['price', 'prezzo', 'unit price', 'prezzo unit', 'costo'],
        'total': ['total', 'totale', 'amount', 'importo'],
    }

    def __init__(self, pdf_path: str):
        """
        Inizializza il parser con il path del PDF.

        Args:
            pdf_path: Path completo al file PDF
        """
        self.pdf_path = pdf_path
        self.pdf = None
        self.text = ""
        self.tables = []

    def __enter__(self):
        """Context manager entry"""
        self.pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.pdf:
            self.pdf.close()

    def extract_all_content(self) -> None:
        """Estrae tutto il testo e le tabelle dal PDF"""
        if not self.pdf:
            raise PDFParseError("PDF not opened. Use context manager (with statement).")

        text_parts = []
        all_tables = []

        for page in self.pdf.pages:
            # Estrai testo
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

            # Estrai tabelle
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)

        self.text = "\n".join(text_parts)
        self.tables = all_tables

        if not self.text and not self.tables:
            raise PDFParseError("PDF appears to be empty or unreadable")

    def extract_metadata(self) -> Dict[str, Optional[str]]:
        """
        Estrae metadati dell'ordine dal testo del PDF.

        Returns:
            Dict con campi: po_number, order_date, supplier
        """
        metadata = {
            'po_number': None,
            'order_date': None,
            'supplier': None,
        }

        # Cerca numero PO
        for pattern in self.PO_NUMBER_PATTERNS:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                metadata['po_number'] = match.group(1).strip()
                break

        # Cerca data
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                metadata['order_date'] = self._parse_date(date_str)
                break

        # Cerca fornitore
        for pattern in self.SUPPLIER_PATTERNS:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                supplier = match.group(1).strip()
                # Limita lunghezza e pulisci
                metadata['supplier'] = supplier[:100]
                break

        return metadata

    def extract_line_items(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Estrae le righe prodotto dalle tabelle del PDF.

        Returns:
            Tuple di (righe_ok, righe_errore)
            - righe_ok: lista di dict con i dati prodotto validi
            - righe_errore: lista di dict con errori e riga originale
        """
        if not self.tables:
            return [], [{'error': 'No tables found in PDF', 'row_num': 0}]

        righe_ok = []
        righe_errore = []

        # Prova ogni tabella trovata
        for table_idx, table in enumerate(self.tables):
            if not table or len(table) < 2:  # Almeno header + 1 riga
                continue

            # Identifica header
            header = self._normalize_header(table[0])

            # Mappa colonne
            col_mapping = self._map_columns(header)

            if not col_mapping.get('code'):
                # Salta tabelle che non hanno almeno una colonna codice
                continue

            # Processa righe dati
            for row_idx, row in enumerate(table[1:], start=1):
                try:
                    item = self._parse_row(row, col_mapping, header)

                    if item:
                        # Validazione base
                        validation_errors = self._validate_item(item, row_idx)

                        if validation_errors:
                            righe_errore.append({
                                'row_num': row_idx,
                                'table_idx': table_idx,
                                'errors': validation_errors,
                                'raw_data': row,
                            })
                        else:
                            item['row_num'] = row_idx
                            item['table_idx'] = table_idx
                            righe_ok.append(item)

                except Exception as e:
                    righe_errore.append({
                        'row_num': row_idx,
                        'table_idx': table_idx,
                        'errors': [f"Parse error: {str(e)}"],
                        'raw_data': row,
                    })

        return righe_ok, righe_errore

    def _normalize_header(self, header: List) -> List[str]:
        """Normalizza l'header della tabella (lowercase, no spaces)"""
        return [
            str(col).lower().strip() if col else ''
            for col in header
        ]

    def _map_columns(self, header: List[str]) -> Dict[str, int]:
        """
        Mappa le colonne dell'header ai campi standard.

        Returns:
            Dict con {campo: indice_colonna}
        """
        mapping = {}

        for field, keywords in self.PRODUCT_COLUMNS.items():
            for idx, col_name in enumerate(header):
                if any(keyword in col_name.lower() for keyword in keywords):
                    mapping[field] = idx
                    break

        return mapping

    def _parse_row(self, row: List, col_mapping: Dict[str, int], header: List[str]) -> Optional[Dict]:
        """Parse una singola riga della tabella"""
        # Riga vuota o solo None
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            return None

        item = {}

        # Estrai campi mappati
        for field, col_idx in col_mapping.items():
            if col_idx < len(row):
                value = row[col_idx]
                item[field] = self._clean_value(value)

        return item if item else None

    def _clean_value(self, value) -> Optional[str]:
        """Pulisce un valore di cella"""
        if value is None:
            return None

        value_str = str(value).strip()

        if value_str == '' or value_str.lower() in ['none', 'n/a', '-']:
            return None

        return value_str

    def _validate_item(self, item: Dict, row_num: int) -> List[str]:
        """
        Valida un item prodotto.

        Returns:
            Lista di errori (vuota se valido)
        """
        errors = []

        # Campo obbligatorio: code
        if not item.get('code'):
            errors.append("Missing product code")

        # Se c'è quantity, deve essere numerica
        if item.get('quantity'):
            try:
                qty = self._parse_number(item['quantity'])
                if qty <= 0:
                    errors.append(f"Invalid quantity: {item['quantity']}")
            except ValueError:
                errors.append(f"Quantity not numeric: {item['quantity']}")

        # Se c'è unit_price, deve essere numerico
        if item.get('unit_price'):
            try:
                price = self._parse_number(item['unit_price'])
                if price < 0:
                    errors.append(f"Invalid unit_price: {item['unit_price']}")
            except ValueError:
                errors.append(f"Unit price not numeric: {item['unit_price']}")

        return errors

    def _parse_number(self, value: str) -> float:
        """
        Parse un numero da stringa, gestendo formati diversi.

        Supporta:
        - 1,234.56 (formato USA)
        - 1.234,56 (formato EU)
        - 1234.56
        """
        if not value:
            raise ValueError("Empty value")

        # Rimuovi spazi e simboli di valuta
        value = str(value).strip()
        value = re.sub(r'[€$£\s]', '', value)

        # Determina formato
        if ',' in value and '.' in value:
            # Entrambi presenti: l'ultimo è il decimale
            if value.rindex(',') > value.rindex('.'):
                # Formato EU: 1.234,56
                value = value.replace('.', '').replace(',', '.')
            else:
                # Formato USA: 1,234.56
                value = value.replace(',', '')
        elif ',' in value:
            # Solo virgola: potrebbe essere decimale EU o separatore migliaia USA
            # Euristica: se ci sono 3+ cifre dopo la virgola, è separatore migliaia
            parts = value.split(',')
            if len(parts[-1]) == 3 and len(parts) > 1:
                # Probabilmente separatore migliaia
                value = value.replace(',', '')
            else:
                # Probabilmente decimale EU
                value = value.replace(',', '.')

        return float(value)

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse una data in vari formati.

        Returns:
            Data in formato ISO (YYYY-MM-DD) o None
        """
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%d/%m/%y',
            '%d-%m-%y',
            '%m/%d/%y',
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return None

    def parse(self) -> Dict:
        """
        Esegue il parsing completo del PDF.

        Returns:
            Dict con:
            - success: bool
            - metadata: dict
            - items: list di items validi
            - errors: list di errori trovati
            - warnings: list di warning
        """
        result = {
            'success': False,
            'metadata': {},
            'items': [],
            'errors': [],
            'warnings': [],
        }

        try:
            # Estrai contenuto
            self.extract_all_content()

            # Estrai metadata
            result['metadata'] = self.extract_metadata()

            # Verifica metadata critici
            if not result['metadata'].get('po_number'):
                result['warnings'].append("PO number not found in document")

            if not result['metadata'].get('order_date'):
                result['warnings'].append("Order date not found in document")

            # Estrai righe prodotto
            items_ok, items_error = self.extract_line_items()

            result['items'] = items_ok

            # Converti errori items in formato standard
            for err_item in items_error:
                for error in err_item.get('errors', []):
                    result['errors'].append({
                        'row_num': err_item.get('row_num'),
                        'message': error,
                        'raw_data': err_item.get('raw_data'),
                    })

            # Se non ci sono items validi, è un errore critico
            if not result['items']:
                result['errors'].append({
                    'row_num': 0,
                    'message': 'No valid product lines found in PDF',
                })
                result['success'] = False
            else:
                result['success'] = True

        except PDFParseError as e:
            result['errors'].append({
                'row_num': 0,
                'message': f"PDF Parse Error: {str(e)}",
            })
        except Exception as e:
            result['errors'].append({
                'row_num': 0,
                'message': f"Unexpected error: {str(e)}",
            })
            logger.exception("Unexpected error during PDF parsing")

        return result


def parse_purchase_order_pdf(pdf_path: str) -> Dict:
    """
    Funzione helper per parsare un PDF di ordine di acquisto.

    Args:
        pdf_path: Path completo al file PDF

    Returns:
        Dict con risultati del parsing (vedi PurchaseOrderParser.parse())
    """
    with PurchaseOrderParser(pdf_path) as parser:
        return parser.parse()
