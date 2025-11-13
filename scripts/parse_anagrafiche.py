# -*- coding: utf-8 -*-
"""
parse_anagrafiche.py — Estrazione generica + HOMA speciale (primo sheet)
- Header = prima riga con prima colonna non vuota
- Campi: codice, descrizione ITA, part name ENG, STAT, Prezzo
- GENERICO (MIDEA/HISENSE): modelli come COLONNE numeriche -> match header con modelli PO
- HOMA: modelli nelle CELLE (colonne 'HOMA model' + 'model*' + '...OEM MODEL')
        -> estrai TUTTI i modelli, PO-filter ON: tieni SOLO quelli presenti nel PO
- Output: un file per ogni input in ../_OUTPUT/anagrafiche/<FORNITORE>/<FILE>__parsed.xlsx
"""

import os
import re
from pathlib import Path
import pandas as pd

# ========= Config =========
DEBUG = True
SHOW_ROWS_PREVIEW = 3
SUPPORT_FILE = "orders_model_quantity_FINAL_shadow.xlsx"  # nella stessa cartella dello script
MAX_PRINT_MODELS = 25  # per non inondare i log
# >>> RICHIESTA: per HOMA vogliamo considerare solo modelli reali (dal PO)
FILTER_HOMA_WITH_PO = True

def dbg(*args):
    if DEBUG:
        print(*args)

# ========= Normalizzazione unica =========
def normalize(s: str) -> str:
    """Case-insensitive, rimuove spazi/punteggiatura: robusto per matching."""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

# ========= Ricerca per pattern su nomi normalizzati =========
def find_idx_by_patterns(cols, patterns, exact=False, prefer='pattern'):
    """
    Ritorna l'INDICE della prima colonna che matcha i patterns.
    - prefer='pattern' => scorre prima i pattern (ordine di priorità), poi le colonne
    - prefer='column'  => scorre prima le colonne (ordine a sinistra), poi i pattern
    - exact=False => match se pattern è substring del nome normalizzato della colonna
    - exact=True  => match se nome_norm == pattern_norm
    """
    ncols = [normalize(c) for c in cols]
    pats = [normalize(p) for p in patterns]

    if prefer == 'pattern':
        for p in pats:
            for idx, norm in enumerate(ncols):
                if (exact and norm == p) or (not exact and p in norm):
                    return idx
    else:  # prefer columns
        for idx, norm in enumerate(ncols):
            for p in pats:
                if (exact and norm == p) or (not exact and p in norm):
                    return idx
    return None

# ========= Pattern di ricerca =========
CODE_PATTERNS_PRIORITY = [
    'mccode','partcode','partno','itemcode','codice','code','sku','articolo'
]
DESC_ITA_PATTERNS = [
    'descrizione','desrita','desrit','descrita','descrizionericambio','descrizioneitaliana','descita'
]
PART_EN_PATTERNS = [
    'partname','partdescription','descriptionen','desceng','englishdescription','description'
]
STAT_PATTERNS_EXACT = ['stat']  # match esatto
PRICE_PATTERNS = [
    'prezzo','price','unitprice','listprice','priceeur','eurprice','prezzolistino','prezzounitario','costo','cost'
]
QTY_PATTERNS = ['quantity','quantita','qty','qt','qta']

# ========= Utility numeriche =========
def to_number_basic(s: str):
    """Converte una stringa numerica semplice (con valuta/separatori) in float/int; None se non riuscito."""
    if s is None:
        return None
    t = str(s).strip()
    if t == '':
        return None
    t = t.replace('€', '').replace('EUR', '').replace('eur', '').replace(' ', '')
    # Gestione 1.234,56 -> 1234.56
    if t.count(',') == 1 and t.count('.') >= 1 and t.rfind(',') > t.rfind('.'):
        t = t.replace('.', '').replace(',', '.')
    else:
        if t.count(',') == 1 and t.count('.') == 0:
            t = t.replace(',', '.')
    try:
        x = float(t)
        return int(x) if x.is_integer() else x
    except Exception:
        return None

def parse_price(val):
    """Mantiene i decimali presenti (niente arrotondamenti)."""
    return None if pd.isna(val) else to_number_basic(val)

