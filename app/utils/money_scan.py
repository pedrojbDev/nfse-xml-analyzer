import re
from typing import Optional

from app.utils.money import parse_money


def scan_first_money_value(text: str) -> Optional[float]:
    """
    Retorna o primeiro valor monetário parseável encontrado no texto.
    Útil como fallback quando já tentamos âncoras e janelas.
    """
    if not text:
        return None

    t = re.sub(r"\s+", " ", text)

    m = re.search(
        r"R?\$?\s*([0-9]{1,3}(?:[.\s][0-9]{3})*|[0-9]{1,9})\s*[,\.]\s*([0-9]{2})",
        t,
        re.IGNORECASE,
    )
    if not m:
        return None

    integral = re.sub(r"\s+", "", m.group(1))
    cents = m.group(2)
    return parse_money(f"{integral},{cents}")


def scan_valor_total_by_anchor_fuzzy(text: str) -> Optional[float]:
    """
    Tenta capturar valor total mesmo com OCR degradado:
    - aceita variações do rótulo (ex.: VAL0R, T0TAL, N0TA)
    - procura valor monetário próximo à âncora
    """
    if not text:
        return None

    t = re.sub(r"\s+", " ", text)

    # âncora tolerante: VALOR/VAL0R + TOTAL/T0TAL + NOTA/N0TA
    anchor = re.search(
        r"V[A4]L[O0]R\s+T[O0]T[A4]L\s+D[A4]\s+N[O0]T[A4]",
        t,
        re.IGNORECASE,
    )
    if not anchor:
        # tenta uma variação sem "DA"
        anchor = re.search(
            r"V[A4]L[O0]R\s+T[O0]T[A4]L\s+N[O0]T[A4]",
            t,
            re.IGNORECASE,
        )
    if not anchor:
        return None

    window = t[anchor.end() : anchor.end() + 320]

    m = re.search(
        r"R?\$?\s*([0-9]{1,3}(?:[.\s][0-9]{3})*|[0-9]{1,9})\s*[,\.]\s*([0-9]{2})",
        window,
        re.IGNORECASE,
    )
    if not m:
        return None

    integral = re.sub(r"\s+", "", m.group(1))
    cents = m.group(2)
    return parse_money(f"{integral},{cents}")
