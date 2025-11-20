"""
Blueprint per la gestione Ordini di Acquisto (CRUD + Upload PDF + Elaborazione)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, OrdineAcquisto, TraceElab, TraceElabDett
from forms import OrdineAcquistoForm, OrdineAcquistoEditForm
from utils.decorators import admin_required
import os
import re
import shutil
import random
import time
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
    Elabora un ordine di acquisto (funzione STUB per test) con tracciamento dettagliato

    Returns:
        tuple: (success: bool, message: str)
    """
    ordine = OrdineAcquisto.query.get(ordine_id)
    if not ordine:
        return False, "Ordine non trovato"

    # ✅ STEP 0: Genera nuovo id_elab per questa elaborazione
    result = db.session.execute(db.text("SELECT nextval('seq_id_elab')"))
    id_elab = result.scalar()

    # ✅ STEP 1: Crea record elaborazione - START
    trace_start = TraceElab(
        id_elab=id_elab,
        id_file=ordine_id,
        tipo_file='ORD',
        step='START',
        stato='OK',
        messaggio='Inizio elaborazione ordine PDF'
    )
    db.session.add(trace_start)
    db.session.commit()  # Commit per avere l'ID
    id_trace_start = trace_start.id_trace

    try:
        # Verifica che il file esista
        if not os.path.exists(ordine.filepath):
            # Logga errore critico
            dettaglio = TraceElabDett(
                id_trace=id_trace_start,
                record_pos=0,
                record_data={'key': 'FILE_NOT_FOUND'},
                stato='KO',
                messaggio=f"File non trovato sul filesystem: {ordine.filepath}"
            )
            db.session.add(dettaglio)

            # Finalizza elaborazione con errore
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
            db.session.add(trace_end)

            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = "File non trovato sul filesystem"

            db.session.commit()
            return False, "File non trovato sul filesystem"

        # ✅ STEP 2: Simula elaborazione (70% successo, 30% errore)
        time.sleep(random.uniform(0.5, 2.0))  # Simula tempo elaborazione

        # Simula numero di righe elaborate
        num_componenti = random.randint(5, 120)
        success = random.random() > 0.3

        if success:
            # SUCCESSO: sposta file in OUTPUT
            output_dir = get_upload_path(ordine.anno, esito='Processato')
            new_filepath = os.path.join(output_dir, ordine.filename)

            try:
                # Simula qualche warning (opzionale)
                num_warnings = random.randint(0, 5)
                for i in range(num_warnings):
                    riga_num = random.randint(1, num_componenti)
                    dettaglio = TraceElabDett(
                        id_trace=id_trace_start,
                        record_pos=riga_num,
                        stato='WARN',
                        messaggio=f"Prezzo componente sospetto (troppo basso): €{random.uniform(0.01, 0.99):.2f}",
                        record_data={'key': f'VAL_WARN|prezzo|{riga_num}', 'campo': 'prezzo', 'riga': riga_num}
                    )
                    db.session.add(dettaglio)

                # Sposta il file
                shutil.move(ordine.filepath, new_filepath)

                # ✅ STEP 3: Finalizza elaborazione con successo
                importo_totale = random.randint(1000, 50000)
                messaggio_finale = f"Elaborati {num_componenti} componenti. Importo: €{importo_totale:,}"

                trace_end = TraceElab(
                    id_elab=id_elab,
                    id_file=ordine_id,
                    tipo_file='ORD',
                    step='END',
                    stato='WARN' if num_warnings > 0 else 'OK',
                    messaggio=messaggio_finale,
                    righe_totali=num_componenti,
                    righe_ok=num_componenti - num_warnings,
                    righe_errore=0,
                    righe_warning=num_warnings
                )
                db.session.add(trace_end)

                # Aggiorna record file
                ordine.filepath = new_filepath
                ordine.esito = 'Processato'
                ordine.data_elaborazione = datetime.utcnow()
                ordine.note = messaggio_finale

                db.session.commit()
                return True, "Ordine elaborato con successo!"

            except Exception as e:
                # Errore nello spostamento file
                dettaglio = TraceElabDett(
                    id_trace=id_trace_start,
                    record_pos=0,
                    record_data={'key': 'FILE_MOVE_ERROR'},
                    stato='KO',
                    messaggio=f"Errore spostamento file: {str(e)}"
                )
                db.session.add(dettaglio)

                trace_end = TraceElab(
                    id_elab=id_elab,
                    id_file=ordine_id,
                    tipo_file='ORD',
                    step='END',
                    stato='KO',
                    messaggio='Errore spostamento file',
                    righe_totali=num_componenti,
                    righe_ok=0,
                    righe_errore=1,
                    righe_warning=num_warnings
                )
                db.session.add(trace_end)

                ordine.esito = 'Errore'
                ordine.data_elaborazione = datetime.utcnow()
                ordine.note = str(e)

                db.session.commit()
                return False, f"Errore: {str(e)}"

        else:
            # ERRORE SIMULATO: file rimane in INPUT
            errori_possibili = [
                ("PDF corrotto o non leggibile", "PDF_CORRUPT"),
                ("Formato ordine non riconosciuto", "FORMAT_ERROR"),
                ("Mancano campi obbligatori nel PDF", "MISSING_FIELDS"),
                ("Codici componenti non validi", "INVALID_CODES"),
                ("Data ordine non presente o non valida", "INVALID_DATE")
            ]

            errore_msg, errore_code = random.choice(errori_possibili)

            # Simula errori su più righe
            num_errori = random.randint(3, 15)
            for i in range(num_errori):
                riga_num = random.randint(1, num_componenti)
                campo = random.choice(['codice_componente', 'quantita', 'prezzo', 'data_ordine'])
                dettaglio = TraceElabDett(
                    id_trace=id_trace_start,
                    record_pos=riga_num,
                    stato='KO',
                    messaggio=errore_msg,
                    record_data={'key': f'{errore_code}|{campo}|{riga_num}', 'campo': campo, 'riga': riga_num}
                )
                db.session.add(dettaglio)

            # ✅ STEP 3: Finalizza elaborazione con errore
            messaggio_finale = f"{errore_msg}: {num_errori} errori su {num_componenti} righe"

            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio=messaggio_finale,
                righe_totali=num_componenti,
                righe_ok=0,
                righe_errore=num_errori,
                righe_warning=0
            )
            db.session.add(trace_end)

            ordine.esito = 'Errore'
            ordine.data_elaborazione = datetime.utcnow()
            ordine.note = messaggio_finale

            db.session.commit()
            return False, f"Elaborazione fallita: {errore_msg}"

    except Exception as e:
        # Gestione errori imprevisti
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
        db.session.add(trace_end)
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
                
                # Controlla se il file è già nel database
                existing = OrdineAcquisto.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database con stato Da processare
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
                files_trovati.add(filepath)
                
                # Controlla se il file è già nel database
                existing = OrdineAcquisto.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database con stato Processato
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
        if ordine.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {ordine.filepath}")
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
    Disponibile solo per ordini con stato 'Da processare' o 'Errore'
    """
    ordine = OrdineAcquisto.query.get_or_404(id)
    
    # Verifica che l'ordine possa essere elaborato
    if ordine.esito not in ['Da processare', 'Errore']:
        flash(f'L\'ordine è già stato elaborato con successo e non può essere rielaborato.', 'warning')
        return redirect(url_for('ordini.list'))
    
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
    ordine = OrdineAcquisto.query.get_or_404(id)

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
    ordine = OrdineAcquisto.query.get_or_404(id)

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

    ordine = OrdineAcquisto.query.get_or_404(id)

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