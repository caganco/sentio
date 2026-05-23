"""Tests for macro signals module."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.signals.macro_signals import (
    SYMBOL_VOLATILITY_PROFILES,
    MacroSignal,
    calculate_macro_environment_score,
    detect_regime,
    generate_macro_signal,
    get_symbol_scale,
    save_signal_json,
    score_macro_component,
)

TEST_DB = "data/test_macro_signals.db"
TEST_OUTPUT_DIR = "data/test_signals"


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up test files after each test."""
    yield
    # Clean up DB
    if Path(TEST_DB).exists():
        try:
            import sqlite3
            conn = sqlite3.connect(TEST_DB)
            conn.close()
            Path(TEST_DB).unlink()
        except Exception:
            pass
    # Clean up output files
    import shutil
    if Path(TEST_OUTPUT_DIR).exists():
        try:
            shutil.rmtree(TEST_OUTPUT_DIR)
        except Exception:
            pass


class TestVolatilityProfiles:
    """Test SYMBOL_VOLATILITY_PROFILES and get_symbol_scale."""

    def test_known_symbols_present(self):
        for sym in ("USDTRY", "VIX", "BRENT", "BRENTOIL", "EURTRY", "XAU", "_default"):
            assert sym in SYMBOL_VOLATILITY_PROFILES

    def test_get_symbol_scale_known(self):
        profile = get_symbol_scale("VIX")
        assert profile["scale"] == 0.15
        assert profile["group"] == "vix"

    def test_get_symbol_scale_unknown_falls_back(self):
        profile = get_symbol_scale("THYAO")
        assert profile == SYMBOL_VOLATILITY_PROFILES["_default"]


class TestScoringFunction:
    """Test component scoring — SPEC 1 asserts."""

    def test_vix_full_saturation(self):
        assert score_macro_component("VIX", 0.15) == pytest.approx(1.0)

    def test_vix_half_scale(self):
        assert score_macro_component("VIX", 0.075) == pytest.approx(0.5)

    def test_vix_clip_upper(self):
        assert score_macro_component("VIX", 0.30) == pytest.approx(1.0)

    def test_vix_clip_lower(self):
        assert score_macro_component("VIX", -0.30) == pytest.approx(-1.0)

    def test_usdtry_full_saturation(self):
        assert score_macro_component("USDTRY", 0.02) == pytest.approx(1.0)

    def test_usdtry_half_scale(self):
        assert score_macro_component("USDTRY", 0.01) == pytest.approx(0.5)

    def test_unknown_symbol_uses_default(self):
        assert score_macro_component("UNKNOWN_SYM", 0.05) == pytest.approx(1.0)

    def test_zero_change(self):
        assert score_macro_component("VIX", 0.0) == pytest.approx(0.0)

    def test_positive_change_positive_score(self):
        score = score_macro_component("BRENT", 0.05)
        assert score > 0

    def test_negative_change_negative_score(self):
        score = score_macro_component("BRENT", -0.05)
        assert score < 0

    def test_score_bounds(self):
        score = score_macro_component("VIX", 5.0)  # way above clip
        assert -1.0 <= score <= 1.0

    def test_profile_override(self):
        custom = {"scale": 0.10, "clip": (-1.0, 1.0)}
        assert score_macro_component("VIX", 0.10, profile_override=custom) == pytest.approx(1.0)

    def test_scale_zero_raises(self):
        with pytest.raises(ValueError):
            score_macro_component("VIX", 0.05, profile_override={"scale": 0, "clip": (-1.0, 1.0)})


