-- ============================================================================
-- MIGRAZIONE: Conversione campi codice da INTEGER a VARCHAR
-- Data: 2025-11-17
-- Descrizione: Converte i campi cod_* da INTEGER a VARCHAR(50) mantenendo i dati
-- ============================================================================

-- IMPORTANTE: Questo script richiede PostgreSQL 9.1+
-- Per database in produzione, creare SEMPRE un backup prima di eseguire!

-- Verifica database in uso
SELECT current_database(), version();

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
    AND tablename IN ('controparti', 'modelli', 'file_ordini', 'ordini');

    RAISE NOTICE '✓ Tabelle esistenti: % su 4', v_count;

    IF v_count < 4 THEN
        RAISE EXCEPTION 'ERRORE: Non tutte le tabelle richieste esistono! Trovate: %', v_count;
    END IF;
END $$;

-- ============================================================================
-- STEP 2: DROP FOREIGN KEY CONSTRAINTS (temporaneo)
-- ============================================================================
RAISE NOTICE '📌 STEP 2: Rimozione temporanea foreign keys...';

-- Drop FK da file_ordini → controparti
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'file_ordini_cod_seller_fkey'
        AND table_name = 'file_ordini'
    ) THEN
        ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS file_ordini_cod_seller_fkey;
        RAISE NOTICE '  ✓ Rimossa FK: file_ordini.cod_seller → controparti';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'file_ordini_cod_buyer_fkey'
        AND table_name = 'file_ordini'
    ) THEN
        ALTER TABLE file_ordini DROP CONSTRAINT IF EXISTS file_ordini_cod_buyer_fkey;
        RAISE NOTICE '  ✓ Rimossa FK: file_ordini.cod_buyer → controparti';
    END IF;
END $$;

-- Drop FK da ordini → modelli
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'ordini_cod_modello_fkey'
        AND table_name = 'ordini'
    ) THEN
        ALTER TABLE ordini DROP CONSTRAINT IF EXISTS ordini_cod_modello_fkey;
        RAISE NOTICE '  ✓ Rimossa FK: ordini.cod_modello → modelli';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: CONVERSIONE controparti.cod_controparte (PK)
-- ============================================================================
RAISE NOTICE '📌 STEP 3: Conversione controparti.cod_controparte...';

DO $$
DECLARE
    v_type TEXT;
BEGIN
    -- Verifica tipo attuale
    SELECT data_type INTO v_type
    FROM information_schema.columns
    WHERE table_name = 'controparti' AND column_name = 'cod_controparte';

    IF v_type = 'integer' THEN
        -- Converti INTEGER → VARCHAR mantenendo i dati
        ALTER TABLE controparti
        ALTER COLUMN cod_controparte TYPE VARCHAR(50)
        USING cod_controparte::TEXT;

        RAISE NOTICE '  ✓ Convertito controparti.cod_controparte: INTEGER → VARCHAR(50)';
    ELSIF v_type LIKE 'character%' THEN
        RAISE NOTICE '  ⚠ controparti.cod_controparte è già VARCHAR (%)!', v_type;
    ELSE
        RAISE WARNING '  ⚠ Tipo imprevisto per cod_controparte: %', v_type;
    END IF;
END $$;

-- ============================================================================
-- STEP 4: CONVERSIONE modelli.cod_modello (PK)
-- ============================================================================
RAISE NOTICE '📌 STEP 4: Conversione modelli.cod_modello...';

DO $$
DECLARE
    v_type TEXT;
BEGIN
    SELECT data_type INTO v_type
    FROM information_schema.columns
    WHERE table_name = 'modelli' AND column_name = 'cod_modello';

    IF v_type = 'integer' THEN
        ALTER TABLE modelli
        ALTER COLUMN cod_modello TYPE VARCHAR(50)
        USING cod_modello::TEXT;

        RAISE NOTICE '  ✓ Convertito modelli.cod_modello: INTEGER → VARCHAR(50)';
    ELSIF v_type LIKE 'character%' THEN
        RAISE NOTICE '  ⚠ modelli.cod_modello è già VARCHAR (%)!', v_type;
    ELSE
        RAISE WARNING '  ⚠ Tipo imprevisto per cod_modello: %', v_type;
    END IF;
