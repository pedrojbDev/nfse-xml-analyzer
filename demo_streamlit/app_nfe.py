# demo_streamlit/app_nfe.py
import io
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="NF-e Extractor Demo (XML)",
    page_icon="📦",
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
    for row in items:
        it = row.get("item", {}) or {}
        norm = row.get("normalized", {}) or {}

        rows.append(
            {
                "nItem": it.get("nItem"),
                "cProd": it.get("cProd"),
                "xProd": it.get("xProd"),
                "NCM": it.get("NCM"),
                "CFOP": it.get("CFOP"),
                "uCom": it.get("uCom"),
                "qCom": it.get("qCom"),
                "vUnCom": it.get("vUnCom"),
                "vProd": it.get("vProd"),

                "icms_tipo": it.get("icms_tipo"),
                "cst": it.get("cst"),
                "csosn": it.get("csosn"),
                "vBC": it.get("vBC"),
                "vICMS": it.get("vICMS"),
                "pis_tipo": it.get("pis_tipo"),
                "pis_cst": it.get("pis_cst"),
                "vPIS": it.get("vPIS"),
                "cofins_tipo": it.get("cofins_tipo"),
                "cofins_cst": it.get("cofins_cst"),
                "vCOFINS": it.get("vCOFINS"),

                "product_class": norm.get("product_class"),
                "suggested_group": norm.get("suggested_group"),
                "decision": row.get("decision"),
                "reasons": "|".join(row.get("reasons", []) or []),

                "confidence": row.get("confidence"),
                "missing_fields": ",".join(row.get("missing_fields", []) or []),
                "incomplete": safe_get(row, ["flags", "incomplete"], False),
            }
        )

    df = pd.DataFrame(rows)

    preferred = [
        "nItem", "cProd", "xProd", "NCM", "CFOP",
        "qCom", "vUnCom", "vProd",
        "product_class", "suggested_group", "decision", "reasons",
        "icms_tipo", "cst", "csosn", "vICMS", "vPIS", "vCOFINS",
        "confidence", "missing_fields", "incomplete",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    return df[cols]


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

st.title("Demonstração Extração de NF-e via XML")
st.caption(
    "Objetivo: extrair itens da NF-e (produto), normalizar e classificar para reduzir revisão humana antes de importar no RM."
)

with st.sidebar:
    st.header("Configuração")
    api_base = st.text_input("Base URL da API", value="http://127.0.0.1:8000")
    page_size = st.number_input("Page size", min_value=10, max_value=200, value=50, step=10)
    st.divider()
    st.header("Arquivo")
    uploaded = st.file_uploader("Envie o XML de NF-e", type=["xml"])
    demo_mode = st.toggle("Modo demonstração (ocultar dados sensíveis)", value=False)

if not uploaded:
    st.info("Envie um XML para visualizar os resultados.")
    st.stop()

xml_bytes = uploaded.getvalue()
filename = uploaded.name or "upload.xml"

url_summary = f"{api_base}/nfe-xml-extract/summary"
url_page = f"{api_base}/nfe-xml-extract"
url_csv = f"{api_base}/nfe-xml-extract/export-csv"

# -----------------------------------------------------------------------------
# Fetch summary
# -----------------------------------------------------------------------------

st.subheader("Resumo da NF-e")

try:
    resp_summary = post_xml(url_summary, xml_bytes, filename)
except Exception as exc:
    st.error(f"Falha ao conectar na API. Verifique se o FastAPI está rodando em: {api_base}\n\nDetalhe: {exc}")
    st.stop()

if resp_summary.status_code != 200:
    st.error(f"Erro no summary ({resp_summary.status_code}): {resp_summary.text}")
    st.stop()

payload = resp_summary.json()
header = payload.get("header", {}) or {}
totals = payload.get("totals", {}) or {}
summary = payload.get("summary", {}) or {}
count_items = int(payload.get("count", 0) or 0)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Itens (det)", f"{count_items}")
k2.metric("vNF (Total NF-e)", format_currency_br(totals.get("vNF")))
k3.metric("vProd (Total produtos)", format_currency_br(totals.get("vProd")))
k4.metric("Diferença (itens vs vProd)", format_currency_br(summary.get("diff_items_vs_total_vProd")))

st.markdown(
    f"""
**Chave:** {header.get("chave_nfe") or "-"}  
**Número/Série:** {header.get("numero") or "-"} / {header.get("serie") or "-"}  
**Emissão:** {header.get("data_emissao") or "-"}  
**Natureza da operação:** {header.get("natureza_operacao") or "-"}  
""".strip()
)

# decision summary (se já estiver integrado no endpoint /page, este bloco pode vir do CSV)
st.divider()

# -----------------------------------------------------------------------------
# Paginated table
# -----------------------------------------------------------------------------

st.subheader("Itens (paginado)")

total_pages = max(1, int((count_items + int(page_size) - 1) // int(page_size)))
page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)

resp_page = post_xml(f"{url_page}?page={int(page)}&page_size={int(page_size)}", xml_bytes, filename)
if resp_page.status_code != 200:
    st.error(f"Erro na paginação ({resp_page.status_code}): {resp_page.text}")
    st.stop()

page_payload = resp_page.json()
items = page_payload.get("items", []) or []
df = items_to_dataframe(items)

# Filtros
f1, f2, f3 = st.columns([2, 2, 2])
with f1:
    filtro_class = st.selectbox("Classe", ["Todos", "MEDICAMENTO", "NAO_MEDICAMENTO"])
with f2:
    filtro_dec = st.selectbox("Decisão", ["Todos", "REVIEW", "BLOCK", "AUTO"])
with f3:
    min_vprod = st.number_input("vProd mínimo (R$)", min_value=0.0, value=0.0, step=100.0)

df_view = df.copy()

if filtro_class != "Todos" and "product_class" in df_view.columns:
    df_view = df_view[df_view["product_class"] == filtro_class]

if filtro_dec != "Todos" and "decision" in df_view.columns:
    df_view = df_view[df_view["decision"] == filtro_dec]

if "vProd" in df_view.columns:
    df_view["vProd"] = pd.to_numeric(df_view["vProd"], errors="coerce")
    df_view = df_view[df_view["vProd"].fillna(0) >= float(min_vprod)]

st.dataframe(df_view, use_container_width=True, height=420)
st.caption(f"Página {page}/{total_pages} • Itens nesta página: {len(df_view)} • Page size: {page_size}")

st.divider()

# -----------------------------------------------------------------------------
# Aggregations (client-friendly)
# -----------------------------------------------------------------------------

st.subheader("Agregações (visão operacional)")
st.caption("Agregações calculadas a partir do CSV exportado pelo endpoint.")

resp_csv = post_xml(url_csv, xml_bytes, filename)
if resp_csv.status_code == 200 and "text/csv" in resp_csv.headers.get("Content-Type", ""):
    df_all = pd.read_csv(io.StringIO(resp_csv.text), sep=";")
else:
    df_all = df.copy()

# normalizações numéricas
for col in ["qCom", "vUnCom", "vProd"]:
    if col in df_all.columns:
        df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

a1, a2 = st.columns(2)

with a1:
    st.markdown("**Itens por decision**")
    if "decision" in df_all.columns:
        g = df_all.groupby("decision", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
        st.dataframe(g, use_container_width=True, height=260)
    else:
        st.info("Coluna decision não encontrada no CSV.")

with a2:
    st.markdown("**vProd por product_class**")
    if "product_class" in df_all.columns and "vProd" in df_all.columns:
        g2 = (
            df_all.groupby("product_class", dropna=False)["vProd"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        # formata
        g2["vProd"] = g2["vProd"].apply(format_currency_br)
        st.dataframe(g2, use_container_width=True, height=260)
    else:
        st.info("Não foi possível agregar por product_class.")

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
