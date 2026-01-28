# app/services/nfe_xml_extract.py
"""
Serviço de extração de dados de XML de NF-e.

Responsável por:
- Parse do XML no padrão Portal Fiscal
- Extração de header, emitente, destinatário, totais e itens
- Cálculo de confiança por item
- Geração de sumário da extração
"""
from __future__ import annotations

import csv
import hashlib
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from app.utils.converters import (
    digits_only_or_none,
    format_datetime_br,
    normalize_text_or_none,
    parse_iso_datetime,
    safe_float,
    safe_int,
)


# Namespace NF-e (Portal Fiscal)
NFE_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def _sha256(data: bytes) -> str:
    """Calcula hash SHA256 dos bytes."""
    return hashlib.sha256(data).hexdigest()


def _findtext(root: ET.Element, xpath: str) -> str | None:
    """Busca texto em elemento XML com namespace NF-e."""
    return root.findtext(xpath, default=None, namespaces=NFE_NS)


def _safe_get_chave_from_nfeproc(root: ET.Element) -> str | None:
    """
    Extrai chave de acesso da NF-e.
    
    Tenta:
    1) nfeProc/protNFe/infProt/chNFe
    2) NFe/infNFe/@Id => "NFe<chave>"
    """
    ch = _findtext(root, ".//nfe:protNFe/nfe:infProt/nfe:chNFe")
    if ch:
        return digits_only_or_none(ch)
    
    inf = root.find(".//nfe:NFe/nfe:infNFe", namespaces=NFE_NS)
    if inf is not None:
        _id = inf.attrib.get("Id")
        if _id:
            # Id geralmente "NFe{44dig}"
            digits = digits_only_or_none(_id)
            if digits and len(digits) >= 44:
                return digits[-44:]
    
    return None


# =============================================================================
# Extração de seções
# =============================================================================

def _extract_header(root: ET.Element) -> dict[str, Any]:
    """Extrai cabeçalho da NF-e."""
    nNF = _findtext(root, ".//nfe:ide/nfe:nNF")
    serie = _findtext(root, ".//nfe:ide/nfe:serie")
    dhEmi = _findtext(root, ".//nfe:ide/nfe:dhEmi") or _findtext(root, ".//nfe:ide/nfe:dEmi")
    natOp = _findtext(root, ".//nfe:ide/nfe:natOp")
    tpNF = _findtext(root, ".//nfe:ide/nfe:tpNF")  # 0=entrada, 1=saída
    tpAmb = _findtext(root, ".//nfe:ide/nfe:tpAmb")
    
    dt = parse_iso_datetime(dhEmi)
    
    return {
        "chave_nfe": _safe_get_chave_from_nfeproc(root),
        "numero": safe_int(nNF),
        "serie": safe_int(serie),
        "data_emissao": format_datetime_br(dt),
        "natureza_operacao": normalize_text_or_none(natOp),
        "tipo_nf": safe_int(tpNF),
        "ambiente": safe_int(tpAmb),
    }


def _extract_party(root: ET.Element, kind: str) -> dict[str, Any]:
    """
    Extrai dados de emitente ou destinatário.
    
    Args:
        root: Elemento raiz do XML
        kind: "emit" ou "dest"
    """
    base = f".//nfe:{kind}"
    cnpj = _findtext(root, base + "/nfe:CNPJ") or _findtext(root, base + "/nfe:CPF")
    xNome = _findtext(root, base + "/nfe:xNome")
    
    ender_suffix = "Emit" if kind == "emit" else "Dest"
    uf = _findtext(root, f"{base}/nfe:ender{ender_suffix}/nfe:UF")
    mun = _findtext(root, f"{base}/nfe:ender{ender_suffix}/nfe:xMun")
    
    return {
        "doc": digits_only_or_none(cnpj),
        "nome": normalize_text_or_none(xNome),
        "uf": normalize_text_or_none(uf),
        "municipio": normalize_text_or_none(mun),
    }


