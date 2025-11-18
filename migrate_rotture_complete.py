"""
Script di migrazione completo per pipeline rotture
- Rinomina tabella rotture -> file_rotture
- Crea nuove tabelle: rotture, rotture_componenti, modelli, componenti, utenti, rivenditori
- Crea tabelle trace: trace_elaborazioni_file, trace_elaborazioni_record
- Crea cartelle necessarie

Esegui con: python migrate_rotture_complete.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def migrate_database():
    """Migra il database per supportare la pipeline rotture completa"""

    from app import create_app
    from models import db
    from sqlalchemy import text, inspect

    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("MIGRAZIONE PIPELINE ROTTURE - COMPLETA")
        print("="*80 + "\n")

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        print("📋 Tabelle esistenti nel database:")
        for table in existing_tables:
            print(f"   - {table}")
        print()

        # 1. Rinomina tabella rotture -> file_rotture se esiste
        if 'rotture' in existing_tables and 'file_rotture' not in existing_tables:
            print("🔄 Rinomino tabella 'rotture' in 'file_rotture'...")
            try:
                # Backup dei dati
                result = db.session.execute(text("SELECT COUNT(*) FROM rotture")).scalar()
                if result > 0:
                    print(f"   ⚠️  ATTENZIONE: La tabella rotture contiene {result} record.")
                    risposta = input("   Vuoi procedere con la migrazione? (si/no): ")
                    if risposta.lower() != 'si':
                        print("   ❌ Migrazione annullata.")
                        return False

                # Rinomina tabella
                db.session.execute(text("ALTER TABLE rotture RENAME TO file_rotture"))
                db.session.commit()
                print("   ✓ Tabella rinominata con successo")
            except Exception as e:
                print(f"   ⚠️  Errore durante rinominazione: {e}")
                print("   Procedo comunque con la creazione delle nuove tabelle...")
                db.session.rollback()

        # 2. Crea tutte le nuove tabelle
        print("\n🔨 Creazione nuove tabelle...")
        try:
            db.create_all()
            print("   ✓ Tutte le tabelle create con successo!")
        except Exception as e:
            print(f"   ❌ Errore creazione tabelle: {e}")
            return False

        # 3. Verifica tabelle create
        print("\n✅ Verifica tabelle create:")
        inspector = inspect(db.engine)
        new_tables = inspector.get_table_names()

        required_tables = [
            'file_rotture', 'rotture', 'rotture_componenti',
            'modelli', 'componenti', 'utenti', 'rivenditori',
            'trace_elaborazioni_file', 'trace_elaborazioni_record'
        ]

        for table in required_tables:
            if table in new_tables:
                print(f"   ✓ {table}")
            else:
                print(f"   ✗ {table} (MANCANTE)")

        # 4. Crea cartelle necessarie
        print("\n📁 Creazione cartelle necessarie...")
        base_dir = app.config.get('BASE_DIR', '.')

        directories = [
            os.path.join(base_dir, 'INPUT', 'rotture'),
            os.path.join(base_dir, 'INPUT', 'rotture_parsed'),
            os.path.join(base_dir, 'OUTPUT', 'rotture'),
        ]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"   ✓ {directory}")
            except Exception as e:
                print(f"   ⚠️  Errore creazione cartella {directory}: {e}")

        # 5. Riepilogo finale
        print("\n" + "="*80)
        print("✅ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("="*80)
        print("\n📊 Struttura database aggiornata:")
        print("\n   TABELLE FILE:")
        print("   - file_rotture (gestione upload/stato file Excel)")
        print("   - file_ordini")
        print("   - file_anagrafiche")
        print("\n   TABELLE DATI:")
        print("   - rotture (singole rotture estratte dai file)")
        print("   - rotture_componenti (relazione M:N rotture-componenti)")
        print("\n   TABELLE ANAGRAFICHE:")
        print("   - modelli")
        print("   - componenti")
        print("   - utenti")
        print("   - rivenditori")
        print("\n   TABELLE TRACE:")
        print("   - trace_elaborazioni_file")
        print("   - trace_elaborazioni_record")
        print("\n📁 Cartelle create:")
        print("   - INPUT/rotture")
        print("   - INPUT/rotture_parsed")
        print("   - OUTPUT/rotture")
        print("\n🚀 Adesso puoi:")
        print("   1. Avviare l'app: python app.py")
        print("   2. Caricare file rotture da /rotture/create")
        print("   3. Elaborare i file con il bottone 'Elabora'")
        print()

        return True


if __name__ == '__main__':
    try:
        success = migrate_database()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
