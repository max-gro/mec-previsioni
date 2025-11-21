# 🛠️ Development Guide - MEC Previsioni

Guida per sviluppatori che contribuiscono al progetto MEC Previsioni.

---

## 📋 Tabella dei Contenuti

- [Setup Ambiente di Sviluppo](#setup-ambiente-di-sviluppo)
- [Gestione Dipendenze](#gestione-dipendenze)
- [Code Quality & Testing](#code-quality--testing)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Workflow di Sviluppo](#workflow-di-sviluppo)

---

## 🚀 Setup Ambiente di Sviluppo

### 1. Prerequisiti

- Python >= 3.9
- Git
- PostgreSQL (opzionale, SQLite funziona per development)

### 2. Clone e Setup Iniziale

```bash
# Clone repository
git clone <repository-url>
cd mec-previsioni

# Crea virtual environment
python -m venv venv

# Attiva virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Installa dipendenze di sviluppo
pip install -r requirements-dev.txt
```

### 3. Configurazione Ambiente

```bash
# Copia template di configurazione
cp .env.example .env

# Genera SECRET_KEY sicura
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Modifica .env e aggiungi la SECRET_KEY generata
```

### 4. Inizializza Database

```bash
# Il database viene creato automaticamente al primo avvio
python app.py

# Le credenziali di default saranno in logs/app.log
```

---

## 📦 Gestione Dipendenze

### File di Dipendenze

- **`requirements.txt`**: Dipendenze di production (pinned)
- **`requirements-dev.txt`**: Dipendenze di sviluppo (testing, linting, etc.)

### Aggiornamento Dipendenze

```bash
# Aggiornare singolo package
pip install --upgrade <package-name>
pip freeze | grep <package-name> >> requirements.txt

# Verificare compatibilità
pip check

# Testare che tutto funzioni
pytest
```

### Aggiungere Nuova Dipendenza

1. **Production dependency:**
   ```bash
   pip install <package>==<version>
   # Aggiungi manualmente a requirements.txt con versione esatta
   ```

2. **Development dependency:**
   ```bash
   pip install <package>==<version>
   # Aggiungi manualmente a requirements-dev.txt
   ```

---

## ✅ Code Quality & Testing

### Formattazione Codice

```bash
# Formatta tutto il codice con Black
black .

# Ordina gli import con isort
isort .

# Esegui entrambi in sequenza
black . && isort .
```

### Linting

```bash
# Flake8 - Controllo stile PEP8
flake8 .

# Pylint - Analisi statica avanzata
pylint app.py routes/ utils/

# Bandit - Security checks
bandit -r . -ll
```

### Type Checking

```bash
# MyPy - Type checking (quando aggiungi type hints)
mypy .
```

### Testing

```bash
# Esegui tutti i test
pytest

# Con coverage report
pytest --cov=. --cov-report=html

# Solo test veloci
pytest -m "not slow"

# Solo test unitari
pytest -m unit

# Apri report coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

---

## 🪝 Pre-commit Hooks

I pre-commit hooks eseguono automaticamente controlli di qualità prima di ogni commit.

### Setup

```bash
# Installa pre-commit hooks
pre-commit install

# Esegui manualmente su tutti i file
pre-commit run --all-files

# Aggiorna hook alle versioni più recenti
pre-commit autoupdate
```

### Hook Configurati

1. **Controlli Base:**
   - Sintassi YAML/JSON/TOML
   - Trailing whitespace
   - Fine file con newline
   - File grandi (>500KB)
   - Merge conflicts
   - Chiavi private hardcoded

2. **Formattazione:**
   - Black (code formatter)
   - isort (import sorting)

3. **Linting:**
   - Flake8 (PEP8 compliance)
   - Bandit (security)

4. **Protezione:**
   - Previene commit su branch main/master

### Saltare Hook (Emergenze)

```bash
# NON RACCOMANDATO - solo per emergenze!
git commit --no-verify -m "Emergency fix"
```

---

## 🔄 Workflow di Sviluppo

### 1. Crea Feature Branch

```bash
git checkout -b feature/nome-feature
```

### 2. Sviluppa e Testa

```bash
# Scrivi codice
# ...

# Formatta
black . && isort .

# Lint
flake8 .

# Test
pytest --cov

# Commit (i pre-commit hooks si attiveranno automaticamente)
git add .
git commit -m "feat: descrizione feature"
```

### 3. Prima di Push

```bash
# Verifica tutto sia OK
pre-commit run --all-files
pytest --cov
flake8 .

# Push
git push -u origin feature/nome-feature
```

### 4. Pull Request

1. Crea PR su GitHub
2. Aspetta review del codice
3. Risolvi eventuali commenti
4. Merge quando approvato

---

## 📝 Convenzioni di Codice

### Stile

- **Black** per formattazione (88 caratteri per riga)
- **isort** per ordinamento import
- **Google style** per docstrings
- **Type hints** dove possibile (opzionale per ora)

### Commit Messages

Usa [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: aggiunge nuova funzionalità
fix: corregge bug
docs: aggiorna documentazione
style: formattazione, missing semi-colons, etc
refactor: refactoring del codice
test: aggiunge test
chore: aggiorna dipendenze, build tasks, etc
```

### Testing

- **Unit tests** per funzioni e classi isolate
- **Integration tests** per route e database
- **Minimum 70% coverage** per nuovo codice
- Test in `tests/` directory con naming `test_*.py`

---

## 🐛 Debugging

### Flask Debug Mode

```bash
# Avvia con debug attivo
python app.py

# Debug toolbar (solo in development)
# Installa: già in requirements-dev.txt
# Toolbar appare automaticamente in development
```

### Logs

```bash
# Visualizza log in tempo reale
tail -f logs/app.log

# Visualizza solo errori
tail -f logs/errors.log
```

### Database Inspection

```bash
# Apri shell interattiva Flask
flask shell

# Esegui query
>>> from models import User
>>> User.query.all()
>>> db.session.execute(text("SELECT * FROM users")).fetchall()
```

---

## 📚 Risorse Aggiuntive

- [Flask Documentation](https://flask.palletsprojects.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

## ❓ Troubleshooting

### Problema: "ImportError: cannot import name 'X'"

```bash
# Reinstalla dipendenze
pip install -r requirements-dev.txt --force-reinstall
```

### Problema: Pre-commit hook fallisce

```bash
# Esegui manualmente per vedere errore dettagliato
pre-commit run --all-files

# Correggi errori segnalati
black .
flake8 .
```

### Problema: Test falliscono

```bash
# Verifica dipendenze
pip check

# Reinstalla test dependencies
pip install -r requirements-dev.txt

# Esegui test singolo per debugging
pytest tests/test_specific.py::test_function_name -v
```

---

**Happy Coding! 🚀**
