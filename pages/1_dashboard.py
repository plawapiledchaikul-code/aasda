import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_sp500_tickers, get_price_data, get_batch_quotes

st.title("📈 US Equity Dashboard")
st.caption("S&P 500 · Live via Yahoo Finance · Refreshed hourly")

tickers_df = get_sp500_tickers()
sectors = ["All"] + sorted(tickers_df["sector"].dropna().unique().tolist())

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
with col_f1:
    sel_sector = st.selectbox("Sector filter", sectors)
with col_f2:
    period_map = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}
    sel_period_label = st.selectbox("Period", list(period_map.keys()), index=3)
    sel_period = period_map[sel_period_label]
with col_f3:
    top_n = st.number_input("Top N movers", min_value=5, max_value=50, value=20, step=5)

if sel_sector != "All":
    filtered = tickers_df[tickers_df["sector"] == sel_sector]
else:
    filtered = tickers_df

ticker_list = filtered["ticker"].tolist()

st.divider()

with st.spinner(f"Loading price data for {len(ticker_list)} tickers…"):
    quotes_df = get_batch_quotes(ticker_list)

if quotes_df.empty:
    st.error("Could not load price data. Check your internet connection.")
    st.stop()

quotes_df = quotes_df.merge(tickers_df[["ticker", "name", "sector"]], on="ticker", how="left")

# ── Market summary ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

up_count = (quotes_df["ret_1d"] > 0).sum()
dn_count = (quotes_df["ret_1d"] < 0).sum()
med_ret1d = quotes_df["ret_1d"].median() * 100
med_ret1m = quotes_df["ret_1m"].median() * 100
avg_vol_surge = quotes_df["vol_surge"].median()

with c1:
    st.metric("Tickers loaded", len(quotes_df))
with c2:
    st.metric("Advancing", int(up_count),
              delta=f"{up_count - dn_count:+d} vs declining")
with c3:
    st.metric("Median 1D return", f"{med_ret1d:+.2f}%")
with c4:
    st.metric("Median 1M return", f"{med_ret1m:+.2f}%")
with c5:
    st.metric("Median vol surge", f"{avg_vol_surge:.2f}x")

st.divider()

# ── Top movers ───────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🟢 Top Gainers (1M)", "🔴 Top Losers (1M)", "⚡ Volume Surge"])

with tab1:
    gainers = quotes_df.nlargest(top_n, "ret_1m")[
        ["ticker", "name", "sector", "price", "ret_1d", "ret_1m", "ret_3m", "vol_surge", "pct_from_52h"]
    ].copy()
    for col in ["ret_1d", "ret_1m", "ret_3m", "pct_from_52h"]:
        gainers[col] = gainers[col].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    gainers["vol_surge"] = gainers["vol_surge"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "—")
    st.dataframe(gainers, use_container_width=True, hide_index=True)

with tab2:
    losers = quotes_df.nsmallest(top_n, "ret_1m")[
        ["ticker", "name", "sector", "price", "ret_1d", "ret_1m", "ret_3m", "vol_surge", "pct_from_52h"]
    ].copy()
    for col in ["ret_1d", "ret_1m", "ret_3m", "pct_from_52h"]:
        losers[col] = losers[col].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    losers["vol_surge"] = losers["vol_surge"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "—")
    st.dataframe(losers, use_container_width=True, hide_index=True)

with tab3:
    surge = quotes_df.nlargest(top_n, "vol_surge")[
        ["ticker", "name", "sector", "price", "ret_1d", "vol_surge", "pct_from_52h"]
    ].copy()
    surge["ret_1d"] = surge["ret_1d"].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    surge["vol_surge"] = surge["vol_surge"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "—")
    surge["pct_from_52h"] = surge["pct_from_52h"].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    st.dataframe(surge, use_container_width=True, hide_index=True)

st.divider()

# ── Sector heatmap ────────────────────────────────────────────────────────────
st.subheader("Sector performance (1M median return)")
sec_perf = (quotes_df.groupby("sector")["ret_1m"]
            .median()
            .dropna()
            .reset_index()
            .sort_values("ret_1m", ascending=False))
sec_perf["ret_pct"] = sec_perf["ret_1m"] * 100

fig_sec = px.bar(
    sec_perf, x="sector", y="ret_pct",
    color="ret_pct",
    color_continuous_scale=["#f25050", "#1e1e2e", "#00d4a1"],
    color_continuous_midpoint=0,
    labels={"ret_pct": "1M Return (%)", "sector": ""},
    height=320,
)
fig_sec.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c8c8d4",
    coloraxis_showscale=False,
    margin=dict(l=0, r=0, t=20, b=0),
    xaxis=dict(tickangle=-30, gridcolor="#1e1e2e"),
    yaxis=dict(gridcolor="#1e1e2e"),
)
st.plotly_chart(fig_sec, use_container_width=True)

# ── Price chart for a quick single stock ─────────────────────────────────────
st.divider()
st.subheader("Quick price chart")
col_t, col_p = st.columns([2, 1])
with col_t:
    sel_ticker = st.selectbox("Ticker", ticker_list, index=0, key="dash_ticker")
with col_p:
    chart_period_label = st.selectbox("Period", list(period_map.keys()), index=3, key="dash_period")
    chart_period = period_map[chart_period_label]

price_df = get_price_data(sel_ticker, chart_period)
if not price_df.empty:
    close = price_df["close"].squeeze()
    fig = go.Figure()
    color = "#00d4a1" if close.iloc[-1] >= close.iloc[0] else "#f25050"
    fig.add_trace(go.Scatter(
        x=close.index, y=close, mode="lines",
        line=dict(color=color, width=1.5), name=sel_ticker,
        fill="tozeroy", fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d4", height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e1e2e", showgrid=True),
        yaxis=dict(gridcolor="#1e1e2e", showgrid=True),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
