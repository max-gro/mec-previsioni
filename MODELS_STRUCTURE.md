# Struttura Modelli Database - MEC Previsioni

## 📊 Architettura

L'applicazione gestisce **3 pipeline** principali per l'analisi predittiva della manutenzione:

```
                    ┌──────────────────┐
                    │      MODELLI     │ ◄── Tabella Centrale
                    │  (cod_modello)   │
                    └──────────────────┘
                            ▲
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐   ┌──────▼───────┐
│   PIPELINE     │  │   PIPELINE   │   │   PIPELINE   │
│    ORDINI      │  │ ANAGRAFICHE  │   │   ROTTURE    │
│   (PDF)        │  │   (Excel)    │   │   (Excel)    │
└────────────────┘  └──────────────┘   └──────────────┘
```

---

## 📁 Tabelle File (Upload e Stato)

### `users`
Autenticazione utenti del sistema
- **PK:** `id_user`
- **Campi:** username, email, password_hash, role ('Utente', 'Amministratore')

### `file_ordini`
File PDF ordini di acquisto
- **PK:** `id_file_ordine`
- **FK:** `cod_seller` → controparti, `cod_buyer` → controparti
- **Campi:** anno, marca, filename, filepath, data_ordine, oggetto_ordine, esito

### `file_anagrafiche`
File Excel anagrafiche componenti
- **PK:** `id_file_anagrafiche`
- **Campi:** anno, marca, filename, filepath, esito

### `file_rotture`
File Excel rotture (guasti)
- **PK:** `id_file_rotture`
- **Campi:** anno, filename, filepath, esito

---

## 🏢 Entità Comuni

### `controparti`
Fornitori e clienti negli ordini
- **PK:** `cod_controparte` (VARCHAR)
- **Campi:** controparte (nome completo)
- **Usato in:** Pipeline Ordini (seller/buyer)

### `modelli`
**TABELLA CENTRALE** - Prodotti/Modelli
- **PK:** `cod_modello` (VARCHAR)
- **UK:** `cod_modello_norm` (normalizzato per matching)
- **Campi:** nome_modello, marca, divisione, produttore, famiglia, tipo, updated_from ('ORD'|'ANA'|'ROT')
- **Usato in:** Tutte e 3 le pipeline

### `componenti`
Parti di ricambio/componenti
- **PK:** `cod_componente` (VARCHAR)
- **UK:** `cod_componente_norm`
- **Campi:** part_no, part_name_{en,cn,it}, cod_ean, prezzi (USD/EUR), stat
- **Usato in:** Pipeline Anagrafiche e Rotture

---

## 📦 Pipeline ORDINI (PDF)

### Flusso:
```
file_ordini (PDF upload)
    ↓
[Parsing PDF]
    ↓
ordini (dettaglio righe) ─→ modelli
```

### `ordini`
Dettaglio righe ordini (componenti ordinati)
- **PK:** `ordine_modello` (VARCHAR = cod_ordine|cod_modello)
- **FK:** `id_file_ordine` → file_ordini, `cod_modello` → modelli
- **UK:** (`cod_ordine`, `cod_modello`)
- **Campi:** brand, item, ean, prezzo_eur, qta, importo_eur

**Esempio:**
```sql
ordine_modello = "PO2024001|MOD12345"
cod_ordine = "PO2024001"
cod_modello = "MOD12345"
qta = 100
prezzo_eur = 150.00
```

---

## 🧩 Pipeline ANAGRAFICHE (Excel)

### Flusso:
```
file_anagrafiche (Excel upload)
    ↓
[Parsing Excel BOM]
    ↓
modelli_componenti ─┬─→ modelli
                    └─→ componenti
```

### `modelli_componenti`
BOM (Bill of Materials) - Distinta base
- **PK:** `cod_modello_componente` (VARCHAR = cod_modello|cod_componente)
- **FK:** `id_file_anagrafiche`, `cod_modello` → modelli, `cod_componente` → componenti
- **Campi:** qta (quantità per modello)

**Esempio:**
```sql
-- Un frigorifero "FRIDGE2000" contiene 2 compressori "COMP001"
cod_modello_componente = "FRIDGE2000|COMP001"
cod_modello = "FRIDGE2000"
cod_componente = "COMP001"
qta = 2
```

**Query utile:**
```sql
-- Trova tutti i componenti di un modello
SELECT c.*
FROM componenti c
JOIN modelli_componenti mc ON c.cod_componente = mc.cod_componente
WHERE mc.cod_modello = 'FRIDGE2000';
```

---

## 🔧 Pipeline ROTTURE (Excel)

### Flusso:
```
file_rotture (Excel upload)
    ↓
[Parsing Excel rotture]
    ↓
rotture ─┬─→ modelli
         ├─→ utenti_rotture (cliente finale)
         ├─→ rivenditori
         └─→ rotture_componenti ─→ componenti
```

### `utenti_rotture`
Clienti finali che hanno avuto guasti
- **PK:** `cod_utente_rottura`
- **Campi:** pv_utente_rottura (provincia), comune_utente_rottura

### `rivenditori`
Negozi/rivenditori che gestiscono le riparazioni
- **PK:** `cod_rivenditore`
- **Campi:** pv_rivenditore (provincia)

### `rotture`
Eventi di guasto/rottura
- **PK:** `cod_rottura` (VARCHAR = id_file_rotture|prot)
- **FK:** `id_file_rotture`, `cod_modello` → modelli, `cod_rivenditore`, `cod_utente` → utenti_rotture
- **Campi:** prot, CAT, flag_consumer, data_competenza, cod_matricola, data_acquisto, data_apertura, difetto, problema_segnalato, riparazione, gg_vita_prodotto

**Esempio:**
```sql
cod_rottura = "123|ROT2024001"
id_file_rotture = 123
prot = "ROT2024001"
cod_modello = "FRIDGE2000"
data_acquisto = "2022-01-15"
data_apertura = "2024-11-10"
gg_vita_prodotto = 1030  -- giorni
difetto = "Compressore guasto"
```

### `rotture_componenti`
Componenti sostituiti durante la riparazione
- **PK composita:** (`cod_rottura`, `cod_componente`)
- **FK:** `cod_rottura` → rotture, `cod_componente` → componenti

**Esempio:**
```sql
-- Nella rottura ROT2024001 è stato sostituito il compressore COMP001
cod_rottura = "123|ROT2024001"
cod_componente = "COMP001"
```

**Query utile:**
```sql
-- Trova i componenti più sostituiti
SELECT
    c.part_name_it,
    COUNT(*) as num_sostituzioni
FROM rotture_componenti rc
JOIN componenti c ON rc.cod_componente = c.cod_componente
GROUP BY c.part_name_it
ORDER BY num_sostituzioni DESC;
```

---

## 📊 Tracciamento Elaborazioni

### Sistema NUOVO (`trace_elab`)

#### `trace_elab`
Tracciamento elaborazione file (livello file)
- **PK:** `id_trace`
- **Campi:** id_file, tipo_file ('ORD'|'ANA'|'ROT'), step, stato ('OK'|'KO'), messaggio

#### `trace_elab_dett`
Dettaglio elaborazione (livello riga/record)
- **PK:** `id_trace_dett`
- **FK:** `id_trace` → trace_elab
- **Campi:** record_pos (numero riga), record_data (JSON), messaggio, stato

**Esempio:**
```sql
-- Trace file ordini
INSERT INTO trace_elab (id_file, tipo_file, step, stato, messaggio)
VALUES (123, 'ORD', 'INIZIO ETL', 'OK', 'Inizio elaborazione file PO2024001.pdf');

-- Trace errore su riga specifica
INSERT INTO trace_elab_dett (id_trace, record_pos, record_data, messaggio, stato)
VALUES (1, 15, '{"cod_ordine": "PO2024001", "riga": 15}', 'Prezzo non valido', 'KO');
```

### Sistema VECCHIO (mantenuto per retrocompatibilità)

- `trace_elaborazioni`
- `trace_elaborazioni_dettaglio`

---

## 🔗 Relazioni Principali

### Relazione Centrale: `modelli`

```
controparti ──→ file_ordini ──→ ordini ──→ modelli
                                              ↑
file_anagrafiche ──→ modelli_componenti ─────┤
                           ↓                  │
                      componenti              │
                           ↑                  │
                           │                  │
file_rotture ──→ rotture ──┴──────────────────┘
                    ↓
            rotture_componenti ──→ componenti
```

### Query Esempio: Analisi Completa Modello

```sql
-- Tutti i dati di un modello
SELECT
    m.cod_modello,
    m.nome_modello,
    m.marca,

    -- Ordini ricevuti
    COUNT(DISTINCT o.cod_ordine) as num_ordini,
    SUM(o.qta) as qta_ordinata,

    -- Componenti (BOM)
    COUNT(DISTINCT mc.cod_componente) as num_componenti,

    -- Rotture
    COUNT(DISTINCT r.cod_rottura) as num_rotture,
    AVG(r.gg_vita_prodotto) as vita_media_giorni

FROM modelli m
LEFT JOIN ordini o ON m.cod_modello = o.cod_modello
LEFT JOIN modelli_componenti mc ON m.cod_modello = mc.cod_modello
LEFT JOIN rotture r ON m.cod_modello = r.cod_modello
WHERE m.cod_modello = 'FRIDGE2000'
GROUP BY m.cod_modello, m.nome_modello, m.marca;
```

---

## 📐 Convenzioni Codici

### Codici Chiave Primaria Composita

Formato: `parte1|parte2`

- `ordini.ordine_modello` = `cod_ordine` + `|` + `cod_modello`
  - Esempio: `"PO2024001|FRIDGE2000"`

- `modelli_componenti.cod_modello_componente` = `cod_modello` + `|` + `cod_componente`
  - Esempio: `"FRIDGE2000|COMP001"`

