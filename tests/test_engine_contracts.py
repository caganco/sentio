"""Tier-A (synthetic, CI-green) tests for src/engine contracts + PM-1 guard."""
from __future__ import annotations

import pandas as pd
import pytest

from src.engine.config import (
    AGREEMENT_CROSS_IC_T_MIN,
    NW_LAG_DAILY,
    NW_LAG_MONTHLY,
    PBO_THRESHOLD,
)
from src.engine.contracts import (
    CutPolicy,
    DialConfig,
    EngineOutput,
    Frequency,
    Panel,
    ReturnBasis,
    SplitMode,
    SplitSpec,
)
from src.engine.signal_protocol import PM1Violation, Signal, assert_pm1_compliant


class TestSplitSpec:
    def test_valid_daily_name(self):
        s = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY)
        assert s.embargo_h == 1
        assert s.cpcv_k < s.cpcv_n

    def test_embargo_floor(self):
        with pytest.raises(ValueError, match="embargo_h"):
            SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.DAILY, embargo_h=0)

    def test_cpcv_k_lt_n(self):
        with pytest.raises(ValueError, match="cpcv_k"):
            SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.DAILY, cpcv_n=2, cpcv_k=2)

    def test_monthly_requires_mod_a(self):
        with pytest.raises(ValueError, match="monthly"):
            SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.MONTHLY)
        with pytest.raises(ValueError, match="monthly"):
            SplitSpec(split_mode=SplitMode.PANEL, frequency=Frequency.MONTHLY)
        # Mod-A monthly is allowed (name-split carries the load).
        SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.MONTHLY)


class TestDialConfig:
    def test_defaults_match_frozen_spec(self):
        d = DialConfig()
        assert d.psi == "spearman"
        assert d.neutralization == ("market",)
        assert d.pbo_max == PBO_THRESHOLD
        assert d.agreement_t_min == AGREEMENT_CROSS_IC_T_MIN
        assert CutPolicy.EXPANDING in d.cut_policies
        assert d.return_basis is ReturnBasis.TR_GROSS

    def test_unknown_factor_rejected(self):
        with pytest.raises(ValueError, match="unknown neutralization"):
            DialConfig(neutralization=("market", "momentum"))

    def test_empty_neutralization_rejected(self):
        with pytest.raises(ValueError, match="market is the minimum"):
            DialConfig(neutralization=())

    def test_winsorize_bounds_validated(self):
        with pytest.raises(ValueError, match="winsorize"):
            DialConfig(winsorize=(0.9, 0.1))

    def test_nw_lag_resolution(self):
        d = DialConfig()
        assert d.nw_lag_for(Frequency.DAILY) == NW_LAG_DAILY
        assert d.nw_lag_for(Frequency.MONTHLY) == NW_LAG_MONTHLY
        assert DialConfig(nw_lag=7).nw_lag_for(Frequency.DAILY) == 7

    def test_market_neutralization_mandatory_for_mod_a(self):
        d = DialConfig(neutralization=("size",))  # valid factor, but no market
        with pytest.raises(ValueError, match="market-beta neutralization"):
            d.requires_market_neutralization(SplitMode.NAME)
        # Mod-B (temporal) does not require market-neutralization.
        d.requires_market_neutralization(SplitMode.TEMPORAL)


class TestEngineOutput:
    def test_empty_output_is_valid(self):
        o = EngineOutput()
        assert o.gross_active_ann is None
        assert o.per_regime == {}
        assert o.plateau_map == {}
        assert o.pm1_guard_raised is False
        assert o.guard_messages == ()

    def test_mutable_defaults_not_shared(self):
        a, b = EngineOutput(), EngineOutput()
        a.per_regime["2022"] = {"x": 1.0}
        assert b.per_regime == {}


def _toy_panel() -> Panel:
    dates = pd.bdate_range("2019-01-02", periods=4)
    names = ["A", "B"]
    frame = pd.DataFrame(1.0, index=dates, columns=names)
    series = pd.Series(1.0, index=dates)
    return Panel(
        close=frame,
        tr_gross=frame,
        tr_net=frame,
        value_tl=frame,
        membership={"bist100": frame},
        market=series,
        tufe=series,
        tlref=series,
    )


class TestPanel:
    def test_properties(self):
        p = _toy_panel()
        assert p.names == ["A", "B"]
        assert len(p.dates) == 4
        assert p.frequency is Frequency.DAILY


class TestPM1Guard:
    def test_fully_invested_ok(self):
        assert_pm1_compliant(pd.Series({"A": 0.5, "B": 0.5}))

    def test_idle_zero_ok(self):
        assert_pm1_compliant(pd.Series({"A": 0.0, "B": 0.0}))

    def test_negative_weight_raises(self):
        with pytest.raises(PM1Violation, match="negative weights"):
            assert_pm1_compliant(pd.Series({"A": 1.2, "B": -0.2}))

    def test_cash_gate_raises(self):
        with pytest.raises(PM1Violation, match="cash-gate"):
            assert_pm1_compliant(pd.Series({"A": 0.3, "B": 0.3}))

    def test_runtime_checkable_protocol(self):
        class Mom:
            name = "mom"
            construction_window = 21

            def scores(self, panel, names, asof):
                return pd.Series(0.0, index=names)

        assert isinstance(Mom(), Signal)
