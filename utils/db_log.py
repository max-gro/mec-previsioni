"""
Modulo per gestire la sessione database SEPARATA per le tabelle di log.

AUTONOMOUS TRANSACTION PATTERN:
- I log (TraceElab, TraceElabDett) usano una connessione separata
- Ogni operazione di log fa commit immediato
- I log persistono SEMPRE, anche in caso di rollback delle tabelle operative

Uso:
    from utils.db_log import log_session

    # Scrivi log (commit immediato)
    trace = TraceElab(...)
    log_session.add(trace)
    log_session.commit()  # ← Sempre persistito

    # Operazioni transazionali normali
    try:
        ordine.esito = 'Processato'
        db.session.add(ordine)
        db.session.commit()  # ← Può fallire
    except:
        db.session.rollback()  # ← Non tocca i log!
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import current_app

# Engine separato per i log (inizializzato in app.py)
log_engine = None

# Sessione separata per i log (thread-safe con scoped_session)
log_session = None


def init_log_session(database_uri):
    """
    Inizializza l'engine e la sessione separata per i log.

    Args:
        database_uri: URI del database (stesso DB, connessione diversa)

    Chiamata da app.py durante l'inizializzazione dell'app.
    """
    global log_engine, log_session

    # Crea engine separato per i log
    log_engine = create_engine(
        database_uri,
        pool_pre_ping=True,  # Verifica connessioni prima di usarle
        pool_recycle=3600,   # Ricicla connessioni ogni ora
        echo=False           # No logging SQL (può essere True per debug)
    )

    # Crea sessione scoped (thread-safe)
    log_session = scoped_session(
        sessionmaker(
            bind=log_engine,
            autocommit=False,
            autoflush=False
        )
    )

    print(f"✓ Log session initialized (separate connection)")


def cleanup_log_session():
    """
    Pulisce la log session alla fine di ogni request.

    Chiamata automaticamente dal teardown handler in app.py.
    """
    if log_session:
        log_session.remove()


def log_commit():
    """
    Helper per commit della log session.

    Uso consigliato invece di log_session.commit() per gestione errori.
    """
    try:
        log_session.commit()
    except Exception as e:
        log_session.rollback()
        # Log l'errore ma non propagare (i log sono best-effort)
        print(f"[WARNING] Log commit failed: {e}")


def log_rollback():
    """
    Helper per rollback della log session.

    Usato raramente, solo in caso di errori critici durante scrittura log.
    """
    log_session.rollback()
