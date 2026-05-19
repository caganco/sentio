"""Automated pipeline: Briefing → Analyst → Auditor → Final Decision."""
import hashlib
import json
import os
import sys
import uuid
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import anthropic
from dotenv import load_dotenv

load_dotenv()

_CLIENT: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Lazily build the Anthropic client.

    The API key is checked on first use rather than at import time, so that
    pytest collection / module import does not call sys.exit(1) when the
    secret is absent (e.g. CI Tier 1+2 jobs without ANTHROPIC_API_KEY).
    """
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("HATA: ANTHROPIC_API_KEY bulunamadı.")
            sys.exit(1)
        _CLIENT = anthropic.Anthropic(api_key=api_key)
    return _CLIENT

MODEL_ANALYST  = "claude-opus-4-6"   # strategic decisions — Opus quality
MODEL_AUDITOR  = "claude-haiku-4-5"  # rule-based risk check — Haiku sufficient
MODEL = MODEL_AUDITOR  # default for backward-compat

MAX_TOKENS_ANALYST  = 600   # JSON output, ~5-8 signals × ~80 tokens each
MAX_TOKENS_AUDITOR  = 400   # JSON audit, only BUY/SELL subset
MAX_TOKENS_FALLBACK = 2000  # full-MD non-compact mode

BASE_DIR = Path(__file__).parent
INTELLIGENCE_DIR = BASE_DIR / "intelligence"
PROMPTS_DIR = BASE_DIR / "prompts"

BRIEFING_FILE = INTELLIGENCE_DIR / "daily_briefing.json"
ANALYST_REPORT_FILE = INTELLIGENCE_DIR / "analyst_report.md"
AUDIT_REPORT_FILE = INTELLIGENCE_DIR / "audit_report.md"
FINAL_DECISION_FILE = INTELLIGENCE_DIR / "final_decision.md"

SEP = "=" * 65

CACHE_DIR = INTELLIGENCE_DIR / "cache"


def _cache_key(prompt: str, system: str) -> str:
    return hashlib.md5((prompt + system).encode()).hexdigest()[:12]


def _cache_get(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        except (KeyError, json.JSONDecodeError):
            return None
    return None


def _cache_set(key: str, response: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({"response": response}), encoding="utf-8")


ANALYST_COMPACT_SYSTEM = """Hedge fund analyst. Druckenmiller methodology: Macro → Sector → Stock → Timing.
Input: macro snapshot + pre-filtered BIST tickers.
Output: JSON only — no prose, no explanation.
Format:
{"signals":[{"ticker":"X","action":"BUY|SELL|HOLD|WATCH","conviction":"HIGH|MED|LOW","reason":"max 15 words","narrative":"max 20 words","levels":{"entry":0,"stop":0,"target":0}}]}

LOKAL MAKRO NARRATIVE:
For each stock signal, answer: "Does current local macro regime support this stock's story?"

Local macro context:
- TCMB rate direction: Hike → weakens holding/cash companies, strengthens exporters
- CDS premium: >350 bps → downgrade all BUY signals one level (BUY→HOLD, HOLD→SELL)
- BIST foreign ownership trend: Declining → institutional exit risk, reduce conviction

