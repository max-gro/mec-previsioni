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
    
    print("\n" + "="*60)
    print("MIGRAZIONE TABELLA ROTTURE")
    print("="*60 + "\n")
    
    # Verifica dipendenze prima di importare app
    try:
        import pandas
        import openpyxl
        print("✓ pandas e openpyxl installati")
    except ImportError as e:
        print(f"❌ ERRORE: Dipendenza mancante: {e}")
        print("\nEsegui: pip install pandas openpyxl")
        return False
    
    # Ora importa l'app
    try:
        from app import create_app
        from models import db
        from sqlalchemy import text
    except ImportError as e:
        print(f"❌ ERRORE Import: {e}")
        print("\nVerifica che tutti i file del progetto siano presenti.")
        return False
    
    try:
        app = create_app()
    except Exception as e:
        print(f"❌ ERRORE creazione app: {e}")
        print("\nVerifica che forms.py contenga RotturaForm e RotturaEditForm")
        return False
    
    with app.app_context():
        # Backup della tabella esistente (opzionale)
        try:
            result = db.session.execute(text("SELECT COUNT(*) FROM rotture")).scalar()
            if result > 0:
                print(f"⚠️  ATTENZIONE: La tabella rotture contiene {result} record.")
                print("\nQuesti dati saranno PERSI durante la migrazione!")
                risposta = input("\nVuoi procedere? (scrivi 'SI' per confermare): ")
                if risposta.upper() != 'SI':
                    print("❌ Migrazione annullata dall'utente.")
                    return False
        except:
            print("✓ Tabella rotture non esiste ancora o è vuota")
        
        # DROP della vecchia tabella
        try:
            db.session.execute(text('DROP TABLE IF EXISTS rotture'))
            db.session.commit()
            print("✓ Vecchia tabella rotture eliminata")
        except Exception as e:
            print(f"⚠️  Avviso DROP tabella: {e}")
        
        # Ricrea tutte le tabelle
        try:
            db.create_all()
            print("✓ Nuova tabella rotture creata con successo!")
        except Exception as e:
            print(f"❌ Errore creazione tabella: {e}")
            db.session.rollback()
            return False
        
        # Crea le cartelle necessarie
        base_dir = app.config.get('BASE_DIR', os.path.dirname(__file__))
        
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
        print("✅ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("="*60)
        print("\n📊 Nuova struttura tabella rotture:")
        print("   ✓ anno (Integer)")
        print("   ✓ filename (String)")
        print("   ✓ filepath (String)")
        print("   ✓ data_acquisizione (Date)")
        print("   ✓ data_elaborazione (DateTime)")
        print("   ✓ esito (String)")
        print("   ✓ note (Text)")
        print("\n📁 Cartelle create:")
        print("   ✓ INPUT/rotture")
        print("   ✓ OUTPUT/rotture")
        print("\n🚀 Prossimi passi:")
        print("   1. Avvia l'app: python app.py")
        print("   2. Vai su: http://localhost:5010/rotture")
        print("   3. Carica un file Excel di test")
        print("\n" + "="*60 + "\n")
        return True

if __name__ == '__main__':
    try:
        success = migrate_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Migrazione interrotta dall'utente.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRORE IMPREVISTO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