def _extract_totals(root: ET.Element) -> dict[str, Any]:
    """Extrai totais (ICMSTot) da NF-e."""
    prefix = ".//nfe:total/nfe:ICMSTot/nfe:"
    
    return {
        "vNF": safe_float(_findtext(root, prefix + "vNF")),
        "vProd": safe_float(_findtext(root, prefix + "vProd")),
        "vDesc": safe_float(_findtext(root, prefix + "vDesc")),
        "vFrete": safe_float(_findtext(root, prefix + "vFrete")),
        "vOutro": safe_float(_findtext(root, prefix + "vOutro")),
        "vICMS": safe_float(_findtext(root, prefix + "vICMS")),
        "vICMSST": safe_float(_findtext(root, prefix + "vST")),
        "vIPI": safe_float(_findtext(root, prefix + "vIPI")),
        "vPIS": safe_float(_findtext(root, prefix + "vPIS")),
        "vCOFINS": safe_float(_findtext(root, prefix + "vCOFINS")),
    }


# =============================================================================
# Extração de impostos por item
# =============================================================================

def _extract_icms_from_det(det: ET.Element) -> dict[str, Any]:
    """
    Extrai ICMS de um item (det).
    
    ICMS varia: ICMS00, ICMS10, ICMS20, ICMS40, ICMS60, ICMS90, ICMSSN101, etc.
    """
    icms_parent = det.find(".//nfe:imposto/nfe:ICMS", namespaces=NFE_NS)
    if icms_parent is None:
        return {}
    
    # Primeiro filho é o grupo (ICMS00, ICMSSN102, etc.)
    group = None
    for child in list(icms_parent):
        group = child
        break
    
    if group is None:
        return {}
    
    local = group.tag.split("}", 1)[-1] if "}" in group.tag else group.tag
    cst = group.findtext("nfe:CST", default=None, namespaces=NFE_NS)
    csosn = group.findtext("nfe:CSOSN", default=None, namespaces=NFE_NS)
    vBC = group.findtext("nfe:vBC", default=None, namespaces=NFE_NS)
    vICMS = group.findtext("nfe:vICMS", default=None, namespaces=NFE_NS)
    
    return {
        "icms_tipo": local,
        "cst": cst,
        "csosn": csosn,
        "vBC": safe_float(vBC),
        "vICMS": safe_float(vICMS),
    }


def _extract_pis_from_det(det: ET.Element) -> dict[str, Any]:
    """Extrai PIS de um item (det)."""
    pis_parent = det.find(".//nfe:imposto/nfe:PIS", namespaces=NFE_NS)
    if pis_parent is None:
        return {}
    
    group = None
    for child in list(pis_parent):
        group = child
        break
    
    if group is None:
        return {}
    
    local = group.tag.split("}", 1)[-1] if "}" in group.tag else group.tag
    cst = group.findtext("nfe:CST", default=None, namespaces=NFE_NS)
    vPIS = group.findtext("nfe:vPIS", default=None, namespaces=NFE_NS)
    
    return {
        "pis_tipo": local,
        "pis_cst": cst,
        "vPIS": safe_float(vPIS),
    }


def _extract_cofins_from_det(det: ET.Element) -> dict[str, Any]:
    """Extrai COFINS de um item (det)."""
    cof_parent = det.find(".//nfe:imposto/nfe:COFINS", namespaces=NFE_NS)
    if cof_parent is None:
        return {}
    
    group = None
    for child in list(cof_parent):
        group = child
        break
    
    if group is None:
        return {}
    
    local = group.tag.split("}", 1)[-1] if "}" in group.tag else group.tag
    cst = group.findtext("nfe:CST", default=None, namespaces=NFE_NS)
    vCOFINS = group.findtext("nfe:vCOFINS", default=None, namespaces=NFE_NS)
    
    return {
        "cofins_tipo": local,
        "cofins_cst": cst,
        "vCOFINS": safe_float(vCOFINS),
    }


