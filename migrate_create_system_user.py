#!/usr/bin/env python3
"""
Script di migrazione: Crea utente di sistema con id_user=0

Questo utente è utilizzato come default per created_by/updated_by quando
i record vengono creati automaticamente (es. scan filesystem) senza un
utente loggato.
"""

import sys
import os
from sqlalchemy import text

# Aggiungi path root al sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import DevelopmentConfig
from models import db

def create_system_user():
    """Crea utente di sistema con id_user=0"""

    app = create_app(DevelopmentConfig)

    with app.app_context():
        try:
            # Verifica se esiste già
            result = db.session.execute(text("SELECT id_user FROM users WHERE id_user = 0")).fetchone()

            if result:
                print("✓ Utente di sistema (id=0) esiste già")
                return True

            print("\n" + "=" * 80)
            print("  CREAZIONE UTENTE DI SISTEMA (id_user=0)")
            print("=" * 80 + "\n")

            # Inserisci utente di sistema
            # Nota: PostgreSQL richiede di impostare esplicitamente id=0
            # disabilitando temporaneamente la sequenza

            db.session.execute(text("""
                INSERT INTO users (id_user, username, email, password_hash, role, active, created_at, created_by)
                VALUES (
                    0,
                    'system',
                    'system@localhost',
                    'SISTEMA_NON_ACCESSIBILE',
                    'Sistema',
                    FALSE,
                    NOW(),
                    0
                )
            """))

            db.session.commit()

            print("✓ Utente di sistema creato con successo")
            print("\n  Dettagli:")
            print("  - id_user: 0")
            print("  - username: system")
            print("  - email: system@localhost")
            print("  - role: Sistema")
            print("  - active: FALSE (non può fare login)")
            print("\nQuesto utente viene usato come default per created_by/updated_by")
            print("quando i record vengono creati automaticamente dal sistema.\n")

            return True

        except Exception as e:
            print(f"\n✗ ERRORE durante creazione utente di sistema: {e}\n")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = create_system_user()
    sys.exit(0 if success else 1)
