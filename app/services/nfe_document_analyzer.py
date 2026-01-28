# app/services/nfe_document_analyzer.py
"""
Serviço de análise de documentos NF-e (nível nota inteira).

Responsável por:
- Classificar o documento com base nos itens normalizados
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
    percent_diff,
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
DOC_CLASS_MEDICAMENTO = "MEDICAMENTO"
DOC_CLASS_MATERIAL_HOSP = "MATERIAL_HOSPITALAR"
DOC_CLASS_GENERICO = "GENERICO"
DOC_CLASS_MIXED = "MIXED"
DOC_CLASS_UNKNOWN = "UNKNOWN"

# Reasons padronizados (strings estáveis para dashboard/BI)
REASON_DOC_NO_ITEMS = "DOC_NO_ITEMS"
REASON_DOC_MISSING_HEADER_KEYS = "DOC_MISSING_HEADER_KEYS"
REASON_DOC_TOTAL_DIVERGENCE = "DOC_TOTAL_DIVERGENCE"
REASON_DOC_ITEMS_MIXED_CLASSES = "DOC_ITEMS_MIXED_CLASSES"
REASON_DOC_ITEMS_HAVE_INCOMPLETE = "DOC_ITEMS_INCOMPLETE"
REASON_DOC_CANNOT_CLASSIFY = "DOC_CANNOT_CLASSIFY"
REASON_DOC_ITEMS_HAVE_REVIEW_HIGH = "DOC_ITEMS_HAVE_REVIEW_HIGH"
REASON_DOC_ITEMS_HAVE_REVIEW_MEDIUM = "DOC_ITEMS_HAVE_REVIEW_MEDIUM"


@dataclass(frozen=True)
class DocumentThresholds:
    """
    Thresholds para divergência de totais.
    
    Attributes:
        vprod_abs: Diferença absoluta máxima em reais
        vprod_pct: Diferença percentual máxima
    """
    vprod_abs: float = 0.10   # R$ 0,10
    vprod_pct: float = 0.001  # 0,1%
    
    @classmethod
    def from_settings(cls) -> "DocumentThresholds":
        """Cria instância a partir das configurações."""
        return cls(
            vprod_abs=settings.doc_vprod_abs_threshold,
            vprod_pct=settings.doc_vprod_pct_threshold,
        )


# =============================================================================
# Helpers
# =============================================================================

def _summarize_top_reasons(reasons: list[str], max_items: int = 8) -> list[str]:
    """Retorna os primeiros N reasons únicos."""
    return dedup_keep_order(reasons)[:max_items]


def _normalize_doc_class(pc: str) -> str:
    """Normaliza classe de produto para comparação."""
    p = (pc or "").strip().upper()
    if p in (DOC_CLASS_MEDICAMENTO, DOC_CLASS_MATERIAL_HOSP, DOC_CLASS_GENERICO):
        return p
    return ""


# =============================================================================
# Classificação do documento
# =============================================================================

def classify_nfe_document_from_items(
    enriched_items: list[dict[str, Any]],
    majority_threshold: float = 0.6,
) -> tuple[str, dict[str, Any]]:
    """
    Classifica documento com base nas classes dos itens normalizados.
    
    Regras (ordem de prioridade):
    1. Se todos itens específicos (MEDICAMENTO ou MATERIAL) são da mesma classe -> essa classe
    2. Se uma classe específica representa >= majority_threshold dos itens específicos -> essa classe
    3. Se há mistura significativa de classes específicas -> MIXED
    4. Se só há GENERICO -> GENERICO
    5. Se não há itens -> UNKNOWN
    
    Nota: GENERICO é tratado como "não classificado", então não conta para determinar MIXED.
    Uma nota só é MIXED se tiver tanto MEDICAMENTO quanto MATERIAL_HOSPITALAR em proporções similares.
    
    Args:
        enriched_items: Itens já normalizados
        majority_threshold: Proporção mínima para considerar classe predominante (padrão: 60%)
        
    Returns:
        Tupla (classe_documento, metadados)
    """
    classes_seen = {
        DOC_CLASS_MEDICAMENTO: 0,
        DOC_CLASS_MATERIAL_HOSP: 0,
        DOC_CLASS_GENERICO: 0,
        "OTHER": 0,
        "UNKNOWN": 0,
    }
    
    for row in enriched_items or []:
        norm = (row.get("normalized") or {}) if isinstance(row, dict) else {}
        pc_raw = norm.get("product_class") or ""
        pc = _normalize_doc_class(pc_raw)
        
        if pc == DOC_CLASS_MEDICAMENTO:
            classes_seen[DOC_CLASS_MEDICAMENTO] += 1
        elif pc == DOC_CLASS_MATERIAL_HOSP:
            classes_seen[DOC_CLASS_MATERIAL_HOSP] += 1
        elif pc == DOC_CLASS_GENERICO:
            classes_seen[DOC_CLASS_GENERICO] += 1
        elif pc_raw:
            classes_seen["OTHER"] += 1
        else:
            classes_seen["UNKNOWN"] += 1
    
    total_items = sum(classes_seen.values())
    meta = {"classes_seen": classes_seen}
    
    if total_items == 0:
        return DOC_CLASS_UNKNOWN, meta
    
    # Contagem de itens específicos (MEDICAMENTO + MATERIAL_HOSPITALAR)
    count_med = classes_seen[DOC_CLASS_MEDICAMENTO]
    count_mat = classes_seen[DOC_CLASS_MATERIAL_HOSP]
    count_gen = classes_seen[DOC_CLASS_GENERICO]
    
    total_specific = count_med + count_mat
    
    # Se não há itens específicos, verifica se há genéricos
    if total_specific == 0:
        if count_gen > 0:
            return DOC_CLASS_GENERICO, meta
        return DOC_CLASS_UNKNOWN, meta
    
    # Calcula proporções apenas entre itens específicos
    # (GENERICO não influencia a decisão MIXED vs específico)
    pct_med = count_med / total_specific if total_specific > 0 else 0
    pct_mat = count_mat / total_specific if total_specific > 0 else 0
    
    meta["pct_medicamento"] = round(pct_med, 3)
    meta["pct_material"] = round(pct_mat, 3)
    
    # Se só tem uma classe específica, usa ela
    if count_med == 0 and count_mat > 0:
        return DOC_CLASS_MATERIAL_HOSP, meta
    if count_mat == 0 and count_med > 0:
        return DOC_CLASS_MEDICAMENTO, meta
    
    # Há ambas as classes - verifica se uma é majoritária
    if pct_mat >= majority_threshold:
        return DOC_CLASS_MATERIAL_HOSP, meta
    if pct_med >= majority_threshold:
        return DOC_CLASS_MEDICAMENTO, meta
    
    # Mistura significativa de ambas as classes
    return DOC_CLASS_MIXED, meta


# =============================================================================
# Review level e texto PT-BR
# =============================================================================

def _compute_review_level(
    *,
    missing_header: list[str],
    has_total_divergence: bool,
    doc_class: str,
    count_items: int,
    count_incomplete: int,
    items_review_high: int,
    items_review_medium: int,
) -> str:
    """
    Determina nível de revisão do documento.
    
    HIGH: forte chance de erro / precisa decisão humana
    MEDIUM: faltas ou sinais que precisam checagem
    LOW: "lançável" no modo genérico, só validação final
    """
    # HIGH
    if doc_class in (DOC_CLASS_MIXED, DOC_CLASS_UNKNOWN):
        return DOC_REVIEW_HIGH
    if count_items == 0:
        return DOC_REVIEW_HIGH
    if has_total_divergence:
        return DOC_REVIEW_HIGH
    
    # MEDIUM
    if len(missing_header) > 0:
        return DOC_REVIEW_MEDIUM
    if count_incomplete > 0:
        return DOC_REVIEW_MEDIUM
    if items_review_high > 0:
        return DOC_REVIEW_MEDIUM
    if items_review_medium > 0:
        return DOC_REVIEW_MEDIUM
    
    # LOW
    return DOC_REVIEW_LOW


def _build_review_text_ptbr(
    *,
    doc_class: str,
    review_level: str,
    reasons: list[str],
    product_code: str | None,
    movement_type: str,
) -> str:
    """Gera texto explicativo em PT-BR para o gestor/operador."""
    base: list[str] = []
    
    # Classificação
    class_texts = {
        DOC_CLASS_MATERIAL_HOSP: "Nota sugerida como MATERIAL HOSPITALAR.",
        DOC_CLASS_MEDICAMENTO: "Nota sugerida como MEDICAMENTO.",
        DOC_CLASS_GENERICO: "Nota sugerida como GENÉRICO (sem evidência suficiente para medicamento/material).",
        DOC_CLASS_MIXED: "Nota com CLASSES MISTURADAS (exige decisão humana: medicamento vs material vs genérico).",
    }
    base.append(class_texts.get(doc_class, "Não foi possível classificar a nota com segurança."))
    
    # Sugestão de lançamento
    if product_code:
        base.append(f"Sugestão de lançamento: movimento {movement_type} com item genérico {product_code}.")
    else:
        base.append(f"Sugestão de lançamento: movimento {movement_type} com item genérico a definir.")
    
    base.append(f"Nível de revisão: {review_level}.")
    
    # Motivos principais
    top = _summarize_top_reasons(reasons, max_items=6)
    if top:
        base.append("Motivos: " + "; ".join(top) + ".")
    
    return " ".join(base)


def _build_next_actions_ptbr(doc_class: str) -> list[str]:
    """Gera lista de próximas ações recomendadas."""
    actions = [
        "Confirmar destinatário/unidade alvo (nota pode ser de uma filial específica).",
        "Confirmar datas (Emissão, Entrada, Competência).",
        "Conferir condição de pagamento (BOLETO; parcelamento/prazos podem exigir ajuste manual).",
        "Validar centro de custo conforme unidade/padrão interno.",
    ]
    
    if doc_class in (DOC_CLASS_MIXED, DOC_CLASS_UNKNOWN):
        actions.insert(0, "Decidir manualmente a natureza da nota (Medicamento vs Material vs Genérico).")
    
    return actions


# =============================================================================
# API Pública
# =============================================================================

def analyze_nfe_document(
    *,
    header: dict[str, Any],
    emit: dict[str, Any],
    dest: dict[str, Any],
    totals: dict[str, Any],
    summary: dict[str, Any],
    enriched_items: list[dict[str, Any]],
    thresholds: DocumentThresholds | None = None,
    movement_type: str | None = None,
    product_code_medicamento: str | None = None,
    product_code_material: str | None = None,
    product_code_generico: str | None = None,
    filial_by_dest_doc: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Analisa documento NF-e (nível nota inteira).
    
    Args:
        header: Cabeçalho da nota
        emit: Dados do emitente
        dest: Dados do destinatário
        totals: Totais da nota
        summary: Sumário da extração
        enriched_items: Itens já normalizados
        thresholds: Limites para validação (padrão: config)
        movement_type: Tipo de movimento ERP (padrão: config)
        product_code_*: Códigos de produto por classe (padrão: config)
        filial_by_dest_doc: Mapa CNPJ destinatário -> código filial
        
    Returns:
        Dicionário com:
        - document: análise completa
        - erp_projection: projeção para ERP
        - document_summary: sumário para dashboards
    """
    # Defaults do config
    if thresholds is None:
        thresholds = DocumentThresholds.from_settings()
    if movement_type is None:
        movement_type = settings.erp_movement_type
    if product_code_medicamento is None:
        product_code_medicamento = settings.erp_product_code_medicamento
    if product_code_material is None:
        product_code_material = settings.erp_product_code_material
    if product_code_generico is None:
        product_code_generico = settings.erp_product_code_generico
    
    reasons: list[str] = []
    
    # Contagem de itens
    count_items = len(enriched_items or [])
    if count_items == 0:
        reasons.append(REASON_DOC_NO_ITEMS)
    
    # Header mínimo
    required_header = ("chave_nfe", "numero", "serie", "data_emissao")
    missing_header = [k for k in required_header if not (header or {}).get(k)]
    if missing_header:
        reasons.append(REASON_DOC_MISSING_HEADER_KEYS)
    
    # Classificação por itens
    doc_class, class_meta = classify_nfe_document_from_items(enriched_items)
    if doc_class == DOC_CLASS_UNKNOWN:
        reasons.append(REASON_DOC_CANNOT_CLASSIFY)
    if doc_class == DOC_CLASS_MIXED:
        reasons.append(REASON_DOC_ITEMS_MIXED_CLASSES)
    
    # Qualidade dos itens
    count_item_incomplete = 0
    items_review_high = 0
    items_review_medium = 0
    
    for row in enriched_items or []:
        flags = row.get("flags") or {}
        if isinstance(flags, dict) and flags.get("incomplete") is True:
            count_item_incomplete += 1
        
        rl = (row.get("review_level") or "").strip().upper()
        if rl == "HIGH":
            items_review_high += 1
        elif rl == "MEDIUM":
            items_review_medium += 1
    
    if count_item_incomplete > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_INCOMPLETE)
    if items_review_high > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_REVIEW_HIGH)
    if items_review_medium > 0:
        reasons.append(REASON_DOC_ITEMS_HAVE_REVIEW_MEDIUM)
    
    # Divergência de totais
    diff_vprod = safe_float((summary or {}).get("diff_items_vs_total_vProd"))
    total_vprod = safe_float((totals or {}).get("vProd"))
    
    has_total_divergence = False
    if diff_vprod is not None and total_vprod is not None:
        abs_ok = abs(diff_vprod) <= thresholds.vprod_abs
        pct_ok = percent_diff(total_vprod, total_vprod + diff_vprod) <= thresholds.vprod_pct
        
        if (not abs_ok) and (not pct_ok):
            has_total_divergence = True
            reasons.append(REASON_DOC_TOTAL_DIVERGENCE)
    
    reasons = dedup_keep_order(reasons)
    
    # Review level do documento
    review_level = _compute_review_level(
        missing_header=missing_header,
        has_total_divergence=has_total_divergence,
        doc_class=doc_class,
        count_items=count_items,
        count_incomplete=count_item_incomplete,
        items_review_high=items_review_high,
        items_review_medium=items_review_medium,
    )
    
    # Produto sugerido
    product_code_map = {
        DOC_CLASS_MEDICAMENTO: product_code_medicamento,
        DOC_CLASS_MATERIAL_HOSP: product_code_material,
        DOC_CLASS_GENERICO: product_code_generico,
    }
    product_code = product_code_map.get(doc_class)
    
    # Projeção ERP
    vnf = safe_float((totals or {}).get("vNF"))
    dest_doc = ((dest or {}).get("doc") or "").strip() if isinstance(dest, dict) else ""
    
    filial_code = None
    if filial_by_dest_doc and dest_doc:
        filial_code = filial_by_dest_doc.get(dest_doc)
    
    erp_projection = {
        "movement_type": movement_type,
        "filial_code": filial_code,
        "supplier_doc": (emit or {}).get("doc"),
        "note_number": (header or {}).get("numero"),
        "note_serie": (header or {}).get("serie"),
        "issue_datetime": (header or {}).get("data_emissao"),
        "quantity": 1,
        "unit_value": vnf,
        "total_value": vnf,
        "product_code": product_code,
        "cost_center_suggested": None,
        "payment_hint": "BOLETO (manual se parcelado/condição variar)",
        "rm_status_target": "PENDENTE/BLOQUEADO (depende de parametrização do RM)",
    }
    
    # Texto explicativo
    review_text_ptbr = _build_review_text_ptbr(
        doc_class=doc_class,
        review_level=review_level,
        reasons=reasons,
        product_code=product_code,
        movement_type=movement_type,
    )
    
    # Documento completo
    document = {
        "document_type": "NFE",
        "doc_class": doc_class,
        "decision": DOC_DECISION_REVIEW,
        "review_level": review_level,
        "review_text_ptbr": review_text_ptbr,
        "reasons": reasons,
        "next_actions": _build_next_actions_ptbr(doc_class),
        "header": header or {},
        "emit": emit or {},
        "dest": dest or {},
        "totals": totals or {},
        "quality": {
            "missing_header_keys": missing_header,
            "diff_items_vs_total_vProd": diff_vprod,
            "class_meta": class_meta,
            "items_review_high": items_review_high,
            "items_review_medium": items_review_medium,
            "items_incomplete": count_item_incomplete,
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
            "vNF": vnf,
            "vProd": total_vprod,
            "diff_items_vs_total_vProd": diff_vprod,
        },
    }
    
    return {
        "document": document,
        "erp_projection": erp_projection,
        "document_summary": document_summary,
    }
