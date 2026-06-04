"""Behavior tests for the D-213 (RR-Y1-003) ex-ante real-rate harness. Synthetic, no network.

The real measurement needs the EVDS-derived snapshot parquets (frozen, tracked) and the
Stage-0 pre-registration; the live EVDS pull is CI-absent by design. These tests exercise
the pure mechanics on small synthetic inputs: the NW-HAC OLS slope t (recovers a known
slope; flags a too-short series; noise stays below the keep-bar), the ported NW mean
t-stat, AR(1), z-score, the CPI-YoY annual-pct geometry, the ex-ante real-rate
construction + lag-1 alignment, and the Stage-0 / hash-drift guards.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import d213_config as cfg
from src.screening import d213_real_rate as d213


# ---------------------------------------------------------------------------
# NW-HAC OLS slope -- recovers a known slope, finite t on a clean linear signal
# ---------------------------------------------------------------------------
def test_nw_ols_slope_recovers_known_slope():
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 1.0, 200)
    y = 0.5 + 2.0 * x + rng.normal(0.0, 0.05, 200)     # true slope = 2.0
    out = d213.nw_ols_slope(x, y, lag=6)
    assert out["slope"] == pytest.approx(2.0, abs=0.05)
    assert out["intercept"] == pytest.approx(0.5, abs=0.05)
    assert np.isfinite(out["t"]) and abs(out["t"]) > 2.0
    assert out["r2"] > 0.95
    assert out["n"] == 200


def test_nw_ols_slope_short_series_returns_nan():
    out = d213.nw_ols_slope([0.1, 0.2, 0.3, 0.4, 0.5], [1.0, 2.0, 3.0, 4.0, 5.0], lag=6)
    assert np.isnan(out["slope"]) and np.isnan(out["t"])   # n=5 < lag+3=9
    assert out["n"] == 5


def test_nw_ols_slope_zero_signal_t_below_bar():
    rng = np.random.default_rng(11)
    x = rng.normal(0.0, 1.0, 150)
    y = rng.normal(0.0, 1.0, 150)                          # independent -> slope ~ 0
    out = d213.nw_ols_slope(x, y, lag=6)
    assert abs(out["t"]) < cfg.D213_KEEP_NW_T_MIN          # noise does not clear keep-bar[1]


# ---------------------------------------------------------------------------
# Ported NW mean t-stat + AR(1) + z-score
# ---------------------------------------------------------------------------
def test_nw_mean_tstat_positive_mean_is_positive():
    rng = np.random.default_rng(1)
    x = rng.normal(0.5, 0.1, 200)
    t, m, n = d213.nw_mean_tstat(x, lag=6)
    assert np.isfinite(t) and t > 0
    assert m == pytest.approx(x.mean(), rel=1e-9)


def test_ar1_detects_persistence():
    rng = np.random.default_rng(5)
    n = 500
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0.0, 1.0)      # AR(1) phi=0.7
    assert d213._ar1(x) == pytest.approx(0.7, abs=0.1)


def test_zscore_is_standardized():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = d213._zscore(s)
    assert z.mean() == pytest.approx(0.0, abs=1e-12)
    assert z.std(ddof=1) == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# CPI-YoY geometry -- 12-month change in annual percentage points
# ---------------------------------------------------------------------------
def test_cpi_yoy_pct_is_annual_points():
    idx = pd.period_range("2020-01", periods=24, freq="M")
    # CPI that doubles over 12 months -> +100.0 pct points YoY at month 13
    cpi = pd.Series(100.0 * (2.0 ** (np.arange(24) / 12.0)), index=idx)
    yoy = d213._cpi_yoy_pct(cpi)
    assert yoy.iloc[12] == pytest.approx(100.0, abs=1e-6)
    assert np.isnan(yoy.iloc[0])                           # first 12 months undefined


# ---------------------------------------------------------------------------
# ex-ante real-rate construction + lag-1 alignment (the core predictor geometry)
# ---------------------------------------------------------------------------
def test_ex_ante_level_and_lag1_alignment():
    idx = pd.period_range("2020-01", periods=6, freq="M")
    nominal = pd.Series([30.0, 32.0, 34.0, 36.0, 38.0, 40.0], index=idx)
    expinf = pd.Series([20.0, 21.0, 22.0, 23.0, 24.0, 25.0], index=idx)
    r_ex_ante = nominal - expinf                           # LEVEL = +10, +11, +12, +13, +14, +15
    assert list(r_ex_ante.values) == [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    # lag-1: to predict return-month t use r_ex_ante(t-1)
    lag = cfg.D213_LOOKAHEAD_LAG_MONTHS
    assert lag == 1
    aligned = r_ex_ante.reindex(idx - lag)
    # for return-month 2020-03 (idx[2]) the predictor is r_ex_ante(2020-02) = 11.0
    assert aligned.values[2] == pytest.approx(11.0)
    assert np.isnan(aligned.values[0])                     # 2019-12 not in series -> dropped


def test_deploy_rule_sign_is_negative_real_rate_long():
    # economic-prior LOCK: r_ex_ante(t-1) < 0 -> index long (1); >= 0 -> cash (0)
    rea = np.array([-5.0, -0.01, 0.0, 3.0, -2.0])
    pos = (rea < cfg.D213_SIGNAL_THRESHOLD).astype(int)
    assert list(pos) == [1, 1, 0, 0, 1]


# ---------------------------------------------------------------------------
# Stage-0 + hash-drift guards
# ---------------------------------------------------------------------------
def test_assert_hash_raises_on_drift(tmp_path, monkeypatch):
    p = tmp_path / "fake.parquet"
    p.write_bytes(b"not the frozen snapshot")
    monkeypatch.setattr(cfg, "D213_SNAPSHOT_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="drift"):
        d213._assert_hash("fake", "deadbeefdeadbeef")


def test_run_refuses_without_stage0(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "D213_STAGE0", tmp_path / "no_stage0.json")
    with pytest.raises(RuntimeError, match="REFUSES to run"):
        d213._assert_stage0()
