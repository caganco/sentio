"""Tier-A tests for the Mod-B temporal-CPCV leg (synthetic, CI-green).

Anti-slop discrimination: a noise signal must NOT pass (high PBO, small pooled
OOS t), and an embedded real edge MUST be detected (low PBO, large pooled t).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.backtest.cross_validation import CombinatorialPurgedCV
from src.engine.contracts import DialConfig, Frequency, Panel, SplitMode, SplitSpec
from src.engine.modb import run_modb


def _panel(n_dates: int = 200, n_names: int = 60, seed: int = 0) -> Panel:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    names = [f"N{i:03d}" for i in range(n_names)]
    steps = rng.standard_normal((n_dates, n_names)) * 0.02
    tr = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=dates, columns=names)
    ones = pd.DataFrame(1.0, index=dates, columns=names)
    series = pd.Series(1.0, index=dates)
    return Panel(
        close=tr.copy(),
        tr_gross=tr,
        tr_net=tr,
        value_tl=ones * 5e7,
        membership={"bist100": ones},
        market=series,
        tufe=series,
        tlref=series,
    )


class _EdgeSignal:
    """Embedded factor: score = next-period total return + small noise."""

    name = "edge"
    construction_window = 1

    def __init__(self, panel: Panel, *, seed: int = 1, noise: float = 5e-4) -> None:
        fwd = panel.tr_gross.shift(-1) / panel.tr_gross - 1.0
        rng = np.random.default_rng(seed)
        self._scores = fwd + rng.standard_normal(fwd.shape) * noise

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._scores.loc[asof, names]


class _NullSignal:
    """Pure noise, orthogonal to forward returns."""

    name = "null"
    construction_window = 1

    def __init__(self, panel: Panel, *, seed: int = 2) -> None:
        idx, cols = panel.close.index, panel.close.columns
        rng = np.random.default_rng(seed)
        self._scores = pd.DataFrame(
            rng.standard_normal((len(idx), len(cols))), index=idx, columns=cols
        )

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._scores.loc[asof, names]


def _spec() -> SplitSpec:
    return SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.DAILY)


class TestCPCVStructure:
    def test_path_count_and_disjoint(self):
        dates = pd.bdate_range("2021-01-04", periods=200)
        cv = CombinatorialPurgedCV(N=10, k=2)
        paths = cv.split(dates, embargo_days=1)
        assert len(paths) == math.comb(10, 2) == 45
        for train_idx, test_idx in paths:
            assert set(train_idx).isdisjoint(set(test_idx))

    def test_run_reports_path_count(self):
        panel = _panel()
        res = run_modb(panel, _NullSignal(panel), _spec(), DialConfig())
        assert res["n_paths"] == 45
        assert res["pbo_is_simplified_proxy"] is True


class TestDiscrimination:
    def test_null_does_not_pass(self):
        panel = _panel()
        res = run_modb(panel, _NullSignal(panel), _spec(), DialConfig())
        assert res["pbo"] >= 0.3  # noise -> roughly half the paths lose
        assert abs(res["pooled_oos_ic_t"]) < 3.0  # no significant rank-IC

    def test_signal_is_detected(self):
        panel = _panel()
        res = run_modb(panel, _EdgeSignal(panel), _spec(), DialConfig())
        assert res["pbo"] < 0.2  # embedded edge -> paths win
        assert res["pooled_oos_ic_t"] > 5.0  # strong, persistent rank-IC

    def test_signal_beats_null(self):
        panel = _panel()
        sig = run_modb(panel, _EdgeSignal(panel), _spec(), DialConfig())
        null = run_modb(panel, _NullSignal(panel), _spec(), DialConfig())
        assert sig["pooled_oos_ic_t"] > null["pooled_oos_ic_t"]
        assert sig["pbo"] < null["pbo"]
