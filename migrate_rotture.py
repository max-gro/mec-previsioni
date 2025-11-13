"""
Script di migrazione database: Converte tabella rotture da eventi a file
Esegui con: python migrate_rotture.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def migrate_database():
    """Migra il database convertendo la struttura della tabella rotture"""
    
    from app import create_app
    from models import db
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("MIGRAZIONE TABELLA ROTTURE")
        print("="*60 + "\n")
        
        # Backup della tabella esistente (opzionale)
        try:
            result = db.session.execute(text("SELECT COUNT(*) FROM rotture")).scalar()
            if result > 0:
                print(f"⚠️  ATTENZIONE: La tabella rotture contiene {result} record.")
                risposta = input("Vuoi procedere con la migrazione? Tutti i dati saranno persi! (si/no): ")
                if risposta.lower() != 'si':
                    print("❌ Migrazione annullata.")
                    return False
        except:
            pass
        
        # DROP della vecchia tabella
        try:
            db.session.execute(text('DROP TABLE IF EXISTS rotture'))
            db.session.commit()
            print("✓ Vecchia tabella rotture eliminata")
        except Exception as e:
            print(f"⚠️  Errore DROP tabella: {e}")
        
        # Ricrea tutte le tabelle
        try:
            db.create_all()
            print("✓ Nuova tabella rotture creata con successo!")
        except Exception as e:
            print(f"❌ Errore creazione tabella: {e}")
            return False
        
        # Crea le cartelle necessarie
        base_dir = app.config.get('BASE_DIR', '.')
        
        directories = [
            os.path.join(base_dir, 'INPUT', 'rotture'),
            os.path.join(base_dir, 'OUTPUT', 'rotture')
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✓ Cartella creata: {directory}")
            except Exception as e:
                print(f"⚠️  Errore creazione cartella {directory}: {e}")
        
        print("\n" + "="*60)
        print("Migrazione completata con successo!")
        print("="*60)
        print("\n✅ La tabella rotture è stata ricreata con la nuova struttura:")
        print("   - anno")
        print("   - filename")
        print("   - filepath")
        print("   - data_acquisizione")
        print("   - data_elaborazione")
        print("   - esito")
        print("   - note")
        print("\n📁 Cartelle create:")
        print("   - INPUT/rotture")
        print("   - OUTPUT/rotture")
        print("\nAdesso puoi avviare l'app con: python app.py")
        return True

if __name__ == '__main__':
    try:
        migrate_database()
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
