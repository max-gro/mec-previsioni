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


def elabora_file_rottura_completo(file_rottura, db, current_user, current_app, models_dict, log_session):
    """
    Elaborazione completa file rotture:
    1. Genera file TSV da Excel
    2. Legge TSV
    3. Inserisce/aggiorna database
    4. Gestisce trace ed errori (AUTONOMOUS TRANSACTION per log)

    Args:
        file_rottura: oggetto FileRottura
        db: istanza database
        current_user: utente corrente
        current_app: applicazione Flask
        models_dict: dizionario con modelli {Rottura, RotturaComponente, Modello, etc}
        log_session: sessione separata per log (AUTONOMOUS TRANSACTION)

    Returns:
        tuple: (success: bool, message: str, num_rotture: int)
    """
    import os

    # Estrai modelli dal dizionario
    Rottura = models_dict['Rottura']
    RotturaComponente = models_dict['RotturaComponente']
    Modello = models_dict['Modello']
    Componente = models_dict['Componente']
    UtenteRottura = models_dict['UtenteRottura']
    Rivenditore = models_dict['Rivenditore']
    TraceElab = models_dict['TraceElab']
    TraceElabDett = models_dict['TraceElabDett']

    base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
    parsed_dir = os.path.join(base_dir, 'INPUT', 'rotture_parsed')
    os.makedirs(parsed_dir, exist_ok=True)

    # Nome file TSV
    name_without_ext = os.path.splitext(file_rottura.filename)[0]
    tsv_filename = f"{name_without_ext}_parsed.tsv"
    tsv_filepath = os.path.join(parsed_dir, tsv_filename)

    # Genera nuovo id_elab
    result = db.session.execute(db.text("SELECT nextval('seq_id_elab')"))
    id_elab = result.scalar()

    # Crea trace START
    trace_start = TraceElab(
        id_elab=id_elab,
        id_file=file_rottura.id,
        tipo_file='ROT',
        step='START',
        stato='OK',
        messaggio=f'Inizio elaborazione file {file_rottura.filename}'
    )
    log_session.add(trace_start)
    log_session.commit()  # ← AUTONOMOUS: Commit immediato

    # Usa trace_start.id_trace per i dettagli
    id_trace_start = trace_start.id_trace

    try:
        # STEP 1: Genera TSV da Excel
        df = pd.read_excel(file_rottura.filepath)

        # Normalizza nomi colonne: rimuovi punti finali, trim, lowercase
        # Mapping colonne Excel → colonne attese dal codice
        column_mapping = {
            # Campi principali
            'Prot.': 'prot',
            'Piattaforma': 'piattaforma',
            'Rivenditore': 'cod_rivenditore',
            'Prov. Riv.': 'pv_rivenditore',
            'Utente': 'cod_utente',
            'Comune Utente': 'comune_utente',
            'Prov. Ut.': 'pv_utente',
            'C.A.T.': 'C.A.T.',
            'Consumo': 'flag_consumer',
            'Da fatturare': 'flag_da_fatturare',
            'Data Competenza': 'data_competenza',
            'Anno Competenza': 'anno_competenza',
            'Mese Competenza': 'mese_competenza',

            # Modello
            'Divisione': 'divisione',
            'Marca': 'marca',
            'Descrizione': 'desc_modello',
            'Matricola': 'cod_matricola',
            'Produttore': 'produttore',
            'Modello Fabbrica': 'cod_modello_fabbrica',
            'Famiglia': 'famiglia',
            'Tipo': 'tipo',
            'Modello': 'cod_modello',

            # Date
            'Data Acquisto': 'data_acquisto',
            'Data Apertura': 'data_apertura',
            'Data Assegnazione': 'data_1',
            'Data Accettazione': 'data_2',
            'Data Appuntamento': 'data_3',
            'Data Fine': 'data_4',
            'Data Approvazione': 'data_5',
            'Data Autorizzazione': 'data_6',
            'Data Chiusura': 'data_7',
            'Data Stato': 'data_stato',
            'Data fine CAT': 'data_fine_cat',

            # Ricambi (possono essere più colonne: Ricambio, Ricambio.1, Ricambio.2, etc.)
            'Ricambio': 'cod_componente',
            'Ricambio.1': 'cod_componente_1',
            'Ricambio.2': 'cod_componente_2',
            'Ricambio.3': 'cod_componente_3',
            'Ricambio.4': 'cod_componente_4',
            'Ricambio.5': 'cod_componente_5',

            # Attività
            'Attivita\'': 'attivita',
            'Attivita\'.1': 'attivita_1',
            'Attivita\'.2': 'attivita_2',
            'Attivita\'.3': 'attivita_3',
            'Attivita\'.4': 'attivita_4',
            'Attivita\'.5': 'attivita_5',
            'Numero Attivita\'': 'numero_attivita',
            'Importo Attitivita\'': 'importo_attitivita',

            # Problemi e riparazione
            'Difetto': 'difetto',
            'Problema Segnalato': 'problema_segnalato',
            'Descrizione Riparazione': 'riparazione',

            # Importi
            'Causale Extra': 'causale_extra',
            'Importo Extra': 'importo_extra',
            'Variaz %': 'variaz_perc',
            'Importo Variazione': 'importo_variazione',
            'Importo Totale': 'importo_totale',

            # Contatori
            'Nr Ricambi': 'nr_ricambi',
            'Nr Pezzi': 'qtà',
            'Nr Ordini': 'nr_ordini',
            'Nr App': 'nr_app',

            # Stato e info
            'Stato': 'stato',
            'Soluzione': 'soluzione',
            'Giorni Vita Prodotto': 'gg_vita_prodotto',
            'Mesi Vita Prodotto': 'mesi_vita_prodotto',

            # Ritorni
            'Ritorno': 'ritorno',
            'Ritorno x CAT': 'ritorno_x_cat',
            'Ritorno x PROD': 'ritorno_x_prod',

            # Causali e flags
            'Causale': 'causale',
            'Triang.': 'triang',
            'Riass.': 'riass',

            # Rimborsi
            'Rimb Prod': 'rimb_prod',
            'Rimb Smalt': 'rimb_smalt',
            'Rimb Reinst': 'rimb_reinst',
            'Rimb Tot': 'rimb_tot',

            # FG
            'FG': 'fg',
            'FG Non Pagata': 'fg_non_pagata',
            'Valore FG Non Pagata': 'valore_fg_non_pagata',

            # Anno/Mese
            'Anno Acquisto': 'anno_acquisto',
            'Mese Acquisto': 'mese_acquisto',
            'Anno Apertura': 'anno_apertura',
            'Mese Apertura': 'mese_apertura',
            'Anno Assegnazione': 'anno_assegnazione',
            'Mese Assegnazione': 'mese_assegnazione',

            # Altri campi
            'Giorni Riparazione': 'giorni_riparazione',
            'Causale Sostituzione': 'causale_sostituzione',
            'Addebito': 'addebito',
            'Apertura PV': 'apertura_pv',
            'KM Richiesti': 'km_richiesti',
            'Tipo Fatturazione': 'tipo_fatturazione'
        }

        # Rinomina colonne presenti nel mapping
        df.rename(columns=column_mapping, inplace=True)

        # Salva come TSV
        df.to_csv(tsv_filepath, sep='\t', index=False, encoding='utf-8')

        trace_rec = TraceElabDett(
            id_trace=id_trace_start,
            record_pos=0,
            record_data={'key': tsv_filename},
            messaggio=f'File TSV generato: {len(df)} righe',
            stato='OK'
        )
        log_session.add(trace_rec)
        log_session.commit()  # ← AUTONOMOUS: Log record persistito

        # STEP 2: Leggi TSV e inserisci dati

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
                        trace_rec = TraceElabDett(
                            id_trace=id_trace_start,
                            record_pos=riga_file,
                            record_data={'key': f'rottura|{prot}'},
                            stato='KO',
                            messaggio=f'Modello {cod_modello} non trovato in anagrafica'
                        )
                        log_session.add(trace_rec)
                        num_errori += 1
                        continue

                    # Aggiorna dati modello se presenti
                    modello_aggiornato = False
                    if row.get('divisione'):
                        modello.divisione = str(row['divisione']).strip()
                        modello_aggiornato = True
                    if row.get('marca'):
                        modello.marca = str(row['marca']).strip()
                        modello_aggiornato = True
                    if row.get('desc_modello'):
                        modello.desc_modello = str(row['desc_modello']).strip()
                        modello_aggiornato = True
                    if row.get('produttore'):
                        modello.produttore = str(row['produttore']).strip()
                        modello_aggiornato = True
                    if row.get('famiglia'):
                        modello.famiglia = str(row['famiglia']).strip()
                        modello_aggiornato = True
                    if row.get('tipo'):
                        modello.tipo = str(row['tipo']).strip()
                        modello_aggiornato = True
                    modello.updated_by = user_id
                    modello.updated_from = 'rotture'

                    # Trace UPDATE modello
                    if modello_aggiornato:
                        trace_rec = TraceElabDett(
                            id_trace=id_trace_start,
                            record_pos=riga_file,
                            record_data={
                                'tipo': 'UPDATE_MODELLO',
                                'cod_modello': cod_modello,
                                'divisione': modello.divisione,
                                'marca': modello.marca
                            },
                            stato='OK',
                            messaggio=f'Aggiornato modello {cod_modello} da rotture'
                        )
                        log_session.add(trace_rec)

                # Gestisci UtenteRottura (insert/update)
                cod_utente = str(row.get('cod_utente', '')).strip()
                if cod_utente:
                    utente = UtenteRottura.query.get(cod_utente)
                    utente_is_new = (utente is None)
                    if not utente:
                        utente = UtenteRottura(cod_utente_rottura=cod_utente, created_by=user_id)
                        db.session.add(utente)
                    utente.pv_utente_rottura = str(row.get('pv_utente', '')).strip() if row.get('pv_utente') else None
                    utente.comune_utente_rottura = str(row.get('comune_utente', '')).strip() if row.get('comune_utente') else None
                    utente.updated_by = user_id

                    # Trace CREATE/UPDATE utente
                    trace_rec = TraceElabDett(
                        id_trace=id_trace_start,
                        record_pos=riga_file,
                        record_data={
                            'tipo': 'CREATE_UTENTE' if utente_is_new else 'UPDATE_UTENTE',
                            'cod_utente': cod_utente,
                            'pv': utente.pv_utente_rottura,
                            'comune': utente.comune_utente_rottura
                        },
                        stato='OK',
                        messaggio=f'{"Creato" if utente_is_new else "Aggiornato"} utente {cod_utente}'
                    )
                    log_session.add(trace_rec)

                # Gestisci Rivenditore (insert/update)
                cod_rivenditore = str(row.get('cod_rivenditore', '')).strip()
                if cod_rivenditore:
                    rivenditore = Rivenditore.query.get(cod_rivenditore)
                    rivenditore_is_new = (rivenditore is None)
                    if not rivenditore:
                        rivenditore = Rivenditore(cod_rivenditore=cod_rivenditore, created_by=user_id)
                        db.session.add(rivenditore)
                    rivenditore.pv_rivenditore = str(row.get('pv_rivenditore', '')).strip() if row.get('pv_rivenditore') else None
                    rivenditore.updated_by = user_id

                    # Trace CREATE/UPDATE rivenditore
                    trace_rec = TraceElabDett(
                        id_trace=id_trace_start,
                        record_pos=riga_file,
                        record_data={
                            'tipo': 'CREATE_RIVENDITORE' if rivenditore_is_new else 'UPDATE_RIVENDITORE',
                            'cod_rivenditore': cod_rivenditore,
                            'pv': rivenditore.pv_rivenditore
                        },
                        stato='OK',
                        messaggio=f'{"Creato" if rivenditore_is_new else "Aggiornato"} rivenditore {cod_rivenditore}'
                    )
                    log_session.add(trace_rec)

                # Gestisci Componente (READ only - no trace, solo READ)
                if cod_componente_norm:
                    componente = Componente.query.filter_by(cod_componente_norm=cod_componente_norm).first()
                    if not componente:
                        # Nota: secondo le specifiche, i componenti dovrebbero essere READ only
                        # Ma il codice esistente li crea se non esistono - mantengo comportamento
                        componente = Componente(
                            cod_componente=cod_componente_raw,
                            cod_componente_norm=cod_componente_norm,
                            created_by=user_id
                        )
                        db.session.add(componente)

                        # Trace CREATE componente (anche se non nelle specifiche originali)
                        trace_rec = TraceElabDett(
                            id_trace=id_trace_start,
                            record_pos=riga_file,
                            record_data={
                                'tipo': 'CREATE_COMPONENTE',
                                'cod_componente': cod_componente_raw
                            },
                            stato='WARN',
                            messaggio=f'Creato componente {cod_componente_raw} (non presente in anagrafiche)'
                        )
                        log_session.add(trace_rec)
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

                # Trace CREATE rottura
                trace_rec = TraceElabDett(
                    id_trace=id_trace_start,
                    record_pos=riga_file,
                    record_data={
                        'tipo': 'CREATE_ROTTURA',
                        'prot': prot,
                        'cod_modello': cod_modello,
                        'cod_matricola': rottura.cod_matricola,
                        'difetto': rottura.difetto
                    },
                    stato='OK',
                    messaggio=f'Creata rottura {prot} per modello {cod_modello}'
                )
                log_session.add(trace_rec)

                # Crea relazione RotturaComponente
                if cod_componente_norm:
                    rottura_comp = RotturaComponente(
                        id_rottura=rottura.id_rottura,
                        cod_componente=cod_componente_raw,
                        created_by=user_id
                    )
                    db.session.add(rottura_comp)

                    # Trace CREATE rottura_componente
                    trace_rec = TraceElabDett(
                        id_trace=id_trace_start,
                        record_pos=riga_file,
                        record_data={
                            'tipo': 'CREATE_ROTTURA_COMPONENTE',
                            'prot': prot,
                            'id_rottura': rottura.id_rottura,
                            'cod_componente': cod_componente_raw
                        },
                        stato='OK',
                        messaggio=f'Associato componente {cod_componente_raw} a rottura {prot}'
                    )
                    log_session.add(trace_rec)

                num_rotture += 1

            except Exception as e:
                # Trace errore per singola riga
                trace_rec = TraceElabDett(
                    id_trace=id_trace_start,
                    record_pos=riga_file,
                    record_data={'key': prot if 'prot' in locals() else f'riga_{riga_file}'},
                    stato='KO',
                    messaggio=str(e)
                )
                log_session.add(trace_rec)
                num_errori += 1
                continue

        # ALL OR NOTHING: se anche una sola riga ha errori, rollback completo
        if num_errori > 0:
            db.session.rollback()

            # Crea trace END con errore
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=file_rottura.id,
                tipo_file='ROT',
                step='END',
                stato='KO',
                messaggio=f'Elaborazione fallita: {num_errori} righe con errori su {len(df)} totali',
                righe_totali=len(df),
                righe_ok=0,
                righe_errore=num_errori,
                righe_warning=0
            )
            log_session.add(trace_end)
            log_session.commit()  # ← AUTONOMOUS: Log END persistito

            return False, f'Elaborazione fallita: {num_errori} righe con errori. Vedere trace per dettagli.', 0

        # Commit finale tabelle operative (DB SESSION - TRANSAZIONALE)
        db.session.commit()  # ← Se fallisce, i log sono GIÀ salvati!

        # Crea trace END con successo (tutte le righe OK)
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=file_rottura.id,
            tipo_file='ROT',
            step='END',
            stato='OK',
            messaggio=f'Elaborazione completata: {num_rotture} rotture inserite su {len(df)} righe',
            righe_totali=len(df),
            righe_ok=num_rotture,
            righe_errore=0,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS: Log END persistito

        return True, f'Elaborazione completata con successo: {num_rotture} rotture inserite', num_rotture

    except Exception as e:
        db.session.rollback()  # ← Rollback solo tabelle operative, log già salvati!

        # Crea trace END con errore critico
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=file_rottura.id,
            tipo_file='ROT',
            step='END',
            stato='KO',
            messaggio=f'Errore durante elaborazione: {str(e)}',
            righe_totali=0,
            righe_ok=0,
            righe_errore=1,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS: Log END persistito anche su errore

        return False, f'Errore durante elaborazione: {str(e)}', 0
