#!/usr/bin/env python3
"""
Script per eseguire la migration add_id_elab_and_metrics.sql
"""

from app import create_app, db

app = create_app()

def run_migration():
    """Esegue la migration SQL"""
    migration_file = 'migrations_sql/add_id_elab_and_metrics.sql'

    print(f"🔄 Esecuzione migration: {migration_file}")
    print("⚠️  ATTENZIONE: Questa operazione eliminerà tutti i dati nelle tabelle trace!")

    response = input("Continuare? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration annullata")
        return

    try:
        with app.app_context():
            # Leggi file SQL
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()

            # Esegui migration
            print("📝 Esecuzione SQL...")
            db.session.execute(db.text(sql))
            db.session.commit()

            print("✅ Migration completata con successo!")

            # Verifica tabelle
            print("\n📊 Verifica tabelle:")
            result = db.session.execute(db.text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('trace_elab', 'trace_elab_dett')
                ORDER BY table_name
            """))

            for row in result:
                print(f"  ✓ {row[0]}")

            # Mostra struttura trace_elab
            print("\n📋 Struttura trace_elab:")
            result = db.session.execute(db.text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'trace_elab'
                ORDER BY ordinal_position
            """))

            for row in result:
                print(f"  - {row[0]}: {row[1]}")

    except Exception as e:
        print(f"❌ Errore durante migration: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    run_migration()