def _extract_item(det: ET.Element) -> dict[str, Any]:
    """Extrai dados de um item (det) da NF-e."""
    n_item = det.attrib.get("nItem")
    
    item = {
        "nItem": safe_int(n_item),
        "cProd": normalize_text_or_none(det.findtext(".//nfe:prod/nfe:cProd", default=None, namespaces=NFE_NS)),
        "xProd": normalize_text_or_none(det.findtext(".//nfe:prod/nfe:xProd", default=None, namespaces=NFE_NS)),
        "NCM": normalize_text_or_none(det.findtext(".//nfe:prod/nfe:NCM", default=None, namespaces=NFE_NS)),
        "CFOP": normalize_text_or_none(det.findtext(".//nfe:prod/nfe:CFOP", default=None, namespaces=NFE_NS)),
        "uCom": normalize_text_or_none(det.findtext(".//nfe:prod/nfe:uCom", default=None, namespaces=NFE_NS)),
        "qCom": safe_float(det.findtext(".//nfe:prod/nfe:qCom", default=None, namespaces=NFE_NS)),
        "vUnCom": safe_float(det.findtext(".//nfe:prod/nfe:vUnCom", default=None, namespaces=NFE_NS)),
        "vProd": safe_float(det.findtext(".//nfe:prod/nfe:vProd", default=None, namespaces=NFE_NS)),
    }
    
    # Impostos por item
    item.update(_extract_icms_from_det(det))
    item.update(_extract_pis_from_det(det))
    item.update(_extract_cofins_from_det(det))
    
    return item


def _confidence_for_item(item: dict[str, Any]) -> tuple[list[str], float]:
    """
    Calcula confiança da extração de um item.
    
    Returns:
        Tupla (campos_faltantes, confiança_0_a_1)
    """
    keys = ("cProd", "xProd", "NCM", "CFOP", "qCom", "vUnCom", "vProd")
    missing = [k for k in keys if not item.get(k)]
    confidence = round(1 - (len(missing) / len(keys)), 2)
    return missing, confidence


# =============================================================================
# Resultado da extração
# =============================================================================

@dataclass(frozen=True)
class NFeExtractResult:
    """Resultado da extração de NF-e."""
    received: bool
    filename: str
    sha256: str
    count: int
    header: dict[str, Any]
    emit: dict[str, Any]
    dest: dict[str, Any]
    totals: dict[str, Any]
    items: list[dict[str, Any]]
    summary: dict[str, Any]


def parse_nfe_xml(xml_bytes: bytes, filename: str = "upload.xml") -> NFeExtractResult:
    """
    Faz parse de XML de NF-e.
    
    Args:
        xml_bytes: Conteúdo do XML em bytes
        filename: Nome do arquivo (para log/auditoria)
        
    Returns:
        NFeExtractResult com todos os dados extraídos
    """
    sha256 = _sha256(xml_bytes)
    
    # XML vazio
    if not xml_bytes:
        return NFeExtractResult(
            received=False,
            filename=filename,
            sha256=sha256,
            count=0,
            header={},
            emit={},
            dest={},
            totals={},
            items=[],
            summary={"error": "Empty body"},
        )
    
    # Parse do XML
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        return NFeExtractResult(
            received=False,
            filename=filename,
            sha256=sha256,
            count=0,
            header={},
            emit={},
            dest={},
            totals={},
            items=[],
            summary={"error": "Invalid XML or parse failure", "exception": str(exc)},
        )
    
    # Extração das seções
    header = _extract_header(root)
    emit = _extract_party(root, "emit")
    dest = _extract_party(root, "dest")
    totals = _extract_totals(root)
    
    # Extração dos itens
    # Tenta múltiplos XPaths para compatibilidade com diferentes estruturas de XML
    det_nodes = root.findall(".//nfe:NFe/nfe:infNFe/nfe:det", namespaces=NFE_NS)
    
    # Fallback: busca direto por det se o primeiro não encontrar
    if not det_nodes:
        det_nodes = root.findall(".//nfe:infNFe/nfe:det", namespaces=NFE_NS)
    
    # Fallback 2: busca em qualquer lugar
    if not det_nodes:
        det_nodes = root.findall(".//nfe:det", namespaces=NFE_NS)
    
    items: list[dict[str, Any]] = []
    
    sum_vProd = 0.0
    missing_any = 0
    
    for det in det_nodes:
        it = _extract_item(det)
        missing, confidence = _confidence_for_item(it)
        
        if it.get("vProd") is not None:
            sum_vProd += float(it["vProd"])
        if missing:
            missing_any += 1
        
        items.append({
            "item": it,
            "missing_fields": missing,
            "confidence": confidence,
            "flags": {
                "incomplete": len(missing) > 0,
            },
            "field_sources": {k: "xml" for k, v in it.items() if v is not None},
        })
    
    # Sumário
    total_vProd = totals.get("vProd")
    summary = {
        "count_items": len(items),
        "items_incomplete": missing_any,
        "sum_items_vProd": round(sum_vProd, 2),
        "total_vProd_xml": total_vProd,
        "diff_items_vs_total_vProd": (
            round(sum_vProd - float(total_vProd), 2) if total_vProd is not None else None
        ),
    }
    
    return NFeExtractResult(
        received=True,
        filename=filename,
        sha256=sha256,
        count=len(items),
        header=header,
        emit=emit,
        dest=dest,
        totals=totals,
        items=items,
        summary=summary,
    )


