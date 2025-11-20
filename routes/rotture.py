"""
Blueprint per la gestione delle rotture (File Excel)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from models import (
    db, FileRottura, Rottura, RotturaComponente,
    Modello, Componente, UtenteRottura, Rivenditore,
    TraceElab, TraceElabDett
)
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Import funzioni elaborazione
from routes.rotture_funzioni_elaborazione import elabora_file_rottura_completo as _elabora_file_rottura_completo

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
            existing = FileRottura.query.filter_by(filepath=filepath).first()

            if not existing:
                # Estrai anno dal nome file (se possibile)
                import re
                match = re.search(r'(20\d{2})', filename)
                anno = int(match.group(1)) if match else datetime.now().year

                # Aggiungi al database con stato Da processare
                nuova_rottura = FileRottura(
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
            existing = FileRottura.query.filter_by(filepath=filepath).first()

            if not existing:
                # Estrai anno dal nome file (se possibile)
                import re
                match = re.search(r'(20\d{2})', filename)
                anno = int(match.group(1)) if match else datetime.now().year

                # Aggiungi al database con stato Processato
                nuova_rottura = FileRottura(
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
    tutte_rotture = FileRottura.query.all()
    for rottura in tutte_rotture:
        if rottura.filepath not in files_trovati:
            print(f"[SYNC] Rimosso record orfano: {rottura.filepath}")
            db.session.delete(rottura)

    db.session.commit()

        

@rotture_bp.route('/')
@login_required
def list():
    """Lista tutti i file rotture con paginazione e filtri"""
    # Sincronizza con il filesystem
    scan_rotture_folder()
    
    page = request.args.get('page', 1, type=int)
    anno_filter = request.args.get('anno', type=int)
    esito_filter = request.args.get('esito', '')
    
    query = FileRottura.query

    if anno_filter:
        query = query.filter(FileRottura.anno == anno_filter)

    if esito_filter:
        query = query.filter(FileRottura.esito == esito_filter)

    rotture = query.order_by(FileRottura.anno.desc(), FileRottura.data_acquisizione.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Lista anni disponibili per filtro
    anni_disponibili = db.session.query(FileRottura.anno.distinct()).order_by(FileRottura.anno.desc()).all()
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
        rottura = FileRottura(
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
    rottura = FileRottura.query.get_or_404(id)
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
    """Elimina un file rottura con cascade (file + rotture + componenti)"""
    file_rottura = FileRottura.query.get_or_404(id)
    filename = file_rottura.filename

    try:
        # Crea trace per eliminazione
        trace_file = TraceElaborazioneFile(
            id_file=id,
            tipo_file='rotture',
            step='delete',
            stato='start',
            messaggio=f'Inizio eliminazione file {filename}'
        )
        db.session.add(trace_file)
        db.session.flush()  # Per ottenere id_trace

        # Elimina rotture componenti associate
        rotture_ids = [r.id_rottura for r in Rottura.query.filter_by(id_file_rotture=id).all()]
        if rotture_ids:
            num_comp = RotturaComponente.query.filter(RotturaComponente.id_rottura.in_(rotture_ids)).delete(synchronize_session=False)
            trace_rec = TraceElabDett(
                id_trace=trace_file.id_trace,
                record_pos=0,
                record_data={'key': f'{len(rotture_ids)} rotture', 'tipo': 'rotture_componenti'},
                messaggio=f'Eliminati {num_comp} record rotture_componenti',
                stato='OK'
            )
            db.session.add(trace_rec)

        # Elimina rotture associate
        num_rotture = Rottura.query.filter_by(id_file_rotture=id).delete()
        if num_rotture > 0:
            trace_rec = TraceElabDett(
                id_trace=trace_file.id_trace,
                record_pos=0,
                record_data={'key': str(id), 'tipo': 'rotture'},
                messaggio=f'Eliminati {num_rotture} record rotture',
                stato='OK'
            )
            db.session.add(trace_rec)

        # Elimina file fisico se esiste
        if os.path.exists(file_rottura.filepath):
            try:
                os.remove(file_rottura.filepath)
                trace_rec = TraceElabDett(
                    id_trace=trace_file.id_trace,
                    record_pos=0,
                    record_data={'key': filename, 'tipo': 'file'},
                    messaggio=f'File fisico eliminato: {file_rottura.filepath}',
                    stato='OK'
                )
                db.session.add(trace_rec)
            except Exception as e:
                flash(f'Errore eliminazione file fisico: {e}', 'warning')
                trace_rec = TraceElabDett(
                    id_trace=trace_file.id_trace,
                    record_pos=0,
                    record_data={'key': filename, 'tipo': 'file'},
                    messaggio=f'Errore eliminazione file fisico: {str(e)}',
                    stato='KO'
                )
                db.session.add(trace_rec)

        # Elimina record file_rotture
        db.session.delete(file_rottura)

        # Trace completamento
        trace_file.stato = 'success'
        trace_file.messaggio = f'Eliminazione completata: {filename}'

        db.session.commit()

        flash(f'File rottura {filename} eliminato (incluse {num_rotture} rotture associate).', 'info')

    except Exception as e:
        db.session.rollback()
        # Trace errore
        trace_err = TraceElaborazioneFile(
            id_file=id,
            tipo_file='rotture',
            step='delete',
            stato='error',
            messaggio=f'Errore durante eliminazione: {str(e)}'
        )
        db.session.add(trace_err)
        db.session.commit()

        flash(f'Errore durante eliminazione: {e}', 'error')

    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/elabora', methods=['POST'])
@admin_required
def elabora(id):
    """Elabora un file rottura"""
    file_rottura = FileRottura.query.get_or_404(id)
    
    # Controlla stato
    if file_rottura.esito == 'Processato':
        flash('Il file Ã¨ giÃ  stato processato!', 'warning')
        return redirect(url_for('rotture.list'))
    
    # Controlla esistenza file
    if not os.path.exists(file_rottura.filepath):
        flash(f'File non trovato: {file_rottura.filepath}', 'error')
        file_rottura.esito = 'Errore'
        file_rottura.note = f"File non trovato al path: {file_rottura.filepath}"
        file_rottura.data_elaborazione = datetime.now()
        db.session.commit()
        return redirect(url_for('rotture.list'))
    
    # Elabora file
    success, message, num_rotture = elabora_file_rottura_completo(file_rottura)
    
    if success:
        # Sposta file in OUTPUT
        base_dir = current_app.config.get('BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
        output_dir = os.path.join(base_dir, 'OUTPUT', 'rotture')
        os.makedirs(output_dir, exist_ok=True)
        
        new_filepath = os.path.join(output_dir, file_rottura.filename)
        
        try:
            # Usa shutil.move invece di os.rename per cross-device compatibility
            import shutil
            shutil.move(file_rottura.filepath, new_filepath)
            
            # Aggiorna record
            file_rottura.filepath = new_filepath
            file_rottura.esito = 'Processato'
            file_rottura.data_elaborazione = datetime.now()
            file_rottura.note = f"Elaborate {num_rotture} rotture. {message}"
            db.session.commit()
            
            flash(f'File elaborato con successo! Elaborate {num_rotture} rotture.', 'success')
        except Exception as e:
            flash(f'Errore spostamento file: {e}', 'error')
            file_rottura.esito = 'Errore'
            file_rottura.note = f"Elaborazione OK ma errore spostamento file: {str(e)}"
            file_rottura.data_elaborazione = datetime.now()
            db.session.commit()
    else:
        # Elaborazione fallita
        file_rottura.esito = 'Errore'
        file_rottura.note = message
        file_rottura.data_elaborazione = datetime.now()
        db.session.commit()
        
        flash(f'Errore durante elaborazione: {message}', 'error')
    
    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/download')
@login_required
def download(id):
    """Download file rottura"""
    file_rottura = FileRottura.query.get_or_404(id)

    if not os.path.exists(file_rottura.filepath):
        flash('File non trovato!', 'error')
        return redirect(url_for('rotture.list'))

    return send_file(file_rottura.filepath, as_attachment=True, download_name=file_rottura.filename)


@rotture_bp.route('/sync')
@admin_required
def sync():
    """Sincronizza manualmente il database con il filesystem"""
    scan_rotture_folder()
    flash('Sincronizzazione completata!', 'success')
    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/elaborazioni')
@login_required
def elaborazioni_list(id):
    """Lista di tutte le elaborazioni per un file rottura specifico"""
    file_rottura = FileRottura.query.get_or_404(id)

    # Recupera tutte le elaborazioni per questo file
    elaborazioni = TraceElab.query.filter_by(
        tipo_file='ROT',
        id_file=id
    ).order_by(TraceElab.created_at.desc()).all()

    return render_template('rotture/elaborazioni_list.html',
                         file_rottura=file_rottura,
                         elaborazioni=elaborazioni)


def elabora_file_rottura_completo(file_rottura):
    """Wrapper per chiamare la funzione di elaborazione con i parametri corretti"""
    models_dict = {
        'Rottura': Rottura,
        'RotturaComponente': RotturaComponente,
        'Modello': Modello,
        'Componente': Componente,
        'UtenteRottura': UtenteRottura,
        'Rivenditore': Rivenditore,
        'TraceElab': TraceElab,
        'TraceElabDett': TraceElabDett
    }
    return _elabora_file_rottura_completo(file_rottura, db, current_user, current_app, models_dict)
