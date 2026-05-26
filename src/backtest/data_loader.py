"""Data loading and feature construction for backtesting."""
from __future__ import annotations

import logging

import pandas as pd
from src.backtest.validation_constants import CRISIS_WINDOWS  # noqa: F401 — D-150e

logger = logging.getLogger(__name__)

# MA-deviation denominators: "how far from 30d MA is extreme?"
# This approach measures deviation from recent trend rather than absolute direction,
# avoiding the structural TRY-depreciation bias that would keep macro scores
# permanently low throughout any multi-month Turkey backtest.
_NORM_MADEV = {
    "USDTRY": 0.04,    # ±4% deviation from 30d MA = extreme USDTRY move
    "VIX":    0.20,    # ±20% deviation from 30d MA VIX level
    "BRENT":  0.08,    # ±8% deviation from 30d MA Brent
    "SP500":  0.05,    # ±5% deviation from 30d MA S&P
    "BIST100": 0.06,   # ±6% deviation from 30d MA BIST100
}
_MA_WINDOW = 30  # 30-day moving average window

_MACRO_INSTRUMENTS = {
    "USDTRY": "USDTRY=X",
    "VIX":    "^VIX",
    "BRENT":  "BZ=F",
    "SP500":  "^GSPC",
    "BIST100": "XU100.IS",
}


def load_price_data(
    tickers: list[str],
    start: str,
    end: str,
) -> dict[str, pd.DataFrame]:
    """Download BIST OHLCV data via yfinance (.IS suffix appended automatically).

    Returns {ticker: DataFrame} with columns [Open, High, Low, Close, Volume].
    Silently skips tickers with insufficient data (<20 rows).
    """
    import yfinance as yf

    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        symbol = f"{ticker}.IS" if not ticker.endswith(".IS") else ticker
        try:
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            if df.empty or len(df) < 20:
                logger.debug(f"{ticker}: insufficient data ({len(df)} rows), skipping")
                continue
            # Handle MultiIndex columns from newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(level=1, axis=1)
            result[ticker] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            logger.debug(f"{ticker}: loaded {len(df)} rows")
        except Exception as exc:
            logger.warning(f"{ticker}: download failed — {exc}")
    return result


def load_macro_series(start: str, end: str) -> pd.DataFrame:
    """Download macro time series from yfinance.

    Returns DataFrame with columns [USDTRY, VIX, BRENT, SP500, BIST100].
    Missing values forward-filled.
    """
    import yfinance as yf

    series: dict[str, pd.Series] = {}
    for name, symbol in _MACRO_INSTRUMENTS.items():
        try:
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            if df.empty:
                logger.warning(f"Macro {name} ({symbol}): no data")
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(level=1, axis=1)
            series[name] = df["Close"]
        except Exception as exc:
            logger.warning(f"Macro {name}: download failed — {exc}")

    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).ffill()


def _compute_adx(snap: pd.DataFrame, period: int = 14) -> float | None:
    """Wilder's {period}-period Average Directional Index. Pure pandas (D-156).

    Returns float in [0, 100] or None if:
    - Insufficient data (< 2 * period rows)
    - Missing High/Low/Close columns
    - Resulting ADX is NaN (e.g., flat price series)

    Minimum veri gereksinimi: 28 gün (14 ATR warmup + 14 ADX smoothing).
    """
    if len(snap) < 2 * period:
        return None
    if not {"High", "Low", "Close"}.issubset(snap.columns):
        return None

    high = snap["High"]
    low = snap["Low"]
    close = snap["Close"]
    prev_close = close.shift(1)

    # True Range: max(H-L, |H-prevClose|, |L-prevClose|)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional Movement (raw)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # Wilder's EWM smoothing (alpha = 1/period)
    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr

    # DX = |+DI - -DI| / (+DI + -DI) × 100; ADX = Wilder smooth of DX
    di_sum = plus_di + minus_di
    dx = (
        (plus_di - minus_di).abs()
        / di_sum.where(di_sum != 0, other=float("nan"))
        * 100.0
    )
    adx_series = dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    last_adx = adx_series.iloc[-1]
    if pd.isna(last_adx):
        return None
    return round(float(last_adx), 4)


