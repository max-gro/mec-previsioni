"""
Script per ispezionare lo schema del database
"""
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

def inspect_database():
    """Ispeziona lo schema del database PostgreSQL"""

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL non impostata")
        return

    print(f"Connessione a: {db_url.split('@')[1] if '@' in db_url else db_url}\n")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Lista tutte le tabelle
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()
        print("=== TABELLE NEL DATABASE ===")
        for table in tables:
            print(f"  - {table['table_name']}")

        # Cerca tabelle che contengono 'ordini'
        ordini_tables = [t['table_name'] for t in tables if 'ordini' in t['table_name'].lower()]

        if not ordini_tables:
            print("\nNessuna tabella trovata con 'ordini' nel nome")
            return

        # Ispeziona ogni tabella ordini
        for table_name in ordini_tables:
            print(f"\n{'='*60}")
            print(f"TABELLA: {table_name}")
            print(f"{'='*60}")

            # Colonne
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))

            columns = cursor.fetchall()
            print("\nCOLONNE:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  {col['column_name']:<30} {col['data_type']:<20} {nullable}{default}")

            # Constraints
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = %s
                ORDER BY tc.constraint_type, tc.constraint_name;
            """, (table_name,))

            constraints = cursor.fetchall()
            if constraints:
                print("\nCONSTRAINTS:")
                for const in constraints:
                    print(f"  {const['constraint_type']:<20} {const['constraint_name']:<40} ({const['column_name']})")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"ERRORE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    inspect_database()
