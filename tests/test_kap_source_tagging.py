"""Tests for KAP scraper source-type tagging — SPEC 3."""
from datetime import datetime, timezone

import pytest

from src.data.kap_scraper import (
    KAP_OFFICIAL_DOMAINS,
    NEWS_MEDIA_DOMAINS,
    NewsItem,
    classify_source_type,
    parse_rss_item,
)


class TestClassifySourceType:

    def test_kap_www(self):
        assert classify_source_type("https://www.kap.org.tr/tr/Bildirim/123") == "kap_official"

    def test_kap_bare(self):
        assert classify_source_type("https://kap.org.tr/tr/Bildirim/456") == "kap_official"

    def test_kap_subdomain(self):
        assert classify_source_type("https://api.kap.org.tr/endpoint") == "kap_official"

    def test_kap_http(self):
        assert classify_source_type("http://www.kap.org.tr/tr/Bildirim/789") == "kap_official"

    def test_bloomberg_news_media(self):
        assert classify_source_type("https://bloomberght.com/haber/thyao") == "news_media"

    def test_unknown_blog(self):
        assert classify_source_type("https://some-blog.com/post") == "unknown"

    def test_empty_string(self):
        assert classify_source_type("") == "unknown"

    def test_not_a_url(self):
        assert classify_source_type("not-a-url") == "unknown"


class TestParseRssItem:

    def test_kap_official_item(self):
        raw = {
            "title": "Test",
            "link": "https://www.kap.org.tr/tr/Bildirim/999",
            "published": "Tue, 13 May 2026 10:00:00 +0000",
        }
        item = parse_rss_item(raw, symbol="THYAO")
        assert item.source_type == "kap_official"
        assert item.source_domain == "www.kap.org.tr"

    def test_news_media_item(self):
        raw = {
            "title": "THYAO kar açıkladı",
            "link": "https://bloomberght.com/thyao-kar-acikladi",
            "published": "Tue, 13 May 2026 10:00:00 +0000",
        }
        item = parse_rss_item(raw)
        assert item.source_type == "news_media"

    def test_unknown_domain_item(self):
        raw = {
            "title": "Some news",
            "link": "https://some-random-blog.com/thyao",
            "published": "Tue, 13 May 2026 10:00:00 +0000",
        }
        item = parse_rss_item(raw)
        assert item.source_type == "unknown"

    def test_missing_link_key(self):
        raw = {"title": "Test", "published": "Tue, 13 May 2026 10:00:00 +0000"}
        item = parse_rss_item(raw)
        assert item.source_type == "unknown"
        assert item.source_domain == ""


class TestNewsItemDataclass:

    def test_source_type_field_exists(self):
        assert "source_type" in NewsItem.__dataclass_fields__

    def test_source_domain_field_exists(self):
        assert "source_domain" in NewsItem.__dataclass_fields__

    def test_create_news_item(self):
        item = NewsItem(
            title="Test",
            url="https://www.kap.org.tr/tr/Bildirim/1",
            published=datetime.now(timezone.utc),
            symbol="THYAO",
            source_type="kap_official",
            source_domain="www.kap.org.tr",
        )
        assert item.source_type == "kap_official"
        assert item.source_domain == "www.kap.org.tr"
        assert item.summary is None
