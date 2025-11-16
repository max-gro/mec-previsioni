"""
Script per correggere i constraints sulla tabella file_ordini:
- Rimuove eventuali duplicati su filename (errore utente: stesso file in anni diversi)
- Rimuove constraint sbagliati (es. su filepath o filename+anno)
- Assicura che ci sia il constraint UNIQUE solo su filename

LOGICA CORRETTA:
- Il filename è unico in assoluto (un file appare una volta sola nel DB)
- Quando il file viene elaborato, viene SPOSTATO da INPUT a OUTPUT
- Il record DB viene aggiornato (filepath cambia, esito diventa 'Processato')

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

    # Fix: rimuovi '+psycopg2' se presente
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://", 1)


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

        # 2. Controlla duplicati su FILENAME (errore utente: stesso file in anni diversi)
        cursor.execute("""
            SELECT filename, COUNT(*) as cnt, string_agg(CAST(anno AS TEXT), ', ') as anni
            FROM file_ordini
            GROUP BY filename
            HAVING COUNT(*) > 1;
        """)

        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n⚠ ATTENZIONE: Trovati {len(duplicates)} filename duplicati:")
            print("Questo è probabilmente un errore utente (stesso file in anni diversi)")
            for filename, count, anni in duplicates[:10]:  # Mostra primi 10
                print(f"  {filename}: {count} occorrenze (anni: {anni})")

            risposta = input("\nVuoi rimuovere i duplicati mantenendo solo il più recente? [s/N]: ")
            if risposta.lower() == 's':
                print("\nRimozione duplicati (mantengo solo il più recente)...")
                cursor.execute("""
                    DELETE FROM file_ordini a
                    USING file_ordini b
                    WHERE a.id_file_ordine < b.id_file_ordine
                    AND a.filename = b.filename;
                """)
                removed = cursor.rowcount
                print(f"✓ Rimossi {removed} record duplicati")
            else:
                print("✗ Operazione annullata. Risolvi manualmente i duplicati prima di continuare.")
                return False
        else:
            print("✓ Nessun duplicato trovato su filename")

        # 3. Rimuovi constraint sbagliati (es. su filepath o filename+anno)
        print("\nRimozione constraint sbagliati...")
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'file_ordini'
            AND constraint_type = 'UNIQUE'
            AND constraint_name NOT LIKE '%filename%'
            AND constraint_name NOT LIKE '%pkey%';
        """)

        wrong_constraints = cursor.fetchall()
        for (constraint_name,) in wrong_constraints:
            cursor.execute(f"ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS {constraint_name};")
            print(f"✓ Rimosso constraint sbagliato: {constraint_name}")

        if not wrong_constraints:
            print("✓ Nessun constraint sbagliato trovato")

        # 4. Assicura che ci sia il constraint UNIQUE su filename
        print("\nVerifica constraint UNIQUE su filename...")
        cursor.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'file_ordini'
            AND tc.constraint_type = 'UNIQUE'
            AND kcu.column_name = 'filename'
            AND NOT EXISTS (
                SELECT 1 FROM information_schema.key_column_usage kcu2
                WHERE kcu2.constraint_name = tc.constraint_name
                AND kcu2.column_name != 'filename'
            );
        """)

        filename_constraint = cursor.fetchall()
        if filename_constraint:
            print(f"✓ Constraint UNIQUE su filename già esistente: {filename_constraint[0][0]}")
        else:
            print("Aggiunta constraint UNIQUE su filename...")
            cursor.execute("""
                ALTER TABLE file_ordini
                ADD CONSTRAINT file_ordini_filename_key UNIQUE (filename);
            """)
            print("✓ Aggiunto constraint UNIQUE su filename")

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
    print("  1. Controlla e rimuove duplicati su filename")
    print("  2. Rimuove constraint sbagliati (es. su filepath)")
    print("  3. Assicura constraint UNIQUE solo su filename")
    print("\nLOGICA CORRETTA:")
    print("  - Filename è unico in assoluto")
    print("  - File spostato INPUT→OUTPUT = aggiornamento record, non duplicato")
    print("\n" + "="*60 + "\n")

    try:
        success = fix_constraints()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Operazione annullata dall'utente")
        exit(1)
