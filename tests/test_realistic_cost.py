"""Behavior tests for the D-204/D-207 realistic per-stock cost model. Synthetic, no network.

Verifies: Roll (1984) close-only spread (bid-ask bounce -> positive; no bounce ->
floored to 0), Kyle (1985) sqrt-impact scaling (sqrt(order/adv), lambda-linear, thin
adv -> nan), the D-207 re-scaled tier half-spread monotonicity, and the D-207 round-trip
combine rule (FIX-1: every spread source contributes a ONE-WAY HALF-spread, doubled for
the round trip -> round_trip = 2*(one_way + impact)+commission; FIX-2 source hierarchy
quoted -> roll -> tier; tier fallback when Roll is 0/undefined).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import realistic_cost as rc
from src.signals import thresholds as th


# ---------------------------------------------------------------------------
# Roll (1984) effective spread -- bid-ask bounce vs no-bounce
# ---------------------------------------------------------------------------
def test_roll_spread_positive_on_bidask_bounce():
    # Flat efficient price + deterministic buy/sell bounce -> negative serial cov in
    # observed price changes -> Roll recovers a POSITIVE spread.
    h = 0.01
    q = np.array([(-1) ** i for i in range(60)], dtype=float)
    close = pd.Series(100.0 * np.exp(q * h), index=pd.bdate_range("2020-01-01", periods=60))
    spread = rc.roll_effective_spread(close, window=21).dropna()
    assert len(spread) > 0
    assert spread.iloc[-1] > 0


def test_roll_spread_floored_to_zero_when_no_bounce():
    # Constant log-return (pure trend) -> serial cov of price changes is ~0 (not
    # negative) -> max(-cov,0) truncation floors the estimator to exactly 0.
    close = pd.Series(100.0 * (1.01 ** np.arange(60)),
                      index=pd.bdate_range("2020-01-01", periods=60))
    spread = rc.roll_effective_spread(close, window=21).dropna()
    assert len(spread) > 0
    assert spread.iloc[-1] == pytest.approx(0.0, abs=1e-8)   # floored (fp noise only)


def test_roll_panel_matches_per_series():
    # The vectorized panel estimand must equal the per-series estimator column-wise.
    idx = pd.bdate_range("2020-01-01", periods=80)
    rng = np.random.default_rng(0)
    a = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, 80))), index=idx)
    h = 0.008
    q = np.array([(-1) ** i for i in range(80)], dtype=float)
    b = pd.Series(50.0 * np.exp(q * h), index=idx)
    panel = pd.DataFrame({"A": a, "B": b})
    pan = rc.roll_spread_panel(panel, window=21)
    sa = rc.roll_effective_spread(a, window=21)
    sb = rc.roll_effective_spread(b, window=21)
    assert pan["A"].iloc[-1] == pytest.approx(sa.iloc[-1], rel=1e-9, abs=1e-12)
    assert pan["B"].iloc[-1] == pytest.approx(sb.iloc[-1], rel=1e-9, abs=1e-12)


# ---------------------------------------------------------------------------
# Kyle (1985) square-root impact
# ---------------------------------------------------------------------------
def _vol_series(sigma: float = 0.02, n: int = 60) -> pd.Series:
    # Deterministic alternating log-returns -> known daily sigma ~= sigma.
    q = np.array([(-1) ** i for i in range(n)], dtype=float)
    return pd.Series(100.0 * np.exp(np.cumsum(q * sigma)),
                     index=pd.bdate_range("2020-01-01", periods=n))


def test_kyle_impact_negligible_for_small_order():
    close = _vol_series()
    impact = rc.kyle_impact(close, order_value=20_000.0, adv=5_000_000_000.0,
                            window=21, lambda_kyle=1.0)
    assert np.isfinite(impact)
    assert 0 <= impact < 1e-3                          # ~20K vs 5B ADV -> tiny


def test_kyle_impact_sqrt_scaling_in_order_value():
    close = _vol_series()
    i1 = rc.kyle_impact(close, order_value=20_000.0, adv=1_000_000.0, window=21, lambda_kyle=1.0)
    i4 = rc.kyle_impact(close, order_value=80_000.0, adv=1_000_000.0, window=21, lambda_kyle=1.0)
    assert i4 == pytest.approx(2.0 * i1, rel=1e-9)      # 4x order -> sqrt(4)=2x impact


def test_kyle_impact_linear_in_lambda():
    close = _vol_series()
    i1 = rc.kyle_impact(close, order_value=20_000.0, adv=1_000_000.0, window=21, lambda_kyle=1.0)
    i2 = rc.kyle_impact(close, order_value=20_000.0, adv=1_000_000.0, window=21, lambda_kyle=2.0)
    assert i2 == pytest.approx(2.0 * i1, rel=1e-9)


def test_kyle_impact_nan_when_adv_nonpositive():
    close = _vol_series()
    assert np.isnan(rc.kyle_impact(close, 20_000.0, adv=0.0))
    assert np.isnan(rc.kyle_impact(close, 20_000.0, adv=float("nan")))


# ---------------------------------------------------------------------------
# D-207 re-scaled tier half-spread floor (last-resort fallback)
# ---------------------------------------------------------------------------
def test_tier_spread_floor_monotone_mega_to_micro():
    mega = rc.tier_spread_floor(th.D207_TIER_MEGA_ADV_TL + 1)
    large = rc.tier_spread_floor(th.D207_TIER_LARGE_ADV_TL + 1)
    mid = rc.tier_spread_floor(th.D207_TIER_MID_ADV_TL + 1)
    micro = rc.tier_spread_floor(th.D207_TIER_MID_ADV_TL - 1)
    assert mega < large < mid < micro
    assert mega == pytest.approx(th.D207_TIER_MEGA_HALF_SPREAD)
    assert micro == pytest.approx(th.D207_TIER_MICRO_HALF_SPREAD)


def test_tier_spread_floor_nonpositive_adv_is_micro():
    assert rc.tier_spread_floor(0.0) == pytest.approx(th.D207_TIER_MICRO_HALF_SPREAD)
    assert rc.tier_spread_floor(float("nan")) == pytest.approx(th.D207_TIER_MICRO_HALF_SPREAD)


# ---------------------------------------------------------------------------
# D-207 round-trip combine rule (FIX-1 half-spread + FIX-2 source hierarchy)
# ---------------------------------------------------------------------------
def test_combine_round_trip_roll_leg_is_half_spread():
    # FIX-1: no quoted -> Roll leg one_way = roll_full/2 (NOT the full S). round_trip
    # spread cost = S, not 2S. spread_source="roll".
    d = rc.combine_round_trip(roll_spread=0.01, kyle_impact_val=0.002,
                              tier_spread=0.005, commission=0.0)
    assert d["spread_source"] == "roll"
    assert d["round_trip_roll"] == pytest.approx(2.0 * (0.01 / 2.0 + 0.002))
    assert d["round_trip_tier"] == pytest.approx(2.0 * (0.005 + 0.002))
    assert d["roll_is_zero"] is False


def test_combine_round_trip_quoted_is_primary_over_roll():
    # FIX-2: a valid quoted spread WINS over Roll; one_way = quoted_full/2.
    d = rc.combine_round_trip(roll_spread=0.01, kyle_impact_val=0.002,
                              tier_spread=0.005, commission=0.0, quoted_spread=0.0011)
    assert d["spread_source"] == "quoted"
    assert d["quoted_spread"] == pytest.approx(0.0011)
    assert d["round_trip_roll"] == pytest.approx(2.0 * (0.0011 / 2.0 + 0.002))
    assert d["roll_is_zero"] is False


def test_combine_round_trip_falls_back_to_tier_when_roll_zero():
    # No quoted + Roll undefined/0 (serial cov >= 0) -> tier floor (already a HALF) + flag.
    d = rc.combine_round_trip(roll_spread=0.0, kyle_impact_val=0.002,
                              tier_spread=0.005, commission=0.0)
    assert d["spread_source"] == "tier"
    assert d["roll_is_zero"] is True
    assert d["round_trip_roll"] == pytest.approx(2.0 * (0.005 + 0.002))
    assert d["roll_spread"] == pytest.approx(0.0) or d["roll_spread"] is None


def test_combine_round_trip_impact_falls_back_to_tier_when_undefined():
    d = rc.combine_round_trip(roll_spread=0.01, kyle_impact_val=float("nan"),
                              tier_spread=0.005, commission=0.0)
    # impact undefined -> impact_eff = tier floor (0.005); roll leg one_way = 0.01/2.
    assert d["round_trip_roll"] == pytest.approx(2.0 * (0.01 / 2.0 + 0.005))
    assert d["kyle_impact"] is None


def test_round_trip_cost_end_to_end_keys():
    close = _vol_series()
    out = rc.round_trip_cost(close, adv=1_000_000.0, order_value=20_000.0,
                             window=21, lambda_kyle=1.0)
    for k in ("roll_spread", "quoted_spread", "kyle_impact", "tier_spread",
              "spread_source", "roll_is_zero", "round_trip_roll", "round_trip_tier"):
        assert k in out
    assert out["round_trip_tier"] > 0


def test_round_trip_cost_quoted_injection_lowers_spread_leg():
    # Injecting a tight observed quoted spread routes through the quoted leg and yields
    # a lower round-trip than the (vol-inflated) Roll leg would.
    close = _vol_series(sigma=0.03)
    no_q = rc.round_trip_cost(close, adv=1_000_000.0, order_value=20_000.0,
                              window=21, lambda_kyle=1.0)
    with_q = rc.round_trip_cost(close, adv=1_000_000.0, order_value=20_000.0,
                                window=21, lambda_kyle=1.0, quoted_spread=0.0011)
    assert with_q["spread_source"] == "quoted"
    assert with_q["round_trip_roll"] < no_q["round_trip_roll"]
