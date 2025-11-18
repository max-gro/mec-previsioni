"""
Script di migrazione database: Crea tabelle per il tracciamento elaborazioni
Esegui con: python migrate_trace_elaborazioni.py
"""

import os
import sys

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def migrate_database():
    """Crea le tabelle trace_elaborazioni e trace_elaborazioni_dettaglio"""

    from app import create_app
    from models import db
    from sqlalchemy import text

    app = create_app()

    with app.app_context():
        try:
            # TABELLA 1: trace_elaborazioni
            print("Creazione tabella 'trace_elaborazioni'...")
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS trace_elaborazioni (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Riferimento al file (polimorfismo)
                    tipo_pipeline VARCHAR(20) NOT NULL,
                    id_file INTEGER NOT NULL,

                    -- Timing elaborazione
                    ts_inizio DATETIME NOT NULL,
                    ts_fine DATETIME,
                    durata_secondi INTEGER,

                    -- Esito
                    esito VARCHAR(50) NOT NULL,

                    -- Statistiche elaborazione
                    righe_totali INTEGER DEFAULT 0,
                    righe_ok INTEGER DEFAULT 0,
                    righe_errore INTEGER DEFAULT 0,
                    righe_warning INTEGER DEFAULT 0,

                    -- Note generali
                    messaggio_globale TEXT,

                    -- Metadata
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # Indici per trace_elaborazioni
            db.session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_trace_elab_pipeline_file
                ON trace_elaborazioni(tipo_pipeline, id_file)
            '''))

            db.session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_trace_elab_esito
                ON trace_elaborazioni(esito)
            '''))

            db.session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_trace_elab_ts_inizio
                ON trace_elaborazioni(ts_inizio)
            '''))

            print("✓ Tabella 'trace_elaborazioni' creata con successo!")

            # TABELLA 2: trace_elaborazioni_dettaglio
            print("Creazione tabella 'trace_elaborazioni_dettaglio'...")
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS trace_elaborazioni_dettaglio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- FK all'elaborazione
                    id_elaborazione INTEGER NOT NULL,

                    -- Dettaglio riga/anomalia
                    riga_numero INTEGER,
                    tipo_messaggio VARCHAR(20),
                    codice_errore VARCHAR(50),
                    messaggio TEXT NOT NULL,

                    -- Contesto aggiuntivo
                    campo VARCHAR(100),
                    valore_originale TEXT,
                    valore_corretto TEXT,

                    -- Timestamp
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (id_elaborazione) REFERENCES trace_elaborazioni(id)
                )
            '''))

            # Indici per trace_elaborazioni_dettaglio
            db.session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_trace_dett_elaborazione
                ON trace_elaborazioni_dettaglio(id_elaborazione)
            '''))

            db.session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_trace_dett_tipo
                ON trace_elaborazioni_dettaglio(tipo_messaggio)
            '''))

            print("✓ Tabella 'trace_elaborazioni_dettaglio' creata con successo!")

            db.session.commit()

            print("\n" + "="*60)
            print("Migrazione completata con successo!")
            print("="*60)
            print("\nTabelle create:")
            print("  - trace_elaborazioni (con 3 indici)")
            print("  - trace_elaborazioni_dettaglio (con 2 indici)")
            print("\nAdesso puoi avviare l'app con: python app.py")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Errore durante la migrazione: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        success = migrate_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
