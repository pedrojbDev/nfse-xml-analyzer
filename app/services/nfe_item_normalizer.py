# app/services/nfe_item_normalizer.py
"""
Serviço de normalização de itens de NF-e.

Responsável por:
- Classificar itens (MEDICAMENTO, MATERIAL_HOSPITALAR, GENERICO)
- Validar qualidade dos dados
- Gerar reasons e review_level para cada item
- Produzir explicações auditáveis em PT-BR
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.utils.converters import (
    calculate_expected_vprod,
    is_positive_number,
    normalize_text_or_none,
    safe_float,
    sanitize_product_code,
)


# =============================================================================
# Reasons (strings estáveis para BI e auditoria)
# =============================================================================

# Campos ausentes
REASON_NCM_MISSING = "NCM_MISSING"
REASON_CFOP_MISSING = "CFOP_MISSING"
REASON_PRODUCT_CODE_MISSING = "PRODUCT_CODE_MISSING"
REASON_PRODUCT_DESC_MISSING = "PRODUCT_DESC_MISSING"
REASON_QTY_OR_PRICE_MISSING = "QTY_OR_PRICE_MISSING"
REASON_TOTAL_ITEM_INVALID = "ITEM_TOTAL_INVALID"

# Classificação por evidência
REASON_CLASS_MED_BY_NCM = "CLASS_MEDICAMENTO_BY_NCM"
REASON_CLASS_MED_BY_KEYWORD = "CLASS_MEDICAMENTO_BY_KEYWORD"
REASON_CLASS_MATERIAL_BY_NCM = "CLASS_MATERIAL_BY_NCM"
REASON_CLASS_MATERIAL_BY_KEYWORD = "CLASS_MATERIAL_BY_KEYWORD"
REASON_CLASS_GENERIC_FALLBACK = "CLASS_GENERIC_FALLBACK"

# NCMs de MEDICAMENTOS (capítulo 30 e outros farmacêuticos)
NCM_MEDICAMENTO_PREFIXES = (
    "3001",  # Glândulas e outros órgãos para usos opoterápicos
    "3002",  # Sangue humano, sangue animal, antissoros, vacinas
    "3003",  # Medicamentos não condicionados para venda a retalho
    "3004",  # Medicamentos condicionados para venda a retalho
    "3005",  # Algodão, gazes, ataduras (inclui curativos medicamentosos)
    "3006",  # Preparações e artigos farmacêuticos (categute, adesivos dentários, etc.)
)

# NCMs de MATERIAL HOSPITALAR (seringas, instrumentais, luvas, etc.)
NCM_MATERIAL_PREFIXES = (
    # Capítulo 90 - Instrumentos e aparelhos médicos
    "9018",  # Instrumentos e aparelhos para medicina, cirurgia, odontologia, veterinária
    "901831",  # Seringas
    "901832",  # Agulhas
    "901839",  # Outros (cateteres, cânulas, etc.)
    "9019",  # Aparelhos de mecanoterapia, massagem, psicotécnicos
    "9021",  # Artigos e aparelhos ortopédicos, talas, muletas
    "9022",  # Aparelhos de raios X
    "9027",  # Instrumentos para análises físicas ou químicas
    # Capítulo 40 - Borracha e suas obras
    "4014",  # Artigos de higiene ou farmácia de borracha
    "4015",  # Vestuário e acessórios de borracha vulcanizada (luvas)
    "401511",  # Luvas para cirurgia
    "401519",  # Outras luvas
    # Capítulo 39 - Plásticos e suas obras
    "3923",  # Artigos de transporte/embalagem de plástico (frascos, seringas plásticas)
    "3926",  # Outras obras de plástico (artigos para laboratório, hospitalar)
    # Outros
    "4818",  # Papel higiênico, fraldas, absorventes
    "5601",  # Pasta de celulose (algodão hidrófilo)
    "6210",  # Vestuário de falso tecido (aventais descartáveis)
    "6307",  # Outros artigos confeccionados (campos cirúrgicos)
    "8419",  # Aparelhos para tratamento de matérias (esterilizadores, autoclaves)
    "7017",  # Artigos de vidro para laboratório
    # NCMs específicos
    "22072019",  # Álcool 70%
    "27111910",  # GLP (não é material hospitalar, mas comum em notas hospitalares)
)

# Níveis de revisão (sempre REVIEW como decisão, mas com severidade)
REVIEW_LEVEL_LOW = "LOW"
REVIEW_LEVEL_MEDIUM = "MEDIUM"
REVIEW_LEVEL_HIGH = "HIGH"

# Decisão (por requisito: tudo REVIEW)
DECISION_REVIEW = "REVIEW"

# Classes de produto (nível item)
CLASS_MEDICAMENTO = "MEDICAMENTO"
CLASS_MATERIAL = "MATERIAL_HOSPITALAR"
CLASS_GENERICO = "GENERICO"


# =============================================================================
# Classificação
# =============================================================================

def _classify_by_ncm_and_keywords(
    ncm: str | None,
    xprod: str | None,
) -> tuple[str, list[str]]:
    """
    Classifica item com base em NCM e keywords na descrição.
    
    Heurística (ordem de prioridade):
    1. NCM de MATERIAL_HOSPITALAR (ex: 9018, 4015, etc.) => MATERIAL_HOSPITALAR
    2. NCM de MEDICAMENTO (ex: 30xx) => MEDICAMENTO
    3. Keywords de MATERIAL_HOSPITALAR na descrição => MATERIAL_HOSPITALAR
    4. Keywords de MEDICAMENTO na descrição => MEDICAMENTO
    5. Fallback => GENERICO
    
    Args:
        ncm: Código NCM do produto
        xprod: Descrição do produto
        
    Returns:
        Tupla (classe, lista de reasons)
    """
    reasons: list[str] = []
    
    # Extrai apenas dígitos do NCM
    ncm_digits = "".join(c for c in (ncm or "") if c.isdigit())
    
    # Descrição em maiúsculas para comparação
    xp = (xprod or "").upper()
    
    # Carrega keywords
    material_keywords = settings.material_keywords_list
    medicamento_keywords = settings.medicamento_keywords_list
    
    # ========================================================================
    # 1) Verifica NCM de MATERIAL HOSPITALAR primeiro (mais específico)
    # ========================================================================
    # NCMs de material hospitalar são muito específicos (seringas, luvas, etc.)
    for prefix in NCM_MATERIAL_PREFIXES:
        if ncm_digits.startswith(prefix):
            reasons.append(REASON_CLASS_MATERIAL_BY_NCM)
            return CLASS_MATERIAL, reasons
    
    # ========================================================================
    # 2) Verifica NCM de MEDICAMENTO
    # ========================================================================
    for prefix in NCM_MEDICAMENTO_PREFIXES:
        if ncm_digits.startswith(prefix):
            # NCM 3005 e 3006 podem ser materiais ou medicamentos
            # Usa heurística adicional pela descrição
            if prefix in ("3005", "3006"):
                # Se descrição indica material, classifica como material
                if any(k in xp for k in material_keywords):
                    reasons.append(REASON_CLASS_MATERIAL_BY_KEYWORD)
                    return CLASS_MATERIAL, reasons
            reasons.append(REASON_CLASS_MED_BY_NCM)
            return CLASS_MEDICAMENTO, reasons
    
    # ========================================================================
    # 3) Keywords de MATERIAL HOSPITALAR na descrição
    # ========================================================================
    if any(k in xp for k in material_keywords):
        reasons.append(REASON_CLASS_MATERIAL_BY_KEYWORD)
        return CLASS_MATERIAL, reasons
    
    # ========================================================================
    # 4) Keywords de MEDICAMENTO na descrição
    # ========================================================================
    if any(k in xp for k in medicamento_keywords):
        reasons.append(REASON_CLASS_MED_BY_KEYWORD)
        return CLASS_MEDICAMENTO, reasons
    
    # ========================================================================
    # 5) Fallback - não conseguiu classificar
    # ========================================================================
    reasons.append(REASON_CLASS_GENERIC_FALLBACK)
    return CLASS_GENERICO, reasons


def _review_level_from_reasons(
    reasons: list[str],
    flags: dict[str, Any],
) -> str:
    """
    Determina nível de revisão baseado nos reasons.
    
    HIGH: faltam chaves fiscais mínimas, ou item sem descrição/código
    MEDIUM: total divergente, qty/preço ausente
    LOW: apenas classificação por heurística / cadastro pendente
    """
    high_reasons = {
        REASON_PRODUCT_CODE_MISSING,
        REASON_PRODUCT_DESC_MISSING,
        REASON_NCM_MISSING,
        REASON_CFOP_MISSING,
    }
    
    if any(r in high_reasons for r in reasons):
        return REVIEW_LEVEL_HIGH
    
    if flags.get("has_minimum_fiscal_keys") is False:
        return REVIEW_LEVEL_HIGH
    
    medium_reasons = {
        REASON_TOTAL_ITEM_INVALID,
        REASON_QTY_OR_PRICE_MISSING,
    }
    
    if any(r in medium_reasons for r in reasons):
        return REVIEW_LEVEL_MEDIUM
    
    return REVIEW_LEVEL_LOW


def _build_review_text_ptbr(product_class: str, reasons: list[str]) -> str:
    """
    Gera texto explicativo em PT-BR para o operador.
    """
    parts: list[str] = []
    
    # Classificação com base na evidência
    if REASON_CLASS_MED_BY_NCM in reasons:
        parts.append("Classificação: MEDICAMENTO (NCM de farmacêutico identificado).")
    elif REASON_CLASS_MED_BY_KEYWORD in reasons:
        parts.append("Classificação: MEDICAMENTO (descrição contém termos farmacêuticos).")
    elif REASON_CLASS_MATERIAL_BY_NCM in reasons:
        parts.append("Classificação: MATERIAL HOSPITALAR (NCM de instrumentos/dispositivos médicos).")
    elif REASON_CLASS_MATERIAL_BY_KEYWORD in reasons:
        parts.append("Classificação: MATERIAL HOSPITALAR (descrição contém termos de materiais).")
    elif product_class == CLASS_MEDICAMENTO:
        parts.append("Classificação sugerida: MEDICAMENTO.")
    elif product_class == CLASS_MATERIAL:
        parts.append("Classificação sugerida: MATERIAL HOSPITALAR.")
    else:
        parts.append("Classificação: GENÉRICO (não foi possível identificar como medicamento ou material).")
    
    # Alertas por reason
    if REASON_NCM_MISSING in reasons or REASON_CFOP_MISSING in reasons:
        parts.append("Faltam chaves fiscais (NCM/CFOP) — conferir XML.")
    
    if REASON_PRODUCT_CODE_MISSING in reasons or REASON_PRODUCT_DESC_MISSING in reasons:
        parts.append("Faltam dados básicos do item (código/descrição) — conferir XML.")
    
    if REASON_TOTAL_ITEM_INVALID in reasons:
        parts.append("Total do item (vProd) não bate com qCom × vUnCom — conferir.")
    
    if REASON_QTY_OR_PRICE_MISSING in reasons:
        parts.append("Quantidade ou preço unitário ausente/zero — conferir.")
    
    return " ".join(parts)


# =============================================================================
# API Pública
# =============================================================================

def normalize_nfe_item(
    item: dict[str, Any],
    *,
    vprod_tolerance: float | None = None,
) -> dict[str, Any]:
    """
    Normaliza UM item de NF-e.
    
    Args:
        item: Dicionário com dados do item
        vprod_tolerance: Tolerância para divergência de vProd (padrão: config)
        
    Returns:
        Dicionário com:
        - item: dados sanitizados
        - normalized: product_class, suggested_group
        - decision: sempre REVIEW
        - reasons: lista estável de códigos
        - norm_flags: flags úteis para UI/dash
        - review_level: LOW/MEDIUM/HIGH
        - review_text_ptbr: explicação
    """
    if vprod_tolerance is None:
        vprod_tolerance = settings.item_vprod_tolerance
    
    reasons: list[str] = []
    norm_flags: dict[str, Any] = {}
    
    # Copia para não modificar original
    it = dict(item or {})
    
    # Sanitizações pontuais
    it["cProd"] = sanitize_product_code(it.get("cProd"))
    it["xProd"] = normalize_text_or_none(it.get("xProd"))
    it["NCM"] = normalize_text_or_none(it.get("NCM"))
    it["CFOP"] = normalize_text_or_none(it.get("CFOP"))
    
    cProd = it.get("cProd")
    xProd = it.get("xProd")
    ncm = it.get("NCM")
    cfop = it.get("CFOP")
    qCom = it.get("qCom")
    vUnCom = it.get("vUnCom")
    vProd = it.get("vProd")
    
    # Validação de qualidade mínima
    if not cProd:
        reasons.append(REASON_PRODUCT_CODE_MISSING)
    if not xProd:
        reasons.append(REASON_PRODUCT_DESC_MISSING)
    if not ncm:
        reasons.append(REASON_NCM_MISSING)
    if not cfop:
        reasons.append(REASON_CFOP_MISSING)
    
    if not is_positive_number(qCom) or not is_positive_number(vUnCom):
        reasons.append(REASON_QTY_OR_PRICE_MISSING)
    
    # Consistência vProd
    expected = calculate_expected_vprod(qCom, vUnCom)
    norm_flags["expected_vProd"] = expected
    
    fvprod = safe_float(vProd)
    if expected is not None and fvprod is not None:
        diff = round(fvprod - expected, 2)
        norm_flags["diff_vProd_vs_expected"] = diff
        
        if abs(diff) > float(vprod_tolerance):
            reasons.append(REASON_TOTAL_ITEM_INVALID)
            norm_flags["vProd_invalid"] = True
        else:
            norm_flags["vProd_invalid"] = False
    else:
        norm_flags["diff_vProd_vs_expected"] = None
        norm_flags["vProd_invalid"] = False
    
    # Flags úteis para UI/revisão
    norm_flags["has_minimum_fiscal_keys"] = bool(ncm) and bool(cfop)
    norm_flags["requires_product_registration"] = True  # sempre item genérico no RM
    
    # Classificação
    product_class, class_reasons = _classify_by_ncm_and_keywords(ncm, xProd)
    
    # Adiciona reasons de classificação sem duplicar
    for r in class_reasons:
        if r not in reasons:
            reasons.append(r)
    
    normalized = {
        "product_class": product_class,
        "suggested_group": product_class,
    }
    
    # Decisão e explicação
    review_level = _review_level_from_reasons(reasons, norm_flags)
    review_text_ptbr = _build_review_text_ptbr(product_class, reasons)
    
    return {
        "item": it,
        "normalized": normalized,
        "decision": DECISION_REVIEW,
        "reasons": reasons,
        "norm_flags": norm_flags,
        "review_level": review_level,
        "review_text_ptbr": review_text_ptbr,
    }


def normalize_nfe_items(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Normaliza uma lista de itens no formato do extractor.
    
    Args:
        rows: Lista de dicts com formato:
            { item: {...}, confidence, missing_fields, ... }
    
    Returns:
        Tupla:
        - rows_enriched: lista com normalized/decision/reasons/etc mesclados
        - summary: agregações para dashboard
    """
    enriched: list[dict[str, Any]] = []
    
    # Contadores
    count_review = 0
    count_missing_ncm = 0
    count_missing_cfop = 0
    count_total_invalid = 0
    
    review_high = 0
    review_medium = 0
    review_low = 0
    
    for row in rows or []:
        base_row = dict(row or {})
        it = (base_row.get("item") or {}) if isinstance(base_row, dict) else {}
        
        out = normalize_nfe_item(it)
        
        # Mescla resultado na row
        base_row["item"] = out["item"]
        base_row["normalized"] = out["normalized"]
        base_row["decision"] = out["decision"]
        base_row["reasons"] = out["reasons"]
        base_row["norm_flags"] = out["norm_flags"]
        base_row["review_level"] = out["review_level"]
        base_row["review_text_ptbr"] = out["review_text_ptbr"]
        
        enriched.append(base_row)
        count_review += 1
        
        # Contagens
        if REASON_NCM_MISSING in out["reasons"]:
            count_missing_ncm += 1
        if REASON_CFOP_MISSING in out["reasons"]:
            count_missing_cfop += 1
        if REASON_TOTAL_ITEM_INVALID in out["reasons"]:
            count_total_invalid += 1
        
        if out["review_level"] == REVIEW_LEVEL_HIGH:
            review_high += 1
        elif out["review_level"] == REVIEW_LEVEL_MEDIUM:
            review_medium += 1
        else:
            review_low += 1
    
    summary = {
        "decision_summary": {
            "review": count_review,
        },
        "quality_summary": {
            "missing_ncm": count_missing_ncm,
            "missing_cfop": count_missing_cfop,
            "item_total_invalid": count_total_invalid,
        },
        "review_summary": {
            "high": review_high,
            "medium": review_medium,
            "low": review_low,
        },
    }
    
    return enriched, summary
