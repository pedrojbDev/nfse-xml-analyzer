# app/services/nfse_service_normalizer.py
"""
Serviço de normalização de serviços NFS-e.

Responsável por:
- Classificar serviços por CNAE (grupos de serviço)
- Classificar por keywords na descrição
- Validar qualidade dos dados
- Gerar reasons e review_level para cada item
- Produzir explicações auditáveis em PT-BR
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.cnae_rules import validate_cnae_vs_descricao


# =============================================================================
# Reasons (strings estáveis para BI e auditoria)
# =============================================================================

# Campos ausentes
REASON_CNAE_MISSING = "CNAE_MISSING"
REASON_VALOR_MISSING = "VALOR_MISSING"
REASON_COMPETENCIA_MISSING = "COMPETENCIA_MISSING"
REASON_NUMERO_MISSING = "NUMERO_NOTA_MISSING"
REASON_CNPJ_MISSING = "CNPJ_FORNECEDOR_MISSING"
REASON_DESCRICAO_MISSING = "DESCRICAO_SERVICO_MISSING"

# Problemas de valor
REASON_VALOR_LIQUIDO_DIVERGENTE = "VALOR_LIQUIDO_DIVERGENTE"
REASON_VALOR_NEGATIVO = "VALOR_NEGATIVO"

# Problemas de CNAE
REASON_CNAE_ALERT = "CNAE_VS_DESCRICAO_ALERT"
REASON_CNAE_UNKNOWN = "CNAE_VS_DESCRICAO_UNKNOWN"

# Classificação por evidência
REASON_CLASS_SAUDE_BY_CNAE = "CLASS_SAUDE_BY_CNAE"
REASON_CLASS_SAUDE_BY_KEYWORD = "CLASS_SAUDE_BY_KEYWORD"
REASON_CLASS_TECNICO_BY_CNAE = "CLASS_TECNICO_BY_CNAE"
REASON_CLASS_TECNICO_BY_KEYWORD = "CLASS_TECNICO_BY_KEYWORD"
REASON_CLASS_ADMIN_BY_CNAE = "CLASS_ADMIN_BY_CNAE"
REASON_CLASS_ADMIN_BY_KEYWORD = "CLASS_ADMIN_BY_KEYWORD"
REASON_CLASS_CONSULTORIA_BY_CNAE = "CLASS_CONSULTORIA_BY_CNAE"
REASON_CLASS_CONSULTORIA_BY_KEYWORD = "CLASS_CONSULTORIA_BY_KEYWORD"
REASON_CLASS_MANUTENCAO_BY_CNAE = "CLASS_MANUTENCAO_BY_CNAE"
REASON_CLASS_MANUTENCAO_BY_KEYWORD = "CLASS_MANUTENCAO_BY_KEYWORD"
REASON_CLASS_OUTROS_FALLBACK = "CLASS_OUTROS_FALLBACK"

# Níveis de revisão
REVIEW_LEVEL_LOW = "LOW"
REVIEW_LEVEL_MEDIUM = "MEDIUM"
REVIEW_LEVEL_HIGH = "HIGH"

# Decisão (por requisito: tudo REVIEW para NFS-e também)
DECISION_REVIEW = "REVIEW"

# Classes de serviço
CLASS_SAUDE = "SERVICO_SAUDE"
CLASS_TECNICO = "SERVICO_TECNICO"
CLASS_ADMIN = "SERVICO_ADMINISTRATIVO"
CLASS_CONSULTORIA = "SERVICO_CONSULTORIA"
CLASS_MANUTENCAO = "SERVICO_MANUTENCAO"
CLASS_OUTROS = "OUTROS"


# =============================================================================
# Mapeamento CNAE para Classes de Serviço
# =============================================================================

# CNAEs de SAÚDE (divisão 86)
CNAE_SAUDE_PREFIXES = (
    "86",     # Atividades de atenção à saúde humana
    "8610",   # Atividades de atendimento hospitalar
    "8620",   # Atividades de atenção ambulatorial
    "8630",   # Atividades de atenção à saúde humana não especificadas
    "8640",   # Atividades de serviços de complementação diagnóstica e terapêutica
    "8650",   # Atividades de profissionais da área de saúde
    "8660",   # Atividades de apoio à gestão de saúde
    "8690",   # Atividades de atenção à saúde humana não especificadas
    "87",     # Atividades de atenção à saúde humana integradas com assistência social
)

# CNAEs de SERVIÇOS TÉCNICOS (divisões 71, 72, 73, 74)
CNAE_TECNICO_PREFIXES = (
    "71",     # Serviços de arquitetura e engenharia
    "72",     # Pesquisa e desenvolvimento científico
    "73",     # Publicidade e pesquisa de mercado
    "74",     # Outras atividades profissionais, científicas e técnicas
    "62",     # Atividades dos serviços de tecnologia da informação
    "63",     # Atividades de prestação de serviços de informação
)

# CNAEs de CONSULTORIA (divisão 70)
CNAE_CONSULTORIA_PREFIXES = (
    "70",     # Atividades de sedes de empresas e de consultoria em gestão
    "7020",   # Atividades de consultoria em gestão empresarial
)

# CNAEs de ADMINISTRATIVOS (divisão 82)
CNAE_ADMIN_PREFIXES = (
    "82",     # Serviços de escritório, de apoio administrativo
    "78",     # Seleção, agenciamento e locação de mão-de-obra
    "80",     # Atividades de vigilância, segurança e investigação
    "81",     # Serviços para edifícios e atividades paisagísticas
)

# CNAEs de MANUTENÇÃO (divisão 33, 95)
CNAE_MANUTENCAO_PREFIXES = (
    "33",     # Manutenção, reparação e instalação de máquinas e equipamentos
    "95",     # Reparação e manutenção de equipamentos de informática e comunicação
    "45",     # Manutenção e reparação de veículos automotores
)


# =============================================================================
# Keywords para classificação por descrição
# =============================================================================

KEYWORDS_SAUDE = [
    "MEDIC", "HOSPITAL", "CLINIC", "SAUDE", "SAÚDE", "ENFERM", "CIRURG",
    "CONSULT", "HONOR", "ATENDIMENTO", "PACIENTE", "EXAME", "DIAGNOS",
    "TERAPIA", "TRATAMENTO", "FISIO", "ODONTO", "PSICO", "NUTRI",
    "LABOR", "PATOLOG", "RADIOLOG", "ULTRASSOM", "TOMOGRAF",
]

KEYWORDS_TECNICO = [
    "SISTEMA", "SOFTWARE", "PROGRAMA", "DESENVOLV", "T.I.", "TI ",
    "INFORMATIC", "TECNOLOG", "SUPORTE", "REDE", "SERVIDOR",
    "ENGENHAR", "ARQUITET", "PROJETO", "LAUDO", "VISTORIA",
    "PESQUISA", "PUBLICIDADE", "MARKETING", "DESIGN",
]

KEYWORDS_CONSULTORIA = [
    "CONSULTORIA", "ASSESSORIA", "PLANEJAMENTO", "GESTAO", "GESTÃO",
    "ESTRATEG", "ANALISE", "ANÁLISE", "DIAGNÓSTICO", "PARECER",
    "ORIENT", "COACHING", "MENTORIA", "TREINAMENTO",
]

KEYWORDS_ADMIN = [
    "ADMINISTRAT", "ESCRITORIO", "ESCRITÓRIO", "SECRETAR", "RECEP",
    "VIGILANCIA", "VIGILÂNCIA", "SEGURANÇA", "LIMPEZA", "CONSERV",
    "PORTARIA", "ZELADORIA", "COPEIRA", "TERCEIRIZ",
]

KEYWORDS_MANUTENCAO = [
    "MANUTENCAO", "MANUTENÇÃO", "REPARO", "CONSERTO", "INSTALAC",
    "REVISAO", "REVISÃO", "PREVENTIV", "CORRETIV", "ASSISTENCIA",
]


# =============================================================================
# Classificação
# =============================================================================

def _classify_by_cnae_and_keywords(
    cnae: str | None,
    descricao: str | None,
) -> tuple[str, list[str]]:
    """
    Classifica serviço com base em CNAE e keywords na descrição.
    
    Heurística (ordem de prioridade):
    1. CNAE de SAÚDE => SERVICO_SAUDE
    2. CNAE de TÉCNICO => SERVICO_TECNICO
    3. CNAE de CONSULTORIA => SERVICO_CONSULTORIA
    4. CNAE de ADMINISTRATIVO => SERVICO_ADMINISTRATIVO
    5. CNAE de MANUTENÇÃO => SERVICO_MANUTENCAO
    6. Keywords de SAÚDE na descrição => SERVICO_SAUDE
    7. Keywords de TÉCNICO na descrição => SERVICO_TECNICO
    8. Keywords de CONSULTORIA na descrição => SERVICO_CONSULTORIA
    9. Keywords de ADMINISTRATIVO na descrição => SERVICO_ADMINISTRATIVO
    10. Keywords de MANUTENÇÃO na descrição => SERVICO_MANUTENCAO
    11. Fallback => OUTROS
    
    Args:
        cnae: Código CNAE do serviço
        descricao: Descrição do serviço
        
    Returns:
        Tupla (classe, lista de reasons)
    """
    reasons: list[str] = []
    
    # Extrai apenas dígitos do CNAE
    cnae_digits = "".join(c for c in (cnae or "") if c.isdigit())
    
    # Descrição em maiúsculas para comparação
    desc_up = (descricao or "").upper()
    
    # ========================================================================
    # 1) Classificação por CNAE
    # ========================================================================
    
    # SAÚDE
    for prefix in CNAE_SAUDE_PREFIXES:
        if cnae_digits.startswith(prefix):
            reasons.append(REASON_CLASS_SAUDE_BY_CNAE)
            return CLASS_SAUDE, reasons
    
    # TÉCNICO
    for prefix in CNAE_TECNICO_PREFIXES:
        if cnae_digits.startswith(prefix):
            reasons.append(REASON_CLASS_TECNICO_BY_CNAE)
            return CLASS_TECNICO, reasons
    
    # CONSULTORIA
    for prefix in CNAE_CONSULTORIA_PREFIXES:
        if cnae_digits.startswith(prefix):
            reasons.append(REASON_CLASS_CONSULTORIA_BY_CNAE)
            return CLASS_CONSULTORIA, reasons
    
    # ADMINISTRATIVO
    for prefix in CNAE_ADMIN_PREFIXES:
        if cnae_digits.startswith(prefix):
            reasons.append(REASON_CLASS_ADMIN_BY_CNAE)
            return CLASS_ADMIN, reasons
    
    # MANUTENÇÃO
    for prefix in CNAE_MANUTENCAO_PREFIXES:
        if cnae_digits.startswith(prefix):
            reasons.append(REASON_CLASS_MANUTENCAO_BY_CNAE)
            return CLASS_MANUTENCAO, reasons
    
    # ========================================================================
    # 2) Classificação por keywords na descrição
    # ========================================================================
    
    # SAÚDE
    if any(k in desc_up for k in KEYWORDS_SAUDE):
        reasons.append(REASON_CLASS_SAUDE_BY_KEYWORD)
        return CLASS_SAUDE, reasons
    
    # TÉCNICO
    if any(k in desc_up for k in KEYWORDS_TECNICO):
        reasons.append(REASON_CLASS_TECNICO_BY_KEYWORD)
        return CLASS_TECNICO, reasons
    
    # CONSULTORIA
    if any(k in desc_up for k in KEYWORDS_CONSULTORIA):
        reasons.append(REASON_CLASS_CONSULTORIA_BY_KEYWORD)
        return CLASS_CONSULTORIA, reasons
    
    # ADMINISTRATIVO
    if any(k in desc_up for k in KEYWORDS_ADMIN):
        reasons.append(REASON_CLASS_ADMIN_BY_KEYWORD)
        return CLASS_ADMIN, reasons
    
    # MANUTENÇÃO
    if any(k in desc_up for k in KEYWORDS_MANUTENCAO):
        reasons.append(REASON_CLASS_MANUTENCAO_BY_KEYWORD)
        return CLASS_MANUTENCAO, reasons
    
    # ========================================================================
    # 3) Fallback
    # ========================================================================
    reasons.append(REASON_CLASS_OUTROS_FALLBACK)
    return CLASS_OUTROS, reasons


def _get_cnae_group(cnae: str | None) -> str | None:
    """Retorna o grupo do CNAE (2 primeiros dígitos)."""
    if not cnae:
        return None
    digits = "".join(c for c in cnae if c.isdigit())
    return digits[:2] if len(digits) >= 2 else None


def _review_level_from_reasons(
    reasons: list[str],
    flags: dict[str, Any],
) -> str:
    """
    Determina nível de revisão baseado nos reasons.
    
    HIGH: faltam campos críticos, valor divergente/negativo
    MEDIUM: CNAE com alerta, campos incompletos
    LOW: classificação por heurística
    """
    high_reasons = {
        REASON_NUMERO_MISSING,
        REASON_CNPJ_MISSING,
        REASON_VALOR_MISSING,
        REASON_VALOR_NEGATIVO,
        REASON_VALOR_LIQUIDO_DIVERGENTE,
    }
    
    if any(r in high_reasons for r in reasons):
        return REVIEW_LEVEL_HIGH
    
    if flags.get("missing_critical"):
        return REVIEW_LEVEL_HIGH
    
    medium_reasons = {
        REASON_CNAE_ALERT,
        REASON_COMPETENCIA_MISSING,
        REASON_DESCRICAO_MISSING,
    }
    
    if any(r in medium_reasons for r in reasons):
        return REVIEW_LEVEL_MEDIUM
    
    if flags.get("incomplete"):
        return REVIEW_LEVEL_MEDIUM
    
    return REVIEW_LEVEL_LOW


def _build_review_text_ptbr(service_class: str, reasons: list[str]) -> str:
    """
    Gera texto explicativo em PT-BR para o operador.
    """
    parts: list[str] = []
    
    # Classificação com base na evidência
    class_texts = {
        REASON_CLASS_SAUDE_BY_CNAE: "Classificação: SERVIÇO DE SAÚDE (CNAE de atividade hospitalar/médica).",
        REASON_CLASS_SAUDE_BY_KEYWORD: "Classificação: SERVIÇO DE SAÚDE (descrição contém termos médicos/hospitalares).",
        REASON_CLASS_TECNICO_BY_CNAE: "Classificação: SERVIÇO TÉCNICO (CNAE de TI/engenharia/técnico).",
        REASON_CLASS_TECNICO_BY_KEYWORD: "Classificação: SERVIÇO TÉCNICO (descrição contém termos técnicos).",
        REASON_CLASS_CONSULTORIA_BY_CNAE: "Classificação: CONSULTORIA (CNAE de consultoria/gestão).",
        REASON_CLASS_CONSULTORIA_BY_KEYWORD: "Classificação: CONSULTORIA (descrição contém termos de consultoria).",
        REASON_CLASS_ADMIN_BY_CNAE: "Classificação: SERVIÇO ADMINISTRATIVO (CNAE de apoio administrativo).",
        REASON_CLASS_ADMIN_BY_KEYWORD: "Classificação: SERVIÇO ADMINISTRATIVO (descrição contém termos administrativos).",
        REASON_CLASS_MANUTENCAO_BY_CNAE: "Classificação: MANUTENÇÃO (CNAE de manutenção/reparo).",
        REASON_CLASS_MANUTENCAO_BY_KEYWORD: "Classificação: MANUTENÇÃO (descrição contém termos de manutenção).",
        REASON_CLASS_OUTROS_FALLBACK: "Classificação: OUTROS (não foi possível identificar o tipo de serviço).",
    }
    
    for reason in reasons:
        if reason in class_texts:
            parts.append(class_texts[reason])
            break
    
    if not parts:
        parts.append(f"Classificação sugerida: {service_class}.")
    
    # Alertas por reason
    if REASON_CNAE_MISSING in reasons:
        parts.append("CNAE ausente — verificar XML.")
    
    if REASON_CNAE_ALERT in reasons:
        parts.append("CNAE não corresponde à descrição — verificar serviço.")
    
    if REASON_VALOR_LIQUIDO_DIVERGENTE in reasons:
        parts.append("Valor líquido diverge do calculado — conferir retenções.")
    
    if REASON_NUMERO_MISSING in reasons or REASON_CNPJ_MISSING in reasons:
        parts.append("Faltam dados críticos (número/CNPJ) — conferir XML.")
    
    if REASON_VALOR_MISSING in reasons or REASON_VALOR_NEGATIVO in reasons:
        parts.append("Valor do serviço ausente ou inválido — conferir.")
    
    return " ".join(parts)


# =============================================================================
# API Pública
# =============================================================================

def normalize_nfse_item(
    item: dict[str, Any],
) -> dict[str, Any]:
    """
    Normaliza UM item de NFS-e.
    
    Args:
        item: Dicionário com dados do item (formato do extrator)
        
    Returns:
        Dicionário com:
        - todos os campos originais
        - normalized: service_class, suggested_group, cnae_group
        - reasons: lista estável de códigos
        - norm_flags: flags úteis para UI/dash
        - review_level: LOW/MEDIUM/HIGH
        - review_text_ptbr: explicação
    """
    reasons: list[str] = []
    norm_flags: dict[str, Any] = {}
    
    # Extrai campos do formato do extrator
    fields = item.get("fields") or {}
    taxes = item.get("taxes") or {}
    flags = item.get("flags") or {}
    validations = item.get("validations") or {}
    
    cnae = fields.get("cnae")
    descricao = fields.get("descricao_servico")
    valor_total = fields.get("valor_total")
    numero_nota = fields.get("numero_nota")
    cnpj_fornecedor = fields.get("cnpj_fornecedor")
    competencia = fields.get("competencia")
    
    # Validação de campos ausentes
    if not numero_nota:
        reasons.append(REASON_NUMERO_MISSING)
    if not cnpj_fornecedor:
        reasons.append(REASON_CNPJ_MISSING)
    if not cnae:
        reasons.append(REASON_CNAE_MISSING)
    if not competencia:
        reasons.append(REASON_COMPETENCIA_MISSING)
    if not descricao:
        reasons.append(REASON_DESCRICAO_MISSING)
    
    # Validação de valor
    if valor_total is None:
        reasons.append(REASON_VALOR_MISSING)
    elif valor_total <= 0:
        reasons.append(REASON_VALOR_NEGATIVO)
    
    # Validação CNAE vs descrição
    cnae_validation = validations.get("cnae_vs_descricao") or {}
    cnae_status = cnae_validation.get("status")
    
    if cnae_status == "alert":
        reasons.append(REASON_CNAE_ALERT)
    elif cnae_status == "unknown" and cnae:
        reasons.append(REASON_CNAE_UNKNOWN)
    
    # Validação de valor líquido
    if taxes.get("valor_liquido_divergente"):
        reasons.append(REASON_VALOR_LIQUIDO_DIVERGENTE)
    
    # Flags do extrator
    norm_flags["missing_critical"] = flags.get("missing_critical", False)
    norm_flags["incomplete"] = flags.get("incomplete", False)
    norm_flags["needs_review"] = flags.get("needs_review", False)
    
    # Flags adicionais
    norm_flags["has_minimum_fields"] = bool(numero_nota and cnpj_fornecedor and valor_total)
    norm_flags["has_valid_cnae"] = bool(cnae) and cnae_status != "alert"
    norm_flags["has_valid_valor"] = valor_total is not None and valor_total > 0
    norm_flags["valor_liquido_divergente"] = taxes.get("valor_liquido_divergente", False)
    norm_flags["requires_review_cnae"] = cnae_status in ("alert", "unknown")
    
    # Classificação
    service_class, class_reasons = _classify_by_cnae_and_keywords(cnae, descricao)
    
    # Adiciona reasons de classificação
    for r in class_reasons:
        if r not in reasons:
            reasons.append(r)
    
    normalized = {
        "service_class": service_class,
        "suggested_group": service_class,
        "cnae_group": _get_cnae_group(cnae),
    }
    
    # Decisão e explicação
    review_level = _review_level_from_reasons(reasons, norm_flags)
    review_text_ptbr = _build_review_text_ptbr(service_class, reasons)
    
    # Monta resultado (preserva dados originais e adiciona normalização)
    result = dict(item)
    result["normalized"] = normalized
    result["norm_flags"] = norm_flags
    result["review_level"] = review_level
    result["review_text_ptbr"] = review_text_ptbr
    
    # Adiciona reasons sem duplicar
    existing_reasons = result.get("reasons") or []
    for r in reasons:
        if r not in existing_reasons:
            existing_reasons.append(r)
    result["reasons"] = existing_reasons
    
    return result


def normalize_nfse_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Normaliza uma lista de itens NFS-e.
    
    Args:
        items: Lista de dicts do extrator
    
    Returns:
        Tupla:
        - items_enriched: lista com normalized/reasons/etc mesclados
        - summary: agregações para dashboard
    """
    enriched: list[dict[str, Any]] = []
    
    # Contadores de decisão
    count_review = 0
    count_auto = 0
    count_block = 0
    
    # Contadores de qualidade
    count_missing_cnae = 0
    count_missing_valor = 0
    count_cnae_alert = 0
    count_liquido_divergente = 0
    
    # Contadores de review_level
    review_high = 0
    review_medium = 0
    review_low = 0
    
    # Contadores de classe de serviço
    class_counts: dict[str, int] = {}
    
    for item in items or []:
        out = normalize_nfse_item(item)
        enriched.append(out)
        
        # Conta decisão original
        decision = item.get("decision", "REVIEW")
        if decision == "AUTO":
            count_auto += 1
        elif decision == "BLOCK":
            count_block += 1
        else:
            count_review += 1
        
        # Conta problemas
        reasons = out.get("reasons") or []
        if REASON_CNAE_MISSING in reasons:
            count_missing_cnae += 1
        if REASON_VALOR_MISSING in reasons:
            count_missing_valor += 1
        if REASON_CNAE_ALERT in reasons:
            count_cnae_alert += 1
        if REASON_VALOR_LIQUIDO_DIVERGENTE in reasons:
            count_liquido_divergente += 1
        
        # Conta review_level
        rl = out.get("review_level", "LOW")
        if rl == REVIEW_LEVEL_HIGH:
            review_high += 1
        elif rl == REVIEW_LEVEL_MEDIUM:
            review_medium += 1
        else:
            review_low += 1
        
        # Conta classe de serviço
        service_class = (out.get("normalized") or {}).get("service_class", CLASS_OUTROS)
        class_counts[service_class] = class_counts.get(service_class, 0) + 1
    
    summary = {
        "decision_summary": {
            "auto": count_auto,
            "review": count_review,
            "block": count_block,
        },
        "quality_summary": {
            "missing_cnae": count_missing_cnae,
            "missing_valor": count_missing_valor,
            "cnae_alert": count_cnae_alert,
            "liquido_divergente": count_liquido_divergente,
        },
        "review_summary": {
            "high": review_high,
            "medium": review_medium,
            "low": review_low,
        },
        "service_class_summary": class_counts,
    }
    
    return enriched, summary
