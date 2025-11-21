# Test Suite - MEC Previsioni

Documentazione completa per la test suite del progetto.

---

## 📋 Struttura Test

```
tests/
├── conftest.py                  # Fixtures comuni pytest
├── __init__.py                  # Package marker
│
├── unit/                        # Test unitari
│   ├── __init__.py
│   ├── test_models.py          # Test modelli SQLAlchemy
│   ├── test_utils.py           # Test utility e decoratori
│   └── test_functions.py       # Test funzioni business (future)
│
└── integration/                 # Test di integrazione
    ├── __init__.py
    ├── test_auth.py            # Test autenticazione
    └── test_routes.py          # Test routes principali
```

---

## 🚀 Esecuzione Test

### Test Completi

```bash
# Tutti i test
pytest

# Con output verboso
pytest -v

# Con coverage
pytest --cov

# Coverage con report HTML
pytest --cov --cov-report=html
```

### Test per Categoria

```bash
# Solo unit test
pytest tests/unit/

# Solo integration test
pytest tests/integration/

# Test specifico
pytest tests/unit/test_models.py

# Funzione specifica
pytest tests/unit/test_models.py::test_user_creation
```

### Test per Marker

```bash
# Solo test unitari (con marker)
pytest -m unit

# Solo test di integrazione
pytest -m integration

# Escludi test lenti
pytest -m "not slow"
```

### Opzioni Utili

```bash
# Stop al primo fallimento
pytest -x

# Mostra print statements
pytest -s

# Re-run solo test falliti
pytest --lf

# Parallel execution (richiede pytest-xdist)
pytest -n auto
```

---

## 📊 Coverage

### Generare Report

```bash
# Report terminale
pytest --cov --cov-report=term-missing

# Report HTML
pytest --cov --cov-report=html

# Report XML (per CI/CD)
pytest --cov --cov-report=xml
```

### Visualizzare Report

```bash
# Apri report HTML
open htmlcov/index.html        # macOS
xdg-open htmlcov/index.html    # Linux
start htmlcov/index.html       # Windows

# Oppure usa Makefile
make coverage
```

### Target Coverage

- **Nuovo codice**: >= 80%
- **Progetto totale**: >= 70%

---

## 🧪 Fixtures Disponibili

Definite in `conftest.py`:

### App & Client

- **`app`**: Flask app configurata per testing
- **`client`**: Test client Flask
- **`runner`**: CLI runner Flask

### Database

- **`db`**: Database SQLAlchemy (in-memory SQLite)

### Autenticazione

- **`auth`**: Helper per login/logout
- **`authenticated_client`**: Client già loggato come admin
- **`user_client`**: Client loggato come user normale

### Esempio Utilizzo

```python
def test_example(authenticated_client, db):
    """Test con client autenticato e database."""
    # Client già loggato come admin
    response = authenticated_client.get('/users/')
    assert response.status_code == 200

    # Accesso al database
    from models import User
    users = User.query.all()
    assert len(users) > 0
```

---

## ✍️ Scrivere Nuovi Test

### Test Unitario

```python
import pytest
from models import User

@pytest.mark.unit
def test_user_password_hashing(db):
    """Test password hashing."""
    user = User(username='test', email='test@test.com', created_by=0)
    password = 'secret123'
    user.set_password(password)

    # Verifica hashing
    assert user.password_hash != password
    assert user.check_password(password) is True
    assert user.check_password('wrong') is False
```

### Test di Integrazione

```python
import pytest

@pytest.mark.integration
def test_login_success(client, auth):
    """Test login con credenziali corrette."""
    response = auth.login(username='admin', password='admin123')
    assert response.status_code == 200
    assert b'logout' in response.data.lower()
```

### Test con Database

```python
@pytest.mark.unit
def test_create_file_anagrafica(db):
    """Test creazione FileAnagrafica."""
    from models import FileAnagrafica

    file_ana = FileAnagrafica(
        anno=2024,
        marca='TEST',
        filename='test.xlsx',
        filepath='/path/test.xlsx',
        created_by=1
    )
    db.session.add(file_ana)
    db.session.commit()

    assert file_ana.id is not None
    assert file_ana.anno == 2024
```

---

## 🏷️ Markers

Usa markers per categorizzare test:

```python
@pytest.mark.unit           # Test unitario
@pytest.mark.integration    # Test di integrazione
@pytest.mark.slow           # Test lento
```

Configurati in `conftest.py` e `pyproject.toml`.

---

## 🔧 Configurazione

### pytest.ini (o pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["-v", "--cov", "--cov-report=term-missing"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

---

## 📝 Best Practices

### Naming

- File: `test_*.py` o `*_test.py`
- Funzioni: `test_*`
- Classes: `Test*`

### Organizzazione

- **Unit tests**: Test di singole unità (funzioni, classi) in isolamento
- **Integration tests**: Test di interazioni tra componenti
- Un file di test per ogni modulo/route

### Assertions

```python
# Buono - Messaggio chiaro
assert user.is_admin() is True, "Admin user should return True"

# Buono - pytest assertion rewriting
assert response.status_code == 200

# Evita - Troppo generico
assert response
```

### Setup/Teardown

Usa fixtures invece di setup/teardown:

```python
@pytest.fixture
def sample_user(db):
    """Crea un utente di esempio."""
    user = User(username='sample', email='sample@test.com', created_by=0)
    user.set_password('pass')
    db.session.add(user)
    db.session.commit()
    return user

def test_with_sample_user(sample_user):
    """Test che usa il sample user."""
    assert sample_user.username == 'sample'
```

---

## 🐛 Debugging

### Test Falliti

```bash
# Verbose output
pytest -vv

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Enter debugger on failure
pytest --pdb
```

### Debugging Specifico

```python
def test_example():
    """Test con debugging."""
    import pdb; pdb.set_trace()  # Breakpoint
    # ...oppure...
    breakpoint()  # Python 3.7+
```

---

## 🔄 CI/CD

I test vengono eseguiti automaticamente su GitHub Actions:

- Trigger: Push/PR su main/develop
- Matrix: Python 3.9, 3.10, 3.11
- Steps:
  1. Setup Python
  2. Install dependencies
  3. Run pytest
  4. Upload coverage

Vedi `.github/workflows/ci.yml` per configurazione completa.

---

## 📚 Risorse

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-flask Documentation](https://pytest-flask.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Flask Testing Guide](https://flask.palletsprojects.com/en/latest/testing/)

---

## ❓ FAQ

### Come testo codice che richiede file esterni?

Usa mocking:

```python
from unittest.mock import patch, mock_open

@patch('builtins.open', mock_open(read_data='test data'))
def test_file_reading():
    # Test funzione che legge file
    ...
```

### Come testo database queries complesse?

Crea fixture con dati di test:

```python
@pytest.fixture
def populated_db(db):
    """Database con dati di test."""
    # Popola con dati
    ...
    yield db
    # Cleanup automatico
```

### Come skippo test che richiedono risorse esterne?

```python
@pytest.mark.skipif(not os.path.exists('/data'), reason="Data directory not found")
def test_with_external_data():
    ...
```

---

**Happy Testing! 🧪**
