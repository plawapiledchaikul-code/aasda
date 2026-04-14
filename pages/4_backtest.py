import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_sp500_tickers, get_price_data
from utils.signals import simple_backtest

st.title("🔁 Backtest")
st.caption("Momentum-based entry/exit strategy · Single stock · Historical simulation")

tickers_df = get_sp500_tickers()
ticker_list = tickers_df["ticker"].tolist()

with st.expander("⚙️ Backtest settings", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_ticker = st.selectbox("Ticker", ticker_list,
                                   index=ticker_list.index("AAPL") if "AAPL" in ticker_list else 0)
        period_map = {"1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
        sel_period = st.selectbox("Historical period", list(period_map.keys()), index=1)
        period = period_map[sel_period]
    with c2:
        entry_threshold = st.slider("Entry score threshold", 40, 90, 65,
                                     help="Buy when momentum score ≥ this value")
        exit_threshold  = st.slider("Exit score threshold",  20, 70, 40,
                                     help="Sell when momentum score falls below this")
    with c3:
        initial_capital = st.number_input("Initial capital ($)", 10_000, 1_000_000,
                                           100_000, step=10_000)

run_bt = st.button("▶️ Run backtest", type="primary", use_container_width=True)

if run_bt:
    with st.spinner(f"Running backtest on {sel_ticker}…"):
        price_df = get_price_data(sel_ticker, period)
        results  = simple_backtest(price_df, entry_threshold, exit_threshold, initial_capital)

    if not results:
        st.error("Not enough data to run backtest. Try a longer period.")
        st.stop()

    st.session_state["bt_results"]  = results
    st.session_state["bt_ticker"]   = sel_ticker
    st.session_state["bt_price_df"] = price_df
    st.session_state["bt_capital"]  = initial_capital

if "bt_results" in st.session_state:
    results    = st.session_state["bt_results"]
    ticker     = st.session_state["bt_ticker"]
    price_df   = st.session_state["bt_price_df"]
    init_cap   = st.session_state["bt_capital"]

    st.divider()

    # ── Summary metrics ────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total return",   f"{results['total_return']:+.2f}%")
    c2.metric("Final capital",  f"${results['final_capital']:,.0f}",
              f"${results['final_capital']-init_cap:+,.0f}")
    c3.metric("Sharpe ratio",   f"{results['sharpe']:.2f}")
    c4.metric("Max drawdown",   f"{results['max_drawdown']:.2f}%")
    c5.metric("# Trades",       results["num_trades"])
    c6.metric("Win rate",       f"{results['win_rate']:.1f}%")

    st.divider()

    # ── Equity curve ──────────────────────────────────────────────────────────
    eq = results["equity_curve"]
    bh_close = price_df["close"].squeeze()
    bh_equity = (bh_close / bh_close.iloc[0]) * init_cap

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eq.index, y=eq["equity"], name="Strategy",
        line=dict(color="#00d4a1", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bh_close.index, y=bh_equity, name="Buy & Hold",
        line=dict(color="#8888aa", width=1.5, dash="dot"),
    ))
    fig.update_layout(
        title="Equity curve — Strategy vs Buy & Hold",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d4", height=380,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.05),
        xaxis=dict(gridcolor="#1e1e2e"),
        yaxis=dict(gridcolor="#1e1e2e", tickprefix="$"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Drawdown chart ────────────────────────────────────────────────────────
    rolling_max = eq["equity"].cummax()
    drawdown    = (eq["equity"] - rolling_max) / rolling_max * 100

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown, fill="tozeroy",
        fillcolor="rgba(242,80,80,0.15)", line=dict(color="#f25050", width=1),
        name="Drawdown",
    ))
    fig_dd.update_layout(
        title="Drawdown (%)",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c8c8d4", height=220,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(gridcolor="#1e1e2e"),
        yaxis=dict(gridcolor="#1e1e2e", ticksuffix="%"),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    # ── Trade log ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Trade log")
    trades_df = results["trades"]
    if not trades_df.empty:
        trades_df["entry_date"] = pd.to_datetime(trades_df["entry_date"]).dt.date
        trades_df["exit_date"]  = pd.to_datetime(trades_df["exit_date"]).dt.date
        st.dataframe(
            trades_df.style.applymap(
                lambda v: "color: #00d4a1" if isinstance(v, (int, float)) and v > 0
                     else ("color: #f25050" if isinstance(v, (int, float)) and v < 0 else ""),
                subset=["pnl", "return_pct"]
            ),
            use_container_width=True, hide_index=True,
            column_config={
                "pnl":        st.column_config.NumberColumn("P&L $",   format="$%.2f"),
                "return_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
                "entry_price":st.column_config.NumberColumn("Entry",   format="$%.2f"),
                "exit_price": st.column_config.NumberColumn("Exit",    format="$%.2f"),
            }
        )
    else:
        st.info("No completed trades in the selected period/thresholds.")
