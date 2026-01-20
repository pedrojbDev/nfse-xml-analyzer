from __future__ import annotations

import hashlib
from fastapi import APIRouter, Request

from app.services.audit_log import append_audit_event
from app.services.nfe_batch import parse_nfe_zip_batch_summary

router = APIRouter(tags=["nfe-batch"])


@router.post("/nfe-xml-batch/summary")
async def nfe_xml_batch_summary(request: Request):
    """
    Recebe um ZIP (application/zip) contendo múltiplas NF-e XMLs.
    Retorna summary por arquivo + agregações do lote (Opção A).
    """
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.zip")

    result = parse_nfe_zip_batch_summary(raw, filename=filename)

    # Auditoria leve: 1 evento por batch + (opcional) 1 por arquivo OK/erro
    try:
        zip_sha256 = hashlib.sha256(raw).hexdigest()

        append_audit_event(
            {
                "kind": "nfe_zip_batch_summary",
                "filename": filename,
                "zip_sha256": zip_sha256,
                "received": result.get("received"),
                "count_files_ok": result.get("count_files_ok"),
                "count_files_error": result.get("count_files_error"),
                "count_total_items": (result.get("batch_summary") or {}).get("count_total_items"),
                "sum_vNF": (result.get("batch_summary") or {}).get("sum_vNF"),
                "sum_vProd": (result.get("batch_summary") or {}).get("sum_vProd"),
                "decision_summary": (result.get("batch_summary") or {}).get("decision_summary"),
                "quality_summary": (result.get("batch_summary") or {}).get("quality_summary"),
            }
        )

        # 1 evento por arquivo OK
        for f in result.get("files", []) or []:
            h = f.get("header") or {}
            t = f.get("totals") or {}
            s = f.get("summary") or {}
            append_audit_event(
                {
                    "kind": "nfe_zip_batch_file_ok",
                    "batch_filename": filename,
                    "zip_sha256": zip_sha256,
                    "file": f.get("file"),
                    "xml_sha256": f.get("xml_sha256"),
                    "chave_nfe": h.get("chave_nfe"),
                    "numero": h.get("numero"),
                    "serie": h.get("serie"),
                    "count_items": f.get("count_items"),
                    "vNF": t.get("vNF"),
                    "vProd": t.get("vProd"),
                    "decision_summary": (s.get("decision_summary") or {}),
                    "quality_summary": (s.get("quality_summary") or {}),
                }
            )

        # 1 evento por erro
        for e in result.get("errors", []) or []:
            append_audit_event(
                {
                    "kind": "nfe_zip_batch_file_error",
                    "batch_filename": filename,
                    "zip_sha256": zip_sha256,
                    "file": e.get("file"),
                    "error": e.get("error"),
                    "exception": e.get("exception"),
                }
            )
    except Exception:
        pass

    return result
