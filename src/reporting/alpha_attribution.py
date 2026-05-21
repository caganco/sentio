"""Alpha attribution daily snapshot writer.

Writes flat daily parquets to data/signal_logs/YYYY-MM-DD.parquet.
One file per trading day; the IC dashboard reads these directly via
ICCalculator(sig_df, ret_df) rather than the Hive-partitioned scanner.

Replaces SignalLogger.log_signal() in daily_update._write_signal_logs_d107:
- Hive format (year=.../month=.../day=.../signals.parquet) is no longer
  written by the daily pipeline (SignalLogger class itself is unchanged).
- Flat format is read by ic_dashboard without schema collisions from returns.parquet.

Storage:
  data/signal_logs/YYYY-MM-DD.parquet   — signal records
  data/analytics/YYYY-MM-DD_attr.json  — pipeline health JSON
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.signals.thresholds import SIGNAL_LOG_BASE_PATH

logger = logging.getLogger(__name__)

_BASE = Path(SIGNAL_LOG_BASE_PATH)
_ANALYTICS = Path("data/analytics")

# Glob pattern that matches only daily flat files (not returns.parquet or Hive dirs)
_FLAT_GLOB = "????-??-??.parquet"


def write_daily_snapshot(
    records: list[dict],
    as_of_date: date | None = None,
) -> Path:
    """Write flat daily parquet + analytics JSON.

    Args:
        records: list of dicts from SignalLogRecord.model_dump().
        as_of_date: trading date (defaults to today).

    Returns:
        Path to the written parquet file.
    """
    today = as_of_date or date.today()
    _BASE.mkdir(parents=True, exist_ok=True)
    _ANALYTICS.mkdir(parents=True, exist_ok=True)

    parquet_path = _BASE / f"{today}.parquet"

    if records:
        df = pd.DataFrame(records)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        df.to_parquet(parquet_path, index=False, compression="snappy")
        logger.info(
            "alpha_attribution: %d records → %s", len(records), parquet_path
        )
    else:
        # Write a structurally valid but empty parquet so downstream checks pass
        pd.DataFrame(columns=["date", "symbol", "composite_score"]).to_parquet(
            parquet_path, index=False, compression="snappy"
        )
        logger.warning(
            "alpha_attribution: 0 records — empty snapshot written to %s", parquet_path
        )

    _ANALYTICS.mkdir(parents=True, exist_ok=True)
    json_path = _ANALYTICS / f"{today}_attr.json"
    json_path.write_text(
        json.dumps(
            {"status": "ok", "date": str(today), "record_count": len(records)},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return parquet_path


def count_flat_signals(base_path: str | None = None) -> int:
    """Return total signal records across all flat daily parquets."""
    base = Path(base_path or SIGNAL_LOG_BASE_PATH)
    if not base.exists():
        return 0
    total = 0
    for p in sorted(base.glob(_FLAT_GLOB)):
        try:
            df = pd.read_parquet(p, columns=["symbol"])
            total += len(df)
        except Exception as exc:
            logger.debug("count_flat_signals: skip %s — %s", p.name, exc)
    return total


def read_flat_signals(base_path: str | None = None) -> pd.DataFrame:
    """Read all flat daily parquets into a single DataFrame.

    Used by ic_dashboard to bypass the Hive dataset scanner (which would
    include returns.parquet and cause a schema mismatch).
    """
    base = Path(base_path or SIGNAL_LOG_BASE_PATH)
    if not base.exists():
        return pd.DataFrame()

    parts: list[pd.DataFrame] = []
    for p in sorted(base.glob(_FLAT_GLOB)):
        try:
            parts.append(pd.read_parquet(p))
        except Exception as exc:
            logger.debug("read_flat_signals: skip %s — %s", p.name, exc)

    if not parts:
        return pd.DataFrame()

    return pd.concat(parts, ignore_index=True)
