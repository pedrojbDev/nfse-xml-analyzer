from fastapi import APIRouter, Request, Response
import hashlib
from app.services.audit_log import append_audit_event


from app.services.nfse_xml_extract import (
    parse_nfse_xml_abrasf,
    parse_nfse_xml_abrasf_paged,
    export_nfse_items_to_csv,
)

router = APIRouter(tags=["nfse-xml"])


@router.post("/nfse-xml-extract")
async def nfse_xml_extract(request: Request, page: int = 1, page_size: int = 50):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf_paged(raw, filename=filename, page=page, page_size=page_size)

    # Auditoria leve: 1 evento por item retornado (página atual)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()

        # evento do request (opcional, mas útil)
        append_audit_event(
            {
                "kind": "nfse_xml_extract_page",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "page": page,
                "page_size": page_size,
                "count_total": result.get("count_total") or result.get("count"),
                "count_page": result.get("count_page") or len(result.get("items", []) or []),
            }
        )

        for it in result.get("items", []) or []:
            f = it.get("fields", {}) or {}
            t = it.get("taxes", {}) or {}
            v = (it.get("validations", {}) or {}).get("cnae_vs_descricao", {}) or {}

            append_audit_event(
                {
                    "kind": "nfse_xml_extract_item",
                    "filename": filename,
                    "xml_sha256": xml_sha256,

                    "numero_nota": f.get("numero_nota"),
                    "competencia": f.get("competencia"),
                    "cnpj_fornecedor": f.get("cnpj_fornecedor"),

                    "valor_total": f.get("valor_total"),
                    "valor_liquido_calc_b": t.get("valor_liquido_calculado_politica_b"),
                    "valor_liquido_xml": t.get("valor_liquido_nfse"),

                    "cnae": f.get("cnae"),
                    "cnae_status": v.get("status"),
                    "decision": it.get("decision"),
                    "reasons": it.get("reasons", []),
                }
            )
    except Exception:
        # auditoria nunca pode quebrar o endpoint
        pass

    return result



@router.post("/nfse-xml-extract/summary")
async def nfse_xml_extract_summary(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf(xml_bytes=raw, filename=filename)

    # Auditoria de resumo (1 por lote)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        summary = result.summary or {}
        append_audit_event(
            {
                "kind": "nfse_xml_extract_summary",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "count": result.count,
                "decision_summary": summary.get("decision_summary"),
                "validation_summary": summary.get("validation_summary"),
                "sum_valor_total_politica_a": summary.get("sum_valor_total_politica_a"),
                "sum_valor_liquido_politica_b": summary.get("sum_valor_liquido_politica_b"),
            }
        )
    except Exception:
        pass
    
    return {
        "received": result.received,
        "filename": result.filename,
        "sha256": result.sha256,
        "count": result.count,
        "summary": result.summary,
    }


@router.post("/nfse-xml-extract/export-csv")
async def nfse_xml_export_csv(request: Request):
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf(xml_bytes=raw, filename=filename)
    if not result.received:
        return {
            "received": False,
            "filename": result.filename,
            "sha256": result.sha256,
            "summary": result.summary,
        }

    csv_text = export_nfse_items_to_csv(result.items)
    out_name = filename.rsplit(".", 1)[0] + ".csv"

        # Auditoria de export (1 por exportação)
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event(
            {
                "kind": "nfse_xml_export_csv",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "count": result.count,
                "out_name": out_name,
            }
        )
    except Exception:
        pass


    
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return Response(content=csv_text, media_type="text/csv; charset=utf-8", headers=headers)
