"""Download KAP disclosure attachments and inspect content."""
import json
import re
import requests
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[2] / "data" / "bist_datastore_archive" / "kap_index_probe"
SCRATCH.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

BASE = "https://www.kap.org.tr"
DISCLOSURES = [
    (1574461, "2026-04-01"),
    (1528220, "2026-01-01"),
    (1450711, "2025-07-01"),
]


def get_attachments(disc_id):
    """Extract attachment objIds from disclosure HTML page."""
    url = f"{BASE}/tr/Bildirim/{disc_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"  ERROR: HTTP {r.status_code}")
        return []

    # Extract attachments JSON from Next.js __NEXT_DATA__ or inline
    att_pattern = re.compile(
        r'"attachments"\s*:\s*\[(\{[^\]]+\})\]',
        re.DOTALL
    )
    # Try finding objId directly
    obj_ids = re.findall(r'"objId"\s*:\s*"([a-f0-9]+)"', r.text)
    file_names = re.findall(r'"fileName"\s*:\s*"([^"]+)"', r.text)

    attachments = list(zip(obj_ids, file_names))
    return attachments, r.text


def download_attachment(obj_id, filename_hint, disc_id):
    """Download attachment by objId."""
    url = f"{BASE}/tr/api/file/download/{obj_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    ct = r.headers.get("Content-Type", "")

    # Determine extension
    ext = ".bin"
    if "pdf" in ct.lower() or filename_hint.lower().endswith(".pdf"):
        ext = ".pdf"
    elif "excel" in ct.lower() or "spreadsheet" in ct.lower() or filename_hint.lower().endswith((".xlsx", ".xls")):
        ext = ".xlsx"
    elif filename_hint:
        suf = Path(filename_hint).suffix
        if suf:
            ext = suf

    dest = SCRATCH / f"kap_{disc_id}_att_{obj_id[:12]}{ext}"
    dest.write_bytes(r.content)
    print(f"  Downloaded: {dest.name} ({len(r.content):,} bytes) CT={ct[:50]}")
    return dest, ct, r.content


def inspect_pdf(content, filename):
    """Try to extract text from PDF using available tools."""
    # Check if it's really a PDF
    if not content[:4] == b"%PDF":
        print(f"  NOT a PDF (starts with {content[:8]})")
        return None

    print(f"  Confirmed PDF ({len(content):,} bytes)")

    # Try pdfplumber
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            print(f"  Pages: {len(pdf.pages)}")
            all_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                all_text.append(f"--- PAGE {i+1} ---\n{text}")
                if tables:
                    print(f"  Page {i+1}: {len(tables)} table(s)")
                    for j, t in enumerate(tables[:2]):
                        print(f"    Table {j+1} ({len(t)} rows):")
                        for row in t[:5]:
                            print(f"      {row}")
            return "\n".join(all_text)
    except ImportError:
        print("  pdfplumber not available")

    # Try PyPDF2
    try:
        import io
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        print(f"  Pages (PyPDF2): {len(reader.pages)}")
        texts = []
        for p in reader.pages:
            texts.append(p.extract_text() or "")
        return "\n".join(texts)
    except ImportError:
        print("  PyPDF2 not available")

    # Raw text extraction - look for readable strings
    import re as _re
    raw_str = content.decode("latin-1", errors="replace")
    readable = _re.findall(r'[\x20-\x7e\xc0-\xff]{8,}', raw_str)
    turkish_hits = [s for s in readable if any(c in s for c in "ğşıöüçĞŞİÖÜÇ")]
    print(f"  Raw readable strings with Turkish chars (first 10):")
    for s in turkish_hits[:10]:
        print(f"    {s[:80]}")
    return None


def inspect_xlsx(content, filename):
    """Inspect Excel attachment."""
    # Check format
    if content[:4] == b"PK\x03\x04":
        print("  Real ZIP/XLSX format")
        import pandas as pd, io
        try:
            xf = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
            print(f"  Sheets: {xf.sheet_names}")
            for sname in xf.sheet_names:
                df = pd.read_excel(xf, sheet_name=sname, header=None, nrows=20)
                print(f"  Sheet '{sname}' ({df.shape}):")
                print(df.to_string(max_rows=15, max_cols=8))
        except Exception as e:
            print(f"  Error: {e}")
    elif content[:4] == b"<htm" or content[:5] == b"<html":
        print("  HTML-as-Excel")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content.decode("utf-8", errors="replace"), "html.parser")
        tables = soup.find_all("table")
        print(f"  Tables: {len(tables)}")
        for i, t in enumerate(tables[:3]):
            rows = [[td.get_text(strip=True) for td in row.find_all(["td","th"])] for row in t.find_all("tr")]
            rows = [r for r in rows if any(r)]
            print(f"  Table {i+1} ({len(rows)} rows):")
            for row in rows[:8]:
                print(f"    {row[:5]}")
    else:
        print(f"  Unknown format: {content[:8]}")


for disc_id, efektif in DISCLOSURES:
    print(f"\n{'='*60}")
    print(f"Disclosure {disc_id} (efektif {efektif})")
    print("="*60)

    atts, html_text = get_attachments(disc_id)
    print(f"  Attachments found: {len(atts)}")
    for obj_id, fname in atts:
        print(f"    objId={obj_id[:16]}... name={fname}")

    for obj_id, fname in atts[:3]:
        print(f"\n  Downloading: {fname}")
        dest, ct, content = download_attachment(obj_id, fname, disc_id)

        if dest.suffix == ".pdf":
            inspect_pdf(content, fname)
        elif dest.suffix in (".xlsx", ".xls"):
            inspect_xlsx(content, fname)
        elif content[:5] == b"<html" or content[:4] == b"<htm":
            print("  HTML content, trying table parse...")
            inspect_xlsx(content, fname)
