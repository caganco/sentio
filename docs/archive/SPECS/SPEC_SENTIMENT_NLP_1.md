# SPEC_SENTIMENT_NLP_1: Layer 4 Sentiment Analysis

**Status:** Active Development  
**Phase:** 5.1  
**Date:** 15 May 2026

---

## Overview

Implement Layer 4 (Sentiment & Narrative) of the 7-layer intelligence stack via natural language processing of Turkish financial news. This layer enriches signal scores with market sentiment, reducing false positives and improving narrative quality.

**Goal:** Convert raw news sentiment into actionable signal layer (weight: 35%) with conviction mapping and narrative context.

---

## Requirements

### 1. News Data Source
- **Primary:** Turkish financial news from YahooFinance news feed (free, no auth)
- **Fallback:** BIST listed company news (KAP scraper if available)
- **Scope:** Last 7-14 days, sector-tagged (Energy, Tech, Banking, etc.)

### 2. Sentiment Scoring
- **Method:** VADER sentiment analysis (fast, tuned for financial news)
- **Output:** Sentiment score per ticker [-1, 1] where:
  - -1 ≤ score < -0.5: Negative (bearish)
  - -0.5 ≤ score < 0.5: Neutral (mixed)
  - 0.5 ≤ score ≤ 1: Positive (bullish)

### 3. Signal Layer Integration
- **Class:** SentimentSignal (inherits from BaseSignal)
- **Output:** Sentiment score [0, 1] for signal engine weighting
- **Calculation:**
  - Aggregated sentiment from all news articles for ticker
  - Recency-weighted (recent news > old news)
  - Volume-adjusted (more articles = stronger signal)

### 4. Signal Engine Weighting
- **New weights (Layer 5 with sentiment):**
  - Technical (RSI, MACD): 20%
  - Macro (Brent, FX, CDS): 35%
  - Sentiment (News NLP): 25%
  - KAP/Corporate: 15%
  - Risk (Kelly): 5%

### 5. Strategist Integration
- **Report Data:** Add sentiment section with:
  - Bullish articles (count, headlines)
  - Bearish articles (count, headlines)
  - Overall sentiment score [0, 1]
  - Narrative context: "News sentiment is [bullish/bearish/mixed] on TICKER"

### 6. Test Requirements
- **Unit tests:** 12+
  - Sentiment scoring accuracy (VADER validation)
  - Recency weighting correctness
  - Volume adjustment edge cases
  - Missing ticker handling
- **Integration tests:** 5+
  - Signal engine weight recalculation
  - Strategist narrative generation
  - End-to-end daily_update flow
- **Edge cases:** 3+
  - No news available for ticker
  - Conflicting sentiments in articles
  - News source failure fallback

---

## Implementation Plan

### Phase 1: Sentiment Scoring Core
1. Create `src/signals/sentiment/vader_analyzer.py`
   - VaderSentimentAnalyzer class
   - Method: analyze_article(text) → sentiment_score
   - Caching for processed articles

2. Create `src/signals/sentiment/news_aggregator.py`
   - NewsAggregator class
   - Method: fetch_news(ticker, days=7) → [articles]
   - Method: aggregate_sentiment(articles) → {score, count, articles}

3. Create `src/signals/sentiment/sentiment_signal.py`
   - SentimentSignal class (inherits BaseSignal)
   - Method: calculate(ticker, macro_state) → signal_dict
   - Integration with signal engine

### Phase 2: Signal Engine Integration
1. Update `src/signals/signal_engine.py`
   - Add SentimentSignal to 5-layer stack
   - Recalculate layer weights (see spec above)
   - Update overall_score calculation

2. Update `src/signals/strategist.py`
   - Extract sentiment data in daily briefing
   - Add sentiment narrative section
   - Integrate bullish/bearish articles in portfolio commentary

### Phase 3: Daily Pipeline
1. Update `scripts/daily_update.py`
   - Initialize SentimentSignal
   - Fetch news for each ticker
   - Calculate sentiment scores
   - Add to portfolio_data and report_data

2. Create `data/sentiment_cache.json`
   - Cache articles and sentiment scores
   - TTL: 12 hours (refresh twice daily)

### Phase 4: Testing & Validation
1. Unit tests: src/signals/sentiment/test_vader_analyzer.py
2. Integration tests: tests/test_sentiment_integration.py
3. End-to-end tests: tests/test_daily_update_sentiment.py

---

## Success Criteria

| Criterion | Target | Notes |
|-----------|--------|-------|
| VADER accuracy | >85% vs. manual review | Sample 20 articles |
| Recency weighting | Recent articles ranked higher | Weight decay by 0.9^days |
| Signal layer quality | No false positives on neutral days | Backtest: neutral → score ~0.5 |
| Layer weights | All 5 layers integrated | Sum to 100% |
| Strategist narrative | Mention sentiment in >80% of briefs | Extract from signal data |
| Test coverage | 20+ tests total | 12 unit + 5 integration + 3 edge |
| Zero regression | 401 baseline tests maintained | New tests only add to total |
| Performance | Sentiment calculation < 2s per 60 tickers | Cache hits improve speed |

---

## Files to Create/Modify

### New Files
- `src/signals/sentiment/__init__.py`
- `src/signals/sentiment/vader_analyzer.py` (150 lines)
- `src/signals/sentiment/news_aggregator.py` (200 lines)
- `src/signals/sentiment/sentiment_signal.py` (120 lines)
- `tests/test_vader_analyzer.py` (200 lines)
- `tests/test_sentiment_integration.py` (250 lines)
- `tests/test_daily_update_sentiment.py` (150 lines)
- `data/sentiment_cache.json` (new cache file)

### Modified Files
- `src/signals/signal_engine.py` (layer weights update)
- `src/signals/strategist.py` (sentiment narrative)
- `scripts/daily_update.py` (sentiment pipeline)
- `docs/SPECS/INDEX.md` (add SPEC_SENTIMENT_NLP_1 entry)

---

## Dependencies

### Python Packages
- `nltk` (VADER sentiment analyzer) — already in environment
- `feedparser` (news feed parsing) — lightweight, no auth
- No additional ML models required

### Data Sources
- YahooFinance news API (free, rate-limited)
- BIST KAP news (if scraper available)
- Fallback: Local cache + dummy data for testing

---

## Notes

1. **VADER vs. Turkish models:** VADER works well on English financial news (most BIST news is in Turkish + English mixed). For pure Turkish, could add `zemberek` or Turkish BERT later (Phase 5.2).

2. **Sentiment as 3rd signal layer:** This is experimental. If sentiment proves noisy, can reduce weight from 25% → 15% or use it for confidence adjustment only.

3. **Real-time news:** Current design is daily batch (daily_update.py). Real-time sentiment would require streaming news source (future).

4. **Backtest validation:** After implementation, validate on historical data (e.g., last 30 days) to ensure sentiment doesn't cause over-trading.

---

## Roadmap

**Phase 5.1a (Today):** Implement core sentiment scoring + basic news fetching  
**Phase 5.1b (Day 2):** Integrate with signal engine, update strategist  
**Phase 5.1c (Day 3):** Full testing, backtest validation, zero-regression check  
**Phase 5.2 (Next):** Turkish-specific NLP, real-time sentiment streaming

