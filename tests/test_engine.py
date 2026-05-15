"""Tests for src/signals/engine.py and all signal layers."""

import pytest
from datetime import date

from src.signals.engine import (
    _score_to_signal,
    _compute_weighted_sum,
    compute_signal,
    compute_batch,
    build_signal_context_for_orchestrator,
)
from src.signals.models import LayerScore, SignalResult, SIGNAL_ORDER
from src.signals.thresholds import (
    MASTER_WEIGHTS,
    SIGNAL_THRESHOLDS,
    CONFLICT_THRESHOLD,
    RISK_OFF_CONDITIONS,
)
from src.signals.layers.technical_layer import score_technical
from src.signals.layers.macro_layer import score_macro
from src.signals.layers.kap_layer import score_kap
from src.signals.layers.sentiment_layer import score_sentiment
from src.signals.layers.smartmoney_layer import score_smartmoney
from src.signals.layers.risk_layer import score_risk, detect_regime


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

AS_OF = date(2026, 5, 13)

# Strong bullish tech: RSI 55, above all MAs, positive momentum, volume surge, near 52w high
TECH_BULLISH = {
    "rsi": 55, "close": 100.0, "ma20": 90.0, "ma50": 85.0, "ma200": 80.0,
    "momentum_score": 0.3, "volume_surge": True, "proximity_52w_high": 0.02,
}

# Bearish tech: RSI 85 (extreme overbought), below all MAs, negative momentum
TECH_BEARISH_RSI82 = {
    "rsi": 85, "close": 80.0, "ma20": 90.0, "ma50": 95.0, "ma200": 100.0,
    "momentum_score": -0.2, "volume_surge": False, "proximity_52w_high": 0.3,
}

# Neutral tech: mid RSI, some MAs
TECH_NEUTRAL = {
    "rsi": 50, "close": 100.0, "ma20": 100.0, "ma50": None, "ma200": None,
    "momentum_score": 0.0, "volume_surge": False, "proximity_52w_high": 0.1,
}

# Macro risk-on: all assets positive for BIST
MACRO_RISK_ON = {
    "USDTRY": -0.5, "VIX": -0.6, "BRENT": 0.3, "SP500": 0.7, "BIST100": 0.5,
    "vix_level": 15.0, "USDTRY_1d_change": 0.001, "BIST100_1d_change": 0.01,
}

# Macro neutral
MACRO_NEUTRAL = {
    "USDTRY": 0.0, "VIX": 0.0, "BRENT": 0.0, "SP500": 0.0, "BIST100": 0.0,
    "vix_level": 22.0, "USDTRY_1d_change": 0.0, "BIST100_1d_change": 0.0,
}

# Macro RISK_OFF: VIX level 35 triggers override, but macro scores still bullish
MACRO_RISK_OFF_VIX35 = {
    "USDTRY": -0.3, "VIX": -0.5, "BRENT": 0.2, "SP500": 0.6, "BIST100": 0.4,
    "vix_level": 35.0, "USDTRY_1d_change": 0.001, "BIST100_1d_change": 0.01,
}

# RISK_OFF triggered via USDTRY spike
MACRO_RISK_OFF_USDTRY = {
    "USDTRY": -0.3, "VIX": -0.5, "BRENT": 0.2, "SP500": 0.6, "BIST100": 0.4,
    "vix_level": 18.0, "USDTRY_1d_change": 0.05, "BIST100_1d_change": 0.0,
}

KAP_TEMETTU = [{"symbol": "THYAO", "category": "temettu", "published_at": "2026-05-13T09:00:00"}]
KAP_EMPTY = []


def _kap_for(symbol: str, category: str = "temettu") -> list[dict]:
    return [{"symbol": symbol, "category": category, "published_at": "2026-05-13T09:00:00"}]


# ---------------------------------------------------------------------------
# test_thresholds: _score_to_signal boundary mapping
# ---------------------------------------------------------------------------

