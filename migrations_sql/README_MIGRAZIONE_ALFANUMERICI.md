# Migrazione: Campi Codice Alfanumerici

**Data**: 2025-11-17
**Obiettivo**: Convertire campi codice da INTEGER a VARCHAR (alfanumerici)

⚠️ **IMPORTANTE**: Esistono DUE scenari possibili:

1. **Le tabelle NON esistono** → Usare `add_business_tables_alphanumeric.sql` (crea nuove tabelle)
2. **Le tabelle ESISTONO già con INTEGER** → Usare `convert_code_fields_to_varchar.sql` (converte campi esistenti)

## 📋 Sommario

Questa migrazione aggiunge le seguenti tabelle al database MEC Previsioni:

| Tabella | Descrizione | Campi Codice Alfanumerici |
|---------|-------------|---------------------------|
| `controparti` | Anagrafica clienti/fornitori | `cod_controparte` VARCHAR(50) PK |
| `modelli` | Anagrafica modelli/prodotti | `cod_modello` VARCHAR(50) PK |
| `file_ordini` | Testata ordini da file | `cod_seller`, `cod_buyer` VARCHAR(50) FK |
| `ordini` | Dettaglio righe ordine | `cod_ordine` VARCHAR(100), `cod_modello` VARCHAR(50) FK |
| `trace_elaborazioni_file` | Log elaborazioni file | - |
| `trace_elaborazioni_record` | Log elaborazioni record | - |

## 🎯 Perché Alfanumerici?

I campi codice sono stati definiti come **VARCHAR** invece di **INTEGER** per supportare:

- ✅ Codici alfanumerici (es: `CLI-001`, `FOR-ABC`, `MOD-123A`)
- ✅ Prefissi e suffissi (es: `2024-ORD-001`, `HISENSE-MOD123`)
- ✅ Caratteri speciali (es: `MOD_123-A`, `CLI/2024/001`)
- ✅ Codici con lunghezza variabile
- ✅ Compatibilità con sistemi esterni che usano codici alfanumerici

## 🚀 Come Eseguire la Migrazione

### SCENARIO 1: Tabelle Esistenti con INTEGER (CONVERSIONE)

Se le tabelle esistono già con campi INTEGER, usa lo script di **conversione**:

#### Opzione A: Script SQL PostgreSQL (Raccomandato)

```bash
# 1. BACKUP OBBLIGATORIO!
pg_dump -U username -d mec_previsioni > backup_pre_conversion_$(date +%Y%m%d).sql

# 2. Esegui conversione
psql -U username -d mec_previsioni -f migrations_sql/convert_code_fields_to_varchar.sql
```

#### Opzione B: Script Python

```bash
# 1. Esegui conversione (crea backup automatico se SQLite)
python migrate_convert_to_varchar.py

# Senza conferma
python migrate_convert_to_varchar.py --yes

# Solo verifica (non modifica nulla)
python migrate_convert_to_varchar.py --verify-only
```

---

### SCENARIO 2: Tabelle NON Esistenti (CREAZIONE)

Se le tabelle non esistono ancora, usa lo script di **creazione**:

#### Opzione 1: Script Python (Raccomandato)

```bash
# Assicurati di avere Flask e le dipendenze installate
pip install -r requirements.txt

# Esegui la migrazione con conferma
python migrate_add_business_tables.py

# Oppure senza conferma (utile per script automatici)
python migrate_add_business_tables.py --yes

# Mostra lo schema dopo la migrazione
python migrate_add_business_tables.py --yes --schema

# Aiuto
python migrate_add_business_tables.py --help
```

### Opzione 2: Script SQL Diretto (PostgreSQL)

```bash
# Connettiti al database PostgreSQL
psql -U username -d mec_previsioni

# Esegui lo script SQL
\i migrations_sql/add_business_tables_alphanumeric.sql

# Oppure da shell
psql -U username -d mec_previsioni -f migrations_sql/add_business_tables_alphanumeric.sql
```

### Opzione 3: Via Docker Compose (PostgreSQL)

```bash
# Se usi docker-compose.postgres.yml
docker-compose -f docker-compose.postgres.yml exec postgres psql -U mecuser -d mecdb -f /path/to/add_business_tables_alphanumeric.sql
```