def parse_nfe_xml_paged(
    xml_bytes: bytes,
    filename: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """
    Faz parse de NF-e com paginação de itens.
    
    Args:
        xml_bytes: Conteúdo do XML
        filename: Nome do arquivo
        page: Número da página (1-based)
        page_size: Tamanho da página
        
    Returns:
        Dicionário com resultado paginado
    """
    result = parse_nfe_xml(xml_bytes=xml_bytes, filename=filename)
    
    if not result.received:
        return {
            "received": False,
            "filename": result.filename,
            "sha256": result.sha256,
            "count_total": 0,
            "count_page": 0,
            "page": page,
            "page_size": page_size,
            "pages": 0,
            "header": {},
            "emit": {},
            "dest": {},
            "totals": {},
            "items": [],
            "summary": result.summary,
        }
    
    total = result.count
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 500))
    pages = (total + page_size - 1) // page_size
    
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    sliced = result.items[start:end] if start < total else []
    
    summary = dict(result.summary or {})
    summary["count_items"] = total
    
    return {
        "received": True,
        "filename": result.filename,
        "sha256": result.sha256,
        "count_total": total,
        "count_page": len(sliced),
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "header": result.header,
        "emit": result.emit,
        "dest": result.dest,
        "totals": result.totals,
        "items": sliced,
        "summary": summary,
    }


# =============================================================================
# Exportação CSV
# =============================================================================

def export_nfe_items_to_csv(items: list[dict[str, Any]]) -> str:
    """
    Exporta itens de NF-e para CSV.
    
    Args:
        items: Lista de itens (formato do extractor)
        
    Returns:
        String CSV com separador ";"
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    
    # Cabeçalho
    writer.writerow([
        "nItem",
        "cProd",
        "xProd",
        "NCM",
        "CFOP",
        "uCom",
        "qCom",
        "vUnCom",
        "vProd",
        "icms_tipo",
        "cst",
        "csosn",
        "vBC",
        "vICMS",
        "pis_tipo",
        "pis_cst",
        "vPIS",
        "cofins_tipo",
        "cofins_cst",
        "vCOFINS",
        "confidence",
        "missing_fields",
        "product_class",
        "suggested_group",
        "decision",
        "reasons",
    ])
    
    # Dados
    for row in items:
        it = row.get("item", {}) or {}
        norm = row.get("normalized", {}) or {}
        decision = row.get("decision")
        reasons = row.get("reasons", []) or []
        
        writer.writerow([
            it.get("nItem") or "",
            it.get("cProd") or "",
            it.get("xProd") or "",
            it.get("NCM") or "",
            it.get("CFOP") or "",
            it.get("uCom") or "",
            it.get("qCom") if it.get("qCom") is not None else "",
            it.get("vUnCom") if it.get("vUnCom") is not None else "",
            it.get("vProd") if it.get("vProd") is not None else "",
            it.get("icms_tipo") or "",
            it.get("cst") or "",
            it.get("csosn") or "",
            it.get("vBC") if it.get("vBC") is not None else "",
            it.get("vICMS") if it.get("vICMS") is not None else "",
            it.get("pis_tipo") or "",
            it.get("pis_cst") or "",
            it.get("vPIS") if it.get("vPIS") is not None else "",
            it.get("cofins_tipo") or "",
            it.get("cofins_cst") or "",
            it.get("vCOFINS") if it.get("vCOFINS") is not None else "",
            row.get("confidence") if row.get("confidence") is not None else "",
            ",".join(row.get("missing_fields", []) or []),
            norm.get("product_class") or "",
            norm.get("suggested_group") or "",
            decision or "",
            "|".join([str(x) for x in reasons]),
        ])
    
    return output.getvalue()
