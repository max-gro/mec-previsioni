# 🚀 Guida Deployment - MEC Previsioni

Guida completa al deployment dell'applicazione MEC Previsioni su diverse architetture.

---

## 📋 Indice

- [Architetture Supportate](#architetture-supportate)
- [1. Development Locale (Laptop)](#1-development-locale-laptop)
- [2. Server Development/Test](#2-server-developmenttest)
- [3. Server Production](#3-server-production)
- [Manutenzione](#manutenzione)
- [Troubleshooting](#troubleshooting)
- [Monitoring](#monitoring)

---

## 🏗️ Architetture Supportate

### 1. **Development Locale** (Laptop)
```
Browser → Flask Development Server (port 5010)
```
- Uso: Sviluppo e testing locale
- Performance: Bassa (single-threaded)
- Sicurezza: Nessuna
- Auto-reload: Sì

### 2. **Development/Test Server**
```
Browser → Apache (port 80/443) → Gunicorn (port 5010) → Flask
```
- Uso: Testing pre-produzione, demo
- Performance: Media (multi-worker)
- Sicurezza: Media (HTTPS opzionale)
- Scalabilità: Limitata

### 3. **Production Server**
```
Browser → Load Balancer → Apache (port 80/443) → Gunicorn (multiple ports) → Flask
```
- Uso: Produzione
- Performance: Alta (load balanced)
- Sicurezza: Alta (HTTPS obbligatorio, headers security)
- Scalabilità: Alta (horizontal scaling)

---

## 1. Development Locale (Laptop)

### Prerequisiti

```bash
- Python 3.9+
- pip
- virtualenv
```

### Setup

```bash
# 1. Clona repository
git clone <repo-url>
cd mec-previsioni

# 2. Crea virtual environment
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Configura .env
cp .env.example .env
nano .env  # Edita SECRET_KEY, ADMIN_PASSWORD

# 5. Inizializza database
python -c "from app import create_app; app = create_app(); app.app_context().push(); from extensions import db; db.create_all()"
```

### Avvio

```bash
# Metodo 1: Python diretto
python app.py

# Metodo 2: Flask CLI
export FLASK_APP=app:create_app
flask run --host=0.0.0.0 --port=5010
```

Accedi su: **http://localhost:5010**

---

## 2. Server Development/Test

### Architettura
**Apache (Reverse Proxy) → Gunicorn (Application Server) → Flask**

### Prerequisiti Server

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv apache2 git

# Enable Apache modules
sudo a2enmod proxy proxy_http headers ssl rewrite
```

### 1. Setup Applicazione

```bash
# 1. Crea directory applicazione
sudo mkdir -p /var/www/mec-previsioni
sudo chown -R $USER:www-data /var/www/mec-previsioni

# 2. Clona repository
cd /var/www/mec-previsioni
git clone <repo-url> .

# 3. Crea virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Installa dipendenze
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configura .env
cp .env.example .env
nano .env

# Configura almeno:
# - SECRET_KEY (genera con: python -c "import secrets; print(secrets.token_hex(32))")
# - FLASK_ENV=production
# - ADMIN_PASSWORD=secure_password
# - DATABASE_URL (se usi PostgreSQL)

# 6. Crea directory necessarie
mkdir -p logs static/pred_charts static/pred_charts_stat INPUT OUTPUT

# 7. Permessi
sudo chown -R www-data:www-data /var/www/mec-previsioni
sudo chmod -R 755 /var/www/mec-previsioni
sudo chmod -R 775 logs INPUT OUTPUT static
```

### 2. Configurazione Gunicorn

```bash
# Testa Gunicorn manualmente
source /var/www/mec-previsioni/venv/bin/activate
gunicorn --config deployment/gunicorn/gunicorn_config.py 'app:create_app()'
# Ctrl+C per fermare

# Verifica su http://localhost:5010
```

### 3. Configurazione Systemd

```bash
# Copia service file
sudo cp deployment/systemd/mec-previsioni.service /etc/systemd/system/

# Ricarica systemd
sudo systemctl daemon-reload

# Abilita avvio automatico
sudo systemctl enable mec-previsioni

# Avvia servizio
sudo systemctl start mec-previsioni

# Verifica status
sudo systemctl status mec-previsioni

# Logs
sudo journalctl -u mec-previsioni -f
```

### 4. Configurazione Apache

```bash
# Copia configurazione Apache
sudo cp deployment/apache/mec-previsioni-dev.conf /etc/apache2/sites-available/

# Modifica configurazione (aggiorna ServerName)
sudo nano /etc/apache2/sites-available/mec-previsioni-dev.conf

# Abilita sito
sudo a2ensite mec-previsioni-dev

# Disabilita default (opzionale)
sudo a2dissite 000-default

# Testa configurazione
sudo apache2ctl configtest

# Riavvia Apache
sudo systemctl restart apache2
```

### 5. Configurazione DNS/Hosts

```bash
# Aggiungi al DNS o al file /etc/hosts
sudo nano /etc/hosts

# Aggiungi:
127.0.0.1   dev.mec-previsioni.local
```

### Test

```bash
# Verifica Gunicorn
curl http://localhost:5010

# Verifica Apache
curl http://dev.mec-previsioni.local
```

### SSL Self-Signed (Opzionale per Dev/Test)

```bash
# Genera certificato self-signed
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/mec-dev-selfsigned.key \
  -out /etc/ssl/certs/mec-dev-selfsigned.crt

# Decommentare sezione HTTPS in mec-previsioni-dev.conf
sudo nano /etc/apache2/sites-available/mec-previsioni-dev.conf

# Abilita mod_ssl
sudo a2enmod ssl

# Riavvia Apache
sudo systemctl restart apache2
```

---

## 3. Server Production

### Architettura
**Load Balancer → Apache (Reverse Proxy) → Gunicorn (Multi-Port) → Flask**

### Prerequisiti

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv apache2 git \
  postgresql postgresql-contrib certbot python3-certbot-apache

# Enable Apache modules
sudo a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests \
  headers ssl rewrite expires deflate
```

### 1. Setup Applicazione (identico a Dev/Test)

Segui i passi 1-3 della sezione Development/Test.

**IMPORTANTE**: In production:
- Usa PostgreSQL invece di SQLite
- Setta `FLASK_ENV=production` nel `.env`
- Usa password robuste per ADMIN_PASSWORD
- Configura `DATABASE_URL` per PostgreSQL

### 2. Configurazione PostgreSQL

```bash
# Crea database
sudo -u postgres psql

postgres=# CREATE DATABASE mec_previsioni;
postgres=# CREATE USER mec_user WITH ENCRYPTED PASSWORD 'secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE mec_previsioni TO mec_user;
postgres=# \q

# Aggiorna .env
DATABASE_URL=postgresql://mec_user:secure_password@localhost:5432/mec_previsioni
```

### 3. Configurazione Gunicorn Multi-Worker

Per production con load balancing, avvia più istanze Gunicorn su porte diverse:

```bash
# Modifica gunicorn_config.py per ogni worker
# Worker 1: bind = "127.0.0.1:5010"
# Worker 2: bind = "127.0.0.1:5011"
# Worker 3: bind = "127.0.0.1:5012"

# Oppure crea più service files systemd
sudo cp deployment/systemd/mec-previsioni.service /etc/systemd/system/mec-previsioni@.service

# Modifica per usare parametro porta
# ExecStart=... --bind 127.0.0.1:%i ...

# Avvia workers
sudo systemctl enable mec-previsioni@5010
sudo systemctl enable mec-previsioni@5011
sudo systemctl start mec-previsioni@5010
sudo systemctl start mec-previsioni@5011
```

### 4. Configurazione Apache Production

```bash
# Copia configurazione
sudo cp deployment/apache/mec-previsioni-prod.conf /etc/apache2/sites-available/

# Modifica (aggiorna ServerName, certificati SSL)
sudo nano /etc/apache2/sites-available/mec-previsioni-prod.conf

# Abilita sito
sudo a2ensite mec-previsioni-prod

# Testa configurazione
sudo apache2ctl configtest

# Riavvia Apache
sudo systemctl restart apache2
```

### 5. SSL con Let's Encrypt

```bash
# Ottieni certificato (interattivo)
sudo certbot --apache -d mec-previsioni.yourdomain.com

# Oppure manuale
sudo certbot certonly --apache -d mec-previsioni.yourdomain.com

# Certbot configura auto-renewal
sudo systemctl status certbot.timer

# Test renewal
sudo certbot renew --dry-run
```

### 6. Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 'Apache Full'
sudo ufw allow ssh
sudo ufw enable
```

### 7. Backup Automatico

```bash
# Crea script backup
sudo nano /usr/local/bin/backup-mec.sh
```

```bash
#!/bin/bash
# Backup MEC Previsioni

BACKUP_DIR="/backups/mec-previsioni"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database PostgreSQL
sudo -u postgres pg_dump mec_previsioni > $BACKUP_DIR/db_$DATE.sql

# Backup file applicazione
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /var/www/mec-previsioni \
  --exclude=venv --exclude=__pycache__ --exclude=*.pyc

# Mantieni solo ultimi 7 backup
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "app_*.tar.gz" -mtime +7 -delete
```

```bash
# Permessi
sudo chmod +x /usr/local/bin/backup-mec.sh

# Cron job (daily alle 2:00 AM)
sudo crontab -e
# Aggiungi:
0 2 * * * /usr/local/bin/backup-mec.sh
```

---

## 🔧 Manutenzione

### Aggiornamento Applicazione

```bash
# 1. Ferma servizio
sudo systemctl stop mec-previsioni

# 2. Backup
sudo tar -czf /tmp/mec-backup-$(date +%F).tar.gz /var/www/mec-previsioni

# 3. Pull nuova versione
cd /var/www/mec-previsioni
git pull origin main

# 4. Aggiorna dipendenze
source venv/bin/activate
pip install -r requirements.txt

# 5. Migrazioni DB (se necessarie)
# flask db upgrade

# 6. Riavvia servizio
sudo systemctl start mec-previsioni

# 7. Verifica
sudo systemctl status mec-previsioni
sudo journalctl -u mec-previsioni -n 50
```

### Restart Servizi

```bash
# Gunicorn
sudo systemctl restart mec-previsioni

# Apache
sudo systemctl restart apache2

# Entrambi
sudo systemctl restart mec-previsioni apache2
```

### Logs

```bash
# Gunicorn logs (systemd)
sudo journalctl -u mec-previsioni -f

# Gunicorn logs (file)
tail -f /var/www/mec-previsioni/logs/gunicorn-error.log
tail -f /var/www/mec-previsioni/logs/gunicorn-access.log

# Apache logs
sudo tail -f /var/log/apache2/mec-previsioni-prod-error.log
sudo tail -f /var/log/apache2/mec-previsioni-prod-access.log

# Application logs
tail -f /var/www/mec-previsioni/logs/app.log
```

---

## 🐛 Troubleshooting

### Problema: Gunicorn non parte

```bash
# Verifica configurazione
sudo systemctl status mec-previsioni

# Logs dettagliati
sudo journalctl -u mec-previsioni -xe

# Testa manualmente
cd /var/www/mec-previsioni
source venv/bin/activate
gunicorn --config deployment/gunicorn/gunicorn_config.py 'app:create_app()'

# Verifica permessi
ls -la /var/www/mec-previsioni
sudo chown -R www-data:www-data /var/www/mec-previsioni
```

### Problema: Apache 502 Bad Gateway

```bash
# Verifica Gunicorn in ascolto
sudo netstat -tlnp | grep 5010

# Testa connessione Gunicorn
curl http://127.0.0.1:5010

# Verifica proxy Apache
sudo apache2ctl -M | grep proxy

# Logs Apache
sudo tail -f /var/log/apache2/error.log
```

### Problema: Static files non caricano

```bash
# Verifica permissions
sudo chown -R www-data:www-data /var/www/mec-previsioni/static
sudo chmod -R 755 /var/www/mec-previsioni/static

# Verifica configurazione Apache (Alias /static)
sudo nano /etc/apache2/sites-available/mec-previsioni-prod.conf
```

### Problema: Database connection error

```bash
# Verifica PostgreSQL attivo
sudo systemctl status postgresql

# Testa connessione
psql -h localhost -U mec_user -d mec_previsioni

# Verifica DATABASE_URL in .env
cat /var/www/mec-previsioni/.env | grep DATABASE_URL
```

---

## 📊 Monitoring

### Health Check

```bash
# Script health check
curl -I https://mec-previsioni.yourdomain.com
```

### Performance Monitoring

```bash
# Apache status
sudo a2enmod status
# Aggiungi a vhost:
# <Location /server-status>
#     SetHandler server-status
#     Require ip 127.0.0.1
# </Location>

# Accedi: http://localhost/server-status
```

### Uptime Monitoring

Usa servizi esterni tipo:
- UptimeRobot
- Pingdom
- StatusCake

### Application Performance Monitoring (APM)

Considera integrare:
- Sentry (error tracking)
- New Relic
- DataDog

---

## 🔒 Security Checklist Production

- [ ] HTTPS obbligatorio (Let's Encrypt)
- [ ] SECRET_KEY robusta (32+ char random)
- [ ] Database password sicure
- [ ] Firewall configurato (solo porte 80, 443, SSH)
- [ ] SSH key-based auth (no password)
- [ ] Regular security updates (`sudo apt update && sudo apt upgrade`)
- [ ] Backup automatici configurati
- [ ] Logs rotation configurata
- [ ] Fail2ban per SSH bruteforce protection
- [ ] ModSecurity o mod_evasive (Apache WAF)
- [ ] Rate limiting applicativo
- [ ] File upload scanning antivirus
- [ ] Security headers configurati (HSTS, CSP, etc.)
- [ ] Directory listing disabilitato
- [ ] .env non accessibile via web

---

## 📞 Supporto

Per problemi o domande:
- Consulta logs: `sudo journalctl -u mec-previsioni -f`
- Verifica status: `sudo systemctl status mec-previsioni apache2`
- Contatta team tecnico: [email]

