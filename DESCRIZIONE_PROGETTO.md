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
  ├── auth.py            # Autenticazione (login/logout)
  ├── anagrafiche.py     # Gestione file anagrafiche componenti
  ├── rotture.py         # Gestione file rotture storiche
  ├── ordini.py          # Gestione ordini di acquisto
  ├── previsioni.py      # Calcolo e visualizzazione previsioni
  └── users.py           # Gestione utenti (admin)

templates/               # Template HTML Jinja2
static/                  # CSS, JavaScript, immagini, grafici
utils/                   # Decoratori e utility
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

### 3. Gestione Ordini di Acquisto
- Caricamento ordini in formato Excel
- Tracking ordini per anno e stato di elaborazione
- Storage in `INPUT/ORDINI/{anno}/`

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
- Gestione utenti con autenticazione e ruoli

**anagrafiche_file**
- Tracking file Excel anagrafiche (anno, marca, filepath, esito)

**rotture**
- Tracking file rotture storiche (anno, filename, data acquisizione/elaborazione)

**ordini_acquisto**
- Tracking file ordini (anno, filepath, esito elaborazione)

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
