# app/services/decision.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class DecisionThresholds:
    # tolerância para divergência entre líquido do XML vs cálculo (Política B)
    net_abs: float = 0.10     # R$ 0,10 (conservador, mas não sensível demais)
    net_pct: float = 0.001    # 0,1%


def _pct_diff(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom


def decide_for_erp_from_xml_item(
    item: Dict[str, Any],
    thresholds: DecisionThresholds = DecisionThresholds(),
) -> Tuple[str, List[str]]:
    """
    item: estrutura atual do seu parse (fields/taxes/validations/flags)
    retorna: (decision, reasons)
    """

    reasons: List[str] = []

    fields = item.get("fields", {}) or {}
    taxes = item.get("taxes", {}) or {}
    validations = item.get("validations", {}) or {}
    cnae_val = (validations.get("cnae_vs_descricao") or {})

    # 1) Campos críticos (para o ERP, sem isso não existe lançamento)
    critical = ("numero_nota", "data_emissao", "competencia", "cnpj_fornecedor", "valor_total")
    if any(not fields.get(k) for k in critical):
        reasons.append("MISSING_REQUIRED_FIELDS")

    # 2) Valores inválidos
    try:
        vt = fields.get("valor_total")
        if vt is None or float(vt) <= 0:
            reasons.append("NEGATIVE_OR_ZERO_VALUES")
    except Exception:
        reasons.append("TAX_INCONSISTENT")

    # 3) CNAE x Descrição
    st = (cnae_val.get("status") or "").lower().strip()
    if st == "unknown":
        reasons.append("CNAE_UNKNOWN")
    elif st == "alert":
        reasons.append("CNAE_MISMATCH")

    # 4) Divergência de líquido (XML vs cálculo Política B)
    vl_inf = taxes.get("valor_liquido_nfse")
    vl_cal = taxes.get("valor_liquido_calculado_politica_b")
    try:
        if vl_inf is not None and vl_cal is not None:
            a = float(vl_inf)
            b = float(vl_cal)
            abs_diff = abs(a - b)
            pct = _pct_diff(a, b)
            if abs_diff > thresholds.net_abs and pct > thresholds.net_pct:
                reasons.append("NET_DIVERGENCE_ABOVE_THRESHOLD")
    except Exception:
        reasons.append("TAX_INCONSISTENT")

    # Decisão (conservadora e auditável)
    if any(r in reasons for r in ("MISSING_REQUIRED_FIELDS", "NEGATIVE_OR_ZERO_VALUES", "TAX_INCONSISTENT")):
        return "BLOCK", sorted(set(reasons))

    if any(r in reasons for r in ("CNAE_UNKNOWN", "CNAE_MISMATCH", "NET_DIVERGENCE_ABOVE_THRESHOLD")):
        return "REVIEW", sorted(set(reasons))

    return "AUTO", []
