"""Parse Borsa Istanbul disclosure list from bildirim-sorgu-sonuc page."""
import re
import json
import requests
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

CACHE = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe" / "bist_disc_list.html"

if CACHE.exists() and CACHE.stat().st_size > 1_000_000:
    html = CACHE.read_text(encoding="utf-8")
    print(f"Using cached HTML ({len(html):,} chars)")
else:
    session = requests.Session()
    r = session.get(
        "https://www.kap.org.tr/tr/bildirim-sorgu-sonuc?member=4028e4a14bcf2a06014be4d7e6e256b6",
        headers=HEADERS, timeout=60
    )
    html = r.text
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(html, encoding="utf-8")
    print(f"Downloaded HTML ({len(html):,} chars)")

# The HTML embeds Next.js RSC payload as double-escaped JSON:
# \\"disclosureBasic\\":{\\"publishDate\\":\\"09.06.2026...\\",\\"disclosureIndex\\":1615501,...}
# Strategy: extract the payload section, unescape it, then parse JSON blocks

# Find the raw JSON section in the HTML
# It typically starts after a numeric marker like "1:["
# Extract all disclosureBasic chunks from double-escaped JSON
# Pattern: the double-escaped JSON has \" as \\" in the HTML string

# Approach: find all \\"disclosureBasic\\" occurrences and extract the block
# Each block ends before the next }},{\ pattern

DONEMSEL_KEYWORDS = [
    "D\xf6nemsel",  # Dönemsel (proper Turkish)
    "donemsel",     # ASCII filename variant
    "Periodic",     # English
]

QUARTERLY_SUMMARY_PATTERN = re.compile(
    r'BIST (?:30|50|100|500|Pay Endeksleri|Geri|T(?:ek|atar)|Kat)',
    re.IGNORECASE
)

records = []
seen_ids = set()

# Extract via regex on the double-escaped HTML
# Match: \\"disclosureIndex\\":NUMBER ... up to next \\"},
disc_blocks = re.findall(
    r'\\"publishDate\\":\\"([^"\\]+)\\"\s*,\\"disclosureIndex\\":(\d+).*?\\"summary\\":\\"([^"\\]+)\\".*?\\"disclosureClass\\":\\"([^"\\]+)\\".*?\\"attachmentCount\\":(\d+)',
    html,
    re.DOTALL
)
print(f"Disclosure blocks (regex): {len(disc_blocks)}")

# Get title too
full_blocks = re.findall(
    r'\\"publishDate\\":\\"([^"\\]+)\\",\\"disclosureIndex\\":(\d+),[^{]*?\\"title\\":\\"([^"\\]*)\\",[^{]*?\\"summary\\":\\"([^"\\]*)\\",[^{]*?\\"disclosureClass\\":\\"([^"\\]*)\\",[^{]*?\\"attachmentCount\\":(\d+)',
    html,
)
print(f"Full blocks with title: {len(full_blocks)}")

# Better: find all disclosureIndex + surrounding context
# We know the structure from inspection:
# {"publishDate":"...","disclosureIndex":N,"stockCode":null,"hasMultiLanguageSupport":"Y",
#  "companyTitle":"...","title":"...","relatedStocks":"...","disclosureClass":"DKB",
#  "summary":"...","isChanged":null,...}
# But in double-escaped form with \\"

# Let's just find the section with all the data by extracting the RSC JSON blob
# The page has format: XX:[ ... ] where XX is a number
# RSC payload starts with something like 1:[...] or 0:{...}

# Find the large JSON array in the HTML
print()
print("Checking for 'D\\xf6nemsel' (Dönemsel) occurrences:")
donemsel_count = html.count("D\xf6nemsel")
print(f"  Dönemsel: {donemsel_count}")
print(f"  donemsel: {html.lower().count('donemsel')}")

# Extract everything between the first and last occurrence of \\"disclosureBasic\\"
start_idx = html.find('\\"disclosureBasic\\"')
print(f"\nFirst disclosureBasic at: {start_idx}")

