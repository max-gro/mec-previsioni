# Sistema MEC Previsioni

## Descrizione Generale

**MEC Previsioni** è un'applicazione web sviluppata in Flask per la gestione e l'analisi predittiva delle rotture di componenti meccanici. Il sistema implementa modelli di survival analysis (analisi di sopravvivenza) basati su Kaplan-Meier e distribuzioni Weibull per prevedere quando i componenti potrebbero guastarsi, permettendo una pianificazione ottimale degli ordini di acquisto.

## Architettura e Tecnologie

### Stack Tecnologico
- **Backend**: Flask 3.x (Python)
- **Database**: PostgreSQL (con supporto SQLite per sviluppo)
- **Data Analysis**: Pandas, NumPy, SciPy
- **Survival Analysis**: Lifelines (Kaplan-Meier Fitter)
- **Visualizzazione**: Matplotlib
- **Autenticazione**: Flask-Login, Werkzeug Security
- **Server**: Gunicorn (produzione)

### Struttura Applicazione
```
app.py                    # Entry point principale
config.py                 # Configurazioni (Development/Production)
models.py                 # Modelli SQLAlchemy (User, FileOrdini, Controparte, Modello,
                          # Ordine, TraceElaborazioneFile, TraceElaborazioneRecord,
                          # Rottura, AnagraficaFile)
forms.py                  # Form WTForms per validazione input
functions.py              # Funzioni analisi statistica e Weibull
preprocessing.py          # Elaborazione dati Excel

routes/
  ├── auth.py            # Autenticazione (login/logout)
  ├── anagrafiche.py     # Gestione file anagrafiche componenti
  ├── rotture.py         # Gestione file rotture storiche
  ├── ordini.py          # Gestione ordini di acquisto + pipeline elaborazione
  ├── previsioni.py      # Calcolo e visualizzazione previsioni
  └── users.py           # Gestione utenti (admin)

services/                # Servizi per elaborazione file (NEW)
  ├── ordini_parser.py   # Parser Excel → TSV
  ├── ordini_db_inserter.py  # Inserimento dati da TSV nel DB
  └── file_manager.py    # Gestione spostamento file e stati

templates/               # Template HTML Jinja2
  └── ordini/
      ├── list.html      # Lista ordini
      ├── trace.html     # Timeline elaborazione (NEW)
      └── ...

static/                  # CSS, JavaScript, immagini, grafici
utils/                   # Decoratori e utility

INPUT/                   # File da elaborare (gitignored)
  ├── po/{anno}/         # Ordini Excel/PDF
  ├── anagrafiche/       # Anagrafiche per marca
  └── rotture/           # File rotture

OUTPUT/                  # File elaborati (gitignored)
  ├── po/{anno}/         # Ordini processati
  ├── anagrafiche/       # Anagrafiche processate
  └── rotture/           # Rotture processate

OUTPUT_ELAB/             # File intermedi TSV (gitignored)
  ├── po/                # TSV ordini
  ├── anagrafiche/       # TSV anagrafiche
  └── rotture/           # TSV rotture
```

## Funzionalità Principali

### 1. Gestione Anagrafiche Componenti
- Upload di file Excel contenenti informazioni sui componenti (codice, descrizione, marca, fornitore)
- Archiviazione file in `INPUT/ANAGRAFICHE/{anno}/{marca}/`
- Tracciamento stato elaborazione (Da processare, Processato, Errore)

### 2. Gestione Rotture Storiche
- Upload di file Excel con dati storici delle rotture
- Informazioni temporali: data di rottura, data di censura, stato del componente
- Storage in `INPUT/ROTTURE/{anno}/`
- Elaborazione per analisi di sopravvivenza

### 3. Gestione Ordini di Acquisto (Pipeline Completa)

#### Upload e Tracciamento
- Upload file Excel ordini con struttura definita (Seller, Buyer, Date, PO No., Brand, Item, EAN, Model No., CIF Price, Q.TY, Amount)
- Storage in `INPUT/po/{anno}/`
- Tracking stato file: **Da processare**, **Elaborato**, **Errore**
- Vincolo unicità: filename univoco per evitare duplicati

#### Pipeline Elaborazione (3 Step)

**Step 1: Parsing Excel → TSV**
- Lettura e validazione file Excel
- Normalizzazione codici modello (lowercase, no spazi)
- Generazione file TSV in `OUTPUT_ELAB/po/`
- Tracciamento step: lettura + parsing

