from __future__ import annotations

import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


NFE_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digits_only(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    d = re.sub(r"\D+", "", s)
    return d or None


def _to_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _to_int(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def _findtext(root: ET.Element, xpath: str) -> Optional[str]:
    return root.findtext(xpath, default=None, namespaces=NFE_NS)


def _parse_iso_dt(dt_str: Optional[str]) -> Optional[datetime]:
    """
    NF-e costuma vir com timezone, ex: 2026-01-12T11:45:12-03:00
    datetime.fromisoformat lida bem com isso.
    """
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def _fmt_br_datetime(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _safe_get_chave_from_nfeproc(root: ET.Element) -> Optional[str]:
    """
    Tenta extrair a chave:
    1) nfeProc/protNFe/infProt/chNFe
    2) NFe/infNFe/@Id => "NFe<chave>"
    """
    ch = _findtext(root, ".//nfe:protNFe/nfe:infProt/nfe:chNFe")
    if ch:
        return _digits_only(ch)

    inf = root.find(".//nfe:NFe/nfe:infNFe", namespaces=NFE_NS)
    if inf is not None:
        _id = inf.attrib.get("Id")
        if _id:
            # Id geralmente "NFe{44dig}"
            digits = _digits_only(_id)
            if digits and len(digits) >= 44:
                return digits[-44:]
    return None


def _extract_header(root: ET.Element) -> Dict[str, Any]:
    ide = root.find(".//nfe:NFe/nfe:infNFe/nfe:ide", namespaces=NFE_NS)

    nNF = _findtext(root, ".//nfe:ide/nfe:nNF")
    serie = _findtext(root, ".//nfe:ide/nfe:serie")
    dhEmi = _findtext(root, ".//nfe:ide/nfe:dhEmi") or _findtext(root, ".//nfe:ide/nfe:dEmi")
    natOp = _findtext(root, ".//nfe:ide/nfe:natOp")
    tpNF = _findtext(root, ".//nfe:ide/nfe:tpNF")  # 0 entrada, 1 saída (padrão NFe)
    tpAmb = _findtext(root, ".//nfe:ide/nfe:tpAmb")

    dt = _parse_iso_dt(dhEmi)
    header = {
        "chave_nfe": _safe_get_chave_from_nfeproc(root),
        "numero": _to_int(nNF),
        "serie": _to_int(serie),
        "data_emissao": _fmt_br_datetime(dt),
        "natureza_operacao": natOp.strip() if natOp else None,
        "tipo_nf": _to_int(tpNF),
        "ambiente": _to_int(tpAmb),
    }
    return header


def _extract_party(root: ET.Element, kind: str) -> Dict[str, Any]:
    """
    kind: "emit" ou "dest"
    """
    base = f".//nfe:{kind}"
    cnpj = _findtext(root, base + "/nfe:CNPJ") or _findtext(root, base + "/nfe:CPF")
    xNome = _findtext(root, base + "/nfe:xNome")
    uf = _findtext(root, base + "/nfe:ender" + ("Emit" if kind == "emit" else "Dest") + "/nfe:UF")
    mun = _findtext(root, base + "/nfe:ender" + ("Emit" if kind == "emit" else "Dest") + "/nfe:xMun")

    return {
        "doc": _digits_only(cnpj),
        "nome": xNome.strip() if xNome else None,
        "uf": uf.strip() if uf else None,
        "municipio": mun.strip() if mun else None,
    }


def _extract_totals(root: ET.Element) -> Dict[str, Any]:
    # Total ICMSTot
    vNF = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vNF"))
    vProd = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vProd"))
    vDesc = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vDesc"))
    vFrete = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vFrete"))
    vOutro = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vOutro"))

    vICMS = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vICMS"))
    vICMSST = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vST"))
    vIPI = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vIPI"))
    vPIS = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vPIS"))
    vCOFINS = _to_float(_findtext(root, ".//nfe:total/nfe:ICMSTot/nfe:vCOFINS"))

    return {
        "vNF": vNF,
        "vProd": vProd,
        "vDesc": vDesc,
        "vFrete": vFrete,
        "vOutro": vOutro,
        "vICMS": vICMS,
        "vICMSST": vICMSST,
        "vIPI": vIPI,
        "vPIS": vPIS,
        "vCOFINS": vCOFINS,
    }


def _extract_icms_from_det(det: ET.Element) -> Dict[str, Any]:
    """
    ICMS varia (ICMS00, ICMS10, ICMS20, ICMS40, ICMS60, ICMS90, ICMSSN101, etc).
    Aqui extraímos:
      - tipo_tag (ex: ICMS00, ICMSSN102)
      - CST/CSOSN
      - base e valor quando existirem
    """
    icms_parent = det.find(".//nfe:imposto/nfe:ICMS", namespaces=NFE_NS)
    if icms_parent is None:
        return {}

    # Primeiro filho real do ICMS é o grupo (ICMS00, ICMSSN102, etc.)
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
        "vBC": _to_float(vBC),
        "vICMS": _to_float(vICMS),
    }


def _extract_pis_from_det(det: ET.Element) -> Dict[str, Any]:
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

    return {"pis_tipo": local, "pis_cst": cst, "vPIS": _to_float(vPIS)}


def _extract_cofins_from_det(det: ET.Element) -> Dict[str, Any]:
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

    return {"cofins_tipo": local, "cofins_cst": cst, "vCOFINS": _to_float(vCOFINS)}


def _extract_item(det: ET.Element) -> Dict[str, Any]:
    n_item = det.attrib.get("nItem")

    cProd = det.findtext(".//nfe:prod/nfe:cProd", default=None, namespaces=NFE_NS)
    xProd = det.findtext(".//nfe:prod/nfe:xProd", default=None, namespaces=NFE_NS)
    ncm = det.findtext(".//nfe:prod/nfe:NCM", default=None, namespaces=NFE_NS)
    cfop = det.findtext(".//nfe:prod/nfe:CFOP", default=None, namespaces=NFE_NS)

    uCom = det.findtext(".//nfe:prod/nfe:uCom", default=None, namespaces=NFE_NS)
    qCom = det.findtext(".//nfe:prod/nfe:qCom", default=None, namespaces=NFE_NS)
    vUnCom = det.findtext(".//nfe:prod/nfe:vUnCom", default=None, namespaces=NFE_NS)
    vProd = det.findtext(".//nfe:prod/nfe:vProd", default=None, namespaces=NFE_NS)

    item = {
        "nItem": _to_int(n_item),
        "cProd": cProd.strip() if cProd else None,
        "xProd": xProd.strip() if xProd else None,
        "NCM": ncm.strip() if ncm else None,
        "CFOP": cfop.strip() if cfop else None,
        "uCom": uCom.strip() if uCom else None,
        "qCom": _to_float(qCom),
        "vUnCom": _to_float(vUnCom),
        "vProd": _to_float(vProd),
    }

    # impostos por item
    item.update(_extract_icms_from_det(det))
    item.update(_extract_pis_from_det(det))
    item.update(_extract_cofins_from_det(det))

    return item


def _confidence_for_item(item: Dict[str, Any]) -> Tuple[List[str], float]:
    # campos mínimos para item NF-e
    keys = ("cProd", "xProd", "NCM", "CFOP", "qCom", "vUnCom", "vProd")
    missing = [k for k in keys if not item.get(k)]
    confidence = round(1 - (len(missing) / len(keys)), 2)
    return missing, confidence


@dataclass(frozen=True)
class NFeExtractResult:
    received: bool
    filename: str
    sha256: str
    count: int
    header: Dict[str, Any]
    emit: Dict[str, Any]
    dest: Dict[str, Any]
    totals: Dict[str, Any]
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]


def parse_nfe_xml(xml_bytes: bytes, filename: str = "upload.xml") -> NFeExtractResult:
    sha256 = _sha256(xml_bytes)

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

    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
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

    header = _extract_header(root)
    emit = _extract_party(root, "emit")
    dest = _extract_party(root, "dest")
    totals = _extract_totals(root)

    det_nodes = root.findall(".//nfe:NFe/nfe:infNFe/nfe:det", namespaces=NFE_NS)
    items: List[Dict[str, Any]] = []

    sum_vProd = 0.0
    missing_any = 0

    for det in det_nodes:
        it = _extract_item(det)
        missing, confidence = _confidence_for_item(it)

        if it.get("vProd") is not None:
            sum_vProd += float(it["vProd"])
        if missing:
            missing_any += 1

        items.append(
            {
                "item": it,
                "missing_fields": missing,
                "confidence": confidence,
                "flags": {
                    "incomplete": len(missing) > 0,
                },
                "field_sources": {k: "xml" for k, v in it.items() if v is not None},
            }
        )

    summary = {
        "count_items": len(items),
        "items_incomplete": missing_any,
        "sum_items_vProd": round(sum_vProd, 2),
        "total_vProd_xml": totals.get("vProd"),
        "diff_items_vs_total_vProd": (
            round(sum_vProd - float(totals["vProd"]), 2) if totals.get("vProd") is not None else None
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


def parse_nfe_xml_paged(xml_bytes: bytes, filename: str, page: int, page_size: int) -> Dict[str, Any]:
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


def export_nfe_items_to_csv(items: List[Dict[str, Any]]) -> str:
    """
    CSV operacional por item (det).
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")

    writer.writerow(
        [
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
        ]
    )

    for row in items:
        it = row.get("item", {}) or {}
        norm = row.get("normalized", {}) or {}
        decision = row.get("decision")
        reasons = row.get("reasons", []) or []
        writer.writerow(
            [
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

            ]
        )

    return output.getvalue()

