import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_sp500_tickers, get_price_data

st.title("⚠️ Risk Monitor")
st.caption("Portfolio P&L · Position sizing · Drawdown alerts")

tickers_df = get_sp500_tickers()
ticker_list = tickers_df["ticker"].tolist()

# ── Portfolio input ──────────────────────────────────────────────────────────
st.subheader("Portfolio positions")
st.caption("Enter your current holdings. P&L and risk metrics will be calculated live.")

if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = pd.DataFrame([
        {"ticker": "AAPL", "shares": 50, "avg_cost": 170.0},
        {"ticker": "MSFT", "shares": 30, "avg_cost": 380.0},
        {"ticker": "NVDA", "shares": 20, "avg_cost": 480.0},
    ])

edited = st.data_editor(
    st.session_state["portfolio"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "ticker":   st.column_config.SelectboxColumn("Ticker", options=ticker_list),
        "shares":   st.column_config.NumberColumn("Shares", min_value=0, format="%.0f"),
        "avg_cost": st.column_config.NumberColumn("Avg cost $", min_value=0, format="$%.2f"),
    },
    key="portfolio_editor",
)
st.session_state["portfolio"] = edited

# ── Risk settings ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Risk parameters"):
    c1, c2, c3 = st.columns(3)
    with c1:
        stop_loss_pct = st.slider("Stop-loss %", 1, 30, 10,
                                   help="Alert when position is X% below avg cost")
    with c2:
        take_profit_pct = st.slider("Take-profit %", 5, 100, 25)
    with c3:
        max_position_pct = st.slider("Max single position %", 5, 50, 20,
                                      help="Alert if any position > X% of total portfolio")

