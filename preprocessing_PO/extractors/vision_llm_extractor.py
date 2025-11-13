# -*- coding: utf-8 -*-
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

from pdf2image import convert_from_path
from PIL import Image
from openai import OpenAI

from .utils import (
    encode_png_base64,
    extract_text_from_response,
    safe_find_json_block,
    save_checkpoint_json,
    atomic_write_text,
    sanitize_for_name,
    log,
    preview_rows,
)

SYSTEM_INSTRUCTIONS = """
Sei un motore di estrazione per Ordini d'Acquisto (PO).
Ti fornisco le pagine di un PDF come immagini.
Devi restituire SOLO JSON valido con lo schema:

{
  "order_date": "YYYY-MM-DD" | null,
  "lines": [
    {"model": "<string>", "quantity": <int>},
    ...
  ],
  "diagnostics": {
    "notes": ["..."],
    "pages": <int>
  }
}

Regole:
- L'output deve contenere **soltanto** un singolo oggetto JSON (nessun testo fuori dal JSON, nessun commento).
- La 'order_date' è unica per documento (tipicamente all'inizio della prima pagina). Se non certa, usa null.
- 'quantity' è un intero; rimuovi punti migliaia, spazi e simboli (es: "1.350" -> 1350).
- Includi solo righe di dettaglio (no totali, no righe vuote).
"""

STRICT_JSON_INSTRUCTIONS = """
IMPORTANTISSIMO: Rispondi **ESCLUSIVAMENTE** con un unico oggetto JSON che rispetti lo schema richiesto.
Non includere alcuna spiegazione, nessun testo fuori dal JSON, nessun codice fence. Inizia con '{' e termina con '}'.
Se non trovi tabelle o dati, rispondi comunque con:
{"order_date": null, "lines": [], "diagnostics": {"notes": ["no_data"], "pages": <NUM_PAGINE>}}
"""

def _build_prompt(file_rel: str, page_indices: List[int], ctx_compact: str = "") -> str:
    ctx = ctx_compact or "(nessuno)"
    return (
        f"FILE: {file_rel}\n"
        f"Pagine incluse (zero-based): {page_indices}\n"
        f"Contesto finora: {ctx}\n"
        f"Istruzioni: estrai la data d'ordine unica e le coppie (model, quantity)."
    )

def _page_images(pdf_path: Path, dpi: int, img_format: str) -> List[Image.Image]:
    return convert_from_path(pdf_path.as_posix(), dpi=dpi, fmt=img_format)

def _call_openai(client: OpenAI, model: str, content: List[Dict], temperature: float, max_output_tokens: int):
    return client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

def _raw_checkpoint(checkpoint_dir: Path, pdf_name: str, batch_id: int, attempt: int, raw_text: str) -> None:
    base = sanitize_for_name(pdf_name)
    out_txt = checkpoint_dir / f"{base}__batch{batch_id:03d}__raw_attempt{attempt}.txt"
    atomic_write_text(out_txt, raw_text, encoding="utf-8")

def _parse_or_fallback(raw: str, pages_count: int) -> Dict:
    try:
        json_str = safe_find_json_block(raw)
        return json.loads(json_str)
    except Exception:
        return {
            "order_date": None,
            "lines": [],
            "diagnostics": {"notes": ["no_json_block"], "pages": pages_count},
        }

# --------- Normalizzazioni robuste in post-processing ---------
_QTY_TOKEN = re.compile(r"\b\d{1,6}\b")
def _parse_quantity(val) -> int | None:
    if val is None:
        return None
    s = str(val)
    toks = _QTY_TOKEN.findall(s)
    if not toks:
        return None
    try:
        q = int(toks[-1])
    except Exception:
        return None
    return q if 1 <= q <= 2_000_000 else None

_MODEL_TOKEN = re.compile(r"\b[A-Z0-9]{2,}[A-Z0-9\-_\/]{2,}\b", re.IGNORECASE)
def _best_model_token(s: str) -> str:
    s = (s or "").replace("<br>", " ").replace("\n", " ")
    cand = _MODEL_TOKEN.findall(s)
    if not cand:
        return re.sub(r"\s+", " ", s).strip()
    def score(tok: str) -> tuple:
        has_alpha = bool(re.search(r"[A-Za-z]", tok))
        has_digit = bool(re.search(r"\d", tok))
        return (has_alpha and has_digit, len(tok))
    return sorted(cand, key=score, reverse=True)[0]

