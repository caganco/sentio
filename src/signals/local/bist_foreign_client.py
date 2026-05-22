"""BIST foreign ownership weekly (macro context only)."""
import logging
import os
from datetime import datetime

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

    def get_latest_weekly(self) -> dict | None:
        """Get latest BIST foreign ownership weekly data."""
        return self.cache.get_latest_bist_foreign()

    # Expanded BIST foreign-ownership series candidates. The legacy codes
    # produced "No valid series found"; TCMB also migrated the REST host
    # (old path now serves the EVDS web SPA). Try the documented post-2024
    # endpoint with this list, then the YAML/cache fallback (DEC-002 pattern).
    # D-089 Research Agent: BIST foreign-share series live in the EVDS2
    # "bie_mkbrgn" datagroup. Exact codes resolvable via the serieMarket
    # browser:
    #   https://evds2.tcmb.gov.tr/index.php?/evds/serieMarket/...bie_mkbrgn/
    # bie_mkbrgn-derived candidates are tried first, then the legacy codes.
    _EVDS_FOREIGN_SERIES = (
        "TP.MKBRGN.A",         # bie_mkbrgn: foreign ownership ratio (equities)
        "TP.MKBRGN.EU",        # bie_mkbrgn: foreign holdings (alt unit)
        "TP.HVYNBNK.Y",        # foreign ownership share (equities)
        "TP.HSDB.Y",           # foreign holdings — equities
        "TP.DNYBNK.ADBK",      # legacy spec'd candidate
        "TP.DNYBNK",           # legacy alt
        "TP.YBNK.ADBK",        # legacy alt
    )
    _EVDS_BASE = "https://evds2.tcmb.gov.tr/service/evds/"

    @staticmethod
    def _extract_value(obs: dict) -> float | None:
        """Pull the numeric series column (named after the series code, not
        "Birimi") from an EVDS item, skipping metadata fields."""
        for key, val in obs.items():
            if key in ("Tarih", "UNIXTIME", "YEARWEEK"):
                continue
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
        return None

    def _fallback_ok(self, context: str) -> bool:
        """Succeed if YAML/cache already holds a foreign-ownership record.

        daily_update.py runs cache.load_from_yaml_fallback() first, so a
        migrated/unreachable live API still leaves a usable macro signal
        (CDS primary->proxy->cache analogue, DEC-002)."""
        latest = self.cache.get_latest_bist_foreign()
        if latest:
            logger.info(
                f"BistForeignClient.fetch_and_store: {context} — using "
                f"YAML/cache fallback ({latest.get('foreign_ownership_pct')}% "
                f"@ {latest.get('week_ending_date')})"
            )
            return True
        logger.error(
            f"BistForeignClient.fetch_and_store: {context} and no fallback "
            f"in cache"
        )
        return False

    def fetch_and_store(self) -> bool:
        """Fetch BIST foreign ownership weekly data from the EVDS API.

        Tries the documented post-2024 EVDS endpoint
        (``GET /service/evds/?series=<code>...``, API key in the ``key``
        header) across an expanded series list. On live-API unavailability
        (migrated host serving HTML SPA, network error, non-JSON, HTTP
        error), gracefully degrades to the YAML/cache fallback.

        Returns: True if a live fetch *or* the fallback yields a record.
        """
        api_key = os.getenv("EVDS_API_KEY")
        if not api_key:
            return self._fallback_ok("EVDS_API_KEY env var not set")

        start_date = "01-01-2020"
        end_date = datetime.utcnow().strftime("%d-%m-%Y")

        for series_id in self._EVDS_FOREIGN_SERIES:
            url = (
                f"{self._EVDS_BASE}?series={series_id}"
                f"&startDate={start_date}&endDate={end_date}&type=json"
            )
            try:
                resp = requests.get(url, headers={"key": api_key}, timeout=3)
            except requests.exceptions.RequestException as e:
                logger.warning(f"BistForeignClient: {series_id} network error: {e}")
                continue

            if resp.status_code != 200:
                logger.warning(
                    f"BistForeignClient: {series_id} HTTP {resp.status_code}"
                )
                continue

            # Migrated host serves the EVDS SPA (HTML) for every path.
            # If any series returns non-JSON, all others will too — break.
            ct = resp.headers.get("Content-Type", "")
            if "html" in ct.lower():
                logger.warning(
                    f"BistForeignClient: {series_id} HTML response — EVDS "
                    f"migrated, aborting series loop"
                )
                break
            try:
                data = resp.json()
            except ValueError:
                logger.warning(
                    f"BistForeignClient: {series_id} non-JSON body — EVDS "
                    f"migrated, aborting series loop"
                )
                break

            observations = data.get("items") or data.get("data") or []
            if not observations:
                logger.warning(
                    f"BistForeignClient: {series_id} empty data"
                )
                continue

            observations_sorted = sorted(
                observations, key=lambda x: x.get("Tarih", ""), reverse=True
            )
            foreign_pct = self._extract_value(observations_sorted[0])
            if foreign_pct is None:
                logger.warning(
                    f"BistForeignClient: {series_id} no numeric value column"
                )
                continue

            pct_change = 0.0
            if len(observations_sorted) >= 2:
                prev = self._extract_value(observations_sorted[1])
                if prev is not None:
                    pct_change = foreign_pct - prev

            self.cache.store_bist_foreign(
                week_ending_date=observations_sorted[0]["Tarih"],
                foreign_ownership_pct=foreign_pct,
                pct_change_weekly=pct_change,
                source=f"evds_api_{series_id}",
                confidence=0.9,
            )
            logger.info(
                f"BistForeignClient.fetch_and_store: Success "
                f"(series={series_id}) — Foreign ownership "
                f"{foreign_pct:.2f}% (change: {pct_change:+.2f}%)"
            )
            return True

        return self._fallback_ok("EVDS live API unavailable")

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
