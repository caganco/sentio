"""Unit tests for StrategistAgent."""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Load strategist.py directly from file — avoids src.signals.__init__ which
# transitively imports yfinance (broken protobuf on Python 3.12 in this env).
# ---------------------------------------------------------------------------

_STRATEGIST_FILE = Path(__file__).parent.parent / "src" / "signals" / "strategist.py"


def _load_module(mock_anthropic_mod=None) -> types.ModuleType:
    """
    Load src/signals/strategist.py in a fresh namespace each time.
    Optionally inject a mock 'anthropic' module before import.
    """
    module_name = "_test_strategist_fresh"
    # Patch anthropic in sys.modules so strategist.py's lazy import picks it up
    extra_mocks: dict = {}
    if mock_anthropic_mod is not None:
        extra_mocks["anthropic"] = mock_anthropic_mod

    with patch.dict("sys.modules", extra_mocks):
        spec = importlib.util.spec_from_file_location(module_name, _STRATEGIST_FILE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


def _make_mock_anthropic():
    mock_mod = MagicMock()
    mock_client = MagicMock()
    mock_mod.Anthropic.return_value = mock_client
    mock_mod.APITimeoutError = type("APITimeoutError", (Exception,), {})
    mock_mod.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_mod.APIError = type("APIError", (Exception,), {})
    return mock_mod, mock_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def system_prompt_path(tmp_path):
    p = tmp_path / "strategist_system_prompt.txt"
    p.write_text(
        "You are a senior equity strategist specializing in Turkish markets (BIST100).",
        encoding="utf-8",
    )
    return str(p)


_VALID_REPORT = {
    "timestamp": "2026-05-14",
    "macro_data": {
        "tcmb_decision": "hold",
        "cds_bps": 280,
        "bist_foreign": "+0.3%",
    },
    "signals": {
        "rsi_5d": 58.0,
        "ma_cross": "bullish",
        "breadth_score": 0.45,
        "volume_trend": "neutral",
    },
    "scores": {
        "overall_score": 62,
        "sector_ratings": "BANKA: positive",
    },
}


def _mock_response(text: str):
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(input_tokens=300, output_tokens=200)
    return resp


def _make_agent(system_prompt_path, mock_mod, mock_client):
    """Build a StrategistAgent with injected mock anthropic client."""
    mod = _load_module(mock_mod)
    agent = mod.StrategistAgent(api_key="sk-test", system_prompt_path=system_prompt_path)
    agent._anthropic = mock_mod
    agent.client = mock_client
    return agent, mod


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

def test_init_with_valid_api_key(system_prompt_path):
    mock_mod, _ = _make_mock_anthropic()
    mod = _load_module(mock_mod)
    agent = mod.StrategistAgent(api_key="sk-test", system_prompt_path=system_prompt_path)
    assert agent.model == "claude-sonnet-4-6"
    assert "strategist" in agent.system_prompt.lower()


def test_init_missing_api_key(system_prompt_path):
    mock_mod, _ = _make_mock_anthropic()
    mod = _load_module(mock_mod)
    env_clean = {k: v for k, v in os.environ.items()
                 if k not in ("CLAUDE_API_KEY", "ANTHROPIC_API_KEY")}
    with patch.dict(os.environ, env_clean, clear=True):
        with pytest.raises(mod.StrategistError, match="CLAUDE_API_KEY"):
            mod.StrategistAgent(system_prompt_path=system_prompt_path)


def test_init_custom_model(system_prompt_path):
    mock_mod, _ = _make_mock_anthropic()
    mod = _load_module(mock_mod)
    agent = mod.StrategistAgent(
        api_key="sk-test",
        model="claude-haiku-4-5",
        system_prompt_path=system_prompt_path,
    )
    assert agent.model == "claude-haiku-4-5"


def test_init_missing_system_prompt_file():
    mock_mod, _ = _make_mock_anthropic()
    mod = _load_module(mock_mod)
    with pytest.raises(mod.StrategistError, match="System prompt file not found"):
        mod.StrategistAgent(
            api_key="sk-test",
            system_prompt_path="/nonexistent/path/prompt.txt",
        )


# ---------------------------------------------------------------------------
# analyze_report() tests
# ---------------------------------------------------------------------------

def test_analyze_report_valid_input(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    long_text = "Detailed equity market analysis for Turkey. " * 15
    mock_client.messages.create.return_value = _mock_response(long_text)
    agent, _ = _make_agent(system_prompt_path, mock_mod, mock_client)

    result = agent.analyze_report(_VALID_REPORT)
    assert isinstance(result, str)
    assert len(result) >= 100


def test_analyze_report_missing_macro_data(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    bad = {k: v for k, v in _VALID_REPORT.items() if k != "macro_data"}
    with pytest.raises(mod.StrategistError, match="macro_data"):
        agent.analyze_report(bad)


def test_analyze_report_missing_signals(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    bad = {k: v for k, v in _VALID_REPORT.items() if k != "signals"}
    with pytest.raises(mod.StrategistError, match="signals"):
        agent.analyze_report(bad)


def test_analyze_report_api_timeout(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    mock_client.messages.create.side_effect = mock_mod.APITimeoutError("timeout")
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    with pytest.raises(mod.StrategistError, match="timeout"):
        agent.analyze_report(_VALID_REPORT)


def test_analyze_report_rate_limit(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    mock_client.messages.create.side_effect = mock_mod.RateLimitError("rate limit")
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    with pytest.raises(mod.StrategistError, match="rate limit"):
        agent.analyze_report(_VALID_REPORT)


def test_analyze_report_api_500(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    mock_client.messages.create.side_effect = mock_mod.APIError("server error")
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    with pytest.raises(mod.StrategistError, match="API error"):
        agent.analyze_report(_VALID_REPORT)


def test_analyze_report_response_too_short(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    mock_client.messages.create.return_value = _mock_response("short")
    agent, mod = _make_agent(system_prompt_path, mock_mod, mock_client)
    with pytest.raises(mod.StrategistError, match="too short"):
        agent.analyze_report(_VALID_REPORT)


def test_analyze_report_with_portfolio_positions(system_prompt_path):
    mock_mod, mock_client = _make_mock_anthropic()
    long_text = "Portfolio-aware equity analysis for BIST. " * 20
    mock_client.messages.create.return_value = _mock_response(long_text)
    agent, _ = _make_agent(system_prompt_path, mock_mod, mock_client)

    report = {
        **_VALID_REPORT,
        "portfolio_positions": [
            {"ticker": "AKBNK", "sector": "BANKA", "unrealized_pnl_pct": 5.2,
             "rsi": 62.0, "alerts": []},
            {"ticker": "EREGL", "sector": "METAL", "unrealized_pnl_pct": -3.1,
             "rsi": 38.0, "alerts": [{"severity": "HIGH", "message": "Near stop-loss"}]},
        ],
    }
    result = agent.analyze_report(report)
    call_args = mock_client.messages.create.call_args
    user_msg = call_args[1]["messages"][0]["content"]
    assert "AKBNK" in user_msg
    assert "EREGL" in user_msg
    assert len(result) >= 100


# ---------------------------------------------------------------------------
# System prompt file tests
# ---------------------------------------------------------------------------

def test_system_prompt_file_loadable():
    prompt_path = (
        Path(__file__).parent.parent / "agents" / "prompts" / "strategist_system_prompt.txt"
    )
    assert prompt_path.exists(), f"System prompt not found: {prompt_path}"
    content = prompt_path.read_text(encoding="utf-8").strip()
    assert len(content) > 50, "System prompt too short"


# ---------------------------------------------------------------------------
# Sentiment encoding tests
# ---------------------------------------------------------------------------

def test_enc_sentiment_bullish():
    mod = _load_module()
    assert mod._enc_sentiment(65) == "B+"
    assert mod._enc_sentiment(100) == "B+"


def test_enc_sentiment_bearish():
    mod = _load_module()
    assert mod._enc_sentiment(35) == "B-"
    assert mod._enc_sentiment(0) == "B-"


def test_enc_sentiment_neutral():
    mod = _load_module()
    assert mod._enc_sentiment(50) == "N"
    assert mod._enc_sentiment(55) == "N"
    assert mod._enc_sentiment(None) == "N"
    assert mod._enc_sentiment("bad") == "N"


def test_build_user_message_includes_sentiment_summary():
    mod = _load_module()
    report = {
        **_VALID_REPORT,
        "sentiment_summary": {
            "avg_score": 62.0,
            "bullish_tickers": ["AKBNK"],
            "bearish_tickers": [],
            "neutral_tickers": [],
        },
        "sentiment_scores": {},
    }
    msg = mod._build_user_message(report)
    assert "SENTIMENT" in msg
    assert "62.0" in msg
    assert "AKBNK" in msg


def test_build_user_message_sentiment_per_position():
    mod = _load_module()
    report = {
        **_VALID_REPORT,
        "portfolio_positions": [
            {"ticker": "AKBNK", "sector": "Bankacılık", "unrealized_pnl_pct": 3.0,
             "rsi": 60, "alerts": []},
        ],
        "sentiment_scores": {
            "AKBNK": {"score": 70, "article_count": 5, "source": "computed"},
        },
    }
    msg = mod._build_user_message(report)
    assert "sent=B+(5art)" in msg


def test_build_user_message_no_sentiment_no_section():
    mod = _load_module()
    report = {**_VALID_REPORT}
    msg = mod._build_user_message(report)
    assert "SENTIMENT" not in msg


def test_system_prompt_borsa_focus():
    prompt_path = (
        Path(__file__).parent.parent / "agents" / "prompts" / "strategist_system_prompt.txt"
    )
    content = prompt_path.read_text(encoding="utf-8").lower()
    assert any(kw in content for kw in ("bist", "turkish", "turkey", "türk")), (
        "System prompt must reference BIST or Turkish market"
    )
