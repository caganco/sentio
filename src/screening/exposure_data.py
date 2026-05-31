"""D-187 -- data freeze layer: XU100, TLREF (compound), TUFE (compound), gold TL.

Key design: TP.BISTTLREF.KAPANIS is an annualised RATE (not a price). We convert
to a COMPOUND-GROWTH INDEX before storing:
    idx[t] = idx[t-1] * (1 + rate[t] / 365)   (start = 1.0)
All portfolio arithmetic uses this index series, never the raw rate -- ensuring
apples-to-apples comparison with XU100 price series and TUFE growth index.

All freezes are idempotent (content_hash + meta.json). fetch functions are
injectable so unit tests run without network.
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.screening.exposure_config import (
    D187_CONFIG_VERSION,
    EXPOSURE_END,
    EXPOSURE_START,
    GOLD_YFINANCE_SYMBOL,
    TLREF_EVDS_SERIES,
    TUFE_EVDS_SERIES,
    USDTRY_EVDS_SERIES,
    XU100_YFINANCE_SYMBOL,
)

logger = logging.getLogger(__name__)
_SNAP = Path(__file__).parent.parent.parent / "data" / "snapshots"


def _content_hash(s: pd.Series) -> str:
    canon = s.dropna().sort_index().reset_index()
    return hashlib.sha256(canon.to_csv(index=False).encode()).hexdigest()


def _meta_path(p: Path) -> Path:
    return p.with_suffix(".meta.json")


def _load_or_none(p: Path) -> pd.Series | None:
    if p.exists() and _meta_path(p).exists():
        df = pd.read_parquet(p)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").squeeze()
    return None


def _freeze(series: pd.Series, path: Path, meta_extra: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = series.reset_index()
    df.columns = ["date", "value"]
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.to_parquet(path, index=False)
    meta = {"content_hash": _content_hash(series), "n_obs": int(len(series)),
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config_version": D187_CONFIG_VERSION, **meta_extra}
    _meta_path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# TLREF compound-growth index
# ---------------------------------------------------------------------------
def _tlref_to_compound(rate_series: pd.Series) -> pd.Series:
    """Convert annualised overnight rate (%) to a compound-growth index (start=1.0).

    Each day: idx[t] = idx[t-1] * (1 + rate[t] / 100 / 365).
    NaN days carry forward the previous index level (no compounding on missing).
    """
    daily_factor = 1.0 + rate_series.fillna(0.0) / 100.0 / 365.0
    return daily_factor.cumprod()


def freeze_tlref_series(
    start: str = EXPOSURE_START, end: str = EXPOSURE_END,
    out_dir: Path | str = _SNAP, fetch_fn: Callable | None = None, tag: str = "d187",
) -> pd.Series:
    """Freeze TLREF compound-growth index. Returns the index series (not raw rate)."""
    path = Path(out_dir) / f"exposure_{tag}_tlref.parquet"
    cached = _load_or_none(path)
    if cached is not None:
        logger.info("TLREF frozen-load: %d obs", len(cached))
        return cached
    if fetch_fn is None:
        from src.data.evds_client import fetch_series
        rate = fetch_series(TLREF_EVDS_SERIES, start, end)
        if rate is None or len(rate) == 0:
            raise RuntimeError("TLREF fetch returned empty")
        rate = pd.Series(rate, name="tlref_rate")
    else:
        rate = fetch_fn(start, end)
    idx = _tlref_to_compound(rate)
    idx.name = "tlref_index"
    _freeze(idx, path, {"series": TLREF_EVDS_SERIES, "window": {"start": start, "end": end},
                        "construction": "compound daily: idx *= (1 + rate/100/365)"})
    logger.info("TLREF frozen: %d obs compound-index", len(idx))
    return idx


# ---------------------------------------------------------------------------
# TUFE compound-growth index
# ---------------------------------------------------------------------------
def freeze_tufe_series(
    start: str = EXPOSURE_START, end: str = EXPOSURE_END,
    out_dir: Path | str = _SNAP, fetch_fn: Callable | None = None, tag: str = "d187",
) -> pd.Series:
    """Freeze TUFE monthly CPI as a compound-growth index (daily, ffill). Start=1.0."""
    path = Path(out_dir) / f"exposure_{tag}_tufe.parquet"
    cached = _load_or_none(path)
    if cached is not None:
        logger.info("TUFE frozen-load: %d obs", len(cached))
        return cached
    if fetch_fn is None:
        from src.data.macro_sources import fetch_tufe_series as _f
        s = _f(start, end)
        if s is None or len(s) == 0:
            raise RuntimeError("TUFE fetch returned empty")
    else:
        s = fetch_fn(start, end)
    daily_ret = s.pct_change().fillna(0.0)
    idx = (1.0 + daily_ret).cumprod()
    idx.name = "tufe_index"
    _freeze(idx, path, {"series": TUFE_EVDS_SERIES, "window": {"start": start, "end": end},
                        "construction": "monthly pct_change ffill -> cumprod"})
    logger.info("TUFE frozen: %d obs compound-index", len(idx))
    return idx


# ---------------------------------------------------------------------------
# XU100 price series
# ---------------------------------------------------------------------------
def freeze_xu100_series(
    start: str = EXPOSURE_START, end: str = EXPOSURE_END,
    out_dir: Path | str = _SNAP, fetch_fn: Callable | None = None, tag: str = "d187",
) -> pd.Series:
    """Freeze XU100.IS daily close (price-only, no dividends -- caveat documented)."""
    path = Path(out_dir) / f"exposure_{tag}_xu100.parquet"
    cached = _load_or_none(path)
    if cached is not None:
        logger.info("XU100 frozen-load: %d obs", len(cached))
        return cached
    if fetch_fn is None:
        import yfinance as yf
        df = yf.download(XU100_YFINANCE_SYMBOL, start=start, end=end,
                         auto_adjust=True, progress=False)
        s = df["Close"].squeeze().dropna()
        s.name = "xu100_close"
        s.index = pd.to_datetime(s.index)
    else:
        s = fetch_fn(start, end)
    _freeze(s, path, {"symbol": XU100_YFINANCE_SYMBOL, "window": {"start": start, "end": end},
                      "caveat": "price-only, no dividends; equity disadvantaged ~2-4%/yr"})
    logger.info("XU100 frozen: %d obs", len(s))
    return s


# ---------------------------------------------------------------------------
# Gold TL/gram (diagnostic B4)
# ---------------------------------------------------------------------------
def freeze_gold_series(
    start: str = EXPOSURE_START, end: str = EXPOSURE_END,
    out_dir: Path | str = _SNAP, fetch_fn: Callable | None = None, tag: str = "d187",
) -> pd.Series | None:
    """Freeze gold TL/gram = GC=F (USD/oz) x USDTRY / 32.1507 (troy oz to gram).

    Returns None on fetch failure (diagnostic only -- absence never fails the test).
    """
    path = Path(out_dir) / f"exposure_{tag}_gold_tl.parquet"
    cached = _load_or_none(path)
    if cached is not None:
        logger.info("Gold TL frozen-load: %d obs", len(cached))
        return cached
    try:
        if fetch_fn is None:
            import yfinance as yf

            from src.data.evds_client import fetch_series
            gc = yf.download(GOLD_YFINANCE_SYMBOL, start=start, end=end,
                             auto_adjust=True, progress=False)["Close"].squeeze()
            gc.index = pd.to_datetime(gc.index)
            usdtry = fetch_series(USDTRY_EVDS_SERIES, start, end)
            if usdtry is None:
                raise RuntimeError("USDTRY fetch failed")
            usdtry = pd.Series(usdtry, name="usdtry").reindex(gc.index).ffill()
            s = (gc * usdtry / 32.1507).dropna()
            s.name = "gold_tl_gram"
        else:
            s = fetch_fn(start, end)
        _freeze(s, path, {"sources": [GOLD_YFINANCE_SYMBOL, USDTRY_EVDS_SERIES],
                          "window": {"start": start, "end": end},
                          "note": "GC=F USD/oz * USDTRY / 32.1507 troy-oz-to-gram"})
        logger.info("Gold TL frozen: %d obs", len(s))
        return s
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gold TL fetch failed (%s) -> B4 diagnostic skipped", exc)
        return None


# ---------------------------------------------------------------------------
# Convenience loader (all series, inject-friendly)
# ---------------------------------------------------------------------------
def load_all_series(
    start: str = EXPOSURE_START, end: str = EXPOSURE_END,
    out_dir: Path | str = _SNAP, tag: str = "d187",
    tlref_fn: Callable | None = None,
    tufe_fn: Callable | None = None,
    xu100_fn: Callable | None = None,
    gold_fn: Callable | None = None,
) -> dict[str, pd.Series | None]:
    return {
        "tlref": freeze_tlref_series(start, end, out_dir, tlref_fn, tag),
        "tufe": freeze_tufe_series(start, end, out_dir, tufe_fn, tag),
        "xu100": freeze_xu100_series(start, end, out_dir, xu100_fn, tag),
        "gold": freeze_gold_series(start, end, out_dir, gold_fn, tag),
    }
