"""
Blueprint per la gestione Ordini di Acquisto (CRUD + Upload PDF + Elaborazione)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, FileOrdine, Ordine, TraceElab, TraceElabDett
from forms import FileOrdineForm, FileOrdineEditForm
from utils.decorators import admin_required
from utils.pdf_parser import parse_purchase_order_pdf
from utils.ordini_parser import genera_tsv_ordine_simulato, valida_riga_tsv
from routes.ordini_funzioni_elaborazione import elabora_tsv_ordine
from utils.db_log import log_session  # Sessione separata per log (AUTONOMOUS TRANSACTION)
import os
import re
import shutil
import random
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ordini_bp = Blueprint('ordini', __name__)

def preserve_list_params():
    """Preserva i parametri di filtro/ordinamento/paginazione della lista"""
    params = {}
    if request.args.get('anno'):
        params['anno'] = request.args.get('anno')
    if request.args.get('esito'):
        params['esito'] = request.args.get('esito')
    if request.args.get('filename'):
        params['filename'] = request.args.get('filename')
    if request.args.get('sort'):
        params['sort'] = request.args.get('sort')
    if request.args.get('order'):
        params['order'] = request.args.get('order')
    if request.args.get('page'):
        params['page'] = request.args.get('page')
    return params

def extract_year_from_filename(filename):
    """
    Estrae l'anno dal nome del file
    Esempi supportati:
    - PO_2024_001.pdf -> 2024
    - ordine_2023.pdf -> 2023
    - 2022_acquisto.pdf -> 2022
    """
    # Cerca un numero di 4 cifre che inizia con 20 (anni 2000-2099)
    match = re.search(r'(20\d{2})', filename)
    if match:
        return int(match.group(1))
    
    # Fallback: anno corrente
    return datetime.now().year

def get_upload_path(anno, esito='Da processare'):
    """
    Restituisce il path di upload per un determinato anno
    Struttura: 
    - INPUT/po/anno/ per Da processare ed Errore
    - OUTPUT/po/anno/ per Processato
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    if esito == 'Processato':
        upload_dir = os.path.join(base_dir, 'OUTPUT', 'po', str(anno))
    else:
        upload_dir = os.path.join(base_dir, 'INPUT', 'po', str(anno))
    
    # Crea la directory se non esiste
    os.makedirs(upload_dir, exist_ok=True)
    
    return upload_dir

