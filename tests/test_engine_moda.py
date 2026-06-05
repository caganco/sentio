"""Tier-A tests for the Mod-A conjugate core (Section 3.2/4.1/4.2).

Three layers:
1. the name-split is liquidity-balanced, disjoint, reproducible, and NOT an
   ordered/alphabetical assignment;
2. the three Section 7 fixtures land where they were frozen BEFORE results --
   noise fails, an embedded market-neutral factor passes, a pure-market signal is
   killed by neutralization;
3. agreement (want STRONG) and residual-arm-correlation (want LOW) are provably
   separate computations (Section 4.3 mixing-ban), and the vectorized rank-IC
   equals the scipy primitive it replaces for speed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.contracts import (
    DialConfig,
    Frequency,
    NameSplitMethod,
    Panel,
    SplitMode,
    SplitSpec,
)
from src.engine.moda import (
    arm_active_correlation,
    conjugate_agreement,
    name_splits,
    residual_arm_correlation,
    run_moda,
)
from src.engine.stats import nw_tstat, rank_ic_series


class _VecSignal:
    """Parameter-free signal: a fixed per-name score vector, same every date."""

    construction_window = 1

    def __init__(self, vec: np.ndarray, names: list[str], name: str) -> None:
        self.name = name
        self._s = pd.Series(np.asarray(vec, dtype=float), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._s.reindex(names)


def _panel(
    kind: str, *, n_names: int = 120, n_dates: int = 300, seed: int = 0
) -> tuple[Panel, np.ndarray, list[str]]:
    """Synthetic panel + the signal vector for one of the three fixtures.

    ``noise``  : returns independent of the signal (f orthogonal to returns).
    ``factor`` : a static MARKET-NEUTRAL loading f drives the residual return
                 (daily = beta*mkt + g*f + idio); the signal is f.
    ``market`` : returns ride the market only (daily = beta*mkt + idio); the
                 signal is beta, which Section-3 neutralization strips away.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    names = [f"S{i:03d}" for i in range(n_names)]
    mkt_ret = rng.normal(0.0, 0.01, size=n_dates)
    market = pd.Series(100.0 * np.cumprod(1.0 + mkt_ret), index=dates)
    beta = rng.uniform(0.4, 1.6, size=n_names)
    idio = rng.normal(0.0, 0.02, size=(n_dates, n_names))
    f = rng.normal(0.0, 1.0, size=n_names)
    f -= f.mean()  # market-neutral by construction

    if kind == "noise":
        daily, sig = idio, f
    elif kind == "factor":
        daily = beta[None, :] * mkt_ret[:, None] + 0.0025 * f[None, :] + idio
        sig = f
    elif kind == "market":
        daily = beta[None, :] * mkt_ret[:, None] + idio
        sig = beta
    else:  # pragma: no cover - guard
        raise ValueError(kind)

    tr = pd.DataFrame(100.0 * np.cumprod(1.0 + daily, axis=0), index=dates, columns=names)
    value_tl = pd.DataFrame(
        np.tile(1e8 * (1.0 + np.arange(n_names) / n_names), (n_dates, 1)),
        index=dates, columns=names,
    )
    one = pd.Series(1.0, index=dates)
    panel = Panel(
        close=tr.copy(), tr_gross=tr, tr_net=tr, value_tl=value_tl,
        membership={}, market=market, tufe=one, tlref=one, frequency=Frequency.DAILY,
    )
    return panel, sig, names


def _spec(method: NameSplitMethod = NameSplitMethod.LIQUIDITY, seed: int = 0) -> SplitSpec:
    return SplitSpec(
        split_mode=SplitMode.NAME, frequency=Frequency.DAILY, seed=seed, name_split_method=method
    )


# --------------------------------------------------------------------------- #
# 1. name-split structure                                                     #
# --------------------------------------------------------------------------- #
class TestNameSplits:
    def _splits(self, method=NameSplitMethod.LIQUIDITY, seed=0):
        panel, _, names = _panel("noise")
        return panel, names, name_splits(panel, names, spec=_spec(method, seed), split_asof=panel.dates[200])

    def test_determinism_same_seed(self):
        panel, names, a = self._splits()
        b = name_splits(panel, names, spec=_spec(seed=0), split_asof=panel.dates[200])
        assert a == b

    def test_different_seed_differs_and_distinct(self):
        panel, names, a = self._splits(seed=0)
        c = name_splits(panel, names, spec=_spec(seed=1), split_asof=panel.dates[200])
        assert a != c
        distinct = len({frozenset(x1) for x1, _ in a})
        assert distinct >= 45  # R=50 seeds over ~60 pairs -> nearly all unique

    def test_disjoint_and_arm_size(self):
        _, _, splits = self._splits()
        assert len(splits) == config.SPLIT_R_MIN
        for x1, x2 in splits:
            assert set(x1).isdisjoint(x2)
            assert len(x1) >= config.MIN_NAMES_PER_ARM
            assert len(x2) >= config.MIN_NAMES_PER_ARM

    def test_liquidity_balanced(self):
        panel, names, splits = self._splits()
        asof = panel.dates[200]
        adv = panel.value_tl.loc[:asof].tail(config.LIQUID_TRAILING_DAYS).median()
        for x1, x2 in splits:
            s1, s2 = float(adv[x1].sum()), float(adv[x2].sum())
            assert abs(s1 - s2) / max(s1, s2) < 0.02  # pair-randomization balances ADV

    def test_not_alphabetical(self):
        _, _, splits = self._splits()
        x1 = splits[0][0]
        prefix = sorted(set().union(*[set(a) | set(b) for a, b in splits]))[: len(x1)]
        assert set(x1) != set(prefix)  # not the ordered first-half

    def test_random_method_disjoint(self):
        _, _, splits = self._splits(method=NameSplitMethod.RANDOM)
        for x1, x2 in splits:
            assert set(x1).isdisjoint(x2)
            assert len(x1) >= config.MIN_NAMES_PER_ARM


