"""Behavior tests for the D-206 NAV-iskonto-Z mean-reversion engine. Synthetic, no network.

Verifies the look-ahead-safe trailing-Z (a future discount NEVER changes a past Z and the Z is
standardized on the trailing window ENDING at t-1); the Stage-0 pre-registration guard RAISES
without the frozen file; the per-holding circular-shift null preserves autocorrelation and is a
no-op on a flat panel but is BEATEN by a planted mean-reversion relationship; the numpy Driscoll-
Kraay within estimator agrees with statsmodels hac-groupsum; LOHO drops one holding at a time and
flags single-holding dominance; the power-of-10 redenomination harmonization undoes a market-wide
unit break while leaving a clean panel untouched; the subsidiary publication lag in the NAV; the
per-holding linear-time detrend; and the combined verdict branches (SERAP / GERCEK-SINYAL /
GERCEK-ama-tradeable-DEGIL).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d206_nav_discount as d206


# ---------------------------------------------------------------------------
# Synthetic helpers (Period[M] index, holding columns)
# ---------------------------------------------------------------------------
def _months(n: int, start: str = "2010-01") -> pd.PeriodIndex:
    return pd.period_range(start, periods=n, freq="M")


def _panel(beta_true: float, n_months: int = 150, n_hold: int = 6, seed: int = 7,
           noise: float = 1.0):
    """z ~ N(0,1) per holding; fwd = beta_true*z + noise. Returns (z_df, fwd_df)."""
    rng = np.random.default_rng(seed)
    idx = _months(n_months)
    cols = [f"H{i}" for i in range(n_hold)]
    z = pd.DataFrame(rng.standard_normal((n_months, n_hold)), index=idx, columns=cols)
    fwd = beta_true * z + rng.standard_normal((n_months, n_hold)) * noise
    return z, fwd


# ===========================================================================
# Look-ahead-safe trailing-Z
# ===========================================================================
def test_trailing_z_future_does_not_change_past():
    """Changing ONLY the last month's discount must leave every earlier Z untouched."""
    idx = _months(8)
    base = pd.DataFrame({"H0": [1.0, 2, 3, 4, 5, 6, 7, 8]}, index=idx)
    bumped = base.copy()
    bumped.iloc[-1, 0] = 999.0
    z_base = d206.trailing_z(base, window=3, min_periods=2)
    z_bump = d206.trailing_z(bumped, window=3, min_periods=2)
    pd.testing.assert_series_equal(z_base["H0"].iloc[:-1], z_bump["H0"].iloc[:-1])


def test_trailing_z_uses_only_trailing_window_ending_at_t_minus_1():
    """Z(t) is standardized on the window [.., t-1]; the current month is excluded."""
    idx = _months(4)
    d = pd.DataFrame({"H0": [10.0, 12.0, 14.0, 16.0]}, index=idx)
    z = d206.trailing_z(d, window=2, min_periods=2)
    # months 0,1: undefined (no full trailing window before them)
    assert np.isnan(z["H0"].iloc[0]) and np.isnan(z["H0"].iloc[1])
    # z[2] uses mean/std of months {0,1} = mean 11, std(ddof=1)=sqrt(2)
    assert z["H0"].iloc[2] == pytest.approx((14.0 - 11.0) / np.sqrt(2.0))
    assert z["H0"].iloc[3] == pytest.approx((16.0 - 13.0) / np.sqrt(2.0))


