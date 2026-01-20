from __future__ import annotations
import re

from typing import Any, Dict, List, Tuple, Optional


# Motivos padronizados (reasons) — mantenha como strings estáveis (bom para dashboard/BI)
REASON_NCM_MISSING = "NCM_MISSING"
REASON_CFOP_MISSING = "CFOP_MISSING"
REASON_PRODUCT_CODE_MISSING = "PRODUCT_CODE_MISSING"
REASON_PRODUCT_DESC_MISSING = "PRODUCT_DESC_MISSING"
REASON_QTY_OR_PRICE_MISSING = "QTY_OR_PRICE_MISSING"
REASON_TOTAL_ITEM_INVALID = "ITEM_TOTAL_INVALID"
REASON_DEFAULT_CLASS_MED = "DEFAULT_CLASS_MEDICAMENTO"
REASON_CLASS_CONFLICT_MED = "CLASS_CONFLICT_MEDICAMENTO"
REASON_KEYWORD_NON_MED = "KEYWORD_NON_MEDICAMENTO"
REASON_NCM_NON_MED = "NCM_NON_MEDICAMENTO"


# Decisões (por item)
DECISION_AUTO = "AUTO"
DECISION_REVIEW = "REVIEW"
DECISION_BLOCK = "BLOCK"


def _is_positive_number(v: Any) -> bool:
    try:
        if v is None:
            return False
        return float(v) > 0
    except Exception:
        return False


def _calc_expected_vprod(q: Optional[float], vun: Optional[float]) -> Optional[float]:
    if q is None or vun is None:
        return None
    try:
        return round(float(q) * float(vun), 2)
    except Exception:
        return None

def _looks_non_medicamento(ncm: Optional[str], xprod: Optional[str]) -> Tuple[bool, List[str]]:
    """
    Heurística determinística e conservadora:
    - Detecta sinais MUITO fortes de não-medicamento
    - Retorna (is_non_med, evidences)
    """
    evidences: List[str] = []

    xp = (xprod or "").upper()

    # Palavras-chave fortes (exemplos óbvios)
    keywords = ["GLP", "GASOLINA", "DIESEL", "ETANOL", "OLEO", "LUBRIFICANTE", "GAS "]
    if any(k in xp for k in keywords):
        evidences.append(REASON_KEYWORD_NON_MED)

    # NCMs claramente fora (ex.: combustíveis/gases). Mantemos conservador:
    # 27xx (capítulo 27 = combustíveis minerais, óleos minerais, etc.)
    if ncm:
        ncm_digits = re.sub(r"\D+", "", ncm)
        if ncm_digits.startswith("27"):
            evidences.append(REASON_NCM_NON_MED)

    return (len(evidences) > 0), evidences



