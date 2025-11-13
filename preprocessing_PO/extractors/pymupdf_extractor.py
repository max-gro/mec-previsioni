# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import unicodedata  # NEW: per rimuovere accenti dagli header

import pandas as pd
import pymupdf4llm as pdf4llm
from dateutil import parser as dateutil_parser

from .utils import log, preview_rows

# ---------------------------
# Config locali a questo modulo
# ---------------------------
PRIMARY_TABLE_STRATEGY = "lines_strict"
FALLBACK_TABLE_STRATEGY = "lines"

# ---------------------------
# 1) Date parsing
# ---------------------------
DATE_PATTERNS = [
    r"Date[:\s]*([0-9]{4}[./-][0-9]{2}[./-][0-9]{2})",
    r"Date[:\s]*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
    r"\b([0-9]{4}[./-][0-9]{2}[./-][0-9]{2})\b",
    r"\b([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})\b",
    r"\b([0-9]{1,2}\s*[- ]\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*[- ]\s*[0-9]{4})\b",
    r"\b([0-9]{1,2}\s*[- ]\s*(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s*[- ]\s*[0-9]{4})\b",
]

def parse_date_str(s: str) -> Optional[pd.Timestamp]:
    s = (s or "").strip().replace("–", "-")
    try:
        dt = dateutil_parser.parse(s, dayfirst=False, fuzzy=True)
        return pd.Timestamp(dt.date())
    except Exception:
        try:
            dt = dateutil_parser.parse(s, dayfirst=True, fuzzy=True)
            return pd.Timestamp(dt.date())
        except Exception:
            return None

def extract_order_date_from_text(text: str) -> Optional[str]:
    for pat in DATE_PATTERNS[:2]:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            dt = parse_date_str(m.group(1))
            if dt:
                return dt.strftime("%Y-%m-%d")
    for pat in DATE_PATTERNS[2:]:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            dt = parse_date_str(m.group(1))
            if dt:
                return dt.strftime("%Y-%m-%d")
    return None

# ---------------------------
# 2) Markdown table helpers
# ---------------------------
MD_SEP_RE = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")

def iter_markdown_table_blocks(md_text: str):
    lines = md_text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        if lines[i].lstrip().startswith("|"):
            block = [lines[i]]
            i += 1
            while i < n and lines[i].lstrip().startswith("|"):
                block.append(lines[i]); i += 1
            if len(block) >= 3 and MD_SEP_RE.match(block[1].strip()):
                yield block
            continue
        i += 1

# NEW: helper per rimuovere accenti
def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def normalize_header(h: str) -> str:
    # MOD: normalizzazione più robusta (accenti, punteggiatura, spazi)
    h = (h or "").strip()
    h = _strip_accents(h)  # NEW
    h = re.sub(r"[\s\.\-_]+", " ", h)
    return h.lower().strip()

def canonical_colname(h: str) -> str:
    """
    Mappa header -> nome canonico robusto.
    - quantity: qty, q.ty, q.tà, qta, qte, quantità, qtà, pcs, pz, pieces, units, ordered qty, etc.
    - model: model, model no, oem model, factory model, sku, product code, item code, part no, codice, articolo, etc.
    """
    n = normalize_header(h)

    # quantity (molti sinonimi)
    if re.search(
        r"\b("
        r"q\s*\.?\s*t\s*\.?\s*y|"      # q.ty / qty / q t y
        r"q\s*\.?\s*t\s*\.?\s*a|"      # q.ta (acc. rimossi)
        r"qta|qta\.?|quantita|qty|qte|qte\.|" 
        r"pcs|pz|pieces|unit|units?|uom|"
        r"ordered\s*qty|qty\s*ordered|order\s*qty"
        r")\b",
        n, flags=re.IGNORECASE
    ):
        return "quantity"

    # model (e sinonimi forti)
    if re.search(
        r"\b("
        r"oem\s*model|model\s*no|factory\s*model|model|"
        r"sku|product\s*code|item\s*code|item\s*no|part\s*no|pn|codice|cod|articolo|art"
        r")\b",
        n, flags=re.IGNORECASE
    ):
        return "model"

    # fallback utili
    if re.search(r"\bitem\b", n):
        return "item"
    if re.search(r"\bbrand\b", n):
        return "brand"
    if re.search(r"\bean\b", n):
        return "ean"
    if re.search(r"\bamount|price|unit\s*price|total\b", n):
        return n

    return n

