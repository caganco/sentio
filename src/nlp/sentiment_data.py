"""YahooNewsFetcher: Fetch real financial news for BIST tickers from YahooFinance."""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# BIST tickers for news fetching
BIST_TICKERS_100 = [
    "AKSEN", "ALARK", "ALGYO", "ALKIM", "ANELE", "ARCLK", "ASELS",
    "AYGAZ", "BAGFS", "BARKA", "BERAS", "BEYAZ", "BFREN", "BIMAS",
    "BMWAD", "BOSSA", "BREO", "BRISA", "BSOKE", "BTCIM", "BUCIM",
    "CHERY", "CIMSA", "CLEBI", "CRPP", "DCCIONI", "DIOR", "DITAS",
    "DOHOL", "DSKB", "DSMM", "DYGYO", "ECILC", "ECYHO", "ENERY",
    "ENKAI", "EPLAS", "ESCOM", "ESKRT", "ETIBK", "EXEMS", "FENER",
    "FERRO", "FETTO", "FLAP", "FOOND", "FROTO", "FSKEN", "FUNDU",
    "GARAN", "GARGYO", "GATEU", "GLYHO", "GOBNK", "GOLDS", "GOLTS",
    "GONUL", "GRIFF", "GRIST", "GSDDE", "GSDHO", "GSRAY", "GULFA",
    "GULKM", "GULUA", "GUSGM", "GUVBD", "GUVTR", "HAFIF", "HATEK",
    "HEKTS", "HLGYO", "HOEPO", "HONKA", "HURGZ", "HZTUR", "HYAKM",
    "IAKIN", "ICBCT", "ICBFT", "ICBGM", "ICBUS", "ICBVT", "IDEXX",
    "IHLAS", "IHLGM", "IHYAY", "ISDMR", "ISKUR", "ISKVY", "ISSAY",
    "ISTAŞ", "ISYNH", "ITALC", "ITABK", "ITCM"
]

# Top 20 BIST tickers (use these for initial testing)
TOP_20_BIST = [
    "AKSEN", "TTKOM", "TAVHL", "KCHOL", "ENERY", "GARAN",
    "SASA", "ASELS", "SISE", "DOHOL", "PGSUS", "THYAO",
    "TOASO", "EREGL", "ARCLK", "TCELL", "AEFES", "KOZAL",
    "GUBRF", "PETKM"
]


class YahooNewsFetcher:
    """Fetch real news articles from YahooFinance for BIST tickers."""

    def __init__(
        self,
        base_url: str = "https://query1.finance.yahoo.com",
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """Initialize YahooNewsFetcher with retry logic.

        Args:
            base_url: YahooFinance API base URL
            timeout: Request timeout in seconds
            max_retries: Max retry attempts for failed requests
            backoff_factor: Exponential backoff multiplier
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session(max_retries, backoff_factor)
        self.fetch_success = 0
        self.fetch_failure = 0

    @staticmethod
    def _create_session(max_retries: int, backoff_factor: float):
        """Create requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=backoff_factor,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 10,
    ) -> list[dict]:
        """Fetch news articles for a ticker from YahooFinance.

        Args:
            ticker: BIST ticker (e.g., "AKSEN")
            days: Look back window (default 7 days)
            max_articles: Maximum articles to return

        Returns:
            List of article dicts with keys: ['title', 'source', 'link', 'date']
            Empty list if fetch fails
        """
        symbol = f"{ticker}.IS" if not ticker.endswith(".IS") else ticker

        try:
            # YahooFinance news endpoint
            endpoint = f"{self.base_url}/v10/finance/quoteSummary/{symbol}"
            params = {
                "modules": "news",
                "region": "TR",
            }

            logger.debug(f"Fetching news for {ticker}...")
            response = self.session.get(
                endpoint, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            articles = []

            # Extract news from response
            if "quoteSummary" in data and "result" in data["quoteSummary"]:
                result = data["quoteSummary"]["result"]
                if result and len(result) > 0:
                    news_section = result[0].get("news", [])
                    if isinstance(news_section, list):
                        for item in news_section[:max_articles]:
                            try:
                                article = {
                                    "title": item.get("title", ""),
                                    "source": item.get("source", "YahooFinance"),
                                    "link": item.get("link", ""),
                                    "date": datetime.fromtimestamp(
                                        item.get("providerPublishTime", 0)
                                    ).isoformat(),
                                }
                                if article["title"]:  # Only add if title exists
                                    articles.append(article)
                            except Exception as e:
                                logger.debug(f"Error parsing article: {e}")
                                continue

            if articles:
                self.fetch_success += 1
                logger.info(
                    f"{ticker}: fetched {len(articles)} articles from YahooFinance"
                )
            else:
                self.fetch_failure += 1
                logger.warning(f"{ticker}: no articles found in YahooFinance")

            return articles

        except requests.RequestException as e:
            self.fetch_failure += 1
            logger.warning(f"{ticker}: fetch failed — {e}")
            return []
        except Exception as e:
            self.fetch_failure += 1
            logger.error(f"{ticker}: unexpected error — {e}")
            return []

    def fetch_batch(
        self,
        tickers: list[str],
        days: int = 7,
        rate_limit_delay: float = 0.5,
    ) -> dict[str, list[dict]]:
        """Fetch news for multiple tickers with rate limiting.

        Args:
            tickers: List of BIST tickers
            days: Look back window
            rate_limit_delay: Delay between requests (seconds)

        Returns:
            Dict mapping ticker → list of articles
        """
        results = {}
        for i, ticker in enumerate(tickers):
            articles = self.fetch_news(ticker, days=days)
            results[ticker] = articles

            # Rate limiting (respect API limits)
            if i < len(tickers) - 1:
                time.sleep(rate_limit_delay)

        return results

    def get_success_rate(self) -> float:
        """Return fetch success rate (0.0-1.0).

        Returns:
            success_rate = successful_tickers / total_attempts
        """
        total = self.fetch_success + self.fetch_failure
        if total == 0:
            return 0.0
        return self.fetch_success / total

    def get_stats(self) -> dict:
        """Return fetch statistics."""
        total = self.fetch_success + self.fetch_failure
        success_rate = self.get_success_rate()
        return {
            "total_attempts": total,
            "successful": self.fetch_success,
            "failed": self.fetch_failure,
            "success_rate_pct": round(success_rate * 100, 2),
        }


def validate_ticker_format(ticker: str) -> bool:
    """Validate BIST ticker format."""
    # BIST tickers are 1-5 uppercase letters, optionally with .IS suffix
    ticker = ticker.rstrip(".IS")
    return len(ticker) >= 1 and len(ticker) <= 5 and ticker.isalpha() and ticker.isupper()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with top 20 tickers
    fetcher = YahooNewsFetcher(timeout=15.0)

    print("\n" + "="*80)
    print("YahooNewsFetcher — Real BIST News Test")
    print("="*80)

    results = fetcher.fetch_batch(TOP_20_BIST, days=7, rate_limit_delay=1.0)

    print("\nResults:")
    for ticker, articles in results.items():
        article_count = len(articles)
        print(f"  {ticker}: {article_count} articles")
        if articles:
            print(f"    Latest: {articles[0]['title'][:60]}...")

    stats = fetcher.get_stats()
    print(f"\nStatistics:")
    print(f"  Total attempts: {stats['total_attempts']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate_pct']:.1f}%")
    print(f"  {'[PASS]' if stats['success_rate_pct'] >= 95.0 else '[FAIL]'} "
          f"(Target: >95%)")

    print("\n" + "="*80)
