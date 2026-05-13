"""Automated pipeline: Briefing → Analyst → Auditor → Final Decision."""
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import anthropic
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("HATA: ANTHROPIC_API_KEY bulunamadı.")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

MODEL = "claude-sonnet-4-6"

BASE_DIR = Path(__file__).parent
INTELLIGENCE_DIR = BASE_DIR / "intelligence"
PROMPTS_DIR = BASE_DIR / "prompts"

BRIEFING_FILE = INTELLIGENCE_DIR / "daily_briefing.json"
ANALYST_REPORT_FILE = INTELLIGENCE_DIR / "analyst_report.md"
AUDIT_REPORT_FILE = INTELLIGENCE_DIR / "audit_report.md"
FINAL_DECISION_FILE = INTELLIGENCE_DIR / "final_decision.md"

SEP = "=" * 65


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}_system_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Sen bir BIST {name} agentısın."


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


def call_analyst(briefing_text: str) -> str:
    print(f"\n{SEP}")
    print("  ANALYST API CALL")
    print(SEP)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=load_prompt("analyst"),
        messages=[{"role": "user", "content": briefing_text}],
    )

    report = response.content[0].text
    print(f"  [tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")
    return report


def call_auditor(analyst_report: str) -> str:
    print(f"\n{SEP}")
    print("  AUDITOR API CALL")
    print(SEP)

    user_message = f"Aşağıdaki Analyst raporunu denetle:\n\n{analyst_report}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=load_prompt("auditor"),
        messages=[{"role": "user", "content": user_message}],
    )

    report = response.content[0].text
    print(f"  [tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")
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


def main() -> None:
    print(SEP)
    print("  BIST HEDGE FUND OS — ORCHESTRATOR")
    print(SEP)

    # Step 1: Load briefing
    print("\n[1/4] Briefing yükleniyor...")
    briefing = load_briefing()
    briefing_date = briefing["date"]
    print(f"      Tarih   : {briefing_date}")
    print(f"      Portföy : {len(briefing.get('portfolio', []))} pozisyon")
    print(f"      Momentum: {len(briefing.get('momentum_top5', []))} hisse")
    print(f"      Uyarılar: {len(briefing.get('alerts', []))} adet")

    briefing_text = format_briefing(briefing)

    # Step 2: Analyst
    print("\n[2/4] Analyst çağrılıyor...")
    analyst_report = call_analyst(briefing_text)
    ANALYST_REPORT_FILE.write_text(f"# Analyst Report\n\n{analyst_report}", encoding="utf-8")

    print()
    print(analyst_report)
    print(f"\n      → analyst_report.md yazıldı")

    # Step 3: Auditor
    print("\n[3/4] Auditor çağrılıyor...")
    audit_report = call_auditor(analyst_report)
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
