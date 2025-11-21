# 🤝 Contributing to MEC Previsioni

Grazie per il tuo interesse nel contribuire a MEC Previsioni! Questo documento fornisce linee guida per contribuire al progetto.

---

## 📋 Tabella dei Contenuti

- [Code of Conduct](#code-of-conduct)
- [Come Posso Contribuire?](#come-posso-contribuire)
- [Setup Sviluppo](#setup-sviluppo)
- [Workflow di Sviluppo](#workflow-di-sviluppo)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)

---

## 📜 Code of Conduct

Questo progetto segue un Code of Conduct standard. Ci aspettiamo che tutti i contributori:

- Siano rispettosi e professionali
- Accettino feedback costruttivo
- Lavorino in modo collaborativo
- Mantengano un ambiente inclusivo

---

## 🚀 Come Posso Contribuire?

### Reportare Bug

Prima di aprire una issue:
1. **Cerca** se la issue esiste già
2. **Verifica** di avere l'ultima versione
3. **Raccogli** informazioni:
   - Versione Python
   - Sistema operativo
   - Passi per riprodurre
   - Comportamento atteso vs. attuale
   - Log di errore completi

**Template Issue:**
```markdown
## Descrizione Bug
[Descrizione chiara e concisa]

## Passi per Riprodurre
1. Vai a '...'
2. Clicca su '...'
3. Vedi errore

## Comportamento Atteso
[Cosa dovrebbe succedere]

## Comportamento Attuale
[Cosa succede invece]

## Ambiente
- Python: 3.9.x
- OS: Ubuntu 22.04
- Browser: Chrome 120

## Log/Screenshots
[Se applicabile]
```

### Suggerire Feature

Per suggerire nuove funzionalità:
1. **Verifica** che non sia già stata proposta
2. **Descrivi** il problema che risolve
3. **Spiega** il comportamento desiderato
4. **Fornisci** esempi d'uso

### Contribuire con Codice

Leggi le sezioni seguenti per il workflow completo.

---

## 🛠️ Setup Sviluppo

### 1. Fork & Clone

```bash
# Fork su GitHub, poi:
git clone https://github.com/YOUR-USERNAME/mec-previsioni.git
cd mec-previsioni
```

### 2. Setup Ambiente

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Dipendenze
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install
```

### 3. Configurazione

```bash
cp .env.example .env
# Modifica .env con SECRET_KEY
```

### 4. Verifica Setup

```bash
# Test
pytest

# Linting
make lint

# Formattazione
make format
```

---

## 🔄 Workflow di Sviluppo

### 1. Crea Branch

```bash
# Aggiorna main
git checkout main
git pull upstream main

# Crea feature branch
git checkout -b feature/nome-descrittivo
# o
git checkout -b fix/nome-bug
```

**Naming Convention:**
- `feature/` - Nuove funzionalità
- `fix/` - Bug fix
- `docs/` - Solo documentazione
- `refactor/` - Refactoring
- `test/` - Aggiungere/migliorare test
- `chore/` - Manutenzione

### 2. Sviluppa

```bash
# Scrivi codice
# ...

# Aggiungi test
# ...

# Testa localmente
make test
```

### 3. Commit

```bash
# Stage modifiche
git add .

# Commit (pre-commit hooks si attivano automaticamente)
git commit -m "feat: descrizione modifiche"
```

### 4. Push

```bash
git push origin feature/nome-descrittivo
```

### 5. Pull Request

Apri PR su GitHub con template.

---

## 📏 Coding Standards

### Python Style

Seguiamo **PEP 8** con alcune eccezioni:

- **Line Length**: 88 caratteri (Black default)
- **Indentation**: 4 spazi (no tabs)
- **Quotes**: Preferire singole `'` per stringhe, doppie `"` per docstrings
- **Imports**: Ordinati con isort (standard, third-party, local)

### Formattazione Automatica

```bash
# Black (formatter)
black .

# isort (import sorting)
isort .

# Oppure entrambi
make format
```

### Linting

Tutti i file devono passare:

```bash
# flake8
flake8 .

# pylint
pylint app.py routes/ utils/

# bandit (security)
bandit -r . -ll

# Oppure tutto
make lint
```

### Type Hints (Opzionale ma Raccomandato)

```python
def calculate_survival(
    time_points: List[int],
    events: np.ndarray,
    confidence: float = 0.95
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calcola curva di sopravvivenza.

    Args:
        time_points: Punti temporali
        events: Eventi osservati (0=censura, 1=evento)
        confidence: Livello confidenza

    Returns:
        Tuple di (survival_function, confidence_bands)
    """
    ...
```

### Docstrings

Usa **Google Style**:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
    """
    ...
```

---

## 📝 Commit Guidelines

### Conventional Commits

Seguiamo [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: Nuova feature
- `fix`: Bug fix
- `docs`: Solo documentazione
- `style`: Formattazione (no logic changes)
- `refactor`: Refactoring
- `perf`: Performance improvement
- `test`: Test
- `chore`: Build, deps, etc.
- `ci`: CI/CD changes

### Esempi

```bash
# Feature
git commit -m "feat(previsioni): add Weibull confidence bands"

# Bug fix
git commit -m "fix(auth): resolve login redirect loop"

# Docs
git commit -m "docs: update README installation steps"

# Breaking change
git commit -m "feat(api)!: change response format

BREAKING CHANGE: API now returns JSON instead of XML"
```

### Regole

- Usa imperativo presente ("add" non "added")
- Prima riga max 72 caratteri
- Body opzionale, wrapping a 72 caratteri
- Footer per breaking changes o issue references

---

## 🔀 Pull Request Process

### 1. Prima di Aprire PR

Verifica che:
- ✅ Tutti i test passano (`make test`)
- ✅ Codice formattato (`make format`)
- ✅ Linting passa (`make lint`)
- ✅ Documentazione aggiornata
- ✅ Changelog aggiornato (se applicabile)

### 2. Template PR

```markdown
## Descrizione
[Descrizione chiara delle modifiche]

## Tipo di Change
- [ ] Bug fix (non-breaking change che risolve issue)
- [ ] New feature (non-breaking change che aggiunge funzionalità)
- [ ] Breaking change (fix o feature che rompe compatibilità)
- [ ] Documentazione

## Come È Stato Testato?
[Descrivi test eseguiti]

## Checklist
- [ ] Codice segue coding standards
- [ ] Self-review del codice
- [ ] Commenti aggiunti dove necessario
- [ ] Documentazione aggiornata
- [ ] Nessun warning generato
- [ ] Test aggiunti/aggiornati
- [ ] Tutti i test passano

## Issue Correlate
Fixes #123
Closes #456
```

### 3. Review Process

- Almeno **1 approvazione** richiesta
- **CI deve passare** (GitHub Actions)
- **Nessun conflitto** con main
- **Commenti risolti**

### 4. Merge

Dopo approvazione:
- **Squash and merge** (preferito per feature)
- **Rebase and merge** (per fix piccoli)
- **Merge commit** (solo per merge tra branch principali)

---

## 🧪 Testing Guidelines

### Scrivere Test

Tutti i nuovi file dovrebbero avere test corrispondenti:

```
app/
  routes/
    previsioni.py
tests/
  unit/
    test_previsioni.py
  integration/
    test_previsioni_integration.py
```

### Test Unitari

```python
# tests/unit/test_functions.py
import pytest
from functions import calculate_weibull

def test_calculate_weibull_basic():
    """Test basic Weibull calculation."""
    result = calculate_weibull([1, 2, 3], [0, 1, 0])
    assert result is not None
    assert len(result) > 0

def test_calculate_weibull_empty_input():
    """Test Weibull with empty input."""
    with pytest.raises(ValueError):
        calculate_weibull([], [])
```

### Test di Integrazione

```python
# tests/integration/test_routes.py
def test_login_success(client):
    """Test successful login."""
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'test123'
    })
    assert response.status_code == 302
```

### Coverage Target

- **Nuovo codice**: >= 80%
- **Progetto totale**: >= 70%

```bash
# Verifica coverage
pytest --cov --cov-report=term-missing
```

---

## 📚 Risorse

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Black Documentation](https://black.readthedocs.io/)

---

## ❓ Domande?

Se hai domande:
- Apri una Discussion su GitHub
- Chiedi nel canale Slack del team
- Email: dev@yourcompany.com

---

**Grazie per aver contribuito a MEC Previsioni! 🎉**
