# coding: utf-8
import os
import io
import time
import unicodedata
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import certifi
from streamlit_autorefresh import st_autorefresh


os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# =========================
# Página / identidade
# =========================
st.set_page_config(page_title="Dashboard Fiat Feedback", layout="wide", page_icon="🚗")
# =========================
# Auto refresh (atualiza a página sozinho)
# =========================
st.sidebar.header("Controles")

auto_refresh = st.sidebar.toggle("Auto-refresh (60s)", value=True)
intervalo = st.sidebar.selectbox("Intervalo", [30, 60, 120, 300], index=1)  # segundos

if auto_refresh:
    st_autorefresh(interval=intervalo * 1000, key="auto_refresh")

FIAT_RED  = "#C8102E"
FIAT_RED2 = "#FE1529"
BORDER_COLOR = "#E5E5E5"
DASH_BG = "#F2F2F2"       # fundo do dashboard (cinza claro)
CARD_BG = "#FFFFFF"       # fundo dos cards
CARD_BORDER = "#E2E2E2"   # borda
CARD_SHADOW = "0 2px 10px rgba(0,0,0,0.08)"  # sombra leve
TITULO_KPI = "#2E2E2E"    # cinza escuro

# =========================
# Paths (relativos para web)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "FSquadra.png")

# =========================
# Google Sheets (público)
# =========================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Lpzq0tVhO3yNdj2a__pJZFgt6OVbBNB0xpPiPfec62I/edit?usp=sharing"
SHEET_ID  = "1Lpzq0tVhO3yNdj2a__pJZFgt6OVbBNB0xpPiPfec62I"
CSV_URL   = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# =========================
# CSS (KPIs)
# =========================
st.markdown(
    f"""
    <style>
      [data-testid="stMetricLabel"] {{
        color: {TITULO_KPI} !important;
      }}
      [data-testid="stMetricValue"] {{
        color: {FIAT_RED} !important;
      }}
      [data-testid="stMetricDelta"] {{
        color: {TITULO_KPI} !important;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# CSS (Layout geral)
# =========================
st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {DASH_BG};
        }}

        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}

        .topbar {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            box-shadow: {CARD_SHADOW};
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 16px;
        }}

        .card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            box-shadow: {CARD_SHADOW};
            border-radius: 14px;
            padding: 14px 14px 6px 14px;
            margin-bottom: 16px;
        }}

        .card [data-testid="stPlotlyChart"] {{
            padding: 0 !important;
            margin: 0 !important;
        }}

        .metric-card {{
            background: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            box-shadow: {CARD_SHADOW};
            border-radius: 14px;
            padding: 10px 14px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Helpers
# =========================
def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.upper().replace(" ", "_")
    return s

def estilizar_grafico(fig):
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=50, l=20, r=20, b=20),

        xaxis=dict(
            showline=True, linewidth=1, linecolor=BORDER_COLOR,
            showgrid=True, gridcolor=BORDER_COLOR, mirror=True,
            tickfont=dict(color="black"),
            tickcolor="black",
            title=dict(font=dict(color="black")),
        ),
        yaxis=dict(
            showline=True, linewidth=1, linecolor=BORDER_COLOR,
            showgrid=True, gridcolor=BORDER_COLOR, mirror=True,
            tickcolor="black",
            tickfont=dict(color="black"),
            title=dict(font=dict(color="black")),
        ),
        legend=dict(font=dict(color="black")),
        font=dict(color="black"),
    )
    fig.update_traces(textfont_color="black")
    return fig

def corrigir_header_se_precisar(df: pd.DataFrame) -> pd.DataFrame:
    # Caso 1: header veio como primeira linha
    if len(df.columns) > 0 and all(str(c).isdigit() for c in df.columns):
        if len(df) > 0:
            new_header = df.iloc[0].astype(str).tolist()
            df2 = df[1:].copy()
            df2.columns = new_header
            return df2

    # Caso 2: tudo em 1 coluna com TAB
    if df.shape[1] == 1:
        col0 = df.columns[0]
        if df[col0].astype(str).str.contains("\t").any():
            tmp = df[col0].astype(str).str.split("\t", expand=True)
            if len(tmp) > 0:
                tmp.columns = tmp.iloc[0].astype(str).tolist()
                tmp = tmp[1:].copy()
            return tmp

    return df

# =========================
# Carregamento (Google Sheets público via CSV)
# =========================
@st.cache_data(ttl=60, show_spinner=False)
@st.cache_data(ttl=60, show_spinner=False)
def carregar_csv_publico() -> pd.DataFrame:
    last_err = None
    for _ in range(2):
        try:
            r = requests.get(
                CSV_URL,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
                verify=certifi.where()  # ✅ CORREÇÃO SSL
            )
            r.raise_for_status()
            df_ = pd.read_csv(io.StringIO(r.text), dtype=str, keep_default_na=False)
            return corrigir_header_se_precisar(df_)
        except Exception as e:
            last_err = e
            time.sleep(0.5)
    raise RuntimeError(f"Falha ao carregar CSV do Google Sheets: {last_err}")


# =========================
# Preparação pesada em cache (não repetir em cada filtro)
# =========================
@st.cache_data(ttl=300, show_spinner=False)
def preparar_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = [norm(c) for c in df.columns]

    # colunas confirmadas
    necessarias = {
        "ID","NUMERO","DATA","NOME_CLIENTE","NOTA","OPCAO","COMENTARIO","ENCERRAMENTO",
        "CATEGORIA_TEMATICA","SENTIMENTO","DEPARTAMENTO_INTERESSE"
    }
    faltando = necessarias - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"Colunas faltando: {', '.join(sorted(faltando))}\n\n"
            f"Colunas detectadas: {list(df.columns)}"
        )

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df["NOTA"] = pd.to_numeric(df["NOTA"], errors="coerce")
    df = df.dropna(subset=["NOTA", "DATA"]).copy()

    return df

# =========================
# Sidebar: Atualização
# =========================
st.sidebar.header("Controles")
if st.sidebar.button("🔄 Atualizar dados agora"):
    st.cache_data.clear()
    st.rerun()

# =========================
# Cabeçalho
# =========================
st.markdown("<div class='topbar'>", unsafe_allow_html=True)
col_logo, col_titulo = st.columns([1, 6])

with col_logo:
    # Se a logo não existir no repo, não quebra o app
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)
    else:
        st.warning("Logo não encontrada em assets/FSquadra.png")

with col_titulo:
    st.markdown(
        f"<h2 style='margin:0; color:{FIAT_RED2};'>Monitoramento de Experiência do Cliente</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='background-color:{FIAT_RED}; height:4px; width:100%; margin-top:6px;'></div>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Carrega dados
# =========================
try:
    df_raw = carregar_csv_publico()
    st.caption("Fonte de dados: **Google Sheets (CSV público)**")
except Exception as e:
    st.error(str(e))
    st.stop()

try:
    df = preparar_df(df_raw)
except Exception as e:
    st.error(str(e))
    st.stop()

if df.empty:
    st.warning("Base vazia após limpeza (DATA/NOTA inválidos).")
    st.stop()

# =========================
# Sidebar filtros
# =========================
st.sidebar.header("Filtros")

min_d, max_d = df["DATA"].min().date(), df["DATA"].max().date()
periodo = st.sidebar.date_input("Período", value=(min_d, max_d), min_value=min_d, max_value=max_d)

sentimentos = ["Todos"] + sorted([x for x in df["SENTIMENTO"].dropna().unique().tolist() if str(x).strip() != ""])
sentimento_sel = st.sidebar.selectbox("Sentimento", sentimentos, index=0)

depts = ["Todos"] + sorted([x for x in df["DEPARTAMENTO_INTERESSE"].dropna().unique().tolist() if str(x).strip() != ""])
dept_sel = st.sidebar.selectbox("Departamento", depts, index=0)

df_f = df

if isinstance(periodo, tuple) and len(periodo) == 2:
    d1 = pd.to_datetime(periodo[0])
    d2 = pd.to_datetime(periodo[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df_f = df_f[(df_f["DATA"] >= d1) & (df_f["DATA"] <= d2)]

if sentimento_sel != "Todos":
    df_f = df_f[df_f["SENTIMENTO"] == sentimento_sel]

if dept_sel != "Todos":
    df_f = df_f[df_f["DEPARTAMENTO_INTERESSE"] == dept_sel]

if df_f.empty:
    st.warning("Nenhum registro com os filtros selecionados.")
    st.stop()

# =========================
# KPIs
# =========================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Média Geral", f"{df_f['NOTA'].mean():.1f} ⭐")
    st.markdown("</div>", unsafe_allow_html=True)

with k2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Total Feedbacks", len(df_f))
    st.markdown("</div>", unsafe_allow_html=True)

with k3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    perc_pos = (df_f["SENTIMENTO"].eq("Positivo").sum() / len(df_f) * 100) if len(df_f) else 0
    st.metric("% Positivos", f"{perc_pos:.1f}%")
    st.markdown("</div>", unsafe_allow_html=True)

with k4:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    top_critica = (
        df_f[df_f["SENTIMENTO"].eq("Negativo")]["CATEGORIA_TEMATICA"].mode().iloc[0]
        if df_f["SENTIMENTO"].eq("Negativo").any()
        else "-"
    )
    st.metric("Principal Ponto de Atenção", top_critica)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Gráficos
# =========================
PLOTLY_CONFIG = {"displayModeBar": False}

c1, c2 = st.columns(2)

with c1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    df_notas_count = (
        df_f["NOTA"]
        .value_counts()
        .rename_axis("NOTA")
        .reset_index(name="count")
        .sort_values("NOTA")
    )
    fig_notas = px.bar(
        df_notas_count, x="NOTA", y="count",
        title="<b>Distribuição de Notas (1-10)</b>",
        color_discrete_sequence=[FIAT_RED],
        text_auto=True,
        height=360
    )
    fig_notas.update_xaxes(tickmode="linear", dtick=1)
    estilizar_grafico(fig_notas)
    st.plotly_chart(fig_notas, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    fig_sent = px.pie(
        df_f, names="SENTIMENTO", hole=0.6,
        title="<b>Clima Geral (Sentimento)</b>",
        color="SENTIMENTO",
        color_discrete_map={"Positivo": "#00C853", "Negativo": FIAT_RED, "Neutro": "#B0BEC5"},
        height=360
    )
    fig_sent.update_traces(textinfo="percent+label", textfont_size=14)
    fig_sent.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
        legend=dict(font=dict(color="black"))
    )
    st.plotly_chart(fig_sent, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("</div>", unsafe_allow_html=True)

c3, c4 = st.columns(2)

with c3:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    df_temp = df_f.set_index("DATA").resample("W")["NOTA"].mean().reset_index()
    fig_evol = px.line(
        df_temp, x="DATA", y="NOTA",
        title="<b>Evolução da Nota Média (Semanal)</b>",
        markers=True,
        color_discrete_sequence=[FIAT_RED],
        height=360
    )
    fig_evol.update_yaxes(range=[0, 10.5])
    estilizar_grafico(fig_evol)
    st.plotly_chart(fig_evol, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    df_dept = (
        df_f["DEPARTAMENTO_INTERESSE"]
        .value_counts()
        .rename_axis("DEPARTAMENTO_INTERESSE")
        .reset_index(name="count")
        .head(10)
    )
    fig_dept = px.bar(
        df_dept, y="DEPARTAMENTO_INTERESSE", x="count", orientation="h",
        title="<b>Volume por Departamento (Top 10)</b>",
        color_discrete_sequence=[FIAT_RED],
        text_auto=True,
        height=360
    )
    fig_dept.update_layout(yaxis={"categoryorder": "total ascending"})
    estilizar_grafico(fig_dept)
    st.plotly_chart(fig_dept, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("</div>", unsafe_allow_html=True)
