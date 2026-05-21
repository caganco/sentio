"""News aggregation and sentiment calculation for tickers."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# BIST tickers map to Yahoo Finance suffix
_BIST_SUFFIX = ".IS"

# How many days old a news article can be before we treat it as missing
_MAX_ARTICLE_AGE_DAYS = 30


class NewsAggregator:
    """Fetch and aggregate news articles with sentiment."""

    def __init__(self, cache_file: str = "data/sentiment_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.cache_ttl = 12 * 3600  # 12 hours in seconds

    def _load_cache(self) -> dict:
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return {}

    def _save_cache(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _is_cache_valid(self, ticker: str) -> bool:
        if ticker not in self.cache:
            return False
        cached = self.cache[ticker]
        if "timestamp" not in cached:
            return False
        age = datetime.now().timestamp() - cached["timestamp"]
        return age < self.cache_ttl

    def fetch_news(self, ticker: str, days: int = 7) -> list[dict]:
        """
        Fetch news articles for ticker via YahooFinance.

        Falls back to cached articles if the live fetch fails.
        Returns empty list when no data is available — caller is
        responsible for handling the "no news" case.
        """
        if self._is_cache_valid(ticker):
            articles = self.cache[ticker].get("articles", [])
            logger.debug(f"{ticker}: using {len(articles)} cached articles")
            return articles

        articles = self._fetch_yahoo_news(ticker, days)

        # Persist whatever we got (even empty list) so we don't hammer
        # Yahoo on every call during a cache-miss storm.
        self.cache[ticker] = {
            "articles": articles,
            "timestamp": datetime.now().timestamp(),
        }
        self._save_cache()

        if not articles:
            logger.warning(f"{ticker}: no news articles from YahooFinance")
        else:
            logger.info(f"{ticker}: fetched {len(articles)} articles from YahooFinance")

        return articles

    def _fetch_yahoo_news(self, ticker: str, days: int) -> list[dict]:
        """Fetch news from YahooFinance for a BIST ticker."""
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed; run: pip install yfinance")
            return []

        yahoo_symbol = ticker + _BIST_SUFFIX
        cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()

        try:
            yf_ticker = yf.Ticker(yahoo_symbol)
            raw_news = yf_ticker.news or []
        except Exception as e:
            logger.warning(f"{ticker}: YahooFinance fetch failed: {e}")
            return []

        articles: list[dict] = []
        for item in raw_news:
            try:
                pub_ts = item.get("providerPublishTime") or item.get("publishTime") or 0
                # yfinance >=0.2 wraps content inside item["content"]
                if not pub_ts and isinstance(item.get("content"), dict):
                    pub_date_str = item["content"].get("pubDate", "")
                    if pub_date_str:
                        try:
                            pub_ts = datetime.fromisoformat(
                                pub_date_str.replace("Z", "+00:00")
                            ).timestamp()
                        except ValueError:
                            pub_ts = 0

                if pub_ts and pub_ts < cutoff_ts:
                    continue

                # Extract title + summary from either schema variant
                content = item.get("content", {})
                if isinstance(content, dict):
                    title = content.get("title") or item.get("title", "")
                    summary = content.get("summary") or content.get("description") or ""
                else:
                    title = item.get("title", "")
                    summary = item.get("summary") or item.get("description") or ""

                text = f"{title}. {summary}".strip(". ") if summary else title
                if not text:
                    continue

                pub_dt = datetime.fromtimestamp(pub_ts) if pub_ts else datetime.now()
                articles.append({
                    "title": title,
                    "text": text,
                    "date": pub_dt.isoformat(),
                    "source": item.get("publisher") or (
                        content.get("provider", {}).get("displayName", "yahoo")
                        if isinstance(content, dict) else "yahoo"
                    ),
                })
            except Exception as e:
                logger.debug(f"{ticker}: skipping malformed news item: {e}")
                continue

        return articles

    def aggregate_sentiment(self, articles: list[dict], analyzer) -> dict:
        """
        Calculate aggregate sentiment from articles with recency weighting.

        Returns:
            score: weighted average sentiment [-1, 1]
            normalized: [0, 1] (0=bearish, 0.5=neutral, 1=bullish)
            count: number of articles
            bullish/bearish: article counts by category
            articles: per-article score breakdown
        """
        if not articles:
            return {
                "score": 0.0,
                "normalized": 0.5,
                "count": 0,
                "bullish": 0,
                "bearish": 0,
                "articles": [],
            }

        now = datetime.now().timestamp()
        article_scores = []

        for article in articles:
            sentiment = analyzer.analyze_article(article.get("text", ""))

            try:
                date = datetime.fromisoformat(article.get("date", ""))
                age_days = (now - date.timestamp()) / 86400
                weight = 0.9 ** age_days
            except (ValueError, TypeError):
                weight = 0.9

            article_scores.append({
                "score": sentiment,
                "weighted": sentiment * weight,
                "weight": weight,
                "title": article.get("title", ""),
            })

        total_weight = sum(a["weight"] for a in article_scores)
        weighted_avg = (
            sum(a["weighted"] for a in article_scores) / total_weight
            if total_weight > 0
            else 0.0
        )

        bullish_count = sum(1 for a in article_scores if a["score"] > 0.5)
        bearish_count = sum(1 for a in article_scores if a["score"] < -0.5)
        normalized = (weighted_avg + 1) / 2

        return {
            "score": weighted_avg,
            "normalized": normalized,
            "count": len(articles),
            "bullish": bullish_count,
            "bearish": bearish_count,
            "articles": article_scores,
        }


# =============================================================================
# D-094 — Mynet News Aggregator (borsa-mcp + FinBERT pipeline)
# Mevcut NewsAggregator korunur — Yahoo Finance fallback olarak kalır.
# =============================================================================

def _empty_result(reason: str) -> dict:
    return {
        "score": 50.0,
        "normalized": 0.0,
        "confidence": 0.0,
        "bullish_count": 0,
        "bearish_count": 0,
        "article_count": 0,
        "source": f"missing:{reason}",
        "model": "none",
        "detail_articles": [],
    }


def _compute_confidence(scored: list, n: int) -> float:
    """Three-component L4 confidence formula.

    Returns 0.0 when n < L4_MIN_ARTICLES_ACTIVATE (hard gate).

    Component 1 — Volume    (weight 0.35): min(n / L4_MIN_ARTICLES_FULL_CONF, 1.0)
    Component 2 — Agreement (weight 0.40): max(bullish_ratio, bearish_ratio)
    Component 3 — Quality   (weight 0.25): mean(relevance × finbert_confidence)
    """
    from src.signals.thresholds import (
        L4_CONF_AGREEMENT_WEIGHT,
        L4_CONF_QUALITY_WEIGHT,
        L4_CONF_VOLUME_WEIGHT,
        L4_MIN_ARTICLES_ACTIVATE,
        L4_MIN_ARTICLES_FULL_CONF,
    )

    if n < L4_MIN_ARTICLES_ACTIVATE:
        return 0.0

    volume_conf = min(n / L4_MIN_ARTICLES_FULL_CONF, 1.0)

    bullish_n = sum(1 for s in scored if s.label == "bullish")
    bearish_n = sum(1 for s in scored if s.label == "bearish")
    agreement_conf = max(bullish_n / n, bearish_n / n)

    quality_conf = sum(s.relevance_weight * s.finbert_confidence for s in scored) / n

    conf = (
        L4_CONF_VOLUME_WEIGHT * volume_conf
        + L4_CONF_AGREEMENT_WEIGHT * agreement_conf
        + L4_CONF_QUALITY_WEIGHT * quality_conf
    )
    return round(min(conf, 1.0), 4)


class MynetNewsAggregator:
    """Aggregate Mynet Finans articles for a ticker using borsa-mcp + FinBERT.

    Usage:
        agg = MynetNewsAggregator()
        result = agg.aggregate(symbol="AKBNK", days=7)
    """

    def __init__(self) -> None:
        from src.data.news_fetcher import MynetNewsFetcher, TickerMatcher
        from src.nlp.finbert_analyzer import FinBERTAnalyzer

        self._fetcher = MynetNewsFetcher()
        self._matcher = TickerMatcher()
        self._analyzer = FinBERTAnalyzer()

    def aggregate(self, symbol: str, days: int) -> dict:
        """Fetch → match → score. Returns dict compatible with SentimentSignal."""
        articles = self._fetcher.fetch(symbol, days)
        if not articles:
            return _empty_result("no_articles")

        matched = [self._matcher.match(art, symbol) for art in articles]
        relevant = [m for m in matched if m.match_type != "no_match"] or matched

        scored = self._analyzer.score_articles(relevant)
        if not scored:
            return _empty_result("scoring_failed")

        weighted_sent = self._analyzer.compute_weighted_sentiment(scored)
        score_0_100 = round((weighted_sent + 1.0) / 2.0 * 100.0, 2)

        n = len(scored)
        confidence = _compute_confidence(scored, n)

        bullish_n = sum(1 for s in scored if s.label == "bullish")
        bearish_n = sum(1 for s in scored if s.label == "bearish")

        return {
            "score":          score_0_100,
            "normalized":     round(weighted_sent, 4),
            "confidence":     confidence,
            "bullish_count":  bullish_n,
            "bearish_count":  bearish_n,
            "article_count":  n,
            "source":         "mynet_finans",
            "model":          scored[0].source if scored else "unknown",
            "detail_articles": [
                {
                    "title":     s.title[:80],
                    "label":     s.label,
                    "sentiment": s.sentiment_raw,
                    "weight":    s.effective_weight,
                }
                for s in scored[:5]
            ],
        }
