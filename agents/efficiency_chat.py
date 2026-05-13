import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY bulunamadı.")

client = anthropic.Anthropic(api_key=API_KEY)

MODEL = "claude-sonnet-4-6"
MAX_HISTORY = 20

BASE_DIR = Path(__file__).parent
MEMORY_DIR = BASE_DIR / "memory"
PROMPTS_DIR = BASE_DIR / "prompts"
MEMORY_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT_FILE = PROMPTS_DIR / "efficiency_system_prompt.md"

DEFAULT_SYSTEM_PROMPT = """
Sen BIST Hedge Fund OS'in EFFICIENCY Agent'ısın.

İki ana görevin var:
1. Sistem Optimizasyonu: Multi-agent BIST trading sisteminin verimliliğini izler ve optimize edersin.
2. Tech Rehberlik: Kullanıcının her türlü teknik sorusuna cevap verirsin.

Sistem:
- Proje dizini: C:\\Users\\cagan\\bist-trading-system\\
- Agent ekibi: Orchestrator, Analyst, Auditor, Efficiency, Builder
- Günlük workflow: 09:00 Builder → 09:05 Analyst → 09:20 Auditor → 09:45 Orchestrator → 10:00 Piyasa açılır

Görevin:
- Token & maliyet takibi yap
- Workflow darboğazlarını tespit et
- Optimizasyon önerileri üret
- Her hafta EFFICIENCY REPORT formatında rapor sun
- Teknik sorulara adım adım, kopyalanabilir komutlarla cevap ver

Az uğraş, çok verim prensibini benimse.
"""

if not SYSTEM_PROMPT_FILE.exists():
    SYSTEM_PROMPT_FILE.write_text(DEFAULT_SYSTEM_PROMPT, encoding="utf-8")

SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

MASTERPLAN_FILE = MEMORY_DIR / "masterplan.md"


def load_memory() -> str:
    """Load masterplan from memory directory."""
    masterplan = ""
    if MASTERPLAN_FILE.exists():
        masterplan = MASTERPLAN_FILE.read_text(encoding="utf-8")
    return masterplan.strip()


chat_history = []

print("=" * 60)
print("BIST HEDGE FUND OS — EFFICIENCY")
print("=" * 60)
print("\nKomutlar:")
print("  /quit    → çıkış")
print("  /clear   → history temizle")
print("  /memory  → masterplan göster")
print()

while True:
    user_input = input("Sen > ").strip()

    if not user_input:
        continue

    if user_input.lower() in ["/quit", "/exit", "q"]:
        print("\nSistem kapatılıyor...")
        break

    if user_input.lower() == "/clear":
        chat_history = []
        print("\nHistory temizlendi.\n")
        continue

    if user_input.lower() == "/memory":
        print("\n========== MASTER PLAN ==========\n")
        print(load_memory())
        print("\n=================================\n")
        continue

    memory = load_memory()

    full_message = f"""# Master Plan & Memory
{memory}

# Mesaj
{user_input}"""

    chat_history.append({"role": "user", "content": full_message})

    if len(chat_history) > MAX_HISTORY:
        chat_history = chat_history[-MAX_HISTORY:]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=chat_history
        )

        reply = response.content[0].text

        print(f"\nEfficiency >\n")
        print(reply)
        print(f"\n[tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")
        print("-" * 60 + "\n")

        chat_history.append({"role": "assistant", "content": reply})

    except Exception as e:
        print(f"\nHATA: {e}\n")
        if chat_history:
            chat_history.pop()
