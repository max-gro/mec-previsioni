-- ============================================================================
-- MIGRAZIONE: Aggiunta campi created_by e updated_by per tracking utenti
-- Data: 2025-11-17
-- Descrizione: Aggiunge i campi created_by e updated_by (FK a users.id_user)
--              alle tabelle: anagrafiche_file, rotture, ordini_acquisto
-- ============================================================================

-- IMPORTANTE: Questa migrazione è SAFE - aggiunge solo nuove colonne nullable
-- Non modifica dati esistenti, quindi non richiede backup obbligatorio
-- (ma è sempre raccomandato!)

BEGIN;

-- ============================================================================
-- STEP 1: Verifica tabelle esistenti
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename IN ('anagrafiche_file', 'rotture', 'ordini_acquisto', 'users');

    RAISE NOTICE '✓ Tabelle esistenti: % su 4', v_count;

    IF v_count < 4 THEN
        RAISE EXCEPTION 'ERRORE: Non tutte le tabelle richieste esistono! Trovate: %', v_count;
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Aggiungi colonne a anagrafiche_file
-- ============================================================================
RAISE NOTICE '📌 STEP 2: Aggiunta colonne a anagrafiche_file...';

DO $$
BEGIN
    -- Aggiungi created_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'anagrafiche_file' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE anagrafiche_file
        ADD COLUMN created_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna anagrafiche_file.created_by';
    ELSE
        RAISE NOTICE '  ⚠ anagrafiche_file.created_by già esistente';
    END IF;

    -- Aggiungi updated_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'anagrafiche_file' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE anagrafiche_file
        ADD COLUMN updated_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna anagrafiche_file.updated_by';
    ELSE
        RAISE NOTICE '  ⚠ anagrafiche_file.updated_by già esistente';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Aggiungi colonne a rotture
-- ============================================================================
RAISE NOTICE '📌 STEP 3: Aggiunta colonne a rotture...';

DO $$
BEGIN
    -- Aggiungi created_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rotture' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE rotture
        ADD COLUMN created_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna rotture.created_by';
    ELSE
        RAISE NOTICE '  ⚠ rotture.created_by già esistente';
    END IF;

    -- Aggiungi updated_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rotture' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE rotture
        ADD COLUMN updated_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna rotture.updated_by';
    ELSE
        RAISE NOTICE '  ⚠ rotture.updated_by già esistente';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Aggiungi colonne a ordini_acquisto
-- ============================================================================
RAISE NOTICE '📌 STEP 4: Aggiunta colonne a ordini_acquisto...';

DO $$
BEGIN
    -- Aggiungi created_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ordini_acquisto' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE ordini_acquisto
        ADD COLUMN created_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna ordini_acquisto.created_by';
    ELSE
        RAISE NOTICE '  ⚠ ordini_acquisto.created_by già esistente';
    END IF;

    -- Aggiungi updated_by
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ordini_acquisto' AND column_name = 'updated_by'
    ) THEN
        ALTER TABLE ordini_acquisto
        ADD COLUMN updated_by INTEGER REFERENCES users(id_user);
        RAISE NOTICE '  ✓ Aggiunta colonna ordini_acquisto.updated_by';
    ELSE
        RAISE NOTICE '  ⚠ ordini_acquisto.updated_by già esistente';
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Crea indici per performance (opzionale ma raccomandato)
-- ============================================================================
RAISE NOTICE '📌 STEP 5: Creazione indici...';

CREATE INDEX IF NOT EXISTS idx_anagrafiche_file_created_by ON anagrafiche_file(created_by);
CREATE INDEX IF NOT EXISTS idx_anagrafiche_file_updated_by ON anagrafiche_file(updated_by);
RAISE NOTICE '  ✓ Indici creati per anagrafiche_file';

CREATE INDEX IF NOT EXISTS idx_rotture_created_by ON rotture(created_by);
CREATE INDEX IF NOT EXISTS idx_rotture_updated_by ON rotture(updated_by);
RAISE NOTICE '  ✓ Indici creati per rotture';

CREATE INDEX IF NOT EXISTS idx_ordini_acquisto_created_by ON ordini_acquisto(created_by);
CREATE INDEX IF NOT EXISTS idx_ordini_acquisto_updated_by ON ordini_acquisto(updated_by);
RAISE NOTICE '  ✓ Indici creati per ordini_acquisto';

