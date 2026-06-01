"""D-188 forward-capture daily entrypoint (scheduled).

Runs ONE forward pass: capture today's catalyst disclosures via the auth-free KAP
feed, record pre-registered event signals, and fill any matured t+5/+20/+60 returns.
Designed to be triggered DAILY (the auth-free KAP feed is recent-only ~24h, so a
weekly cadence would miss most events). No token required.

Usage (manual):
    python scripts/event_forward_capture.py

Scheduled (Windows Task Scheduler) -- created by scripts/register_event_capture_task.ps1.
Output is one JSON summary line; failures degrade gracefully (events never fabricated).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

# Ensure repo root on sys.path when run as a bare script from Task Scheduler.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.screening.event_forward_recorder import capture_once  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        summary = capture_once()
        print(json.dumps({"run": stamp, "ok": True, **summary}, ensure_ascii=False))
        return 0
    except Exception as exc:  # never crash the scheduled task hard; log + nonzero
        print(json.dumps({"run": stamp, "ok": False, "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        logging.exception("event_forward_capture failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
