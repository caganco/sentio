"""Tier-A tests for the top-level assembler (TASARIM Section 9 / math-spec Section 7).

The assembler turns (panel, signal, split_spec, dial) into the single EngineOutput
vector. These tests pin:
- the tradeable returns/cost sub-vector (gross/net/cost/tax/mean_rt + headline NW-t),
  including the exact net = gross - cost - tax identity and the closed-form tax line;
- the benchmark-floor + per-regime + bounded plateau wiring;
- dispatch by split_mode (A -> Mod-A conjugate fields; B -> Mod-B DSR + proxy PBO;
  A+B -> both legs), with the conjugate verdicts reproducing the Faz-2 moda fixtures;
- the partial-leg contract: a universe too thin to form arms NEVER raises -- it
  records guards and still returns a populated (NaN-where-undefined) vector;
- honest partials: fair-null / mirror / deflated-OOS-t are left None with a note,
  not fabricated.

The synthetic panels reuse the Faz-2 'factor' / 'noise' construction, so the Mod-A
agreement verdict here is the same one the moda fixtures already froze.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.engine.contracts import (
    DialConfig,
    Frequency,
    Panel,
    SplitMode,
    SplitSpec,
)
from src.engine.harness import harness
from src.screening import d203_config as _costcfg

_EXPECTED_TAX_ANN = float(_costcfg.D203_DIV_WITHHOLDING * _costcfg.D203_ASSUMED_ANNUAL_DIV_YIELD)


class _VecSignal:
    """Parameter-free static scorer (same per-name vector every date), h=1."""

    construction_window = 1

    def __init__(self, vec: np.ndarray, names: list[str], name: str) -> None:
        self.name = name
        self._s = pd.Series(np.asarray(vec, dtype=float), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._s.reindex(names)


def _panel(
    kind: str, *, n_names: int = 120, n_dates: int = 300, seed: int = 0
) -> tuple[Panel, np.ndarray, list[str]]:
    """Synthetic panel + signal vector (mirrors the Faz-2 moda fixtures).

    ``factor`` : a static MARKET-NEUTRAL loading drives the residual return; the
                 signal IS that loading -> a real conjugate edge.
    ``noise``  : returns independent of the signal -> conjugate test must fail.
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

    if kind == "factor":
        daily = beta[None, :] * mkt_ret[:, None] + 0.0025 * f[None, :] + idio
        sig = f
    elif kind == "noise":
        daily, sig = idio, f
    else:  # pragma: no cover - guard
        raise ValueError(kind)

    tr = pd.DataFrame(100.0 * np.cumprod(1.0 + daily, axis=0), index=dates, columns=names)
    value_tl = pd.DataFrame(
        np.tile(1e8 * (1.0 + np.arange(n_names) / n_names), (n_dates, 1)),
        index=dates, columns=names,
    )
    one = pd.Series(1.0, index=dates)  # flat TUFE/TLREF -> 0 deflator, 0 floor
    panel = Panel(
        close=tr.copy(), tr_gross=tr, tr_net=tr, value_tl=value_tl,
        membership={}, market=market, tufe=one, tlref=one, frequency=Frequency.DAILY,
    )
    return panel, sig, names


def _spec(mode: SplitMode = SplitMode.NAME) -> SplitSpec:
    return SplitSpec(split_mode=mode, frequency=Frequency.DAILY, seed=0)


@pytest.fixture(scope="module")
def factor_out():
    panel, sig, names = _panel("factor")
    return harness(panel, _VecSignal(sig, names, "factor"), _spec(), DialConfig())


# --------------------------------------------------------------------------- #
# returns / cost sub-vector                                                   #
# --------------------------------------------------------------------------- #
class TestReturnsCost:
    def test_subvector_populated(self, factor_out):
        o = factor_out
        assert o.split_mode == "A"
        assert o.n_names == 120
        assert o.n_obs is not None and o.n_obs > 0
        assert np.isfinite(o.gross_active_ann)
        assert np.isfinite(o.cost_ann) and o.cost_ann >= 0.0
        assert np.isfinite(o.mean_rt_bps) and o.mean_rt_bps > 0.0
        assert np.isfinite(o.nw_t)

    def test_tax_is_closed_form_dividend_withholding(self, factor_out):
        assert factor_out.tax_ann == pytest.approx(_EXPECTED_TAX_ANN)

    def test_net_equals_gross_minus_cost_minus_tax(self, factor_out):
        o = factor_out
        assert o.net_active_ann == pytest.approx(o.gross_active_ann - o.cost_ann - o.tax_ann)


# --------------------------------------------------------------------------- #
# benchmark floor + per-regime + bounded plateau                              #
# --------------------------------------------------------------------------- #
class TestRelativeAndRegime:
    def test_benchmark_floor_wired(self, factor_out):
        o = factor_out
        # flat TUFE/TLREF (level == 1.0 throughout, window predates 2022-07) ->
        # deflator 0, TUFE-only floor 0, no guard.
        assert o.real_active_ann is not None and np.isfinite(o.real_active_ann)
        assert o.benchmark_floor_ann == pytest.approx(0.0)
        assert o.real_active_ann == pytest.approx(o.net_active_ann)  # 0% deflator
        assert isinstance(o.beats_benchmark_floor, bool)

    def test_per_regime_partitions_the_active_series(self, factor_out):
        o = factor_out
        assert set(o.per_regime) <= {"pre_2022", "post_2022"}
        assert o.per_regime  # the 2021-2022 span straddles the 2022-01-01 cut
        total = sum(int(v["n_obs"]) for v in o.per_regime.values())
        assert total == o.n_obs
        for v in o.per_regime.values():
            assert np.isfinite(v["active_ann"])

    def test_plateau_map_is_bounded_2x2(self, factor_out):
        o = factor_out
        assert set(o.plateau_map) == {"tercile_h1", "tercile_h2", "decile_h1", "decile_h2"}
        assert all(np.isfinite(v) for v in o.plateau_map.values())


