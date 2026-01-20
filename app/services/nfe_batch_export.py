from __future__ import annotations

import csv
import io
import zipfile
from typing import Any, Dict, List, Optional

from app.services.nfe_xml_extract import parse_nfe_xml
from app.services.nfe_item_normalizer import normalize_nfe_items


def _is_xml_name(name: str) -> bool:
    n = (name or "").lower().strip()
    return n.endswith(".xml")


def export_nfe_zip_batch_to_csv(
    zip_bytes: bytes,
    *,
    max_files: int = 200,
    max_total_bytes: int = 50 * 1024 * 1024,
) -> str:
    """
    Exporta um ZIP com múltiplas NF-e XMLs para um CSV consolidado (1 linha por item).
    Inclui metadados do arquivo e da NF-e para rastreabilidade.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")

    # Header do CSV consolidado
    writer.writerow(
        [
            "batch_file",
            "file",
            "chave_nfe",
            "numero",
            "serie",
            "data_emissao",
            "natureza_operacao",
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

    if not zip_bytes:
        return output.getvalue()

    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = [n for n in zf.namelist() if _is_xml_name(n) and not n.endswith("/")]
    names = [n for n in names if "__MACOSX" not in n]
    if not names:
        return output.getvalue()

    if len(names) > max_files:
        names = names[:max_files]

    decompressed_total = 0

    for name in names:
        xml_bytes = zf.read(name)
        decompressed_total += len(xml_bytes)
        if decompressed_total > max_total_bytes:
            break

        parsed = parse_nfe_xml(xml_bytes=xml_bytes, filename=name)
        if not getattr(parsed, "received", False):
            continue

        enriched, _norm_sum = normalize_nfe_items(parsed.items)

        h = parsed.header or {}
        chave = h.get("chave_nfe")

        for row in enriched:
            it = row.get("item", {}) or {}
            norm = row.get("normalized", {}) or {}
            reasons = row.get("reasons", []) or []

            writer.writerow(
                [
                    "",  # batch_file preenchido pelo endpoint (melhor)
                    name,
                    chave or "",
                    h.get("numero") or "",
                    h.get("serie") or "",
                    h.get("data_emissao") or "",
                    h.get("natureza_operacao") or "",
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
                    row.get("decision") or "",
                    "|".join([str(x) for x in reasons]),
                ]
            )

    return output.getvalue()