# ===========================================================================
# Stage-0 pre-registration guard
# ===========================================================================
def test_load_stage0_refuses_without_file(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        d206.load_stage0(stage0_path=missing, require_stage0=True)


def test_load_stage0_returns_empty_when_not_required(tmp_path):
    missing = tmp_path / "no_stage0.json"
    assert d206.load_stage0(stage0_path=missing, require_stage0=False) == {}


def test_stage0_holdings_parses_frozen_composition():
    stage0 = {"universe_composition_FROZEN": {"holdings": {
        "KCHOL": {"listed_subsidiaries": {"FROTO": 0.387, "TUPRS": 0.464}},
        "SAHOL": {"listed_subsidiaries": {"AKBNK": 0.4075}}}}}
    out = d206.stage0_holdings(stage0)
    assert out == {"KCHOL": {"FROTO": 0.387, "TUPRS": 0.464}, "SAHOL": {"AKBNK": 0.4075}}


# ===========================================================================
# Driscoll-Kraay within estimator: sign recovery + statsmodels agreement
# ===========================================================================
def test_dk_within_recovers_positive_sign():
    z, fwd = _panel(beta_true=0.5, noise=0.5)
    panel = d206._panel_long(z, fwd)
    beta, se, t = d206.dk_within(panel["z"].values, panel["fwd"].values,
                                 panel["holding"].values, panel["tid"].values, lags=6)
    assert beta > 0 and t > 2.0


def test_dk_within_matches_statsmodels_hac_groupsum():
    z, fwd = _panel(beta_true=0.3, noise=1.0)
    panel = d206._panel_long(z, fwd)
    beta, se, t = d206.dk_within(panel["z"].values, panel["fwd"].values,
                                 panel["holding"].values, panel["tid"].values, lags=6)
    sm_x = d206._statsmodels_dk_crosscheck(panel, lags=6)
    assert sm_x["available"] is True
    assert sm_x["beta"] == pytest.approx(beta, abs=1e-6)   # FE within == FE dummies
    assert sm_x["dk_t"] == pytest.approx(t, rel=0.05)      # same HAC, tiny dof/scale diff


# ===========================================================================
# Circular-shift null (AC-preserving): no-op on flat, beaten by planted MR
# ===========================================================================
def test_circular_shift_null_flat_panel_is_no_op():
    """A flat forward panel gives a zero within-beta and is NOT beaten by the null."""
    z, _ = _panel(beta_true=0.0)
    fwd = z * 0.0 + 1.0                     # constant per holding -> within-demeaned to 0
    res = d206.circular_shift_null(z, fwd, lags=6, n=200, seed=1)
    assert res["real_beta"] == 0.0
    assert res["beats_null"] is False


def test_circular_shift_null_beaten_by_planted_mean_reversion():
    z, fwd = _panel(beta_true=0.6, noise=0.4)
    res = d206.circular_shift_null(z, fwd, lags=6, n=300, seed=2)
    assert res["real_beta"] > 0
    assert res["pctile"] >= 0.95            # real beta in the far-right tail of the null
    assert res["beats_null"] is True


# ===========================================================================
# LOHO single-holding dominance
# ===========================================================================
def test_loho_robust_when_signal_is_broad():
    z, fwd = _panel(beta_true=0.5, noise=0.5, n_hold=6)
    panel = d206._panel_long(z, fwd)
    full_beta, _, _ = d206.dk_within(panel["z"].values, panel["fwd"].values,
                                     panel["holding"].values, panel["tid"].values, lags=6)
    res = d206.loho(z, fwd, lags=6, full_beta=full_beta)
    assert len(res["fits"]) == 6
    assert res["sign_flips"] is False
    assert res["robust"] is True


def test_loho_fragile_when_one_holding_carries_the_signal():
    """Only H0 has the relationship; dropping it must flip/weaken -> not robust."""
    rng = np.random.default_rng(11)
    idx = _months(150)
    cols = [f"H{i}" for i in range(6)]
    z = pd.DataFrame(rng.standard_normal((150, 6)), index=idx, columns=cols)
    fwd = pd.DataFrame(rng.standard_normal((150, 6)) * 0.3, index=idx, columns=cols)
    fwd["H0"] = 2.0 * z["H0"] + rng.standard_normal(150) * 0.2   # all signal in H0
    panel = d206._panel_long(z, fwd)
    full_beta, _, _ = d206.dk_within(panel["z"].values, panel["fwd"].values,
                                     panel["holding"].values, panel["tid"].values, lags=6)
    res = d206.loho(z, fwd, lags=6, full_beta=full_beta)
    assert res["robust"] is False


# ===========================================================================
# Power-of-10 redenomination harmonization
# ===========================================================================
def test_harmonize_undoes_marketwide_power_of_10_break():
    idx = _months(10)
    rng = np.random.default_rng(3)
    base = pd.DataFrame(100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, (10, 5)), axis=0)),
                        index=idx, columns=[f"S{i}" for i in range(5)])
    broken = base.copy()
    broken.iloc[5:] *= 1000.0               # market-wide x1000 redenomination at month 5
    fixed, meta = d206.harmonize_mktval_units(broken)
    assert meta["n_breaks"] == 1
    assert meta["breaks"][0]["applied_factor"] == 1000.0
    # post-fix panel matches the clean base (the break is removed)
    np.testing.assert_allclose(fixed.values, base.values, rtol=1e-9)