## 🔍 Verifica Migrazione

### Verifica Tipo Colonne

Dopo la conversione, verifica che i campi siano VARCHAR:

```sql
-- PostgreSQL: Verifica tipi colonne
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('controparti', 'modelli', 'file_ordini', 'ordini')
AND column_name IN ('cod_controparte', 'cod_modello', 'cod_seller', 'cod_buyer', 'cod_ordine')
ORDER BY table_name, column_name;

-- Risultato atteso:
-- controparti.cod_controparte → character varying (50)
-- file_ordini.cod_buyer → character varying (50)
-- file_ordini.cod_seller → character varying (50)
-- modelli.cod_modello → character varying (50)
-- ordini.cod_modello → character varying (50)
-- ordini.cod_ordine → character varying (100)

-- Verifica struttura completa
\d controparti
\d modelli
\d file_ordini
\d ordini

-- Verifica foreign keys
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('file_ordini', 'ordini', 'trace_elaborazioni_file', 'trace_elaborazioni_record');
```

## 📊 Struttura Tabelle

### 1. Controparti

```sql
CREATE TABLE controparti (
    cod_controparte VARCHAR(50) PRIMARY KEY,  -- ← ALFANUMERICO
    controparte VARCHAR(200) NOT NULL,
    created_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)
);
```

**Esempio dati:**
```sql
INSERT INTO controparti (cod_controparte, controparte, created_by)
VALUES
    ('CLI-001', 'Cliente Esempio S.r.l.', 1),
    ('FOR-ABC', 'Fornitore ABC', 1),
    ('BUY-2024-01', 'Acquirente Test', 1);
```

### 2. Modelli

```sql
CREATE TABLE modelli (
    cod_modello VARCHAR(50) PRIMARY KEY,  -- ← ALFANUMERICO
    cod_modello_norm VARCHAR(100) NOT NULL,
    cod_modello_fabbrica VARCHAR(100),
    nome_modello VARCHAR(200),
    marca VARCHAR(100),
    -- ... altri campi
);
```

**Esempio dati:**
```sql
INSERT INTO modelli (cod_modello, cod_modello_norm, nome_modello, marca, created_by)
VALUES
    ('MOD-123A', 'MOD123A', 'Modello Esempio 123A', 'HISENSE', 1),
    ('HOMA-456B', 'HOMA456B', 'Modello HOMA 456B', 'HOMA', 1),
    ('2024-MOD-789', '2024MOD789', 'Modello 2024', 'MIDEA', 1);
```

### 3. File Ordini

```sql
CREATE TABLE file_ordini (
    id_file_ordine INTEGER PRIMARY KEY,
    anno INTEGER NOT NULL,
    marca VARCHAR(100),
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    cod_seller VARCHAR(50) REFERENCES controparti(cod_controparte),  -- ← ALFANUMERICO
    cod_buyer VARCHAR(50) REFERENCES controparti(cod_controparte),   -- ← ALFANUMERICO
    data_ordine DATE,
    -- ... altri campi
);
```

### 4. Ordini

```sql
CREATE TABLE ordini (
    ordine_modello_pk VARCHAR(200) PRIMARY KEY,
    id_file_ordine INTEGER REFERENCES file_ordini(id_file_ordine),
    cod_ordine VARCHAR(100) NOT NULL,  -- ← ALFANUMERICO
    cod_modello VARCHAR(50) REFERENCES modelli(cod_modello),  -- ← ALFANUMERICO
    brand VARCHAR(100),
    item VARCHAR(200),
    prezzo_eur NUMERIC(10, 2),
    qta INTEGER,
    -- ... altri campi
);
```

## 🧪 Test e Query Esempio

### Query 1: Ordini per controparte (acquirente)

```sql
SELECT
    fo.id_file_ordine,
    fo.filename,
    fo.data_ordine,
    c.cod_controparte,
    c.controparte AS nome_acquirente,
    COUNT(o.ordine_modello_pk) AS num_righe,
    SUM(o.importo_eur) AS totale_ordine
FROM file_ordini fo
LEFT JOIN controparti c ON fo.cod_buyer = c.cod_controparte
LEFT JOIN ordini o ON fo.id_file_ordine = o.id_file_ordine
WHERE fo.anno = 2024
GROUP BY fo.id_file_ordine, fo.filename, fo.data_ordine, c.cod_controparte, c.controparte
ORDER BY fo.data_ordine DESC;
```

