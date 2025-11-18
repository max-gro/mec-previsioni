-- ============================================================================
-- MIGRAZIONE: Aggiunta tabelle business con campi codice alfanumerici
-- Data: 2025-11-17
-- Descrizione: Crea le tabelle controparti, modelli, file_ordini, ordini,
--              trace_elaborazioni_file, trace_elaborazioni_record
--              con campi cod_* già impostati come VARCHAR (alfanumerici)
-- ============================================================================

-- IMPORTANTE: Eseguire questo script solo se le tabelle non esistono già!
-- Verificare prima con: SELECT tablename FROM pg_tables WHERE schemaname = 'public';

BEGIN;

-- ============================================================================
-- 1. TABELLA CONTROPARTI (Clienti/Fornitori)
-- ============================================================================
CREATE TABLE IF NOT EXISTS controparti (
    cod_controparte VARCHAR(50) PRIMARY KEY,
    controparte VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);

CREATE INDEX IF NOT EXISTS idx_controparti_controparte ON controparti(controparte);
CREATE INDEX IF NOT EXISTS idx_controparti_created_by ON controparti(created_by);
CREATE INDEX IF NOT EXISTS idx_controparti_updated_by ON controparti(updated_by);

COMMENT ON TABLE controparti IS 'Anagrafica controparti (clienti/fornitori)';
COMMENT ON COLUMN controparti.cod_controparte IS 'Codice controparte alfanumerico (chiave primaria)';

-- ============================================================================
-- 2. TABELLA MODELLI (Prodotti/Apparecchi)
-- ============================================================================
CREATE TABLE IF NOT EXISTS modelli (
    cod_modello VARCHAR(50) PRIMARY KEY,
    cod_modello_norm VARCHAR(100) NOT NULL,
    cod_modello_fabbrica VARCHAR(100),
    nome_modello VARCHAR(200),
    nome_modello_it VARCHAR(200),
    divisione VARCHAR(100),
    marca VARCHAR(100),
    desc_modello TEXT,
    produttore VARCHAR(200),
    famiglia VARCHAR(100),
    tipo VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user),
    updated_from VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_modelli_norm ON modelli(cod_modello_norm);
CREATE INDEX IF NOT EXISTS idx_modelli_marca ON modelli(marca);
CREATE INDEX IF NOT EXISTS idx_modelli_divisione ON modelli(divisione);
CREATE INDEX IF NOT EXISTS idx_modelli_famiglia ON modelli(famiglia);
CREATE INDEX IF NOT EXISTS idx_modelli_created_by ON modelli(created_by);
CREATE INDEX IF NOT EXISTS idx_modelli_updated_by ON modelli(updated_by);

COMMENT ON TABLE modelli IS 'Anagrafica modelli prodotti';
COMMENT ON COLUMN modelli.cod_modello IS 'Codice modello alfanumerico (chiave primaria)';
COMMENT ON COLUMN modelli.cod_modello_norm IS 'Codice modello normalizzato';
COMMENT ON COLUMN modelli.cod_modello_fabbrica IS 'Codice modello del fabbricante';

-- ============================================================================
-- 3. TABELLA FILE_ORDINI (Testata ordini da file)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS file_ordini_id_file_ordine_seq START 1;

CREATE TABLE IF NOT EXISTS file_ordini (
    id_file_ordine INTEGER PRIMARY KEY DEFAULT nextval('file_ordini_id_file_ordine_seq'),
    anno INTEGER NOT NULL,
    marca VARCHAR(100),
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    data_acquisizione DATE NOT NULL,
    data_elaborazione TIMESTAMP,
    esito VARCHAR(50) DEFAULT 'Da processare',
    note TEXT,
    cod_seller VARCHAR(50) REFERENCES controparti(cod_controparte),
    cod_buyer VARCHAR(50) REFERENCES controparti(cod_controparte),
    data_ordine DATE,
    oggetto_ordine TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);

