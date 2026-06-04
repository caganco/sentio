"""Behavior tests for the D-211 (RR-Y1-002) foreign-flow harness. Synthetic, no network.

The real measurement needs the foreign_flow archive + gitignored snapshot parquets
(CI-absent by design -- the archive does NOT enter CI). These tests exercise the
pure mechanics on small synthetic inputs: the NW-HAC OLS slope t (recovers a known
slope; flags a too-short series), the ported NW mean t-stat, AR(1), z-score, the
foreign_flow .xls->NF_pct parser geometry (ticker filter + USD net/gross aggregation
on a synthetic in-memory zip), and the Stage-0 pre-registration guard.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import d211_config as cfg
from src.screening import d211_foreign_flow as d211


# ---------------------------------------------------------------------------
# NW-HAC OLS slope -- recovers a known slope, finite t on a clean linear signal
# ---------------------------------------------------------------------------
def test_nw_ols_slope_recovers_known_slope():
    rng = np.random.default_rng(3)
    x = rng.normal(0.0, 1.0, 200)
    y = 0.5 + 2.0 * x + rng.normal(0.0, 0.05, 200)     # true slope = 2.0
    out = d211.nw_ols_slope(x, y, lag=6)
    assert out["slope"] == pytest.approx(2.0, abs=0.05)
    assert out["intercept"] == pytest.approx(0.5, abs=0.05)
    assert np.isfinite(out["t"]) and abs(out["t"]) > 2.0   # strong signal -> significant
    assert out["r2"] > 0.95
    assert out["n"] == 200


def test_nw_ols_slope_short_series_returns_nan():
    out = d211.nw_ols_slope([0.1, 0.2, 0.3, 0.4, 0.5], [1.0, 2.0, 3.0, 4.0, 5.0], lag=6)
    assert np.isnan(out["slope"]) and np.isnan(out["t"])   # n=5 < lag+3=9
    assert out["n"] == 5


def test_nw_ols_slope_zero_signal_t_below_bar():
    rng = np.random.default_rng(11)
    x = rng.normal(0.0, 1.0, 150)
    y = rng.normal(0.0, 1.0, 150)                          # independent -> slope ~ 0
    out = d211.nw_ols_slope(x, y, lag=6)
    assert abs(out["t"]) < cfg.D211_KEEP_NW_T_MIN          # noise does not clear keep-bar[1]


# ---------------------------------------------------------------------------
# Ported NW mean t-stat + AR(1) + z-score
# ---------------------------------------------------------------------------
def test_nw_mean_tstat_positive_mean_is_positive():
    rng = np.random.default_rng(1)
    x = rng.normal(0.5, 0.1, 200)
    t, m, n = d211.nw_mean_tstat(x, lag=6)
    assert np.isfinite(t) and t > 0
    assert m == pytest.approx(x.mean(), rel=1e-9)


def test_ar1_detects_persistence():
    rng = np.random.default_rng(5)
    n = 500
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.7 * x[i - 1] + rng.normal(0.0, 1.0)      # AR(1) phi=0.7
    assert d211._ar1(x) == pytest.approx(0.7, abs=0.1)


def test_zscore_is_standardized():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = d211._zscore(s)
    assert z.mean() == pytest.approx(0.0, abs=1e-12)
    assert z.std(ddof=1) == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# foreign_flow parser geometry -- ticker filter + USD net/gross from synthetic .xls
# ---------------------------------------------------------------------------
def _synthetic_ff_zip(tmp_path: Path, ym: str) -> Path:
    """Build a yabanci{ym}.zip with one inner .xls. 8 cols, no header.
    cols: ticker, name, buy_nom, buy_tl, buy_usd, sell_nom, sell_tl, sell_usd.
    Two real .E tickers + one segment sub-header row that must be filtered out."""
    rows = [
        ["AAA.E", "Alpha", 100, 1000, 10.0, 50, 500, 4.0],     # net_usd = +6
        ["BBB.E", "Beta", 200, 2000, 20.0, 80, 800, 9.0],      # net_usd = +11
        ["TOPLAM", "segment-header", 0, 0, 0.0, 0, 0, 0.0],    # filtered (no .E)
    ]
    df = pd.DataFrame(rows)
    xls_bytes = io.BytesIO()
    df.to_excel(xls_bytes, header=False, index=False)
    xls_bytes.seek(0)
    zp = tmp_path / f"yabanci{ym}.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr(f"yabanci{ym}.xlsx", xls_bytes.read())
    return zp


def test_ff_parser_filters_tickers_and_reads_usd(tmp_path):
    zp = _synthetic_ff_zip(tmp_path, "202401")
    df = d211._read_ff_zip(zp)
    assert df is not None
    assert set(df["ticker"]) == {"AAA.E", "BBB.E"}            # TOPLAM excluded
    assert df["buy_usd"].sum() == pytest.approx(30.0)
    assert df["sell_usd"].sum() == pytest.approx(13.0)
    assert df["month"].iloc[0] == pd.Period("2024-01", freq="M")


def test_ff_aggregation_nf_pct(tmp_path, monkeypatch):
    """load_nf_pct over two synthetic months: NF_pct = net/gross from USD columns only."""
    d1 = _synthetic_ff_zip(tmp_path, "202401")
    d2 = _synthetic_ff_zip(tmp_path, "202402")
    monkeypatch.setattr(cfg, "D211_FOREIGN_FLOW_DIR", tmp_path)
    out = d211.load_nf_pct()
    # each month: net_usd = (10+20)-(4+9) = 17 ; gross_usd = 30+13 = 43
    assert out.loc[pd.Period("2024-01", "M"), "net_usd"] == pytest.approx(17.0)
    assert out.loc[pd.Period("2024-01", "M"), "gross_usd"] == pytest.approx(43.0)
    assert out.loc[pd.Period("2024-01", "M"), "nf_pct"] == pytest.approx(17.0 / 43.0)
    assert list(out.index) == [pd.Period("2024-01", "M"), pd.Period("2024-02", "M")]


# ---------------------------------------------------------------------------
# Stage-0 pre-registration guard
# ---------------------------------------------------------------------------
def test_assert_hash_raises_on_drift(tmp_path, monkeypatch):
    p = tmp_path / "fake.parquet"
    p.write_bytes(b"not the frozen snapshot")
    monkeypatch.setattr(cfg, "D211_SNAPSHOT_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="drift"):
        d211._assert_hash("fake", "deadbeefdeadbeef")


def test_run_refuses_without_stage0(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "D211_STAGE0", tmp_path / "no_stage0.json")
    with pytest.raises(RuntimeError, match="REFUSES to run"):
        d211._assert_stage0()
