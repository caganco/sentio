"""Tests for macro_layer.py (refactored with local signals support)."""
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.signals.layers.macro_layer import score_macro
from src.signals.local import LocalMacroCache
from src.signals.thresholds import LOCAL_MACRO_ENABLED


class TestScoreMacroWithoutLocalSignals:
    """Test macro_layer in DEFAULT mode (LOCAL_MACRO_ENABLED=False)."""

    def test_score_global_signals_only(self):
        """Global signals only -> should work as before."""
        macro_data = {
            "USDTRY": -0.2,
            "VIX": -0.3,
            "BRENT": 0.1,
            "BIST100": 0.4,
            "SP500": 0.2,
            "GOLD": -0.1,
            "EURTRY": -0.15,
        }
        score = score_macro(macro_data)
        assert score.layer == "macro"
        assert 0.0 <= score.score <= 100.0
        assert abs(score.weight - round(0.25 / 0.65, 10)) < 1e-9  # MASTER_WEIGHTS["macro"]
        assert score.source == "computed"

    def test_score_missing_assets(self):
        """Missing assets -> confidence 0.6."""
        macro_data = {
            "USDTRY": -0.2,
            "VIX": -0.3,
        }
        score = score_macro(macro_data)
        assert score.confidence == 0.6
        assert "missing_assets" in score.detail

    def test_score_all_missing(self):
        """All assets missing -> confidence 0.0, score 50.0."""
        macro_data = {}
        score = score_macro(macro_data)
        assert score.score == 50.0
        assert score.confidence == 0.0
        assert score.source == "missing"

    def test_backward_compatibility(self):
        """Backward compat: score_key format still works."""
        macro_data = {
            "vix_score": -0.3,
            "usdtry_score": -0.2,
            "brent_score": 0.1,
            "bist100_score": 0.4,
        }
        score = score_macro(macro_data)
        assert 0.0 <= score.score <= 100.0
        assert score.source == "computed"


class TestScoreMacroWithLocalSignals:
    """Test macro_layer WITH local signals (if enabled)."""

    def test_local_signals_composite(self):
        """When LOCAL_MACRO_ENABLED: composite score includes TCMB + CDS."""
        if not LOCAL_MACRO_ENABLED:
            pytest.skip("LOCAL_MACRO_ENABLED=False, skipping local signals test")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup local macro cache with test data
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()

            cache.store_tcmb(decision_date=today, decision_type="hike")
            cache.store_cds(data_date=today, cds_bps=300.0)

            # Global signals
            macro_data = {
                "USDTRY": -0.2,
                "VIX": -0.3,
                "BRENT": 0.1,
                "BIST100": 0.4,
                "SP500": 0.2,
                "GOLD": -0.1,
                "EURTRY": -0.15,
            }

            score = score_macro(macro_data)
            assert "local_macro" in score.detail
            assert score.source == "computed"

    def test_local_signals_confidence_min(self):
        """Composite confidence = min(global, tcmb, cds)."""
        if not LOCAL_MACRO_ENABLED:
            pytest.skip("LOCAL_MACRO_ENABLED=False")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()

            # Fresh local data
            cache.store_tcmb(decision_date=today, decision_type="hike")
            cache.store_cds(data_date=today, cds_bps=300.0)

            # Global signals with missing assets
            macro_data = {
                "USDTRY": -0.2,
            }

            score = score_macro(macro_data)
            # Confidence should be min of global (0.6 due to missing assets) and local (1.0)
            assert score.confidence == 0.6