def test_harmonize_leaves_clean_panel_untouched():
    idx = _months(12)
    rng = np.random.default_rng(4)
    clean = pd.DataFrame(100.0 * np.exp(np.cumsum(rng.normal(0, 0.03, (12, 5)), axis=0)),
                         index=idx, columns=[f"S{i}" for i in range(5)])
    fixed, meta = d206.harmonize_mktval_units(clean)
    assert meta["n_breaks"] == 0
    np.testing.assert_allclose(fixed.values, clean.values, rtol=1e-12)


# ===========================================================================
# NAV subsidiary publication lag + discount
# ===========================================================================
def test_nav_uses_lagged_subsidiary_and_same_month_holding():
    idx = _months(4)
    mk = pd.DataFrame({
        "KCHOL": [100.0, 100.0, 100.0, 100.0],
        "FROTO": [200.0, 400.0, 600.0, 800.0]},
        index=idx)
    disc = d206.nav_discount_panel(mk, {"KCHOL": {"FROTO": 0.5}}, lag=1)
    # month 0: NAV uses FROTO(t-1) which is NaN -> discount NaN
    assert np.isnan(disc["KCHOL"].iloc[0])
    # month 1: NAV = 0.5 * FROTO(month0)=0.5*200=100; discount=(100-100)/100 = 0
    assert disc["KCHOL"].iloc[1] == pytest.approx(0.0)
    # month 2: NAV = 0.5 * FROTO(month1)=0.5*400=200; discount=(200-100)/200 = 0.5
    assert disc["KCHOL"].iloc[2] == pytest.approx(0.5)


def test_detrend_removes_linear_drift():
    idx = _months(40)
    drift = pd.DataFrame({"H0": np.linspace(0.0, 1.0, 40)}, index=idx)
    out = d206.detrend_discount(drift)
    assert abs(float(out["H0"].mean())) < 1e-9
    # residual of a pure line is ~0 everywhere
    assert float(np.nanmax(np.abs(out["H0"].values))) < 1e-9


# ===========================================================================
# Combined verdict branches
# ===========================================================================
def _gate2(dk=True, boot=True, ss=True):
    return {"dk_t_pass": dk, "wild_boot_pass": boot, "same_sign_pass": ss}


def test_verdict_serap_when_gate1_sign_wrong():
    v = d206.d206_verdict(
        g1_sign_ok=False, gate2=_gate2(False, False, False),
        gate3={"beats_null": False}, gate4={"both_positive": False},
        carry={"available": False}, loho_res={"robust": False},
        gate5={"available": True, "after_cost_positive": False,
               "breakeven_bps": 0.0, "realistic_cost_bps": 396.0})
    assert v["headline"] == "SERAP"
    assert v["cost_free_real"] is False


def test_verdict_real_signal_when_all_gates_pass_and_tradeable():
    v = d206.d206_verdict(
        g1_sign_ok=True, gate2=_gate2(True, True, True),
        gate3={"beats_null": True}, gate4={"both_positive": True},
        carry={"available": True, "trap_rejected_signal_survives": True},
        loho_res={"robust": True},
        gate5={"available": True, "after_cost_positive": True,
               "breakeven_bps": 300.0, "realistic_cost_bps": 50.0})
    assert v["headline"] == "GERCEK-SINYAL"
    assert v["tradeable"] is True


def test_verdict_real_but_not_tradeable_when_breakeven_near_cost():
    v = d206.d206_verdict(
        g1_sign_ok=True, gate2=_gate2(True, True, True),
        gate3={"beats_null": True}, gate4={"both_positive": True},
        carry={"available": True, "trap_rejected_signal_survives": True},
        loho_res={"robust": True},
        gate5={"available": True, "after_cost_positive": True,
               "breakeven_bps": 80.0, "realistic_cost_bps": 50.0})   # 80 < 2x50
    assert v["headline"] == "GERCEK-ama-tradeable-DEGIL"
    assert v["tradeable"] is False
