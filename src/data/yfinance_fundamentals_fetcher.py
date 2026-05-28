"""yfinance quarterly/annual financials -> fetch_fr_history ile ayni sema. D-175.

Fallback katmani: MKK VYK API bos dondugunde BIST ticker'lari icin
yfinance quarterly/annual finansallari kullanir.

Look-ahead guard (SPK zorunlu bildirim suresi):
  Ceyreklik: period_end + 60 gun -> publication_date
  Yillik:    period_end + 90 gun -> publication_date

Ticker format: ic olarak {ticker}.IS kullanilir.
yfinance alan adlari surume gore degisebilir; prefix (substring) match kullanilir.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"

_QUARTERLY_LAG_DAYS = 60
_ANNUAL_LAG_DAYS = 90

_COLS = [
    "date", "ticker", "year", "period",
    "revenue", "gross_profit", "net_income",
    "total_assets", "equity", "publication_date",
]


def fetch_yf_fundamentals(
    ticker: str,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """yfinance quarterly + annual financials. Bos ise bos DataFrame doner (exception yok).

    Kolonlar: date, ticker, year, period, revenue, gross_profit,
              net_income, total_assets, equity, publication_date.
    """
    df = _load_all(ticker)
    if df.empty:
        return df
    mask = (df["year"].astype(int) >= start_year) & (df["year"].astype(int) <= end_year)
    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_all(ticker: str) -> pd.DataFrame:
    """Tum tarihsel yfinance verisini ceker, cache'e yazar.

    Cache: yf_fund_{ticker}_all.parquet (TTL yok; historical statik).
    """
    cache_path = _CACHE_DIR / f"yf_fund_{ticker}_all.parquet"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        try:
            return pd.read_parquet(cache_path)
        except Exception as exc:
            logger.warning("yf cache okunamadi: ticker=%s %s", ticker, exc)
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

    rows = _fetch_yfinance_rows(ticker)
    if not rows:
        return pd.DataFrame(columns=_COLS)

    df = pd.DataFrame(rows, columns=_COLS)
    try:
        df.to_parquet(cache_path, index=False)
    except Exception as exc:
        logger.warning("yf cache yazilamadi: ticker=%s %s", ticker, exc)
    return df


def _fetch_yfinance_rows(ticker: str) -> list[dict[str, Any]]:
    """yfinance API cagrisini yapar; quarterly + annual verisini birlestir."""
    try:
        import yfinance as yf
        t = yf.Ticker(f"{ticker}.IS")
        qf = t.quarterly_financials
        qbs = t.quarterly_balance_sheet
        af = t.financials
        abs_ = t.balance_sheet
    except Exception as exc:
        logger.warning("yfinance fetch hatasi: ticker=%s %s", ticker, exc)
        return []

    rows: list[dict[str, Any]] = []
    rows.extend(_parse_statements(ticker, qf, qbs, "Ceyreklik", _QUARTERLY_LAG_DAYS))
    rows.extend(_parse_statements(ticker, af, abs_, "Yillik", _ANNUAL_LAG_DAYS))
    return rows


def _parse_statements(
    ticker: str,
    income_stmt: "pd.DataFrame | None",
    balance_sheet: "pd.DataFrame | None",
    period_label: str,
    lag_days: int,
) -> list[dict[str, Any]]:
    """income_stmt + balance_sheet satirlarini _COLS sema satirlarina donusturur."""
    if income_stmt is None or not hasattr(income_stmt, "columns") or income_stmt.empty:
        return []

    rows: list[dict[str, Any]] = []
    for col in income_stmt.columns:
        try:
            period_end = pd.Timestamp(str(col)[:10])
        except Exception:
            continue

        pub_date = (period_end + timedelta(days=lag_days)).strftime("%Y-%m-%d")

        revenue = _get_metric(income_stmt, col, "Total Revenue", "Operating Revenue")
        gross_profit = _get_metric(income_stmt, col, "Gross Profit")
        net_income = _get_metric(income_stmt, col, "Net Income")

        ta = None
        equity = None
        if balance_sheet is not None and hasattr(balance_sheet, "columns") and not balance_sheet.empty:
            if col in balance_sheet.columns:
                ta = _get_metric(balance_sheet, col, "Total Assets")
                equity = _get_metric(balance_sheet, col, "Stockholders Equity", "Total Equity")

        rows.append({
            "date": pub_date,
            "ticker": ticker,
            "year": int(period_end.year),
            "period": period_label,
            "revenue": revenue,
            "gross_profit": gross_profit,
            "net_income": net_income,
            "total_assets": ta,
            "equity": equity,
            "publication_date": pub_date,
        })
    return rows


def _get_metric(df: pd.DataFrame, col: Any, *prefixes: str) -> "float | None":
    """prefix ile eslesen satirdan col degerini float dondurur.

    Yfinance alan adlari surume gore degisir (orn. 'Net Income' vs
    'Net Income Common Stockholders') — prefix (substring) match kullanilir.
    """
    for prefix in prefixes:
        try:
            matches = df.filter(like=prefix, axis=0)
        except Exception:
            continue
        if matches.empty or col not in matches.columns:
            continue
        val = matches[col].dropna()
        if len(val) > 0:
            try:
                return float(val.iloc[0])
            except (ValueError, TypeError):
                continue
    return None
