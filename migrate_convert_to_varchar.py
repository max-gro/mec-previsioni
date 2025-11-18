#!/usr/bin/env python3
"""
Script di migrazione per convertire campi codice da INTEGER a VARCHAR

Converte:
- controparti.cod_controparte: INTEGER → VARCHAR(50)
- modelli.cod_modello: INTEGER → VARCHAR(50)
- file_ordini.cod_seller: INTEGER → VARCHAR(50)
- file_ordini.cod_buyer: INTEGER → VARCHAR(50)
- ordini.cod_modello: INTEGER → VARCHAR(50)

IMPORTANTE: Crea un backup prima di eseguire!
"""

import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, inspect, text, MetaData
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
    else:
        print("⚠ ATTENZIONE: Per PostgreSQL, creare manualmente il backup con pg_dump!")
        print(f"  pg_dump -U username -d dbname > backup_{datetime.now().strftime('%Y%m%d')}.sql")
        return None

def table_exists(inspector, table_name):
    """Verifica se una tabella esiste"""
    return table_name in inspector.get_table_names()

def get_column_type(inspector, table_name, column_name):
    """Ottiene il tipo di una colonna"""
    columns = inspector.get_columns(table_name)
    for col in columns:
        if col['name'] == column_name:
            return str(col['type'])
    return None

def migrate_postgresql(engine):
    """Migrazione per PostgreSQL - esegue lo script SQL"""
    print("\n🐘 Database PostgreSQL rilevato")
    print("Per PostgreSQL, si raccomanda di usare lo script SQL:")
    print("  psql -U username -d dbname -f migrations_sql/convert_code_fields_to_varchar.sql")
    print()

    risposta = input("Vuoi procedere con la migrazione Python (meno testato)? [y/N]: ")
    if risposta.lower() != 'y':
        print("Migrazione annullata. Usa lo script SQL per maggiore affidabilità.")
        return False

    with engine.begin() as conn:
        print("\n📌 STEP 1: Rimozione foreign keys...")

        # Drop FK
        try:
            conn.execute(text("ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS file_ordini_cod_seller_fkey"))
            conn.execute(text("ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS file_ordini_cod_buyer_fkey"))
            conn.execute(text("ALTER TABLE ordini DROP CONSTRAINT IF EXISTS ordini_cod_modello_fkey"))
            print("  ✓ Foreign keys rimosse")
        except Exception as e:
            print(f"  ⚠ Errore rimozione FK: {e}")

        print("\n📌 STEP 2: Conversione colonne...")

        # Converti controparti.cod_controparte
        try:
            conn.execute(text("""
                ALTER TABLE controparti
                ALTER COLUMN cod_controparte TYPE VARCHAR(50)
                USING cod_controparte::TEXT
            """))
            print("  ✓ controparti.cod_controparte → VARCHAR(50)")
        except Exception as e:
            print(f"  ⚠ controparti.cod_controparte: {e}")

        # Converti modelli.cod_modello
        try:
            conn.execute(text("""
                ALTER TABLE modelli
                ALTER COLUMN cod_modello TYPE VARCHAR(50)
                USING cod_modello::TEXT
            """))
            print("  ✓ modelli.cod_modello → VARCHAR(50)")
        except Exception as e:
            print(f"  ⚠ modelli.cod_modello: {e}")

        # Converti file_ordini.cod_seller
        try:
            conn.execute(text("""
                ALTER TABLE file_ordini
                ALTER COLUMN cod_seller TYPE VARCHAR(50)
                USING cod_seller::TEXT
            """))
            print("  ✓ file_ordini.cod_seller → VARCHAR(50)")
        except Exception as e:
            print(f"  ⚠ file_ordini.cod_seller: {e}")

        # Converti file_ordini.cod_buyer
        try:
            conn.execute(text("""
                ALTER TABLE file_ordini
                ALTER COLUMN cod_buyer TYPE VARCHAR(50)
                USING cod_buyer::TEXT
            """))
            print("  ✓ file_ordini.cod_buyer → VARCHAR(50)")
        except Exception as e:
            print(f"  ⚠ file_ordini.cod_buyer: {e}")

        # Converti ordini.cod_modello
        try:
            conn.execute(text("""
                ALTER TABLE ordini
                ALTER COLUMN cod_modello TYPE VARCHAR(50)
                USING cod_modello::TEXT
            """))
            print("  ✓ ordini.cod_modello → VARCHAR(50)")
        except Exception as e:
            print(f"  ⚠ ordini.cod_modello: {e}")

        print("\n📌 STEP 3: Ricreazione foreign keys...")

        # Ricrea FK
        try:
            conn.execute(text("""
                ALTER TABLE file_ordini
                ADD CONSTRAINT file_ordini_cod_seller_fkey
                FOREIGN KEY (cod_seller) REFERENCES controparti(cod_controparte)
            """))
            print("  ✓ file_ordini.cod_seller → controparti.cod_controparte")
        except Exception as e:
            print(f"  ⚠ FK cod_seller: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE file_ordini
                ADD CONSTRAINT file_ordini_cod_buyer_fkey
                FOREIGN KEY (cod_buyer) REFERENCES controparti(cod_controparte)
            """))
            print("  ✓ file_ordini.cod_buyer → controparti.cod_controparte")
        except Exception as e:
            print(f"  ⚠ FK cod_buyer: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE ordini
                ADD CONSTRAINT ordini_cod_modello_fkey
                FOREIGN KEY (cod_modello) REFERENCES modelli(cod_modello)
            """))
            print("  ✓ ordini.cod_modello → modelli.cod_modello")
        except Exception as e:
            print(f"  ⚠ FK cod_modello: {e}")

    return True

