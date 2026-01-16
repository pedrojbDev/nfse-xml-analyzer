# demo_streamlit/app.py
import io
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="NFSe Extractor Demo (XML)",
    page_icon="📄",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def post_xml(url: str, xml_bytes: bytes, filename: str, timeout: int = 60) -> requests.Response:
    headers = {"X-Filename": filename, "Content-Type": "application/xml"}
    return requests.post(url, headers=headers, data=xml_bytes, timeout=timeout)


def safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def format_currency_br(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    try:
        s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return str(v)


def items_to_dataframe(items: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for it in items:
        f = it.get("fields", {}) or {}
        t = it.get("taxes", {}) or {}
        v_all = it.get("validations", {}) or {}
        v_cnae = v_all.get("cnae_vs_descricao", {}) or {}

        row = {
            # principais
            "numero_nota": f.get("numero_nota"),
            "data_emissao": f.get("data_emissao"),
            "competencia": f.get("competencia"),
            "cnpj_fornecedor": f.get("cnpj_fornecedor"),
            "cnae": f.get("cnae"),
            "valor_total": f.get("valor_total"),
            "descricao_servico": f.get("descricao_servico"),
            # validação CNAE x descrição
            "cnae_vs_descricao_status": v_cnae.get("status"),
            "cnae_vs_descricao_severity": v_cnae.get("severity"),
            "cnae_vs_descricao_label": v_cnae.get("rule_label"),
            "cnae_vs_descricao_reason": v_cnae.get("reason"),
            # tributos
            "iss_retido": t.get("iss_retido"),
            "base_calculo": t.get("base_calculo"),
            "aliquota": t.get("aliquota"),
            "valor_iss": t.get("valor_iss"),
            "valor_iss_retido": t.get("valor_iss_retido"),
            "valor_deducoes": t.get("valor_deducoes"),
            "valor_pis": t.get("valor_pis"),
            "valor_cofins": t.get("valor_cofins"),
            "valor_inss": t.get("valor_inss"),
            "valor_ir": t.get("valor_ir"),
            "valor_csll": t.get("valor_csll"),
            "outras_retencoes": t.get("outras_retencoes"),
            "desconto_incondicionado": t.get("desconto_incondicionado"),
            "desconto_condicionado": t.get("desconto_condicionado"),
            "valor_liquido_nfse": t.get("valor_liquido_nfse"),
            "valor_liquido_calculado_politica_b": t.get("valor_liquido_calculado_politica_b"),
            "valor_liquido_diff_xml_vs_calc": t.get("valor_liquido_diff_xml_vs_calc"),
            "valor_liquido_divergente": t.get("valor_liquido_divergente"),
            # qualidade
            "confidence": it.get("confidence"),
            "needs_review": safe_get(it, ["flags", "needs_review"], False),
            "missing_critical": safe_get(it, ["flags", "missing_critical"], False),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    preferred = [
        "numero_nota", "data_emissao", "competencia", "cnpj_fornecedor",
        "cnae", "cnae_vs_descricao_status", "cnae_vs_descricao_severity", "cnae_vs_descricao_label", "cnae_vs_descricao_reason",
        "valor_total", "valor_liquido_nfse", "valor_liquido_calculado_politica_b",
        "valor_iss", "valor_iss_retido", "valor_pis", "valor_cofins", "valor_inss", "valor_ir", "valor_csll",
        "aliquota", "base_calculo", "iss_retido",
        "valor_liquido_diff_xml_vs_calc", "valor_liquido_divergente",
        "needs_review", "missing_critical", "confidence",
        "descricao_servico",
        "valor_deducoes", "outras_retencoes", "desconto_incondicionado", "desconto_condicionado",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    return df[cols]


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

st.title("Demonstração Extração de NFSe via XML")
st.caption(
    "Objetivo: apresentar que o pipeline já extrai campos e tributos de NFSe de forma determinística, com exportação operacional."
)

with st.sidebar:
    st.header("Configuração")
    api_base = st.text_input("Base URL da API", value="http://127.0.0.1:8000")
    page_size = st.number_input("Page size", min_value=10, max_value=200, value=50, step=10)
    st.divider()
    st.header("Arquivo")
    uploaded = st.file_uploader("Envie o XML de NFSe", type=["xml"])
    demo_mode = st.toggle("Modo demonstração (ocultar dados sensíveis)", value=False)

if not uploaded:
    st.info("Envie um XML para visualizar os resultados.")
    st.stop()

xml_bytes = uploaded.getvalue()
filename = uploaded.name or "upload.xml"

# Endpoints
url_summary = f"{api_base}/nfse-xml-extract/summary"
url_page = f"{api_base}/nfse-xml-extract"
url_csv = f"{api_base}/nfse-xml-extract/export-csv"

# -----------------------------------------------------------------------------
# Fetch summary
# -----------------------------------------------------------------------------

st.subheader("Resumo do lote")

try:
    resp_summary = post_xml(url_summary, xml_bytes, filename)
except Exception as exc:
    st.error(
        f"Falha ao conectar na API. Verifique se o FastAPI está rodando em: {api_base}\n\nDetalhe: {exc}"
    )
    st.stop()

if resp_summary.status_code != 200:
    st.error(f"Erro no summary ({resp_summary.status_code}): {resp_summary.text}")
    st.stop()

summary_payload = resp_summary.json()
summary = summary_payload.get("summary", {}) or {}
count = int(summary_payload.get("count", 0) or 0)

tax_totals = summary.get("tax_totals", {}) or {}

sum_retencoes_total = (
    (tax_totals.get("sum_valor_iss_retido") or 0)
    + (tax_totals.get("sum_valor_pis") or 0)
    + (tax_totals.get("sum_valor_cofins") or 0)
    + (tax_totals.get("sum_valor_inss") or 0)
    + (tax_totals.get("sum_valor_ir") or 0)
    + (tax_totals.get("sum_valor_csll") or 0)
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Quantidade de notas", f"{count}")
k2.metric("Bruto (Política A)", format_currency_br(summary.get("sum_valor_total_politica_a")))
k3.metric("Retenções (Total)", format_currency_br(sum_retencoes_total))
k4.metric("Líquido (Política B)", format_currency_br(summary.get("sum_valor_liquido_politica_b")))

k5, k6, k7, k8 = st.columns(4)
k5.metric("Soma PIS", format_currency_br(tax_totals.get("sum_valor_pis")))
k6.metric("Soma COFINS", format_currency_br(tax_totals.get("sum_valor_cofins")))
k7.metric("Soma INSS", format_currency_br(tax_totals.get("sum_valor_inss")))
k8.metric("Soma IR", format_currency_br(tax_totals.get("sum_valor_ir")))

vs = (summary.get("validation_summary", {}) or {}).get("cnae_vs_descricao", {}) or {}
c_ok = int(vs.get("ok", 0) or 0)
c_alert = int(vs.get("alert", 0) or 0)
c_unk = int(vs.get("unknown", 0) or 0)

v1, v2, v3 = st.columns(3)
v1.metric("CNAE x Descrição — OK", f"{c_ok}")
v2.metric("CNAE x Descrição — Alertas", f"{c_alert}")
v3.metric("CNAE x Descrição — Inconclusivo", f"{c_unk}")

st.markdown(
    f"""
### Metodologia e qualidade do lote

**Como os valores são obtidos**
- **Bruto:** extraído do XML (campo *ValorServicos*).
- **Retenções:** soma das retenções do XML (**ISS retido, PIS, COFINS, INSS, IR e CSLL**).
- **Líquido (Política B):** **Bruto – Retenções** (cálculo determinístico).

**Qualidade dos dados**
- **Campos críticos ausentes:** {int(summary.get("items_with_missing_critical", 0) or 0)}
- **Cobertura do cálculo do líquido:** {int(summary.get("count_liquido_politica_b", 0) or 0)}/{count} notas

**Conferência (quando o município informa líquido no XML)**
- **Notas com valor líquido informado no XML:** {int(summary.get("count_valor_liquido_informado_xml", 0) or 0)}/{count}
- **Divergências (XML vs cálculo):** {int(summary.get("count_valor_liquido_divergente", 0) or 0)}
""",
    unsafe_allow_html=False,
)

st.divider()

# -----------------------------------------------------------------------------
# Paginated table
# -----------------------------------------------------------------------------

st.subheader("Notas (paginado)")

total_pages = max(1, int((count + int(page_size) - 1) // int(page_size)))
page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)

resp_page = post_xml(f"{url_page}?page={int(page)}&page_size={int(page_size)}", xml_bytes, filename)
if resp_page.status_code != 200:
    st.error(f"Erro na paginação ({resp_page.status_code}): {resp_page.text}")
    st.stop()

page_payload = resp_page.json()
items = page_payload.get("items", []) or []
df = items_to_dataframe(items)

# Modo demonstração: mascara CNPJ
if demo_mode and "cnpj_fornecedor" in df.columns:
    df["cnpj_fornecedor"] = df["cnpj_fornecedor"].astype(str).str.replace(r"\d", "X", regex=True)

# Filtros
f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
with f1:
    filtro_comp = st.multiselect(
        "Filtrar por competência",
        sorted([c for c in df["competencia"].dropna().unique()]) if "competencia" in df.columns else [],
    )
with f2:
    filtro_review = st.selectbox("Revisão", ["Todos", "Somente needs_review=True", "Somente needs_review=False"])
with f3:
    min_val = st.number_input("Valor mínimo (R$)", min_value=0.0, value=0.0, step=100.0)
with f4:
    filtro_cnae_val = st.selectbox(
        "CNAE x Descrição",
        ["Todos", "Somente alertas", "Somente OK", "Somente inconclusivo"],
    )

df_view = df.copy()

if filtro_comp and "competencia" in df_view.columns:
    df_view = df_view[df_view["competencia"].isin(filtro_comp)]

if "needs_review" in df_view.columns:
    if filtro_review == "Somente needs_review=True":
        df_view = df_view[df_view["needs_review"] == True]
    elif filtro_review == "Somente needs_review=False":
        df_view = df_view[df_view["needs_review"] == False]

if "valor_total" in df_view.columns:
    df_view = df_view[df_view["valor_total"].fillna(0) >= float(min_val)]

if "cnae_vs_descricao_status" in df_view.columns:
    if filtro_cnae_val == "Somente alertas":
        df_view = df_view[df_view["cnae_vs_descricao_status"] == "alert"]
    elif filtro_cnae_val == "Somente OK":
        df_view = df_view[df_view["cnae_vs_descricao_status"] == "ok"]
    elif filtro_cnae_val == "Somente inconclusivo":
        df_view = df_view[df_view["cnae_vs_descricao_status"] == "unknown"]

st.dataframe(df_view, use_container_width=True, height=420)
st.caption(f"Página {page}/{total_pages} • Itens nesta página: {len(df_view)} • Page size: {page_size}")

st.divider()

# -----------------------------------------------------------------------------
# Aggregations (client-friendly)
# -----------------------------------------------------------------------------

st.subheader("Agregações (visão de conciliação)")
st.caption(
    "As agregações abaixo são calculadas a partir do CSV exportado pelo seu próprio endpoint (prova de pipeline completo)."
)

resp_csv = post_xml(url_csv, xml_bytes, filename)
if resp_csv.status_code == 200 and "text/csv" in resp_csv.headers.get("Content-Type", ""):
    df_all = pd.read_csv(io.StringIO(resp_csv.text), sep=";")
else:
    df_all = df.copy()

if demo_mode and "cnpj_fornecedor" in df_all.columns:
    df_all["cnpj_fornecedor"] = df_all["cnpj_fornecedor"].astype(str).str.replace(r"\d", "X", regex=True)

# numéricos
for col in [
    "valor_total", "valor_iss", "valor_iss_retido", "valor_pis", "valor_cofins", "valor_inss", "valor_ir", "valor_csll",
    "valor_liquido_nfse", "valor_liquido_calculado_politica_b",
]:
    if col in df_all.columns:
        df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

a1, a2 = st.columns(2)

with a1:
    st.markdown("**Total por fornecedor (Top 15 por valor_total)**")
    if "cnpj_fornecedor" in df_all.columns and "valor_total" in df_all.columns:
        g = (
            df_all.groupby("cnpj_fornecedor", dropna=False)["valor_total"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )
        st.dataframe(g, use_container_width=True, height=380)
    else:
        st.info("Não foi possível agregar por fornecedor (colunas ausentes).")

with a2:
    st.markdown("**Total por competência**")
    if "competencia" in df_all.columns and "valor_total" in df_all.columns:
        g2 = (
            df_all.groupby("competencia", dropna=False)["valor_total"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        st.dataframe(g2, use_container_width=True, height=380)
    else:
        st.info("Não foi possível agregar por competência (colunas ausentes).")

st.divider()

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------

st.subheader("Exportação")

col_dl1, _ = st.columns([1, 2])
with col_dl1:
    if resp_csv.status_code == 200:
        st.download_button(
            label="Baixar CSV (export do endpoint)",
            data=resp_csv.content,
            file_name=(filename.rsplit(".", 1)[0] + ".csv"),
            mime="text/csv",
        )
