"""Faz 0 frozen point-in-time price snapshot. D-177.

Freezes BIST100 + XU100 Close prices to a versioned parquet + metadata JSON with
a content hash, so every IC computation reads identical data (D-176 showed
yfinance is non-reproducible: ~67% reconciliation). Close-only is sufficient for
Faz 0 (RS / realized-vol / forward-returns all use Close; ADV/volume is Faz 1).

Survivorship (invariant 9): delisted names (KOZAA/KOZAL/IPEKE/TRALT) are not
fetchable from yfinance (404). The snapshot is built from available constituents
and EXPLICITLY records the gap plus its bias DIRECTION (the maintainer condition):
survivors-only -> IC may read optimistic; high-vol falsely-good in TEST 2.

fetch_fn / macro_fn are injectable so tests run without network.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from src.screening import faz0_config as cfg

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"
_LONG_COLS = ["date", "symbol", "close"]
_INDEX_SYMBOL = "XU100"


def _paths(start: str, end: str, out_dir: Path) -> tuple[Path, Path]:
    base = f"faz0_prices_{start}_{end}"
    return out_dir / f"{base}.parquet", out_dir / f"{base}.meta.json"


def content_hash(long_df: pd.DataFrame) -> str:
    """Deterministic sha256 of the snapshot, independent of parquet metadata.

    Canonical form: sorted by [symbol, date], fixed float format, CSV bytes.
    """
    canon = long_df.sort_values(["symbol", "date"]).reset_index(drop=True)
    csv_bytes = canon.to_csv(index=False, float_format="%.10g").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def _build_long(
    prices: dict[str, pd.DataFrame],
    macro: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Build long-format [date, symbol, close]; include XU100 index row."""
    rows: list[tuple] = []
    loaded = sorted(prices.keys())
    for t in loaded:
        s = prices[t]["Close"].dropna()
        for d, c in s.items():
            rows.append((pd.Timestamp(d).strftime("%Y-%m-%d"), t, float(c)))
    if macro is not None and not macro.empty and "BIST100" in macro.columns:
        xu = macro["BIST100"].dropna()
        for d, c in xu.items():
            rows.append((pd.Timestamp(d).strftime("%Y-%m-%d"), _INDEX_SYMBOL, float(c)))
    long_df = pd.DataFrame(rows, columns=_LONG_COLS).sort_values(
        ["symbol", "date"]
    ).reset_index(drop=True)
    return long_df, loaded


def freeze_price_snapshot(
    universe: list[str],
    start: str = cfg.SNAPSHOT_START,
    end: str = cfg.SNAPSHOT_END,
    out_dir: Path | str = _SNAPSHOT_DIR,
    fetch_fn: Callable | None = None,
    macro_fn: Callable | None = None,
    timestamp: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Freeze (or load) the point-in-time Close snapshot.

    Idempotent: if the parquet exists it is loaded (FROZEN) and re-fetch is
    skipped -> reproducible IC. Returns (long_df, metadata).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path, meta_path = _paths(start, end, out_dir)

    if parquet_path.exists() and meta_path.exists():
        long_df = pd.read_parquet(parquet_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        logger.info("snapshot frozen-load: %s (%d rows)", parquet_path.name, len(long_df))
        return long_df, meta

    # Lazy import keeps network deps out of the module import graph (test-safe).
    if fetch_fn is None:
        from src.backtest.data_loader import load_price_data as fetch_fn  # type: ignore
    if macro_fn is None:
        from src.backtest.data_loader import load_macro_series as macro_fn  # type: ignore

    prices = fetch_fn(universe, start, end)
    macro = macro_fn(start, end)
    long_df, loaded = _build_long(prices, macro)

    chash = content_hash(long_df)
    missing_delisted = [t for t in cfg.KNOWN_DELISTED if t not in loaded]
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "directive": "D-177",
        "window": {"start": start, "end": end},
        "source": "yfinance (Close, auto_adjust)",
        "requested_universe_n": len(universe),
        "loaded_universe": loaded,
        "loaded_universe_n": len(loaded),
        "index_symbol": _INDEX_SYMBOL,
        "n_rows": int(len(long_df)),
        "content_hash": chash,
        "timestamp_utc": ts,
        "config_version": cfg.CONFIG_VERSION,
        "survivorship": {
            "excluded_delisted": missing_delisted,
            "note": (
                "survivors-only snapshot: delisted names not fetchable (yfinance "
                "404), so excluded."
            ),
            "bias_direction": (
                "Excluding delisted names removes their (mostly poor) outcomes -> "
                "measured IC may read OPTIMISTIC/inflated; in TEST 2 the missing "
                "left tail biases skewness UP -> high-vol group looks falsely good. "
                "Read Faz 0 results as an upper-ish bound, not a neutral estimate."
            ),
        },
    }
    long_df.to_parquet(parquet_path, index=False)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "snapshot frozen: %s rows=%d hash=%s missing_delisted=%s",
        parquet_path.name, len(long_df), chash[:12], missing_delisted,
    )
    return long_df, meta


def to_close_panel(long_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Long [date, symbol, close] -> (stock Close panel, XU100 series).

    Index = DatetimeIndex (sorted); stock columns sorted; XU100 separated out.
    """
    df = long_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
    wide = wide.sort_index()
    xu = wide[_INDEX_SYMBOL] if _INDEX_SYMBOL in wide.columns else pd.Series(dtype=float)
    stocks = wide.drop(columns=[_INDEX_SYMBOL], errors="ignore")
    stocks = stocks.reindex(sorted(stocks.columns), axis=1)
    return stocks, xu


def resolve_universe() -> list[str]:
    """Current BIST100 universe (config-driven, deterministic). Fallback: BIST50."""
    try:
        from src.data.fetcher import get_bist100_tickers
        tickers = get_bist100_tickers()
        if tickers:
            return sorted(set(tickers))
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_bist100_tickers failed (%s); falling back to BIST50", exc)
    from src.signals.thresholds import CUSTODY_BIST50_TICKERS
    return sorted(set(CUSTODY_BIST50_TICKERS))


def _main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Faz 0 frozen price snapshot (D-177)")
    p.add_argument("--start", default=cfg.SNAPSHOT_START)
    p.add_argument("--end", default=cfg.SNAPSHOT_END)
    args = p.parse_args()
    universe = resolve_universe()
    _, meta = freeze_price_snapshot(universe, args.start, args.end)
    print(json.dumps({
        "content_hash": meta["content_hash"],
        "loaded_universe_n": meta["loaded_universe_n"],
        "n_rows": meta["n_rows"],
        "excluded_delisted": meta["survivorship"]["excluded_delisted"],
    }, indent=2))


if __name__ == "__main__":
    _main()
