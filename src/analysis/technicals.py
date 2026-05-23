import numpy as np
import pandas as pd


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_moving_averages(df: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    result = df.copy()
    for p in periods:
        result[f"MA{p}"] = df["Close"].rolling(window=p).mean()
    return result


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Daily VWAP: rolling cumulative (price * volume) / cumulative volume."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_pv = (typical_price * df["Volume"]).cumsum()
    cum_vol = df["Volume"].cumsum()
    return cum_pv / cum_vol.replace(0, np.nan)


def add_indicators(df: pd.DataFrame, rsi_period: int = 14, ma_periods: list[int] | None = None) -> pd.DataFrame:
    """Add RSI, moving averages, and VWAP columns to a price DataFrame."""
    if ma_periods is None:
        ma_periods = [20, 50, 200]
    result = calculate_moving_averages(df, ma_periods)
    result["RSI"] = calculate_rsi(df["Close"], period=rsi_period)
    result["VWAP"] = calculate_vwap(df)
    return result


def get_indicator_snapshot(df: pd.DataFrame, rsi_period: int = 14, ma_periods: list[int] | None = None) -> dict:
    """Return the most recent indicator values as a plain dict."""
    if ma_periods is None:
        ma_periods = [20, 50, 200]
    enriched = add_indicators(df, rsi_period=rsi_period, ma_periods=ma_periods)
    last = enriched.iloc[-1]
    close = float(last["Close"])

    snapshot: dict = {
        "close": close,
        "rsi": round(float(last["RSI"]), 1) if not pd.isna(last["RSI"]) else None,
        "vwap": round(float(last["VWAP"]), 2) if not pd.isna(last["VWAP"]) else None,
    }
    for p in ma_periods:
        col = f"MA{p}"
        val = last.get(col)
        snapshot[col.lower()] = round(float(val), 2) if val is not None and not pd.isna(val) else None
        if snapshot[col.lower()] is not None:
            snapshot[f"pct_vs_ma{p}"] = round((close - snapshot[col.lower()]) / snapshot[col.lower()] * 100, 2)

    return snapshot
