# app/utils/converters.py
"""
Funções utilitárias para conversão de tipos.

Centraliza conversões que eram duplicadas em múltiplos serviços:
- nfe_item_normalizer.py
- nfe_document_analyzer.py
- nfe_xml_extract.py

Todas as funções são seguras (não lançam exceções).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional


def safe_float(value: Any) -> Optional[float]:
    """
    Converte valor para float de forma segura.
    
    Trata:
    - None -> None
    - Strings com vírgula como separador decimal
    - Valores já numéricos
    
    Args:
        value: Valor a ser convertido
        
    Returns:
        Float ou None se conversão falhar
    """
    if value is None:
        return None
    
    try:
        if isinstance(value, (int, float)):
            return float(value)
        
        s = str(value).strip()
        if not s:
            return None
        
        # Trata formato brasileiro (1.234,56 -> 1234.56)
        s = s.replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """
    Converte valor para int de forma segura.
    
    Args:
        value: Valor a ser convertido
        
    Returns:
        Int ou None se conversão falhar
    """
    if value is None:
        return None
    
    try:
        if isinstance(value, int):
            return value
        
        s = str(value).strip()
        if not s:
            return None
        
        return int(float(s))  # Permite "123.0" -> 123
    except (ValueError, TypeError):
        return None


def digits_only(value: Optional[str]) -> str:
    """
    Remove todos os caracteres não-numéricos de uma string.
    
    Args:
        value: String a ser processada
        
    Returns:
        String contendo apenas dígitos (pode ser vazia)
    """
    if not value:
        return ""
    return re.sub(r"\D+", "", str(value))


def digits_only_or_none(value: Optional[str]) -> Optional[str]:
    """
    Remove caracteres não-numéricos, retorna None se resultado for vazio.
    
    Args:
        value: String a ser processada
        
    Returns:
        String com dígitos ou None se vazia
    """
    result = digits_only(value)
    return result if result else None


def normalize_text(value: Any) -> str:
    """
    Normaliza texto: strip e converte None para string vazia.
    
    Args:
        value: Valor a ser normalizado
        
    Returns:
        String normalizada (nunca None)
    """
    if value is None:
        return ""
    return str(value).strip()


def normalize_text_or_none(value: Any) -> Optional[str]:
    """
    Normaliza texto, retorna None se resultado for vazio.
    
    Args:
        value: Valor a ser normalizado
        
    Returns:
        String normalizada ou None se vazia
    """
    result = normalize_text(value)
    return result if result else None


def sanitize_product_code(value: Any) -> Optional[str]:
    """
    Sanitiza código de produto (cProd).
    
    Evita problemas no frontend onde códigos como '21,754' ou '21.754'
    aparecem formatados incorretamente.
    
    Regras:
    - Remove espaços
    - Se parecer numérico com separador, extrai apenas dígitos
    - Caso contrário, mantém string original
    
    Args:
        value: Código do produto
        
    Returns:
        Código sanitizado ou None
    """
    if value is None:
        return None
    
    s = str(value).strip()
    if not s:
        return None
    
    s_no_space = s.replace(" ", "")
    d = digits_only(s_no_space)
    
    # Se tinha separadores e o resultado é um número plausível
    if ("," in s_no_space or "." in s_no_space) and d:
        return d
    
    return s


def is_positive_number(value: Any) -> bool:
    """
    Verifica se valor é um número positivo.
    
    Args:
        value: Valor a ser verificado
        
    Returns:
        True se for número > 0
    """
    f = safe_float(value)
    return f is not None and f > 0


def calculate_expected_vprod(quantity: Any, unit_price: Any) -> Optional[float]:
    """
    Calcula valor esperado do produto (qCom × vUnCom).
    
    Args:
        quantity: Quantidade (qCom)
        unit_price: Preço unitário (vUnCom)
        
    Returns:
        Valor calculado arredondado para 2 casas ou None
    """
    fq = safe_float(quantity)
    fv = safe_float(unit_price)
    
    if fq is None or fv is None:
        return None
    
    try:
        return round(fq * fv, 2)
    except (ValueError, TypeError, OverflowError):
        return None


def percent_diff(a: float, b: float) -> float:
    """
    Calcula diferença percentual entre dois valores.
    
    Args:
        a: Primeiro valor
        b: Segundo valor
        
    Returns:
        Diferença percentual (0 a 1)
    """
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse de data/hora ISO (formato NF-e com timezone).
    
    Exemplo: 2026-01-12T11:45:12-03:00
    
    Args:
        dt_str: String de data/hora ISO
        
    Returns:
        Objeto datetime ou None
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def format_datetime_br(dt: Optional[datetime]) -> Optional[str]:
    """
    Formata datetime para padrão brasileiro (DD/MM/YYYY HH:MM:SS).
    
    Args:
        dt: Objeto datetime
        
    Returns:
        String formatada ou None
    """
    if not dt:
        return None
    
    try:
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, AttributeError):
        return None


def format_currency_br(value: Any) -> str:
    """
    Formata valor monetário para padrão brasileiro.
    
    Exemplo: 1234.56 -> "R$ 1.234,56"
    
    Args:
        value: Valor numérico
        
    Returns:
        String formatada ou "-" se inválido
    """
    f = safe_float(value)
    if f is None:
        return "-"
    
    try:
        # Formata com separador de milhar e 2 casas decimais
        s = f"{f:,.2f}"
        # Converte para formato BR (. como milhar, , como decimal)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except (ValueError, TypeError):
        return "-"


def dedup_keep_order(items: list[str]) -> list[str]:
    """
    Remove duplicatas de lista mantendo ordem original.
    
    Args:
        items: Lista de strings
        
    Returns:
        Lista sem duplicatas
    """
    seen: set[str] = set()
    result: list[str] = []
    
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    
    return result
