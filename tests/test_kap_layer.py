"""score_kap() finansal_rapor entegrasyon testleri — D-158.

score_kap() fonksiyonunun finansal_rapor branching'ini test eder.
Diğer kategori testleri tests/test_engine.py::TestKapLayer'da.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.signals.layers.kap_layer import score_kap

_AS_OF = date(2026, 5, 21)


def _fr_event(kap_text: str) -> dict:
    """finansal_rapor eventi fixture."""
    return {
        "category": "finansal_rapor",
        "kap_text": kap_text,
        "published_at": "2026-05-21T09:00:00",
    }


class TestKapLayerFinansalRapor:
    """score_kap() finansal_rapor → numeric surprise branching (D-158)."""

    def test_positive_earnings_raises_score_above_50(self):
        """Güçlü pozitif sürpriz (%50) → L3 score > 50."""
        ls = score_kap(
            "GARAN",
            [_fr_event("Net kâr 450 milyon TL (geçen yıl: 300 milyon TL)")],
            _AS_OF,
        )
        assert ls.score > 50.0
        assert ls.source == "computed"

    def test_negative_earnings_lowers_score_below_50(self):
        """Güçlü negatif sürpriz (-%27) → L3 score < 50."""
        ls = score_kap(
            "GARAN",
            [_fr_event("Net satışlar 800 milyon TL (önceki dönem: 1.100 milyon TL)")],
            _AS_OF,
        )
        assert ls.score < 50.0

    def test_unparseable_text_falls_back_to_neutral(self):
        """Parse edilemeyen metin → impact=0.0 → score=50.0 (base)."""
        ls = score_kap(
            "GARAN",
            [_fr_event("Yönetim kurulu toplantısı yapıldı.")],
            _AS_OF,
        )
        assert ls.score == pytest.approx(50.0)

    def test_no_kap_text_field_falls_back_to_neutral(self):
        """kap_text alanı olmayan event → impact=0.0 → score=50.0 (base)."""
        event = {"category": "finansal_rapor", "published_at": "2026-05-21T09:00:00"}
        ls = score_kap("GARAN", [event], _AS_OF)
        assert ls.score == pytest.approx(50.0)