def parse_model_qty(val):
    """
    Quantità modello:
    - 'a+b+...' => somma
    - '12 (note)' => 12
    - numeri con ,/.
    - ritorna int/float (in pratica int), None se non numerico.
    """
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s == '':
        return None
    # prendi solo la parte prima di eventuale parentesi
    s_front = s.split('(')[0].strip()

    # somma a+b+...
    if '+' in s_front:
        parts = re.findall(r'\d+(?:[\.,]\d+)?', s_front)
        if not parts:
            return None
        total = 0.0
        for p in parts:
            p = p.replace(',', '.')
            try:
                total += float(p)
            except Exception:
                return None
        return int(total) if total.is_integer() else total

    # caso semplice
    n = to_number_basic(s_front)
    return int(n) if n is not None and float(n).is_integer() else n

# ========= Espansione modelli (celle HOMA) =========
def expand_model_string(s):
    """
    Espande stringhe modello sintetiche:
    - separatori ; , / (crea token separati)
    - 'SHMT-46B/N' -> 'SHMT-46B', 'SHMT-46N' (euristica conservativa)
    - 'ABC(N)' -> 'ABC', 'ABCN'
    Se non riconosce pattern, ritorna [s] (token originale).
    """
    if s is None:
        return []
    raw = str(s).strip()
    if raw == '' or raw == '0':
        return []

    out = set()

    # split elementare su ; e , per più token nella cella
    primary_parts = re.split(r'[;,]', raw)
    if not primary_parts:
        primary_parts = [raw]

    for part in primary_parts:
        part = part.strip()
        if not part or part == '0':
            continue

        # parentesi: ABC(N) -> ABC + ABCN
        if '(' in part and ')' in part:
            pre = part[:part.find('(')].strip()
            inside = part[part.find('(')+1:part.find(')')].strip()
            if pre:
                out.add(pre)
            if pre and inside:
                out.add((pre + inside).strip())

        # suffisso con slash: SHMT-46B/N -> SHMT-46B, SHMT-46N
        if '/' in part and '-' in part:
            left, right = part.rsplit('-', 1)
            segs = right.split('/')
            if len(segs) == 2 and segs[0] and segs[1]:
                out.add(left + '-' + segs[0])
                # variante “sostituzione ultima parte”
                if len(segs[1]) > 1:
                    out.add(left + '-' + segs[1])
                else:
                    base = segs[0][:-1] if len(segs[0]) > 1 else segs[0]
                    out.add(left + '-' + base + segs[1])

        # split residuo semplice su '/'
        if '/' in part:
            for sub in part.split('/'):
                sub = sub.strip()
                if sub:
                    out.add(sub)

        # token grezzo
        out.add(part)

    return [x for x in sorted(out) if x]

# ========= Header detection =========
def read_first_sheet_with_detected_header(xlsx_path: Path):
    """
    Legge il 1° sheet SENZA header; individua la riga-header come prima riga
    con colonna A non vuota; usa quella riga come intestazione.
    """
    df_raw = pd.read_excel(xlsx_path, sheet_name=0, header=None, engine='openpyxl')
    if df_raw.empty or df_raw.shape[1] == 0:
        raise Exception("Foglio vuoto o senza colonne.")

    col0 = df_raw.iloc[:, 0].astype(str).str.strip()
    col0 = col0.replace({'nan': '', 'None': '', 'NaT': ''})

    idx_candidates = col0[col0 != '']
    if idx_candidates.empty:
        header_idx = 0
        first_val = str(df_raw.iloc[0, 0])
    else:
        header_idx = idx_candidates.index[0]
        first_val = str(df_raw.iloc[header_idx, 0])

    first_val_norm = normalize(first_val)
    print(f"  [HEADER] row={header_idx+1} | colA='{first_val}' | norm='{first_val_norm}'")

    header_row = df_raw.iloc[header_idx].astype(str).tolist()
    df = df_raw.iloc[header_idx+1:].copy()
    df.columns = header_row

    # elimina colonne completamente vuote
    df = df.loc[:, ~(df.isna() | (df.astype(str).eq(''))).all(axis=0)]
    return df, header_idx, first_val, first_val_norm