def elabora_ordine(ordine_id):
    """
    Elabora un ordine di acquisto con flusso completo:

    PDF → TSV simulato → Inserimento DB (controparti, modelli, ordini)

    Processo:
    1. Verifica esistenza file PDF
    2. Genera TSV simulato (estrazione dati dal PDF)
    3. Elabora TSV e popola database (controparti, modelli, ordini)
    4. Sposta file PDF in OUTPUT se successo, lascia in INPUT se errore
    5. Trace completo con autonomous transaction

    Returns:
        tuple: (success: bool, message: str)
    """
    ordine = FileOrdine.query.get(ordine_id)
    if not ordine:
        return False, "Ordine non trovato"

    # ✅ STEP 0: Genera nuovo id_elab per questa elaborazione
    result = db.session.execute(db.text("SELECT nextval('seq_id_elab')"))
    id_elab = result.scalar()

    # ✅ STEP 1: Crea record elaborazione - START (LOG SESSION - COMMIT IMMEDIATO)
    trace_start = TraceElab(
        id_elab=id_elab,
        id_file=ordine_id,
        tipo_file='ORD',
        step='START',
        stato='OK',
        messaggio='Inizio elaborazione ordine PDF'
    )
    log_session.add(trace_start)
    log_session.commit()  # ← AUTONOMOUS: Commit immediato, sempre persistito
    id_trace_start = trace_start.id_trace

    try:
        # Verifica che il file esista
        if not os.path.exists(ordine.filepath):
            logger.error(f"File not found: {ordine.filepath}")

            # Logga errore critico (LOG SESSION)
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                record_data={'key': 'FILE_NOT_FOUND'},
                stato='KO',
                messaggio=f"File non trovato sul filesystem: {ordine.filepath}"
            )
            log_session.add(dettaglio)
            log_session.commit()

            # Finalizza elaborazione con errore (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio='File non trovato',
                righe_totali=0,
                righe_ok=0,
                righe_errore=1,
                righe_warning=0
            )
            log_session.add(trace_end)
            log_session.commit()

            # Aggiorna tabella operativa (DB SESSION)
            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = "File non trovato sul filesystem"
            ordine.updated_at = datetime.utcnow()
            ordine.updated_by = current_user.id
            db.session.commit()

            return False, "File non trovato sul filesystem"

        # ✅ STEP 2: Genera TSV simulato dal PDF
        logger.info(f"Generazione TSV da PDF: {ordine.filepath}")

        # Directory per TSV parsed
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        parsed_dir = os.path.join(base_dir, 'INPUT', 'ordini_parsed')
        os.makedirs(parsed_dir, exist_ok=True)

        try:
            tsv_filepath, num_righe_tsv, metadati = genera_tsv_ordine_simulato(ordine.filepath, parsed_dir)
            logger.info(f"TSV generato: {tsv_filepath} ({num_righe_tsv} righe)")

            # Log TSV generato (LOG SESSION)
            dettaglio_tsv = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                stato='OK',
                messaggio=f'TSV generato: {num_righe_tsv} righe',
                record_data={'key': 'TSV_GEN', 'tsv_file': os.path.basename(tsv_filepath)}
            )
            log_session.add(dettaglio_tsv)
            log_session.commit()

        except Exception as e:
            logger.exception(f"Errore generazione TSV: {e}")

            # Log errore (LOG SESSION)
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                stato='KO',
                messaggio=f"Errore generazione TSV: {str(e)}",
                record_data={'key': 'TSV_GEN_ERROR'}
            )
            log_session.add(dettaglio)
            log_session.commit()

            # Log END (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
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

            # Aggiorna tabella operativa (DB SESSION)
            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = f"Errore generazione TSV: {str(e)}"
            ordine.updated_at = datetime.utcnow()
            ordine.updated_by = current_user.id
            db.session.commit()

            return False, f"Errore generazione TSV: {str(e)}"

        # ✅ STEP 3: Elabora TSV e popola database (controparti, modelli, ordini)
        logger.info(f"Elaborazione TSV: {tsv_filepath}")
        success_tsv, message_tsv, stats = elabora_tsv_ordine(ordine_id, tsv_filepath, current_user.id)

        # Estrai statistiche
        num_righe_ok = stats.get('righe_ok', 0)
        num_errori = stats.get('errori', 0)
        num_warnings = stats.get('warnings', 0)

        # Log warning dettagliati (LOG SESSION)
        for warning in stats.get('warnings_dettaglio', [])[:10]:  # Max 10
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                stato='WARN',
                messaggio=warning,
                record_data={'key': 'TSV_WARN'}
            )
            log_session.add(dettaglio)
        if num_warnings > 0:
            log_session.commit()

        # Log errori dettagliati (LOG SESSION)
        for errore in stats.get('errori_dettaglio', [])[:10]:  # Max 10
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                stato='KO',
                messaggio=errore,
                record_data={'key': 'TSV_ERROR'}
            )
            log_session.add(dettaglio)
        if num_errori > 0:
            log_session.commit()

        # Verifica se elaborazione TSV è fallita
        if not success_tsv:
            # ✅ STEP 4A: ERRORE CRITICO - file rimane in INPUT
            messaggio_finale = f"Elaborazione TSV fallita: {message_tsv}"

            # Log END con errore (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio=messaggio_finale,
                righe_totali=num_righe_ok + num_errori,
                righe_ok=num_righe_ok,
                righe_errore=num_errori,
                righe_warning=num_warnings
            )
            log_session.add(trace_end)
            log_session.commit()

            # Aggiorna tabella operativa (DB SESSION)
            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = messaggio_finale
            ordine.updated_at = datetime.utcnow()
            ordine.updated_by = current_user.id
            db.session.commit()

            return False, messaggio_finale

        # ✅ STEP 4B: SUCCESSO - sposta file PDF in OUTPUT
        output_dir = get_upload_path(ordine.anno, esito='Processato')
        new_filepath = os.path.join(output_dir, ordine.filename)

        try:
            # Sposta il file PDF
            shutil.move(ordine.filepath, new_filepath)
            logger.info(f"Moved PDF to OUTPUT: {new_filepath}")

            # Messaggio finale con dettagli
            msg_parts = [f"Elaborati {num_righe_ok} righe ordine"]

            if metadati.get('num_modelli_unici'):
                msg_parts.append(f"{metadati['num_modelli_unici']} modelli unici")

            if metadati.get('po_number'):
                msg_parts.append(f"PO: {metadati['po_number']}")

            if num_warnings > 0:
                msg_parts.append(f"{num_warnings} warning")

            if num_errori > 0:
                msg_parts.append(f"{num_errori} righe con errori ignorate")

            messaggio_finale = ". ".join(msg_parts)

            # ✅ STEP 5A: Log END con successo (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='WARN' if num_warnings > 0 else 'OK',
                messaggio=messaggio_finale,
                righe_totali=num_righe_ok + num_errori,
                righe_ok=num_righe_ok,
                righe_errore=num_errori,
                righe_warning=num_warnings
            )
            log_session.add(trace_end)
            log_session.commit()

            # ✅ STEP 5B: Aggiorna tabella operativa (DB SESSION - TRANSAZIONALE)
            ordine.filepath = new_filepath
            ordine.esito = 'Processato'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = messaggio_finale
            ordine.updated_at = datetime.utcnow()
            ordine.updated_by = current_user.id
            db.session.commit()

            success_msg = f"Ordine elaborato con successo! {num_righe_ok} righe inserite"
            if num_warnings > 0:
                success_msg += f" ({num_warnings} warning)"

            return True, success_msg

        except Exception as e:
            # Errore nello spostamento file
            logger.exception(f"Error moving file: {str(e)}")

            # Log dettaglio errore (LOG SESSION)
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                stato='KO',
                messaggio=f"Errore spostamento file PDF: {str(e)}",
                record_data={'key': 'FILE_MOVE_ERROR'}
            )
            log_session.add(dettaglio)
            log_session.commit()

            # Log END con errore (LOG SESSION)
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio=f"TSV elaborato ma errore spostamento PDF: {str(e)}",
                righe_totali=num_righe_ok,
                righe_ok=num_righe_ok,
                righe_errore=1,
                righe_warning=num_warnings
            )
            log_session.add(trace_end)
            log_session.commit()

            # Aggiorna tabella operativa (DB SESSION)
            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = f"TSV elaborato ma errore: {str(e)}"
            ordine.updated_at = datetime.utcnow()
            ordine.updated_by = current_user.id
            db.session.commit()

            return False, f"Errore: {str(e)}"

    except Exception as e:
        # Gestione errori imprevisti
        logger.exception(f"Unexpected error during elaboration: {str(e)}")

        # Log dettaglio errore imprevisto (LOG SESSION)
        dettaglio = TraceElabDett(
            id_trace=id_trace_start,
            record_pos=0,
            stato='KO',
            messaggio=f"Errore imprevisto: {str(e)}",
            record_data={'key': 'UNEXPECTED_ERROR'}
        )
        log_session.add(dettaglio)
        log_session.commit()

        # Log END con errore imprevisto (LOG SESSION)
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=ordine_id,
            tipo_file='ORD',
            step='END',
            stato='KO',
            messaggio=f"Errore imprevisto: {str(e)}",
            righe_totali=0,
            righe_ok=0,
            righe_errore=1,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()

        # Aggiorna tabella operativa (DB SESSION)
        ordine.esito = 'Errore'
        ordine.data_elaborazione = datetime.utcnow()
        ordine.note = str(e)
        ordine.updated_at = datetime.utcnow()
        ordine.updated_by = current_user.id
        db.session.commit()

        return False, f"Errore imprevisto: {str(e)}"
