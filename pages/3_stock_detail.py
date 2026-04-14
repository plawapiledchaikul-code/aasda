import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_sp500_tickers, get_price_data, get_fundamentals
from utils.signals import momentum_score, fundamental_score, combined_score, compute_rsi, compute_macd

st.title("📊 Stock Detail")

tickers_df = get_sp500_tickers()
ticker_list = tickers_df["ticker"].tolist()

col_t, col_p = st.columns([2, 1])
with col_t:
    sel_ticker = st.selectbox("Select ticker", ticker_list,
                               index=ticker_list.index("AAPL") if "AAPL" in ticker_list else 0)
with col_p:
    period_map = {"3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y"}
    sel_period = st.selectbox("Period", list(period_map.keys()), index=2)
    period = period_map[sel_period]

with st.spinner(f"Loading {sel_ticker}…"):
    price_df = get_price_data(sel_ticker, period)
    info     = get_fundamentals(sel_ticker)
    mom      = momentum_score(price_df)
    fund     = fundamental_score(info)
    combo    = combined_score(mom, fund)

if price_df.empty:
    st.error("No price data available.")
    st.stop()

close  = price_df["close"].squeeze()
volume = price_df["volume"].squeeze() if "volume" in price_df.columns else None

# ── Header ────────────────────────────────────────────────────────────────────
name = info.get("short_name", sel_ticker)
sector = info.get("sector", "—")
industry = info.get("industry", "—")
price_now = close.iloc[-1]
ret_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else 0

signal_color = {"BUY": "#00d4a1", "WATCH": "#f5c842", "NEUTRAL": "#8888aa", "AVOID": "#f25050"}
sig = combo.get("signal", "N/A")

