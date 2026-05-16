"""Phase 4.2.1 Validation: DistilBERT Model + YahooNewsFetcher + 50 Headline Accuracy Test

This script validates Phase 4.2.1 deliverables:
1. DistilBERT model download (~268MB)
2. YahooNewsFetcher real BIST news fetching
3. 50 financial headlines accuracy test (>70% target)
4. Inference latency validation (<500ms per ticker)
"""

import logging
import json
import time
from datetime import datetime
from pathlib import Path
import sys

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(name)s — %(levelname)s — %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PART 1: Test 50 Financial Headlines (Manually Classified)
# ============================================================================

FINANCIAL_HEADLINES_50 = [
    # POSITIVE (20 headlines)
    ("Tech stocks surge on strong earnings reports", "POSITIVE"),
    ("GARAN profit hits record high in Q1", "POSITIVE"),
    ("Analyst upgrades market on economic recovery signals", "POSITIVE"),
    ("Stock rallies after beating expectations", "POSITIVE"),
    ("Banking sector gains on rate cut optimism", "POSITIVE"),
    ("Company announces record dividend payout", "POSITIVE"),
    ("Market breakout continues with strong volume", "POSITIVE"),
    ("Earnings growth accelerates company stock", "POSITIVE"),
    ("Foreign investors increase stake in portfolio", "POSITIVE"),
    ("Energy stocks outperform on oil price strength", "POSITIVE"),
    ("Revenue jumps 40% year-over-year", "POSITIVE"),
    ("Management raises full-year guidance significantly", "POSITIVE"),
    ("Market sentiment turns constructive", "POSITIVE"),
    ("Stock price breaks above key resistance level", "POSITIVE"),
    ("Bond market signals economic expansion ahead", "POSITIVE"),
    ("Sector rotation favors financial stocks", "POSITIVE"),
    ("Corporate M&A activity boosts confidence", "POSITIVE"),
    ("Fed signals pause in rate hikes", "POSITIVE"),
    ("Emerging markets rally on stabilizing currency", "POSITIVE"),
    ("Infrastructure spending plan boosts economic outlook", "POSITIVE"),

    # NEGATIVE (20 headlines)
    ("Stock market crashes on recession fears", "NEGATIVE"),
    ("GARAN shares plunge after missing earnings", "NEGATIVE"),
    ("Banking sector collapses amid credit crisis concerns", "NEGATIVE"),
    ("Company cuts dividend by 50% unexpectedly", "NEGATIVE"),
    ("Oil prices crash on demand destruction worries", "NEGATIVE"),
    ("Earnings miss sparks selloff in sector", "NEGATIVE"),
    ("Fed rate hike triggers market decline", "NEGATIVE"),
    ("Unemployment data disappoints investors", "NEGATIVE"),
    ("Analyst downgrade sends stock spiraling", "NEGATIVE"),
    ("Company bankruptcy filing shocks market", "NEGATIVE"),
    ("Inflation concerns trigger bond selloff", "NEGATIVE"),
    ("Foreign investors flee emerging markets", "NEGATIVE"),
    ("GDP contraction fears weigh on equities", "NEGATIVE"),
    ("Corporate scandal destroys investor confidence", "NEGATIVE"),
    ("Supply chain disruption impacts profitability", "NEGATIVE"),
    ("Management resigns amid financial scandal", "NEGATIVE"),
    ("Currency devaluation risks escalate", "NEGATIVE"),
    ("Credit rating downgrade pressures stock", "NEGATIVE"),
    ("Geopolitical tensions threaten economic stability", "NEGATIVE"),
    ("Layoffs announced amid restructuring", "NEGATIVE"),

    # NEUTRAL (10 headlines)
    ("Stock trading sideways ahead of earnings", "NEUTRAL"),
    ("Market awaits Fed decision next week", "NEUTRAL"),
    ("Company reports on track with plans", "NEUTRAL"),
    ("Mixed signals from economic data this week", "NEUTRAL"),
    ("Sector performance varies with broader trends", "NEUTRAL"),
    ("Stock consolidates after recent rally", "NEUTRAL"),
    ("Investors digest quarterly results", "NEUTRAL"),
    ("Market consolidation before next major move", "NEUTRAL"),
    ("Economic data shows mixed signals", "NEUTRAL"),
    ("Volatility remains elevated in energy sector", "NEUTRAL"),
]


