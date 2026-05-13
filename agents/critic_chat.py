"""Weekly critic pipeline: reads final_decision + decision_log and generates a critic report."""
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

FINAL_DECISION = INTELLIGENCE_DIR / "final_decision.md"
DECISION_LOG = INTELLIGENCE_DIR / "decision_log.csv"
CRITIC_REPORT = INTELLIGENCE_DIR / "critic_report.md"

SEP = "=" * 65

CRITIC_SYSTEM_PROMPT_FILE = PROMPTS_DIR / "critic_system_prompt.md"

DEFAULT_CRITIC_SYSTEM_PROMPT = """
Sen BIST Hedge Fund OS'in CRITIC Agent'ısın.

Rolün:
Sistemin kendi kendini doğrulama eğilimine (confirmation bias) karşı yapısal bir itiraz mekanizmasısın.
Analyst, Auditor ve Orchestrator aynı ham veriden beslenip birbirini doğruluyorsa — sen onların görmediğini görürsün.

Görevin:
1. Final kararları ve decision log'u oku
2. Şu soruları sırayla yanıtla:

   A) SİSTEM GERÇEKTEN DRUCKENMILLER GİBİ Mİ DÜŞÜNÜYOR?
      Makro conviction mu teknik sinyali yönlendiriyor, yoksa teknik sinyal mi makroyla gerekçelendiriliyor?
      Fark: Druckenmiller teknik analizi ZAMANLAMA ARACI olarak kullanır, strateji olarak değil.

   B) EN ZAYIF VARSAYIM NEDİR?
      Son kararda en az test edilmiş, hiç sorgulanmamış varsayımı bul.

   C) KİMSENİN SORMADĞI SORU NEDİR?
      Decision log'a bakarak sistemin görmezden geldiği riski isimlendirö

   D) GROUPTHINK RİSKİ VAR MI?
      Tüm katmanlar aynı sonuca mı ulaştı? Varsa bu güçlü sinyal mi, yoksa confirmation bias mı?

   E) İNSAN SORUSU — KULLANICI DİSİPLİNİ
      Sistemin "sat" dediği kararlarda kullanıcı "biraz daha bekleyeyim" dedi mi?
      Decision log'da "applied: pending" olanlar varsa bu soruyu sor.

3. ORCHESTRATOR'A TAVSİYE: 2-3 madde, aksiyon odaklı.

4. SİSTEM GÜVEN SKORU: X/10 — kısa gerekçeyle.

Format:
=== CRITIC REPORT — {tarih} ===

SİSTEM GÜVEN SKORU: X/10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ SİSTEM GERÇEKTEN DRUCKENMILLER GİBİ Mİ DÜŞÜNÜYOR?
[cevap]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ EN ZAYIF VARSAYIM
[cevap]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ KİMSENİN SORMADĞI SORU
[cevap]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ GROUPTHINK RİSKİ: VAR / YOK
[gerekçe]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ İNSAN SORUSU — KULLANICI DİSİPLİNİ
[cevap — decision_log'daki applied durumuna göre]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ ORCHESTRATOR'A TAVSİYE
[2-3 madde]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SİSTEM REVİZYON GEREKİYOR MU: Evet / Hayır
[tek cümle gerekçe]

Kısa, keskin, acımasız dürüst. İyi haber değil, gerçek haber.
"""


def load_system_prompt() -> str:
    if CRITIC_SYSTEM_PROMPT_FILE.exists():
        return CRITIC_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    CRITIC_SYSTEM_PROMPT_FILE.write_text(DEFAULT_CRITIC_SYSTEM_PROMPT, encoding="utf-8")
    return DEFAULT_CRITIC_SYSTEM_PROMPT


def load_inputs() -> str:
    sections = []
    for path, label in [
        (FINAL_DECISION, "FINAL DECISION"),
        (DECISION_LOG, "DECISION LOG (CSV)"),
    ]:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            sections.append(f"## {label}\n\n{content}")
        else:
            sections.append(f"## {label}\n\nDosya bulunamadı: {path}")
    return "\n\n---\n\n".join(sections)


def main() -> None:
    print(SEP)
    print("  BIST HEDGE FUND OS — CRITIC")
    print(SEP)

    today = str(date.today())

    inputs_text = load_inputs()
    user_message = (
        f"Tarih: {today}\n\n"
        "Aşağıdaki bu haftanın kararlarını ve decision log'u analiz et, "
        "CRITIC REPORT üret:\n\n"
        f"{inputs_text}"
    )

    print(f"\n[1/2] Girdiler okunuyor...")
    print(f"      final_decision.md : {'✓' if FINAL_DECISION.exists() else '✗'}")
    print(f"      decision_log.csv  : {'✓' if DECISION_LOG.exists() else '✗'}")

    print(f"\n[2/2] Critic analizi yapılıyor...")
    print(SEP)

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=load_system_prompt(),
        messages=[{"role": "user", "content": user_message}],
    )

    report = response.content[0].text
    print(f"  [tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")

    output = f"# Critic Report — {today}\n\n{report}"
    CRITIC_REPORT.write_text(output, encoding="utf-8")

    print()
    print(report)
    print(f"\n      → critic_report.md yazıldı")

    print(f"\n{SEP}")
    print("  Critic tamamlandı.")
    print(SEP)


if __name__ == "__main__":
    try:
        main()
    except anthropic.APIError as e:
        print(f"\nAPI HATASI: {e}")
        sys.exit(1)
