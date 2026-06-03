"""D-207 EOD quoted-spread panel loader (PORT, offline, CI-safe via injection).

Builds a point-in-time [date x symbol] panel of the trailing-median EOD quoted
PROPORTIONAL spread (ask - bid)/mid from the BIST datastore archive
(prices_official PP_GUNSONUFIYATHACIM, cols BEKLEYEN EN IYI ALIS / BEKLEYEN EN IYI
SATIS). This is the DIRECT observed microstructure spread that NRR-010 anchored to
(~11bp full spread on liquid megas, vol-correlation ~0) -- vol-robust where the
Roll(1984) estimator inflates (~0.47*sigma even at zero true spread).

The proportional spread (ask-bid)/mid is corp-action-ADJUSTMENT-INVARIANT (numerator
and denominator scale together under any split/bonus factor), so it is read from RAW
bid/ask with NO adj_factor join -- unlike cross-day price terms.

CI-SAFETY: the archive is NOT present on CI. Engines build this panel LOCALLY and
INJECT it into the cost harness (d204_hi52_stress.per_stock_cost_panel quoted_panel=...);
tests inject synthetic panels (or None). This module is therefore never imported by a
CI test that lacks the archive. The built panel is cached to a gitignored parquet.

Promotes the working parser from the NRR-010 diagnostic (demo-pa/nrr010/nrr010_diag.py)
into a reusable loader. HTTP-free.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.signals import thresholds as _th

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCHIVE_DIR = _REPO_ROOT / "data" / "bist_datastore_archive" / "prices_official"
_DEFAULT_CACHE = _REPO_ROOT / "data" / "clean_universe" / "d207_quoted_spread_panel.parquet"

# Archive Turkish headers -> canonical names (NRR-010 mapping, bid/ask subset).
# Note the DOUBLE space in "ISLEM  KODU" is the literal archive header.
_ARCH_COLS = {
    "TARIH": "date",
    "ISLEM  KODU": "sym",
    "BEKLEYEN EN IYI ALIS": "bid",
    "BEKLEYEN EN IYI SATIS": "ask",
}


def _month_range(start: str, end: str) -> list[tuple[int, int]]:
    y0, m0 = int(start[:4]), int(start[5:7])
    y1, m1 = int(end[:4]), int(end[5:7])
    return [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13)
            if (y0, m0) <= (y, m) <= (y1, m1)]


def load_raw_quotes(
    symbols: set[str], start: str, end: str, archive_dir: Path = _ARCHIVE_DIR,
) -> pd.DataFrame:
    """Raw daily EOD best bid/ask for `symbols` from the monthly archive CSVs.

    Returns a long frame [date, symbol, bid, ask] (corp-action UNADJUSTED -- the
    proportional spread is adjustment-invariant so no adj_factor is needed). Symbols
    are the bare ticker (e.g. "TTKOM"); the archive stores ".E"-suffixed codes."""
    sy_e = {s + ".E" for s in symbols}
    frames = []
    for y, m in _month_range(start, end):
        fp = archive_dir / f"PP_GUNSONUFIYATHACIM.M.{y}{m:02d}.csv"
        if not fp.exists():
            continue
        d = pd.read_csv(fp, sep=";", encoding="cp1254", skiprows=[1],
                        usecols=list(_ARCH_COLS), dtype=str)
        d = d.rename(columns=_ARCH_COLS)
        d = d[d["sym"].isin(sy_e)]
        if d.empty:
            continue
        frames.append(d)
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "bid", "ask"])
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["sym"].str[:-2]
    for c in ("bid", "ask"):
        out[c] = pd.to_numeric(out[c].str.replace(",", ".", regex=False), errors="coerce")
    return out.drop(columns=["sym"]).sort_values(["symbol", "date"]).reset_index(drop=True)


def daily_proportional_spread(quotes_long: pd.DataFrame) -> pd.DataFrame:
    """Per (date,symbol) proportional quoted spread (ask-bid)/mid (fraction).

    Only days with bid>0, ask>0, ask>=bid (a valid two-sided quote) are kept; all
    other rows (no-quote / crossed / halted) are dropped. Returns long [date, symbol,
    spread]."""
    if quotes_long.empty:
        return pd.DataFrame(columns=["date", "symbol", "spread"])
    q = quotes_long
    bid, ask = q["bid"], q["ask"]
    ok = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask > 0) & (ask >= bid)
    q = q[ok].copy()
    mid = (q["ask"] + q["bid"]) / 2.0
    q["spread"] = (q["ask"] - q["bid"]) / mid
    return q[["date", "symbol", "spread"]].reset_index(drop=True)


def build_quoted_panel(
    symbols, start: str, end: str,
    window: int = _th.D207_QUOTED_WINDOW,
    min_coverage: int = _th.D207_QUOTED_MIN_COVERAGE,
    archive_dir: Path = _ARCHIVE_DIR,
) -> pd.DataFrame:
    """Point-in-time [date x symbol] panel of the trailing-median proportional spread.

    For each (date, symbol): the MEDIAN of the daily (ask-bid)/mid over the trailing
    `window` trading days, requiring >= `min_coverage` valid quote-days in the window
    (else the cell is NaN = "no quote", and the cost harness falls through to the Roll
    fallback). The median is robust to one-day quote outliers. NaNs within the window
    are excluded from the median (pandas rolling skips NaN). Returns a fraction panel."""
    daily = daily_proportional_spread(load_raw_quotes(set(symbols), start, end, archive_dir))
    if daily.empty:
        return pd.DataFrame()
    wide = daily.pivot_table(index="date", columns="symbol", values="spread",
                             aggfunc="last").sort_index()
    return wide.rolling(window, min_periods=min_coverage).median()


def load_or_build_quoted_panel(
    symbols, start: str, end: str,
    window: int = _th.D207_QUOTED_WINDOW,
    min_coverage: int = _th.D207_QUOTED_MIN_COVERAGE,
    cache_path: Path = _DEFAULT_CACHE,
    archive_dir: Path = _ARCHIVE_DIR,
    rebuild: bool = False,
) -> pd.DataFrame:
    """Load the cached quoted-spread panel, or build + cache it (gitignored parquet).

    The cache is keyed implicitly by (window, min_coverage, universe, span) -- pass
    rebuild=True after changing any of those. Returns the columns intersecting
    `symbols`. Build is the slow path (archive CSV parse); cache load is instant."""
    cache_path = Path(cache_path)
    if cache_path.exists() and not rebuild:
        panel = pd.read_parquet(cache_path)
        panel.index = pd.to_datetime(panel.index)
        keep = [c for c in panel.columns if c in set(symbols)]
        return panel[keep] if keep else panel
    panel = build_quoted_panel(symbols, start, end, window, min_coverage, archive_dir)
    if not panel.empty:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(cache_path)
    return panel
