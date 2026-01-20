# app/services/pdf_text.py
from __future__ import annotations

from typing import Optional


try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None


def extract_text_with_pdfplumber(pdf_bytes: bytes) -> str:
    """
    Extrai texto de PDF usando pdfplumber quando disponível.
    Se pdfplumber não estiver instalado, levanta erro claro (mas não quebra o boot da API).
    """
    if pdfplumber is None:
        raise RuntimeError(
            "pdfplumber não está instalado. Instale com: pip install pdfplumber "
            "ou desabilite o fluxo de PDF/OCR para este ambiente."
        )

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:  # noqa: F821 (io import abaixo)
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)

    return "\n".join(text_parts)


# Import local para evitar dependency no boot se não usar a função
import io
