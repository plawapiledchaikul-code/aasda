import pandas as pd
import numpy as np

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def compute_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_roc(series: pd.Series, period: int = 63) -> pd.Series:
    return (series / series.shift(period) - 1) * 100

def momentum_score(price_df: pd.DataFrame) -> dict:
    """
    Score 0-100. Components:
      - RSI trend (RSI 14 between 50-70 = bullish zone)
      - MACD crossover (macd > signal → bullish)
      - ROC 3M (positive = +pts)
      - 52w position (price in top 30% of 52w range → bullish)
      - Volume surge (>1.5x avg = confirms move)
    """
    if price_df.empty or len(price_df) < 30:
        return {"momentum_score": None, "rsi": None, "macd_bull": None,
                "roc_3m": None, "w52_pct": None, "vol_surge": None}

    close = price_df["close"].squeeze()
    volume = price_df["volume"].squeeze() if "volume" in price_df.columns else None

    rsi = compute_rsi(close).iloc[-1]
    macd_line, signal_line, _ = compute_macd(close)
    macd_bull = macd_line.iloc[-1] > signal_line.iloc[-1]
    roc_3m = compute_roc(close, 63).iloc[-1] if len(close) >= 63 else 0.0

    w52_high = close.tail(252).max()
    w52_low  = close.tail(252).min()
    w52_range = w52_high - w52_low
    w52_pct = ((close.iloc[-1] - w52_low) / w52_range * 100) if w52_range > 0 else 50

    vol_surge = 1.0
    if volume is not None and len(volume) >= 20:
        avg_vol = volume.iloc[-20:-1].mean()
        vol_surge = (volume.iloc[-1] / avg_vol) if avg_vol > 0 else 1.0

    # Scoring
    score = 0
    # RSI component (0-30 pts)
    if 50 <= rsi <= 70:
        score += 30
    elif 40 <= rsi < 50:
        score += 15
    elif rsi > 70:
        score += 20  # overbought but still bullish
    elif rsi < 40:
        score += 0

    # MACD (0-20 pts)
    score += 20 if macd_bull else 0

    # ROC 3M (0-30 pts)
    if roc_3m >= 15:
        score += 30
    elif roc_3m >= 5:
        score += 20
    elif roc_3m >= 0:
        score += 10
    else:
        score += 0

    # 52w position (0-10 pts)
    if w52_pct >= 70:
        score += 10
    elif w52_pct >= 40:
        score += 5

    # Volume surge (0-10 pts)
    if vol_surge >= 2.0:
        score += 10
    elif vol_surge >= 1.5:
        score += 7
    elif vol_surge >= 1.2:
        score += 4

    return {
        "momentum_score": min(score, 100),
        "rsi":            round(rsi, 1),
        "macd_bull":      macd_bull,
        "roc_3m":         round(roc_3m, 2),
        "w52_pct":        round(w52_pct, 1),
        "vol_surge":      round(vol_surge, 2),
    }

def fundamental_score(info: dict) -> dict:
    """
    Score 0-100. Components:
      - P/E relative (low P/E within reason = better value)
      - Revenue growth
      - Earnings growth / EPS surprise
      - ROE
      - Debt/Equity
    """
    if not info:
        return {"fundamental_score": None}

    score = 0

    # P/E (0-25 pts)
    pe = info.get("pe_ratio")
    if pe and pe > 0:
        if pe < 15:
            score += 25
        elif pe < 25:
            score += 20
        elif pe < 35:
            score += 12
        elif pe < 50:
            score += 5

    # Revenue growth (0-25 pts)
    rev_g = info.get("revenue_growth")
    if rev_g is not None:
        if rev_g >= 0.20:
            score += 25
        elif rev_g >= 0.10:
            score += 18
        elif rev_g >= 0.05:
            score += 10
        elif rev_g >= 0:
            score += 5

    # Earnings growth (0-25 pts)
    earn_g = info.get("earnings_growth")
    if earn_g is not None:
        if earn_g >= 0.20:
            score += 25
        elif earn_g >= 0.10:
            score += 18
        elif earn_g >= 0.05:
            score += 10
        elif earn_g >= 0:
            score += 5

    # ROE (0-15 pts)
    roe = info.get("roe")
    if roe is not None:
        if roe >= 0.20:
            score += 15
        elif roe >= 0.12:
            score += 10
        elif roe >= 0.06:
            score += 5

    # Debt/Equity (0-10 pts) — lower is better
    de = info.get("debt_equity")
    if de is not None:
        if de < 30:
            score += 10
        elif de < 80:
            score += 7
        elif de < 150:
            score += 3

    return {"fundamental_score": min(score, 100)}

