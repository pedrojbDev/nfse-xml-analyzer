import re
from typing import Optional, Dict, Any

from app.utils.regex import find_regex
from app.utils.money import parse_money, extract_valor_total
from app.utils.money_scan import scan_first_money_value, scan_valor_total_by_anchor_fuzzy


def extract_numero_nota(source_text: str) -> Optional[str]:
    """
    Extrai número da nota por âncora 'Número da Nota' e captura dígitos após.
    Regra de robustez:
      - exige pelo menos 6 dígitos (evita capturar '2025' como nota).
      - NFSe costuma vir com zeros à esquerda (ex.: 00000820).
    """
    text = re.sub(r"\s+", " ", source_text)

    anchor = re.search(r"(?:N[uú]mero|Numero)\s+da\s+Nota", text, re.IGNORECASE)
    if not anchor:
        return None

    window = text[anchor.end() : anchor.end() + 140]

    # Exige 6+ dígitos (evita ano "2025")
    m = re.search(r"[:=]?\s*([0-9]{6,})\b", window)
    if not m:
        return None

    return m.group(1).strip()


def extract_nfse_fields(source_text: str) -> Dict[str, Any]:
    # ---------------------------
    # Número da Nota
    # ---------------------------
    numero_nota = find_regex(
        r"(?:N[uú]mero|Numero)\s+da\s+Nota\s*[:=]?\s*([0-9]{6,})",
        source_text,
    )
    if not numero_nota:
        numero_nota = extract_numero_nota(source_text)

    # ---------------------------
    # Data e Hora de Emissão
    # ---------------------------
    data_emissao = find_regex(
        r"Data\s+e\s+Hora\s+de\s+Emiss[aã]o\s*[:=]?\s*"
        r"([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}:[0-9]{2})?)",
        source_text,
    ) or find_regex(
        r"Data\s+.*Emiss[aã]o\s*[:=]?\s*"
        r"([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}:[0-9]{2})?)",
        source_text,
    )

    # ---------------------------
    # CNPJ Prestador (Fornecedor)
    # ---------------------------
    cnpj_fornecedor = find_regex(
        r"(?:CPF/CNPJ|CNPJ)\s*[:=]?\s*"
        r"([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})",
        source_text,
    ) or find_regex(
        r"\b([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})\b",
        source_text,
    )

    # ---------------------------
    # Competência
    # ---------------------------
    competencia = find_regex(
        r"COMPET[EÊ]NCIA\s*[:=]?\s*([0-9]{2}/[0-9]{4})",
        source_text,
    ) or find_regex(
        r"COMPETENCIA\s*[:=]?\s*([0-9]{2}/[0-9]{4})",
        source_text,
    )

    # ---------------------------
    # Valor total (robusto)
    # Ordem:
    #  1) regex estrito com âncora
    #  2) extract_valor_total (janela após âncora)
    #  3) âncora fuzzy (tolerante a OCR)
    #  4) scan monetário global (último recurso sem crop)
    # ---------------------------
    valor_total_raw = find_regex(
        r"VALOR\s+TOTAL\s+DA\s+NOTA\s*[:=]?\s*R?\$?\s*"
        r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})",
        source_text,
    ) or find_regex(
        r"Valor\s+Total\s+da\s+Nota\s*[:=]?\s*R?\$?\s*"
        r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})",
        source_text,
    )

    valor_total = parse_money(valor_total_raw)

    if valor_total is None:
        valor_total = extract_valor_total(source_text)

    if valor_total is None:
        valor_total = scan_valor_total_by_anchor_fuzzy(source_text)

    if valor_total is None:
        # Se a nota tiver vários valores, esse fallback pode pegar outro.
        # Por isso ele fica depois das tentativas com âncora.
        valor_total = scan_first_money_value(source_text)

    return {
        "numero_nota": numero_nota,
        "data_emissao": data_emissao,
        "cnpj_fornecedor": cnpj_fornecedor,
        "valor_total": valor_total,
        "competencia": competencia,
        "descricao_servico": "honorarios medicos",
    }
