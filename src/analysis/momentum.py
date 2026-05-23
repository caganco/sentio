import numpy as np
import pandas as pd

from src.analysis.technicals import calculate_rsi
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def calculate_volume_surge(df: pd.DataFrame, window: int = 20) -> float:
    """Ratio of today's volume to the 20-day average volume."""
    if len(df) < window + 1:
        return float("nan")
    avg_vol = df["Volume"].iloc[-(window + 1):-1].mean()
    if avg_vol == 0:
        return float("nan")
    return float(df["Volume"].iloc[-1] / avg_vol)


def find_high_52w_proximity(df: pd.DataFrame) -> float:
    """Fraction below the 52-week high (0 = at the high, 0.10 = 10% below)."""
    lookback = min(252, len(df))
    high_52w = df["High"].iloc[-lookback:].max()
    current = float(df["Close"].iloc[-1])
    if high_52w == 0:
        return float("nan")
    return float((high_52w - current) / high_52w)


def calculate_momentum_score(df: pd.DataFrame, vol_threshold: float = 1.5, proximity_threshold: float = 0.05) -> float:
    """
    Composite momentum score (higher = stronger momentum).
    Components:
      - 1-month return (40%)
      - 3-month return (30%)
      - Volume surge ratio (20%)
      - 52-week high proximity bonus (10%)
    """
    if len(df) < 60:
        return float("nan")

    close = df["Close"]
    ret_1m = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] if len(df) >= 21 else 0
    ret_3m = (close.iloc[-1] - close.iloc[-63]) / close.iloc[-63] if len(df) >= 63 else 0

    vol_surge = calculate_volume_surge(df)
    proximity = find_high_52w_proximity(df)

    vol_score = min(vol_surge / vol_threshold, 3.0) if not np.isnan(vol_surge) else 1.0
    prox_bonus = 1.0 if (not np.isnan(proximity) and proximity <= proximity_threshold) else 0.0

    score = (ret_1m * 0.40) + (ret_3m * 0.30) + ((vol_score - 1) * 0.20) + (prox_bonus * 0.10)
    return round(float(score), 4)


def scan_momentum_stocks(
    all_data: dict[str, pd.DataFrame],
    vol_threshold: float = 1.5,
    proximity_threshold: float = 0.05,
    min_price: float = 1.0,
    top_n: int = 10,
) -> pd.DataFrame:
    """Scan all stocks and return a ranked DataFrame of momentum candidates."""
    rows = []
    for ticker, df in all_data.items():
        if df is None or df.empty or len(df) < 20:
            continue

        current_price = float(df["Close"].iloc[-1])
        if current_price < min_price:
            continue

        prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else current_price
        daily_chg = (current_price - prev_close) / prev_close * 100 if prev_close else 0

        vol_surge = calculate_volume_surge(df)
        proximity = find_high_52w_proximity(df)
        score = calculate_momentum_score(df, vol_threshold, proximity_threshold)

        ret_1m = (
            (current_price - float(df["Close"].iloc[-21])) / float(df["Close"].iloc[-21]) * 100
            if len(df) >= 21 else float("nan")
        )

        rsi = calculate_rsi(df["Close"]).iloc[-1]

        rows.append({
            "ticker": ticker,
            "close": round(current_price, 2),
            "daily_chg_pct": round(daily_chg, 2),
            "vol_surge": round(vol_surge, 2) if not np.isnan(vol_surge) else None,
            "proximity_52w_high_pct": round(proximity * 100, 1) if not np.isnan(proximity) else None,
            "ret_1m_pct": round(ret_1m, 1) if not np.isnan(ret_1m) else None,
            "rsi": round(float(rsi), 1) if not np.isnan(rsi) else None,
            "momentum_score": score if not np.isnan(score) else None,
        })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("momentum_score", ascending=False).head(top_n)
    return result.reset_index(drop=True)
