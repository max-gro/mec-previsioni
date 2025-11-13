# -*- coding: utf-8 -*-
"""
Master pipeline:
1) Scandisce la cartella INPUT_DIR.
2) Per ogni PDF tenta l'estrazione con PyMuPDF (testo).
3) Se vuoto/fallito, tenta Vision LLM (immagini).
4) Salva incrementale in Excel (4 colonne) e checkpoint JSON.
"""

import sys
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

# Import locali (siamo in preprocessing_PO/)
CURR_DIR = Path(__file__).resolve().parent
if str(CURR_DIR) not in sys.path:
    sys.path.insert(0, str(CURR_DIR))

from config import (
    INPUT_DIR, SUCCESS_DIR, FAILED_DIR, FINAL_XLSX,
    CHECKPOINT_DIR, NUM_DOCS,
    DPI, IMG_FORMAT, OPENAI_MODEL, MAX_PAGES_PER_REQUEST,
    TEMPERATURE, MAX_OUTPUT_TOKENS,VERBOSE
)
from extractors import extract_pymupdf, extract_vision, append_4cols_xlsx
from extractors.utils import iter_pdfs, ensure_dir, save_checkpoint_json
from extractors.utils import log, preview_rows

def main():
    load_dotenv()

    ensure_dir(SUCCESS_DIR)
    ensure_dir(FAILED_DIR)
    ensure_dir(CHECKPOINT_DIR)
    ensure_dir(FINAL_XLSX.parent)

    pdfs = sorted(iter_pdfs(INPUT_DIR))
    if NUM_DOCS > 0:
        pdfs = pdfs[:NUM_DOCS]

    if not pdfs:
        print(f"Nessun PDF trovato in: {INPUT_DIR.resolve()}")
        return

    print(f"Documenti da processare: {len(pdfs)}")
    if VERBOSE:
        log(f"🚀 Avvio pipeline | docs={len(pdfs)} | verbose={VERBOSE}")


    client = OpenAI()  # legge OPENAI_API_KEY dall'ambiente

    all_rows_4cols: List[Dict] = []
    ok, ko = 0, 0

    for i, pdf in enumerate(pdfs, start=1):
        rel = pdf.relative_to(INPUT_DIR)
        print(f"[{i}/{len(pdfs)}] {rel}")

        if VERBOSE:
            log(f"▶️  Try PyMuPDF: {pdf.name}")

        # === 1) Tentativo PyMuPDF
        rows_p, meta_p = extract_pymupdf(pdf,verbose = VERBOSE)
        if VERBOSE:
            log(f"PyMuPDF result | rows={len(rows_p)} | notes={meta_p.get('notes', [])}")

        if not rows_p:
            if VERBOSE:
                log("↪️  Fallback a Vision-LLM (PyMuPDF non ha prodotto righe utili)")
        if rows_p:
            # preparo righe 4-colonne
            rows_4 = [{"file": r["file"], "data": r.get("order_date"), "modello": r["model"], "quantità": r["quantity"]} for r in rows_p]
            append_4cols_xlsx(FINAL_XLSX, rows_4)
            all_rows_4cols.extend(rows_4)
            ok += 1
            # checkpoint (facoltativo)
            save_checkpoint_json(CHECKPOINT_DIR, f"{pdf.name}__pymupdf", "", {"meta": meta_p, "rows": rows_p[:5]})
            continue

        # === 2) Fallback Vision LLM
        rows_v, meta_v = extract_vision(
            pdf_path=pdf,
            client=client,
            checkpoint_dir=CHECKPOINT_DIR,
            dpi=DPI,
            img_format=IMG_FORMAT,
            model_name=OPENAI_MODEL,
            max_pages_per_request=MAX_PAGES_PER_REQUEST,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            verbose=VERBOSE
        )
        if VERBOSE:
            log(f"Vision result | rows={len(rows_v)} | notes={meta_v.get('notes', [])}")
            if rows_v:
                log("Vision preview:\n" + preview_rows(rows_v, n=5))

        if rows_v:
            rows_4 = [{"file": r["file"], "data": r.get("order_date"), "modello": r["model"], "quantità": r["quantity"]} for r in rows_v]
            append_4cols_xlsx(FINAL_XLSX, rows_4)
            all_rows_4cols.extend(rows_4)
            ok += 1
            save_checkpoint_json(CHECKPOINT_DIR, f"{pdf.name}__vision_summary", "", {"meta": meta_v, "rows": rows_v[:5]})
        else:
            ko += 1
            save_checkpoint_json(CHECKPOINT_DIR, f"{pdf.name}__failed", "", {"meta": meta_v, "meta_vision": meta_v, "reason": "no rows"})
        chosen = rows_p if rows_p else rows_v
        if VERBOSE:
            src = "PyMuPDF" if rows_p else "Vision-LLM"
            log(f"📦 Scelgo {src} | rows={len(chosen)} → append all_rows")

    # Riepilogo finale anche in un unico Excel ricalcolato (opzionale)
    print("\n=== RIEPILOGO ===")
    print(f"Riusciti: {ok} | Falliti: {ko}")
    print(f"Excel incrementale: {FINAL_XLSX}")

    # opzionale: riscrivo un foglio unico dal buffer in memoria
    try:
        df = pd.DataFrame(all_rows_4cols, columns=["file", "data", "modello", "quantità"])
        if not df.empty:
            # scrivo in un file shadow accanto a quello incrementale
            shadow = FINAL_XLSX.with_name(FINAL_XLSX.stem + "_shadow.xlsx")
            df.to_excel(shadow, index=False)
            print(f"Excel omogeneo di riepilogo: {shadow}")
    except Exception as e:
        print(f"(warning) impossibile scrivere il riepilogo shadow: {e}")

if __name__ == "__main__":
    main()
