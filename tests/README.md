# Test Suite MEC Previsioni

Test suite completa per le pipeline di gestione file (Ordini e Anagrafiche).

## Struttura Test

```
tests/
├── __init__.py                      # Package test
├── conftest.py                      # Fixtures pytest comuni
├── test_pipeline_ordini.py          # Test pipeline ordini PDF
├── test_pipeline_anagrafiche.py     # Test pipeline anagrafiche Excel
└── README.md                        # Questo file
```

## Setup

### Installazione Dipendenze Test

```bash
pip install pytest pytest-cov pytest-flask
```

### Esecuzione Test

**Tutti i test:**
```bash
pytest
```

**Test specifici:**
```bash
# Solo pipeline ordini
pytest tests/test_pipeline_ordini.py

# Solo pipeline anagrafiche
pytest tests/test_pipeline_anagrafiche.py

# Test specifico
pytest tests/test_pipeline_anagrafiche.py::TestAnagraficheElaborazione::test_elabora_anagrafica_success
```

**Con coverage:**
```bash
pytest --cov=routes --cov=models --cov-report=html --cov-report=term-missing
```

**Verboso:**
```bash
pytest -v -s
```

## Test Coverage

### Pipeline Ordini (`test_pipeline_ordini.py`)

- **TestOrdiniUpload**: Test caricamento PDF
  - ✅ Upload file PDF con successo
  - ✅ Upload file con estensione non valida
  - ✅ Upload senza autenticazione

- **TestOrdiniElaborazione**: Test elaborazione ordini
  - ✅ Elaborazione con successo
  - ✅ Elaborazione con file mancante

- **TestOrdiniDelete**: Test cancellazione ordini
  - ✅ Cancellazione con successo
  - ✅ Cancellazione con file già cancellato
  - ✅ Cancellazione senza permessi admin

- **TestOrdiniSync**: Test sincronizzazione filesystem
  - ✅ Sincronizzazione cartelle INPUT/OUTPUT
  - ✅ Rimozione record orfani dal DB

- **TestOrdiniDownload**: Test download file
  - ✅ Download file PDF
  - ✅ Download file mancante

- **TestOrdiniList**: Test lista e filtri
  - ✅ Lista ordini con filtri
  - ✅ Paginazione

### Pipeline Anagrafiche (`test_pipeline_anagrafiche.py`)

- **TestAnagraficheUpload**: Test caricamento Excel
  - ✅ Upload file Excel con successo
  - ✅ Upload file con estensione non valida

- **TestAnagraficheElaborazione**: Test elaborazione e CRUD DB
  - ✅ Elaborazione con inserimento dati (modelli, componenti, modelli_componenti)
  - ✅ UPSERT modello esistente
  - ✅ UPSERT componente esistente
  - ✅ DELETE preventivo modelli_componenti
  - ✅ Errore con colonne mancanti
  - ✅ Rollback automatico su errore

- **TestAnagraficheDelete**: Test cancellazione CASCADE
  - ✅ Cancellazione CASCADE modelli_componenti (NON modelli/componenti)
  - ✅ Rollback su errore

- **TestAnagraficheHelperFunctions**: Test funzioni utility
  - ✅ normalizza_codice()
  - ✅ safe_decimal()
  - ✅ safe_int()
  - ✅ safe_str()

- **TestAnagraficheSync**: Test sincronizzazione
  - ✅ Sincronizzazione filesystem con DB

- **TestAnagrafichePreview**: Test anteprima Excel
  - ✅ Preview HTML file Excel
  - ✅ Preview con file mancante

- **TestAnagraficheMarche**: Test gestione marche
  - ✅ Creazione nuova marca
  - ✅ Creazione marca duplicata

## Fixtures Disponibili (conftest.py)

### App e Client
- `app`: Applicazione Flask configurata per test
- `client`: Client HTTP per test
- `authenticated_client`: Client autenticato come admin

### Database
- `db_session`: Sessione DB con rollback automatico

### Utenti
- `admin_user`: Utente admin di test
- `normal_user`: Utente normale di test

### File di Test
- `sample_pdf_file`: File PDF fake per test ordini
- `sample_excel_file`: File Excel con dati anagrafica validi

### Record Database
- `sample_ordine_acquisto`: Record ordine di test nel DB
- `sample_anagrafica_file`: Record anagrafica di test nel DB
- `sample_modello`: Modello di test nel DB
- `sample_componente`: Componente di test nel DB

## Note Importanti

### Cancellazione CASCADE
I test verificano che:
- ✅ Cancellando un file anagrafica, vengono cancellati i record `modelli_componenti`
- ❌ NON vengono mai cancellati i record `modelli` e `componenti` (tabelle master condivise)

### UPSERT Logic
I test verificano che:
- Se un modello/componente esiste → UPDATE
- Se un modello/componente NON esiste → INSERT
- Nessuna duplicazione di record

### Rollback Automatico
Tutti gli errori durante l'elaborazione triggherano un rollback automatico del database:
- File non valido → rollback
- Colonne mancanti → rollback
- Errori SQL → rollback

### Gestione Errori
I test coprono scenari di errore comuni:
- File mancanti sul filesystem
- File Excel corrotti o non validi
- Colonne mancanti nel file Excel
- Errori di permessi
- Record orfani nel database

## Esecuzione CI/CD

### GitHub Actions (esempio)

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-flask

    - name: Run tests
      run: pytest --cov=routes --cov=models --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Troubleshooting

### Test Falliscono con Errori di Import
```bash
# Aggiungi il path del progetto a PYTHONPATH
export PYTHONPATH=/home/user/mec-previsioni:$PYTHONPATH
pytest
```

### Errori di Permessi su Directory
```bash
# I test creano directory temporanee, assicurati di avere i permessi
chmod -R 755 /tmp
```

### Database Locked
```bash
# Se usi SQLite e ottieni errori "database locked":
# - Chiudi tutte le connessioni al DB
# - Riavvia i test
# - Considera l'uso di PostgreSQL per test paralleli
```

## Metriche Target

| Metrica | Target | Attuale |
|---------|--------|---------|
| **Coverage Totale** | >80% | TBD |
| **Coverage routes/** | >85% | TBD |
| **Coverage models.py** | >90% | TBD |
| **Test Success Rate** | 100% | TBD |

## Prossimi Test da Implementare

- [ ] Test integrazione con preprocessing_PO (estrazione PDF)
- [ ] Test pipeline rotture
- [ ] Test previsioni Weibull
- [ ] Test performance (caricamento 1000+ record)
- [ ] Test concurrency (più utenti simultanei)
- [ ] Test sicurezza (SQL injection, XSS, CSRF)
