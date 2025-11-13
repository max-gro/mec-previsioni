# postgres_create_schema.py

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from models import db  # contiene db.metadata con tutte le tabelle

load_dotenv()
pg_url = os.environ.get("DATABASE_URL")
print(f"Using DATABASE_URL: {pg_url}")
if not pg_url:
    raise SystemExit("DATABASE_URL non impostata")

engine = create_engine(pg_url, future=True)
# Crea lo schema su Postgres partendo dai modelli SQLAlchemy/Flask
db.metadata.create_all(engine)
print("Schema creato su Postgres.")
