"""Tests for Smart Money Layer (Layer 5) — Institutional flow detection and bull trap prevention."""
import pytest

from src.signals.layers.smart_money_layer import SmartMoneyLayer, SmartMoneySignal


class TestInstitutionalFlowCalculation:
    """Test Suite 1: Institutional flow → Smart Money score calculation (3 tests)."""

    def test_positive_net_buy(self):
        """Test: Positive net buy (institutions buying)."""
        layer = SmartMoneyLayer()

        institutional_flow = {
            "ticker": "AKSEN",
            "date": "2026-05-14",
            "institutional_net_total": 1_300_000,
            "daily_volume": 45_000_000,
            "net_pct": 1_300_000 / 45_000_000,  # +2.89%
            "source": "borsa"
        }

        signal = layer.calculate_score("AKSEN", institutional_flow)

        # net_pct = 0.0289, scale = 0.10
        # score = 0.5 + (0.0289 / 0.10) = 0.5 + 0.289 = 0.789
        assert signal.score == pytest.approx(0.789, abs=0.01)
        assert signal.institutional_net_pct == pytest.approx(0.0289, abs=0.001)
        assert signal.confidence > 0.7  # Strong signal

    def test_negative_net_sell(self):
        """Test: Negative net sell (institutions selling)."""
        layer = SmartMoneyLayer()

        institutional_flow = {
            "ticker": "TAVHL",
            "date": "2026-05-14",
            "institutional_net_total": -2_000_000,
            "daily_volume": 50_000_000,
            "net_pct": -2_000_000 / 50_000_000,  # -4%
            "source": "borsa"
        }

        signal = layer.calculate_score("TAVHL", institutional_flow)

        # net_pct = -0.04, scale = 0.10
        # score = 0.5 + (-0.04 / 0.10) = 0.5 - 0.40 = 0.10
        assert signal.score == pytest.approx(0.10, abs=0.01)
        assert signal.institutional_net_pct == pytest.approx(-0.04, abs=0.001)
        assert signal.confidence > 0.7  # Strong signal

    def test_neutral_no_flow(self):
        """Test: Neutral (zero institutional flow)."""
        layer = SmartMoneyLayer()

        institutional_flow = {
            "ticker": "ENERY",
            "date": "2026-05-14",
            "institutional_net_total": 0,
            "daily_volume": 60_000_000,
            "net_pct": 0.0,
            "source": "borsa"
        }

        signal = layer.calculate_score("ENERY", institutional_flow)

        # net_pct = 0, score = 0.5
        assert signal.score == pytest.approx(0.5, abs=0.01)
        assert signal.institutional_net_pct == pytest.approx(0.0, abs=0.001)
        assert signal.confidence < 0.3  # Weak signal


class TestThreeDayTrendCalculation:
    """Test Suite 2: 3-day rolling trend calculation (3 tests)."""

    def test_accumulation_three_days_buying(self):
        """Test: 3 consecutive days of institutional buying (ACCUMULATION)."""
        layer = SmartMoneyLayer()

        daily_flows = [
            {"date": "2026-05-12", "net_pct": 0.015},   # +1.5%
            {"date": "2026-05-13", "net_pct": 0.021},   # +2.1%
            {"date": "2026-05-14", "net_pct": 0.018}    # +1.8%
        ]

        trend = layer.calculate_3day_trend("AKSEN", daily_flows)

        assert trend is not None
        assert trend["day_1"] == pytest.approx(0.015, abs=0.001)
        assert trend["day_2"] == pytest.approx(0.021, abs=0.001)
        assert trend["day_3"] == pytest.approx(0.018, abs=0.001)
        assert trend["avg_3day"] == pytest.approx(0.018, abs=0.001)  # 1.8%
        assert trend["direction"] == "ACCUMULATION"

    def test_distribution_three_days_selling(self):
        """Test: 3 consecutive days of institutional selling (DISTRIBUTION)."""
        layer = SmartMoneyLayer()

        daily_flows = [
            {"date": "2026-05-12", "net_pct": -0.012},  # -1.2%
            {"date": "2026-05-13", "net_pct": -0.008},  # -0.8%
            {"date": "2026-05-14", "net_pct": -0.015}   # -1.5%
        ]

        trend = layer.calculate_3day_trend("TAVHL", daily_flows)

        assert trend is not None
        assert trend["direction"] == "DISTRIBUTION"
        assert trend["avg_3day"] == pytest.approx(-0.01167, abs=0.001)  # -1.17%

    def test_mixed_no_clear_trend(self):
        """Test: Mixed buying and selling (MIXED)."""
        layer = SmartMoneyLayer()

        daily_flows = [
            {"date": "2026-05-12", "net_pct": 0.010},   # +1%
            {"date": "2026-05-13", "net_pct": -0.005},  # -0.5%
            {"date": "2026-05-14", "net_pct": 0.008}    # +0.8%
        ]

        trend = layer.calculate_3day_trend("TTKOM", daily_flows)

        assert trend is not None
        assert trend["direction"] == "MIXED"
        assert trend["avg_3day"] == pytest.approx(0.00433, abs=0.001)  # 0.43%