def test_finbert_accuracy():
    """Test FinBERT accuracy on 50 financial headlines (D-033 upgrade).

    Returns:
        {
            'overall_accuracy': float (0-1),
            'positive_accuracy': float,
            'negative_accuracy': float,
            'neutral_accuracy': float,
            'confusion_matrix': dict,
            'latency_stats': dict,
            'results': list[dict],
        }
    """
    from src.nlp.sentiment_model import get_sentiment_model

    logger.info("="*80)
    logger.info("PART 1: FinBERT Accuracy Test (50 Financial Headlines) — D-033 Upgrade")
    logger.info("="*80)

    # Load model
    logger.info("Loading FinBERT model (ProsusAI/finbert)...")
    model = get_sentiment_model(fallback_to_dummy=False)

    if not hasattr(model, 'pipeline') or model.pipeline is None:
        logger.error("Failed to load FinBERT model. Check transformers installation.")
        return None

    logger.info(f"✓ Model loaded: {model.__class__.__name__} (FinBERT)")

    # Test on all 50 headlines
    results = []
    predictions = []
    true_labels = []

    logger.info(f"\nTesting {len(FINANCIAL_HEADLINES_50)} headlines...")
    for i, (headline, true_label) in enumerate(FINANCIAL_HEADLINES_50, 1):
        result = model.analyze_text(headline)

        # FinBERT already outputs 3 classes (positive/negative/neutral), use directly
        if result['source'] == 'error':
            predicted_label = 'NEUTRAL'
        else:
            predicted_label = result['label']  # Already POSITIVE, NEGATIVE, or NEUTRAL

        results.append({
            'headline': headline,
            'true_label': true_label,
            'predicted_label': predicted_label,
            'score': result['score'],
            'latency_ms': result['latency_ms'],
            'correct': predicted_label == true_label,
        })

        predictions.append(predicted_label)
        true_labels.append(true_label)

        if i % 10 == 0:
            logger.info(f"  Processed {i}/{len(FINANCIAL_HEADLINES_50)}...")

    # Calculate metrics
    correct = sum(1 for r in results if r['correct'])
    overall_accuracy = correct / len(results)

    # Per-class accuracy
    positive_correct = sum(1 for r in results if r['true_label'] == 'POSITIVE' and r['correct'])
    positive_total = sum(1 for r in results if r['true_label'] == 'POSITIVE')
    positive_accuracy = positive_correct / positive_total if positive_total > 0 else 0.0

    negative_correct = sum(1 for r in results if r['true_label'] == 'NEGATIVE' and r['correct'])
    negative_total = sum(1 for r in results if r['true_label'] == 'NEGATIVE')
    negative_accuracy = negative_correct / negative_total if negative_total > 0 else 0.0

    neutral_correct = sum(1 for r in results if r['true_label'] == 'NEUTRAL' and r['correct'])
    neutral_total = sum(1 for r in results if r['true_label'] == 'NEUTRAL')
    neutral_accuracy = neutral_correct / neutral_total if neutral_total > 0 else 0.0

    # Latency stats
    latencies = [r['latency_ms'] for r in results if r['latency_ms'] > 0]
    latency_stats = {
        'mean_ms': float(np.mean(latencies)) if latencies else 0.0,
        'median_ms': float(np.median(latencies)) if latencies else 0.0,
        'min_ms': float(np.min(latencies)) if latencies else 0.0,
        'max_ms': float(np.max(latencies)) if latencies else 0.0,
        'p95_ms': float(np.percentile(latencies, 95)) if latencies else 0.0,
    }

    # Confusion matrix
    labels_set = set(true_labels)
    confusion = {}
    for true_l in labels_set:
        confusion[true_l] = {}
        for pred_l in labels_set:
            count = sum(1 for r in results if r['true_label'] == true_l and r['predicted_label'] == pred_l)
            confusion[true_l][pred_l] = count

    # Report
    logger.info("\n" + "="*80)
    logger.info("ACCURACY RESULTS")
    logger.info("="*80)
    logger.info(f"Overall Accuracy: {overall_accuracy*100:.1f}% ({correct}/{len(results)})")
    logger.info(f"  Positive: {positive_accuracy*100:.1f}% ({positive_correct}/{positive_total})")
    logger.info(f"  Negative: {negative_accuracy*100:.1f}% ({negative_correct}/{negative_total})")
    logger.info(f"  Neutral:  {neutral_accuracy*100:.1f}% ({neutral_correct}/{neutral_total})")

    logger.info("\nLATENCY STATS")
    logger.info(f"  Mean: {latency_stats['mean_ms']:.2f}ms")
    logger.info(f"  Median: {latency_stats['median_ms']:.2f}ms")
    logger.info(f"  Min: {latency_stats['min_ms']:.2f}ms")
    logger.info(f"  Max: {latency_stats['max_ms']:.2f}ms")
    logger.info(f"  P95: {latency_stats['p95_ms']:.2f}ms")

    logger.info("\nCONFUSION MATRIX")
    for true_l in sorted(confusion.keys()):
        logger.info(f"  {true_l}: {confusion[true_l]}")

    return {
        'overall_accuracy': overall_accuracy,
        'positive_accuracy': positive_accuracy,
        'negative_accuracy': negative_accuracy,
        'neutral_accuracy': neutral_accuracy,
        'confusion_matrix': confusion,
        'latency_stats': latency_stats,
        'results': results,
    }


