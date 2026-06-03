"""Universal fundamentals freeze for the D-202 clean universe. D-203 FAZ-0.

Builds a frozen, content-hashed, survivorship-clean fundamental-ratio panel for the
681-symbol D-202 clean universe, sourced from the UNIVERSAL datastore archive
(`bist_datastore_archive/fundamental_ratios/degoran_M_YYYYMM.zip`) -- NOT from any
lab-local / survivor-only / D-200-broken copy. Read-only on the archive.

Each monthly zip holds one oranYYYYMM.xlsx of per-stock month-end fundamental ratios
in one of two layouts (modern 13-col with '.E' tickers, or legacy 15-col bare codes).
We parse both, strip the '.E' suffix to match the D-202 bare-code symbols, coerce the
special string codes 'VY' (veri yok) / 'HY' (hesaplanamaz) to NaN, and derive the
value signals (HIGHER = CHEAPER = expected higher forward return):

  ey   = net_profit / market_value     (earnings yield; signed, robust to losses)
  bm   = equity     / market_value     (book-to-market = 1 / PBV)
  dyld = dividend_yield / 100          (TV%)

Output (junctioned single source, git-local, ASCII meta):
  data/clean_universe/fundamentals_2019_2026.parquet  -- long [month, symbol, ...]
  data/clean_universe/_meta_fundamentals.json         -- provenance + content-hash

Coverage: degoran files span 2019-07 .. 2026-04 (publication lag ~mid M+1, so the
month-M snapshot is known at end-M -> consumers must lag >=1 month, look-ahead safe).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
CLEAN_UNIVERSE_ROOT = _REPO_ROOT / "data" / "clean_universe"
ARCHIVE_FR_DIR = _REPO_ROOT / "data" / "bist_datastore_archive" / "fundamental_ratios"

_PRICES_PARQUET = CLEAN_UNIVERSE_ROOT / "adjusted_prices_2019_2026.parquet"
_FUND_PARQUET = CLEAN_UNIVERSE_ROOT / "fundamentals_2019_2026.parquet"
_FUND_META = CLEAN_UNIVERSE_ROOT / "_meta_fundamentals.json"

_TICKER_E_RE = re.compile(r"^[A-Z0-9]{2,6}\.E$")    # modern col1: 'AKBNK.E'
_TICKER_RE = re.compile(r"^[A-Z0-9]{3,6}$")          # legacy col0 / bare code: 'AKBNK'

RAW_COLS = ["mktval", "net_profit", "equity", "net_div", "pe", "pbv", "dy"]
DERIVED_COLS = ["ey", "bm", "dyld"]
FUND_COLS = ["month", "symbol"] + RAW_COLS + DERIVED_COLS

# column index of each RAW_COL in the two archive layouts
_MODERN = {"ticker": 1, "mktval": 6, "net_profit": 7, "equity": 8, "net_div": 9,
           "pe": 10, "pbv": 11, "dy": 12}                      # 13-col, ticker '.E'
_LEGACY = {"ticker": 0, "mktval": 3, "net_profit": 4, "net_div": 6, "equity": 7,
           "pe": 10, "dy": 12, "pbv": 14}                      # 15-col, ticker no '.E'


def _extract(raw: pd.DataFrame, layout: dict, strip_e: bool) -> pd.DataFrame:
    """Pull the RAW_COLS out of one raw sheet under a given column layout.

    Drops sector/total header rows (non-ticker col or non-positive market value).
    'VY'/'HY' and any other non-numeric coerce to NaN via pd.to_numeric.
    """
    tick = raw[layout["ticker"]].astype(str).str.strip()
    tick = tick.str.replace(r"\.E$", "", regex=True) if strip_e else tick
    mval = pd.to_numeric(raw[layout["mktval"]], errors="coerce")
    mask = tick.str.match(_TICKER_RE) & (mval > 0)
    df = pd.DataFrame({"symbol": tick[mask]})
    for c in RAW_COLS:
        df[c] = pd.to_numeric(raw[layout[c]], errors="coerce")[mask]
    return df


def _read_one(fp: Path) -> pd.DataFrame | None:
    """Parse one degoran_M_YYYYMM.zip -> long rows [month, symbol, RAW_COLS] or None."""
    try:
        z = zipfile.ZipFile(fp)
    except Exception:  # noqa: BLE001 - corrupt zip must not break the freeze
        return None
    inner = [x for x in z.namelist() if x.lower().endswith((".xls", ".xlsx"))]
    if not inner:
        return None
    try:
        raw = pd.read_excel(io.BytesIO(z.read(inner[0])), header=None)
    except Exception:  # noqa: BLE001
        return None
    if raw.shape[1] < 13:
        return None
    if raw[1].astype(str).str.strip().str.match(_TICKER_E_RE).any():
        df = _extract(raw, _MODERN, strip_e=True)
    elif raw.shape[1] >= 15:
        df = _extract(raw, _LEGACY, strip_e=False)
    else:
        return None
    if df.empty:
        return None
    m = re.search(r"(\d{6})", fp.stem)
    if not m:
        return None
    ym = m.group(1)
    df["month"] = pd.Period(f"{ym[:4]}-{ym[4:]}", freq="M")
    return df[["month", "symbol"] + RAW_COLS]


def _derive(long: pd.DataFrame) -> pd.DataFrame:
    """Add ey / bm / dyld value signals (market_value=0 -> NaN to avoid inf)."""
    mv = long["mktval"].replace(0, np.nan)
    long = long.copy()
    long["ey"] = long["net_profit"] / mv
    long["bm"] = long["equity"] / mv
    long["dyld"] = long["dy"] / 100.0
    return long


def load_degoran_fundamentals(
    archive_fr_dir: Path | str = ARCHIVE_FR_DIR,
    start: str = "2019-01",
    end: str = "2026-12",
    file_glob: str = "degoran_M_*.zip",
) -> pd.DataFrame:
    """Concatenate all degoran monthly files in [start, end] -> long fundamentals.

    Read-only on the universal archive. Raises if no files parse in range.

    file_glob defaults to the modern 'degoran_M_YYYYMM.zip' monthly files (2019-07+,
    the D-203/204 frozen window) -- keeping the default preserves those content-hashes.
    Pass 'degoran*.zip' to ALSO include the legacy 'degoranYYYYMM.zip' monthly files
    (2009-01..2019-06); 4-digit annual 'degoranYYYY.zip' are skipped (no 6-digit month).
    When both namings exist for one month, the modern '_M_' file wins (dedup).
    """
    fr_dir = Path(archive_fr_dir)
    p0, p1 = pd.Period(start, "M"), pd.Period(end, "M")
    by_period: dict[pd.Period, Path] = {}
    for fp in sorted(fr_dir.glob(file_glob)):
        m = re.search(r"(\d{6})", fp.stem)
        if not m:
            continue
        mm = int(m.group(1)[4:])
        if mm < 1 or mm > 12:        # skip year-aggregate files (e.g. 'degoran201500.zip')
            continue
        per = pd.Period(f"{m.group(1)[:4]}-{m.group(1)[4:]}", "M")
        if per < p0 or per > p1:
            continue
        prev = by_period.get(per)
        if prev is None or ("_M_" in fp.stem and "_M_" not in prev.stem):
            by_period[per] = fp
    rows: list[pd.DataFrame] = []
    for per in sorted(by_period):
        one = _read_one(by_period[per])
        if one is not None:
            rows.append(one)
    if not rows:
        raise RuntimeError(f"no degoran fundamental-ratios files parsed in {start}..{end} under {fr_dir}")
    return _derive(pd.concat(rows, ignore_index=True))


def load_universe_symbols(prices_parquet: Path | str = _PRICES_PARQUET) -> list[str]:
    """The 681 D-202 clean-universe symbols (bare codes)."""
    px = pd.read_parquet(prices_parquet, columns=["symbol"])
    return sorted(px["symbol"].astype(str).unique())


def content_hash_fundamentals(df: pd.DataFrame) -> str:
    """Deterministic SHA256, sorted by [symbol, month]. Mirrors clean_universe_builder."""
    canon = df.copy()
    canon["month"] = canon["month"].astype(str)
    canon = canon.sort_values(["symbol", "month"]).reset_index(drop=True)
    csv_bytes = canon.to_csv(index=False, float_format="%.10g").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def build_and_freeze_fundamentals(
    clean_root: Path | str = CLEAN_UNIVERSE_ROOT,
    archive_fr_dir: Path | str = ARCHIVE_FR_DIR,
    prices_parquet: Path | str = _PRICES_PARQUET,
    start: str = "2019-01",
    end: str = "2026-12",
    force_rebuild: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Freeze (or load) the universal fundamentals panel aligned to the 681 D-202 symbols.

    Idempotent: if the parquet + meta exist and not force_rebuild, load and return.
    Output is git-local (junctioned single source); meta is ASCII.
    """
    clean_root = Path(clean_root)
    fund_pq = clean_root / "fundamentals_2019_2026.parquet"
    fund_meta = clean_root / "_meta_fundamentals.json"
    if fund_pq.exists() and fund_meta.exists() and not force_rebuild:
        df = pd.read_parquet(fund_pq)
        meta = json.loads(fund_meta.read_text(encoding="utf-8"))
        logger.info("[clean-fund] frozen-load: %s (%d rows)", fund_pq.name, len(df))
        return df, meta

    universe = load_universe_symbols(prices_parquet)
    raw = load_degoran_fundamentals(archive_fr_dir, start, end)
    uni_set = set(universe)
    aligned = raw[raw["symbol"].isin(uni_set)].copy()
    aligned = aligned[FUND_COLS].sort_values(["symbol", "month"]).reset_index(drop=True)

    chash = content_hash_fundamentals(aligned)
    months = sorted(aligned["month"].astype(str).unique())
    covered = sorted(aligned["symbol"].unique())
    missing = sorted(uni_set - set(covered))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "schema_version": 1,
        "directive": "D-203",
        "phase": "FAZ-0 universal fundamentals freeze",
        "timestamp_utc": ts,
        "source": "bist_datastore_archive/fundamental_ratios/degoran_M_*.zip (universal, read-only)",
        "publication_lag_note": "degoran month-M known at end-M; consumers must lag >=1 month (look-ahead safe)",
        "value_signals": {"ey": "net_profit/market_value", "bm": "equity/market_value (=1/PBV)",
                          "dyld": "dividend_yield/100"},
        "n_rows": int(len(aligned)),
        "n_months": len(months),
        "month_min": months[0] if months else None,
        "month_max": months[-1] if months else None,
        "content_hash_fundamentals": chash,
        "universe_n": len(universe),
        "covered_n": len(covered),
        "missing_n": len(missing),
        "missing_symbols": missing,
    }
    clean_root.mkdir(parents=True, exist_ok=True)
    aligned.to_parquet(fund_pq, index=False)
    fund_meta.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    logger.info("[clean-fund] frozen: %s rows=%d months=%d covered=%d/%d hash=%s",
                fund_pq.name, len(aligned), len(months), len(covered), len(universe), chash[:12])
    return aligned, meta


def verify_frozen_fundamentals(clean_root: Path | str = CLEAN_UNIVERSE_ROOT) -> bool:
    """Recompute the content-hash of the frozen parquet and compare to the meta. """
    clean_root = Path(clean_root)
    df = pd.read_parquet(clean_root / "fundamentals_2019_2026.parquet")
    meta = json.loads((clean_root / "_meta_fundamentals.json").read_text(encoding="utf-8"))
    recomputed = content_hash_fundamentals(df)
    ok = recomputed == meta.get("content_hash_fundamentals")
    logger.info("[clean-fund] verify hash %s: stored=%s recomputed=%s",
                "OK" if ok else "MISMATCH",
                str(meta.get("content_hash_fundamentals"))[:12], recomputed[:12])
    return ok