# --------------------------------------------------------------------------- #
# leg dispatch + conjugate passthrough (verdicts match the Faz-2 fixtures)     #
# --------------------------------------------------------------------------- #
class TestLegDispatch:
    def test_moda_conjugate_passthrough_on_factor(self, factor_out):
        o = factor_out
        assert o.agreement_pass is True
        assert o.agreement_t_cross_median > 2.0
        assert o.sign_consistency >= 0.90
        assert o.pbo < 0.50
        assert o.residual_corr_flag is False
        assert o.dsr is None  # Mod-A-only: DSR is the Mod-B measure

    def test_noise_does_not_pass(self):
        panel, sig, names = _panel("noise")
        o = harness(panel, _VecSignal(sig, names, "noise"), _spec(), DialConfig())
        assert o.agreement_pass is False

    def test_modb_only_gives_dsr_and_proxy_pbo(self):
        panel, sig, names = _panel("factor")
        o = harness(panel, _VecSignal(sig, names, "factor"), _spec(SplitMode.TEMPORAL), DialConfig())
        assert o.split_mode == "B"
        assert o.agreement_pass is None       # no Mod-A leg
        assert o.dsr is not None
        assert o.pbo is not None              # Mod-B simplified proxy
        assert any("proxy" in n for n in o.notes)

    def test_panel_mode_runs_both_legs(self):
        panel, sig, names = _panel("factor")
        o = harness(panel, _VecSignal(sig, names, "factor"), _spec(SplitMode.PANEL), DialConfig())
        assert o.split_mode == "A+B"
        assert o.agreement_pass is not None   # Mod-A
        assert o.dsr is not None              # Mod-B


# --------------------------------------------------------------------------- #
# honest partials + partial-leg robustness                                    #
# --------------------------------------------------------------------------- #
class TestHonestyAndRobustness:
    def test_unproduced_fields_are_none_with_notes(self, factor_out):
        o = factor_out
        assert o.null_percentile is None
        assert o.mirror_active_ann is None
        assert o.deflated_oos_t is None
        joined = " ".join(o.notes)
        assert "null_percentile" in joined and "deflated_oos_t" in joined

    def test_thin_universe_never_raises(self):
        # 20 names: below the 30-name cross-section floor (empty tilt) AND below the
        # arm floor (Mod-A cannot form 50-name arms). The assembler must record guards
        # and still return a valid object -- never raise.
        panel, sig, names = _panel("factor", n_names=20)
        o = harness(panel, _VecSignal(sig, names, "factor"), _spec(), DialConfig())
        assert o.n_obs == 0
        assert len(o.guard_messages) >= 1
        assert o.gross_active_ann is None or np.isnan(o.gross_active_ann)


# --------------------------------------------------------------------------- #
# FAZ-4 (b): Stage-0 tried-config count threads into the DSR deflation          #
# --------------------------------------------------------------------------- #
def _stage0_doc(n_trials: int) -> dict:
    """Minimal valid Stage-0 freeze (mirrors test_engine_stage0._valid_doc)."""
    return {
        "prototip_id": "RR-Y1-005-faz4-toy",
        "hipotez": "toy",
        "tutunma_noktasi": "cross_sectional",
        "split_modu": "A",
        "psi": "rank_ic",
        "faktor_notrleme": ["market"],
        "embargo_h": "construction_window",
        "split_arm_floor": 1e7,
        "sort_depth": "tercile",
        "hedef_rejim": "agnostic",
        "frekans": "daily",
        "getiri_tabani": "total_return",
        "keep_bar": {"pbo_max": 0.5, "dsr_min": 0.95},
        "denenen_konfig_sayisi": n_trials,
        "frozen_before_results": True,
        "date_frozen": "2026-06-05",
        "snapshots_content_hash_sha256_prefix": "",
        "strangler_constraints": "committed-motorlar-dokunulmaz",
    }


class TestStage0TrialBinding:
    def test_stage0_n_trials_surfaces_on_dsr_field(self, tmp_path):
        p = tmp_path / "stage0.json"
        p.write_text(json.dumps(_stage0_doc(25)), encoding="utf-8")
        panel, sig, names = _panel("factor")
        o = harness(
            panel, _VecSignal(sig, names, "factor"),
            _spec(SplitMode.TEMPORAL), DialConfig(), stage0_path=p,
        )
        assert o.dsr_n_trials == 25       # honest count is visible/auditable
        assert o.dsr is not None
        assert any("N=25" in n for n in o.notes)  # DSR-layer-not-bucket-PBO note

    def test_no_stage0_defaults_to_single_trial(self):
        panel, sig, names = _panel("factor")
        o = harness(panel, _VecSignal(sig, names, "factor"), _spec(SplitMode.TEMPORAL), DialConfig())
        assert o.dsr_n_trials == 1        # default -> no deflation
