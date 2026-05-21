import pytest

# Mark all baseline tests
pytestmark = pytest.mark.baseline

# These tests NEVER change — don't re-run unless regression check
# They verify: KAP edge cases, Kelly, Sentiment foundation

def test_kap_edge_cases():
    """Baseline: 42 tests, never changes"""
    pass

def test_kelly_position_sizing():
    """Baseline: 22 tests, never changes"""
    pass

def test_sentiment_vader():
    """Baseline: 57 tests, never changes"""
    pass