# ========= Caricamento modelli dal PO (canonici) =========
def load_models_catalog(path_support: Path):
    """
    Usa SOLO il 1° sheet del file PO.
    Colonna cercata per pattern 'colonna modello'/'modello'/'model'... (case-insensitive, normalizzata).
    Ritorna:
      - known_norm: set di header normalizzati (modelli)
      - canon_by_norm: dict norm -> nome modello canonico
    """
    known_norm, canon_by_norm = set(), {}
    if not path_support.exists():
        print(f"[WARN] File PO non trovato: {path_support}")
        return known_norm, canon_by_norm

    df = pd.read_excel(path_support, sheet_name=0, engine='openpyxl')
    cols = list(df.columns)

    # 1) priorità 'colonna modello'
    col_model_idx = find_idx_by_patterns(cols, ['colonna modello', 'colonnamodello'], exact=False, prefer='pattern')
    # 2) fallback ragionevoli
    if col_model_idx is None:
        col_model_idx = find_idx_by_patterns(cols, ['modello','model','models','modelname','nomemodello','mod','mod.'], exact=False, prefer='pattern')
    if col_model_idx is None:
        # ultimissimo fallback: prima colonna testuale
        text_cols = [i for i, c in enumerate(cols) if df[c].dtype == object]
        col_model_idx = (text_cols[0] if text_cols else 0)

    col_model = cols[col_model_idx]
    for m in df[col_model].dropna().astype(str).str.strip().unique():
        n = normalize(m)
        if n and n not in known_norm:
            known_norm.add(n)
            canon_by_norm[n] = m

    print(f"[INFO] Modelli PO caricati: {len(known_norm)} (colonna: '{col_model}')")
    return known_norm, canon_by_norm

# ========= Individuazione colonne modello (GENERICO da header) =========
def detect_model_columns_idx(df, known_models_norm, canon_by_norm):
    """
    Seleziona SOLO le colonne i cui header normalizzati sono tra i modelli del PO.
    Ritorna lista di tuple (col_idx, col_name, modello_canonico).
    """
    hits = []
    for idx, c in enumerate(df.columns):
        n = normalize(c)
        if n in known_models_norm:
            hits.append((idx, c, canon_by_norm.get(n, c)))
    dbg("    -> Colonne modello trovate:", [h[1] for h in hits][:MAX_PRINT_MODELS])
    return hits

# ========= Riconoscimento HOMA =========
def looks_like_homa(supplier: str, cols) -> bool:
    """
    Heuristics: è HOMA se la cartella si chiama 'HOMA' O se esiste una colonna 'HOMA model'
    (normalize contiene 'homamodel').
    """
    if normalize(supplier) == 'homa':
        return True
    ncols = [normalize(c) for c in cols]
    return any('homamodel' in n for n in ncols)

# ========= Estrazione GENERICA (MIDEA/HISENSE) =========
def extract_rows_generic(df, supplier, source_file, known_models_norm, canon_by_norm):
    cols = list(df.columns)
    dbg("    [GENERIC] Colonne (raw):", cols)
    dbg("    [GENERIC] Colonne (norm):", [normalize(c) for c in cols])

    # Attributi
    code_idx = find_idx_by_patterns(cols, CODE_PATTERNS_PRIORITY, exact=False, prefer='pattern')
    if code_idx is None:
        code_idx = 0
        dbg("    [FALLBACK] 'codice' non trovato: uso colonna indice 0")

    desc_it_idx = find_idx_by_patterns(cols, DESC_ITA_PATTERNS, exact=False, prefer='column')
    part_en_idx = find_idx_by_patterns(cols, PART_EN_PATTERNS,   exact=False, prefer='column')
    stat_idx    = find_idx_by_patterns(cols, STAT_PATTERNS_EXACT, exact=True,  prefer='column')  # STAT esatto
    price_idx   = find_idx_by_patterns(cols, PRICE_PATTERNS,     exact=False,  prefer='column')  # prima disponibile

    def name_at(i): return f"{cols[i]} @ {i}" if i is not None else "None"
    print(f"    [ATTR] codice='{name_at(code_idx)}' | desc_ita='{name_at(desc_it_idx)}' | part_en='{name_at(part_en_idx)}' | stat='{name_at(stat_idx)}' | prezzo='{name_at(price_idx)}'")

    if SHOW_ROWS_PREVIEW:
        dbg("    Anteprima prime righe:")
        dbg(df.head(SHOW_ROWS_PREVIEW).to_string())

    # Colonne modello DA HEADER (match con PO)
    model_cols = detect_model_columns_idx(df, known_models_norm, canon_by_norm)
    if not model_cols:
        print("    [INFO] Nessuna colonna modello trovata (match con PO).")

    out_rows = []
    for _, r in df.iterrows():
        codice = r.iloc[code_idx] if code_idx is not None else None
        if pd.isna(codice) or str(codice).strip() == '':
            continue

        base = {
            'supplier': supplier,
            'source_file': source_file,
            'codice': str(codice).strip(),
            'descrizione_ita': (str(r.iloc[desc_it_idx]).strip() if desc_it_idx is not None and not pd.isna(r.iloc[desc_it_idx]) else ''),
            'part_name_en':   (str(r.iloc[part_en_idx]).strip() if part_en_idx is not None and not pd.isna(r.iloc[part_en_idx]) else ''),
            'stat':           (str(r.iloc[stat_idx]).strip() if stat_idx is not None and not pd.isna(r.iloc[stat_idx]) else ''),
            'prezzo':         (parse_price(r.iloc[price_idx]) if price_idx is not None else None),
        }

        for m_idx, _, m_canon in model_cols:
            qty = parse_model_qty(r.iloc[m_idx])
            if qty is not None and qty != 0:
                out_rows.append({**base, 'modello': m_canon, 'valore_modello': qty})

    dbg(f"    [GENERIC] Righe estratte (prima di agg.): {len(out_rows)}")
    if out_rows:
        df_tmp = pd.DataFrame(out_rows)
        keys = ['supplier','source_file','codice','descrizione_ita','part_name_en','stat','prezzo','modello']
        df_tmp = df_tmp.groupby(keys, as_index=False, dropna=False)['valore_modello'].sum()
        out_rows = df_tmp.to_dict(orient='records')
        dbg(f"    [GENERIC] Righe dopo aggregazione: {len(out_rows)}")

    return out_rows

