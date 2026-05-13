"""TCMB policy rate decision client."""
from datetime import datetime, timedelta
from typing import Optional

from ..models import LocalMacroSignal
from ..thresholds import (
    TCMB_DECISION_MAP,
    TCMB_STALE_DAYS,
)
from .cache_store import LocalMacroCache


class TCMBClient:
    """TCMB policy rate decision fetcher."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_decision(self) -> Optional[dict]:
        """Get latest TCMB decision from cache."""
        return self.cache.get_latest_tcmb()

    def interpret_decision(self, decision_type: str) -> float:
        """Convert decision type to signal score (0-100)."""
        return TCMB_DECISION_MAP.get(decision_type, 50.0)

    def score(self) -> LocalMacroSignal:
        """
        Generate TCMB signal score.

        Logic:
        - Fresh decision (< TCMB_STALE_DAYS): confidence = 1.0
        - Stale decision (> TCMB_STALE_DAYS): confidence = 0.7
        - No decision: score = 50.0 (neutral), confidence = 0.0
        """
        decision = self.get_latest_decision()

        if not decision:
            return LocalMacroSignal(
                component="tcmb",
                score=50.0,
                confidence=0.0,
                raw_value=None,
                last_update=None,
                data_freshness="missing",
                audit_msg="No TCMB decision in cache",
            )

        # Calculate freshness
        decision_date_str = decision["decision_date"]
        decision_datetime = datetime.fromisoformat(decision_date_str)
        age_days = (datetime.utcnow() - decision_datetime).days

        if age_days <= TCMB_STALE_DAYS:
            confidence = 1.0
            freshness = "fresh"
        else:
            confidence = 0.7
            freshness = "stale"

        score = self.interpret_decision(decision["decision_type"])

        return LocalMacroSignal(
            component="tcmb",
            score=score,
            confidence=confidence,
            raw_value=decision.get("rate_after"),
            last_update=decision_date_str,
            data_freshness=freshness,
            audit_msg=(
                f"Decision: {decision['decision_type']} "
                f"on {decision_date_str} "
                f"(age: {age_days}d, conf: {confidence})"
            ),
        )
