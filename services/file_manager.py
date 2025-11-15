"""
Gestione spostamento file e aggiornamento stati
"""
import os
import shutil
from datetime import datetime
from models import db, FileOrdini, TraceElaborazioneFile


def _trace_step(id_file_ordine, step, stato, messaggio=None):
    """Traccia uno step dell'elaborazione"""
    trace = TraceElaborazioneFile(
        id_file_ordine=id_file_ordine,
        tipo_file='ord',
        step=step,
        stato=stato,
        messaggio=messaggio,
        timestamp=datetime.utcnow()
    )
    db.session.add(trace)
    db.session.commit()
    return trace.id


def completa_elaborazione_ordine(id_file_ordine, input_path, output_path):
    """
    Completa elaborazione con successo:
    - Sposta file INPUT/po/{anno}/{file}.xlsx → OUTPUT/po/{anno}/{file}.xlsx
    - Aggiorna file_ordini.esito = 'Elaborato'
    - Aggiorna file_ordini.data_elaborazione = NOW()
    - Traccia in trace_elaborazioni_file

    Args:
        id_file_ordine: ID del record FileOrdini
        input_path: Percorso file in INPUT
        output_path: Percorso destinazione in OUTPUT

    Returns:
        tuple: (success: bool, error_msg: str|None)
    """
    try:
        _trace_step(id_file_ordine, 'spostamento', 'success', f'Inizio spostamento {os.path.basename(input_path)}')

        # Verifica esistenza file sorgente
        if not os.path.exists(input_path):
            error_msg = f'File sorgente non trovato: {input_path}'
            _trace_step(id_file_ordine, 'spostamento', 'error', error_msg)
            return False, error_msg

        # Crea directory di destinazione se non esiste
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Sposta file (usa shutil.move per gestire filesystem diversi)
        shutil.move(input_path, output_path)

        # Aggiorna record database
        file_ordine = FileOrdini.query.get(id_file_ordine)
        if not file_ordine:
            error_msg = f'Record FileOrdini {id_file_ordine} non trovato'
            _trace_step(id_file_ordine, 'spostamento', 'error', error_msg)
            return False, error_msg

        file_ordine.esito = 'Elaborato'
        file_ordine.filepath = output_path
        file_ordine.data_elaborazione = datetime.utcnow()
        file_ordine.note = None  # Pulisci eventuali note di errori precedenti
        file_ordine.updated_at = datetime.utcnow()

        db.session.commit()

        _trace_step(id_file_ordine, 'completato', 'success', f'File spostato in OUTPUT, stato=Elaborato')

        return True, None

    except Exception as e:
        db.session.rollback()
        error_msg = f'Errore spostamento file: {str(e)}'
        _trace_step(id_file_ordine, 'spostamento', 'error', error_msg)
        return False, error_msg


def gestisci_errore_elaborazione(id_file_ordine, error_msg, fase_errore='elaborazione'):
    """
    Gestisce errore elaborazione:
    - File rimane in INPUT/
    - Aggiorna file_ordini.esito = 'Errore'
    - Aggiorna file_ordini.note = error_msg
    - Traccia errore

    Args:
        id_file_ordine: ID del record FileOrdini
        error_msg: Messaggio di errore
        fase_errore: Fase in cui si è verificato l'errore

    Returns:
        tuple: (success: bool, None)
    """
    try:
        file_ordine = FileOrdini.query.get(id_file_ordine)
        if not file_ordine:
            return False, None

        file_ordine.esito = 'Errore'
        file_ordine.note = f'[{fase_errore}] {error_msg}'
        file_ordine.updated_at = datetime.utcnow()

        db.session.commit()

        _trace_step(id_file_ordine, 'errore', 'error', f'Elaborazione fallita: {error_msg}')

        return True, None

    except Exception as e:
        db.session.rollback()
        print(f'Errore durante gestione errore elaborazione: {str(e)}')
        return False, None


def cancella_file_ordine(id_file_ordine):
    """
    Cancella file ordine:
    - Elimina file dal filesystem
    - Rimuove record file_ordini (CASCADE elimina ordini e trace)
    - NON rimuove controparti e modelli

    Args:
        id_file_ordine: ID del record FileOrdini

    Returns:
        tuple: (success: bool, error_msg: str|None)
    """
    try:
        file_ordine = FileOrdini.query.get(id_file_ordine)
        if not file_ordine:
            return False, f'Record FileOrdini {id_file_ordine} non trovato'

        # Elimina file se esiste
        if file_ordine.filepath and os.path.exists(file_ordine.filepath):
            os.remove(file_ordine.filepath)

        # Elimina record (CASCADE rimuove ordini e trace)
        db.session.delete(file_ordine)
        db.session.commit()

        return True, None

    except Exception as e:
        db.session.rollback()
        error_msg = f'Errore cancellazione file ordine: {str(e)}'
        return False, error_msg
