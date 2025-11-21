"""
Funzioni di elaborazione per inserimento ordini da TSV nel database
"""
from datetime import datetime
from models import db, FileOrdine, Controparte, Modello, Ordine
from utils.db_log import log_session
import logging

logger = logging.getLogger(__name__)


def normalizza_codice(codice):
    """Normalizza un codice per ricerca/confronto"""
    if not codice:
        return ''
    return str(codice).strip().upper()


def upsert_controparte(cod_controparte, controparte_desc, current_user_id=0):
    """
    Inserisce o aggiorna una controparte.

    Args:
        cod_controparte: codice controparte
        controparte_desc: descrizione controparte
        current_user_id: ID utente corrente

    Returns:
        Controparte: oggetto controparte (nuovo o aggiornato)
    """
    cod_norm = normalizza_codice(cod_controparte)

    # Cerca per codice
    controparte = Controparte.query.filter_by(cod_controparte=cod_norm).first()

    if controparte:
        # Record esistente: SEMPRE aggiorna tracciatura (anche se dati non cambiano)
        # Aggiorna descrizione se cambiata
        if controparte.controparte != controparte_desc:
            controparte.controparte = controparte_desc
            logger.info(f"Controparte aggiornata: {cod_norm} -> {controparte_desc}")

        # ✅ SEMPRE traccia l'update (anche se dati uguali)
        controparte.updated_at = datetime.utcnow()
        controparte.updated_by = current_user_id
    else:
        # Inserisci nuova controparte
        controparte = Controparte(
            cod_controparte=cod_norm,
            controparte=controparte_desc,
            created_by=current_user_id
        )
        db.session.add(controparte)
        logger.info(f"Controparte inserita: {cod_norm} -> {controparte_desc}")

    return controparte


def upsert_modello(model_no, brand=None, current_user_id=0):
    """
    Inserisce o aggiorna un modello.

    Args:
        model_no: codice modello
        brand: marca (opzionale)
        current_user_id: ID utente corrente

    Returns:
        Modello: oggetto modello (nuovo o esistente)
    """
    cod_norm = normalizza_codice(model_no)

    # Cerca per codice normalizzato
    modello = Modello.query.filter_by(cod_modello_norm=cod_norm).first()

    if modello:
        # Record esistente: SEMPRE aggiorna tracciatura (anche se dati non cambiano)
        # Aggiorna marca se fornita e mancante
        if brand and not modello.marca:
            modello.marca = brand
            logger.info(f"Modello aggiornato con marca: {model_no} -> {brand}")

        # ✅ SEMPRE traccia l'update (anche se dati uguali)
        modello.updated_at = datetime.utcnow()
        modello.updated_by = current_user_id
        modello.updated_from = 'ORD'
    else:
        # Inserisci nuovo modello
        modello = Modello(
            cod_modello=model_no,
            cod_modello_norm=cod_norm,
            nome_modello=model_no,  # Default: usa stesso codice
            marca=brand,
            created_by=current_user_id,
            updated_from='ORD'
        )
        db.session.add(modello)
        logger.info(f"Modello inserito: {model_no} (marca: {brand})")

    return modello


