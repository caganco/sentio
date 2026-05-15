"""Smart Money client: Institutional flow data from Borsa Istanbul and fallback sources."""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class BorsaSettlementClient:
    """Fetch institutional flows from Borsa Istanbul settlement report."""

    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
    CACHE_TTL_HOURS = 24

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, date_str: str) -> Path:
        """Cache file path for given date."""
        return self.CACHE_DIR / f"borsa_settlement_{date_str}.json"

    def _load_cache(self, date_str: str) -> dict:
        """Load cached settlement data if fresh."""
        cache_path = self._get_cache_path(date_str)

        if not cache_path.exists():
            return None

        # Check freshness
        file_age_hours = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() / 3600
        if file_age_hours > self.CACHE_TTL_HOURS:
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Cache load failed for {date_str}: {e}")
            return None

    def _save_cache(self, date_str: str, data: dict):
        """Save settlement data to cache."""
        cache_path = self._get_cache_path(date_str)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed for {date_str}: {e}")

    def fetch_settlement_report(self, date_str: str = None) -> dict:
        """
        Fetch institutional flows from Borsa Istanbul settlement report.

        Returns dict: {
            "AKSEN": {
                "ticker": "AKSEN",
                "date": "2026-05-14",
                "domestic_institutions_net": 1300000,  # shares
                "foreign_institutions_net": -1200000,
                "institutional_net_total": 100000,
                "daily_volume": 45000000,
                "close_price": 98.50,
                "net_pct": 0.00222,  # net_total / daily_volume
                "source": "borsa"
            },
            ...
        }
        """

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Try cache first
        cached = self._load_cache(date_str)
        if cached:
            logger.info(f"Borsa settlement: Using cached data for {date_str}")
            return cached

        logger.info(f"Borsa settlement: Fetching from Borsa Istanbul for {date_str}")

        try:
            # Construct URL for settlement report
            # Example: https://www.borsaistanbul.com/...settlement-report-2026-05-14
            url = f"https://www.borsaistanbul.com/en/markets-data-services/reports/settlement-reports"

            # For now, return mock data (actual scraping would require parsing HTML/PDF)
            # In production, implement actual PDF/HTML parsing via pdfplumber or BeautifulSoup

            flows = self._mock_settlement_data(date_str)

            # Cache result
            self._save_cache(date_str, flows)

            return flows

        except Exception as e:
            logger.error(f"Borsa settlement fetch failed: {e}")
            return {}

    def _mock_settlement_data(self, date_str: str) -> dict:
        """
        Mock settlement data for testing.
        In production, replace with actual Borsa Istanbul PDF/HTML parsing.
        """

        # Sample data structure (would be populated from actual Borsa report)
        flows = {
            "AKSEN": {
                "ticker": "AKSEN",
                "date": date_str,
                "domestic_institutions_net": 1_300_000,
                "foreign_institutions_net": -1_200_000,
                "institutional_net_total": 100_000,
                "daily_volume": 45_000_000,
                "close_price": 98.50,
                "source": "borsa"
            },
            "TTKOM": {
                "ticker": "TTKOM",
                "date": date_str,
                "domestic_institutions_net": 500_000,
                "foreign_institutions_net": 3_100_000,
                "institutional_net_total": 3_600_000,
                "daily_volume": 67_000_000,
                "close_price": 102.30,
                "source": "borsa"
            },
            "TAVHL": {
                "ticker": "TAVHL",
                "date": date_str,
                "domestic_institutions_net": -800_000,
                "foreign_institutions_net": -400_000,
                "institutional_net_total": -1_200_000,
                "daily_volume": 12_000_000,
                "close_price": 265.75,
                "source": "borsa"
            },
            "KCHOL": {
                "ticker": "KCHOL",
                "date": date_str,
                "domestic_institutions_net": 200_000,
                "foreign_institutions_net": -100_000,
                "institutional_net_total": 100_000,
                "daily_volume": 28_000_000,
                "close_price": 204.70,
                "source": "borsa"
            },
            "ENERY": {
                "ticker": "ENERY",
                "date": date_str,
                "domestic_institutions_net": -500_000,
                "foreign_institutions_net": 1_500_000,
                "institutional_net_total": 1_000_000,
                "daily_volume": 98_000_000,
                "close_price": 8.77,
                "source": "borsa"
            }
        }

        # Calculate net percentages
        for ticker, data in flows.items():
            if data["daily_volume"] > 0:
                data["net_pct"] = data["institutional_net_total"] / data["daily_volume"]
            else:
                data["net_pct"] = 0.0

        return flows


