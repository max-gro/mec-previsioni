"""
TEMPORARY DEV ROUTE - Esegue migration per aggiungere STOCK al constraint
Da rimuovere dopo l'uso!
"""

from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

dev_migrate_bp = Blueprint('dev_migrate', __name__, url_prefix='/dev')

@dev_migrate_bp.route('/migrate-stock-constraint')
@login_required
def migrate_stock_constraint():
    """
    TEMPORARY: Esegue migration per aggiungere 'STOCK' al constraint tipo_file
    """
    # Solo admin può eseguire migration
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Accesso negato', 'error')
        return redirect(url_for('dashboard.index'))

    try:
        # SQL migration
        migration_sql = """
        -- Drop vecchio constraint
        ALTER TABLE trace_elab DROP CONSTRAINT IF EXISTS trace_elab_tipo_file_check;

        -- Aggiungi nuovo constraint con 'STOCK'
        ALTER TABLE trace_elab
        ADD CONSTRAINT trace_elab_tipo_file_check
        CHECK (tipo_file IN ('ORD', 'ANA', 'ROT', 'STOCK'));
        """

        db.session.execute(text(migration_sql))
        db.session.commit()

        logger.info("✅ Migration completata: trace_elab_tipo_file_check ora include 'STOCK'")
        flash('Migration completata! Il tipo STOCK è ora permesso in trace_elab', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Errore migration: {e}")
        flash(f'Errore durante migration: {str(e)}', 'error')

    return redirect(url_for('stock.index'))
