"""D-187 -- portfolio simulation: static barbell + regime switcher + metrics.

All inputs are DAILY price/index series aligned on a common DatetimeIndex.
TLREF must be passed as a compound-growth index (not raw rate) -- exposure_data
guarantees this. All series are rebased to 1.0 at the start of each analysis
window, so results are relative (not absolute TL amounts).

Look-ahead guard: regime signal computed at t-close -> position effective t+1.
Cost applied on rebalance/switch events (not daily).
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening.exposure_config import (
    INFLATION_REGIMES,
    REBALANCE_COST_BPS,
    REBALANCE_FREQ,
    REGIME_MA_WINDOW,
    SWITCH_COST_BPS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _align(*series: pd.Series) -> list[pd.Series]:
    """Align series to a common index (intersection, ffill) with a JOINT mask.

    All returned series share the SAME cleaned index -> equal length (positional
    .iloc[i] is safe). A joint dropna drops any date where ANY series is NaN,
    so series with different EVDS coverage (e.g. TLREF starts 2022-07) restrict
    the common window correctly instead of producing mismatched lengths.
    """
    idx = series[0].index
    for s in series[1:]:
        idx = idx.intersection(s.index)
    aligned = [s.reindex(idx).ffill() for s in series]
    mask = aligned[0].notna()
    for a in aligned[1:]:
        mask &= a.notna()
    return [a[mask] for a in aligned]


def _rebase(s: pd.Series) -> pd.Series:
    """Rebase series to 1.0 at first valid observation."""
    first = s.dropna().iloc[0] if len(s.dropna()) else 1.0
    return s / first


def _rebalance_dates(idx: pd.DatetimeIndex, freq: str) -> set:
    """Monthly or quarterly rebalance dates (first trading day of each period)."""
    s = pd.Series(0, index=idx)
    if freq == "monthly":
        resampled = s.resample("MS").first()
    else:
        resampled = s.resample("QS").first()
    return set(resampled.index.intersection(idx))


# ---------------------------------------------------------------------------
# Static barbell (S-A)
# ---------------------------------------------------------------------------
def build_static_barbell(
    xu100: pd.Series,
    tlref: pd.Series,
    equity_ratio: float,
    rebalance_freq: str = REBALANCE_FREQ,
    cost_bps: float = REBALANCE_COST_BPS,
) -> dict:
    """Simulate a static equity/TLREF barbell with periodic rebalance.

    equity_ratio in [0,1]; TLREF fraction = 1 - equity_ratio.
    Cost applied on the drift magnitude at rebalance dates.
    Returns daily portfolio value series starting at 1.0.
    """
    xu, tl = _align(xu100, tlref)
    xu, tl = _rebase(xu), _rebase(tl)
    idx = xu.index
    rebal_dates = _rebalance_dates(idx, rebalance_freq)
    cost_frac = cost_bps / 10_000.0

    eq_w = equity_ratio
    bond_w = 1.0 - equity_ratio
    eq_val = eq_w        # notional in equity
    bond_val = bond_w    # notional in TLREF

    prev_eq = xu.iloc[0]
    prev_tl = tl.iloc[0]
    portfolio = np.empty(len(idx), dtype=float)
    total_cost = 0.0
    n_rebal = 0

    for i, d in enumerate(idx):
        # mark-to-market
        if i > 0:
            eq_val *= xu.iloc[i] / prev_eq
            bond_val *= tl.iloc[i] / prev_tl
        prev_eq = xu.iloc[i]
        prev_tl = tl.iloc[i]
        pv = eq_val + bond_val
        # rebalance
        if d in rebal_dates and pv > 0:
            target_eq = equity_ratio * pv
            drift = abs(eq_val - target_eq)
            cost = drift * cost_frac
            total_cost += cost
            pv -= cost
            eq_val = equity_ratio * pv
            bond_val = (1.0 - equity_ratio) * pv
            n_rebal += 1
        portfolio[i] = eq_val + bond_val

    port = pd.Series(portfolio, index=idx, name=f"barbell_{int(equity_ratio*100)}")
    dd = _max_drawdown(port)
    return {"portfolio": port, "total_cost": round(total_cost, 6),
            "n_rebalances": n_rebal, "equity_ratio": equity_ratio,
            "max_drawdown": round(dd, 4)}


# ---------------------------------------------------------------------------
# Regime switcher (S-B)
# ---------------------------------------------------------------------------
def _regime_signal(xu100: pd.Series, ma_window: int = REGIME_MA_WINDOW) -> pd.Series:
    """1=equity, 0=TLREF. Signal at t (t-close), position effective t+1."""
    ma = xu100.rolling(ma_window, min_periods=ma_window).mean()
    above = xu100 > ma
    rising = ma.diff() > 0
    signal = (above & rising).astype(int)
    signal.iloc[:ma_window] = 0   # no signal during warm-up
    return signal


def build_regime_switcher(
    xu100: pd.Series,
    tlref: pd.Series,
    cost_bps: float = SWITCH_COST_BPS,
    ma_window: int = REGIME_MA_WINDOW,
) -> dict:
    """Equity<->TLREF regime switcher. Look-ahead guard: t-signal -> t+1 position."""
    xu, tl = _align(xu100, tlref)
    xu, tl = _rebase(xu), _rebase(tl)
    idx = xu.index
    signal = _regime_signal(xu, ma_window)
    # shift by 1: signal at t -> position at t+1
    pos = signal.shift(1).fillna(0).astype(int)
    cost_frac = cost_bps / 10_000.0

    portfolio = np.empty(len(idx), dtype=float)
    portfolio[0] = 1.0
    val = 1.0
    prev_pos = int(pos.iloc[0])
    prev_xu = xu.iloc[0]
    prev_tl = tl.iloc[0]
    n_switches = 0
    total_cost = 0.0

    for i in range(1, len(idx)):
        cur_pos = int(pos.iloc[i])
        if cur_pos == 1:
            val *= xu.iloc[i] / prev_xu
        else:
            val *= tl.iloc[i] / prev_tl
        if cur_pos != prev_pos:   # switch event
            val -= val * cost_frac
            n_switches += 1
            total_cost += val * cost_frac  # approx; already deducted above
        prev_xu = xu.iloc[i]
        prev_tl = tl.iloc[i]
        prev_pos = cur_pos
        portfolio[i] = val

    port = pd.Series(portfolio, index=idx, name="regime_switcher")
    dd = _max_drawdown(port)
    return {"portfolio": port, "total_cost": round(total_cost, 6),
            "n_switches": n_switches, "max_drawdown": round(dd, 4)}


# ---------------------------------------------------------------------------
# Benchmark portfolios (rebase series for comparison)
# ---------------------------------------------------------------------------
def build_benchmarks(xu100: pd.Series, tlref: pd.Series,
                     tufe: pd.Series, gold: pd.Series | None) -> dict[str, pd.Series]:
    xu, tl, tu = _align(xu100, tlref, tufe)
    xu, tl, tu = _rebase(xu), _rebase(tl), _rebase(tu)
    # B2: 50/50 barbell (rebalanced monthly) -- just reuse build_static_barbell
    b2_res = build_static_barbell(xu100, tlref, 0.50, "monthly", REBALANCE_COST_BPS)
    out: dict[str, pd.Series] = {
        "B1_TLREF": tl, "B2_BARBELL": _rebase(b2_res["portfolio"]),
        "B3_XU100": xu, "B5_TUFE": tu,
    }
    if gold is not None:
        aligned_gold = gold.reindex(xu.index).ffill().dropna()
        out["B4_GOLD_DIAG"] = _rebase(aligned_gold)
    return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _max_drawdown(port: pd.Series) -> float:
    eq = port.to_numpy(float)
    peak = np.maximum.accumulate(eq)
    dd = np.where(peak > 0, (peak - eq) / peak, 0.0)
    return float(dd.max())


def compute_metrics(
    port: pd.Series, tufe: pd.Series, start: str, end: str,
) -> dict:
    """Nominal + real return metrics for a portfolio series."""
    p = port.reindex(port.index[(port.index >= start) & (port.index <= end)]).dropna()
    if len(p) < 2:
        nan = float("nan")
        return {"n_days": 0, "total_nominal": nan, "total_real": nan,
                "annual_nominal": nan, "annual_real": nan, "max_drawdown": nan}
    years = len(p) / 252.0
    total_nom = float(p.iloc[-1] / p.iloc[0] - 1.0)
    ann_nom = float((p.iloc[-1] / p.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else float("nan")
    # real deflation
    tl_s = tufe.reindex(p.index).ffill()
    if tl_s.dropna().empty or float(tl_s.dropna().iloc[0]) == 0:
        total_real = ann_real = float("nan")
    else:
        tufe_ratio = float(tl_s.iloc[-1]) / float(tl_s.dropna().iloc[0])
        total_real = float((1.0 + total_nom) / tufe_ratio - 1.0)
        ann_real = float((1.0 + total_real) ** (1.0 / years) - 1.0) if years > 0 else float("nan")
    dd = _max_drawdown(p)
    return {"n_days": len(p), "total_nominal": round(total_nom, 4),
            "total_real": round(total_real, 4) if np.isfinite(total_real) else float("nan"),
            "annual_nominal": round(ann_nom, 4) if np.isfinite(ann_nom) else float("nan"),
            "annual_real": round(ann_real, 4) if np.isfinite(ann_real) else float("nan"),
            "max_drawdown": round(dd, 4)}


def compute_all_metrics(
    portfolios: dict[str, pd.Series], tufe: pd.Series,
    start: str, end: str,
) -> dict[str, dict]:
    return {name: compute_metrics(p, tufe, start, end) for name, p in portfolios.items()}


def slice_metrics(
    portfolios: dict[str, pd.Series], tufe: pd.Series,
) -> dict[str, dict[str, dict]]:
    """Metrics per inflation regime slice."""
    out: dict[str, dict[str, dict]] = {}
    for label, lo, hi in INFLATION_REGIMES:
        out[label] = compute_all_metrics(portfolios, tufe, lo, hi)
    return out
