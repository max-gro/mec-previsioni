# migrate_anagrafiche.py
"""
Migrazione 'anno' per anagrafiche_file.
- Crea la colonna se manca.
- Popola sempre i valori NULL da data_acquisizione/created_at/now.
- Opzionale: --recompute ricalcola TUTTE le righe (sovrascrive anno).
Uso:
    python migrate_anagrafiche.py           # crea e/o riempie solo i NULL
    python migrate_anagrafiche.py --recompute  # ricalcola tutti i record
"""

import os
import sys
import argparse
from datetime import datetime, date
from sqlalchemy import inspect, text

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from app import create_app
    _app = create_app()
except Exception:
    from app import app as _app

from models import db


def column_exists(engine, table_name, column_name):
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def add_column_sqlite(engine, table_name, column_def):
    ddl = text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
    with engine.begin() as conn:
        conn.execute(ddl)


def run(recompute: bool = False):
    with _app.app_context():
        engine = db.engine
        table = "anagrafiche_file"

        # 1) Assicurati che la colonna esista
        if not column_exists(engine, table, "anno"):
            print("➕ Aggiungo colonna 'anno' …")
            add_column_sqlite(engine, table, "anno INTEGER")
        else:
            print("ℹ️  Colonna 'anno' già presente.")

        # 2) Se --recompute: sovrascrivi per tutte le righe
        if recompute:
            print("↻ Ricalcolo 'anno' per TUTTI i record (modalità --recompute)…")
            sql_all = text(f"""
                UPDATE {table}
                SET anno = COALESCE(
                    CAST(strftime('%Y', data_acquisizione) AS INTEGER),
                    CAST(strftime('%Y', created_at)       AS INTEGER),
                    CAST(strftime('%Y','now')             AS INTEGER)
                )
            """)
            with engine.begin() as conn:
                res = conn.execute(sql_all)
                print(f"✓ Aggiornati (recompute) {res.rowcount or 0} record.")
        else:
            # 3) Default: riempi solo i NULL
            print("↻ Popolo 'anno' per i record con valore NULL …")
            sql_nulls = text(f"""
                UPDATE {table}
                SET anno = COALESCE(
                    CAST(strftime('%Y', data_acquisizione) AS INTEGER),
                    CAST(strftime('%Y', created_at)       AS INTEGER),
                    CAST(strftime('%Y','now')             AS INTEGER)
                )
                WHERE anno IS NULL
            """)
            with engine.begin() as conn:
                res = conn.execute(sql_nulls)
                print(f"✓ Aggiornati {res.rowcount or 0} record.")

        # 4) Safety: clampa intervallo plausibile (1950 … anno_corrente+1)
        minY, maxY = 1950, date.today().year + 1
        print(f"🧹 Normalizzo fuori range ({minY}..{maxY}) …")
        sql_low = text(f"UPDATE {table} SET anno = :minY WHERE anno IS NOT NULL AND anno < :minY")
        sql_high = text(f"UPDATE {table} SET anno = :maxY WHERE anno IS NOT NULL AND anno > :maxY")
        with engine.begin() as conn:
            r1 = conn.execute(sql_low, {"minY": minY})
            r2 = conn.execute(sql_high, {"maxY": maxY})
        print(f"✓ Normalizzati <{minY}: {r1.rowcount or 0}  |  >{maxY}: {r2.rowcount or 0}")

        print("✔ Migrazione completata.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recompute", action="store_true",
                        help="Ricalcola 'anno' per tutti i record, sovrascrivendo i valori esistenti.")
    args = parser.parse_args()
    run(recompute=args.recompute)