-- ============================================================================
-- STEP 6: VERIFICA FINALE
-- ============================================================================
RAISE NOTICE '📌 STEP 6: Verifica finale...';

DO $$
DECLARE
    r RECORD;
    v_ok BOOLEAN := TRUE;
BEGIN
    RAISE NOTICE ' ';
    RAISE NOTICE '📊 RIEPILOGO COLONNE AGGIUNTE:';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    FOR r IN
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name IN ('anagrafiche_file', 'rotture', 'ordini_acquisto')
        AND column_name IN ('created_by', 'updated_by')
        ORDER BY table_name, column_name
    LOOP
        RAISE NOTICE '✓ %.%: % (nullable: %)',
            r.table_name, r.column_name, r.data_type, r.is_nullable;
    END LOOP;

    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    -- Verifica foreign keys
    RAISE NOTICE ' ';
    RAISE NOTICE '🔗 FOREIGN KEYS:';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    FOR r IN
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name IN ('anagrafiche_file', 'rotture', 'ordini_acquisto')
        AND kcu.column_name IN ('created_by', 'updated_by')
        ORDER BY tc.table_name, kcu.column_name
    LOOP
        RAISE NOTICE '✓ %.% → %.%',
            r.table_name, r.column_name, r.foreign_table, r.foreign_column;
    END LOOP;

    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    -- Verifica indici
    RAISE NOTICE ' ';
    RAISE NOTICE '🔍 INDICI:';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    FOR r IN
        SELECT
            tablename,
            indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN ('anagrafiche_file', 'rotture', 'ordini_acquisto')
        AND (indexname LIKE '%created_by%' OR indexname LIKE '%updated_by%')
        ORDER BY tablename, indexname
    LOOP
        RAISE NOTICE '✓ %.%', r.tablename, r.indexname;
    END LOOP;

    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    RAISE NOTICE ' ';
    RAISE NOTICE '✅ MIGRAZIONE COMPLETATA CON SUCCESSO!';
    RAISE NOTICE ' ';
    RAISE NOTICE 'Campi aggiunti:';
    RAISE NOTICE '  • anagrafiche_file.created_by → users.id_user (FK)';
    RAISE NOTICE '  • anagrafiche_file.updated_by → users.id_user (FK)';
    RAISE NOTICE '  • rotture.created_by → users.id_user (FK)';
    RAISE NOTICE '  • rotture.updated_by → users.id_user (FK)';
    RAISE NOTICE '  • ordini_acquisto.created_by → users.id_user (FK)';
    RAISE NOTICE '  • ordini_acquisto.updated_by → users.id_user (FK)';
    RAISE NOTICE ' ';
    RAISE NOTICE '📝 NOTA: I campi sono nullable, i record esistenti avranno NULL.';
    RAISE NOTICE '         Per popolarli, aggiorna manualmente o tramite trigger.';
    RAISE NOTICE ' ';
END $$;

COMMIT;

-- ============================================================================
-- ESEMPI DI UTILIZZO
-- ============================================================================
/*

-- Esempio 1: Popolare created_by/updated_by per record esistenti con admin (id_user=1)
UPDATE anagrafiche_file
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;

UPDATE rotture
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;

UPDATE ordini_acquisto
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;

-- Esempio 2: Query per vedere chi ha creato/modificato i file
SELECT
    id_file_anagrafiche,
    filename,
    marca,
    u_created.username AS creato_da,
    u_updated.username AS modificato_da,
    created_at,
    updated_at
FROM anagrafiche_file af
LEFT JOIN users u_created ON af.created_by = u_created.id_user
LEFT JOIN users u_updated ON af.updated_by = u_updated.id_user
ORDER BY created_at DESC;

-- Esempio 3: Statistiche per utente
SELECT
    u.username,
    COUNT(DISTINCT af.id_file_anagrafiche) AS num_anagrafiche,
    COUNT(DISTINCT r.id_file_rotture) AS num_rotture,
    COUNT(DISTINCT oa.id_file_ordini_acquisto) AS num_ordini
FROM users u
LEFT JOIN anagrafiche_file af ON u.id_user = af.created_by
LEFT JOIN rotture r ON u.id_user = r.created_by
LEFT JOIN ordini_acquisto oa ON u.id_user = oa.created_by
GROUP BY u.id_user, u.username
ORDER BY num_anagrafiche + num_rotture + num_ordini DESC;

*/
