-- ============================================================================
-- Script di migrazione: Crea utente di sistema con id_user=0
--
-- Questo utente è utilizzato come default per created_by/updated_by quando
-- i record vengono creati automaticamente (es. scan filesystem) senza un
-- utente loggato.
-- ============================================================================

-- Inserisci utente di sistema (solo se non esiste già)
INSERT INTO users (id_user, username, email, password_hash, role, active, created_at, created_by)
SELECT
    0,
    'system',
    'system@localhost',
    'SISTEMA_NON_ACCESSIBILE',
    'Sistema',
    FALSE,
    NOW(),
    0
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE id_user = 0
);

-- Verifica inserimento
SELECT id_user, username, email, role, active
FROM users
WHERE id_user = 0;