def scan_po_folder():
    """
    Scansiona le cartelle INPUT/po/ e OUTPUT/po/ e sincronizza con il database
    - Aggiunge file nuovi che non sono nel DB
    - Rimuove record DB per file che non esistono più
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    files_trovati = set()  # Set di tutti i filepath trovati nel filesystem
    
    # Scansiona INPUT/po/
    input_base_dir = os.path.join(base_dir, 'INPUT', 'po')
    if os.path.exists(input_base_dir):
        for anno_folder in os.listdir(input_base_dir):
            anno_path = os.path.join(input_base_dir, anno_folder)
            
            if not os.path.isdir(anno_path) or not anno_folder.isdigit():
                continue
            
            anno = int(anno_folder)
            
            for filename in os.listdir(anno_path):
                if not filename.lower().endswith('.pdf'):
                    continue
                
                filepath = os.path.join(anno_path, filename)
                files_trovati.add(filepath)

                # Controlla se il file è già nel database (per filepath O filename)
                existing = FileOrdine.query.filter(
                    (FileOrdine.filepath == filepath) | (FileOrdine.filename == filename)
                ).first()

                if not existing:
                    # Aggiungi al database con stato Da processare
                    nuovo_ordine = FileOrdine(
                        anno=anno,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=datetime.now().date(),
                        esito='Da processare'
                    )
                    db.session.add(nuovo_ordine)
                    logger.info(f"[SYNC INPUT] Aggiunto: {filepath}")
                else:
                    logger.info(f"[SYNC INPUT] Saltato (già presente): {filename}")
    
    # Scansiona OUTPUT/po/
    output_base_dir = os.path.join(base_dir, 'OUTPUT', 'po')
    if os.path.exists(output_base_dir):
        for anno_folder in os.listdir(output_base_dir):
            anno_path = os.path.join(output_base_dir, anno_folder)
            
            if not os.path.isdir(anno_path) or not anno_folder.isdigit():
                continue
            
            anno = int(anno_folder)
            
            for filename in os.listdir(anno_path):
                if not filename.lower().endswith('.pdf'):
                    continue
                
                filepath = os.path.join(anno_path, filename)
                files_trovati.add(filepath)

                # Controlla se il file è già nel database (per filepath O filename)
                existing = FileOrdine.query.filter(
                    (FileOrdine.filepath == filepath) | (FileOrdine.filename == filename)
                ).first()

                if not existing:
                    # Aggiungi al database con stato Processato
                    nuovo_ordine = FileOrdine(
                        anno=anno,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=datetime.now().date(),
                        esito='Processato',
                        data_elaborazione=datetime.utcnow(),
                        note='File già processato, trovato in OUTPUT durante sincronizzazione'
                    )
                    db.session.add(nuovo_ordine)
                    logger.info(f"[SYNC OUTPUT] Aggiunto: {filepath}")
                else:
                    logger.info(f"[SYNC OUTPUT] Saltato (già presente): {filename}")
    
    # Rimuovi record orfani (file nel DB ma non nel filesystem)
    num_rimossi = 0
    tutti_ordini = FileOrdine.query.all()
    for ordine in tutti_ordini:
        if ordine.filepath not in files_trovati:
            logger.info(f"[SYNC] Rimosso record orfano: {ordine.filepath}")
            db.session.delete(ordine)
            num_rimossi += 1

    # Commit con gestione errori
    try:
        db.session.commit()
        logger.info(f"[SYNC] Completata: {len(files_trovati)} file, {num_rimossi} orfani rimossi")
    except Exception as e:
        db.session.rollback()
        logger.error(f"[SYNC] Errore durante commit: {str(e)}")
        raise

@ordini_bp.route('/')
@login_required
def list():
    """Lista tutti gli ordini di acquisto con paginazione, filtri e ordinamento"""
    # Sincronizza con il filesystem
    scan_po_folder()

    page = request.args.get('page', 1, type=int)
    anno_filter = request.args.get('anno', type=int)
    esito_filter = request.args.get('esito', '')
    filename_filter = request.args.get('filename', '').strip()
    sort_by = request.args.get('sort', 'anno')
    order = request.args.get('order', 'desc')

    # Conteggio totale prima dei filtri
    total_count = FileOrdine.query.count()

    query = FileOrdine.query

    # Filtri
    if anno_filter:
        query = query.filter_by(anno=anno_filter)
    if esito_filter:
        query = query.filter_by(esito=esito_filter)
    if filename_filter:
        query = query.filter(FileOrdine.filename.ilike(f'%{filename_filter}%'))

    # Conteggio dopo filtri
    filtered_count = query.count()

    # Ordinamento dinamico - validazione colonne permesse
    sortable_columns = ['anno', 'filename', 'data_acquisizione', 'data_elaborazione', 'esito', 'created_at']
    if sort_by in sortable_columns and hasattr(FileOrdine, sort_by):
        column = getattr(FileOrdine, sort_by)
        if order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default: ordina per anno decrescente e data creazione
        query = query.order_by(FileOrdine.anno.desc(), FileOrdine.created_at.desc())

    ordini = query.paginate(page=page, per_page=20, error_out=False)

    # Lista anni disponibili per filtro
    anni_disponibili = db.session.query(FileOrdine.anno).distinct().order_by(FileOrdine.anno.desc()).all()
    anni_disponibili = [a[0] for a in anni_disponibili]

    return render_template('ordini/list.html',
                         ordini=ordini,
                         anno_filter=anno_filter,
                         esito_filter=esito_filter,
                         filename_filter=filename_filter,
                         anni_disponibili=anni_disponibili,
                         sort_by=sort_by,
                         order=order,
                         total_count=total_count,
                         filtered_count=filtered_count)

@ordini_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Crea un nuovo ordine di acquisto (upload PDF)"""
    form = FileOrdineForm()
    
    # Inizializza data acquisizione con data corrente al primo caricamento
    if request.method == 'GET':
        form.data_acquisizione.data = datetime.now().date()
    
    if form.validate_on_submit():
        file = form.file.data
        
        # Verifica che sia un PDF
        if not file.filename.lower().endswith('.pdf'):
            flash('Solo file PDF sono permessi!', 'danger')
            return redirect(url_for('ordini.create'))
        
        # Salva il file con nome sicuro
        filename = secure_filename(file.filename)
        
        # Estrai anno dal nome file
        anno = extract_year_from_filename(filename)
        
        # Ottieni path di upload (sempre INPUT per nuovi file)
        upload_dir = get_upload_path(anno, esito='Da processare')
        filepath = os.path.join(upload_dir, filename)
        
        # Verifica se file esiste già
        if os.path.exists(filepath):
            flash(f'Un file con nome {filename} esiste già per l\'anno {anno}!', 'warning')
            return redirect(url_for('ordini.create'))
        
        # Salva il file
        file.save(filepath)
        
        # Crea record nel database
        ordine = FileOrdine(
            anno=anno,
            filename=filename,
            filepath=filepath,
            data_acquisizione=form.data_acquisizione.data,
            esito=form.esito.data,
            note=form.note.data
        )
        
        db.session.add(ordine)
        db.session.commit()
        
        flash(f'Ordine di acquisto {filename} caricato con successo! (Anno: {anno})', 'success')
        return redirect(url_for('ordini.list', **preserve_list_params()))
    
    return render_template('ordini/create.html', form=form)

