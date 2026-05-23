"""Interactive Architect Agent for BIST Hedge Fund OS."""
import json
import os
import sys
from datetime import datetime
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
SPECS_DIR = INTELLIGENCE_DIR / "specs"
PROMPTS_DIR = BASE_DIR / "prompts"

SPECS_DIR.mkdir(parents=True, exist_ok=True)

SEP = "=" * 65


def load_system_prompt() -> str:
    path = PROMPTS_DIR / "architect_system_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Sen BIST Hedge Fund OS'in ARCHITECT Agent'ısın."


def format_spec_filename(topic: str) -> str:
    """Generate SPEC filename: SPEC_YYYY-MM-DD_topic.md"""
    today = datetime.now().strftime("%Y-%m-%d")
    clean_topic = topic.lower().replace(" ", "_")
    # Remove special characters that cause filesystem issues
    for char in ":<>|?*\"/":
        clean_topic = clean_topic.replace(char, "_")
    clean_topic = clean_topic[:30]
    return f"SPEC_{today}_{clean_topic}.md"


def save_spec(spec_content: str, topic: str) -> Path:
    """Save SPEC to specs directory."""
    filename = format_spec_filename(topic)
    path = SPECS_DIR / filename
    path.write_text(spec_content, encoding="utf-8")
    return path


def architect_chat(directive: str) -> str:
    """Send directive to Architect Agent, return SPEC response."""
    print(f"\n{SEP}")
    print("  ARCHITECT API CALL")
    print(SEP)
    print(f"  Directive: {directive[:80]}...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=load_system_prompt(),
        messages=[{"role": "user", "content": directive}],
    )

    spec = response.content[0].text
    print(f"  [tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out]")
    return spec


def main() -> None:
    print(SEP)
    print("  BIST HEDGE FUND OS — ARCHITECT (Interactive)")
    print(SEP)
    print("  Orchestrator direktiflerini SPEC'lere dönüştür.")
    print("  (CTRL+C ile çık)")
    print(SEP)

    while True:
        print()
        directive = input("Directive (konu başlığı): ").strip()
        if not directive:
            continue

        spec = architect_chat(directive)

        print()
        print(spec)
        print()

        # Optionally save
        save_choice = input("SPEC'i kaydet? (e/h) [e]: ").strip().lower()
        if save_choice != "h":
            path = save_spec(spec, directive)
            print(f"✓ Kaydedildi: {path.relative_to(BASE_DIR.parent)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nÇıkılıyor...")
        sys.exit(0)
    except anthropic.APIError as e:
        print(f"\nAPI HATASI: {e}")
        sys.exit(1)
