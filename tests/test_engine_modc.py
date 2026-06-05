"""Tier-A tests for the Mod-C intra-regime forward time-holdout leg (RR-Y1-010).

Mod-C freezes a cross-sectional factor on a TRAINING time-window and measures its
forward rank-IC on a LATER held-out window WITHIN THE SAME regime, with an embargo
(= the forward-return horizon) purged across the boundary. The fixtures plant a
TIME-VARYING factor loading so the two persistence outcomes are separable:

- ``persistent``  : the factor drives the residual return on BOTH segments -> holdout
                    reproduces train (PASS), adequate breadth + single regime -> HIGH.
- ``train_only``  : the factor drives the TRAIN segment only; the holdout is pure
                    market+idio noise -> holdout IC collapses (persistence FAIL).

Confidence semantics are the OPPOSITE-but-consistent mirror of Mod-A: single-regime
is the DESIGN; the holdout window CROSSING REGIME_SPLIT is the confound.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine import config
from src.engine.contracts import (
    DialConfig,
    Frequency,
    HoldoutConfidence,
    Panel,
    SplitMode,
    SplitSpec,
)
from src.engine.modc import run_modc


class _VecSignal:
    """Parameter-free signal: a fixed per-name score vector, same every date."""

    construction_window = 1

    def __init__(self, vec: np.ndarray, names: list[str], name: str) -> None:
        self.name = name
        self._s = pd.Series(np.asarray(vec, dtype=float), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._s.reindex(names)


def _panel_tv(
    kind: str,
    *,
    boundary_idx: int,
    n_names: int = 120,
    n_dates: int = 420,
    seed: int = 0,
    start: str = "2023-01-02",
) -> tuple[Panel, np.ndarray, list[str], pd.Timestamp]:
    """Synthetic panel with a TIME-VARYING market-neutral factor loading.

    ``persistent`` : loading active on every date (train + holdout).
    ``train_only`` : loading active only on dates strictly before ``boundary_idx``;
                     after the boundary the cross-section is market+idio only.

    Returns the panel, the signal vector (= the factor f), the names, and the
    boundary Timestamp (= ``dates[boundary_idx]``) to feed ``holdout_start``.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n_dates)
    names = [f"S{i:03d}" for i in range(n_names)]
    mkt_ret = rng.normal(0.0, 0.01, size=n_dates)
    market = pd.Series(100.0 * np.cumprod(1.0 + mkt_ret), index=dates)
    beta = rng.uniform(0.4, 1.6, size=n_names)
    idio = rng.normal(0.0, 0.02, size=(n_dates, n_names))
    f = rng.normal(0.0, 1.0, size=n_names)
    f -= f.mean()  # market-neutral by construction

    load = np.full(n_dates, 0.0025)
    if kind == "train_only":
        load[boundary_idx:] = 0.0
    elif kind != "persistent":  # pragma: no cover - guard
        raise ValueError(kind)

    daily = beta[None, :] * mkt_ret[:, None] + load[:, None] * f[None, :] + idio
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
    return panel, f, names, dates[boundary_idx]


def _spec(boundary: pd.Timestamp, seed: int = 0) -> SplitSpec:
    return SplitSpec(
        split_mode=SplitMode.TIME_HOLDOUT,
        frequency=Frequency.DAILY,
        seed=seed,
        holdout_start=boundary.strftime("%Y-%m-%d"),
    )


# --------------------------------------------------------------------------- #
# 1. persistence verdict                                                      #
# --------------------------------------------------------------------------- #
class TestPersistentFactor:
    def test_holdout_reproduces_train_and_is_high(self):
        panel, sig, names, boundary = _panel_tv("persistent", boundary_idx=260)
        r = run_modc(panel, _VecSignal(sig, names, "persistent"), _spec(boundary), DialConfig())
        assert r["holdout_persistence_pass"] is True
        assert r["holdout_ic_t"] > config.AGREEMENT_CROSS_IC_T_MIN
        assert r["holdout_sign_consistent"] is True
        assert np.sign(r["holdout_ic_mean"]) == np.sign(r["train_ic_mean"])
        assert r["n_holdout_obs"] >= config.HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE
        assert r["n_train_obs"] >= config.HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE
        assert r["holdout_confidence"] is HoldoutConfidence.HIGH
        assert r["holdout_confidence_reasons"] == ()
        assert r["guard_messages"] == ()


class TestTrainOnlyFactor:
    def test_persistence_fails_when_holdout_is_noise(self):
        panel, sig, names, boundary = _panel_tv("train_only", boundary_idx=260)
        r = run_modc(panel, _VecSignal(sig, names, "train-only"), _spec(boundary), DialConfig())
        # the train window still carries the factor -> train IC is real ...
        assert r["train_ic_t"] > config.AGREEMENT_CROSS_IC_T_MIN
        # ... but the holdout lost it, so the persistence verdict must be False.
        assert r["holdout_persistence_pass"] is False


# --------------------------------------------------------------------------- #
# 2. embargo / power guard                                                    #
# --------------------------------------------------------------------------- #
class TestPowerGuard:
    def test_boundary_too_close_to_edge_guards(self):
        # boundary just past the beta warm-up -> train segment below the NW floor.
        panel, sig, names, boundary = _panel_tv("persistent", boundary_idx=103)
        r = run_modc(panel, _VecSignal(sig, names, "thin-train"), _spec(boundary), DialConfig())
        assert r["holdout_persistence_pass"] is None
        assert r["holdout_sign_consistent"] is None
        assert np.isnan(r["holdout_ic_t"])
        assert any("insufficient train/holdout IC observations" in m for m in r["guard_messages"])


# --------------------------------------------------------------------------- #
# 3. confidence semantics (the opposite-but-consistent regime rule)           #
# --------------------------------------------------------------------------- #
class TestConfidenceSemantics:
    def test_holdout_crossing_regime_is_confounded(self):
        # start pre-2022 with the boundary before REGIME_SPLIT so the holdout window
        # straddles 2022-01-01 -> train/holdout span different regimes -> CONFOUNDED.
        panel, sig, names, boundary = _panel_tv(
            "persistent", boundary_idx=120, start="2021-06-01"
        )
        assert boundary < pd.Timestamp(config.REGIME_SPLIT)
        r = run_modc(panel, _VecSignal(sig, names, "crosses"), _spec(boundary), DialConfig())
        assert r["holdout_confidence"] is HoldoutConfidence.CONFOUNDED
        assert any("crosses REGIME_SPLIT" in m for m in r["holdout_confidence_reasons"])

    def test_short_holdout_is_low(self):
        # single regime, no crossing, but the holdout is below the obs floor -> LOW.
        panel, sig, names, boundary = _panel_tv("persistent", boundary_idx=390)
        r = run_modc(panel, _VecSignal(sig, names, "short-hold"), _spec(boundary), DialConfig())
        assert 0 < r["n_holdout_obs"] < config.HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE
        assert r["holdout_confidence"] is HoldoutConfidence.LOW
        assert any("structurally underpowered" in m for m in r["holdout_confidence_reasons"])
