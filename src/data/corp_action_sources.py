"""Corporate-action FACTOR sources for the D-202 clean-universe builder.

Keeps all HTTP + disk caching here so ``clean_universe_builder`` stays network-free
and unit-testable via injected data.

LAYER-1 (yfinance, free, primary)
    ``fetch_yf_corp_actions(ticker)`` -> ``(splits_df, dividends_df)``.
    Splits are the market-implied adjustment factor for survivors (TERP already
    embedded in the post-event re-pricing); dividends feed the total-return index.
    404 / delisted / any exception -> empty frames (never raises).

LAYER-4 (KAP MKK-VYK residual, opt-in, budgeted)
    ``fetch_kap_ca_residual(ticker, client, company_map, budget)`` -> ``list[dict]``.
    Per-companyId only (no blind pagination -- the endpoint is IP-rate-limited, so a
    hard ``_CallBudget`` aborts before we burn our quota). Disk-cached per ticker
    (written even when empty so a reachable-but-eventless symbol is not re-fetched).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"

# Shared 1 req/sec limiter -- same Yahoo soft-limit budget used elsewhere.
from src.data._hub_sources import _rl_yfinance  # noqa: E402

_SPLITS_COLS = ["date", "symbol", "ratio"]
_DIVIDENDS_COLS = ["ex_date", "symbol", "amount_per_share"]

# long-format cache schema: kind in {"split", "dividend"}
_CACHE_COLS = ["kind", "date", "symbol", "value"]


# ---------------------------------------------------------------------------
# LAYER-1: yfinance splits + dividends
# ---------------------------------------------------------------------------

def fetch_yf_corp_actions(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """yfinance ``.splits`` + ``.dividends`` for ``{ticker}.IS``.

    Returns ``(splits_df, dividends_df)``:
        splits_df    columns ``["date", "symbol", "ratio"]`` -- ratio R is the
                     R-for-1 split factor (e.g. 2.0, 7.0); the builder converts to a
                     back-adjust factor via ``1.0 / R``.
        dividends_df columns ``["ex_date", "symbol", "amount_per_share"]``.

    Delisted (404) / any error -> two empty frames. Never raises.
    """
    long_df = _load_all(ticker)
    if long_df.empty:
        return (
            pd.DataFrame(columns=_SPLITS_COLS),
            pd.DataFrame(columns=_DIVIDENDS_COLS),
        )

    splits = long_df[long_df["kind"] == "split"]
    splits_df = pd.DataFrame(
        {
            "date": pd.to_datetime(splits["date"]).dt.date,
            "symbol": splits["symbol"].astype(str),
            "ratio": splits["value"].astype(float),
        }
    ).reset_index(drop=True)

    divs = long_df[long_df["kind"] == "dividend"]
    dividends_df = pd.DataFrame(
        {
            "ex_date": pd.to_datetime(divs["date"]).dt.date,
            "symbol": divs["symbol"].astype(str),
            "amount_per_share": divs["value"].astype(float),
        }
    ).reset_index(drop=True)

    return splits_df, dividends_df


def _load_all(ticker: str) -> pd.DataFrame:
    """Long-format splits+dividends for one ticker, disk-cached (no TTL; historical).

    Cache: ``data/cache/yf_ca_{ticker}.parquet`` with columns
    ``["kind", "date", "symbol", "value"]``. Corrupt cache -> unlink + re-fetch.
    """
    cache_path = _CACHE_DIR / f"yf_ca_{ticker}.parquet"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        try:
            return pd.read_parquet(cache_path)
        except Exception as exc:
            logger.warning("yf CA cache okunamadi: ticker=%s %s", ticker, exc)
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

    rows = _fetch_yf_rows(ticker)
    df = pd.DataFrame(rows, columns=_CACHE_COLS)
    try:
        df.to_parquet(cache_path, index=False)
    except Exception as exc:
        logger.warning("yf CA cache yazilamadi: ticker=%s %s", ticker, exc)
    return df


def _fetch_yf_rows(ticker: str) -> list[dict[str, Any]]:
    """yfinance API call: splits + dividends -> long rows. [] on 404/exception."""
    _rl_yfinance.wait()
    try:
        import yfinance as yf

        t = yf.Ticker(f"{ticker}.IS")
        splits = t.splits
        dividends = t.dividends
    except Exception as exc:
        logger.warning("yfinance CA fetch hatasi: ticker=%s %s", ticker, exc)
        return []

    rows: list[dict[str, Any]] = []
    for kind, series in (("split", splits), ("dividend", dividends)):
        if series is None or len(series) == 0:
            continue
        for idx, value in series.items():
            try:
                val = float(value)
            except (TypeError, ValueError):
                continue
            if val <= 0:
                continue
            # idx is a tz-aware Timestamp; strip tz, keep date.
            ts = pd.Timestamp(idx)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            rows.append(
                {
                    "kind": kind,
                    "date": ts.date(),
                    "symbol": ticker,
                    "value": val,
                }
            )
    return rows


# ---------------------------------------------------------------------------
# LAYER-4: KAP MKK-VYK residual (opt-in, hard call budget)
# ---------------------------------------------------------------------------

class _BudgetExceeded(RuntimeError):
    """Raised when a KAP call would exceed the hard request budget."""


class _CallBudget:
    """Hard cap on outbound KAP calls. The endpoint is IP-rate-limited, so we never
    blind-paginate -- once ``limit`` calls are spent, ``spend()`` raises and the
    caller marks the remainder ``kap-budget-exhausted``.
    """

    def __init__(self, limit: int = 40) -> None:
        self.limit = limit
        self.count = 0

    def spend(self, n: int = 1) -> None:
        if self.count + n > self.limit:
            raise _BudgetExceeded(
                f"KAP call budget exhausted (limit={self.limit}, spent={self.count})"
            )
        self.count += n


# KAP CA-form fields that distinguish bedelsiz (bonus) from bedelli (rights).
_KAP_CA_FIELDS = (
    "subProcessName",
    "preemtiveRightsPercentage",
    "internalResourcesBonusPercentage",
)


def fetch_kap_ca_residual(
    ticker: str,
    client: Any,
    company_map: dict[str, str],
    budget: _CallBudget,
    *,
    disclosure_class: str = "CA",
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """KAP corporate-action records for one residual ``ticker``. Opt-in (LAYER-4).

    ``company_map`` is companyId(str) -> stockCode(ticker), as returned by
    ``build_company_map()``. We invert it to find this ticker's companyId and query
    KAP *per-companyId only*; if the ticker is not in the map (not a KAP member -- e.g.
    HALKS/IDEAS/ITTFH) it is unreachable -> ``[]`` at zero cost.

    Every outbound call is metered through ``budget``; on ``_BudgetExceeded`` we
    return what we have so far. Disk-cached at ``data/cache/kap_ca_{ticker}.parquet``
    (written even when empty so reachable-but-eventless tickers are not re-fetched).

    Returns ``list[dict]`` with at least ``_KAP_CA_FIELDS`` per event.
    """
    cache_path = _CACHE_DIR / f"kap_ca_{ticker}.parquet"
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        try:
            cached = pd.read_parquet(cache_path)
            return cached.to_dict("records")
        except Exception as exc:
            logger.warning("kap CA cache okunamadi: ticker=%s %s", ticker, exc)
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

    company_id = _company_id_for(ticker, company_map)
    records: list[dict[str, Any]] = []
    if company_id is None:
        logger.info("KAP residual: %s KAP uyesi degil -> unreachable", ticker)
        _write_kap_cache(cache_path, records)
        return records

    try:
        start_index = 0
        for _ in range(max_pages):
            budget.spend()
            page = client.get_disclosures(
                start_index=start_index,
                disclosure_class=disclosure_class,
                company_id=int(company_id),
            )
            if not page:
                break
            for item in page:
                rec = {f: item.get(f) for f in _KAP_CA_FIELDS}
                rec["symbol"] = ticker
                rec["disclosure_index"] = item.get("disclosureIndex") or item.get("index")
                records.append(rec)
            start_index = _next_start_index(page, start_index)
            if start_index is None:
                break
    except _BudgetExceeded:
        logger.warning("KAP residual: %s -> budget exhausted mid-fetch", ticker)
    except Exception as exc:
        logger.warning("KAP residual fetch hatasi: ticker=%s %s", ticker, exc)

    _write_kap_cache(cache_path, records)
    return records


def _company_id_for(ticker: str, company_map: dict[str, str]) -> str | None:
    for company_id, stock_code in company_map.items():
        if stock_code == ticker:
            return company_id
    return None


def _next_start_index(page: list[dict[str, Any]], current: int) -> int | None:
    indices = [
        it.get("disclosureIndex") or it.get("index")
        for it in page
        if (it.get("disclosureIndex") or it.get("index")) is not None
    ]
    if not indices:
        return None
    nxt = max(int(i) for i in indices) + 1
    return nxt if nxt > current else None


def _write_kap_cache(cache_path: Path, records: list[dict[str, Any]]) -> None:
    try:
        cols = list(_KAP_CA_FIELDS) + ["symbol", "disclosure_index"]
        df = pd.DataFrame(records, columns=cols) if records else pd.DataFrame(columns=cols)
        df.to_parquet(cache_path, index=False)
    except Exception as exc:
        logger.warning("kap CA cache yazilamadi: %s %s", cache_path.name, exc)
