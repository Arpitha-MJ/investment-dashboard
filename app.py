import streamlit as st
from data.portfolio import init_db

st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── global ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0B0F1A;
}
[data-testid="stAppViewContainer"] > section:first-child {
    background-color: #0B0F1A;
}

/* ── hide default streamlit chrome ── */
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ── header banner ── */
.dash-header {
    background: linear-gradient(135deg, #0B0F1A 0%, #141927 60%, #1A2140 100%);
    border-bottom: 3px solid #F5A623;
    padding: 1.4rem 1.8rem 1rem;
    margin-bottom: 1.2rem;
    border-radius: 0 0 12px 12px;
}
.dash-header h1 {
    color: #FFFFFF;
    font-size: 2.1rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
}
.dash-header h1 span { color: #F5A623; }
.dash-header p {
    color: #7B8699;
    font-size: 0.84rem;
    margin: 0.3rem 0 0;
    letter-spacing: 0.3px;
}

/* ── KPI metric cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #141927, #1A2140);
    border: 1px solid #252D42;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
[data-testid="metric-container"] label {
    color: #7B8699 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 2rem !important;
    font-weight: 800;
    line-height: 1.1;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 1rem !important;
    font-weight: 700;
}

/* ── tab bar ── */
[data-baseweb="tab-list"] {
    background: #141927 !important;
    border-radius: 12px;
    padding: 5px;
    gap: 4px;
    border: 1px solid #252D42;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #7B8699 !important;
    font-weight: 600;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.2rem !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #F5A62322 !important;
    color: #F5A623 !important;
    border-bottom: 2px solid #F5A623 !important;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #252D42;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

/* ── sliders ── */
[data-baseweb="slider"] [data-testid="stSliderThumbValue"] {
    color: #F5A623 !important;
    font-weight: 700;
}
[data-baseweb="slider"] div[role="slider"] {
    background: #F5A623 !important;
    border-color: #F5A623 !important;
}

/* ── expander ── */
[data-testid="stExpander"] {
    border: 1px solid #252D42 !important;
    border-radius: 10px !important;
    background: #141927 !important;
}
[data-testid="stExpander"] summary {
    color: #C8D0DF !important;
    font-weight: 600;
}

/* ── buttons ── */
[data-testid="stButton"] > button {
    background: #F5A62315;
    border: 1px solid #F5A62355;
    color: #F5A623;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.88rem;
    transition: all 0.15s;
    padding: 0.4rem 1rem;
}
[data-testid="stButton"] > button:hover {
    background: #F5A62330;
    border-color: #F5A623;
    color: #FFFFFF;
}

/* ── warning / info / success boxes ── */
[data-testid="stAlert"] {
    border-radius: 10px;
    font-size: 0.9rem;
}

/* ── section title ── */
.section-title {
    color: #F5A623;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    border-bottom: 1px solid #252D42;
    padding-bottom: 0.35rem;
    margin: 1.2rem 0 0.6rem;
}

/* ── inputs ── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background: #141927 !important;
    border: 1px solid #252D42 !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
}
[data-testid="stSelectbox"] div,
[data-baseweb="select"] {
    background: #141927 !important;
    border-color: #252D42 !important;
}

/* ── multiselect tags ── */
[data-baseweb="tag"] {
    background: #F5A62322 !important;
    border: 1px solid #F5A62355 !important;
    color: #F5A623 !important;
    border-radius: 6px !important;
}

/* ── radio buttons ── */
[data-testid="stRadio"] label { color: #C8D0DF !important; }
[data-testid="stRadio"] [aria-checked="true"] + div { color: #F5A623 !important; }

/* ── scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0B0F1A; }
::-webkit-scrollbar-thumb { background: #252D42; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #F5A62355; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="dash-header">
  <h1>📈 Investment <span>Dashboard</span></h1>
  <p>My Portfolio &nbsp;·&nbsp; SIP tracker &nbsp;·&nbsp; Stocks &nbsp;·&nbsp; Mutual Funds</p>
</div>
""", unsafe_allow_html=True)

init_db()

tab4, tab1, tab2, tab3 = st.tabs([
    "💼  My Portfolio",
    "📊  Top Stocks",
    "💰  Top SIP Funds",
    "🚀  IPO Watch",
])

with tab1:
    from ui.tab_stocks import render as render_stocks
    render_stocks()

with tab2:
    from ui.tab_mf import render as render_mf
    render_mf()

with tab3:
    from ui.tab_ipo import render as render_ipo
    render_ipo()

with tab4:
    from ui.tab_portfolio import render as render_portfolio
    render_portfolio()
