"""Pytest configuration and fixtures."""

import pytest


def pytest_collection_modifyitems(items):
    """Auto-mark tests by category: baseline, new, regression."""
    for item in items:
        # Baseline: Previously passing tests (known stable)
        if any(kw in item.nodeid for kw in [
            "test_kap", "test_kelly", "test_sentiment", "test_engine",
            "test_macro", "test_technical", "test_local_macro", "test_cds",
            "test_strategist", "test_bist_fetch", "test_tcmb_fetch"
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
