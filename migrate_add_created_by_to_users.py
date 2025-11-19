#!/usr/bin/env python3
"""
Script per aggiornare la tabella users aggiungendo la colonna created_by
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import DevelopmentConfig, ProductionConfig
from models import db

# Crea istanza app usando factory pattern
app = create_app(DevelopmentConfig)


def column_exists(engine, table_name, column_name):
    """Verifica se una colonna esiste in una tabella"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)


def update_users_table():
    """Aggiorna la tabella users aggiungendo created_by se mancante"""
    print("=" * 80)
    print("  AGGIORNAMENTO TABELLA USERS")
    print("=" * 80)

    with app.app_context():
        engine = db.engine
        db_type = engine.dialect.name

        print(f"\nDatabase Type: {db_type}")

        # Verifica se la colonna created_by esiste
        if column_exists(engine, 'users', 'created_by'):
            print("\n✓ La colonna 'created_by' esiste già nella tabella 'users'")
            print("  Nessuna modifica necessaria.\n")
            return True

        print("\n→ Aggiunta colonna 'created_by' alla tabella 'users'")

        try:
            with engine.begin() as conn:
                if db_type == 'sqlite':
                    # SQLite non supporta ALTER COLUMN con DEFAULT, quindi usa un approccio diverso
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN created_by INTEGER NOT NULL DEFAULT 0"
                    ))
                elif db_type == 'postgresql':
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN created_by INTEGER NOT NULL DEFAULT 0"
                    ))
                else:
                    print(f"\n✗ Database {db_type} non supportato")
                    return False

            print("  ✓ Colonna 'created_by' aggiunta con successo\n")

            # Verifica
            if column_exists(engine, 'users', 'created_by'):
                print("✓ VERIFICA RIUSCITA: La colonna è stata aggiunta correttamente\n")
                return True
            else:
                print("✗ ERRORE: La colonna non è stata aggiunta\n")
                return False

        except Exception as e:
            print(f"\n✗ ERRORE durante l'aggiornamento: {e}\n")
            return False


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python migrate_add_created_by_to_users.py

Descrizione:
  Aggiunge la colonna 'created_by' alla tabella 'users' se non esiste.
  Questa colonna è necessaria per tracciare chi ha creato ciascun utente.
""")
        sys.exit(0)

    try:
        success = update_users_table()
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n✗ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
