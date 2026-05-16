"""Tests for local macro signals (TCMB, CDS, BIST Foreign)."""
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.signals.local import (
    BistForeignOwnershipClient,
    CDSClient,
    LocalMacroCache,
    TCMBClient,
)
from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.thresholds import (
    CDS_SCORES,
    LOCAL_MACRO_WEIGHTS,
    TCMB_DECISION_MAP,
)


@pytest.fixture
def temp_cache():
    """Temporary cache for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalMacroCache(db_path=str(Path(tmpdir) / "test_local_macro.db"))


class TestTCMBClient:
    """TCMB policy rate decision client tests."""

    def test_interpret_decision_hike(self):
        """Hike decision -> bearish signal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = TCMBClient(cache)
            assert client.interpret_decision("hike") == TCMB_DECISION_MAP["hike"]
            assert client.interpret_decision("hike") == 25.0

    def test_interpret_decision_cut(self):
        """Cut decision -> bullish signal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = TCMBClient(cache)
            assert client.interpret_decision("cut") == TCMB_DECISION_MAP["cut"]
            assert client.interpret_decision("cut") == 75.0

    def test_interpret_decision_hold(self):
        """Hold decision -> neutral signal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = TCMBClient(cache)
            assert client.interpret_decision("hold") == TCMB_DECISION_MAP["hold"]
            assert client.interpret_decision("hold") == 50.0

    def test_score_no_decision(self):
        """No decision in cache -> neutral score, confidence 0.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = TCMBClient(cache)
            signal = client.score()
            assert signal.component == "tcmb"
            assert signal.score == 50.0
            assert signal.confidence == 0.0
            assert signal.data_freshness == "missing"

    def test_score_fresh_decision(self):
        """Fresh decision (< 45 days) -> confidence 1.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()
            cache.store_tcmb(
                decision_date=today,
                decision_type="hike",
                rate_before=32.0,
                rate_after=33.0,
            )
            client = TCMBClient(cache)
            signal = client.score()
            assert signal.score == 25.0
            assert signal.confidence == 1.0
            assert signal.data_freshness == "fresh"

    def test_score_stale_decision(self):
        """Stale decision (> 45 days) -> confidence 0.7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            old_date = (datetime.utcnow() - timedelta(days=50)).date().isoformat()
            cache.store_tcmb(
                decision_date=old_date,
                decision_type="cut",
                rate_before=33.0,
                rate_after=32.0,
            )
            client = TCMBClient(cache)
            signal = client.score()
            assert signal.score == 75.0
            assert signal.confidence == 0.7
            assert signal.data_freshness == "stale"


class TestCDSClient:
    """CDS spreads client tests."""

    def test_cds_to_score_low_risk(self):
        """CDS < 250 bps -> bullish score (75.0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = CDSClient(cache)
            score, risk = client.cds_to_score(200.0)
            assert score == CDS_SCORES["low_risk"]
            assert risk == "low_risk"

    def test_cds_to_score_neutral(self):
        """250 < CDS < 350 bps -> neutral score (50.0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = CDSClient(cache)
            score, risk = client.cds_to_score(300.0)
            assert score == CDS_SCORES["neutral"]
            assert risk == "neutral"

    def test_cds_to_score_high_risk(self):
        """350 < CDS < 500 bps -> bearish score (30.0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = CDSClient(cache)
            score, risk = client.cds_to_score(400.0)
            assert score == CDS_SCORES["high_risk"]
            assert risk == "high_risk"

    def test_cds_to_score_extreme(self):
        """CDS > 500 bps -> critical score (10.0)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = CDSClient(cache)
            score, risk = client.cds_to_score(550.0)
            assert score == CDS_SCORES["extreme_risk"]
            assert risk == "extreme_risk"

    def test_score_no_data(self):
        """No CDS data in cache -> neutral score, confidence 0.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = CDSClient(cache)
            signal = client.score()
            assert signal.component == "cds"
            assert signal.score == 50.0
            assert signal.confidence == 0.0
            assert signal.data_freshness == "missing"

    def test_score_fresh_cds(self):
        """Fresh CDS data (< 2 days) -> confidence 1.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()
            cache.store_cds(data_date=today, cds_bps=300.0)
            client = CDSClient(cache)
            signal = client.score()
            assert signal.score == 50.0
            assert signal.confidence == 1.0
            assert signal.data_freshness == "fresh"

    def test_score_stale_cds(self):
        """Stale CDS data (2-5 days) -> confidence 0.8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            old_date = (datetime.utcnow() - timedelta(days=3)).date().isoformat()
            cache.store_cds(data_date=old_date, cds_bps=350.0)
            client = CDSClient(cache)
            signal = client.score()
            assert signal.score == 30.0  # high_risk
            assert signal.confidence == 0.8
            assert signal.data_freshness == "stale"


class TestBistForeignClient:
    """BIST foreign ownership weekly client tests."""

    def test_weekly_change_to_score_strong_inflow(self):
        """Strong inflow (+0.4%) -> bullish score (70+)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = BistForeignOwnershipClient(cache)
            score = client.weekly_change_to_score(0.4)
            assert score > 65.0
            assert score <= 80.0

    def test_weekly_change_to_score_strong_outflow(self):
        """Strong outflow (-0.4%) -> bearish score (<35)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = BistForeignOwnershipClient(cache)
            score = client.weekly_change_to_score(-0.4)
            assert score < 35.0
            assert score >= 20.0

    def test_weekly_change_to_score_neutral(self):
        """Neutral change (±0.1%) -> neutral score (~50)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = BistForeignOwnershipClient(cache)
            score = client.weekly_change_to_score(0.1)
            assert 48.0 <= score <= 55.0

    def test_score_no_data(self):
        """No foreign data in cache -> neutral score, confidence 0.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            client = BistForeignOwnershipClient(cache)
            signal = client.score()
            assert signal.component == "bist_foreign_weekly"
            assert signal.score == 50.0
            assert signal.confidence == 0.0
            assert signal.data_freshness == "missing"

    def test_score_fresh_data(self):
        """Fresh foreign data (< 10 days) -> confidence 0.9."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()
            cache.store_bist_foreign(
                week_ending_date=today,
                foreign_ownership_pct=28.45,
                pct_change_weekly=-0.12,
            )
            client = BistForeignOwnershipClient(cache)
            signal = client.score()
            assert signal.confidence == 0.9
            assert signal.data_freshness == "fresh"


class TestLocalMacroSignals:
    """Composite local macro signals tests."""

    def test_score_all_components(self):
        """Test composite score with all components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))

            # Populate cache
            today = datetime.utcnow().date().isoformat()
            cache.store_tcmb(
                decision_date=today, decision_type="hike", rate_before=32.0, rate_after=33.0
            )
            cache.store_cds(data_date=today, cds_bps=300.0)
            cache.store_bist_foreign(
                week_ending_date=today,
                foreign_ownership_pct=28.45,
                pct_change_weekly=-0.12,
            )

            # Score
            signals = LocalMacroSignals(cache=cache)
            result = signals.score()

            # Assertions
            assert result.tcmb.component == "tcmb"
            assert result.cds.component == "cds"
            assert result.bist_foreign_weekly.component == "bist_foreign_weekly"
            assert 0.0 <= result.composite_score <= 100.0

    def test_composite_weights(self):
        """Composite uses config-driven LOCAL_MACRO_WEIGHTS (no foreign data)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalMacroCache(db_path=str(Path(tmpdir) / "test.db"))
            today = datetime.utcnow().date().isoformat()

            # TCMB: hike -> 25.0, CDS: neutral -> 50.0, both confidence 1.0.
            # No foreign data -> confidence 0.0 -> contributes 0 regardless
            # of its weight.
            cache.store_tcmb(decision_date=today, decision_type="hike")
            cache.store_cds(data_date=today, cds_bps=300.0)

            signals = LocalMacroSignals(cache=cache)
            result = signals.score()

            expected = (
                25.0 * LOCAL_MACRO_WEIGHTS["tcmb"]
                + 50.0 * LOCAL_MACRO_WEIGHTS["cds"]
            )
            assert abs(result.composite_score - expected) < 1.0
