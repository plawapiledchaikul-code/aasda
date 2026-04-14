# US Equity Signal Dashboard

Momentum + Fundamental signal screener for S&P 500 stocks.
Built with Streamlit + yfinance. No paid API required.

## Features
- **Dashboard** — market overview, sector heatmap, top movers
- **Signal Screener** — scan up to 505 S&P 500 tickers with composite scoring
- **Stock Detail** — price chart + RSI/MACD/volume + fundamental metrics
- **Backtest** — momentum strategy vs buy-and-hold with Sharpe & drawdown
- **Risk Monitor** — portfolio P&L, alerts, position sizing guide

## Deploy on Streamlit Cloud (free)

1. Push this folder to a **GitHub repo** (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Set:
   - **Repository**: your GitHub repo
   - **Branch**: main
   - **Main file path**: `app.py`
4. Click **Deploy** — done in ~2 minutes

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Yahoo Finance data is delayed ~15min for US equities
- Scanning all 500 tickers takes ~8-12 min (cached for 1 hour after first run)
- For faster screening, limit to a sector or reduce "Max tickers to scan"
- Auto trading execution requires a broker API (Alpaca, IBKR) — not included

## Project structure
```
app.py                  ← entry point
pages/
  1_dashboard.py        ← market overview
  2_screener.py         ← S&P 500 signal scanner
  3_stock_detail.py     ← single stock deep dive
  4_backtest.py         ← strategy backtesting
  5_risk.py             ← portfolio risk monitor
utils/
  data.py               ← yfinance wrappers + caching
  signals.py            ← momentum/fundamental scoring + backtest engine
requirements.txt
.streamlit/config.toml  ← dark theme config
```
