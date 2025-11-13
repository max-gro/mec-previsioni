# 🤝 Contributing to MEC Previsioni

Grazie per il tuo interesse nel contribuire al progetto MEC Previsioni! Questa guida ti aiuterà a configurare l'ambiente di sviluppo e a seguire le best practice del progetto.

---

## 📋 Indice

- [Setup Ambiente Sviluppo](#setup-ambiente-sviluppo)
- [Struttura Progetto](#struttura-progetto)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Git Workflow](#git-workflow)
- [Pull Requests](#pull-requests)

---

## 🛠️ Setup Ambiente Sviluppo

### 1. Fork e Clone

```bash
# Fork del repository su GitHub, poi clona
git clone https://github.com/YOUR_USERNAME/mec-previsioni.git
cd mec-previsioni

# Aggiungi upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/mec-previsioni.git
```

### 2. Virtual Environment

```bash
# Crea virtual environment
python3 -m venv venv

# Attiva (Linux/macOS)
source venv/bin/activate

# Attiva (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Dipendenze production
pip install -r requirements.txt

# Dipendenze development (include testing, linting, etc.)
pip install -r requirements-dev.txt
```

### 4. Configura Environment

```bash
# Copia .env.example
cp .env.example .env

# Edita .env e imposta almeno:
# - SECRET_KEY (genera con: python -c "import secrets; print(secrets.token_hex(32))")
# - ADMIN_PASSWORD
nano .env
```

### 5. Inizializza Database

```bash
# Metodo 1: Usando Flask-Migrate (raccomandato)
flask db upgrade

# Metodo 2: Se migrations non esistono ancora
python -c "from app import create_app; app = create_app(); app.app_context().push(); from extensions import db; db.create_all()"
```

### 6. Verifica Setup

```bash
# Avvia server development
python app.py

# In un altro terminale, verifica
curl http://localhost:5010/login
```

---

## 📂 Struttura Progetto

```
mec-previsioni/
├── app.py                  # Application factory
├── config.py               # Configurazioni (Dev/Prod/Test)
├── extensions.py           # Flask extensions (DB, Cache, Limiter, Migrate)
│
├── models/                 # Database models
│   ├── __init__.py
│   ├── user.py            # User model
│   ├── rottura.py         # Rottura model
│   ├── ordine.py          # OrdineAcquisto model
│   └── anagrafica.py      # AnagraficaFile model
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── statistical_service.py     # Weibull, Kaplan-Meier
│   ├── prediction_service.py      # Predictions orchestration
│   ├── chart_service.py           # Chart generation
│   └── data_service.py            # Data loading & helpers
│
├── routes/                 # Flask blueprints
│   ├── auth.py            # Authentication routes
│   ├── users.py           # User management
│   ├── previsioni.py      # Predictions routes
│   ├── rotture.py         # Rotture management
│   ├── ordini.py          # Ordini management
│   └── anagrafiche.py     # Anagrafiche management
│
├── forms.py                # WTForms forms
├── utils/                  # Utilities
│   └── decorators.py      # Custom decorators
│
├── templates/              # Jinja2 templates
├── static/                 # Static files
│
├── tests/                  # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_models.py     # Model tests
│   └── test_auth.py       # Auth tests
│
├── deployment/             # Deployment configurations
│   ├── apache/            # Apache configs
│   ├── gunicorn/          # Gunicorn config
│   └── systemd/           # Systemd service
│
└── scripts/                # Utility scripts
    └── init_migrations.sh
```

---

## 🗄️ Database Migrations

Il progetto usa **Flask-Migrate** (Alembic) per gestire le migrazioni database.

### Creare una Migrazione

Dopo aver modificato i modelli in `models/`:

```bash
# Genera migrazione automatica
flask db migrate -m "Descrizione modifica"

# Esempio:
flask db migrate -m "Add new column to User model"
```

### Applicare Migrazioni

```bash
# Applica tutte le migrazioni pending
flask db upgrade

# Verifica stato
flask db current

# Rollback ultima migrazione
flask db downgrade
```

### Best Practices Migrations

- **Non modificare mai** migrazioni già committate
- **Testa sempre** le migrazioni prima del commit (upgrade + downgrade)
- **Scrivi descrizioni chiare** nel messaggio `-m`
- **Controlla sempre** il file generato prima del commit

### Comandi Utili

```bash
# Storia migrazioni
flask db history

# Upgrade a revisione specifica
flask db upgrade <revision_id>

# Stamp current (senza applicare migrazioni)
flask db stamp head
```

---

## 🧪 Testing

### Run Tests

```bash
# Run tutti i test
pytest

# Run con coverage
pytest --cov

# Run solo test specifici
pytest tests/test_models.py
pytest tests/test_auth.py::TestLogin::test_login_success

# Run con markers
pytest -m unit          # Solo unit tests
pytest -m "not slow"    # Escludi test slow
```

### Scrivere Test

**Esempio test model:**

```python
def test_create_user(db):
    user = User(username='test', email='test@test.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.check_password('password123')
```

**Esempio test route:**

```python
def test_login_success(client, regular_user):
    response = client.post('/login', data={
        'username': regular_user.username,
        'password': 'testpassword123'
    }, follow_redirects=True)

    assert response.status_code == 200
```

### Coverage Target

- **Minimum:** 50% (configurato in pytest.ini)
- **Target:** 70%+
- **Models:** 90%+
- **Services:** 80%+

---

## 🎨 Code Quality

### Linting

```bash
# Flake8
flake8 .

# Pylint
pylint app.py models/ services/

# MyPy (type checking)
mypy app.py
```

### Formatting

```bash
# Black (auto-format)
black .

# isort (import sorting)
isort .

# Check without changes
black --check .
isort --check-only .
```

### Pre-commit Hook (Raccomandato)

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 🌿 Git Workflow

### Branch Naming

```
feature/nome-feature      # Nuove feature
bugfix/nome-bug          # Fix bug
hotfix/nome-hotfix       # Fix urgenti
refactor/nome-refactor   # Refactoring
docs/nome-doc            # Documentazione
test/nome-test           # Aggiunta test
```

### Commit Messages

Usa **Conventional Commits**:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nuova feature
- `fix`: Bug fix
- `docs`: Documentazione
- `style`: Formattazione (no logic changes)
- `refactor`: Refactoring
- `test`: Aggiunta test
- `chore`: Manutenzione

**Esempi:**

```bash
git commit -m "feat(auth): add password reset functionality"
git commit -m "fix(previsioni): correct Weibull calculation"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(models): add User model tests"
```

### Workflow

```bash
# 1. Sync con upstream
git fetch upstream
git checkout main
git merge upstream/main

# 2. Crea branch feature
git checkout -b feature/my-feature

# 3. Sviluppa e commit
git add .
git commit -m "feat: add my feature"

# 4. Push to your fork
git push origin feature/my-feature

# 5. Apri Pull Request su GitHub
```

---

## 📬 Pull Requests

### Checklist Prima del PR

- [ ] Codice formattato con `black` e `isort`
- [ ] Linting passed (`flake8`)
- [ ] Tutti i test passano (`pytest`)
- [ ] Coverage non diminuita
- [ ] Migrations testate (se applicabile)
- [ ] Documentazione aggiornata (se necessario)
- [ ] Changelog aggiornato (se breaking changes)

### Template PR

```markdown
## Description
Breve descrizione delle modifiche

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Punto 1
- Punto 2

## Testing
Describe how you tested this

## Screenshots (if applicable)
[screenshots here]

## Checklist
- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation updated
```

### Review Process

1. **Automated Checks:** CI/CD runs tests
2. **Code Review:** Almeno 1 approval richiesto
3. **Discussion:** Rispondi ai commenti
4. **Merge:** Squash and merge (mantenere storia pulita)

---

## 🐛 Reporting Bugs

Quando riporti un bug, includi:

1. **Versione** Python e dipendenze
2. **Ambiente** (dev/prod, OS, DB)
3. **Steps to Reproduce**
4. **Expected Behavior**
5. **Actual Behavior**
6. **Logs** (se applicabile)
7. **Screenshots** (se applicabile)

---

## 💡 Feature Requests

Per richiedere nuove feature:

1. **Descrizione** chiara della feature
2. **Use Case** e motivazione
3. **Possibili Implementazioni**
4. **Alternative Considerate**

---

## 📞 Supporto

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** [email di supporto]

---

## 📄 Licenza

Contribuendo al progetto, accetti che le tue modifiche saranno licenziate sotto la stessa licenza del progetto.

---

**Grazie per contribuire a MEC Previsioni! 🚀**
