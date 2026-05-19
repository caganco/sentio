"""TCMB policy rate decision client."""
import logging
import os
from datetime import datetime, timedelta

import requests

from ..models import LocalMacroSignal
from ..thresholds import (
    TCMB_DECISION_MAP,
    TCMB_STALE_DAYS,
    TCMB_TREND_SCORES,
)
from .cache_store import LocalMacroCache

logger = logging.getLogger(__name__)


class TCMBClient:
    """TCMB policy rate decision fetcher."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_decision(self) -> dict | None:
        """Get latest TCMB decision from cache."""
        return self.cache.get_latest_tcmb()

    def interpret_decision(self, decision_type: str) -> float:
        """Convert decision type to signal score (0-100)."""
        return TCMB_DECISION_MAP.get(decision_type, 50.0)

    def calculate_trend(self) -> dict:
        """Analyze rate direction trend from recent TCMB decisions.

        Returns dict with keys:
            category (str): one of cutting_cycle / easing / holding /
                            tightening / hiking_cycle / unknown
            delta_3m, delta_6m, delta_12m (float|None): rate_after deltas
                over the respective rolling windows (positive = tightening).
        """
        history = self.cache.get_tcmb_history(n=15)
        if not history:
            return {"category": "unknown", "delta_3m": None, "delta_6m": None, "delta_12m": None}

        # --- Inflection detection ---
        # history[0] = most recent; history[1] = one before
        last_type = history[0]["decision_type"]

        if len(history) >= 2:
            prev_type = history[1]["decision_type"]
            if last_type == "cut" and prev_type == "hike":
                category = "cutting_cycle"
            elif last_type == "hike" and prev_type == "cut":
                category = "hiking_cycle"
            elif last_type == "cut":
                category = "easing"
            elif last_type == "hike":
                category = "tightening"
            else:
                # hold — inherit direction from prior non-hold decision
                category = "holding"
                for h in history[1:]:
                    if h["decision_type"] in ("cut", "hike"):
                        category = "easing" if h["decision_type"] == "cut" else "tightening"
                        break
        else:
            if last_type == "cut":
                category = "easing"
            elif last_type == "hike":
                category = "tightening"
            else:
                category = "holding"

        # --- Rate deltas ---
        latest_rate = history[0].get("rate_after")
        now = datetime.utcnow()

        def _delta_for_months(months: int) -> float | None:
            if latest_rate is None:
                return None
            cutoff = now - timedelta(days=months * 30)
            candidates = [
                h for h in history[1:]
                if h.get("rate_after") is not None
                and datetime.fromisoformat(h["decision_date"]) <= cutoff
            ]
            if not candidates:
                return None
            # Pick the decision closest to the cutoff date
            ref_rate = candidates[0]["rate_after"]
            return round(latest_rate - ref_rate, 4)

        return {
            "category": category,
            "delta_3m":  _delta_for_months(3),
            "delta_6m":  _delta_for_months(6),
            "delta_12m": _delta_for_months(12),
        }

    def fetch_and_store(self) -> bool:
        """
        Fetch latest TCMB policy decision from EVDS API.

        EVDS v3 correct format:
        - URL: https://evds3.tcmb.gov.tr/igmevdsms-dis/series=SERI_KODU&startDate=dd-mm-yyyy&endDate=dd-mm-yyyy&type=json
        - API key in header: {"key": "..."}
        - Date format: dd-mm-yyyy

        Returns: True if success, False if failed (logged)
        """
        api_key = os.getenv("EVDS_API_KEY")
        if not api_key:
            logger.error("TCMBClient.fetch_and_store: EVDS_API_KEY env var not set")
            return False

        try:
            # EVDS v3 endpoint for TP.MK.IE.BSP (policy rate change series)
            # Endpoint: https://evds3.tcmb.gov.tr/igmevdsms-dis/
            # API key in header: {"key": "..."}
            # Date format: dd-mm-yyyy (per TCMB docs, returns 400 but progresses)
            # Note: Endpoint currently in development/migration; fallback YAML active
            start_date = "01-01-2020"
            end_date = datetime.utcnow().strftime("%d-%m-%Y")

            url = (
                "https://evds3.tcmb.gov.tr/igmevdsms-dis/series=TP.MK.IE.BSP"
                f"&startDate={start_date}&endDate={end_date}&type=json"
            )
            headers = {"key": api_key}
            resp = requests.get(url, headers=headers, timeout=5)

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

        base_score = self.interpret_decision(decision["decision_type"])
        trend = self.calculate_trend()
        score = TCMB_TREND_SCORES.get(trend["category"], base_score)

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
                f"(age: {age_days}d, conf: {confidence}, "
                f"trend: {trend['category']}, score: {score})"
            ),
        )
