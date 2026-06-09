"""Extract real attachment URLs from KAP disclosure."""
import re, requests
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.kap.org.tr"

DISC_ID = 1574461
url = f"{BASE}/tr/Bildirim/{DISC_ID}"
r = requests.get(url, headers=HEADERS, timeout=30)
html = r.text

# Find the raw attachment block from the previous probe output
# We know objId = 4028328d9cc9d32c019d05d3d7df11b5 and 4028328d9cc9d32c019d05d3d7fd11b6
obj_ids = re.findall(r'4028328d[a-f0-9]+', html)
print("ObjIds found:", obj_ids[:10])

# Find fileName context
for m in re.finditer(r'fileName[^,\}]{0,120}', html):
    print("  fileName ctx:", m.group()[:100])

# Also check the /tr/api/notification/attachments/{id} endpoint
att_url = f"{BASE}/tr/api/notification/attachments/{DISC_ID}"
att_r = requests.get(att_url, headers=HEADERS, timeout=30)
print(f"\nAttachments API: HTTP {att_r.status_code}")
if att_r.status_code == 200:
    print("  Content:", att_r.text[:500])

# Try the direct file download with the known obj IDs
known_ids = [
    "4028328d9cc9d32c019d05d3d7df11b5",
    "4028328d9cc9d32c019d05d3d7fd11b6",
]
for obj in known_ids:
    dl_url = f"{BASE}/tr/api/file/download/{obj}"
    rr = requests.get(dl_url, headers=HEADERS, timeout=30)
    ct = rr.headers.get("Content-Type", "")
    cd = rr.headers.get("Content-Disposition", "")
    print(f"\n{obj[:20]}...")
    print(f"  HTTP {rr.status_code} | CT={ct[:60]} | CD={cd[:80]}")
    print(f"  Size: {len(rr.content):,} bytes")
    print(f"  First 16 bytes: {rr.content[:16]}")
    # Save to inspect
    ext = ".pdf" if "pdf" in ct.lower() or b"%PDF" == rr.content[:4] else ".bin"
    if "excel" in ct.lower() or b"PK" == rr.content[:2]:
        ext = ".xlsx"
    dest = SCRATCH / f"kap_{DISC_ID}_att_{obj[:12]}{ext}"
    dest.write_bytes(rr.content)
    print(f"  Saved: {dest.name}")
