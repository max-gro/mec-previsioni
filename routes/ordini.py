"""
Blueprint per la gestione Ordini di Acquisto (CRUD + Upload PDF + Elaborazione)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, OrdineAcquisto, FileOrdini
from forms import OrdineAcquistoForm, OrdineAcquistoEditForm
from utils.decorators import admin_required
from services.ordini_parser import leggi_ordine_excel_to_tsv
from services.ordini_db_inserter import inserisci_ordine_da_tsv
from services.file_manager import completa_elaborazione_ordine, gestisci_errore_elaborazione
import os
import re
import shutil
import random
from datetime import datetime

ordini_bp = Blueprint('ordini', __name__)

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
    Elabora un ordine di acquisto tramite pipeline completa:
    1. Leggi Excel → TSV (OUTPUT_ELAB)
    2. Inserisci DB (transazione atomica)
    3. Se OK → sposta INPUT→OUTPUT, esito='Elaborato'
       Se KO → esito='Errore', nota errore

    Returns:
        tuple: (success: bool, message: str, stats: dict)
    """
    file_ordine = FileOrdini.query.get(ordine_id)
    if not file_ordine:
        return False, "Ordine non trovato", {}

    # Verifica che il file esista
    if not os.path.exists(file_ordine.filepath):
        gestisci_errore_elaborazione(ordine_id, f"File non trovato: {file_ordine.filepath}", 'verifica_file')
        return False, "File non trovato sul filesystem", {}

    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    output_elab_dir = os.path.join(base_dir, 'OUTPUT_ELAB', 'po')

    try:
        # Step 1: Parsing Excel → TSV
        success, tsv_path, error, parse_stats = leggi_ordine_excel_to_tsv(
            ordine_id,
            file_ordine.filepath,
            output_elab_dir
        )

        if not success:
            gestisci_errore_elaborazione(ordine_id, error, 'parsing')
            return False, f"Errore parsing: {error}", {}

        # Step 2: Inserimento DB
        success, db_stats, error = inserisci_ordine_da_tsv(
            ordine_id,
            tsv_path,
            current_user.id
        )

        if not success:
            gestisci_errore_elaborazione(ordine_id, error, 'inserimento_db')
            return False, f"Errore DB: {error}", {}

        # Step 3: Spostamento file INPUT → OUTPUT
        output_dir = get_upload_path(file_ordine.anno, esito='Elaborato')
        new_filepath = os.path.join(output_dir, file_ordine.filename)

        success, error = completa_elaborazione_ordine(ordine_id, file_ordine.filepath, new_filepath)

        if not success:
            gestisci_errore_elaborazione(ordine_id, error, 'spostamento')
            return False, f"Errore spostamento: {error}", {}

        # Successo completo
        combined_stats = {**parse_stats, **db_stats}
        message = f"Elaborato: {db_stats['n_ordini']} righe ordine, " \
                  f"{db_stats['n_modelli_inseriti']} nuovi modelli, " \
                  f"{db_stats['n_modelli_aggiornati']} modelli aggiornati"

        return True, message, combined_stats

    except Exception as e:
        error_msg = f"Errore imprevisto: {str(e)}"
        gestisci_errore_elaborazione(ordine_id, error_msg, 'generale')
        return False, error_msg, {}

def scan_po_folder():
    """
    Scansiona le cartelle INPUT/po/ e OUTPUT/po/ e sincronizza con il database
    - Aggiunge file nuovi che non sono nel DB
    - Aggiorna filepath ed esito per file spostati (es. da INPUT a OUTPUT)
    - Rimuove record DB per file che non esistono più
    """
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    files_trovati = {}  # Dict: filename -> filepath (per tracciare quali file esistono)

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
                files_trovati[filename] = filepath

                # Cerca il file per FILENAME (non filepath)
                existing = OrdineAcquisto.query.filter_by(filename=filename).first()

                if existing:
                    # File già nel DB: aggiorna solo se il path è cambiato
                    if existing.filepath != filepath:
                        existing.filepath = filepath
                        existing.esito = 'Da processare'
                        print(f"[SYNC INPUT] Aggiornato path: {filename}")
                else:
                    # File nuovo: aggiungilo al database
                    nuovo_ordine = OrdineAcquisto(
                        anno=anno,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=datetime.now().date(),
                        esito='Da processare'
                    )
                    db.session.add(nuovo_ordine)
                    print(f"[SYNC INPUT] Aggiunto: {filepath}")

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
                files_trovati[filename] = filepath

                # Cerca il file per FILENAME (non filepath)
                existing = OrdineAcquisto.query.filter_by(filename=filename).first()

                if existing:
                    # File già nel DB: aggiorna filepath ed esito (il file è stato spostato in OUTPUT)
                    if existing.filepath != filepath or existing.esito != 'Processato':
                        existing.filepath = filepath
                        existing.esito = 'Processato'
                        existing.data_elaborazione = datetime.utcnow()
                        print(f"[SYNC OUTPUT] Aggiornato path e stato: {filename}")
                else:
                    # File nuovo già processato: aggiungilo direttamente come Processato
                    nuovo_ordine = OrdineAcquisto(
                        anno=anno,
                        filename=filename,
                        filepath=filepath,
                        data_acquisizione=datetime.now().date(),
                        esito='Processato',
                        data_elaborazione=datetime.utcnow(),
                        note='File già processato, trovato in OUTPUT durante sincronizzazione'
                    )
                    db.session.add(nuovo_ordine)
                    print(f"[SYNC OUTPUT] Aggiunto: {filepath}")

    # Rimuovi record orfani (file nel DB ma non nel filesystem)
    tutti_ordini = OrdineAcquisto.query.all()
    for ordine in tutti_ordini:
        if ordine.filename not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {ordine.filename} (path: {ordine.filepath})")
            db.session.delete(ordine)

    db.session.commit()

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
    
    query = OrdineAcquisto.query
    
    # Filtri
    if anno_filter:
        query = query.filter_by(anno=anno_filter)
    if esito_filter:
        query = query.filter_by(esito=esito_filter)
    if filename_filter:
        query = query.filter(OrdineAcquisto.filename.ilike(f'%{filename_filter}%'))
    
    # Ordinamento dinamico - validazione colonne permesse
    sortable_columns = ['anno', 'filename', 'data_acquisizione', 'data_elaborazione', 'esito', 'created_at']
    if sort_by in sortable_columns and hasattr(OrdineAcquisto, sort_by):
        column = getattr(OrdineAcquisto, sort_by)
        if order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default: ordina per anno decrescente e data creazione
        query = query.order_by(OrdineAcquisto.anno.desc(), OrdineAcquisto.created_at.desc())
    
    ordini = query.paginate(page=page, per_page=20, error_out=False)
    
    # Lista anni disponibili per filtro
    anni_disponibili = db.session.query(OrdineAcquisto.anno).distinct().order_by(OrdineAcquisto.anno.desc()).all()
    anni_disponibili = [a[0] for a in anni_disponibili]
    
    return render_template('ordini/list.html', 
                         ordini=ordini, 
                         anno_filter=anno_filter,
                         esito_filter=esito_filter,
                         filename_filter=filename_filter,
                         anni_disponibili=anni_disponibili,
                         sort_by=sort_by,
                         order=order)

