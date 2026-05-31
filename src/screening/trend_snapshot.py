"""D-185 Trend-Motor Test -- frozen point-in-time OHLCV snapshot.

The Faz 0 snapshot.freeze_price_snapshot is CLOSE-ONLY (RS/vol/forward-returns
need only Close). Trend variants need full OHLCV (ATR, Donchian, NR7/inside-bar,
volume confirmation, t+1-open entry) -> this module freezes OHLCV to a versioned
parquet + meta with a content hash, so every run reads identical data.

Reuses snapshot.py helpers (content_hash, _compute_adv) WITHOUT modifying the
old Close-only path (strangler: additive only).

Survivorship (Faz 0 precedent): delisted names are 404 on yfinance; the gap and
its bias DIRECTION (survivors-only -> UPPER BOUND) are recorded in meta.
fetch_fn / macro_fn are injectable so tests run without network.

No composite / conviction / signal-engine / backtest-engine imports.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import trend_config as cfg
from src.screening.faz0_config import KNOWN_DELISTED
from src.screening.snapshot import _compute_adv, content_hash

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"
_OHLCV_COLS = ["date", "symbol", "open", "high", "low", "close", "volume"]
_INDEX_SYMBOL = "XU100"


def _paths(start: str, end: str, out_dir: Path, tag: str = "") -> tuple[Path, Path]:
    suffix = f"_{tag}" if tag else ""
    base = f"trend{suffix}_ohlcv_{start}_{end}"
    return out_dir / f"{base}.parquet", out_dir / f"{base}.meta.json"


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Case-insensitive column fetch (loader gives Open/High/...; tests lower)."""
    lut = {c.lower(): c for c in df.columns}
    if name in lut:
        return pd.to_numeric(df[lut[name]], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _build_long(prices: dict[str, pd.DataFrame], macro: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Build long [date, symbol, OHLCV]; append XU100 (close only) for regime."""
    frames: list[pd.DataFrame] = []
    loaded = sorted(prices.keys())
    for t in loaded:
        df = prices[t]
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(df.index).strftime("%Y-%m-%d"),
            "symbol": t,
            "open": _col(df, "open").to_numpy(), "high": _col(df, "high").to_numpy(),
            "low": _col(df, "low").to_numpy(), "close": _col(df, "close").to_numpy(),
            "volume": _col(df, "volume").to_numpy(),
        }))
    if macro is not None and not macro.empty and "BIST100" in macro.columns:
        xu = pd.to_numeric(macro["BIST100"], errors="coerce").dropna()
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(xu.index).strftime("%Y-%m-%d"), "symbol": _INDEX_SYMBOL,
            "open": np.nan, "high": np.nan, "low": np.nan, "close": xu.to_numpy(), "volume": np.nan,
        }))
    if not frames:
        return pd.DataFrame(columns=_OHLCV_COLS), loaded
    long_df = pd.concat(frames, ignore_index=True)[_OHLCV_COLS].sort_values(
        ["symbol", "date"]).reset_index(drop=True)
    return long_df, loaded


def freeze_ohlcv_snapshot(
    universe: list[str],
    start: str = cfg.TREND_SNAPSHOT_START,
    end: str = cfg.TREND_SNAPSHOT_END,
    out_dir: Path | str = _SNAPSHOT_DIR,
    fetch_fn: Callable | None = None,
    macro_fn: Callable | None = None,
    timestamp: str | None = None,
    adv_floor_tl: float | None = cfg.TREND_ADV_FLOOR_TL,
    adv_min_days: int = cfg.TREND_ADV_MIN_DAYS,
    tag: str = "v1",
    directive: str = "D-185",
) -> tuple[pd.DataFrame, dict]:
    """Freeze (or load) the point-in-time OHLCV snapshot. Idempotent.

    Returns (long_df, metadata). If the parquet exists it is loaded FROZEN.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path, meta_path = _paths(start, end, out_dir, tag)

    if parquet_path.exists() and meta_path.exists():
        long_df = pd.read_parquet(parquet_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        logger.info("trend snapshot frozen-load: %s (%d rows)", parquet_path.name, len(long_df))
        return long_df, meta

    if fetch_fn is None:
        from src.backtest.data_loader import load_price_data as fetch_fn  # type: ignore
    if macro_fn is None:
        from src.backtest.data_loader import load_macro_series as macro_fn  # type: ignore

    prices = fetch_fn(universe, start, end)
    macro = macro_fn(start, end)

    adv_block: dict | None = None
    if adv_floor_tl is not None:
        adv = _compute_adv(prices, adv_min_days)
        not_fetched = sorted(set(universe) - set(prices))
        passers = {t: df for t, df in prices.items() if adv.get(t, 0.0) >= adv_floor_tl}
        below_floor = sorted(set(prices) - set(passers))
        adv_block = {
            "adv_floor_tl": adv_floor_tl,
            "adv_min_days": adv_min_days,
            "method": "median daily TL volume (Close x Volume) over window [snapshot._compute_adv]",
            "candidates_n": len(universe),
            "fetched_n": len(prices),
            "not_fetched_404": not_fetched,
            "adv_passed_n": len(passers),
            "adv_dropped_below_floor": below_floor,
        }
        prices = passers

    long_df, loaded = _build_long(prices, macro)
    chash = content_hash(long_df)
    missing_delisted = [t for t in KNOWN_DELISTED if t not in loaded]
    ts = timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "directive": directive,
        "window": {"start": start, "end": end},
        "source": "yfinance OHLCV (auto_adjust)",
        "requested_universe_n": len(universe),
        "loaded_universe": loaded,
        "loaded_universe_n": len(loaded),
        "index_symbol": _INDEX_SYMBOL,
        "n_rows": int(len(long_df)),
        "content_hash": chash,
        "timestamp_utc": ts,
        "config_version": cfg.CONFIG_VERSION,
        "adv_filter": adv_block,
        "survivorship": {
            "excluded_delisted": missing_delisted,
            "note": "survivors-only OHLCV snapshot: delisted names not fetchable (yfinance 404), so excluded.",
            "bias_direction": (
                "Survivors-only INFLATES per-trade expectancy -> results are an UPPER BOUND. "
                "If a variant cannot beat the random-entry benchmark post-cost here, it definitely "
                "cannot in reality. No silent full-coverage claim (the maintainer condition)."
            ),
        },
    }
    long_df.to_parquet(parquet_path, index=False)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("trend snapshot frozen: %s rows=%d hash=%s missing_delisted=%s",
                parquet_path.name, len(long_df), chash[:12], missing_delisted)
    return long_df, meta


def to_ohlcv_panels(long_df: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """Long -> ({ticker: OHLCV DataFrame (DatetimeIndex)}, XU100 close Series).

    Per-ticker frames have columns [open, high, low, close, volume], sorted by
    date, NaN rows dropped on close.
    """
    df = long_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    xu_mask = df["symbol"] == _INDEX_SYMBOL
    xu = (df[xu_mask].set_index("date")["close"].sort_index()
          if xu_mask.any() else pd.Series(dtype=float))
    prices: dict[str, pd.DataFrame] = {}
    for sym, g in df[~xu_mask].groupby("symbol"):
        sub = g.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()
        sub = sub.dropna(subset=["close"])
        if not sub.empty:
            prices[str(sym)] = sub
    return prices, xu