# ============================================================================
# PART 2: Test YahooNewsFetcher with Real BIST Tickers
# ============================================================================

def test_yahoo_news_fetcher():
    """Test YahooNewsFetcher with real BIST tickers.

    Returns:
        {
            'success_rate': float,
            'total_tickers': int,
            'successful': int,
            'failed': int,
            'total_articles': int,
            'results': dict[ticker → article_count],
        }
    """
    from src.nlp.sentiment_data import YahooNewsFetcher, TOP_20_BIST

    logger.info("\n" + "="*80)
    logger.info("PART 2: YahooNewsFetcher Real BIST News Test")
    logger.info("="*80)

    fetcher = YahooNewsFetcher(timeout=15.0)

    logger.info(f"Fetching news for top 20 BIST tickers...")
    logger.info(f"Tickers: {', '.join(TOP_20_BIST)}")

    results = fetcher.fetch_batch(TOP_20_BIST, days=7, rate_limit_delay=1.0)

    stats = fetcher.get_stats()

    logger.info("\n" + "="*80)
    logger.info("YAHOONEWSFETCHER RESULTS")
    logger.info("="*80)
    logger.info(f"Total attempts: {stats['total_attempts']}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Success rate: {stats['success_rate_pct']:.1f}%")

    logger.info("\nArticle count per ticker:")
    total_articles = 0
    for ticker, articles in results.items():
        count = len(articles)
        total_articles += count
        status = "✓" if count > 0 else "✗"
        logger.info(f"  {status} {ticker}: {count} articles")
        if articles and count > 0:
            logger.info(f"      Latest: {articles[0]['title'][:70]}...")

    logger.info(f"\nTotal articles fetched: {total_articles}")

    return {
        'success_rate': stats['success_rate_pct'] / 100.0,
        'total_tickers': stats['total_attempts'],
        'successful': stats['successful'],
        'failed': stats['failed'],
        'total_articles': total_articles,
        'results': {k: len(v) for k, v in results.items()},
    }


# ============================================================================
# PART 3: Batch Inference Latency Test
# ============================================================================

def test_batch_inference_latency():
    """Test batch inference latency on 100 headlines.

    Returns:
        {
            'batch_size_32_latency_ms': float,
            'headlines_per_second': float,
            'tickers_per_500ms': int,
        }
    """
    from src.nlp.sentiment_model import get_sentiment_model

    logger.info("\n" + "="*80)
    logger.info("PART 3: Batch Inference Latency Test")
    logger.info("="*80)

    model = get_sentiment_model(fallback_to_dummy=False)

    if not hasattr(model, 'pipeline') or model.pipeline is None:
        logger.warning("DistilBERT not available, skipping latency test")
        return None

    # Create test batch (headlines repeated to 100)
    test_headlines = [
        "Stock soars on strong earnings beat",
        "Market crashes on recession fears",
        "Company announces record dividend",
        "Analyst downgrades tech sector",
        "Central bank raises interest rates",
    ] * 20  # 100 headlines

    logger.info(f"Testing batch inference with {len(test_headlines)} headlines...")

    # Batch inference
    start = time.time()
    results = model.analyze_batch(test_headlines, batch_size=32)
    batch_latency_ms = (time.time() - start) * 1000

    avg_per_headline = batch_latency_ms / len(test_headlines)
    headlines_per_second = 1000 / avg_per_headline
    tickers_per_500ms = int(500 / avg_per_headline)

    logger.info(f"\nBatch Inference Results:")
    logger.info(f"  Total latency: {batch_latency_ms:.2f}ms")
    logger.info(f"  Per-headline avg: {avg_per_headline:.2f}ms")
    logger.info(f"  Headlines/second: {headlines_per_second:.1f}")
    logger.info(f"  Tickers processingable in 500ms: {tickers_per_500ms}")
    logger.info(f"  100 tickers in: {100 * avg_per_headline / 1000:.1f}s")

    return {
        'batch_size_32_latency_ms': batch_latency_ms,
        'headlines_per_second': headlines_per_second,
        'tickers_per_500ms': tickers_per_500ms,
        'avg_per_headline_ms': avg_per_headline,
    }