def combined_score(mom: dict, fund: dict, mom_weight=0.5, fund_weight=0.5) -> dict:
    ms = mom.get("momentum_score")
    fs = fund.get("fundamental_score")
    if ms is None and fs is None:
        return {"combined_score": None, "signal": "N/A"}
    if ms is None:
        cs = fs
    elif fs is None:
        cs = ms
    else:
        cs = ms * mom_weight + fs * fund_weight

    if cs >= 70:
        signal = "BUY"
    elif cs >= 55:
        signal = "WATCH"
    elif cs <= 30:
        signal = "AVOID"
    else:
        signal = "NEUTRAL"

    return {"combined_score": round(cs, 1), "signal": signal}

def simple_backtest(price_df: pd.DataFrame, entry_threshold=65, exit_threshold=40,
                    initial_capital=100_000) -> dict:
    """
    Rolling window backtest using momentum score as entry/exit signal.
    Rebalances weekly.
    """
    if price_df.empty or len(price_df) < 90:
        return {}

    close = price_df["close"].squeeze()
    volume = price_df["volume"].squeeze() if "volume" in price_df.columns else pd.Series(dtype=float)
    capital = float(initial_capital)
    position = 0.0
    entry_price = 0.0
    equity_curve = []
    trades = []
    in_position = False

    rsi_series = compute_rsi(close)
    macd_line, signal_line, _ = compute_macd(close)
    roc_series = compute_roc(close, 63)

    step = 5
    for i in range(66, len(close), step):
        rsi_val = rsi_series.iloc[i]
        macd_bull = macd_line.iloc[i] > signal_line.iloc[i]
        roc_val = roc_series.iloc[i] if not pd.isna(roc_series.iloc[i]) else 0
        w52_high = close.iloc[max(0, i-252):i].max()
        w52_low  = close.iloc[max(0, i-252):i].min()
        w52_range = w52_high - w52_low
        w52_pct = ((close.iloc[i] - w52_low) / w52_range * 100) if w52_range > 0 else 50

        vol_surge = 1.0
        if not volume.empty and i >= 20:
            avg_vol = volume.iloc[i-20:i-1].mean()
            if avg_vol > 0:
                vol_surge = volume.iloc[i] / avg_vol

        # Quick score
        sc = 0
        if 50 <= rsi_val <= 70: sc += 30
        elif rsi_val > 70: sc += 20
        elif 40 <= rsi_val < 50: sc += 15
        sc += 20 if macd_bull else 0
        if roc_val >= 15: sc += 30
        elif roc_val >= 5: sc += 20
        elif roc_val >= 0: sc += 10
        if w52_pct >= 70: sc += 10
        elif w52_pct >= 40: sc += 5
        if vol_surge >= 2.0: sc += 10
        elif vol_surge >= 1.5: sc += 7
        elif vol_surge >= 1.2: sc += 4

        price_now = close.iloc[i]
        date_now  = close.index[i]

        if not in_position and sc >= entry_threshold:
            position = capital / price_now
            entry_price = price_now
            entry_date = date_now
            in_position = True

        elif in_position and sc < exit_threshold:
            pnl = (price_now - entry_price) * position
            trades.append({
                "entry_date": entry_date, "exit_date": date_now,
                "entry_price": round(entry_price, 2), "exit_price": round(price_now, 2),
                "pnl": round(pnl, 2),
                "return_pct": round((price_now / entry_price - 1) * 100, 2),
            })
            capital += pnl
            position = 0
            in_position = False

        portfolio_val = capital + (position * price_now if in_position else 0)
        equity_curve.append({"date": date_now, "equity": portfolio_val})

    # Close open position
    if in_position:
        pnl = (close.iloc[-1] - entry_price) * position
        trades.append({
            "entry_date": entry_date, "exit_date": close.index[-1],
            "entry_price": round(entry_price, 2), "exit_price": round(close.iloc[-1], 2),
            "pnl": round(pnl, 2),
            "return_pct": round((close.iloc[-1] / entry_price - 1) * 100, 2),
        })
        capital += pnl

    eq_df = pd.DataFrame(equity_curve).set_index("date")
    total_return = (capital / initial_capital - 1) * 100
    returns = eq_df["equity"].pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0
    rolling_max = eq_df["equity"].cummax()
    drawdown = (eq_df["equity"] - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()
    win_trades = [t for t in trades if t["pnl"] > 0]

    return {
        "equity_curve":   eq_df,
        "trades":         pd.DataFrame(trades),
        "total_return":   round(total_return, 2),
        "sharpe":         round(sharpe, 2),
        "max_drawdown":   round(max_dd, 2),
        "num_trades":     len(trades),
        "win_rate":       round(len(win_trades) / len(trades) * 100, 1) if trades else 0,
        "final_capital":  round(capital, 2),
    }
