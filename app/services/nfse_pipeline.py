from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, Any, Tuple, Optional

from app.utils.payload import normalize_pdf_payload
from app.services.pdf_text import extract_text_with_pdfplumber
from app.services.ocr import ocr_pdf_with_tesseract
from app.services.nfse_extract import extract_nfse_fields
from app.utils.money_scan import scan_first_money_value

logger = logging.getLogger("doc_api")

CRITICAL_FIELDS = (
    "numero_nota",
    "data_emissao",
    "valor_total",
    "competencia",
    "cnpj_fornecedor",
)


def _compute_confidence(fields: Dict[str, Any]) -> Tuple[list[str], float]:
    missing = [k for k, v in fields.items() if v is None]
    confidence = round(1 - (len(missing) / len(fields)), 2) if fields else 0.0
    return missing, confidence


def _missing_critical(fields: Dict[str, Any]) -> list[str]:
    return [k for k in CRITICAL_FIELDS if not fields.get(k)]


def _merge_sources(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge de campos: usa valores novos apenas quando forem "melhores" (não None).
    """
    merged = dict(base)
    for k, v in update.items():
        if merged.get(k) is None and v is not None:
            merged[k] = v
    return merged


def _source_map_for_update(
    previous_fields: Dict[str, Any],
    new_fields: Dict[str, Any],
    source_name: str,
    field_sources: Dict[str, str],
) -> None:
    """
    Marca origem do campo quando ele foi preenchido agora (antes era None e agora não é).
    """
    for k, v in new_fields.items():
        if previous_fields.get(k) is None and v is not None:
            field_sources[k] = source_name


def _parse_crop_env(var_name: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Espera 'x0,y0,x1,y1' em points do PDF. Ex.: '0,420,595,520'
    """
    raw = os.getenv(var_name)
    if not raw:
        return None
    try:
        parts = [float(p.strip()) for p in raw.split(",")]
        if len(parts) != 4:
            return None
        return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        return None


def run_nfse_extract_pipeline(raw: bytes, filename: str = "upload.pdf") -> Dict[str, Any]:
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

    # --------
    # 1) PDF text
    # --------
    pages, text_pdf = extract_text_with_pdfplumber(pdf_bytes)
    method = "pdf_text"
    text_pdf = text_pdf or ""

    fields_pdf = extract_nfse_fields(text_pdf)
    fields = dict(fields_pdf)

    field_sources: Dict[str, str] = {k: "pdf_text" for k, v in fields.items() if v is not None}

    missing_crit = _missing_critical(fields)

    debug = {"steps": []}

    # Crop opcional para OCR de header e valor
    ocr_header_crop = _parse_crop_env("OCR_HEADER_CROP")
    ocr_valor_crop = _parse_crop_env("OCR_VALOR_CROP")

    # --------
    # 2) OCR header-first
    # --------
    if missing_crit:
        try:
            _, text_ocr_header = ocr_pdf_with_tesseract(
                pdf_bytes,
                lang="por+eng",
                config="--oem 3 --psm 11",
                only_first_page=True,
                crop_rect=ocr_header_crop,
            )
            debug["steps"].append({"stage": "ocr_header", "crop": ocr_header_crop, "chars": len(text_ocr_header)})

            fields_hdr = extract_nfse_fields(text_ocr_header)
            _source_map_for_update(fields, fields_hdr, "ocr_header", field_sources)
            fields = _merge_sources(fields, fields_hdr)

            missing_crit = _missing_critical(fields)
            if method == "pdf_text":
                method = "pdf_text+ocr_header"
        except Exception as exc:
            logger.warning("OCR header failed | file=%s | err=%s", filename, exc)
            debug["steps"].append({"stage": "ocr_header_failed", "err": str(exc)})

    # --------
    # 3) OCR main (fallback pesado) — 1ª página (MVP barato)
    # --------
    if missing_crit:
        try:
            ocr_pages_main, text_ocr_main = ocr_pdf_with_tesseract(
                pdf_bytes,
                lang="por+eng",
                config="--oem 3 --psm 6",
                only_first_page=True,
            )
            debug["steps"].append({"stage": "ocr_main_first_page", "pages": ocr_pages_main, "chars": len(text_ocr_main)})

            fields_main = extract_nfse_fields(text_ocr_main)
            _source_map_for_update(fields, fields_main, "ocr_main", field_sources)
            fields = _merge_sources(fields, fields_main)

            pages = max(pages, ocr_pages_main)

            if method == "pdf_text":
                method = "pdf_text+ocr"
            elif method == "pdf_text+ocr_header":
                method = "pdf_text+ocr_header+ocr"
        except Exception as exc:
            logger.warning("OCR main failed | file=%s | err=%s", filename, exc)
            debug["steps"].append({"stage": "ocr_main_failed", "err": str(exc)})

    # --------
    # 4) OCR por crop para valor_total (último recurso)
    #    Só roda se OCR_VALOR_CROP estiver setado.
    # --------
    if fields.get("valor_total") is None and ocr_valor_crop:
        try:
            _, text_ocr_valor = ocr_pdf_with_tesseract(
                pdf_bytes,
                lang="por+eng",
                config="--oem 3 --psm 6",
                only_first_page=True,
                crop_rect=ocr_valor_crop,
            )
            debug["steps"].append({"stage": "ocr_valor_crop", "crop": ocr_valor_crop, "chars": len(text_ocr_valor)})

            v = scan_first_money_value(text_ocr_valor)
            if v is not None:
                fields["valor_total"] = v
                field_sources["valor_total"] = "ocr_valor_crop"
        except Exception as exc:
            logger.warning("OCR valor crop failed | file=%s | err=%s", filename, exc)
            debug["steps"].append({"stage": "ocr_valor_crop_failed", "err": str(exc)})

    missing, confidence = _compute_confidence(fields)

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
        "field_sources": field_sources,
        "debug": debug,
    }
