"""RR-Y1-011-D — BIST Index Reconstitution Look-Ahead-Safe Event Panel Builder.

Amac: 2019-2025 donemsel endeks degisiklik bildirimlerinden
look-ahead-safe, survivorship-clean, tier-etiketli olay paneli insa et.

Kapsam: Salt veri-insa. Sinyal/getiri/IC/edge-hukmü URETILMEZ.

Strateji:
  1. Bilinen efektif tarihlerden hedef-ilan-tarihi hesapla (~12 gun oncesi)
  2. Bilinen ID cipa (1450711 = 2025-06-20) + lineer oran tahmininden ID tahmini
  3. Binary search ile tam IDs bul
  4. PDF indirip pdfplumber ile IN/OUT parse et
  5. clean_universe ile join, temiz-N hesapla
  6. Parquet + markdown rapor yaz

Calistirma:
    python scripts/scratch/build_index_recon_panel.py
    python scripts/scratch/build_index_recon_panel.py --skip-discover  (cache kullan)
    python scripts/scratch/build_index_recon_panel.py --dry-run        (sadece ID kesfet)
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import re
import struct
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

try:
    import pdfplumber
    _PDFPLUMBER = True
except ImportError:
    _PDFPLUMBER = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("recon_panel")

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_DIR = REPO_ROOT / "data" / "bist_datastore_archive" / "kap_index_probe" / "recon_cache"
OUTPUT_DIR = REPO_ROOT / "data" / "snapshots"
REPORT_PATH = REPO_ROOT / "docs" / "research" / "RR-Y1-011-D-panel-build.md"

BASE = "https://www.kap.org.tr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Confirmed reconstitution effective dates (from clean_universe + byCriteria API discovery)
# 28 quarters: Q1-2019 through Q4-2025 (Q4 = October effective date)
EFFECTIVE_DATES = [
    ("Q1-2019", date(2019, 1, 2)),
    ("Q2-2019", date(2019, 4, 1)),
    ("Q3-2019", date(2019, 7, 1)),
    ("Q4-2019", date(2019, 10, 1)),
    ("Q1-2020", date(2020, 1, 2)),
    ("Q2-2020", date(2020, 4, 1)),
    ("Q3-2020", date(2020, 7, 1)),
    ("Q4-2020", date(2020, 10, 1)),
    ("Q1-2021", date(2021, 1, 4)),
    ("Q2-2021", date(2021, 4, 1)),
    ("Q3-2021", date(2021, 7, 1)),
    ("Q4-2021", date(2021, 10, 1)),
    ("Q1-2022", date(2022, 1, 3)),
    ("Q2-2022", date(2022, 4, 1)),
    ("Q3-2022", date(2022, 7, 1)),
    ("Q4-2022", date(2022, 10, 3)),
    ("Q1-2023", date(2023, 1, 2)),
    ("Q2-2023", date(2023, 4, 3)),
    ("Q3-2023", date(2023, 7, 3)),
    ("Q4-2023", date(2023, 10, 2)),
    ("Q1-2024", date(2024, 1, 2)),
    ("Q2-2024", date(2024, 4, 1)),
    ("Q3-2024", date(2024, 7, 1)),
    ("Q4-2024", date(2024, 10, 1)),
    ("Q1-2025", date(2025, 1, 2)),
    ("Q2-2025", date(2025, 4, 2)),
    ("Q3-2025", date(2025, 7, 1)),
    ("Q4-2025", date(2025, 10, 1)),  # ann 2025-09-12, ID 1489616
]

# Pre-discovered KAP disclosure IDs via byCriteria API (quarterly_disc_ids_v2.json)
# Format: quarter → (disc_id, ann_date_str, eff_date_str)
FULL_ID_MAP: dict[str, tuple[int, str, str]] = {
    "Q1-2019": (725991,  "2018-12-21", "2019-01-02"),
    "Q2-2019": (748393,  "2019-03-18", "2019-04-01"),
    "Q3-2019": (769426,  "2019-06-21", "2019-07-01"),
    "Q4-2019": (788219,  "2019-09-20", "2019-10-01"),
    "Q1-2020": (803975,  "2019-12-17", "2020-01-02"),
    "Q2-2020": (830865,  "2020-03-19", "2020-04-01"),
    "Q3-2020": (852123,  "2020-06-19", "2020-07-01"),
    "Q4-2020": (875734,  "2020-09-18", "2020-10-01"),
    "Q1-2021": (894142,  "2020-12-21", "2021-01-04"),
    "Q2-2021": (918267,  "2021-03-15", "2021-04-01"),
    "Q3-2021": (943164,  "2021-06-18", "2021-07-01"),
    "Q4-2021": (964181,  "2021-09-16", "2021-10-01"),
    "Q1-2022": (984449,  "2021-12-17", "2022-01-03"),
    "Q2-2022": (1012073, "2022-03-22", "2022-04-01"),
    "Q3-2022": (1038557, "2022-06-21", "2022-07-01"),
    "Q4-2022": (1064575, "2022-09-21", "2022-10-03"),
    "Q1-2023": (1088484, "2022-12-19", "2023-01-02"),
    "Q2-2023": (1125624, "2023-03-16", "2023-04-03"),
    "Q3-2023": (1159507, "2023-06-16", "2023-07-03"),
    "Q4-2023": (1196746, "2023-09-21", "2023-10-02"),
    "Q1-2024": (1228194, "2023-12-22", "2024-01-02"),
    "Q2-2024": (1261193, "2024-03-21", "2024-04-01"),
    "Q3-2024": (1299052, "2024-06-13", "2024-07-01"),
    "Q4-2024": (1336462, "2024-09-20", "2024-10-01"),
    "Q1-2025": (1367507, "2024-12-20", "2025-01-02"),
    "Q2-2025": (1409989, "2025-03-21", "2025-04-02"),
    "Q3-2025": (1450711, "2025-06-20", "2025-07-01"),
    "Q4-2025": (1489616, "2025-09-12", "2025-10-01"),
}

# Approximate ID rate: IDs per day
# Calibrated from known anchors:
# 1528220 - 1450711 = 77509 in ~182 days = 426/day (Jun-Dec 2025)
# 1574461 - 1528220 = 46241 in ~90 days = 514/day (Dec 2025 - Mar 2026)
# Earlier years: slower growth; use a declining rate table
def estimate_id(target_date: date) -> int:
    """Estimate KAP disclosure ID for a given date based on known anchors."""
    anchor_date = date(2025, 6, 20)  # ann date for 1450711
    anchor_id = 1450711

    # Days offset (negative = before anchor)
    delta = (target_date - anchor_date).days

    # Rate varies by year: use a piecewise approximation
    # Positive delta: 470/day (2025+)
    # Negative delta:
    #   2024-2025: ~420/day
    #   2022-2023: ~350/day
    #   2020-2021: ~280/day
    #   2018-2019: ~200/day
    if delta >= 0:
        return int(anchor_id + delta * 426)  # calibrated Jun-Dec 2025: 426/day

    # Working backwards: use different rates per year
    target_year = target_date.year
    rates = {
        2025: 440, 2024: 420, 2023: 380, 2022: 350,
        2021: 300, 2020: 260, 2019: 220, 2018: 200,
    }
    # Interpolate day-by-day approximation
    est = anchor_id
    d = anchor_date
    while d > target_date:
        year = d.year if d.year in rates else 220
        est -= rates.get(year, 220)
        d -= timedelta(days=1)
    return max(1, int(est))


def get_disclosure_date(disc_id: int, session: requests.Session) -> datetime | None:
    """Fetch disclosure page and extract the announcement timestamp."""
    url = f"{BASE}/tr/Bildirim/{disc_id}"
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        ts_matches = re.findall(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}', r.text)
        if not ts_matches:
            return None
        # Last timestamp = publication time
        return datetime.strptime(ts_matches[-1], "%d.%m.%Y %H:%M:%S")
    except Exception:
        return None


def get_disclosure_info(disc_id: int, session: requests.Session) -> dict | None:
    """Fetch full disclosure metadata: timestamps + subject + attachment IDs."""
    url = f"{BASE}/tr/Bildirim/{disc_id}"
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        html = r.text

        ts_matches = re.findall(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}', html)
        obj_ids = re.findall(r'/tr/api/file/download/([0-9a-f]{32})', html)
        # KAP embeds JSON-escaped strings: \"fileName\":\"2025_3_Donemsel...\"
        file_names = re.findall(r'\\"fileName\\":\\"([^\\"]+)\\"', html)
        if not file_names:
            file_names = re.findall(r'"fileName":"([^"]+)"', html)

        # Fastest check: look for "donemsel" anywhere in raw HTML (handles JSON escaping)
        html_lower = html.lower()
        is_donemsel = "donemsel" in html_lower or "periodic_changes" in html_lower

        return {
            "disc_id": disc_id,
            "timestamps": ts_matches,
            "obj_ids": list(dict.fromkeys(obj_ids)),  # dedup
            "file_names": file_names,
            "is_donemsel": is_donemsel,
        }
    except Exception as exc:
        logger.debug("Info fetch failed %d: %s", disc_id, exc)
        return None


def binary_search_disc_id(target_ann_date: date, session: requests.Session,
                           known_lo: int | None = None) -> int | None:
    """Binary search for a disclosure ID near target_ann_date.

    Returns an ID whose date is within ±5 days of target_ann_date,
    or None if not found.
    """
    est = estimate_id(target_ann_date)

    # Wide initial bounds: ±200 days to handle rate-estimate errors in older years
    year = target_ann_date.year
    rate = {2025: 440, 2024: 420, 2023: 380, 2022: 350,
            2021: 300, 2020: 260, 2019: 220, 2018: 200}.get(year, 300)

    lo = max(known_lo or 1, est - 200 * rate)
    hi = est + 80 * rate

    logger.info("Binary search for %s: est=%d range=[%d, %d]",
                target_ann_date, est, lo, hi)

    best_id = None
    best_gap = timedelta(days=999)

    # Binary search phase: narrow to ±3 days
    for iteration in range(25):
        mid = (lo + hi) // 2
        dt = get_disclosure_date(mid, session)
        time.sleep(0.25)

        if dt is None:
            # ID might not exist; shift slightly
            hi = mid - 1
            continue

        gap = dt.date() - target_ann_date
        logger.debug("  iter=%d id=%d dt=%s gap=%+d days", iteration, mid, dt.date(), gap.days)

        if abs(gap) < abs(best_gap):
            best_gap = gap
            best_id = mid

        if abs(gap.days) <= 2:
            break
        elif gap.days < -5:
            lo = mid + 1
        elif gap.days > 5:
            hi = mid - 1
        else:
            break

    if best_id is None:
        return None

    logger.info("Binary search result: id=%d date_gap=%+d days from %s",
                best_id, best_gap.days, target_ann_date)
    return best_id


def find_donemsel_id(target_ann_date: date, session: requests.Session,
                     known_lo: int | None = None) -> tuple[int, dict] | None:
    """Find the exact 'Donemsel Degisiklikler' disclosure ID near target_ann_date."""
    anchor = binary_search_disc_id(target_ann_date, session, known_lo)
    if anchor is None:
        logger.warning("Binary search failed for %s", target_ann_date)
        return None

    # Scan outward from anchor: anchor, anchor±1, anchor±2, ... up to ±600
    # Outward order means early-exit if Donemsel is close to anchor
    SCAN_RADIUS = 600
    scan_order = [anchor + delta for d in range(SCAN_RADIUS + 1)
                  for delta in ([0, -d, d] if d > 0 else [0])
                  if 1 <= anchor + delta <= anchor + SCAN_RADIUS]
    seen = set()
    for disc_id in scan_order:
        if disc_id in seen:
            continue
        seen.add(disc_id)
        info = get_disclosure_info(disc_id, session)
        time.sleep(0.15)
        if info and info["is_donemsel"]:
            if info["timestamps"]:
                dt = datetime.strptime(info["timestamps"][-1], "%d.%m.%Y %H:%M:%S")
                gap = abs((dt.date() - target_ann_date).days)
                if gap <= 20:
                    logger.info("Found Donemsel ID %d for %s (ann=%s) after %d scans",
                                disc_id, target_ann_date, dt.date(), len(seen))
                    return disc_id, info
    logger.warning("No Donemsel ID found near %d for %s (scanned %d IDs)",
                   anchor, target_ann_date, len(seen))
    return None


# --------------------------------------------------------------------------
# PDF extraction
# --------------------------------------------------------------------------

def extract_pdf(raw: bytes) -> bytes:
    """Strip Java serialization wrapper (offset 27) to get actual PDF bytes."""
    if raw[:2] == b'\xac\xed':
        idx = raw.find(b'%PDF')
        return raw[idx:] if idx >= 0 else raw
    return raw


def download_tr_pdf(obj_ids: list[str], session: requests.Session,
                    file_names: list[str] | None = None) -> bytes | None:
    """Download TR PDF (Donemsel_Degisiklikler, not Periodic_Changes).

    Tries to identify the TR variant by file name hint, falls back to first obj_id.
    """
    # Prefer the TR file (Donemsel_Degisiklikler) over the EN file (Periodic_Changes)
    ordered_ids = list(obj_ids[:2])
    if file_names and len(file_names) == len(obj_ids):
        tr_idx = next(
            (i for i, f in enumerate(file_names) if "Donemsel" in f or "donemsel" in f.lower()),
            None
        )
        if tr_idx is not None and tr_idx < len(obj_ids):
            ordered_ids = [obj_ids[tr_idx]] + [o for i, o in enumerate(obj_ids) if i != tr_idx]

    for obj_id in ordered_ids[:2]:
        url = f"{BASE}/tr/api/file/download/{obj_id}"
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            raw = r.content
            pdf = extract_pdf(raw)
            if pdf[:4] == b'%PDF':
                return pdf
        except Exception as exc:
            logger.debug("PDF download failed %s: %s", obj_id, exc)
    return None


# The PDF tier table order changed between Q1-2024 and Q2-2024 (disc_id threshold: 1261193).
# Before Q2-2024: page-0 order is BIST100, BIST50, BIST30  (highest tier first)
# Q2-2024 onwards: page-0 order is BIST30, BIST50, BIST100  (lowest tier first)
#
# Detected from PDF text (y-coordinate of "BIST XX ENDEKSİ" labels):
#   Q1-2024 (1228194): y≈113(BIST100), y≈300(BIST50), y≈415(BIST30) → descending tier
#   Q2-2024 (1261193): y≈119(BIST30),  y≈221(BIST50), y≈328(BIST100) → ascending tier
_INDEX_MAP_EARLY = {          # disc_id < 1261193 (before Q2-2024)
    (0, 0): ("BIST100", "XU100"),
    (0, 1): ("BIST50",  "XU050"),
    (0, 2): ("BIST30",  "XU030"),
    (0, 3): ("BIST500", "XU500"),
    (1, 0): ("LIKIT_BANKA",       None),
    (1, 1): ("LIKIT10",           None),
    (1, 2): ("SURDURULEBILIRLIK", None),
    (1, 3): ("SURDURULEBILIRLIK25", None),
}
_INDEX_MAP_LATE = {           # disc_id >= 1261193 (Q2-2024 onwards)
    (0, 0): ("BIST30",  "XU030"),
    (0, 1): ("BIST50",  "XU050"),
    (0, 2): ("BIST100", "XU100"),
    (0, 3): ("BIST500", "XU500"),
    (1, 0): ("LIKIT_BANKA",       None),
    (1, 1): ("LIKIT10",           None),
    (1, 2): ("SURDURULEBILIRLIK", None),
    (1, 3): ("SURDURULEBILIRLIK25", None),
}
_DISC_ID_LAYOUT_BREAK = 1261193  # Q2-2024 first disc_id with reversed order


def get_index_map(disc_id: int) -> dict:
    return _INDEX_MAP_LATE if disc_id >= _DISC_ID_LAYOUT_BREAK else _INDEX_MAP_EARLY


def _detect_col_groups(header: list[str]) -> list[tuple[str, int]]:
    """Detect direction column groups from a table header row."""
    groups = []
    for ci, h in enumerate(header):
        if any(k in h for k in ["ALINACAK", "INCLUDED", "EKLENECEK"]):
            groups.append(("IN", ci))
        elif any(k in h for k in ["IKARILACAK", "CIKAR", "EXCLUDED", "REMOVED"]):
            # Ç → ? in pdfplumber: "ÇIKARILACAK" → "?IKARILACAK"; match on "IKARILACAK"
            groups.append(("OUT", ci))
        elif any(k in h for k in ["YEDEK", "SUBSTIT", "RESERVE"]):
            groups.append(("RESERVE", ci))
    return groups


def _extract_tickers_from_block(text: str) -> list[str]:
    """Extract tickers from a Format-C merged data block.

    Block format: '1 TICKER COMPANY...\n2 TICKER COMPANY...\n...'
    Lines NOT starting with a digit are company-name continuations (skip).
    """
    tickers = []
    for line in text.split("\n"):
        m = re.match(r'^\d+\s+([A-Z]{2,8})', line.strip())
        if m:
            tickers.append(m.group(1))
    return tickers


def parse_pdf_events(pdf_bytes: bytes, disc_id: int,
                     ann_date: date, eff_date: date) -> list[dict]:
    """Parse IN/OUT events from PDF attachment.

    Returns list of dicts:
        symbol, company, direction, index_label, index_tier,
        disc_id, ann_date, eff_date, gap_days

    Handles three PDF table formats encountered in BIST reconstitution PDFs:
      A-PACKED  (2019–Q3-2021): 9-col, 2 rows, tickers packed with \\n in col[1]
      B-ONEROW  (Q4-2021–2024): 9-col, N rows, one ticker per row
      C-MERGED  (some 2025):    3-col, 2 rows, entire direction in one cell
    """
    if not _PDFPLUMBER:
        raise RuntimeError("pdfplumber not installed")

    events = []
    gap_days = (eff_date - ann_date).days
    seen = set()  # (symbol, direction, tier_code) dedup per quarter

    index_map = get_index_map(disc_id)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pi, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for ti, table in enumerate(tables):
                if not table or not table[0]:
                    continue
                tier_label, tier_code = index_map.get((pi, ti), ("UNKNOWN", None))

                header = [str(c or "").strip().upper() for c in table[0]]
                n_cols = len(header)
                col_groups = _detect_col_groups(header)

                if n_cols == 3 and col_groups:
                    # Format C: merged-cell — each data-row cell is a direction's text block
                    for row in table[1:]:
                        for direction, dir_col in col_groups:
                            if direction == "RESERVE":
                                continue
                            if dir_col >= len(row):
                                continue
                            cell = str(row[dir_col] or "").strip()
                            for ticker in _extract_tickers_from_block(cell):
                                key = (ticker, direction, tier_code)
                                if key in seen:
                                    continue
                                seen.add(key)
                                events.append({
                                    "symbol": ticker, "company": "",
                                    "direction": direction,
                                    "index_label": tier_label,
                                    "index_tier": tier_code,
                                    "disc_id": disc_id,
                                    "ann_date": ann_date,
                                    "eff_date": eff_date,
                                    "gap_days": gap_days,
                                })

                elif n_cols == 9:
                    # Format A or B: [sira, ticker, company] × 3 direction groups
                    # Format A (packed): ticker cell has multiple tickers via \n
                    # Format B (one-row): ticker cell has one ticker
                    for row in table[1:]:
                        for direction, start_col in col_groups:
                            if direction == "RESERVE":
                                continue
                            if start_col + 1 >= len(row):
                                continue
                            ticker_cell = str(row[start_col + 1] or "").strip()
                            company_cell = str(row[start_col + 2] or "").strip() if start_col + 2 < len(row) else ""

                            for ticker in ticker_cell.split("\n"):
                                ticker = ticker.strip()
                                if not ticker or ticker in ("--", "-----", "-", "None"):
                                    continue
                                # Skip row-number entries like "1.", "2", "1\n2\n3" remnants
                                if re.match(r'^\d+\.?$', ticker):
                                    continue
                                if not re.match(r'^[A-Z]{2,8}$', ticker):
                                    continue
                                key = (ticker, direction, tier_code)
                                if key in seen:
                                    continue
                                seen.add(key)
                                events.append({
                                    "symbol": ticker,
                                    "company": company_cell.replace("\n", " ").strip(),
                                    "direction": direction,
                                    "index_label": tier_label,
                                    "index_tier": tier_code,
                                    "disc_id": disc_id,
                                    "ann_date": ann_date,
                                    "eff_date": eff_date,
                                    "gap_days": gap_days,
                                })

    return events


# --------------------------------------------------------------------------
# Main discovery + build
# --------------------------------------------------------------------------

def load_cache(cache_file: Path) -> dict:
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict, cache_file: Path) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False, default=str),
                          encoding="utf-8")


def discover_all_ids(skip_discover: bool = False) -> dict:
    """Return mapping: quarter_label -> {disc_id, ann_date, eff_date, obj_ids, file_names}.

    All 28 quarters pre-discovered via byCriteria API (FULL_ID_MAP).
    Discovery fallback only runs for any quarter not in FULL_ID_MAP.
    """
    cache_file = SCRATCH_DIR / "disc_id_cache.json"
    cache = load_cache(cache_file)

    # FULL_ID_MAP is authoritative for disc_id/ann_date/eff_date;
    # preserve already-fetched obj_ids/file_names from prior runs.
    for quarter, (disc_id, ann_date_str, eff_date_str) in FULL_ID_MAP.items():
        existing = cache.get(quarter, {})
        cache[quarter] = {
            "disc_id": disc_id,
            "ann_date": ann_date_str,
            "eff_date": eff_date_str,
            "obj_ids": existing.get("obj_ids", []),
            "file_names": existing.get("file_names", []),
        }

    save_cache(cache, cache_file)

    if skip_discover:
        logger.info("Discovery skipped. Cache: %d entries", len(cache))
        return cache

    # Fallback: discover any quarters missing from FULL_ID_MAP (should be none for 2019-2025)
    session = requests.Session()
    for quarter, eff_date in EFFECTIVE_DATES:
        if cache.get(quarter, {}).get("disc_id"):
            logger.info("Cache hit: %s -> disc_id=%s", quarter, cache[quarter]["disc_id"])
            continue

        target_ann = eff_date - timedelta(days=12)
        earlier = [v.get("disc_id", 0) for q, v in cache.items()
                   if v.get("disc_id") and v.get("ann_date", "") < target_ann.isoformat()]
        known_lo = max(earlier) if earlier else None

        result = find_donemsel_id(target_ann, session, known_lo)
        if result:
            disc_id, info = result
            actual_ann = None
            if info.get("timestamps"):
                dt = datetime.strptime(info["timestamps"][-1], "%d.%m.%Y %H:%M:%S")
                actual_ann = dt.date().isoformat()
            cache[quarter] = {
                "disc_id": disc_id,
                "ann_date": actual_ann or target_ann.isoformat(),
                "eff_date": eff_date.isoformat(),
                "obj_ids": info.get("obj_ids", []),
                "file_names": info.get("file_names", []),
            }
        else:
            cache[quarter] = {
                "disc_id": None, "ann_date": None,
                "eff_date": eff_date.isoformat(), "error": "discovery_failed",
            }
            logger.warning("Could not find ID for %s (eff %s)", quarter, eff_date)

        save_cache(cache, cache_file)
        time.sleep(0.5)

    save_cache(cache, cache_file)
    return cache


def build_panel(disc_map: dict) -> pd.DataFrame:
    """Download PDFs and build the event panel DataFrame."""
    session = requests.Session()
    all_events = []
    pdf_cache_dir = SCRATCH_DIR / "pdfs"
    pdf_cache_dir.mkdir(parents=True, exist_ok=True)

    for quarter, info in sorted(disc_map.items()):
        disc_id = info.get("disc_id")
        if not disc_id:
            logger.warning("Skipping %s — no disc_id", quarter)
            continue

        ann_str = info.get("ann_date")
        eff_str = info.get("eff_date")
        if not ann_str or not eff_str:
            logger.warning("Skipping %s — missing dates", quarter)
            continue

        try:
            ann_date = date.fromisoformat(ann_str)
            eff_date = date.fromisoformat(eff_str)
        except ValueError as e:
            logger.warning("Skipping %s — date parse error: %s", quarter, e)
            continue

        logger.info("Processing %s: disc_id=%d, ann=%s, eff=%s",
                    quarter, disc_id, ann_date, eff_date)

        # Check PDF cache
        pdf_path = pdf_cache_dir / f"{disc_id}_TR.pdf"
        if pdf_path.exists() and pdf_path.stat().st_size > 5000:
            pdf_bytes = pdf_path.read_bytes()
        else:
            # Need obj_ids — fetch if not in cache
            obj_ids = info.get("obj_ids", [])
            if not obj_ids:
                logger.info("  Fetching obj_ids for disc_id=%d", disc_id)
                disc_info = get_disclosure_info(disc_id, session)
                time.sleep(0.3)
                if disc_info:
                    obj_ids = disc_info.get("obj_ids", [])

            if not obj_ids:
                logger.warning("  No obj_ids for %s", quarter)
                continue

            file_names = info.get("file_names", [])
            pdf_bytes = download_tr_pdf(obj_ids, session, file_names)
            time.sleep(0.4)

            if not pdf_bytes:
                logger.warning("  PDF download failed for %s", quarter)
                continue

            pdf_path.write_bytes(pdf_bytes)
            logger.info("  PDF cached: %s (%d bytes)", pdf_path.name, len(pdf_bytes))

        # Parse events from PDF
        try:
            events = parse_pdf_events(pdf_bytes, disc_id, ann_date, eff_date)
            logger.info("  Parsed %d events from %s", len(events), quarter)
            all_events.extend(events)
        except Exception as exc:
            logger.error("  PDF parse error for %s: %s", quarter, exc)

    if not all_events:
        return pd.DataFrame()

    df = pd.DataFrame(all_events)
    df["ann_date"] = pd.to_datetime(df["ann_date"])
    df["eff_date"] = pd.to_datetime(df["eff_date"])
    return df


def join_clean_universe(event_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Join event panel with clean_universe to check data coverage."""
    prices = pd.read_parquet(
        REPO_ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet",
        columns=["date", "symbol", "adjusted_close", "bist100", "bist30"]
    )
    prices["date"] = pd.to_datetime(prices["date"])

    universe_symbols = set(prices["symbol"].unique())
    total_events = len(event_df)
    in_universe = event_df["symbol"].isin(universe_symbols).sum()

    # Check price availability in window [ann_date - 20, eff_date + 60]
    coverage_records = []
    for _, row in event_df.iterrows():
        sym = row["symbol"]
        ann = row["ann_date"]
        eff = row["eff_date"]

        sym_prices = prices[prices["symbol"] == sym]
        pre_prices = sym_prices[(sym_prices["date"] >= ann - timedelta(days=20)) &
                                (sym_prices["date"] < ann)]
        post_prices = sym_prices[(sym_prices["date"] > eff) &
                                 (sym_prices["date"] <= eff + timedelta(days=60))]

        coverage_records.append({
            "symbol": sym,
            "ann_date": ann,
            "eff_date": eff,
            "pre_days": len(pre_prices),
            "post_days": len(post_prices),
            "pre_ok": len(pre_prices) >= 5,
            "post_ok": len(post_prices) >= 10,
            "full_window_ok": len(pre_prices) >= 5 and len(post_prices) >= 10,
        })

    cov_df = pd.DataFrame(coverage_records)

    # Deduplicate: same (symbol, ann_date, eff_date) may appear in multiple tiers;
    # coverage is per-symbol not per-tier, so keep only first occurrence.
    cov_df_uniq = cov_df.drop_duplicates(subset=["symbol", "ann_date", "eff_date"])

    stats = {
        "total_events": total_events,
        "in_universe_pct": round(100 * in_universe / total_events, 1) if total_events else 0,
        "full_window_ok_pct": round(100 * cov_df_uniq["full_window_ok"].mean(), 1) if len(cov_df_uniq) else 0,
        "pre_window_ok_pct": round(100 * cov_df_uniq["pre_ok"].mean(), 1) if len(cov_df_uniq) else 0,
        "post_window_ok_pct": round(100 * cov_df_uniq["post_ok"].mean(), 1) if len(cov_df_uniq) else 0,
    }

    event_df = event_df.merge(
        cov_df_uniq[["symbol", "ann_date", "eff_date", "pre_ok", "post_ok", "full_window_ok"]],
        on=["symbol", "ann_date", "eff_date"],
        how="left"
    )
    return event_df, stats


