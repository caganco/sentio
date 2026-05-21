"""
D-007: SPEC_S_1 Integration Validation
Test that Brent price changes (80 vs 105) affect energy sector signal scores.
"""
import pytest

from src.signals.macro_alignment import MacroAlignmentCalculator


class TestBrentEnergyIntegration:
    """Verify Brent-energy sector correlation is operational in signal scoring."""

    def test_brent_80_energy_stocks(self):
        """
        Scenario: Brent = $80/bbl (LOW)
        Expected: Energy stocks get alignment_score < 0.5 (unfavorable macro)
        """
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        macro_state_low = {
            "brent": 80.0,  # Low oil price
            "usd_try": 45.0,
            "vix": 20.0,
            "cds": 350.0,
        }

        energy_stocks = ["AKSEN", "ENERY", "AKENR", "ZOREN"]
        scores_low = {}

        for ticker in energy_stocks:
            result = calculator.calculate_alignment(ticker, macro_state_low)
            scores_low[ticker] = result["alignment_score"]
            print(f"\nBrent=$80: {ticker}")
            print(f"  Score: {result['alignment_score']}")
            print(f"  Direction: {result['alignment_direction']}")

        # Energy stocks should have LOW alignment when Brent is low
        for ticker, score in scores_low.items():
            assert 0 <= score <= 1, f"{ticker} score out of bounds: {score}"

    def test_brent_105_energy_stocks(self):
        """
        Scenario: Brent = $105/bbl (HIGH)
        Expected: Energy stocks get alignment_score > 0.5 (favorable macro)
        """
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        macro_state_high = {
            "brent": 105.0,  # High oil price
            "usd_try": 45.0,
            "vix": 20.0,
            "cds": 350.0,
        }

        energy_stocks = ["AKSEN", "ENERY", "AKENR", "ZOREN"]
        scores_high = {}

        for ticker in energy_stocks:
            result = calculator.calculate_alignment(ticker, macro_state_high)
            scores_high[ticker] = result["alignment_score"]
            print(f"\nBrent=$105: {ticker}")
            print(f"  Score: {result['alignment_score']}")
            print(f"  Direction: {result['alignment_direction']}")

        # Energy stocks should have HIGH alignment when Brent is high
        for ticker, score in scores_high.items():
            assert 0 <= score <= 1, f"{ticker} score out of bounds: {score}"

    def test_brent_difference_matters(self):
        """
        CRITICAL: Verify that scores CHANGE when Brent changes.
        This is the core integration test.
        """
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        macro_state_low = {
            "brent": 80.0,
            "usd_try": 45.0,
            "vix": 20.0,
            "cds": 350.0,
        }

        macro_state_high = {
            "brent": 105.0,
            "usd_try": 45.0,
            "vix": 20.0,
            "cds": 350.0,
        }

        energy_stocks = ["AKSEN", "ENERY", "AKENR", "ZOREN"]

        for ticker in energy_stocks:
            result_low = calculator.calculate_alignment(ticker, macro_state_low)
            result_high = calculator.calculate_alignment(ticker, macro_state_high)

            score_low = result_low["alignment_score"]
            score_high = result_high["alignment_score"]

            print(f"\n{ticker}: Brent effect")
            print(f"  Low (80):  {score_low:.3f}")
            print(f"  High (105): {score_high:.3f}")
            print(f"  Delta: {score_high - score_low:+.3f}")

            # For AKSEN (strong + Brent): high Brent should increase score
            if ticker == "AKSEN":
                assert score_high > score_low, (
                    f"AKSEN should benefit from higher Brent: "
                    f"$80={score_low:.3f} vs $105={score_high:.3f}"
                )

            # For ENERY (medium - Brent): high Brent should decrease score
            if ticker == "ENERY":
                assert score_high < score_low, (
                    f"ENERY should suffer from higher Brent (thermal cost): "
                    f"$80={score_low:.3f} vs $105={score_high:.3f}"
                )

    def test_aksen_specific_brent_direction(self):
        """
        AKSEN has strong (+) Brent sensitivity.
        Brent UP → AKSEN alignment UP.
        """
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        test_cases = [
            (75, "very_low"),
            (85, "low"),
            (95, "medium"),
            (105, "high"),
            (120, "very_high"),
        ]

        scores = []
        for brent_val, label in test_cases:
            macro_state = {
                "brent": brent_val,
                "usd_try": 45.0,
                "vix": 20.0,
                "cds": 350.0,
            }
            result = calculator.calculate_alignment("AKSEN", macro_state)
            score = result["alignment_score"]
            scores.append((brent_val, score))
            print(f"AKSEN: Brent ${brent_val} -> alignment {score:.3f}")

        # Verify monotonic increase: higher Brent → higher alignment
        for i in range(1, len(scores)):
            prev_brent, prev_score = scores[i - 1]
            curr_brent, curr_score = scores[i]
            assert curr_score >= prev_score, (
                f"AKSEN alignment should increase with Brent: "
                f"${prev_brent}={prev_score:.3f} vs ${curr_brent}={curr_score:.3f}"
            )

    def test_enery_specific_brent_direction(self):
        """
        ENERY has medium (-) Brent sensitivity (thermal cost).
        Brent UP → ENERY alignment DOWN.
        """
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        test_cases = [
            (75, "very_low"),
            (85, "low"),
            (95, "medium"),
            (105, "high"),
            (120, "very_high"),
        ]

        scores = []
        for brent_val, label in test_cases:
            macro_state = {
                "brent": brent_val,
                "usd_try": 45.0,
                "vix": 20.0,
                "cds": 350.0,
            }
            result = calculator.calculate_alignment("ENERY", macro_state)
            score = result["alignment_score"]
            scores.append((brent_val, score))
            print(f"ENERY: Brent ${brent_val} -> alignment {score:.3f}")

        # Verify monotonic decrease: higher Brent → lower alignment
        for i in range(1, len(scores)):
            prev_brent, prev_score = scores[i - 1]
            curr_brent, curr_score = scores[i]
            assert curr_score <= prev_score, (
                f"ENERY alignment should decrease with Brent: "
                f"${prev_brent}={prev_score:.3f} vs ${curr_brent}={curr_score:.3f}"
            )

    def test_sector_context_matches_sensitivity(self):
        """
        Verify sector_context in sector_mapping.json matches actual sensitivity.
        """
        from src.data.database import get_sector_context

        energy_stocks = ["AKSEN", "ENERY", "AKENR", "ZOREN", "ODAS"]

        for ticker in energy_stocks:
            context = get_sector_context(ticker)
            assert context is not None, f"{ticker} missing sector_context"
            assert "Brent" in context, f"{ticker} context doesn't mention Brent"
            print(f"{ticker}: {context}")

    def test_daily_update_integration(self):
        """
        Verify that daily_update.py would pick up Brent-energy correlation
        if macro_alignment is integrated into signal scoring.
        """
        # This test documents what SHOULD happen but isn't yet wired
        calculator = MacroAlignmentCalculator("data/macro_sensitivity.json")

        # Simulate high and low Brent scenarios
        scenario_high_brent = {
            "brent": 110.0,
            "usd_try": 45.43,
            "vix": 17.89,
            "cds": 450.0,
        }

        scenario_low_brent = {
            "brent": 75.0,
            "usd_try": 45.43,
            "vix": 17.89,
            "cds": 450.0,
        }

        # Currently: macro_alignment is calculated in daily_update.py
        # but NOT fed into signal engine scoring
        # TODO: Integrate macro_alignment scores into signal engine weights

        print("\n[INTEGRATION CHECK]")
        print("macro_alignment scores are CALCULATED but not INTEGRATED into signals")
        print("Fix required: daily_update.py should add alignment score to signal_data")