def build_technical_data(df: pd.DataFrame, as_of: pd.Timestamp) -> dict | None:
    """Build technical_data dict for score_technical() from OHLCV snapshot.

    Enforces look-ahead guard: only rows <= as_of are used.
    Returns None if insufficient data (<14 rows).
    """
    snap = df.loc[:as_of]
    if len(snap) < 14:
        return None

    close = snap["Close"]
    volume = snap["Volume"]

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    last_loss = loss.iloc[-1]
    if last_loss == 0 or pd.isna(last_loss):
        rsi = 100.0
    else:
        rs = gain.iloc[-1] / last_loss
        rsi = float(100 - (100 / (1 + rs)))

    # Moving averages
    ma20 = float(close.rolling(20).mean().iloc[-1]) if len(snap) >= 20 else None
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(snap) >= 50 else None
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(snap) >= 200 else None

    # Momentum (20-day return, clamped to ±0.30)
    if len(snap) >= 21:
        close_20d = close.iloc[-21]
        momentum = float((close.iloc[-1] - close_20d) / close_20d) if close_20d != 0 else 0.0
        momentum = max(-0.30, min(0.30, momentum))
    else:
        momentum = 0.0

    # Volume surge (current > 1.5x 20-day avg)
    vol_20d_avg = volume.rolling(20).mean().iloc[-1] if len(snap) >= 20 else None
    if vol_20d_avg and vol_20d_avg > 0:
        volume_surge = bool(volume.iloc[-1] > 1.5 * vol_20d_avg)
    else:
        volume_surge = False

    # Proximity to 52-week high (fraction below high; 0 = at high)
    window = min(252, len(snap))
    high_52w = float(snap["High"].iloc[-window:].max())
    current_close = float(close.iloc[-1])
    if high_52w > 0:
        proximity_52w_high = (high_52w - current_close) / high_52w
    else:
        proximity_52w_high = 0.0

    return {
        "rsi": rsi,
        "close": current_close,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "momentum_score": momentum,
        "volume_surge": volume_surge,
        "proximity_52w_high": proximity_52w_high,
        "prev_close": float(close.iloc[-2]) if len(snap) >= 2 else current_close,
        "adx": _compute_adx(snap),  # D-156: Wilder-14 ADX, None if < 28 rows
    }


def build_macro_data(macro_ts: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Build macro_data dict for score_macro() and score_risk() from macro time series.

    Enforces look-ahead guard: only rows <= as_of are used.
    Normalized daily pct changes to [-1, +1] for macro_layer.
    Raw values kept for risk_layer (vix_level, USDTRY_1d_change).
    Returns {} if insufficient data.
    """
    if macro_ts.empty:
        return {}

    snap = macro_ts.loc[:as_of]
    if len(snap) < 2:
        return {}

    today = snap.iloc[-1]
    yesterday = snap.iloc[-2]
    result: dict = {}

    for col, norm_factor in _NORM_MADEV.items():
        if col not in snap.columns:
            continue
        curr_val = float(today[col])
        if pd.isna(curr_val):
            continue
        # 30-day MA deviation: measures whether asset is above/below recent trend.
        # This avoids the structural TRY-depreciation bias from raw returns.
        window = _MA_WINDOW if len(snap) >= _MA_WINDOW else len(snap)
        ma = float(snap[col].rolling(window).mean().iloc[-1])
        if pd.isna(ma) or ma == 0:
            continue
        deviation = (curr_val - ma) / ma
        normalized = float(max(-1.0, min(1.0, deviation / norm_factor)))
        result[col] = normalized

    # Extra keys consumed by risk_layer (kept as daily / absolute)
    if "VIX" in snap.columns and not pd.isna(today["VIX"]):
        result["vix_level"] = float(today["VIX"])
    if "USDTRY" in snap.columns:
        prev_1d = float(yesterday["USDTRY"]) if not pd.isna(yesterday["USDTRY"]) else 0.0
        curr_1d = float(today["USDTRY"]) if not pd.isna(today["USDTRY"]) else 0.0
        if prev_1d != 0:
            result["USDTRY_1d_change"] = float((curr_1d - prev_1d) / prev_1d)
    if "BIST100" in snap.columns:
        prev_1d = float(yesterday["BIST100"]) if not pd.isna(yesterday["BIST100"]) else 0.0
        curr_1d = float(today["BIST100"]) if not pd.isna(today["BIST100"]) else 0.0
        if prev_1d != 0:
            result["BIST100_1d_change"] = float((curr_1d - prev_1d) / prev_1d)

    return result