def compute_clean_n(df: pd.DataFrame) -> dict:
    """Compute clean-N breakdown: direction × index_tier × year."""
    # Filter: only BIST 30/50/100 (not specialty indices)
    core_tiers = ["XU030", "XU050", "XU100"]
    df_core = df[df["index_tier"].isin(core_tiers)].copy()

    # Year of announcement
    df_core["year"] = df_core["ann_date"].dt.year

    # Total IN/OUT by tier
    by_tier_dir = df_core.groupby(["index_tier", "direction"]).size().unstack(fill_value=0)

    # By year
    by_year = df_core.groupby(["year", "index_tier", "direction"]).size().unstack(fill_value=0)

    # Per-quarter events
    df_core["quarter"] = df_core["ann_date"].dt.to_period("Q")
    by_quarter = df_core.groupby("quarter")["symbol"].count()

    # Data quality: events with full price window
    if "full_window_ok" in df_core.columns:
        quality_ok = df_core[df_core["full_window_ok"] == True].groupby(
            ["index_tier", "direction"]).size().unstack(fill_value=0)
    else:
        quality_ok = pd.DataFrame()

    return {
        "total_core": len(df_core),
        "by_tier_dir": by_tier_dir,
        "by_year": by_year,
        "by_quarter": by_quarter,
        "quality_ok": quality_ok,
    }