END $$;

-- ============================================================================
-- STEP 5: CONVERSIONE file_ordini.cod_seller e cod_buyer (FK)
-- ============================================================================
RAISE NOTICE '📌 STEP 5: Conversione file_ordini.cod_seller e cod_buyer...';

DO $$
DECLARE
    v_type_seller TEXT;
    v_type_buyer TEXT;
BEGIN
    -- Verifica cod_seller
    SELECT data_type INTO v_type_seller
    FROM information_schema.columns
    WHERE table_name = 'file_ordini' AND column_name = 'cod_seller';

    IF v_type_seller = 'integer' THEN
        ALTER TABLE file_ordini
        ALTER COLUMN cod_seller TYPE VARCHAR(50)
        USING cod_seller::TEXT;

        RAISE NOTICE '  ✓ Convertito file_ordini.cod_seller: INTEGER → VARCHAR(50)';
    ELSIF v_type_seller LIKE 'character%' THEN
        RAISE NOTICE '  ⚠ file_ordini.cod_seller è già VARCHAR (%)!', v_type_seller;
    END IF;

    -- Verifica cod_buyer
    SELECT data_type INTO v_type_buyer
    FROM information_schema.columns
    WHERE table_name = 'file_ordini' AND column_name = 'cod_buyer';

    IF v_type_buyer = 'integer' THEN
        ALTER TABLE file_ordini
        ALTER COLUMN cod_buyer TYPE VARCHAR(50)
        USING cod_buyer::TEXT;

        RAISE NOTICE '  ✓ Convertito file_ordini.cod_buyer: INTEGER → VARCHAR(50)';
    ELSIF v_type_buyer LIKE 'character%' THEN
        RAISE NOTICE '  ⚠ file_ordini.cod_buyer è già VARCHAR (%)!', v_type_buyer;
    END IF;
END $$;

-- ============================================================================
-- STEP 6: CONVERSIONE ordini.cod_modello (FK)
-- ============================================================================
RAISE NOTICE '📌 STEP 6: Conversione ordini.cod_modello...';

DO $$
DECLARE
    v_type TEXT;
BEGIN
    SELECT data_type INTO v_type
    FROM information_schema.columns
    WHERE table_name = 'ordini' AND column_name = 'cod_modello';

    IF v_type = 'integer' THEN
        ALTER TABLE ordini
        ALTER COLUMN cod_modello TYPE VARCHAR(50)
        USING cod_modello::TEXT;

        RAISE NOTICE '  ✓ Convertito ordini.cod_modello: INTEGER → VARCHAR(50)';
    ELSIF v_type LIKE 'character%' THEN
        RAISE NOTICE '  ⚠ ordini.cod_modello è già VARCHAR (%)!', v_type;
    ELSE
        RAISE WARNING '  ⚠ Tipo imprevisto per cod_modello: %', v_type;
    END IF;
END $$;

-- ============================================================================
-- STEP 7: RICREA FOREIGN KEY CONSTRAINTS
-- ============================================================================
RAISE NOTICE '📌 STEP 7: Ricostruzione foreign keys...';

-- FK da file_ordini → controparti
ALTER TABLE file_ordini
ADD CONSTRAINT file_ordini_cod_seller_fkey
FOREIGN KEY (cod_seller) REFERENCES controparti(cod_controparte);
RAISE NOTICE '  ✓ Ricreata FK: file_ordini.cod_seller → controparti.cod_controparte';

ALTER TABLE file_ordini
ADD CONSTRAINT file_ordini_cod_buyer_fkey
FOREIGN KEY (cod_buyer) REFERENCES controparti(cod_controparte);
RAISE NOTICE '  ✓ Ricreata FK: file_ordini.cod_buyer → controparti.cod_controparte';