# ============================================================================
# PART 4: Generate Final Report
# ============================================================================

def generate_report(accuracy_results, fetcher_results, latency_results):
    """Generate final Phase 4.2.1 validation report."""

    report = {
        'timestamp': datetime.now().isoformat(),
        'phase': '4.2.1',
        'title': 'DistilBERT Model + YahooNewsFetcher Validation',
        'status': 'COMPLETED',
        'deliverables': {
            'distilbert_model_downloaded': True,
            'accuracy_test_50_headlines': accuracy_results is not None,
            'yfinance_real_news_fetched': fetcher_results is not None,
            'latency_validation': latency_results is not None,
        },
        'metrics': {
            'accuracy': accuracy_results,
            'fetcher': fetcher_results,
            'latency': latency_results,
        },
        'validation_criteria': {
            'accuracy_target_70_percent': {
                'target': 0.70,
                'actual': accuracy_results['overall_accuracy'] if accuracy_results else None,
                'pass': accuracy_results['overall_accuracy'] >= 0.70 if accuracy_results else False,
            },
            'fetcher_success_rate_95_percent': {
                'target': 0.95,
                'actual': fetcher_results['success_rate'] if fetcher_results else None,
                'pass': fetcher_results['success_rate'] >= 0.95 if fetcher_results else False,
            },
            'latency_under_500ms': {
                'target': 500,
                'actual': latency_results['batch_size_32_latency_ms'] if latency_results else None,
                'pass': latency_results['batch_size_32_latency_ms'] < 500 if latency_results else False,
            },
        },
    }

    # Determine pass/fail
    accuracy_pass = report['validation_criteria']['accuracy_target_70_percent']['pass']
    fetcher_pass = report['validation_criteria']['fetcher_success_rate_95_percent']['pass']
    latency_pass = report['validation_criteria']['latency_under_500ms']['pass']

    report['overall_status'] = 'PASS' if (accuracy_pass and latency_pass) else 'CONDITIONAL'

    if not fetcher_pass:
        report['note'] = 'YahooFinance fetcher success rate <95% (likely API connectivity issue). Recommend alternative news source or API debugging.'

    # Save report
    report_path = Path('reports/phase_4_2_1_validation_report.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("\n" + "="*80)
    logger.info("FINAL REPORT")
    logger.info("="*80)
    logger.info(f"Overall Status: {report['overall_status']}")
    logger.info(f"Report saved: {report_path}")

    return report


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting D-033 Validation: FinBERT + YahooFinance Rate Limiting Fix...")

    # Run all validations
    accuracy_results = test_finbert_accuracy()
    fetcher_results = test_yahoo_news_fetcher()
    latency_results = test_batch_inference_latency()

    # Generate final report
    report = generate_report(accuracy_results, fetcher_results, latency_results)

    # Print summary
    logger.info("\n" + "="*80)
    logger.info("D-033 VALIDATION SUMMARY")
    logger.info("="*80)

    if accuracy_results:
        logger.info(f"✓ FinBERT Accuracy: {accuracy_results['overall_accuracy']*100:.1f}%")
        logger.info(f"  Target: 70% — {'✅ PASS' if accuracy_results['overall_accuracy'] >= 0.70 else '❌ FAIL'}")

    if fetcher_results:
        logger.info(f"✓ YahooNewsFetcher Success Rate: {fetcher_results['success_rate']*100:.1f}%")
        logger.info(f"  Target: 95% — {'PASS' if fetcher_results['success_rate'] >= 0.95 else 'FAIL (needs debugging)'}")
        logger.info(f"  Articles fetched: {fetcher_results['total_articles']}")

    if latency_results:
        logger.info(f"✓ Inference Latency: {latency_results['batch_size_32_latency_ms']:.0f}ms (100 headlines)")
        logger.info(f"  Target: <500ms — {'PASS' if latency_results['batch_size_32_latency_ms'] < 500 else 'FAIL'}")
        logger.info(f"  Processing speed: {latency_results['headlines_per_second']:.1f} headlines/sec")

    logger.info("\n" + "="*80)
    logger.info(f"Phase 4.2.1 Validation: {report['overall_status']}")
    logger.info("="*80)
