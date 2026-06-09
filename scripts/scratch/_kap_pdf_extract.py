"""Extract actual PDF from Java-serialized byte array wrapper from KAP."""
import struct
import requests
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.kap.org.tr"

ATT_INFO = [
    ("4028328d9cc9d32c019d05d3d7df11b5", "2026_2_TR.pdf", 1574461),
    ("4028328d9cc9d32c019d05d3d7fd11b6", "2026_2_EN.pdf", 1574461),
]

# Additional disclosures - need to find their attachment IDs
DISC_IDS_EXTRA = [1528220, 1450711]


def extract_java_byte_array(data: bytes) -> bytes:
    """Strip Java serialization header to get raw bytes.

    Java ObjectOutputStream byte array format:
      AC ED 00 05           - magic + version
      75                    - TC_ARRAY
      72                    - TC_CLASSDESC
      00 02 5B 42           - class name len=2, "[B"
      AC F3 17 F8 06 08 54 E0  - serialVersionUID (8 bytes)
      02                    - SC_SERIALIZABLE flag
      00 00                 - field count = 0
      78                    - TC_ENDBLOCKDATA
      70                    - TC_NULL (no superclass)
      00 00 XX XX           - array length (4 bytes big-endian)
      [actual bytes...]
    """
    # Check magic
    if data[:2] != b'\xac\xed':
        print("  Not Java serialized, returning as-is")
        return data

    # Find the actual content - look for %PDF signature
    pdf_start = data.find(b'%PDF')
    if pdf_start >= 0:
        print(f"  Found %PDF at offset {pdf_start}")
        return data[pdf_start:]

    # Manual parse: skip to after TC_NULL (70) and read array length
    # Header: AC ED 00 05 75 72 00 02 5B 42 + 8 byte UID + 02 00 00 78 70
    # That's: 2+2+1+1+2+2+8+1+2+1+1 = 23 bytes before array length
    # Actually let me just scan for the length field
    try:
        # After fixed header portion, there should be a 4-byte length
        # Try to find it by looking at known format
        header_len = 4 + 1 + 1 + 4 + 8 + 1 + 2 + 1 + 1  # = 23
        arr_len = struct.unpack(">I", data[header_len:header_len+4])[0]
        print(f"  Java byte array length: {arr_len:,}")
        content = data[header_len+4:header_len+4+arr_len]
        print(f"  Extracted {len(content):,} bytes, first 4: {content[:4]}")
        return content
    except Exception as e:
        print(f"  Parse error: {e}")
        return data


def get_disc_attachments(disc_id):
    """Get attachment obj IDs for a disclosure."""
    import re
    url = f"{BASE}/tr/Bildirim/{disc_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    obj_ids = re.findall(r'4028328d[a-f0-9]+', r.text)
    file_names = re.findall(r'"fileName"\s*:\s*"([^"]+)"', r.text)
    return list(zip(obj_ids[:len(file_names)], file_names))


def download_and_extract(obj_id, filename, disc_id):
    url = f"{BASE}/tr/api/file/download/{obj_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    raw = r.content
    print(f"\n  {filename}: {len(raw):,} bytes, starts {raw[:4]}")
    actual = extract_java_byte_array(raw)
    dest = SCRATCH / f"kap_{disc_id}_{filename}"
    dest.write_bytes(actual)
    print(f"  Saved: {dest.name} ({len(actual):,} bytes), starts {actual[:4]}")
    return dest, actual


print("=== Disclosure 1574461 ===")
for obj_id, fname, disc_id in ATT_INFO:
    dest, content = download_and_extract(obj_id, fname, disc_id)
    if content[:4] == b"%PDF":
        print(f"  Valid PDF!")
        # Try to read text with pdfplumber
        try:
            import io
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                print(f"  Pages: {len(pdf.pages)}")
                for i, page in enumerate(pdf.pages[:3]):
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    print(f"\n  --- Page {i+1} text (first 400 chars) ---")
                    print(f"  {text[:400]}")
                    if tables:
                        print(f"\n  Tables on page {i+1}: {len(tables)}")
                        for j, t in enumerate(tables[:1]):
                            print(f"  Table {j+1} ({len(t)} rows x {max(len(r) for r in t if r)} cols):")
                            for row in t[:8]:
                                print(f"    {row}")
        except ImportError:
            print("  pdfplumber not installed")
            # Try raw text extraction
            import re
            text = content.decode("latin-1", errors="replace")
            # Find Turkish strings
            hits = re.findall(r'[A-ZÇĞİÖŞÜa-zçğışöü]{3,}', text)
            print(f"  Raw text hits (first 20): {hits[:20]}")

# Check other disclosures
print("\n=== Checking other disclosures ===")
for disc_id in DISC_IDS_EXTRA:
    print(f"\nDisclosure {disc_id}:")
    atts = get_disc_attachments(disc_id)
    print(f"  Attachments: {atts}")
