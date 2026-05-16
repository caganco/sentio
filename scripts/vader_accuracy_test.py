"""VADER sentiment analyzer accuracy validation on 50 financial headlines."""
from src.signals.sentiment.vader_analyzer import VaderSentimentAnalyzer

# 50 financial headlines with expected sentiment
TEST_HEADLINES = [
    # POSITIVE (bullish) — 20 examples
    ("BIST100 hits all-time high amid strong economic recovery", 1),
    ("Tech stocks surge as earnings beat expectations", 1),
    ("Gold prices surge to 10-year high on inflation concerns", 1),
    ("Turkish lira strengthens against US dollar", 1),
    ("Energy sector rallies on OPEC production cuts", 1),
    ("Bank stocks gain on rising interest rates", 1),
    ("AI stocks soar after major breakthrough", 1),
    ("Housing starts exceed forecasts significantly", 1),
    ("Corporate earnings crush analyst estimates", 1),
    ("Turkey's exports reach record high in Q1", 1),
    ("Stock market breaks through resistance level", 1),
    ("Retail sales jump 8% year-over-year", 1),
    ("Manufacturing output grows faster than expected", 1),
    ("Credit spreads tighten amid risk appetite", 1),
    ("Fed signals pause in rate hikes", 1),
    ("Merger and acquisition activity surges", 1),
    ("Small-cap stocks outperform in strong market", 1),
    ("Dividend increases drive investor confidence", 1),
    ("Corporate guidance raised across sectors", 1),
    ("IPO market heats up with strong demand", 1),

    # NEGATIVE (bearish) — 20 examples
    ("Stock market crashes as recession fears mount", -1),
    ("Tech stocks plunge on disappointing earnings", -1),
    ("Economic slowdown signals global downturn risk", -1),
    ("Banking crisis threatens financial stability", -1),
    ("Inflation surges to 40-year high", -1),
    ("Unemployment rises unexpectedly", -1),
    ("Oil prices collapse amid demand destruction", -1),
    ("Corporate bankruptcies accelerate", -1),
    ("Currency crisis deepens in emerging markets", -1),
    ("Credit downgrades hit financial sector", -1),
    ("Supply chain disruptions worsen", -1),
    ("Housing starts plummet 15% month-over-month", -1),
    ("Trade wars escalate amid tariff threats", -1),
    ("Debt defaults surge in junk bond market", -1),
    ("Fed hikes rates aggressively to combat inflation", -1),
    ("Corporate margins compress on cost pressures", -1),
    ("Market volatility spikes to 3-year high", -1),
    ("Earnings guidance lowered across industries", -1),
    ("Political instability threatens markets", -1),
    ("Real estate bubble bursts in major cities", -1),

    # NEUTRAL (mixed/unclear) — 10 examples
    ("Market mixed ahead of Fed decision", 0),
    ("Stocks flat as investors await earnings season", 0),
    ("Economic data shows mixed signals", 0),
    ("Oil prices unchanged on demand concerns", 0),
    ("Corporate earnings show varied results", 0),
    ("Market consolidates gains from last week", 0),
    ("Fed officials divided on rate outlook", 0),
    ("Analyst opinions split on sector prospects", 0),
    ("Trade negotiations continue with no agreement", 0),
    ("Market awaits clarity on policy direction", 0),
]

def classify_vader_score(compound_score: float) -> int:
    """Convert VADER compound score to sentiment class.

    compound > 0.05: positive (1)
    compound < -0.05: negative (-1)
    else: neutral (0)
    """
    if compound_score > 0.05:
        return 1
    elif compound_score < -0.05:
        return -1
    else:
        return 0


def main():
    analyzer = VaderSentimentAnalyzer()

    correct = 0
    incorrect = 0
    results = []

    for headline, expected_class in TEST_HEADLINES:
        compound = analyzer.analyze_article(headline)
        predicted_class = classify_vader_score(compound)
        is_correct = predicted_class == expected_class

        if is_correct:
            correct += 1
        else:
            incorrect += 1

        results.append({
            "headline": headline,
            "expected": expected_class,
            "compound_score": round(compound, 4),
            "predicted": predicted_class,
            "correct": is_correct,
        })

    accuracy = correct / len(TEST_HEADLINES) * 100

    # Print results
    print("\n" + "="*80)
    print("VADER SENTIMENT ANALYZER — ACCURACY TEST (50 Financial Headlines)")
    print("="*80)

    print(f"\nAccuracy: {correct}/{len(TEST_HEADLINES)} ({accuracy:.1f}%)")
    print(f"  [+] Correct:   {correct}")
    print(f"  [-] Incorrect: {incorrect}")

    # Breakdown by expected sentiment
    positive = [r for r, _ in TEST_HEADLINES if _ == 1]
    negative = [r for r, _ in TEST_HEADLINES if _ == -1]
    neutral = [r for r, _ in TEST_HEADLINES if _ == 0]

    pos_correct = sum(1 for r in results if r["expected"] == 1 and r["correct"])
    neg_correct = sum(1 for r in results if r["expected"] == -1 and r["correct"])
    neu_correct = sum(1 for r in results if r["expected"] == 0 and r["correct"])

    print(f"\nBy sentiment class:")
    print(f"  Positive (bullish):  {pos_correct}/{len(positive)} ({pos_correct/len(positive)*100:.1f}%)")
    print(f"  Negative (bearish):  {neg_correct}/{len(negative)} ({neg_correct/len(negative)*100:.1f}%)")
    print(f"  Neutral (mixed):     {neu_correct}/{len(neutral)} ({neu_correct/len(neutral)*100:.1f}%)")

    # Show misclassifications
    misclassified = [r for r in results if not r["correct"]]
    if misclassified:
        print(f"\nMisclassified headlines ({len(misclassified)}):")
        for r in misclassified[:5]:  # Show first 5
            expected_label = {1: "Positive", -1: "Negative", 0: "Neutral"}[r["expected"]]
            predicted_label = {1: "Positive", -1: "Negative", 0: "Neutral"}[r["predicted"]]
            print(f"  '{r['headline'][:60]}...'")
            print(f"    Expected: {expected_label} | Got: {predicted_label} (score: {r['compound_score']})")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Accuracy: {accuracy:.1f}% (target: >70%)")
    if accuracy >= 70:
        print("[PASS] VADER accuracy is acceptable for production")
    else:
        print("[FAIL] VADER accuracy below target; consider DistilBERT for improvement")

    print(f"\nRecommendation:")
    if accuracy >= 75:
        print("  VADER is production-ready for financial sentiment analysis")
    elif accuracy >= 65:
        print("  VADER is acceptable with caution; monitor performance in live trading")
    else:
        print("  VADER accuracy insufficient; evaluate DistilBERT or fine-tuned BERT")

    return accuracy


if __name__ == "__main__":
    accuracy = main()
    exit(0 if accuracy >= 70 else 1)
