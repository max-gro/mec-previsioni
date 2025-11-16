"""
Parser per file Excel ordini -> TSV
Legge file Excel da INPUT/po/{anno}/{file}.xlsx
Produce OUTPUT_ELAB/po/{file}.tsv (tab-separated)
"""
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from models import db, TraceElaborazioneFile


# Colonne attese nel file Excel ordini
COLONNE_ORDINI = [
    'Seller', 'Seller desc', 'Buyer', 'Buyer desc', 'Date',
    'PO No.', 'Brand', 'Item', 'EAN', 'Model No.',
    'CIF Price €', 'Q.TY', 'Amount €'
]


def normalizza_codice_modello(codice):
    """
    Normalizza codice modello: lowercase + rimuovi spazi
    Es: "MODEL ABC-123" -> "modelabc-123"
    """
    if not codice or pd.isna(codice):
        return ''
    return str(codice).lower().replace(' ', '')


def _trace_step(id_file_ordine, step, stato, messaggio=None):
    """Traccia uno step dell'elaborazione"""
    trace = TraceElaborazioneFile(
        id_file_ordine=id_file_ordine,
        tipo_file='ord',
        step=step,
        stato=stato,
        messaggio=messaggio,
        timestamp=datetime.utcnow()
    )
    db.session.add(trace)
    db.session.commit()
    return trace.id


def leggi_ordine_excel_to_tsv(id_file_ordine, input_filepath, output_elab_dir):
    """
    Legge file Excel ordini e genera TSV per elaborazione DB

    Args:
        id_file_ordine: ID del record FileOrdini
        input_filepath: Percorso completo file Excel in INPUT/po/{anno}/
        output_elab_dir: Directory OUTPUT_ELAB/po/

    Returns:
        tuple: (success: bool, tsv_path: str|None, error_msg: str|None, stats: dict)
    """
    try:
        # Step 1: Lettura file
        _trace_step(id_file_ordine, 'lettura', 'success', f'Inizio lettura {os.path.basename(input_filepath)}')

        if not os.path.exists(input_filepath):
            error_msg = f'File non trovato: {input_filepath}'
            _trace_step(id_file_ordine, 'lettura', 'error', error_msg)
            return False, None, error_msg, {}

        # Leggi Excel (supporta .xlsx e .xls)
        try:
            df = pd.read_excel(input_filepath, engine='openpyxl' if input_filepath.endswith('.xlsx') else 'xlrd')
        except Exception as e:
            error_msg = f'Errore lettura Excel: {str(e)}'
            _trace_step(id_file_ordine, 'lettura', 'error', error_msg)
            return False, None, error_msg, {}

        _trace_step(id_file_ordine, 'lettura', 'success', f'Lette {len(df)} righe dal file Excel')

        # Step 2: Validazione struttura
        _trace_step(id_file_ordine, 'parsing', 'success', 'Inizio validazione struttura')

        # Controlla colonne
        colonne_presenti = df.columns.tolist()
        colonne_mancanti = [col for col in COLONNE_ORDINI if col not in colonne_presenti]

        if colonne_mancanti:
            error_msg = f'Colonne mancanti nel file Excel: {", ".join(colonne_mancanti)}'
            _trace_step(id_file_ordine, 'parsing', 'error', error_msg)
            return False, None, error_msg, {}

        # Seleziona solo le colonne necessarie (in caso ci siano colonne extra)
        df = df[COLONNE_ORDINI]

        # Rimuovi righe completamente vuote
        df = df.dropna(how='all')

        if len(df) == 0:
            error_msg = 'File Excel vuoto (nessuna riga con dati)'
            _trace_step(id_file_ordine, 'parsing', 'error', error_msg)
            return False, None, error_msg, {}

        # Step 3: Normalizzazione dati
        # Normalizza codice modello
        df['Model No. Normalized'] = df['Model No.'].apply(normalizza_codice_modello)

        # Gestisci valori nulli
        df = df.fillna({
            'Seller': '',
            'Seller desc': '',
            'Buyer': '',
            'Buyer desc': '',
            'PO No.': '',
            'Brand': '',
            'Item': '',
            'EAN': '',
            'Model No.': '',
            'Model No. Normalized': '',
            'CIF Price €': 0.0,
            'Q.TY': 0,
            'Amount €': 0.0
        })

        # Converti date (gestisci formati multipli)
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        except:
            df['Date'] = ''

        # Converti numerici
        try:
            df['CIF Price €'] = pd.to_numeric(df['CIF Price €'], errors='coerce').fillna(0.0)
            df['Q.TY'] = pd.to_numeric(df['Q.TY'], errors='coerce').fillna(0).astype(int)
            df['Amount €'] = pd.to_numeric(df['Amount €'], errors='coerce').fillna(0.0)
        except Exception as e:
            error_msg = f'Errore conversione dati numerici: {str(e)}'
            _trace_step(id_file_ordine, 'parsing', 'error', error_msg)
            return False, None, error_msg, {}

        # Validazioni business
        errori_validazione = []

        # Verifica che ci sia almeno un ordine
        if df['PO No.'].str.strip().eq('').all():
            errori_validazione.append('Nessun numero ordine (PO No.) trovato')

        # Verifica che ci siano modelli
        if df['Model No. Normalized'].str.strip().eq('').all():
            errori_validazione.append('Nessun codice modello (Model No.) trovato')

        if errori_validazione:
            error_msg = 'Errori validazione: ' + '; '.join(errori_validazione)
            _trace_step(id_file_ordine, 'parsing', 'error', error_msg)
            return False, None, error_msg, {}

        # Step 4: Genera TSV
        filename_base = Path(input_filepath).stem
        tsv_filename = f'{filename_base}.tsv'
        tsv_path = os.path.join(output_elab_dir, tsv_filename)

        # Assicurati che la directory esista
        os.makedirs(output_elab_dir, exist_ok=True)

        # Salva TSV (separatore TAB)
        df.to_csv(tsv_path, sep='\t', index=False, encoding='utf-8')

        # Statistiche
        n_righe = len(df)
        n_ordini_unici = df['PO No.'].nunique()
        n_modelli_unici = df['Model No. Normalized'].nunique()

        stats = {
            'n_righe': n_righe,
            'n_ordini_unici': n_ordini_unici,
            'n_modelli_unici': n_modelli_unici,
            'tsv_size_kb': round(os.path.getsize(tsv_path) / 1024, 2)
        }

        msg_success = f'TSV generato: {n_righe} righe, {n_ordini_unici} ordini, {n_modelli_unici} modelli'
        _trace_step(id_file_ordine, 'parsing', 'success', msg_success)

        return True, tsv_path, None, stats

    except Exception as e:
        error_msg = f'Errore imprevisto durante parsing: {str(e)}'
        _trace_step(id_file_ordine, 'parsing', 'error', error_msg)
        return False, None, error_msg, {}
