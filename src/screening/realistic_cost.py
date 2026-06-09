"""D-204/D-207 realistic per-stock transaction-cost model (PORT, committed, offline).

D-203 gate-5 used a FLAT 20/100bp per-turnover cost. D-204 stress-tests the hi52
edge under a REALISTIC per-stock round-trip cost: a close-only effective spread
(Roll 1984) plus a square-root market-impact term (Kyle 1985), with an empirical
liquidity-tier half-spread floor (RR-015) as a model-independent CROSS-CHECK.

D-207 RE-CALIBRATION (NRR-010 diagnosed the model as SISIK / inflated ~12-25x on
liquid names): FIX-1 corrects a unit double-count (round-trip spread cost = S, not 2S
-- every source now contributes a one-way HALF-spread, doubled for the round trip);
FIX-2 prefers the EOD OBSERVED quoted spread (vol-robust) over the vol-biased 21-day
Roll, falling back to a longer-window Roll then the tier floor; FIX-3 re-scales the
tier ADV boundaries + half-spreads to BIST reality (edge-blind, anchored to observed
quoted spreads). All anchored to OBSERVED reality, NOT to any edge outcome
(calibration = optimization-risk; frozen edge-blind at docs/yol1/D207_CALIBRATION.json).

PORT, not import (Strangler): the Kyle impact + round-trip structure are ported
from the ballast-bist lab (`ballast.costs.transaction_cost_v2`, D-193) which is NOT
on PyPI -- importing it would break CI (cf. the openpyxl CI failure). The frozen
D-202 panel is CLOSE-ONLY (no high/low), so the Abdi-Ranaldo (2017) OHLC spread
cannot run; Roll (1984) is its close-only analogue and is used instead. HTTP-free.

Citations:
  Roll, R. (1984). "A Simple Implicit Measure of the Effective Bid-Ask Spread in
    an Efficient Market." Journal of Finance, 39(4), 1127-1139.
  Abdi, F. & Ranaldo, A. (2017). "A Simple Estimation of Bid-Ask Spreads from Daily
    Close, High, and Low Prices." RFS 30(12), 4437-4480 (the OHLC analogue Roll
    substitutes for here).
  Kyle, A.S. (1985). "Continuous Auctions and Insider Trading." Econometrica, 53(6),
    1315-1335; Almgren et al. (2005) Risk 18(7) (square-root impact).
  Internal cost-research note sec.3.1 -- empirical BIST liquidity-tier
    half-spreads (mega/large/mid/micro) used as the tier cross-check.

All decision/tier constants live in src/signals/thresholds.py (D204_* historical +
D207_* live re-calibrated block, single source per PROJECT_GUIDE.md). This module holds only
the cost MECHANICS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.signals import thresholds as _th


def roll_effective_spread(
    close: pd.Series, window: int = _th.D204_ROLL_WINDOW,
) -> pd.Series:
    """Roll (1984) close-only rolling effective spread (proportional, in fraction).

    spread_t = 2 * sqrt(max(-cov(dp_t, dp_{t-1}), 0)), where dp = diff of log(close)
    over a trailing `window`. Roll's autocovariance argument: a positive bid-ask
    spread induces NEGATIVE serial covariance in observed price changes; the
    magnitude recovers the spread. When the sample serial covariance is >= 0 (an
    efficient/illiquid-noise regime), the estimator is undefined and floored to 0
    -- exactly the max(-cov, 0) truncation of the Abdi-Ranaldo (2017) close-only
    analogue. The first `window` rows are NaN (rolling warm-up).

    Returns a fraction (0.01 = 1%). Higher = wider spread = costlier to cross.
    """
    p = np.log(close.astype(float))
    dp = p.diff()
    cov = dp.rolling(window).cov(dp.shift(1))
    return 2.0 * np.sqrt(np.clip(-cov, 0.0, None))


def roll_spread_panel(
    close: pd.DataFrame, window: int = _th.D204_ROLL_WINDOW,
) -> pd.DataFrame:
    """Vectorized Roll(1984) spread for every column of a [date x symbol] close panel.

    Same estimand as `roll_effective_spread` (sample serial covariance, ddof=1, floored
    at 0), computed column-wise via rolling sums so the harness can asof-index it at
    rebalance dates without a per-name Python loop. Returns a [date x symbol] fraction
    panel (NaN during the rolling warm-up)."""
    p = np.log(close.astype(float))
    dp = p.diff()
    dp1 = dp.shift(1)
    n = window
    sxy = (dp * dp1).rolling(n).sum()
    sx = dp.rolling(n).sum()
    sy = dp1.rolling(n).sum()
    cov = (sxy - sx * sy / n) / (n - 1)
    return 2.0 * np.sqrt(np.clip(-cov, 0.0, None))


def combine_round_trip(
    roll_spread: float, kyle_impact_val: float, tier_spread: float,
    commission: float = None, quoted_spread: float = None,
) -> dict:
    """Combine an observed/estimated spread + Kyle impact + tier floor into the round-trip
    cost dict (D-207 re-calibrated). Pure (no rolling math) so both `round_trip_cost` and
    the harness per-stock panel share ONE combine rule.

    D-207 FIX-1 (unit double-count): EVERY spread source contributes a ONE-WAY HALF-spread,
    then doubles for the round trip -- matching the already-correct tier convention. The
    pre-D207 code used the FULL Roll spread S as the one-way leg (-> 2S), double-counting
    the round-trip spread cost (you pay S/2 at the ask on entry + S/2 at the bid on exit = S,
    not 2S). The tier leg was already correct; only the Roll/quoted leg needed the /2.

    D-207 FIX-2 (vol-robust spread, source hierarchy per name):
      quoted (EOD observed, vol-robust)  -> one_way = quoted_spread / 2   spread_source="quoted"
      elif roll (longer-window estimate) -> one_way = roll_spread   / 2   spread_source="roll"
      else  (no observed/estimable)      -> one_way = tier_spread (a HALF) spread_source="tier"
    `quoted_spread`/`roll_spread` are PROPORTIONAL FULL spreads (so /2 = one-way half);
    `tier_spread` is already a half-spread. Impact falls back to the tier floor when undefined
    (thin name, adv<=0). round_trip = 2*(one_way + impact) + commission; commission defaults to
    the frozen Midas D204_COMMISSION_PCT.

    Compat: `round_trip_roll` (now "primary observed-spread leg"), `roll_is_zero` (now "fell all
    the way back to the tier floor") and `round_trip_tier` (tier cross-check) keys are KEPT so
    the d205/nrr007/nrr008/d206 callers don't ripple; `spread_source` is the new accounting tag."""
    if commission is None:
        commission = _th.D204_COMMISSION_PCT
    quoted_valid = (quoted_spread is not None and np.isfinite(quoted_spread)
                    and quoted_spread > 0)
    roll_valid = np.isfinite(roll_spread) and roll_spread > 0
    impact_eff = kyle_impact_val if np.isfinite(kyle_impact_val) else tier_spread
    if quoted_valid:
        one_way, spread_source = quoted_spread / 2.0, "quoted"
    elif roll_valid:
        one_way, spread_source = roll_spread / 2.0, "roll"
    else:
        one_way, spread_source = tier_spread, "tier"
    return {
        "roll_spread": float(roll_spread) if np.isfinite(roll_spread) else None,
        "quoted_spread": float(quoted_spread) if quoted_valid else None,
        "kyle_impact": float(kyle_impact_val) if np.isfinite(kyle_impact_val) else None,
        "tier_spread": float(tier_spread),
        "spread_source": spread_source,
        "roll_is_zero": bool(spread_source == "tier"),
        "round_trip_roll": float(2.0 * (one_way + impact_eff) + commission),
        "round_trip_tier": float(2.0 * (tier_spread + impact_eff) + commission),
    }


def kyle_impact(
    close: pd.Series, order_value: float, adv: float,
    window: int = _th.D204_ROLL_WINDOW, lambda_kyle: float = _th.D204_LAMBDA_KYLE,
) -> float:
    """One-way Kyle (1985) square-root market impact (fraction). PORT of ballast
    `transaction_cost_v2.kyle_impact` (close_to_close sigma path, bit-for-bit).

    sigma_daily = std(log(close_t / close_{t-1})) over the last `window` days
    impact      = lambda_kyle * sigma_daily * sqrt(order_value / adv)

    For a ~20K-TL order against a multi-million-TL ADV the impact is negligible
    (sqrt(order/ADV) << 1); for thin illiquid names it grows. lambda_kyle is FROZEN
    (calibration = optimization, forbidden in D-204). adv <= 0 / non-finite sigma
    -> NaN (caller falls back to the tier floor).
    """
    if not np.isfinite(adv) or adv <= 0:
        return float("nan")
    log_ret = np.log(close.astype(float) / close.astype(float).shift(1)).dropna()
    if len(log_ret) == 0:
        return float("nan")
    sigma_daily = float(log_ret.iloc[-window:].std())
    if not np.isfinite(sigma_daily):
        return float("nan")
    return float(lambda_kyle * sigma_daily * np.sqrt(order_value / adv))


def tier_spread_floor(value_tl_adv: float) -> float:
    """BIST liquidity-tier ONE-WAY half-spread (fraction) -- the LAST-RESORT floor when no
    quoted spread and no fallback Roll are available (D-207 re-scaled, D207_TIER_* block).

    Maps a trailing TL ADV to the observed half-spread of its liquidity tier
    (mega/large/mid/micro). D-207 re-derived the ladder EDGE-BLIND from observed quoted
    spreads bucketed by the BIST ADV distribution: the EOD quoted full spread is ~flat
    ~11bp across the whole spectrum (micro is NOT wider on the quoted dimension -- its extra
    cost is Kyle IMPACT), so the ladder is nearly flat by design, within the observed
    [10.6,13.4]bp full envelope. The pre-D207 D204_TIER_* ladder had unreachable ADV
    boundaries (MEGA>=2e9 TL) AND ~4-6x inflated half-spreads. Monotone mega < large < mid <
    micro (architecture invariant). Boundaries + values are frozen in thresholds.py."""
    if not np.isfinite(value_tl_adv) or value_tl_adv <= 0:
        return _th.D207_TIER_MICRO_HALF_SPREAD
    if value_tl_adv >= _th.D207_TIER_MEGA_ADV_TL:
        return _th.D207_TIER_MEGA_HALF_SPREAD
    if value_tl_adv >= _th.D207_TIER_LARGE_ADV_TL:
        return _th.D207_TIER_LARGE_HALF_SPREAD
    if value_tl_adv >= _th.D207_TIER_MID_ADV_TL:
        return _th.D207_TIER_MID_HALF_SPREAD
    return _th.D207_TIER_MICRO_HALF_SPREAD


def round_trip_cost(
    close: pd.Series, adv: float, order_value: float,
    window: int = _th.D204_ROLL_WINDOW, lambda_kyle: float = _th.D204_LAMBDA_KYLE,
    quoted_spread: float = None,
) -> dict:
    """Per-stock round-trip cost (fraction): observed/estimated spread + shared Kyle impact.

    round_trip = 2 * (one_way_spread + one_way_impact) + commission (Midas = 0). D-207
    spread source hierarchy (combine_round_trip): a passed-in `quoted_spread` (EOD observed,
    vol-robust, the FULL proportional spread) is preferred; else the latest Roll spread; else
    the re-scaled tier half-spread floor (`roll_is_zero=True`). The `spread_source` tag records
    which leg fired. Impact (Kyle) is shared. commission is D204_COMMISSION_PCT (0.0).
    """
    spread_series = roll_effective_spread(close, window).dropna()
    roll = float(spread_series.iloc[-1]) if len(spread_series) else float("nan")
    tier = tier_spread_floor(adv)
    impact = kyle_impact(close, order_value, adv, window, lambda_kyle)
    return combine_round_trip(roll, impact, tier, quoted_spread=quoted_spread)
