"""KAP daily pipeline orchestration.

Runs the full fetch → parse → write JSON → DB upsert cycle for all
watched BIST symbols. Called by the orchestrator before market data fetch.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from src.data.database import initialize_db, upsert_kap_events
from src.data.kap_fetcher import fetch_all_symbols
from src.data.kap_parser import KapEvent, parse_all
from src.utils.config import load_config

logger = logging.getLogger(__name__)

# Istanbul is UTC+3 — used for "today" default when no target_date given
_TZ_OFFSET_HOURS = 3


def _get_watched_symbols() -> list[str]:
    cfg = load_config()
    tickers = cfg.get("portfolio", {}).get("tickers", [])
    return list(tickers) if tickers else []


def run_daily_kap_pipeline(
    target_date: date | None = None,
    output_dir: str | Path = "intelligence",
    symbols: list[str] | None = None,
) -> str:
    """Run the daily KAP disclosure pipeline.

    Steps:
    1. Fetch all disclosures for `symbols` on `target_date`
    2. Parse into KapEvent objects
    3. Write intelligence/kap_YYYY-MM-DD.json
    4. Upsert into kap_events DB table

    Args:
        target_date: Day to fetch (default: today Istanbul time)
        output_dir: Directory for output JSON (relative to project root or absolute)
        symbols: BIST tickers to check (default: config portfolio.tickers)

    Returns:
        Absolute path to the written JSON file.
    """
    if target_date is None:
        now_istanbul = datetime.now(tz=timezone.utc)
        target_date = now_istanbul.date()

    if symbols is None:
        symbols = _get_watched_symbols()

    fetched_at = datetime.utcnow()

    logger.info("KAP pipeline: fetching %d symbols for %s", len(symbols), target_date)

    try:
        raw_by_symbol = fetch_all_symbols(symbols, target_date)
    except Exception as exc:
        logger.error("KAP pipeline: fetch_all_symbols failed: %s", exc)
        raw_by_symbol = {s: [] for s in symbols}

    # Parse needs a live Kap() session for attachment fetching — reuse fetcher's session
    # We parse without attachment re-fetching here (attachments already captured in fetcher dict)
    # For attachment URLs, parse_all needs a kap_client — pass a dummy that won't be called
    # (has_attachment=True triggers fetch, so we use a minimal wrapper)
    from kap_client import Kap
    with Kap() as kap:
        events = parse_all(raw_by_symbol, fetched_at, kap)

    logger.info("KAP pipeline: parsed %d events", len(events))

    # Resolve output dir relative to project root if not absolute
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        from pathlib import Path as _P
        project_root = _P(__file__).parent.parent.parent
        output_path = project_root / output_dir

    output_path.mkdir(parents=True, exist_ok=True)

    json_path = write_kap_json(events, target_date, str(output_path))

    try:
        initialize_db()
        upsert_kap_events(events)
    except Exception as exc:
        logger.warning("KAP pipeline: DB upsert failed (continuing): %s", exc)

    return json_path


def write_kap_json(
    events: list[KapEvent],
    target_date: date,
    output_dir: str | Path,
) -> str:
    """Write KapEvent list to intelligence/kap_YYYY-MM-DD.json.

    Overwrites if file already exists (with a WARNING log).
    high_priority_flags: symbols with 2+ ozel_durum events on the same day.

    Returns: absolute path of the written file.
    """
    output_path = Path(output_dir)
    filename = f"kap_{target_date.strftime('%Y-%m-%d')}.json"
    file_path = output_path / filename

    if file_path.exists():
        logger.warning("KAP: overwriting existing file %s", file_path)

    # Count ozel_durum per symbol for high_priority_flags
    ozel_durum_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {
        "ozel_durum": 0,
        "finansal_rapor": 0,
        "insider": 0,
        "temettu": 0,
        "sermaye_artirimi": 0,
        "genel_kurul": 0,
        "diger": 0,
    }
    for ev in events:
        category_counts[ev.category] = category_counts.get(ev.category, 0) + 1
        if ev.category == "ozel_durum":
            ozel_durum_counts[ev.symbol] = ozel_durum_counts.get(ev.symbol, 0) + 1

    high_priority_flags = sorted(sym for sym, cnt in ozel_durum_counts.items() if cnt >= 2)

    doc = {
        "date": target_date.strftime("%Y-%m-%d"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_run_id": str(uuid.uuid4()),
        "symbols_checked": 0,  # filled below after we know symbol count
        "total_events": len(events),
        "summary": category_counts,
        "high_priority_flags": high_priority_flags,
        "events": [_event_to_dict(ev) for ev in events],
    }
    # symbols_checked: count distinct symbols that had at least 1 result
    doc["symbols_checked"] = len({ev.symbol for ev in events}) if events else 0

    output_path.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("KAP: wrote %s (%d events)", file_path, len(events))
    return str(file_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _event_to_dict(ev: KapEvent) -> dict:
    return {
        "disclosure_index": ev.disclosure_index,
        "symbol": ev.symbol,
        "published_at": ev.published_at.isoformat(),
        "fetched_at": ev.fetched_at.isoformat(),
        "subject": ev.subject,
        "category": ev.category,
        "summary": ev.summary,
        "url": ev.url,
        "source_type": ev.source_type,
        "source_domain": ev.source_domain,
        "structured_data": ev.structured_data,
        "has_attachment": ev.has_attachment,
        "attachment_urls": ev.attachment_urls,
    }
