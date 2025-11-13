"""
Script di migrazione database: Aggiunge campo data_elaborazione
Esegui con: python migrate_ordini.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def migrate_database():
    """Migra il database aggiungendo il campo data_elaborazione"""
    
    from app import create_app
    from models import db
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        # Usa ALTER TABLE per aggiungere la nuova colonna
        try:
            # Per SQLite - usa db.session.execute invece di db.engine.execute
            db.session.execute(text('ALTER TABLE ordini_acquisto ADD COLUMN data_elaborazione DATETIME'))
            db.session.commit()
            print("✓ Campo 'data_elaborazione' aggiunto con successo!")
        except Exception as e:
            db.session.rollback()
            if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
                print("✓ Campo 'data_elaborazione' già esistente, nessuna azione necessaria.")
            else:
                print(f"✗ Errore durante la migrazione: {e}")
                print("\nSe il database è nuovo, esegui invece: python init_db.py")
                return False
        
        print("\n" + "="*60)
        print("Migrazione completata con successo!")
        print("="*60)
        print("\nAdesso puoi avviare l'app con: python app.py")
        return True

if __name__ == '__main__':
    try:
        migrate_database()
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


