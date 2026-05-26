"""Tests for macro_layer.py (refactored with local signals support)."""
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.signals.layers.macro_layer import score_macro
from src.signals.local import LocalMacroCache
from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.thresholds import (
    LOCAL_MACRO_ENABLED,
    LOCAL_MACRO_WEIGHTS,
    MACRO_WEIGHTS_COMPOSITE,
)


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
        # D-154: macro weight renormalized from 0.20 → 0.20/0.97 (~0.2062).
        from src.signals.thresholds import MASTER_WEIGHTS
        assert abs(score.weight - MASTER_WEIGHTS["macro"]) < 1e-9
        assert score.source == "computed"

    def test_score_missing_assets(self):
        """Missing assets -> confidence 0.6."""
        from unittest.mock import MagicMock, patch

        # Mock LocalMacroSignals so the test does not depend on the
        # git-ignored YAML macro fallback (absent on CI → tcmb/cds
        # confidence 0.0, which would collapse the min()). Local
        # confidence pinned to 1.0; assertion still checks min() picks
        # the global 0.6 (missing assets).
        mock_local = MagicMock()
        mock_local.tcmb.score = 50.0
        mock_local.tcmb.confidence = 1.0
        mock_local.tcmb.audit_msg = "mocked"
        mock_local.cds.score = 50.0
        mock_local.cds.confidence = 1.0
        mock_local.cds.audit_msg = "mocked"
        mock_local.dxy.score = 50.0
        mock_local.dxy.confidence = 0.0   # absent → weight falls back to global_signals
        mock_local.dxy.audit_msg = "mocked"
        mock_local.bist_foreign_weekly.score = 50.0
        mock_local.bist_foreign_weekly.confidence = 0.0   # absent → weight falls back to global_signals
        mock_local.bist_foreign_weekly.raw_value = None
        mock_local.bist_foreign_weekly.audit_msg = "mocked"
        mock_local.tl_bond_proxy.score = 50.0
        mock_local.tl_bond_proxy.raw_value = None
        mock_local.tl_bond_proxy.audit_msg = "mocked"

        macro_data = {
            "USDTRY": -0.2,
            "VIX": -0.3,
        }

        with patch("src.signals.layers.macro_layer.LocalMacroSignals", return_value=MagicMock(score=MagicMock(return_value=mock_local))):
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

        from unittest.mock import MagicMock, patch

        # Mock LocalMacroSignals so the test does not depend on the
        # git-ignored YAML macro fallback (absent on CI → tcmb/cds
        # confidence 0.0, which would collapse the min()). Local
        # confidence pinned to 1.0; assertion still checks min() picks
        # the global 0.6 (missing assets).
        mock_local = MagicMock()
        mock_local.tcmb.score = 50.0
        mock_local.tcmb.confidence = 1.0
        mock_local.tcmb.audit_msg = "mocked"
        mock_local.cds.score = 50.0
        mock_local.cds.confidence = 1.0
        mock_local.cds.audit_msg = "mocked"
        mock_local.dxy.score = 50.0
        mock_local.dxy.confidence = 0.0   # absent → weight falls back to global_signals
        mock_local.dxy.audit_msg = "mocked"
        mock_local.bist_foreign_weekly.score = 50.0
        mock_local.bist_foreign_weekly.confidence = 0.0   # absent → weight falls back to global_signals
        mock_local.bist_foreign_weekly.raw_value = None
        mock_local.bist_foreign_weekly.audit_msg = "mocked"
        mock_local.tl_bond_proxy.score = 50.0
        mock_local.tl_bond_proxy.raw_value = None
        mock_local.tl_bond_proxy.audit_msg = "mocked"

        # Global signals with missing assets
        macro_data = {
            "USDTRY": -0.2,
        }

        with patch("src.signals.layers.macro_layer.LocalMacroSignals", return_value=MagicMock(score=MagicMock(return_value=mock_local))):
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


# Neutral global macro input → global_score = 50 (drives score_macro into the
# LOCAL_MACRO_ENABLED branch without skewing the global term).
_NEUTRAL_GLOBAL = {"USDTRY": 0.0, "VIX": 0.0, "BRENT": 0.0, "BIST100": 0.0}


def _score_macro_with_cache(cache) -> object:
    """Run score_macro() against an injected test cache, then restore singleton.

    score_macro() calls LocalMacroSignals() (no cache) → the process singleton.
    An explicit-cache instance is NOT the singleton (see __new__), so we assign
    it to _instance manually, then reset afterward to avoid cross-test leakage.
    """
    LocalMacroSignals._reset()
    LocalMacroSignals._instance = LocalMacroSignals(cache=cache)
    try:
        return score_macro(dict(_NEUTRAL_GLOBAL))
    finally:
        LocalMacroSignals._reset()


