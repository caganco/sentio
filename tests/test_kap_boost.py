"""Tests for D-131 (CB-004): KAP L3 event-triggered weight boost.

KAP filings are episodic, so the kap layer's flat MASTER_WEIGHTS["kap"] (0.30)
over-counts quiet days. compute_signal() applies a per-call multiplier to the
kap layer's effective weight:
  - relevant event in KAP_BOOST_CATEGORIES -> KAP_EVENT_BOOST_MULTIPLIER (1.4)
  - some relevant event but none boost-worthy -> 1.0 (neutral)
  - no relevant event in window            -> KAP_NO_EVENT_MULTIPLIER (0.7)

MASTER_WEIGHTS is never mutated; only the per-call local weight is scaled.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.signals.engine import compute_signal
from src.signals.models import SignalResult
from src.signals.thresholds import (
    KAP_EVENT_BOOST_MULTIPLIER,
    KAP_NO_EVENT_MULTIPLIER,
    MASTER_WEIGHTS,
)

AS_OF = date(2026, 5, 13)

TECH_NEUTRAL = {
    "rsi": 50, "close": 100.0, "ma20": 100.0, "ma50": None, "ma200": None,
    "momentum_score": 0.0, "volume_surge": False, "proximity_52w_high": 0.1,
}
MACRO_NEUTRAL = {
    "USDTRY": 0.0, "VIX": 0.0, "BRENT": 0.0, "SP500": 0.0, "BIST100": 0.0,
    "vix_level": 22.0, "USDTRY_1d_change": 0.0, "BIST100_1d_change": 0.0,
}

_KAP_BASE = MASTER_WEIGHTS["kap"]


def _kap_for(symbol: str, category: str = "temettu",
             published_at: str = "2026-05-13T09:00:00") -> list[dict]:
    return [{"symbol": symbol, "category": category, "published_at": published_at}]


def _kap_layer(r: SignalResult):
    return [ls for ls in r.audit.layer_scores if ls.layer == "kap"][0]


def _kap_weight(symbol: str, kap_events: list[dict]) -> float:
    r = compute_signal(symbol, TECH_NEUTRAL, MACRO_NEUTRAL, kap_events, AS_OF)
    return _kap_layer(r).weight


class TestKapEventBoost:

    def test_boost_category_event_raises_kap_weight(self):
        assert _kap_weight("THYAO", _kap_for("THYAO", "temettu")) > _KAP_BASE

    def test_boost_weight_exact(self):
        w = _kap_weight("THYAO", _kap_for("THYAO", "temettu"))
        assert w == pytest.approx(_KAP_BASE * KAP_EVENT_BOOST_MULTIPLIER)

    def test_no_event_lowers_kap_weight(self):
        assert _kap_weight("THYAO", []) < _KAP_BASE

    def test_no_event_weight_exact(self):
        w = _kap_weight("THYAO", [])
        assert w == pytest.approx(_KAP_BASE * KAP_NO_EVENT_MULTIPLIER)

    def test_non_boost_category_neutral(self):
        # "diger" is a relevant event but not in KAP_BOOST_CATEGORIES -> x1.0
        w = _kap_weight("THYAO", _kap_for("THYAO", "diger"))
        assert w == pytest.approx(_KAP_BASE)

    def test_pay_sahipligi_triggers_boost(self):
        w = _kap_weight("THYAO", _kap_for("THYAO", "pay_sahipligi"))
        assert w == pytest.approx(_KAP_BASE * KAP_EVENT_BOOST_MULTIPLIER)

    def test_sermaye_artirimi_triggers_boost(self):
        w = _kap_weight("THYAO", _kap_for("THYAO", "sermaye_artirimi"))
        assert w == pytest.approx(_KAP_BASE * KAP_EVENT_BOOST_MULTIPLIER)

    def test_master_weights_not_mutated(self):
        # D-154: kap renormalized to 0.30/0.97 (~0.3093). Invariant: not mutated by compute_signal.
        before = MASTER_WEIGHTS["kap"]
        compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL,
                       _kap_for("THYAO", "temettu"), AS_OF)
        assert MASTER_WEIGHTS["kap"] == before == pytest.approx(round(0.30 / 0.97, 10))

    def test_weight_multiplier_in_detail(self):
        r = compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL,
                           _kap_for("THYAO", "temettu"), AS_OF)
        assert _kap_layer(r).detail["weight_multiplier"] == KAP_EVENT_BOOST_MULTIPLIER
        r2 = compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL, [], AS_OF)
        assert _kap_layer(r2).detail["weight_multiplier"] == KAP_NO_EVENT_MULTIPLIER

    def test_out_of_window_event_dampens(self):
        # Event 30 days before AS_OF is outside the 3-day window -> no relevant
        # event -> dampen (same as empty).
        old = _kap_for("THYAO", "temettu", published_at="2026-04-13T09:00:00")
        assert _kap_weight("THYAO", old) == pytest.approx(_KAP_BASE * KAP_NO_EVENT_MULTIPLIER)

    def test_boost_changes_composite_vs_no_event(self):
        r_boost = compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL,
                                 _kap_for("THYAO", "temettu"), AS_OF)
        r_none = compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL, [], AS_OF)
        assert r_boost.score != r_none.score