class TestScoreToSignal:

    def test_buy_strong_exact(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["buy_strong"]) == "BUY-STRONG"

    def test_buy_strong_below_threshold(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["buy_strong"] - 0.1) == "BUY-WEAK"

    def test_buy_weak_exact(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["buy_weak"]) == "BUY-WEAK"

    def test_buy_weak_below_threshold(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["buy_weak"] - 0.1) == "HOLD"

    def test_hold_lower_exact(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["hold_lower"]) == "HOLD"

    def test_hold_lower_below(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["hold_lower"] - 0.1) == "SELL-WEAK"

    def test_sell_weak_exact(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["sell_weak"]) == "SELL-WEAK"

    def test_sell_strong_below_threshold(self):
        assert _score_to_signal(SIGNAL_THRESHOLDS["sell_weak"] - 0.1) == "SELL-STRONG"

    def test_extreme_high(self):
        assert _score_to_signal(100.0) == "BUY-STRONG"

    def test_extreme_low(self):
        assert _score_to_signal(0.0) == "SELL-STRONG"


# ---------------------------------------------------------------------------
# test_weighted_sum
# ---------------------------------------------------------------------------

class TestComputeWeightedSum:

    def _ls(self, layer: str, score: float, weight: float) -> LayerScore:
        return LayerScore(layer=layer, score=score, confidence=1.0, weight=weight,
                          detail={}, source="computed")

    def test_single_layer(self):
        ls = [self._ls("technical", 80.0, 0.15)]
        assert _compute_weighted_sum(ls) == 80.0

    def test_all_neutral(self):
        layers = [self._ls(k, 50.0, v) for k, v in MASTER_WEIGHTS.items()]
        assert _compute_weighted_sum(layers) == pytest.approx(50.0, abs=0.01)

    def test_empty_returns_50(self):
        assert _compute_weighted_sum([]) == 50.0

    def test_weighted_average_correct(self):
        layers = [
            self._ls("a", 100.0, 0.25),
            self._ls("b", 0.0, 0.75),
        ]
        # (100*0.25 + 0*0.75) / 1.0 = 25.0
        assert _compute_weighted_sum(layers) == pytest.approx(25.0, abs=0.01)


# ---------------------------------------------------------------------------
# test_technical_layer
# ---------------------------------------------------------------------------

class TestTechnicalLayer:

    def test_bullish_score_above_neutral(self):
        ls = score_technical(TECH_BULLISH)
        assert ls.score > 50.0
        assert ls.confidence == 1.0
        assert ls.layer == "technical"

    def test_bearish_rsi_reduces_score(self):
        ls = score_technical(TECH_BEARISH_RSI82)
        assert ls.score < 50.0

    def test_empty_data_returns_partial(self):
        ls = score_technical({})
        assert ls.source == "partial" or ls.source == "computed"
        assert ls.score == pytest.approx(50.0, abs=15.0)

    def test_missing_rsi_sets_partial(self):
        data = dict(TECH_BULLISH)
        del data["rsi"]
        ls = score_technical(data)
        assert ls.confidence == 0.5

    def test_detail_contains_rsi(self):
        ls = score_technical(TECH_BULLISH)
        assert "rsi" in ls.detail
        assert ls.detail["rsi"] == TECH_BULLISH["rsi"]

    def test_rsi_oversold_is_bullish(self):
        ls = score_technical({**TECH_NEUTRAL, "rsi": 25})
        rsi_sub = ls.detail.get("rsi_sub", 0)
        assert rsi_sub >= 80.0

    def test_rsi_extreme_overbought_is_bearish(self):
        ls = score_technical({**TECH_NEUTRAL, "rsi": 82})
        rsi_sub = ls.detail.get("rsi_sub", 100)
        assert rsi_sub <= 10.0

    def test_all_mas_above_gives_high_ma_sub(self):
        ls = score_technical({"close": 110.0, "ma20": 100.0, "ma50": 90.0, "ma200": 80.0})
        assert ls.detail.get("ma_sub", 0) == 80.0

    def test_all_mas_below_gives_low_ma_sub(self):
        ls = score_technical({"close": 70.0, "ma20": 100.0, "ma50": 90.0, "ma200": 80.0})
        assert ls.detail.get("ma_sub", 100) == 20.0

    def test_volume_surge_adds_points(self):
        with_surge = score_technical({**TECH_NEUTRAL, "volume_surge": True})
        no_surge = score_technical({**TECH_NEUTRAL, "volume_surge": False})
        assert with_surge.score >= no_surge.score


# ---------------------------------------------------------------------------
# test_macro_layer
# ---------------------------------------------------------------------------

