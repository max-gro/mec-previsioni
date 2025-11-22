# 🔧 MEC Previsioni

**Sistema di analisi predittiva per la manutenzione di componenti meccanici**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask Version](https://img.shields.io/badge/flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 📋 Tabella dei Contenuti

- [Panoramica](#-panoramica)
- [Caratteristiche](#-caratteristiche)
- [Requisiti](#-requisiti)
- [Installazione](#-installazione)
- [Configurazione](#-configurazione)
- [Utilizzo](#-utilizzo)
- [Architettura](#-architettura)
- [Sviluppo](#-sviluppo)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Licenza](#-licenza)

---

## 🎯 Panoramica

**MEC Previsioni** è un'applicazione web sviluppata in Flask per la **gestione e l'analisi predittiva delle rotture di componenti meccanici**.

Il sistema implementa modelli di **survival analysis** (Kaplan-Meier e distribuzioni Weibull) per prevedere quando i componenti potrebbero guastarsi, permettendo una **pianificazione ottimale degli ordini di acquisto** e una manutenzione preventiva efficace.

### Il Problema

Le aziende che gestiscono macchinari complessi devono:
- Prevedere quando i componenti potrebbero guastarsi
- Ottimizzare gli ordini di ricambi evitando sprechi
- Minimizzare i fermi macchina non pianificati
- Analizzare pattern di rottura storici

### La Soluzione

MEC Previsioni analizza dati storici di rottura e utilizza modelli statistici avanzati per:
- ✅ Stimare la probabilità di guasto nel tempo
- ✅ Calcolare intervalli di confidenza delle previsioni
- ✅ Suggerire quantità ottimali per ordini futuri
- ✅ Visualizzare curve di sopravvivenza per componente
- ✅ Tracciare elaborazioni e gestire file dati

---

## ✨ Caratteristiche

### Core Features

- 🔬 **Survival Analysis**
  - Kaplan-Meier (stima non parametrica)
  - Weibull Bayesiano (modello parametrico)
  - Confidence bands con bootstrap

- 📊 **Gestione Dati (4 Pipeline)**
  - Upload file PDF (ordini di acquisto)
  - Upload file Excel (anagrafiche BOM, rotture)
  - Upload file TSV (stock giacenze)
  - Parsing automatico con validazione
  - Tracciamento stato elaborazioni
  - Storicizzazione modifiche

- 📈 **Visualizzazioni**
  - Curve di sopravvivenza
  - Grafici Weibull fit
  - Dashboard KPI
  - Export grafici PNG/JSON

- 🔐 **Sicurezza**
  - Autenticazione utenti (Flask-Login)
  - Gestione ruoli (admin/user)
  - Password hashing (Werkzeug)
  - CSRF protection
  - Session management

- 🗄️ **Database**
  - SQLite (development)
  - PostgreSQL (production)
  - Migrazioni versionare (Flask-Migrate)
  - User tracking (created_by, updated_by)

---

## 📋 Requisiti

### Sistema

- **Python**: >= 3.9
- **Database**:
  - SQLite 3.x (development)
  - PostgreSQL 12+ (production, opzionale)
- **Sistema Operativo**: Linux, macOS, Windows

### Python Packages

Vedere [`requirements.txt`](requirements.txt) per la lista completa.

**Principali dipendenze:**
- Flask 3.1.0
- pandas 2.2.3
- numpy 2.1.3
- lifelines 0.29.0 (survival analysis)
- matplotlib 3.9.2
- Flask-SQLAlchemy 3.1.1
- gunicorn 23.0.0 (production)

---

## 🚀 Installazione

### 1. Clone Repository

```bash
git clone <repository-url>
cd mec-previsioni
```

### 2. Virtual Environment

```bash
# Crea virtual environment
python -m venv venv

# Attiva virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Installa Dipendenze

#### Opzione A: SQLite (Consigliato per Development/Windows)

**Nessuna dipendenza aggiuntiva richiesta!** SQLite è incluso in Python.

```bash
# Production
pip install -r requirements.txt

# Development (include testing e linting)
pip install -r requirements-dev.txt
```

#### Opzione B: PostgreSQL (Production)

**Linux/macOS:**
```bash
# Installa dipendenze base + PostgreSQL driver
pip install -r requirements-postgres.txt
```

**Windows:**

⚠️ **NOTA**: Su Windows, psycopg2-binary richiede Visual C++ Build Tools.

**Consigliato**: Usa SQLite (opzione A sopra) per evitare problemi di compilazione.

Se hai bisogno di PostgreSQL:

1. **Installa Visual C++ Build Tools**
   - Scarica da: [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Seleziona "Desktop development with C++"
   - Installa (può richiedere 3-7 GB)

2. **Installa dipendenze PostgreSQL**
   ```bash
   pip install -r requirements-postgres.txt
   ```

**Alternativa Windows**: Usa wheel pre-compilato
```bash
# 1. Scarica wheel da: https://www.lfd.uci.edu/~gohlke/pythonlibs/#psycopg
# 2. Installa wheel
pip install psycopg2‑2.9.9‑cp39‑cp39‑win_amd64.whl
# 3. Installa resto dipendenze
pip install -r requirements.txt
```

### 4. Configurazione

```bash
# Copia template di configurazione
cp .env.example .env

# Genera SECRET_KEY sicura
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Modifica .env e aggiungi SECRET_KEY
nano .env
```

### 5. Inizializza Database

```bash
# Il database viene creato automaticamente al primo avvio
python app.py

# Le credenziali di default saranno in logs/app.log
```

---

## ⚙️ Configurazione

### Variabili d'Ambiente (.env)

File: `.env` (creato da `.env.example`)

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here

# Database (opzionale, default: SQLite)
# DATABASE_URL=postgresql://user:password@localhost:5432/mec_previsioni

# Default User Passwords (opzionale)
# ADMIN_DEFAULT_PASSWORD=secure-password
# DEMO_DEFAULT_PASSWORD=secure-password

# File Paths (opzionale, per personalizzare percorsi dati)
# ROTTURE_FILE_PATH=/custom/path/to/rotture.xlsx
# ANAGRAFICA_FILE_PATH=/custom/path/to/anagrafica.xlsx
```

### Configurazione Database

**SQLite (Development):**
```python
# Automatico, nessuna configurazione necessaria
# Database creato in: instance/mec.db
```

**PostgreSQL (Production):**
```bash
# 1. Avvia PostgreSQL con Docker
docker compose -f docker-compose.postgres.yml up -d

# 2. Configura .env
DATABASE_URL=postgresql://mec:password@localhost:5432/mec_previsioni

# 3. Avvia applicazione
python app.py
```

---

## 📖 Utilizzo

### Avvio Applicazione

**Development:**
```bash
python app.py
```

**Production (con Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5010 "app:create_app()"
```

### Accesso Web UI

```
URL: http://localhost:5010
```

**Credenziali di default:**
- **Admin**: `admin` / (vedi `logs/app.log` al primo avvio)
- **Demo**: `demo` / (vedi `logs/app.log` al primo avvio)

⚠️ **IMPORTANTE**: Cambiare le password dopo il primo login!

### Workflow Tipico

1. **Login** con credenziali admin
2. **Upload File** per le 4 pipeline:
   - **Ordini**: File PDF ordini di acquisto
   - **Anagrafiche**: File Excel con distinte base (BOM) componenti
   - **Rotture**: File Excel con storico rotture
   - **Stock**: File TSV con giacenze magazzino
3. **Elabora Dati**: Processa file caricati (parsing automatico)
4. **Esplora Dati**: Usa Explorer per cercare e filtrare dati elaborati
5. **Visualizza Previsioni**: Accedi a dashboard previsioni e statistiche
6. **Export Risultati**: Scarica CSV, grafici e JSON

---

## 🏗️ Architettura

### Struttura Directory

```
mec-previsioni/
├── app.py                      # Entry point Flask
├── config.py                   # Configurazioni (Dev/Prod)
├── models.py                   # Modelli SQLAlchemy
├── forms.py                    # WTForms validazione
├── functions.py                # Analisi statistica
├── preprocessing.py            # Elaborazione dati
│
├── routes/                     # Blueprint Flask
│   ├── auth.py                # Autenticazione
│   ├── ordini.py              # Pipeline Ordini (PDF)
│   ├── ordini_explorer.py     # Ordini Explorer
│   ├── anagrafiche.py         # Pipeline Anagrafiche (Excel)
│   ├── anagrafiche_catalogo.py # Catalogo Modelli & Componenti
│   ├── rotture.py             # Pipeline Rotture (Excel)
│   ├── rotture_explorer.py    # Rotture Explorer
│   ├── stock.py               # Pipeline Stock (TSV)
│   ├── stock_explorer.py      # Stock Explorer
│   ├── previsioni.py          # Calcolo previsioni
│   ├── users.py               # Gestione utenti
│   └── dashboard.py           # Dashboard KPI
│
├── templates/                  # Template Jinja2
│   ├── base.html              # Layout base
│   ├── home.html              # Homepage
│   ├── help.html              # Guida utente
│   ├── errors/                # Pagine errore
│   ├── dashboard/             # Dashboard elaborazioni
│   ├── ordini/                # Template ordini
│   ├── anagrafiche/           # Template anagrafiche
│   ├── rotture/               # Template rotture
│   ├── stock/                 # Template stock
│   └── previsioni/            # Template previsioni
│
├── utils/                      # Utility
│   ├── decorators.py          # @admin_required, @handle_errors
│   └── db_log.py              # Logging database
│
├── static/                     # Asset statici
│   ├── images/                # Immagini
│   ├── pred_charts/           # Grafici generati
│   └── pred_charts_stat/      # Grafici statistici
│
├── migrations/                 # Database migrations
├── tests/                      # Test suite
├── logs/                       # Log applicazione
├── instance/                   # Database SQLite
│
├── INPUT/                      # File input (git-ignored)
│   ├── ordini/                # PDF ordini da elaborare
│   ├── anagrafiche/           # Excel BOM da elaborare
│   ├── rotture/               # Excel rotture da elaborare
│   └── stock/                 # TSV giacenze da elaborare
│
└── OUTPUT/                     # File output (git-ignored)
    ├── ordini/                # PDF elaborati
    ├── anagrafiche/           # Excel elaborati
    ├── rotture/               # Excel elaborati
    └── stock/                 # TSV elaborati
```

### Stack Tecnologico

| Layer | Tecnologia |
|-------|------------|
| **Backend** | Flask 3.x |
| **Database** | PostgreSQL / SQLite |
| **ORM** | SQLAlchemy |
| **Data Analysis** | Pandas, NumPy |
| **Statistical Models** | Lifelines (Kaplan-Meier, Weibull) |
| **Visualization** | Matplotlib |
| **Authentication** | Flask-Login, Werkzeug |
| **Forms** | WTForms |
| **Server** | Gunicorn |

### Modelli Database (Principali)

- **User**: Autenticazione e autorizzazione
- **FileAnagrafica**: Tracking file anagrafiche Excel
- **FileRottura**: Tracking file rotture storiche
- **FileOrdine**: Tracking ordini di acquisto
- **Modello**: Anagrafica modelli prodotto
- **Componente**: Anagrafica componenti
- **Rottura**: Eventi di guasto
- **TraceElab**: Tracciamento elaborazioni

Vedere [`MODELS_STRUCTURE.md`](MODELS_STRUCTURE.md) per dettagli.

---

## 🛠️ Sviluppo

### Setup Ambiente di Sviluppo

```bash
# Installa dipendenze dev
pip install -r requirements-dev.txt

# Installa pre-commit hooks
pre-commit install
```

### Comandi Makefile

```bash
# Mostra tutti i comandi disponibili
make help

# Formatta codice
make format

# Linting
make lint

# Test
make test

# Coverage
make test-cov

# CI completo (format + lint + test)
make ci
```

### Code Quality Tools

- **Black**: Code formatter (88 char line length)
- **isort**: Import sorting
- **flake8**: PEP8 linting
- **pylint**: Advanced static analysis
- **mypy**: Type checking
- **bandit**: Security checks
- **pre-commit**: Automatic hooks

### Workflow di Sviluppo

1. Crea feature branch: `git checkout -b feature/nome-feature`
2. Sviluppa e testa localmente
3. Formatta codice: `make format`
4. Lint: `make lint`
5. Test: `make test`
6. Commit (pre-commit hooks si attivano automaticamente)
7. Push e crea Pull Request

Vedere [`DEVELOPMENT.md`](DEVELOPMENT.md) per guida completa.

---

## ✅ Testing

### Esegui Test

```bash
# Tutti i test
pytest

# Con coverage
pytest --cov --cov-report=html

# Solo unit test
pytest -m unit

# Solo integration test
pytest -m integration

# Test specifico
pytest tests/test_models.py::test_user_creation -v
```

### Coverage Report

```bash
# Genera report HTML
make test-cov

# Apri report
make coverage
```

### Struttura Test

```
tests/
├── conftest.py              # Fixtures pytest
├── unit/                    # Unit tests
│   ├── test_models.py
│   ├── test_functions.py
│   └── test_preprocessing.py
└── integration/             # Integration tests
    ├── test_routes.py
    └── test_database.py
```

---

## 🚢 Deployment

### Production con Docker

```bash
# Build immagine
docker build -t mec-previsioni:latest .

# Run container
docker run -d \
  -p 5010:5010 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=postgresql://... \
  --name mec-previsioni \
  mec-previsioni:latest
```

### Production con Gunicorn

```bash
# Installa dipendenze production
pip install -r requirements.txt

# Configura environment
export SECRET_KEY=your-secret-key
export DATABASE_URL=postgresql://...
export FLASK_ENV=production

# Avvia con gunicorn
gunicorn -w 4 -b 0.0.0.0:5010 "app:create_app(config.ProductionConfig)"
```

### Environment Variables (Production)

```bash
# OBBLIGATORIO
SECRET_KEY=<generate-with-secrets-module>

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Session
SESSION_COOKIE_SECURE=True

# Logging
LOG_LEVEL=INFO
```

---

## 🔍 Troubleshooting

### Problema: "SECRET_KEY not set"

**Soluzione:**
```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Copia output in .env come SECRET_KEY=...
```

### Problema: "ModuleNotFoundError"

**Soluzione:**
```bash
# Verifica virtual environment attivo
which python  # Deve puntare a venv/bin/python

# Reinstalla dipendenze
pip install -r requirements.txt --force-reinstall
```

### Problema: "Database locked" (SQLite)

**Soluzione:**
```bash
# Usa PostgreSQL in production
# Oppure aumenta timeout SQLite in config.py
```

### Problema: File mancanti per modulo Previsioni

**Errore:**
```
FileNotFoundError: File richiesti mancanti per il modulo Previsioni
```

**Soluzione:**
Verificare che esistano:
- `output_rotture_filtrate_completate.xlsx`
- `OUTPUT/output_anagrafica.xlsx`
- `output_modelli.json`
- `output_modelli_per_data.json`

Oppure configurare path custom in `.env`.

### Logs

```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/errors.log
```

---

## 📚 Documentazione Aggiuntiva

- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Guida sviluppatori completa
- **[DESCRIZIONE_PROGETTO.md](DESCRIZIONE_PROGETTO.md)**: Descrizione tecnica dettagliata
- **[MODELS_STRUCTURE.md](MODELS_STRUCTURE.md)**: Struttura database
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)**: Guida migrazioni database

---

## 🤝 Contributing

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit delle modifiche (`git commit -m 'feat: Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

### Commit Message Convention

Usa [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nuova feature
- `fix:` Bug fix
- `docs:` Documentazione
- `style:` Formattazione
- `refactor:` Refactoring
- `test:` Test
- `chore:` Manutenzione

---

## 📄 Licenza

Proprietario - Tutti i diritti riservati

---

## 👥 Team

Sviluppato da **[Your Team Name]**

---

## 📞 Supporto

Per problemi o domande:
- Apri una issue su GitHub
- Email: support@yourcompany.com
- Documentazione: [Wiki del progetto]

---

**Built with ❤️ using Flask and Python**