def md_table_to_df(block_lines: List[str]) -> Optional[pd.DataFrame]:
    def split_row(row: str) -> List[str]:
        row = row.strip()
        if row.startswith("|"): row = row[1:]
        if row.endswith("|"): row = row[:-1]
        return [c.strip() for c in row.split("|")]

    if len(block_lines) < 3:
        return None

    header = split_row(block_lines[0])
    body_lines = block_lines[2:]
    rows = [split_row(r) for r in body_lines]
    width = max(len(header), max((len(r) for r in rows), default=0))
    header = (header + [""] * (width - len(header)))[:width]
    fixed = [(r + [""] * (width - len(r)))[:width] for r in rows]

    df = pd.DataFrame(fixed, columns=header)

    # MOD: canonicalizzazione + gestione duplicati
    canon = [canonical_colname(c) for c in df.columns]
    seen, final_cols = {}, []
    for c in canon:
        idx = seen.get(c, 0)
        final_cols.append(f"{c}__{idx+1}" if idx else c)
        seen[c] = idx + 1
    df.columns = final_cols
    return df

# ---------------------------
# 2bis) Normalizzazioni robuste
# ---------------------------
_QTY_TOKEN = re.compile(r"\b\d{1,6}\b")  # quantità plausibili

def clean_quantity(val) -> Optional[int]:
    """
    Estrae una quantità plausibile da una cella:
    - cerca token numerici (1..6 cifre)
    - prende l'ultimo token (spesso è la qty)
    - ritorna None se non valido (range 1..2_000_000)
    """
    if val is None:
        return None
    s = str(val)
    toks = _QTY_TOKEN.findall(s.replace(" ", ""))
    if not toks:
        return None
    try:
        q = int(toks[-1])
    except Exception:
        return None
    if 1 <= q <= 2_000_000:
        return q
    return None

# token “codice modello” (lettere+numeri, almeno 4, con -_/ possibile)
_MODEL_TOKEN = re.compile(r"\b[A-Z0-9]{2,}[A-Z0-9\-_\/]{2,}\b", re.IGNORECASE)

def best_model_token(s: str) -> str:
    """
    Cerca il token più "codice" nella cella del modello.
    Se non trova nulla, ritorna la stringa ripulita da <br>, spazi ridotti.
    """
    s = (s or "").replace("<br>", " ").replace("\n", " ")
    cand = _MODEL_TOKEN.findall(s)
    if not cand:
        return re.sub(r"\s+", " ", s).strip()
    # preferisci token misti (lettere+numeri), poi i più lunghi
    def score(tok: str) -> tuple:
        has_alpha = bool(re.search(r"[A-Za-z]", tok))
        has_digit = bool(re.search(r"\d", tok))
        return (has_alpha and has_digit, len(tok))
    return sorted(cand, key=score, reverse=True)[0]

# NEW: selezione colonne candidate (più robusta)
def _candidate_model_columns(columns: List[str]) -> List[str]:
    """
    Ritorna lista ordinata di colonne plausibili per il MODEL:
    - priorità a 'model*'
    - poi 'item*'
    - poi intestazioni contenenti 'code' (product code / item code / part no)
    """
    cols = []
    cols += [c for c in columns if c.startswith("model")]
    cols += [c for c in columns if c.startswith("item")]
    cols += [c for c in columns if "code" in c]  # 'product code', 'item code', 'part no', etc.
    # de-duplica preservando ordine
    out, seen = [], set()
    for c in cols:
        if c not in seen:
            out.append(c); seen.add(c)
    return out

def _candidate_qty_columns(columns: List[str]) -> List[str]:
    """
    Ritorna lista di colonne plausibili per la QUANTITY:
    - tutte quelle canonicalizzate in 'quantity' (con eventuali __n)
    """
    return [c for c in columns if c.startswith("quantity")]

def extract_lines_from_df(df: pd.DataFrame) -> Tuple[List[Dict], Dict]:
    """
    Estrae le coppie (model, quantity) da una tabella DataFrame.
    Sceglie automaticamente la COPPIA (model_col, qty_col) che produce più righe valide.
    Ritorna (rows, debug_meta) per logging.
    """
    model_candidates = _candidate_model_columns(list(df.columns))  # NEW
    qty_candidates   = _candidate_qty_columns(list(df.columns))    # NEW

    debug = {
        "model_candidates": model_candidates,
        "qty_candidates": qty_candidates,
        "best_pair": None,
        "best_valid": 0
    }

    if not model_candidates or not qty_candidates:
        return [], debug

    best_rows: List[Dict] = []
    best_pair = (None, None)
    best_valid = 0

    # NEW: prova tutte le combinazioni e scegli la migliore
    for mcol in model_candidates:
        for qcol in qty_candidates:
            tmp_rows: List[Dict] = []
            valid = 0
            for _, row in df.iterrows():
                model_raw = str(row.get(mcol, "")).strip()
                qty_val   = clean_quantity(row.get(qcol))
                model     = best_model_token(model_raw)
                if model and qty_val is not None:
                    tmp_rows.append({"model": model, "quantity": qty_val})
                    valid += 1
            if valid > best_valid:
                best_valid = valid
                best_rows = tmp_rows
                best_pair = (mcol, qcol)

    debug["best_pair"] = best_pair
    debug["best_valid"] = best_valid
    return best_rows, debug