def normalize_nfe_item(
    item: Dict[str, Any],
    *,
    default_product_class: str = "MEDICAMENTO",
    vprod_tolerance: float = 0.05,
) -> Dict[str, Any]:
    """
    Normaliza UM item de NF-e para uso operacional (RM / revisão humana).
    Não altera o XML original: apenas enriquece o dict do item.

    Retorna um dict com:
      - normalized: campos operacionais (product_class, etc.)
      - decision: AUTO/REVIEW/BLOCK
      - reasons: lista de motivos padronizados
      - flags: sinais booleanos úteis para UI/ERP
    """

    reasons: List[str] = []
    flags: Dict[str, Any] = {}

    cProd = item.get("cProd")
    xProd = item.get("xProd")
    ncm = item.get("NCM")
    cfop = item.get("CFOP")
    qCom = item.get("qCom")
    vUnCom = item.get("vUnCom")
    vProd = item.get("vProd")
    is_non_med, evidences = _looks_non_medicamento(ncm, xProd)


    # Regras mínimas (determinísticas) para qualidade de cadastro
    if not cProd:
        reasons.append(REASON_PRODUCT_CODE_MISSING)
    if not xProd:
        reasons.append(REASON_PRODUCT_DESC_MISSING)
    if not ncm:
        reasons.append(REASON_NCM_MISSING)
    if not cfop:
        reasons.append(REASON_CFOP_MISSING)

    if not _is_positive_number(qCom) or not _is_positive_number(vUnCom):
        reasons.append(REASON_QTY_OR_PRICE_MISSING)

    # Consistência do total do item (quando possível)
    expected = _calc_expected_vprod(qCom, vUnCom)
    if expected is not None and vProd is not None:
        try:
            diff = round(float(vProd) - float(expected), 2)
        except Exception:
            diff = None

        flags["expected_vProd"] = expected
        flags["diff_vProd_vs_expected"] = diff
        if diff is not None and abs(diff) > float(vprod_tolerance):
            reasons.append(REASON_TOTAL_ITEM_INVALID)
            flags["vProd_invalid"] = True
        else:
            flags["vProd_invalid"] = False
    else:
        flags["expected_vProd"] = expected
        flags["diff_vProd_vs_expected"] = None
        flags["vProd_invalid"] = False

    # Classificação operacional (MVP)
    # Hoje o cliente manualmente "cadastra como medicamento". Então:
    if is_non_med:
        normalized = {
            "product_class": "NAO_MEDICAMENTO",
            "suggested_group": "OUTROS",
        }
        reasons.append(REASON_CLASS_CONFLICT_MED)
        reasons.extend(evidences)
    else:
        normalized = {
            "product_class": default_product_class,
            "suggested_group": default_product_class,
        }
        reasons.append(REASON_DEFAULT_CLASS_MED)


    # Flags úteis para UI/revisão
    flags["requires_product_registration"] = True  # MVP: assume que precisa casar/cadastrar no RM
    flags["has_minimum_fiscal_keys"] = (ncm is not None and cfop is not None)

    # Decisão determinística (MVP)
    # BLOCK: faltas que impedem cadastro fiscal mínimo (NCM/CFOP/descrição/código)
    # REVIEW: dados ok, mas ainda exige conferência/cadastro
    hard_block = (
        (REASON_NCM_MISSING in reasons)
        or (REASON_CFOP_MISSING in reasons)
        or (REASON_PRODUCT_CODE_MISSING in reasons)
        or (REASON_PRODUCT_DESC_MISSING in reasons)
    )
    if hard_block:
        decision = DECISION_BLOCK
    elif is_non_med:
        decision = DECISION_REVIEW
    else:
        decision = DECISION_REVIEW

    return {
        "item": item,
        "normalized": normalized,
        "decision": decision,
        "reasons": reasons,
        "flags": flags,
    }


def normalize_nfe_items(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Normaliza uma lista de linhas no formato do seu extractor (cada row tem 'item', 'confidence', etc.).
    Retorna:
      - rows_enriched: lista com 'normalized', 'decision', 'reasons', 'flags' mesclados no row
      - summary: métricas agregadas
    """
    enriched: List[Dict[str, Any]] = []

    count_auto = 0
    count_review = 0
    count_block = 0

    count_missing_ncm = 0
    count_missing_cfop = 0
    count_total_invalid = 0

    for row in rows:
        it = (row.get("item") or {}) if isinstance(row, dict) else {}
        out = normalize_nfe_item(it)

        # mescla de forma não destrutiva
        merged = dict(row)
        merged["normalized"] = out["normalized"]
        merged["decision"] = out["decision"]
        merged["reasons"] = out["reasons"]
        merged["norm_flags"] = out["flags"]
        enriched.append(merged)

        if out["decision"] == DECISION_AUTO:
            count_auto += 1
        elif out["decision"] == DECISION_REVIEW:
            count_review += 1
        else:
            count_block += 1

        if REASON_NCM_MISSING in out["reasons"]:
            count_missing_ncm += 1
        if REASON_CFOP_MISSING in out["reasons"]:
            count_missing_cfop += 1
        if REASON_TOTAL_ITEM_INVALID in out["reasons"]:
            count_total_invalid += 1

    summary = {
        "decision_summary": {
            "auto": count_auto,
            "review": count_review,
            "block": count_block,
        },
        "quality_summary": {
            "missing_ncm": count_missing_ncm,
            "missing_cfop": count_missing_cfop,
            "item_total_invalid": count_total_invalid,
        },
    }

    return enriched, summary
