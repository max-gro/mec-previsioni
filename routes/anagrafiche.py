"""
Blueprint per la gestione Anagrafiche File Excel (CRUD + Upload)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, FileAnagrafica, TraceElab, TraceElabDett
from forms import AnagraficaFileForm, AnagraficaFileEditForm, NuovaMarcaForm
from utils.decorators import admin_required
import os
import shutil
import random
import time
from datetime import datetime, date

anagrafiche_bp = Blueprint('anagrafiche', __name__)

# Marche iniziali di default
MARCHE_DEFAULT = ['HISENSE', 'HOMA', 'MIDEA']

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
                existing = FileAnagrafica.query.filter_by(filepath=filepath).first()
                
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
                    print(f"[SYNC] Aggiunto: {filepath}")
    
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
                existing = FileAnagrafica.query.filter_by(filepath=filepath).first()
                
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
                    print(f"[SYNC] Aggiunto: {filepath}")
    
    # Rimuovi record orfani
    tutte_anagrafiche = FileAnagrafica.query.all()
    for anagrafica in tutte_anagrafiche:
        if anagrafica.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {anagrafica.filepath}")
            db.session.delete(anagrafica)
    
    db.session.commit()


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

    # ✅ STEP 2: Crea record elaborazione START
    ts_inizio = datetime.utcnow()
    trace_start = TraceElab(
        id_elab=id_elab,
        id_file=anagrafica_id,
        tipo_file='ANA',
        step='START',
        stato='OK',
        messaggio='Inizio elaborazione anagrafica'
    )
    db.session.add(trace_start)
    db.session.commit()

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
        db.session.add(trace_end)

        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = '❌ File non trovato sul filesystem'
        db.session.commit()
        return False, 'File non trovato sul filesystem'
    
    # Simula elaborazione con esito random
    esito_ok = random.random() < 0.7  # 70% successo
    
    if esito_ok:
        # ELABORAZIONE RIUSCITA
        
        # Path di destinazione OUTPUT
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'OUTPUT', 'anagrafiche', anagrafica.marca)
        os.makedirs(output_dir, exist_ok=True)
        
        new_filepath = os.path.join(output_dir, anagrafica.filename)
        
        try:
            # Sposta file da INPUT a OUTPUT
            shutil.move(anagrafica.filepath, new_filepath)

            # Statistiche simulate
            num_record = random.randint(50, 500)
            num_componenti = random.randint(20, 200)
            num_warnings = random.randint(0, 10)

            # Crea alcuni record di dettaglio simulati per i warnings
            if num_warnings > 0:
                warnings_simulati = [
                    'Codice componente mancante',
                    'Descrizione troppo lunga (troncata)',
                    'Prezzo non valido (impostato a 0)',
                    'Data non valida',
                    'Marca sconosciuta'
                ]
                for i in range(min(num_warnings, 5)):  # Max 5 warning di esempio
                    trace_dett = TraceElabDett(
                        id_trace=trace_start.id_trace,
                        record_pos=random.randint(1, num_record),
                        record_data={'key': f'ANA-{random.randint(1000, 9999)}', 'campo': random.choice(['codice', 'descrizione', 'prezzo', 'data', 'marca'])},
                        stato='WARN',
                        messaggio=random.choice(warnings_simulati)
                    )
                    db.session.add(trace_dett)

            # Crea trace END con successo
            trace_end = TraceElab(
                id_elab=id_elab,
                id_file=anagrafica_id,
                tipo_file='ANA',
                step='END',
                stato='WARN' if num_warnings > 0 else 'OK',
                messaggio=f'Elaborazione completata. Record: {num_record}, Componenti: {num_componenti}',
                righe_totali=num_record,
                righe_ok=num_record - num_warnings,
                righe_errore=0,
                righe_warning=num_warnings
            )
            db.session.add(trace_end)

            # Aggiorna database
            anagrafica.filepath = new_filepath
            anagrafica.esito = 'Processato'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'Elaborazione completata con successo.\n' \
                            f'Record elaborati: {num_record}.\n' \
                            f'Componenti aggiornati: {num_componenti}.'

            db.session.commit()

            return True, 'Elaborazione completata con successo!'

        except Exception as e:
            # Errore durante lo spostamento
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
            db.session.add(trace_end)

            anagrafica.esito = 'Errore'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'Errore durante lo spostamento file: {str(e)}'
            db.session.commit()
            return False, f'Errore durante lo spostamento: {str(e)}'
    
    else:
        # ELABORAZIONE FALLITA

        # Messaggi di errore random realistici
        errori_possibili = [
            '❌ Formato file non valido: colonne mancanti',
            '❌ Errore: duplicati trovati nelle righe 15-23',
            '❌ Validazione fallita: codici componente non validi',
            '❌ Errore di integrità : riferimenti a marche inesistenti',
            '❌ File corrotto o incompleto',
        ]

        errore_msg = random.choice(errori_possibili)

        # Simula numero errori
        num_errori = random.randint(5, 50)

        # Crea alcuni record di dettaglio simulati per gli errori
        errori_dettaglio = [
            'Formato colonna non valido',
            'Valore duplicato trovato',
            'Riferimento a marca inesistente',
            'Codice componente già esistente',
            'Lunghezza campo superata'
        ]
        for i in range(min(num_errori, 8)):  # Max 8 errori di esempio
            trace_dett = TraceElabDett(
                id_trace=trace_start.id_trace,
                record_pos=random.randint(1, 100),
                record_data={'key': f'ANA-{random.randint(1000, 9999)}', 'campo': random.choice(['codice', 'descrizione', 'marca', 'categoria'])},
                stato='KO',
                messaggio=random.choice(errori_dettaglio)
            )
            db.session.add(trace_dett)

        # Crea trace END con errore
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=anagrafica_id,
            tipo_file='ANA',
            step='END',
            stato='KO',
            messaggio=errore_msg,
            righe_totali=num_errori,
            righe_ok=0,
            righe_errore=num_errori,
            righe_warning=0
        )
        db.session.add(trace_end)

        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        anagrafica.note = f'❌ {errore_msg}'
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
    """Elimina un'anagrafica"""
    anagrafica = FileAnagrafica.query.get_or_404(id)
    filename = anagrafica.filename
    filepath = anagrafica.filepath
    
    # Elimina il file dal filesystem
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            flash(f'Errore nell\'eliminazione del file: {str(e)}', 'danger')
            return redirect(url_for('anagrafiche.list'))
    
    # Elimina dal database
    db.session.delete(anagrafica)
    db.session.commit()
    
    flash(f'Anagrafica {filename} eliminata.', 'info')
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
    """Sincronizza manualmente il database con il filesystem"""
    scan_anagrafiche_folder()
    flash('Sincronizzazione completata!', 'success')
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
