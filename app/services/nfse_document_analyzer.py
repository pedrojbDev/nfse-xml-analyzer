# app/services/nfse_document_analyzer.py
"""
Serviço de análise de documentos NFS-e (nível nota inteira).

Responsável por:
- Classificar o documento com base nos serviços normalizados
- Determinar review_level do documento
- Gerar projeção para ERP
- Produzir explicações auditáveis em PT-BR
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.utils.converters import (
    dedup_keep_order,
    safe_float,
)


# =============================================================================
# Constantes (nível documento)
# =============================================================================

DOC_DECISION_REVIEW = "REVIEW"  # Requisito: NUNCA bloquear (tudo REVIEW)

DOC_REVIEW_LOW = "LOW"
DOC_REVIEW_MEDIUM = "MEDIUM"
DOC_REVIEW_HIGH = "HIGH"

# Classes (nível documento)
DOC_CLASS_SAUDE = "SERVICO_SAUDE"
DOC_CLASS_TECNICO = "SERVICO_TECNICO"
DOC_CLASS_ADMIN = "SERVICO_ADMINISTRATIVO"
DOC_CLASS_CONSULTORIA = "SERVICO_CONSULTORIA"
DOC_CLASS_MANUTENCAO = "SERVICO_MANUTENCAO"
DOC_CLASS_OUTROS = "OUTROS"
DOC_CLASS_MIXED = "MIXED"
DOC_CLASS_UNKNOWN = "UNKNOWN"

# Reasons padronizados (strings estáveis para dashboard/BI)
REASON_DOC_NO_ITEMS = "DOC_NO_ITEMS"
REASON_DOC_MISSING_PRESTADOR = "DOC_MISSING_PRESTADOR"
REASON_DOC_MISSING_VALOR = "DOC_MISSING_VALOR"
REASON_DOC_VALOR_LIQUIDO_DIVERGENTE = "DOC_VALOR_LIQUIDO_DIVERGENTE"
REASON_DOC_ITEMS_MIXED_CLASSES = "DOC_ITEMS_MIXED_CLASSES"
REASON_DOC_ITEMS_HAVE_INCOMPLETE = "DOC_ITEMS_INCOMPLETE"
REASON_DOC_CANNOT_CLASSIFY = "DOC_CANNOT_CLASSIFY"
REASON_DOC_ITEMS_HAVE_REVIEW_HIGH = "DOC_ITEMS_HAVE_REVIEW_HIGH"
REASON_DOC_ITEMS_HAVE_REVIEW_MEDIUM = "DOC_ITEMS_HAVE_REVIEW_MEDIUM"
REASON_DOC_CNAE_ALERTS = "DOC_CNAE_ALERTS"


@dataclass(frozen=True)
class NfseDocumentThresholds:
    """
    Thresholds para divergência de valores.
    """
    liquido_abs: float = 0.10   # R$ 0,10
    liquido_pct: float = 0.001  # 0,1%
    
    @classmethod
    def from_settings(cls) -> "NfseDocumentThresholds":
        """Cria instância a partir das configurações."""
        return cls(
            liquido_abs=getattr(settings, "nfse_liquido_abs_threshold", 0.10),
            liquido_pct=getattr(settings, "nfse_liquido_pct_threshold", 0.001),
        )


# =============================================================================
# Helpers
# =============================================================================

def _summarize_top_reasons(reasons: list[str], max_items: int = 8) -> list[str]:
    """Retorna os primeiros N reasons únicos."""
    return dedup_keep_order(reasons)[:max_items]


def _normalize_doc_class(sc: str) -> str:
    """Normaliza classe de serviço para comparação."""
    s = (sc or "").strip().upper()
    valid_classes = (
        DOC_CLASS_SAUDE, DOC_CLASS_TECNICO, DOC_CLASS_ADMIN,
        DOC_CLASS_CONSULTORIA, DOC_CLASS_MANUTENCAO, DOC_CLASS_OUTROS,
    )
    for vc in valid_classes:
        if s == vc.upper():
            return vc
    return ""


# =============================================================================
# Classificação do documento
# =============================================================================

def classify_nfse_document_from_items(
    enriched_items: list[dict[str, Any]],
    majority_threshold: float = 0.6,
) -> tuple[str, dict[str, Any]]:
    """
    Classifica documento com base nas classes dos serviços normalizados.
    
    Regras (ordem de prioridade):
    1. Se todos itens específicos são da mesma classe -> essa classe
    2. Se uma classe representa >= majority_threshold dos itens -> essa classe
    3. Se há mistura significativa -> MIXED
    4. Se só há OUTROS -> OUTROS
    5. Se não há itens -> UNKNOWN
    
    Args:
        enriched_items: Itens já normalizados
        majority_threshold: Proporção mínima para considerar classe predominante
        
    Returns:
        Tupla (classe_documento, metadados)
    """
    classes_seen: dict[str, int] = {
        DOC_CLASS_SAUDE: 0,
        DOC_CLASS_TECNICO: 0,
        DOC_CLASS_ADMIN: 0,
        DOC_CLASS_CONSULTORIA: 0,
        DOC_CLASS_MANUTENCAO: 0,
        DOC_CLASS_OUTROS: 0,
        "UNKNOWN": 0,
    }
    
    for row in enriched_items or []:
        norm = (row.get("normalized") or {}) if isinstance(row, dict) else {}
        sc_raw = norm.get("service_class") or ""
        sc = _normalize_doc_class(sc_raw)
        
        if sc in classes_seen:
            classes_seen[sc] += 1
        elif sc_raw:
            classes_seen[DOC_CLASS_OUTROS] += 1
        else:
            classes_seen["UNKNOWN"] += 1
    
    total_items = sum(classes_seen.values())
    meta = {"classes_seen": classes_seen}
    
    if total_items == 0:
        return DOC_CLASS_UNKNOWN, meta
    
    # Classes específicas (excluindo OUTROS e UNKNOWN)
    specific_classes = [
        DOC_CLASS_SAUDE, DOC_CLASS_TECNICO, DOC_CLASS_ADMIN,
        DOC_CLASS_CONSULTORIA, DOC_CLASS_MANUTENCAO,
    ]
    
    # Contagem de itens específicos
    total_specific = sum(classes_seen[c] for c in specific_classes)
    
    # Se não há itens específicos, verifica se há OUTROS
    if total_specific == 0:
        if classes_seen[DOC_CLASS_OUTROS] > 0:
            return DOC_CLASS_OUTROS, meta
        return DOC_CLASS_UNKNOWN, meta
    
    # Encontra a classe com maior contagem
    max_class = None
    max_count = 0
    for c in specific_classes:
        if classes_seen[c] > max_count:
            max_count = classes_seen[c]
            max_class = c
    
    # Calcula proporção da classe majoritária
    pct_max = max_count / total_specific if total_specific > 0 else 0
    meta["pct_majority"] = round(pct_max, 3)
    meta["majority_class"] = max_class
    
    # Se só tem uma classe específica com itens
    classes_with_items = [c for c in specific_classes if classes_seen[c] > 0]
    if len(classes_with_items) == 1:
        return classes_with_items[0], meta
    
    # Se a classe majoritária representa >= threshold
    if pct_max >= majority_threshold:
        return max_class, meta
    
    # Mistura significativa
    return DOC_CLASS_MIXED, meta


# =============================================================================
# Review level e texto PT-BR
# =============================================================================

def _compute_review_level(
    *,
    missing_prestador: bool,
    missing_valor: bool,
    has_liquido_divergente: bool,
    doc_class: str,
    count_items: int,
    count_incomplete: int,
    items_review_high: int,
    items_review_medium: int,
    cnae_alerts: int,
) -> str:
    """
    Determina nível de revisão do documento.
    
    HIGH: forte chance de erro / precisa decisão humana
    MEDIUM: faltas ou sinais que precisam checagem
    LOW: "lançável", só validação final
    """
    # HIGH
    if doc_class in (DOC_CLASS_MIXED, DOC_CLASS_UNKNOWN):
        return DOC_REVIEW_HIGH
    if count_items == 0:
        return DOC_REVIEW_HIGH
    if missing_prestador or missing_valor:
        return DOC_REVIEW_HIGH
    if has_liquido_divergente:
        return DOC_REVIEW_HIGH
    
    # MEDIUM
    if count_incomplete > 0:
        return DOC_REVIEW_MEDIUM
    if items_review_high > 0:
        return DOC_REVIEW_MEDIUM
    if items_review_medium > 0:
        return DOC_REVIEW_MEDIUM
    if cnae_alerts > 0:
        return DOC_REVIEW_MEDIUM
    
    # LOW
    return DOC_REVIEW_LOW


def _build_review_text_ptbr(
    *,
    doc_class: str,
    review_level: str,
    reasons: list[str],
    service_code: str | None,
    movement_type: str,
) -> str:
    """Gera texto explicativo em PT-BR para o gestor/operador."""
    base: list[str] = []
    
    # Classificação
    class_texts = {
        DOC_CLASS_SAUDE: "Nota sugerida como SERVIÇO DE SAÚDE.",
        DOC_CLASS_TECNICO: "Nota sugerida como SERVIÇO TÉCNICO.",
        DOC_CLASS_ADMIN: "Nota sugerida como SERVIÇO ADMINISTRATIVO.",
        DOC_CLASS_CONSULTORIA: "Nota sugerida como CONSULTORIA.",
        DOC_CLASS_MANUTENCAO: "Nota sugerida como MANUTENÇÃO.",
        DOC_CLASS_OUTROS: "Nota sugerida como OUTROS SERVIÇOS.",
        DOC_CLASS_MIXED: "Nota com TIPOS DE SERVIÇO MISTURADOS (exige decisão humana).",
    }
    base.append(class_texts.get(doc_class, "Não foi possível classificar a nota com segurança."))
    
    # Sugestão de lançamento
    if service_code:
        base.append(f"Sugestão de lançamento: movimento {movement_type} com código {service_code}.")
    else:
        base.append(f"Sugestão de lançamento: movimento {movement_type}.")
    
    base.append(f"Nível de revisão: {review_level}.")
    
    # Motivos principais
    top = _summarize_top_reasons(reasons, max_items=6)
    if top:
        base.append("Motivos: " + "; ".join(top) + ".")
    
    return " ".join(base)


def _build_next_actions_ptbr(doc_class: str) -> list[str]:
    """Gera lista de próximas ações recomendadas."""
    actions = [
        "Confirmar prestador e dados do serviço.",
        "Verificar retenções de impostos (ISS, PIS, COFINS, IR, CSLL, INSS).",
        "Conferir competência e datas.",
        "Validar centro de custo conforme regras internas.",
    ]
    
    if doc_class in (DOC_CLASS_MIXED, DOC_CLASS_UNKNOWN):
        actions.insert(0, "Decidir manualmente o tipo de serviço para classificação correta.")
    
    if doc_class == DOC_CLASS_SAUDE:
        actions.append("Verificar se há necessidade de classificação específica por tipo de atendimento.")
    
    return actions


# =============================================================================
# API Pública
# =============================================================================

def analyze_nfse_document(
    *,
    prestador: dict[str, Any],
    tomador: dict[str, Any],
    totals: dict[str, Any],
    summary: dict[str, Any],
    enriched_items: list[dict[str, Any]],
    thresholds: NfseDocumentThresholds | None = None,
    movement_type: str | None = None,
    service_code_saude: str | None = None,
    service_code_tecnico: str | None = None,
    service_code_outros: str | None = None,
    filial_by_tomador_doc: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Analisa documento NFS-e (nível nota inteira).
    
    Args:
        prestador: Dados do prestador
        tomador: Dados do tomador
        totals: Totais da nota
        summary: Sumário da extração
        enriched_items: Itens já normalizados
        thresholds: Limites para validação
        movement_type: Tipo de movimento ERP
        service_code_*: Códigos de serviço por classe
        filial_by_tomador_doc: Mapa CNPJ tomador -> código filial
        
    Returns:
        Dicionário com:
        - document: análise completa
        - erp_projection: projeção para ERP
        - document_summary: sumário para dashboards
    """
    # Defaults
    if thresholds is None:
        thresholds = NfseDocumentThresholds.from_settings()
    if movement_type is None:
        movement_type = getattr(settings, "erp_nfse_movement_type", "2.1.01")
    if service_code_saude is None:
        service_code_saude = getattr(settings, "erp_service_code_saude", "00010")
    if service_code_tecnico is None:
        service_code_tecnico = getattr(settings, "erp_service_code_tecnico", "00011")
    if service_code_outros is None:
        service_code_outros = getattr(settings, "erp_service_code_outros", "00012")
    
    reasons: list[str] = []
    
    # Contagem de itens
    count_items = len(enriched_items or [])
    if count_items == 0:
        reasons.append(REASON_DOC_NO_ITEMS)
    
    # Validação do prestador
    prestador_doc = (prestador or {}).get("doc") or (prestador or {}).get("doc_formatado")
    missing_prestador = not bool(prestador_doc)
    if missing_prestador:
        reasons.append(REASON_DOC_MISSING_PRESTADOR)
    
    # Validação de valor
    valor_total = safe_float(totals.get("valor_servicos") if totals else None)
    if valor_total is None:
        valor_total = safe_float(summary.get("sum_valor_total_politica_a") if summary else None)
    
    missing_valor = valor_total is None or valor_total <= 0
    if missing_valor:
        reasons.append(REASON_DOC_MISSING_VALOR)
    
    # Classificação por itens
    doc_class, class_meta = classify_nfse_document_from_items(enriched_items)
    if doc_class == DOC_CLASS_UNKNOWN:
        reasons.append(REASON_DOC_CANNOT_CLASSIFY)
    if doc_class == DOC_CLASS_MIXED:
        reasons.append(REASON_DOC_ITEMS_MIXED_CLASSES)
    
    # Qualidade dos itens
    count_item_incomplete = 0
    items_review_high = 0
    items_review_medium = 0
    cnae_alerts = 0
    has_liquido_divergente = False
    
    for row in enriched_items or []:
        flags = row.get("flags") or row.get("norm_flags") or {}
        if isinstance(flags, dict) and flags.get("incomplete") is True:
            count_item_incomplete += 1
        
        rl = (row.get("review_level") or "").strip().upper()
        if rl == "HIGH":
            items_review_high += 1
        elif rl == "MEDIUM":
            items_review_medium += 1
        
        # Verifica CNAE alerts
        item_reasons = row.get("reasons") or []
        if "CNAE_VS_DESCRICAO_ALERT" in item_reasons or "CNAE_ALERT" in item_reasons:
            cnae_alerts += 1
        
        # Verifica valor líquido divergente
        taxes = row.get("taxes") or {}
        if taxes.get("valor_liquido_divergente"):
            has_liquido_divergente = True
    
    if count_item_incomplete > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_INCOMPLETE)
    if items_review_high > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_REVIEW_HIGH)
    if items_review_medium > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_REVIEW_MEDIUM)
    if cnae_alerts > 0:
        reasons.append(REASON_DOC_CNAE_ALERTS)
    if has_liquido_divergente:
        reasons.append(REASON_DOC_VALOR_LIQUIDO_DIVERGENTE)
    
    reasons = dedup_keep_order(reasons)
    
    # Review level do documento
    review_level = _compute_review_level(
        missing_prestador=missing_prestador,
        missing_valor=missing_valor,
        has_liquido_divergente=has_liquido_divergente,
        doc_class=doc_class,
        count_items=count_items,
        count_incomplete=count_item_incomplete,
        items_review_high=items_review_high,
        items_review_medium=items_review_medium,
        cnae_alerts=cnae_alerts,
    )
    
    # Código de serviço sugerido
    service_code_map = {
        DOC_CLASS_SAUDE: service_code_saude,
        DOC_CLASS_TECNICO: service_code_tecnico,
        DOC_CLASS_ADMIN: service_code_outros,
        DOC_CLASS_CONSULTORIA: service_code_outros,
        DOC_CLASS_MANUTENCAO: service_code_outros,
        DOC_CLASS_OUTROS: service_code_outros,
    }
    service_code = service_code_map.get(doc_class)
    
    # Projeção ERP
    valor_liquido = safe_float(summary.get("sum_valor_liquido_politica_b") if summary else None)
    tomador_doc = (tomador or {}).get("doc") if isinstance(tomador, dict) else ""
    
    filial_code = None
    if filial_by_tomador_doc and tomador_doc:
        filial_code = filial_by_tomador_doc.get(tomador_doc)
    
    # Extrai dados do primeiro item para informações básicas
    first_item = enriched_items[0] if enriched_items else {}
    first_fields = first_item.get("fields") or {}
    first_taxes = first_item.get("taxes") or {}
    
    # Calcula retenções
    retencoes = {}
    tax_totals = summary.get("tax_totals") or {}
    if tax_totals.get("sum_valor_iss_retido"):
        retencoes["iss_retido"] = tax_totals["sum_valor_iss_retido"]
    if tax_totals.get("sum_valor_pis"):
        retencoes["pis"] = tax_totals["sum_valor_pis"]
    if tax_totals.get("sum_valor_cofins"):
        retencoes["cofins"] = tax_totals["sum_valor_cofins"]
    if tax_totals.get("sum_valor_inss"):
        retencoes["inss"] = tax_totals["sum_valor_inss"]
    if tax_totals.get("sum_valor_ir"):
        retencoes["ir"] = tax_totals["sum_valor_ir"]
    if tax_totals.get("sum_valor_csll"):
        retencoes["csll"] = tax_totals["sum_valor_csll"]
    
    erp_projection = {
        "movement_type": movement_type,
        "filial_code": filial_code,
        "supplier_doc": prestador_doc,
        "note_number": first_fields.get("numero_nota"),
        "competencia": first_fields.get("competencia"),
        "issue_datetime": first_fields.get("data_emissao"),
        "valor_bruto": valor_total,
        "valor_liquido": valor_liquido,
        "service_code": service_code,
        "cost_center_suggested": None,
        "payment_hint": "BOLETO (verificar condição de pagamento)",
        "rm_status_target": "PENDENTE/BLOQUEADO (depende de parametrização)",
        "retencoes": retencoes,
    }
    
    # Texto explicativo
    review_text_ptbr = _build_review_text_ptbr(
        doc_class=doc_class,
        review_level=review_level,
        reasons=reasons,
        service_code=service_code,
        movement_type=movement_type,
    )
    
    # Documento completo
    document = {
        "document_type": "NFSE",
        "doc_class": doc_class,
        "decision": DOC_DECISION_REVIEW,
        "review_level": review_level,
        "review_text_ptbr": review_text_ptbr,
        "reasons": reasons,
        "next_actions": _build_next_actions_ptbr(doc_class),
        "prestador": prestador or {},
        "tomador": tomador or {},
        "totals": totals or {},
        "quality": {
            "missing_fields": [],
            "diff_liquido_vs_calculated": None,
            "class_meta": class_meta,
            "items_review_high": items_review_high,
            "items_review_medium": items_review_medium,
            "items_incomplete": count_item_incomplete,
            "cnae_alerts": cnae_alerts,
        },
    }
    
    # Sumário para dashboards
    document_summary = {
        "doc_class": doc_class,
        "decision": DOC_DECISION_REVIEW,
        "review_level": review_level,
        "review_text_ptbr": review_text_ptbr,
        "top_reasons": _summarize_top_reasons(reasons, max_items=8),
        "kpis": {
            "items": count_items,
            "valor_bruto": valor_total,
            "valor_liquido": valor_liquido,
        },
    }
    
    return {
        "document": document,
        "erp_projection": erp_projection,
        "document_summary": document_summary,
    }
