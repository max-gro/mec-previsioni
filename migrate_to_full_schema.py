#!/usr/bin/env python3
"""
Script di migrazione per creare lo schema completo delle 3 pipeline:
- Pipeline Ordini (file_ordini → ordini, controparti)
- Pipeline Anagrafiche (file_anagrafiche → modelli, componenti, modelli_componenti)
- Pipeline Rotture (file_rotture → rotture, rotture_componenti, utenti_rotture, rivenditori)

Rinomina anche le tabelle esistenti per coerenza:
- ordini_acquisto → file_ordini
- anagrafiche_file → file_anagrafiche
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Aggiungi il path dell'app per importare i modelli
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import DevelopmentConfig, ProductionConfig
from models import (
    db, User,
    FileRottura, FileOrdine, FileAnagrafica,
    Controparte, Modello, Componente,
    Ordine, ModelloComponente,
    UtenteRottura, Rivenditore, Rottura, RotturaComponente,
    TraceElab, TraceElabDett
)

# Crea istanza app usando factory pattern
app = create_app(DevelopmentConfig)


def print_header(title):
    """Stampa un header formattato"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title):
    """Stampa una sezione"""
    print(f"\n→ {title}")
    print("-" * 80)


def table_exists(engine, table_name):
    """Verifica se una tabella esiste nel database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def rename_table_if_exists(engine, old_name, new_name):
    """Rinomina una tabella se esiste"""
    if not table_exists(engine, old_name):
        print(f"  ⚠ Tabella {old_name} non trovata, skip rename")
        return False

    if table_exists(engine, new_name):
        print(f"  ⚠ Tabella {new_name} già esistente, skip rename")
        return False

    try:
        with engine.begin() as conn:
            # Sintassi diversa per SQLite e PostgreSQL
            if engine.dialect.name == 'sqlite':
                conn.execute(text(f"ALTER TABLE {old_name} RENAME TO {new_name}"))
            elif engine.dialect.name == 'postgresql':
                conn.execute(text(f"ALTER TABLE {old_name} RENAME TO {new_name}"))
            else:
                print(f"  ✗ Database {engine.dialect.name} non supportato per rename")
                return False

        print(f"  ✓ Tabella rinominata: {old_name} → {new_name}")
        return True

    except Exception as e:
        print(f"  ✗ Errore durante rename {old_name} → {new_name}: {e}")
        return False


def backup_database(db_uri):
    """Crea backup del database SQLite se necessario"""
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✓ Backup database creato: {backup_path}")
            return backup_path
    else:
        print("⚠ Database remoto: backup non creato automaticamente")
    return None


def verify_models():
    """Verifica che tutti i modelli siano importabili"""
    models_to_check = [
        ('User', User),
        ('FileRottura', FileRottura),
        ('FileOrdine', FileOrdine),
        ('FileAnagrafica', FileAnagrafica),
        ('Controparte', Controparte),
        ('Modello', Modello),
        ('Componente', Componente),
        ('Ordine', Ordine),
        ('ModelloComponente', ModelloComponente),
        ('UtenteRottura', UtenteRottura),
        ('Rivenditore', Rivenditore),
        ('Rottura', Rottura),
        ('RotturaComponente', RotturaComponente),
        ('TraceElab', TraceElab),
        ('TraceElabDett', TraceElabDett),
    ]

    print_section("Verifica Modelli SQLAlchemy")
    all_ok = True
    for model_name, model_class in models_to_check:
        try:
            tablename = model_class.__tablename__
            print(f"  ✓ {model_name:25s} → {tablename}")
        except Exception as e:
            print(f"  ✗ {model_name:25s} → ERRORE: {e}")
            all_ok = False

    return all_ok


def migrate_schema():
    """Migrazione principale"""
    print_header("MIGRAZIONE SCHEMA COMPLETO - 3 PIPELINE")

    with app.app_context():
        engine = db.engine
        db_type = engine.dialect.name
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']

        print(f"\nDatabase Type: {db_type}")
        print(f"Database URI:  {db_uri}")

        # Verifica modelli
        if not verify_models():
            print("\n✗ ERRORE: Alcuni modelli non sono validi!")
            return False

        # Chiedi conferma
        print_section("Operazioni da eseguire")
        print("  1. Backup database (se SQLite)")
        print("  2. Rinomina tabelle esistenti per coerenza:")
        print("     - ordini_acquisto → file_ordini")
        print("     - anagrafiche_file → file_anagrafiche")
        print("  3. Crea nuove tabelle:")
        print("     - controparti, modelli, componenti")
        print("     - ordini (dettaglio righe ordini)")
        print("     - modelli_componenti (BOM)")
        print("     - utenti_rotture, rivenditori")
        print("     - rotture, rotture_componenti")
        print("     - trace_elab, trace_elab_dett")

        if '--yes' not in sys.argv and '-y' not in sys.argv:
            risposta = input("\n⚠ Procedere con la migrazione? [y/N]: ")
            if risposta.lower() != 'y':
                print("Migrazione annullata.")
                return False

        # Backup
        print_section("Backup Database")
        backup_path = backup_database(db_uri)

        # STEP 1: Rinomina tabelle esistenti
        print_section("STEP 1: Rinomina Tabelle Esistenti")

        tables_to_rename = [
            ('ordini_acquisto', 'file_ordini'),
            ('anagrafiche_file', 'file_anagrafiche'),
        ]

        for old_name, new_name in tables_to_rename:
            rename_table_if_exists(engine, old_name, new_name)

        # STEP 2: Crea nuove tabelle
        print_section("STEP 2: Creazione Nuove Tabelle")

        new_tables = [
            ('controparti', Controparte),
            ('modelli', Modello),
            ('componenti', Componente),
            ('ordini', Ordine),
            ('modelli_componenti', ModelloComponente),
            ('utenti_rotture', UtenteRottura),
            ('rivenditori', Rivenditore),
            ('rotture', Rottura),
            ('rotture_componenti', RotturaComponente),
            ('trace_elab', TraceElab),
            ('trace_elab_dett', TraceElabDett),
        ]

        created_count = 0
        skipped_count = 0
        error_count = 0

        for table_name, model_class in new_tables:
            if table_exists(engine, table_name):
                print(f"  ⚠ {table_name:30s} già esistente, skip")
                skipped_count += 1
                continue

            try:
                model_class.__table__.create(engine, checkfirst=True)
                print(f"  ✓ {table_name:30s} creata")
                created_count += 1
            except Exception as e:
                print(f"  ✗ {table_name:30s} ERRORE: {e}")
                error_count += 1

        # STEP 3: Verifica finale
        print_section("STEP 3: Verifica Finale")

        all_tables = [
            'users',
            'file_rotture',
            'file_ordini',
            'file_anagrafiche',
            'controparti',
            'modelli',
            'componenti',
            'ordini',
            'modelli_componenti',
            'utenti_rotture',
            'rivenditori',
            'rotture',
            'rotture_componenti',
            'trace_elab',
            'trace_elab_dett',
        ]

        missing_tables = []
        existing_tables = []

        for table_name in all_tables:
            if table_exists(engine, table_name):
                print(f"  ✓ {table_name:35s} OK")
                existing_tables.append(table_name)
            else:
                print(f"  ✗ {table_name:35s} MANCANTE")
                missing_tables.append(table_name)

        # Report finale
        print_header("REPORT MIGRAZIONE")
        print(f"\nTabelle create:    {created_count}")
        print(f"Tabelle esistenti: {skipped_count}")
        print(f"Errori:            {error_count}")
        print(f"\nTabelle totali:    {len(existing_tables)}/{len(all_tables)}")

        if missing_tables:
            print(f"\n⚠ ATTENZIONE: {len(missing_tables)} tabelle mancanti:")
            for t in missing_tables:
                print(f"  - {t}")

        if backup_path:
            print(f"\nBackup disponibile: {backup_path}")

        if error_count > 0:
            print("\n✗ MIGRAZIONE COMPLETATA CON ERRORI")
            return False
        elif missing_tables:
            print("\n⚠ MIGRAZIONE PARZIALE: Alcune tabelle non sono state create")
            return False
        else:
            print("\n✓ MIGRAZIONE COMPLETATA CON SUCCESSO!")
            print("\nProssimi passi:")
            print("  1. Verificare che l'app si avvii correttamente")
            print("  2. Testare le funzionalità di upload e elaborazione")
            print("  3. Popolare le tabelle di lookup (controparti, modelli, componenti)")
            return True


def show_schema():
    """Mostra lo schema completo del database"""
    print_header("SCHEMA DATABASE COMPLETO")

    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)

        tables = inspector.get_table_names()

        for table_name in sorted(tables):
            print(f"\n📋 Tabella: {table_name}")
            print("-" * 80)

            # Colonne
            columns = inspector.get_columns(table_name)
            for col in columns:
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                default = f" DEFAULT {col['default']}" if col.get('default') else ""
                print(f"  {col['name']:30s} {col_type:20s} {nullable}{default}")

            # Primary Key
            pk = inspector.get_pk_constraint(table_name)
            if pk and pk.get('constrained_columns'):
                print(f"\n  PRIMARY KEY: {', '.join(pk['constrained_columns'])}")

            # Foreign Keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print(f"\n  FOREIGN KEYS:")
                for fk in fks:
                    local_cols = ', '.join(fk['constrained_columns'])
                    remote_table = fk['referred_table']
                    remote_cols = ', '.join(fk['referred_columns'])
                    print(f"    {local_cols} → {remote_table}({remote_cols})")

            # Indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print(f"\n  INDEXES:")
                for idx in indexes:
                    cols = ', '.join(idx['column_names'])
                    unique = "UNIQUE" if idx.get('unique') else ""
                    print(f"    {idx['name']:30s} ({cols}) {unique}")


if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Uso: python migrate_to_full_schema.py [opzioni]

Opzioni:
  -y, --yes       Esegui migrazione senza chiedere conferma
  --schema        Mostra lo schema completo dopo la migrazione
  -h, --help      Mostra questo messaggio di aiuto

Descrizione:
  Questo script crea lo schema completo per le 3 pipeline:

  PIPELINE ORDINI:
    - file_ordini (rinomina da ordini_acquisto)
    - controparti (seller/buyer)
    - modelli (prodotti)
    - ordini (dettaglio righe ordini)

  PIPELINE ANAGRAFICHE:
    - file_anagrafiche (rinomina da anagrafiche_file)
    - modelli (prodotti)
    - componenti (parti di ricambio)
    - modelli_componenti (BOM - Bill of Materials)

  PIPELINE ROTTURE:
    - file_rotture
    - modelli (prodotti)
    - componenti (parti di ricambio)
    - utenti_rotture (clienti finali)
    - rivenditori
    - rotture (eventi di guasto)
    - rotture_componenti (parti sostituite)

  TRACCIAMENTO:
    - trace_elab (livello file)
    - trace_elab_dett (livello record)

IMPORTANTE: Crea un backup prima di eseguire!
""")
        sys.exit(0)

    try:
        success = migrate_schema()

        if success and '--schema' in sys.argv:
            show_schema()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n✗ ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
