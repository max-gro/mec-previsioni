"""
Inserimento dati ordini da TSV nel database
Gestisce transazione atomica con rollback in caso di errore
"""
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import (
    db, FileOrdini, Controparte, Modello, Ordine,
    TraceElaborazioneFile, TraceElaborazioneRecord
)


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


def _trace_record_error(id_trace_file, riga_file, tipo_record, record_key, record_data, errore):
    """Traccia errore a livello record"""
    trace_record = TraceElaborazioneRecord(
        id_trace_file=id_trace_file,
        riga_file=riga_file,
        tipo_record=tipo_record,
        record_key=record_key,
        record_data=record_data,
        errore=errore,
        timestamp=datetime.utcnow()
    )
    db.session.add(trace_record)
    db.session.commit()


def _get_or_create_controparte(cod_controparte, desc_controparte, user_id):
    """
    Ottieni o crea controparte
    Se esiste aggiorna tutti i campi, altrimenti inserisci

    Returns: cod_controparte (ID)
    """
    # Usa il codice come chiave univoca
    controparte = Controparte.query.filter_by(controparte=cod_controparte).first()

    if controparte:
        # Aggiorna tutti i campi
        controparte.descrizione = desc_controparte
        controparte.updated_at = datetime.utcnow()
        controparte.updated_by = user_id
    else:
        # Crea nuovo
        controparte = Controparte(
            controparte=cod_controparte,
            descrizione=desc_controparte,
            created_at=datetime.utcnow(),
            created_by=user_id,
            updated_at=datetime.utcnow(),
            updated_by=user_id
        )
        db.session.add(controparte)
        db.session.flush()  # Per ottenere l'ID

    return controparte.id


def _get_or_create_modello(row, user_id):
    """
    Ottieni o crea modello
    Se esiste aggiorna tutti i campi, altrimenti inserisci

    Args:
        row: riga pandas con dati modello
        user_id: ID utente

    Returns: cod_modello (ID)
    """
    cod_modello_norm = row.get('Model No. Normalized', '').strip()

    if not cod_modello_norm:
        raise ValueError('Codice modello normalizzato vuoto')

    modello = Modello.query.filter_by(cod_modello_norm=cod_modello_norm).first()

    if modello:
        # Aggiorna tutti i campi
        modello.cod_modello_fabbrica = row.get('Model No.', '')
        modello.nome_modello = row.get('Item', '')
        modello.marca = row.get('Brand', '')
        modello.updated_at = datetime.utcnow()
        modello.updated_by = user_id
        modello.updated_from = 'ord'
    else:
        # Crea nuovo
        modello = Modello(
            cod_modello_norm=cod_modello_norm,
            cod_modello_fabbrica=row.get('Model No.', ''),
            nome_modello=row.get('Item', ''),
            marca=row.get('Brand', ''),
            created_at=datetime.utcnow(),
            created_by=user_id,
            updated_at=datetime.utcnow(),
            updated_by=user_id,
            updated_from='ord'
        )
        db.session.add(modello)
        db.session.flush()  # Per ottenere l'ID

    return modello.id