st.markdown(f"""
<div style="display:flex;align-items:baseline;gap:1.2rem;margin-bottom:0.5rem">
  <span style="font-family:'IBM Plex Mono',monospace;font-size:2rem;font-weight:600">{sel_ticker}</span>
  <span style="color:#8888aa;font-size:1rem">{name}</span>
  <span style="margin-left:auto;background:{signal_color.get(sig,'#333')};color:#000;
               font-weight:700;padding:4px 14px;border-radius:4px;font-size:0.85rem">{sig}</span>
</div>
<div style="color:#8888aa;font-size:0.85rem;margin-bottom:1.2rem">{sector} · {industry}</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Price", f"${price_now:.2f}", f"{ret_1d:+.2f}%")
m2.metric("Combined score", f"{combo.get('combined_score','—')}/100")
m3.metric("Momentum score", f"{mom.get('momentum_score','—')}/100")
m4.metric("Fundamental score", f"{fund.get('fundamental_score','—')}/100")
m5.metric("RSI (14)", f"{mom.get('rsi','—')}")

st.divider()

# ── Price + Volume + Indicators chart ────────────────────────────────────────
rsi_series  = compute_rsi(close)
macd_line, signal_line, histogram = compute_macd(close)

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    row_heights=[0.50, 0.18, 0.16, 0.16],
    vertical_spacing=0.03,
    subplot_titles=("Price & MA", "Volume", "RSI (14)", "MACD"),
)

# Price
ma20 = close.rolling(20).mean()
ma50 = close.rolling(50).mean()
ret_total = close.iloc[-1] / close.iloc[0] - 1
line_color = "#00d4a1" if ret_total >= 0 else "#f25050"

fig.add_trace(go.Scatter(x=close.index, y=close, name="Price",
    line=dict(color=line_color, width=1.5),
    fill="tozeroy", fillcolor=line_color.replace("#","rgba(").replace(")", ",0.06)") if False else "rgba(0,212,161,0.05)"),
    row=1, col=1)
fig.add_trace(go.Scatter(x=ma20.index, y=ma20, name="MA20",
    line=dict(color="#f5c842", width=1, dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=ma50.index, y=ma50, name="MA50",
    line=dict(color="#8888cc", width=1, dash="dot")), row=1, col=1)

# Volume
if volume is not None:
    vol_colors = ["#00d4a1" if close.iloc[i] >= close.iloc[i-1] else "#f25050"
                  for i in range(len(close))]
    fig.add_trace(go.Bar(x=volume.index, y=volume, name="Volume",
        marker_color=vol_colors, opacity=0.6), row=2, col=1)

# RSI
fig.add_trace(go.Scatter(x=rsi_series.index, y=rsi_series, name="RSI",
    line=dict(color="#c084fc", width=1.2)), row=3, col=1)
fig.add_hline(y=70, line=dict(color="#f25050", width=0.5, dash="dash"), row=3, col=1)
fig.add_hline(y=30, line=dict(color="#00d4a1", width=0.5, dash="dash"), row=3, col=1)
fig.add_hline(y=50, line=dict(color="#333355", width=0.5), row=3, col=1)

# MACD
hist_colors = ["#00d4a1" if v >= 0 else "#f25050" for v in histogram]
fig.add_trace(go.Bar(x=histogram.index, y=histogram, name="MACD Hist",
    marker_color=hist_colors, opacity=0.7), row=4, col=1)
fig.add_trace(go.Scatter(x=macd_line.index, y=macd_line, name="MACD",
    line=dict(color="#60a5fa", width=1.2)), row=4, col=1)
fig.add_trace(go.Scatter(x=signal_line.index, y=signal_line, name="Signal",
    line=dict(color="#f97316", width=1.2)), row=4, col=1)

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c8c8d4", height=680,
    margin=dict(l=0, r=0, t=30, b=0),
    legend=dict(orientation="h", y=1.02),
    xaxis4=dict(gridcolor="#1e1e2e"),
    xaxis3=dict(gridcolor="#1e1e2e"),
    xaxis2=dict(gridcolor="#1e1e2e"),
    xaxis=dict(gridcolor="#1e1e2e"),
)
for r in range(1, 5):
    fig.update_yaxes(gridcolor="#1e1e2e", row=r, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── Fundamentals ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Fundamental metrics")

def fmt(val, fmt_str=".2f", suffix="", prefix=""):
    if val is None: return "—"
    try: return f"{prefix}{val:{fmt_str}}{suffix}"
    except: return str(val)

fund_data = {
    "P/E (TTM)":         fmt(info.get("pe_ratio"), ".1f"),
    "Forward P/E":       fmt(info.get("forward_pe"), ".1f"),
    "P/B":               fmt(info.get("pb_ratio"), ".2f"),
    "EV/EBITDA":         fmt(info.get("ev_ebitda"), ".1f"),
    "Revenue growth":    fmt(info.get("revenue_growth"), ".1%"),
    "Earnings growth":   fmt(info.get("earnings_growth"), ".1%"),
    "Profit margin":     fmt(info.get("profit_margin"), ".1%"),
    "ROE":               fmt(info.get("roe"), ".1%"),
    "Debt/Equity":       fmt(info.get("debt_equity"), ".1f"),
    "Current ratio":     fmt(info.get("current_ratio"), ".2f"),
    "Market cap":        f"${info.get('market_cap',0)/1e9:.1f}B" if info.get("market_cap") else "—",
    "EPS (TTM)":         fmt(info.get("eps_ttm"), ".2f", prefix="$"),
    "Dividend yield":    fmt(info.get("dividend_yield"), ".2%"),
    "52w high":          fmt(info.get("52w_high"), ".2f", prefix="$"),
    "52w low":           fmt(info.get("52w_low"), ".2f", prefix="$"),
    "Analyst target":    fmt(info.get("analyst_target"), ".2f", prefix="$"),
    "Recommendation":    str(info.get("recommendation", "—")).upper(),
}

cols = st.columns(4)
for i, (k, v) in enumerate(fund_data.items()):
    with cols[i % 4]:
        st.metric(k, v)

# ── Momentum detail ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Momentum breakdown")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("RSI (14)", mom.get("rsi", "—"))
mc2.metric("ROC 3M", f"{mom.get('roc_3m','—')}%")
mc3.metric("MACD signal", "Bullish ✓" if mom.get("macd_bull") else "Bearish ✗")
mc4.metric("52w rank", f"{mom.get('w52_pct','—')}%")
mc5.metric("Volume surge", f"{mom.get('vol_surge','—')}x")
