# 📊 MEC Previsioni

Sistema di previsione dell'affidabilità dei componenti basato su analisi di sopravvivenza (Kaplan-Meier e Weibull).

---

## 📋 Indice

- [Caratteristiche](#caratteristiche)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo](#utilizzo)
- [Struttura del Progetto](#struttura-del-progetto)
- [Sicurezza](#sicurezza)
- [Deployment](#deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## ✨ Caratteristiche

- **Analisi di Affidabilità**: Curve di sopravvivenza Kaplan-Meier e Weibull
- **Gestione Anagrafiche**: Upload e gestione file Excel componenti
- **Gestione Rotture**: Tracciamento rotture componenti
- **Gestione Ordini**: Upload e processamento ordini di acquisto (PDF)
- **Previsioni**: Calcolo probabilità di rottura a 12, 24, 36 mesi
- **Autenticazione**: Sistema login con ruoli (admin/user)
- **Export Excel**: Esportazione previsioni multi-foglio

---

## 🔧 Requisiti

### Software
- Python 3.9+
- pip (package manager Python)
- PostgreSQL 13+ (produzione) o SQLite (development)

### Sistema Operativo
- Linux (raccomandato)
- Windows 10+
- macOS 10.15+

---

## 📦 Installazione

### 1. Clona il Repository

```bash
git clone https://github.com/your-org/mec-previsioni.git
cd mec-previsioni
```

### 2. Crea Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Installa Dipendenze

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ Configurazione

### 1. Crea File `.env`

Copia il template e personalizza:

```bash
cp .env.example .env
```

### 2. Genera Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copia l'output e aggiungilo al file `.env`:

```env
SECRET_KEY=tua-chiave-generata-qui
```

### 3. Configura Database

#### Development (SQLite)

Lascia DATABASE_URL commentato in `.env`, verrà usato SQLite di default:

```env
# DATABASE_URL non settata → usa SQLite in instance/mec.db
```

#### Production (PostgreSQL)

Imposta DATABASE_URL nel `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/mec_previsioni
```

### 4. Configura Credenziali Admin

**⚠️ OBBLIGATORIO IN PRODUZIONE!**

Nel file `.env`:

```env
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your-secure-password-here
```

### 5. Crea Directory Necessarie

```bash
mkdir -p INPUT/{rotture,po} OUTPUT/{rotture,anagrafiche} logs static/{pred_charts,pred_charts_stat}
```

---

## 🚀 Utilizzo

### Development Server

```bash
# Attiva virtual environment
source venv/bin/activate  # Linux/macOS
# oppure
venv\Scripts\activate     # Windows

# Avvia server development
python app.py
```

Il server sarà disponibile su: **http://localhost:5010**

### Production Server (Gunicorn)

```bash
# Imposta ambiente production
export FLASK_ENV=production

# Avvia con Gunicorn (4 workers)
gunicorn -w 4 -b 0.0.0.0:5010 'app:create_app()'
```

### Docker (Opzionale)

```bash
# Con PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d
```

---

## 📁 Struttura del Progetto

```
mec-previsioni/
├── app.py                    # Application factory
├── config.py                 # Configurazioni (Dev/Prod/Test)
├── models.py                 # Modelli database (SQLAlchemy)
├── forms.py                  # Form validazione (WTForms)
├── functions.py              # Funzioni analisi statistica
├── preprocessing.py          # Preprocessing dati
│
├── routes/                   # Blueprint Flask
│   ├── auth.py              # Login/Logout
│   ├── users.py             # Gestione utenti
│   ├── anagrafiche.py       # Gestione anagrafiche
│   ├── rotture.py           # Gestione rotture
│   ├── ordini.py            # Gestione ordini
│   └── previsioni.py        # Calcolo previsioni
│
├── templates/                # Template Jinja2
│   ├── base.html
│   ├── index.html
│   ├── errors/              # Template errori (403, 404, 500)
│   └── ...
│
├── static/                   # File statici
│   ├── pred_charts/         # Grafici previsioni
│   └── pred_charts_stat/
│
├── utils/                    # Utility
│   └── decorators.py        # Decoratori custom
│
├── scripts/                  # Script migrazione/setup
│   ├── init_db.py
│   └── migrate_*.py
│
├── preprocessing_PO/         # Pipeline preprocessing ordini
│
├── .env.example              # Template variabili ambiente
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔒 Sicurezza

### Best Practice Implementate

#### ✅ Credenziali
- ❌ **NO** credenziali hardcoded nel codice
- ✅ Credenziali caricate da variabili d'ambiente (`.env`)
- ✅ File `.env` escluso da git (`.gitignore`)

#### ✅ Secret Key
- ✅ Secret key generata casualmente
- ✅ Fallimento obbligatorio in produzione se non settata
- ✅ Chiave temporanea auto-generata in development

#### ✅ Session Security
- ✅ `SESSION_COOKIE_HTTPONLY = True` (anti XSS)
- ✅ `SESSION_COOKIE_SAMESITE = Lax` (anti CSRF)
- ✅ `SESSION_COOKIE_SECURE = True` in produzione (HTTPS only)

#### ✅ CSRF Protection
- ✅ Flask-WTF CSRF abilitato
- ✅ Token CSRF timeout: 1 ora
- ✅ Tutti i form protetti con `{{ form.csrf_token }}`

#### ✅ Password Hashing
- ✅ Werkzeug `generate_password_hash()` / `check_password_hash()`
- ✅ Algoritmo: pbkdf2:sha256

#### ✅ File Upload Security
- ✅ `secure_filename()` per sanitizzazione nomi
- ✅ Whitelist estensioni permesse (`.xls`, `.xlsx`, `.pdf`)
- ✅ Limite dimensione file: 100 MB (configurabile)

#### ✅ SQL Injection Protection
- ✅ SQLAlchemy ORM (query parametrizzate)
- ✅ Nessun raw SQL (eccetto versione DB check)

### Raccomandazioni Aggiuntive

1. **HTTPS Obbligatorio in Produzione**
   ```nginx
   # Esempio nginx
   server {
       listen 443 ssl;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       ...
   }
   ```

2. **Rate Limiting** (TODO)
   - Installare `Flask-Limiter`
   - Limitare tentativi login

3. **Backup Regolari**
   ```bash
   # PostgreSQL
   pg_dump mec_previsioni > backup_$(date +%F).sql
   ```

---

## 🐳 Deployment

### Opzione 1: Server Tradizionale (Gunicorn + Nginx)

#### 1. Installa Nginx

```bash
sudo apt install nginx
```

#### 2. Configura Nginx

```nginx
# /etc/nginx/sites-available/mec-previsioni
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/mec-previsioni/static;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/mec-previsioni /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3. Crea Systemd Service

```ini
# /etc/systemd/system/mec-previsioni.service
[Unit]
Description=MEC Previsioni Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/mec-previsioni
Environment="FLASK_ENV=production"
ExecStart=/path/to/mec-previsioni/venv/bin/gunicorn -w 4 -b 127.0.0.1:5010 'app:create_app()'

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start mec-previsioni
sudo systemctl enable mec-previsioni
```

### Opzione 2: Docker

Vedi `docker-compose.postgres.yml`

---

## 🧪 Testing

### Setup Testing (TODO)

```bash
pip install pytest pytest-cov pytest-flask
```

### Run Tests (TODO)

```bash
# Unit tests
pytest tests/

# Con coverage
pytest --cov=app tests/
```

---

## 🐛 Troubleshooting

### Problema: Errore "SECRET_KEY not set" in production

**Causa:** `SECRET_KEY` non configurata nel `.env`

**Soluzione:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Aggiungi output a .env come SECRET_KEY=...
```

---

### Problema: Database connection error

**Causa:** PostgreSQL non raggiungibile o credenziali errate

**Soluzione:**
```bash
# Verifica PostgreSQL attivo
sudo systemctl status postgresql

# Verifica connessione
psql -h localhost -U user -d mec_previsioni

# Controlla DATABASE_URL in .env
```

---

### Problema: Import error "No module named 'X'"

**Causa:** Dipendenze non installate

**Soluzione:**
```bash
pip install -r requirements.txt
```

---

### Problema: File upload fallisce con 413

**Causa:** File supera limite `MAX_CONTENT_LENGTH`

**Soluzione:**
Aumenta limite in `.env`:
```env
MAX_UPLOAD_SIZE_MB=200
```

---

## 📝 Changelog

### v2.0.0 - 2025-01-XX (Refactoring Sicurezza & Architettura)

#### 🔒 Sicurezza
- ✅ Rimossi credenziali hardcoded
- ✅ Secret key robusta con validazione
- ✅ Configurazione ambiente-specifica (Dev/Prod/Test)
- ✅ Session cookie security migliorata
- ✅ CSRF protection configurata

#### 🏗️ Architettura
- ✅ Logging professionale implementato
- ✅ Error handlers personalizzati (403, 404, 500, 413)
- ✅ .gitignore esteso
- ✅ Script migrazione organizzati in `scripts/`
- ✅ Documentazione completa

#### 📦 Configurazione
- ✅ File `.env.example` template
- ✅ Factory function `get_config()`
- ✅ Configurazioni DB migliorate (pool, pre-ping)

---

## 👥 Contributi

Per contribuire al progetto:

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

---

## 📄 Licenza

[Specificare licenza]

---

## 📧 Contatti

Per supporto o domande: [email di contatto]

---

## 🙏 Acknowledgments

- **Lifelines** - Libreria survival analysis
- **Flask** - Web framework
- **Pandas** - Data processing
- **NumPy/SciPy** - Calcoli scientifici
