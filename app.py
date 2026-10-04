import streamlit as st
from data.portfolio import init_db

st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

is_dark = st.session_state["theme"] == "dark"

BG       = "#0B0F1A" if is_dark else "#F7F8FA"
BG2      = "#141927" if is_dark else "#FFFFFF"
BG3      = "#1A2140" if is_dark else "#F0F2F5"
BORDER   = "#252D42" if is_dark else "#E2E6EE"
ACCENT   = "#F5A623" if is_dark else "#00C853"
ACCENT2  = "#D4900A" if is_dark else "#009624"
TEXT     = "#FFFFFF" if is_dark else "#0D1525"
SUBTEXT  = "#7B8699" if is_dark else "#5A6478"
TEXTMID  = "#C8D0DF" if is_dark else "#2D3A50"

st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background-color: {BG};
}}
[data-testid="stAppViewContainer"] > section:first-child {{
    background-color: {BG};
}}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}

.dash-header {{
    background: linear-gradient(135deg, {BG} 0%, {BG2} 60%, {BG3} 100%);
    border-bottom: 3px solid {ACCENT};
    padding: 1.4rem 1.8rem 1rem;
    margin-bottom: 1.2rem;
    border-radius: 0 0 12px 12px;
}}
.dash-header h1 {{ color: {TEXT}; font-size: 2.1rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; }}
.dash-header h1 span {{ color: {ACCENT}; }}
.dash-header p {{ color: {SUBTEXT}; font-size: 0.84rem; margin: 0.3rem 0 0; letter-spacing: 0.3px; }}

[data-testid="metric-container"] {{
    background: linear-gradient(135deg, {BG2}, {BG3});
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}
[data-testid="metric-container"] label {{
    color: {SUBTEXT} !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-size: 2rem !important;
    font-weight: 800;
    line-height: 1.1;
}}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
    font-size: 1rem !important;
    font-weight: 700;
}}

[data-baseweb="tab-list"] {{
    background: {BG2} !important;
    border-radius: 12px;
    padding: 5px;
    gap: 4px;
    border: 1px solid {BORDER};
}}
[data-baseweb="tab"] {{
    border-radius: 8px !important;
    color: {SUBTEXT} !important;
    font-weight: 600;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.2rem !important;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    background: {ACCENT}22 !important;
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT} !important;
}}

[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

[data-baseweb="slider"] [data-testid="stSliderThumbValue"] {{
    color: {ACCENT} !important;
    font-weight: 700;
}}
[data-baseweb="slider"] div[role="slider"] {{
    background: {ACCENT} !important;
    border-color: {ACCENT} !important;
}}

[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    background: {BG2} !important;
}}
[data-testid="stExpander"] summary {{ color: {TEXTMID} !important; font-weight: 600; }}

[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button {{
    background: {ACCENT}15;
    border: 1px solid {ACCENT}55;
    color: {ACCENT};
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.88rem;
    transition: all 0.15s;
    padding: 0.4rem 1rem;
}}
[data-testid="stButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover {{
    background: {ACCENT}30;
    border-color: {ACCENT};
    color: {TEXT};
}}

[data-testid="stAlert"] {{ border-radius: 10px; font-size: 0.9rem; }}

.section-title {{
    color: {ACCENT};
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    border-bottom: 1px solid {BORDER};
    padding-bottom: 0.35rem;
    margin: 1.2rem 0 0.6rem;
}}

[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {{
    background: {BG2} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 8px !important;
}}
[data-testid="stSelectbox"] div,
[data-baseweb="select"] {{
    background: {BG2} !important;
    border-color: {BORDER} !important;
}}

[data-baseweb="tag"] {{
    background: {ACCENT}22 !important;
    border: 1px solid {ACCENT}55 !important;
    color: {ACCENT} !important;
    border-radius: 6px !important;
}}

[data-testid="stRadio"] label {{ color: {TEXTMID} !important; }}
[data-testid="stRadio"] [aria-checked="true"] + div {{ color: {ACCENT} !important; }}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {ACCENT}55; }}

p, span, div, label {{ color: {TEXT}; }}
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────────────────────
hcol1, hcol2 = st.columns([8, 1])
with hcol1:
    st.markdown(f"""
<div class="dash-header">
  <h1>📈 Investment <span>Dashboard</span></h1>
  <p>My Portfolio &nbsp;·&nbsp; SIP tracker &nbsp;·&nbsp; Stocks &nbsp;·&nbsp; Mutual Funds</p>
</div>
""", unsafe_allow_html=True)
with hcol2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    toggle_label = "☀️ Light" if is_dark else "🌙 Dark"
    if st.button(toggle_label, key="theme_toggle"):
        st.session_state["theme"] = "light" if is_dark else "dark"
        st.rerun()

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
