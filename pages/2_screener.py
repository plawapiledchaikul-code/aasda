import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.data import get_sp500_tickers, get_price_data, get_fundamentals
from utils.signals import momentum_score, fundamental_score, combined_score

st.title("🔍 Signal Screener")
st.caption("Momentum + Fundamental composite score across S&P 500")

tickers_df = get_sp500_tickers()
sectors = ["All"] + sorted(tickers_df["sector"].dropna().unique().tolist())

# ── Filters ──────────────────────────────────────────────────────────────────
with st.expander("⚙️ Screener settings", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_sector = st.selectbox("Sector", sectors)
        min_score = st.slider("Min combined score", 0, 100, 60)
    with c2:
        mom_weight = st.slider("Momentum weight", 0.0, 1.0, 0.5, 0.1)
        fund_weight = round(1 - mom_weight, 1)
        st.caption(f"Fundamental weight: **{fund_weight}**")
    with c3:
        signal_filter = st.multiselect("Signal filter", ["BUY", "WATCH", "NEUTRAL", "AVOID"],
                                       default=["BUY", "WATCH"])
        max_tickers = st.number_input("Max tickers to scan (speed)", 50, 505, 100, step=50)

if sel_sector != "All":
    scan_df = tickers_df[tickers_df["sector"] == sel_sector].head(max_tickers)
else:
    scan_df = tickers_df.head(max_tickers)

st.divider()

if st.button("🚀 Run screener", type="primary", use_container_width=True):
    results = []
    progress = st.progress(0, text="Scanning…")
    total = len(scan_df)

    for i, row in scan_df.iterrows():
        ticker = row["ticker"]
        progress.progress((list(scan_df.index).index(i) + 1) / total,
                          text=f"Scanning {ticker}… ({list(scan_df.index).index(i)+1}/{total})")
        try:
            price_df = get_price_data(ticker, "1y")
            info = get_fundamentals(ticker)
            mom  = momentum_score(price_df)
            fund = fundamental_score(info)
            combo = combined_score(mom, fund, mom_weight, fund_weight)

            if combo["combined_score"] is None:
                continue
            if combo["combined_score"] < min_score:
                continue
            if signal_filter and combo["signal"] not in signal_filter:
                continue

            current_price = price_df["close"].iloc[-1] if not price_df.empty else None
            results.append({
                "ticker":         ticker,
                "name":           row["name"],
                "sector":         row["sector"],
                "price":          round(current_price, 2) if current_price else None,
                "signal":         combo["signal"],
                "combined_score": combo["combined_score"],
                "momentum_score": mom.get("momentum_score"),
                "fundamental_score": fund.get("fundamental_score"),
                "rsi":            mom.get("rsi"),
                "macd_bull":      mom.get("macd_bull"),
                "roc_3m_%":       mom.get("roc_3m"),
                "w52_pct":        mom.get("w52_pct"),
                "vol_surge":      mom.get("vol_surge"),
            })
        except Exception:
            continue

    progress.empty()

    if not results:
        st.warning("No tickers matched the filters. Try lowering min score or adjusting signal filter.")
    else:
        result_df = pd.DataFrame(results).sort_values("combined_score", ascending=False)
        st.session_state["screener_results"] = result_df
        st.success(f"✅ Found **{len(result_df)}** signals matching your criteria.")

# ── Display results ──────────────────────────────────────────────────────────
if "screener_results" in st.session_state:
    df = st.session_state["screener_results"]

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total matches", len(df))
    with c2: st.metric("BUY signals",   (df["signal"] == "BUY").sum())
    with c3: st.metric("WATCH signals", (df["signal"] == "WATCH").sum())
    with c4: st.metric("Avg combined score", f"{df['combined_score'].mean():.1f}")

    st.divider()

    def color_signal(val):
        colors = {"BUY": "color: #00d4a1; font-weight:600",
                  "WATCH": "color: #f5c842; font-weight:600",
                  "NEUTRAL": "color: #8888aa",
                  "AVOID": "color: #f25050; font-weight:600"}
        return colors.get(val, "")

    display_df = df.copy()
    display_df["macd_bull"] = display_df["macd_bull"].map({True: "✓", False: "✗"})

    st.dataframe(
        display_df.style.applymap(color_signal, subset=["signal"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "combined_score": st.column_config.ProgressColumn("Combined", min_value=0, max_value=100, format="%.1f"),
            "momentum_score": st.column_config.ProgressColumn("Momentum", min_value=0, max_value=100, format="%.0f"),
            "fundamental_score": st.column_config.ProgressColumn("Fundamental", min_value=0, max_value=100, format="%.0f"),
            "price": st.column_config.NumberColumn("Price $", format="$%.2f"),
            "vol_surge": st.column_config.NumberColumn("Vol surge", format="%.2fx"),
            "w52_pct": st.column_config.NumberColumn("52w rank %", format="%.1f%%"),
        }
    )

    csv = df.to_csv(index=False)
    st.download_button("⬇️ Export CSV", data=csv, file_name="signals.csv",
                       mime="text/csv", use_container_width=True)