**Step 2: Inserimento Database (Transazione Atomica)**
- Inserimento/aggiornamento **controparti** (Seller, Buyer)
  - Chiave: codice controparte (es: `SELL001`)
  - Salvataggio descrizione completa
  - Update automatico di `updated_at` e `updated_by`
- Inserimento/aggiornamento **modelli**
  - Chiave: `cod_modello_norm` (normalizzato)
  - Campi: brand, item, EAN, descrizione
  - Tracciamento origine aggiornamento (`updated_from`: ord/ana/rot)
- Inserimento **ordini** (relazione N:N ordine-modelli)
  - PK composta: `cod_ordine|cod_modello`
  - Verifica unicità per prevenire duplicati
  - Dati: prezzo, quantità, importo
- Tracciamento record-level per errori dettagliati

**Step 3: Completamento**
- Spostamento file `INPUT/po/` → `OUTPUT/po/`
- Aggiornamento stato a **Elaborato**
- Registrazione `data_elaborazione`

#### Gestione Errori
- Rollback completo transazione in caso di errore
- File rimane in INPUT con stato **Errore**
- Tracciamento a 2 livelli:
  - **trace_elaborazioni_file**: timeline step (lettura, parsing, inserimento_db, spostamento)
  - **trace_elaborazioni_record**: errori dettagliati con numero riga e dati record
- Possibilità rielaborazione dopo correzione file

#### Visualizzazione Trace
- Timeline elaborazione con icone stato (✓ success, ✗ error)
- Dettaglio errori a livello record (riga file, tipo, messaggio, dati JSON)
- Link download file originale per correzione
- Pulsante **Rielabora** per file in errore

### 4. Analisi Predittiva (Core Business)

#### Metodi Implementati:
- **Kaplan-Meier**: Stima non parametrica della funzione di sopravvivenza
- **Weibull Bayesiano**: Modello parametrico con prior informativi per migliorare le previsioni
- **Confidence Bands**: Intervalli di confidenza bootstrap per quantificare incertezza

#### Output:
- Grafici di sopravvivenza (curve Kaplan-Meier + fit Weibull)
- Previsioni a 6, 12, 18, 24, 36 mesi
- Quantità consigliate per ordini futuri
- Analisi risk-set per valutare robustezza delle stime

### 5. Sistema di Autenticazione
- Login/Logout con Flask-Login
- Ruoli utente: **admin** (pieno accesso) e **user** (accesso limitato)
- Credenziali default:
  - Admin: `admin / admin123`
  - Demo: `demo / demo123`

### 6. Dashboard e Reporting
- Visualizzazione stato file (anagrafiche, rotture, ordini)
- Grafici salvati in `static/pred_charts/` e `static/pred_charts_stat/`
- Esportazione risultati in formato JSON per analisi esterne

## Modello Dati (Database)

### Tabelle Principali:

**users**
- Gestione utenti con autenticazione e ruoli (admin/user)
- Campi: username, email, password_hash, role, active

**anagrafiche_file**
- Tracking file Excel anagrafiche (anno, marca, filepath, esito)
- Stati: Da processare, Processato, Errore

**rotture**
- Tracking file rotture storiche (anno, filename, data acquisizione/elaborazione)
- Stati: Da processare, Processato, Errore

### Tabelle Area Ordini (NEW - Pipeline Completa)

**file_ordini** (ex ordini_acquisto)
- Tracking file ordini di acquisto
- Campi: anno, marca, filename (UNIQUE), filepath, esito, note
- Riferimenti: cod_seller, cod_buyer (FK → controparti)
- Dati ordine: data_ordine, oggetto_ordine
- Audit: created_at, created_by, updated_at, updated_by
- Relationships: seller, buyer, ordini, traces

**controparti**
- Anagrafica seller e buyer
- Campi: cod_controparte (PK), controparte (UNIQUE), descrizione
- Audit: created_at, created_by, updated_at, updated_by
- Pattern upsert: insert se nuovo, update se esistente

**modelli**
- Catalogo modelli componenti
- Campi: cod_modello (PK), cod_modello_norm (UNIQUE, normalizzato)
- Dati: cod_modello_fabbrica, nome_modello, marca, brand, descrizione
- Classificazione: divisione, produttore, famiglia, tipo
- Audit: created_at, created_by, updated_at, updated_by, updated_from (ord/ana/rot)
- Pattern upsert: insert se nuovo, update se esistente

**ordini**
- Righe ordini (relazione N:N ordine-modelli)
- PK: ordine_modello_pk (cod_ordine|cod_modello)
- FK: id_file_ordine, cod_modello
- Dati: brand, item, ean, prezzo_eur, qta, importo_eur
- Audit: created_at, created_by, updated_at, updated_by
- Constraint: UNIQUE(cod_ordine, cod_modello)