# ---------------------------
# 3) Lettura markdown con PyMuPDF4LLM
# ---------------------------
def read_md_pages(pdf_path: Path, strategy: str) -> List[Dict]:
    return pdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        table_strategy=strategy,
        ignore_images=True,
        show_progress=False,
    )

def extract_from_pages(pdf_path: Path, pages: List[Dict]) -> Tuple[List[Dict], str]:
    results: List[Dict] = []
    if not pages:
        return [], "File PDF illeggibile o vuoto."

    first_page_text = pages[0].get("text", "")
    order_date = extract_order_date_from_text(first_page_text)

    found_md_tables = False
    all_reasons: List[str] = []

    for pg in pages:
        md_text = pg.get("text", "")
        table_blocks = list(iter_markdown_table_blocks(md_text))
        if not table_blocks:
            continue
        found_md_tables = True

        for block in table_blocks:
            df = md_table_to_df(block)
            if df is None or df.empty:
                continue

            # NEW: usa estrattore con ricerca "miglior coppia" model/qty
            lines, dbg = extract_lines_from_df(df)

            if not dbg.get("model_candidates"):
                all_reasons.append("colonna 'model' non trovata")
            if not dbg.get("qty_candidates"):
                all_reasons.append("colonna 'quantity' non trovata")

            if not lines:
                # MOD: motivazione più informativa se non ha prodotto righe
                mc = dbg.get("model_candidates") or []
                qc = dbg.get("qty_candidates") or []
                bp = dbg.get("best_pair")
                all_reasons.append(
                    f"nessuna riga valida (model_cand={mc}, qty_cand={qc}, best_pair={bp})"
                )
                continue

            for ln in lines:
                results.append({
                    "file": pdf_path.name,
                    "order_date": order_date,
                    **ln
                })

    if results:
        return results, "Successo"

    if not found_md_tables:
        if not first_page_text.strip():
            return [], "Nessun testo estratto dal PDF."
        return [], "Nessun blocco tabella in formato Markdown trovato nel documento."

    if all_reasons:
        return [], "Trovate tabelle Markdown, ma problemi: " + "; ".join(sorted(set(all_reasons)))

    return [], "Motivo sconosciuto"

def extract_orders_from_pdf(pdf_path: Path) -> Tuple[List[Dict], str]:
    pages = read_md_pages(pdf_path, PRIMARY_TABLE_STRATEGY)
    rows, reason = extract_from_pages(pdf_path, pages)
    if rows:
        return rows, reason

    # fallback
    pages_fb = read_md_pages(pdf_path, FALLBACK_TABLE_STRATEGY)
    rows, reason_fb = extract_from_pages(pdf_path, pages_fb)
    if rows:
        return rows, reason_fb

    return [], f"Primaria: ({reason}). Fallback: ({reason_fb})."

# ---------- INTERFACCIA UNIFICATA ----------
def extract(pdf_path: Path, verbose: bool = False) -> Tuple[List[Dict], Dict]:
    """
    Wrapper conforme all'interfaccia del pacchetto.
    - Chiama extract_orders_from_pdf (che prova primaria + fallback)
    - Arricchisce meta con engine/notes/status/rows_count
    - Log "parlanti" se verbose=True
    Ritorna (rows, meta)
    """
    if verbose:
        log(f"📄 PyMuPDF | start | file={pdf_path.name}")

    rows, reason = extract_orders_from_pdf(pdf_path)

    meta: Dict = {
        "engine": "pymupdf4llm",
        "reason": reason,                          # stringa aggregata
        "notes": [reason] if reason else [],
        "rows_count": len(rows),
        "status": "ok" if rows else "empty",
    }

    if verbose:
        if rows:
            log(f"  ✓ PyMuPDF OK | rows={len(rows)}")
            log("  preview:\n" + preview_rows(rows, n=5))
        else:
            log(f"  ✗ PyMuPDF EMPTY | reason={reason}")

    return rows, meta
