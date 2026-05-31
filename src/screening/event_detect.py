"""D-188 -- catalyst-event detection (pure functions over injected data).

E1 (earnings): REAL YoY surprise (TUFE-deflated) from a fundamentals frame shaped
like src/data/kap_historical_fetcher.fetch_fr_history output
(cols: ticker, year, period, net_income, revenue, ..., publication_date).
  real_yoy = (1 + nominal_yoy) / (1 + cpi_yoy) - 1
where nominal_yoy compares the same fiscal period year-over-year and cpi_yoy uses
TUFE at the two publication dates. The event_date is publication_date (look-ahead
correct: the date the figure became public). High-surprise = real_yoy >= threshold,
prior-year base positive (sign flips make YoY meaningless).

E2 (index inclusion) / E3 (material KAP): no frozen HISTORICAL source -> honest
data_pending stubs (forward capture is handled by the forward recorder).

No network here; the runner fetches and injects. No composite/engine imports.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from src.screening.event_config import (
    SURPRISE_CORROBORATING_FIELD,
    SURPRISE_HIGH_THRESHOLD,
    SURPRISE_PRIMARY_FIELD,
    SURPRISE_REQUIRE_POSITIVE_BASE,
)


def _cpi_at(tufe: pd.Series | None, date) -> float:
    if tufe is None or len(tufe) == 0:
        return float("nan")
    v = tufe.asof(pd.Timestamp(date))
    return float(v) if v == v else float("nan")  # NaN-safe


def _real_yoy(val_t, val_prev, cpi_t, cpi_prev) -> float:
    """Real YoY growth: nominal YoY deflated by CPI YoY. NaN if base invalid."""
    if not all(np.isfinite([val_t, val_prev, cpi_t, cpi_prev])):
        return float("nan")
    if val_prev <= 0 or cpi_prev <= 0:
        return float("nan")
    nominal_yoy = val_t / val_prev - 1.0
    cpi_yoy = cpi_t / cpi_prev - 1.0
    if (1.0 + cpi_yoy) <= 0:
        return float("nan")
    return (1.0 + nominal_yoy) / (1.0 + cpi_yoy) - 1.0


def detect_earnings_events(
    fundamentals: pd.DataFrame,
    tufe: pd.Series | None,
    threshold: float = SURPRISE_HIGH_THRESHOLD,
    primary_field: str = SURPRISE_PRIMARY_FIELD,
    corroborating_field: str = SURPRISE_CORROBORATING_FIELD,
    require_positive_base: bool = SURPRISE_REQUIRE_POSITIVE_BASE,
) -> list[dict]:
    """High REAL-YoY-surprise earnings events (E1).

    Returns one dict per HIGH-surprise event:
      {ticker, event_date, event_type, surprise_real, surprise_real_corroborating,
       year, period}
    event_date = publication_date (look-ahead safe). Only positive surprises at or
    above `threshold` with a positive prior-year base are returned.
    """
    if fundamentals is None or fundamentals.empty:
        return []
    df = fundamentals.copy()
    needed = {"ticker", "year", "period", "publication_date", primary_field}
    if not needed.issubset(df.columns):
        return []
    df = df.dropna(subset=["ticker", "year", "period", "publication_date"])
    events: list[dict] = []
    for (ticker, period), grp in df.groupby(["ticker", "period"]):
        grp = grp.sort_values("year")
        rows = grp.to_dict("records")
        by_year = {int(r["year"]): r for r in rows if str(r["year"]).isdigit()}
        for yr, row in by_year.items():
            prev = by_year.get(yr - 1)
            if prev is None:
                continue
            ev_date = row["publication_date"]
            prev_date = prev["publication_date"]
            val_t = _num(row.get(primary_field))
            val_prev = _num(prev.get(primary_field))
            if require_positive_base and not (val_prev is not None and val_prev > 0):
                continue
            sr = _real_yoy(val_t, val_prev, _cpi_at(tufe, ev_date), _cpi_at(tufe, prev_date))
            if not np.isfinite(sr) or sr < threshold:
                continue
            # corroborating (revenue) real YoY -- informational, not gating
            cv_t = _num(row.get(corroborating_field))
            cv_prev = _num(prev.get(corroborating_field))
            sr_corr = _real_yoy(cv_t, cv_prev, _cpi_at(tufe, ev_date), _cpi_at(tufe, prev_date)) \
                if (cv_t is not None and cv_prev is not None) else float("nan")
            events.append({
                "ticker": str(ticker),
                "event_date": str(pd.Timestamp(ev_date).date()),
                "event_type": "E1_earnings",
                "surprise_real": round(float(sr), 5),
                "surprise_real_corroborating": round(float(sr_corr), 5) if np.isfinite(sr_corr) else None,
                "year": int(yr),
                "period": str(period),
            })
    events.sort(key=lambda e: (e["event_date"], e["ticker"]))
    return events


def detect_index_inclusion(*_args, **_kwargs) -> tuple[list[dict], bool]:
    """E2 index-inclusion: no frozen HISTORICAL source -> (empty, data_pending=True).

    Forward capture (announcement disclosures) is handled by the forward recorder.
    Backtest requires a separate data-provisioning directive (no fabrication).
    """
    return [], True


def detect_material_kap(*_args, **_kwargs) -> tuple[list[dict], bool]:
    """E3 material-KAP: KAP ODA pagination needs MKK_VYK_TOKEN historically ->
    (empty, data_pending=True). Forward capture via auth-free disclosures."""
    return [], True


def _num(x):
    try:
        if x is None:
            return None
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def probe_data_availability() -> dict:
    """Read-only feasibility probe (env + light checks). Network calls are guarded;
    failures are reported, not raised. Used only by the feasibility script/runner.main.
    """
    out: dict = {
        "mkk_vyk_token_present": bool(os.getenv("MKK_VYK_TOKEN")),
        "mkk_vyk_base_present": bool(os.getenv("MKK_VYK_BASE_URL")),
        "evds_api_key_present": bool(os.getenv("EVDS_API_KEY")),
        "kap4_min_disclosure_index": None,
        "notes": [],
    }
    try:
        from src.data.kap_historical_fetcher import _MIN_DISCLOSURE_INDEX
        out["kap4_min_disclosure_index"] = int(_MIN_DISCLOSURE_INDEX)
        out["notes"].append(
            "KAP-4.0 cutoff: disclosures below this index are html-only (no XBRL) -> "
            "historical earnings depth is bounded below by KAP-4.0 (~2020/21+), not 2019."
        )
    except Exception as exc:  # pragma: no cover - defensive
        out["notes"].append(f"kap_historical_fetcher import failed: {exc}")
    if not out["mkk_vyk_token_present"]:
        out["notes"].append(
            "MKK_VYK_TOKEN absent -> historical earnings fall back to yfinance "
            "fundamentals, where announcement dates are unreliable (look-ahead risk)."
        )
    return out
