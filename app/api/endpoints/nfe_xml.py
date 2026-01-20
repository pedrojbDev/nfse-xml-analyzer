from fastapi import APIRouter, Request, Response
import hashlib
from app.services.nfe_item_normalizer import normalize_nfe_items


from app.services.audit_log import append_audit_event
from app.services.nfe_xml_extract import (
    parse_nfe_xml,
    parse_nfe_xml_paged,
    export_nfe_items_to_csv,
)

router = APIRouter(tags=["nfe-xml"])


@router.post("/nfe-xml-extract")
async def nfe_xml_extract(request: Request, page: int = 1, page_size: int = 50):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    # 1) Parse
    result = parse_nfe_xml_paged(
        raw, filename=filename, page=page, page_size=page_size
    )

    # 2) NORMALIZAÇÃO (ANTES da auditoria)
    try:
        enriched_items, norm_summary = normalize_nfe_items(
            result.get("items", []) or []
        )
        result["items"] = enriched_items

        summary = dict(result.get("summary", {}) or {})
        summary.update(norm_summary)
        result["summary"] = summary
    except Exception:
        # normalizador nunca pode derrubar o endpoint
        pass

    # 3) AUDITORIA (já com decision/reasons)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()

        append_audit_event(
            {
                "kind": "nfe_xml_extract_page",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "page": page,
                "page_size": page_size,
                "count_total": result.get("count_total"),
                "count_page": result.get("count_page"),
                "chave_nfe": (result.get("header") or {}).get("chave_nfe"),
                "numero": (result.get("header") or {}).get("numero"),
                "serie": (result.get("header") or {}).get("serie"),
            }
        )

        for row in result.get("items", []) or []:
            it = row.get("item", {}) or {}
            append_audit_event(
                {
                    "kind": "nfe_xml_extract_item",
                    "filename": filename,
                    "xml_sha256": xml_sha256,
                    "chave_nfe": (result.get("header") or {}).get("chave_nfe"),
                    "nItem": it.get("nItem"),
                    "cProd": it.get("cProd"),
                    "xProd": it.get("xProd"),
                    "NCM": it.get("NCM"),
                    "CFOP": it.get("CFOP"),
                    "vProd": it.get("vProd"),
                    "icms_tipo": it.get("icms_tipo"),
                    "cst": it.get("cst"),
                    "csosn": it.get("csosn"),
                    "vICMS": it.get("vICMS"),
                    "vPIS": it.get("vPIS"),
                    "vCOFINS": it.get("vCOFINS"),
                    "confidence": row.get("confidence"),
                    "missing_fields": row.get("missing_fields", []),
                    "decision": row.get("decision"),
                    "reasons": row.get("reasons", []),
                }
            )
    except Exception:
        pass

    return result



@router.post("/nfe-xml-extract/summary")
async def nfe_xml_extract_summary(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfe_xml(xml_bytes=raw, filename=filename)

    # Auditoria de resumo (1 por lote)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event(
            {
                "kind": "nfe_xml_extract_summary",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "received": result.received,
                "count_items": result.count,
                "chave_nfe": (result.header or {}).get("chave_nfe"),
                "vNF": (result.totals or {}).get("vNF"),
                "vProd": (result.totals or {}).get("vProd"),
                "diff_items_vs_total_vProd": (result.summary or {}).get("diff_items_vs_total_vProd"),
            }
        )
    except Exception:
        pass

    return {
        "received": result.received,
        "filename": result.filename,
        "sha256": result.sha256,
        "count": result.count,
        "header": result.header,
        "emit": result.emit,
        "dest": result.dest,
        "totals": result.totals,
        "summary": result.summary,
    }


@router.post("/nfe-xml-extract/export-csv")
async def nfe_xml_export_csv(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfe_xml(xml_bytes=raw, filename=filename)
    if not result.received:
        return {
            "received": False,
            "filename": result.filename,
            "sha256": result.sha256,
            "summary": result.summary,
        }

    csv_text = export_nfe_items_to_csv(result.items)
    out_name = filename.rsplit(".", 1)[0] + ".csv"

    # Auditoria de export (1 por exportação)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event(
            {
                "kind": "nfe_xml_export_csv",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "count_items": result.count,
                "out_name": out_name,
                "chave_nfe": (result.header or {}).get("chave_nfe"),
            }
        )
    except Exception:
        pass

    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return Response(content=csv_text, media_type="text/csv; charset=utf-8", headers=headers)
