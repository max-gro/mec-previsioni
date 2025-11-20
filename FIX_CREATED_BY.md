# Fix Foreign Key Constraint - created_by

## Problema

Errore quando si accede a Ordini/Anagrafiche/Rotture:
```
sqlalchemy.exc.IntegrityError:
(psycopg2.errors.ForeignKeyViolation) insert or update on table "file_ordini" violates foreign key constraint "file_ordini_created_by_fkey"
DETAIL: Key (created_by)=(0) is not present in table "users".
```

## Causa

Tutti i modelli hanno `created_by` con default=0, ma non esiste un utente con `id_user=0` nel database.

Questo utente serve come "utente di sistema" quando i file vengono scansionati automaticamente dal filesystem (funzioni `scan_po_folder()`, `scan_anagrafiche_folder()`, ecc.) senza un utente loggato.

## Soluzione

Eseguire la migrazione SQL per creare l'utente di sistema con `id_user=0`.

### Opzione 1: Script Python (raccomandato)

```bash
python migrate_create_system_user.py
```

### Opzione 2: Script SQL diretto

```bash
# PostgreSQL
psql -U your_username -d your_database -f migrate_create_system_user.sql

# Oppure da psql:
\i migrate_create_system_user.sql
```

### Opzione 3: SQL manuale

```sql
INSERT INTO users (id_user, username, email, password_hash, role, active, created_at, created_by)
VALUES (
    0,
    'system',
    'system@localhost',
    'SISTEMA_NON_ACCESSIBILE',
    'Sistema',
    FALSE,
    NOW(),
    0
);
```

## Verifica

Dopo l'esecuzione, verifica che l'utente sia stato creato:

```sql
SELECT id_user, username, email, role, active FROM users WHERE id_user = 0;
```

Output atteso:
```
 id_user | username |      email       |  role   | active
---------+----------+------------------+---------+--------
       0 | system   | system@localhost | Sistema | f
```

## Note

- L'utente di sistema ha `active=FALSE`, quindi **non può fare login**
- Viene usato solo come valore di default per `created_by` e `updated_by`
- È sicuro eseguire la migrazione più volte (inserisce solo se non esiste già)
