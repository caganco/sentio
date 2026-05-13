"""Weekly efficiency tracker: reads intelligence reports and generates an efficiency report."""
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

MODEL = "claude-haiku-4-5"

BASE_DIR = Path(__file__).parent
INTELLIGENCE_DIR = BASE_DIR / "intelligence"
PROMPTS_DIR = BASE_DIR / "prompts"

ANALYST_REPORT = INTELLIGENCE_DIR / "analyst_report.md"
AUDIT_REPORT = INTELLIGENCE_DIR / "audit_report.md"
FINAL_DECISION = INTELLIGENCE_DIR / "final_decision.md"
EFFICIENCY_REPORT = INTELLIGENCE_DIR / "efficiency_report.md"

SEP = "=" * 65

EFFICIENCY_SYSTEM_PROMPT_FILE = PROMPTS_DIR / "efficiency_system_prompt.md"

DEFAULT_EFFICIENCY_SYSTEM_PROMPT = """
Sen BIST Hedge Fund OS'in EFFICIENCY Agent'ısın.

İki ana görevin var:
1. Sistem Optimizasyonu: Multi-agent BIST trading sisteminin verimliliğini izler ve optimize edersin.
2. Tech Rehberlik: Kullanıcının her türlü teknik sorusuna cevap verirsin.

Sistem:
- Proje dizini: C:\\Users\\cagan\\bist-trading-system\\
- Agent ekibi: Orchestrator, Analyst, Auditor, Efficiency, Builder
- Günlük workflow: 09:00 Builder → 09:05 Analyst+Auditor → 09:10 Efficiency (Pazartesi)

Görevin (WEEKLY EFFICIENCY REPORT):
- Geçen haftanın analyst ve audit raporlarını değerlendir
- Sinyal kalitesini, risk yönetimini, kararların tutarlılığını analiz et
- Token & tahmini maliyet hesapla
- Workflow darboğazlarını tespit et
- Gelecek hafta için 3 optimizasyon önerisi sun

Rapor formatı:
## EFFICIENCY REPORT — {tarih}

### 1. Sinyal Kalitesi
### 2. Risk Yönetimi Değerlendirmesi
### 3. Karar Tutarlılığı
### 4. Tahmini Token Maliyeti
### 5. Workflow Darboğazları
### 6. Gelecek Hafta İçin 3 Öneri

Az uğraş, çok verim prensibini benimse. Kısa, aksiyon odaklı cevaplar ver.
"""


def load_system_prompt() -> str:
    if EFFICIENCY_SYSTEM_PROMPT_FILE.exists():
        return EFFICIENCY_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    EFFICIENCY_SYSTEM_PROMPT_FILE.write_text(DEFAULT_EFFICIENCY_SYSTEM_PROMPT, encoding="utf-8")
    return DEFAULT_EFFICIENCY_SYSTEM_PROMPT


def load_reports() -> str:
    sections = []
    for path, label in [
        (ANALYST_REPORT, "ANALYST REPORT"),
        (AUDIT_REPORT, "AUDIT REPORT"),
        (FINAL_DECISION, "FINAL DECISION"),
    ]:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            sections.append(f"## {label}\n\n{content}")
        else:
            sections.append(f"## {label}\n\nDosya bulunamadı: {path}")
    return "\n\n---\n\n".join(sections)


def main() -> None:
    print(SEP)
    print("  BIST HEDGE FUND OS — EFFICIENCY TRACKER")
    print(SEP)

    today = str(date.today())

    reports_text = load_reports()
    user_message = (
        f"Tarih: {today}\n\n"
        "Aşağıdaki bu haftanın agent raporlarını analiz et ve EFFICIENCY REPORT üret:\n\n"
        f"{reports_text}"
    )

    print(f"\n[1/2] Raporlar okunuyor...")
    analyst_exists = ANALYST_REPORT.exists()
    audit_exists = AUDIT_REPORT.exists()
    print(f"      analyst_report.md : {'✓' if analyst_exists else '✗'}")
    print(f"      audit_report.md   : {'✓' if audit_exists else '✗'}")

    print(f"\n[2/2] Efficiency analizi yapılıyor...")
    print(SEP)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=load_system_prompt(),
        messages=[{"role": "user", "content": user_message}],
    )

    report = response.content[0].text
    print(f"  [tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")

    output = f"# Efficiency Report — {today}\n\n{report}"
    EFFICIENCY_REPORT.write_text(output, encoding="utf-8")

    print()
    print(report)
    print(f"\n      → efficiency_report.md yazıldı")

    print(f"\n{SEP}")
    print("  Efficiency Tracker tamamlandı.")
    print(SEP)


if __name__ == "__main__":
    try:
        main()
    except anthropic.APIError as e:
        print(f"\nAPI HATASI: {e}")
        sys.exit(1)
