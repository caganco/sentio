"""CDS spreads (Turkey 5Y) client."""
from datetime import datetime, timedelta
from typing import Optional

from ..models import LocalMacroSignal
from ..thresholds import (
    CDS_SCORES,
    CDS_STALE_DAYS,
    CDS_THRESHOLDS,
)
from .cache_store import LocalMacroCache


class CDSClient:
    """Turkey 5Y CDS spreads fetcher (World Government Bonds scraping stub)."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_cds(self) -> Optional[dict]:
        """Get latest CDS data from cache."""
        return self.cache.get_latest_cds()

    def cds_to_score(self, cds_bps: float) -> tuple[float, str]:
        """
        Convert CDS basis points to signal score (0-100).

        Returns: (score, risk_level)
        """
        for risk_level, (lower, upper) in CDS_THRESHOLDS.items():
            if lower <= cds_bps < upper:
                return CDS_SCORES[risk_level], risk_level

        # Fallback: extreme risk
        return CDS_SCORES["extreme_risk"], "extreme_risk"

    def score(self) -> LocalMacroSignal:
        """
        Generate CDS signal score.

        Logic:
        - Fresh CDS data (< CDS_STALE_DAYS): confidence = 1.0
        - Stale data (< 5 days): confidence = 0.8
        - Very stale (> 5 days): confidence = 0.4
        - No data: score = 50.0 (neutral), confidence = 0.0
        """
        cds_data = self.get_latest_cds()

        if not cds_data:
            return LocalMacroSignal(
                component="cds",
                score=50.0,
                confidence=0.0,
                raw_value=None,
                last_update=None,
                data_freshness="missing",
                audit_msg="No CDS data in cache",
            )

        # Calculate freshness
        cds_date_str = cds_data["data_date"]
        cds_datetime = datetime.fromisoformat(cds_date_str)
        age_days = (datetime.utcnow() - cds_datetime).days

        if age_days <= CDS_STALE_DAYS:
            confidence = 1.0
            freshness = "fresh"
        elif age_days <= 5:
            confidence = 0.8
            freshness = "stale"
        else:
            confidence = 0.4
            freshness = "very_stale"

        cds_bps = cds_data["cds_bps"]
        score, risk_level = self.cds_to_score(cds_bps)

        return LocalMacroSignal(
            component="cds",
            score=score,
            confidence=confidence,
            raw_value=cds_bps,
            last_update=cds_date_str,
            data_freshness=freshness,
            audit_msg=(
                f"CDS {cds_bps:.1f} bps ({risk_level}) "
                f"from {cds_date_str} "
                f"(age: {age_days}d, conf: {confidence})"
            ),
        )