# ========= Estrazione SPECIALE HOMA =========
def extract_rows_homa(df, supplier, source_file, known_models_norm, canon_by_norm):
    """
    Per HOMA:
      - modelli nei VALORI: 'HOMA model' + TUTTE le colonne che iniziano con 'model' o contengono 'oemmodel'
      - quantità: da 'Quantity' (o sinonimi QTY_PATTERNS)
      - PO-filter: se FILTER_HOMA_WITH_PO=True, tiene SOLO i modelli presenti nel PO (canonizzati)
    """
    cols = list(df.columns)
    dbg("    [HOMA] Colonne (raw):", cols)
    dbg("    [HOMA] Colonne (norm):", [normalize(c) for c in cols])

    # Attributi di base (INDICI per evitare ambiguità con nomi duplicati)
    code_idx = find_idx_by_patterns(cols, CODE_PATTERNS_PRIORITY, exact=False, prefer='pattern')
    if code_idx is None:
        code_idx = 0
        dbg("    [HOMA][FALLBACK] 'codice' non trovato: uso colonna indice 0")

    desc_it_idx = find_idx_by_patterns(cols, DESC_ITA_PATTERNS, exact=False, prefer='column')
    part_en_idx = find_idx_by_patterns(cols, PART_EN_PATTERNS,   exact=False, prefer='column')
    stat_idx    = find_idx_by_patterns(cols, STAT_PATTERNS_EXACT, exact=True,  prefer='column')
    price_idx   = find_idx_by_patterns(cols, PRICE_PATTERNS,     exact=False,  prefer='column')
    qty_idx     = find_idx_by_patterns(cols, QTY_PATTERNS,       exact=False,  prefer='pattern')

    # Colonne "fonte modello" (VALORI!)
    ncols = [normalize(c) for c in cols]
    model_value_cols = []
    for i, n in enumerate(ncols):
        if n.startswith('model') or 'oemmodel' in n or 'homamodel' in n:
            model_value_cols.append(i)

    def name_at(i): return f"{cols[i]} @ {i}" if i is not None else "None"
    print(f"    [HOMA][ATTR] codice='{name_at(code_idx)}' | desc_ita='{name_at(desc_it_idx)}' | part_en='{name_at(part_en_idx)}' | stat='{name_at(stat_idx)}' | prezzo='{name_at(price_idx)}' | qty='{name_at(qty_idx)}'")
    print(f"    [HOMA] colonne valore modello: {[cols[i] for i in model_value_cols][:MAX_PRINT_MODELS]}")
    if SHOW_ROWS_PREVIEW:
        dbg("    [HOMA] Anteprima prime righe:")
        dbg(df.head(SHOW_ROWS_PREVIEW).to_string())

    out_rows = []
    total_tokens, kept_tokens = 0, 0

    for _, r in df.iterrows():
        codice = r.iloc[code_idx] if code_idx is not None else None
        if pd.isna(codice) or str(codice).strip() == '':
            continue

        q = parse_model_qty(r.iloc[qty_idx]) if qty_idx is not None else None

        base = {
            'supplier': supplier,
            'source_file': source_file,
            'codice': str(codice).strip(),
            'descrizione_ita': (str(r.iloc[desc_it_idx]).strip() if desc_it_idx is not None and not pd.isna(r.iloc[desc_it_idx]) else ''),
            'part_name_en':   (str(r.iloc[part_en_idx]).strip() if part_en_idx is not None and not pd.isna(r.iloc[part_en_idx]) else ''),
            'stat':           (str(r.iloc[stat_idx]).strip() if stat_idx is not None and not pd.isna(r.iloc[stat_idx]) else ''),
            'prezzo':         (parse_price(r.iloc[price_idx]) if price_idx is not None else None),
            'quantita_riga':  q,
        }

        for i in model_value_cols:
            raw = r.iloc[i]
            if pd.isna(raw) or str(raw).strip() == '' or str(raw).strip() == '0':
                continue
            tokens = expand_model_string(str(raw).strip())
            total_tokens += len(tokens)

            for token in tokens:
                if FILTER_HOMA_WITH_PO:
                    n = normalize(token)
                    if n in known_models_norm:
                        kept_tokens += 1
                        out_rows.append({
                            **base,
                            'modello': canon_by_norm.get(n, token),  # canonico dal PO
                            'colonna_modello': cols[i]
                        })
                else:
                    kept_tokens += 1
                    out_rows.append({**base, 'modello': token, 'colonna_modello': cols[i]})

    print(f"    [HOMA] Token modello totali: {total_tokens} | tenuti (PO-match): {kept_tokens} | scartati: {total_tokens - kept_tokens}")
    return out_rows

