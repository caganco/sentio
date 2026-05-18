"""Tests for macro_layer.py (refactored with local signals support)."""
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.signals.layers.macro_layer import score_macro
from src.signals.local import LocalMacroCache
from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.thresholds import LOCAL_MACRO_ENABLED, LOCAL_MACRO_WEIGHTS


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
        # Phase 4.5 (D-052): macro weight 0.35 -> 0.20 (less gatekeeping; L2
        # now drives macro modulation instead of acting as a hard veto).
        assert abs(score.weight - 0.20) < 1e-9
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


class TestForeignFlowsWeighting:
    """Gap 1 (SPEC_L2_ENHANCEMENT_1): foreign flows activated from 0% -> 20%."""

    def test_foreign_weight_is_configured_and_positive(self):
        """Foreign weight is read from config and is now > 0."""
        assert LOCAL_MACRO_WEIGHTS["bist_foreign_weekly"] > 0.0
        # Weights normalize to 1.0 (sanity on the composite config).
        assert abs(sum(LOCAL_MACRO_WEIGHTS.values()) - 1.0) < 1e-9

    def test_foreign_flows_contribute_to_composite(self):
        """With fresh foreign data the composite reflects the foreign term."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()

            cache.store_tcmb(decision_date=today, decision_type="hike")  # 25.0
            cache.store_cds(data_date=today, cds_bps=300.0)              # 50.0
            # Strong weekly outflow -> bearish foreign score (<50), conf 0.9.
            cache.store_bist_foreign(
                week_ending_date=today,
                foreign_ownership_pct=28.0,
                pct_change_weekly=-0.40,
            )

            result = LocalMacroSignals(cache=cache).score()

            # Foreign signal is real (fresh, non-neutral) and now weighted.
            assert result.bist_foreign_weekly.confidence > 0.0
            assert result.bist_foreign_weekly.score < 50.0

            w = LOCAL_MACRO_WEIGHTS
            expected = (
                result.tcmb.score * result.tcmb.confidence * w["tcmb"]
                + result.cds.score * result.cds.confidence * w["cds"]
                + result.bist_foreign_weekly.score
                * result.bist_foreign_weekly.confidence
                * w["bist_foreign_weekly"]
            )
            assert abs(result.composite_score - expected) < 1e-6

    def test_foreign_flows_change_composite_vs_absent(self):
        """Composite differs when foreign data is present vs absent."""
        today = datetime.utcnow().date().isoformat()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_no = LocalMacroCache(db_path=str(Path(tmpdir) / "no.db"))
            cache_no.store_tcmb(decision_date=today, decision_type="hike")
            cache_no.store_cds(data_date=today, cds_bps=300.0)
            composite_absent = LocalMacroSignals(cache=cache_no).score().composite_score

            cache_yes = LocalMacroCache(db_path=str(Path(tmpdir) / "yes.db"))
            cache_yes.store_tcmb(decision_date=today, decision_type="hike")
            cache_yes.store_cds(data_date=today, cds_bps=300.0)
            cache_yes.store_bist_foreign(
                week_ending_date=today,
                foreign_ownership_pct=28.0,
                pct_change_weekly=-0.40,
            )
            composite_present = LocalMacroSignals(cache=cache_yes).score().composite_score

            assert composite_present != composite_absent
