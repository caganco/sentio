"""Tests for fetch_kap_news() per-ticker merge logic — D-115."""
from unittest.mock import call, patch

import pytest

import src.data.kap_scraper as _mod
from src.data.kap_scraper import fetch_kap_news


def _kap_item(ticker: str, category: str = "IMPORTANT") -> dict:
    return {
        "source": "kap_api",
        "ticker": ticker,
        "title": f"{ticker} KAP bildirim",
        "published": "2026-05-21T10:00:00+00:00",
        "category": category,
        "url": f"https://www.kap.org.tr/tr/bildirim/1",
    }


def _rss_item(ticker: str, category: str = "NOISE") -> dict:
    return {
        "source": "gnews:Haberturk",
        "ticker": ticker,
        "title": f"{ticker} haber",
        "published": "2026-05-21T09:00:00+00:00",
        "category": category,
        "url": f"https://haberturk.com/{ticker.lower()}",
    }


class TestPerTickerMerge:
    """Core per-ticker fallback behaviour."""

    def test_kap_hit_skips_rss_for_that_ticker(self):
        """When KAP returns data for ticker A, RSS must NOT be called for A."""
        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", return_value=[_kap_item("AKSEN")]),
            patch.object(_mod, "_fetch_gnews") as mock_gnews,
            patch.object(_mod.time, "sleep"),
        ):
            result = fetch_kap_news("AKSEN")

        mock_gnews.assert_not_called()
        assert len(result) == 1
        assert result[0]["source"] == "kap_api"

    def test_kap_empty_triggers_rss_for_that_ticker(self):
        """When KAP returns [] for ticker B, RSS must be called for B."""
        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", return_value=[]),
            patch.object(_mod, "_fetch_gnews", return_value=[_rss_item("THYAO")]) as mock_gnews,
            patch.object(_mod.time, "sleep"),
        ):
            result = fetch_kap_news("THYAO")

        mock_gnews.assert_called_once_with("THYAO", None)
        assert len(result) == 1
        assert result[0]["source"] == "gnews:Haberturk"

    def test_mixed_two_tickers_independent(self):
        """Ticker A gets KAP data → no RSS for A. Ticker B gets nothing → RSS for B only."""
        kap_side = {"AKSEN": [_kap_item("AKSEN")], "THYAO": []}
        rss_side = {"THYAO": [_rss_item("THYAO")]}

        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", side_effect=lambda t: kap_side.get(t, [])),
            patch.object(_mod, "_fetch_gnews", side_effect=lambda t, n: rss_side.get(t, [])) as mock_gnews,
            patch.object(_mod.time, "sleep"),
        ):
            result = fetch_kap_news(["AKSEN", "THYAO"])

        # RSS called for THYAO only, not for AKSEN
        mock_gnews.assert_called_once_with("THYAO", None)
        sources = {item["source"] for item in result}
        assert "kap_api" in sources
        assert "gnews:Haberturk" in sources

    def test_all_kap_empty_rss_called_for_every_ticker(self):
        """When KAP returns [] for all → RSS called per-ticker, not once globally."""
        tickers = ["AKSEN", "THYAO", "TTKOM"]

        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", return_value=[]),
            patch.object(_mod, "_fetch_gnews", return_value=[]) as mock_gnews,
            patch.object(_mod.time, "sleep"),
        ):
            fetch_kap_news(tickers)

        assert mock_gnews.call_count == 3
        called_tickers = [c.args[0] for c in mock_gnews.call_args_list]
        assert set(called_tickers) == set(tickers)


class TestKapBlockedFlag:
    """_KAP_BLOCKED=True → all tickers fall to RSS, max 1 timeout per process start."""

    def test_kap_blocked_causes_all_rss(self):
        """Simulates state after first ticker times out (_KAP_BLOCKED=True)."""
        original = _mod._KAP_BLOCKED
        try:
            _mod._KAP_BLOCKED = True  # simulate post-timeout state
            with (
                patch.object(_mod, "_kap_api_warmup"),
                patch.object(_mod, "_fetch_gnews", return_value=[_rss_item("AKSEN")]) as mock_gnews,
                patch.object(_mod.time, "sleep"),
            ):
                result = fetch_kap_news(["AKSEN", "THYAO"])

            # RSS called for both tickers since KAP is globally blocked
            assert mock_gnews.call_count == 2
        finally:
            _mod._KAP_BLOCKED = original  # restore module state


class TestRateLimiting:
    """sleep() called with correct delay per path."""

    def test_kap_hit_sleeps_03(self):
        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", return_value=[_kap_item("AKSEN")]),
            patch.object(_mod, "_fetch_gnews"),
            patch.object(_mod.time, "sleep") as mock_sleep,
        ):
            fetch_kap_news("AKSEN")

        mock_sleep.assert_called_once_with(0.3)

    def test_rss_fallback_sleeps_05(self):
        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", return_value=[]),
            patch.object(_mod, "_fetch_gnews", return_value=[_rss_item("AKSEN")]),
            patch.object(_mod.time, "sleep") as mock_sleep,
        ):
            fetch_kap_news("AKSEN")

        mock_sleep.assert_called_once_with(0.5)

    def test_mixed_sleeps_correct_per_ticker(self):
        """AKSEN: KAP hit → 0.3s. THYAO: RSS → 0.5s."""
        kap_side = {"AKSEN": [_kap_item("AKSEN")], "THYAO": []}

        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", side_effect=lambda t: kap_side.get(t, [])),
            patch.object(_mod, "_fetch_gnews", return_value=[_rss_item("THYAO")]),
            patch.object(_mod.time, "sleep") as mock_sleep,
        ):
            fetch_kap_news(["AKSEN", "THYAO"])

        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        assert 0.3 in sleep_args
        assert 0.5 in sleep_args


class TestSortOrder:
    """CRITICAL < IMPORTANT < NOISE regardless of source mix."""

    def test_critical_before_important_before_noise(self):
        items_unordered = [
            _rss_item("A", "NOISE"),
            _kap_item("B", "CRITICAL"),
            _rss_item("C", "IMPORTANT"),
        ]
        kap_side = {"A": [], "B": [_kap_item("B", "CRITICAL")], "C": []}
        rss_side = {
            "A": [_rss_item("A", "NOISE")],
            "B": [],
            "C": [_rss_item("C", "IMPORTANT")],
        }

        with (
            patch.object(_mod, "_kap_api_warmup"),
            patch.object(_mod, "_fetch_kap_api", side_effect=lambda t: kap_side.get(t, [])),
            patch.object(_mod, "_fetch_gnews", side_effect=lambda t, n: rss_side.get(t, [])),
            patch.object(_mod.time, "sleep"),
        ):
            result = fetch_kap_news(["A", "B", "C"])

        categories = [item["category"] for item in result]
        assert categories.index("CRITICAL") < categories.index("IMPORTANT")
        assert categories.index("IMPORTANT") < categories.index("NOISE")