# ========= Main =========
def process_anagrafiche(base_dir: Path, output_dir: Path, support_orders_path: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    known_models_norm, canon_by_norm = load_models_catalog(support_orders_path)

    ignore_names = {support_orders_path.name.lower()}
    for root, _, files in os.walk(base_dir):
        supplier = Path(root).name  # sottocartella fornitore
        xlsx_files = [f for f in files
                      if f.lower().endswith(('.xlsx', '.xls'))
                      and not f.startswith('~$')
                      and f.lower() not in ignore_names]
        if not xlsx_files:
            continue

        out_supplier_dir = output_dir / supplier if supplier else output_dir
        out_supplier_dir.mkdir(parents=True, exist_ok=True)

        for fname in xlsx_files:
            fpath = Path(root) / fname
            print(f"[RUN] {fpath}")
            try:
                # 1) Leggi 1° sheet, trova riga-header dalla prima colonna
                df, header_idx, first_val, first_val_norm = read_first_sheet_with_detected_header(fpath)
            except Exception as e:
                print(f"[ERROR] {fpath}: {e}")
                continue

            # 2) Scegli percorso: GENERIC vs HOMA
            try:
                if looks_like_homa(supplier, df.columns):
                    rows = extract_rows_homa(df, supplier, fname, known_models_norm, canon_by_norm)
                else:
                    rows = extract_rows_generic(df, supplier, fname, known_models_norm, canon_by_norm)
            except Exception as e:
                print(f"  [FAIL] Estrazione dati: {e}")
                continue

            # 3) Salva un file per input
            df_out = pd.DataFrame(rows)
            if not df_out.empty:
                # Ordine colonne robusto: includo solo quelle effettivamente presenti
                preferred_base    = ['supplier','source_file','codice','descrizione_ita','part_name_en','stat','prezzo','modello']
                preferred_generic = ['valore_modello']                 # solo GENERICO
                preferred_homa    = ['colonna_modello','quantita_riga']  # solo HOMA

                preferred_all = preferred_base + preferred_generic + preferred_homa
                present = [c for c in preferred_all if c in df_out.columns]
                other = [c for c in df_out.columns if c not in present]

                dbg("    [SAVE] colonne presenti (preferred):", present)
                dbg("    [SAVE] altre colonne:", other)

                df_out = df_out[present + other]

                out_name = f"{Path(fname).stem}__parsed.xlsx"
                out_path = out_supplier_dir / out_name
                with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
                    df_out.to_excel(writer, index=False, sheet_name='parsed')
                print(f"  [OK] Salvato: {out_path}  (righe: {len(df_out)})")
            else:
                print(f"  [INFO] Nessuna riga utile trovata in: {fpath}")

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent  # .../M&C/anagrafiche
    base_dir = script_dir                         # scansiona ./<FORNITORE>/
    output_dir = script_dir.parent / "_OUTPUT" / "anagrafiche"
    support_orders = script_dir / SUPPORT_FILE
    process_anagrafiche(base_dir=base_dir, output_dir=output_dir, support_orders_path=support_orders)
