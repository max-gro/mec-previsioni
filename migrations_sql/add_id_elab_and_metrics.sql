-- ============================================================================
-- Migration: Aggiunta id_elab e metriche alle tabelle trace
-- Data: 2025-11-20
-- Descrizione:
--   - Aggiunge campo id_elab per raggruppare operazioni di una elaborazione
--   - Aggiunge campi metriche (righe_totali, righe_ok, righe_errore, righe_warning)
--   - Rimuove campi inutilizzati (ts_inizio, ts_fine, durata_secondi, ecc.)
-- ============================================================================

-- STEP 1: Backup dati esistenti (opzionale, se vuoi conservarli)
-- CREATE TABLE trace_elab_backup AS SELECT * FROM trace_elab;
-- CREATE TABLE trace_elab_dett_backup AS SELECT * FROM trace_elab_dett;

-- STEP 2: Drop tabelle esistenti
DROP TABLE IF EXISTS trace_elab_dett CASCADE;
DROP TABLE IF EXISTS trace_elab CASCADE;

-- STEP 3: Ricrea trace_elab con nuovo schema
CREATE TABLE trace_elab (
    id_trace SERIAL PRIMARY KEY,
    id_elab INTEGER NOT NULL,                    -- NUOVO: identifica gruppo elaborazione
    id_file INTEGER NOT NULL,
    tipo_file VARCHAR(10) NOT NULL,              -- 'ORD', 'ANA', 'ROT'
    step VARCHAR(50) NOT NULL DEFAULT 'PROCESS', -- 'START', 'END', 'PROCESS', ecc.
    stato VARCHAR(20) NOT NULL DEFAULT 'OK',     -- 'OK', 'KO', 'WARN'
    messaggio TEXT,

    -- NUOVI campi metriche
    righe_totali INTEGER DEFAULT 0,
    righe_ok INTEGER DEFAULT 0,
    righe_errore INTEGER DEFAULT 0,
    righe_warning INTEGER DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Indici per performance
    CONSTRAINT trace_elab_tipo_file_check CHECK (tipo_file IN ('ORD', 'ANA', 'ROT')),
    CONSTRAINT trace_elab_stato_check CHECK (stato IN ('OK', 'KO', 'WARN'))
);

-- Indici
CREATE INDEX idx_trace_elab_id_elab ON trace_elab(id_elab);
CREATE INDEX idx_trace_elab_id_file ON trace_elab(id_file);
CREATE INDEX idx_trace_elab_tipo_file ON trace_elab(tipo_file);
CREATE INDEX idx_trace_elab_created_at ON trace_elab(created_at);

-- STEP 4: Ricrea trace_elab_dett con schema confermato
CREATE TABLE trace_elab_dett (
    id_trace_dett SERIAL PRIMARY KEY,
    id_trace INTEGER NOT NULL REFERENCES trace_elab(id_trace) ON DELETE CASCADE,
    record_pos INTEGER,           -- Numero riga/record
    record_data JSONB,            -- Dati del record (incluso 'key' se serve)
    messaggio TEXT,
    stato VARCHAR(20) NOT NULL DEFAULT 'OK',  -- 'OK', 'KO', 'WARN'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT trace_elab_dett_stato_check CHECK (stato IN ('OK', 'KO', 'WARN'))
);

-- Indici
CREATE INDEX idx_trace_elab_dett_id_trace ON trace_elab_dett(id_trace);
CREATE INDEX idx_trace_elab_dett_stato ON trace_elab_dett(stato);
CREATE INDEX idx_trace_elab_dett_record_data ON trace_elab_dett USING GIN (record_data);

-- STEP 5: Sequence per id_elab (parte da 1)
CREATE SEQUENCE IF NOT EXISTS seq_id_elab START 1;

-- ============================================================================
-- NOTE:
-- - id_elab viene generato con: SELECT nextval('seq_id_elab')
-- - Tutte le operazioni di una elaborazione condividono lo stesso id_elab
-- - righe_* vengono popolate dal codice Python durante elaborazione
-- - record_data è JSONB per query efficienti con operatori JSON
-- ============================================================================

-- STEP 6: Verifica
SELECT 'Migration completata con successo!' as status;
SELECT 'Tabelle ricreate:' as info;
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('trace_elab', 'trace_elab_dett')
ORDER BY table_name;
