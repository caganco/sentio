"""Short interest integration tests (D-058)."""
import pytest

from src.data.short_interest_normalizer import (
    compute_universe_percentiles,
    score_short_interest,
)
from src.signals.layers.connectors.bist_datastore_connector import (
    BISTDataStoreConnector,
)
from src.signals.thresholds import (
    L5_FOREIGN_WEIGHT,
    L5_KAP_OVERLAP_DAMP,
    L5_SHORT_INT_WEIGHT,
    MASTER_WEIGHTS,
    SHORT_INTEREST_HIGH,
)


class TestShortInterestScoring:
    """Test score_short_interest function."""

    def test_short_interest_score_inverted(self):
        """High universe_percentile (crowded short) → low score."""
        score = score_short_interest(short_ratio=20.0, universe_percentile=0.9)
        assert score == pytest.approx(0.1, abs=0.01)

    def test_short_interest_score_clip(self):
        """Boundary: percentile=0 → 1.0, percentile=1 → 0.0."""
        assert score_short_interest(20.0, 0.0) == pytest.approx(1.0)
        assert score_short_interest(20.0, 1.0) == pytest.approx(0.0)


class TestBISTDataStoreConnector:
    """Test BISTDataStoreConnector."""

    def test_bist_datastore_csv_parse(self):
        """CSV → symbol dict, invalid rows skipped."""
        import pandas as pd

        connector = BISTDataStoreConnector(stale_days=10)
        df = pd.DataFrame({
            "symbol": ["ASELS", "AKCNS", "INVALID"],
            "short_volume_ratio": [5.0, 12.0, -1.0],  # -1.0 invalid
        })
        result = connector.parse_short_interest(df)
        assert "ASELS" in result
        assert result["ASELS"] == 5.0
        assert "AKCNS" in result
        assert result["AKCNS"] == 12.0
        assert "INVALID" not in result

    def test_short_interest_stale_neutral(self):
        """is_stale() returns True after stale_days."""
        from datetime import datetime, timedelta

        connector = BISTDataStoreConnector(stale_days=10)
        assert connector.is_stale() is True

        connector._last_fetch = datetime.utcnow()
        assert connector.is_stale() is False

        connector._last_fetch = datetime.utcnow() - timedelta(days=11)
        assert connector.is_stale() is True


class TestShortInterestNormalizer:
    """Test compute_universe_percentiles."""

    def test_universe_percentiles_rank_order(self):
        """Lower short_ratio → higher percentile rank."""
        short_ratios = {
            "A": 5.0,
            "B": 15.0,
            "C": 25.0,
        }
        percentiles = compute_universe_percentiles(short_ratios)
        assert percentiles["A"] < percentiles["B"] < percentiles["C"]
        assert all(0.0 <= p <= 1.0 for p in percentiles.values())


class TestL5ShortInterestIntegration:
    """Test L5 short interest integration in scoring logic."""

    def test_kap_overlap_dampening_triggered(self):
        """L3 event + short_ratio > threshold → score centralized."""
        foreign_score = 80.0
        short_interest_score = 0.2  # [0, 1]
        short_ratio = 20.0  # > 15 threshold

        si = float(short_interest_score)
        if short_ratio > SHORT_INTEREST_HIGH:
            si = 0.5 + (si - 0.5) * L5_KAP_OVERLAP_DAMP

        assert si > short_interest_score
        assert si == pytest.approx(0.5 + (0.2 - 0.5) * L5_KAP_OVERLAP_DAMP)

    def test_kap_overlap_dampening_not_triggered(self):
        """No KAP event or low short_ratio → no dampening."""
        short_interest_score = 0.2
        short_ratio = 10.0  # < 15 threshold

        si = float(short_interest_score)
        if short_ratio > SHORT_INTEREST_HIGH:
            si = 0.5 + (si - 0.5) * L5_KAP_OVERLAP_DAMP

        assert si == short_interest_score  # unchanged

    def test_l5_internal_weights_sum_to_one(self):
        """L5 sub-weights must sum to 1.0 (internal normalization)."""
        assert (L5_FOREIGN_WEIGHT + L5_SHORT_INT_WEIGHT) == pytest.approx(1.0)

    def test_master_weights_unchanged(self):
        """MASTER_WEIGHTS sum must be in [0.85, 1.05] (unchanged by D-058)."""
        total = sum(MASTER_WEIGHTS.values())
        assert 0.85 <= total <= 1.05, (
            f"MASTER_WEIGHTS sum is {total}, "
            f"but D-058 should not change it"
        )


pytestmark = pytest.mark.baseline
