"""
Migration: Aggiungi 'STOCK' al constraint tipo_file in trace_elab
Esegui con: python migrate_add_stock_tipo_file.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def run_migration():
    """Esegue la migration SQL per aggiungere 'STOCK' al constraint"""
    from app import create_app
    from models import db

    app = create_app()

    with app.app_context():
        print(f"\n{'='*80}")
        print(f"Migration: Aggiungi 'STOCK' a trace_elab_tipo_file_check")
        print(f"{'='*80}\n")
        print(f"URI: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

        # Leggi il file SQL
        sql_file = 'migrations_sql/add_stock_to_trace_tipo_file.sql'

        if not os.path.exists(sql_file):
            print(f"❌ File SQL non trovato: {sql_file}")
            return

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        print(f"📄 Esecuzione migration da: {sql_file}\n")

        try:
            # Esegui la migration
            db.session.execute(db.text(sql_content))
            db.session.commit()
            print("\n✅ Migration completata con successo!")
            print("   Il tipo_file 'STOCK' è ora permesso in trace_elab\n")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Errore durante la migration: {e}\n")
            raise

if __name__ == '__main__':
    run_migration()
