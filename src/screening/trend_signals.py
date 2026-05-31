"""D-185 Trend-Motor Test -- variant signal generators (RR-039 sec.6).

Three rule variants (A/B/C) + common pre-filter + parabolic-avoidance (on/off).
Every signal is computed at bar t using ONLY data <= t; the backtest enters at
t+1 open (look-ahead guard, mirrors factors._pit_index discipline).

Swing-based logic uses only CONFIRMED extrema as-of t: a peak at position p is
usable at i only if p <= i - distance (it already had `distance` right-side
bars). This is the look-ahead guard for two-sided find_peaks.

No composite / conviction / signal-engine / backtest-engine imports.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src.screening import indicators as ind
from src.screening import trend_config as cfg


@dataclass
class TradeSetup:
    """A long entry confirmed at signal_date close; entry executes t+1 open."""
    ticker: str
    variant: str
    parabolic_on: bool
    signal_date: str          # YYYY-MM-DD (bar t)
    stop_price: float
    ref_level: float          # zone/box/donchian level (reporting)
    trail_donchian_n: int

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Per-ticker indicator precompute (trailing only)
# ---------------------------------------------------------------------------
def compute_indicators(ohlcv: pd.DataFrame) -> dict:
    h, lo, c, v = ohlcv["high"], ohlcv["low"], ohlcv["close"], ohlcv["volume"]
    return {
        "atr": ind.atr(h, lo, c, cfg.ATR_WINDOW),
        "rsi": ind.rsi(c, cfg.PARABOLIC_RSI_WINDOW),
        "sma20": ind.sma(c, cfg.PARABOLIC_SMA_WINDOW),
        "ema_c": ind.ema(c, cfg.C_RETEST_EMA),
        "vol_ma": ind.sma(v, cfg.VOLUME_MA_WINDOW),
        "adx": ind.adx(h, lo, c, cfg.B_ADX_WINDOW),
        "bbw": ind.bollinger_bandwidth(c, cfg.B_BBW_WINDOW, cfg.B_BBW_STD),
        "nr7": ind.nr7(h, lo),
        "donch_up": ind.donchian_upper_prior(h, cfg.C_DONCHIAN_N),
        "swing_hi": ind.swing_high_idx(h, cfg.A_FIND_PEAKS_DISTANCE),
        "swing_lo": ind.swing_low_idx(lo, cfg.A_FIND_PEAKS_DISTANCE),
    }


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------
def _confirmed(idx_arr: np.ndarray, i: int, distance: int, lo_bound: int = -1) -> np.ndarray:
    """Positions confirmed as-of bar i (p <= i-distance) and >= lo_bound."""
    conf = idx_arr[idx_arr <= i - distance]
    if lo_bound >= 0:
        conf = conf[conf >= lo_bound]
    return conf


def _last_confirmed_swing_low(low: pd.Series, swing_lo: np.ndarray, i: int) -> float:
    conf = _confirmed(swing_lo, i, cfg.A_FIND_PEAKS_DISTANCE)
    if len(conf) == 0:
        return float("nan")
    return float(low.iloc[conf[-1]])


def _parabolic_block(c: float, ix: dict, i: int, low: pd.Series, swing_lo: np.ndarray) -> bool:
    """True if a NEW BUY is blocked by parabolic-avoidance (RR-039 sec.2.5)."""
    sma20 = ix["sma20"].iloc[i]
    if not np.isnan(sma20) and c > sma20 * (1.0 + cfg.PARABOLIC_SMA_DEV_PCT):
        return True
    rsi_v = ix["rsi"].iloc[i]
    if not np.isnan(rsi_v) and rsi_v > cfg.PARABOLIC_RSI_MAX:
        return True
    a = ix["atr"].iloc[i]
    sl = _last_confirmed_swing_low(low, swing_lo, i)
    if not np.isnan(a) and not np.isnan(sl) and (c - sl) > cfg.PARABOLIC_SWING_LOW_ATR_MULT * a:
        return True
    return False


def _hh_hl_ok(high: pd.Series, low: pd.Series, swing_hi: np.ndarray, swing_lo: np.ndarray, i: int) -> bool:
    """Higher-high AND higher-low over the last two confirmed swings as-of i."""
    ch = _confirmed(swing_hi, i, cfg.A_FIND_PEAKS_DISTANCE)
    cl = _confirmed(swing_lo, i, cfg.A_FIND_PEAKS_DISTANCE)
    if len(ch) < 2 or len(cl) < 2:
        return False
    hh = float(high.iloc[ch[-1]]) > float(high.iloc[ch[-2]])
    hl = float(low.iloc[cl[-1]]) > float(low.iloc[cl[-2]])
    return hh and hl


def _warmup() -> int:
    return max(cfg.A_SWING_LOOKBACK_DAYS, cfg.B_BBW_LOOKBACK_DAYS,
              cfg.REGIME_MA_WINDOW, 60)


# ---------------------------------------------------------------------------
# Variant A -- S/R-Flip Retest
# ---------------------------------------------------------------------------
def generate_variant_a(ticker: str, ohlcv: pd.DataFrame, ix: dict, parabolic_on: bool) -> list[TradeSetup]:
    c, h, lo, v = ohlcv["close"], ohlcv["high"], ohlcv["low"], ohlcv["volume"]
    atr_s, vma, swing_hi, swing_lo = ix["atr"], ix["vol_ma"], ix["swing_hi"], ix["swing_lo"]
    dates = ohlcv.index
    n = len(dates)
    setups: list[TradeSetup] = []
    pending = None                       # {"level":..., "pos":...}
    cache_key = None
    cache_zones: list[tuple[float, int]] = []
    start = _warmup()
    for i in range(start, n):
        a = atr_s.iloc[i]
        if np.isnan(a) or a <= 0:
            continue
        ci, cprev, vi, vmi = c.iloc[i], c.iloc[i - 1], v.iloc[i], vma.iloc[i]
        lo_bound = max(0, i - cfg.A_SWING_LOOKBACK_DAYS)
        conf = _confirmed(swing_hi, i, cfg.A_FIND_PEAKS_DISTANCE, lo_bound)
        key = (int(conf[0]), int(conf[-1]), len(conf)) if len(conf) else (i, i, 0)
        if key != cache_key:
            prices = h.iloc[conf].to_numpy(dtype=float) if len(conf) else np.array([])
            cache_zones = ind.sr_zones(prices, cfg.A_CLUSTER_MERGE_ATR_MULT * a, cfg.A_MIN_TOUCHES)
            cache_key = key
        zones = cache_zones
        thr = cfg.A_BREAKOUT_BUFFER_PCT
        if pending is None:
            for level, _touch in zones:
                trig = level * (1.0 + thr)
                if ci > trig and cprev <= trig and not np.isnan(vmi) and vi >= cfg.VOLUME_CONFIRM_MULT * vmi:
                    pending = {"level": level, "pos": i}
                    break
        else:
            level = pending["level"]
            if i - pending["pos"] > cfg.A_RETEST_WINDOW_BARS:
                pending = None
            else:
                tol = cfg.A_RETEST_TOL_ATR_MULT * a
                if abs(ci - level) <= tol and ci >= level and lo.iloc[i] <= level + tol:
                    if not (parabolic_on and _parabolic_block(ci, ix, i, lo, swing_lo)):
                        setups.append(TradeSetup(
                            ticker, "A_sr_flip_retest", parabolic_on,
                            dates[i].strftime("%Y-%m-%d"),
                            float(level - cfg.A_STOP_ATR_MULT * a), float(level),
                            cfg.A_TRAIL_DONCHIAN_N))
                    pending = None
    return setups


# ---------------------------------------------------------------------------
# Variant B -- Consolidation Breakout
# ---------------------------------------------------------------------------
def generate_variant_b(ticker: str, ohlcv: pd.DataFrame, ix: dict, parabolic_on: bool) -> list[TradeSetup]:
    c, h, lo, v = ohlcv["close"], ohlcv["high"], ohlcv["low"], ohlcv["volume"]
    atr_s, vma, adx_s, bbw, nr7s = ix["atr"], ix["vol_ma"], ix["adx"], ix["bbw"], ix["nr7"]
    swing_hi, swing_lo = ix["swing_hi"], ix["swing_lo"]
    box_up = h.rolling(cfg.B_BOX_WINDOW, min_periods=cfg.B_BOX_WINDOW).max().shift(1)
    box_lo = lo.rolling(cfg.B_BOX_WINDOW, min_periods=cfg.B_BOX_WINDOW).min().shift(1)
    bbw_q = bbw.rolling(cfg.B_BBW_LOOKBACK_DAYS, min_periods=cfg.B_BBW_LOOKBACK_DAYS).quantile(cfg.B_BBW_LOW_PCTILE)
    consol = (bbw <= bbw_q)
    if cfg.B_USE_NR7:
        consol = consol | nr7s
    dates = ohlcv.index
    n = len(dates)
    setups: list[TradeSetup] = []
    start = _warmup()
    for i in range(start, n):
        a = atr_s.iloc[i]
        if np.isnan(a) or a <= 0:
            continue
        bu, bl = box_up.iloc[i], box_lo.iloc[i]
        if np.isnan(bu) or np.isnan(bl):
            continue
        ci, cprev, vi, vmi, adxi = c.iloc[i], c.iloc[i - 1], v.iloc[i], vma.iloc[i], adx_s.iloc[i]
        fresh = ci > bu and cprev <= box_up.iloc[i - 1]
        had_consol = bool(consol.iloc[max(0, i - cfg.B_BOX_WINDOW):i].any())
        vol_ok = (not np.isnan(vmi)) and vi >= cfg.VOLUME_CONFIRM_MULT * vmi
        adx_ok = (not np.isnan(adxi)) and (adxi > cfg.B_ADX_MIN or adxi > adx_s.iloc[i - 1])
        if fresh and had_consol and vol_ok and adx_ok and _hh_hl_ok(h, lo, swing_hi, swing_lo, i):
            if not (parabolic_on and _parabolic_block(ci, ix, i, lo, swing_lo)):
                setups.append(TradeSetup(
                    ticker, "B_consolidation_breakout", parabolic_on,
                    dates[i].strftime("%Y-%m-%d"), float(bl), float(bu),
                    cfg.B_TRAIL_DONCHIAN_N))
    return setups


# ---------------------------------------------------------------------------
# Variant C -- Trend-start Donchian + retest
# ---------------------------------------------------------------------------
def generate_variant_c(ticker: str, ohlcv: pd.DataFrame, ix: dict, parabolic_on: bool) -> list[TradeSetup]:
    c, h, lo = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    atr_s, adx_s, dup, ema_c = ix["atr"], ix["adx"], ix["donch_up"], ix["ema_c"]
    swing_hi, swing_lo = ix["swing_hi"], ix["swing_lo"]
    dates = ohlcv.index
    n = len(dates)
    setups: list[TradeSetup] = []
    pending = None
    start = _warmup()
    for i in range(start, n):
        a = atr_s.iloc[i]
        if np.isnan(a) or a <= 0:
            continue
        ci, cprev = c.iloc[i], c.iloc[i - 1]
        if pending is None:
            du, dup_prev = dup.iloc[i], dup.iloc[i - 1]
            adxi = adx_s.iloc[i]
            if np.isnan(du) or np.isnan(dup_prev):
                continue
            fresh = ci > du and cprev <= dup_prev
            adx_ok = (not np.isnan(adxi)) and adxi > cfg.C_ADX_MIN
            if fresh and adx_ok and _hh_hl_ok(h, lo, swing_hi, swing_lo, i):
                pending = {"level": float(du), "pos": i}
        else:
            level = pending["level"]
            if i - pending["pos"] > cfg.C_RETEST_WINDOW_BARS:
                pending = None
            else:
                ema_lvl = ema_c.iloc[i]
                ref = level if np.isnan(ema_lvl) else max(level, float(ema_lvl))
                tol = cfg.C_RETEST_TOL_ATR_MULT * a
                if abs(ci - ref) <= tol and ci >= ref and lo.iloc[i] <= ref + tol:
                    if not (parabolic_on and _parabolic_block(ci, ix, i, lo, swing_lo)):
                        setups.append(TradeSetup(
                            ticker, "C_donchian_retest", parabolic_on,
                            dates[i].strftime("%Y-%m-%d"),
                            float(ref - cfg.C_STOP_ATR_MULT * a), float(ref),
                            cfg.C_TRAIL_DONCHIAN_N))
                    pending = None
    return setups


_DISPATCH = {
    "A_sr_flip_retest": generate_variant_a,
    "B_consolidation_breakout": generate_variant_b,
    "C_donchian_retest": generate_variant_c,
}


def generate_signals(variant: str, ticker: str, ohlcv: pd.DataFrame, parabolic_on: bool) -> list[TradeSetup]:
    """Generate trade setups for one variant on one ticker's OHLCV frame."""
    if variant not in _DISPATCH:
        raise ValueError(f"unknown variant: {variant}")
    if len(ohlcv) <= _warmup() + 2:
        return []
    ix = compute_indicators(ohlcv)
    return _DISPATCH[variant](ticker, ohlcv, ix, parabolic_on)
