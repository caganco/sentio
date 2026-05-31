"""D-185 Trend-Motor Test -- hand-rolled, look-ahead-safe technical indicators.

Pure pandas/numpy + scipy.find_peaks + sklearn AgglomerativeClustering. No new
heavy dependency (no vectorbt / pandas-ta). Every indicator is TRAILING only
(uses bar t and earlier); forward-looking quantities are forbidden here.

Swing detection (find_peaks) is two-sided by nature: a peak at index p needs
`distance` bars on each side to be confirmed. Look-ahead safety is enforced by
the CALLER (trend_signals): a peak is only usable as-of date t if it is already
confirmed (p + distance <= t). See confirmed_swing_highs / _lows.

No composite / conviction / MASTER_WEIGHTS / signal-engine / backtest-engine
imports (architecture invariant; mirrors factor_ic_harness).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.cluster import AgglomerativeClustering


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------
def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average (trailing)."""
    return series.rolling(window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average (trailing, no look-ahead)."""
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


# ---------------------------------------------------------------------------
# RSI (Wilder, EWM form)
# ---------------------------------------------------------------------------
def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder RSI via exponential smoothing (alpha=1/window). Trailing."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # avg_loss == 0 -> RSI 100 (pure up-streak)
    out = out.where(avg_loss != 0.0, 100.0)
    return out


# ---------------------------------------------------------------------------
# True range / ATR (Wilder)
# ---------------------------------------------------------------------------
def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average true range, Wilder smoothing (alpha=1/window). Trailing."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


# ---------------------------------------------------------------------------
# Bollinger bandwidth
# ---------------------------------------------------------------------------
def bollinger_bandwidth(close: pd.Series, window: int = 20, n_std: float = 2.0) -> pd.Series:
    """(upper - lower) / middle for Bollinger(window, n_std). Trailing.

    Lower bandwidth = tighter consolidation.
    """
    mid = close.rolling(window, min_periods=window).mean()
    sd = close.rolling(window, min_periods=window).std(ddof=0)
    upper = mid + n_std * sd
    lower = mid - n_std * sd
    return (upper - lower) / mid.replace(0.0, np.nan)


# ---------------------------------------------------------------------------
# Donchian channels (PRIOR window -> breakout/stop ready, no current-bar leak)
# ---------------------------------------------------------------------------
def donchian_upper_prior(high: pd.Series, window: int) -> pd.Series:
    """Highest high of the PRIOR `window` bars (excludes current bar).

    Breakout test at t: close[t] > donchian_upper_prior[t].
    """
    return high.rolling(window, min_periods=window).max().shift(1)


def donchian_lower_prior(low: pd.Series, window: int) -> pd.Series:
    """Lowest low of the PRIOR `window` bars (excludes current bar).

    Trailing-stop test at t: close[t] < donchian_lower_prior[t] (or low<=...).
    """
    return low.rolling(window, min_periods=window).min().shift(1)


# ---------------------------------------------------------------------------
# ADX (Wilder DMI)
# ---------------------------------------------------------------------------
def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder ADX (trend strength, direction-agnostic). Trailing."""
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    tr = true_range(high, low, close)
    atr_w = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr_w
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean() / atr_w
    denom = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denom
    return dx.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


# ---------------------------------------------------------------------------
# Range patterns
# ---------------------------------------------------------------------------
def nr7(high: pd.Series, low: pd.Series) -> pd.Series:
    """True where today's range is the narrowest of the last 7 bars (trailing)."""
    rng = high - low
    return rng == rng.rolling(7, min_periods=7).min()


def inside_bar(high: pd.Series, low: pd.Series) -> pd.Series:
    """True where bar is inside the prior bar (high<prev high and low>prev low)."""
    return (high < high.shift(1)) & (low > low.shift(1))


# ---------------------------------------------------------------------------
# Swing extrema (find_peaks) -- caller enforces confirmation lag
# ---------------------------------------------------------------------------
def _peaks(values: np.ndarray, distance: int, prominence: float | None) -> np.ndarray:
    """Indices of local maxima with min horizontal distance + prominence."""
    if len(values) < 3:
        return np.array([], dtype=int)
    kw: dict = {"distance": max(1, distance)}
    if prominence is not None and prominence > 0:
        kw["prominence"] = prominence
    idx, _ = find_peaks(values, **kw)
    return idx


def swing_high_idx(high: pd.Series, distance: int, prominence: float | None = None) -> np.ndarray:
    """Positional indices of swing highs in `high`."""
    return _peaks(high.to_numpy(dtype=float), distance, prominence)


def swing_low_idx(low: pd.Series, distance: int, prominence: float | None = None) -> np.ndarray:
    """Positional indices of swing lows in `low` (peaks of the negated series)."""
    return _peaks(-low.to_numpy(dtype=float), distance, prominence)


# ---------------------------------------------------------------------------
# Support/resistance zones via 1D agglomerative clustering of swing prices
# ---------------------------------------------------------------------------
def sr_zones(prices: np.ndarray, merge_distance: float, min_touches: int) -> list[tuple[float, int]]:
    """Cluster swing-high prices into resistance zones.

    Returns [(zone_price, touch_count), ...] for clusters with >= min_touches,
    sorted ascending by price. merge_distance is the agglomerative distance
    threshold (typically ~1 x ATR). Deterministic.
    """
    prices = np.asarray(prices, dtype=float)
    prices = prices[~np.isnan(prices)]
    if len(prices) == 0 or merge_distance <= 0:
        return []
    if len(prices) == 1:
        return [(float(prices[0]), 1)] if min_touches <= 1 else []
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=float(merge_distance),
        linkage="single",
        metric="euclidean",
    )
    labels = model.fit_predict(prices.reshape(-1, 1))
    zones: list[tuple[float, int]] = []
    for lab in np.unique(labels):
        members = prices[labels == lab]
        if len(members) >= min_touches:
            zones.append((float(np.mean(members)), int(len(members))))
    zones.sort(key=lambda z: z[0])
    return zones
