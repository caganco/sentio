"""D-207 cost RE-CALIBRATION behavior tests. Synthetic, no network, CI-safe.

Covers the three D-207 fixes + the harness quoted injection + the fidelity-band shape:
  FIX-1  round-trip spread cost = S (one-way HALF-spread doubled), not 2S.
  FIX-2  source hierarchy quoted -> long-Roll -> tier, exercised through
         per_stock_cost_panel with an INJECTED synthetic quoted panel (no archive).
  FIX-3  re-scaled D207 tier ladder: reachable BIST ADV boundaries + monotone halves
         inside the observed ~10-14bp full-spread envelope.
  FIDELITY a synthetic liquid mega (tight quoted spread + deep ADV) lands in the frozen
         [D207_FIDELITY_BAND_LO_BPS, D207_FIDELITY_BAND_HI_BPS] round-trip band.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d204_hi52_stress as d204
from src.screening import realistic_cost as rc
from src.signals import thresholds as th


# ---------------------------------------------------------------------------
# FIX-1 -- round-trip spread cost is S (half-spread doubled), not 2S
# ---------------------------------------------------------------------------
def test_fix1_round_trip_spread_is_S_not_2S():
    # Pure-spread case (zero impact): a quoted FULL spread of 0.0011 costs 0.0011 round
    # trip (0.00055 at the ask on entry + 0.00055 at the bid on exit), NOT 0.0022.
    d = rc.combine_round_trip(roll_spread=float("nan"), kyle_impact_val=0.0,
                              tier_spread=0.0006, commission=0.0, quoted_spread=0.0011)
    assert d["spread_source"] == "quoted"
    assert d["round_trip_roll"] == pytest.approx(0.0011)          # == S, the half doubled
    assert d["round_trip_roll"] != pytest.approx(2.0 * 0.0011)    # NOT 2S (the old bug)


# ---------------------------------------------------------------------------
# FIX-2 -- source hierarchy quoted > roll > tier
# ---------------------------------------------------------------------------
def test_fix2_source_hierarchy_quoted_then_roll_then_tier():
    quoted = rc.combine_round_trip(0.02, 0.001, 0.0006, commission=0.0, quoted_spread=0.0011)
    roll = rc.combine_round_trip(0.02, 0.001, 0.0006, commission=0.0, quoted_spread=np.nan)
    tier = rc.combine_round_trip(0.0, 0.001, 0.0006, commission=0.0, quoted_spread=np.nan)
    assert (quoted["spread_source"], roll["spread_source"], tier["spread_source"]) == \
        ("quoted", "roll", "tier")
    # tighter observed quoted < vol-inflated roll leg (de-inflation is the whole point)
    assert quoted["round_trip_roll"] < roll["round_trip_roll"]


def _quoted_capable_panel():
    # 400 rows so the 252-day fallback Roll is DEFINED; bounce -> Roll > 0 (a real
    # fallback), and a quoted panel can override it on selected names/dates.
    idx = pd.bdate_range("2020-01-01", periods=400)
    h = 0.01
    bounce = np.array([(-1) ** i for i in range(400)], dtype=float)
    liq = pd.Series(100.0 * np.exp(np.cumsum(0.0002 + bounce * h)), index=idx)
    ill = pd.Series(20.0 * np.exp(np.cumsum(0.0002 + bounce * h)), index=idx)
    close = pd.DataFrame({"LIQ": liq, "ILL": ill})
    value_tl = pd.DataFrame({"LIQ": np.full(400, 1e10), "ILL": np.full(400, 1e7)}, index=idx)
    return close, value_tl, [idx[-1]]


def test_fix2_injected_quoted_panel_routes_through_quoted_source():
    close, value_tl, rebal = _quoted_capable_panel()
    # quote ONLY LIQ; ILL has no quote -> must fall back to the long Roll.
    qpanel = pd.DataFrame({"LIQ": np.full(400, 0.0011)}, index=close.index)
    out = d204.per_stock_cost_panel(close, value_tl, rebal, quoted_panel=qpanel)
    s = out["summary"]
    assert s["spread_source_counts"]["quoted"] == 1     # LIQ via quoted
    assert s["spread_source_counts"]["roll"] == 1       # ILL via 252-Roll fallback
    assert s["spread_source_counts"]["tier"] == 0
    # injected tight quote makes LIQ cheaper than the vol-inflated Roll-priced ILL
    d = rebal[0]
    assert out["cost_roll"][d]["LIQ"] < out["cost_roll"][d]["ILL"]


def test_fix2_no_quoted_panel_uses_roll_then_tier_only():
    close, value_tl, rebal = _quoted_capable_panel()
    out = d204.per_stock_cost_panel(close, value_tl, rebal)   # quoted_panel=None
    s = out["summary"]
    assert s["spread_source_counts"]["quoted"] == 0
    assert s["spread_source_counts"]["roll"] == 2            # both via 252-Roll (bounce>0)


# ---------------------------------------------------------------------------
# FIX-3 -- re-scaled tier ladder: reachable boundaries + monotone, low magnitude
# ---------------------------------------------------------------------------
def test_fix3_tier_boundaries_are_bist_reachable():
    # The old D204 MEGA boundary (2e9 TL) was unreachable; D207 MEGA = 5e7 TL -> a
    # genuine BIST mega (1e10 ADV) classifies as MEGA, not micro.
    assert th.D207_TIER_MEGA_ADV_TL <= 1e8
    assert rc.tier_spread_floor(1e10) == pytest.approx(th.D207_TIER_MEGA_HALF_SPREAD)


def test_fix3_tier_halves_within_observed_envelope():
    # Observed quoted FULL spread is ~flat 10-14bp; the half-spreads (full/2) must sit in
    # ~5-7.5bp (de-inflated vs the old ~6.5-40bp D204 ladder). Monotone mega<...<micro.
    halves = [th.D207_TIER_MEGA_HALF_SPREAD, th.D207_TIER_LARGE_HALF_SPREAD,
              th.D207_TIER_MID_HALF_SPREAD, th.D207_TIER_MICRO_HALF_SPREAD]
    assert halves == sorted(halves)
    assert halves[0] != halves[-1]
    for hs in halves:
        assert 0.00045 <= hs <= 0.00075          # 4.5-7.5bp half = 9-15bp full envelope


# ---------------------------------------------------------------------------
# FIDELITY -- a synthetic liquid mega lands in the frozen ground-truth band
# ---------------------------------------------------------------------------
def test_fidelity_synthetic_mega_round_trip_in_band():
    # ISCTR-like: ~11bp quoted full spread, deep ADV -> tiny impact. Corrected round-trip
    # must land in the pre-registered [7,35]bp band (NOT the SISIK 271-509bp).
    idx = pd.bdate_range("2020-01-01", periods=300)
    rng = np.random.default_rng(7)
    close = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.015, 300))), index=idx)
    out = rc.round_trip_cost(close, adv=5e8, order_value=20_000.0,
                             window=21, lambda_kyle=1.0, quoted_spread=0.0011)
    rt_bps = out["round_trip_roll"] * 1e4
    assert out["spread_source"] == "quoted"
    assert th.D207_FIDELITY_BAND_LO_BPS <= rt_bps <= th.D207_FIDELITY_BAND_HI_BPS


def test_fidelity_band_constants_are_external_and_sane():
    # The band is a VALIDITY criterion, not an edge knob: positive, ordered, and wide
    # enough to bracket NRR-010 (~7.5-13.7bp) + RR-015 (17-25bp) without being unbounded.
    assert 0 < th.D207_FIDELITY_BAND_LO_BPS < th.D207_FIDELITY_BAND_HI_BPS <= 50
