# Migration: Aggiunta id_elab e Metriche

**Data**: 2025-11-20
**File SQL**: `add_id_elab_and_metrics.sql`

## Obiettivo

Aggiungere campo `id_elab` per raggruppare tutte le operazioni di una singola elaborazione (click bottone "Elabora") e campi metriche per visualizzare statistiche.

## Cambiamenti

### Tabella `trace_elab`

**Campi AGGIUNTI:**
- `id_elab` (INTEGER): identifica gruppo di operazioni della stessa elaborazione
- `righe_totali` (INTEGER): totale righe elaborate
- `righe_ok` (INTEGER): righe processate con successo
- `righe_errore` (INTEGER): righe con errori
- `righe_warning` (INTEGER): righe con warning

**Campi RIMOSSI:**
- `ts_inizio`, `ts_fine`, `durata_secondi`, `esito`, `messaggio_globale` (non utilizzati)

**Schema Finale:**
```sql
id_trace        SERIAL PRIMARY KEY
id_elab         INTEGER NOT NULL
id_file         INTEGER NOT NULL
tipo_file       VARCHAR(10) NOT NULL  -- 'ORD', 'ANA', 'ROT'
step            VARCHAR(50) NOT NULL  -- 'START', 'END', 'PROCESS'
stato           VARCHAR(20) NOT NULL  -- 'OK', 'KO', 'WARN'
messaggio       TEXT
righe_totali    INTEGER DEFAULT 0
righe_ok        INTEGER DEFAULT 0
righe_errore    INTEGER DEFAULT 0
righe_warning   INTEGER DEFAULT 0
created_at      TIMESTAMP NOT NULL
```

### Tabella `trace_elab_dett`

**Nessun cambiamento strutturale**, confermato schema esistente:
```sql
id_trace_dett   SERIAL PRIMARY KEY
id_trace        INTEGER NOT NULL (FK)
record_pos      INTEGER
record_data     JSONB
messaggio       TEXT
stato           VARCHAR(20) NOT NULL  -- 'OK', 'KO', 'WARN'
created_at      TIMESTAMP NOT NULL
```

## Come Applicare

```bash
# 1. Connetti al database
psql -U postgres -d mec_previsioni

# 2. Esegui migration
\i migrations_sql/add_id_elab_and_metrics.sql

# 3. Verifica
\dt trace_elab*
\d trace_elab
```

Oppure via Python:

```python
from app import app, db
with app.app_context():
    with open('migrations_sql/add_id_elab_and_metrics.sql', 'r') as f:
        db.session.execute(f.read())
        db.session.commit()
```

## Logica id_elab

Ogni volta che si clicca "Elabora":
1. Genera nuovo `id_elab`: `SELECT nextval('seq_id_elab')`
2. Tutte le operazioni usano lo stesso `id_elab`

**Esempio:**
```
id_trace | id_elab | step  | messaggio
---------|---------|-------|------------------
100      | 10      | START | Inizio conversione PDF
101      | 10      | END   | Fine conversione PDF (50 warning)
102      | 10      | START | Inizio caricamento DB
103      | 10      | END   | Fine caricamento DB
```

Così nella pagina "Storico Elaborazioni" possiamo raggruppare per `id_elab` e mostrare tutte le operazioni insieme.

## Impatto Codice

- ✅ `models.py`: aggiornare modello TraceElab
- ✅ `routes/ordini.py`: generare id_elab e popolare metriche
- ✅ `templates/ordini/elaborazioni_list.html`: usare campi reali
- ⚠️ `routes/anagrafiche.py` e `routes/rotture.py`: da aggiornare dopo ordini

## Rollback

Se serve tornare indietro (i dati vengono persi):

```sql
-- Ripristina backup (se fatto)
DROP TABLE trace_elab_dett CASCADE;
DROP TABLE trace_elab CASCADE;

ALTER TABLE trace_elab_backup RENAME TO trace_elab;
ALTER TABLE trace_elab_dett_backup RENAME TO trace_elab_dett;
```
