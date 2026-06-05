"""Tier-A tests for the engine stats core (rank-IC / IR / Newey-West t).

The NW-equivalence block pins the engine estimator to the committed precedents
(``d213``/``d211`` ``nw_mean_tstat``), which share the population-variance
convention of the untracked ``c9._nw_t`` that produced the C12 golden. The
``c9``-golden reproduction itself is a Faz-3 hard gate (placeholder below).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.stats import ic_ir, nw_tstat, rank_ic_series
from src.screening.d211_foreign_flow import nw_mean_tstat as d211_nw
from src.screening.d213_real_rate import nw_mean_tstat as d213_nw

# --- C12 golden hard-gate provenance (Section 8.1) -------------------------------- #
# The CI gate reads ONLY the committed ASCII fixture + meta. The skipif local e2e
# additionally needs the gitignored lab harness + OHLCV snapshot (absent in CI).
_GOLDEN_META = json.loads(config.C12_GOLDEN_META.read_text(encoding="ascii"))
_OHLCV_SNAPSHOT = config.SNAPSHOTS / _GOLDEN_META["ohlcv_snapshot"]
_LAB_DUMP = config.REPO_ROOT / "lab-demo-clone1" / "harness" / "dump_c12_golden_fixture.py"
_LOCAL_E2E_AVAILABLE = _LAB_DUMP.exists() and _OHLCV_SNAPSHOT.exists()


def _pool_committed_golden() -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex, list[str]]:
    """Pool the committed per-fold C12 fixture the way the assembler would: concatenate
    each fold's daily active vectors in fold-origin order (exercises the concatenation
    the pre-pooled scalars alone cannot)."""
    df = pd.read_csv(config.C12_GOLDEN_FIXTURE)
    folds = sorted(df["fold_origin"].unique(), key=pd.Timestamp)
    gross = np.concatenate([df.loc[df.fold_origin == o, "gross_active"].to_numpy(float) for o in folds])
    net = np.concatenate([df.loc[df.fold_origin == o, "net_active"].to_numpy(float) for o in folds])
    dates = pd.to_datetime(
        np.concatenate([df.loc[df.fold_origin == o, "date"].to_numpy() for o in folds])
    )
    return gross, net, dates, [str(o) for o in folds]


def _load_lab_dump_module():  # pragma: no cover - local-only (CI skips)
    """Import the gitignored dump module by path (it puts the lab harness on sys.path and
    exposes c12 + the canonical _all_universe_folds/_pool reconstruction). Importing it does
    NOT run main() (guarded by __main__), so it never rewrites the committed fixture."""
    harness_dir = config.REPO_ROOT / "lab-demo-clone1" / "harness"
    if str(harness_dir) not in sys.path:
        sys.path.insert(0, str(harness_dir))
    spec = importlib.util.spec_from_file_location("c12_golden_dump", _LAB_DUMP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _aligned_panels(n_dates: int = 6, n_names: int = 40, sign: float = 1.0):
    dates = pd.bdate_range("2022-01-03", periods=n_dates)
    names = [f"S{i:02d}" for i in range(n_names)]
    base = np.arange(n_names, dtype=float)
    scores = pd.DataFrame([base] * n_dates, index=dates, columns=names)
    fwd = pd.DataFrame([sign * base] * n_dates, index=dates, columns=names)
    return scores, fwd


class TestRankIC:
    def test_monotone_is_plus_one(self):
        scores, fwd = _aligned_panels(sign=1.0)
        ic = rank_ic_series(scores, fwd)
        assert len(ic) == 6
        assert ic.to_numpy() == pytest.approx(1.0)

    def test_antimonotone_is_minus_one(self):
        scores, fwd = _aligned_panels(sign=-1.0)
        ic = rank_ic_series(scores, fwd)
        assert ic.to_numpy() == pytest.approx(-1.0)

    def test_min_names_floor_drops_thin_dates(self):
        scores, fwd = _aligned_panels(n_dates=4, n_names=40)
        # Blank out 15 names on the 2nd date -> 25 pairs < 30 floor -> dropped.
        thin = scores.index[1]
        scores.loc[thin, scores.columns[:15]] = np.nan
        ic = rank_ic_series(scores, fwd, min_names=30)
        assert thin not in ic.index
        assert len(ic) == 3

    def test_below_floor_everywhere_is_empty(self):
        scores, fwd = _aligned_panels(n_names=20)  # 20 < 30
        ic = rank_ic_series(scores, fwd, min_names=30)
        assert ic.empty


class TestIR:
    def test_known_value(self):
        assert ic_ir(pd.Series([1.0, 2.0, 3.0])) == pytest.approx(2.0)  # mean 2 / std 1

    def test_sign_flips(self):
        assert ic_ir(pd.Series([-1.0, -2.0, -3.0])) == pytest.approx(-2.0)

    def test_scale_invariant(self):
        assert ic_ir(pd.Series([2.0, 4.0, 6.0])) == pytest.approx(ic_ir(pd.Series([1.0, 2.0, 3.0])))

    def test_degenerate_is_nan(self):
        assert np.isnan(ic_ir(pd.Series([5.0, 5.0, 5.0])))  # zero dispersion
        assert np.isnan(ic_ir(pd.Series([1.0])))  # < 2 obs


class TestNeweyWestEquivalence:
    @pytest.mark.parametrize("lag", [3, 6, 10])
    def test_matches_committed_d213_and_d211(self, lag):
        rng = np.random.default_rng(20260605)
        x = rng.standard_normal(200) * 0.01 + 0.0008  # autocorr-free, finite n
        t_engine = nw_tstat(x, lag=lag)
        assert t_engine == pytest.approx(d213_nw(x, lag=lag)[0], rel=1e-12, abs=1e-12)
        assert t_engine == pytest.approx(d211_nw(x, lag=lag)[0], rel=1e-12, abs=1e-12)


class TestNeweyWestEdges:
    def test_below_guard_is_nan(self):
        assert np.isnan(nw_tstat(np.zeros(5), lag=3))  # n=5 < lag+3=6

    def test_zero_variance_is_nan(self):
        # Exact-constant -> deviations are exactly 0 -> HAC variance 0 -> NaN.
        # (np.full(50, 0.7) would NOT qualify: 0.7 is inexact, so FP rounding
        # leaves a ~1e-30 dispersion and yields a huge finite t -- that is the
        # near-constant case covered by test_perfect_signal_is_large_t.)
        assert np.isnan(nw_tstat(np.ones(50), lag=5))

    def test_perfect_signal_is_large_t(self):
        x = 0.05 + np.zeros(60)
        x[::2] += 1e-6  # tiny dispersion so variance > 0
        assert nw_tstat(x, lag=5) > 50.0

    def test_pure_noise_is_small_t(self):
        rng = np.random.default_rng(7)
        assert abs(nw_tstat(rng.standard_normal(400), lag=5)) < 3.0

    def test_drops_nonfinite(self):
        rng = np.random.default_rng(11)
        x = rng.standard_normal(200) * 0.01 + 0.001
        x_holes = x.copy()
        x_holes[5] = np.nan
        x_holes[50] = np.inf
        # Same finite subset -> identical t to the explicitly-cleaned array.
        clean = x[np.isfinite(x_holes)]
        assert nw_tstat(x_holes, lag=5) == pytest.approx(nw_tstat(clean, lag=5))


def test_nw_reproduces_c9_golden():
    """C12 golden HARD GATE -- the real-data DETERMINISM anchor (Section 8 anti-silent-error /
    off-by-one-purge-leak guard). The engine pools the committed per-fold C12 ALL-universe
    active-return fixture itself (concatenate in fold-origin order + regime-mask + annualize --
    the assembler bits) and must reproduce the frozen c9 golden: nw_tstat(gross, lag=10) ==
    6.928414 and nw_tstat(net, lag=10) == -6.274774. The D-207 cost FLIPS the sign -- the gross
    daily continuation EXISTS (+t), net is cost-killed (-t).

    HONEST FRAMING (mandatory, note N3): this is ONE of three correctness layers, NOT the
    ultimate proof the engine is methodologically correct. It proves the engine is DETERMINISTIC
    and silent-error-free on a known, frozen, economically-artifactual reference. Methodological
    correctness lives on the three synthetic Mod-A fixtures + the synthetic-null
    (test_engine_moda); C12 is gross-only, cost-killed. The gate reproduces a known number,
    nothing more.

    CI-green: reads ONLY the committed ASCII fixture + meta (no gitignored data). The
    construction off-by-one (snapshot -> per-fold series) is covered by the skipif e2e below.
    """
    meta = _GOLDEN_META
    gross, net, dates, folds = _pool_committed_golden()
    lag = config.C12_GOLDEN_NW_LAG
    yr = config.C12_GOLDEN_TRADING_DAYS_YR

    # shape / provenance
    assert len(folds) == meta["n_folds"]
    assert gross.size == net.size == config.C12_GOLDEN_N_POOLED == meta["n_pooled_days"]

    gross_t = nw_tstat(gross, lag=lag)
    net_t = nw_tstat(net, lag=lag)
    # the engine estimator reproduces the frozen (rounded) c9 golden constants ...
    assert gross_t == pytest.approx(config.C12_GOLDEN_GROSS_NWT, abs=5e-6)
    assert net_t == pytest.approx(config.C12_GOLDEN_NET_NWT, abs=5e-6)
    # ... and matches the full-precision meta byte-for-byte (same series, same estimator).
    assert gross_t == pytest.approx(meta["gross_nw_t"], rel=1e-9)
    assert net_t == pytest.approx(meta["net_nw_t"], rel=1e-9)
    # cost FLIPS the daily-dependency sign: gross +, net - (D-207 cost-killed).
    assert gross_t > 0.0 > net_t

    # mean / annualized active reproduce byte-for-byte.
    assert float(gross.mean()) == pytest.approx(meta["gross_active_mean"], rel=1e-9)
    assert float(net.mean()) == pytest.approx(meta["net_active_mean"], rel=1e-9)
    assert float(gross.mean() * yr) == pytest.approx(meta["gross_active_ann"], rel=1e-9)
    assert float(net.mean() * yr) == pytest.approx(meta["net_active_ann"], rel=1e-9)

    # regime-mask (assembler bit): pre/post 2022-01-01 split on the pooled return-dates.
    pre = dates < pd.Timestamp(config.C12_GOLDEN_REGIME_CUT)
    assert float(gross[pre].mean()) == pytest.approx(meta["regime_split_gross"]["pre_2022"], rel=1e-9)
    assert float(gross[~pre].mean()) == pytest.approx(meta["regime_split_gross"]["post_2022"], rel=1e-9)
    assert float(net[pre].mean()) == pytest.approx(meta["regime_split_net"]["pre_2022"], rel=1e-9)
    assert float(net[~pre].mean()) == pytest.approx(meta["regime_split_net"]["post_2022"], rel=1e-9)

    # realistic per-name D-207 cost (frozen meta) exceeds the flat fallback -- the economic
    # reason gross flips to net (tamper-evident pin on the committed cost provenance).
    assert meta["mean_rt_bps"] > meta["fallback_rt_bps"]
    assert meta["mean_rt_bps"] == pytest.approx(46.77595554973686, rel=1e-9)


@pytest.mark.skipif(
    not _LOCAL_E2E_AVAILABLE,
    reason="C12 end-to-end reconstruction needs the gitignored lab harness + OHLCV snapshot "
    "(absent in CI and on non-lab clones). CI-skips by design (note N1: the Builder runs it "
    "locally >=1 before merge and records the pass in the PR).",
)
def test_c12_golden_end_to_end_from_snapshot():  # pragma: no cover - local-only (CI skips)
    """LOCAL end-to-end reconstruction (note N1) -- the ONLY check of the forward-return
    t->t+1 construction off-by-one that the pre-pooled gate cannot cover. Re-derives the C12
    pooled series FROM the gitignored OHLCV snapshot via the canonical lab reconstruction
    (pinned to the snapshot's sha256), asserts it matches the committed fixture row-for-row
    (date alignment + per-fold concatenation order), and that the ENGINE estimator reproduces
    the golden NW-t on the freshly-built series. CI-skips (snapshot + lab absent)."""
    dump = _load_lab_dump_module()
    c12 = dump.c12

    # provenance pin: the live snapshot c12 loads must be the exact bytes the golden froze on.
    sha = hashlib.sha256(c12.OHLCV.read_bytes()).hexdigest()[:16]
    assert sha == _GOLDEN_META["ohlcv_sha256_prefix"], (sha, _GOLDEN_META["ohlcv_sha256_prefix"])

    D = c12.load_components()
    rt_all, _micro = c12.cost_vector(D["names"])
    folds = dump._all_universe_folds(D, rt_all)
    net, gross, dts = dump._pool(folds)

    # row-for-row identity with the committed fixture: this is the t->t+1 alignment + the
    # per-fold concatenation-order check the pre-pooled gate cannot reach.
    df = pd.read_csv(config.C12_GOLDEN_FIXTURE)
    assert gross.size == len(df) == config.C12_GOLDEN_N_POOLED
    np.testing.assert_allclose(gross, df["gross_active"].to_numpy(float), rtol=0, atol=1e-9)
    np.testing.assert_allclose(net, df["net_active"].to_numpy(float), rtol=0, atol=1e-9)
    assert [str(pd.Timestamp(x).date()) for x in dts] == list(df["date"].astype(str))

    # the engine estimator reproduces the golden on the freshly-rebuilt-from-snapshot series.
    assert nw_tstat(gross, lag=config.C12_GOLDEN_NW_LAG) == pytest.approx(config.C12_GOLDEN_GROSS_NWT, abs=5e-6)
    assert nw_tstat(net, lag=config.C12_GOLDEN_NW_LAG) == pytest.approx(config.C12_GOLDEN_NET_NWT, abs=5e-6)