def elabora_tsv_ordine(file_ordine_id, tsv_filepath, current_user_id=0):
    """
    Elabora un file TSV ordini e popola il database.

    Tabelle coinvolte:
    - controparti: upsert seller/buyer
    - file_ordini: aggiorna cod_seller, cod_buyer, data_ordine, oggetto_ordine
    - modelli: upsert modelli se mancanti
    - ordini: inserisce righe ordine

    Args:
        file_ordine_id: ID del FileOrdine in elaborazione
        tsv_filepath: path del file TSV da elaborare
        current_user_id: ID utente corrente

    Returns:
        tuple: (success: bool, message: str, stats: dict)
    """
    # Recupera FileOrdine
    file_ordine = FileOrdine.query.get(file_ordine_id)
    if not file_ordine:
        return False, "FileOrdine non trovato", {}

    try:
        # Leggi TSV
        with open(tsv_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 2:
            return False, "TSV vuoto o solo header", {}

        header = lines[0].strip().split('\t')
        righe_dati = [line.strip().split('\t') for line in lines[1:] if line.strip()]

        logger.info(f"Elaborazione TSV: {len(righe_dati)} righe da processare")

        # Statistiche
        num_righe_processate = 0
        num_righe_ok = 0
        num_errori = 0
        num_warnings = 0
        errori_dettaglio = []
        warnings_dettaglio = []

        # Metadati ordine (dalla prima riga)
        if righe_dati:
            prima_riga = righe_dati[0]
            if len(prima_riga) >= 15:
                cod_seller = prima_riga[1]
                seller_desc = prima_riga[2]
                cod_buyer = prima_riga[3]
                buyer_desc = prima_riga[4]
                data_ordine_str = prima_riga[5]
                oggetto_ordine = prima_riga[6]

                # STEP 1: Upsert controparti
                seller = upsert_controparte(cod_seller, seller_desc, current_user_id)
                buyer = upsert_controparte(cod_buyer, buyer_desc, current_user_id)
                db.session.flush()  # Assicura FK disponibili

                # STEP 2: Aggiorna FileOrdine con controparti e metadati
                file_ordine.cod_seller = seller.cod_controparte
                file_ordine.cod_buyer = buyer.cod_controparte
                file_ordine.data_ordine = datetime.strptime(data_ordine_str, '%Y-%m-%d').date()
                file_ordine.oggetto_ordine = oggetto_ordine
                file_ordine.updated_at = datetime.utcnow()
                file_ordine.updated_by = current_user_id
                db.session.flush()

                logger.info(f"FileOrdine aggiornato: seller={seller.cod_controparte}, buyer={buyer.cod_controparte}")

        # STEP 3: Processa righe ordine
        for idx, riga in enumerate(righe_dati, start=2):  # +2 per contare dall'header
            num_righe_processate += 1

            try:
                if len(riga) != 15:
                    errore = f"Riga {idx}: numero colonne errato (atteso 15, trovato {len(riga)})"
                    errori_dettaglio.append(errore)
                    num_errori += 1
                    continue

                # Estrai campi
                file, cod_seller, seller, cod_buyer, buyer, date_str, obj, po, brand, item, ean, model_no, price_str, qty_str, amount_str = riga

                # Validazioni
                if not model_no:
                    errore = f"Riga {idx}: model_no mancante"
                    errori_dettaglio.append(errore)
                    num_errori += 1
                    continue

                if not po:
                    errore = f"Riga {idx}: numero PO mancante"
                    errori_dettaglio.append(errore)
                    num_errori += 1
                    continue

                # Parse numeri
                try:
                    price_eur = float(price_str) if price_str else None
                    qty = int(qty_str) if qty_str else None
                    amount_eur = float(amount_str) if amount_str else None
                except ValueError as e:
                    errore = f"Riga {idx}: errore parsing numeri ({str(e)})"
                    errori_dettaglio.append(errore)
                    num_errori += 1
                    continue

                # Warning per dati sospetti
                if price_eur and price_eur <= 0:
                    warning = f"Riga {idx}: prezzo <= 0 ({price_eur})"
                    warnings_dettaglio.append(warning)
                    num_warnings += 1

                if qty and qty <= 0:
                    warning = f"Riga {idx}: quantità <= 0 ({qty})"
                    warnings_dettaglio.append(warning)
                    num_warnings += 1

                # STEP 3A: Upsert modello
                modello = upsert_modello(model_no, brand, current_user_id)
                db.session.flush()

                # STEP 3B: Inserisci riga ordine
                ordine_modello_key = f"{po}|{modello.cod_modello}"

                # Verifica se esiste già
                existing = Ordine.query.filter_by(
                    cod_ordine=po,
                    cod_modello=modello.cod_modello
                ).first()

                if existing:
                    warning = f"Riga {idx}: ordine già esistente per PO={po}, modello={model_no} (skip)"
                    warnings_dettaglio.append(warning)
                    num_warnings += 1
                    continue

                # Inserisci nuovo ordine
                ordine = Ordine(
                    ordine_modello=ordine_modello_key,
                    id_file_ordine=file_ordine_id,
                    cod_ordine=po,
                    cod_modello=modello.cod_modello,
                    brand=brand if brand else None,
                    item=item if item else None,
                    ean=ean if ean else None,
                    prezzo_eur=price_eur,
                    qta=qty,
                    importo_eur=amount_eur,
                    created_by=current_user_id
                )
                db.session.add(ordine)
                num_righe_ok += 1

            except Exception as e:
                errore = f"Riga {idx}: errore imprevisto ({str(e)})"
                errori_dettaglio.append(errore)
                num_errori += 1
                logger.exception(f"Errore processing riga {idx}: {e}")

        # Statistiche finali
        stats = {
            'righe_processate': num_righe_processate,
            'righe_ok': num_righe_ok,
            'errori': num_errori,
            'warnings': num_warnings,
            'errori_dettaglio': errori_dettaglio[:20],  # Max 20 per log
            'warnings_dettaglio': warnings_dettaglio[:20]
        }

        # STEP 4: ALL OR NOTHING - Commit solo se TUTTE le righe sono OK
        if num_errori > 0:
            db.session.rollback()
            logger.warning(f"[ELAB ORD] Rollback completo: {num_errori} righe con errori su {num_righe_processate} totali")
            return False, f"Elaborazione fallita: {num_errori} righe con errori (rollback completo)", stats

        # Tutte le righe OK - Commit
        db.session.commit()
        logger.info(f"[ELAB ORD] Commit DB: {num_righe_ok} righe ordini inserite (tutte OK)")

        success_msg = f"Elaborazione completata: {num_righe_ok} righe inserite"
        if num_warnings > 0:
            success_msg += f" ({num_warnings} warning)"

        return True, success_msg, stats

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Errore elaborazione TSV: {e}")
        return False, f"Errore durante elaborazione TSV: {str(e)}", {}
