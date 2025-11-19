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

    # ✅ STEP 1: Crea record elaborazione - START
    ts_inizio = datetime.utcnow()
    trace = TraceElab(
        id_file=ordine_id,
        tipo_file='ORD',
        step='START',
        stato='OK',
        messaggio='Inizio elaborazione ordine'
    )
    db.session.add(trace)
    db.session.commit()  # Commit per avere l'ID
    id_trace = trace.id_trace

    try:
        # Verifica che il file esista
        if not os.path.exists(ordine.filepath):
            # Logga errore critico
            dettaglio = TraceElabDett(
                id_trace=id_trace,
                record_pos=0,
                record_key='FILE_NOT_FOUND',
                stato='KO',
                messaggio=f"File non trovato sul filesystem: {ordine.filepath}"
            )
            db.session.add(dettaglio)

            # Finalizza elaborazione con errore
            ts_fine = datetime.utcnow()
            durata_secondi = int((ts_fine - ts_inizio).total_seconds())
            trace_end = TraceElab(
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio=f"File non trovato (durata: {durata_secondi}s)"
            )
            db.session.add(trace_end)

            ordine.esito = 'Errore'
            ordine.data_elaborazione = ts_fine
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
                        id_trace=id_trace,
                        record_pos=riga_num,
                        record_key=f'VAL_WARN|prezzo|{riga_num}',
                        stato='WARN',
                        messaggio=f"Prezzo componente sospetto (troppo basso): €{random.uniform(0.01, 0.99):.2f}",
                        record_data={'campo': 'prezzo', 'riga': riga_num}
                    )
                    db.session.add(dettaglio)

                # Sposta il file
                shutil.move(ordine.filepath, new_filepath)

                # ✅ STEP 3: Finalizza elaborazione con successo
                ts_fine = datetime.utcnow()
                durata_secondi = int((ts_fine - ts_inizio).total_seconds())
                importo_totale = random.randint(1000, 50000)
                messaggio_finale = f"Elaborati {num_componenti} componenti. Importo totale: €{importo_totale:,}. {num_warnings} warning. Durata: {durata_secondi}s"

                trace_end = TraceElab(
                    id_file=ordine_id,
                    tipo_file='ORD',
                    step='END',
                    stato='WARN' if num_warnings > 0 else 'OK',
                    messaggio=messaggio_finale
                )
                db.session.add(trace_end)

                # Aggiorna record file
                ordine.filepath = new_filepath
                ordine.esito = 'Processato'
                ordine.data_elaborazione = ts_fine
                ordine.note = messaggio_finale

                db.session.commit()
                return True, "Ordine elaborato con successo!"

            except Exception as e:
                # Errore nello spostamento file
                dettaglio = TraceElabDett(
                    id_trace=id_trace,
                    record_pos=0,
                    record_key='FILE_MOVE_ERROR',
                    stato='KO',
                    messaggio=f"Errore spostamento file: {str(e)}"
                )
                db.session.add(dettaglio)

                ts_fine = datetime.utcnow()
                durata_secondi = int((ts_fine - ts_inizio).total_seconds())
                trace_end = TraceElab(
                    id_file=ordine_id,
                    tipo_file='ORD',
                    step='END',
                    stato='KO',
                    messaggio=f"Errore durante spostamento file (durata: {durata_secondi}s)"
                )
                db.session.add(trace_end)

                ordine.esito = 'Errore'
                ordine.data_elaborazione = ts_fine
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
                    id_trace=id_trace,
                    record_pos=riga_num,
                    record_key=f'{errore_code}|{campo}|{riga_num}',
                    stato='KO',
                    messaggio=errore_msg,
                    record_data={'campo': campo, 'riga': riga_num}
                )
                db.session.add(dettaglio)

            # ✅ STEP 3: Finalizza elaborazione con errore
            ts_fine = datetime.utcnow()
            durata_secondi = int((ts_fine - ts_inizio).total_seconds())
            messaggio_finale = f"Elaborazione fallita: {errore_msg}. Trovati {num_errori} errori su {num_componenti} righe. Durata: {durata_secondi}s"

            trace_end = TraceElab(
                id_file=ordine_id,
                tipo_file='ORD',
                step='END',
                stato='KO',
                messaggio=messaggio_finale
            )
            db.session.add(trace_end)

            ordine.esito = 'Errore'
            ordine.data_elaborazione = ts_fine
            ordine.note = messaggio_finale

            db.session.commit()
            return False, f"Elaborazione fallita: {errore_msg}"

    except Exception as e:
        # Gestione errori imprevisti
        ts_fine = datetime.utcnow()
        durata_secondi = int((ts_fine - ts_inizio).total_seconds())

        trace_end = TraceElab(
            id_file=ordine_id,
            tipo_file='ORD',
            step='END',
            stato='KO',
            messaggio=f"Errore imprevisto: {str(e)} (durata: {durata_secondi}s)"
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

    return redirect(url_for('ordini.list'))


# ========== NUOVI ENDPOINT PER TRACCIAMENTO ELABORAZIONI ==========

@ordini_bp.route('/<int:id>/elaborazioni')
@login_required
def elaborazioni_list(id):
    """
    LIVELLO 2: Lista di tutte le elaborazioni per un ordine specifico
    """
    ordine = OrdineAcquisto.query.get_or_404(id)

    # Recupera tutte le elaborazioni START per questo ordine (ogni START rappresenta un'elaborazione)
    elaborazioni = TraceElab.query.filter_by(
        tipo_file='ORD',
        id_file=id,
        step='START'
    ).order_by(TraceElab.created_at.desc()).all()

    # Per ogni elaborazione, arricchisci con info END
    for elab in elaborazioni:
        elab.trace_end = TraceElab.query.filter_by(
            tipo_file='ORD',
            id_file=id,
            step='END'
        ).filter(TraceElab.created_at >= elab.created_at).order_by(TraceElab.created_at).first()

    return render_template('ordini/elaborazioni_list.html',
                         ordine=ordine,
                         elaborazioni=elaborazioni)


@ordini_bp.route('/<int:id>/elaborazioni/<int:id_elab>/dettaglio')
@login_required
def elaborazione_dettaglio(id, id_elab):
    """
    LIVELLO 3: Dettaglio completo di un'elaborazione specifica (JSON per modal)
    """
    ordine = OrdineAcquisto.query.get_or_404(id)
    elaborazione = TraceElab.query.get_or_404(id_elab)

    # Verifica che l'elaborazione appartenga all'ordine
    if elaborazione.tipo_file != 'ORD' or elaborazione.id_file != id:
        flash('Elaborazione non trovata per questo ordine', 'danger')
        return redirect(url_for('ordini.elaborazioni_list', id=id))

    # Trova il trace END corrispondente
    elaborazione.trace_end = TraceElab.query.filter_by(
        tipo_file='ORD',
        id_file=id,
        step='END'
    ).filter(TraceElab.created_at >= elaborazione.created_at).order_by(TraceElab.created_at).first()

    # Recupera tutti i dettagli (anomalie)
    page = request.args.get('page', 1, type=int)
    stato_filter = request.args.get('stato', '')

    query = TraceElabDett.query.filter_by(id_trace=id_elab)

    if stato_filter:
        query = query.filter_by(stato=stato_filter)

    query = query.order_by(TraceElabDett.record_pos)
    dettagli = query.paginate(page=page, per_page=50, error_out=False)

    # Se richiesta AJAX, ritorna JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify

        # Calcola statistiche dai dettagli
        num_ko = sum(1 for d in dettagli.items if d.stato == 'KO')
        num_warn = sum(1 for d in dettagli.items if d.stato == 'WARN')
        num_ok = len(dettagli.items) - num_ko - num_warn

        durata_secondi = None
        if elaborazione.trace_end:
            durata_secondi = int((elaborazione.trace_end.created_at - elaborazione.created_at).total_seconds())

        return jsonify({
            'elaborazione': {
                'id': elaborazione.id_trace,
                'ts_inizio': elaborazione.created_at.isoformat() if elaborazione.created_at else None,
                'ts_fine': elaborazione.trace_end.created_at.isoformat() if elaborazione.trace_end else None,
                'durata_secondi': durata_secondi,
                'esito': elaborazione.trace_end.stato if elaborazione.trace_end else 'IN_CORSO',
                'righe_totali': len(dettagli.items),
                'righe_ok': num_ok,
                'righe_errore': num_ko,
                'righe_warning': num_warn,
                'messaggio_globale': elaborazione.trace_end.messaggio if elaborazione.trace_end else elaborazione.messaggio
            },
            'dettagli': [{
                'id': d.id_dett,
                'riga_numero': d.record_pos,
                'tipo_messaggio': d.stato,
                'codice_errore': d.record_key,
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
                         elaborazione=elaborazione,
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
    elaborazione = TraceElab.query.get_or_404(id_elab)

    # Verifica che l'elaborazione appartenga all'ordine
    if elaborazione.tipo_file != 'ORD' or elaborazione.id_file != id:
        flash('Elaborazione non trovata per questo ordine', 'danger')
        return redirect(url_for('ordini.elaborazioni_list', id=id))

    # Recupera tutti i dettagli
    dettagli = TraceElabDett.query.filter_by(
        id_trace=id_elab
    ).order_by(TraceElabDett.record_pos).all()

    # Crea CSV in memoria
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow([
        'Riga',
        'Tipo',
        'Codice Errore',
        'Messaggio',
        'Campo',
        'Valore Originale'
    ])

    # Dati
    for d in dettagli:
        campo = d.record_data.get('campo') if d.record_data else ''
        writer.writerow([
            d.record_pos or '',
            d.stato or '',
            d.record_key or '',
            d.messaggio or '',
            campo or '',
            ''  # valore_originale non più presente nel nuovo sistema
        ])

    # Ritorna come download
    output = si.getvalue()
    si.close()

    filename = f"elaborazione_{ordine.filename}_{elaborazione.id}_{elaborazione.ts_inizio.strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )