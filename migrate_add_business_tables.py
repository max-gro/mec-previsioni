#!/usr/bin/env python3
"""
Script di migrazione per aggiungere tabelle business con campi codice alfanumerici:
- controparti (cod_controparte VARCHAR)
- modelli (cod_modello VARCHAR)
- file_ordini (cod_seller, cod_buyer VARCHAR)
- ordini (cod_ordine, cod_modello VARCHAR)
- trace_elaborazioni_file
- trace_elaborazioni_record

IMPORTANTE: I campi codice sono già alfanumerici (VARCHAR) fin dall'inizio.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect, text
from app import app
from models import db, Controparte, Modello, FileOrdine, Ordine, TraceElaborazioneFile, TraceElaborazioneRecord

def table_exists(engine, table_name):
    """Verifica se una tabella esiste nel database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def backup_database():
    """Crea backup del database SQLite se in modalità development"""
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///'):
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✓ Backup database creato: {backup_path}")
            return backup_path
    return None

def create_sequences(engine):
    """Crea sequence per PostgreSQL (se necessario)"""
    db_type = engine.dialect.name

    if db_type == 'postgresql':
        with engine.connect() as conn:
            sequences = [
                ('file_ordini_id_file_ordine_seq', 'file_ordini', 'id_file_ordine'),
                ('trace_elaborazioni_file_id_trace_seq', 'trace_elaborazioni_file', 'id_trace'),
                ('trace_elaborazioni_record_id_trace_record_seq', 'trace_elaborazioni_record', 'id_trace_record'),
            ]

            for seq_name, table_name, col_name in sequences:
                try:
                    # Verifica se la sequence esiste già
                    result = conn.execute(text(
                        f"SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = '{seq_name}'"
                    ))
                    if not result.fetchone():
                        conn.execute(text(f"CREATE SEQUENCE {seq_name} START 1"))
                        print(f"  ✓ Sequence creata: {seq_name}")
                    else:
                        print(f"  ⚠ Sequence già esistente: {seq_name}")
                except Exception as e:
                    print(f"  ⚠ Errore creazione sequence {seq_name}: {e}")

            conn.commit()

