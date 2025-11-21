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
from utils.db_log import log_session  # Sessione separata per log (AUTONOMOUS TRANSACTION)
import os
import csv
import random
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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

# ============================================================================
# FUNZIONI HELPER PER ELABORAZIONE
# ============================================================================

def normalize_code(code):
    """
    Normalizza un codice rimuovendo spazi, punteggiatura e convertendo in minuscolo
    """
    if not code:
        return ''
    return re.sub(r'[^a-z0-9]', '', str(code).lower())


def genera_tsv_simulato_rotture(file_rottura_id):
    """
    Genera un file TSV simulato per testing della pipeline rotture.
    Usa modelli ESISTENTI dalla tabella modelli.

    Una rottura = 1 modello + 0-6 componenti sostituiti

    Campi TSV (principali):
    - prot (protocollo univoco)
    - cod_modello
    - cod_componente (può essere vuoto - rottura senza sostituzione)
    - cod_utente, pv_utente, comune_utente
    - cod_rivenditore, pv_rivenditore
    - C.A.T., flag_consumer, flag_da_fatturare
    - data_competenza, cod_matricola, cod_modello_fabbrica
    - data_acquisto, data_apertura
    - difetto, problema_segnalato, riparazione
    - qtà, gg_vita_prodotto
    - divisione, marca, desc_modello, produttore, famiglia, tipo

    Returns: filepath del TSV generato
    """
    base_dir = current_app.root_path
    parsed_dir = os.path.join(base_dir, 'INPUT', 'rotture_parsed')
    os.makedirs(parsed_dir, exist_ok=True)

    # Prendi modelli esistenti dal DB
    modelli_esistenti = db.session.query(Modello).limit(15).all()

    if not modelli_esistenti:
        logger.warning(f"[TSV SIMULATO ROT] Nessun modello disponibile nel DB")
        return None

    # Prendi componenti esistenti dal DB (se ci sono)
    componenti_esistenti = db.session.query(Componente).limit(20).all()

    # Genera dati simulati
    rows = []
    for i, modello in enumerate(modelli_esistenti, start=1):
        # Ogni modello genera 1-3 rotture
        num_rotture_per_modello = random.randint(1, 3)

        for j in range(num_rotture_per_modello):
            prot = f'PROT-{file_rottura_id}-{i:03d}-{j:02d}'

            # Numero di componenti sostituiti: 0-6
            num_componenti = random.randint(0, min(6, len(componenti_esistenti))) if componenti_esistenti else 0

            # Se 0 componenti → una sola riga con cod_componente vuoto
            # Se N componenti → N righe con stesso prot ma cod_componente diverso
            if num_componenti == 0:
                componenti_da_usare = [None]  # Una sola riga senza componente
            else:
                componenti_da_usare = random.sample(componenti_esistenti, num_componenti)

            for componente in componenti_da_usare:
                row = {
                    'prot': prot,
                    'cod_modello': modello.cod_modello,
                    'cod_componente': componente.cod_componente if componente else '',
                    'cod_utente': f'USER-{random.randint(1000, 9999)}',
                    'pv_utente': random.choice(['MI', 'RM', 'TO', 'NA', 'FI']),
                    'comune_utente': random.choice(['Milano', 'Roma', 'Torino', 'Napoli', 'Firenze']),
                    'cod_rivenditore': f'RIV-{random.randint(100, 999)}',
                    'pv_rivenditore': random.choice(['MI', 'RM', 'TO']),
                    'C.A.T.': f'CAT-{random.randint(1000, 9999)}',
                    'flag_consumer': random.choice(['S', 'N', '']),
                    'flag_da_fatturare': random.choice(['S', 'N', '']),
                    'data_competenza': f'2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
                    'cod_matricola': f'MAT-{random.randint(100000, 999999)}',
                    'cod_modello_fabbrica': f'FAB-{modello.cod_modello[:10]}-{random.randint(100, 999)}',
                    'data_acquisto': f'2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
                    'data_apertura': f'2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
                    'difetto': random.choice(['Non si accende', 'Rumore anomalo', 'Display rotto', 'Non raffredda', 'Perdita acqua']),
                    'problema_segnalato': random.choice(['Malfunzionamento', 'Difetto estetico', 'Rumore', 'Altro']),
                    'riparazione': random.choice(['Sostituzione componente', 'Regolazione', 'Pulizia', 'Riparazione']),
                    'qtà': random.randint(1, 3),
                    'gg_vita_prodotto': random.randint(30, 1095),  # da 1 mese a 3 anni
                    'divisione': modello.divisione or random.choice(['CLIMA', 'FREDDO', 'LAVAGGIO']),
                    'marca': modello.marca or 'HISENSE',
                    'desc_modello': modello.desc_modello or f'Modello {modello.cod_modello}',
                    'produttore': modello.produttore or 'HISENSE',
                    'famiglia': modello.famiglia or random.choice(['FAM_A', 'FAM_B', 'FAM_C']),
                    'tipo': modello.tipo or random.choice(['MONO', 'DUAL', 'MULTI'])
                }
                rows.append(row)

    # Scrivi TSV
    tsv_filename = f'rotture_{file_rottura_id}_parsed.tsv'
    tsv_path = os.path.join(parsed_dir, tsv_filename)

    if rows:
        with open(tsv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"[TSV SIMULATO ROT] Generato: {tsv_path} ({len(rows)} righe, {len(set(r['prot'] for r in rows))} rotture)")
    else:
        logger.warning(f"[TSV SIMULATO ROT] Nessun dato generato per file_rottura {file_rottura_id}")

    return tsv_path if rows else None


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

            # Controlla se il file è già nel database (per filepath O filename)
            existing = FileRottura.query.filter(
                (FileRottura.filepath == filepath) | (FileRottura.filename == filename)
            ).first()

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
                logger.info(f"[SYNC INPUT] Aggiunto: {filepath}")
            else:
                logger.info(f"[SYNC INPUT] Saltato (già presente): {filename}")

    # Scansiona OUTPUT/rotture/
    output_dir = os.path.join(base_dir, 'OUTPUT', 'rotture')
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if not filename.lower().endswith(('.xls', '.xlsx')):
                continue

            filepath = os.path.join(output_dir, filename)
            files_trovati.add(filepath)

            # Controlla se il file è già nel database (per filepath O filename)
            existing = FileRottura.query.filter(
                (FileRottura.filepath == filepath) | (FileRottura.filename == filename)
            ).first()

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
                logger.info(f"[SYNC OUTPUT] Aggiunto: {filepath}")
            else:
                logger.info(f"[SYNC OUTPUT] Saltato (già presente): {filename}")

    # Rimuovi record orfani (file nel DB ma non nel filesystem)
    num_rimossi = 0
    tutte_rotture = FileRottura.query.all()
    for rottura in tutte_rotture:
        if rottura.filepath not in files_trovati:
            logger.info(f"[SYNC] Rimosso record orfano: {rottura.filepath}")
            db.session.delete(rottura)
            num_rimossi += 1

    # Commit con gestione errori
    try:
        db.session.commit()
        logger.info(f"[SYNC] Completata: {len(files_trovati)} file, {num_rimossi} orfani rimossi")
    except Exception as e:
        db.session.rollback()
        logger.error(f"[SYNC] Errore durante commit: {str(e)}")
        raise

        

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
        # Permetti modifica di tutti i campi, anche per file processati
        rottura.data_acquisizione = form.data_acquisizione.data
        if form.data_elaborazione.data:
            rottura.data_elaborazione = datetime.combine(form.data_elaborazione.data, datetime.min.time())
        rottura.esito = form.esito.data
        rottura.note = form.note.data
        rottura.updated_at = datetime.utcnow()
        rottura.updated_by = current_user.id

        db.session.commit()
        flash(f'File rottura aggiornato!', 'success')
        return redirect(url_for('rotture.list'))

    return render_template('rotture/edit.html', form=form, rottura=rottura)