@ordini_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un ordine di acquisto esistente"""
    ordine = FileOrdine.query.get_or_404(id)
    form = FileOrdineEditForm(obj=ordine)
    
    if form.validate_on_submit():
        ordine.data_acquisizione = form.data_acquisizione.data
        ordine.esito = form.esito.data
        ordine.note = form.note.data
        ordine.updated_at = datetime.utcnow()
        ordine.updated_by = current_user.id

        db.session.commit()
        flash(f'Ordine {ordine.filename} aggiornato!', 'success')
        return redirect(url_for('ordini.list', **preserve_list_params()))
    
    return render_template('ordini/edit.html', form=form, ordine=ordine)

@ordini_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """
    Elimina un ordine di acquisto.

    Comportamento:
    - Cancella righe ordini associate (tabella ordini)
    - Cancella record FileOrdine
    - Cancella file PDF dal filesystem
    - NON tocca modelli e controparti (dati master)
    - NON tocca trace_elab/trace_elab_dett (storico)
    - Logga operazione in console/file
    """
    ordine = FileOrdine.query.get_or_404(id)
    filename = ordine.filename
    filepath = ordine.filepath

    # ✅ STEP 1: Conta righe ordini da cancellare
    righe_ordini = Ordine.query.filter_by(id_file_ordine=id).all()
    num_righe = len(righe_ordini)

    logger.info(f"[DELETE] Inizio cancellazione FileOrdine ID={id}, file={filename}")
    logger.info(f"[DELETE] Righe ordini associate: {num_righe}")

    # ✅ STEP 2: Cancella righe ordini (NON tocca modelli/controparti)
    if num_righe > 0:
        for riga in righe_ordini:
            db.session.delete(riga)
        logger.info(f"[DELETE] Cancellate {num_righe} righe dalla tabella ordini")

    # ✅ STEP 3: Cancella file PDF dal filesystem
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"[DELETE] File PDF rimosso: {filepath}")
        except Exception as e:
            logger.error(f"[DELETE] Errore rimozione file PDF: {str(e)}")
            flash(f'Errore nell\'eliminazione del file: {str(e)}', 'danger')
            db.session.rollback()
            return redirect(url_for('ordini.list', **preserve_list_params()))
    else:
        logger.warning(f"[DELETE] File PDF non trovato: {filepath}")

    # ✅ STEP 4: Cancella record FileOrdine dal database
    db.session.delete(ordine)
    db.session.commit()

    logger.info(f"[DELETE] FileOrdine ID={id} cancellato con successo")
    logger.info(f"[DELETE] Riepilogo: {num_righe} righe ordini, 1 file_ordine, 1 PDF rimossi")
    logger.info(f"[DELETE] Modelli e controparti: NON toccati (dati master)")
    logger.info(f"[DELETE] Trace: NON toccate (storico elaborazioni)")

    flash(f'Ordine {filename} eliminato ({num_righe} righe ordini rimosse).', 'info')
    return redirect(url_for('ordini.list', **preserve_list_params()))

@ordini_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Download del file PDF"""
    ordine = FileOrdine.query.get_or_404(id)
    
    if not os.path.exists(ordine.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('ordini.list', **preserve_list_params()))
    
    directory = os.path.dirname(ordine.filepath)
    filename = os.path.basename(ordine.filepath)
    
    return send_from_directory(directory, filename, as_attachment=True)