def extract(
    pdf_path: Path,
    client: OpenAI,
    checkpoint_dir: Path,
    *,
    dpi: int,
    img_format: str,
    model_name: str,
    max_pages_per_request: int,
    temperature: float,
    max_output_tokens: int,
    retry_if_no_json: int = 1,
    verbose: bool = False,
) -> Tuple[List[Dict], Dict]:
    """
    Estrae (file, order_date, model, quantity) via Vision LLM.
    Salva JSON di checkpoint per batch e i RAW delle risposte.
    Non solleva eccezioni in caso di risposta non-JSON: ritorna lines=[] e annota la causa.
    """
    pages = _page_images(pdf_path, dpi, img_format)
    if not pages:
        return [], {"engine": "vision_llm", "pages": 0, "notes": ["no_pages"]}

    page_indices = list(range(len(pages)))
    context_json: Dict = {}
    all_rows: List[Dict] = []
    diag_notes: List[str] = []
    if verbose:
        log(f"🧠 Vision-LLM | {pdf_path.name} | pages={len(pages)} dpi={dpi} fmt={img_format}")

    for b_start in range(0, len(pages), max_pages_per_request):
        batch_id      = (b_start // max_pages_per_request) + 1
        batch_indices = page_indices[b_start:b_start + max_pages_per_request]

        content = [
            {"type": "input_text", "text": SYSTEM_INSTRUCTIONS.strip()},
            {"type": "input_text", "text": _build_prompt(pdf_path.name, batch_indices, json.dumps(context_json, ensure_ascii=False)[:3000])},
        ]
        for idx in batch_indices:
            b64 = encode_png_base64(pages[idx])
            content.append({"type": "input_image", "image_url": b64})

        if verbose:
            log(f"  ▸ Batch {batch_id} pages={batch_indices} | ctx_models={len(context_json.get('models_so_far', []))}")

        # ===== Attempt #1 =====
        t0 = time.time()
        resp1 = _call_openai(client, model_name, content, temperature, max_output_tokens)
        raw1  = extract_text_from_response(resp1).strip()
        _raw_checkpoint(checkpoint_dir, pdf_path.name, batch_id, 1, raw1)
        data = _parse_or_fallback(raw1, pages_count=len(pages))
        if verbose:
            log(f"    ↳ attempt#1 raw_len={len(raw1)} | notes={data.get('diagnostics',{}).get('notes', [])}")

        # ===== Retry se no_json_block =====
        attempts_left = retry_if_no_json
        attempt_no = 2
        while attempts_left > 0 and not data.get("lines") and "no_json_block" in (data.get("diagnostics", {}).get("notes") or []):
            strict_content = [
                {"type": "input_text", "text": STRICT_JSON_INSTRUCTIONS.strip()},
                {"type": "input_text", "text": _build_prompt(pdf_path.name, batch_indices, json.dumps(context_json, ensure_ascii=False)[:3000])},
            ]
            for idx in batch_indices:
                strict_content.append({"type": "input_image", "image_url": encode_png_base64(pages[idx])})

            resp2 = _call_openai(client, model_name, strict_content, temperature, max_output_tokens)
            raw2  = extract_text_from_response(resp2).strip()
            _raw_checkpoint(checkpoint_dir, pdf_path.name, batch_id, attempt_no, raw2)
            data  = _parse_or_fallback(raw2, pages_count=len(pages))
            if verbose:
                log(f"    ↳ retry strict#{attempt_no} raw_len={len(raw2)} | notes={data.get('diagnostics',{}).get('notes', [])}")

            attempts_left -= 1
            attempt_no    += 1

        # checkpoint JSON per-batch (sempre)
        save_checkpoint_json(checkpoint_dir, f"{pdf_path.name}__batch{batch_id:03d}", "", data)

        order_date = data.get("order_date")
        lines = data.get("lines") or []
        before = len(all_rows)

        for ln in lines:
            model = _best_model_token(str(ln.get("model", "")).strip())
            qty   = _parse_quantity(ln.get("quantity"))
            if not model or qty is None:
                continue
            all_rows.append({
                "file": pdf_path.name,
                "order_date": order_date,
                "model": model,
                "quantity": qty,
            })

        added = len(all_rows) - before
        if verbose:
            log(f"    ✓ batch{batch_id} lines_added={added} | total_lines={len(all_rows)}")
            if added:
                log("      preview:\n" + preview_rows(all_rows[before:before+5], n=5))

        elapsed = round(time.time() - t0, 2)
        notes   = data.get("diagnostics", {}).get("notes") or []
        diag_notes.extend([f"batch{batch_id}:{n}" for n in notes])
        context_json = {
            "order_date": order_date,
            "models_so_far": [r["model"] for r in all_rows][-1000:],
            "count_lines": len(all_rows),
            "elapsed_batch_s": elapsed,
        }

    meta = {
        "engine": "vision_llm",
        "pages": len(pages),
        "notes": sorted(set(diag_notes)) if diag_notes else [],
    }
    if verbose:
        log(f"✅ Vision-LLM DONE | {pdf_path.name} | rows={len(all_rows)} | notes={meta.get('notes', [])}")

    return all_rows, meta