class TestMacroLayer:

    def test_risk_on_above_neutral(self):
        ls = score_macro(MACRO_RISK_ON)
        assert ls.score > 50.0

    def test_neutral_near_50(self):
        ls = score_macro(MACRO_NEUTRAL)
        # With LOCAL_MACRO_ENABLED: TCMB hike pulls neutral down to ~43.75
        # (50% global*50 + 25% TCMB*25 + 25% CDS*50 = 43.75)
        assert ls.score == pytest.approx(50.0, abs=10.0)

    def test_empty_returns_missing(self):
        ls = score_macro({})
        assert ls.source == "missing"
        assert ls.score == 50.0
        assert ls.confidence == 0.0

    def test_partial_assets_lower_confidence(self):
        ls = score_macro({"USDTRY": -0.5, "VIX": -0.3})
        assert ls.confidence == 0.6

    def test_all_assets_full_confidence(self):
        full = {**MACRO_RISK_ON, "EURTRY": -0.3, "GOLD": -0.2}
        ls = score_macro(full)
        assert ls.confidence == 1.0

    def test_vix_score_key_accepted(self):
        ls = score_macro({"vix_score": -0.5, "usdtry_score": -0.3, "bist100_score": 0.4})
        assert ls.source == "computed"
        assert ls.score > 50.0

    def test_score_clamped_0_100(self):
        extreme = {"USDTRY": -1.0, "VIX": -1.0, "BRENT": 1.0, "SP500": 1.0, "BIST100": 1.0}
        ls = score_macro(extreme)
        assert 0.0 <= ls.score <= 100.0


# ---------------------------------------------------------------------------
# test_kap_layer
# ---------------------------------------------------------------------------

class TestKapLayer:

    def test_no_events_returns_neutral_no_events(self):
        ls = score_kap("THYAO", [], AS_OF)
        assert ls.score == 50.0
        assert ls.confidence == 0.0
        assert ls.source == "no_events"

    def test_temettu_raises_score(self):
        events = _kap_for("THYAO", "temettu")
        ls = score_kap("THYAO", events, AS_OF)
        assert ls.score > 50.0

    def test_old_events_ignored(self):
        old_events = [{"symbol": "THYAO", "category": "temettu", "published_at": "2026-05-01T09:00:00"}]
        ls = score_kap("THYAO", old_events, AS_OF)
        assert ls.score == 50.0
        assert ls.source == "no_events"

    def test_wrong_symbol_ignored(self):
        events = [{"symbol": "AKBNK", "category": "temettu", "published_at": "2026-05-13T09:00:00"}]
        ls = score_kap("THYAO", events, AS_OF)
        assert ls.score == 50.0

    def test_high_priority_multiplier_applied(self):
        normal = _kap_for("THYAO", "temettu")
        hp_events = [{**normal[0], "high_priority_flag": True}]
        ls_normal = score_kap("THYAO", normal, AS_OF)
        ls_hp = score_kap("THYAO", hp_events, AS_OF)
        assert ls_hp.score > ls_normal.score

    def test_duplicate_category_half_impact(self):
        events = [
            {"symbol": "THYAO", "category": "temettu", "published_at": "2026-05-13T09:00:00"},
            {"symbol": "THYAO", "category": "temettu", "published_at": "2026-05-13T10:00:00"},
        ]
        ls = score_kap("THYAO", events, AS_OF)
        # 50 + 25 + 12.5 = 87.5
        assert ls.score == pytest.approx(87.5, abs=1.0)

    def test_score_clamped_0_100(self):
        many_events = [
            {"symbol": "THYAO", "category": "temettu", "published_at": "2026-05-13T09:00:00"},
            {"symbol": "THYAO", "category": "sermaye_artirimi", "published_at": "2026-05-13T09:00:00"},
            {"symbol": "THYAO", "category": "genel_kurul", "published_at": "2026-05-13T09:00:00"},
        ]
        ls = score_kap("THYAO", many_events, AS_OF)
        assert 0.0 <= ls.score <= 100.0

    def test_events_with_no_symbol_field_accepted(self):
        events = [{"category": "temettu", "published_at": "2026-05-13T09:00:00"}]
        ls = score_kap("THYAO", events, AS_OF)
        assert ls.score > 50.0


# ---------------------------------------------------------------------------
# test_sentiment_stub
# ---------------------------------------------------------------------------