def migrate_sqlite(engine):
    """
    Migrazione per SQLite
    SQLite non supporta ALTER COLUMN TYPE, quindi dobbiamo:
    1. Creare nuove tabelle con VARCHAR
    2. Copiare i dati
    3. Eliminare vecchie tabelle
    4. Rinominare nuove tabelle
    """
    print("\n💾 Database SQLite rilevato")
    print("\n⚠ ATTENZIONE: SQLite non supporta ALTER COLUMN TYPE!")
    print("La migrazione richiederà:")
    print("  1. Creazione tabelle temporanee")
    print("  2. Copia dati (INTEGER → VARCHAR)")
    print("  3. Sostituzione tabelle originali")
    print()

    risposta = input("Procedere? [y/N]: ")
    if risposta.lower() != 'y':
        print("Migrazione annullata.")
        return False

    with engine.begin() as conn:
        print("\n📌 STEP 1: Creazione tabelle temporanee...")

        # Tabella temporanea controparti
        conn.execute(text("""
            CREATE TABLE controparti_new (
                cod_controparte VARCHAR(50) PRIMARY KEY,
                controparte VARCHAR(200) NOT NULL,
                created_at TIMESTAMP,
                created_by INTEGER REFERENCES users(id_user),
                updated_at TIMESTAMP,
                updated_by INTEGER REFERENCES users(id_user)
            )
        """))
        print("  ✓ controparti_new creata")

        # Tabella temporanea modelli
        conn.execute(text("""
            CREATE TABLE modelli_new (
                cod_modello VARCHAR(50) PRIMARY KEY,
                cod_modello_norm VARCHAR(100) NOT NULL,
                cod_modello_fabbrica VARCHAR(100),
                nome_modello VARCHAR(200),
                nome_modello_it VARCHAR(200),
                divisione VARCHAR(100),
                marca VARCHAR(100),
                desc_modello TEXT,
                produttore VARCHAR(200),
                famiglia VARCHAR(100),
                tipo VARCHAR(100),
                created_at TIMESTAMP,
                created_by INTEGER REFERENCES users(id_user),
                updated_at TIMESTAMP,
                updated_by INTEGER REFERENCES users(id_user),
                updated_from VARCHAR(10)
            )
        """))
        print("  ✓ modelli_new creata")

        print("\n📌 STEP 2: Copia dati (INTEGER → VARCHAR)...")

        # Copia controparti
        conn.execute(text("""
            INSERT INTO controparti_new
            SELECT
                CAST(cod_controparte AS TEXT),
                controparte,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM controparti
        """))
        print("  ✓ Dati controparti copiati")

        # Copia modelli
        conn.execute(text("""
            INSERT INTO modelli_new
            SELECT
                CAST(cod_modello AS TEXT),
                cod_modello_norm,
                cod_modello_fabbrica,
                nome_modello,
                nome_modello_it,
                divisione,
                marca,
                desc_modello,
                produttore,
                famiglia,
                tipo,
                created_at,
                created_by,
                updated_at,
                updated_by,
                updated_from
            FROM modelli
        """))
        print("  ✓ Dati modelli copiati")

        print("\n📌 STEP 3: Aggiornamento file_ordini e ordini...")

        # Aggiorna file_ordini (converte FK)
        conn.execute(text("""
            UPDATE file_ordini
            SET
                cod_seller = CAST(cod_seller AS TEXT),
                cod_buyer = CAST(cod_buyer AS TEXT)
        """))
        print("  ✓ file_ordini.cod_seller/cod_buyer convertiti")

        # Aggiorna ordini (converte FK)
        conn.execute(text("""
            UPDATE ordini
            SET cod_modello = CAST(cod_modello AS TEXT)
        """))
        print("  ✓ ordini.cod_modello convertito")

        print("\n📌 STEP 4: Sostituzione tabelle...")

        # Elimina vecchie tabelle
        conn.execute(text("DROP TABLE controparti"))
        conn.execute(text("DROP TABLE modelli"))
        print("  ✓ Vecchie tabelle eliminate")

        # Rinomina nuove tabelle
        conn.execute(text("ALTER TABLE controparti_new RENAME TO controparti"))
        conn.execute(text("ALTER TABLE modelli_new RENAME TO modelli"))
        print("  ✓ Nuove tabelle rinominate")

        print("\n📌 STEP 5: Ricreazione foreign keys...")

        # SQLite: ricrea vincoli tramite ricostruzione tabelle file_ordini e ordini
        print("  ⚠ SQLite: i vincoli FK devono essere verificati manualmente")

    return True