@ordini_bp.route('/view/<int:id>')
@login_required
def view(id):
    """Visualizza il PDF nel browser"""
    ordine = FileOrdine.query.get_or_404(id)
    
    if not os.path.exists(ordine.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('ordini.list', **preserve_list_params()))
    
    directory = os.path.dirname(ordine.filepath)
    filename = os.path.basename(ordine.filepath)
    
    return send_from_directory(directory, filename, as_attachment=False)

@ordini_bp.route('/sync')
@admin_required
def sync():
    """
    Sincronizza manualmente il database con il filesystem.

    Comportamento:
    - Scansiona INPUT/po/ e OUTPUT/po/
    - Aggiunge file nuovi (saltando duplicati)
    - Rimuove record orfani (file eliminati dal filesystem)
    - Logga tutte le operazioni
    """
    try:
        scan_po_folder()
        flash('Sincronizzazione completata! Controlla i log per i dettagli.', 'success')
    except Exception as e:
        logger.error(f"[SYNC] Errore sincronizzazione: {str(e)}")
        flash(f'Errore durante sincronizzazione: {str(e)}', 'danger')

    return redirect(url_for('ordini.list', **preserve_list_params()))

@ordini_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """
    Elabora un ordine di acquisto (SINCRONO)
    Disponibile solo per ordini con stato 'Da processare' o 'Errore'
    """
    ordine = FileOrdine.query.get_or_404(id)
    
    # Verifica che l'ordine possa essere elaborato
    if ordine.esito not in ['Da processare', 'Errore']:
        flash(f'L\'ordine è già stato elaborato con successo e non può essere rielaborato.', 'warning')
        return redirect(url_for('ordini.list', **preserve_list_params()))
    
    # Elabora l'ordine (sincrono - attende il completamento)
    success, message = elabora_ordine(id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    # Redirect alla pagina storico elaborazioni per vedere immediatamente il risultato
    return redirect(url_for('ordini.elaborazioni_list', id=id))


# ========== NUOVI ENDPOINT PER TRACCIAMENTO ELABORAZIONI ==========

@ordini_bp.route('/<int:id>/elaborazioni')
@login_required
def elaborazioni_list(id):
    """
    LIVELLO 2: Lista di tutte le elaborazioni per un ordine specifico
    Raggruppa per id_elab e mostra metriche aggregate
    """
    ordine = FileOrdine.query.get_or_404(id)

    # Recupera tutti i record END (contengono le metriche aggregate)
    elaborazioni_end = TraceElab.query.filter_by(
        tipo_file='ORD',
        id_file=id,
        step='END'
    ).order_by(TraceElab.created_at.desc()).all()

    # Per ogni elaborazione END, trova il corrispondente START
    elaborazioni = []
    for elab_end in elaborazioni_end:
        elab_start = TraceElab.query.filter_by(
            id_elab=elab_end.id_elab,
            tipo_file='ORD',
            id_file=id,
            step='START'
        ).first()

        # Crea oggetto aggregato con tutte le info
        elaborazioni.append({
            'id_elab': elab_end.id_elab,
            'id_trace_start': elab_start.id_trace if elab_start else None,
            'id_trace_end': elab_end.id_trace,
            'ts_inizio': elab_start.created_at if elab_start else elab_end.created_at,
            'ts_fine': elab_end.created_at,
            'esito': elab_end.stato,  # 'OK', 'KO', 'WARN'
            'messaggio': elab_end.messaggio,
            'righe_totali': elab_end.righe_totali,
            'righe_ok': elab_end.righe_ok,
            'righe_errore': elab_end.righe_errore,
            'righe_warning': elab_end.righe_warning
        })

    return render_template('ordini/elaborazioni_list.html',
                         ordine=ordine,
                         elaborazioni=elaborazioni)


@ordini_bp.route('/<int:id>/elaborazioni/<int:id_elab>/dettaglio')
@login_required
def elaborazione_dettaglio(id, id_elab):
    """
    LIVELLO 3: Dettaglio completo di un'elaborazione specifica (mostra tutti i trace_elab_dett)
    """
    ordine = FileOrdine.query.get_or_404(id)

    # Trova tutti i record trace_elab per questo id_elab
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ORD',
        id_file=id
    ).order_by(TraceElab.created_at).all()

    if not traces:
        flash('Elaborazione non trovata', 'danger')
        return redirect(url_for('ordini.elaborazioni_list', id=id))

    # Estrai START e END
    trace_start = next((t for t in traces if t.step == 'START'), None)
    trace_end = next((t for t in traces if t.step == 'END'), None)

    # Recupera tutti i dettagli (anomalie) da tutti i trace
    page = request.args.get('page', 1, type=int)
    stato_filter = request.args.get('stato', '')

    # Trova tutti gli id_trace per questo id_elab
    id_traces = [t.id_trace for t in traces]
    query = TraceElabDett.query.filter(TraceElabDett.id_trace.in_(id_traces))

    if stato_filter:
        query = query.filter_by(stato=stato_filter)

    query = query.order_by(TraceElabDett.record_pos)
    dettagli = query.paginate(page=page, per_page=50, error_out=False)

    # Se richiesta AJAX, ritorna JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify

        durata_secondi = None
        if trace_start and trace_end:
            durata_secondi = int((trace_end.created_at - trace_start.created_at).total_seconds())

        return jsonify({
            'elaborazione': {
                'id_elab': id_elab,
                'ts_inizio': trace_start.created_at.isoformat() if trace_start else None,
                'ts_fine': trace_end.created_at.isoformat() if trace_end else None,
                'durata_secondi': durata_secondi,
                'esito': trace_end.stato if trace_end else 'IN_CORSO',
                'righe_totali': trace_end.righe_totali if trace_end else 0,
                'righe_ok': trace_end.righe_ok if trace_end else 0,
                'righe_errore': trace_end.righe_errore if trace_end else 0,
                'righe_warning': trace_end.righe_warning if trace_end else 0,
                'messaggio_globale': trace_end.messaggio if trace_end else (trace_start.messaggio if trace_start else '')
            },
            'dettagli': [{
                'id': d.id_trace_dett,
                'riga_numero': d.record_pos,
                'tipo_messaggio': d.stato,
                'codice_errore': d.record_data.get('key') if d.record_data else None,
                'messaggio': d.messaggio,
                'campo': d.record_data.get('campo') if d.record_data else None,
                'valore_originale': None
            } for d in dettagli.items],
            'pagination': {
                'page': dettagli.page,
                'pages': dettagli.pages,
                'total': dettagli.total,
                'has_next': dettagli.has_next,
                'has_prev': dettagli.has_prev
            }
        })

    # Altrimenti ritorna template HTML (per modal)
    return render_template('ordini/elaborazione_dettaglio_modal.html',
                         ordine=ordine,
                         trace_start=trace_start,
                         trace_end=trace_end,
                         dettagli=dettagli,
                         stato_filter=stato_filter)