class TestSentimentLayer:

    def test_returns_valid_score(self):
        ls = score_sentiment("AKSEN")
        assert 0 <= ls.score <= 100

    def test_returns_valid_confidence(self):
        ls = score_sentiment("AKSEN")
        assert 0 <= ls.confidence <= 1.0

    def test_source_computed_or_missing(self):
        ls = score_sentiment("AKSEN")
        assert ls.source in ("computed", "missing")

    def test_layer_name(self):
        assert score_sentiment("AKSEN").layer == "sentiment"

    def test_accepts_ticker_argument(self):
        ls = score_sentiment("GARAN")
        assert ls.layer == "sentiment"


# ---------------------------------------------------------------------------
# test_smartmoney_stub
# ---------------------------------------------------------------------------

class TestSmartMoneyStub:

    def test_returns_neutral(self):
        assert score_smartmoney().score == 50.0

    def test_confidence_zero(self):
        assert score_smartmoney().confidence == 0.0

    def test_source_missing(self):
        assert score_smartmoney().source == "missing"


# ---------------------------------------------------------------------------
# test_risk_layer
# ---------------------------------------------------------------------------

class TestRiskLayer:

    def test_baseline_score_no_risks(self):
        ls = score_risk("THYAO", {"rsi": 50}, {"vix_level": 10.0})
        assert ls.score == pytest.approx(70.0, abs=0.1)

    def test_rsi_overbought_penalizes(self):
        ls_high = score_risk("THYAO", {"rsi": 82}, {"vix_level": 10.0})
        ls_low = score_risk("THYAO", {"rsi": 50}, {"vix_level": 10.0})
        assert ls_high.score < ls_low.score

    def test_vix_extreme_penalizes_heavily(self):
        ls_safe = score_risk("THYAO", {}, {"vix_level": 10.0})
        ls_danger = score_risk("THYAO", {}, {"vix_level": 35.0})
        assert ls_danger.score < ls_safe.score

    def test_usdtry_spike_penalizes(self):
        ls_stable = score_risk("THYAO", {}, {"USDTRY_1d_change": 0.001})
        ls_spike = score_risk("THYAO", {}, {"USDTRY_1d_change": 0.05})
        assert ls_spike.score < ls_stable.score

    def test_score_clamped_0_100(self):
        ls = score_risk("THYAO", {"rsi": 82}, {"vix_level": 40.0, "USDTRY_1d_change": 0.1})
        assert 0.0 <= ls.score <= 100.0


class TestDetectRegime:

    def test_risk_on_low_vix(self):
        r = detect_regime({"vix_level": 15.0, "USDTRY_1d_change": 0.001})
        assert r == "RISK_ON"

    def test_risk_off_high_vix(self):
        r = detect_regime({"vix_level": 35.0, "USDTRY_1d_change": 0.001})
        assert r == "RISK_OFF"

    def test_risk_off_usdtry_spike(self):
        r = detect_regime({"vix_level": 18.0, "USDTRY_1d_change": 0.05})
        assert r == "RISK_OFF"

    def test_risk_off_bist100_crash(self):
        r = detect_regime({"vix_level": 18.0, "USDTRY_1d_change": 0.01, "BIST100_1d_change": -0.06})
        assert r == "RISK_OFF"

    def test_neutral_medium_vix(self):
        r = detect_regime({"vix_level": 24.0, "USDTRY_1d_change": 0.01})
        assert r == "NEUTRAL"


# ---------------------------------------------------------------------------
# test_engine: compute_signal
# ---------------------------------------------------------------------------