# --------------------------------------------------------------------------- #
# 2. the three frozen Section-7 fixtures (run_moda end-to-end)                 #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def noise_result():
    panel, sig, names = _panel("noise")
    return run_moda(panel, _VecSignal(sig, names, "noise"), _spec(), DialConfig())


@pytest.fixture(scope="module")
def factor_result():
    panel, sig, names = _panel("factor")
    return run_moda(panel, _VecSignal(sig, names, "factor"), _spec(), DialConfig())


@pytest.fixture(scope="module")
def market_result():
    panel, sig, names = _panel("market")
    return run_moda(panel, _VecSignal(sig, names, "market"), _spec(), DialConfig())


class TestFixtureNoise:
    def test_does_not_pass(self, noise_result):
        r = noise_result
        assert r["agreement_pass"] is False
        assert abs(r["agreement_t_cross_median"]) < 1.5  # no per-arm significance
        assert r["sign_consistency"] < 0.90              # cross-arm sign is a coin
        assert 0.3 <= r["pbo"] <= 0.7                    # IS-best lands ~ OOS-median
        assert r["residual_corr_flag"] is False


class TestFixtureFactor:
    def test_passes_strongly(self, factor_result):
        r = factor_result
        assert r["agreement_pass"] is True
        assert r["median_t_x1"] > 2.0 and r["median_t_x2"] > 2.0
        assert r["sign_consistency"] >= 0.90
        assert r["pbo"] < 0.50
        assert r["residual_corr_flag"] is False  # idiosyncratic, arms hold different names


class TestFixtureMarket:
    def test_neutralization_kills_the_signal(self, market_result):
        # The guaranteed assertion: a beta-only signal is dead after Section-3
        # market-neutralization, so the conjugate test must NOT pass.
        r = market_result
        assert r["agreement_pass"] is False
        assert abs(r["agreement_t_cross_median"]) < 1.5


# --------------------------------------------------------------------------- #
# 3. mixing-ban + IC-equivalence (Section 4.3 made structural)                 #
# --------------------------------------------------------------------------- #
class TestSeparation:
    def test_residual_corr_flag_high_and_low(self):
        null = np.random.default_rng(0).normal(0.0, 0.1, size=200)  # null centered ~ 0
        _, hi = residual_arm_correlation(0.9, null)
        _, lo = residual_arm_correlation(0.0, null)
        assert hi is True and lo is False

    def test_arm_active_correlation_extremes(self):
        idx = pd.bdate_range("2022-01-03", periods=80)
        rng = np.random.default_rng(1)
        a = pd.Series(rng.normal(size=80), index=idx)
        b = pd.Series(rng.normal(size=80), index=idx)
        assert abs(arm_active_correlation(a, a) - 1.0) < 1e-9
        assert abs(arm_active_correlation(a, b)) < 0.3

    def test_anti_mix_opposite_sign(self, factor_result):
        # On a real edge the two SEPARATE fields take opposite-meaning values:
        # agreement = PASS (strong is good), residual = not flagged (low is good).
        assert factor_result["agreement_pass"] is True
        assert factor_result["residual_corr_flag"] is False
        # The residual verdict PENALIZES high co-movement -- the inverse of
        # "strength is good" -- so feeding near-perfect co-movement flips it to
        # True. The two cannot be the same computation.
        null = np.random.default_rng(0).normal(0.0, 0.05, size=200)
        _, flag = residual_arm_correlation(0.99, null)
        assert flag is True

    def test_vectorized_ic_matches_scipy(self):
        # conjugate_agreement uses a vectorized Spearman in place of the per-date
        # scipy primitive (stats.rank_ic_series) for speed; pin them equal via the
        # PUBLIC function so the substitution stays honest.
        rng = np.random.default_rng(5)
        dates = pd.bdate_range("2022-01-03", periods=120)
        names = [f"S{i:03d}" for i in range(80)]
        scores = pd.DataFrame(rng.normal(size=(120, 80)), index=dates, columns=names)
        resid = pd.DataFrame(rng.normal(size=(120, 80)), index=dates, columns=names)
        x1, x2 = names[:40], names[40:]
        out = conjugate_agreement(scores, resid, [(x1, x2)], lag=config.NW_LAG_DAILY)
        ref_t1 = nw_tstat(
            rank_ic_series(scores[x1], resid[x1], min_names=config.MIN_NAMES_CROSS_SECTION).to_numpy(),
            lag=config.NW_LAG_DAILY,
        )
        ref_t2 = nw_tstat(
            rank_ic_series(scores[x2], resid[x2], min_names=config.MIN_NAMES_CROSS_SECTION).to_numpy(),
            lag=config.NW_LAG_DAILY,
        )
        assert out["median_t_x1"] == pytest.approx(ref_t1, abs=1e-9)
        assert out["median_t_x2"] == pytest.approx(ref_t2, abs=1e-9)
