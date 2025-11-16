# Fix Errore Duplicati Ordini

## Problema

Quando si accede alla form Ordini, si verifica l'errore:

```
IntegrityError: duplicate key value violates unique constraint "file_ordini_filename_key"
DETAIL: Key (filename)=(UNIEURO-KADEER-PO No.4508185794.pdf) already exists.
```

## Causa

La funzione `scan_po_folder()` cercava i file per `filepath` invece di `filename`. Quando un file viene elaborato:

1. Il file viene **SPOSTATO** (non copiato) da `INPUT/po/ANNO/` a `OUTPUT/po/ANNO/`
2. Il `filepath` cambia (es. da `INPUT/po/2024/ordine.pdf` a `OUTPUT/po/2024/ordine.pdf`)
3. La funzione `scan_po_folder()` non trova il record (cerca per filepath vecchio)
4. Tenta di creare un NUOVO record con lo stesso `filename` → errore duplicate key

**Nota**: Se ci sono duplicati reali (stesso file in anni diversi), è un errore utente.

## Soluzione

### 1. Modello (`models.py`)

- **Unique constraint**: Solo su `filename` (un file appare una volta sola nel DB)
- Il file spostato da INPUT a OUTPUT → record aggiornato, non duplicato

### 2. Funzione `scan_po_folder()` (`routes/ordini.py`)

**Prima (SBAGLIATO)**:
```python
existing = OrdineAcquisto.query.filter_by(filepath=filepath).first()
if not existing:
    db.session.add(nuovo_ordine)  # ERRORE se filename esiste!
```

**Dopo (CORRETTO)**:
```python
existing = OrdineAcquisto.query.filter_by(filename=filename).first()
if existing:
    # AGGIORNA record esistente
    existing.filepath = filepath
    existing.esito = 'Processato'
else:
    # Crea nuovo record
    db.session.add(nuovo_ordine)
```

### 3. Script Migrazione (`fix_ordini_constraints.py`)

- Rimuove duplicati su `filename` (con conferma)
- Rimuove constraint sbagliati
- Assicura UNIQUE solo su `filename`

## Come Applicare il Fix

### Passo 1: PostgreSQL

```bash
docker compose -f docker-compose.postgres.yml up -d
```

### Passo 2: DATABASE_URL

File `.env`:
```
DATABASE_URL=postgresql://mec:cem@localhost:5432/mec_previsioni
```

### Passo 3: Migrazione

```bash
python fix_ordini_constraints.py
```

### Passo 4: Riavvio

```bash
python app.py
```

## Logica Corretta

Un file ha UN SOLO record nel DB:
- Upload → `INPUT/po/2024/ordine.pdf` (esito: Da processare)
- Elaborazione → file SPOSTATO a `OUTPUT/po/2024/ordine.pdf`
- Record AGGIORNATO: filepath cambia, esito diventa Processato
- NO duplicati

## Troubleshooting

**Connection refused**: `docker compose -f docker-compose.postgres.yml up -d`

**Table not found**: `python init_db.py`

**Duplicati trovati**: Probabilmente errore utente (stesso file in anni diversi). Lo script chiede conferma prima di rimuoverli.