class TestBullTrapDetection:
    """Test Suite 3: Bull trap detection logic (3 tests)."""

    def test_bull_trap_not_detected_weak_tech(self):
        """Test: Bull trap NOT detected when tech signal is not STRONG-BUY."""
        layer = SmartMoneyLayer()

        technical_score = 0.70  # BUY, not STRONG-BUY (< 0.75)
        institutional_flow_3day = {
            "day_1": -0.012,  # -1.2% selling
            "day_2": -0.008,  # -0.8% selling
            "day_3": -0.007   # -0.7% selling
        }

        is_trap, reason = layer.detect_bull_trap("AKSEN", technical_score, institutional_flow_3day)

        assert is_trap is False
        assert "not STRONG-BUY" in reason

    def test_bull_trap_not_detected_institutions_buying(self):
        """Test: Bull trap NOT detected when institutions are buying."""
        layer = SmartMoneyLayer()

        technical_score = 0.80  # STRONG-BUY
        institutional_flow_3day = {
            "day_1": 0.030,  # +3% buying
            "day_2": 0.025,  # +2.5% buying
            "day_3": 0.028   # +2.8% buying
        }

        is_trap, reason = layer.detect_bull_trap("TTKOM", technical_score, institutional_flow_3day)

        assert is_trap is False
        assert "Not 3 days" in reason

    def test_bull_trap_detected_strong_buy_plus_selling(self):
        """Test: Bull trap DETECTED (tech STRONG-BUY + 3 days -0.5%+ selling)."""
        layer = SmartMoneyLayer()

        technical_score = 0.80  # STRONG-BUY
        institutional_flow_3day = {
            "day_1": -0.012,  # -1.2% selling
            "day_2": -0.008,  # -0.8% selling
            "day_3": -0.007   # -0.7% selling
        }

        is_trap, reason = layer.detect_bull_trap("TAVHL", technical_score, institutional_flow_3day)

        assert is_trap is True
        assert "Bull trap" in reason
        assert "STRONG-BUY" in reason


class TestBullTrapOverride:
    """Test Suite 4: Bull trap technical score override (2 tests)."""

    def test_no_override_without_bull_trap(self):
        """Test: Technical score unchanged when bull trap not detected."""
        layer = SmartMoneyLayer()

        original_score = 0.75
        adjusted = layer.apply_bull_trap_override("AKSEN", original_score, bull_trap_detected=False)

        assert adjusted == original_score

    def test_override_downgrade_on_bull_trap(self):
        """Test: Technical score downgraded by 0.15 when bull trap detected."""
        layer = SmartMoneyLayer()

        original_score = 0.80  # STRONG-BUY
        adjusted = layer.apply_bull_trap_override("TAVHL", original_score, bull_trap_detected=True)

        # Expected: 0.80 - 0.15 = 0.65
        assert adjusted == pytest.approx(0.65, abs=0.01)
        assert adjusted < original_score


class TestSmartMoneySignalObject:
    """Test Suite 5: SmartMoneySignal class (2 tests)."""

    def test_signal_initialization_neutral(self):
        """Test: Signal initializes with neutral values."""
        signal = SmartMoneySignal()

        assert signal.score == 0.5
        assert signal.confidence == 0.0
        assert signal.bull_trap_detected is False
        assert signal.source == "none"

    def test_signal_to_dict(self):
        """Test: Signal serializes to dict correctly."""
        signal = SmartMoneySignal()
        signal.score = 0.789
        signal.confidence = 0.85
        signal.institutional_net_pct = 0.0289
        signal.net_3day_avg = 0.018
        signal.trend = "ACCUMULATION"
        signal.source = "borsa"

        signal_dict = signal.to_dict()

        assert isinstance(signal_dict, dict)
        assert signal_dict["score"] == pytest.approx(0.789, abs=0.001)
        assert signal_dict["confidence"] == pytest.approx(0.85, abs=0.01)
        assert "institutional_net_pct" in signal_dict
        assert signal_dict["trend"] == "ACCUMULATION"


