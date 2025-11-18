# Migrazione: Campi User Tracking (created_by/updated_by)

**Data**: 2025-11-17
**Obiettivo**: Aggiungere campi `created_by` e `updated_by` per tracciare chi crea/modifica i record

## 📋 Sommario

Questa migrazione aggiunge i campi di tracking utente alle tabelle esistenti:

| Tabella | Campi Aggiunti | Foreign Key |
|---------|----------------|-------------|
| `anagrafiche_file` | `created_by`, `updated_by` | → `users.id_user` |
| `rotture` | `created_by`, `updated_by` | → `users.id_user` |
| `ordini_acquisto` | `created_by`, `updated_by` | → `users.id_user` |

## 🎯 Perché Questi Campi?

I campi `created_by` e `updated_by` permettono di:

- ✅ Tracciare **chi** ha creato un record
- ✅ Tracciare **chi** ha modificato un record l'ultima volta
- ✅ Implementare **audit trail** per compliance
- ✅ Supportare **controlli di accesso** basati su proprietà
- ✅ Generare **statistiche per utente** (es: "file caricati da Mario Rossi")
- ✅ Implementare **notifiche** personalizzate

## ⚠️ Caratteristiche Migrazione

- **SAFE**: Aggiunge solo nuove colonne nullable
- **NON DISTRUTTIVA**: Non modifica né elimina dati esistenti
- **BACKWARD COMPATIBLE**: Record esistenti avranno NULL nei nuovi campi
- **OPZIONALE**: È possibile popolare i campi NULL successivamente

## 🚀 Come Eseguire la Migrazione

### Opzione 1: Script SQL PostgreSQL (Raccomandato)

```bash
# Esegui lo script SQL
psql -U username -d mec_previsioni -f migrations_sql/add_user_tracking_columns.sql
```

### Opzione 2: Script Python

```bash
# Esegui migrazione senza conferma
python migrate_add_user_tracking.py --yes

# Esegui migrazione E popola record esistenti con admin (user_id=1)
python migrate_add_user_tracking.py --yes --populate=1

# Solo verifica (non modifica nulla)
python migrate_add_user_tracking.py --verify-only

# Aiuto
python migrate_add_user_tracking.py --help
```

## 🔍 Verifica Migrazione

Dopo l'esecuzione, verifica che i campi siano stati aggiunti:

```sql
-- Verifica struttura colonne
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('anagrafiche_file', 'rotture', 'ordini_acquisto')
AND column_name IN ('created_by', 'updated_by')
ORDER BY table_name, column_name;

-- Risultato atteso:
-- anagrafiche_file.created_by → integer, YES (nullable)
-- anagrafiche_file.updated_by → integer, YES (nullable)
-- rotture.created_by → integer, YES (nullable)
-- rotture.updated_by → integer, YES (nullable)
-- ordini_acquisto.created_by → integer, YES (nullable)
-- ordini_acquisto.updated_by → integer, YES (nullable)

-- Verifica foreign keys
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('anagrafiche_file', 'rotture', 'ordini_acquisto')
AND kcu.column_name IN ('created_by', 'updated_by');
```

## 📝 Popolamento Campi per Record Esistenti

I record esistenti avranno `created_by` e `updated_by` = NULL. Puoi popolarli:

### Metodo 1: Assegna tutti all'admin (user_id=1)

```sql
UPDATE anagrafiche_file
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;

UPDATE rotture
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;

UPDATE ordini_acquisto
SET created_by = 1, updated_by = 1
WHERE created_by IS NULL;
```

### Metodo 2: Via script Python

```bash
# Popola con admin (user_id=1)
python migrate_add_user_tracking.py --yes --populate=1

# Oppure con un altro utente
python migrate_add_user_tracking.py --yes --populate=5
```

### Metodo 3: Lascia NULL (raccomandato per audit)

Lasciare NULL indica chiaramente che il record è stato creato **prima** dell'implementazione del tracking. Utile per:
- Distinguere record legacy da nuovi
- Mantenere integrità storica
- Audit trail trasparente

## 🧪 Esempi di Query

### Query 1: File caricati per utente

```sql
SELECT
    u.username,
    COUNT(DISTINCT af.id_file_anagrafiche) AS anagrafiche,
    COUNT(DISTINCT r.id_file_rotture) AS rotture,
    COUNT(DISTINCT oa.id_file_ordini_acquisto) AS ordini
FROM users u
LEFT JOIN anagrafiche_file af ON u.id_user = af.created_by
LEFT JOIN rotture r ON u.id_user = r.created_by
LEFT JOIN ordini_acquisto oa ON u.id_user = oa.created_by
GROUP BY u.id_user, u.username
ORDER BY anagrafiche + rotture + ordini DESC;
```

### Query 2: Dettagli file con autore

```sql
SELECT
    af.id_file_anagrafiche,
    af.filename,
    af.marca,
    u_created.username AS creato_da,
    af.created_at,
    u_updated.username AS modificato_da,
    af.updated_at
FROM anagrafiche_file af
LEFT JOIN users u_created ON af.created_by = u_created.id_user
LEFT JOIN users u_updated ON af.updated_by = u_updated.id_user
ORDER BY af.created_at DESC
LIMIT 10;
```