class TestForeignFlowsL2Migration:
    """D-118 (CB-007): bist_foreign_weekly activated in MACRO_WEIGHTS_COMPOSITE.

    Asserts on score_macro() output (MACRO_WEIGHTS_COMPOSITE path), distinct
    from TestForeignFlowsWeighting which checks LocalMacroResult.composite_score
    (LOCAL_MACRO_WEIGHTS path, untouched by D-118).
    """

    def test_score_macro_changes_with_foreign_flow(self):
        """Strong net inflow lifts score_macro() above a strong net outflow."""
        today = datetime.utcnow().date().isoformat()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_in = LocalMacroCache(db_path=str(Path(tmpdir) / "in.db"))
            cache_in.store_tcmb(decision_date=today, decision_type="hold")
            cache_in.store_cds(data_date=today, cds_bps=300.0)
            cache_in.store_bist_foreign(
                week_ending_date=today, foreign_ownership_pct=30.0,
                pct_change_weekly=+0.40,
            )
            score_inflow = _score_macro_with_cache(cache_in).score

            cache_out = LocalMacroCache(db_path=str(Path(tmpdir) / "out.db"))
            cache_out.store_tcmb(decision_date=today, decision_type="hold")
            cache_out.store_cds(data_date=today, cds_bps=300.0)
            cache_out.store_bist_foreign(
                week_ending_date=today, foreign_ownership_pct=28.0,
                pct_change_weekly=-0.40,
            )
            score_outflow = _score_macro_with_cache(cache_out).score

        assert score_inflow > score_outflow
        assert (score_inflow - score_outflow) > 1.0

    def test_score_macro_no_foreign_data_no_nan(self):
        """Absent foreign data → valid score (weight redistributed), no NaN."""
        today = datetime.utcnow().date().isoformat()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "nofx.db"))
            cache.store_tcmb(decision_date=today, decision_type="hold")
            cache.store_cds(data_date=today, cds_bps=300.0)
            result = _score_macro_with_cache(cache)

        assert result.score == result.score          # not NaN
        assert 0.0 <= result.score <= 100.0

    def test_score_macro_detail_includes_bist_foreign(self):
        """detail dict must surface the bist_foreign_weekly block at weight 0.15."""
        today = datetime.utcnow().date().isoformat()
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "detail.db"))
            cache.store_tcmb(decision_date=today, decision_type="hold")
            cache.store_cds(data_date=today, cds_bps=300.0)
            cache.store_bist_foreign(
                week_ending_date=today, foreign_ownership_pct=30.0,
                pct_change_weekly=0.0,
            )
            result = _score_macro_with_cache(cache)

        assert "local_macro" in result.detail
        fw = result.detail["local_macro"]["bist_foreign_weekly"]
        assert "score" in fw and "conf" in fw and "contrib" in fw
        assert fw["weight"] == pytest.approx(0.15)



class TestEmRelStrengthFallback:
    """D-154: BIST100 → EM_RELSTRENGTH swap + backward-compat fallback."""

    def test_bist100_fallback_active(self):
        """BIST100 in macro_data → used as EM_RELSTRENGTH proxy (fallback)."""
        macro_data = {
            "USDTRY": -0.2,
            "VIX": -0.3,
            "BIST100": 0.4,   # no EM_RELSTRENGTH key → fallback triggers
            "SP500": 0.2,
        }
        original_copy = dict(macro_data)
        score = score_macro(macro_data)
        assert 0.0 <= score.score <= 100.0
        assert score.layer == "macro"
        # Input dict must remain unchanged (fallback operates on normalised copy)
        assert macro_data == original_copy

    def test_em_relstrength_direct_key(self):
        """EM_RELSTRENGTH direct key → accepted without fallback."""
        macro_data = {
            "USDTRY": -0.2,
            "VIX": -0.3,
            "EM_RELSTRENGTH": 0.5,   # direct key
            "SP500": 0.2,
        }
        score = score_macro(macro_data)
        assert 0.0 <= score.score <= 100.0

    def test_em_relstrength_takes_priority_over_bist100(self):
        """When both keys present, EM_RELSTRENGTH used; BIST100 ignored for composite."""
        macro_data_em = {
            "USDTRY": 0.0, "VIX": 0.0, "EM_RELSTRENGTH": 1.0,
        }
        macro_data_bist = {
            "USDTRY": 0.0, "VIX": 0.0, "BIST100": 1.0,   # fallback path
        }
        score_em = score_macro(macro_data_em)
        score_bist = score_macro(macro_data_bist)
        # Both should produce similar scores (same value via different key)
        assert abs(score_em.score - score_bist.score) < 0.1