def inserisci_ordine_da_tsv(id_file_ordine, tsv_path, user_id):
    """
    Legge TSV e inserisce dati in DB (transazione atomica)

    Args:
        id_file_ordine: ID del record FileOrdini
        tsv_path: Percorso file TSV in OUTPUT_ELAB/po/
        user_id: ID utente che ha richiesto l'elaborazione

    Returns:
        tuple: (success: bool, stats: dict, error_msg: str|None)

    Logic:
        1. Verifica filename univoco (no duplicati in file_ordini)
        2. Inserisce/aggiorna controparti (seller, buyer)
        3. Inserisce/aggiorna modelli
        4. Inserisce ordini (verifica unicità cod_ordine|cod_modello)
        5. Aggiorna file_ordini (cod_seller, cod_buyer, data_ordine, oggetto_ordine)

    Se errore su singolo record:
        - Traccia in trace_elaborazioni_record
        - Rollback completo transazione
        - Ritorna (False, {}, error_summary)

    Se tutto ok:
        - Commit
        - Ritorna (True, stats, None)
    """
    id_trace_file = None

    try:
        # Step 1: Verifica esistenza file
        id_trace_file = _trace_step(id_file_ordine, 'inserimento_db', 'success', f'Inizio inserimento da {os.path.basename(tsv_path)}')

        if not os.path.exists(tsv_path):
            error_msg = f'File TSV non trovato: {tsv_path}'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            return False, {}, error_msg

        # Leggi TSV
        df = pd.read_csv(tsv_path, sep='\t', encoding='utf-8')

        if len(df) == 0:
            error_msg = 'File TSV vuoto'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            return False, {}, error_msg

        # Step 2: Ottieni file_ordine e verifica univocità filename
        file_ordine = FileOrdini.query.get(id_file_ordine)
        if not file_ordine:
            error_msg = f'Record FileOrdini {id_file_ordine} non trovato'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            return False, {}, error_msg

        # Verifica che non esista già un altro file con lo stesso nome (escludendo questo)
        duplicato = FileOrdini.query.filter(
            FileOrdini.filename == file_ordine.filename,
            FileOrdini.id != id_file_ordine,
            FileOrdini.esito == 'Elaborato'
        ).first()

        if duplicato:
            error_msg = f'File con nome {file_ordine.filename} già elaborato (ID: {duplicato.id}). Eliminare prima il precedente.'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            return False, {}, error_msg

        # Step 3: Elabora controparti (Seller e Buyer)
        # Prendi primo record per Seller/Buyer (assumiamo siano gli stessi per tutto l'ordine)
        first_row = df.iloc[0]

        seller_code = str(first_row['Seller']).strip()
        buyer_code = str(first_row['Buyer']).strip()

        if not seller_code or not buyer_code:
            error_msg = 'Seller o Buyer mancanti nel file'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            return False, {}, error_msg

        try:
            cod_seller = _get_or_create_controparte(seller_code, first_row.get('Seller desc', ''), user_id)
            cod_buyer = _get_or_create_controparte(buyer_code, first_row.get('Buyer desc', ''), user_id)
        except Exception as e:
            error_msg = f'Errore creazione controparti: {str(e)}'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            db.session.rollback()
            return False, {}, error_msg

        # Step 4: Aggiorna file_ordine con dati ordine
        try:
            # Data ordine (primo record)
            data_ordine_str = first_row.get('Date', '')
            if data_ordine_str:
                file_ordine.data_ordine = datetime.strptime(data_ordine_str, '%Y-%m-%d').date()

            file_ordine.cod_seller = cod_seller
            file_ordine.cod_buyer = cod_buyer
            file_ordine.oggetto_ordine = f"Ordine {first_row.get('PO No.', 'N/A')}"
            file_ordine.updated_at = datetime.utcnow()
            file_ordine.updated_by = user_id

        except Exception as e:
            error_msg = f'Errore aggiornamento file_ordine: {str(e)}'
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
            db.session.rollback()
            return False, {}, error_msg

        # Step 5: Elabora righe ordine
        stats = {
            'n_controparti_inserite': 0,
            'n_controparti_aggiornate': 0,
            'n_modelli_inseriti': 0,
            'n_modelli_aggiornati': 0,
            'n_ordini': 0
        }

        modelli_processati = set()
        ordini_inseriti = []

        for idx, row in df.iterrows():
            riga_file = idx + 2  # +2 perché idx parte da 0 e c'è l'header

            try:
                # Gestisci modello
                cod_modello_norm = row.get('Model No. Normalized', '').strip()

                if not cod_modello_norm:
                    error_msg = f'Codice modello vuoto alla riga {riga_file}'
                    _trace_record_error(
                        id_trace_file, riga_file, 'modello', '',
                        row.to_dict(), error_msg
                    )
                    raise ValueError(error_msg)

                # Traccia se modello è nuovo o aggiornato
                modello_esistente = Modello.query.filter_by(cod_modello_norm=cod_modello_norm).first()

                cod_modello = _get_or_create_modello(row, user_id)

                if cod_modello_norm not in modelli_processati:
                    if modello_esistente:
                        stats['n_modelli_aggiornati'] += 1
                    else:
                        stats['n_modelli_inseriti'] += 1
                    modelli_processati.add(cod_modello_norm)

                # Inserisci ordine
                cod_ordine = str(row.get('PO No.', '')).strip()

                if not cod_ordine:
                    error_msg = f'Numero ordine (PO No.) vuoto alla riga {riga_file}'
                    _trace_record_error(
                        id_trace_file, riga_file, 'ordine', '',
                        row.to_dict(), error_msg
                    )
                    raise ValueError(error_msg)

                # Verifica unicità ordine-modello
                ordine_modello_pk = f"{cod_ordine}|{cod_modello}"

                ordine_esistente = Ordine.query.filter_by(ordine_modello_pk=ordine_modello_pk).first()

                if ordine_esistente:
                    error_msg = f'Ordine-modello duplicato: {ordine_modello_pk} alla riga {riga_file}'
                    _trace_record_error(
                        id_trace_file, riga_file, 'ordine', ordine_modello_pk,
                        row.to_dict(), error_msg
                    )
                    raise ValueError(error_msg)

                # Crea ordine
                ordine = Ordine(
                    ordine_modello_pk=ordine_modello_pk,
                    id_file_ordine=id_file_ordine,
                    cod_ordine=cod_ordine,
                    cod_modello=cod_modello,
                    brand=row.get('Brand', ''),
                    item=row.get('Item', ''),
                    ean=row.get('EAN', ''),
                    prezzo_eur=float(row.get('CIF Price €', 0)),
                    qta=int(row.get('Q.TY', 0)),
                    importo_eur=float(row.get('Amount €', 0)),
                    created_at=datetime.utcnow(),
                    created_by=user_id,
                    updated_at=datetime.utcnow(),
                    updated_by=user_id
                )

                db.session.add(ordine)
                ordini_inseriti.append(ordine_modello_pk)
                stats['n_ordini'] += 1

            except Exception as e:
                error_msg = f'Errore elaborazione riga {riga_file}: {str(e)}'
                _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)
                db.session.rollback()
                return False, {}, error_msg

        # Step 6: Commit transazione
        db.session.commit()

        msg_success = f'Inseriti {stats["n_ordini"]} ordini, {stats["n_modelli_inseriti"]} nuovi modelli, {stats["n_modelli_aggiornati"]} modelli aggiornati'
        _trace_step(id_file_ordine, 'inserimento_db', 'success', msg_success)

        return True, stats, None

    except Exception as e:
        db.session.rollback()
        error_msg = f'Errore imprevisto durante inserimento DB: {str(e)}'

        if id_trace_file:
            _trace_step(id_file_ordine, 'inserimento_db', 'error', error_msg)

        return False, {}, error_msg