- `rotture.cod_rottura` = `id_file_rotture` + `|` + `prot`
  - Esempio: `"123|ROT2024001"`

### Codici Normalizzati

Per facilitare il matching tra file diversi:

- `modelli.cod_modello_norm`: versione normalizzata del codice (uppercase, trim, ecc.)
- `componenti.cod_componente_norm`: versione normalizzata del codice

**Esempio normalizzazione:**
```python
cod_modello = "  FriDge-2000  "
cod_modello_norm = "FRIDGE2000"  # uppercase, no spaces, no dash
```

---

## 🔄 Campi Audit (Tutti i Modelli)

Tutti i modelli business hanno campi di audit:

- `created_at`: timestamp creazione
- `created_by`: FK → users.id_user (chi ha creato)
- `updated_at`: timestamp ultimo aggiornamento
- `updated_by`: FK → users.id_user (chi ha aggiornato)

**Esempio:**
```python
modello = Modello(
    cod_modello="FRIDGE2000",
    nome_modello="Frigorifero 2000",
    created_by=current_user.id
)
db.session.add(modello)
db.session.commit()
```

---

## 🎯 Esempi d'Uso

### Esempio 1: Upload Ordine

```python
# 1. Upload PDF
file_ordine = FileOrdine(
    anno=2024,
    filename="PO2024001.pdf",
    filepath="/path/to/file.pdf",
    cod_seller="SELLER001",
    cod_buyer="BUYER001",
    data_ordine=date(2024, 11, 15),
    created_by=current_user.id
)
db.session.add(file_ordine)
db.session.flush()

# 2. Parsing PDF e creazione righe
for riga in parse_pdf("PO2024001.pdf"):
    # Crea/aggiorna modello se necessario
    modello = get_or_create_modello(riga['cod_modello'])

    # Crea riga ordine
    ordine = Ordine(
        ordine_modello=f"{riga['cod_ordine']}|{riga['cod_modello']}",
        id_file_ordine=file_ordine.id,
        cod_ordine=riga['cod_ordine'],
        cod_modello=riga['cod_modello'],
        qta=riga['qta'],
        prezzo_eur=riga['prezzo'],
        created_by=current_user.id
    )
    db.session.add(ordine)

db.session.commit()
```

### Esempio 2: Upload Anagrafica

```python
# 1. Upload Excel
file_ana = FileAnagrafica(
    anno=2024,
    marca="HISENSE",
    filename="ana_hisense_2024.xlsx",
    filepath="/path/to/file.xlsx",
    created_by=current_user.id
)
db.session.add(file_ana)
db.session.flush()

# 2. Parsing Excel BOM
for riga in parse_excel_bom("ana_hisense_2024.xlsx"):
    # Crea/aggiorna modello
    modello = get_or_create_modello(riga['cod_modello'])

    # Crea/aggiorna componente
    componente = get_or_create_componente(riga['cod_componente'])

    # Crea associazione
    mc = ModelloComponente(
        cod_modello_componente=f"{riga['cod_modello']}|{riga['cod_componente']}",
        id_file_anagrafiche=file_ana.id,
        cod_modello=riga['cod_modello'],
        cod_componente=riga['cod_componente'],
        qta=riga['qta'],
        created_by=current_user.id
    )
    db.session.add(mc)

db.session.commit()
```

### Esempio 3: Upload Rotture

```python
# 1. Upload Excel
file_rot = FileRottura(
    anno=2024,
    filename="rotture_2024.xlsx",
    filepath="/path/to/file.xlsx",
    created_by=current_user.id
)
db.session.add(file_rot)
db.session.flush()

# 2. Parsing Excel rotture
for riga in parse_excel_rotture("rotture_2024.xlsx"):
    # Crea utente/rivenditore se necessari
    utente = get_or_create_utente_rottura(riga['cod_utente'])
    rivenditore = get_or_create_rivenditore(riga['cod_rivenditore'])
    modello = get_or_create_modello(riga['cod_modello'])

    # Crea rottura
    rottura = Rottura(
        cod_rottura=f"{file_rot.id}|{riga['prot']}",
        id_file_rotture=file_rot.id,
        prot=riga['prot'],
        cod_modello=riga['cod_modello'],
        cod_rivenditore=riga['cod_rivenditore'],
        cod_utente=riga['cod_utente'],
        data_acquisto=riga['data_acquisto'],
        data_apertura=riga['data_apertura'],
        difetto=riga['difetto'],
        created_by=current_user.id
    )
    db.session.add(rottura)

    # Crea componenti sostituiti
    for cod_comp in riga['componenti_sostituiti']:
        rc = RotturaComponente(
            cod_rottura=rottura.cod_rottura,
            cod_componente=cod_comp,
            created_by=current_user.id
        )
        db.session.add(rc)

db.session.commit()
```

---

**Versione:** 1.0
**Data:** 2025-01-19
**Autore:** Claude (Anthropic)
