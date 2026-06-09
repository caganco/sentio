"""Full parse of all 3 KAP disclosure PDFs for RR-Y1-011-C."""
import io
import re
import struct
import requests
import pdfplumber
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe"
SCRATCH.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.kap.org.tr"

DISC_INFO = [
    (1574461, "2026-03-19", "2026-04-01"),
    (1528220, "2025-12-19", "2026-01-01"),
    (1450711, "2025-06-20", "2025-07-01"),
]


def get_attachment_ids(disc_id):
    """Extract all attachment objIds and filenames from disclosure page."""
    url = f"{BASE}/tr/Bildirim/{disc_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    # Find all objId patterns (hex UUID-like strings after 'file/download/')
    obj_ids = re.findall(r'(?:file/download/|"objId"\s*:\s*")([0-9a-f]{32})', r.text)
    file_names = re.findall(r'"fileName"\s*:\s*"([^"]+)"', r.text)
    # Also find from href
    href_ids = re.findall(r'/tr/api/file/download/([0-9a-f]{32})', r.text)
    all_ids = list(dict.fromkeys(obj_ids + href_ids))  # dedup preserve order
    return all_ids, file_names, r.text


def extract_from_java_serialized(data: bytes) -> bytes:
    """Strip Java object serialization wrapper to get raw bytes."""
    if data[:2] != b'\xac\xed':
        return data
    idx = data.find(b'%PDF')
    if idx >= 0:
        return data[idx:]
    # Generic: skip Java header (magic + array descriptor) and read length
    try:
        # Header is ~23 bytes before the 4-byte array length
        hdr = 23
        arr_len = struct.unpack(">I", data[hdr:hdr+4])[0]
        return data[hdr+4:hdr+4+arr_len]
    except Exception:
        return data


def parse_pdf_tables(pdf_bytes: bytes, disc_id: int, filename: str) -> list:
    """Extract IN/OUT + tier tables from PDF."""
    results = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        print(f"  Pages: {len(pdf.pages)}")
        for pi, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            text = page.extract_text() or ""
            # Detect period from text
            period_m = re.search(r'(\d{2}\.\d{2}\.\d{4})[- ]+(\d{2}\.\d{2}\.\d{4})', text)
            period = period_m.group(0) if period_m else ""
            # Also try YYYY format
            period_m2 = re.search(r'(APRIL|OCAK|NISAN|TEMMUZ|EKIM|JANUARY|JULY|OCTOBER)[^0-9]*(\d{4})', text, re.I)

            print(f"\n  Page {pi+1}: {len(tables)} tables | period: {period}")

            # Each table: ALINACAK/STOCKS_TO_INCLUDED | CIKARILACAK/EXCLUDED | YEDEK/SUBSTITUTE
            # Find what index section each table belongs to
            # Split text into index sections
            index_sections = re.split(
                r'(BIST\s+(?:30|50|100|500|LIQUID|LIKID|SUR|BANKA|LIKIT)[^\n]*)',
                text, flags=re.I
            )

            for ti, table in enumerate(tables):
                if not table:
                    continue
                # Get header row
                header = table[0] if table else []
                header_str = " | ".join(str(c or "") for c in header)
                print(f"    Table {ti+1} header: {header_str[:100]}")

                parsed_rows = []
                for row in table[1:]:
                    row_clean = [str(c or "").strip() for c in row]
                    if any(row_clean):
                        parsed_rows.append(row_clean)

                # Try to classify header as IN/OUT/SUBSTITUTE columns
                col_types = []
                for h in header:
                    hs = str(h or "").lower()
                    if any(k in hs for k in ["alinacak", "included", "eklen", "girecek"]):
                        col_types.append("IN")
                    elif any(k in hs for k in ["cikar", "excluded", "removed", "cikacak"]):
                        col_types.append("OUT")
                    elif any(k in hs for k in ["yedek", "substit", "reserve"]):
                        col_types.append("RESERVE")
                    else:
                        col_types.append("OTHER")

                results.append({
                    "page": pi+1,
                    "table": ti+1,
                    "header": header,
                    "col_types": col_types,
                    "rows": parsed_rows[:20],
                    "has_in": "IN" in col_types,
                    "has_out": "OUT" in col_types,
                })

                # Print first few rows
                for row in parsed_rows[:5]:
                    print(f"      {row}")
    return results


print("=" * 65)
print("RR-Y1-011-C: Full PDF parse for all 3 disclosures")
print("=" * 65)

summary = {}

for disc_id, ann_date, eff_date in DISC_INFO:
    print(f"\n{'='*50}")
    print(f"Disclosure {disc_id} | ann={ann_date} | eff={eff_date}")
    print("="*50)

    att_ids, file_names, html_text = get_attachment_ids(disc_id)
    print(f"  Attachment IDs: {att_ids}")
    print(f"  File names: {file_names}")

    # Also get timestamps
    ts = re.findall(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}', html_text)
    print(f"  Timestamps: {ts[:3]}")

    disc_tables = []
    for i, obj_id in enumerate(att_ids[:2]):
        fname = file_names[i] if i < len(file_names) else f"att_{i}.bin"
        dest = SCRATCH / f"kap_{disc_id}_{obj_id[:12]}.pdf"

        if dest.exists() and dest.stat().st_size > 10000:
            raw = dest.read_bytes()
            print(f"\n  Using cached: {dest.name}")
        else:
            url = f"{BASE}/tr/api/file/download/{obj_id}"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            raw = resp.content
            pdf_data = extract_from_java_serialized(raw)
            dest.write_bytes(pdf_data)
            raw = pdf_data
            print(f"\n  Downloaded: {fname} ({len(raw):,} bytes)")

        # Check if it's a PDF
        actual = extract_from_java_serialized(raw) if raw[:2] == b'\xac\xed' else raw
        if actual[:4] != b'%PDF':
            print(f"  Not a PDF: {actual[:8]}")
            continue

        print(f"\n  Parsing PDF: {fname}")
        try:
            tables = parse_pdf_tables(actual, disc_id, fname)
            disc_tables.extend(tables)
        except Exception as e:
            print(f"  Error parsing: {e}")

    # Count IN/OUT tables
    in_tables = [t for t in disc_tables if t["has_in"]]
    out_tables = [t for t in disc_tables if t["has_out"]]
    print(f"\n  Summary: {len(in_tables)} IN tables, {len(out_tables)} OUT tables")
    summary[disc_id] = {
        "ann_date": ann_date,
        "eff_date": eff_date,
        "timestamps": ts[:3],
        "attachment_count": len(att_ids),
        "tables_with_in": len(in_tables),
        "tables_with_out": len(out_tables),
    }

print("\n\n=== FINAL SUMMARY ===")
for disc_id, info in summary.items():
    print(f"\nDisclosure {disc_id}:")
    for k, v in info.items():
        print(f"  {k}: {v}")