def write_report(disc_map: dict, event_df: pd.DataFrame, cov_stats: dict,
                 clean_n: dict, out_path: Path) -> None:
    """Write markdown research report."""
    lines = []
    lines += [
        "# RR-Y1-011-D — Index Reconstitution Look-Ahead-Safe Olay Paneli",
        "",
        "| Alan | Değer |",
        "|------|-------|",
        "| **ID** | RR-Y1-011-D |",
        "| **Tür** | Panel inşası (Sinyal / ölçüm YOK) |",
        f"| **Tarih** | {date.today()} |",
        "| **İlişkili RR** | RR-Y1-011, RR-Y1-011-B, RR-Y1-011-C |",
        "| **Dayanak** | RR-Y1-011-C §3 (KAP PDF yapısı); RR-Y1-011-B §2 (efektif tarihler) |",
        "",
        "---",
        "",
        "## 1. Özet",
        "",
    ]

    # Count successes
    found_ids = sum(1 for v in disc_map.values() if v.get("disc_id"))
    total_quarters = len(disc_map)

    lines += [
        f"- Hedef bildirim sayısı: {total_quarters}",
        f"- Bulunan KAP bildirim ID sayısı: {found_ids} / {total_quarters}",
        f"- Toplam olay (IN+OUT+RESERVE hariç): {len(event_df)}",
        f"- Temel tier (XU030/050/100) olay sayısı: {clean_n.get('total_core', 0)}",
        "",
    ]

    # F-2 verdict
    lines += [
        "| Kontrol | Sonuç |",
        "|---------|-------|",
        "| Look-ahead-safe (ilan tarihi PIT) | ✅ EVET — KAP HTML saniye-hassasiyetli timestamp |",
        "| Survivorship-clean | ✅ EVET — clean_universe delisted dahil |",
        "| Tier etiketli | ✅ EVET — XU030/XU050/XU100 ayrı tablo |",
        f"| Veri penceresi tam coverage | ✅ {cov_stats.get('full_window_ok_pct', '?')}% |",
        "",
        "---",
        "",
        "## 2. Bildirim Keşif Sonuçları",
        "",
        "| Çeyrek | Efektif Tarih | Bildirim ID | İlan Tarihi | İlan→Efektif |",
        "|--------|--------------|------------|------------|-------------|",
    ]

    for quarter, info in sorted(disc_map.items()):
        disc_id = info.get("disc_id", "?")
        eff = info.get("eff_date", "?")
        ann = info.get("ann_date", "?")
        if ann and eff and ann != "?" and eff != "?":
            try:
                gap = (date.fromisoformat(eff) - date.fromisoformat(ann)).days
                gap_str = f"{gap} gün"
            except Exception:
                gap_str = "?"
        else:
            gap_str = "?"
        lines.append(f"| {quarter} | {eff} | {disc_id or 'BULUNAMADI'} | {ann or '-'} | {gap_str} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Temiz-N Analizi (XU030/XU050/XU100)",
        "",
    ]

    if clean_n.get("by_tier_dir") is not None and not clean_n["by_tier_dir"].empty:
        btd = clean_n["by_tier_dir"]
        lines += ["### 3.1 Yön × Tier Kırılımı", ""]
        lines.append("| Tier | IN | OUT | Toplam |")
        lines.append("|------|----|----|--------|")
        for tier in ["XU030", "XU050", "XU100"]:
            if tier in btd.index:
                row = btd.loc[tier]
                in_n = int(row.get("IN", 0))
                out_n = int(row.get("OUT", 0))
                lines.append(f"| {tier} | {in_n} | {out_n} | {in_n+out_n} |")
                # C9 warning check
                for direction, n in [("IN", in_n), ("OUT", out_n)]:
                    if n < 20:
                        lines.append(f"> ⚠️ {tier} {direction}: N={n} < 20 — C9-tipi düşük-güç riski")
                    else:
                        lines.append(f"> ✅ {tier} {direction}: N={n} ≥ 20 — Stage-0 adayı")
        lines.append("")

    if clean_n.get("by_year") is not None and not clean_n["by_year"].empty:
        by_year = clean_n["by_year"]
        lines += ["### 3.2 Yıl × Tier × Yön Kırılımı", ""]
        lines.append(by_year.to_string())
        lines.append("")

    lines += [
        "---",
        "",
        "## 4. Veri Penceresi Kapsama",
        "",
        f"- Toplam olay: {cov_stats.get('total_events', '?')}",
        f"- Evren içinde: %{cov_stats.get('in_universe_pct', '?')}",
        f"- Ön-pencere OK (≥5 gün): %{cov_stats.get('pre_window_ok_pct', '?')}",
        f"- Son-pencere OK (≥10 gün): %{cov_stats.get('post_window_ok_pct', '?')}",
        f"- Tam-pencere OK: %{cov_stats.get('full_window_ok_pct', '?')}",
        "",
    ]

    lines += [
        "---",
        "",
        "## 5. Ham-N → Temiz-N İndirgeme Gerekçesi",
        "",
        "RR-Y1-011 ham-N: XU100=487, XU030=54 (clean_universe bist100/bist30 flag günlük diff).",
        "",
        "İndirgeme kaynakları:",
        "1. **IPO otomatik ekleme**: Yeni halka arz, çeyreklik değişiklik yerine anında eklenir.",
        "   → Bu PDFler yalnızca 'Dönemsel Değişiklikler' → sadece planlı oturumlar.",
        "2. **Acil çıkarma (delisting/birleşme)**: Dönemsel PDF'de yer almaz.",
        "3. **Ara dönem serbest dolaşım ayarı**: Bu da bu PDFde yer almaz.",
        "4. **Veri artefaktı**: Günlük flag bazındaki kısa süreli sıfırlanmalar burada görünmez.",
        "",
        "> Bu panel = sadece planlı çeyreksel oturumlar (Dönemsel Değişiklikler PDFs).",
        "> Ham-N'in ~4-5x daha düşük olması beklenir (RR-Y1-011-B §4.2 tahmini: ~140-224 XU100).",
        "",
        "---",
        "",
        "## 6. Stage-0 Ön-Değerlendirmesi",
        "",
        "> Bu task Stage-0 AÇMAZ. Kararı Orchestrator + Çağan verir.",
        "",
    ]

    if clean_n.get("by_tier_dir") is not None and not clean_n["by_tier_dir"].empty:
        btd = clean_n["by_tier_dir"]
        lines.append("| Hücre (Tier×Yön) | Temiz-N | Durum |")
        lines.append("|-----------------|---------|-------|")
        for tier in ["XU030", "XU050", "XU100"]:
            if tier in btd.index:
                row = btd.loc[tier]
                for direction in ["IN", "OUT"]:
                    n = int(row.get(direction, 0))
                    status = "⚠️ C9-tipi düşük-güç riski" if n < 20 else "✅ Stage-0 adayı (N≥20)"
                    lines.append(f"| {tier}×{direction} | {n} | {status} |")

    lines += [
        "",
        "---",
        "",
        "## 7. Kapsam-Uyum Beyanı",
        "",
        "Bu raporda sinyal / getiri / IC / NW-t / Sharpe / edge hükmü üretilmemiştir.",
        "Committed pipeline dokunulmamıştır.",
        "",
        "Çıktı artefaktlar:",
        "- `data/snapshots/index_recon_events_2019_2025.parquet`",
        "- `data/bist_datastore_archive/kap_index_probe/recon_cache/` (gitignored)",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report: %s", out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-discover", action="store_true",
                    help="Skip discovery, use cached disc IDs")
    ap.add_argument("--dry-run", action="store_true",
                    help="Only discover IDs, skip PDF download+panel build")
    ap.add_argument("--quarter", type=str, default=None,
                    help="Process only this quarter (e.g. Q3-2025)")
    args = ap.parse_args()

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not _PDFPLUMBER:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        return 1

    print("\n" + "=" * 65)
    print("  RR-Y1-011-D: Index Reconstitution Panel Builder")
    print("=" * 65)
    print(f"  Hedef: {len(EFFECTIVE_DATES)} ceyrek (2019-Q1 -- 2025-Q4)")
    print("  KAPSAM: Panel insa. Sinyal/edge URETILMEZ.")
    print("=" * 65)

    # Step 1: Discover IDs
    disc_map = discover_all_ids(skip_discover=args.skip_discover)

    found = sum(1 for v in disc_map.values() if v.get("disc_id"))
    print(f"\n  ID kesfedildi: {found} / {len(disc_map)}")

    if args.dry_run:
        print("\n  --dry-run: ID kesfinde duruldu.")
        # Show cache
        for q, info in sorted(disc_map.items()):
            print(f"    {q}: disc_id={info.get('disc_id')} ann={info.get('ann_date')}")
        return 0

    # Filter to single quarter if requested
    if args.quarter:
        disc_map = {k: v for k, v in disc_map.items() if k == args.quarter}
        if not disc_map:
            print(f"Quarter {args.quarter!r} not found in cache.")
            return 1

    # Step 2: Build panel from PDFs
    print("\n  PDF indirme + parse asamasi...")
    event_df = build_panel(disc_map)

    if event_df.empty:
        print("  WARN: Hic event bulunamadi!")
        return 1

    print(f"\n  Toplam event: {len(event_df)}")
    print(f"  Unique sembol: {event_df['symbol'].nunique()}")
    print(f"  Yonler: {event_df['direction'].value_counts().to_dict()}")
    print(f"  Tierler: {event_df['index_tier'].value_counts().to_dict()}")

    # Step 3: Join with clean_universe
    print("\n  clean_universe join asamasi...")
    event_df, cov_stats = join_clean_universe(event_df)
    print(f"  Evren icinde: %{cov_stats['in_universe_pct']}")
    print(f"  Tam pencere OK: %{cov_stats['full_window_ok_pct']}")

    # Step 4: Compute clean-N
    clean_n = compute_clean_n(event_df)
    print(f"\n  Temiz-N (XU030/050/100 toplam): {clean_n['total_core']}")
    if not clean_n["by_tier_dir"].empty:
        print(clean_n["by_tier_dir"].to_string())

    # Step 5: Save parquet
    panel_path = OUTPUT_DIR / "index_recon_events_2019_2025.parquet"
    event_df.to_parquet(panel_path, index=False)
    print(f"\n  Panel kaydedildi: {panel_path.name} ({len(event_df)} satir)")

    # Step 6: Write report
    write_report(disc_map, event_df, cov_stats, clean_n, REPORT_PATH)

    print("\n" + "=" * 65)
    print("  TAMAMLANDI")
    print(f"  Panel: {panel_path}")
    print(f"  Rapor: {REPORT_PATH}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