Narrative output format: "narrative": "max 20 words briefly explaining if macro supports this signal"
Do NOT modify Layer 7 score — narrative is audit context only."""

AUDITOR_COMPACT_SYSTEM = """Hedge fund risk director. Devil's advocate.
Input: analyst JSON signals.
Audit only BUY/SELL actions — what kills this trade?
Output: JSON only.
Format:
{"audits":[{"ticker":"X","risk_score":5,"red_flags":["..."],"verdict":"CONFIRM|REDUCE|REJECT","worst_case":"max 10 words"}]}"""


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}_system_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Sen bir BIST {name} agentısın."


def build_compact_analyst_prompt(briefing: dict) -> str:
    """Build a compact analyst prompt from pre-filtered signals + macro snapshot."""
    macro = briefing.get("macro_snapshot", {})
    prices = macro.get("prices", {})
    comps = macro.get("components", {})

    macro_line = (
        f"USDTRY:{prices.get('usdtry', 'N/A')} "
        f"VIX:{prices.get('vix', 'N/A')} "
        f"BRENT:{prices.get('brent', 'N/A')} "
        f"BIST100_score:{comps.get('bist100', 'N/A'):+.3f} "
        f"REGIME:{macro.get('regime', 'UNKNOWN')}"
        if prices else "MACRO: no data"
    )

    filtered = briefing.get("filtered_signals", [])
    if not filtered:
        # Fall back to momentum_top5
        filtered = briefing.get("momentum_top5", [])

    portfolio = briefing.get("portfolio", [])
    portfolio_tickers = {p["ticker"] for p in portfolio}

    ticker_lines = []
    for s in filtered:
        ticker = s.get("ticker", "?")
        tag = "[PORT]" if ticker in portfolio_tickers else "[WATCH]"
        rsi = s.get("rsi")
        vol = s.get("vol_surge")
        ret1m = s.get("ret_1m_pct")
        score = s.get("momentum_score")
        line = (
            f"{ticker}{tag}: "
            f"RSI={rsi:.0f} " if rsi is not None else f"{ticker}{tag}: RSI=N/A "
        )
        line = f"{ticker}{tag}:"
        if rsi is not None:
            line += f" RSI={rsi:.0f}"
        if vol is not None:
            line += f" VOL={vol:.1f}x"
        if ret1m is not None:
            line += f" 1M={ret1m:+.1f}%"
        if score is not None:
            line += f" SCORE={score:.3f}"
        ticker_lines.append(line)

    # Also include portfolio positions not in filtered
    for p in portfolio:
        if p["ticker"] not in {s.get("ticker") for s in filtered}:
            pnl = p.get("unrealized_pnl_pct")
            rsi = p.get("rsi")
            line = f"{p['ticker']}[PORT]: cost=₺{p['avg_cost']:.2f}"
            if rsi is not None:
                line += f" RSI={rsi:.0f}"
            if pnl is not None:
                line += f" P&L={pnl:+.1f}%"
            ticker_lines.append(line)

    return (
        f"MACRO: {macro_line}\n\n"
        f"TICKERS ({len(ticker_lines)}):\n"
        + "\n".join(ticker_lines)
        + "\n\nReturn JSON only."
    )


def build_compact_audit_prompt(analyst_signals: list[dict]) -> str:
    """Build compact audit prompt — only BUY/SELL actions."""
    to_audit = [s for s in analyst_signals if s.get("action") in ("BUY", "SELL")]
    if not to_audit:
        return ""
    lines = [
        f"{s['ticker']} {s['action']} {s.get('conviction','?')}: {s.get('reason','?')}"
        for s in to_audit
    ]
    return "Audit these signals — what can go wrong?\n" + "\n".join(lines) + "\n\nReturn JSON only."


def load_kap_context(kap_json_path: str) -> dict:
    """Load intelligence/kap_YYYY-MM-DD.json and return analyst-injectable context.

    Returns:
        {
            "kap_alerts": ["THYAO: Ozel durum — ... (kap_official)", ...],
            "high_priority_symbols": ["THYAO", ...]
        }
        Empty lists if file missing or unreadable.
    """
    path = Path(kap_json_path)
    if not path.exists():
        return {"kap_alerts": [], "high_priority_symbols": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"kap_alerts": [], "high_priority_symbols": []}

    alerts = []
    for ev in data.get("events", []):
        symbol = ev.get("symbol", "?")
        category = ev.get("category", "diger")
        subject = ev.get("subject", "")
        src = ev.get("source_type", "kap_official")
        alerts.append(f"{symbol}: {category} — {subject[:80]} ({src})")

    return {
        "kap_alerts": alerts,
        "high_priority_symbols": data.get("high_priority_flags", []),
    }


def load_briefing() -> dict:
    if not BRIEFING_FILE.exists():
        raise FileNotFoundError(
            f"Briefing bulunamadı: {BRIEFING_FILE}\n"
            "Önce çalıştır: python scripts/daily_update.py --scan --generate-report"
        )
    data = json.loads(BRIEFING_FILE.read_text(encoding="utf-8"))
    if not data.get("date"):
        raise ValueError("Briefing boş — daily_update.py henüz çalışmamış.")
    return data


def format_briefing(briefing: dict) -> str:
    lines = [f"# Günlük Briefing — {briefing['date']}"]

    # Risk limits
    risk_limits = briefing.get("risk_limits", {})
    max_sector = risk_limits.get("max_sector_concentration", 0.30)
    max_position = risk_limits.get("max_position_size", 0.15)
    lines.append(f"\n## Risk Limitleri")
    lines.append(f"- Max sektör konsantrasyonu: %{max_sector * 100:.0f}")
    lines.append(f"- Max pozisyon büyüklüğü: %{max_position * 100:.0f}")

    # Portfolio section
    lines.append("\n## Portföy Durumu")
    portfolio = briefing.get("portfolio", [])
    total_cost = sum(
        p["avg_cost"] * p["quantity"]
        for p in portfolio
        if p.get("avg_cost") is not None
    )
    for pos in portfolio:
        pnl = pos.get("unrealized_pnl_pct")
        rsi = pos.get("rsi")
        price = pos.get("current_price")
        sector = pos.get("sector", "bilinmiyor")
        pnl_str = f"{pnl:+.1f}%" if pnl is not None else "N/A"
        rsi_str = f"RSI={rsi:.0f}" if rsi is not None else "RSI=N/A"
        price_str = f"₺{price:.2f}" if price is not None else "N/A"
        alert_msgs = [a["message"] for a in pos.get("alerts", [])]
        alert_str = " ⚠️ " + ", ".join(alert_msgs) if alert_msgs else ""
        lines.append(
            f"- {pos['ticker']} [{sector}]: {pos['quantity']} lot @ ₺{pos['avg_cost']:.2f} | "
            f"Şimdi: {price_str} | P&L: {pnl_str} | {rsi_str}{alert_str}"
        )

    # Sector concentration check
    if total_cost > 0:
        sector_costs: dict[str, float] = {}
        for pos in portfolio:
            s = pos.get("sector", "bilinmiyor")
            sector_costs[s] = sector_costs.get(s, 0.0) + pos["avg_cost"] * pos["quantity"]

        lines.append("\n## Sektör Konsantrasyon Analizi")
        breaches = []
        for sector, cost in sorted(sector_costs.items(), key=lambda x: -x[1]):
            pct = cost / total_cost
            flag = " ❌ LİMİT AŞILDI" if pct > max_sector else " ✅"
            lines.append(f"- {sector}: %{pct * 100:.1f} (₺{cost:,.0f}){flag}")
            if pct > max_sector:
                breaches.append(f"{sector} %{pct * 100:.1f} > limit %{max_sector * 100:.0f}")
        if breaches:
            lines.append(f"\n⚠️ KONSANTRASYON UYARISI: {', '.join(breaches)}")

    # Momentum section
    momentum = briefing.get("momentum_top5", [])
    if momentum:
        lines.append("\n## Momentum Top 5")
        for m in momentum:
            rsi = m.get("rsi")
            score = m.get("momentum_score")
            day = m.get("daily_chg_pct")
            rsi_str = f"{rsi:.0f}" if rsi is not None else "N/A"
            score_str = f"{score:.4f}" if score is not None else "N/A"
            day_str = f"{day:+.1f}%" if day is not None else "N/A"
            lines.append(
                f"- {m['ticker']}: ₺{m['close']:.2f} | Günlük: {day_str} | "
                f"RSI: {rsi_str} | Skor: {score_str}"
            )

    macro = briefing.get("macro_data", {})
    if macro:
        lines.append("\n## Makro Veri")

        def _fmt(key: str, label: str, suffix: str = "") -> str:
            val = macro.get(key)
            chg = macro.get(f"{key}_change_pct")
            val_str = f"{val:.2f}{suffix}" if val is not None else "N/A"
            chg_str = f"{chg:+.2f}%" if chg is not None else "N/A"
            return f"- {label}: {val_str} ({chg_str})"

        lines.append(_fmt("usdtry", "USD/TRY"))
        lines.append(_fmt("oil_brent", "Brent Petrol", "$"))
        lines.append(_fmt("vix", "VIX"))
        lines.append(_fmt("sp500", "S&P500"))
        lines.append(_fmt("gold", "Altın", "$"))

    alerts = briefing.get("alerts", [])
    if alerts:
        lines.append("\n## Aktif Uyarılar")
        for al in alerts:
            lines.append(f"- [{al['severity']}] {al.get('ticker', '')}: {al['message']}")

    return "\n".join(lines)


def call_analyst(briefing_text: str, compact: bool = False) -> str:
    print(f"\n{SEP}")
    print("  ANALYST API CALL")
    print(SEP)

    system = ANALYST_COMPACT_SYSTEM if compact else load_prompt("analyst")
    max_tok = MAX_TOKENS_ANALYST if compact else MAX_TOKENS_FALLBACK
    mode_label = "compact/JSON" if compact else "full/MD"

    key = _cache_key(briefing_text, system)
    cached = _cache_get(key)
    if cached is not None:
        print(f"  [CACHE HIT | mode: {mode_label} | key: {key}]")
        return cached

    response = _get_client().messages.create(
        model=MODEL_ANALYST,
        max_tokens=max_tok,
        system=system,
        messages=[{"role": "user", "content": briefing_text}],
    )
    report = response.content[0].text
    _cache_set(key, report)
    print(f"  [model: {MODEL_ANALYST} | mode: {mode_label} | tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out | key: {key}]")
    return report


def call_auditor(analyst_report: str, compact_prompt: str | None = None) -> str:
    print(f"\n{SEP}")
    print("  AUDITOR API CALL")
    print(SEP)

    if compact_prompt is not None:
        if not compact_prompt.strip():
            print("  [skipped — no BUY/SELL signals to audit]")
            return '{"audits":[]}'
        user_message = compact_prompt
        system = AUDITOR_COMPACT_SYSTEM
        max_tok = MAX_TOKENS_AUDITOR
    else:
        user_message = f"Aşağıdaki Analyst raporunu denetle:\n\n{analyst_report}"
        system = load_prompt("auditor")
        max_tok = MAX_TOKENS_FALLBACK

    key = _cache_key(user_message, system)
    cached = _cache_get(key)
    if cached is not None:
        print(f"  [CACHE HIT | key: {key}]")
        return cached

    response = _get_client().messages.create(
        model=MODEL_AUDITOR,
        max_tokens=max_tok,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    report = response.content[0].text
    _cache_set(key, report)
    print(f"  [model: {MODEL_AUDITOR} | tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out | key: {key}]")
    return report


def build_final_decision(analyst_report: str, audit_report: str, briefing_date: str) -> str:
    signal_keywords = ("BUY", "SELL", "HOLD", "WATCH", "AL", "SAT")
    audit_keywords = ("ONAYLANDI", "REDDEDİLDİ", "DEĞİŞTİRİLDİ", "ORCHESTRATOR", "TAVSİYE")

    analyst_actions = [
        line for line in analyst_report.splitlines()
        if any(k in line.upper() for k in signal_keywords)
    ]
    audit_actions = [
        line for line in audit_report.splitlines()
        if any(k in line.upper() for k in audit_keywords)
    ]

    sections = [
        f"# Final Decision — {briefing_date}",
        "",
        "## Analyst Sinyalleri",
        *analyst_actions,
        "",
        "## Auditor Onayı",
        *audit_actions,
        "",
        "---",
        f"*Üretildi: {briefing_date} | Model: {MODEL}*",
    ]
    return "\n".join(sections)


def generate_decisions_file(
    final_decision_path: str,
    output_dir: str = "decisions",
    date_override: str | None = None,
) -> str:
    """
    Read final_decision.md and write decisions_YYYY-MM-DD.md to output_dir.

    Returns:
        str: Full path of the written decisions file.

    Raises:
        FileNotFoundError: If final_decision_path does not exist.
        ValueError: If final_decision content is empty or date_override format is wrong.
        PermissionError: If output_dir is not writable.
    """
    src = Path(final_decision_path)
    if not src.exists():
        raise FileNotFoundError(f"final_decision not found: {src}")

    content = src.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Empty final_decision")

    if date_override is not None:
        try:
            datetime.strptime(date_override, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date_override must be YYYY-MM-DD")
        today = date_override
    else:
        today = date.today().strftime("%Y-%m-%d")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"decisions_{today}.md"
    if out_path.exists():
        import logging
        logging.getLogger(__name__).warning(
            "decisions_%s.md already exists — overwriting", today
        )

    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    run_id = str(uuid.uuid4())

    decisions_content = (
        f"# Trading Decisions — {today}\n\n"
        f"## Source\n"
        f"Generated from: {src}\n"
        f"Generated at: {generated_at}\n\n"
        f"## Decisions\n\n"
        f"{content}\n\n"
        f"## Metadata\n"
        f"- pipeline_run_id: {run_id}\n"
    )

    out_path.write_text(decisions_content, encoding="utf-8")
    return str(out_path)


def main() -> None:
    print(SEP)
    print("  BIST HEDGE FUND OS — ORCHESTRATOR")
    print(SEP)

    # Step 0: KAP pipeline + Signal Engine (pre-market, zero API cost)
    print("\n[0/4] KAP bildirimleri ve sinyal motoru çalıştırılıyor...")
    kap_context: dict = {"kap_alerts": [], "high_priority_symbols": []}
    signal_context: dict = {}
    try:
        import sys as _sys
        _project_root = str(BASE_DIR.parent)
        if _project_root not in _sys.path:
            _sys.path.insert(0, _project_root)
        from src.data.kap_scheduler import run_daily_kap_pipeline
        kap_json_path = run_daily_kap_pipeline(
            output_dir=str(INTELLIGENCE_DIR),
        )
        kap_context = load_kap_context(kap_json_path)
        print(f"      KAP alerts : {len(kap_context['kap_alerts'])}")
        print(f"      High prio  : {kap_context['high_priority_symbols']}")
    except Exception as exc:
        print(f"      [KAP SKIP] {exc}")

    # Signal Engine: runs after KAP, uses pre-filter data from briefing (loaded at step 1)
    # We defer signal engine to after briefing load — stored in signal_context

    # Step 1: Load briefing
    print("\n[1/4] Briefing yükleniyor...")
    briefing = load_briefing()
    briefing_date = briefing["date"]
    print(f"      Tarih   : {briefing_date}")
    print(f"      Portföy : {len(briefing.get('portfolio', []))} pozisyon")
    print(f"      Momentum: {len(briefing.get('momentum_top5', []))} hisse")
    print(f"      Uyarılar: {len(briefing.get('alerts', []))} adet")

    briefing_text = format_briefing(briefing)

    # Use compact mode when pre-filtered signals are available (token optimization)
    has_filtered = bool(briefing.get("filtered_signals"))
    compact_mode = has_filtered

    # Signal Engine: build signal context from briefing data
    try:
        from src.signals.engine import compute_batch, build_signal_context_for_orchestrator
        _filtered = briefing.get("filtered_signals", briefing.get("momentum_top5", []))
        _macro_snap = briefing.get("macro_snapshot", {})
        _macro_comps = _macro_snap.get("components", {})
        _macro_data = {
            "USDTRY": _macro_comps.get("usdtry", 0.0),
            "VIX": _macro_comps.get("vix", 0.0),
            "BRENT": _macro_comps.get("brent", 0.0),
            "SP500": _macro_comps.get("sp500", 0.0),
            "BIST100": _macro_comps.get("bist100", 0.0),
            "vix_level": _macro_snap.get("prices", {}).get("vix", 22.0),
            "USDTRY_1d_change": _macro_snap.get("changes", {}).get("usdtry", 0.0),
            "BIST100_1d_change": _macro_snap.get("changes", {}).get("bist100", 0.0),
        }
        _symbols = [s["ticker"] for s in _filtered if "ticker" in s]
        _tech_batch = {
            s["ticker"]: {
                "rsi": s.get("rsi"),
                "momentum_score": s.get("momentum_score"),
                "volume_surge": s.get("vol_surge", 1.0) is not None and s.get("vol_surge", 1.0) > 1.5,
            }
            for s in _filtered if "ticker" in s
        }
        _kap_events_raw = json.loads(
            (INTELLIGENCE_DIR / f"kap_{date.today().strftime('%Y-%m-%d')}.json").read_text(encoding="utf-8")
        ).get("events", []) if (INTELLIGENCE_DIR / f"kap_{date.today().strftime('%Y-%m-%d')}.json").exists() else []
        _kap_batch = {}
        for ev in _kap_events_raw:
            sym = ev.get("symbol", "")
            _kap_batch.setdefault(sym, []).append(ev)

        if _symbols:
            _results = compute_batch(_symbols, _tech_batch, _macro_data, _kap_batch)
            signal_context = build_signal_context_for_orchestrator(_results)
            # Write signals JSON to intelligence dir
            _signals_path = INTELLIGENCE_DIR / f"signals_{date.today().strftime('%Y-%m-%d')}.json"
            _signals_path.write_text(
                json.dumps(
                    {"date": signal_context["date"], "regime": signal_context["regime"],
                     "risk_off": signal_context["risk_off"],
                     "signals": [{"symbol": r.symbol, "final_signal": r.final_signal,
                                  "score": round(r.score, 2),
                                  "summary": r.audit.signal_summary}
                                 for r in _results]},
                    ensure_ascii=False, indent=2
                ),
                encoding="utf-8"
            )
            print(f"      Signal engine: {len(_results)} symbols | regime={signal_context['regime']} | risk_off={signal_context['risk_off']}")
        else:
            print("      [SIGNAL SKIP] no symbols from briefing")
    except Exception as exc:
        print(f"      [SIGNAL SKIP] {exc}")

    # Step 2: Analyst
    mode_label = "compact/JSON" if compact_mode else "full/MD"
    print(f"\n[2/4] Analyst çağrılıyor... [{mode_label}]")

    if compact_mode:
        analyst_input = build_compact_analyst_prompt(briefing)
        if kap_context["kap_alerts"]:
            kap_lines = "\n".join(f"  • {a}" for a in kap_context["kap_alerts"][:10])
            analyst_input = f"KAP ALERTS:\n{kap_lines}\n\n{analyst_input}"
        if signal_context:
            strong = signal_context.get("strong_signals", [])
            weak = signal_context.get("weak_signals", [])
            sells = signal_context.get("sell_signals", [])
            conflicts = signal_context.get("conflict_symbols", [])
            regime = signal_context.get("regime", "NEUTRAL")
            risk_off = signal_context.get("risk_off", False)
            sig_lines = []
            for entry in (strong + weak):
                sig_lines.append(f"  {entry['symbol']}: {entry['signal']} (score={entry['score']})")
            for entry in sells:
                sig_lines.append(f"  {entry['symbol']}: {entry['signal']} (score={entry['score']})")
            if sig_lines:
                sig_block = (
                    f"[SIGNAL ENGINE | REGIME:{regime} | RISK_OFF:{risk_off}]\n"
                    + "\n".join(sig_lines[:15])
                )
                if conflicts:
                    sig_block += f"\n  CONFLICT_SYMBOLS: {', '.join(conflicts)}"
                sig_block += f"\n  MISSING_LAYERS: sentiment, smart_money\n"
                analyst_input = sig_block + "\n\n" + analyst_input
    else:
        analyst_input = briefing_text

    analyst_report = call_analyst(analyst_input, compact=compact_mode)
    ANALYST_REPORT_FILE.write_text(f"# Analyst Report\n\n{analyst_report}", encoding="utf-8")

    print()
    print(analyst_report)
    print(f"\n      → analyst_report.md yazıldı")

    # Step 3: Auditor
    print(f"\n[3/4] Auditor çağrılıyor...")

    # In compact mode, parse analyst JSON and build targeted audit prompt
    compact_audit_prompt = None
    if compact_mode:
        try:
            analyst_json = json.loads(analyst_report)
            signals = analyst_json.get("signals", [])
            compact_audit_prompt = build_compact_audit_prompt(signals)
        except (json.JSONDecodeError, AttributeError):
            # Analyst returned non-JSON — fall back to full audit
            compact_audit_prompt = None

    audit_report = call_auditor(analyst_report, compact_prompt=compact_audit_prompt)
    AUDIT_REPORT_FILE.write_text(f"# Audit Report\n\n{audit_report}", encoding="utf-8")

    print()
    print(audit_report)
    print(f"\n      → audit_report.md yazıldı")

    # Step 4: Final decision
    print(f"\n[4/4] Final decision yazılıyor...")
    final = build_final_decision(analyst_report, audit_report, briefing_date)
    FINAL_DECISION_FILE.write_text(final, encoding="utf-8")

    print(f"\n{SEP}")
    print("  FINAL DECISION")
    print(SEP)
    print(final)
    print(f"\n      → final_decision.md yazıldı")

    # Step 5: Decisions file
    decisions_out = BASE_DIR.parent / "decisions"
    decisions_path = generate_decisions_file(
        str(FINAL_DECISION_FILE),
        output_dir=str(decisions_out),
    )
    print(f"\n      → {decisions_path} yazıldı")

    print(f"\n{SEP}")
    print("  Pipeline tamamlandı.")
    print(SEP)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as e:
        print(f"\nHATA: {e}")
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"\nAPI HATASI: {e}")
        sys.exit(1)