### Query 3: File orfani (senza autore)

```sql
-- Anagrafiche senza autore
SELECT COUNT(*) AS num_orfani
FROM anagrafiche_file
WHERE created_by IS NULL;

-- Rotture senza autore
SELECT COUNT(*) AS num_orfani
FROM rotture
WHERE created_by IS NULL;

-- Ordini senza autore
SELECT COUNT(*) AS num_orfani
FROM ordini_acquisto
WHERE created_by IS NULL;
```

### Query 4: Attività recente per utente

```sql
SELECT
    u.username,
    'anagrafica' AS tipo,
    af.filename,
    af.created_at AS data
FROM anagrafiche_file af
JOIN users u ON af.created_by = u.id_user
WHERE af.created_at >= CURRENT_DATE - INTERVAL '7 days'

UNION ALL

SELECT
    u.username,
    'rottura' AS tipo,
    r.filename,
    r.created_at AS data
FROM rotture r
JOIN users u ON r.created_by = u.id_user
WHERE r.created_at >= CURRENT_DATE - INTERVAL '7 days'

UNION ALL

SELECT
    u.username,
    'ordine' AS tipo,
    oa.filename,
    oa.created_at AS data
FROM ordini_acquisto oa
JOIN users u ON oa.created_by = u.id_user
WHERE oa.created_at >= CURRENT_DATE - INTERVAL '7 days'

ORDER BY data DESC;
```

## 🔄 Integrazione con Applicazione Flask

Dopo la migrazione, aggiorna il codice Flask per popolare automaticamente questi campi:

### routes/anagrafiche.py (esempio)

```python
from flask_login import current_user

@anagrafiche_bp.route('/create', methods=['POST'])
@login_required
def create():
    # ... codice esistente ...

    anagrafica = AnagraficaFile(
        filename=filename,
        filepath=filepath,
        marca=marca,
        anno=anno,
        created_by=current_user.id,  # ← Aggiungi questo
        updated_by=current_user.id   # ← Aggiungi questo
    )

    db.session.add(anagrafica)
    db.session.commit()
```

### routes/anagrafiche.py - Edit (esempio)

```python
@anagrafiche_bp.route('/<int:id>/edit', methods=['POST'])
@login_required
def edit(id):
    anagrafica = AnagraficaFile.query.get_or_404(id)

    # ... aggiorna campi ...

    anagrafica.updated_by = current_user.id  # ← Aggiungi questo
    anagrafica.updated_at = datetime.utcnow()

    db.session.commit()
```

## 📊 Struttura Completa Tabelle

### anagrafiche_file

```sql
CREATE TABLE anagrafiche_file (
    id_file_anagrafiche INTEGER PRIMARY KEY,
    anno INTEGER NOT NULL,
    marca VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    data_acquisizione DATE NOT NULL,
    data_elaborazione DATE,
    esito VARCHAR(50),
    note TEXT,
    created_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),  -- ← NUOVO
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)   -- ← NUOVO
);
```

### rotture

```sql
CREATE TABLE rotture (
    id_file_rotture INTEGER PRIMARY KEY,
    anno INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    data_acquisizione DATE NOT NULL,
    data_elaborazione TIMESTAMP,
    esito VARCHAR(50),
    note TEXT,
    created_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),  -- ← NUOVO
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)   -- ← NUOVO
);
```

### ordini_acquisto

```sql
CREATE TABLE ordini_acquisto (
    id_file_ordini_acquisto INTEGER PRIMARY KEY,
    anno INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    data_acquisizione DATE NOT NULL,
    data_elaborazione TIMESTAMP,
    esito VARCHAR(50),
    note TEXT,
    created_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id_user),  -- ← NUOVO
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES users(id_user)   -- ← NUOVO
);
```

## 🔗 File Correlati

- **models.py**: Modelli SQLAlchemy aggiornati con relationships
- **migrate_add_user_tracking.py**: Script Python di migrazione
- **add_user_tracking_columns.sql**: Script SQL diretto

## ✅ Checklist Post-Migrazione

- [ ] Campi `created_by` e `updated_by` aggiunti alle 3 tabelle
- [ ] Foreign key constraints creati verso `users.id_user`
- [ ] Indici creati per performance
- [ ] Verifica query di test funzionanti
- [ ] (Opzionale) Record esistenti popolati
- [ ] Codice Flask aggiornato per usare `current_user.id`
- [ ] Test creazione/modifica record con nuovi campi

## 📞 Note Importanti

1. **NULL vs Popolamento**: È preferibile lasciare NULL per record legacy per mantenere trasparenza nell'audit trail
2. **Performance**: Gli indici sono già creati, le query JOIN con users saranno efficienti
3. **Retrocompatibilità**: Il codice esistente continuerà a funzionare (i campi sono nullable)
4. **Cascading**: Se un utente viene eliminato, i campi diventeranno NULL (non ON DELETE CASCADE)

## 🎉 Conclusione

Dopo questa migrazione, avrai un sistema completo di tracking utenti per audit, compliance e statistiche!

**Buona migrazione! 🚀**
