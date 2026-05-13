"""TCMB policy rate decision client."""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import requests

from ..models import LocalMacroSignal
from ..thresholds import (
    TCMB_DECISION_MAP,
    TCMB_STALE_DAYS,
)
from .cache_store import LocalMacroCache

logger = logging.getLogger(__name__)


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

    def fetch_and_store(self) -> bool:
        """
        Fetch latest TCMB policy decision from EVDS API.

        Returns: True if success, False if failed (logged)
        """
        api_key = os.getenv("EVDS_API_KEY")
        if not api_key:
            logger.error("TCMBClient.fetch_and_store: EVDS_API_KEY env var not set")
            return False

        try:
            # EVDS v3 endpoint for TP.MK.IE.BSP (policy rate change series)
            # Key passed as query parameter: ?key=...&type=json
            # Note: evds2 redirects to evds3; evds3 currently returns HTML SPA
            url = (
                "https://evds3.tcmb.gov.tr/service/series/TP.MK.IE.BSP"
                f"?startDate=2020-01-01&endDate={datetime.utcnow().strftime('%Y-%m-%d')}"
                f"&key={api_key}&type=json"
            )
            resp = requests.get(url, timeout=5, allow_redirects=True)

            if resp.status_code != 200:
                logger.error(
                    f"TCMBClient.fetch_and_store: HTTP {resp.status_code}: {resp.text[:200]}"
                )
                return False

            data = resp.json()
            if "data" not in data or not data["data"]:
                logger.error(
                    "TCMBClient.fetch_and_store: Empty or missing 'data' field in response"
                )
                return False

            observations = data["data"]
            if len(observations) < 2:
                logger.error(
                    f"TCMBClient.fetch_and_store: Insufficient historical data ({len(observations)} points)"
                )
                return False

            # Sort by date descending, take latest 2
            observations_sorted = sorted(
                observations, key=lambda x: x["Tarih"], reverse=True
            )
            current = float(observations_sorted[0]["Birimi"])
            previous = float(observations_sorted[1]["Birimi"])
            decision_date = observations_sorted[0]["Tarih"]

            # Determine decision type
            if current > previous:
                decision_type = "hike"
            elif current < previous:
                decision_type = "cut"
            else:
                decision_type = "hold"

            # Store in cache
            self.cache.store_tcmb(
                decision_date=decision_date,
                decision_type=decision_type,
                rate_before=previous,
                rate_after=current,
                source="evds_api",
                confidence=1.0,
            )

            logger.info(
                f"TCMBClient.fetch_and_store: Success — {decision_type} at {current}% (was {previous}%)"
            )
            return True

        except requests.exceptions.Timeout:
            logger.error("TCMBClient.fetch_and_store: Request timeout (5s)")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"TCMBClient.fetch_and_store: Network error: {e}")
            return False
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"TCMBClient.fetch_and_store: Parse error: {e}")
            return False
        except Exception as e:
            logger.error(
                f"TCMBClient.fetch_and_store failed: {e.__class__.__name__}: {str(e)}"
            )
            return False

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
