"""Fetch all BIST Pay Endeksleri quarterly disclosure IDs via byCriteria API.

Uses quarterly splits to avoid the 2000-record API limit.
"""
import json
import time
import requests
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
BASE = "https://www.kap.org.tr"
BIST_OID = "4028e4a14bcf2a06014be4d7e6e256b6"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe" / "recon_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()

all_records = []
seen_ids = set()

# Query quarterly: Dec 2017 (Q1-2018 announcement) through Mar 2026
QUARTERS = [
    # (label, fromDate, toDate)
    ("2017Q4", "2017-10-01", "2017-12-31"),  # Q1-2018 ann in Dec 2017
    ("2018Q1", "2018-01-01", "2018-03-31"),
    ("2018Q2", "2018-04-01", "2018-06-30"),
    ("2018Q3", "2018-07-01", "2018-09-30"),
    ("2018Q4", "2018-10-01", "2018-12-31"),  # Q1-2019 ann in Dec 2018
    ("2019Q1", "2019-01-01", "2019-03-31"),  # Q2-2019 ann in Mar 2019
    ("2019Q2", "2019-04-01", "2019-06-30"),  # Q3-2019 ann in Jun 2019
    ("2019Q3", "2019-07-01", "2019-09-30"),  # Q4-2019 ann in Sep 2019
    ("2019Q4", "2019-10-01", "2019-12-31"),  # Q1-2020 ann in Dec 2019
    ("2020Q1", "2020-01-01", "2020-03-31"),  # Q2-2020 ann in Mar 2020
    ("2020Q2", "2020-04-01", "2020-06-30"),
    ("2020Q3", "2020-07-01", "2020-09-30"),
    ("2020Q4", "2020-10-01", "2020-12-31"),
    ("2021Q1", "2021-01-01", "2021-03-31"),
    ("2021Q2", "2021-04-01", "2021-06-30"),
    ("2021Q3", "2021-07-01", "2021-09-30"),
    ("2021Q4", "2021-10-01", "2021-12-31"),
    ("2022Q1", "2022-01-01", "2022-03-31"),
    ("2022Q2", "2022-04-01", "2022-06-30"),
    ("2022Q3", "2022-07-01", "2022-09-30"),
    ("2022Q4", "2022-10-01", "2022-12-31"),
    ("2023Q1", "2023-01-01", "2023-03-31"),
    ("2023Q2", "2023-04-01", "2023-06-30"),
    ("2023Q3", "2023-07-01", "2023-09-30"),
    ("2023Q4", "2023-10-01", "2023-12-31"),
    ("2024Q1", "2024-01-01", "2024-03-31"),
    ("2024Q2", "2024-04-01", "2024-06-30"),
    ("2024Q3", "2024-07-01", "2024-09-30"),
    ("2024Q4", "2024-10-01", "2024-12-31"),
    ("2025Q1", "2025-01-01", "2025-03-31"),
    ("2025Q2", "2025-04-01", "2025-06-30"),
    ("2025Q3", "2025-07-01", "2025-09-30"),
    ("2025Q4", "2025-10-01", "2025-12-31"),
    ("2026Q1", "2026-01-01", "2026-03-31"),
]

for label, from_date, to_date in QUARTERS:
    cache_file = CACHE_DIR / f"byCriteria_q_{label}.json"

    if cache_file.exists():
        records = json.loads(cache_file.read_bytes())
        print(f"{label}: {len(records):4d} records (cached)")
    else:
        data = {
            "fromDate": from_date,
            "toDate": to_date,
            "disclosureClass": "",
            "subjectList": [],
            "mkkMemberOidList": [BIST_OID],
            "inactiveMkkMemberOidList": [],
            "bdkMemberOidList": [],
            "fromSrc": False,
            "disclosureIndexList": [],
        }
        r = session.post(
            f"{BASE}/tr/api/disclosure/members/byCriteria",
            headers=HEADERS, json=data, timeout=30
        )
        if r.status_code != 200:
            print(f"{label}: ERROR status={r.status_code}")
            time.sleep(3)
            continue

        records = r.json()
        print(f"{label}: {len(records):4d} records (fetched)")
        if len(records) == 2000:
            print(f"  *** WARNING: {label} hit 2000-record limit, may be truncated!")
        cache_file.write_bytes(r.content)
        time.sleep(0.8)

    for rec in records:
        disc_id = rec.get("disclosureIndex")
        if disc_id and disc_id not in seen_ids:
            seen_ids.add(disc_id)
            all_records.append(rec)

print(f"\nTotal unique records: {len(all_records)}")

# Filter: BIST Pay Endeksleri + comprehensive summary mentioning BIST 30/50/100
# The quarterly main-index changes have summaries with "BIST 30, BIST 50, BIST 100"
quarterly = [
    r for r in all_records
    if r.get("subject") == "BIST Pay Endeksleri"
    and r.get("attachmentCount") == 2
    and ("BIST 30" in r.get("summary", "") or "Dönemsel" in r.get("summary", ""))
]

# Further filter: exclude specialty-index-only announcements
# Main quarterly has BIST 100 in summary
main_quarterly = [
    r for r in quarterly
    if "BIST 100" in r.get("summary", "") or
    ("BIST 30" in r.get("summary", "") and "BIST 50" in r.get("summary", ""))
]

print(f"\nAll quarterly BIST Pay Endeksleri (att=2, BIST30/100): {len(main_quarterly)}")
print()
for q in sorted(main_quarterly, key=lambda x: x["publishDate"]):
    print(f"  {q['disclosureIndex']:>10}  [{q['publishDate']}]  {q['summary'][:90]}")

# Save
out_file = CACHE_DIR / "quarterly_disc_ids_v2.json"
out_file.write_bytes(
    json.dumps(main_quarterly, indent=2, ensure_ascii=False).encode("utf-8")
)
print(f"\nSaved: {out_file}")
