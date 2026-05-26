"""Numeric earnings surprise parser tests — D-158.

parse_earnings_surprise() birim testleri. L3 entegrasyon testleri
tests/test_kap_layer.py dosyasında.
"""
from __future__ import annotations

import pytest

from src.signals.layers.kap_earnings_parser import parse_earnings_surprise


class TestParseEarningsSurprise:
    """KAP finansal rapor metni → numerik sürpriz skoru (D-158 Faz 1)."""

    def test_strong_positive_net_kar(self):
        """450M vs 300M → +%50 > strong_threshold → score = +1.0."""
        r = parse_earnings_surprise("Net kâr 450 milyon TL (geçen yıl: 300 milyon TL)")
        assert r.score > 0.5
        assert r.confidence > 0.0
        assert r.parse_method == "regex"
        assert "net_kar" in r.metrics_found

    def test_negative_surprise_net_satis(self):
        """800M vs 1.100M → -%27 < -strong_threshold → score ≈ -1.0."""
        r = parse_earnings_surprise("Net satışlar 800 milyon TL (önceki dönem: 1.100 milyon TL)")
        assert r.score < -0.2
        assert r.confidence > 0.0

    def test_fallback_on_non_financial_text(self):
        """Finansal rakam içermeyen metin → fallback."""
        r = parse_earnings_surprise("Şirket yönetim kurulu karar aldı.")
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.parse_method == "fallback"
        assert r.metrics_found == []

    def test_neutral_band_returns_zero(self):
        """105M vs 100M → +%5 = neutral_band → score = 0.0."""
        r = parse_earnings_surprise("Net kâr 105 milyon TL (geçen yıl: 100 milyon TL)")
        assert r.score == pytest.approx(0.0)

    def test_score_always_in_bounds(self):
        """Extreme pozitif sürpriz → score ≤ +1.0 (clamp garantisi)."""
        r = parse_earnings_surprise("Net kâr 10000 milyon TL (geçen yıl: 1 milyon TL)")
        assert -1.0 <= r.score <= 1.0

    def test_empty_string_returns_fallback(self):
        """Boş string → fail-safe fallback, exception yok."""
        r = parse_earnings_surprise("")
        assert r.score == 0.0
        assert r.confidence == 0.0
        assert r.parse_method == "fallback"

    def test_thousand_dot_separator_parsed_correctly(self):
        """Türkçe binlik nokta ayracı: '1.100' → 1100 (not 1.1)."""
        # 1200M vs 1100M → +%9.09 → should be in (band, strong) range → score > 0
        r = parse_earnings_surprise("Net satışlar 1.200 milyon TL (önceki dönem: 1.100 milyon TL)")
        assert r.score > 0.0  # +9.09% > neutral band (5%)

    def test_confidence_single_metric(self):
        """1 metrik bulunursa confidence = 0.5."""
        r = parse_earnings_surprise("Net kâr 450 milyon TL (geçen yıl: 300 milyon TL)")
        assert r.confidence == pytest.approx(0.5)
