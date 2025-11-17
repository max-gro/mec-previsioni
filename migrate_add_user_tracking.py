#!/usr/bin/env python3
"""
Script di migrazione per aggiungere campi created_by e updated_by

Aggiunge i campi di tracking utente a:
- anagrafiche_file.created_by, updated_by
- rotture.created_by, updated_by
- ordini_acquisto.created_by, updated_by

IMPORTANTE: Questa è una migrazione SAFE - aggiunge solo colonne nullable
"""

import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, inspect, text, MetaData, Column, Integer, ForeignKey
from app import app
from models import db

def backup_database():
    """Crea backup del database SQLite"""
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///'):
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_path)
            print(f"✓ Backup database creato: {backup_path}")
            return backup_path
    return None

def column_exists(inspector, table_name, column_name):
    """Verifica se una colonna esiste in una tabella"""
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)

def migrate_postgresql(engine):
    """Migrazione per PostgreSQL"""
    print("\n🐘 Database PostgreSQL rilevato")
    print("\nEsecuzione migrazione...")

    with engine.begin() as conn:
        tables = ['anagrafiche_file', 'rotture', 'ordini_acquisto']

        for table in tables:
            print(f"\n📌 Tabella: {table}")

            # Aggiungi created_by
            if not column_exists(inspect(engine), table, 'created_by'):
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ADD COLUMN created_by INTEGER REFERENCES users(id_user)
                    """))
                    print(f"  ✓ Aggiunta colonna {table}.created_by")
                except Exception as e:
                    print(f"  ⚠ Errore aggiunta {table}.created_by: {e}")
            else:
                print(f"  ⚠ {table}.created_by già esistente")

            # Aggiungi updated_by
            if not column_exists(inspect(engine), table, 'updated_by'):
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ADD COLUMN updated_by INTEGER REFERENCES users(id_user)
                    """))
                    print(f"  ✓ Aggiunta colonna {table}.updated_by")
                except Exception as e:
                    print(f"  ⚠ Errore aggiunta {table}.updated_by: {e}")
            else:
                print(f"  ⚠ {table}.updated_by già esistente")

            # Crea indici
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_created_by ON {table}(created_by)"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_updated_by ON {table}(updated_by)"))
                print(f"  ✓ Indici creati per {table}")
            except Exception as e:
                print(f"  ⚠ Errore creazione indici: {e}")

    return True

def migrate_sqlite(engine):
    """Migrazione per SQLite"""
    print("\n💾 Database SQLite rilevato")
    print("\n⚠ ATTENZIONE: SQLite ha limitazioni su ALTER TABLE!")
    print("Questa migrazione userà ADD COLUMN (supportato da SQLite 3.2+)\n")

    with engine.begin() as conn:
        tables = ['anagrafiche_file', 'rotture', 'ordini_acquisto']

        for table in tables:
            print(f"\n📌 Tabella: {table}")

            # Aggiungi created_by
            if not column_exists(inspect(engine), table, 'created_by'):
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ADD COLUMN created_by INTEGER REFERENCES users(id_user)
                    """))
                    print(f"  ✓ Aggiunta colonna {table}.created_by")
                except Exception as e:
                    print(f"  ⚠ Errore aggiunta {table}.created_by: {e}")
            else:
                print(f"  ⚠ {table}.created_by già esistente")

            # Aggiungi updated_by
            if not column_exists(inspect(engine), table, 'updated_by'):
                try:
                    conn.execute(text(f"""
                        ALTER TABLE {table}
                        ADD COLUMN updated_by INTEGER REFERENCES users(id_user)
                    """))
                    print(f"  ✓ Aggiunta colonna {table}.updated_by")
                except Exception as e:
                    print(f"  ⚠ Errore aggiunta {table}.updated_by: {e}")
            else:
                print(f"  ⚠ {table}.updated_by già esistente")

            # SQLite: gli indici vanno creati separatamente
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_created_by ON {table}(created_by)"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_updated_by ON {table}(updated_by)"))
                print(f"  ✓ Indici creati per {table}")
            except Exception as e:
                print(f"  ⚠ Errore creazione indici: {e}")

    return True

def verify_migration(engine):
    """Verifica che la migrazione sia andata a buon fine"""
    print("\n📌 Verifica migrazione...")

    inspector = inspect(engine)
    tables_columns = [
        ('anagrafiche_file', 'created_by'),
        ('anagrafiche_file', 'updated_by'),
        ('rotture', 'created_by'),
        ('rotture', 'updated_by'),
        ('ordini_acquisto', 'created_by'),
        ('ordini_acquisto', 'updated_by'),
    ]

    all_ok = True

    print("\n📊 RIEPILOGO COLONNE:")
    print("━" * 60)

    for table, column in tables_columns:
        exists = column_exists(inspector, table, column)
        status = "✓" if exists else "✗"
        print(f"{status} {table}.{column}: {'OK' if exists else 'MANCANTE'}")
        if not exists:
            all_ok = False

    print("━" * 60)

    if all_ok:
        print("\n✅ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("\nCampi aggiunti:")
        print("  • anagrafiche_file.created_by → users.id_user (FK)")
        print("  • anagrafiche_file.updated_by → users.id_user (FK)")
        print("  • rotture.created_by → users.id_user (FK)")
        print("  • rotture.updated_by → users.id_user (FK)")
        print("  • ordini_acquisto.created_by → users.id_user (FK)")
        print("  • ordini_acquisto.updated_by → users.id_user (FK)")
        print("\n📝 NOTA: I campi sono nullable, i record esistenti avranno NULL.")
        print()
    else:
        print("\n⚠ ATTENZIONE: Alcuni campi non sono stati aggiunti correttamente!")

    return all_ok

def populate_existing_records(engine, admin_user_id=1):
    """Popola i campi created_by/updated_by per record esistenti"""
    print(f"\n📝 Popolamento campi per record esistenti (user_id={admin_user_id})...")

    with engine.begin() as conn:
        tables = ['anagrafiche_file', 'rotture', 'ordini_acquisto']

        for table in tables:
            try:
                result = conn.execute(text(f"""
                    UPDATE {table}
                    SET created_by = {admin_user_id}, updated_by = {admin_user_id}
                    WHERE created_by IS NULL
                """))
                print(f"  ✓ {table}: {result.rowcount} record aggiornati")
            except Exception as e:
                print(f"  ⚠ Errore aggiornamento {table}: {e}")

def main():
    """Funzione principale di migrazione"""
    print("\n" + "="*80)
    print("MIGRAZIONE: Aggiunta campi created_by e updated_by")
    print("="*80)

    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python migrate_add_user_tracking.py [opzioni]

Opzioni:
  -y, --yes           Esegui senza chiedere conferma
  --populate=USER_ID  Popola record esistenti con USER_ID (default: 1=admin)
  --verify-only       Solo verifica senza eseguire migrazione
  -h, --help          Mostra questo messaggio

Descrizione:
  Aggiunge i campi created_by e updated_by (FK a users.id_user) a:
  - anagrafiche_file
  - rotture
  - ordini_acquisto

Nota:
  Questa è una migrazione SAFE - aggiunge solo colonne nullable.
  Non modifica dati esistenti.
""")
        return 0

    with app.app_context():
        engine = db.engine
        db_type = engine.dialect.name

        print(f"\nDatabase: {db_type}")
        print(f"URI: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

        # Solo verifica
        if '--verify-only' in sys.argv:
            verify_migration(engine)
            return 0

        # Richiedi conferma
        if '--yes' not in sys.argv and '-y' not in sys.argv:
            print("⚠ Questa operazione aggiungerà nuove colonne al database.")
            risposta = input("Procedere? [y/N]: ")
            if risposta.lower() != 'y':
                print("Migrazione annullata.")
                return 0

        # Backup
        backup_path = backup_database()

        try:
            # Esegui migrazione in base al database
            if db_type == 'postgresql':
                success = migrate_postgresql(engine)
            elif db_type == 'sqlite':
                success = migrate_sqlite(engine)
            else:
                print(f"✗ ERRORE: Database {db_type} non supportato!")
                return 1

            if not success:
                return 1

            # Verifica finale
            success = verify_migration(engine)

            # Popola record esistenti se richiesto
            populate_arg = [arg for arg in sys.argv if arg.startswith('--populate=')]
            if populate_arg:
                user_id = int(populate_arg[0].split('=')[1])
                populate_existing_records(engine, user_id)
            elif '--populate' in sys.argv:
                populate_existing_records(engine, 1)  # Default: admin

            if backup_path:
                print(f"\nBackup disponibile in: {backup_path}")

            return 0 if success else 1

        except Exception as e:
            print(f"\n✗ ERRORE durante la migrazione: {e}")
            if backup_path:
                print(f"È possibile ripristinare il backup da: {backup_path}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == '__main__':
    sys.exit(main())