CREATE INDEX IF NOT EXISTS idx_file_ordini_anno ON file_ordini(anno);
CREATE INDEX IF NOT EXISTS idx_file_ordini_marca ON file_ordini(marca);
CREATE INDEX IF NOT EXISTS idx_file_ordini_esito ON file_ordini(esito);
CREATE INDEX IF NOT EXISTS idx_file_ordini_seller ON file_ordini(cod_seller);
CREATE INDEX IF NOT EXISTS idx_file_ordini_buyer ON file_ordini(cod_buyer);
CREATE INDEX IF NOT EXISTS idx_file_ordini_data_ordine ON file_ordini(data_ordine);
CREATE INDEX IF NOT EXISTS idx_file_ordini_created_by ON file_ordini(created_by);
CREATE INDEX IF NOT EXISTS idx_file_ordini_updated_by ON file_ordini(updated_by);

COMMENT ON TABLE file_ordini IS 'Testata ordini estratti da file';
COMMENT ON COLUMN file_ordini.cod_seller IS 'Codice venditore alfanumerico (FK a controparti)';
COMMENT ON COLUMN file_ordini.cod_buyer IS 'Codice acquirente alfanumerico (FK a controparti)';

-- ============================================================================
-- 4. TABELLA ORDINI (Righe ordine)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ordini (
    ordine_modello_pk VARCHAR(200) PRIMARY KEY,
    id_file_ordine INTEGER NOT NULL REFERENCES file_ordini(id_file_ordine) ON DELETE CASCADE,
    cod_ordine VARCHAR(100) NOT NULL,
    cod_modello VARCHAR(50) NOT NULL REFERENCES modelli(cod_modello),
    brand VARCHAR(100),
    item VARCHAR(200),
    ean VARCHAR(50),
    prezzo_eur NUMERIC(10, 2),
    qta INTEGER,
    importo_eur NUMERIC(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);

CREATE INDEX IF NOT EXISTS idx_ordini_file_ordine ON ordini(id_file_ordine);
CREATE INDEX IF NOT EXISTS idx_ordini_cod_ordine ON ordini(cod_ordine);
CREATE INDEX IF NOT EXISTS idx_ordini_cod_modello ON ordini(cod_modello);
CREATE INDEX IF NOT EXISTS idx_ordini_brand ON ordini(brand);
CREATE INDEX IF NOT EXISTS idx_ordini_ean ON ordini(ean);
CREATE INDEX IF NOT EXISTS idx_ordini_created_by ON ordini(created_by);
CREATE INDEX IF NOT EXISTS idx_ordini_updated_by ON ordini(updated_by);

COMMENT ON TABLE ordini IS 'Dettaglio righe ordine';
COMMENT ON COLUMN ordini.ordine_modello_pk IS 'Chiave primaria composta ordine-modello';
COMMENT ON COLUMN ordini.cod_ordine IS 'Codice ordine alfanumerico';
COMMENT ON COLUMN ordini.cod_modello IS 'Codice modello alfanumerico (FK a modelli)';

-- ============================================================================
-- 5. TABELLA TRACE_ELABORAZIONI_FILE (Log elaborazioni file)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS trace_elaborazioni_file_id_trace_seq START 1;

CREATE TABLE IF NOT EXISTS trace_elaborazioni_file (
    id_trace INTEGER PRIMARY KEY DEFAULT nextval('trace_elaborazioni_file_id_trace_seq'),
    id_file_ordine INTEGER NOT NULL REFERENCES file_ordini(id_file_ordine) ON DELETE CASCADE,
    tipo_file VARCHAR(10) NOT NULL,
    step VARCHAR(50) NOT NULL,
    stato VARCHAR(20) NOT NULL,
    messaggio TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trace_file_ordine ON trace_elaborazioni_file(id_file_ordine);
CREATE INDEX IF NOT EXISTS idx_trace_tipo_file ON trace_elaborazioni_file(tipo_file);
CREATE INDEX IF NOT EXISTS idx_trace_stato ON trace_elaborazioni_file(stato);
CREATE INDEX IF NOT EXISTS idx_trace_timestamp ON trace_elaborazioni_file(timestamp);

COMMENT ON TABLE trace_elaborazioni_file IS 'Log elaborazioni file ordini';

-- ============================================================================
-- 6. TABELLA TRACE_ELABORAZIONI_RECORD (Log elaborazioni record)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS trace_elaborazioni_record_id_trace_record_seq START 1;

CREATE TABLE IF NOT EXISTS trace_elaborazioni_record (
    id_trace_record INTEGER PRIMARY KEY DEFAULT nextval('trace_elaborazioni_record_id_trace_record_seq'),
    id_trace_file INTEGER NOT NULL REFERENCES trace_elaborazioni_file(id_trace) ON DELETE CASCADE,
    riga_file INTEGER,
    tipo_record VARCHAR(20),
    record_key VARCHAR(200),
    record_data JSON,
    errore TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trace_record_trace_file ON trace_elaborazioni_record(id_trace_file);
CREATE INDEX IF NOT EXISTS idx_trace_record_tipo ON trace_elaborazioni_record(tipo_record);
CREATE INDEX IF NOT EXISTS idx_trace_record_timestamp ON trace_elaborazioni_record(timestamp);

COMMENT ON TABLE trace_elaborazioni_record IS 'Log elaborazioni singoli record';

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
    AND tablename IN ('controparti', 'modelli', 'file_ordini', 'ordini',
                      'trace_elaborazioni_file', 'trace_elaborazioni_record');

    RAISE NOTICE '✓ Tabelle create: % su 6', v_count;

    IF v_count = 6 THEN
        RAISE NOTICE '✓ MIGRAZIONE COMPLETATA CON SUCCESSO';
        RAISE NOTICE ' ';
        RAISE NOTICE 'Riepilogo campi codice alfanumerici (VARCHAR):';
        RAISE NOTICE '  - controparti.cod_controparte: VARCHAR(50) PRIMARY KEY';
        RAISE NOTICE '  - modelli.cod_modello: VARCHAR(50) PRIMARY KEY';
        RAISE NOTICE '  - file_ordini.cod_seller: VARCHAR(50) FOREIGN KEY';
        RAISE NOTICE '  - file_ordini.cod_buyer: VARCHAR(50) FOREIGN KEY';
        RAISE NOTICE '  - ordini.cod_ordine: VARCHAR(100)';
        RAISE NOTICE '  - ordini.cod_modello: VARCHAR(50) FOREIGN KEY';
        RAISE NOTICE ' ';
        RAISE NOTICE '✓ Tutti i codici sono alfanumerici e supportano lettere, numeri e caratteri speciali.';
    ELSE
        RAISE WARNING '⚠ ATTENZIONE: Solo % tabelle su 6 sono state create', v_count;
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- ESEMPI DI UTILIZZO
-- ============================================================================
/*

-- Inserimento controparte
INSERT INTO controparti (cod_controparte, controparte, created_by)
VALUES ('CLI-001', 'Cliente Esempio S.r.l.', 1);

INSERT INTO controparti (cod_controparte, controparte, created_by)
VALUES ('FOR-ABC', 'Fornitore ABC', 1);

-- Inserimento modello
INSERT INTO modelli (cod_modello, cod_modello_norm, nome_modello, marca, created_by)
VALUES ('MOD-123A', 'MOD123A', 'Modello Esempio 123A', 'HISENSE', 1);

-- Query esempio: ordini per controparte
SELECT fo.*, c.controparte
FROM file_ordini fo
LEFT JOIN controparti c ON fo.cod_buyer = c.cod_controparte
WHERE fo.anno = 2024;

-- Query esempio: dettagli ordini con modelli
SELECT o.*, m.nome_modello, m.marca
FROM ordini o
INNER JOIN modelli m ON o.cod_modello = m.cod_modello
WHERE o.cod_ordine = 'ORD-2024-001';

*/
