"""
Funzioni di utilità per elaborazione file rotture
"""
import pandas as pd
from datetime import datetime


def normalizza_codice(codice):
    """Normalizza un codice rimuovendo spazi, maiuscole e valori null"""
    if not codice or pd.isna(codice):
        return ''
    return str(codice).strip().lower().replace(' ', '')


def parse_date(date_value):
    """Converte un valore in data, gestendo vari formati"""
    if pd.isna(date_value) or date_value is None or date_value == '':
        return None
    try:
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, str):
            # Prova vari formati
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except:
                    continue
        return pd.to_datetime(date_value).date()
    except:
        return None


def elabora_file_rottura_completo(file_rottura, db, current_user, current_app, models_dict):
    """
    Elaborazione completa file rotture:
    1. Genera file TSV da Excel
    2. Legge TSV
    3. Inserisce/aggiorna database
    4. Gestisce trace ed errori

    Args:
        file_rottura: oggetto FileRottura
        db: istanza database
        current_user: utente corrente
        current_app: applicazione Flask
        models_dict: dizionario con modelli {Rottura, RotturaComponente, Modello, etc}

    Returns:
        tuple: (success: bool, message: str, num_rotture: int)
    """
    import os

    # Estrai modelli dal dizionario
    Rottura = models_dict['Rottura']
    RotturaComponente = models_dict['RotturaComponente']
    Modello = models_dict['Modello']
    Componente = models_dict['Componente']
    Utente = models_dict['Utente']
    Rivenditore = models_dict['Rivenditore']
    TraceElaborazioneFile = models_dict['TraceElaborazioneFile']
    TraceElaborazioneRecord = models_dict['TraceElaborazioneRecord']

    base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
    parsed_dir = os.path.join(base_dir, 'INPUT', 'rotture_parsed')
    os.makedirs(parsed_dir, exist_ok=True)

    # Nome file TSV
    name_without_ext = os.path.splitext(file_rottura.filename)[0]
    tsv_filename = f"{name_without_ext}_parsed.tsv"
    tsv_filepath = os.path.join(parsed_dir, tsv_filename)

    # Crea trace file
    trace_file = TraceElaborazioneFile(
        id_file=file_rottura.id,
        tipo_file='rotture',
        step='start',
        stato='start',
        messaggio=f'Inizio elaborazione file {file_rottura.filename}'
    )
    db.session.add(trace_file)
    db.session.flush()

    try:
        # STEP 1: Genera TSV da Excel
        trace_file.step = 'parse_excel'
        trace_file.messaggio = 'Lettura file Excel e generazione TSV'
        db.session.flush()

        df = pd.read_excel(file_rottura.filepath)

        # Salva come TSV
        df.to_csv(tsv_filepath, sep='\t', index=False, encoding='utf-8')

        trace_rec = TraceElaborazioneRecord(
            id_trace_file=trace_file.id_trace,
            tipo_record='file',
            record_key=tsv_filename,
            messaggio=f'File TSV generato: {len(df)} righe'
        )
        db.session.add(trace_rec)
        db.session.flush()

        # STEP 2: Leggi TSV e inserisci dati
        trace_file.step = 'insert_data'
        trace_file.messaggio = 'Inserimento dati nel database'
        db.session.flush()

        num_rotture = 0
        num_errori = 0
        user_id = current_user.id if current_user.is_authenticated else None

        for idx, row in df.iterrows():
            riga_file = idx + 2  # +2 perché idx parte da 0 e c'è l'header

            try:
                # Estrai dati dalla riga
                prot = str(row.get('prot', '')).strip()
                cod_modello = str(row.get('cod_modello', '')).strip()
                cod_componente_raw = str(row.get('cod_componente', '')).strip()

                if not prot:
                    raise ValueError("Protocollo mancante")

                # Normalizza codici
                cod_modello_norm = normalizza_codice(cod_modello)
                cod_componente_norm = normalizza_codice(cod_componente_raw)

                # Verifica modello
                if cod_modello_norm:
                    modello = Modello.query.filter_by(cod_modello_norm=cod_modello_norm).first()
                    if not modello:
                        # Modello non trovato - segnala e skippa
                        trace_rec = TraceElaborazioneRecord(
                            id_trace_file=trace_file.id_trace,
                            riga_file=riga_file,
                            tipo_record='rottura',
                            record_key=prot,
                            errore=f'Modello {cod_modello} non trovato in anagrafica'
                        )
                        db.session.add(trace_rec)
                        num_errori += 1
                        continue

                    # Aggiorna dati modello se presenti
                    if row.get('divisione'):
                        modello.divisione = str(row['divisione']).strip()
                    if row.get('marca'):
                        modello.marca = str(row['marca']).strip()
                    if row.get('desc_modello'):
                        modello.desc_modello = str(row['desc_modello']).strip()
                    if row.get('produttore'):
                        modello.produttore = str(row['produttore']).strip()
                    if row.get('famiglia'):
                        modello.famiglia = str(row['famiglia']).strip()
                    if row.get('tipo'):
                        modello.tipo = str(row['tipo']).strip()
                    modello.updated_by = user_id
                    modello.updated_from = 'rotture'

                # Gestisci Utente (insert/update)
                cod_utente = str(row.get('cod_utente', '')).strip()
                if cod_utente:
                    utente = Utente.query.get(cod_utente)
                    if not utente:
                        utente = Utente(cod_utente=cod_utente, created_by=user_id)
                        db.session.add(utente)
                    utente.pv_utente = str(row.get('pv_utente', '')).strip() if row.get('pv_utente') else None
                    utente.comune_utente = str(row.get('comune_utente', '')).strip() if row.get('comune_utente') else None
                    utente.updated_by = user_id

                # Gestisci Rivenditore (insert/update)
                cod_rivenditore = str(row.get('cod_rivenditore', '')).strip()
                if cod_rivenditore:
                    rivenditore = Rivenditore.query.get(cod_rivenditore)
                    if not rivenditore:
                        rivenditore = Rivenditore(cod_rivenditore=cod_rivenditore, created_by=user_id)
                        db.session.add(rivenditore)
                    rivenditore.pv_rivenditore = str(row.get('pv_rivenditore', '')).strip() if row.get('pv_rivenditore') else None
                    rivenditore.updated_by = user_id

                # Gestisci Componente (insert/update)
                if cod_componente_norm:
                    componente = Componente.query.filter_by(cod_componente_norm=cod_componente_norm).first()
                    if not componente:
                        componente = Componente(
                            cod_componente=cod_componente_raw,
                            cod_componente_norm=cod_componente_norm,
                            created_by=user_id
                        )
                        db.session.add(componente)
                    # Aggiorna campi non chiave (qui puoi aggiungere logica per altri campi)
                    componente.updated_by = user_id

                # Crea Rottura
                rottura = Rottura(
                    id_file_rotture=file_rottura.id,
                    prot=prot,
                    cod_modello=cod_modello if cod_modello else None,
                    cod_rivenditore=cod_rivenditore if cod_rivenditore else None,
                    cod_utente=cod_utente if cod_utente else None,
                    piattaforma=str(row.get('piattaforma', '')).strip() if row.get('piattaforma') else None,
                    cat=str(row.get('C.A.T.', '')).strip() if row.get('C.A.T.') else None,
                    flag_consumer=str(row.get('flag_consumer', '')).strip() if row.get('flag_consumer') else None,
                    flag_da_fatturare=str(row.get('flag_da_fatturare', '')).strip() if row.get('flag_da_fatturare') else None,
                    cod_matricola=str(row.get('cod_matricola', '')).strip() if row.get('cod_matricola') else None,
                    cod_modello_fabbrica=str(row.get('cod_modello_fabbrica', '')).strip() if row.get('cod_modello_fabbrica') else None,
                    data_competenza=parse_date(row.get('data_competenza')),
                    data_acquisto=parse_date(row.get('data_acquisto')),
                    data_apertura=parse_date(row.get('data_apertura')),
                    data_1=parse_date(row.get('data_1')),
                    data_2=parse_date(row.get('data_2')),
                    data_3=parse_date(row.get('data_3')),
                    data_4=parse_date(row.get('data_4')),
                    data_5=parse_date(row.get('data_5')),
                    data_6=parse_date(row.get('data_6')),
                    data_7=parse_date(row.get('data_7')),
                    difetto=str(row.get('difetto', '')).strip() if row.get('difetto') else None,
                    problema_segnalato=str(row.get('problema_segnalato', '')).strip() if row.get('problema_segnalato') else None,
                    riparazione=str(row.get('riparazione', '')).strip() if row.get('riparazione') else None,
                    gg_vita_prodotto=int(row.get('gg_vita_prodotto')) if pd.notna(row.get('gg_vita_prodotto')) else None,
                    qta=int(row.get('qtà')) if pd.notna(row.get('qtà')) else None,
                    pv_rivenditore=str(row.get('pv_rivenditore', '')).strip() if row.get('pv_rivenditore') else None,
                    pv_utente=str(row.get('pv_utente', '')).strip() if row.get('pv_utente') else None,
                    comune_utente=str(row.get('comune_utente', '')).strip() if row.get('comune_utente') else None,
                    divisione=str(row.get('divisione', '')).strip() if row.get('divisione') else None,
                    marca=str(row.get('marca', '')).strip() if row.get('marca') else None,
                    desc_modello=str(row.get('desc_modello', '')).strip() if row.get('desc_modello') else None,
                    produttore=str(row.get('produttore', '')).strip() if row.get('produttore') else None,
                    famiglia=str(row.get('famiglia', '')).strip() if row.get('famiglia') else None,
                    tipo=str(row.get('tipo', '')).strip() if row.get('tipo') else None,
                    created_by=user_id
                )
                db.session.add(rottura)
                db.session.flush()  # Per ottenere id_rottura

                # Crea relazione RotturaComponente
                if cod_componente_norm:
                    rottura_comp = RotturaComponente(
                        id_rottura=rottura.id_rottura,
                        cod_componente=cod_componente_raw,
                        created_by=user_id
                    )
                    db.session.add(rottura_comp)

                num_rotture += 1

            except Exception as e:
                # Trace errore per singola riga
                trace_rec = TraceElaborazioneRecord(
                    id_trace_file=trace_file.id_trace,
                    riga_file=riga_file,
                    tipo_record='rottura',
                    record_key=prot if 'prot' in locals() else f'riga_{riga_file}',
                    errore=str(e)
                )
                db.session.add(trace_rec)
                num_errori += 1
                continue

        if num_errori > 0:
            # Rollback se ci sono errori
            db.session.rollback()
            trace_file.stato = 'error'
            trace_file.messaggio = f'Errori durante elaborazione: {num_errori} righe con errori'
            db.session.commit()
            return False, f'{num_errori} righe con errori. Vedere trace per dettagli.', 0

        # Commit finale
        db.session.commit()

        # Trace successo
        trace_file.step = 'complete'
        trace_file.stato = 'success'
        trace_file.messaggio = f'Elaborazione completata: {num_rotture} rotture inserite'
        db.session.commit()

        return True, f'Elaborazione completata con successo', num_rotture

    except Exception as e:
        db.session.rollback()
        trace_file.stato = 'error'
        trace_file.step = 'error'
        trace_file.messaggio = f'Errore durante elaborazione: {str(e)}'
        db.session.commit()

        return False, f'Errore durante elaborazione: {str(e)}', 0