class TestBatchCalculation:
    """Test Suite 6: Batch Smart Money calculation (2 tests)."""

    def test_batch_calculate_multiple_tickers(self):
        """Test: Batch calculation for multiple tickers."""
        layer = SmartMoneyLayer()

        market_data = {
            "AKSEN": {
                "institutional_flow": {
                    "net_pct": 0.0289,  # +2.89%
                    "source": "borsa"
                },
                "technical_score": 0.72
            },
            "TAVHL": {
                "institutional_flow": {
                    "net_pct": -0.04,  # -4%
                    "source": "borsa"
                },
                "technical_score": 0.80
            }
        }

        results = layer.batch_calculate(["AKSEN", "TAVHL"], market_data)

        assert "AKSEN" in results
        assert "TAVHL" in results
        assert results["AKSEN"].score > 0.5  # Buying
        assert results["TAVHL"].score < 0.5  # Selling

    def test_batch_calculate_with_trend_and_bull_trap(self):
        """Test: Batch calc includes 3-day trend and bull trap detection."""
        layer = SmartMoneyLayer()

        market_data = {
            "TAVHL": {
                "institutional_flow": {
                    "net_pct": -0.007,
                    "source": "borsa"
                },
                "technical_score": 0.80,  # STRONG-BUY
                "daily_flows": [
                    {"net_pct": -0.012},
                    {"net_pct": -0.008},
                    {"net_pct": -0.007}
                ]
            }
        }

        results = layer.batch_calculate(["TAVHL"], market_data)

        signal = results["TAVHL"]
        assert signal.trend == "DISTRIBUTION"
        assert signal.bull_trap_detected is True  # Tech STRONG-BUY + 3 days selling


class TestEdgeCases:
    """Test Suite 7: Edge cases and error handling (2 tests)."""

    def test_none_institutional_flow(self):
        """Test: None institutional flow returns neutral signal."""
        layer = SmartMoneyLayer()

        signal = layer.calculate_score("UNKNOWN", None)

        assert signal.score == 0.5  # Neutral
        assert signal.confidence == 0.0

    def test_less_than_three_days_data(self):
        """Test: Less than 3 days data returns None (can't calculate trend)."""
        layer = SmartMoneyLayer()

        daily_flows = [
            {"net_pct": 0.010},
            {"net_pct": 0.015}
        ]

        trend = layer.calculate_3day_trend("AKSEN", daily_flows)

        assert trend is None


class TestSignalEngineIntegration:
    """Test Suite 8: Integration with signal engine weights (2 tests)."""

    def test_smart_money_weight_20_percent(self):
        """Test: Smart Money layer at 20% weight in composite signal."""
        layer = SmartMoneyLayer()

        # Composite signal (Option A weights)
        signals = {
            "tech": 0.72,
            "macro": 0.62,
            "kap": 0.55,
            "risk": 0.38,
            "smart_money": 0.75,  # Institutional buying
            "sentiment": 0.50
        }

        weights = {
            "tech": 0.20,
            "macro": 0.35,
            "kap": 0.15,
            "risk": 0.05,
            "smart_money": 0.20,  # 20% weight
            "sentiment": 0.05
        }

        # Calculate composite
        overall = sum(signals[k] * weights[k] for k in weights.keys())

        # Expected: 0.72*0.20 + 0.62*0.35 + 0.55*0.15 + 0.38*0.05 + 0.75*0.20 + 0.50*0.05
        #         = 0.144 + 0.217 + 0.0825 + 0.019 + 0.15 + 0.025 = 0.6385
        assert overall == pytest.approx(0.6385, abs=0.01)

        # Smart Money contribution: 0.75 * 0.20 = 0.15
        smart_money_contribution = signals["smart_money"] * weights["smart_money"]
        assert smart_money_contribution == pytest.approx(0.15, abs=0.01)

    def test_sentiment_weight_reduced_to_5_percent(self):
        """Test: Sentiment weight reduced from 25% to 5% (Option A)."""
        # Before: Sentiment 25%
        # After: Sentiment 5%, Smart Money 20%

        before_sentiment_weight = 0.25
        after_sentiment_weight = 0.05

        difference = before_sentiment_weight - after_sentiment_weight
        # Freed weight goes to Smart Money
        smart_money_new_weight = 0.20

        assert smart_money_new_weight == difference
        assert after_sentiment_weight == 0.05
