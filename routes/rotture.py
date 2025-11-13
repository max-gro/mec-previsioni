"""
Blueprint per la gestione delle rotture (File Excel)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required
from extensions import db
from models import Rottura
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Import forms
try:
    from forms import RotturaForm, RotturaEditForm
except ImportError:
    print("ERRORE: Impossibile importare RotturaForm e RotturaEditForm da forms.py")
    print("Verifica che forms.py contenga entrambi i form.")
    raise

# Import decorators
try:
    from utils.decorators import admin_required
except ImportError:
    # Fallback se utils.decorators non esiste
    from functools import wraps
    from flask_login import current_user
    
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin():
                flash('Accesso negato: solo gli amministratori possono eseguire questa azione.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function

# Import pandas
try:
    import pandas as pd
except ImportError:
    print("ERRORE: pandas non installato. Esegui: pip install pandas openpyxl")
    raise

rotture_bp = Blueprint('rotture', __name__)

def scan_rotture_folder():
    """
    Scansiona le cartelle INPUT/rotture/ e OUTPUT/rotture/ e sincronizza con il database
    - Aggiunge file nuovi che non sono nel DB
    - Rimuove record DB per file che non esistono più
    """
    base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
    
    files_trovati = set()  # Set di tutti i filepath trovati nel filesystem
    
    # Scansiona INPUT/rotture/
    input_dir = os.path.join(base_dir, 'INPUT', 'rotture')
    if os.path.exists(input_dir):
        for filename in os.listdir(input_dir):
            if not filename.lower().endswith(('.xls', '.xlsx')):
                continue
            
            filepath = os.path.join(input_dir, filename)
            files_trovati.add(filepath)
            
            # Controlla se il file è già nel database
            existing = Rottura.query.filter_by(filepath=filepath).first()
            
            if not existing:
                # Estrai anno dal nome file (se possibile)
                import re
                match = re.search(r'(20\d{2})', filename)
                anno = int(match.group(1)) if match else datetime.now().year
                
                # Aggiungi al database con stato Da processare
                nuova_rottura = Rottura(
                    anno=anno,
                    filename=filename,
                    filepath=filepath,
                    data_acquisizione=datetime.now().date(),
                    esito='Da processare'
                )
                db.session.add(nuova_rottura)
                print(f"[SYNC INPUT] Aggiunto: {filepath}")
    
    # Scansiona OUTPUT/rotture/
    output_dir = os.path.join(base_dir, 'OUTPUT', 'rotture')
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if not filename.lower().endswith(('.xls', '.xlsx')):
                continue
            
            filepath = os.path.join(output_dir, filename)
            files_trovati.add(filepath)
            
            # Controlla se il file è già nel database
            existing = Rottura.query.filter_by(filepath=filepath).first()
            
            if not existing:
                # Estrai anno dal nome file (se possibile)
                import re
                match = re.search(r'(20\d{2})', filename)
                anno = int(match.group(1)) if match else datetime.now().year
                
                # Aggiungi al database con stato Processato
                nuova_rottura = Rottura(
                    anno=anno,
                    filename=filename,
                    filepath=filepath,
                    data_acquisizione=datetime.now().date(),
                    esito='Processato',
                    data_elaborazione=datetime.now(),
                    note='File già processato, trovato in OUTPUT durante sincronizzazione'
                )
                db.session.add(nuova_rottura)
                print(f"[SYNC OUTPUT] Aggiunto: {filepath}")
    
    # Rimuovi record orfani (file nel DB ma non nel filesystem)
    tutte_rotture = Rottura.query.all()
    for rottura in tutte_rotture:
        if rottura.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {rottura.filepath}")
            db.session.delete(rottura)
    
    db.session.commit()

def elabora_rottura_excel(filepath):
    """
    Funzione stub per elaborare file rottura Excel.
    
    Args:
        filepath: percorso completo del file da elaborare
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Leggi il file Excel
        df = pd.read_excel(filepath)
        
        # ðŸŸ¢ STUB: Simula elaborazione
        num_righe = len(df)
        num_colonne = len(df.columns)
        
        # ðŸ”´ QUI ANDRÃ€ LA TUA LOGICA DI ELABORAZIONE REALE
        # Esempio:
        # - Validazione struttura file
        # - Parsing dati rotture
        # - Inserimento/aggiornamento database
        # - Calcoli statistici
        
        # Per ora ritorna sempre successo
        note_success = f"File elaborato con successo: {num_righe} righe e {num_colonne} colonne processate."
        return True, note_success
        
    except Exception as e:
        return False, f"Errore durante elaborazione: {str(e)}"