def verify_migration(engine):
    """Verifica che la migrazione sia andata a buon fine"""
    print("\n📌 Verifica migrazione...")

    inspector = inspect(engine)

    tables_columns = [
        ('controparti', 'cod_controparte'),
        ('modelli', 'cod_modello'),
        ('file_ordini', 'cod_seller'),
        ('file_ordini', 'cod_buyer'),
        ('ordini', 'cod_modello'),
    ]

    all_ok = True

    print("\n📊 RIEPILOGO CONVERSIONI:")
    print("━" * 60)

    for table, column in tables_columns:
        if not table_exists(inspector, table):
            print(f"✗ Tabella {table} non trovata!")
            all_ok = False
            continue

        col_type = get_column_type(inspector, table, column)
        if col_type:
            is_varchar = 'VARCHAR' in col_type.upper() or 'CHAR' in col_type.upper() or 'TEXT' in col_type.upper()
            status = "✓" if is_varchar else "✗"
            print(f"{status} {table}.{column}: {col_type}")
            if not is_varchar:
                all_ok = False
        else:
            print(f"✗ {table}.{column}: colonna non trovata!")
            all_ok = False

    print("━" * 60)

    if all_ok:
        print("\n✅ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("\nI campi codice sono ora alfanumerici (VARCHAR):")
        print("  • controparti.cod_controparte")
        print("  • modelli.cod_modello")
        print("  • file_ordini.cod_seller")
        print("  • file_ordini.cod_buyer")
        print("  • ordini.cod_modello")
        print()
    else:
        print("\n⚠ ATTENZIONE: Alcuni campi non sono stati convertiti correttamente!")

    return all_ok

def main():
    """Funzione principale di migrazione"""
    print("\n" + "="*80)
    print("MIGRAZIONE: Conversione campi codice INTEGER → VARCHAR")
    print("="*80)

    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python migrate_convert_to_varchar.py [opzioni]

Opzioni:
  -y, --yes       Esegui senza chiedere conferma
  --verify-only   Solo verifica senza eseguire migrazione
  -h, --help      Mostra questo messaggio

Descrizione:
  Converte i campi codice da INTEGER a VARCHAR(50):
  - controparti.cod_controparte
  - modelli.cod_modello
  - file_ordini.cod_seller, cod_buyer
  - ordini.cod_modello

IMPORTANTE:
  - Crea sempre un backup prima di eseguire
  - Per PostgreSQL, usa lo script SQL per maggiore affidabilità
  - Per SQLite, richiede ricostruzione completa delle tabelle
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

        # Verifica tabelle esistenti
        inspector = inspect(engine)
        required_tables = ['controparti', 'modelli', 'file_ordini', 'ordini']
        missing_tables = [t for t in required_tables if not table_exists(inspector, t)]

        if missing_tables:
            print(f"✗ ERRORE: Tabelle mancanti: {', '.join(missing_tables)}")
            print("  Eseguire prima migrate_add_business_tables.py")
            return 1

        print("✓ Tutte le tabelle richieste sono presenti\n")

        # Richiedi conferma
        if '--yes' not in sys.argv and '-y' not in sys.argv:
            print("⚠ ATTENZIONE: Questa operazione modificherà lo schema del database!")
            print("  Assicurati di avere un backup recente.")
            print()
            risposta = input("Procedere con la migrazione? [y/N]: ")
            if risposta.lower() != 'y':
                print("Migrazione annullata.")
                return 0

        # Backup
        backup_path = backup_database()

        # Esegui migrazione in base al database
        try:
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