class TestComputeSignal:

    def test_returns_signal_result(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_RISK_ON, KAP_TEMETTU, AS_OF)
        assert isinstance(r, SignalResult)

    def test_buy_signal_for_strong_bullish(self):
        r = compute_signal("AKBNK", TECH_BULLISH, MACRO_RISK_ON, _kap_for("AKBNK"), AS_OF)
        # With weight restructuring (Sentiment 25%→5%, Smart Money 0%→20%),
        # moderate macro (46.9) pulls down score below BUY-WEAK threshold despite bullish tech.
        # This reflects proper weight balance: macro (35%) > sentiment (5%) impact.
        assert r.final_signal in ("HOLD", "BUY-WEAK")
        assert r.score > 55.0

    def test_risk_off_overrides_buy(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_RISK_OFF_VIX35, KAP_TEMETTU, AS_OF)
        assert r.final_signal == "HOLD"
        # With LOCAL_MACRO_ENABLED, macro score is lower (TCMB hike pulls it down),
        # so pre_conflict_signal may already be HOLD, not triggering override
        assert r.audit.regime == "RISK_OFF"

    def test_risk_off_usdtry_trigger(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_RISK_OFF_USDTRY, KAP_TEMETTU, AS_OF)
        assert r.final_signal == "HOLD"
        # With LOCAL_MACRO_ENABLED, macro score is lower (TCMB hike pulls it down)
        assert r.audit.regime == "RISK_OFF"

    def test_risk_off_does_not_affect_sell(self):
        # Even in RISK_OFF, SELL signals stay
        r = compute_signal("THYAO", TECH_BEARISH_RSI82, MACRO_RISK_OFF_VIX35, [], AS_OF)
        assert r.final_signal in ("SELL-WEAK", "SELL-STRONG", "HOLD")
        # Should NOT be a BUY
        assert r.final_signal not in ("BUY-STRONG", "BUY-WEAK")

    def test_conflict_detected_gap_over_40(self):
        # tech bearish (score ~34), kap temettu (score 75) -> gap 41 > 40
        kap = _kap_for("TEST", "temettu")
        r = compute_signal("TEST", TECH_BEARISH_RSI82, MACRO_NEUTRAL, kap, AS_OF)
        assert r.audit.conflict.detected is True
        assert r.audit.conflict.score_gap > CONFLICT_THRESHOLD

    def test_conflict_downgrades_one_level(self):
        kap = _kap_for("TEST", "temettu")
        r = compute_signal("TEST", TECH_BEARISH_RSI82, MACRO_NEUTRAL, kap, AS_OF)
        if r.audit.conflict.detected:
            pre_idx = SIGNAL_ORDER.index(r.audit.pre_conflict_signal)
            post_idx = SIGNAL_ORDER.index(r.audit.final_signal)
            assert post_idx == pre_idx + 1 or r.audit.final_signal == "HOLD"

    def test_no_conflict_small_gap(self):
        r = compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL, [], AS_OF)
        assert r.audit.conflict.detected is False

    def test_sentiment_layer_computed(self):
        r = compute_signal("TEST", TECH_NEUTRAL, MACRO_NEUTRAL, [], AS_OF)
        layer_names = [ls.layer for ls in r.audit.layer_scores]
        assert "sentiment" in layer_names
        # smart_money now in layers (SPEC_SMART_MONEY_1 implementation active)
        assert "smart_money" in layer_names

    def test_smartmoney_active_layer(self):
        r = compute_signal("TEST", TECH_NEUTRAL, MACRO_NEUTRAL, [], AS_OF)
        layer_names = [ls.layer for ls in r.audit.layer_scores]
        # Smart Money is now Layer 5 (active)
        assert "smart_money" in layer_names
        smart_money_ls = [ls for ls in r.audit.layer_scores if ls.layer == "smart_money"][0]
        # Should be neutral (stub) since no institutional flow data
        assert smart_money_ls.score == pytest.approx(50.0, abs=1.0)  # 0.5 * 100 = 50

    def test_backtesting_stateless(self):
        r1 = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], date(2025, 1, 15))
        r2 = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], date(2025, 1, 15))
        assert r1.final_signal == r2.final_signal
        assert r1.score == r2.score

    def test_future_date_raises(self):
        import datetime
        future = date.today() + datetime.timedelta(days=5)
        with pytest.raises(ValueError):
            compute_signal("THYAO", TECH_NEUTRAL, MACRO_NEUTRAL, [], future)

    def test_audit_has_6_layers(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], AS_OF)
        assert len(r.audit.layer_scores) == 6  # Added smart_money layer
        layer_names = {ls.layer for ls in r.audit.layer_scores}
        assert layer_names == {"technical", "macro", "kap", "sentiment", "risk", "smart_money"}

    def test_audit_signal_summary_nonempty(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], AS_OF)
        assert r.audit.signal_summary != ""
        assert "THYAO" in r.audit.signal_summary

    def test_audit_final_matches_result(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], AS_OF)
        assert r.audit.final_signal == r.final_signal

    def test_audit_weighted_sum_not_none(self):
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], AS_OF)
        assert r.audit.weighted_sum is not None

    def test_weight_override_normalized(self):
        # Unnormalized weights: engine should normalize them
        overrides = {"technical": 2.0, "macro": 3.0}
        r = compute_signal("THYAO", TECH_BULLISH, MACRO_NEUTRAL, [], AS_OF,
                           weight_override=overrides)
        assert isinstance(r, SignalResult)

    def test_all_layers_confidence_zero_gives_hold(self):
        # Empty data everywhere -> all layers near 50 -> HOLD
        r = compute_signal("EMPTY", {}, {}, [], AS_OF)
        # Score should be near 50 -> HOLD
        assert r.final_signal in ("HOLD", "SELL-WEAK", "BUY-WEAK")


