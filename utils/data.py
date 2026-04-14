import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

@st.cache_data(ttl=86400)
def get_sp500_tickers() -> pd.DataFrame:
    """Fetch S&P 500 tickers + metadata from Wikipedia."""
    tables = pd.read_html(SP500_URL)
    df = tables[0][["Symbol", "Security", "GICS Sector", "GICS Sub-Industry", "Date added"]]
    df.columns = ["ticker", "name", "sector", "sub_industry", "date_added"]
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df.reset_index(drop=True)

@st.cache_data(ttl=3600)
def get_price_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download OHLCV data for a single ticker."""
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fundamentals(ticker: str) -> dict:
    """Fetch fundamental data from yfinance."""
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe_ratio":          info.get("trailingPE"),
            "forward_pe":        info.get("forwardPE"),
            "pb_ratio":          info.get("priceToBook"),
            "ev_ebitda":         info.get("enterpriseToEbitda"),
            "revenue_growth":    info.get("revenueGrowth"),
            "earnings_growth":   info.get("earningsGrowth"),
            "profit_margin":     info.get("profitMargins"),
            "roe":               info.get("returnOnEquity"),
            "debt_equity":       info.get("debtToEquity"),
            "current_ratio":     info.get("currentRatio"),
            "market_cap":        info.get("marketCap"),
            "eps_ttm":           info.get("trailingEps"),
            "dividend_yield":    info.get("dividendYield"),
            "52w_high":          info.get("fiftyTwoWeekHigh"),
            "52w_low":           info.get("fiftyTwoWeekLow"),
            "analyst_target":    info.get("targetMeanPrice"),
            "recommendation":    info.get("recommendationKey"),
            "short_name":        info.get("shortName", ticker),
            "sector":            info.get("sector", ""),
            "industry":          info.get("industry", ""),
        }
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_batch_quotes(tickers: list[str]) -> pd.DataFrame:
    """Download latest close prices for a list of tickers."""
    try:
        raw = yf.download(tickers, period="6mo", auto_adjust=True,
                          progress=False, group_by="ticker")
        records = []
        for t in tickers:
            try:
                if len(tickers) == 1:
                    sub = raw
                else:
                    sub = raw[t]
                sub.columns = [c.lower() for c in sub.columns]
                sub = sub.dropna(subset=["close"])
                if sub.empty:
                    continue
                close = sub["close"]
                vol   = sub["volume"]
                ret1d  = (close.iloc[-1] / close.iloc[-2] - 1) if len(close) >= 2 else None
                ret1m  = (close.iloc[-1] / close.iloc[-22] - 1) if len(close) >= 22 else None
                ret3m  = (close.iloc[-1] / close.iloc[-66] - 1) if len(close) >= 66 else None
                ret6m  = (close.iloc[-1] / close.iloc[0]  - 1) if len(close) >= 2 else None
                avg_vol = vol.iloc[-20:].mean() if len(vol) >= 20 else None
                last_vol = vol.iloc[-1]
                vol_surge = (last_vol / avg_vol) if avg_vol and avg_vol > 0 else None
                w52_high = close.max()
                w52_low  = close.min()
                pct_from_high = (close.iloc[-1] / w52_high - 1)
                records.append({
                    "ticker":         t,
                    "price":          round(close.iloc[-1], 2),
                    "ret_1d":         ret1d,
                    "ret_1m":         ret1m,
                    "ret_3m":         ret3m,
                    "ret_6m":         ret6m,
                    "vol_surge":      vol_surge,
                    "pct_from_52h":   pct_from_high,
                    "52w_high":       w52_high,
                    "52w_low":        w52_low,
                })
            except Exception:
                continue
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()
