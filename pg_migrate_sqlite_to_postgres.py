# pg_migrate_sqlite_to_postgres.py
import os
import pandas as pd
from sqlalchemy import create_engine, text
from models import db
from config import Config  # contiene il path di SQLite attuale

# URL sorgente (SQLite) e destinazione (Postgres)
sqlite_url = f"sqlite:///{Config.db_path}"
pg_url = os.environ.get("DATABASE_URL")
if not pg_url:
    raise SystemExit("DATABASE_URL non impostata")

src = create_engine(sqlite_url, future=True)
dst = create_engine(pg_url, future=True)

# 1) Crea tabelle su Postgres dai modelli, se non già create
db.metadata.create_all(dst)

tables = [
    "users",
    "rotture",
    "ordini_acquisto",
    "anagrafiche_file",
]

def copy_table(name: str):
    print(f"→ Copio tabella: {name}")
    df = pd.read_sql_table(name, con=src)
    if df.empty:
        print(f"  (vuota)")
        return
    # Scrivi su Postgres preservando gli id
    df.to_sql(name, con=dst, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"  Copiate {len(df)} righe")

# 2) Copia dati tabella per tabella
for t in tables:
    copy_table(t)

# 3) Riallinea sequence di Postgres per gli id
with dst.begin() as conn:
    for t in tables:
        sql = text(f"""
            SELECT setval(pg_get_serial_sequence('{t}','id'),
                          GREATEST((SELECT COALESCE(MAX(id),0) FROM {t}), 1),
                          true);
        """)
        conn.execute(sql)
print("✓ Migrazione completata.")
