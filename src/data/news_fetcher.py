"""Mynet Finans direct news scraper (D-094 HOTFIX — no borsa-mcp dependency).

MynetDirectFetcher — scrapes finans.mynet.com/borsa/hisseler/ directly.
MynetNewsFetcher   — caches fetched articles, returns NewsArticle list.
TickerMatcher      — maps article text to a BIST ticker with relevance weight.

Fallback policy: scrape fails → [] → SentimentSignal confidence=0.0
→ L4 weight=0 → system continues (SUSPENDED-equivalent).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup

from src.signals.thresholds import (
    L4_NEWS_CACHE_TTL_HOURS,
    L4_NEWS_LOOKBACK_DAYS,
    TICKER_COMPANY_ALIASES,
    TICKER_MATCH_WEIGHTS,
)

logger = logging.getLogger(__name__)

_CACHE_FILE = Path("data/news_cache.json")
_MYNET_BASE = "https://finans.mynet.com/borsa/hisseler/"
_HTTP_TIMEOUT = 12
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}
# URL map refresh interval (seconds)
_URL_MAP_TTL = 86400  # 24h


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class NewsArticle:
    """Single Mynet Finans article."""
    title: str
    body: str
    published_at: datetime
    url: str
    source: str = "mynet_finans"
    tags: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        body = self.body or ""
        return f"{self.title}. {body}".strip(". ")

    @property
    def age_days(self) -> float:
        now = datetime.now(timezone.utc)
        pub = self.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return max(0.0, (now - pub).total_seconds() / 86400)


@dataclass
class MatchedArticle:
    """Article with ticker relevance score."""
    article: NewsArticle
    match_type: Literal["exact_ticker", "company_name", "sector_theme", "no_match"]
    relevance_weight: float


# ---------------------------------------------------------------------------
# Mynet direct fetcher
# ---------------------------------------------------------------------------

class MynetDirectFetcher:
    """Scrapes finans.mynet.com/borsa/hisseler/ for ticker-specific news.

    Two-step process:
    1. Build ticker→URL map from the hisseler listing page (cached 24h).
    2. For each ticker, scrape its page for KAP/editorial news items.

    Returns list of raw dicts with keys: baslik, tarih, url, metin.
    """

    def __init__(self) -> None:
        self._url_map: dict[str, str] = {}
        self._url_map_fetched_at: float = 0.0

    def fetch_raw(self, ticker: str, limit: int = 50) -> list[dict]:
        """Return raw article dicts for ticker. Raises RuntimeError on failure."""
        ticker_url = self._get_ticker_url(ticker)
        if not ticker_url:
            raise RuntimeError(f"Mynet URL not found for ticker {ticker}")
        return self._scrape_news(ticker_url, limit)

    def _get_ticker_url(self, ticker: str) -> str | None:
        """Return Mynet page URL for ticker, refreshing map if stale."""
        if time.time() - self._url_map_fetched_at > _URL_MAP_TTL or not self._url_map:
            self._refresh_url_map()
        return self._url_map.get(ticker.upper())

    def _refresh_url_map(self) -> None:
        try:
            resp = requests.get(_MYNET_BASE, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "lxml")
            tbody = soup.select_one("div.scrollable-box-hisseler tbody.tbody-type-default")
            if not tbody:
                logger.warning("news_fetcher: Mynet hisseler table not found — layout may have changed")
                return
            url_map: dict[str, str] = {}
            for row in tbody.find_all("tr"):
                link = row.select_one("td > strong > a")
                if link and link.get("href") and link.get("title"):
                    parts = link["title"].split()
                    if parts:
                        url_map[parts[0].upper()] = link["href"]
            self._url_map = url_map
            self._url_map_fetched_at = time.time()
            logger.info("news_fetcher: Mynet URL map refreshed (%d tickers)", len(url_map))
        except Exception as exc:
            logger.warning("news_fetcher: URL map refresh failed: %s", exc)

    def _scrape_news(self, ticker_url: str, limit: int) -> list[dict]:
        """Scrape news items from a ticker page."""
        resp = requests.get(ticker_url, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")

        # Primary: div.card.kap section (KAP/editorial news block)
        articles: list[dict] = []
        kap_container = soup.select_one("div.card.kap")
        if kap_container:
            news_list = kap_container.select_one("ul.list-type-link-box")
            if news_list:
                for item in news_list.find_all("li"):
                    link = item.find("a")
                    if not link:
                        continue
                    title_el = link.find("em", class_="title")
                    date_el = link.find("span", class_="date")
                    if title_el:
                        articles.append({
                            "baslik": title_el.get_text(strip=True),
                            "tarih": date_el.get_text(strip=True) if date_el else "",
                            "url": link.get("href", ""),
                            "metin": link.get("title", ""),
                        })
                    if len(articles) >= limit:
                        break

        # Fallback: any haberdetay links on the page
        if not articles:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "haberdetay" in href or ("/haber/detay/" in href):
                    text = link.get("title") or link.get_text(strip=True)
                    if text and len(text) > 10:
                        articles.append({
                            "baslik": text[:200],
                            "tarih": "",
                            "url": href,
                            "metin": text[:200],
                        })
                if len(articles) >= limit:
                    break

        return articles


# ---------------------------------------------------------------------------
# News fetcher (caching wrapper)
# ---------------------------------------------------------------------------

class MynetNewsFetcher:
    """Fetch Mynet Finans articles for a BIST ticker.

    Cache TTL: L4_NEWS_CACHE_TTL_HOURS (6h default).
    On failure: returns stale cache if available, else [].
    """

    def __init__(
        self,
        cache_file: Path = _CACHE_FILE,
        direct_fetcher: MynetDirectFetcher | None = None,
    ) -> None:
        self._cache_file = cache_file
        self._fetcher = direct_fetcher or MynetDirectFetcher()
        self._cache: dict = self._load_cache()

    def fetch(
        self,
        ticker: str,
        days: int = L4_NEWS_LOOKBACK_DAYS,
    ) -> list[NewsArticle]:
        """Return Mynet Finans articles for ticker (cached).

        Returns [] on total failure — caller handles no-news case.
        """
        cache_key = f"{ticker}:{days}"
        if self._is_fresh(cache_key):
            raw = self._cache[cache_key]["articles"]
            logger.debug("news_fetcher: %s cache hit (%d articles)", ticker, len(raw))
            return self._deserialize(raw)

        try:
            raw_articles = self._fetcher.fetch_raw(ticker, limit=50)
        except Exception as exc:
            logger.warning("news_fetcher: Mynet unavailable for %s: %s", ticker, exc)
            if cache_key in self._cache:
                logger.info("news_fetcher: returning stale cache for %s", ticker)
                return self._deserialize(self._cache[cache_key]["articles"])
            return []

        self._cache[cache_key] = {
            "articles": raw_articles,
            "fetched_at": time.time(),
        }
        self._persist()
        logger.info("news_fetcher: %s → %d articles from Mynet Finans", ticker, len(raw_articles))
        return self._deserialize(raw_articles)

    def _is_fresh(self, key: str) -> bool:
        if key not in self._cache:
            return False
        age_s = time.time() - self._cache[key].get("fetched_at", 0)
        return age_s < L4_NEWS_CACHE_TTL_HOURS * 3600

    def _deserialize(self, raw: list[dict]) -> list[NewsArticle]:
        articles = []
        for r in raw:
            try:
                pub_str = r.get("published_at") or r.get("tarih") or r.get("date") or ""
                if pub_str:
                    pub = _parse_date(pub_str)
                else:
                    pub = datetime.now(timezone.utc)

                title = r.get("title") or r.get("baslik") or r.get("title_attr") or ""
                body = r.get("body") or r.get("metin") or r.get("content") or r.get("summary") or ""

                articles.append(NewsArticle(
                    title=title,
                    body=body,
                    published_at=pub,
                    url=r.get("url") or r.get("haber_url") or "",
                    source=r.get("source", "mynet_finans"),
                    tags=r.get("tags", []),
                ))
            except Exception as exc:
                logger.debug("news_fetcher: skipping malformed article: %s", exc)
        return articles

    def _load_cache(self) -> dict:
        if not self._cache_file.exists():
            return {}
        try:
            return json.loads(self._cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _persist(self) -> None:
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("news_fetcher: cache persist failed: %s", exc)


def _parse_date(s: str) -> datetime:
    """Parse Mynet date strings: '15 May 2026', '15.05.2026', ISO, etc."""
    # Try ISO first
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    # Turkish/EU formats
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Ticker matcher
# ---------------------------------------------------------------------------

class TickerMatcher:
    """Map a NewsArticle to a BIST ticker with relevance weight.

    Priority:
    1. exact_ticker (1.00) — raw ticker in text/tags
    2. company_name (0.85) — alias from TICKER_COMPANY_ALIASES found
    3. sector_theme (0.30) — sector keyword, no specific company
    4. no_match     (0.10) — general market noise
    """

    _SECTOR_KEYWORDS: dict[str, str] = {
        "bankacılık": "XBANK",
        "banka":      "XBANK",
        "kredi":      "XBANK",
        "faiz":       "XBANK",
        "holding":    "XHOLD",
        "enerji":     "XENRJ",
        "petrol":     "XENRJ",
        "elektrik":   "XENRJ",
        "perakende":  "XPERA",
        "market":     "XPERA",
        "gıda":       "XGIDA",
        "teknoloji":  "XTEK",
        "telekom":    "XTEK",
        "uçak":       "XTRZM",
        "havacılık":  "XTRZM",
        "otomotiv":   "XTRZM",
    }

    def match(self, article: NewsArticle, ticker: str) -> MatchedArticle:
        text_lower = article.full_text.lower()
        tags_lower = [t.lower() for t in article.tags]

        # 1. Exact ticker
        if ticker.upper() in article.full_text.upper() or ticker.lower() in tags_lower:
            return MatchedArticle(article, "exact_ticker", TICKER_MATCH_WEIGHTS["exact_ticker"])

        # 2. Company alias
        for alias in TICKER_COMPANY_ALIASES.get(ticker, []):
            if alias in text_lower:
                return MatchedArticle(article, "company_name", TICKER_MATCH_WEIGHTS["company_name"])

        # 3. Sector theme
        for keyword in self._SECTOR_KEYWORDS:
            if keyword in text_lower:
                return MatchedArticle(article, "sector_theme", TICKER_MATCH_WEIGHTS["sector_theme"])

        return MatchedArticle(article, "no_match", TICKER_MATCH_WEIGHTS["no_match"])