class TestEnvironmentScore:
    """Test weighted macro environment score."""

    def test_all_positive_scores(self):
        """All positive components should yield positive macro score."""
        score = calculate_macro_environment_score(
            vix_score=0.5,
            usdtry_score=0.5,
            brent_score=0.5,
            bist100_score=0.5,
        )
        assert score > 0, "All positive components should yield positive macro score"

    def test_all_negative_scores(self):
        """All negative components should yield negative macro score."""
        score = calculate_macro_environment_score(
            vix_score=-0.5,
            usdtry_score=-0.5,
            brent_score=-0.5,
            bist100_score=-0.5,
        )
        assert score < 0, "All negative components should yield negative macro score"

    def test_mixed_scores(self):
        """Mixed scores should yield intermediate result."""
        score = calculate_macro_environment_score(
            vix_score=0.8,  # positive
            usdtry_score=-0.3,  # negative
            brent_score=0.5,  # positive
            bist100_score=0.2,  # slightly positive
        )
        assert -1.0 <= score <= 1.0, f"Score {score} out of bounds"

    def test_custom_weights(self):
        """Custom weights should be respected."""
        # Make VIX dominant (100% weight)
        score_high_vix = calculate_macro_environment_score(
            vix_score=0.8,
            usdtry_score=-0.5,
            brent_score=-0.5,
            bist100_score=-0.5,
            weights={"vix": 1.0, "usdtry": 0, "brent": 0, "bist100": 0},
        )
        assert score_high_vix > 0.5, "VIX-dominant weighting should emphasize VIX score"

    def test_bounds(self):
        """Score should always be in [-1, +1]."""
        score = calculate_macro_environment_score(
            vix_score=2.0,  # out of bounds
            usdtry_score=2.0,  # out of bounds
            brent_score=2.0,  # out of bounds
            bist100_score=2.0,  # out of bounds
        )
        assert -1.0 <= score <= 1.0, f"Score {score} should be clamped to [-1, 1]"


class TestRegimeDetection:
    """Test risk regime detection."""

    def test_regime_risk_on(self):
        """Positive macro score should give RISK_ON."""
        regime = detect_regime(
            vix_score=0.8,
            usdtry_score=0.2,
            brent_score=0.5,
            bist100_score=0.7,
            macro_score=0.5,  # > 0.3
        )
        assert regime == "RISK_ON", f"Expected RISK_ON, got {regime}"

    def test_regime_risk_off(self):
        """Negative macro score should give RISK_OFF."""
        regime = detect_regime(
            vix_score=-0.8,
            usdtry_score=-0.2,
            brent_score=-0.5,
            bist100_score=-0.7,
            macro_score=-0.5,  # < -0.3
        )
        assert regime == "RISK_OFF", f"Expected RISK_OFF, got {regime}"

    def test_regime_transition(self):
        """Neutral macro score should give TRANSITION."""
        regime = detect_regime(
            vix_score=0.1,
            usdtry_score=-0.1,
            brent_score=0.0,
            bist100_score=0.05,
            macro_score=0.01,  # between -0.3 and 0.3
        )
        assert regime == "TRANSITION", f"Expected TRANSITION, got {regime}"

    def test_regime_boundary_high(self):
        """Score exactly at +0.3 boundary."""
        regime = detect_regime(
            vix_score=0.3,
            usdtry_score=0.3,
            brent_score=0.3,
            bist100_score=0.3,
            macro_score=0.3,
        )
        assert regime == "RISK_ON", "Score = 0.3 should be RISK_ON"

    def test_regime_boundary_low(self):
        """Score exactly at -0.3 boundary."""
        regime = detect_regime(
            vix_score=-0.3,
            usdtry_score=-0.3,
            brent_score=-0.3,
            bist100_score=-0.3,
            macro_score=-0.3,
        )
        assert regime == "RISK_OFF", "Score = -0.3 should be RISK_OFF"


class TestMacroSignalObject:
    """Test MacroSignal dataclass."""

    def test_signal_creation(self):
        """Create valid MacroSignal."""
        signal = MacroSignal(
            timestamp="2026-05-13T15:30:00Z",
            regime="RISK_ON",
            vix_score=0.8,
            usdtry_score=0.2,
            brent_score=0.5,
            bist100_score=0.7,
            macro_environment_score=0.58,
            data_date="2026-05-13",
            symbols={"USDTRY": 45.39, "BRENT": 107.41, "VIX": 17.99, "BIST100": 9876.5},
        )

        assert signal.regime == "RISK_ON"
        assert signal.macro_environment_score == 0.58
        assert len(signal.symbols) == 4

    def test_signal_regime_validation(self):
        """Regime should be one of three values."""
        for regime in ["RISK_ON", "RISK_OFF", "TRANSITION"]:
            signal = MacroSignal(
                timestamp="2026-05-13T15:30:00Z",
                regime=regime,
                vix_score=0.0,
                usdtry_score=0.0,
                brent_score=0.0,
                bist100_score=0.0,
                macro_environment_score=0.0,
                data_date="2026-05-13",
                symbols={},
            )
            assert signal.regime == regime


