"""BIST foreign ownership weekly (macro context only)."""
from datetime import datetime, timedelta
from typing import Optional

from ..models import LocalMacroSignal
from ..thresholds import (
    BIST_FOREIGN_STALE_DAYS,
    BIST_FOREIGN_THRESHOLD_INFLOW,
    BIST_FOREIGN_THRESHOLD_OUTFLOW,
)
from .cache_store import LocalMacroCache


class BistForeignOwnershipClient:
    """BIST haftalık yabancı pay oranı (macro context, not Bull Trap detection)."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_weekly(self) -> Optional[dict]:
        """Get latest BIST foreign ownership weekly data."""
        return self.cache.get_latest_bist_foreign()

    def weekly_change_to_score(self, weekly_pct_change: float) -> float:
        """
        Convert weekly ownership % change to signal score (0-100).

        Logic:
        - Positive change (inflow): bullish (base 50 + contribution)
        - Negative change (outflow): bearish (base 50 - contribution)
        - Linear scaling: each 0.2% change -> ~10 points
        """
        base_score = 50.0

        if weekly_pct_change > BIST_FOREIGN_THRESHOLD_INFLOW:
            # Strong inflow: +0.2% to +0.4% -> +10 to +20 points
            contribution = min(20.0, abs(weekly_pct_change) * 50)
        elif weekly_pct_change < BIST_FOREIGN_THRESHOLD_OUTFLOW:
            # Strong outflow: -0.2% to -0.4% -> -10 to -20 points
            contribution = -min(20.0, abs(weekly_pct_change) * 50)
        else:
            # Neutral: within threshold -> linear
            contribution = weekly_pct_change * 50

        score = base_score + contribution
        return max(20.0, min(80.0, score))  # Clamp to 20-80

    def score(self) -> LocalMacroSignal:
        """
        Generate BIST foreign ownership signal score.

        Logic:
        - Fresh data (< BIST_FOREIGN_STALE_DAYS): confidence = 0.9
        - Stale data (< 14 days): confidence = 0.7
        - Very stale (> 14 days): confidence = 0.4
        - No data: score = 50.0 (neutral), confidence = 0.0

        Note: This is MACRO context only (weekly trend).
        Bull Trap detection (daily granular data) -> Layer 5 (SmartMoneyLayer).
        """
        foreign_data = self.get_latest_weekly()

        if not foreign_data:
            return LocalMacroSignal(
                component="bist_foreign_weekly",
                score=50.0,
                confidence=0.0,
                raw_value=None,
                last_update=None,
                data_freshness="missing",
                audit_msg="No BIST foreign ownership data in cache",
            )

        # Calculate freshness
        week_date_str = foreign_data["week_ending_date"]
        week_datetime = datetime.fromisoformat(week_date_str)
        age_days = (datetime.utcnow() - week_datetime).days

        if age_days <= BIST_FOREIGN_STALE_DAYS:
            confidence = 0.9
            freshness = "fresh"
        elif age_days <= 14:
            confidence = 0.7
            freshness = "stale"
        else:
            confidence = 0.4
            freshness = "very_stale"

        weekly_change = foreign_data.get("pct_change_weekly", 0.0) or 0.0
        score = self.weekly_change_to_score(weekly_change)
        current_pct = foreign_data["foreign_ownership_pct"]

        return LocalMacroSignal(
            component="bist_foreign_weekly",
            score=score,
            confidence=confidence,
            raw_value=current_pct,
            last_update=week_date_str,
            data_freshness=freshness,
            audit_msg=(
                f"BIST foreign {current_pct:.2f}% "
                f"(weekly change: {weekly_change:+.2f}%) "
                f"from {week_date_str} "
                f"(age: {age_days}d, conf: {confidence})"
            ),
        )
