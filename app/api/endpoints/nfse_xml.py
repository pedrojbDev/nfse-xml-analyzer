# app/api/endpoints/nfse_xml.py
"""
Endpoints para processamento de NFS-e em XML.

Endpoints disponíveis:
- POST /nfse-xml-extract - Extrai com paginação
- POST /nfse-xml-extract/summary - Extrai resumo completo com normalização
- POST /nfse-xml-extract/multi - Extrai MÚLTIPLAS notas individuais de um XML
- POST /nfse-xml-extract/export-csv - Exporta para CSV
- POST /nfse-xml-batch/summary - Processa ZIP com múltiplos XMLs
"""
from fastapi import APIRouter, Request, Response, File, UploadFile
import hashlib
import logging

from app.services.audit_log import append_audit_event
from app.services.nfse_xml_extract import (
    parse_nfse_xml_abrasf,
    parse_nfse_xml_abrasf_paged,
    export_nfse_items_to_csv,
    parse_nfse_xml_multi_notes,
)
from app.services.nfse_service_normalizer import normalize_nfse_items, normalize_nfse_item
from app.services.nfse_document_analyzer import analyze_nfse_document
from app.services.nfse_batch import parse_nfse_zip_batch_summary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nfse-xml"])


def _extract_prestador_from_items(items: list[dict]) -> dict:
    """Extrai dados do prestador do primeiro item."""
    if not items:
        return {}
    
    first_item = items[0]
    fields = first_item.get("fields") or {}
    
    cnpj = fields.get("cnpj_fornecedor")
    
    return {
        "doc": cnpj.replace(".", "").replace("/", "").replace("-", "") if cnpj else None,
        "doc_formatado": cnpj,
        "nome": None,
    }


def _extract_totals_from_summary(summary: dict) -> dict:
    """Extrai totais do summary."""
    tax_totals = summary.get("tax_totals") or {}
    
    return {
        "valor_servicos": summary.get("sum_valor_total_politica_a"),
        "valor_liquido": summary.get("sum_valor_liquido_politica_b"),
        "valor_iss": tax_totals.get("sum_valor_iss"),
        "valor_iss_retido": tax_totals.get("sum_valor_iss_retido"),
        "valor_pis": tax_totals.get("sum_valor_pis"),
        "valor_cofins": tax_totals.get("sum_valor_cofins"),
        "valor_inss": tax_totals.get("sum_valor_inss"),
        "valor_ir": tax_totals.get("sum_valor_ir"),
        "valor_csll": tax_totals.get("sum_valor_csll"),
    }


@router.post("/nfse-xml-extract")
async def nfse_xml_extract(request: Request, page: int = 1, page_size: int = 50):
    """
    Extrai dados de NFS-e XML com paginação.
    
    Headers:
        x-filename: Nome do arquivo (opcional)
    
    Query params:
        page: Página (default: 1)
        page_size: Itens por página (default: 50, max: 500)
    """
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    result = parse_nfse_xml_abrasf_paged(raw, filename=filename, page=page, page_size=page_size)

    # Auditoria
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()

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
        pass

    return result


