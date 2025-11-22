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
CREATE TABLE IF NOT EXISTS public.file_stock (
	id_file_stock serial4 NOT NULL,
	anno int4 NOT NULL,
	filename varchar(255) NOT NULL,
	filepath varchar(500) NOT NULL,
	data_acquisizione timestamp DEFAULT now() NOT NULL,
	data_elaborazione timestamp NULL,
	esito varchar(50) DEFAULT 'Da processare'::character varying NULL,
	note text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	created_by int4 DEFAULT 0 NOT NULL,
	updated_at timestamp NULL,
	updated_by int4 DEFAULT 0 NULL,
	CONSTRAINT file_stock_pkey PRIMARY KEY (id_file_stock),
	CONSTRAINT file_stock_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id_user) ON DELETE SET DEFAULT,
	CONSTRAINT file_stock_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id_user) ON DELETE SET DEFAULT
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
CREATE TABLE IF NOT EXISTS public.stock (
    id_stock serial4 NOT NULL,
    id_file_stock INTEGER NOT NULL,
    cod_componente VARCHAR(100),
    -- Magazzino
  	warehouse VARCHAR(100), 							-- Magazzino (A, B, C...)
  	ubicazione VARCHAR(100), 							-- Scaffale/posizione
  	lotto VARCHAR(100),
  	-- Giacenze
  	giacenza_disponibile INTEGER DEFAULT 0,
  	giacenza_impegnata INTEGER DEFAULT 0,    			-- Riservata per ordini clienti
  	giacenza_fisica INTEGER DEFAULT 0,       			-- Totale fisico in magazzino
  	-- Soglie
  	scorta_minima INTEGER,                   			-- Sotto questo = allarme
  	scorta_massima INTEGER,
  	punto_riordino INTEGER,                  			-- Quando ordinare
  	lead_time_days INTEGER, 							-- Tempo riordino
  	-- Metadata
  	data_snapshot TIMESTAMP DEFAULT NOW() NOT NULL,   	-- Quando è stato fatto export Mexal
  	data_stock TIMESTAMP,								-- Data stock
  	flag_corrente BOOLEAN NOT NULL DEFAULT FALSE,		-- Identifica lo stock corrente (più recente)
	-- Audit
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	created_by int4 DEFAULT 0 NOT NULL,
	updated_at timestamp NULL,
	updated_by int4 DEFAULT 0 NULL,
	CONSTRAINT stock_pkey PRIMARY KEY (id_stock),
	CONSTRAINT stock_file_stock_fkey FOREIGN KEY (id_file_stock) REFERENCES file_stock(id_file_stock) ON DELETE CASCADE,
	CONSTRAINT stock_componente_fkey FOREIGN KEY (cod_componente) REFERENCES componenti(cod_componente) ON DELETE CASCADE,
	CONSTRAINT stock_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id_user) ON DELETE SET DEFAULT,
	CONSTRAINT stock_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users(id_user) ON DELETE SET DEFAULT
);

CREATE INDEX IF NOT EXISTS idx_stock_file ON stock(id_file_stock);
CREATE INDEX IF NOT EXISTS idx_stock_componente ON stock(cod_componente);
CREATE INDEX IF NOT EXISTS idx_stock_data_snapshot ON stock(data_snapshot);
CREATE INDEX IF NOT EXISTS idx_stock_flag_corrente ON stock(flag_corrente);
CREATE INDEX IF NOT EXISTS idx_stock_warehouse ON stock(warehouse);
CREATE INDEX IF NOT EXISTS idx_stock_created_by ON stock(created_by);
CREATE INDEX IF NOT EXISTS idx_stock_updated_by ON stock(updated_by);

-- Index composito per query per componente e data
CREATE INDEX IF NOT EXISTS idx_stock_comp_data ON stock(cod_componente, data_snapshot);

COMMENT ON TABLE stock IS 'Giacenze componenti (snapshot da file importati)';
COMMENT ON COLUMN stock.cod_componente IS 'Codice componente (FK a componenti)';
COMMENT ON COLUMN stock.giacenza_disponibile IS 'Quantità disponibile';
COMMENT ON COLUMN stock.giacenza_impegnata IS 'Quantità impegnata per ordini clienti';
COMMENT ON COLUMN stock.giacenza_fisica IS 'Quantità fisica totale in magazzino';
COMMENT ON COLUMN stock.data_snapshot IS 'Data della rilevazione giacenza (export Mexal)';
COMMENT ON COLUMN stock.data_stock IS 'Data stock';
COMMENT ON COLUMN stock.flag_corrente IS 'TRUE se è lo stock corrente (più recente)';
COMMENT ON COLUMN stock.ubicazione IS 'Ubicazione fisica del componente (es. Scaffale 12)';
COMMENT ON COLUMN stock.warehouse IS 'Magazzino (A, B, C...)';
COMMENT ON COLUMN stock.lotto IS 'Numero lotto di produzione';
COMMENT ON COLUMN stock.scorta_minima IS 'Soglia minima - sotto genera allarme';
COMMENT ON COLUMN stock.punto_riordino IS 'Soglia riordino - quando ordinare';
COMMENT ON COLUMN stock.lead_time_days IS 'Tempo di riordino in giorni';

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
        RAISE NOTICE '  - stock: Righe giacenze componenti con warehouse, soglie, flag_corrente';
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

-- Query giacenze correnti (flag_corrente = TRUE)
SELECT s.cod_componente, c.componente_it,
       s.giacenza_disponibile, s.giacenza_impegnata, s.giacenza_fisica,
       s.warehouse, s.ubicazione, s.data_snapshot
FROM stock s
LEFT JOIN componenti c ON s.cod_componente = c.cod_componente
WHERE s.flag_corrente = TRUE
ORDER BY s.giacenza_disponibile ASC;

-- Componenti sotto scorta minima (alert)
SELECT s.cod_componente, c.componente_it,
       s.giacenza_disponibile, s.scorta_minima, s.punto_riordino,
       s.warehouse
FROM stock s
LEFT JOIN componenti c ON s.cod_componente = c.cod_componente
WHERE s.flag_corrente = TRUE
  AND s.scorta_minima IS NOT NULL
  AND s.giacenza_disponibile < s.scorta_minima
ORDER BY s.giacenza_disponibile ASC;

-- Storico giacenze per componente
SELECT data_snapshot, giacenza_disponibile, giacenza_fisica, warehouse, flag_corrente
FROM stock
WHERE cod_componente = 'PCB-MAIN-0001'
ORDER BY data_snapshot DESC;

-- Aggiornamento flag_corrente dopo nuovo import
-- (prima resetta tutti, poi imposta il nuovo)
UPDATE stock SET flag_corrente = FALSE WHERE flag_corrente = TRUE;
UPDATE stock SET flag_corrente = TRUE WHERE data_snapshot = (SELECT MAX(data_snapshot) FROM stock);

*/