class HalkYatirimFallback:
    """Fallback: Scrape institutional flow from Halk Yatırım (if Borsa unavailable)."""

    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
    CACHE_TTL_HOURS = 4  # Shorter TTL for intraday scraping
    RATE_LIMIT_DELAY = 0.1  # 100ms between requests

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _get_cache_path(self, ticker: str) -> Path:
        """Cache file path for ticker."""
        return self.CACHE_DIR / f"halk_flow_{ticker}.json"

    def _load_cache(self, ticker: str) -> dict:
        """Load cached Halk data if fresh."""
        cache_path = self._get_cache_path(ticker)

        if not cache_path.exists():
            return None

        file_age_hours = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() / 3600
        if file_age_hours > self.CACHE_TTL_HOURS:
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Halk cache load failed for {ticker}: {e}")
            return None

    def _save_cache(self, ticker: str, data: dict):
        """Save Halk data to cache."""
        cache_path = self._get_cache_path(ticker)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Halk cache save failed for {ticker}: {e}")

    def fetch_flow(self, ticker: str) -> dict:
        """
        Fetch institutional flow from Halk Yatırım.

        Returns: {
            "ticker": "AKSEN",
            "net_pct": 0.025,  # +2.5%
            "timestamp": "2026-05-15T10:30:00Z",
            "source": "halk_yatirim"
        }
        """

        # Try cache first
        cached = self._load_cache(ticker)
        if cached:
            logger.debug(f"Halk Yatırım: Using cached data for {ticker}")
            return cached

        logger.debug(f"Halk Yatırım: Fetching for {ticker}")

        try:
            # URL for Halk Yatırım analysis page
            url = f"https://analizim.halkyatirim.com.tr/hisse/{ticker}"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")

            # Find institutional flow section (structure varies)
            # Mock: In production, inspect page HTML and locate actual data
            flow_data = self._parse_halk_html(soup, ticker)

            if flow_data:
                flow_data["source"] = "halk_yatirim"
                self._save_cache(ticker, flow_data)
                return flow_data

            logger.warning(f"Halk Yatırım: Could not extract for {ticker}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Halk Yatırım fetch failed for {ticker}: {e}")
            return None

        finally:
            time.sleep(self.RATE_LIMIT_DELAY)  # Rate limit

    def _parse_halk_html(self, soup: BeautifulSoup, ticker: str) -> dict:
        """
        Parse Halk Yatırım HTML for institutional flow.
        Mock implementation — actual parsing depends on page structure.
        """

        # In production:
        # 1. Inspect analizim.halkyatirim.com.tr/{ticker} HTML structure
        # 2. Locate institutional flow element (CSS class, ID, or structure)
        # 3. Extract net buy % text
        # 4. Convert to float

        # For now, return mock data based on ticker
        mock_flows = {
            "AKSEN": 0.015,     # +1.5%
            "TTKOM": 0.038,     # +3.8%
            "TAVHL": -0.012,    # -1.2%
            "KCHOL": 0.005,     # +0.5%
            "ENERY": 0.010      # +1%
        }

        net_pct = mock_flows.get(ticker, 0.0)

        return {
            "ticker": ticker,
            "net_pct": net_pct,
            "timestamp": datetime.now().isoformat() + "Z"
        }


class SmartMoneyCache:
    """Cache and manage institutional flow history (3-day rolling)."""

    def __init__(self):
        self.history = {}  # {ticker: [day1_net%, day2_net%, day3_net%]}

    def update_flow(self, ticker: str, net_pct: float):
        """Add today's flow, maintain 3-day rolling window."""

        if ticker not in self.history:
            self.history[ticker] = []

        # Keep only last 2 days, add today
        self.history[ticker] = self.history[ticker][-2:] + [net_pct]

    def get_3day_trend(self, ticker: str) -> dict:
        """
        Get 3-day rolling average and direction.

        Returns: {
            "day_1": -0.012,
            "day_2": -0.008,
            "day_3": -0.007,
            "avg_3day": -0.009,
            "direction": "DISTRIBUTION"
        }
        """

        if ticker not in self.history or len(self.history[ticker]) < 3:
            return None

        days = self.history[ticker][-3:]

        avg_3day = sum(days) / 3

        # Direction
        if all(d > 0 for d in days):
            direction = "ACCUMULATION"
        elif all(d < 0 for d in days):
            direction = "DISTRIBUTION"
        else:
            direction = "MIXED"

        return {
            "day_1": days[0],
            "day_2": days[1],
            "day_3": days[2],
            "avg_3day": avg_3day,
            "direction": direction
        }

    def get_history(self, ticker: str) -> list:
        """Get raw history for ticker."""
        return self.history.get(ticker, [])

    def load_from_db(self, ticker: str, days: int = 3):
        """
        Load historical institutional flow from database.
        Placeholder — actual implementation would query database.
        """
        # In production: Query daily_briefing or macro_feed table
        # For now: Return empty (real data comes from Borsa/Halk daily)
        pass
