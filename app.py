import base64
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------
# Config
# -----------------------------
st.set_page_config(
    page_title="RLI — Repositório de Leis de Inovação Brasil",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_PATH = "observatorio_leis_inovacao_app_ready.csv"
GEOJSON_PATH = "br_states.geojson"

ASSETS_DIR = Path("assets")
LOGO_SMALL_SVG = ASSETS_DIR / "rli_logo.svg"
LOGO_HERO_SVG = ASSETS_DIR / "rli_logo_hero.svg"

GREEN = "#00BF63"
TEXT = "#111827"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
BG = "#FFFFFF"
INPUT_BORDER = "#D1D5DB"

LINKEDIN_URL = "https://www.linkedin.com/in/pedroacase/"
EMAIL = "pedrocasefilho2208@gmail.com"


# -----------------------------
# Helpers
# -----------------------------
def svg_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    svg = path.read_text(encoding="utf-8")
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"


# -----------------------------
# Data loaders
# -----------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path).fillna("")

    for col in [
        "scope",
        "uf",
        "municipio",
        "lei_numero",
        "lei_nome",
        "data",
        "url_integra",
        "fonte",
        "tipo_lei",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["scope"] = df["scope"].astype(str).str.strip().str.lower()
    df["uf"] = df["uf"].astype(str).str.strip().str.upper()
    df["municipio"] = df["municipio"].astype(str).str.strip()
    df["data"] = df["data"].astype(str).str.strip()
    df["lei_numero"] = df["lei_numero"].astype(str).str.strip()
    df["lei_nome"] = df["lei_nome"].astype(str).str.strip()
    df["url_integra"] = df["url_integra"].astype(str).str.strip()
    df["fonte"] = df["fonte"].astype(str).str.strip()
    df["tipo_lei"] = (
        df["tipo_lei"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    df["tipo_lei_key"] = df["tipo_lei"].str.lower()

    return df


@st.cache_data
def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_feature_key(geo: dict) -> str:
    feats = geo.get("features", [])
    if not feats:
        raise ValueError("GeoJSON não tem 'features'.")

    f0 = feats[0]
    props = f0.get("properties", {}) if isinstance(f0.get("properties", {}), dict) else {}

    fid = f0.get("id", "")
    if isinstance(fid, str) and len(fid.strip()) == 2:
        return "id"

    candidates = [
        "sigla",
        "SIGLA",
        "uf",
        "UF",
        "abbrev",
        "ABBREV",
        "abbr",
        "ABBR",
        "SIGLA_UF",
        "sigla_uf",
        "CD_UF",
        "cd_uf",
    ]

    for k in candidates:
        if k in props:
            v = str(props.get(k, "")).strip()
            if len(v) == 2 and v.isalpha():
                return f"properties.{k}"

    for k, v in props.items():
        vs = str(v).strip()
        if len(vs) == 2 and vs.isalpha():
            return f"properties.{k}"

    raise ValueError("Não consegui detectar o campo de UF (sigla) no GeoJSON.")


UF_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}


# -----------------------------
# State
# -----------------------------
if "selected_uf" not in st.session_state:
    st.session_state.selected_uf = ""
if "scope" not in st.session_state:
    st.session_state.scope = "estadual"
if "tipo_sel" not in st.session_state:
    st.session_state.tipo_sel = []


# -----------------------------
# CSS
# -----------------------------
st.markdown(
    f"""
<style>
:root {{
  color-scheme: light !important;
}}


html, body, .stApp {{
  background: {BG} !important;
  color: {TEXT} !important;
}}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stVerticalBlock"],
section.main {{
  background: {BG} !important;
}}

header[data-testid="stHeader"] {{
  display: none;
}}

footer {{
  visibility: hidden;
}}

.block-container {{
  padding-top: 0 !important;
  padding-bottom: 2rem;
  max-width: 1200px;
}}

/* Helpers full-width */
.rli-fullwidth {{
  width: 100vw;
  margin-left: calc(50% - 50vw);
  background: {BG};
}}

.rli-full-line {{
  width: 100vw;
  border-bottom: 1px solid {BORDER};
  margin-left: calc(50% - 50vw);
}}

/* Header */
.rli-header-wrap {{
  position: sticky;
  top: 0;
  z-index: 999;
  background: {BG};
}}

.rli-header-inner {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 0;
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}}

.rli-brand {{
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}}

.rli-logo-header {{
  display: flex;
  align-items: center;
  flex-shrink: 0;
}}

.rli-logo-header img {{
  width: 42px;
  height: auto;
  display: block;
}}

.rli-brand-title {{
  font-weight: 600;
  font-size: 15px;
  line-height: 1.2;
  color: {TEXT};
  white-space: nowrap;
}}

.rli-nav {{
  display: flex;
  align-items: center;
  gap: 28px;
  flex-shrink: 0;
}}

.rli-nav a {{
  color: {MUTED};
  text-decoration: none;
  font-weight: 500;
  font-size: 14px;
}}

.rli-nav a:hover {{
  color: {TEXT};
}}

/* Hero */
.rli-hero {{
  padding: 86px 0 64px 0;
  text-align: center;
}}

.rli-hero-logo {{
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 22px;
}}

.rli-hero-logo img {{
  width: 230px;
  max-width: 100%;
  height: auto;
  display: block;
}}

.rli-hero-sub {{
  max-width: 760px;
  margin: 0 auto;
  color: {MUTED};
  font-size: 18px;
  line-height: 1.5;
  font-weight: 400;
}}

.rli-hero-actions {{
  margin-top: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}}

.rli-btn {{
  display: inline-block;
  padding: 11px 18px;
  border-radius: 4px;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid {BORDER};
}}

.rli-btn-primary {{
  background: {GREEN};
  color: #fff !important;
  border-color: {GREEN};
}}

.rli-btn-secondary {{
  background: #fff !important;
  color: {TEXT} !important;
}}

.rli-btn:hover {{
  filter: brightness(0.98);
}}

/* Seções */
.rli-section {{
  padding: 34px 0;
}}

.rli-kicker {{
  font-size: 12px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: {GREEN};
  font-weight: 700;
  margin-bottom: 6px;
}}

.rli-h2 {{
  font-size: 32px;
  font-weight: 650;
  margin: 0 0 10px 0;
}}

.rli-p {{
  color: {MUTED};
  font-size: 16px;
  line-height: 1.65;
  max-width: 920px;
  margin-bottom: 16px;
  font-weight: 400;
}}

/* Cards */
.rli-card {{
  border: 1px solid {BORDER};
  border-radius: 4px;
  padding: 16px;
  background: #fff !important;
  height: 100%;
}}

.rli-card-title {{
  color: {GREEN};
  font-weight: 700;
  margin-bottom: 6px;
}}

.rli-card-text {{
  color: {MUTED};
  line-height: 1.55;
  font-weight: 400;
}}

/* Steps */
.rli-step {{
  display: flex;
  gap: 12px;
  align-items: flex-start;
}}

.rli-step-num {{
  width: 34px;
  height: 34px;
  min-width: 34px;
  border-radius: 4px;
  background: {GREEN};
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}}

.rli-step-title {{
  font-weight: 650;
  margin-bottom: 2px;
}}

.rli-step-text {{
  color: {MUTED};
  font-size: 14px;
  line-height: 1.5;
  font-weight: 400;
}}

/* Mapa */
.rli-mapwrap {{
  border: 1px solid {BORDER};
  border-radius: 4px;
  overflow: hidden;
  background: #fff !important;
  margin-top: 10px;
}}

.rli-mapbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid {BORDER};
  color: {MUTED};
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  font-size: 12px;
  background: #fff !important;
}}

.rli-mapbar a {{
  color: {GREEN};
  text-decoration: none;
  font-weight: 700;
  text-transform: none;
  letter-spacing: normal;
}}

.rli-mapbar a:hover {{
  text-decoration: underline;
}}

/* Leis */
.rli-law {{
  border: 1px solid {BORDER};
  border-radius: 4px;
  padding: 14px;
  background: #fff !important;
  margin-bottom: 10px;
}}

.rli-law-title {{
  font-weight: 650;
  margin-bottom: 6px;
}}

.rli-law-meta {{
  color: {MUTED};
  font-size: 13px;
  line-height: 1.45;
  font-weight: 400;
}}

.rli-chip {{
  display: inline-block;
  border: 1px solid {BORDER};
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: {MUTED};
  margin-right: 6px;
  margin-top: 8px;
  font-weight: 400;
}}

.rli-cta {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 4px;
  border: 1px solid {GREEN};
  background: {GREEN};
  color: #fff !important;
  font-weight: 500;
  text-decoration: none;
}}

.rli-cta:hover {{
  filter: brightness(0.98);
}}

/* Footer */
.rli-footer {{
  border-top: 1px solid {BORDER};
  padding: 18px 0;
  display: flex;
  justify-content: space-between;
  color: {MUTED};
  font-size: 13px;
  margin-top: 18px;
}}

/* Inputs */
div[data-baseweb="select"] > div {{
  background: #fff !important;
  border: 1px solid {INPUT_BORDER} !important;
  color: {MUTED} !important;
}}

div[data-baseweb="select"] span {{
  color: {MUTED} !important;
  opacity: 1 !important;
}}

div[data-baseweb="select"] input {{
  color: {MUTED} !important;
}}

div[data-baseweb="select"] input::placeholder {{
  color: {MUTED} !important;
  opacity: 0.75 !important;
}}

div[data-baseweb="select"] svg {{
  fill: {MUTED} !important;
  color: {MUTED} !important;
}}

div[data-baseweb="select"] > div:focus-within {{
  border-color: {GREEN} !important;
  box-shadow: 0 0 0 1px {GREEN} !important;
}}

.stMultiSelect div[data-baseweb="tag"] {{
  background: #00BF63 !important;
  border: 1px solid {GREEN} !important;
}}

.stMultiSelect div[data-baseweb="tag"] span {{
  color: #ffffff !important;
}}

div[data-baseweb="select"] *:focus {{
  outline: none !important;
}}

input, textarea {{
  background: #fff !important;
  color: #6B7280 !important;
  border-color: #00BF63!important;
}}

input::placeholder {{
  color: {MUTED} !important;
  opacity: 0.75;
}}

label, .stTextInput label, .stSelectbox label, .stMultiSelect label {{
  color: {MUTED} !important;
  font-weight: 500 !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Load
# -----------------------------
df = load_data(DATA_PATH)
br_geo = load_geojson(GEOJSON_PATH)
feature_key = detect_feature_key(br_geo)

logo_small_uri = svg_to_data_uri(LOGO_SMALL_SVG)
hero_logo_uri = svg_to_data_uri(LOGO_HERO_SVG if LOGO_HERO_SVG.exists() else LOGO_SMALL_SVG)

# -----------------------------
# Header
# -----------------------------
st.markdown(
    f"""
<div class="rli-header-wrap rli-fullwidth">
  <div class="rli-header-inner">
    <div class="rli-brand">
      <div class="rli-logo-header">
        <img src="{logo_small_uri}" alt="RLI" />
      </div>
      <div class="rli-brand-title">Repositório de Leis de Inovação Brasil</div>
    </div>
    <div class="rli-nav">
      <a href="#sobre">Sobre</a>
      <a href="#mapa">Mapa</a>
      <a href="#contato">Contato</a>
    </div>
  </div>
  <div class="rli-full-line"></div>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Hero
# -----------------------------
st.markdown(
    f"""
<div class="rli-hero">
  <div class="rli-hero-logo">
    <img src="{hero_logo_uri}" alt="RLI" />
  </div>
  <div class="rli-hero-sub">
    Consulta, sistematização e acesso direto aos marcos normativos de inovação nos três níveis federativos do Brasil.
  </div>
  <div class="rli-hero-actions">
    <a class="rli-btn rli-btn-primary" href="#mapa">Acessar o Mapa</a>
    <a class="rli-btn rli-btn-secondary" href="#sobre">Saiba mais</a>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='rli-full-line'></div>", unsafe_allow_html=True)

# -----------------------------
# Seção: Sobre
# -----------------------------
st.markdown("<div id='sobre' class='rli-section'>", unsafe_allow_html=True)
st.markdown("<div class='rli-kicker'>Sobre o Repositório</div>", unsafe_allow_html=True)
st.markdown("<div class='rli-h2'>O que é o Repositório de Leis de Inovação?</div>", unsafe_allow_html=True)

st.markdown(
    """
<div class="rli-p">
O Repositório de Leis de Inovação é uma base pública estruturada voltada à organização, padronização e disponibilização
de marcos normativos relacionados à política de inovação no Brasil. Seu objetivo é oferecer um instrumento de consulta
e sistematização, com metadados comparáveis e acesso direto às fontes oficiais, apoiando estudos em Ciência, Tecnologia e
Inovação (CT&I), análise institucional e desenho de políticas públicas em diferentes níveis federativos.<br><br>
A base reúne normas de três escopos: federal, estadual e municipal, sendo o recorte municipal delimitado exclusivamente às capitais brasileiras.
Estão contempladas leis e atos estruturantes associados à CT&I, ao fomento a startups, à institucionalização de programas públicos de inovação e
a ambientes regulatórios experimentais (sandbox regulatório). O repositório preserva rastreabilidade por meio de identificação normativa, datação e link para a íntegra.
</div>
""",
    unsafe_allow_html=True,
)

cA, cB, cC = st.columns(3, gap="large")
with cA:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-card-title">Federal</div>
  <div class="rli-card-text">Marcos normativos de âmbito nacional em CT&I e inovação.</div>
</div>
""",
        unsafe_allow_html=True,
    )
with cB:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-card-title">Estadual</div>
  <div class="rli-card-text">Legislações estaduais sobre inovação por unidade da federação.</div>
</div>
""",
        unsafe_allow_html=True,
    )
with cC:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-card-title">Municipal</div>
  <div class="rli-card-text">Normas das capitais brasileiras relacionadas à inovação.</div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<div class='rli-full-line'></div>", unsafe_allow_html=True)

# -----------------------------
# Seção: Mapa
# -----------------------------
st.markdown("<div id='mapa' class='rli-section'>", unsafe_allow_html=True)
st.markdown("<div class='rli-kicker'>Mapa Interativo</div>", unsafe_allow_html=True)
st.markdown("<div class='rli-h2'>Navegue pelas Leis de Inovação</div>", unsafe_allow_html=True)

st.markdown(
    """
<div class="rli-p">
A navegação do repositório é orientada por um mapa interativo do Brasil, que permite localizar e acessar normas por Unidade da Federação e,
no escopo municipal, por capitais. O mapa agrega as entradas cadastradas e oferece uma visualização sintética da distribuição territorial dos marcos normativos.
</div>
""",
    unsafe_allow_html=True,
)

s1, s2, s3, s4 = st.columns([1, 1, 1, 1], gap="large")
with s1:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-step">
    <div class="rli-step-num">1</div>
    <div>
      <div class="rli-step-title">Selecione o escopo</div>
      <div class="rli-step-text">Federal, estadual ou municipal (capitais).</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
with s2:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-step">
    <div class="rli-step-num">2</div>
    <div>
      <div class="rli-step-title">Filtre por categoria</div>
      <div class="rli-step-text">CT&I, startups, programas de inovação ou sandbox regulatório.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
with s3:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-step">
    <div class="rli-step-num">3</div>
    <div>
      <div class="rli-step-title">Clique na UF</div>
      <div class="rli-step-text">Exiba a lista de normas com número, data e descrição.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
with s4:
    st.markdown(
        """
<div class="rli-card">
  <div class="rli-step">
    <div class="rli-step-num">4</div>
    <div>
      <div class="rli-step-title">Abra a íntegra</div>
      <div class="rli-step-text">Acesse a referência normativa oficial em nova aba.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

f1, f2, f3 = st.columns([0.22, 0.48, 0.30], gap="large")

with f1:
    scope = st.selectbox(
        "Escopo",
        ["federal", "estadual", "municipal"],
        index=["federal", "estadual", "municipal"].index(st.session_state.scope),
        help="Selecione o nível federativo das normas que deseja visualizar.",
    )
    st.session_state.scope = scope

tipos = sorted(
    [t for t in df["tipo_lei"].dropna().astype(str).str.strip().unique() if t != ""],
    key=lambda x: x.lower(),
)
TIPO_LABELS = {
    "governanca_cti": "Governança em CT&I",
    "fomento_startups": "Fomento a Startups",
    "marco_cti_inovacao": "Marco de CT&I e Inovação",
    "programa_inovacao": "Programa de Inovação",
    "sandbox_regulatorio": "Sandbox Regulatório",
}

with f2:
    tipo_sel = st.selectbox(
        "Categoria",
        options=[""] + tipos,
        index=([""] + tipos).index(st.session_state.tipo_sel[0]) if st.session_state.tipo_sel else 0,
        help="Filtre pelas categorias temáticas das normas cadastradas.",
        format_func=lambda x: "Todas as categorias" if x == "" else TIPO_LABELS.get(x, x.replace("_", " ").title()),
    )
    st.session_state.tipo_sel = [tipo_sel] if tipo_sel else []
    
with f3:
    search = st.text_input(
        "Busca (número ou palavras-chave)",
        value="",
        placeholder="Ex.: 13.243, startups, sandbox...",
        help="Pesquise pelo número da norma ou por palavras do título.",
    )

df_scope = df[df["scope"] == st.session_state.scope].copy()

if st.session_state.tipo_sel:
    tipo_sel_keys = [t.strip().lower() for t in st.session_state.tipo_sel if str(t).strip() != ""]
    df_scope = df_scope[df_scope["tipo_lei_key"].isin(tipo_sel_keys)]

if search.strip():
    q = search.strip().lower()
    df_scope = df_scope[
        df_scope["lei_numero"].str.lower().str.contains(q)
        | df_scope["lei_nome"].str.lower().str.contains(q)
    ]

show_list_mode = st.session_state.scope == "federal" or bool(st.session_state.tipo_sel)

df_map = pd.DataFrame({"uf": list(UF_NAMES.keys())})
df_map["nome"] = df_map["uf"].map(UF_NAMES)
counts = df_scope.groupby("uf").size().reset_index(name="qtd")
df_map = df_map.merge(counts, on="uf", how="left").fillna({"qtd": 0})

st.markdown(
    """
<div class="rli-mapwrap">
  <div class="rli-mapbar">
    <div>Mapa do Repositório</div>
    <a href="#mapa">Voltar ao topo do mapa &#8599;</a>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if show_list_mode:
    if st.session_state.scope == "federal":
        df_view = df_scope.sort_values(["data", "lei_numero"], ascending=[False, True]).copy()
        st.markdown(
            f"<div class='rli-law-meta'>Visualização em lista — Total: <b>{len(df_view)}</b></div>",
            unsafe_allow_html=True,
        )
    else:
        df_view = df_scope.sort_values(
            ["uf", "municipio", "data", "lei_numero"],
            ascending=[True, True, False, True],
        ).copy()
        st.markdown(
            f"<div class='rli-law-meta'>Visualização em lista por categoria — Total: <b>{len(df_view)}</b></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if df_view.empty:
        st.warning("Nenhuma norma encontrada para os filtros selecionados.")
    else:
        for _, r in df_view.iterrows():
            if st.session_state.scope == "federal":
                title = f'{r["lei_numero"]} — {r["data"]}'
            elif st.session_state.scope == "estadual":
                title = f'{r["uf"]} • {r["lei_numero"]} — {r["data"]}'
            else:
                title = f'{r["uf"]} • {r["municipio"]} • {r["lei_numero"]} — {r["data"]}'

            st.markdown(
                f"<div class='rli-law'><div class='rli-law-title'>{title}</div>",
                unsafe_allow_html=True,
            )

            if r["lei_nome"]:
                st.markdown(f"<div class='rli-law-meta'>{r['lei_nome']}</div>", unsafe_allow_html=True)

            chips = []
            if r.get("tipo_lei", ""):
                chips.append(f"<span class='rli-chip'>{r['tipo_lei']}</span>")
            if r.get("fonte", ""):
                chips.append(f"<span class='rli-chip'>{r['fonte']}</span>")
            if chips:
                st.markdown("".join(chips), unsafe_allow_html=True)

            if r.get("url_integra", ""):
                st.markdown(
                    f"<a class='rli-cta' href='{r['url_integra']}' target='_blank'>Abrir íntegra &#8599;</a>",
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)
else:
    map_col, list_col = st.columns([1.15, 0.85], gap="large")

    with map_col:
        fig = px.choropleth(
            df_map,
            geojson=br_geo,
            locations="uf",
            featureidkey=feature_key,
            color="qtd",
            hover_name="nome",
            hover_data={"uf": True, "qtd": True},
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="rgba(0,0,0,0)",
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
            coloraxis_colorbar=dict(
                title=dict(text="qtd", font=dict(color="black")),
                tickfont=dict(color="black"),
            ),
        )

        sel = st.plotly_chart(
            fig,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
        )

        selection = getattr(sel, "selection", None)

        if selection and selection.get("points"):
            uf_clicked = selection["points"][0].get("location", "")
            if uf_clicked:
                st.session_state.selected_uf = uf_clicked

        if st.session_state.selected_uf:
            st.success(f"UF selecionada: {st.session_state.selected_uf}")
        else:
            st.caption("Clique em um estado no mapa para listar as normas.")

    with list_col:
        if not st.session_state.selected_uf:
            st.markdown(
                "<div class='rli-law-meta'>Selecione uma UF no mapa para exibir as normas.</div>",
                unsafe_allow_html=True,
            )
            df_view = df_scope.iloc[0:0].copy()
        else:
            uf = st.session_state.selected_uf
            df_view = df_scope[df_scope["uf"] == uf].copy()
            df_view = df_view.sort_values(
                ["municipio", "data", "lei_numero"],
                ascending=[True, False, True],
            )
            st.markdown(
                f"<div class='rli-law-meta'>UF <b>{uf}</b> — Total: <b>{len(df_view)}</b></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        if df_view.empty and st.session_state.selected_uf:
            st.warning("Nenhuma norma encontrada para os filtros selecionados nesta UF.")
        else:
            for _, r in df_view.iterrows():
                if st.session_state.scope == "municipal":
                    title = f'{r["municipio"]} • {r["lei_numero"]} — {r["data"]}'
                else:
                    title = f'{r["lei_numero"]} — {r["data"]}'

                st.markdown(
                    f"<div class='rli-law'><div class='rli-law-title'>{title}</div>",
                    unsafe_allow_html=True,
                )

                if r["lei_nome"]:
                    st.markdown(f"<div class='rli-law-meta'>{r['lei_nome']}</div>", unsafe_allow_html=True)

                chips = []
                if r.get("tipo_lei", ""):
                    chips.append(f"<span class='rli-chip'>{r['tipo_lei']}</span>")
                if r.get("fonte", ""):
                    chips.append(f"<span class='rli-chip'>{r['fonte']}</span>")
                if chips:
                    st.markdown("".join(chips), unsafe_allow_html=True)

                if r.get("url_integra", ""):
                    st.markdown(
                        f"<a class='rli-cta' href='{r['url_integra']}' target='_blank'>Abrir íntegra &#8599;</a>",
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Seção: Contato
# -----------------------------
st.markdown("<div id='contato' class='rli-section'>", unsafe_allow_html=True)
st.markdown("<div class='rli-kicker'>Contato & Autoria</div>", unsafe_allow_html=True)
st.markdown("<div class='rli-h2'>Sobre o autor</div>", unsafe_allow_html=True)

st.markdown(
    """
<div class="rli-p">
Este repositório é mantido por <b>Pedro Augusto Casé</b>, entusiasta e pesquisador aplicado no estudo de políticas públicas de inovação,
com atuação continuada no tema ao longo dos últimos quatro anos. A iniciativa tem caráter público e colaborativo, orientada a ampliar
a acessibilidade e a qualidade do debate técnico sobre marcos normativos de inovação no país.<br><br>
Contribuições são bem-vindas, especialmente para: ampliação da cobertura, atualização de atos mais recentes, correção de referências e
sugestões de aprimoramento de taxonomia e critérios de classificação.
</div>

<div style="display:flex; gap:14px; align-items:center; flex-wrap:wrap;">
  <a class="rli-cta" href="{linkedin}" target="_blank">LinkedIn &#8599;</a>
  <div style="display:inline-flex; gap:8px; align-items:center; color:{muted}; font-size:14px;">
    <span style="font-size:16px;">&#9993;</span>
    <span>{email}</span>
  </div>
</div>
""".format(
        linkedin=LINKEDIN_URL,
        email=EMAIL,
        muted=MUTED,
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="rli-footer">
  <div>&copy; 2026 Repositório de Leis de Inovação</div>
  <div>Mantido por Pedro Augusto Casé</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)