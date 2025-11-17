#!/usr/bin/env python3
# migrate_pipeline_anagrafiche.py
"""
Migrazione per pipeline anagrafiche: crea tabelle modelli, componenti, modelli_componenti
e aggiunge campi audit a anagrafiche_file.

Uso:
    python migrate_pipeline_anagrafiche.py
"""

import os
import sys
from sqlalchemy import inspect, text

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from app import create_app
    _app = create_app()
except Exception:
    from app import app as _app

from models import db


def table_exists(engine, table_name):
    """Controlla se una tabella esiste"""
    insp = inspect(engine)
    return table_name in insp.get_table_names()


def column_exists(engine, table_name, column_name):
    """Controlla se una colonna esiste in una tabella"""
    if not table_exists(engine, table_name):
        return False
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def add_column_sqlite(engine, table_name, column_def):
    """Aggiunge una colonna a una tabella SQLite"""
    ddl = text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
    with engine.begin() as conn:
        conn.execute(ddl)


def create_table_modelli(engine):
    """Crea la tabella modelli"""
    sql = text("""
        CREATE TABLE IF NOT EXISTS modelli (
            cod_modello VARCHAR(100) PRIMARY KEY,
            cod_modello_norm VARCHAR(100) UNIQUE NOT NULL,
            cod_modello_fabbrica VARCHAR(100),
            nome_modello VARCHAR(200),
            nome_modello_it VARCHAR(200),
            divisione VARCHAR(100),
            marca VARCHAR(100),
            desc_modello TEXT,
            produttore VARCHAR(200),
            famiglia VARCHAR(100),
            tipo VARCHAR(100),
            created_at DATETIME,
            created_by VARCHAR(80),
            updated_at DATETIME,
            updated_by VARCHAR(80),
            updated_from VARCHAR(10)
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql)

    # Crea indice su cod_modello_norm
    idx_sql = text("CREATE INDEX IF NOT EXISTS idx_modelli_norm ON modelli(cod_modello_norm)")
    with engine.begin() as conn:
        conn.execute(idx_sql)


def create_table_componenti(engine):
    """Crea la tabella componenti"""
    sql = text("""
        CREATE TABLE IF NOT EXISTS componenti (
            cod_componente VARCHAR(100) PRIMARY KEY,
            cod_componente_norm VARCHAR(100) UNIQUE NOT NULL,
            desc_componente_it TEXT,
            cod_alt VARCHAR(100),
            cod_alt_2 VARCHAR(100),
            pos_no VARCHAR(50),
            part_no VARCHAR(100),
            part_name_en VARCHAR(200),
            part_name_cn VARCHAR(200),
            part_name_it VARCHAR(200),
            cod_ean VARCHAR(50),
            barcode VARCHAR(10),
            unit_price_usd DECIMAL(10, 2),
            unit_price_notra_noiva_netto_eur DECIMAL(10, 2),
            unit_price_tra_noiva_netto_eur DECIMAL(10, 2),
            unit_price_public_eur DECIMAL(10, 2),
            stat VARCHAR(50),
            softech_stat VARCHAR(50),
            created_at DATETIME,
            created_by VARCHAR(80),
            updated_at DATETIME,
            updated_by VARCHAR(80)
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql)

    # Crea indice su cod_componente_norm
    idx_sql = text("CREATE INDEX IF NOT EXISTS idx_componenti_norm ON componenti(cod_componente_norm)")
    with engine.begin() as conn:
        conn.execute(idx_sql)


def create_table_modelli_componenti(engine):
    """Crea la tabella modelli_componenti"""
    sql = text("""
        CREATE TABLE IF NOT EXISTS modelli_componenti (
            modello_componente VARCHAR(200) PRIMARY KEY,
            id_file_anagrafiche INTEGER NOT NULL,
            cod_modello VARCHAR(100) NOT NULL,
            cod_componente VARCHAR(100) NOT NULL,
            qta INTEGER NOT NULL,
            created_at DATETIME,
            created_by VARCHAR(80),
            updated_at DATETIME,
            updated_by VARCHAR(80),
            FOREIGN KEY (id_file_anagrafiche) REFERENCES anagrafiche_file(id_file_anagrafiche),
            FOREIGN KEY (cod_modello) REFERENCES modelli(cod_modello),
            FOREIGN KEY (cod_componente) REFERENCES componenti(cod_componente)
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql)


def add_audit_columns_to_anagrafiche_file(engine):
    """Aggiunge campi created_by e updated_by a anagrafiche_file"""
    if not column_exists(engine, "anagrafiche_file", "created_by"):
        print("➕ Aggiungo colonna 'created_by' a anagrafiche_file…")
        add_column_sqlite(engine, "anagrafiche_file", "created_by VARCHAR(80)")
    else:
        print("ℹ️  Colonna 'created_by' già presente in anagrafiche_file.")

    if not column_exists(engine, "anagrafiche_file", "updated_by"):
        print("➕ Aggiungo colonna 'updated_by' a anagrafiche_file…")
        add_column_sqlite(engine, "anagrafiche_file", "updated_by VARCHAR(80)")
    else:
        print("ℹ️  Colonna 'updated_by' già presente in anagrafiche_file.")


def run():
    """Esegue la migrazione"""
    with _app.app_context():
        engine = db.engine

        print("🔧 Inizio migrazione pipeline anagrafiche…\n")

        # 1. Crea tabella modelli
        if not table_exists(engine, "modelli"):
            print("➕ Creo tabella 'modelli'…")
            create_table_modelli(engine)
            print("✓ Tabella 'modelli' creata.")
        else:
            print("ℹ️  Tabella 'modelli' già esistente.")

        # 2. Crea tabella componenti
        if not table_exists(engine, "componenti"):
            print("➕ Creo tabella 'componenti'…")
            create_table_componenti(engine)
            print("✓ Tabella 'componenti' creata.")
        else:
            print("ℹ️  Tabella 'componenti' già esistente.")

        # 3. Crea tabella modelli_componenti
        if not table_exists(engine, "modelli_componenti"):
            print("➕ Creo tabella 'modelli_componenti'…")
            create_table_modelli_componenti(engine)
            print("✓ Tabella 'modelli_componenti' creata.")
        else:
            print("ℹ️  Tabella 'modelli_componenti' già esistente.")

        # 4. Aggiungi campi audit a anagrafiche_file
        print("\n🔧 Aggiungo campi audit a anagrafiche_file…")
        add_audit_columns_to_anagrafiche_file(engine)

        print("\n✔ Migrazione completata con successo!")


if __name__ == "__main__":
    run()