@ordini_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Crea un nuovo ordine di acquisto (upload PDF)"""
    form = OrdineAcquistoForm()
    
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
        ordine = OrdineAcquisto(
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
        return redirect(url_for('ordini.list'))
    
    return render_template('ordini/create.html', form=form)

@ordini_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un ordine di acquisto esistente"""
    ordine = OrdineAcquisto.query.get_or_404(id)
    form = OrdineAcquistoEditForm(obj=ordine)
    
    if form.validate_on_submit():
        ordine.data_acquisizione = form.data_acquisizione.data
        ordine.esito = form.esito.data
        ordine.note = form.note.data
        
        db.session.commit()
        flash(f'Ordine {ordine.filename} aggiornato!', 'success')
        return redirect(url_for('ordini.list'))
    
    return render_template('ordini/edit.html', form=form, ordine=ordine)

@ordini_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Elimina un ordine di acquisto"""
    ordine = OrdineAcquisto.query.get_or_404(id)
    filename = ordine.filename
    filepath = ordine.filepath
    
    # Elimina il file dal filesystem
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            flash(f'Errore nell\'eliminazione del file: {str(e)}', 'danger')
            return redirect(url_for('ordini.list'))
    
    # Elimina dal database
    db.session.delete(ordine)
    db.session.commit()
    
    flash(f'Ordine {filename} eliminato.', 'info')
    return redirect(url_for('ordini.list'))

@ordini_bp.route('/download/<int:id>')
@login_required
def download(id):
    """Download del file PDF"""
    ordine = OrdineAcquisto.query.get_or_404(id)
    
    if not os.path.exists(ordine.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('ordini.list'))
    
    directory = os.path.dirname(ordine.filepath)
    filename = os.path.basename(ordine.filepath)
    
    return send_from_directory(directory, filename, as_attachment=True)

@ordini_bp.route('/view/<int:id>')
@login_required
def view(id):
    """Visualizza il PDF nel browser"""
    ordine = OrdineAcquisto.query.get_or_404(id)
    
    if not os.path.exists(ordine.filepath):
        flash('File non trovato sul server!', 'danger')
        return redirect(url_for('ordini.list'))
    
    directory = os.path.dirname(ordine.filepath)
    filename = os.path.basename(ordine.filepath)
    
    return send_from_directory(directory, filename, as_attachment=False)

@ordini_bp.route('/sync')
@admin_required
def sync():
    """Sincronizza manualmente il database con il filesystem"""
    scan_po_folder()
    flash('Sincronizzazione completata!', 'success')
    return redirect(url_for('ordini.list'))

@ordini_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """
    Elabora un ordine di acquisto (SINCRONO)
    Pipeline: Excel → TSV → DB → Spostamento file
    Disponibile solo per ordini con stato 'Da processare' o 'Errore'
    """
    ordine = OrdineAcquisto.query.get_or_404(id)

    # Verifica che l'ordine possa essere elaborato
    if ordine.esito not in ['Da processare', 'Errore']:
        flash(f'L\'ordine è già stato elaborato con successo e non può essere rielaborato.', 'warning')
        return redirect(url_for('ordini.list'))

    # Elabora l'ordine (sincrono - attende il completamento)
    success, message, stats = elabora_ordine(id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('ordini.list'))

@ordini_bp.route('/<int:id>/trace')
@login_required
def view_trace(id):
    """
    Visualizza trace elaborazione per un file ordine
    Mostra timeline degli step con eventuali errori a livello record
    """
    from models import TraceElaborazioneFile, TraceElaborazioneRecord

    file_ordine = FileOrdini.query.get_or_404(id)

    # Query trace file (ordinati per timestamp)
    traces_file = TraceElaborazioneFile.query.filter_by(
        id_file_ordine=id
    ).order_by(TraceElaborazioneFile.timestamp.asc()).all()

    # Query trace record (solo errori)
    traces_record = []
    for trace_file in traces_file:
        records = TraceElaborazioneRecord.query.filter_by(
            id_trace_file=trace_file.id
        ).order_by(TraceElaborazioneRecord.riga_file.asc()).all()
        traces_record.extend(records)

    return render_template('ordini/trace.html',
                         file_ordine=file_ordine,
                         traces_file=traces_file,
                         traces_record=traces_record)