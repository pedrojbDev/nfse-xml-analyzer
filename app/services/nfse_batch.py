# app/services/nfse_batch.py
"""
Serviço de processamento em lote de NFS-e.

Responsável por:
- Processar ZIPs com múltiplos XMLs de NFS-e
- Agregar resultados do lote
- Retornar dados completos por arquivo
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any, Dict, List

from app.services.nfse_xml_extract import parse_nfse_xml_abrasf
from app.services.nfse_service_normalizer import normalize_nfse_items
from app.services.nfse_document_analyzer import analyze_nfse_document


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_xml_name(name: str) -> bool:
    n = (name or "").lower().strip()
    return n.endswith(".xml")


def _extract_prestador_from_items(items: list[dict]) -> dict[str, Any]:
    """Extrai dados do prestador do primeiro item."""
    if not items:
        return {}
    
    first_item = items[0]
    fields = first_item.get("fields") or {}
    
    cnpj = fields.get("cnpj_fornecedor")
    
    return {
        "doc": cnpj.replace(".", "").replace("/", "").replace("-", "") if cnpj else None,
        "doc_formatado": cnpj,
        "nome": None,  # XML ABRASF não traz nome no formato atual
    }


def _extract_tomador_from_items(items: list[dict]) -> dict[str, Any]:
    """Extrai dados do tomador (não disponível no formato atual)."""
    return {}


def _extract_totals_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
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


def parse_nfse_zip_batch_summary(
    zip_bytes: bytes,
    filename: str = "upload.zip",
    *,
    max_files: int = 200,
    max_total_bytes: int = 50 * 1024 * 1024,  # 50MB descompactado
) -> Dict[str, Any]:
    """
    Processa um ZIP com vários XMLs de NFS-e e retorna dados completos por arquivo.

    Saída:
      - received, filename, sha256_zip
      - count_files_ok, count_files_error
      - files: lista de resultados por arquivo
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

    # Agregações do lote
    total_items = 0
    sum_valor_servicos = 0.0
    sum_valor_liquido = 0.0

    sum_dec_auto = 0
    sum_dec_review = 0
    sum_dec_block = 0

    sum_missing_cnae = 0
    sum_missing_valor = 0
    sum_cnae_alert = 0
    sum_liquido_divergente = 0

    # Controle de volume descompactado
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

    # Lista de candidatos
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
        names = names[:max_files]

    for name in names:
        try:
            xml_bytes = zf.read(name)
            decompressed_total += len(xml_bytes)
            if decompressed_total > max_total_bytes:
                errors_out.append({
                    "file": name,
                    "error": "Batch decompressed size exceeded limit",
                    "limit_bytes": max_total_bytes
                })
                break

            # Parse 1 NFS-e
            parsed = parse_nfse_xml_abrasf(xml_bytes=xml_bytes, filename=name)
            if not parsed.received:
                errors_out.append({
                    "file": name,
                    "error": "parse_failed",
                    "details": parsed.summary.get("error") if parsed.summary else None
                })
                continue

            # Normaliza itens
            enriched_items, norm_summary = normalize_nfse_items(parsed.items)

            # Mescla summary
            merged_summary = {
                **(parsed.summary or {}),
                **norm_summary,
            }

            # Extrai dados estruturados
            prestador = _extract_prestador_from_items(parsed.items)
            tomador = _extract_tomador_from_items(parsed.items)
            totals = _extract_totals_from_summary(parsed.summary or {})

            # Analisa documento (nível nota)
            doc_out = analyze_nfse_document(
                prestador=prestador,
                tomador=tomador,
                totals=totals,
                summary=merged_summary,
                enriched_items=enriched_items,
                filial_by_tomador_doc=None,
            )

            # Adiciona document_summary ao summary
            merged_summary["document_summary"] = doc_out.get("document_summary")

            # Agrega lote
            total_items += int(parsed.count or 0)

            valor_serv = parsed.summary.get("sum_valor_total_politica_a") if parsed.summary else None
            valor_liq = parsed.summary.get("sum_valor_liquido_politica_b") if parsed.summary else None
            
            if valor_serv is not None:
                try:
                    sum_valor_servicos += float(valor_serv)
                except Exception:
                    pass
            if valor_liq is not None:
                try:
                    sum_valor_liquido += float(valor_liq)
                except Exception:
                    pass

            ds = norm_summary.get("decision_summary") or {}
            qs = norm_summary.get("quality_summary") or {}

            sum_dec_auto += int(ds.get("auto", 0) or 0)
            sum_dec_review += int(ds.get("review", 0) or 0)
            sum_dec_block += int(ds.get("block", 0) or 0)

            sum_missing_cnae += int(qs.get("missing_cnae", 0) or 0)
            sum_missing_valor += int(qs.get("missing_valor", 0) or 0)
            sum_cnae_alert += int(qs.get("cnae_alert", 0) or 0)
            sum_liquido_divergente += int(qs.get("liquido_divergente", 0) or 0)

            # Extrai nome do arquivo sem path
            file_basename = name.split("/")[-1].split("\\")[-1]

            files_out.append({
                "file": file_basename,
                "xml_sha256": _sha256(xml_bytes),
                "received": True,
                "count_items": int(parsed.count or 0),
                "prestador": prestador,
                "tomador": tomador,
                "totals": totals,
                "summary": merged_summary,
                "document": doc_out.get("document"),
                "erp_projection": doc_out.get("erp_projection"),
                "items": enriched_items,
            })

        except Exception as exc:
            errors_out.append({
                "file": name,
                "error": "exception",
                "exception": str(exc)
            })

    batch_summary = {
        "count_files_ok": len(files_out),
        "count_files_error": len(errors_out),
        "count_total_items": total_items,
        "sum_valor_servicos": round(sum_valor_servicos, 2),
        "sum_valor_liquido": round(sum_valor_liquido, 2),
        "decision_summary": {
            "auto": sum_dec_auto,
            "review": sum_dec_review,
            "block": sum_dec_block,
        },
        "quality_summary": {
            "missing_cnae": sum_missing_cnae,
            "missing_valor": sum_missing_valor,
            "cnae_alert": sum_cnae_alert,
            "liquido_divergente": sum_liquido_divergente,
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
