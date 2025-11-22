-- ============================================================================
-- MIGRAZIONE: Aggiunta tabelle pipeline STOCK (giacenze componenti)
-- Data: 2025-11-22
-- Descrizione: Crea le tabelle file_stock e stock per gestire le giacenze
--              dei componenti importate da file TSV
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. TABELLA FILE_STOCK (Pipeline Import Stock)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS file_stock_id_file_stock_seq START 1;

CREATE TABLE IF NOT EXISTS file_stock (
    id_file_stock INTEGER PRIMARY KEY DEFAULT nextval('file_stock_id_file_stock_seq'),
    anno INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    data_acquisizione TIMESTAMP NOT NULL DEFAULT NOW(),
    data_elaborazione TIMESTAMP,
    esito VARCHAR(50) DEFAULT 'Da processare',
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by INTEGER NOT NULL DEFAULT 0 REFERENCES users(id_user),
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);

CREATE INDEX IF NOT EXISTS idx_file_stock_anno ON file_stock(anno);
CREATE INDEX IF NOT EXISTS idx_file_stock_esito ON file_stock(esito);
CREATE INDEX IF NOT EXISTS idx_file_stock_created_by ON file_stock(created_by);
CREATE INDEX IF NOT EXISTS idx_file_stock_updated_by ON file_stock(updated_by);

COMMENT ON TABLE file_stock IS 'File stock importati (TSV/Excel giacenze componenti)';
COMMENT ON COLUMN file_stock.anno IS 'Anno di riferimento del file';
COMMENT ON COLUMN file_stock.esito IS 'Stato elaborazione: Da processare, Elaborato, Errore';

-- ============================================================================
-- 2. TABELLA STOCK (Giacenze Componenti)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS stock_id_stock_seq START 1;

CREATE TABLE IF NOT EXISTS stock (
    id_stock INTEGER PRIMARY KEY DEFAULT nextval('stock_id_stock_seq'),
    id_file_stock INTEGER NOT NULL REFERENCES file_stock(id_file_stock) ON DELETE CASCADE,
    cod_componente VARCHAR(100) NOT NULL REFERENCES componenti(cod_componente),
    qtà INTEGER NOT NULL DEFAULT 0,
    data_rilevazione DATE NOT NULL,
    ubicazione VARCHAR(100),
    lotto VARCHAR(100),
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by INTEGER NOT NULL DEFAULT 0 REFERENCES users(id_user),
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);

CREATE INDEX IF NOT EXISTS idx_stock_file ON stock(id_file_stock);
CREATE INDEX IF NOT EXISTS idx_stock_componente ON stock(cod_componente);
CREATE INDEX IF NOT EXISTS idx_stock_data_rilevazione ON stock(data_rilevazione);
CREATE INDEX IF NOT EXISTS idx_stock_created_by ON stock(created_by);
CREATE INDEX IF NOT EXISTS idx_stock_updated_by ON stock(updated_by);

-- Index composito per query per componente e data
CREATE INDEX IF NOT EXISTS idx_stock_comp_data ON stock(cod_componente, data_rilevazione);

COMMENT ON TABLE stock IS 'Giacenze componenti (snapshot da file importati)';
COMMENT ON COLUMN stock.cod_componente IS 'Codice componente (FK a componenti)';
COMMENT ON COLUMN stock.qtà IS 'Quantità in giacenza';
COMMENT ON COLUMN stock.data_rilevazione IS 'Data della rilevazione giacenza';
COMMENT ON COLUMN stock.ubicazione IS 'Ubicazione fisica del componente (es. Magazzino A, Scaffale 12)';
COMMENT ON COLUMN stock.lotto IS 'Numero lotto di produzione';

-- ============================================================================
-- VERIFICA FINALE
-- ============================================================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename IN ('file_stock', 'stock');

    RAISE NOTICE '✓ Tabelle stock create: % su 2', v_count;

    IF v_count = 2 THEN
        RAISE NOTICE '✓ MIGRAZIONE STOCK COMPLETATA CON SUCCESSO';
        RAISE NOTICE ' ';
        RAISE NOTICE 'Riepilogo tabelle:';
        RAISE NOTICE '  - file_stock: Tracciamento file TSV importati';
        RAISE NOTICE '  - stock: Righe giacenze componenti';
        RAISE NOTICE ' ';
        RAISE NOTICE '✓ Pronto per import pipeline stock!';
    ELSE
        RAISE WARNING '⚠ ATTENZIONE: Solo % tabelle su 2 sono state create', v_count;
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- ESEMPI DI UTILIZZO
-- ============================================================================
/*

-- Query giacenze per componente
SELECT s.cod_componente, c.componente_it, s.qtà, s.data_rilevazione, s.ubicazione
FROM stock s
LEFT JOIN componenti c ON s.cod_componente = c.cod_componente
WHERE s.cod_componente = 'COMP-001'
ORDER BY s.data_rilevazione DESC;

-- Giacenze correnti (ultima rilevazione per ogni componente)
WITH last_dates AS (
    SELECT cod_componente, MAX(data_rilevazione) as ultima_data
    FROM stock
    GROUP BY cod_componente
)
SELECT s.cod_componente, c.componente_it, s.qtà, s.data_rilevazione, s.ubicazione
FROM stock s
INNER JOIN last_dates ld ON s.cod_componente = ld.cod_componente
    AND s.data_rilevazione = ld.ultima_data
LEFT JOIN componenti c ON s.cod_componente = c.cod_componente
ORDER BY s.qtà ASC;

-- Componenti sotto scorta (esempio: meno di 10 unità)
WITH last_dates AS (
    SELECT cod_componente, MAX(data_rilevazione) as ultima_data
    FROM stock
    GROUP BY cod_componente
)
SELECT s.cod_componente, c.componente_it, s.qtà, s.ubicazione
FROM stock s
INNER JOIN last_dates ld ON s.cod_componente = ld.cod_componente
    AND s.data_rilevazione = ld.ultima_data
LEFT JOIN componenti c ON s.cod_componente = c.cod_componente
WHERE s.qtà < 10
ORDER BY s.qtà ASC;

*/
