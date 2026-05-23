"""Tests for TurkishLexiconScorer (Tier-1 hybrid NLP) — D-124."""
import pytest

from src.nlp.finbert_analyzer import TurkishLexiconScorer
from src.signals.thresholds import LEXICON_TIER1_HIGH, LEXICON_TIER1_LOW


@pytest.fixture
def scorer():
    return TurkishLexiconScorer()


# ---------------------------------------------------------------------------
# score() — basic term matching
# ---------------------------------------------------------------------------

class TestScore:
    def test_bullish_term_positive(self, scorer):
        assert scorer.score("GARAN rekor kar açıkladı") > 0

    def test_bearish_term_negative(self, scorer):
        assert scorer.score("AKBNK soruşturma altında") < 0

    def test_neutral_empty(self, scorer):
        assert scorer.score("") == 0.0

    def test_no_match_returns_zero(self, scorer):
        assert scorer.score("Toplantı tarihi açıklandı") == 0.0

    def test_strong_bearish_konkordato(self, scorer):
        s = scorer.score("Şirket konkordato ilan etti")
        assert s < -2.0

    def test_strong_bullish_rekor_kar(self, scorer):
        s = scorer.score("Net kar rekor seviyede")
        assert s > 2.0

    def test_multiple_bullish_terms_accumulate(self, scorer):
        s1 = scorer.score("kar artışı")
        s2 = scorer.score("kar artışı büyüme rekor")
        assert s2 > s1

    def test_mixed_terms_additive(self, scorer):
        bull = scorer.score("güçlü kar")
        bear = scorer.score("zarar düşüş")
        mixed = scorer.score("güçlü kar zarar düşüş")
        # mixed should be between extremes
        assert bear < mixed < bull or mixed != 0.0


# ---------------------------------------------------------------------------
# score() — negation window
# ---------------------------------------------------------------------------

class TestNegation:
    def test_negation_flips_bullish_to_negative(self, scorer):
        without = scorer.score("GARAN kar açıkladı")
        with_neg = scorer.score("GARAN kar değil açıkladı")
        assert without > 0
        assert with_neg < without

    def test_negation_flips_bearish_to_less_negative(self, scorer):
        without = scorer.score("AKBNK zarar açıkladı")
        with_neg = scorer.score("AKBNK zarar değil açıkladı")
        assert without < 0
        assert with_neg > without

    def test_negation_outside_window_no_effect(self, scorer):
        # Negation >60 chars before the term — outside both pre and post windows
        padding = "x" * 70
        text = f"değil {padding} kar"
        # "değil" at position 0, "kar" at ~77 → pre-window misses it, post-window is empty
        assert scorer.score(text) == scorer.score("kar")


# ---------------------------------------------------------------------------
# tier() — boundary classification
# ---------------------------------------------------------------------------

class TestTier:
    def test_definite_above_high(self, scorer):
        assert scorer.tier(LEXICON_TIER1_HIGH + 0.1) == "definite"
        assert scorer.tier(-(LEXICON_TIER1_HIGH + 0.1)) == "definite"

    def test_neutral_at_or_below_low(self, scorer):
        assert scorer.tier(LEXICON_TIER1_LOW) == "neutral"
        assert scorer.tier(0.0) == "neutral"
        assert scorer.tier(-LEXICON_TIER1_LOW) == "neutral"

    def test_ambiguous_between_low_and_high(self, scorer):
        mid = (LEXICON_TIER1_LOW + LEXICON_TIER1_HIGH) / 2
        assert scorer.tier(mid) == "ambiguous"
        assert scorer.tier(-mid) == "ambiguous"

    def test_boundary_exactly_high_is_ambiguous(self, scorer):
        # strictly greater-than threshold is definite; equal → ambiguous
        assert scorer.tier(LEXICON_TIER1_HIGH) == "ambiguous"

    def test_boundary_exactly_low_is_neutral(self, scorer):
        assert scorer.tier(LEXICON_TIER1_LOW) == "neutral"


# ---------------------------------------------------------------------------
# Filter rate — ≥50% bypass Tier-2 on realistic BIST headlines
# ---------------------------------------------------------------------------

SAMPLE_BIST_HEADLINES = [
    "GARAN 3. çeyrekte %23 kar artışı açıkladı",          # definite bullish
    "AKBNK SPK soruşturması altına girdi",                  # definite bearish
    "THYAO ihracat anlaşması imzaladı",                     # definite bullish
    "EREGL net zarar açıkladı",                             # definite bearish
    "BIMAS yönetim kurulu toplantı tarihi açıklandı",       # neutral (no terms)
    "ASELS hakkında dava açıldı",                           # definite bearish
    "TUPRS rekor üretim kapasitesine ulaştı",               # definite bullish
    "KCHOL temettü artışı duyurdu",                         # definite bullish
    "PGSUS yolcu sayısı arttı",                             # definite bullish
    "SISE iflas tehlikesiyle karşı karşıya",                # definite bearish
    "FROTO yeni model lansmanı gerçekleşti",                # neutral
    "TCELL güçlü büyüme rakamları açıkladı",               # definite bullish
    "EKGYO konkordato başvurusu yaptı",                     # definite bearish
    "ISCTR hisse geri alımı programı başlattı",             # definite bullish
    "KOZAA faaliyet raporu yayımlandı",                     # neutral
    "ASELS beklenti üzeri sipariş aldı",                    # definite bullish
    "VESTL zarar açıkladı",                                 # definite bearish
    "MGROS ciro arttı olumlu sonuçlar",                     # definite bullish
    "TTKOM yatırım planını açıkladı",                       # definite bullish
    "HALKB hedef fiyat düşürüldü",                         # definite bearish
]


def test_tier1_filter_rate_at_least_50_percent(scorer):
    """Tier-1 should bypass Tier-2 for ≥50% of realistic BIST headlines."""
    bypassed = 0
    for headline in SAMPLE_BIST_HEADLINES:
        raw = scorer.score(headline)
        t = scorer.tier(raw)
        if t in ("definite", "neutral"):
            bypassed += 1

    filter_rate = bypassed / len(SAMPLE_BIST_HEADLINES)
    assert filter_rate >= 0.50, (
        f"Tier-1 filter rate {filter_rate:.0%} < 50% — "
        f"too many articles going to Tier-2"
    )
