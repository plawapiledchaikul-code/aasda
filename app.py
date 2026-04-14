import streamlit as st

st.set_page_config(
    page_title="US Equity Signal Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
code, .stCode { font-family: 'IBM Plex Mono', monospace; }

[data-testid="stSidebar"] {
    background: #0a0a0f;
    border-right: 1px solid #1e1e2e;
}
[data-testid="stSidebar"] * { color: #c8c8d4 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiselect label { color: #6b6b8a !important; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }

.main { background: #07070d; }
.block-container { padding: 2rem 2.5rem; }

h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }

.metric-card {
    background: #0f0f1a;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.signal-bull { color: #00d4a1; font-weight: 600; }
.signal-bear { color: #f25050; font-weight: 600; }
.signal-neutral { color: #8888aa; font-weight: 500; }

.stDataFrame { border: 1px solid #1e1e2e; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/1_dashboard.py",   title="Dashboard",      icon="⬛"),
    st.Page("pages/2_screener.py",    title="Signal Screener",icon="🔍"),
    st.Page("pages/3_stock_detail.py",title="Stock Detail",   icon="📊"),
    st.Page("pages/4_backtest.py",    title="Backtest",       icon="🔁"),
    st.Page("pages/5_risk.py",        title="Risk Monitor",   icon="⚠️"),
])
pg.run()
