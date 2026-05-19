"""CDS spreads (Turkey 5Y) client."""
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

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
        """
        Fetch Turkey 5Y CDS spreads from worldgovernmentbonds.com.

        Returns: True if success, False if failed (logged)
        """
        try:
            url = "https://www.worldgovernmentbonds.com/country/turkey/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code != 200:
                logger.error(
                    f"CDSClient.fetch_and_store: HTTP {resp.status_code} from {url}"
                )
                return False

            soup = BeautifulSoup(resp.content, "html.parser")

            # Look for "5Y CDS: XXX" or similar patterns in full page text
            page_text = soup.get_text()

            # Pattern: "5Y CDS: 287.5" or "5 Y CDS 287.5" etc
            match = re.search(r"5\s*Y.*?CDS\s*[:=]?\s*(\d+\.?\d*)", page_text, re.IGNORECASE)
            cds_value = None

            if match:
                cds_value = float(match.group(1))

            # Fallback: Look for largest number > 100 (CDS spreads are typically > 100 bps)
            if not cds_value:
                numbers = re.findall(r"(\d+\.?\d*)", page_text)
                for num_str in numbers:
                    val = float(num_str)
                    if 100 < val < 1000:  # CDS range is typically 100-1000 bps
                        cds_value = val
                        break

            if not cds_value:
                logger.error("CDSClient.fetch_and_store: CDS 5Y value not found on page")
                return False

            # Store in cache with today's date
            self.cache.store_cds(
                data_date=datetime.utcnow().strftime("%Y-%m-%d"),
                cds_bps=cds_value,
                source="worldgovernmentbonds_scrape",
                confidence=0.9,
            )

            logger.info(
                f"CDSClient.fetch_and_store: Success — Turkey 5Y CDS = {cds_value:.1f} bps"
            )
            return True

        except requests.exceptions.Timeout:
            logger.error("CDSClient.fetch_and_store: Request timeout (10s)")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"CDSClient.fetch_and_store: Network error: {e}")
            return False
        except (ValueError, AttributeError) as e:
            logger.error(f"CDSClient.fetch_and_store: Parse error: {e}")
            return False
        except Exception as e:
            logger.error(
                f"CDSClient.fetch_and_store failed: {e.__class__.__name__}: {str(e)}"
            )
            return False

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
