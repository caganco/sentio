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

    # EVDS policy-rate series candidates. The legacy codes silently changed;
    # TCMB also migrated the REST host (the old path now serves the EVDS web
    # SPA). We try the documented post-2024 endpoint with this expanded list,
    # then fall back to the YAML/cache value (DEC-002 fallback-chain pattern).
    _EVDS_POLICY_SERIES = (
        "TP.APIFON4",          # D-089 Research Agent: confirmed policy-rate
                               # series (1-week repo / weighted avg cost of
                               # CB funding) — primary, tried first
        "TP.PY.P01",           # policy (1-week repo) rate
        "TP.FAIZ.PYUVDL",      # late-liquidity / policy corridor
        "TP.MK.IE.BSP",        # legacy code (kept last for compatibility)
    )
    # Documented endpoint after the 05/04/2024 change: query string starts
    # with "?series=" (no "?" -> server returns the SPA HTML), key in header.
    _EVDS_BASE = "https://evds2.tcmb.gov.tr/service/evds/"

    @staticmethod
    def _extract_value(obs: dict) -> float | None:
        """Pull the numeric series column from an EVDS item.

        EVDS names the value column after the series code (dots -> underscores),
        not "Birimi". Pick the first numeric, non-metadata field generically.
        """
        for key, val in obs.items():
            if key in ("Tarih", "UNIXTIME", "YEARWEEK"):
                continue
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _scrape_tcmb_rate() -> float | None:
        """Scrape current TCMB policy rate from tcmb.gov.tr (first-party source).

        Returns the rate as a float (e.g. 37.0), or None on failure.
        Fallback chain: EVDS → tcmb.gov.tr scrape → YAML/cache (D-095).
        """
        try:
            from src.data.tcmb_scraper import fetch_tcmb_policy_rate
            return fetch_tcmb_policy_rate()
        except Exception as exc:
            logger.warning(f"TCMBClient: tcmb.gov.tr scraper error: {exc}")
            return None

    def _fallback_ok(self, context: str) -> bool:
        """Graceful degradation: succeed if YAML/cache already has a decision.

        daily_update.py calls cache.load_from_yaml_fallback() before fetch, so
        when the live EVDS API is unreachable/migrated we still have a usable
        macro signal. Mirrors the CDS primary->proxy->cache chain (DEC-002).
        """
        latest = self.cache.get_latest_tcmb()
        if latest:
            logger.info(
                f"TCMBClient.fetch_and_store: {context} — using YAML/cache "
                f"fallback ({latest.get('decision_type')} on "
                f"{latest.get('decision_date')})"
            )
            return True
        logger.error(
            f"TCMBClient.fetch_and_store: {context} and no fallback in cache"
        )
        return False

    def fetch_and_store(self) -> bool:
        """Fetch the latest TCMB policy decision from the EVDS API.

        Tries the documented post-2024 EVDS endpoint
        (``GET /service/evds/?series=<code>...``, API key in the ``key``
        header) across an expanded series list. If the live API is
        unavailable (TCMB-side migration now serves an HTML SPA, network
        error, non-JSON, or HTTP error), gracefully degrades to the
        YAML/cache fallback.

        Returns: True if a live fetch *or* the fallback yields a decision.
        """
        api_key = os.getenv("EVDS_API_KEY")
        if not api_key:
            return self._fallback_ok("EVDS_API_KEY env var not set")

        start_date = "01-01-2020"
        end_date = datetime.utcnow().strftime("%d-%m-%Y")

        for series in self._EVDS_POLICY_SERIES:
            url = (
                f"{self._EVDS_BASE}?series={series}"
                f"&startDate={start_date}&endDate={end_date}&type=json"
            )
            try:
                resp = requests.get(url, headers={"key": api_key}, timeout=3)
            except requests.exceptions.RequestException as e:
                logger.warning(f"TCMBClient: {series} network error: {e}")
                continue

            if resp.status_code != 200:
                logger.warning(
                    f"TCMBClient: {series} HTTP {resp.status_code}"
                )
                continue

            # Migrated host serves the EVDS SPA (HTML) for every path.
            # If any series returns non-JSON, all others will too — break.
            ct = resp.headers.get("Content-Type", "")
            if "html" in ct.lower():
                logger.warning(
                    f"TCMBClient: {series} HTML response — EVDS migrated, "
                    f"aborting series loop"
                )
                break
            try:
                data = resp.json()
            except ValueError:
                logger.warning(
                    f"TCMBClient: {series} non-JSON body — EVDS migrated, "
                    f"aborting series loop"
                )
                break

            observations = data.get("items") or data.get("data") or []
            if len(observations) < 2:
                logger.warning(
                    f"TCMBClient: {series} insufficient data "
                    f"({len(observations)} points)"
                )
                continue

            observations_sorted = sorted(
                observations, key=lambda x: x.get("Tarih", ""), reverse=True
            )
            current = self._extract_value(observations_sorted[0])
            previous = self._extract_value(observations_sorted[1])
            if current is None or previous is None:
                logger.warning(
                    f"TCMBClient: {series} no numeric value column"
                )
                continue

            if current > previous:
                decision_type = "hike"
            elif current < previous:
                decision_type = "cut"
            else:
                decision_type = "hold"

            self.cache.store_tcmb(
                decision_date=observations_sorted[0]["Tarih"],
                decision_type=decision_type,
                rate_before=previous,
                rate_after=current,
                source=f"evds_api_{series}",
                confidence=1.0,
            )
            logger.info(
                f"TCMBClient.fetch_and_store: Success (series={series}) — "
                f"{decision_type} at {current}% (was {previous}%)"
            )
            return True

        # EVDS unavailable — try tcmb.gov.tr scraper before YAML (D-095)
        logger.warning("TCMBClient: EVDS unavailable, trying tcmb.gov.tr scraper")
        scraped_rate = self._scrape_tcmb_rate()
        if scraped_rate is not None:
            latest = self.cache.get_latest_tcmb()
            prev_rate = latest.get("rate_after") if latest else None

            if prev_rate is not None:
                if scraped_rate > prev_rate:
                    decision_type = "hike"
                elif scraped_rate < prev_rate:
                    decision_type = "cut"
                else:
                    decision_type = "hold"
            else:
                decision_type = "hold"

            self.cache.store_tcmb(
                decision_date=datetime.utcnow().strftime("%Y-%m-%d"),
                decision_type=decision_type,
                rate_before=prev_rate or scraped_rate,
                rate_after=scraped_rate,
                source="tcmb_gov_scrape",
                confidence=0.9,
            )
            logger.info(
                f"TCMBClient: tcmb.gov.tr scrape success — {decision_type} at {scraped_rate}% "
                f"(was {prev_rate}%)"
            )
            return True

        return self._fallback_ok("EVDS and tcmb.gov.tr scraper both unavailable")

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
