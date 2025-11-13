# -*- coding: utf-8 -*-
"""
Pacchetto 'extractors': espone un'interfaccia uniforme verso i due estrattori.

Entrambi espongono:
    extract(pdf_path: pathlib.Path, ...) -> (rows: List[dict], meta: dict)

Dove rows è una lista di dict:
    {"file": str, "order_date": Optional[str], "model": str, "quantity": int}
"""

from .pymupdf_extractor import extract as extract_pymupdf
from .vision_llm_extractor import extract as extract_vision
from .utils import append_4cols_xlsx  # utile nei pipeline

__all__ = [
    "extract_pymupdf",
    "extract_vision",
    "append_4cols_xlsx",
]
