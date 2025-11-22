-- ============================================================================
-- Migration: Aggiungi 'STOCK' al constraint tipo_file in trace_elab
-- Data: 2025-11-22
-- Descrizione:
--   Estende il constraint trace_elab_tipo_file_check per includere 'STOCK'
--   oltre ai tipi esistenti 'ORD', 'ANA', 'ROT'
-- ============================================================================

-- STEP 1: Drop vecchio constraint
ALTER TABLE trace_elab DROP CONSTRAINT IF EXISTS trace_elab_tipo_file_check;

-- STEP 2: Aggiungi nuovo constraint con 'STOCK'
ALTER TABLE trace_elab
ADD CONSTRAINT trace_elab_tipo_file_check
CHECK (tipo_file IN ('ORD', 'ANA', 'ROT', 'STOCK'));

-- STEP 3: Verifica
SELECT 'Migration completata con successo!' as status;
SELECT conname, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conname = 'trace_elab_tipo_file_check';