@ordini_bp.route('/<int:id>/elaborazioni/<int:id_elab>/export')
@login_required
def elaborazione_export(id, id_elab):
    """
    Export CSV dei dettagli di un'elaborazione
    """
    from flask import Response
    import csv
    from io import StringIO

    ordine = FileOrdine.query.get_or_404(id)

    # Trova tutti i record trace_elab per questo id_elab
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ORD',
        id_file=id
    ).all()

    if not traces:
        flash('Elaborazione non trovata per questo ordine', 'danger')
        return redirect(url_for('ordini.elaborazioni_list', id=id))

    # Recupera tutti i dettagli da tutti i trace
    id_traces = [t.id_trace for t in traces]
    dettagli = TraceElabDett.query.filter(
        TraceElabDett.id_trace.in_(id_traces)
    ).order_by(TraceElabDett.record_pos).all()

    # Crea CSV in memoria
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow([
        'Riga',
        'Tipo',
        'Codice',
        'Messaggio',
        'Campo'
    ])

    # Dati
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

    # Ritorna come download
    output = si.getvalue()
    si.close()

    # Usa timestamp dal trace_start se disponibile
    trace_start = next((t for t in traces if t.step == 'START'), None)
    timestamp = trace_start.created_at.strftime('%Y%m%d_%H%M%S') if trace_start else datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"elaborazione_{ordine.filename}_elab{id_elab}_{timestamp}.csv"

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )