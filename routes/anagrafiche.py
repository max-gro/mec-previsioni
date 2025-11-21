"""
Blueprint per la gestione Anagrafiche File Excel (CRUD + Upload)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, FileAnagrafica, Modello, Componente, ModelloComponente, TraceElab, TraceElabDett
from forms import AnagraficaFileForm, AnagraficaFileEditForm, NuovaMarcaForm
from utils.decorators import admin_required
from utils.db_log import log_session  # Sessione separata per log (AUTONOMOUS TRANSACTION)
import os
import shutil
import random
import time
import logging
import csv
import re
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

anagrafiche_bp = Blueprint('anagrafiche', __name__)

# Marche iniziali di default
MARCHE_DEFAULT = ['HISENSE', 'HOMA', 'MIDEA']

# ============================================================================
# FUNZIONI HELPER PER ELABORAZIONE
# ============================================================================

def normalize_code(code):
    """
    Normalizza un codice rimuovendo spazi, punteggiatura e convertendo in minuscolo
    Per confronti e matching robusti
    """
    if not code:
        return ''
    return re.sub(r'[^a-z0-9]', '', str(code).lower())


def genera_tsv_simulato(anagrafica_id, marca):
    """
    Genera un file TSV simulato per testing della pipeline anagrafiche.
    Usa modelli ESISTENTI dalla tabella modelli (generati dalla pipeline ordini).

    Campi TSV:
    - file
    - anno
    - modello (cod_modello)
    - M&C code (cod_componente)
    - modello fabbrica (cod_modello_fabbrica)
    - qtà
    - pos number
    - part no
    - alt code
    - alt code 2
    - ean code
    - barcode
    - part name
    - chinese name
    - descr ita
    - unit price usd
    - prezzo EURO al CAT NO trasporto - NO iva - NETTO
    - prezzo EURO al CAT con trasporto - NO iva - NETTO
    - prezzo EURO al PUBBLICO (suggerito) con IVA
    - stat
    - softech stat

    Returns: filepath del TSV generato
    """
    base_dir = current_app.root_path
    parsed_dir = os.path.join(base_dir, 'INPUT', 'anagrafiche_parsed')
    os.makedirs(parsed_dir, exist_ok=True)

    # Prendi modelli esistenti dalla marca specificata (o tutti se marca non specificata)
    query = db.session.query(Modello)
    if marca:
        query = query.filter_by(marca=marca)

    modelli_esistenti = query.limit(10).all()  # Max 10 modelli per file simulato

    if not modelli_esistenti:
        # Se non ci sono modelli per quella marca, prendi modelli random
        modelli_esistenti = db.session.query(Modello).limit(10).all()

    # Genera dati simulati
    rows = []
    for modello in modelli_esistenti:
        # Ogni modello ha 3-8 componenti
        num_componenti = random.randint(3, 8)
        for i in range(num_componenti):
            row = {
                'file': f'anagrafica_{marca}_{anagrafica_id}.xlsx',
                'anno': datetime.now().year,
                'modello': modello.cod_modello,
                'M&C code': f'COMP-{marca}-{random.randint(1000, 9999)}',
                'modello fabbrica': f'FAB-{modello.cod_modello[:10]}-{random.randint(100, 999)}',
                'qtà': random.randint(1, 5),
                'pos number': f'POS-{random.randint(1, 100)}',
                'part no': f'PN-{random.randint(10000, 99999)}',
                'alt code': f'ALT-{random.randint(1000, 9999)}' if random.random() > 0.3 else '',
                'alt code 2': f'ALT2-{random.randint(1000, 9999)}' if random.random() > 0.5 else '',
                'ean code': f'{random.randint(1000000000000, 9999999999999)}',
                'barcode': f'BC{random.randint(100000, 999999)}',
                'part name': f'Component {i+1} for {modello.cod_modello}',
                'chinese name': f'组件 {i+1}',
                'descr ita': f'Componente {i+1} per modello {modello.cod_modello}',
                'unit price usd': round(random.uniform(5.0, 150.0), 2),
                'prezzo EURO al CAT NO trasporto - NO iva - NETTO': round(random.uniform(4.5, 135.0), 2),
                'prezzo EURO al CAT con trasporto - NO iva - NETTO': round(random.uniform(5.0, 140.0), 2),
                'prezzo EURO al PUBBLICO (suggerito) con IVA': round(random.uniform(6.0, 180.0), 2),
                'stat': random.choice(['A', 'B', 'C', 'D', '']),
                'softech stat': random.choice(['ACTIVE', 'OBSOLETE', 'DISCONTINUED', ''])
            }
            rows.append(row)

    # Scrivi TSV
    tsv_filename = f'anagrafica_{marca}_{anagrafica_id}_parsed.tsv'
    tsv_path = os.path.join(parsed_dir, tsv_filename)

    if rows:
        with open(tsv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"[TSV SIMULATO] Generato: {tsv_path} ({len(rows)} righe)")
    else:
        logger.warning(f"[TSV SIMULATO] Nessun dato generato per anagrafica {anagrafica_id}")

    return tsv_path if rows else None

def get_marche_disponibili():
    """
    Restituisce la lista di tutte le marche disponibili
    Scansiona le cartelle INPUT/anagrafiche/ e OUTPUT/anagrafiche/
    """
    base_dir = current_app.root_path   # <<< più affidabile di risalire da __file__
    input_dir = os.path.join(base_dir, 'INPUT', 'anagrafiche')
    output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche')

    marche = set()

    def _accumula_cartelle(root):
        if os.path.exists(root):
            for entry in os.listdir(root):
                try:
                    p = os.path.join(root, entry)
                    # Prendi SOLO directory, evita file/shortcut/ecc.
                    if os.path.isdir(p):
                        name = str(entry).strip()  # forza a str
                        if name:
                            marche.add(name)
                except Exception:
                    # Ignora qualunque voce "strana"
                    continue

    _accumula_cartelle(input_dir)
    _accumula_cartelle(output_dir)

    # Se non c'è nulla, usa le marche di default
    if not marche:
        marche = set(MARCHE_DEFAULT)

    # Ordina in modo deterministico e "case-insensitive"
    return sorted(marche, key=lambda s: s.lower())


def crea_cartelle_marca(marca):
    """
    Crea le cartelle INPUT/anagrafiche/{marca}/ e OUTPUT/anagrafiche/{marca}/
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    input_dir = os.path.join(base_dir, 'INPUT', 'anagrafiche', marca)
    output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', marca)
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    return input_dir


def get_filepath_by_status(marca, filename, esito):
    """
    Restituisce il path completo del file in base allo stato
    - Da processare / Errore: INPUT/anagrafiche/{marca}/
    - Processato: OUTPUT/anagrafiche/{marca}/
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    if esito == 'Processato':
        folder = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', marca)
    else:
        folder = os.path.join(base_dir, 'INPUT', 'anagrafiche', marca)
    
    return os.path.join(folder, filename)


def scan_anagrafiche_folder():
    """
    Scansiona le cartelle INPUT/anagrafiche/ e OUTPUT/anagrafiche/
    e sincronizza con il database
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    input_base = os.path.join(base_dir, 'INPUT', 'anagrafiche')
    output_base = os.path.join(base_dir, 'OUTPUT', 'anagrafiche')
    
    # Crea cartelle base se non esistono
    os.makedirs(input_base, exist_ok=True)
    os.makedirs(output_base, exist_ok=True)
    
    files_trovati = set()  # Set di tutti i filepath trovati
    
    # Scansiona INPUT
    if os.path.exists(input_base):
        for marca in os.listdir(input_base):
            marca_path = os.path.join(input_base, marca)
            
            if not os.path.isdir(marca_path):
                continue
            
            for filename in os.listdir(marca_path):
                if not filename.lower().endswith(('.xls', '.xlsx')):
                    continue
                
                filepath = os.path.join(marca_path, filename)
                files_trovati.add(filepath)
                
                # Controlla se già  nel DB
                # Controlla se già nel DB (per filepath O filename)
                existing = FileAnagrafica.query.filter(
                    (FileAnagrafica.filepath == filepath) | (FileAnagrafica.filename == filename)
                ).first()

                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = FileAnagrafica(
                        anno=date.today().year,
                        marca=marca,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=date.today(),
                        esito='Da processare'
                    )
                    db.session.add(nuova_anagrafica)
                    logger.info(f"[SYNC INPUT] Aggiunto: {filepath}")
                else:
                    logger.info(f"[SYNC INPUT] Saltato (già presente): {filename}")
    
    # Scansiona OUTPUT
    if os.path.exists(output_base):
        for marca in os.listdir(output_base):
            marca_path = os.path.join(output_base, marca)
            
            if not os.path.isdir(marca_path):
                continue
            
            for filename in os.listdir(marca_path):
                if not filename.lower().endswith(('.xls', '.xlsx')):
                    continue
                
                filepath = os.path.join(marca_path, filename)
                files_trovati.add(filepath)
                
                # Controlla se già  nel DB
                # Controlla se già nel DB (per filepath O filename)
                existing = FileAnagrafica.query.filter(
                    (FileAnagrafica.filepath == filepath) | (FileAnagrafica.filename == filename)
                ).first()

                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = FileAnagrafica(
                        anno=date.today().year,
                        marca=marca,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=date.today(),
                        esito='Processato',
                        data_elaborazione=date.today()
                    )
                    db.session.add(nuova_anagrafica)
                    logger.info(f"[SYNC OUTPUT] Aggiunto: {filepath}")
                else:
                    logger.info(f"[SYNC OUTPUT] Saltato (già presente): {filename}")
    
    # Rimuovi record orfani
    num_rimossi = 0
    tutte_anagrafiche = FileAnagrafica.query.all()
    for anagrafica in tutte_anagrafiche:
        if anagrafica.filepath not in files_trovati:
            logger.info(f"[SYNC] Rimosso record orfano: {anagrafica.filepath}")
            db.session.delete(anagrafica)
            num_rimossi += 1

    # Commit con gestione errori
    try:
        db.session.commit()
        logger.info(f"[SYNC] Completata: {len(files_trovati)} file, {num_rimossi} orfani rimossi")
    except Exception as e:
        db.session.rollback()
        logger.error(f"[SYNC] Errore durante commit: {str(e)}")
        raise


def elabora_anagrafica(anagrafica_id):
    """
    Elabora un file di anagrafica con tracciamento dettagliato

    Logica simulata:
    - 70% probabilità di successo →  sposta in OUTPUT, stato Processato
    - 30% probabilità di errore →  lascia in INPUT, stato Errore

    TODO: Sostituire con logica reale di elaborazione
    """
    anagrafica = FileAnagrafica.query.get_or_404(anagrafica_id)

    # ✅ STEP 1: Genera nuovo id_elab
    result = db.session.execute(db.text("SELECT nextval('seq_id_elab')"))
    id_elab = result.scalar()

    # ✅ STEP 2: Crea record elaborazione START (LOG SESSION)
    ts_inizio = datetime.utcnow()
    trace_start = TraceElab(
        id_elab=id_elab,
        id_file=anagrafica_id,
        tipo_file='ANA',
        step='START',
        stato='OK',
        messaggio='Inizio elaborazione anagrafica'
    )
    log_session.add(trace_start)
    log_session.commit()  # ← AUTONOMOUS: Commit immediato

    # Verifica che il file esista
    if not os.path.exists(anagrafica.filepath):
        # Crea trace END con errore
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=anagrafica_id,
            tipo_file='ANA',
            step='END',
            stato='KO',
            messaggio='File non trovato sul filesystem',
            righe_totali=0,
            righe_ok=0,
            righe_errore=1,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS: Log END persistito

        # Aggiorna tabella operativa (DB SESSION)
        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = '❌ File non trovato sul filesystem'
        anagrafica.updated_at = datetime.utcnow()
        anagrafica.updated_by = current_user.id
        db.session.commit()
        return False, 'File non trovato sul filesystem'
    
    # ✅ STEP 3: Genera TSV simulato (in futuro: lettura da Excel reale)
    try:
        tsv_path = genera_tsv_simulato(anagrafica_id, anagrafica.marca)
        if not tsv_path:
            raise Exception("Impossibile generare TSV simulato: nessun modello disponibile")
    except Exception as e:
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=anagrafica_id,
            tipo_file='ANA',
            step='END',
            stato='KO',
            messaggio=f'Errore generazione TSV: {str(e)}',
            righe_totali=0,
            righe_ok=0,
            righe_errore=1,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()

        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = f'❌ Errore generazione TSV: {str(e)}'
        anagrafica.updated_at = datetime.utcnow()
        anagrafica.updated_by = current_user.id
        db.session.commit()
        return False, f'Errore generazione TSV: {str(e)}'

    # ✅ STEP 4: Leggi TSV ed elabora dati
    try:
        righe_totali = 0
        righe_ok = 0
        righe_errore = 0
        righe_warning = 0

        modelli_aggiornati = set()
        componenti_creati = set()
        componenti_aggiornati = set()
        relazioni_create = set()

        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            for idx, row in enumerate(reader, start=1):
                righe_totali += 1

                # Crea SAVEPOINT per questa riga (permette rollback parziale)
                savepoint = db.session.begin_nested()

                try:
                    # Estrai dati dalla riga
                    cod_modello = row.get('modello', '').strip()
                    cod_componente = row.get('M&C code', '').strip()
                    cod_modello_fabbrica = row.get('modello fabbrica', '').strip()
                    qta = int(row.get('qtà', 1))

                    if not cod_modello or not cod_componente:
                        savepoint.rollback()
                        righe_warning += 1
                        trace_dett = TraceElabDett(
                            id_trace=trace_start.id_trace,
                            record_pos=idx,
                            record_data={'modello': cod_modello, 'componente': cod_componente},
                            stato='WARN',
                            messaggio='Modello o componente mancante'
                        )
                        log_session.add(trace_dett)
                        continue

                    # UPDATE modello (cod_modello_fabbrica)
                    modello = Modello.query.filter_by(cod_modello=cod_modello).first()
                    if modello:
                        if cod_modello_fabbrica:
                            modello.cod_modello_fabbrica = cod_modello_fabbrica
                            modello.updated_at = datetime.utcnow()
                            modello.updated_by = current_user.id
                            modello.updated_from = 'ANA'
                            modelli_aggiornati.add(cod_modello)

                            # Trace UPDATE modello
                            trace_dett = TraceElabDett(
                                id_trace=trace_start.id_trace,
                                record_pos=idx,
                                record_data={
                                    'tipo': 'UPDATE_MODELLO',
                                    'cod_modello': cod_modello,
                                    'cod_modello_fabbrica': cod_modello_fabbrica
                                },
                                stato='OK',
                                messaggio=f'Aggiornato modello {cod_modello} con cod_modello_fabbrica'
                            )
                            log_session.add(trace_dett)
                    else:
                        righe_warning += 1
                        trace_dett = TraceElabDett(
                            id_trace=trace_start.id_trace,
                            record_pos=idx,
                            record_data={'modello': cod_modello},
                            stato='WARN',
                            messaggio=f'Modello {cod_modello} non trovato nel DB'
                        )
                        log_session.add(trace_dett)

                    # CREATE/UPDATE componente
                    cod_componente_norm = normalize_code(cod_componente)
                    componente = Componente.query.filter_by(cod_componente_norm=cod_componente_norm).first()

                    if componente:
                        # UPDATE
                        componente.cod_alt = row.get('alt code', '').strip() or componente.cod_alt
                        componente.cod_alt_2 = row.get('alt code 2', '').strip() or componente.cod_alt_2
                        componente.pos_no = row.get('pos number', '').strip() or componente.pos_no
                        componente.part_no = row.get('part no', '').strip() or componente.part_no
                        componente.part_name_en = row.get('part name', '').strip() or componente.part_name_en
                        componente.part_name_cn = row.get('chinese name', '').strip() or componente.part_name_cn
                        componente.part_name_it = row.get('descr ita', '').strip() or componente.part_name_it
                        componente.cod_ean = row.get('ean code', '').strip() or componente.cod_ean
                        componente.barcode = row.get('barcode', '').strip() or componente.barcode

                        # Prezzi (se presenti)
                        try:
                            if row.get('unit price usd'):
                                componente.unit_price_usd = float(row['unit price usd'])
                            if row.get('prezzo EURO al CAT NO trasporto - NO iva - NETTO'):
                                componente.unit_price_notra_noiva_netto_eur = float(row['prezzo EURO al CAT NO trasporto - NO iva - NETTO'])
                            if row.get('prezzo EURO al CAT con trasporto - NO iva - NETTO'):
                                componente.unit_price_tra_noiva_netto_eur = float(row['prezzo EURO al CAT con trasporto - NO iva - NETTO'])
                            if row.get('prezzo EURO al PUBBLICO (suggerito) con IVA'):
                                componente.unit_price_public_eur = float(row['prezzo EURO al PUBBLICO (suggerito) con IVA'])
                        except ValueError:
                            pass  # Ignora errori di conversione prezzi

                        componente.stat = row.get('stat', '').strip() or componente.stat
                        componente.softech_stat = row.get('softech stat', '').strip() or componente.softech_stat
                        componente.updated_at = datetime.utcnow()
                        componente.updated_by = current_user.id
                        componenti_aggiornati.add(cod_componente)

                        # Trace UPDATE componente
                        trace_dett = TraceElabDett(
                            id_trace=trace_start.id_trace,
                            record_pos=idx,
                            record_data={
                                'tipo': 'UPDATE_COMPONENTE',
                                'cod_componente': cod_componente,
                                'part_name': row.get('part name', '')[:50]
                            },
                            stato='OK',
                            messaggio=f'Aggiornato componente {cod_componente}'
                        )
                        log_session.add(trace_dett)
                    else:
                        # CREATE
                        try:
                            componente = Componente(
                                cod_componente=cod_componente,
                                cod_componente_norm=cod_componente_norm,
                                cod_alt=row.get('alt code', '').strip(),
                                cod_alt_2=row.get('alt code 2', '').strip(),
                                pos_no=row.get('pos number', '').strip(),
                                part_no=row.get('part no', '').strip(),
                                part_name_en=row.get('part name', '').strip(),
                                part_name_cn=row.get('chinese name', '').strip(),
                                part_name_it=row.get('descr ita', '').strip(),
                                cod_ean=row.get('ean code', '').strip(),
                                barcode=row.get('barcode', '').strip(),
                                stat=row.get('stat', '').strip(),
                                softech_stat=row.get('softech stat', '').strip(),
                                created_by=current_user.id
                            )

                            # Prezzi
                            try:
                                if row.get('unit price usd'):
                                    componente.unit_price_usd = float(row['unit price usd'])
                                if row.get('prezzo EURO al CAT NO trasporto - NO iva - NETTO'):
                                    componente.unit_price_notra_noiva_netto_eur = float(row['prezzo EURO al CAT NO trasporto - NO iva - NETTO'])
                                if row.get('prezzo EURO al CAT con trasporto - NO iva - NETTO'):
                                    componente.unit_price_tra_noiva_netto_eur = float(row['prezzo EURO al CAT con trasporto - NO iva - NETTO'])
                                if row.get('prezzo EURO al PUBBLICO (suggerito) con IVA'):
                                    componente.unit_price_public_eur = float(row['prezzo EURO al PUBBLICO (suggerito) con IVA'])
                            except ValueError:
                                pass

                            db.session.add(componente)
                            componenti_creati.add(cod_componente)

                            # Trace CREATE componente
                            trace_dett = TraceElabDett(
                                id_trace=trace_start.id_trace,
                                record_pos=idx,
                                record_data={
                                    'tipo': 'CREATE_COMPONENTE',
                                    'cod_componente': cod_componente,
                                    'part_name': row.get('part name', '')[:50]
                                },
                                stato='OK',
                                messaggio=f'Creato nuovo componente {cod_componente}'
                            )
                            log_session.add(trace_dett)
                        except Exception as e:
                            righe_errore += 1
                            trace_dett = TraceElabDett(
                                id_trace=trace_start.id_trace,
                                record_pos=idx,
                                record_data={'componente': cod_componente},
                                stato='KO',
                                messaggio=f'Errore creazione componente: {str(e)}'
                            )
                            log_session.add(trace_dett)
                            continue

                    # CREATE modello_componente (relazione)
                    if modello and componente:
                        cod_modello_componente = f"{cod_modello}|{cod_componente}"

                        # Verifica se esiste già
                        existing_rel = ModelloComponente.query.filter_by(
                            cod_modello_componente=cod_modello_componente
                        ).first()

                        if not existing_rel:
                            relazione = ModelloComponente(
                                cod_modello_componente=cod_modello_componente,
                                id_file_anagrafiche=anagrafica_id,
                                cod_modello=cod_modello,
                                cod_componente=cod_componente,
                                qta=qta,
                                created_by=current_user.id
                            )
                            db.session.add(relazione)
                            relazioni_create.add(cod_modello_componente)

                            # Trace CREATE relazione modello-componente
                            trace_dett = TraceElabDett(
                                id_trace=trace_start.id_trace,
                                record_pos=idx,
                                record_data={
                                    'tipo': 'CREATE_RELAZIONE',
                                    'cod_modello': cod_modello,
                                    'cod_componente': cod_componente,
                                    'qta': qta
                                },
                                stato='OK',
                                messaggio=f'Creata relazione {cod_modello}|{cod_componente} (qtà: {qta})'
                            )
                            log_session.add(trace_dett)

                    righe_ok += 1

                    # Commit del savepoint (conferma operazioni per questa riga)
                    savepoint.commit()

                except Exception as e:
                    # Rollback del savepoint (annulla operazioni per questa riga ma continua con le altre)
                    savepoint.rollback()
                    righe_errore += 1
                    trace_dett = TraceElabDett(
                        id_trace=trace_start.id_trace,
                        record_pos=idx,
                        record_data={'row': str(row)[:100]},
                        stato='KO',
                        messaggio=f'Errore elaborazione riga: {str(e)}'
                    )
                    log_session.add(trace_dett)
                    logger.error(f"[ELAB ANA] Errore riga {idx}: {str(e)}")

        # ALL OR NOTHING: committa dati business SOLO se nessun errore
        # Se ci sono errori, verrà fatto rollback più avanti
        logger.info(f"[ELAB ANA] Fine elaborazione righe: {righe_ok} OK, {righe_errore} errori, {righe_warning} warning")

    except Exception as e:
        db.session.rollback()
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=anagrafica_id,
            tipo_file='ANA',
            step='END',
            stato='KO',
            messaggio=f'Errore elaborazione TSV: {str(e)}',
            righe_totali=righe_totali,
            righe_ok=righe_ok,
            righe_errore=righe_errore + 1,
            righe_warning=righe_warning
        )
        log_session.add(trace_end)
        log_session.commit()

        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = f'❌ Errore elaborazione: {str(e)}'
        anagrafica.updated_at = datetime.utcnow()
        anagrafica.updated_by = current_user.id
        db.session.commit()
        return False, f'Errore elaborazione: {str(e)}'

    # ✅ STEP 5: Se tutto OK, committa e sposta file in OUTPUT
    if righe_errore == 0:
        # ELABORAZIONE RIUSCITA - Commit dati business
        db.session.commit()
        logger.info(f"[ELAB ANA] Dati committati: {len(modelli_aggiornati)} modelli aggiornati, "
                   f"{len(componenti_creati)} componenti creati, {len(componenti_aggiornati)} componenti aggiornati, "
                   f"{len(relazioni_create)} relazioni create")

        # Path di destinazione OUTPUT
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', anagrafica.marca)
        os.makedirs(output_dir, exist_ok=True)
        
        new_filepath = os.path.join(output_dir, anagrafica.filename)
        
        try:
            # Sposta file da INPUT a OUTPUT
            shutil.move(anagrafica.filepath, new_filepath)

            # Commit warning log già creati durante elaborazione
            if righe_warning > 0:
                log_session.commit()  # ← AUTONOMOUS: Warning log persistiti

            # Crea trace END con successo (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=anagrafica_id,
                tipo_file='ANA',
                step='END',
                stato='WARN' if righe_warning > 0 else 'OK',
                messaggio=f'Elaborazione completata. Modelli aggiornati: {len(modelli_aggiornati)}, '
                         f'Componenti creati: {len(componenti_creati)}, '
                         f'Componenti aggiornati: {len(componenti_aggiornati)}, '
                         f'Relazioni create: {len(relazioni_create)}',
                righe_totali=righe_totali,
                righe_ok=righe_ok,
                righe_errore=righe_errore,
                righe_warning=righe_warning
            )
            log_session.add(trace_end)
            log_session.commit()  # ← AUTONOMOUS: Log END persistito

            # Aggiorna tabella operativa (DB SESSION - TRANSAZIONALE)
            anagrafica.filepath = new_filepath
            anagrafica.esito = 'Processato'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'✅ Elaborazione completata con successo.\n' \
                            f'Righe elaborate: {righe_totali}\n' \
                            f'Modelli aggiornati: {len(modelli_aggiornati)}\n' \
                            f'Componenti creati: {len(componenti_creati)}\n' \
                            f'Componenti aggiornati: {len(componenti_aggiornati)}\n' \
                            f'Relazioni create: {len(relazioni_create)}'
            anagrafica.updated_at = datetime.utcnow()
            anagrafica.updated_by = current_user.id
            db.session.commit()  # ← Se fallisce, i log sono GIÀ salvati!

            return True, 'Elaborazione completata con successo!'

        except Exception as e:
            # Errore durante lo spostamento (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=anagrafica_id,
                tipo_file='ANA',
                step='END',
                stato='KO',
                messaggio=f'Errore spostamento file: {str(e)}',
                righe_totali=0,
                righe_ok=0,
                righe_errore=1,
                righe_warning=0
            )
            log_session.add(trace_end)
            log_session.commit()  # ← AUTONOMOUS: Log END persistito

            # Aggiorna tabella operativa (DB SESSION)
            anagrafica.esito = 'Errore'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'Errore durante lo spostamento file: {str(e)}'
            anagrafica.updated_at = datetime.utcnow()
            anagrafica.updated_by = current_user.id
            db.session.commit()
            return False, f'Errore durante lo spostamento: {str(e)}'
    
    else:
        # ELABORAZIONE CON ERRORI - Rollback completo (ALL OR NOTHING)
        db.session.rollback()
        logger.warning(f"[ELAB ANA] Rollback dati business: {righe_errore} righe con errori")

        # Commit error/warning log già creati durante elaborazione
        log_session.commit()  # ← AUTONOMOUS: Error log persistiti

        # Crea trace END con errore (LOG SESSION)
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=anagrafica_id,
            tipo_file='ANA',
            step='END',
            stato='KO',
            messaggio=f'❌ Elaborazione fallita: {righe_errore} righe con errori su {righe_totali} totali (rollback completo)',
            righe_totali=righe_totali,
            righe_ok=0,  # ALL OR NOTHING: se ci sono errori, nessuna riga è stata committata
            righe_errore=righe_errore,
            righe_warning=righe_warning
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS: Log END persistito

        # Aggiorna tabella operativa (DB SESSION) - FILE RIMANE IN INPUT
        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = f'❌ Elaborazione fallita (rollback completo).\n' \
                        f'Righe totali: {righe_totali}\n' \
                        f'Righe con errori: {righe_errore}\n' \
                        f'Righe con warning: {righe_warning}\n' \
                        f'Nessun dato inserito/aggiornato (all or nothing).\n' \
                        f'File mantenuto in INPUT per revisione.'
        anagrafica.updated_at = datetime.utcnow()
        anagrafica.updated_by = current_user.id
        db.session.commit()

        return False, anagrafica.note



@anagrafiche_bp.route('/')
@login_required
def list():
    """Lista tutte le anagrafiche con paginazione, filtri e ordinamento"""
    # Sincronizza con filesystem
    scan_anagrafiche_folder()
    
    page = request.args.get('page', 1, type=int)
    marca_filter = request.args.get('marca', '')
    esito_filter = request.args.get('esito', '')
    anno_filter = request.args.get('anno', type=int)
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    
    query = FileAnagrafica.query
    
    # Filtri
    if marca_filter:
        query = query.filter_by(marca=marca_filter)
    if esito_filter:
        query = query.filter_by(esito=esito_filter)
    if anno_filter:
        query = query.filter_by(anno=anno_filter)
    if q:
        query = query.filter(FileAnagrafica.filename.ilike(f"%{q}%"))
    
    # Ordinamento dinamico
    sortable_columns = ['anno','marca','filename','data_acquisizione','data_elaborazione','esito','created_at','updated_at']
    if sort_by in sortable_columns and hasattr(FileAnagrafica, sort_by):
        column = getattr(FileAnagrafica, sort_by)
        if order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default: ordina per data creazione decrescente
        query = query.order_by(FileAnagrafica.created_at.desc())
    
    anagrafiche = query.paginate(page=page, per_page=20, error_out=False)
    
    # Liste per filtri
    marche_disponibili = get_marche_disponibili()
    anni_disponibili = [r[0] for r in db.session.query(FileAnagrafica.anno).distinct().order_by(FileAnagrafica.anno.desc())]
    
    return render_template('anagrafiche/list.html',
                         anagrafiche=anagrafiche,
                         marca_filter=marca_filter,
                         esito_filter=esito_filter,
                         anno_filter=anno_filter,
                         q=q,
                         marche_disponibili=marche_disponibili,
                         anni_disponibili=anni_disponibili,
                         sort_by=sort_by,
                         order=order)


@anagrafiche_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Upload nuovo file anagrafica"""
    form = AnagraficaFileForm()
    
    # Popola le scelte della select marca
    marche = get_marche_disponibili()
    form.marca.choices = [(m, m) for m in marche]
 
    # Inizializza data corrente al primo caricamento
    if request.method == 'GET':
        form.data_acquisizione.data = datetime.now().date()
        
    if form.validate_on_submit():
        file = form.file.data
        marca = form.marca.data
        anno = int(form.anno.data)
        
        # Verifica estensione
        if not file.filename.lower().endswith(('.xls', '.xlsx')):
            flash('Solo file Excel (.xls, .xlsx) sono permessi!', 'danger')
            return redirect(url_for('anagrafiche.create'))
        
        # Nome file sicuro
        filename = secure_filename(file.filename)
        
        # Crea cartelle marca se non esistono
        input_dir = crea_cartelle_marca(marca)
        
        filepath = os.path.join(input_dir, filename)
        
        # Verifica se file esiste già
        if os.path.exists(filepath):
            flash(f'Un file con nome {filename} esiste già per la marca {marca}!', 'warning')
            return redirect(url_for('anagrafiche.create'))
        
        # Salva il file
        file.save(filepath)
        
        # Crea record nel database
        anagrafica = FileAnagrafica(
            anno=anno,
            marca=marca,
            filename=filename,
            filepath=filepath,
            data_acquisizione=form.data_acquisizione.data,  # ← già date object
            esito='Da processare',
            note=form.note.data
        )
        
        db.session.add(anagrafica)
        db.session.commit()
        
        flash(f'File {filename} caricato con successo per la marca {marca}!', 'success')
        return redirect(url_for('anagrafiche.list'))
    
    return render_template('anagrafiche/create.html', form=form)


@anagrafiche_bp.route('/nuova-marca', methods=['GET', 'POST'])
@admin_required
def nuova_marca():
    """Crea una nuova marca"""
    form = NuovaMarcaForm()
    
    if form.validate_on_submit():
        nome_marca = form.nome_marca.data.strip().upper()
        
        # Verifica se esiste già
        marche_esistenti = get_marche_disponibili()
        if nome_marca in marche_esistenti:
            flash(f'La marca {nome_marca} esiste già!', 'warning')
            return redirect(url_for('anagrafiche.nuova_marca'))
        
        # Crea le cartelle
        crea_cartelle_marca(nome_marca)
        
        flash(f'Marca {nome_marca} creata con successo!', 'success')
        return redirect(url_for('anagrafiche.create'))
    
    return render_template('anagrafiche/nuova_marca.html', form=form)


@anagrafiche_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un'anagrafica esistente"""
    anagrafica = FileAnagrafica.query.get_or_404(id)
    form = AnagraficaFileEditForm(obj=anagrafica)  # ← WTForms popola automaticamente
    
    if form.validate_on_submit():
        anagrafica.anno = int(form.anno.data)
        anagrafica.data_acquisizione = form.data_acquisizione.data
        anagrafica.data_elaborazione = form.data_elaborazione.data
        anagrafica.esito = form.esito.data
        anagrafica.note = form.note.data
        anagrafica.updated_at = datetime.utcnow()
        anagrafica.updated_by = current_user.id

        db.session.commit()
        flash(f'Anagrafica {anagrafica.filename} aggiornata!', 'success')
        return redirect(url_for('anagrafiche.list'))
    
    return render_template('anagrafiche/edit.html', form=form, anagrafica=anagrafica)

@anagrafiche_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """Elabora un file di anagrafica"""
    success, message = elabora_anagrafica(id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    # Redirect alla pagina storico elaborazioni
    return redirect(url_for('anagrafiche.elaborazioni_list', id=id))


@anagrafiche_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """
    Elimina un'anagrafica.

    Cancella:
    - File_anagrafiche
    - Modelli_componenti associati (relazioni BOM)

    NON cancella:
    - Modelli (rimangono nel DB)
    - Componenti (rimangono nel DB)
    """
    anagrafica = FileAnagrafica.query.get_or_404(id)
    filename = anagrafica.filename
    filepath = anagrafica.filepath

    try:
        # ✅ STEP 1: Elimina modelli_componenti associati
        relazioni = ModelloComponente.query.filter_by(id_file_anagrafiche=id).all()
        num_relazioni = len(relazioni)

        for relazione in relazioni:
            db.session.delete(relazione)

        logger.info(f"[DELETE ANA] Eliminate {num_relazioni} relazioni modelli_componenti per anagrafica {id}")

        # ✅ STEP 2: Elimina file_anagrafiche dal database
        db.session.delete(anagrafica)
        db.session.commit()

        logger.info(f"[DELETE ANA] Eliminato file_anagrafiche {id}")

        # ✅ STEP 3: Elimina il file dal filesystem (se esiste)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"[DELETE ANA] Eliminato file fisico: {filepath}")
            except Exception as e:
                logger.warning(f"[DELETE ANA] Errore eliminazione file fisico: {str(e)}")
                flash(f'Anagrafica {filename} eliminata dal DB. Errore eliminazione file: {str(e)}', 'warning')
                return redirect(url_for('anagrafiche.list'))

        flash(f'✅ Anagrafica {filename} eliminata con successo. '
              f'({num_relazioni} relazioni modelli-componenti rimosse)', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"[DELETE ANA] Errore durante eliminazione: {str(e)}")
        flash(f'❌ Errore durante l\'eliminazione: {str(e)}', 'danger')

    return redirect(url_for('anagrafiche.list'))


@anagrafiche_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Download del file Excel"""
    anagrafica = FileAnagrafica.query.get_or_404(id)
    
    if not os.path.exists(anagrafica.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('anagrafiche.list'))
    
    directory = os.path.dirname(anagrafica.filepath)
    filename = os.path.basename(anagrafica.filepath)
    
    return send_from_directory(directory, filename, as_attachment=True)


@anagrafiche_bp.route('/view/<int:id>')
@login_required
def view(id):
    """Apri il file Excel nel browser (se possibile)"""
    anagrafica = FileAnagrafica.query.get_or_404(id)
    
    if not os.path.exists(anagrafica.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('anagrafiche.list'))
    
    directory = os.path.dirname(anagrafica.filepath)
    filename = os.path.basename(anagrafica.filepath)
    
    # Excel non si può aprire direttamente nel browser, quindi scarica
    return send_from_directory(directory, filename, as_attachment=False)


@anagrafiche_bp.route('/sync')
@admin_required
def sync():
    """
    Sincronizza manualmente il database con il filesystem.

    Comportamento:
    - Scansiona INPUT/anagrafiche/ e OUTPUT/anagrafiche/
    - Aggiunge file nuovi (saltando duplicati)
    - Rimuove record orfani (file eliminati dal filesystem)
    - Logga tutte le operazioni
    """
    try:
        scan_anagrafiche_folder()
        flash('Sincronizzazione completata! Controlla i log per i dettagli.', 'success')
    except Exception as e:
        logger.error(f"[SYNC] Errore sincronizzazione: {str(e)}")
        flash(f'Errore durante sincronizzazione: {str(e)}', 'danger')

    return redirect(url_for('anagrafiche.list'))


@anagrafiche_bp.route('/<int:id>/elaborazioni')
@login_required
def elaborazioni_list(id):
    """Lista storico elaborazioni raggruppate per id_elab"""
    file_ana = FileAnagrafica.query.get_or_404(id)

    # Recupera tutti i record END (contengono le metriche)
    elaborazioni_end = TraceElab.query.filter_by(
        tipo_file='ANA',
        id_file=id,
        step='END'
    ).order_by(TraceElab.created_at.desc()).all()

    # Per ogni END, trova il corrispondente START
    elaborazioni = []
    for elab_end in elaborazioni_end:
        elab_start = TraceElab.query.filter_by(
            id_elab=elab_end.id_elab,
            tipo_file='ANA',
            id_file=id,
            step='START'
        ).first()

        elaborazioni.append({
            'id_elab': elab_end.id_elab,
            'ts_inizio': elab_start.created_at if elab_start else elab_end.created_at,
            'ts_fine': elab_end.created_at,
            'esito': elab_end.stato,
            'messaggio': elab_end.messaggio,
            'righe_totali': elab_end.righe_totali,
            'righe_ok': elab_end.righe_ok,
            'righe_errore': elab_end.righe_errore,
            'righe_warning': elab_end.righe_warning
        })

    return render_template('anagrafiche/elaborazioni_list.html',
                         file_ana=file_ana,
                         elaborazioni=elaborazioni)


@anagrafiche_bp.route('/<int:id>/elaborazioni/<int:id_elab>/dettaglio')
@login_required
def elaborazione_dettaglio(id, id_elab):
    """Mostra i dettagli di una specifica elaborazione"""
    file_ana = FileAnagrafica.query.get_or_404(id)

    # Trova tutti i trace di questa elaborazione
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ANA',
        id_file=id
    ).order_by(TraceElab.created_at).all()

    if not traces:
        flash('Elaborazione non trovata', 'warning')
        return redirect(url_for('anagrafiche.elaborazioni_list', id=id))

    # Separa START e END
    trace_start = next((t for t in traces if t.step == 'START'), None)
    trace_end = next((t for t in traces if t.step == 'END'), None)

    # Recupera dettagli da trace_elab_dett
    page = request.args.get('page', 1, type=int)
    stato_filter = request.args.get('stato', '')

    id_traces = [t.id_trace for t in traces]
    query = TraceElabDett.query.filter(TraceElabDett.id_trace.in_(id_traces))

    if stato_filter:
        query = query.filter_by(stato=stato_filter)

    dettagli = query.order_by(TraceElabDett.record_pos).paginate(page=page, per_page=50, error_out=False)

    return render_template('anagrafiche/elaborazione_dettaglio_modal.html',
                         file_ana=file_ana,
                         trace_start=trace_start,
                         trace_end=trace_end,
                         dettagli=dettagli,
                         stato_filter=stato_filter)


@anagrafiche_bp.route('/<int:id>/elaborazioni/<int:id_elab>/export')
@login_required
def elaborazione_export(id, id_elab):
    """Esporta i dettagli di un'elaborazione in CSV"""
    import csv
    import io
    from flask import Response

    file_ana = FileAnagrafica.query.get_or_404(id)

    # Trova tutti i traces di questa elaborazione
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ANA',
        id_file=id
    ).all()

    if not traces:
        flash('Elaborazione non trovata', 'warning')
        return redirect(url_for('anagrafiche.elaborazioni_list', id=id))

    # Recupera tutti i dettagli
    id_traces = [t.id_trace for t in traces]
    dettagli = TraceElabDett.query.filter(
        TraceElabDett.id_trace.in_(id_traces)
    ).order_by(TraceElabDett.record_pos).all()

    # Crea CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Posizione', 'Stato', 'Codice', 'Messaggio', 'Campo'])

    # Righe
    for d in dettagli:
        campo = d.record_data.get('campo') if d.record_data else ''
        codice = d.record_data.get('key') if d.record_data else ''

        writer.writerow([
            d.record_pos or '',
            d.stato or '',
            codice or '',
            d.messaggio or '',
            campo or ''
        ])

    # Prepara risposta
    output.seek(0)
    trace_start = next((t for t in traces if t.step == 'START'), None)
    timestamp = trace_start.created_at.strftime('%Y%m%d_%H%M%S') if trace_start else datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"elaborazione_{file_ana.filename}_elab{id_elab}_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


#from flask import Markup
from markupsafe import Markup
import pandas as pd

@anagrafiche_bp.route('/preview/<int:id>')
@login_required
def preview(id):
    """Anteprima HTML del file Excel (prime righe del primo foglio)."""
    ana = FileAnagrafica.query.get_or_404(id)

    # Verifica path e stato/cartella
    filepath = ana.filepath
    if not os.path.isfile(filepath):
        flash("File non trovato sul filesystem.", "danger")
        return redirect(url_for('anagrafiche.list'))

    # Carica prime righe
    try:
        # Legge solo il primo foglio; in futuro puoi esporre un selettore dei fogli
        df = pd.read_excel(filepath, nrows=200)  # limite anti-memoria
        table_html = Markup(df.to_html(classes="table table-striped table-sm", index=False, border=0))
        error = None
    except Exception as e:
        table_html = None
        error = f"Impossibile generare anteprima: {e}"

    return render_template(
        'anagrafiche/preview.html',
        ana=ana,
        table_html=table_html,
        error=error
    )
