"""Strategist Agent — Claude API wrapper for daily equity market narrative."""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT_PATH = str(
    Path(__file__).parent / "strategist_system_prompt.txt"
)
_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_TIMEOUT = 10
_MIN_RESPONSE_CHARS = 100
# D-134: report truncated mid-content ("## 📋 KA") because the response hit the
# old 2000-token cap. 4096 gives the full multi-section narrative headroom.
_MAX_OUTPUT_TOKENS = 4096

# ---------------------------------------------------------------------------
# Encoding helpers — compact format for token budget
# ---------------------------------------------------------------------------

_TCMB_CODES: dict[str, str] = {"hold": "H", "hike": "U", "cut": "D"}

_SECTOR_CODES: dict[str, str] = {
    "Bankacılık":          "B",
    "Enerji":              "E",
    "Telekomünikasyon":    "T",
    "Holding":             "H",
    "Havacılık":           "Av",
    "Havacılık Hizmetleri": "AH",
    "Gayrimenkul":         "RE",
    "Perakende":           "Pe",
    "Demir Çelik":         "DS",
    "Petrokimya":          "PC",
    "Otomotiv":            "Ot",
    "İnşaat":              "In",
    "İnşaat Malzemesi":    "IM",
    "Kimya":               "Ki",
    "Savunma":             "Sa",
    "İlaç":                "Il",
    "Dayanıklı Tüketim":   "DT",
    "Cam":                 "Ca",
    "Yazılım":             "Ya",
    "Elektronik":          "El",
    "Gıda":                "Gd",
}


def _enc_tcmb(val: str) -> str:
    return _TCMB_CODES.get(str(val).lower(), str(val))


def _enc_ma(val: str) -> str:
    """Encode MA cross signal. BL=bullish, BR=bearish, 0=neutral/unknown."""
    v = str(val).lower()
    if "bull" in v or v == "buy":
        return "BL"
    if "bear" in v or v == "sell":
        return "BR"
    return "0"


def _enc_sector(sector: str) -> str:
    return _SECTOR_CODES.get(sector, sector[:2] if sector else "?")


def _enc_brent_corr(ctx: str | None) -> str | None:
    """Extract Brent correlation code from sector_context string."""
    if not ctx:
        return None
    lower = ctx.lower()
    if "pozitif" in lower:
        return "bc=+"
    if "negatif" in lower:
        return "bc=-"
    if "karma" in lower:
        return "bc=~"
    return None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class StrategistError(Exception):
    """Raised when Strategist agent fails."""


class StrategistAgent:
    """Generates strategic equity market narrative via Claude API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        system_prompt_path: str = _DEFAULT_SYSTEM_PROMPT_PATH,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as fh:
                self.system_prompt = fh.read().strip()
        except FileNotFoundError:
            raise StrategistError(
                f"System prompt file not found: {system_prompt_path}"
            )

        resolved_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise StrategistError("CLAUDE_API_KEY env var not set")

        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
            self.client = _anthropic.Anthropic(api_key=resolved_key)
        except ImportError as exc:
            raise StrategistError(
                "anthropic package not installed; run: pip install anthropic>=0.27.0"
            ) from exc

        self.model = model
        self.timeout = timeout

    def analyze_report(self, report_data: dict) -> str:
        """
        Generate strategic notes from arastirma katmani report dict.

        Returns markdown-formatted string (300-500 words).
        Raises StrategistError on any failure.
        """
        required_keys = ["macro_data", "signals", "scores", "timestamp"]
        missing = [k for k in required_keys if k not in report_data]
        if missing:
            raise StrategistError(f"report_data missing required keys: {missing}")

        user_message = _build_user_message(report_data)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=_MAX_OUTPUT_TOKENS,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
                timeout=float(self.timeout),
            )
            notes = response.content[0].text

            # D-134: a max_tokens stop is NOT an API error, so it was logged as
            # "generated successfully" while the markdown was cut mid-heading.
            # Surface it loudly instead of silently writing a truncated report.
            if getattr(response, "stop_reason", None) == "max_tokens":
                logger.warning(
                    "Strategist response truncated at max_tokens=%d; "
                    "report narrative may be incomplete.", _MAX_OUTPUT_TOKENS
                )

            if not notes or len(notes) < _MIN_RESPONSE_CHARS:
                raise StrategistError(
                    f"Response too short ({len(notes)} chars); minimum {_MIN_RESPONSE_CHARS}"
                )

            usage = getattr(response, "usage", None)
            if usage:
                logger.info(
                    "Strategist notes generated (input_tokens=%d, output_tokens=%d)",
                    usage.input_tokens,
                    usage.output_tokens,
                )
            return notes

        except self._anthropic.APITimeoutError as exc:
            raise StrategistError(f"API timeout after {self.timeout}s") from exc
        except self._anthropic.RateLimitError as exc:
            raise StrategistError("API rate limit exceeded") from exc
        except self._anthropic.AuthenticationError as exc:
            raise StrategistError(f"API authentication failed: {exc}") from exc
        except self._anthropic.APIError as exc:
            raise StrategistError(f"API error: {exc.__class__.__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Compact user message builder (~400 tokens vs ~1000 before)
# ---------------------------------------------------------------------------

def _enc_sentiment(score) -> str:
    """Encode sentiment score: B+=bullish, B-=bearish, N=neutral."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "N"
    if s > 60:
        return "B+"
    if s < 40:
        return "B-"
    return "N"


