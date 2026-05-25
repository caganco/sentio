"""EVDS (Electronic Data Delivery System) native client (D-095).

EVDS is the TCMB data API. Endpoint: https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/
Auth: API key in 'key' request header (obtained from evds3.tcmb.gov.tr).

Usage:
    from src.data.evds_client import fetch_series, fetch_series_df
    data = fetch_series("TP.APIFON4", "1y")     # list of {date, value}
    df   = fetch_series_df("TP.APIFON4", "1y")  # pandas DataFrame

Env:
    EVDS_API_KEY — required. Set in .env or environment.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/"
_DEFAULT_TIMEOUT = 10

_LOOKBACK_WINDOWS: dict[str, int] = {
    "1m": 31,
    "3m": 92,
    "6m": 183,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
}


class EvdsError(RuntimeError):
    """Raised when EVDS API returns an error or unexpected response."""


def fetch_series(
    series_code: str,
    lookback: str = "1y",
    start_date: str | None = None,
    end_date: str | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch an EVDS time series.

    Args:
        series_code: EVDS series code, e.g. "TP.APIFON4" or "TP.TCMB.PFAIZ".
        lookback: Shorthand window ("1m", "3m", "6m", "1y", "2y", "5y").
                  Ignored when start_date/end_date are provided.
        start_date: DD-MM-YYYY format. Overrides lookback.
        end_date:   DD-MM-YYYY format. Defaults to today.
        api_key:    EVDS API key. Reads EVDS_API_KEY env var if not given.

    Returns:
        List of {"date": str (YYYY-MM-DD), "value": float} dicts, newest first.

    Raises:
        EvdsError: On auth failure, unexpected response format, or empty data.
        ValueError: When series_code is empty or lookback is invalid.
    """
    if not series_code:
        raise ValueError("series_code must not be empty")

    key = api_key or os.getenv("EVDS_API_KEY")
    if not key:
        raise EvdsError(
            "EVDS_API_KEY not set. Obtain a free key at https://evds3.tcmb.gov.tr/ "
            "and add it to your .env file."
        )

    # Build date window
    if end_date is None:
        end_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    if start_date is None:
        days_back = _LOOKBACK_WINDOWS.get(lookback)
        if days_back is None:
            raise ValueError(f"Unknown lookback '{lookback}'. Valid: {list(_LOOKBACK_WINDOWS)}")
        dt_start = datetime.now(timezone.utc) - timedelta(days=days_back)
        start_date = dt_start.strftime("%d-%m-%Y")

    url = (
        f"{_BASE_URL}?series={series_code}"
        f"&startDate={start_date}&endDate={end_date}&type=json"
    )
    logger.debug("EVDS fetch: %s [%s → %s]", series_code, start_date, end_date)

    try:
        resp = requests.get(url, headers={"key": key}, timeout=_DEFAULT_TIMEOUT)
    except requests.exceptions.Timeout:
        raise EvdsError(f"EVDS request timed out (series={series_code})")
    except requests.exceptions.RequestException as exc:
        raise EvdsError(f"EVDS network error: {exc}") from exc

    if resp.status_code == 403:
        raise EvdsError("EVDS API key rejected (HTTP 403). Check EVDS_API_KEY.")
    if resp.status_code != 200:
        raise EvdsError(f"EVDS HTTP {resp.status_code} for series={series_code}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise EvdsError(
            f"EVDS returned non-JSON (HTML SPA?) for series={series_code}"
        ) from exc

    observations = body.get("items") or body.get("data") or []
    if not observations:
        raise EvdsError(f"EVDS returned 0 observations for series={series_code}")

    results: list[dict[str, Any]] = []
    for obs in observations:
        date_raw = obs.get("Tarih") or obs.get("tarih") or ""
        value = _extract_numeric(obs)
        if value is None or not date_raw:
            continue
        # Normalise date to YYYY-MM-DD
        date_iso = _normalise_date(date_raw)
        results.append({"date": date_iso, "value": value})

    if not results:
        raise EvdsError(
            f"EVDS series {series_code} had observations but no numeric values — "
            "check the series code"
        )

    results.sort(key=lambda x: x["date"], reverse=True)
    logger.info(
        "EVDS: %s → %d observations (%s … %s)",
        series_code, len(results), results[-1]["date"], results[0]["date"],
    )
    return results


def fetch_latest_value(
    series_code: str,
    lookback: str = "3m",
    api_key: str | None = None,
) -> float:
    """Return the most recent numeric value for a series.

    Raises EvdsError on any failure.
    """
    data = fetch_series(series_code, lookback=lookback, api_key=api_key)
    return data[0]["value"]


def fetch_series_df(
    series_code: str,
    lookback: str = "1y",
    start_date: str | None = None,
    end_date: str | None = None,
    api_key: str | None = None,
):
    """Same as fetch_series but returns a pandas DataFrame.

    Columns: date (datetime64[ns]), value (float64).
    Raises ImportError if pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas required for fetch_series_df") from exc

    data = fetch_series(series_code, lookback, start_date, end_date, api_key)
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_numeric(obs: dict) -> float | None:
    """Extract the first numeric non-metadata field from an EVDS observation."""
    _SKIP = {"Tarih", "tarih", "UNIXTIME", "YEARWEEK"}
    for key, val in obs.items():
        if key in _SKIP:
            continue
        if val in (None, "", "ND"):
            continue
        try:
            return float(str(val).replace(",", "."))
        except (TypeError, ValueError):
            continue
    return None


def _normalise_date(raw: str) -> str:
    """Convert EVDS date strings to YYYY-MM-DD.

    EVDS formats seen: "2024-01-05", "05-01-2024", "2024", "2024-W01".
    """
    raw = raw.strip()
    # Already ISO
    if len(raw) == 10 and raw[4] == "-":
        return raw
    # DD-MM-YYYY
    if len(raw) == 10 and raw[2] == "-" and raw[5] == "-":
        try:
            return datetime.strptime(raw, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Year only
    if len(raw) == 4 and raw.isdigit():
        return f"{raw}-01-01"
    # ISO week YYYY-WNN
    if len(raw) == 8 and raw[4] == "-" and raw[5] == "W":
        try:
            year, week = int(raw[:4]), int(raw[6:])
            d = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Fallback: return as-is
    return raw


def is_series_fresh(data: list[dict[str, Any]], stale_days: int) -> bool:
    """
    Check if the most recent observation in a fetch_series() result is within stale_days.

    Dayanak: D-151, RR-021 §3.3 — freshness gate for monthly EVDS series.

    Args:
        data: list returned by fetch_series() — each item has "date" (ISO string) + "value"
        stale_days: maximum acceptable age in calendar days

    Returns:
        True if last observation is ≤ stale_days old; False if empty, malformed, or stale.

    Examples:
        >>> # Monthly TÜFE: stale if last obs > 45 days ago
        >>> is_series_fresh(data, stale_days=45)
        True
    """
    if not data:
        return False
    try:
        last_date = datetime.fromisoformat(data[-1]["date"]).date()
    except (KeyError, ValueError):
        return False
    age = (datetime.now(timezone.utc).date() - last_date).days
    return age <= stale_days