def migrate_add_business_tables():
    """Migrazione principale: aggiunge tabelle business con codici alfanumerici"""

    print("\n" + "="*80)
    print("MIGRAZIONE: Aggiunta tabelle business con codici alfanumerici")
    print("="*80 + "\n")

    with app.app_context():
        engine = db.engine
        db_type = engine.dialect.name

        print(f"Database: {db_type}")
        print(f"URI: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

        # Lista delle tabelle da creare
        tables_to_create = [
            ('controparti', Controparte),
            ('modelli', Modello),
            ('file_ordini', FileOrdine),
            ('ordini', Ordine),
            ('trace_elaborazioni_file', TraceElaborazioneFile),
            ('trace_elaborazioni_record', TraceElaborazioneRecord),
        ]

        # Verifica quali tabelle esistono già
        existing_tables = []
        missing_tables = []

        for table_name, model_class in tables_to_create:
            if table_exists(engine, table_name):
                existing_tables.append(table_name)
            else:
                missing_tables.append((table_name, model_class))

        if existing_tables:
            print("⚠ ATTENZIONE: Le seguenti tabelle esistono già:")
            for table in existing_tables:
                print(f"  - {table}")
            print()

        if not missing_tables:
            print("✓ Tutte le tabelle business sono già presenti nel database.")
            print("  Nessuna migrazione necessaria.\n")
            return True

        print(f"Tabelle da creare: {len(missing_tables)}")
        for table_name, _ in missing_tables:
            print(f"  - {table_name}")
        print()

        # Richiedi conferma
        if '--yes' not in sys.argv and '-y' not in sys.argv:
            risposta = input("Procedere con la migrazione? [y/N]: ")
            if risposta.lower() != 'y':
                print("Migrazione annullata.")
                return False

        # Backup del database (solo SQLite)
        backup_path = backup_database()

        try:
            # Crea sequence (solo PostgreSQL)
            if db_type == 'postgresql':
                print("\nCreazione sequence PostgreSQL...")
                create_sequences(engine)

            # Crea le tabelle mancanti
            print("\nCreazione tabelle...")

            for table_name, model_class in missing_tables:
                try:
                    model_class.__table__.create(engine)
                    print(f"  ✓ Tabella creata: {table_name}")
                except Exception as e:
                    print(f"  ✗ Errore creazione tabella {table_name}: {e}")
                    raise

            # Verifica finale
            print("\nVerifica finale...")
            all_ok = True
            for table_name, _ in tables_to_create:
                exists = table_exists(engine, table_name)
                status = "✓" if exists else "✗"
                print(f"  {status} {table_name}: {'OK' if exists else 'MANCANTE'}")
                if not exists:
                    all_ok = False

            if all_ok:
                print("\n" + "="*80)
                print("✓ MIGRAZIONE COMPLETATA CON SUCCESSO")
                print("="*80)
                print("\nRiepilogo campi codice alfanumerici (VARCHAR):")
                print("  - controparti.cod_controparte: VARCHAR(50) PRIMARY KEY")
                print("  - modelli.cod_modello: VARCHAR(50) PRIMARY KEY")
                print("  - file_ordini.cod_seller: VARCHAR(50) FOREIGN KEY")
                print("  - file_ordini.cod_buyer: VARCHAR(50) FOREIGN KEY")
                print("  - ordini.cod_ordine: VARCHAR(100)")
                print("  - ordini.cod_modello: VARCHAR(50) FOREIGN KEY")
                print("\n✓ Tutti i codici sono alfanumerici e supportano lettere, numeri e caratteri speciali.\n")

                if backup_path:
                    print(f"Backup disponibile in: {backup_path}\n")

                return True
            else:
                print("\n⚠ ATTENZIONE: Alcune tabelle non sono state create correttamente.")
                return False

        except Exception as e:
            print(f"\n✗ ERRORE durante la migrazione: {e}")
            if backup_path:
                print(f"È possibile ripristinare il backup da: {backup_path}")
            raise

def show_schema():
    """Mostra lo schema delle nuove tabelle"""
    print("\n" + "="*80)
    print("SCHEMA TABELLE BUSINESS")
    print("="*80 + "\n")

    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)

        tables = ['controparti', 'modelli', 'file_ordini', 'ordini',
                 'trace_elaborazioni_file', 'trace_elaborazioni_record']

        for table_name in tables:
            if table_exists(engine, table_name):
                print(f"📋 Tabella: {table_name}")
                columns = inspector.get_columns(table_name)
                for col in columns:
                    col_type = str(col['type'])
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    default = f"DEFAULT {col['default']}" if col['default'] else ""
                    print(f"  - {col['name']}: {col_type} {nullable} {default}")

                # Mostra chiavi primarie
                pk = inspector.get_pk_constraint(table_name)
                if pk and pk['constrained_columns']:
                    print(f"  PRIMARY KEY: {', '.join(pk['constrained_columns'])}")

                # Mostra foreign keys
                fks = inspector.get_foreign_keys(table_name)
                if fks:
                    print(f"  FOREIGN KEYS:")
                    for fk in fks:
                        print(f"    - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

                print()
            else:
                print(f"⚠ Tabella {table_name} non trovata\n")

if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python migrate_add_business_tables.py [opzioni]

Opzioni:
  -y, --yes     Esegui migrazione senza chiedere conferma
  --schema      Mostra lo schema delle tabelle dopo la migrazione
  -h, --help    Mostra questo messaggio di aiuto

Descrizione:
  Questo script crea le tabelle business con campi codice alfanumerici:
  - controparti (cod_controparte VARCHAR)
  - modelli (cod_modello VARCHAR)
  - file_ordini (cod_seller, cod_buyer VARCHAR)
  - ordini (cod_ordine, cod_modello VARCHAR)
  - trace_elaborazioni_file
  - trace_elaborazioni_record

  I campi codice sono definiti come VARCHAR per supportare codici alfanumerici
  (lettere, numeri e caratteri speciali) invece di solo numeri interi.
""")
        sys.exit(0)

    try:
        success = migrate_add_business_tables()

        if success and '--schema' in sys.argv:
            show_schema()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n✗ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
