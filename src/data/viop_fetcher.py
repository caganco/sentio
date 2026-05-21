"""BIST VIOP (derivatives) CSV fetcher — T+1 EOD signals.

Downloads viop_YYYYMMDD.csv and viopgs_YYYYMMDD.csv from the BIST public
data portal. Computes per-ticker open interest totals, Put/Call ratio, and
day-over-day OI delta. No browser required — plain requests + pandas.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests

from src.signals.thresholds import VIOP_MIN_OI, VIOP_STALE_DAYS  # noqa: F401 (re-exported)

logger = logging.getLogger(__name__)

_BASE_URL = "https://borsaistanbul.com/data/vadeli/"
_TIMEOUT = 10
_HEADERS = {"Referer": "https://borsaistanbul.com"}

# Fuzzy column-name fragments for CSV column detection
_OI_FRAGMENTS = ("açık pozisyon", "acik pozisyon", "open interest")
_NAME_FRAGMENTS = ("sözleşme", "sozlesme", "kontrat", "kod", "contract")

# Contract naming regex: {TICKER}[EF]{YYMM}[CP?]{STRIKE?}
# Examples:
#   THYAOE0626C110  → ticker=THYAO, type=C, expiry=0626, strike=110
#   THYAOE0626P100  → ticker=THYAO, type=P
#   XU030F0626      → ticker=XU030, type=F (futures, no strike)
_CONTRACT_RE = re.compile(r'^([A-Z0-9]{3,7})[EF](\d{4})([CP]?)(.*)$')


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _last_trading_day(ref: Optional[date] = None) -> date:
    """Return the most recent weekday strictly before *ref* (defaults to today)."""
    d = (ref or date.today()) - timedelta(days=1)
    while d.weekday() >= 5:  # Saturday=5, Sunday=6
        d -= timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# CSV download
# ---------------------------------------------------------------------------

def _download_csv(filename: str) -> Optional[pd.DataFrame]:
    """Generic BIST CSV downloader. Returns DataFrame or None on any failure."""
    url = _BASE_URL + filename
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        if resp.status_code != 200:
            logger.warning("viop_fetcher: HTTP %d for %s", resp.status_code, filename)
            return None
        # BIST legacy encoding: windows-1254; separator: semicolon
        df = pd.read_csv(
            io.BytesIO(resp.content),
            encoding="windows-1254",
            sep=";",
            thousands=".",
            decimal=",",
        )
        logger.info("viop_fetcher: fetched %d rows from %s", len(df), filename)
        return df
    except Exception as exc:
        logger.error("viop_fetcher: failed to fetch %s — %s", filename, exc)
        return None


def fetch_viop_csv(target_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Download full VIOP bulletin (all contracts, all series) for *target_date*.

    Defaults to the most recent trading day (T-1). Returns None on failure.
    """
    d = target_date or _last_trading_day()
    return _download_csv(f"viop_{d:%Y%m%d}.csv")


def fetch_viopgs_csv(target_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Download VIOP day-end series summary (viopgs) for *target_date*.

    Defaults to the most recent trading day (T-1). Returns None on failure.
    """
    d = target_date or _last_trading_day()
    return _download_csv(f"viopgs_{d:%Y%m%d}.csv")


# ---------------------------------------------------------------------------
# Contract name parsing
# ---------------------------------------------------------------------------

def parse_contract_symbol(contract_name: str) -> Optional[dict]:
    """Extract ticker, option type, expiry, and strike from a BIST contract name.

    Returns a dict with keys {ticker, type, expiry, strike} or None if the
    name does not match the expected pattern.

    Option type values: 'C' (call), 'P' (put), 'F' (futures).
    """
    m = _CONTRACT_RE.match(contract_name.strip().upper())
    if not m:
        return None
    ticker, expiry, opt_type, strike = m.groups()
    return {
        "ticker": ticker,
        "type": opt_type if opt_type else "F",
        "expiry": expiry,
        "strike": strike,
    }


# ---------------------------------------------------------------------------
# OI aggregation
# ---------------------------------------------------------------------------

def _detect_column(df: pd.DataFrame, fragments: tuple[str, ...]) -> Optional[str]:
    """Return the first column whose lowercased name contains any of *fragments*."""
    for col in df.columns:
        col_lower = col.lower()
        if any(frag in col_lower for frag in fragments):
            return col
    return None


def _safe_float(value: object) -> float:
    """Parse a numeric string that may use Turkish formatting (. thousands, , decimal)."""
    try:
        return float(str(value).replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def compute_ticker_oi(df: pd.DataFrame, symbol: str) -> dict[str, float]:
    """Aggregate open interest by option type for *symbol*.

    Returns ``{call_oi, put_oi, total_oi}``. All values are 0.0 if the symbol
    has no contracts in *df* or if required columns cannot be detected.
    """
    name_col = _detect_column(df, _NAME_FRAGMENTS)
    oi_col = _detect_column(df, _OI_FRAGMENTS)

    if name_col is None or oi_col is None:
        logger.warning(
            "viop_fetcher: required columns not found. Available: %s", list(df.columns)
        )
        return {"call_oi": 0.0, "put_oi": 0.0, "total_oi": 0.0}

    ticker = symbol.replace(".IS", "").upper()
    call_oi = put_oi = 0.0

    for _, row in df.iterrows():
        parsed = parse_contract_symbol(str(row[name_col]))
        if not parsed or parsed["ticker"] != ticker:
            continue
        oi = _safe_float(row[oi_col]) if pd.notna(row[oi_col]) else 0.0
        if parsed["type"] == "C":
            call_oi += oi
        elif parsed["type"] == "P":
            put_oi += oi
        # Futures ("F") are not counted in put/call ratio

    return {"call_oi": call_oi, "put_oi": put_oi, "total_oi": call_oi + put_oi}


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------

def compute_pc_ratio(oi_data: dict[str, float]) -> float:
    """Put/Call OI ratio.

    - ``< 1.0`` = more calls outstanding → bullish derivatives positioning.
    - ``> 1.0`` = more puts outstanding → bearish/hedge positioning.
    - Returns ``float('inf')`` when call_oi == 0 and put_oi > 0.
    - Returns ``1.0`` (neutral) when both are zero.
    """
    call_oi = oi_data.get("call_oi", 0.0)
    put_oi = oi_data.get("put_oi", 0.0)
    if call_oi == 0.0:
        return float("inf") if put_oi > 0.0 else 1.0
    return put_oi / call_oi


def compute_oi_delta(today_oi: dict[str, float], yesterday_oi: dict[str, float]) -> float:
    """Fractional change in total OI from yesterday to today.

    Returns 0.0 when yesterday total OI is zero (avoids division by zero).
    Positive = OI growing; negative = OI shrinking.
    """
    today_total = today_oi.get("total_oi", 0.0)
    yest_total = yesterday_oi.get("total_oi", 0.0)
    if yest_total == 0.0:
        return 0.0
    return (today_total - yest_total) / yest_total