@rotture_bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """
    Elimina un file rottura con cascade.

    Cancella:
    - File_rotture
    - Rotture
    - Rotture_componenti

    NON cancella:
    - Modelli (rimangono nel DB)
    - Componenti (rimangono nel DB)
    - Utenti_rotture (rimangono nel DB)
    - Rivenditori (rimangono nel DB)
    """
    file_rottura = FileRottura.query.get_or_404(id)
    filename = file_rottura.filename

    # Genera id_elab per trace (LOG SESSION - AUTONOMOUS)
    result = db.session.execute(db.text("SELECT nextval('seq_id_elab')"))
    id_elab = result.scalar()

    try:
        # Crea trace START (LOG SESSION)
        trace_start = TraceElab(
            id_elab=id_elab,
            id_file=id,
            tipo_file='ROT',
            step='DELETE_START',
            stato='OK',
            messaggio=f'Inizio eliminazione file {filename}'
        )
        log_session.add(trace_start)
        log_session.commit()  # ← AUTONOMOUS: Commit immediato
        id_trace = trace_start.id_trace

        # STEP 1: Elimina rotture_componenti associate
        rotture_ids = [r.id_rottura for r in Rottura.query.filter_by(id_file_rotture=id).all()]
        num_comp = 0
        if rotture_ids:
            num_comp = RotturaComponente.query.filter(RotturaComponente.id_rottura.in_(rotture_ids)).delete(synchronize_session=False)
            trace_rec = TraceElabDett(
                id_trace=id_trace,
                record_pos=0,
                record_data={'tipo': 'DELETE_ROTTURE_COMPONENTI', 'num_rotture': len(rotture_ids), 'num_componenti': num_comp},
                messaggio=f'Eliminati {num_comp} record rotture_componenti per {len(rotture_ids)} rotture',
                stato='OK'
            )
            log_session.add(trace_rec)
            log_session.commit()  # ← AUTONOMOUS

        # STEP 2: Elimina rotture
        num_rotture = Rottura.query.filter_by(id_file_rotture=id).delete()
        if num_rotture > 0:
            trace_rec = TraceElabDett(
                id_trace=id_trace,
                record_pos=0,
                record_data={'tipo': 'DELETE_ROTTURE', 'num': num_rotture},
                messaggio=f'Eliminati {num_rotture} record rotture',
                stato='OK'
            )
            log_session.add(trace_rec)
            log_session.commit()  # ← AUTONOMOUS

        # STEP 3: Elimina file_rotture dal DB
        db.session.delete(file_rottura)
        db.session.commit()

        logger.info(f"[DELETE ROT] Eliminato file_rotture {id}, {num_rotture} rotture, {num_comp} componenti")

        # STEP 4: Elimina file fisico
        if os.path.exists(file_rottura.filepath):
            try:
                os.remove(file_rottura.filepath)
                trace_rec = TraceElabDett(
                    id_trace=id_trace,
                    record_pos=0,
                    record_data={'tipo': 'DELETE_FILE', 'path': file_rottura.filepath},
                    messaggio=f'File fisico eliminato: {file_rottura.filepath}',
                    stato='OK'
                )
                log_session.add(trace_rec)
                log_session.commit()  # ← AUTONOMOUS
                logger.info(f"[DELETE ROT] Eliminato file fisico: {file_rottura.filepath}")
            except Exception as e:
                logger.warning(f"[DELETE ROT] Errore eliminazione file fisico: {str(e)}")
                trace_rec = TraceElabDett(
                    id_trace=id_trace,
                    record_pos=0,
                    record_data={'tipo': 'DELETE_FILE', 'path': file_rottura.filepath},
                    messaggio=f'Errore eliminazione file fisico: {str(e)}',
                    stato='WARN'
                )
                log_session.add(trace_rec)
                log_session.commit()  # ← AUTONOMOUS
                flash(f'File rottura eliminato dal DB. Errore eliminazione file fisico: {e}', 'warning')

        # Trace END con successo (LOG SESSION)
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=id,
            tipo_file='ROT',
            step='DELETE_END',
            stato='OK',
            messaggio=f'Eliminazione completata: {filename}',
            righe_totali=num_rotture,
            righe_ok=num_rotture,
            righe_errore=0,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS

        flash(f'✅ File rottura {filename} eliminato con successo. '
              f'({num_rotture} rotture, {num_comp} componenti rimossi)', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"[DELETE ROT] Errore durante eliminazione: {str(e)}")

        # Trace END con errore (LOG SESSION)
        trace_end = TraceElab(
            id_elab=id_elab,
            id_file=id,
            tipo_file='ROT',
            step='DELETE_END',
            stato='KO',
            messaggio=f'Errore durante eliminazione: {str(e)}',
            righe_totali=0,
            righe_ok=0,
            righe_errore=1,
            righe_warning=0
        )
        log_session.add(trace_end)
        log_session.commit()  # ← AUTONOMOUS

        flash(f'❌ Errore durante eliminazione: {e}', 'danger')

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
        file_rottura.updated_at = datetime.utcnow()
        file_rottura.updated_by = current_user.id
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
            file_rottura.updated_at = datetime.utcnow()
            file_rottura.updated_by = current_user.id
            db.session.commit()
            
            flash(f'File elaborato con successo! Elaborate {num_rotture} rotture.', 'success')
        except Exception as e:
            flash(f'Errore spostamento file: {e}', 'error')
            file_rottura.esito = 'Errore'
            file_rottura.note = f"Elaborazione OK ma errore spostamento file: {str(e)}"
            file_rottura.data_elaborazione = datetime.now()
            file_rottura.updated_at = datetime.utcnow()
            file_rottura.updated_by = current_user.id
            db.session.commit()
    else:
        # Elaborazione fallita
        file_rottura.esito = 'Errore'
        file_rottura.note = message
        file_rottura.data_elaborazione = datetime.now()
        file_rottura.updated_at = datetime.utcnow()
        file_rottura.updated_by = current_user.id
        db.session.commit()
        
        flash(f'Errore durante elaborazione: {message}', 'error')

    # Redirect alla pagina storico elaborazioni
    return redirect(url_for('rotture.elaborazioni_list', id=id))


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
    """
    Sincronizza manualmente il database con il filesystem.

    Comportamento:
    - Scansiona INPUT/rotture/ e OUTPUT/rotture/
    - Aggiunge file nuovi (saltando duplicati)
    - Rimuove record orfani (file eliminati dal filesystem)
    - Logga tutte le operazioni
    """
    try:
        scan_rotture_folder()
        flash('Sincronizzazione completata! Controlla i log per i dettagli.', 'success')
    except Exception as e:
        logger.error(f"[SYNC] Errore sincronizzazione: {str(e)}")
        flash(f'Errore durante sincronizzazione: {str(e)}', 'danger')

    return redirect(url_for('rotture.list'))


