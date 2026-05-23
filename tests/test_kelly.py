"""Comprehensive tests for Kelly Criterion position sizing (SPEC_KELLY_1)."""
import pytest

from src.risk.kelly import KellySizer
from src.risk.portfolio_heat import PortfolioHeat


class TestConvictionMapping:
    """Tests for conviction mapping (3 tests)."""

    def test_conviction_high_agreement(self):
        """Conviction HIGH: far from 0.5, high agreement, strong macro."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        conviction = sizer._map_conviction(signal_data)
        assert conviction == "HIGH"

    def test_conviction_medium_distance(self):
        """Conviction MEDIUM: moderate distance from 0.5, decent agreement."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.65,
            "signals": {
                "tech": {"score": 0.65, "weight": 0.20},
                "macro": {"score": 0.70, "weight": 0.333},
                "kap": {"score": 0.60, "weight": 0.267},
                "risk": {"score": 0.55, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        conviction = sizer._map_conviction(signal_data)
        assert conviction == "MEDIUM"

    def test_conviction_low_agreement(self):
        """Conviction LOW: close to 0.5 or poor signal agreement."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.52,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.35, "weight": 0.333},
                "kap": {"score": 0.60, "weight": 0.267},
                "risk": {"score": 0.30, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        conviction = sizer._map_conviction(signal_data)
        assert conviction == "LOW"


class TestKellyCalculation:
    """Tests for Kelly Criterion calculation (4 tests)."""

    def test_kelly_high_conviction(self):
        """Kelly HIGH: p=0.58, b=1.0 → 16% full Kelly, 4% fractional."""
        sizer = KellySizer(kelly_fraction=0.25)
        signal_data = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("AKSEN", signal_data)
        assert result["conviction"] == "HIGH"
        assert result["win_probability"] == 0.58
        assert 15 <= result["kelly_pct"] <= 17  # ~16%
        assert 3.5 <= result["kelly_fractional_pct"] <= 4.5  # ~4%

    def test_kelly_medium_conviction(self):
        """Kelly MEDIUM: p=0.52, b=1.0 → 4% full Kelly, 1% fractional."""
        sizer = KellySizer(kelly_fraction=0.25)
        signal_data = {
            "overall_score": 0.65,
            "signals": {
                "tech": {"score": 0.65, "weight": 0.20},
                "macro": {"score": 0.70, "weight": 0.333},
                "kap": {"score": 0.60, "weight": 0.267},
                "risk": {"score": 0.55, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("TTKOM", signal_data)
        assert result["conviction"] == "MEDIUM"
        assert result["win_probability"] == 0.52
        assert 3.5 <= result["kelly_pct"] <= 4.5  # ~4%
        assert 0.8 <= result["kelly_fractional_pct"] <= 1.2  # ~1%

    def test_kelly_no_edge(self):
        """Kelly LOW: p=0.50 → 0% Kelly, action=SKIP."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.52,
            "signals": {
                "tech": {"score": 0.30, "weight": 0.20},
                "macro": {"score": 0.35, "weight": 0.333},
                "kap": {"score": 0.60, "weight": 0.267},
                "risk": {"score": 0.65, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("TAVHL", signal_data)
        assert result["conviction"] == "LOW"
        assert result["kelly_pct"] == 0
        assert result["action"] == "SKIP"

    def test_kelly_stress_market(self):
        """Kelly reduced 25% when VIX > 25."""
        sizer = KellySizer(kelly_fraction=0.25)
        signal_data = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
            "vix": 30,
        }

        result = sizer.size_position("KCHOL", signal_data)
        # Normal HIGH: ~4% fractional, stress: ~3%
        assert result["kelly_fractional_pct"] < 3.5

    def test_kelly_different_fraction(self):
        """Test different Kelly fraction (0.5x instead of 0.25x)."""
        sizer = KellySizer(kelly_fraction=0.5)
        signal_data = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("ENERY", signal_data)
        # HIGH conviction: 16% kelly, 0.5x fraction = 8%
        assert 7.5 <= result["kelly_fractional_pct"] <= 8.5


class TestPositionLimits:
    """Tests for position sizing limits (3 tests)."""

    def test_position_max_3_pct(self):
        """Position capped at 3% max even if Kelly suggests higher."""
        sizer = KellySizer(max_position_pct=0.03)
        signal_data = {
            "overall_score": 0.90,
            "signals": {
                "tech": {"score": 0.95, "weight": 0.20},
                "macro": {"score": 0.95, "weight": 0.333},
                "kap": {"score": 0.95, "weight": 0.267},
                "risk": {"score": 0.95, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("BIMAS", signal_data)
        assert result["recommended_size_pct"] <= 0.03

    def test_position_min_0_5_pct(self):
        """Position below 0.5% is skipped."""
        sizer = KellySizer(kelly_fraction=0.25)
        signal_data = {
            "overall_score": 0.55,
            "signals": {
                "tech": {"score": 0.55, "weight": 0.20},
                "macro": {"score": 0.50, "weight": 0.333},
                "kap": {"score": 0.55, "weight": 0.267},
                "risk": {"score": 0.55, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("THYAO", signal_data)
        # MEDIUM conviction, but tiny Kelly (< 0.5%)
        assert result["action"] == "SKIP"

    def test_position_loses_dont_add(self):
        """Position in loss: don't increase size."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }
        current_positions = {
            "AKSEN": {"size": 0.02, "pnl_pct": -5.0},  # In loss
        }

        result = sizer.size_position("AKSEN", signal_data, current_positions)
        # Should HOLD or REDUCE, not ADD
        assert result["action"] != "ADD"


class TestPortfolioHeat:
    """Tests for portfolio heat calculation (3 tests)."""

    def test_heat_calculation(self):
        """Heat = sum(position_size × stop_loss)."""
        heat = PortfolioHeat(max_heat_pct=0.10)
        heat.add_position("AKSEN", 0.04, 0.05)  # 4% × 5% = 0.20%
        heat.add_position("TTKOM", 0.03, 0.04)  # 3% × 4% = 0.12%

        current_heat = heat.get_current_heat()
        assert 0.0031 <= current_heat <= 0.0033  # ~0.32%

    def test_heat_exceeds_limit(self):
        """Portfolio heat CRITICAL when exceeds limit."""
        heat = PortfolioHeat(max_heat_pct=0.10)
        # Add positions totaling 12% heat (0.04*0.05*3 = 0.006 = 0.6%, add more)
        heat.add_position("AKSEN", 0.20, 0.05)  # 1.0% heat
        heat.add_position("TTKOM", 0.20, 0.05)  # 1.0% heat
        heat.add_position("TAVHL", 0.20, 0.05)  # 1.0% heat
        # Total: 3.0% heat (within 10%)
        # Add more to exceed
        heat.add_position("KCHOL", 0.40, 0.15)  # 6.0% heat
        # Total: 9% heat, still under 10%
        # Need to exceed 10%
        heat.add_position("ENERY", 0.20, 0.10)  # 2.0% heat
        # Total: 11% heat, exceeds 10% limit

        status = heat.check_heat()
        assert status["status"] == "CRITICAL"
        assert status["exceeded"] is True

    def test_heat_rebalance_scale(self):
        """Rebalance scales positions proportionally."""
        heat = PortfolioHeat(max_heat_pct=0.10)
        heat.add_position("AKSEN", 0.40, 0.05)  # 2.0% heat
        heat.add_position("TTKOM", 0.40, 0.05)  # 2.0% heat
        heat.add_position("TAVHL", 0.40, 0.05)  # 2.0% heat
        # Total: 6.0% heat (under 10%)
        # Add more to exceed
        heat.add_position("KCHOL", 0.50, 0.10)  # 5.0% heat
        # Total: 11.0% heat, exceeds 10% limit

        rebalance = heat.rebalance(action="scale")
        assert rebalance["status"] == "REBALANCE_NEEDED"
        # Scale factor should be 10/11 = 0.909x
        assert 0.90 <= rebalance["scale_factor"] <= 0.92


class TestEdgeCases:
    """Tests for edge cases and special scenarios (5 tests)."""

    def test_disagreement_signals(self):
        """Disagreement reduces conviction: tech=0.85, macro=0.35."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.70,  # Raise score to satisfy distance check
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.35, "weight": 0.333},  # Very low, disagreement
                "kap": {"score": 0.70, "weight": 0.267},
                "risk": {"score": 0.75, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("AKSEN", signal_data)
        # Disagreement (2/4 = 0.5) → conviction capped at MEDIUM (need 0.75+ for HIGH)
        assert result["conviction"] == "MEDIUM"

    def test_new_portfolio_bootstrap(self):
        """New portfolio: 5 positions sized appropriately."""
        sizer = KellySizer(max_position_pct=0.03)

        # 2 HIGH conviction
        high_signal = {
            "overall_score": 0.82,
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.80, "weight": 0.333},
                "kap": {"score": 0.75, "weight": 0.267},
                "risk": {"score": 0.85, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        high1 = sizer.size_position("AKSEN", high_signal)
        high2 = sizer.size_position("TTKOM", high_signal)

        assert high1["conviction"] == "HIGH"
        assert high2["conviction"] == "HIGH"
        # Both should be sized similarly
        assert 0.02 <= high1["recommended_size_pct"] <= 0.03
        assert 0.02 <= high2["recommended_size_pct"] <= 0.03

    def test_signal_agreement_ratio(self):
        """Signal agreement calculated correctly (3/4 bullish = 0.75)."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.70,
            "signals": {
                "tech": {"score": 0.80, "weight": 0.20},  # Bullish
                "macro": {"score": 0.75, "weight": 0.333},  # Bullish
                "kap": {"score": 0.70, "weight": 0.267},  # Bullish
                "risk": {"score": 0.40, "weight": 0.067},  # Bearish
            },
            "stop_loss_pct": 5.0,
        }

        agreement = sizer._calculate_agreement(signal_data["signals"])
        assert 0.74 <= agreement <= 0.76  # ~0.75

    def test_conviction_low_with_high_score(self):
        """LOW conviction when overall_score is 0.5-0.65 even if parts are high."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.55,  # Close to 0.5
            "signals": {
                "tech": {"score": 0.85, "weight": 0.20},
                "macro": {"score": 0.55, "weight": 0.333},  # Weak macro
                "kap": {"score": 0.50, "weight": 0.267},
                "risk": {"score": 0.40, "weight": 0.067},
            },
            "stop_loss_pct": 5.0,
        }

        conviction = sizer._map_conviction(signal_data)
        assert conviction == "LOW"

    def test_heat_exit_lowest_conviction(self):
        """Heat rebalance: exit lowest conviction position."""
        heat = PortfolioHeat(max_heat_pct=0.10)
        heat.add_position("AKSEN", 0.40, 0.05, conviction="HIGH")   # 2% heat
        heat.add_position("TTKOM", 0.40, 0.05, conviction="MEDIUM") # 2% heat
        heat.add_position("TAVHL", 0.40, 0.05, conviction="LOW")    # 2% heat
        heat.add_position("KCHOL", 0.50, 0.10, conviction="HIGH")   # 5% heat
        # Total: 11% heat, exceeds 10% limit

        rebalance = heat.rebalance(action="exit_lowest")
        assert rebalance["status"] == "REBALANCE_NEEDED"
        # Should exit TAVHL (lowest conviction)
        assert len(rebalance["actions"]) > 0
        assert rebalance["actions"][0]["ticker"] == "TAVHL"
        assert rebalance["actions"][0]["action"] == "EXIT"


class TestIntegration:
    """Integration tests combining Kelly and portfolio heat."""

    def test_full_workflow(self):
        """Full workflow: size positions, track heat."""
        sizer = KellySizer(max_position_pct=0.03)
        heat = PortfolioHeat(max_heat_pct=0.10)

        # 3 positions
        tickers = ["AKSEN", "TTKOM", "TAVHL"]
        signals = [
            {  # HIGH
                "overall_score": 0.82,
                "signals": {
                    "tech": {"score": 0.85, "weight": 0.20},
                    "macro": {"score": 0.80, "weight": 0.333},
                    "kap": {"score": 0.75, "weight": 0.267},
                    "risk": {"score": 0.85, "weight": 0.067},
                },
                "stop_loss_pct": 0.05,
            },
            {  # MEDIUM
                "overall_score": 0.65,
                "signals": {
                    "tech": {"score": 0.65, "weight": 0.20},
                    "macro": {"score": 0.70, "weight": 0.333},
                    "kap": {"score": 0.60, "weight": 0.267},
                    "risk": {"score": 0.55, "weight": 0.067},
                },
                "stop_loss_pct": 0.04,
            },
            {  # MEDIUM
                "overall_score": 0.60,
                "signals": {
                    "tech": {"score": 0.60, "weight": 0.20},
                    "macro": {"score": 0.65, "weight": 0.333},
                    "kap": {"score": 0.55, "weight": 0.267},
                    "risk": {"score": 0.60, "weight": 0.067},
                },
                "stop_loss_pct": 0.06,
            },
        ]

        results = []
        for ticker, signal in zip(tickers, signals):
            result = sizer.size_position(ticker, signal)
            results.append(result)
            heat.add_position(
                ticker, result["recommended_size_pct"], signal["stop_loss_pct"]
            )

        # Check results
        assert results[0]["conviction"] == "HIGH"
        assert results[1]["conviction"] == "MEDIUM"
        # Signal 3 has LOW macro strength (0.65) and 0.60 overall score
        # distance = 0.10 (< 0.15) → LOW conviction
        assert results[2]["conviction"] == "LOW"

        # Check heat
        heat_check = heat.check_heat()
        assert heat_check["status"] in ["OK", "WARNING"]
        assert heat_check["positions_count"] == 3

    def test_empty_signals(self):
        """Test with missing/empty signal data."""
        sizer = KellySizer()
        signal_data = {
            "overall_score": 0.5,
            "signals": {},
            "stop_loss_pct": 5.0,
        }

        result = sizer.size_position("AKSEN", signal_data)
        # Should default to LOW conviction
        assert result["conviction"] == "LOW"

    def test_kelly_formula_math(self):
        """Verify Kelly formula math: K = (p*b - q) / b."""
        sizer = KellySizer()

        # Test case: p=0.58, b=1.0
        # K = (0.58*1.0 - 0.42) / 1.0 = 0.16 = 16%
        kelly = sizer._calculate_kelly(0.58, 1.0)
        assert 15.9 <= kelly <= 16.1

        # Test case: p=0.52, b=1.0
        # K = (0.52*1.0 - 0.48) / 1.0 = 0.04 = 4%
        kelly = sizer._calculate_kelly(0.52, 1.0)
        assert 3.9 <= kelly <= 4.1

        # Test case: p=0.50, b=1.0
        # K = (0.50*1.0 - 0.50) / 1.0 = 0.0 = 0%
        kelly = sizer._calculate_kelly(0.50, 1.0)
        assert kelly == 0.0
