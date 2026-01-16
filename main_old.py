"""
Document Processor API (MVP)
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Optional, Tuple

import fitz  # pymupdf
import pdfplumber
import pytesseract
from fastapi import FastAPI, Request
from PIL import Image
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

logger = logging.getLogger("doc_api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ------------------------------------------------------------------------------
# FastAPI
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Document Processor API (MVP)",
    version="0.2.2",
)

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])


class RawPdfAckResponse(BaseModel):
    received: bool
    source: str
    filename: str
    content_type: str
    bytes: int
    sha256: str


class ErrorResponse(BaseModel):
    received: bool = False
    filename: str
    bytes: int
    sha256: str
    error: str
    hint: Optional[str] = None
    head_ascii: Optional[str] = None
    head_hex: Optional[str] = None


# ------------------------------------------------------------------------------
# Helpers gerais
# ------------------------------------------------------------------------------

PDF_MAGIC = b"%PDF-"


@dataclass(frozen=True)
class PayloadInfo:
    filename: str
    content_type: str
    raw_bytes: bytes

    @property
    def size(self) -> int:
        return len(self.raw_bytes)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()


def normalize_pdf_payload(raw: bytes) -> Tuple[bytes, str, bool, str]:
    if raw.startswith(PDF_MAGIC):
        return raw, "none", True, raw[:8].decode("latin1", errors="replace")

    idx = raw.find(PDF_MAGIC)
    if idx != -1:
        header = raw[idx : idx + 8].decode("latin1", errors="replace")
        return raw[idx:], "cut_to_pdf_header", True, header

    return raw, "none", False, ""


def extract_text_with_pdfplumber(pdf_bytes: bytes) -> Tuple[int, str]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = len(pdf.pages)
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return pages, text.strip()


# ------------------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------------------


def configure_tesseract() -> None:
    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def ocr_pdf_with_tesseract(
    pdf_bytes: bytes,
    lang: str = "por+eng",
    config: str = "--oem 3 --psm 6",
    only_first_page: bool = False,
    crop_rect: Optional[Tuple[float, float, float, float]] = None,
) -> Tuple[int, str]:
    """
    OCR com Tesseract.

    Args:
        pdf_bytes: PDF em bytes.
        lang: idiomas do Tesseract (ex.: "por+eng").
        config: parâmetros do Tesseract (ex.: "--oem 3 --psm 6").
        only_first_page: se True, processa apenas a primeira página.
        crop_rect: (x0, y0, x1, y1) em coordenadas do PDF (points).
                   Use para recortar uma região específica (ex.: box do topo).

    Returns:
        (qtd_paginas_processadas, texto)
    """
    configure_tesseract()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        texts: list[str] = []
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)

        pages_iter = [doc.load_page(0)] if only_first_page else list(doc)

        for page in pages_iter:
            if crop_rect:
                pix = page.get_pixmap(matrix=mat, clip=fitz.Rect(*crop_rect))
            else:
                pix = page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texts.append(pytesseract.image_to_string(img, lang=lang, config=config))

        return len(texts), "\n".join(texts).strip()
    finally:
        doc.close()


# ------------------------------------------------------------------------------
# Helpers NFSe
# ------------------------------------------------------------------------------


def parse_money(val: Optional[str]) -> Optional[float]:
    if not val:
        return None

    s = (
        val.strip()
        .replace("R$", "")
        .replace("\u00a0", " ")
        .replace(" ", "")
    )

    # mantém só dígitos e separadores
    s = re.sub(r"[^0-9,\.]", "", s)
    if not s:
        return None

    # Se tiver múltiplas vírgulas (ex: 3,150,00), trata como milhares + decimal
    if s.count(",") > 1 and "." not in s:
        last = s.rfind(",")
        s = s[:last].replace(",", "") + "." + s[last + 1 :]
    # Se tiver múltiplos pontos (ex: 3.150.00), trata como milhares + decimal (raro)
    elif s.count(".") > 1 and "," not in s:
        last = s.rfind(".")
        s = s[:last].replace(".", "") + "." + s[last + 1 :]
    else:
        # Decide decimal pelo último separador
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "")
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        value = float(s)
    except ValueError:
        return None

    return value if value > 0 else None


def extract_valor_total(source_text: str) -> Optional[float]:
    """
    Extrai valor após a âncora 'VALOR TOTAL DA NOTA' (tolerante a OCR):
    - aceita espaço entre separador e centavos: 3.150, 00
    - aceita ruído e variações: R$3.150,00 | R$ 3150,00 | 3150.00
    """
    # normaliza espaços (mas preserva números)
    text = re.sub(r"\s+", " ", source_text)

    anchor = re.search(r"VALOR\s+TOTAL\s+DA\s+NOTA", text, re.IGNORECASE)
    if not anchor:
        return None

    window = text[anchor.end() : anchor.end() + 260]

    m = re.search(
        r"R?\$?\s*"
        r"([0-9]{1,3}(?:[.\s][0-9]{3})*|[0-9]{1,7})"
        r"(?:[,\.]\s*([0-9]{2}))",
        window,
    )
    if not m:
        return None

    # junta inteiro + centavos capturados, ignorando espaços no meio
    integral = re.sub(r"\s+", "", m.group(1))
    cents = m.group(2)
    return parse_money(f"{integral},{cents}")



def find_regex(pattern: str, source_text: str) -> Optional[str]:
    m = re.search(pattern, source_text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def extract_numero_nota(source_text: str) -> Optional[str]:
    """
    Pega o número da nota ancorando em 'Número da Nota' e capturando dígitos logo após,
    tolerando quebra de linha e OCR.
    """
    text = re.sub(r"\s+", " ", source_text)

    anchor = re.search(r"(?:N[uú]mero|Numero)\s+da\s+Nota", text, re.IGNORECASE)
    if not anchor:
        return None

    window = text[anchor.end() : anchor.end() + 120]

    # Captura o primeiro bloco de 3+ dígitos após o rótulo (normalmente 00000091 etc.)
    m = re.search(r"[:=]?\s*([0-9]{3,})\b", window)
    if not m:
        return None

    return m.group(1).strip()


def extract_nfse_fields(source_text: str) -> dict:
    # Número da Nota: tenta regex direto, senão usa âncora com janela
    numero_nota = find_regex(
        r"(?:N[uú]mero|Numero)\s+da\s+Nota\s*[:=]?\s*([0-9]{3,})",
        source_text,
    )
    if not numero_nota:
        numero_nota = extract_numero_nota(source_text)

    # Data e Hora de Emissão
    data_emissao = find_regex(
        r"Data\s+e\s+Hora\s+de\s+Emiss[aã]o\s*[:=]?\s*"
        r"([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}:[0-9]{2})?)",
        source_text,
    ) or find_regex(
        r"Data\s+.*Emiss[aã]o\s*[:=]?\s*"
        r"([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}:[0-9]{2})?)",
        source_text,
    )

    # CNPJ Prestador (Fornecedor)
    cnpj_fornecedor = find_regex(
        r"(?:CPF/CNPJ|CNPJ)\s*[:=]?\s*"
        r"([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})",
        source_text,
    ) or find_regex(
        r"\b([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})\b",
        source_text,
    )

    # Competência
    competencia = find_regex(
        r"COMPET[EÊ]NCIA\s*[:=]?\s*([0-9]{2}/[0-9]{4})",
        source_text,
    ) or find_regex(
        r"COMPETENCIA\s*[:=]?\s*([0-9]{2}/[0-9]{4})",
        source_text,
    )

    # Valor total
    valor_total_raw = find_regex(
        r"VALOR\s+TOTAL\s+DA\s+NOTA\s*[:=]?\s*R?\$?\s*"
        r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})",
        source_text,
    ) or find_regex(
        r"Valor\s+Total\s+da\s+Nota\s*[:=]?\s*R?\$?\s*"
        r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})",
        source_text,
    )

    valor_total = parse_money(valor_total_raw)
    if valor_total is None:
        valor_total = extract_valor_total(source_text)

    return {
        "numero_nota": numero_nota,
        "data_emissao": data_emissao,
        "cnpj_fornecedor": cnpj_fornecedor,
        "valor_total": valor_total,
        "competencia": competencia,
        "descricao_servico": "honorarios medicos",
    }



# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/nfse-service-extract-raw")
async def nfse_service_extract_raw(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.pdf")

    if not raw:
        return {"received": False, "error": "Empty body"}

    sha256 = hashlib.sha256(raw).hexdigest()

    pdf_bytes, fix_applied, is_pdf, pdf_header = normalize_pdf_payload(raw)
    if not is_pdf:
        return {
            "received": False,
            "error": "Not a valid PDF",
            "filename": filename,
            "sha256": sha256,
        }

    pages, text_pdf = extract_text_with_pdfplumber(pdf_bytes)
    method = "pdf_text"
    text = text_pdf or ""

    # 1) Extrai do texto do PDF
    fields = extract_nfse_fields(text)

    critical = ("numero_nota", "data_emissao", "valor_total", "competencia", "cnpj_fornecedor")
    missing_critical = [k for k in critical if not fields.get(k)]

    # 2) OCR híbrido: PSM 6 (geral) + PSM 11 (header/caixas)
    if missing_critical:
        try:
            ocr_pages_main, text_ocr_main = ocr_pdf_with_tesseract(
                pdf_bytes,
                lang="por+eng",
                config="--oem 3 --psm 6",
            )

            _, text_ocr_header = ocr_pdf_with_tesseract(
                pdf_bytes,
                lang="por+eng",
                config="--oem 3 --psm 11",
                only_first_page=True,
            )

            pages = max(pages, ocr_pages_main)
            method = "pdf_text+ocr"
            combined = "\n".join([text, text_ocr_main, text_ocr_header]).strip()
            fields = extract_nfse_fields(combined)

        except Exception as exc:
            logger.warning(
                "OCR failed (will keep pdf_text fields) | file=%s | err=%s",
                filename,
                exc,
            )

    missing = [k for k, v in fields.items() if v is None]
    confidence = round(1 - (len(missing) / len(fields)), 2)

    logger.info(
        "NFSE extract | file=%s | pages=%d | method=%s | confidence=%.2f | sha256=%s",
        filename,
        pages,
        method,
        confidence,
        sha256,
    )

    return {
        "received": True,
        "filename": filename,
        "pages": pages,
        "sha256": sha256,
        "method": method,
        "fix_applied": fix_applied,
        "pdf_header": pdf_header,
        "fields": fields,
        "missing_fields": missing,
        "confidence": confidence,
        "flags": {
            "needs_review": confidence < 0.95,
            "incomplete": len(missing) > 0,
        },
    }
