# Fix Errore Duplicati Ordini

## Problema

Quando si accede alla form Ordini, si verifica l'errore:

```
IntegrityError: duplicate key value violates unique constraint "file_ordini_filename_key"
DETAIL: Key (filename)=(UNIEURO-KADEER-PO No.4508185794.pdf) already exists.
```

## Causa

Il database PostgreSQL aveva un vincolo di unicità sul campo `filename` della tabella `file_ordini`. Questo causava problemi quando:

1. Un file PDF viene caricato in `INPUT/po/ANNO/` (stato: Da processare)
2. Il file viene elaborato e spostato in `OUTPUT/po/ANNO/` (stato: Processato)
3. La funzione `scan_po_folder()` cerca di creare un nuovo record per il file in OUTPUT
4. Il filename è lo stesso, ma il filepath è diverso
5. Il database rifiuta l'inserimento perché `filename` non è unico

## Soluzione

Sono state apportate le seguenti modifiche:

### 1. Aggiornamento Modello (`models.py`)

Il modello `OrdineAcquisto` è stato allineato allo schema del database PostgreSQL:

- **Tablename**: Cambiato da `ordini_acquisto` a `file_ordini` (per matchare il DB esistente)
- **Campo ID**: Rinominato da `id_file_ordini_acquisto` a `id_file_ordine`
- **Unique constraint**: Spostato da `filename` a `filepath`
- **Nuove colonne**: Aggiunti campi mancanti:
  - `marca`
  - `cod_seller`, `cod_buyer`
  - `data_ordine`, `oggetto_ordine`
  - `created_by`, `updated_by`

### 2. Script di Migrazione Database

È stato creato lo script `fix_ordini_constraints.py` che:

1. Rimuove il constraint UNIQUE su `filename`
2. Aggiunge constraint UNIQUE su `filepath`
3. Rimuove eventuali duplicati esistenti su `filepath`

## Come Applicare il Fix

### Passo 1: Assicurati che PostgreSQL sia in esecuzione

```bash
# Avvia il container PostgreSQL se non è già attivo
docker compose -f docker-compose.postgres.yml up -d

# Verifica che sia attivo
docker ps | grep mec-postgres
```

### Passo 2: Configura DATABASE_URL

Crea un file `.env` nella root del progetto (se non esiste già):

```bash
DATABASE_URL=postgresql://mec:cem@localhost:5432/mec_previsioni
```

Oppure esporta la variabile d'ambiente:

```bash
export DATABASE_URL="postgresql://mec:cem@localhost:5432/mec_previsioni"
```

### Passo 3: Esegui lo Script di Migrazione

```bash
python fix_ordini_constraints.py
```

Output atteso:
```
==============================================================
SCRIPT DI MIGRAZIONE: Fix Constraints file_ordini
==============================================================

Connessione al database...
✓ Tabella 'file_ordini' trovata
✓ Nessun duplicato trovato su filepath
✓ Rimosso constraint: file_ordini_filename_key
✓ Aggiunto constraint UNIQUE su filepath

==============================================================
RIEPILOGO CONSTRAINTS FINALI:
==============================================================
  FOREIGN KEY          ...
  PRIMARY KEY          file_ordini_pkey
  UNIQUE               file_ordini_filepath_unique

✓ MIGRAZIONE COMPLETATA CON SUCCESSO!
==============================================================
```

### Passo 4: Riavvia l'Applicazione

```bash
# Se l'app è in esecuzione, fermala e riavviala
python app.py
```

## Verifica

1. Accedi a http://localhost:5010/login
2. Vai su "Ordini di Acquisto"
3. La pagina dovrebbe caricarsi senza errori
4. Prova a caricare un nuovo file PDF
5. Prova ad elaborare un ordine (dovrebbe spostare il file da INPUT a OUTPUT senza errori)

## Script Aggiuntivi

- `inspect_schema.py`: Ispeziona lo schema del database per debugging
  ```bash
  python inspect_schema.py
  ```

## Note Tecniche

### Perché `filepath` è unique invece di `filename`?

- `filename`: Es. `UNIEURO-KADEER-PO No.4508185794.pdf` (solo nome file)
- `filepath`: Es. `/home/user/mec-previsioni/INPUT/po/2024/UNIEURO-KADEER-PO No.4508185794.pdf` (path completo)

Lo stesso file può avere stati diversi:
- `INPUT/po/2024/ordine.pdf` → Da processare
- `OUTPUT/po/2024/ordine.pdf` → Processato

Entrambi hanno lo stesso `filename` ma `filepath` diversi. Il vincolo unique su `filepath` garantisce che:
- Non ci siano duplicati nello stesso percorso
- Lo stesso file può esistere in INPUT e OUTPUT contemporaneamente

### Funzione `scan_po_folder()`

La funzione in `routes/ordini.py` sincronizza il filesystem con il database:

1. Scansiona `INPUT/po/ANNO/` e `OUTPUT/po/ANNO/`
2. Per ogni PDF trovato, verifica se esiste già un record con quel `filepath`
3. Se non esiste, crea un nuovo record
4. Se il file è in OUTPUT, imposta `esito='Processato'`
5. Rimuove record orfani (file nel DB ma non nel filesystem)

Con il fix applicato, questa funzione ora funziona correttamente anche quando lo stesso filename esiste in INPUT e OUTPUT.

## Troubleshooting

### Errore: "connection refused"

PostgreSQL non è in esecuzione. Avvia il container:
```bash
docker compose -f docker-compose.postgres.yml up -d
```

### Errore: "table file_ordini does not exist"

Il database è nuovo. Inizializza prima:
```bash
python init_db.py
```

### Errore persiste dopo la migrazione

1. Rimuovi la cache Python:
   ```bash
   rm -rf __pycache__
   find . -name "*.pyc" -delete
   ```

2. Riavvia l'applicazione:
   ```bash
   python app.py
   ```

3. Controlla i log del database per altri errori

## Supporto

In caso di problemi, verifica:

1. DATABASE_URL è configurata correttamente
2. PostgreSQL è in esecuzione e raggiungibile
3. Le credenziali sono corrette (mec/cem)
4. Il database mec_previsioni esiste

Per verificare la connessione manualmente:
```bash
psql postgresql://mec:cem@localhost:5432/mec_previsioni -c "\dt"
```