### Query 2: Dettagli ordini con modelli

```sql
SELECT
    o.cod_ordine,
    o.ordine_modello_pk,
    o.cod_modello,
    m.nome_modello,
    m.marca,
    o.item,
    o.qta,
    o.prezzo_eur,
    o.importo_eur
FROM ordini o
INNER JOIN modelli m ON o.cod_modello = m.cod_modello
WHERE o.cod_ordine = 'ORD-2024-001';
```

### Query 3: Statistiche elaborazioni

```sql
SELECT
    tf.tipo_file,
    tf.stato,
    COUNT(*) AS num_elaborazioni,
    AVG(EXTRACT(EPOCH FROM (
        SELECT MAX(timestamp) - MIN(timestamp)
        FROM trace_elaborazioni_file
        WHERE id_file_ordine = tf.id_file_ordine
    ))) AS durata_media_sec
FROM trace_elaborazioni_file tf
GROUP BY tf.tipo_file, tf.stato;
```

## 🔄 Rollback (Se Necessario)

Se la migrazione causa problemi, puoi fare rollback eliminando le tabelle:

```sql
-- ATTENZIONE: Questo eliminerà tutti i dati!
BEGIN;

DROP TABLE IF EXISTS trace_elaborazioni_record CASCADE;
DROP TABLE IF EXISTS trace_elaborazioni_file CASCADE;
DROP TABLE IF EXISTS ordini CASCADE;
DROP TABLE IF EXISTS file_ordini CASCADE;
DROP TABLE IF EXISTS modelli CASCADE;
DROP TABLE IF EXISTS controparti CASCADE;

DROP SEQUENCE IF EXISTS file_ordini_id_file_ordine_seq;
DROP SEQUENCE IF EXISTS trace_elaborazioni_file_id_trace_seq;
DROP SEQUENCE IF EXISTS trace_elaborazioni_record_id_trace_record_seq;

COMMIT;
```

## 📝 Note Importanti

1. **Backup**: Lo script Python crea automaticamente un backup del database SQLite. Per PostgreSQL, eseguire manualmente:
   ```bash
   pg_dump -U username -d mec_previsioni > backup_pre_migration_$(date +%Y%m%d).sql
   ```

2. **Performance**: Gli indici sono stati creati sui campi codice per ottimizzare le query con JOIN e WHERE.

3. **Vincoli di integrità**: Le foreign key garantiscono l'integrità referenziale tra le tabelle.

4. **Compatibilità**: Lo script SQL è ottimizzato per PostgreSQL. Per SQLite, alcune sintassi potrebbero richiedere adattamenti (es: JSON → TEXT).

5. **Cascade**: Le foreign key in `ordini` e `trace_elaborazioni_*` hanno ON DELETE CASCADE per eliminare automaticamente i record dipendenti.

## 🔗 File Correlati

- **models.py**: Definizioni SQLAlchemy dei modelli
- **migrate_add_business_tables.py**: Script Python di migrazione
- **add_business_tables_alphanumeric.sql**: Script SQL diretto

## 📞 Supporto

Per problemi o domande sulla migrazione:
1. Verifica i log di errore
2. Controlla che tutte le dipendenze siano installate (`pip install -r requirements.txt`)
3. Verifica connessione al database
4. Controlla i permessi dell'utente database

## ✅ Checklist Post-Migrazione

- [ ] Tutte le 6 tabelle sono state create
- [ ] Le sequence PostgreSQL sono state create (se PostgreSQL)
- [ ] Gli indici sono stati creati correttamente
- [ ] Le foreign key funzionano (test con INSERT)
- [ ] I campi VARCHAR accettano codici alfanumerici
- [ ] Il backup del database è stato creato
- [ ] L'applicazione Flask riconosce i nuovi modelli
- [ ] I test di integrazione passano (se presenti)

## 🎉 Conclusione

Dopo questa migrazione, il database supporta **codici alfanumerici** per controparti, modelli e ordini, rendendo il sistema più flessibile e compatibile con sistemi esterni che utilizzano codici non numerici.

**Buona migrazione! 🚀**
