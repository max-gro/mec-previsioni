
"""
Decoratori per Flask
"""

from functools import wraps
from flask import flash, redirect, url_for, render_template, current_app
from flask_login import current_user
from models import db
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator che richiede che l'utente sia autenticato e sia admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Devi effettuare il login per accedere a questa pagina.', 'warning')
            return redirect(url_for('auth.login'))

        if not current_user.is_admin():
            flash('Accesso negato: solo gli amministratori possono eseguire questa azione.', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function


def handle_errors(f):
    """
    Decorator per gestire automaticamente gli errori nelle route.
    Esegue rollback del database in caso di errore e mostra messaggio all'utente.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Rollback della sessione database
            db.session.rollback()

            # Log dell'errore con stack trace completo
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)

            # Mostra messaggio user-friendly
            flash(f'Si è verificato un errore: {str(e)}', 'danger')

            # In development, re-raise per vedere il traceback
            if current_app.config.get('DEBUG'):
                raise

            # In production, redirect alla home
            return redirect(url_for('index'))

    return decorated_function