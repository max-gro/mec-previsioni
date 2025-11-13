# -*- coding: utf-8 -*-
import os
from pathlib import Path

# Cartella di questo modulo (preprocessing_PO/)
BASE_DIR = Path(__file__).resolve().parent

# === I/O di base ===
INPUT_DIR   = Path(os.getenv("PDF_INPUT_DIR", BASE_DIR / "PO"))
SUCCESS_DIR = Path(os.getenv("PDF_SUCCESS_DIR", BASE_DIR / "_PDF_RIUSCITI"))
FAILED_DIR  = Path(os.getenv("PDF_FAILED_DIR",  BASE_DIR / "_PDF_FALLITI"))

# Excel finale (4 colonne: file, data, modello, quantità)
FINAL_XLSX  = Path(os.getenv("FINAL_XLSX", BASE_DIR.parent / "orders_model_quantity_FINAL.xlsx"))

# Limite documenti da processare (0 = tutti)
NUM_DOCS = int(os.getenv("NUM_DOCS", "0"))

# Checkpoints (salvataggi incrementali & log)
CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", BASE_DIR / "checkpoints_second_attempt"))

# === Parametri Vision LLM ===
DPI                   = int(os.getenv("DPI", "240"))
IMG_FORMAT            = os.getenv("IMG_FORMAT", "PNG").upper()  # "PNG" consigliato
OPENAI_MODEL          = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_PAGES_PER_REQUEST = int(os.getenv("MAX_PAGES_PER_REQUEST", "6"))
TEMPERATURE           = float(os.getenv("TEMPERATURE", "0"))
MAX_OUTPUT_TOKENS     = int(os.getenv("MAX_OUTPUT_TOKENS", "2000"))

# === Logging / Verbosity ===
VERBOSE = os.getenv("VERBOSE", "1").strip() not in ("0", "false", "False", "")
