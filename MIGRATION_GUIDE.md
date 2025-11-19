# Guida Migrazione Database - Schema Completo 3 Pipeline

## 📋 Indice
1. [Panoramica](#panoramica)
2. [Pre-requisiti](#pre-requisiti)
3. [Step-by-Step](#step-by-step)
4. [Verifiche Post-Migrazione](#verifiche-post-migrazione)
5. [Rollback](#rollback)

---

## 📊 Panoramica

Questa migrazione crea lo schema completo per gestire le **3 pipeline** del sistema MEC Previsioni:

### **Pipeline Ordini** (PDF)
```
file_ordini (PDF uploads)
    ├── controparti (seller/buyer)
    ├── modelli (prodotti ordinati)
    └── ordini (dettaglio righe)
```

### **Pipeline Anagrafiche** (Excel)
```
file_anagrafiche (Excel uploads)
    ├── modelli (prodotti)
    ├── componenti (parti di ricambio)
    └── modelli_componenti (BOM - Bill of Materials)
```

### **Pipeline Rotture** (Excel)
```
file_rotture (Excel uploads)
    ├── modelli (prodotti)
    ├── componenti (parti)
    ├── utenti_rotture (clienti finali)
    ├── rivenditori
    ├── rotture (eventi di guasto)
    └── rotture_componenti (parti sostituite)
```

### **Tracciamento**
```
trace_elab (livello file)
    └── trace_elab_dett (livello record/riga)
```

---

## ✅ Pre-requisiti

### 1. Backup del Database
**IMPORTANTE:** Prima di procedere, crea un backup manuale del database!

```bash
# Se usi SQLite
cp instance/mec_previsioni.db instance/mec_previsioni.db.backup_$(date +%Y%m%d_%H%M%S)

# Se usi PostgreSQL
pg_dump -U your_user -d mec_previsioni > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Verifica Ambiente
```bash
# Attiva virtual environment
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Verifica dipendenze
pip install -r requirements.txt

# Verifica configurazione database
# Lo script usa DevelopmentConfig (SQLite) di default
# Per usare PostgreSQL in produzione, modifica migrate_to_full_schema.py
# cambiando: app = create_app(ProductionConfig)
```

### 3. Verifica File
Assicurati di avere:
- ✓ `models.py` (aggiornato con tutti i nuovi modelli)
- ✓ `migrate_to_full_schema.py` (script di migrazione)
- ✓ `verify_models.py` (script di verifica)

---

## 🚀 Step-by-Step

### STEP 1: Verifica Modelli

Prima di migrare, verifica che i modelli siano corretti:

```bash
python verify_models.py
```

**Output atteso:**
```
==========================================
  VERIFICA MODELLI SQLALCHEMY
==========================================

✓ Tutti i modelli importati correttamente

Modelli definiti:
------------------------------------------
  ✓ User                           → users
  ✓ FileRottura                    → file_rotture
  ✓ FileOrdine                     → file_ordini
  ✓ FileAnagrafica                 → file_anagrafiche
  ✓ Controparte                    → controparti
  ✓ Modello                        → modelli
  ...

✓ TUTTI I MODELLI SONO CORRETTI
```

Se ci sono errori, **NON procedere** e correggi i modelli prima!

### STEP 2: Verifica Relazioni (Opzionale)

```bash
python verify_models.py --relationships
```

Questo mostra le relazioni tra i modelli per capire la struttura.

### STEP 3: Esegui Migrazione (DRY-RUN)

Prima esegui la migrazione in modalità interattiva:

```bash
python migrate_to_full_schema.py
```

Lo script chiederà conferma prima di procedere:
```
⚠ Procedere con la migrazione? [y/N]:
```

Rispondi `N` per annullare e rivedere le operazioni.

### STEP 4: Esegui Migrazione (REALE)

Quando sei sicuro, esegui la migrazione:

```bash
python migrate_to_full_schema.py --yes
```

**Output atteso:**
```
==========================================
  MIGRAZIONE SCHEMA COMPLETO - 3 PIPELINE
==========================================

→ STEP 1: Rinomina Tabelle Esistenti
------------------------------------------
  ✓ Tabella rinominata: ordini_acquisto → file_ordini
  ✓ Tabella rinominata: anagrafiche_file → file_anagrafiche

→ STEP 2: Creazione Nuove Tabelle
------------------------------------------
  ✓ controparti                    creata
  ✓ modelli                        creata
  ✓ componenti                     creata
  ✓ ordini                         creata
  ✓ modelli_componenti             creata
  ✓ utenti_rotture                 creata
  ✓ rivenditori                    creata
  ✓ rotture                        creata
  ✓ rotture_componenti             creata
  ✓ trace_elab                     creata
  ✓ trace_elab_dett                creata

→ STEP 3: Verifica Finale
------------------------------------------
  ✓ users                              OK
  ✓ file_rotture                       OK
  ✓ file_ordini                        OK
  ✓ file_anagrafiche                   OK
  ✓ controparti                        OK
  ✓ modelli                            OK
  ...

==========================================
  REPORT MIGRAZIONE
==========================================

Tabelle create:    11
Tabelle esistenti: 6
Errori:            0

Tabelle totali:    17/17

✓ MIGRAZIONE COMPLETATA CON SUCCESSO!
```

### STEP 5: Visualizza Schema (Opzionale)

Per vedere lo schema completo:

```bash
python migrate_to_full_schema.py --yes --schema
```

---

## 🔍 Verifiche Post-Migrazione

### 1. Avvia l'Applicazione

```bash
python app.py
```

Verifica che:
- ✓ L'app si avvii senza errori
- ✓ Non ci siano errori nei log
- ✓ Le route `/ordini`, `/anagrafiche`, `/rotture` funzionino

### 2. Verifica Database

```bash
# SQLite
sqlite3 instance/mec_previsioni.db ".tables"

# PostgreSQL
psql -U your_user -d mec_previsioni -c "\dt"
```

Dovresti vedere tutte le 17 tabelle.

### 3. Test Upload File

Prova a:
1. Caricare un file ordine (PDF)
2. Caricare un file anagrafica (Excel)
3. Caricare un file rotture (Excel)

**NOTA:** L'elaborazione vera e propria richiede l'implementazione delle funzioni di parsing (Fase 2-4).

---

## ⚠️ Rollback

Se qualcosa va storto durante la migrazione:

### Opzione 1: Ripristina da Backup

```bash
# SQLite
cp instance/mec_previsioni.db.backup_XXXXXXXX instance/mec_previsioni.db

# PostgreSQL
psql -U your_user -d mec_previsioni < backup_XXXXXXXX.sql
```

### Opzione 2: Drop e Ricrea (SOLO IN SVILUPPO!)

```bash
# Cancella database
rm instance/mec_previsioni.db  # SOLO SQLite

# Ricrea da zero
python init_db.py
```

**ATTENZIONE:** Questa opzione cancella TUTTI i dati!

---

## 📝 Note Importanti

### Retrocompatibilità

Lo script mantiene gli **alias** per il codice esistente:
- `OrdineAcquisto` → `FileOrdine`
- `AnagraficaFile` → `FileAnagrafica`

Quindi il codice esistente continuerà a funzionare senza modifiche.

### Tabelle Vecchie

Il sistema di tracciamento vecchio (`trace_elaborazioni`, `trace_elaborazioni_dettaglio`) è **mantenuto** per retrocompatibilità.

Il nuovo sistema (`trace_elab`, `trace_elab_dett`) sarà usato dalle nuove implementazioni.

### Prossimi Passi

Dopo la migrazione:

1. **Fase 2:** Implementare parsing PDF ordini
2. **Fase 3:** Implementare parsing Excel anagrafiche
3. **Fase 4:** Implementare parsing Excel rotture
4. **Fase 5:** Dashboard analytics

---

## 🆘 Troubleshooting

### Errore: "Table already exists"

Se una tabella esiste già, lo script la salta automaticamente.
Se vuoi ricrearla, devi prima droppare la tabella manualmente.

### Errore: "Foreign key constraint fails"

Questo può accadere se ci sono dati esistenti che non rispettano i vincoli.
Pulisci i dati inconsistenti prima della migrazione.

### Errore: "No module named 'models'"

Verifica di essere nella directory corretta:
```bash
cd /path/to/mec-previsioni
python migrate_to_full_schema.py
```

---

## 📚 Riferimenti

- [Schema Database Originale](DATABASE_SCHEMA.md) (se disponibile)
- [Documentazione SQLAlchemy](https://docs.sqlalchemy.org/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)

---

**Autore:** Claude (Anthropic)
**Data:** 2025-01-19
**Versione:** 1.0