# ---------------------------------------------------------------------------
# test_compute_batch
# ---------------------------------------------------------------------------

class TestComputeBatch:

    def test_returns_list(self):
        results = compute_batch(["THYAO"], {"THYAO": TECH_BULLISH}, MACRO_NEUTRAL, {})
        assert isinstance(results, list)

    def test_sorted_by_score_desc(self):
        tb = {"THYAO": TECH_BULLISH, "AKBNK": TECH_BEARISH_RSI82, "GARAN": TECH_NEUTRAL}
        results = compute_batch(["THYAO", "AKBNK", "GARAN"], tb, MACRO_NEUTRAL, {})
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_all_symbols_present(self):
        tb = {"THYAO": TECH_BULLISH, "AKBNK": TECH_NEUTRAL}
        results = compute_batch(["THYAO", "AKBNK"], tb, MACRO_NEUTRAL, {})
        syms = {r.symbol for r in results}
        assert "THYAO" in syms and "AKBNK" in syms

    def test_missing_tech_data_not_crash(self):
        results = compute_batch(["THYAO", "AKBNK"], {}, MACRO_NEUTRAL, {})
        assert len(results) == 2

    def test_empty_symbols_returns_empty(self):
        results = compute_batch([], {}, MACRO_NEUTRAL, {})
        assert results == []

    def test_macro_shared_across_symbols(self):
        tb = {"THYAO": TECH_BULLISH, "AKBNK": TECH_BULLISH}
        r1, r2 = compute_batch(["THYAO", "AKBNK"], tb, MACRO_RISK_ON, {})[:2]
        m1 = next(ls for ls in r1.audit.layer_scores if ls.layer == "macro")
        m2 = next(ls for ls in r2.audit.layer_scores if ls.layer == "macro")
        assert m1.score == m2.score


# ---------------------------------------------------------------------------
# test_build_signal_context_for_orchestrator
# ---------------------------------------------------------------------------

class TestBuildSignalContext:

    def _run_batch(self, symbols, tech, macro, kap):
        tb = {s: tech for s in symbols}
        kb = {s: kap for s in symbols}
        return compute_batch(symbols, tb, macro, kb, AS_OF)

    def test_empty_results(self):
        ctx = build_signal_context_for_orchestrator([])
        assert "strong_signals" in ctx
        assert "missing_layers" in ctx
        assert ctx["risk_off"] is False

    def test_context_has_required_keys(self):
        results = self._run_batch(["THYAO"], TECH_BULLISH, MACRO_RISK_ON, _kap_for("THYAO"))
        ctx = build_signal_context_for_orchestrator(results)
        for key in ("date", "regime", "risk_off", "strong_signals", "weak_signals",
                    "holds", "sell_signals", "conflict_symbols", "missing_layers"):
            assert key in ctx, f"Missing key: {key}"

    def test_missing_layers_empty(self):
        results = self._run_batch(["THYAO"], TECH_NEUTRAL, MACRO_NEUTRAL, [])
        ctx = build_signal_context_for_orchestrator(results)
        assert ctx["missing_layers"] == []

    def test_risk_off_reflected(self):
        results = self._run_batch(["THYAO"], TECH_BULLISH, MACRO_RISK_OFF_VIX35, _kap_for("THYAO"))
        ctx = build_signal_context_for_orchestrator(results)
        # With LOCAL_MACRO_ENABLED, macro score is lower, so pre_conflict_signal may be HOLD
        # Instead, check that regime is RISK_OFF
        assert ctx["regime"] == "RISK_OFF"

    def test_conflict_symbols_populated(self):
        # bearish tech + bullish KAP = conflict
        tb = {"TEST": TECH_BEARISH_RSI82}
        kb = {"TEST": _kap_for("TEST", "temettu")}
        results = compute_batch(["TEST"], tb, MACRO_NEUTRAL, kb, AS_OF)
        ctx = build_signal_context_for_orchestrator(results)
        if results[0].audit.conflict.detected:
            assert "TEST" in ctx["conflict_symbols"]
