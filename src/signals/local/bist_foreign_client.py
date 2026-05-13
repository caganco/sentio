"""BIST foreign ownership weekly (macro context only)."""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import requests

from ..models import LocalMacroSignal
from ..thresholds import (
    BIST_FOREIGN_STALE_DAYS,
    BIST_FOREIGN_THRESHOLD_INFLOW,
    BIST_FOREIGN_THRESHOLD_OUTFLOW,
)
from .cache_store import LocalMacroCache

logger = logging.getLogger(__name__)


class BistForeignOwnershipClient:
    """BIST haftalık yabancı pay oranı (macro context, not Bull Trap detection)."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_weekly(self) -> Optional[dict]:
        """Get latest BIST foreign ownership weekly data."""
        return self.cache.get_latest_bist_foreign()

    def fetch_and_store(self) -> bool:
        """
        Fetch BIST foreign ownership weekly data from EVDS API.

        Series ID: TP.DNYBNK.ADBK (TBD: confirm if not found)
        Returns: True if success, False if failed (logged)
        """
        api_key = os.getenv("EVDS_API_KEY")
        if not api_key:
            logger.error(
                "BistForeignClient.fetch_and_store: EVDS_API_KEY env var not set"
            )
            return False

        # Try multiple potential series IDs for BIST foreign ownership
        series_ids = [
            "TP.DNYBNK.ADBK",  # Primary candidate (spec'd)
            "TP.DNYBNK",  # Alternative
            "TP.YBNK.ADBK",  # Alternative
        ]

        try:
            for series_id in series_ids:
                # EVDS v3 endpoint: key passed as query parameter
                # Note: evds2 redirects to evds3; evds3 currently returns HTML SPA
                url = (
                    f"https://evds3.tcmb.gov.tr/service/series/{series_id}"
                    f"?startDate=2020-01-01&endDate={datetime.utcnow().strftime('%Y-%m-%d')}"
                    f"&frequency=weekly&key={api_key}&type=json"
                )
                resp = requests.get(url, timeout=5, allow_redirects=True)

                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and data["data"]:
                        observations = data["data"]
                        # Sort by date, take latest
                        observations_sorted = sorted(
                            observations, key=lambda x: x["Tarih"], reverse=True
                        )
                        latest = observations_sorted[0]
                        week_ending_date = latest["Tarih"]
                        foreign_pct = float(latest["Birimi"])

                        # Calculate weekly change if we have 2+ points
                        pct_change = 0.0
                        if len(observations_sorted) >= 2:
                            previous = float(observations_sorted[1]["Birimi"])
                            pct_change = foreign_pct - previous

                        self.cache.store_bist_foreign(
                            week_ending_date=week_ending_date,
                            foreign_ownership_pct=foreign_pct,
                            pct_change_weekly=pct_change,
                            source=f"evds_api_{series_id}",
                            confidence=0.9,
                        )

                        logger.info(
                            f"BistForeignClient.fetch_and_store: Success (series={series_id}) — "
                            f"Foreign ownership {foreign_pct:.2f}% (change: {pct_change:+.2f}%)"
                        )
                        return True

            # No series ID worked
            logger.error(
                f"BistForeignClient.fetch_and_store: No valid series found. Tried: {series_ids}"
            )
            return False

        except requests.exceptions.Timeout:
            logger.error("BistForeignClient.fetch_and_store: Request timeout (5s)")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"BistForeignClient.fetch_and_store: Network error: {e}")
            return False
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"BistForeignClient.fetch_and_store: Parse error: {e}")
            return False
        except Exception as e:
            logger.error(
                f"BistForeignClient.fetch_and_store failed: {e.__class__.__name__}: {str(e)}"
            )
            return False

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
