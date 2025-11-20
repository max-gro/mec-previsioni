"""
Parser e generatore TSV per Ordini di Acquisto

Flusso: PDF → TSV → Database
"""
import os
import random
from datetime import datetime, timedelta


def genera_tsv_ordine_simulato(pdf_filepath, output_dir):
    """
    Genera un file TSV simulato con dati di ordini estratti dal PDF.

    Colonne TSV:
    - file: nome file PDF elaborato
    - cod_seller, seller: codice e descrizione venditore
    - cod_buyer, buyer: codice e descrizione acquirente
    - date: data ordine (YYYY-MM-DD)
    - object: oggetto ordine (es: "PO No. 2501504")
    - po: numero PO (es: "2501504")
    - brand: marca
    - item: codice articolo
    - EAN: codice EAN
    - model_no: numero modello
    - price_eur: prezzo unitario
    - qty: quantità
    - amount_eur: importo totale riga

    Args:
        pdf_filepath: path del PDF da elaborare
        output_dir: directory dove salvare il TSV

    Returns:
        tuple: (tsv_filepath: str, num_righe: int, metadati: dict)
    """
    # Estrai filename senza estensione
    pdf_filename = os.path.basename(pdf_filepath)
    base_name = os.path.splitext(pdf_filename)[0]
    tsv_filename = f"{base_name}_parsed.tsv"
    tsv_filepath = os.path.join(output_dir, tsv_filename)

    # Genera dati simulati realistici

    # Controparti (Seller/Buyer)
    sellers = [
        ('SELL001', 'Hisense Italy S.r.l.'),
        ('SELL002', 'Midea Europe B.V.'),
        ('SELL003', 'Haier Europe Trading S.r.l.'),
        ('SELL004', 'Samsung Electronics Italia'),
        ('SELL005', 'LG Electronics Italia S.p.A.')
    ]

    buyers = [
        ('BUY001', 'MediaWorld S.p.A.'),
        ('BUY002', 'Unieuro S.p.A.'),
        ('BUY003', 'Expert Italia S.r.l.'),
        ('BUY004', 'Euronics Italia S.p.A.'),
        ('BUY005', 'Trony S.p.A.')
    ]

    # Seleziona seller e buyer per questo ordine
    cod_seller, seller = random.choice(sellers)
    cod_buyer, buyer = random.choice(buyers)

    # Genera data ordine (ultimi 90 giorni)
    days_ago = random.randint(1, 90)
    order_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

    # Genera numero PO realistico
    po_number = f"25{random.randint(10000, 99999):05d}"
    object_ordine = f"PO No. {po_number}"

    # Brands realistici
    brands = ['HISENSE', 'HOMA', 'MIDEA', 'HAIER', 'SAMSUNG', 'LG', 'CANDY', 'HOOVER']

    # Genera righe ordine (tra 5 e 50 modelli)
    num_righe = random.randint(5, 50)

    righe = []
    for i in range(num_righe):
        brand = random.choice(brands)

        # Codice modello realistico (es: HIS-WM8012, MID-AC7000)
        model_prefix = brand[:3].upper()
        model_suffix = random.choice(['WM', 'DW', 'AC', 'TV', 'RF', 'FR'])
        model_number = random.randint(1000, 9999)
        model_no = f"{model_prefix}-{model_suffix}{model_number}"

        # Item code (SKU)
        item = f"{brand[:2].upper()}{random.randint(100000, 999999)}"

        # EAN (13 digit barcode)
        ean = f"80{random.randint(10000000000, 99999999999)}"

        # Prezzo e quantità realistici
        price_eur = round(random.uniform(150.0, 1500.0), 2)
        qty = random.randint(5, 200)
        amount_eur = round(price_eur * qty, 2)

        # Costruisci riga TSV
        riga = [
            pdf_filename,      # file
            cod_seller,        # cod_seller
            seller,            # seller
            cod_buyer,         # cod_buyer
            buyer,             # buyer
            order_date,        # date
            object_ordine,     # object
            po_number,         # po
            brand,             # brand
            item,              # item
            ean,               # EAN
            model_no,          # model_no
            f"{price_eur:.2f}",    # price_eur
            str(qty),              # qty
            f"{amount_eur:.2f}"    # amount_eur
        ]
        righe.append('\t'.join(riga))

    # Crea file TSV con header
    header = ['file', 'cod_seller', 'seller', 'cod_buyer', 'buyer', 'date', 'object',
              'po', 'brand', 'item', 'EAN', 'model_no', 'price_eur', 'qty', 'amount_eur']

    with open(tsv_filepath, 'w', encoding='utf-8') as f:
        f.write('\t'.join(header) + '\n')
        f.write('\n'.join(righe))

    # Metadati per log
    metadati = {
        'cod_seller': cod_seller,
        'seller': seller,
        'cod_buyer': cod_buyer,
        'buyer': buyer,
        'data_ordine': order_date,
        'oggetto_ordine': object_ordine,
        'po_number': po_number,
        'num_righe': num_righe,
        'num_modelli_unici': len(set(r.split('\t')[11] for r in righe))  # model_no
    }

    return tsv_filepath, num_righe, metadati


def valida_riga_tsv(riga, num_riga):
    """
    Valida una riga TSV e ritorna errori/warning.

    Returns:
        tuple: (valida: bool, errori: list, warnings: list)
    """
    errori = []
    warnings = []

    # Verifica numero colonne
    if len(riga) != 15:
        errori.append(f"Riga {num_riga}: Numero colonne errato (atteso 15, trovato {len(riga)})")
        return False, errori, warnings

    file, cod_seller, seller, cod_buyer, buyer, date, obj, po, brand, item, ean, model_no, price, qty, amount = riga

    # Validazioni obbligatorie
    if not cod_seller or not seller:
        errori.append(f"Riga {num_riga}: Seller mancante")

    if not cod_buyer or not buyer:
        errori.append(f"Riga {num_riga}: Buyer mancante")

    if not po:
        errori.append(f"Riga {num_riga}: Numero PO mancante")

    if not model_no:
        errori.append(f"Riga {num_riga}: Model number mancante")

    # Validazioni numeriche
    try:
        price_val = float(price) if price else 0.0
        if price_val <= 0:
            warnings.append(f"Riga {num_riga}: Prezzo <= 0 ({price})")
    except ValueError:
        errori.append(f"Riga {num_riga}: Prezzo non valido ({price})")

    try:
        qty_val = int(qty) if qty else 0
        if qty_val <= 0:
            warnings.append(f"Riga {num_riga}: Quantità <= 0 ({qty})")
    except ValueError:
        errori.append(f"Riga {num_riga}: Quantità non valida ({qty})")

    # Validazione data
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        errori.append(f"Riga {num_riga}: Data non valida ({date})")

    # Warning per campi opzionali mancanti
    if not brand:
        warnings.append(f"Riga {num_riga}: Brand mancante")

    if not ean or len(ean) != 13:
        warnings.append(f"Riga {num_riga}: EAN mancante o non valido (atteso 13 digit)")

    return len(errori) == 0, errori, warnings
