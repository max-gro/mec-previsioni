"""
Blueprint per la gestione Anagrafiche File Excel (CRUD + Upload)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import AnagraficaFile
from forms import AnagraficaFileForm, AnagraficaFileEditForm, NuovaMarcaForm
from utils.decorators import admin_required
import os
import shutil
import random
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
                existing = AnagraficaFile.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = AnagraficaFile(
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
                existing = AnagraficaFile.query.filter_by(filepath=filepath).first()
                
                if not existing:
                    # Aggiungi al database
                    nuova_anagrafica = AnagraficaFile(
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
    tutte_anagrafiche = AnagraficaFile.query.all()
    for anagrafica in tutte_anagrafiche:
        if anagrafica.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {anagrafica.filepath}")
            db.session.delete(anagrafica)
    
    db.session.commit()


def elabora_anagrafica(anagrafica_id):
    """
    Elabora un file di anagrafica
    
    Logica simulata:
    - 70% probabilità di successo →  sposta in OUTPUT, stato Processato
    - 30% probabilità di errore →  lascia in INPUT, stato Errore
    
    TODO: Sostituire con logica reale di elaborazione
    """
    anagrafica = AnagraficaFile.query.get_or_404(anagrafica_id)
    
    # Verifica che il file esista
    if not os.path.exists(anagrafica.filepath):
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
            
            # Aggiorna database
            anagrafica.filepath = new_filepath
            anagrafica.esito = 'Processato'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'Elaborazione completata con successo.\n' \
                            f'Record elaborati: {random.randint(50, 500)}.\n' \
                            f'Componenti aggiornati: {random.randint(20, 200)}.'
            
            db.session.commit()
            
            return True, 'Elaborazione completata con successo!'
        
        except Exception as e:
            # Errore durante lo spostamento
            anagrafica.esito = 'Errore'
            anagrafica.data_elaborazione = date.today()
            anagrafica.note = f'Errore durante lo spostamento file: {str(e)}'
            db.session.commit()
            return False, f'Errore durante lo spostamento: {str(e)}'
    
    else:
        # ELABORAZIONE FALLITA
        
        anagrafica.esito = 'Errore'
        anagrafica.data_elaborazione = date.today()
        
        # Messaggi di errore random realistici
        errori_possibili = [
            '❌ Formato file non valido: colonne mancanti',
            '❌ Errore: duplicati trovati nelle righe 15-23',
            '❌ Validazione fallita: codici componente non validi',
            '❌ Errore di integrità : riferimenti a marche inesistenti',
            '❌ File corrotto o incompleto',
        ]
        
        anagrafica.note = random.choice(errori_possibili)
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
    
    query = AnagraficaFile.query
    
    # Filtri
    if marca_filter:
        query = query.filter_by(marca=marca_filter)
    if esito_filter:
        query = query.filter_by(esito=esito_filter)
    if anno_filter:
        query = query.filter_by(anno=anno_filter)
    if q:
        query = query.filter(AnagraficaFile.filename.ilike(f"%{q}%"))
    
    # Ordinamento dinamico
    sortable_columns = ['anno','marca','filename','data_acquisizione','data_elaborazione','esito','created_at','updated_at']
    if sort_by in sortable_columns and hasattr(AnagraficaFile, sort_by):
        column = getattr(AnagraficaFile, sort_by)
        if order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Default: ordina per data creazione decrescente
        query = query.order_by(AnagraficaFile.created_at.desc())
    
    anagrafiche = query.paginate(page=page, per_page=20, error_out=False)
    
    # Liste per filtri
    marche_disponibili = get_marche_disponibili()
    anni_disponibili = [r[0] for r in db.session.query(AnagraficaFile.anno).distinct().order_by(AnagraficaFile.anno.desc())]
    
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
        anagrafica = AnagraficaFile(
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
    anagrafica = AnagraficaFile.query.get_or_404(id)
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
    
    return redirect(url_for('anagrafiche.list'))


@anagrafiche_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Elimina un'anagrafica"""
    anagrafica = AnagraficaFile.query.get_or_404(id)
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
    anagrafica = AnagraficaFile.query.get_or_404(id)
    
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
    anagrafica = AnagraficaFile.query.get_or_404(id)
    
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


#from flask import Markup
from markupsafe import Markup
import pandas as pd

@anagrafiche_bp.route('/preview/<int:id>')
@login_required
def preview(id):
    """Anteprima HTML del file Excel (prime righe del primo foglio)."""
    ana = AnagraficaFile.query.get_or_404(id)

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
