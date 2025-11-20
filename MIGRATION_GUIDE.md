# 🚀 Guida Migration id_elab e Metriche

## Cosa Cambia

Abbiamo aggiunto:
1. **`id_elab`**: campo per raggruppare tutte le operazioni di una singola elaborazione
2. **Metriche**: `righe_totali`, `righe_ok`, `righe_errore`, `righe_warning` per statistiche aggregate

### Schema Aggiornato

**`trace_elab`**:
- ✅ `id_elab` (nuovo) - identifica gruppo elaborazione
- ✅ `righe_totali`, `righe_ok`, `righe_errore`, `righe_warning` (nuovi)
- ❌ Rimossi: `ts_inizio`, `ts_fine`, `durata_secondi`, `esito`, `messaggio_globale`

**`trace_elab_dett`**: nessun cambiamento

---

## 📋 Procedura Migration

### 1. Esegui Migration

```bash
python run_migration.py
```

### 2. Verifica

```bash
python -c "from app import app, db; from models import TraceElab; with app.app_context(): print('OK:', TraceElab.__table__.columns.keys())"
```

---

## 🧪 Test

1. Avvia app: `python app.py`
2. Vai su http://localhost:5010/ordini
3. Clicca "Elabora" su un ordine
4. Clicca "📊 Dettagli"
5. Verifica metriche e dettagli funzionano

---

**IMPORTANTE**: I dati esistenti vengono persi. Se serve backup:
```bash
pg_dump -U postgres -d mec_previsioni -t trace_elab -t trace_elab_dett > backup.sql
```
