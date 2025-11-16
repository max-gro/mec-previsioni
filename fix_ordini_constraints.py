"""
Script per correggere i constraints sulla tabella file_ordini:
- Rimuove il constraint UNIQUE su filename (che causa duplicati quando file in INPUT/OUTPUT)
- Aggiunge constraint UNIQUE su filepath (ogni path completo deve essere unico)
- Rimuove eventuali duplicati prima di applicare il nuovo constraint

Esegui con: python fix_ordini_constraints.py
"""

from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

def fix_constraints():
    """Corregge i constraints sulla tabella file_ordini"""

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERRORE: DATABASE_URL non impostata")
        print("Imposta DATABASE_URL nel file .env o come variabile d'ambiente")
        print("Esempio: DATABASE_URL=postgresql://mec:cem@localhost:5432/mec_previsioni")
        return False

    print(f"Connessione al database...")
    print(f"URL: {db_url.split('@')[1] if '@' in db_url else db_url}\n")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # 1. Verifica che la tabella esista
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'file_ordini'
            );
        """)

        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("AVVISO: La tabella 'file_ordini' non esiste.")
            print("Probabilmente il database è nuovo. Esegui prima: python init_db.py")
            return False

        print("✓ Tabella 'file_ordini' trovata")

        # 2. Controlla duplicati su filepath prima di procedere
        cursor.execute("""
            SELECT filepath, COUNT(*) as cnt
            FROM file_ordini
            GROUP BY filepath
            HAVING COUNT(*) > 1;
        """)

        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n⚠ ATTENZIONE: Trovati {len(duplicates)} filepath duplicati:")
            for filepath, count in duplicates[:5]:  # Mostra primi 5
                print(f"  {filepath}: {count} occorrenze")

            print("\nRimozione duplicati (mantengo solo il più recente)...")
            cursor.execute("""
                DELETE FROM file_ordini a
                USING file_ordini b
                WHERE a.id_file_ordine < b.id_file_ordine
                AND a.filepath = b.filepath;
            """)
            removed = cursor.rowcount
            print(f"✓ Rimossi {removed} record duplicati")
        else:
            print("✓ Nessun duplicato trovato su filepath")

        # 3. Rimuovi constraint UNIQUE su filename (se esiste)
        print("\nRimozione constraint UNIQUE su filename...")
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'file_ordini'
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%filename%';
        """)

        filename_constraints = cursor.fetchall()
        for (constraint_name,) in filename_constraints:
            cursor.execute(f"ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS {constraint_name};")
            print(f"✓ Rimosso constraint: {constraint_name}")

        if not filename_constraints:
            print("✓ Nessun constraint su filename da rimuovere")

        # 4. Aggiungi constraint UNIQUE su filepath (se non esiste già)
        print("\nAggiunta constraint UNIQUE su filepath...")
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'file_ordini'
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%filepath%';
        """)

        filepath_constraints = cursor.fetchall()
        if filepath_constraints:
            print(f"✓ Constraint su filepath già esistente: {filepath_constraints[0][0]}")
        else:
            cursor.execute("""
                ALTER TABLE file_ordini
                ADD CONSTRAINT file_ordini_filepath_unique UNIQUE (filepath);
            """)
            print("✓ Aggiunto constraint UNIQUE su filepath")

        # 5. Verifica stato finale
        print("\n" + "="*60)
        print("RIEPILOGO CONSTRAINTS FINALI:")
        print("="*60)
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'file_ordini'
            ORDER BY constraint_type, constraint_name;
        """)

        for constraint_name, constraint_type in cursor.fetchall():
            print(f"  {constraint_type:<20} {constraint_name}")

        # Commit delle modifiche
        conn.commit()

        print("\n" + "="*60)
        print("✓ MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("="*60)
        print("\nOra puoi usare l'applicazione senza errori di duplicati.")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"\n✗ ERRORE DATABASE: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("="*60)
    print("SCRIPT DI MIGRAZIONE: Fix Constraints file_ordini")
    print("="*60)
    print("\nQuesta migrazione:")
    print("  1. Rimuove constraint UNIQUE su 'filename'")
    print("  2. Aggiunge constraint UNIQUE su 'filepath'")
    print("  3. Rimuove eventuali duplicati su filepath")
    print("\n" + "="*60 + "\n")

    try:
        success = fix_constraints()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Operazione annullata dall'utente")
        exit(1)