@rotture_bp.route('/')
@login_required
def list():
    """Lista tutti i file rotture con paginazione e filtri"""
    # Sincronizza con il filesystem
    scan_rotture_folder()
    
    page = request.args.get('page', 1, type=int)
    anno_filter = request.args.get('anno', type=int)
    esito_filter = request.args.get('esito', '')
    
    query = Rottura.query
    
    if anno_filter:
        query = query.filter(Rottura.anno == anno_filter)
    
    if esito_filter:
        query = query.filter(Rottura.esito == esito_filter)
    
    rotture = query.order_by(Rottura.anno.desc(), Rottura.data_acquisizione.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Lista anni disponibili per filtro
    anni_disponibili = db.session.query(Rottura.anno.distinct()).order_by(Rottura.anno.desc()).all()
    anni_disponibili = [a[0] for a in anni_disponibili]
    
    return render_template('rotture/list.html', 
                         rotture=rotture, 
                         anni_disponibili=anni_disponibili,
                         anno_filter=anno_filter,
                         esito_filter=esito_filter)


@rotture_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    """Carica un nuovo file rottura"""
    form = RotturaForm()
    
    # Inizializza anno corrente e data corrente al primo caricamento
    if request.method == 'GET':
        form.anno.data = datetime.now().year
        form.data_acquisizione.data = datetime.now().date()
    
    if form.validate_on_submit():
        file = form.file.data
        anno = form.anno.data
        
        # Crea cartella INPUT/rotture se non esiste
        base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
        input_dir = os.path.join(base_dir, 'INPUT', 'rotture')
        os.makedirs(input_dir, exist_ok=True)
            
        # Salva file
        filename = secure_filename(file.filename)
        # Aggiungi timestamp per evitare sovrascritture
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = os.path.join(input_dir, filename)
        file.save(filepath)
            
        # Crea record database
        rottura = Rottura(
            anno=anno,
            filename=filename,
            filepath=filepath,
            data_acquisizione=form.data_acquisizione.data,
            esito='Da processare',
            note=form.note.data
        )
        db.session.add(rottura)
        db.session.commit()
        
        flash(f'File rottura {filename} caricato con successo!', 'success')
        return redirect(url_for('rotture.list'))
    
    return render_template('rotture/create.html', form=form)


@rotture_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(id):
    """Modifica un file rottura esistente"""
    rottura = Rottura.query.get_or_404(id)
    form = RotturaEditForm(obj=rottura)
        
    if form.validate_on_submit():
        # Permetti modifica solo note per file giÃ  processati
        if rottura.esito == 'Processato':
            rottura.note = form.note.data
        else:
            rottura.data_acquisizione = form.data_acquisizione.data
            if form.data_elaborazione.data:
                rottura.data_elaborazione = datetime.combine(form.data_elaborazione.data, datetime.min.time())
            rottura.esito = form.esito.data
            rottura.note = form.note.data
        
        db.session.commit()
        flash(f'File rottura aggiornato!', 'success')
        return redirect(url_for('rotture.list'))
    
        flash(f'File rottura aggiornato!', 'success')
        return redirect(url_for('rotture.list'))
    
    return render_template('rotture/edit.html', form=form, rottura=rottura)


@rotture_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Elimina un file rottura"""
    rottura = Rottura.query.get_or_404(id)
    filename = rottura.filename
    
    # Elimina file fisico se esiste
    if os.path.exists(rottura.filepath):
        try:
            os.remove(rottura.filepath)
        except Exception as e:
            flash(f'Errore eliminazione file fisico: {e}', 'warning')
    
    # Elimina record database
    db.session.delete(rottura)
    db.session.commit()
    
    flash(f'File rottura {filename} eliminato.', 'info')
    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """Elabora un file rottura"""
    rottura = Rottura.query.get_or_404(id)
    
    # Controlla stato
    if rottura.esito == 'Processato':
        flash('Il file Ã¨ giÃ  stato processato!', 'warning')
        return redirect(url_for('rotture.list'))
    
    # Controlla esistenza file
    if not os.path.exists(rottura.filepath):
        flash(f'File non trovato: {rottura.filepath}', 'error')
        rottura.esito = 'Errore'
        rottura.note = f"File non trovato al path: {rottura.filepath}"
        rottura.data_elaborazione = datetime.now()
        db.session.commit()
        return redirect(url_for('rotture.list'))
    
    # Elabora file
    success, message = elabora_rottura_excel(rottura.filepath)
    
    if success:
        # Sposta file in OUTPUT
        base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'OUTPUT', 'rotture')
        os.makedirs(output_dir, exist_ok=True)
        
        new_filepath = os.path.join(output_dir, rottura.filename)
        
        try:
            # Usa shutil.move invece di os.rename per cross-device compatibility
            import shutil
            shutil.move(rottura.filepath, new_filepath)
            
            # Aggiorna record
            rottura.filepath = new_filepath
            rottura.esito = 'Processato'
            rottura.data_elaborazione = datetime.now()
            rottura.note = message
            db.session.commit()
            
            flash(f'File elaborato con successo!', 'success')
        except Exception as e:
            flash(f'Errore spostamento file: {e}', 'error')
            rottura.esito = 'Errore'
            rottura.note = f"Elaborazione OK ma errore spostamento file: {str(e)}"
            rottura.data_elaborazione = datetime.now()
            db.session.commit()
    else:
        # Elaborazione fallita
        rottura.esito = 'Errore'
        rottura.note = message
        rottura.data_elaborazione = datetime.now()
        db.session.commit()
        
        flash(f'Errore durante elaborazione: {message}', 'error')
    
    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/download')
@login_required
def download(id):
    """Download file rottura"""
    rottura = Rottura.query.get_or_404(id)
    
    if not os.path.exists(rottura.filepath):
        flash('File non trovato!', 'error')
        return redirect(url_for('rotture.list'))
    
    return send_file(rottura.filepath, as_attachment=True, download_name=rottura.filename)


@rotture_bp.route('/sync')
@admin_required
def sync():
    """Sincronizza manualmente il database con il filesystem"""
    scan_rotture_folder()
    flash('Sincronizzazione completata!', 'success')
    return redirect(url_for('rotture.list'))