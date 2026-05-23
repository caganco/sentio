"""CDS spreads (Turkey 5Y) client."""
import logging
from datetime import datetime

from ..models import LocalMacroSignal
from ..thresholds import (
    CDS_SCORES,
    CDS_STALE_DAYS,
    CDS_THRESHOLDS,
    TL_BOND_PROXY_BASE_YIELD,
    TL_BOND_PROXY_SCORES,
    TL_BOND_PROXY_THRESHOLDS,
)
from .cache_store import LocalMacroCache

logger = logging.getLogger(__name__)


class CDSClient:
    """Turkey 5Y CDS spreads fetcher (World Government Bonds scraping stub)."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def get_latest_cds(self) -> dict | None:
        """Get latest CDS data from cache."""
        return self.cache.get_latest_cds()

    def fetch_and_store(self) -> bool:
        """Fetch Turkey 5Y CDS via cds_fetcher (WGB API → yfinance proxy).

        Returns: True if a value was fetched and stored, False on total failure.
        """
        from src.data.cds_fetcher import fetch_turkey_cds_bps

        cds_value = fetch_turkey_cds_bps()
        if cds_value is None:
            logger.error("CDSClient.fetch_and_store: all sources failed")
            return False

        source = "worldgovernmentbonds_api" if cds_value > 0 else "yfinance_proxy"
        self.cache.store_cds(
            data_date=datetime.utcnow().strftime("%Y-%m-%d"),
            cds_bps=cds_value,
            source=source,
            confidence=0.9,
        )
        logger.info(
            f"CDSClient.fetch_and_store: Success — Turkey 5Y CDS = {cds_value:.1f} bps "
            f"(source: {source})"
        )
        return True

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

    def get_tl_bond_proxy(self) -> LocalMacroSignal:
        """CDS-based implied TL bond yield proxy (Gap 4 — SPEC_L2_ENHANCEMENT_1).

        Formula: implied_tl_yield (%) = TL_BOND_PROXY_BASE_YIELD + cds_bps / 100
        Example: base=4.5%, CDS=300bps → implied=7.5% → medium bucket → score=50.

        Phase 5: Replace with native TL yields (ICDP/MINT data integration).
        """
        cds_data = self.get_latest_cds()
        if not cds_data:
            return LocalMacroSignal(
                component="tl_bond_proxy",
                score=50.0,
                confidence=0.0,
                raw_value=None,
                last_update=None,
                data_freshness="missing",
                audit_msg="No CDS data — TL bond proxy unavailable",
            )

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
        implied_yield = round(TL_BOND_PROXY_BASE_YIELD + cds_bps / 100.0, 4)

        if implied_yield < TL_BOND_PROXY_THRESHOLDS["low"]:
            bucket = "low"
        elif implied_yield < TL_BOND_PROXY_THRESHOLDS["medium"]:
            bucket = "medium"
        elif implied_yield < TL_BOND_PROXY_THRESHOLDS["high"]:
            bucket = "high"
        else:
            bucket = "extreme"

        proxy_score = TL_BOND_PROXY_SCORES[bucket]

        return LocalMacroSignal(
            component="tl_bond_proxy",
            score=proxy_score,
            confidence=confidence,
            raw_value=implied_yield,   # implied_tl_real_rate in %
            last_update=cds_date_str,
            data_freshness=freshness,
            audit_msg=(
                f"implied_tl_yield={implied_yield:.2f}% "
                f"(CDS={cds_bps:.1f}bps, bucket={bucket}) "
                f"score={proxy_score} conf={confidence}"
            ),
        )