if start_idx > 0:
    # The data is JSON embedded in a JS string. Let me extract the full blob.
    # Find the containing JS string: starts with something like 2:[ and ends with ]
    # Go backwards from start_idx to find the start

    # Simple approach: extract all the JSON-like content between markers
    # Each disclosure basic looks like:
    # \\"disclosureBasic\\":{\\"publishDate\\":\\"DD.MM.YYYY HH:MM:SS\\",\\"disclosureIndex\\":NNNNN,...}

    # Extract all disclosureIndex values with surrounding context
    pattern = re.compile(
        r'\\"disclosureBasic\\":\{'
        r'\\"publishDate\\":\\"([\d. :]+)\\",'
        r'\\"disclosureIndex\\":(\d+),'
        r'[^}]*'
        r'\\"title\\":\\"([^"\\]*)(?:\\"|\\\\")'
    )

    # Because the content uses \\" for quotes, and the title may have
    # special chars encoded as \uXXXX, let me use a simpler per-field extraction

    # Extract all publishDate+disclosureIndex pairs
    index_pattern = re.compile(
        r'\\"publishDate\\":\\"([\d. :]+)\\"[^}]{0,50}?\\"disclosureIndex\\":(\d+)'
    )
    index_matches = index_pattern.findall(html)
    print(f"\nTotal disclosures found: {len(index_matches)}")

    # For each, find nearby title and summary
    all_records = []
    # Get positions of all disclosureBasic
    for m in re.finditer(r'\\"disclosureBasic\\":\{', html):
        start = m.start()
        # Extract the next ~600 chars for this block
        block = html[start:start + 600]

        # Extract fields
        date_m = re.search(r'\\"publishDate\\":\\"([^"\\]+)\\"', block)
        idx_m = re.search(r'\\"disclosureIndex\\":(\d+)', block)
        title_m = re.search(r'\\"title\\":\\"([^"\\]*)\\"', block)
        summary_m = re.search(r'\\"summary\\":\\"([^"\\]*)\\"', block)
        class_m = re.search(r'\\"disclosureClass\\":\\"([^"\\]+)\\"', block)
        attach_m = re.search(r'\\"attachmentCount\\":(\d+)', block)

        if not (date_m and idx_m):
            continue

        pub_date = date_m.group(1)
        disc_idx = int(idx_m.group(1))
        title = title_m.group(1) if title_m else ""
        summary = summary_m.group(1) if summary_m else ""
        disc_class = class_m.group(1) if class_m else ""
        attach_cnt = int(attach_m.group(1)) if attach_m else 0

        if disc_idx in seen_ids:
            continue
        seen_ids.add(disc_idx)

        all_records.append({
            "disclosureIndex": disc_idx,
            "publishDate": pub_date,
            "title": title,
            "summary": summary,
            "disclosureClass": disc_class,
            "attachmentCount": attach_cnt,
        })

    print(f"All unique disclosures parsed: {len(all_records)}")

    # Filter: BIST Pay Endeksleri Dönemsel quarterly changes (XU030/050/100)
    # These have:
    # - title = "BIST Pay Endeksleri"
    # - summary contains "D\xf6nemsel" (Dönemsel) or attachments == 2
    # - summary mentions BIST 30, 50, 100 specifically

    quarterly = [
        r for r in all_records
        if "Pay Endeksleri" in r["title"]
        and r["attachmentCount"] == 2
        and ("D\xf6nemsel" in r["summary"] or "Dönemsel" in r["summary"])
    ]
    print(f"\nQuarterly pay endeks donemsel (attachmentCount=2): {len(quarterly)}")
    print()
    for q in sorted(quarterly, key=lambda x: x["publishDate"]):
        print(f"  {q['disclosureIndex']:>10}  [{q['publishDate']}]  {q['summary'][:80]}")
