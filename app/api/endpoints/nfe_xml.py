# app/api/endpoints/nfe_xml.py
"""
Endpoints para processamento de NF-e (XML).

Endpoints:
- POST /nfe-xml-extract: Extrai e normaliza NF-e com paginação
- POST /nfe-xml-extract/summary: Retorna sumário da nota
- POST /nfe-xml-extract/export-csv: Exporta itens para CSV
"""
from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Request, Response

from app.services.audit_log import append_audit_event
from app.services.nfe_document_analyzer import analyze_nfe_document
from app.services.nfe_item_normalizer import normalize_nfe_items
from app.services.nfe_xml_extract import (
    export_nfe_items_to_csv,
    parse_nfe_xml,
    parse_nfe_xml_paged,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nfe-xml"])


@router.post("/nfe-xml-extract")
async def nfe_xml_extract(request: Request, page: int = 1, page_size: int = 50):
    """
    Extrai dados de NF-e (XML) com normalização e análise.
    
    Args:
        request: Requisição com XML no body
        page: Número da página (1-based)
        page_size: Itens por página (máx 500)
        
    Returns:
        JSON com header, emit, dest, totals, items (paginados), summary, document
    """
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")
    
    # 1) Parse
    result = parse_nfe_xml_paged(raw, filename=filename, page=page, page_size=page_size)
    
    # 2) Normalização dos itens
    try:
        enriched_items, norm_summary = normalize_nfe_items(result.get("items", []) or [])
        result["items"] = enriched_items
        
        summary = dict(result.get("summary", {}) or {})
        summary.update(norm_summary)
        result["summary"] = summary
    except Exception as exc:
        logger.warning(f"Falha na normalização de itens: {exc}", exc_info=True)
    
    # 3) Análise do documento (nível nota)
    try:
        doc_out = analyze_nfe_document(
            header=result.get("header") or {},
            emit=result.get("emit") or {},
            dest=result.get("dest") or {},
            totals=result.get("totals") or {},
            summary=result.get("summary") or {},
            enriched_items=result.get("items") or [],
            filial_by_dest_doc=None,  # plugar depois com mapa real
        )
        result["document"] = doc_out["document"]
        result["erp_projection"] = doc_out["erp_projection"]
        
        # Anexa resumo do documento no summary para dashboard
        summary = dict(result.get("summary", {}) or {})
        summary["document_summary"] = doc_out["document_summary"]
        result["summary"] = summary
    except Exception as exc:
        logger.warning(f"Falha na análise do documento: {exc}", exc_info=True)
    
    # 4) Auditoria
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        
        append_audit_event({
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
            "doc_class": (result.get("document") or {}).get("doc_class"),
            "doc_decision": (result.get("document") or {}).get("decision"),
            "doc_reasons": (result.get("document") or {}).get("reasons", []),
        })
        
        # Auditoria por item
        for row in result.get("items", []) or []:
            it = row.get("item", {}) or {}
            append_audit_event({
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
            })
    except Exception as exc:
        logger.warning(f"Falha na auditoria: {exc}", exc_info=True)
    
    return result


@router.post("/nfe-xml-extract/summary")
async def nfe_xml_extract_summary(request: Request):
    """
    Retorna sumário da NF-e com análise do documento.
    
    Útil para dashboards e visão de gestor.
    
    Returns:
        JSON com header, emit, dest, totals, summary, document, erp_projection
    """
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")
    
    result = parse_nfe_xml(xml_bytes=raw, filename=filename)
    
    # Inicializa variáveis
    doc_summary_payload = None
    doc_payload = None
    erp_projection = None
    merged_summary = dict(result.summary or {})
    
    # Normalização + análise
    try:
        enriched_items, norm_summary = normalize_nfe_items(result.items or [])
        merged_summary.update(norm_summary)
        
        doc_out = analyze_nfe_document(
            header=result.header or {},
            emit=result.emit or {},
            dest=result.dest or {},
            totals=result.totals or {},
            summary=merged_summary,
            enriched_items=enriched_items,
            filial_by_dest_doc=None,
        )
        
        doc_payload = doc_out["document"]
        erp_projection = doc_out["erp_projection"]
        doc_summary_payload = doc_out["document_summary"]
        merged_summary["document_summary"] = doc_summary_payload
    except Exception as exc:
        logger.warning(f"Falha no processamento do summary: {exc}", exc_info=True)
    
    # Auditoria
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event({
            "kind": "nfe_xml_extract_summary",
            "filename": filename,
            "xml_sha256": xml_sha256,
            "received": result.received,
            "count_items": result.count,
            "chave_nfe": (result.header or {}).get("chave_nfe"),
            "vNF": (result.totals or {}).get("vNF"),
            "vProd": (result.totals or {}).get("vProd"),
            "diff_items_vs_total_vProd": merged_summary.get("diff_items_vs_total_vProd"),
            "doc_class": (doc_payload or {}).get("doc_class") if isinstance(doc_payload, dict) else None,
            "doc_decision": (doc_payload or {}).get("decision") if isinstance(doc_payload, dict) else None,
            "doc_reasons": (doc_payload or {}).get("reasons", []) if isinstance(doc_payload, dict) else [],
        })
    except Exception as exc:
        logger.warning(f"Falha na auditoria: {exc}", exc_info=True)
    
    # Normaliza itens para retornar
    items_out = []
    try:
        enriched_items, _ = normalize_nfe_items(result.items or [])
        items_out = enriched_items
    except Exception as exc:
        logger.warning(f"Falha ao normalizar itens para retorno: {exc}", exc_info=True)
    
    return {
        "received": result.received,
        "filename": result.filename,
        "sha256": result.sha256,
        "count": result.count,
        "header": result.header,
        "emit": result.emit,
        "dest": result.dest,
        "totals": result.totals,
        "summary": merged_summary,
        "document": doc_payload,
        "erp_projection": erp_projection,
        "items": items_out,
    }


@router.post("/nfe-xml-extract/export-csv")
async def nfe_xml_export_csv(request: Request):
    """
    Exporta itens da NF-e para CSV.
    
    Returns:
        Arquivo CSV com separador ";" ou JSON de erro
    """
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
    
    # Normaliza antes de exportar para incluir product_class/decision no CSV
    items_for_csv = result.items
    try:
        enriched_items, _norm_summary = normalize_nfe_items(result.items or [])
        items_for_csv = enriched_items
    except Exception as exc:
        logger.warning(f"Falha na normalização para CSV: {exc}", exc_info=True)
    
    csv_text = export_nfe_items_to_csv(items_for_csv)
    out_name = filename.rsplit(".", 1)[0] + ".csv"
    
    # Auditoria
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event({
            "kind": "nfe_xml_export_csv",
            "filename": filename,
            "xml_sha256": xml_sha256,
            "count_items": result.count,
            "out_name": out_name,
            "chave_nfe": (result.header or {}).get("chave_nfe"),
        })
    except Exception as exc:
        logger.warning(f"Falha na auditoria: {exc}", exc_info=True)
    
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return Response(content=csv_text, media_type="text/csv; charset=utf-8", headers=headers)