-- FK da ordini → modelli
ALTER TABLE ordini
ADD CONSTRAINT ordini_cod_modello_fkey
FOREIGN KEY (cod_modello) REFERENCES modelli(cod_modello);
RAISE NOTICE '  ✓ Ricreata FK: ordini.cod_modello → modelli.cod_modello';

-- ============================================================================
-- STEP 8: VERIFICA FINALE
-- ============================================================================
RAISE NOTICE '📌 STEP 8: Verifica finale...';

DO $$
DECLARE
    r RECORD;
    v_ok BOOLEAN := TRUE;
BEGIN
    RAISE NOTICE ' ';
    RAISE NOTICE '📊 RIEPILOGO CONVERSIONI:';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    FOR r IN
        SELECT
            table_name,
            column_name,
            data_type,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name IN ('controparti', 'modelli', 'file_ordini', 'ordini')
        AND column_name IN ('cod_controparte', 'cod_modello', 'cod_seller', 'cod_buyer', 'cod_ordine')
        ORDER BY table_name, column_name
    LOOP
        IF r.data_type LIKE 'character%' THEN
            RAISE NOTICE '✓ %.%: % (%)',
                r.table_name, r.column_name, r.data_type, r.character_maximum_length;
        ELSE
            RAISE NOTICE '✗ %.%: % (NON VARCHAR!)',
                r.table_name, r.column_name, r.data_type;
            v_ok := FALSE;
        END IF;
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
        AND tc.table_name IN ('file_ordini', 'ordini')
        AND kcu.column_name IN ('cod_seller', 'cod_buyer', 'cod_modello')
        ORDER BY tc.table_name, kcu.column_name
    LOOP
        RAISE NOTICE '✓ %.% → %.%',
            r.table_name, r.column_name, r.foreign_table, r.foreign_column;
    END LOOP;

    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';

    IF v_ok THEN
        RAISE NOTICE ' ';
        RAISE NOTICE '✅ MIGRAZIONE COMPLETATA CON SUCCESSO!';
        RAISE NOTICE ' ';
        RAISE NOTICE 'I seguenti campi sono ora alfanumerici (VARCHAR):';
        RAISE NOTICE '  • controparti.cod_controparte (PK)';
        RAISE NOTICE '  • modelli.cod_modello (PK)';
        RAISE NOTICE '  • file_ordini.cod_seller (FK)';
        RAISE NOTICE '  • file_ordini.cod_buyer (FK)';
        RAISE NOTICE '  • ordini.cod_modello (FK)';
        RAISE NOTICE ' ';
    ELSE
        RAISE EXCEPTION 'Alcuni campi non sono stati convertiti correttamente!';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- TEST POST-MIGRAZIONE
-- ============================================================================
/*
-- Test 1: Inserimento controparte con codice alfanumerico
INSERT INTO controparti (cod_controparte, controparte, created_by)
VALUES ('CLI-ABC123', 'Cliente Test Alfanumerico', 1);

-- Test 2: Inserimento modello con codice alfanumerico
INSERT INTO modelli (cod_modello, cod_modello_norm, nome_modello, created_by)
VALUES ('MOD-XYZ-789', 'MODXYZ789', 'Modello Test Alfanumerico', 1);

-- Test 3: Query JOIN per verificare FK
SELECT
    fo.id_file_ordine,
    fo.cod_seller,
    cs.controparte AS seller_name,
    fo.cod_buyer,
    cb.controparte AS buyer_name
FROM file_ordini fo
LEFT JOIN controparti cs ON fo.cod_seller = cs.cod_controparte
LEFT JOIN controparti cb ON fo.cod_buyer = cb.cod_controparte;

-- Test 4: Query ordini con modelli
SELECT
    o.cod_ordine,
    o.cod_modello,
    m.nome_modello
FROM ordini o
INNER JOIN modelli m ON o.cod_modello = m.cod_modello;

-- Cleanup test
DELETE FROM controparti WHERE cod_controparte = 'CLI-ABC123';
DELETE FROM modelli WHERE cod_modello = 'MOD-XYZ-789';
*/
