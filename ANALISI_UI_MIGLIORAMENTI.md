# Analisi UI e Miglioramenti - Sistema MEC Previsioni

**Data Analisi:** 2025-11-21
**Branch:** claude/analyze-ui-improvements-0186LN7UhaDpKVMysQ7StAaz
**Versione Applicazione:** 0.0.8
**Completamento Progetto:** 56%

---

## INDICE

1. [Executive Summary](#executive-summary)
2. [Aree di Miglioramento UI](#aree-di-miglioramento-ui)
3. [Funzionalità Mancanti per Valore](#funzionalità-mancanti-per-valore)
4. [Quick Wins Prioritari](#quick-wins-prioritari)
5. [Roadmap Consigliata](#roadmap-consigliata)

---

## EXECUTIVE SUMMARY

### Stato Attuale
- **Infrastruttura:** Solida (100% completa)
- **UI Base:** Funzionale ma migliorabile (6.5/10)
- **Parsing Dati:** Non implementato (0-20%)
- **Analytics:** Base presente (20%)

### Valore Potenziale Non Realizzato
Il sistema è ben progettato ma **il valore reale per il cliente è bloccato** dalla mancanza di:
1. Parsing automatico dei file (eliminerebbe lavoro manuale)
2. Analytics predittiva completa (ridurrebbe costi inventario del 20-30%)
3. Dashboard business intelligence (migliorerebbe decision-making)

### Raccomandazione Principale
**Priorità assoluta:** Completare le 3 pipeline di parsing (Ordini PDF, Anagrafiche Excel, Rotture Excel) per sbloccare il valore business del sistema predittivo.

---

## AREE DI MIGLIORAMENTO UI

### 1. PROBLEMI CRITICI (P0) - Impatto Alto, Facilità Alta

#### 1.1 Validazione Client-Side Assente
**Problema:** Nessuna validazione HTML5 nei form.

**Impatto:**
- Errori evitabili scoperti solo dopo submit server
- Frustrazione utenti
- Carico server inutile

**Soluzioni Quick:**
```html
<!-- Date input senza date picker -->
❌ ATTUALE: <input type="text" placeholder="gg/mm/aaaa">
✅ MIGLIORE: <input type="date" required>

<!-- Email senza pattern -->
❌ ATTUALE: <input type="text" name="email">
✅ MIGLIORE: <input type="email" required pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$">

<!-- Password senza toggle -->
❌ ATTUALE: <input type="password">
✅ MIGLIORE: <input type="password"> <button type="button" onclick="togglePassword()">👁️</button>
```

**File da modificare:**
- `templates/login.html` (email, password)
- `templates/users/create.html` (email, password)
- `templates/users/edit.html` (email, password)
- `templates/ordini/create.html` (data_ordine)
- `templates/anagrafiche/create.html` (anno)
- `templates/rotture/create.html` (anno)

**Stima:** 2-3 ore, ROI immediato

---

#### 1.2 Upload File Senza Feedback
**Problema:** Nessuna progress bar, nessuna conferma file selezionato.

**Impatto:**
- Utenti non sanno se upload è in corso
- Upload grandi (PDF/Excel) sembrano freezare l'app
- Rischio doppio upload

**Soluzioni:**
```javascript
// Progress bar con fetch API
async function uploadWithProgress(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/upload', {
    method: 'POST',
    body: formData
  });

  // Mostra progress bar durante upload
}
```

**File da modificare:**
- `templates/ordini/create.html`
- `templates/anagrafiche/create.html`
- `templates/rotture/create.html`

**Libreria consigliata:** Dropzone.js o fetch con progress
**Stima:** 4-6 ore

---

#### 1.3 Submit Multipli Non Prevenuti
**Problema:** Form possono essere submitted più volte.

**Impatto:**
- Elaborazioni duplicate
- Record duplicati nel database
- Confusione utenti

**Soluzione Quick:**
```html
<button type="submit" onclick="this.disabled=true; this.form.submit();">
  Salva
</button>

<!-- Meglio: con loading state -->
<button type="submit" id="submitBtn">
  <span id="btnText">Salva</span>
  <span id="btnSpinner" class="d-none">
    <span class="spinner-border spinner-border-sm"></span> Caricamento...
  </span>
</button>

<script>
document.getElementById('myForm').addEventListener('submit', function() {
  document.getElementById('submitBtn').disabled = true;
  document.getElementById('btnText').classList.add('d-none');
  document.getElementById('btnSpinner').classList.remove('d-none');
});
</script>
```

**File da modificare:** Tutti i form (10+ template)
**Stima:** 1-2 ore

---

### 2. PROBLEMI ALTI (P1) - Impatto Alto, Sforzo Medio

#### 2.1 Breadcrumbs Inconsistenti
**Problema:** Breadcrumbs presenti in create/edit ma NON in list pages.

**Impatto:**
- Disorientamento utenti
- Difficile navigazione gerarchica

**Esempio:**
```html
<!-- users/list.html - MANCANTE -->
❌ Nessun breadcrumb

<!-- users/create.html - PRESENTE -->
✅ Home > Utenti > Crea Nuovo Utente
```

**Soluzione:**
Aggiungere breadcrumb consistente in TUTTE le list pages:
```html
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="{{ url_for('dashboard') }}">Home</a></li>
    <li class="breadcrumb-item active" aria-current="page">File Ordini</li>
  </ol>
</nav>
```

**File da modificare:**
- `templates/users/list.html`
- `templates/ordini/list.html` (già presente, verificare)
- `templates/anagrafiche/list.html` (già presente, verificare)
- `templates/rotture/list.html` (già presente, verificare)

**Stima:** 1 ora

---

#### 2.2 Tabelle Non Responsive
**Problema:** Overflow su mobile non gestito, tabelle larghe illeggibili.

**Impatto:**
- Impossibile usare app su mobile/tablet
- Scrolling orizzontale difficile

**Soluzioni:**
1. **Opzione 1 - DataTables Responsive** (già usato in previsioni)
```javascript
$('#myTable').DataTable({
  responsive: true
});
```

2. **Opzione 2 - Bootstrap table-responsive**
```html
<div class="table-responsive">
  <table class="table">...</table>
</div>
```

3. **Opzione 3 - Card stack su mobile**
```html
<!-- Desktop: tabella -->
<!-- Mobile: card -->
@media (max-width: 768px) {
  .table { display: none; }
  .card-view { display: block; }
}
```

**File da modificare:** Tutte le list pages
**Stima:** 1 giorno

---

#### 2.3 Filtri Senza Conteggio Risultati
**Problema:** Non si sa quanti record ci sono prima/dopo filtro.

**Impatto:**
- Utenti non sanno se filtro ha funzionato
- Esperienza UX povera

**Soluzione:**
```html
<!-- Prima -->
<h4>File Ordini</h4>

<!-- Dopo -->
<h4>File Ordini <span class="badge bg-secondary">{{ files|length }} risultati</span></h4>

<!-- Con filtri attivi -->
<h4>
  File Ordini
  <span class="badge bg-primary">{{ filtered_count }} di {{ total_count }}</span>
  {% if has_filters %}
    <a href="{{ url_for('ordini.list') }}" class="btn btn-sm btn-outline-secondary">
      Reset Filtri
    </a>
  {% endif %}
</h4>
```

**File da modificare:**
- `routes/ordini.py` (aggiungere total_count al context)
- `templates/ordini/list.html`
- Idem per anagrafiche, rotture, users

**Stima:** 2-3 ore

---

#### 2.4 HTML Malformato
**Problema:** `rotture/list.html:249` contiene `<h56class` invece `<h6 class`.

**Impatto:**
- Rendering incorretto
- Possibili errori parsing browser

**Soluzione:** Fix immediato.

**File:** `templates/rotture/list.html` riga 249
**Stima:** 2 minuti

---

### 3. PROBLEMI MEDI (P2) - Impatto Medio, Sforzo Vario

#### 3.1 JavaScript/CSS Inline
**Problema:** Logica e stili nei template invece di file esterni.

**Impatto:**
- Manutenibilità difficile
- Duplicazione codice
- No caching browser
- Dimensione HTML aumentata

**Soluzione:**
Creare file separati:
```
static/
  js/
    app.js          # JavaScript globale
    ordini.js       # Specifico ordini
    anagrafiche.js  # Specifico anagrafiche
    charts.js       # Grafici
  css/
    custom.css      # Stili custom
    dashboard.css   # Dashboard
```

**File da refactoring:**
- `templates/previsioni/previsioni.html` (CSS molto lungo inline)
- `templates/ordini/create.html` (JS preview anno)
- Tutti i modal AJAX

**Stima:** 2 giorni
**Valore:** Alto lungo termine

---

#### 3.2 Conferme con alert()
**Problema:** `onsubmit="return confirm()"` non accessibile.

**Impatto:**
- Non screen-reader friendly
- UX povera
- Non customizzabile

**Soluzione:**
Usare modal Bootstrap (già presente in anagrafiche):
```html
<!-- Invece di -->
<form onsubmit="return confirm('Sicuro?')">

<!-- Usare modal -->
<button type="button" data-bs-toggle="modal" data-bs-target="#confirmModal">
  Elimina
</button>

<div class="modal" id="confirmModal">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5>Conferma Eliminazione</h5>
      </div>
      <div class="modal-body">
        Sei sicuro di voler eliminare questo record?
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
        <form method="POST" style="display:inline;">
          <button type="submit" class="btn btn-danger">Elimina</button>
        </form>
      </div>
    </div>
  </div>
</div>
```

**File da modificare:**
- `templates/ordini/list.html` (elabora)
- `templates/rotture/list.html` (elabora)
- Uniformare pattern in tutti i delete

**Stima:** 3-4 ore

---

#### 3.3 Nessun Bulk Actions
**Problema:** Impossibile selezionare multipli record per azioni batch.

**Impatto:**
- Operazioni ripetitive manuali
- Inefficienza per grandi dataset

**Soluzione:**
```html
<table>
  <thead>
    <tr>
      <th><input type="checkbox" id="selectAll"></th>
      <th>Filename</th>
      <th>Azioni</th>
    </tr>
  </thead>
  <tbody>
    {% for file in files %}
    <tr>
      <td><input type="checkbox" name="selected[]" value="{{ file.id }}"></td>
      <td>{{ file.filename }}</td>
      <td>...</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<div id="bulkActions" style="display:none;">
  <button type="button" onclick="bulkDelete()">Elimina Selezionati</button>
  <button type="button" onclick="bulkProcess()">Elabora Selezionati</button>
</div>

<script>
// Mostra bulk actions quando almeno 1 checkbox selezionato
document.querySelectorAll('input[name="selected[]"]').forEach(cb => {
  cb.addEventListener('change', function() {
    const anyChecked = document.querySelectorAll('input[name="selected[]"]:checked').length > 0;
    document.getElementById('bulkActions').style.display = anyChecked ? 'block' : 'none';
  });
});
</script>
```

**File da modificare:** Tutte le list pages
**Backend:** Aggiungere route `/bulk-delete`, `/bulk-process`
**Stima:** 2 giorni

---

#### 3.4 Tooltips e Help Text Mancanti
**Problema:** Abbreviazioni (STAT, CI, MTBF) senza spiegazione.

**Impatto:**
- Curva apprendimento alta
- Confusione utenti nuovi

**Soluzione:**
```html
<!-- Bootstrap Tooltips -->
<span data-bs-toggle="tooltip" data-bs-placement="top" title="Confidence Interval">
  CI
</span>

<!-- Help icon -->
<label>
  Stato
  <i class="fas fa-question-circle" data-bs-toggle="tooltip" title="OK = Elaborato con successo, KO = Errore, WARN = Warning"></i>
</label>

<!-- Field-level help text -->
<input type="text" name="cod_modello" class="form-control">
<small class="form-text text-muted">
  Codice modello alfanumerico, max 50 caratteri. Es: FRIDGE2000
</small>
```

**File da modificare:**
- `templates/previsioni/previsioni.html` (CI, STAT, MTBF)
- Tutti i form (help text campi complessi)

**Stima:** 1 giorno

---

### 4. PROBLEMI BASSI (P3) - Nice to Have

#### 4.1 Animazioni Feedback Assenti
- Flash messages statici (aggiungere fade in/out)
- Nessuna success animation dopo operazioni
- Transizioni pagine brusche

**Soluzione:** CSS animations, Toast notifications
**Stima:** 1-2 giorni

---

#### 4.2 Drag & Drop Upload
- Upload solo browse file (aggiungere drag & drop)

**Soluzione:** Dropzone.js
**Stima:** 1 giorno

---

#### 4.3 Preview Migliorata
- PDF: link esterno invece preview inline
- Excel: preview ok ma limitata a prime righe

**Soluzione:** PDF.js per preview inline, DataTables per Excel completo
**Stima:** 2-3 giorni

---

## FUNZIONALITÀ MANCANTI PER VALORE

Ordinate per **ROI economico/operativo per il cliente**.

### TIER 1: ALTISSIMO VALORE (ROI 6-12 mesi)

---

#### 1. PARSING AUTOMATICO PDF ORDINI (Valore: €€€€€)

**Problema Attuale:**
Parsing PDF ordini è stub (dati simulati). Tabelle business vuote.

**Valore per Cliente:**
- **Riduzione lavoro manuale:** Eliminazione inserimento dati manuale (stima 2-4 ore/ordine)
- **Riduzione errori:** No errori trascrizione (stima 5-10% errori manuali)
- **Scalabilità:** Gestione centinaia ordini/mese automaticamente
- **ROI stimato:** €20.000-40.000/anno in tempo risparmiato

**Implementazione:**
```python
# utils/pdf_parser.py
import pdfplumber

def parse_ordine_pdf(filepath):
    """
    Estrae da PDF ordine:
    - Seller/Buyer (controparti)
    - Data ordine, oggetto ordine
    - Righe: cod_modello, qta, prezzo_eur
    """
    with pdfplumber.open(filepath) as pdf:
        # Logic parsing
        pass

    return {
        'seller': 'SELLER001',
        'buyer': 'BUYER001',
        'data_ordine': '2024-11-20',
        'righe': [
            {'cod_modello': 'FRIDGE2000', 'qta': 100, 'prezzo_eur': 150.00},
            ...
        ]
    }

# routes/ordini.py - elabora_ordine()
def elabora_ordine(file_id):
    file_ordine = FileOrdine.query.get(file_id)

    # Parsing
    data = parse_ordine_pdf(file_ordine.filepath)

    # Popola controparti
    seller = get_or_create_controparte(data['seller'])
    buyer = get_or_create_controparte(data['buyer'])

    # Popola ordini
    for riga in data['righe']:
        modello = get_or_create_modello(riga['cod_modello'])
        ordine = Ordine(...)
        db.session.add(ordine)

    db.session.commit()
```

**File da modificare:**
- Creare `utils/pdf_parser.py` (nuovo)
- Modificare `routes/ordini_funzioni_elaborazione.py`
- Creare `utils/normalizer.py` per cod_modello_norm

**Dipendenze:**
- `pdfplumber` o `PyPDF2` (già in requirements.txt)
- Logica normalizzazione codici

**Stima:** 5-7 giorni
**Priorità:** 🔴 CRITICA

---

#### 2. PARSING AUTOMATICO EXCEL ANAGRAFICHE (Valore: €€€€€)

**Problema Attuale:**
Parsing Excel BOM è stub. Tabelle `modelli_componenti`, `componenti` vuote.

**Valore per Cliente:**
- **Database BOM completo:** Foundation per analisi predittive
- **Riduzione lavoro manuale:** Eliminazione inserimento BOM (stima 4-8 ore/file)
- **Matching cross-pipeline:** Correlazione ordini-rotture-BOM
- **ROI stimato:** €15.000-30.000/anno

**Implementazione:**
```python
# utils/excel_parser_ana.py
import pandas as pd

def parse_anagrafica_excel(filepath):
    """
    Estrae da Excel BOM:
    - cod_modello, marca, famiglia
    - cod_componente, part_no, part_name, qta
    """
    df = pd.read_excel(filepath, engine='openpyxl')

    # Identifica colonne (potrebbe variare per marca)
    # Normalizza encoding (caratteri cinesi)

    return [
        {
            'cod_modello': 'FRIDGE2000',
            'marca': 'HISENSE',
            'componenti': [
                {'cod_componente': 'COMP001', 'qta': 2, 'part_name_cn': '压缩机'},
                ...
            ]
        },
        ...
    ]

# routes/anagrafiche.py - elabora_anagrafica()
def elabora_anagrafica(file_id):
    file_ana = FileAnagrafica.query.get(file_id)

    # Parsing
    data = parse_anagrafica_excel(file_ana.filepath)

    for item in data:
        # Popola modelli
        modello = get_or_create_modello(item['cod_modello'], item['marca'])

        # Popola componenti e BOM
        for comp in item['componenti']:
            componente = get_or_create_componente(comp['cod_componente'])
            mc = ModelloComponente(...)
            db.session.add(mc)

    db.session.commit()
```

**File da modificare:**
- Creare `utils/excel_parser_ana.py` (nuovo)
- Modificare `routes/anagrafiche.py`
- Gestione encoding caratteri speciali

**Dipendenze:**
- `pandas`, `openpyxl` (già presenti)
- Logica normalizzazione multi-lingua

**Stima:** 5-7 giorni
**Priorità:** 🔴 CRITICA

---

#### 3. PARSING AUTOMATICO EXCEL ROTTURE (Valore: €€€€€)

**Problema Attuale:**
Parsing parziale (solo TSV base). Tabelle `rotture`, `rotture_componenti` non popolate.

**Valore per Cliente:**
- **Analisi predittiva sbloccata:** Core business dell'app
- **MTBF automatico:** Mean Time Between Failures per componente
- **Previsioni domanda:** Basate su tasso rotture reale
- **ROI stimato:** €50.000-100.000/anno in riduzione costi inventario

**Implementazione:**
```python
# routes/rotture_funzioni_elaborazione.py - completare
def parse_rotture_excel(filepath):
    """
    Estrae da Excel rotture:
    - prot, CAT, data_acquisto, data_apertura
    - cod_modello, cod_componenti_sostituiti
    - cod_utente_rottura, cod_rivenditore
    - difetto, problema_segnalato
    """
    df = pd.read_excel(filepath, engine='openpyxl')

    # Calcola gg_vita_prodotto
    df['gg_vita_prodotto'] = (df['data_apertura'] - df['data_acquisto']).dt.days

    return df.to_dict('records')

# Popola tabelle
def elabora_rotture(file_id):
    # ...
    for riga in data:
        rottura = Rottura(
            cod_rottura=f"{file_id}|{riga['prot']}",
            gg_vita_prodotto=riga['gg_vita_prodotto'],
            ...
        )

        # Componenti sostituiti
        for cod_comp in riga['componenti']:
            rc = RotturaComponente(...)
            db.session.add(rc)
```

**File da modificare:**
- Completare `routes/rotture_funzioni_elaborazione.py`
- Aggiungere calcolo metriche (gg_vita_prodotto)

**Dipendenze:**
- `pandas` (già presente)
- Validazione date

**Stima:** 4-6 giorni
**Priorità:** 🔴 CRITICA

---

### TIER 2: ALTO VALORE (ROI 12-24 mesi)

---

#### 4. DASHBOARD ANALYTICS AVANZATA (Valore: €€€€)

**Problema Attuale:**
Dashboard esistente mostra solo statistiche base (numero file, elaborazioni).

**Valore per Cliente:**
- **Business Intelligence:** KPI actionable
- **Decision-making:** Data-driven invece istinto
- **Early warning:** Componenti a rischio
- **ROI stimato:** €10.000-20.000/anno in decisioni migliori

**Funzionalità Richieste:**

1. **KPI Cards**
   - Numero totale modelli attivi
   - Componenti critici (alta frequenza rottura)
   - MTBF medio per marca
   - Valore inventario ottimale

2. **Grafici Interattivi**
   - Trend rotture nel tempo (line chart)
   - Top 10 componenti guasti (bar chart)
   - Distribuzione rotture per marca (pie chart)
   - Heatmap rotture per modello/componente

3. **Tabelle Analitiche**
   - Modelli con MTBF < soglia (ordina per rischio)
   - Componenti con stock insufficiente (alerts)
   - Previsioni domanda prossimi 6 mesi

**Implementazione:**
```python
# routes/dashboard.py
@dashboard_bp.route('/analytics')
def analytics():
    # KPI
    total_models = db.session.query(Modello).count()

    # Top componenti guasti
    top_rotture = db.session.query(
        Componente.part_name_it,
        func.count(RotturaComponente.cod_componente).label('num_rotture')
    ).join(RotturaComponente).group_by(Componente.part_name_it).order_by(desc('num_rotture')).limit(10).all()

    # MTBF per marca
    mtbf_by_marca = db.session.query(
        Modello.marca,
        func.avg(Rottura.gg_vita_prodotto).label('mtbf_avg')
    ).join(Rottura).group_by(Modello.marca).all()

    return render_template('dashboard/analytics.html',
        total_models=total_models,
        top_rotture=top_rotture,
        mtbf_by_marca=mtbf_by_marca
    )
```

**Template (Chart.js):**
```html
<canvas id="topRottureChart"></canvas>
<script>
const ctx = document.getElementById('topRottureChart').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: {{ top_rotture|map(attribute='part_name_it')|list|tojson }},
    datasets: [{
      label: 'Numero Rotture',
      data: {{ top_rotture|map(attribute='num_rotture')|list|tojson }},
      backgroundColor: 'rgba(255, 99, 132, 0.5)'
    }]
  }
});
</script>
```

**File da creare:**
- `templates/dashboard/analytics.html` (nuovo)
- `static/js/charts.js` (Chart.js wrapper)

**Dipendenze:**
- Chart.js (CDN o npm)

**Stima:** 7-10 giorni
**Priorità:** 🟠 ALTA (dopo parsing completo)

---

#### 5. PREVISIONI DOMANDA COMPONENTI (Valore: €€€€)

**Problema Attuale:**
Route `/previsioni` esiste ma funzionalità limitata.

**Valore per Cliente:**
- **Ottimizzazione inventario:** Stock minimo necessario
- **Riduzione costi stoccaggio:** -20% inventario medio
- **Riduzione stockout:** Sempre componenti disponibili
- **ROI stimato:** €30.000-60.000/anno

**Funzionalità:**

1. **Previsione per Componente**
   - Input: cod_componente
   - Output: quantità necessaria 1/3/6/12 mesi
   - Basato su: tasso rotture storico + seasonal patterns

2. **Previsione per Modello**
   - Input: cod_modello
   - Output: tutti componenti BOM con quantità
   - Basato su: previsioni vendite modello × BOM × tasso guasto

3. **Suggerimenti Ordine**
   - Lista componenti sotto scorta minima
   - Quantità ottimale ordine
   - Fornitore consigliato (da storico ordini)

**Implementazione:**
```python
# utils/analytics.py
from lifelines import KaplanMeierFitter
import numpy as np

def forecast_component_demand(cod_componente, months=6):
    """
    Previsione domanda componente basata su:
    - Storico rotture
    - Seasonal patterns
    - Trend vendite modelli che lo usano
    """
    # 1. Recupera rotture storiche
    rotture = db.session.query(RotturaComponente).filter_by(
        cod_componente=cod_componente
    ).all()

    # 2. Calcola tasso rotture mensile
    rate_per_month = len(rotture) / 12  # Esempio semplificato

    # 3. Kaplan-Meier per tempo medio rottura
    kmf = KaplanMeierFitter()
    # ... fit su dati ...

    # 4. Previsione
    forecast = rate_per_month * months

    # 5. Intervallo confidenza
    ci_lower = forecast * 0.8
    ci_upper = forecast * 1.2

    return {
        'forecast': forecast,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'recommended_order_qty': ci_upper  # Ordina upper bound per sicurezza
    }

# routes/previsioni.py
@previsioni_bp.route('/domanda', methods=['GET', 'POST'])
def domanda_componenti():
    if request.method == 'POST':
        cod_componente = request.form.get('cod_componente')
        months = int(request.form.get('months', 6))

        forecast = forecast_component_demand(cod_componente, months)

        return render_template('previsioni/domanda.html',
            componente=Componente.query.get(cod_componente),
            forecast=forecast,
            months=months
        )

    return render_template('previsioni/domanda.html')
```

**File da creare:**
- `utils/analytics.py` (nuovo)
- `templates/previsioni/domanda.html` (nuovo)

**Dipendenze:**
- `lifelines` (già presente)
- `numpy`, `scipy` (già presenti)

**Stima:** 7-10 giorni
**Priorità:** 🟠 ALTA

---

#### 6. ANALISI MTBF E COMPONENTI CRITICI (Valore: €€€€)

**Problema Attuale:**
Nessuna analisi automatica affidabilità.

**Valore per Cliente:**
- **Identificazione componenti critici:** Focus miglioramento qualità
- **Garanzie data-driven:** Estensione/riduzione garanzia basata su MTBF
- **Negoziazione fornitori:** Dati oggettivi per contrattazione
- **ROI stimato:** €15.000-25.000/anno

**Funzionalità:**

1. **MTBF per Componente**
   - Mean Time Between Failures (giorni)
   - Distribuzione Weibull fit
   - Confronto MTBF atteso vs reale

2. **Componenti Critici Dashboard**
   - Top 10 componenti con MTBF più basso
   - Trend MTBF nel tempo (migliora/peggiora?)
   - Alert se MTBF < soglia

3. **Analisi Correlazioni**
   - Difetto → Componente (quali componenti per ogni tipo difetto?)
   - Modello → Componente critico (quali modelli hanno più problemi?)
   - Marca → MTBF (qual è la marca più affidabile?)

**Implementazione:**
```python
# utils/analytics.py
def calculate_mtbf(cod_componente=None, cod_modello=None):
    """
    Calcola MTBF (Mean Time Between Failures) in giorni
    """
    query = db.session.query(Rottura.gg_vita_prodotto)

    if cod_componente:
        query = query.join(RotturaComponente).filter(
            RotturaComponente.cod_componente == cod_componente
        )

    if cod_modello:
        query = query.filter(Rottura.cod_modello == cod_modello)

    failures = [r[0] for r in query.all() if r[0] is not None]

    if not failures:
        return None

    mtbf = np.mean(failures)
    mtbf_median = np.median(failures)
    mtbf_std = np.std(failures)

    # Weibull fit
    from scipy.stats import weibull_min
    shape, loc, scale = weibull_min.fit(failures)

    return {
        'mtbf_mean': mtbf,
        'mtbf_median': mtbf_median,
        'mtbf_std': mtbf_std,
        'weibull_shape': shape,
        'weibull_scale': scale,
        'sample_size': len(failures)
    }

# routes/previsioni.py
@previsioni_bp.route('/mtbf')
def mtbf_analysis():
    # Top 10 componenti critici (MTBF più basso)
    componenti = Componente.query.all()

    mtbf_data = []
    for comp in componenti:
        mtbf = calculate_mtbf(cod_componente=comp.cod_componente)
        if mtbf and mtbf['sample_size'] >= 5:  # Solo se >= 5 rotture
            mtbf_data.append({
                'componente': comp,
                'mtbf': mtbf
            })

    # Ordina per MTBF crescente (più critici primi)
    mtbf_data.sort(key=lambda x: x['mtbf']['mtbf_mean'])

    return render_template('previsioni/mtbf.html',
        mtbf_data=mtbf_data[:10]  # Top 10
    )
```

**File da creare:**
- Aggiungere funzioni a `utils/analytics.py`
- `templates/previsioni/mtbf.html` (nuovo)

**Stima:** 5-7 giorni
**Priorità:** 🟠 ALTA

---

### TIER 3: MEDIO VALORE (ROI 24+ mesi)

---

#### 7. EXPORT REPORT AUTOMATICI (Valore: €€€)

**Funzionalità:**
- Export PDF report mensili (rotture, MTBF, previsioni)
- Export Excel dashboard analytics
- Scheduled reports (email automatica)

**Valore:**
- Riduzione tempo preparazione report: 4-8 ore/mese
- Report consistenti (no errori manuali)

**Implementazione:**
```python
# utils/report_generator.py
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_monthly_report(year, month):
    """
    Genera PDF con:
    - Statistiche mese (rotture, elaborazioni, MTBF)
    - Grafici principali
    - Top componenti critici
    - Previsioni prossimo mese
    """
    filename = f"report_{year}_{month:02d}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    # Header
    c.drawString(100, 750, f"Report Mensile - {year}/{month}")

    # Contenuto
    # ...

    c.save()
    return filename
```

**Dipendenze:**
- `reportlab` (PDF)
- `openpyxl` (Excel export)
- `celery` (scheduled tasks) - opzionale

**Stima:** 5-7 giorni
**Priorità:** 🟡 MEDIA

---

#### 8. API REST PER INTEGRAZIONI (Valore: €€€)

**Funzionalità:**
- REST API per accesso dati
- Autenticazione JWT
- Endpoint: /api/modelli, /api/componenti, /api/previsioni
- Swagger documentation

**Valore:**
- Integrazione con ERP/CRM cliente
- Accesso programmatico dati
- Mobile app futura

**Implementazione:**
```python
# routes/api.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/modelli', methods=['GET'])
@jwt_required()
def get_modelli():
    modelli = Modello.query.all()
    return jsonify([{
        'cod_modello': m.cod_modello,
        'nome_modello': m.nome_modello,
        'marca': m.marca
    } for m in modelli])

@api_bp.route('/previsioni/<cod_componente>', methods=['GET'])
@jwt_required()
def get_forecast(cod_componente):
    months = request.args.get('months', 6, type=int)
    forecast = forecast_component_demand(cod_componente, months)
    return jsonify(forecast)
```

**Dipendenze:**
- `flask-jwt-extended`
- `flask-restful` o `flask-smorest`
- `apispec` (OpenAPI/Swagger)

**Stima:** 7-10 giorni
**Priorità:** 🟡 MEDIA

---

#### 9. GESTIONE ALERT E NOTIFICHE (Valore: €€)

**Funzionalità:**
- Email alert quando componente sotto scorta minima
- Notifiche elaborazioni fallite
- Alert MTBF < soglia
- Dashboard notifiche in-app

**Valore:**
- Proattività invece reattività
- Riduzione downtime

**Implementazione:**
```python
# utils/alerts.py
from flask_mail import Mail, Message

def check_stock_alerts():
    """
    Controlla componenti sotto scorta minima
    Invia email se necessario
    """
    # Query componenti critici
    # ...

    if critical_components:
        send_email(
            to='admin@example.com',
            subject='Alert: Componenti sotto scorta',
            body=render_template('emails/stock_alert.html', components=critical_components)
        )
```

**Dipendenze:**
- `flask-mail`
- `celery` per scheduled checks

**Stima:** 3-5 giorni
**Priorità:** 🟡 MEDIA

---

### TIER 4: BASSO VALORE DIRETTO (Qualità Vita Utenti)

---

#### 10. MIGLIORAMENTI UX/UI GLOBALI (Valore: €€)

**Funzionalità:**
- Password visibility toggle
- Toast notifications
- Loading states
- Animazioni feedback
- Responsive completo
- Accessibilità (ARIA, keyboard nav)
- Dark mode

**Valore:**
- Adozione utenti migliore
- Riduzione training time
- Soddisfazione utenti

**Stima:** 10-15 giorni (tutti insieme)
**Priorità:** 🟢 BASSA (ma importante lungo termine)

---

#### 11. TESTING AUTOMATIZZATO (Valore: €)

**Funzionalità:**
- Unit tests (pytest)
- Integration tests
- E2E tests (Selenium)
- CI/CD pipeline

**Valore:**
- Riduzione bug produzione
- Confidence refactoring
- Qualità codice

**Stima:** 7-10 giorni setup iniziale
**Priorità:** 🟢 BASSA (ma best practice)

---

## QUICK WINS PRIORITARI

Lista actionable task con alto ROI/effort ratio.

### Top 5 Quick Wins (1-3 ore ciascuno)

1. **Fix HTML malformato** (2 min)
   - File: `templates/rotture/list.html:249`
   - Cambiare `<h56class` → `<h6 class`

2. **Aggiungi `type="date"` a input date** (1-2 ore)
   - File: tutti i form create/edit
   - Migliora UX immediatamente

3. **Aggiungi pattern email validation** (15 min)
   - File: `templates/users/create.html`, `templates/users/edit.html`
   - Previeni errori comuni

4. **Previeni submit multipli** (1 ora)
   - File: tutti i form
   - Aggiungi `onclick="this.disabled=true; this.form.submit();"`

5. **Aggiungi breadcrumbs a list pages** (1 ora)
   - File: `templates/users/list.html`
   - Migliora navigazione

**Totale stima:** 3-4 ore
**Impatto:** Migliora UX da 6.5/10 a 7.5/10

---

## ROADMAP CONSIGLIATA

### FASE 1: SBLOCCA VALORE BUSINESS (Priorità CRITICA)
**Timeline:** 3-4 settimane
**Obiettivo:** Rendere sistema completamente funzionale

**Task:**
1. ✅ Implementa parsing PDF ordini (5-7 giorni)
2. ✅ Implementa parsing Excel anagrafiche (5-7 giorni)
3. ✅ Implementa parsing Excel rotture (4-6 giorni)
4. ✅ Testing completo pipeline (2-3 giorni)

**Milestone:** Database popolato con dati reali, analisi predittive funzionanti

---

### FASE 2: ANALYTICS E INSIGHTS (Priorità ALTA)
**Timeline:** 2-3 settimane
**Obiettivo:** Dashboard business intelligence

**Task:**
1. ✅ Dashboard analytics avanzata (7-10 giorni)
2. ✅ Analisi MTBF componenti critici (5-7 giorni)
3. ✅ Previsioni domanda componenti (7-10 giorni)

**Milestone:** Cliente può prendere decisioni data-driven

---

### FASE 3: AUTOMAZIONE E REPORTING (Priorità MEDIA)
**Timeline:** 2 settimane
**Obiettivo:** Riduzione lavoro manuale

**Task:**
1. ✅ Export report PDF automatici (5-7 giorni)
2. ✅ Sistema alert/notifiche (3-5 giorni)
3. ✅ Bulk actions (2 giorni)

**Milestone:** Report mensili automatici, alert proattivi

---

### FASE 4: INTEGRAZIONI E SCALABILITÀ (Priorità BASSA)
**Timeline:** 2-3 settimane
**Obiettivo:** Preparazione futuro

**Task:**
1. ✅ API REST (7-10 giorni)
2. ✅ Testing automatizzato (7-10 giorni)

**Milestone:** Sistema pronto per integrazioni esterne

---

### FASE 5: UX/UI POLISH (Continuativo)
**Timeline:** Ongoing
**Obiettivo:** Eccellenza utente

**Task (parallelizzabili):**
1. ✅ Quick wins UI (1 settimana)
2. ✅ Responsive completo (1 settimana)
3. ✅ Accessibilità (1 settimana)
4. ✅ Separazione CSS/JS (2 giorni)

**Milestone:** UI professionale 9/10

---

## SUMMARY ESECUTIVO

### Investimento Raccomandato

| Fase | Timeline | Costo Stima* | ROI Atteso | Priorità |
|------|----------|--------------|------------|----------|
| Fase 1: Parsing | 3-4 settimane | €15.000-20.000 | €85.000/anno | 🔴 CRITICA |
| Fase 2: Analytics | 2-3 settimane | €10.000-15.000 | €55.000/anno | 🟠 ALTA |
| Fase 3: Automazione | 2 settimane | €6.000-8.000 | €20.000/anno | 🟡 MEDIA |
| Fase 4: API | 2-3 settimane | €10.000-12.000 | €10.000/anno** | 🟢 BASSA |
| Fase 5: UX/UI | 3 settimane | €8.000-10.000 | Indiretta*** | 🟢 BASSA |
| **TOTALE** | **12-15 settimane** | **€49.000-65.000** | **€170.000/anno** | |

\* Basato su 1 sviluppatore full-time
\*\* ROI indiretto (abilita integrazioni)
\*\*\* Migliora adozione utenti, riduce training

### Break-Even
- **Con solo Fase 1+2:** 3-6 mesi
- **Completo:** 6-9 mesi

### Raccomandazione Finale

**Path Minimo (MVP Completo):**
1. Fase 1 (Parsing) - **MUST HAVE**
2. Quick Wins UI - **NICE TO HAVE**

**Total:** 4-5 settimane, €20.000-25.000, ROI €85.000/anno

**Path Consigliato (Full Value):**
1. Fase 1 (Parsing)
2. Fase 2 (Analytics)
3. Quick Wins UI
4. Fase 3 (Automazione)

**Total:** 8-10 settimane, €35.000-45.000, ROI €160.000/anno

---

**Prossimo Step Suggerito:**
Iniziare IMMEDIATAMENTE con Fase 1 (parsing PDF/Excel) per sbloccare valore business entro 1 mese.

---

**Fine Documento**
**Autore:** Claude (Anthropic)
**Versione:** 1.0
**Data:** 2025-11-21