class TestSignalSaving:
    """Test JSON signal saving."""

    def test_save_signal_creates_file(self):
        """Saving signal should create JSON file."""
        signal = MacroSignal(
            timestamp="2026-05-13T15:30:00Z",
            regime="RISK_ON",
            vix_score=0.8,
            usdtry_score=0.2,
            brent_score=0.5,
            bist100_score=0.7,
            macro_environment_score=0.58,
            data_date="2026-05-13",
            symbols={"USDTRY": 45.39, "BRENT": 107.41, "VIX": 17.99, "BIST100": 9876.5},
        )

        filepath = save_signal_json(signal, output_dir=TEST_OUTPUT_DIR)

        assert Path(filepath).exists(), f"Signal file not created: {filepath}"

    def test_save_signal_json_format(self):
        """Saved JSON should be valid and complete."""
        signal = MacroSignal(
            timestamp="2026-05-13T15:30:00Z",
            regime="RISK_OFF",
            vix_score=-0.7,
            usdtry_score=0.3,
            brent_score=-0.4,
            bist100_score=-0.6,
            macro_environment_score=-0.42,
            data_date="2026-05-13",
            symbols={"USDTRY": 46.12, "BRENT": 104.20, "VIX": 22.50, "BIST100": 9650.0},
        )

        filepath = save_signal_json(signal, output_dir=TEST_OUTPUT_DIR)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["regime"] == "RISK_OFF"
        assert data["macro_environment_score"] == -0.42
        assert data["data_date"] == "2026-05-13"
        assert data["symbols"]["BIST100"] == 9650.0

    def test_save_signal_filename(self):
        """File should be named macro_signal_YYYY-MM-DD.json."""
        signal = MacroSignal(
            timestamp="2026-05-13T15:30:00Z",
            regime="TRANSITION",
            vix_score=0.0,
            usdtry_score=0.0,
            brent_score=0.0,
            bist100_score=0.0,
            macro_environment_score=0.0,
            data_date="2026-05-13",
            symbols={},
        )

        filepath = save_signal_json(signal, output_dir=TEST_OUTPUT_DIR)

        assert "macro_signal_2026-05-13.json" in filepath


class TestSignalGeneration:
    """Test full signal generation from macro feed."""

    def test_generate_signal_requires_data(self):
        """Signal generation should fail gracefully if no data."""
        with pytest.raises(ValueError, match="no macro data"):
            generate_macro_signal(db_path=TEST_DB)

    def test_generate_signal_structure(self):
        """Generated signal should have all required fields."""
        from src.data.macro_feed import fetch_macro_snapshot, save_to_db

        # Create test data
        snapshot = fetch_macro_snapshot()
        if snapshot.empty:
            pytest.skip("No macro feed data available")

        save_to_db(snapshot, db_path=TEST_DB)

        # Generate signal
        signal = generate_macro_signal(db_path=TEST_DB)

        assert signal.regime in ["RISK_ON", "RISK_OFF", "TRANSITION"]
        assert -1.0 <= signal.macro_environment_score <= 1.0
        assert -1.0 <= signal.vix_score <= 1.0
        assert -1.0 <= signal.usdtry_score <= 1.0
        assert -1.0 <= signal.brent_score <= 1.0
        assert -1.0 <= signal.bist100_score <= 1.0
        assert len(signal.symbols) > 0
        assert signal.timestamp.endswith("Z")

    def test_generate_and_save(self):
        """Generate signal and save to JSON."""
        from src.data.macro_feed import fetch_macro_snapshot, save_to_db

        snapshot = fetch_macro_snapshot()
        if snapshot.empty:
            pytest.skip("No macro feed data available")

        save_to_db(snapshot, db_path=TEST_DB)

        signal = generate_macro_signal(db_path=TEST_DB)
        filepath = save_signal_json(signal, output_dir=TEST_OUTPUT_DIR)

        assert Path(filepath).exists()
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["regime"] == signal.regime
        assert data["macro_environment_score"] == signal.macro_environment_score
