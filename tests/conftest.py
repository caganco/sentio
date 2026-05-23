"""Pytest configuration and fixtures."""

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# FinBERT isolation (session-scoped, autouse)
# ---------------------------------------------------------------------------
# Patches _load_model to a no-op so self.pipeline stays None.
# get_sentiment_model() then falls through to DummyDistilBERTAnalyzer
# (existing fallback_to_dummy=True path). Prevents all HF API calls and
# eliminates 429 rate-limit warnings from the Thread-auto_conversion thread.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _finbert_offline():
    """Block FinBERT from touching the HF network during the test session."""
    def _noop_load(self):
        self.pipeline = None

    with patch("src.nlp.sentiment_model.FinBERTSentimentModel._load_model", _noop_load):
        yield


def pytest_collection_modifyitems(items):
    """Auto-mark tests by category: baseline, new, regression."""
    for item in items:
        # Baseline: Previously passing tests (known stable)
        if any(kw in item.nodeid for kw in [
            "test_kap", "test_kelly", "test_sentiment", "test_engine",
            "test_macro", "test_technical", "test_local_macro", "test_cds",
            "test_strategist", "test_bist_fetch", "test_tcmb_fetch",
            "test_backtest",
        ]):
            item.add_marker(pytest.mark.baseline)

        # New: Recent feature tests (run always)
        if any(kw in item.nodeid for kw in [
            "test_sentiment_integration",  # Phase 5.1 sentiment + 5-layer integration
            "test_audit_has_5_layers",     # 5-layer stack checkpoint
        ]):
            item.add_marker(pytest.mark.new)

        # Regression: Catch regressions (weekly)
        if any(kw in item.nodeid for kw in [
            "test_all_5_layers_in_signal",
            "test_sentiment_layer_included",
            "test_integration_checkpoint_5_layers",
        ]):
            item.add_marker(pytest.mark.regression)
