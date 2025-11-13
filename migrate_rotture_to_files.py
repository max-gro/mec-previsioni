"""
Script di migrazione database: Conversione tabella rotture da singole rotture a file Excel
Esegui con: python migrate_rotture_to_files.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def migrate_database():
    """Migra il database dalla vecchia struttura rotture alla nuova"""
    
    from app import create_app
    from models import db
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("MIGRAZIONE TABELLA ROTTURE")
        print("="*60)
        
        # ATTENZIONE: Questa migrazione ELIMINA TUTTI I DATI ESISTENTI
        # dalla tabella rotture perché la struttura è completamente diversa
        
        risposta = input("\n⚠️  ATTENZIONE: Questa migrazione ELIMINERÀ tutti i dati esistenti nella tabella 'rotture'.\n"
                        "La struttura passerà da 'singole rotture' a 'file Excel rotture'.\n"
                        "Vuoi continuare? (scrivi 'SI' per confermare): ")
        
        if risposta != 'SI':
            print("\n❌ Migrazione annullata.")
            return False
        
        try:
            # Step 1: Drop della vecchia tabella
            print("\n📌 Step 1: Elimino vecchia tabella rotture...")
            db.session.execute(text('DROP TABLE IF EXISTS rotture'))
            db.session.commit()
            print("✅ Tabella eliminata")
            
            # Step 2: Ricrea tabella con nuova struttura
            print("\n📌 Step 2: Creo nuova struttura tabella rotture...")
            db.create_all()
            print("✅ Nuova struttura creata")
            
            # Step 3: Verifica struttura
            print("\n📌 Step 3: Verifico nuova struttura...")
            result = db.session.execute(text("PRAGMA table_info(rotture)"))
            colonne = result.fetchall()
            
            print("\nColonne della nuova tabella 'rotture':")
            for col in colonne:
                print(f"  - {col[1]} ({col[2]})")
            
            # Verifica che ci siano i campi corretti
            nomi_colonne = [col[1] for col in colonne]
            campi_richiesti = ['id', 'anno', 'filename', 'filepath', 'data_acquisizione', 
                             'data_elaborazione', 'esito', 'note', 'created_at', 'updated_at']
            
            campi_mancanti = [c for c in campi_richiesti if c not in nomi_colonne]
            
            if campi_mancanti:
                print(f"\n❌ ERRORE: Campi mancanti: {campi_mancanti}")
                return False
            
            print("\n✅ Tutti i campi sono presenti")
            
            print("\n" + "="*60)
            print("MIGRAZIONE COMPLETATA CON SUCCESSO!")
            print("="*60)
            print("\nProssimi passi:")
            print("1. Copia i file template nella cartella templates/rotture/")
            print("2. Sostituisci routes/rotture.py con il nuovo file")
            print("3. Aggiorna forms.py con i nuovi form")
            print("4. Riavvia l'applicazione: python app.py")
            print("\nPuoi iniziare a caricare file Excel in 'Gestione Rotture'")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRORE durante la migrazione: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        success = migrate_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
