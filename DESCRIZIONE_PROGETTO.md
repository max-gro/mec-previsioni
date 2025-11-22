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
models.py                 # Modelli SQLAlchemy (User, Rottura, OrdineAcquisto, AnagraficaFile)
forms.py                  # Form WTForms per validazione input
functions.py              # Funzioni analisi statistica e Weibull
preprocessing.py          # Elaborazione dati Excel

routes/
  ├── auth.py                # Autenticazione (login/logout)
  ├── ordini.py              # Pipeline Ordini (PDF)
  ├── ordini_explorer.py     # Ordini Explorer
  ├── anagrafiche.py         # Pipeline Anagrafiche (Excel BOM)
  ├── anagrafiche_catalogo.py # Catalogo Modelli & Componenti
  ├── rotture.py             # Pipeline Rotture (Excel)
  ├── rotture_explorer.py    # Rotture Explorer
  ├── stock.py               # Pipeline Stock (TSV giacenze)
  ├── stock_explorer.py      # Stock Explorer
  ├── previsioni.py          # Calcolo e visualizzazione previsioni
  ├── dashboard.py           # Dashboard elaborazioni
  └── users.py               # Gestione utenti (admin)

templates/               # Template HTML Jinja2
static/                  # CSS, JavaScript, immagini, grafici
utils/                   # Decoratori e utility
```

## Funzionalità Principali

### 1. Pipeline Ordini di Acquisto (PDF)
- Upload file PDF ordini di acquisto
- Parsing automatico con OCR e estrazione tabelle
- Archiviazione in `INPUT/ORDINI/{anno}/`
- Tracciamento stato elaborazione con trace logging
- Ordini Explorer per ricerca e filtri avanzati

### 2. Pipeline Anagrafiche Componenti (Excel)
- Upload file Excel con distinte base (BOM) per marca/modello
- Estrazione componenti e mapping modelli
- Storage in `INPUT/ANAGRAFICHE/{anno}/{marca}/`
- Catalogo Modelli & Componenti per consultazione
- Tracciamento elaborazioni con dettagli anomalie

### 3. Pipeline Rotture Storiche (Excel)
- Upload file Excel con eventi di guasto
- Dati temporali: data rottura, componente, modello
- Storage in `INPUT/ROTTURE/{anno}/`
- Rotture Explorer con statistiche affidabilità
- Elaborazione per analisi di sopravvivenza

### 4. Pipeline Stock Giacenze (TSV)
- Upload file TSV con snapshot giacenze magazzino
- Campi: cod_componente, giacenze (fisica/disponibile/impegnata), scorte
- Storage in `INPUT/STOCK/{anno}/`
- Stock Explorer con vista giacenze correnti e storiche
- Alert scorte critiche (< 50 unità)
- Gestione flag_corrente per snapshot più recenti

### 5. Analisi Predittiva (Core Business)

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
- Gestione utenti con autenticazione e ruoli

**anagrafiche_file**
- Tracking file Excel anagrafiche (anno, marca, filepath, esito)

**rotture**
- Tracking file rotture storiche (anno, filename, data acquisizione/elaborazione)

**file_ordini**
- Tracking file ordini PDF (anno, filepath, esito elaborazione)

**file_stock**
- Tracking file giacenze TSV (anno, filename, data acquisizione/elaborazione)

**stock**
- Giacenze componenti (cod_componente, giacenza_fisica, disponibile, impegnata)
- Scorte (min, max, punto riordino, lead time)
- Snapshot temporali con data_snapshot e flag_corrente

**trace_elab** / **trace_elab_dett**
- Tracciamento elaborazioni con metriche (righe OK/KO/warning)
- Log dettagli anomalie per debugging

## Workflow Operativo

1. **Setup Iniziale**:
   - Avvio database PostgreSQL via Docker Compose
   - Inizializzazione schema con `init_db.py`
   - Creazione utenti admin/demo

2. **Acquisizione Dati**:
   - Upload file Excel (anagrafiche, rotture, ordini)
   - Validazione formato e salvataggio nelle directory INPUT

3. **Elaborazione**:
   - Parsing file Excel con Pandas
   - Costruzione dataset per analisi survival
   - Calcolo parametri Weibull e curve KM

4. **Previsioni**:
   - Generazione previsioni per componente/modello
   - Calcolo quantità ordini suggerite
   - Creazione grafici e report

5. **Consultazione**:
   - Navigazione dashboard per visualizzare risultati
   - Esportazione dati per reportistica esterna

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

## Prossimi Sviluppi

- Migrazione completa a PostgreSQL
- API REST per integrazioni esterne
- Ottimizzazione performance calcoli Weibull
- Dashboard interattiva con grafici dinamici
- Export automatico report PDF

---

**Versione Python**: 3.13.4
**Framework**: Flask 3.x
**Database**: PostgreSQL 12+
**Licenza**: Proprietaria