@rotture_bp.route('/<int:id>/elaborazioni')
@login_required
def elaborazioni_list(id):
    """Lista storico elaborazioni raggruppate per id_elab"""
    file_rottura = FileRottura.query.get_or_404(id)

    # Recupera tutti i record END (contengono le metriche)
    elaborazioni_end = TraceElab.query.filter_by(
        tipo_file='ROT',
        id_file=id,
        step='END'
    ).order_by(TraceElab.created_at.desc()).all()

    # Per ogni END, trova il corrispondente START
    elaborazioni = []
    for elab_end in elaborazioni_end:
        elab_start = TraceElab.query.filter_by(
            id_elab=elab_end.id_elab,
            tipo_file='ROT',
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

    return render_template('rotture/elaborazioni_list.html',
                         file_rottura=file_rottura,
                         elaborazioni=elaborazioni)


@rotture_bp.route('/<int:id>/elaborazioni/<int:id_elab>/dettaglio')
@login_required
def elaborazione_dettaglio(id, id_elab):
    """Mostra i dettagli di una specifica elaborazione"""
    file_rottura = FileRottura.query.get_or_404(id)

    # Trova tutti i trace di questa elaborazione
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ROT',
        id_file=id
    ).order_by(TraceElab.created_at).all()

    if not traces:
        flash('Elaborazione non trovata', 'warning')
        return redirect(url_for('rotture.elaborazioni_list', id=id))

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

    return render_template('rotture/elaborazione_dettaglio_modal.html',
                         file_rottura=file_rottura,
                         trace_start=trace_start,
                         trace_end=trace_end,
                         dettagli=dettagli,
                         stato_filter=stato_filter)


@rotture_bp.route('/<int:id>/elaborazioni/<int:id_elab>/export')
@login_required
def elaborazione_export(id, id_elab):
    """Esporta i dettagli di un'elaborazione in CSV"""
    import csv
    import io
    from flask import Response

    file_rottura = FileRottura.query.get_or_404(id)

    # Trova tutti i traces di questa elaborazione
    traces = TraceElab.query.filter_by(
        id_elab=id_elab,
        tipo_file='ROT',
        id_file=id
    ).all()

    if not traces:
        flash('Elaborazione non trovata', 'warning')
        return redirect(url_for('rotture.elaborazioni_list', id=id))

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
    filename = f"elaborazione_{file_rottura.filename}_elab{id_elab}_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


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
    return _elabora_file_rottura_completo(file_rottura, db, current_user, current_app, models_dict, log_session)
