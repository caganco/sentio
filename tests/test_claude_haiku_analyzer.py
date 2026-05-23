"""Tests for ClaudeHaikuAnalyzer (Tier-2 hybrid NLP) — D-124.

All tests use mocked anthropic client — no real API calls in CI.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.nlp.finbert_analyzer import ClaudeHaikuAnalyzer


@pytest.fixture
def analyzer():
    return ClaudeHaikuAnalyzer()


def _mock_response(label: str, score: float, reason: str = "test") -> MagicMock:
    """Build a mock anthropic response that returns valid JSON."""
    payload = json.dumps({"label": label, "score": score, "reason": reason})
    content_block = MagicMock()
    content_block.text = payload
    resp = MagicMock()
    resp.content = [content_block]
    return resp


# ---------------------------------------------------------------------------
# Correct parse — valid JSON from Haiku
# ---------------------------------------------------------------------------

class TestValidResponse:
    def test_positive_label_parsed(self, analyzer):
        mock_resp = _mock_response("POSITIVE", 0.82)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("GARAN kar artışı")
        assert result["label"] == "POSITIVE"
        assert abs(result["score"] - 0.82) < 1e-6

    def test_negative_label_parsed(self, analyzer):
        mock_resp = _mock_response("NEGATIVE", 0.78)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("ASELS soruşturma")
        assert result["label"] == "NEGATIVE"
        assert abs(result["score"] - 0.78) < 1e-6

    def test_neutral_label_parsed(self, analyzer):
        mock_resp = _mock_response("NEUTRAL", 0.50)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("Toplantı tarihi açıklandı")
        assert result["label"] == "NEUTRAL"

    def test_reason_field_present(self, analyzer):
        mock_resp = _mock_response("POSITIVE", 0.75, "kar artisi")
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("test")
        assert "reason" in result


# ---------------------------------------------------------------------------
# Fallback on errors
# ---------------------------------------------------------------------------

class TestFallback:
    def test_invalid_json_returns_neutral(self, analyzer):
        content_block = MagicMock()
        content_block.text = "bu json değil"
        resp = MagicMock()
        resp.content = [content_block]
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("test")
        assert result["label"] == "NEUTRAL"
        assert result["score"] == 0.5

    def test_import_error_returns_neutral(self, analyzer):
        import sys
        with patch.dict(sys.modules, {"anthropic": None}):
            result = analyzer.analyze("test")
        assert result["label"] == "NEUTRAL"
        assert result["score"] == 0.5

    def test_api_exception_returns_neutral(self, analyzer):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = Exception("API error")
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze("test")
        assert result["label"] == "NEUTRAL"
        assert result["score"] == 0.5


# ---------------------------------------------------------------------------
# JSON parse rate ≥95% across diverse inputs
# ---------------------------------------------------------------------------

DIVERSE_TEXTS = [
    "GARAN 3. çeyrekte rekor kar",
    "AKBNK zarar açıkladı",
    "THYAO ihracat arttı",
    "EREGL konkordato",
    "ASELS SPK soruşturması",
    "BIMAS temettü duyurusu",
    "TUPRS üretim kapasitesi",
    "KCHOL yatırım planı",
    "PGSUS yolcu artışı",
    "SISE iflas riski",
    "FROTO yeni model",
    "TCELL güçlü büyüme",
    "EKGYO proje lansmanı",
    "ISCTR hisse geri alımı",
    "KOZAA maden üretimi",
    "ASELS sipariş aldı",
    "VESTL zarar açıkladı",
    "MGROS ciro arttı",
    "TTKOM yatırım",
    "HALKB hedef fiyat",
]


def test_json_parse_rate_at_least_95_percent():
    """Mocked valid JSON responses should parse successfully ≥95% of the time."""
    analyzer = ClaudeHaikuAnalyzer()
    success = 0
    for i, text in enumerate(DIVERSE_TEXTS):
        label = ["POSITIVE", "NEGATIVE", "NEUTRAL"][i % 3]
        score = 0.5 + (i % 5) * 0.1
        mock_resp = _mock_response(label, score)
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            with patch("anthropic.Anthropic", MockClient):
                result = analyzer.analyze(text)
        if result.get("label") in ("POSITIVE", "NEGATIVE", "NEUTRAL") and "error" not in result.get("reason", ""):
            success += 1

    parse_rate = success / len(DIVERSE_TEXTS)
    assert parse_rate >= 0.95, f"JSON parse rate {parse_rate:.0%} < 95%"


# ---------------------------------------------------------------------------
# Model / config
# ---------------------------------------------------------------------------

def test_model_string_correct(analyzer):
    assert analyzer._model == "claude-haiku-4-5-20251001"


def test_text_truncated_to_512():
    """Analyzer sends at most 512 chars to API."""
    analyzer = ClaudeHaikuAnalyzer()
    sent_texts = []

    def capture_call(**kwargs):
        sent_texts.append(kwargs["messages"][0]["content"])
        raise Exception("stop")

    with patch("anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = capture_call
        with patch("anthropic.Anthropic", MockClient):
            analyzer.analyze("x" * 1000)

    assert len(sent_texts) == 1
    assert len(sent_texts[0]) <= 512