**trace_elaborazioni_file**
- Timeline elaborazione a livello file
- Campi: id_file_ordine, tipo_file (ord/ana/rot), step, stato, messaggio, timestamp
- Step: lettura, parsing, inserimento_db, spostamento, completato, errore
- Stati: success, error, warning
- Relationship: trace_records (1:N)

**trace_elaborazioni_record**
- Errori dettagliati a livello record
- Campi: id_trace_file, riga_file, tipo_record, record_key, record_data (JSON), errore, timestamp
- Tipo record: ordine, controparte, modello
- Usato per debugging e correzione file

## Workflow Operativo

### 1. Setup Iniziale
```bash
# Inizializza database
python init_db.py

# Avvia applicazione (sviluppo)
python app.py
# Applicazione disponibile su http://localhost:5010

# Login
# Admin: admin / admin123
# Demo: demo / demo123
```

### 2. Gestione Ordini (Workflow Completo)

**Upload File**
1. Login come admin
2. Menu Ordini → **➕ Carica Nuovo Ordine**
3. Seleziona file Excel con colonne: Seller, Buyer, Date, PO No., Brand, Item, EAN, Model No., CIF Price, Q.TY, Amount
4. File salvato in `INPUT/po/{anno}/` con stato **Da processare**

**Elaborazione**
1. Lista ordini → Click **⚙️ Elabora** sul file
2. Pipeline automatica:
   - ✅ Parsing Excel → TSV
   - ✅ Validazione dati
   - ✅ Inserimento/aggiornamento controparti
   - ✅ Inserimento/aggiornamento modelli
   - ✅ Inserimento ordini
   - ✅ Spostamento file in OUTPUT
3. Stato aggiornato a **Elaborato** (o **Errore** se fallisce)

**Monitoraggio**
- Click **🔍 Trace** per visualizzare timeline elaborazione
- Se errori: visualizza riga file, tipo record, messaggio errore
- Download file originale per correzione
- Rielabora dopo fix

**Consultazione Dati**
- Controparti inserite in tabella `controparti`
- Modelli inseriti/aggiornati in `modelli`
- Righe ordine in `ordini` (con relazione ordine-modello)

### 3. Gestione Anagrafiche
- Upload file Excel anagrafiche componenti
- Organizzazione per marca e anno
- Elaborazione (in sviluppo - pipeline simile a ordini)

### 4. Gestione Rotture
- Upload file Excel rotture storiche
- Tracciamento data rottura, censura, stato
- Elaborazione per analisi survival (in sviluppo)

### 5. Analisi Previsioni
- Selezione componente/modello
- Generazione curve Kaplan-Meier + fit Weibull
- Visualizzazione previsioni a 6/12/18/24/36 mesi
- Calcolo quantità ordini suggerite
- Export grafici e dati JSON

## Deployment

### Sviluppo
```bash
python app.py
# Server avviato su http://localhost:5010
```

### Produzione
```bash
# PostgreSQL via Docker
docker compose -f docker-compose.postgres.yml up -d

# Avvio con Gunicorn
gunicorn -w 4 -b 0.0.0.0:5010 app:app
```

## File di Configurazione

- **requirements.txt**: Dipendenze Python
- **docker-compose.postgres.yml**: Configurazione PostgreSQL
- **.gitignore**: Esclusione venv, cache, database locale

## Implementazioni Recenti (v2.0)

✅ **Pipeline Elaborazione Ordini Completa**
- Parser Excel → TSV con validazione struttura
- Inserimento database transazionale
- Tracciamento a 2 livelli (file + record)
- UI per visualizzazione trace e rielaborazione

✅ **Gestione Controparti e Modelli**
- Pattern upsert (insert/update automatico)
- Normalizzazione codici modello
- Tracciamento origine aggiornamenti

✅ **Sistema Trace Completo**
- Timeline elaborazione con stati
- Dettaglio errori record-level
- Link file originale per correzione

## Prossimi Sviluppi

- 🔄 Estensione pipeline ad **anagrafiche** e **rotture**
- 🔄 Migrazione completa a PostgreSQL
- API REST per integrazioni esterne
- Ottimizzazione performance calcoli Weibull
- Dashboard interattiva con grafici dinamici
- Export automatico report PDF
- OCR per elaborazione PDF ordini scansionati

---

**Versione Python**: 3.13.4
**Framework**: Flask 3.x
**Database**: PostgreSQL 12+
**Licenza**: Proprietaria