def _build_user_message(report_data: dict) -> str:
    macro = report_data.get("macro_data", {})
    signals = report_data.get("signals", {})
    scores = report_data.get("scores", {})
    timestamp = report_data.get("timestamp", "unknown")
    portfolio = report_data.get("portfolio_positions", [])
    momentum_top10 = report_data.get("momentum_top10", [])
    kelly_sizing = report_data.get("kelly_sizing", {})
    sentiment_scores = report_data.get("sentiment_scores", {})
    sentiment_summary = report_data.get("sentiment_summary", {})

    # Macro
    tcmb = _enc_tcmb(macro.get("tcmb_decision", "N/A"))
    cds = macro.get("cds_bps", "N/A")
    brent = macro.get("brent_usd", "N/A")
    fa = macro.get("bist_foreign", "N/A")

    # Signals
    rsi5d = signals.get("rsi_5d", "N/A")
    ma = _enc_ma(signals.get("ma_cross", "N/A"))
    breadth = signals.get("breadth_score", "N/A")

    # Score
    overall = scores.get("overall_score", "N/A")

    lines = [
        f"BIST {timestamp}",
        "ENC tcmb:H=hold,U=hike,D=cut | ma:BL=bullish,BR=bearish | bc:+=pos,-=neg,~=mix | s:B=bank,E=enrj,T=telekom,H=hold,Av=avia,RE=re | sent:B+=bullish,B-=bearish,N=neutral",
        f"MACRO tcmb={tcmb} cds={cds} brent={brent} fa={fa}",
        f"SIG rsi5d={rsi5d} ma={ma} breadth={breadth}",
        f"SCORE {overall}/100",
    ]

    if portfolio:
        lines.append("PORT")
        for pos in portfolio:
            t = pos.get("ticker", "?")
            s = _enc_sector(pos.get("sector", ""))
            p = pos.get("unrealized_pnl_pct") if pos.get("unrealized_pnl_pct") is not None else pos.get("allocation", "?")
            r = pos.get("rsi", "?")
            alerts = pos.get("alerts", [])
            alert_str = ";".join(a.get("message", "") for a in alerts) if alerts else ""
            bc = _enc_brent_corr(pos.get("sector_context"))
            parts = [f"{t} {s} pnl={p} rsi={r}"]
            if bc:
                parts.append(bc)
            if alert_str:
                parts.append(f"[{alert_str}]")

            # Add Kelly sizing if available (conviction level + recommended action)
            if t in kelly_sizing and "error" not in kelly_sizing[t]:
                kelly = kelly_sizing[t]
                conviction = kelly.get("conviction", "?")
                action = kelly.get("action", "?")
                kelly_pct = kelly.get("kelly_fractional_pct", "?")
                parts.append(f"kelly={conviction}({kelly_pct}%,{action})")

            # Add sentiment if available (B+=bullish,B-=bearish,N=neutral)
            if t in sentiment_scores:
                sent_score = sentiment_scores[t].get("score")
                sent_articles = sentiment_scores[t].get("article_count", 0)
                sent_code = _enc_sentiment(sent_score)
                if sent_articles > 0:
                    parts.append(f"sent={sent_code}({sent_articles}art)")
                else:
                    parts.append("sent=N(0art)")

            lines.append(" ".join(parts))

    if sentiment_summary:
        avg_s = sentiment_summary.get("avg_score", 50)
        bull_t = ",".join(sentiment_summary.get("bullish_tickers", [])) or "none"
        bear_t = ",".join(sentiment_summary.get("bearish_tickers", [])) or "none"
        lines.append(f"SENTIMENT avg={avg_s} bull={bull_t} bear={bear_t}")

    if momentum_top10:
        lines.append("MOMENTUM")
        for i, mom in enumerate(momentum_top10, 1):
            t = mom.get("ticker", "?")
            sc = mom.get("score", "?")
            r = mom.get("rsi", "?")
            m = mom.get("1m_pct", "?")
            v = mom.get("vol_surge", "?")
            lines.append(f"{i}.{t} sc={sc} r={r} 1m={m}% v={v}x")

    # Derive risk flags
    flags: list[str] = []
    try:
        if float(breadth) < 0.1:
            flags.append("breadth_extreme")
    except (TypeError, ValueError):
        pass
    try:
        if float(cds) > 400:
            flags.append("cds_elevated")
    except (TypeError, ValueError):
        pass
    if any((pos.get("unrealized_pnl_pct") or 0) < -5 for pos in portfolio):
        flags.append("drawdown_alert")

    lines += [
        f"FLAGS {','.join(flags) or 'NONE'}",
        "",
        "Generate strategic market notes for a professional equity portfolio manager.",
    ]
    return "\n".join(lines)
