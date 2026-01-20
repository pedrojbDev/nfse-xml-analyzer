from __future__ import annotations

import csv
import io
import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.services.cnae_rules import validate_cnae_vs_descricao
from app.services.decision import decide_for_erp_from_xml_item




ABRASF_NS = {"nfse": "http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digits_only(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    d = re.sub(r"\D+", "", s)
    return d or None


def _fmt_cnpj_mask(digits: Optional[str]) -> Optional[str]:
    if not digits:
        return None
    if len(digits) != 14:
        return digits
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
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


def _competencia_mm_yyyy(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.strftime("%m/%Y")


def _to_float(val: Optional[str]) -> Optional[float]:
    """
    XML pode vir com:
      - "13750"
      - "5863,95"
      - "7462.79"
    """
    if val is None:
        return None
    s = val.strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        f = float(s)
    except Exception:
        return None
    return f if f > 0 else None


def _to_int_boolflag(val: Optional[str]) -> Optional[int]:
    """
    Flags como IssRetido geralmente vêm "1" ou "2" (ou "true/false" em emissores específicos).
    Mantemos como int quando possível.
    """
    if val is None:
        return None
    s = val.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    s_low = s.lower()
    if s_low in ("true", "yes", "sim"):
        return 1
    if s_low in ("false", "no", "nao", "não"):
        return 0
    return None


def _guess_descricao_servico(discriminacao: Optional[str]) -> str:
    if not discriminacao:
        return "servico"
    d = discriminacao.strip()
    d_upper = d.upper()
    if "HONOR" in d_upper:
        return "honorarios medicos"
    resumo = re.sub(r"\s+", " ", d)[:120].strip()
    return resumo if resumo else "servico"


@dataclass(frozen=True)
class XmlExtractResult:
    received: bool
    filename: str
    sha256: str
    count: int
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]


def _confidence_for_item(fields: Dict[str, Any]) -> Tuple[List[str], float]:
    missing = [k for k, v in fields.items() if v is None]
    confidence = round(1 - (len(missing) / len(fields)), 2) if fields else 0.0
    return missing, confidence


def _findtext(comp: ET.Element, xpath: str) -> Optional[str]:
    return comp.findtext(xpath, default=None, namespaces=ABRASF_NS)


def _extract_taxes(comp: ET.Element) -> Dict[str, Any]:
    """
    Extrai tributos do XML ABRASF.
    Mantém tudo opcional: se não existir no emissor, retorna None nos campos.
    """
    # Em alguns emissores o valor líquido aparece aqui:
    valor_liquido_nfse = _to_float(_findtext(comp, ".//nfse:InfNfse/nfse:ValorLiquidoNfse"))

    # Servico/Valores (ABRASF)
    iss_retido = _to_int_boolflag(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:IssRetido"))

    base_calculo = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:BaseCalculo"))
    aliquota = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:Aliquota"))

    valor_iss = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorIss"))
    valor_iss_retido = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorIssRetido"))

    valor_deducoes = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorDeducoes"))

    valor_pis = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorPis"))
    valor_cofins = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorCofins"))
    valor_inss = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorInss"))
    valor_ir = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorIr"))
    valor_csll = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorCsll"))

    outras_retencoes = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:OutrasRetencoes"))
    desconto_incondicionado = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:DescontoIncondicionado"))
    desconto_condicionado = _to_float(_findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:DescontoCondicionado"))

    taxes = {
        "iss_retido": iss_retido,  # normalmente 1=sim, 2=não (depende do emissor)
        "base_calculo": base_calculo,
        "aliquota": aliquota,
        "valor_iss": valor_iss,
        "valor_iss_retido": valor_iss_retido,
        "valor_deducoes": valor_deducoes,
        "valor_pis": valor_pis,
        "valor_cofins": valor_cofins,
        "valor_inss": valor_inss,
        "valor_ir": valor_ir,
        "valor_csll": valor_csll,
        "outras_retencoes": outras_retencoes,
        "desconto_incondicionado": desconto_incondicionado,
        "desconto_condicionado": desconto_condicionado,
        "valor_liquido_nfse": valor_liquido_nfse,
    }
    return taxes

def _calc_valor_liquido_politica_b(valor_servicos: Optional[float], taxes: Dict[str, Any]) -> Optional[float]:
    """
    Política B (determinística):
      valor_liquido = valor_servicos
                   - ISS Retido (quando existir)
                   - PIS
                   - COFINS
                   - INSS
                   - IR
                   - CSLL (opcional, mas recomendado incluir)
                   - OutrasRetencoes (opcional; aqui NÃO subtraímos por padrão para evitar falso negativo)
                   - Descontos (depende do município; aqui NÃO subtraímos por padrão)

    Regras:
      - Se valor_servicos for None -> None
      - Campos ausentes ou None -> 0
      - Nunca retorna negativo (se der negativo, retorna None e deixa para checks futuros)
    """
    if valor_servicos is None:
        return None

    iss_retido = taxes.get("valor_iss_retido") or 0.0
    pis = taxes.get("valor_pis") or 0.0
    cofins = taxes.get("valor_cofins") or 0.0
    inss = taxes.get("valor_inss") or 0.0
    ir = taxes.get("valor_ir") or 0.0
    csll = taxes.get("valor_csll") or 0.0

    liquido = float(valor_servicos) - float(iss_retido) - float(pis) - float(cofins) - float(inss) - float(ir) - float(csll)

    # blindagem mínima (evita "líquido" negativo por layout/retencoes inconsistentes)
    if liquido < 0:
        return None

    return round(liquido, 2)

def _normalize_cnae(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D+", "", str(raw))
    return digits or None


def _extract_cnae_from_comp(comp: ET.Element) -> Optional[str]:
    """
    Extrai CNAE do XML.
    Suporta:
      - com namespace (nfse:CodigoCnae)
      - sem namespace (<CodigoCnae>)
      - variações comuns (CodigoCNAE, Cnae, CNAE)
    """
    # 1) Tentativa direta com namespace (ABRASF)
    candidates_ns = [
        ".//nfse:Servico/nfse:CodigoCnae",
        ".//nfse:Servico/nfse:CodigoCNAE",
        ".//nfse:Servico/nfse:Cnae",
        ".//nfse:Servico/nfse:CNAE",
        ".//nfse:CodigoCnae",
        ".//nfse:CodigoCNAE",
        ".//nfse:Cnae",
        ".//nfse:CNAE",
    ]
    for xp in candidates_ns:
        val = _findtext(comp, xp)  # usa ABRASF_NS internamente
        if val and val.strip():
            return _normalize_cnae(val)

    # 2) Fallback sem namespace (seu caso: <CodigoCnae>8610101</CodigoCnae>)
    candidates_no_ns = [
        ".//Servico/CodigoCnae",
        ".//Servico/CodigoCNAE",
        ".//Servico/Cnae",
        ".//Servico/CNAE",
        ".//CodigoCnae",
        ".//CodigoCNAE",
        ".//Cnae",
        ".//CNAE",
    ]
    for xp in candidates_no_ns:
        node = comp.find(xp)
        if node is not None and (node.text or "").strip():
            return _normalize_cnae(node.text)

    # 3) Fallback final: varrer por "local-name" (pega mesmo se houver namespace diferente)
    for el in comp.iter():
        tag = el.tag
        local = tag.split("}", 1)[-1] if "}" in tag else tag
        if local in ("CodigoCnae", "CodigoCNAE", "Cnae", "CNAE"):
            txt = (el.text or "").strip()
            if txt:
                return _normalize_cnae(txt)

    return None




def _parse_all_items_from_xml(xml_bytes: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse completo do XML.
    Política A: valor_total := ValorServicos
    Acrescenta bloco 'taxes' por nota.
    """
    root = ET.fromstring(xml_bytes)
    comp_nodes = root.findall(".//nfse:CompNfse", ABRASF_NS)

    items: List[Dict[str, Any]] = []

    total_valor_servicos = 0.0
    missing_valor_total = 0
    missing_competencia = 0
    missing_crit_any = 0
    count_dec_auto = 0
    count_dec_review = 0
    count_dec_block = 0


    # Somatórios tributários (apenas quando existirem)
    sum_valor_iss = 0.0
    sum_valor_iss_retido = 0.0
    sum_valor_pis = 0.0
    sum_valor_cofins = 0.0
    sum_valor_inss = 0.0
    sum_valor_ir = 0.0
    sum_valor_csll = 0.0
    sum_valor_liquido_politica_b = 0.0
    count_liquido_politica_b = 0
    count_valor_liquido_informado = 0
    count_valor_liquido_divergente = 0

    count_cnae_ok = 0
    count_cnae_alert = 0
    count_cnae_unknown = 0



    critical = ("numero_nota", "data_emissao", "valor_total", "competencia", "cnpj_fornecedor")

    for comp in comp_nodes:
        numero = _findtext(comp, ".//nfse:InfNfse/nfse:Numero")
        data_emissao_raw = _findtext(comp, ".//nfse:InfNfse/nfse:DataEmissao")

        competencia_raw = _findtext(comp, ".//nfse:InfNfse/nfse:Competencia")
        if not competencia_raw:
            competencia_raw = _findtext(comp, ".//nfse:Competencia")

        cnpj_prestador = _findtext(comp, ".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:Cnpj")

        valor_servicos_raw = _findtext(comp, ".//nfse:Servico/nfse:Valores/nfse:ValorServicos")
        discriminacao = _findtext(comp, ".//nfse:Servico/nfse:Discriminacao")
        discriminacao_raw = discriminacao.strip() if discriminacao else None


        dt_emissao = _parse_iso_datetime(data_emissao_raw)
        dt_comp = _parse_iso_datetime(competencia_raw)

        # Campos principais (contrato atual)
        fields = {
            "numero_nota": (numero.strip() if numero else None),
            "data_emissao": _fmt_br_datetime(dt_emissao),
            "cnpj_fornecedor": _fmt_cnpj_mask(_digits_only(cnpj_prestador)),
            "valor_total": _to_float(valor_servicos_raw),  # Política A
            "competencia": _competencia_mm_yyyy(dt_comp),
            "descricao_servico": _guess_descricao_servico(discriminacao),
            "cnae": _extract_cnae_from_comp(comp),
            
        }

        # Validação determinística: Descrição x CNAE (regras plugáveis via CSV)
        validation_cnae = validate_cnae_vs_descricao(
        cnae=fields.get("cnae"),
        descricao=discriminacao_raw or fields.get("descricao_servico"),
)



        missing, confidence = _confidence_for_item(fields)
        missing_crit = [k for k in critical if not fields.get(k)]

        if fields["valor_total"] is None:
            missing_valor_total += 1
        if fields["competencia"] is None:
            missing_competencia += 1
        if missing_crit:
            missing_crit_any += 1

        if fields["valor_total"] is not None:
            total_valor_servicos += float(fields["valor_total"])

        # Tributos
        taxes = _extract_taxes(comp)
        # Política B: cálculo do valor líquido (determinístico) a partir de ValorServicos e retenções do XML
        taxes["valor_liquido_calculado_politica_b"] = _calc_valor_liquido_politica_b(fields.get("valor_total"), taxes)

        # Check: se o XML informar ValorLiquidoNfse, comparamos com o calculado (Política B)
        tolerancia = 0.05  # R$ 0,05 (arredondamentos)
        vl_inf = taxes.get("valor_liquido_nfse")
        vl_cal = taxes.get("valor_liquido_calculado_politica_b")

        if vl_inf is not None and vl_cal is not None:
            diff = round(float(vl_inf) - float(vl_cal), 2)
            taxes["valor_liquido_diff_xml_vs_calc"] = diff
            taxes["valor_liquido_divergente"] = abs(diff) > tolerancia
        else:
            taxes["valor_liquido_diff_xml_vs_calc"] = None
            taxes["valor_liquido_divergente"] = False

        if taxes.get("valor_liquido_nfse") is not None:
            count_valor_liquido_informado += 1
        if taxes.get("valor_liquido_divergente") is True:
            count_valor_liquido_divergente += 1



        vlb = taxes.get("valor_liquido_calculado_politica_b")
        if vlb is not None:
            sum_valor_liquido_politica_b += float(vlb)
            count_liquido_politica_b += 1



        # Somatórios tributários (somente quando existirem)
        if taxes.get("valor_iss") is not None:
            sum_valor_iss += float(taxes["valor_iss"])
        if taxes.get("valor_iss_retido") is not None:
            sum_valor_iss_retido += float(taxes["valor_iss_retido"])
        if taxes.get("valor_pis") is not None:
            sum_valor_pis += float(taxes["valor_pis"])
        if taxes.get("valor_cofins") is not None:
            sum_valor_cofins += float(taxes["valor_cofins"])
        if taxes.get("valor_inss") is not None:
            sum_valor_inss += float(taxes["valor_inss"])
        if taxes.get("valor_ir") is not None:
            sum_valor_ir += float(taxes["valor_ir"])
        if taxes.get("valor_csll") is not None:
            sum_valor_csll += float(taxes["valor_csll"])

        status_cnae = validation_cnae.get("status")
        if status_cnae == "ok":
            count_cnae_ok += 1
        elif status_cnae == "alert":
            count_cnae_alert += 1
        else:
            count_cnae_unknown += 1


        item = {
            
            "fields": fields,
            "taxes": taxes,
            "missing_fields": missing,
            "confidence": confidence,
            "flags": {
                "needs_review": confidence < 0.95,
                "incomplete": len(missing) > 0,
                "missing_critical": len(missing_crit) > 0,
            },
            "field_sources": {k: "xml" for k, v in fields.items() if v is not None},
            "tax_sources": {k: "xml" for k, v in taxes.items() if v is not None},
            "xml_raw": {
                "numero": numero,
                "data_emissao": data_emissao_raw,
                "competencia": competencia_raw,
                "cnpj_prestador": cnpj_prestador,
                "valor_servicos": valor_servicos_raw,
            },
            "validations": {
            "cnae_vs_descricao": validation_cnae
            },
        }
        decision, reasons = decide_for_erp_from_xml_item(item)
        item["decision"] = decision
        item["reasons"] = reasons

        if decision == "AUTO":
            count_dec_auto += 1
        elif decision == "REVIEW":
            count_dec_review += 1
        else:
            count_dec_block += 1
        items.append(item)
    

    summary = {
        "count": len(items),
        "decision_summary": {
            "auto": count_dec_auto,
            "review": count_dec_review,
            "block": count_dec_block,
        },
        "sum_valor_total_politica_a": round(total_valor_servicos, 2),

        "count_valor_liquido_informado_xml": count_valor_liquido_informado,
        "count_valor_liquido_divergente": count_valor_liquido_divergente,


        # NOVO: Política B (líquido calculado)
        "sum_valor_liquido_politica_b": round(sum_valor_liquido_politica_b, 2),
        "count_liquido_politica_b": count_liquido_politica_b,

        "missing_valor_total": missing_valor_total,
        "missing_competencia": missing_competencia,
        "items_with_missing_critical": missing_crit_any,

        # Totais tributários (quando existirem no XML)
        "tax_totals": {
            "sum_valor_iss": round(sum_valor_iss, 2),
            "sum_valor_iss_retido": round(sum_valor_iss_retido, 2),
            "sum_valor_pis": round(sum_valor_pis, 2),
            "sum_valor_cofins": round(sum_valor_cofins, 2),
            "sum_valor_inss": round(sum_valor_inss, 2),
            "sum_valor_ir": round(sum_valor_ir, 2),
            "sum_valor_csll": round(sum_valor_csll, 2),
        },

        "policy": "A (valor_total := ValorServicos)",

        "validation_summary": {
            "cnae_vs_descricao": {
                "ok": count_cnae_ok,
                "alert": count_cnae_alert,
                "unknown": count_cnae_unknown,
            }
},
    }


    return items, summary


def parse_nfse_xml_abrasf(xml_bytes: bytes, filename: str = "upload.xml") -> XmlExtractResult:
    sha256 = _sha256(xml_bytes)

    if not xml_bytes:
        return XmlExtractResult(
            received=False,
            filename=filename,
            sha256=sha256,
            count=0,
            items=[],
            summary={"error": "Empty body"},
        )

    try:
        items, summary = _parse_all_items_from_xml(xml_bytes)
    except Exception as exc:
        return XmlExtractResult(
            received=False,
            filename=filename,
            sha256=sha256,
            count=0,
            items=[],
            summary={"error": "Invalid XML or parse failure", "exception": str(exc)},
        )

    return XmlExtractResult(
        received=True,
        filename=filename,
        sha256=sha256,
        count=len(items),
        items=items,
        summary=summary,
    )


def parse_nfse_xml_abrasf_paged(xml_bytes: bytes, filename: str, page: int, page_size: int) -> Dict[str, Any]:
    result = parse_nfse_xml_abrasf(xml_bytes=xml_bytes, filename=filename)
    if not result.received:
        return {
            "received": False,
            "filename": result.filename,
            "sha256": result.sha256,
            "count": 0,              # compat antigo (total)
            "count_total": 0,        # novo
            "count_page": 0,         # novo
            "page": page,
            "page_size": page_size,
            "pages": 0,
            "items": [],
            "summary": result.summary,
        }

    total = result.count  # TOTAL real do XML (ex.: 380)
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 500))
    pages = (total + page_size - 1) // page_size

    start = (page - 1) * page_size
    end = min(start + page_size, total)
    sliced = result.items[start:end] if start < total else []

    # Garante que summary "count" represente o TOTAL (evita qualquer inconsistência)
    summary = dict(result.summary or {})
    summary["count"] = total

    return {
        "received": True,
        "filename": result.filename,
        "sha256": result.sha256,

        # compatibilidade: "count" continua sendo o TOTAL
        "count": total,

        # novos campos explícitos (recomendado a UI usar)
        "count_total": total,
        "count_page": len(sliced),

        "page": page,
        "page_size": page_size,
        "pages": pages,
        "items": sliced,
        "summary": summary,
    }




def export_nfse_items_to_csv(items: List[Dict[str, Any]]) -> str:
    """
    CSV operacional: inclui colunas principais + tributos + validações CNAE x descrição.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")

    writer.writerow(
        [
            "numero_nota",
            "data_emissao",
            "cnpj_fornecedor",
            "competencia",
            "cnae",
            "cnae_vs_descricao_status",
            "cnae_vs_descricao_reason",
            "cnae_vs_descricao_label",
            "cnae_vs_descricao_severity",
            "valor_total",
            "descricao_servico",
            # Tributos
            "iss_retido",
            "base_calculo",
            "aliquota",
            "valor_iss",
            "valor_iss_retido",
            "valor_deducoes",
            "valor_pis",
            "valor_cofins",
            "valor_inss",
            "valor_ir",
            "valor_csll",
            "outras_retencoes",
            "desconto_incondicionado",
            "desconto_condicionado",
            "valor_liquido_nfse",
            "valor_liquido_calculado_politica_b",
            "decision",
            "reasons",

        ]
    )

    for item in items:
        f = item.get("fields", {}) or {}
        t = item.get("taxes", {}) or {}
        v = (item.get("validations", {}) or {}).get("cnae_vs_descricao", {}) or {}

        writer.writerow(
            [
                f.get("numero_nota") or "",
                f.get("data_emissao") or "",
                f.get("cnpj_fornecedor") or "",
                f.get("competencia") or "",
                f.get("cnae") or "",
                v.get("status") or "",
                v.get("reason") or "",
                v.get("rule_label") or "",
                v.get("severity") or "",
                f.get("valor_total") if f.get("valor_total") is not None else "",
                f.get("descricao_servico") or "",
                # Tributos
                t.get("iss_retido") if t.get("iss_retido") is not None else "",
                t.get("base_calculo") if t.get("base_calculo") is not None else "",
                t.get("aliquota") if t.get("aliquota") is not None else "",
                t.get("valor_iss") if t.get("valor_iss") is not None else "",
                t.get("valor_iss_retido") if t.get("valor_iss_retido") is not None else "",
                t.get("valor_deducoes") if t.get("valor_deducoes") is not None else "",
                t.get("valor_pis") if t.get("valor_pis") is not None else "",
                t.get("valor_cofins") if t.get("valor_cofins") is not None else "",
                t.get("valor_inss") if t.get("valor_inss") is not None else "",
                t.get("valor_ir") if t.get("valor_ir") is not None else "",
                t.get("valor_csll") if t.get("valor_csll") is not None else "",
                t.get("outras_retencoes") if t.get("outras_retencoes") is not None else "",
                t.get("desconto_incondicionado") if t.get("desconto_incondicionado") is not None else "",
                t.get("desconto_condicionado") if t.get("desconto_condicionado") is not None else "",
                t.get("valor_liquido_nfse") if t.get("valor_liquido_nfse") is not None else "",
                t.get("valor_liquido_calculado_politica_b") if t.get("valor_liquido_calculado_politica_b") is not None else "",
                item.get("decision") or "",
                ",".join(item.get("reasons", []) or []),
            ]
        )

    return output.getvalue()