if st.button("📊 Calculate risk", type="primary", use_container_width=True):
    portfolio = st.session_state["portfolio"].dropna(subset=["ticker"])
    if portfolio.empty:
        st.warning("Add at least one position.")
        st.stop()

    records = []
    with st.spinner("Fetching current prices…"):
        for _, row in portfolio.iterrows():
            ticker = str(row["ticker"]).strip()
            shares = float(row["shares"])
            avg_cost = float(row["avg_cost"])
            if not ticker or shares == 0:
                continue
            try:
                price_df = get_price_data(ticker, "6mo")
                if price_df.empty:
                    continue
                close = price_df["close"].squeeze()
                current_price = close.iloc[-1]
                cost_basis    = avg_cost * shares
                market_value  = current_price * shares
                unrealized_pnl = market_value - cost_basis
                pnl_pct        = (current_price / avg_cost - 1) * 100

                # Drawdown from peak
                peak = close.max()
                drawdown_from_peak = (current_price / peak - 1) * 100

                # 1M volatility (annualised)
                daily_ret = close.pct_change().dropna()
                vol_1m = daily_ret.tail(22).std() * (252 ** 0.5) * 100

                records.append({
                    "ticker":         ticker,
                    "shares":         shares,
                    "avg_cost":       avg_cost,
                    "current_price":  round(current_price, 2),
                    "cost_basis":     round(cost_basis, 2),
                    "market_value":   round(market_value, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "pnl_pct":        round(pnl_pct, 2),
                    "drawdown_peak":  round(drawdown_from_peak, 2),
                    "vol_ann":        round(vol_1m, 1),
                })
            except Exception:
                continue

    if not records:
        st.error("Could not load prices. Check tickers.")
        st.stop()

    result_df = pd.DataFrame(records)
    total_value = result_df["market_value"].sum()
    result_df["weight_pct"] = (result_df["market_value"] / total_value * 100).round(2)
    st.session_state["risk_results"] = result_df
    st.session_state["risk_total"]   = total_value
    st.session_state["risk_params"]  = (stop_loss_pct, take_profit_pct, max_position_pct)

if "risk_results" in st.session_state:
    df = st.session_state["risk_results"]
    total_value = st.session_state["risk_total"]
    stop_loss_pct, take_profit_pct, max_position_pct = st.session_state["risk_params"]

    st.divider()

    # ── Summary ───────────────────────────────────────────────────────────────
    total_cost   = df["cost_basis"].sum()
    total_pnl    = df["unrealized_pnl"].sum()
    total_pnl_pct = (total_value / total_cost - 1) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total market value", f"${total_value:,.0f}")
    c2.metric("Total cost basis",   f"${total_cost:,.0f}")
    c3.metric("Unrealized P&L",     f"${total_pnl:+,.0f}", f"{total_pnl_pct:+.2f}%")
    c4.metric("# Positions",        len(df))

    st.divider()

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = []
    for _, r in df.iterrows():
        if r["pnl_pct"] <= -stop_loss_pct:
            alerts.append(f"🔴 **{r['ticker']}** — Stop-loss triggered: {r['pnl_pct']:+.1f}% (threshold: -{stop_loss_pct}%)")
        if r["pnl_pct"] >= take_profit_pct:
            alerts.append(f"🟢 **{r['ticker']}** — Take-profit zone: {r['pnl_pct']:+.1f}% (threshold: +{take_profit_pct}%)")
        if r["weight_pct"] > max_position_pct:
            alerts.append(f"⚠️ **{r['ticker']}** — Overweight: {r['weight_pct']:.1f}% of portfolio (max: {max_position_pct}%)")

    if alerts:
        st.subheader("Alerts")
        for a in alerts:
            st.warning(a)

    # ── Position table ────────────────────────────────────────────────────────
    st.subheader("Position detail")
    display = df.copy()
    st.dataframe(
        display.style.applymap(
            lambda v: "color:#00d4a1" if isinstance(v, float) and v > 0
               else  ("color:#f25050" if isinstance(v, float) and v < 0 else ""),
            subset=["unrealized_pnl", "pnl_pct", "drawdown_peak"]
        ),
        use_container_width=True, hide_index=True,
        column_config={
            "current_price":  st.column_config.NumberColumn("Price",      format="$%.2f"),
            "cost_basis":     st.column_config.NumberColumn("Cost basis",  format="$%.2f"),
            "market_value":   st.column_config.NumberColumn("Mkt value",   format="$%.2f"),
            "unrealized_pnl": st.column_config.NumberColumn("Unreal. P&L", format="$%.2f"),
            "pnl_pct":        st.column_config.NumberColumn("P&L %",       format="%.2f%%"),
            "drawdown_peak":  st.column_config.NumberColumn("DD from peak",format="%.2f%%"),
            "vol_ann":        st.column_config.NumberColumn("Ann. vol %",   format="%.1f%%"),
            "weight_pct":     st.column_config.ProgressColumn("Weight %", min_value=0, max_value=100, format="%.1f%%"),
        }
    )

    st.divider()
    col_a, col_b = st.columns(2)

    # ── Portfolio pie ────────────────────────────────────────────────────────
    with col_a:
        st.subheader("Portfolio allocation")
        fig_pie = px.pie(df, names="ticker", values="market_value",
                         color_discrete_sequence=px.colors.qualitative.Dark24,
                         height=320)
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="#c8c8d4",
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── P&L bar ──────────────────────────────────────────────────────────────
    with col_b:
        st.subheader("Unrealized P&L by position")
        fig_bar = go.Figure(go.Bar(
            x=df["ticker"], y=df["unrealized_pnl"],
            marker_color=["#00d4a1" if v >= 0 else "#f25050" for v in df["unrealized_pnl"]],
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c8c8d4", height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(gridcolor="#1e1e2e"),
            yaxis=dict(gridcolor="#1e1e2e", tickprefix="$"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Position sizing guide ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Position sizing guide (Kelly-lite)")
    st.caption("Based on annualised volatility. Assume 2% portfolio risk per trade.")
    risk_per_trade = total_value * 0.02
    sizing_records = []
    for _, r in df.iterrows():
        daily_vol = r["vol_ann"] / (252 ** 0.5)
        dollar_vol = r["current_price"] * daily_vol / 100
        suggested_shares = risk_per_trade / (r["current_price"] * (stop_loss_pct / 100))
        sizing_records.append({
            "ticker": r["ticker"],
            "current_price": r["current_price"],
            "ann_vol_%": r["vol_ann"],
            "stop_loss_$": round(r["current_price"] * stop_loss_pct / 100, 2),
            "suggested_shares (2% risk)": int(suggested_shares),
            "suggested_value": round(suggested_shares * r["current_price"], 0),
        })
    st.dataframe(pd.DataFrame(sizing_records), use_container_width=True, hide_index=True,
        column_config={
            "current_price":    st.column_config.NumberColumn("Price", format="$%.2f"),
            "stop_loss_$":      st.column_config.NumberColumn("Stop $", format="$%.2f"),
            "suggested_value":  st.column_config.NumberColumn("Suggested value", format="$%.0f"),
        }
    )