@router.post("/nfse-xml-extract/summary")
async def nfse_xml_extract_summary(request: Request):
    """
    NOVO: Extrai MÚLTIPLAS notas individuais de um único XML ABRASF.
    
    Cada <CompNfse> é tratado como uma nota fiscal individual.
    
    Retorna:
        - received: bool
        - filename: str
        - sha256: str
        - count: int (número total de notas)
        - notes: List[Dict] (lista de notas individuais prontas para lançamento)
        - batch_summary: Dict (resumo agregado para o gestor)
    """
    raw = await request.body()
    filename = request.headers.get("x-filename", "upload.xml")

    # Usa a nova função que extrai múltiplas notas
    result = parse_nfse_xml_multi_notes(xml_bytes=raw, filename=filename)
    
    if not result.get("received"):
        return {
            "received": False,
            "filename": filename,
            "sha256": result.get("sha256"),
            "count": 0,
            "notes": [],
            "batch_summary": result.get("batch_summary", {"error": "Parse failed"}),
        }
    
    # Enriquece cada nota com normalização
    enriched_notes = []
    for note in result.get("notes", []):
        # Cria um item fictício para usar o normalizador existente
        fake_item = {
            "fields": {
                "numero_nota": note.get("numero_nota"),
                "data_emissao": note.get("data_emissao"),
                "cnpj_fornecedor": note.get("prestador", {}).get("doc_formatado"),
                "valor_total": note.get("totals", {}).get("valor_servicos"),
                "competencia": note.get("competencia"),
                "descricao_servico": note.get("servico", {}).get("descricao_resumida"),
                "cnae": note.get("servico", {}).get("cnae"),
            },
            "taxes": note.get("taxes", {}),
            "validations": note.get("validations", {}),
            "flags": {
                "needs_review": note.get("decision") == "REVIEW",
                "incomplete": not note.get("numero_nota") or not note.get("totals", {}).get("valor_servicos"),
                "missing_critical": not note.get("numero_nota") or not note.get("prestador", {}).get("doc"),
            },
            "decision": note.get("decision"),
            "reasons": note.get("reasons", []),
        }
        
        # Normaliza o item para obter classificação de serviço
        enriched_item = normalize_nfse_item(fake_item)
        
        # Determina review_level
        if note.get("is_cancelada"):
            review_level = "HIGH"
            review_text = "Nota cancelada - não deve ser lançada"
        elif note.get("decision") == "AUTO":
            review_level = "LOW"
            review_text = "Nota OK para lançamento automático"
        elif note.get("decision") == "REVIEW":
            review_level = "MEDIUM"
            review_text = f"Requer revisão: {', '.join(note.get('reasons', []))}"
        else:
            review_level = "HIGH"
            review_text = f"Bloqueada: {', '.join(note.get('reasons', []))}"
        
        # Cria estrutura de documento para a nota individual
        document = {
            "document_type": "NFSE",
            "doc_class": enriched_item.get("normalized", {}).get("service_class", "OUTROS"),
            "decision": note.get("decision", "REVIEW"),
            "review_level": review_level,
            "review_text_ptbr": review_text,
            "reasons": note.get("reasons", []),
        }
        
        # Projeção ERP
        erp_projection = {
            "movement_type": "2.1.01",
            "supplier_doc": note.get("prestador", {}).get("doc"),
            "note_number": note.get("numero_nota"),
            "competencia": note.get("competencia"),
            "issue_datetime": note.get("data_emissao"),
            "valor_bruto": note.get("totals", {}).get("valor_servicos"),
            "valor_liquido": note.get("totals", {}).get("valor_liquido"),
            "service_code": "00010" if document["doc_class"] == "SERVICO_SAUDE" else "00020",
        }
        
        enriched_note = {
            **note,
            "normalized": enriched_item.get("normalized"),
            "review_level": review_level,
            "review_text_ptbr": review_text,
            "document": document,
            "erp_projection": erp_projection,
        }
        
        enriched_notes.append(enriched_note)
    
    # Auditoria
    try:
        xml_sha256 = hashlib.sha256(raw).hexdigest()
        append_audit_event(
            {
                "kind": "nfse_xml_extract_multi",
                "filename": filename,
                "xml_sha256": xml_sha256,
                "count": result.get("count"),
                "batch_summary": result.get("batch_summary"),
            }
        )
    except Exception:
        pass
    
    return {
        "received": True,
        "filename": result.get("filename"),
        "sha256": result.get("sha256"),
        "count": result.get("count"),
        "notes": enriched_notes,
        "batch_summary": result.get("batch_summary"),
    }


@router.post("/nfse-xml-extract/export-csv")
async def nfse_xml_export_csv(request: Request):
    """
    Exporta dados de NFS-e XML para CSV.
    
    Retorna arquivo CSV com todos os campos e tributos.
    """
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

    # Auditoria
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


@router.post("/nfse-xml-batch/summary")
async def nfse_xml_batch_summary(file: UploadFile = File(...)):
    """
    Processa ZIP com múltiplos XMLs de NFS-e.
    
    Retorna:
        - Lista de resultados por arquivo
        - Agregações do lote
        - Erros por arquivo (se houver)
    """
    raw = await file.read()
    filename = file.filename or "upload.zip"
    
    result = parse_nfse_zip_batch_summary(zip_bytes=raw, filename=filename)
    
    # Auditoria
    try:
        append_audit_event(
            {
                "kind": "nfse_xml_batch_summary",
                "filename": filename,
                "sha256_zip": result.get("sha256_zip"),
                "count_files_ok": result.get("count_files_ok"),
                "count_files_error": result.get("count_files_error"),
                "batch_summary": result.get("batch_summary"),
            }
        )
    except Exception:
        pass
    
    return result
