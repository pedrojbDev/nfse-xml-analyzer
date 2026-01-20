from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.nfe_xml_extract import parse_nfe_xml
from app.services.nfe_item_normalizer import normalize_nfe_items


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_xml_name(name: str) -> bool:
    n = (name or "").lower().strip()
    return n.endswith(".xml")


def parse_nfe_zip_batch_summary(
    zip_bytes: bytes,
    filename: str = "upload.zip",
    *,
    max_files: int = 200,
    max_total_bytes: int = 50 * 1024 * 1024,  # 50MB descompactado (limite conservador)
) -> Dict[str, Any]:
    """
    Opção A (MVP): Processa um ZIP com vários XMLs de NF-e e retorna SUMMARY por arquivo.

    Saída:
      - received, filename, sha256_zip
      - count_files_ok, count_files_error
      - files: lista de resultados por arquivo (header, totals, count_items, summary_norm)
      - errors: lista de erros por arquivo
      - batch_summary: agregações do lote
    """
    sha256_zip = _sha256(zip_bytes)

    if not zip_bytes:
        return {
            "received": False,
            "filename": filename,
            "sha256_zip": sha256_zip,
            "count_files_ok": 0,
            "count_files_error": 0,
            "files": [],
            "errors": [{"file": None, "error": "Empty body"}],
            "batch_summary": {"error": "Empty body"},
        }

    files_out: List[Dict[str, Any]] = []
    errors_out: List[Dict[str, Any]] = []

    # agregações do lote
    total_items = 0
    sum_vnf = 0.0
    sum_vprod = 0.0

    sum_dec_auto = 0
    sum_dec_review = 0
    sum_dec_block = 0

    sum_missing_ncm = 0
    sum_missing_cfop = 0
    sum_item_total_invalid = 0

    # controle de volume descompactado
    decompressed_total = 0

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:
        return {
            "received": False,
            "filename": filename,
            "sha256_zip": sha256_zip,
            "count_files_ok": 0,
            "count_files_error": 0,
            "files": [],
            "errors": [{"file": None, "error": "Invalid zip", "exception": str(exc)}],
            "batch_summary": {"error": "Invalid zip"},
        }

    # lista de candidatos
    names = [n for n in zf.namelist() if _is_xml_name(n) and not n.endswith("/")]
    names = [n for n in names if "__MACOSX" not in n]

    if not names:
        return {
            "received": False,
            "filename": filename,
            "sha256_zip": sha256_zip,
            "count_files_ok": 0,
            "count_files_error": 0,
            "files": [],
            "errors": [{"file": None, "error": "No .xml files found in zip"}],
            "batch_summary": {"error": "No .xml files found"},
        }

    if len(names) > max_files:
        # processa só os primeiros max_files para evitar abuso
        names = names[:max_files]

    for name in names:
        try:
            xml_bytes = zf.read(name)
            decompressed_total += len(xml_bytes)
            if decompressed_total > max_total_bytes:
                errors_out.append(
                    {"file": name, "error": "Batch decompressed size exceeded limit", "limit_bytes": max_total_bytes}
                )
                break

            # Parse 1 NF-e
            parsed = parse_nfe_xml(xml_bytes=xml_bytes, filename=name)
            if not getattr(parsed, "received", False):
                errors_out.append({"file": name, "error": "parse_failed", "details": getattr(parsed, "error", None)})
                continue

            # Normaliza itens e gera métricas (decision_summary / quality_summary)
            enriched_items, norm_summary = normalize_nfe_items(parsed.items)

            # agrega lote
            total_items += int(parsed.count or 0)

            vnf = parsed.totals.get("vNF")
            vprod = parsed.totals.get("vProd")
            if vnf is not None:
                try:
                    sum_vnf += float(vnf)
                except Exception:
                    pass
            if vprod is not None:
                try:
                    sum_vprod += float(vprod)
                except Exception:
                    pass

            ds = (norm_summary.get("decision_summary") or {})
            qs = (norm_summary.get("quality_summary") or {})

            sum_dec_auto += int(ds.get("auto", 0) or 0)
            sum_dec_review += int(ds.get("review", 0) or 0)
            sum_dec_block += int(ds.get("block", 0) or 0)

            sum_missing_ncm += int(qs.get("missing_ncm", 0) or 0)
            sum_missing_cfop += int(qs.get("missing_cfop", 0) or 0)
            sum_item_total_invalid += int(qs.get("item_total_invalid", 0) or 0)

            files_out.append(
                {
                    "file": name,
                    "xml_sha256": _sha256(xml_bytes),
                    "count_items": int(parsed.count or 0),
                    "header": parsed.header,
                    "totals": parsed.totals,
                    "summary": {
                        **(parsed.summary or {}),
                        **norm_summary,
                    },
                }
            )

        except Exception as exc:
            errors_out.append({"file": name, "error": "exception", "exception": str(exc)})

    batch_summary = {
        "count_files_ok": len(files_out),
        "count_files_error": len(errors_out),
        "count_total_items": total_items,
        "sum_vNF": round(sum_vnf, 2),
        "sum_vProd": round(sum_vprod, 2),
        "decision_summary": {
            "auto": sum_dec_auto,
            "review": sum_dec_review,
            "block": sum_dec_block,
        },
        "quality_summary": {
            "missing_ncm": sum_missing_ncm,
            "missing_cfop": sum_missing_cfop,
            "item_total_invalid": sum_item_total_invalid,
        },
        "limits": {
            "max_files": max_files,
            "max_total_bytes": max_total_bytes,
        },
    }

    return {
        "received": True,
        "filename": filename,
        "sha256_zip": sha256_zip,
        "count_files_ok": len(files_out),
        "count_files_error": len(errors_out),
        "files": files_out,
        "errors": errors_out,
        "batch_summary": batch_summary,
    }
