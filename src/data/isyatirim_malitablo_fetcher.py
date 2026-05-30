"""Is Yatirim MaliTablo (XI_29 / UFRS) financial-statement fetcher. D-183.

Production channel for Faz 0b value-factor fundamentals (RR-032-V3 / D-181 /
D-182 confirmed endpoint). Cross-sectionally consistent (RR-035: Spearman rho=1.0
vs Mynet, 3-source). NOT throwaway -- this is the value data channel.

Endpoint (live-confirmed, RR-032-V3):
    GET .../_Layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo
        ?companyCode=X&exchange=TRY&financialGroup=XI_29
        &year1=Y1&period1=P1 ... &year4=Y4&period4=P4   (4 periods MANDATORY)
    -> JSON rows: {itemCode, itemDescTr, value1..value4}  (value_i = period_i col)

Anti-block (smart_money_connector.py pattern): warm GET + 1-2s jitter + Chrome UA,
no login. /_layouts/ is ToS-gray -> minimum requests, snapshot once. Soft-block
(HTTP 200 + empty) raises an explicit alert, never silent.

No signal/backtest engine imports (screening isolation).
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)

_MALITABLO_URL = (
    "https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/"
    "Data.aspx/MaliTablo"
)
_PAGE_URL = (
    "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/"
    "sirket-karti.aspx"
)
_RATE_JITTER = (1.0, 2.0)
_N_PERIODS = 4   # endpoint requires exactly 4 periods (3 -> empty values)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": _PAGE_URL,
}


class MaliTabloError(Exception):
    """Raised on soft-block / empty / malformed MaliTablo responses (never silent)."""


def _make_session(timeout: float = 20.0):
    import requests

    s = requests.Session()
    s.headers.update(_HEADERS)
    try:                                  # warm GET (cookies / anti-block)
        s.get(_PAGE_URL, timeout=timeout)
    except Exception as exc:              # noqa: BLE001 - warm-up best-effort
        logger.warning("MaliTablo warm GET failed (continuing): %s", exc)
    return s


def _extract_rows(payload: Any) -> list[dict]:
    """Pull the list of statement rows from the JSON payload (defensive).

    Is Yatirim has returned the list under a 'value' key historically; accept a
    bare list too. Each row carries itemCode + a Turkish description + value1..4.
    """
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("value", "d", "data", "Value"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        if rows is None:                  # single list value anywhere
            lists = [v for v in payload.values() if isinstance(v, list)]
            rows = lists[0] if lists else []
    else:
        rows = []
    return [r for r in rows if isinstance(r, dict)]


def _row_name(row: dict) -> str:
    for key in ("itemDescTr", "itemDescEng", "itemDesc", "itemName", "aciklama"):
        v = row.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _row_code(row: dict) -> str:
    for key in ("itemCode", "itemcode", "code", "kod"):
        v = row.get(key)
        if v is not None:
            return str(v).strip()
    return ""


def fetch_malitablo(
    company_code: str,
    periods: list[tuple[int, int]],
    financial_group: str = "XI_29",
    session: Any | None = None,
    timeout: float = 20.0,
) -> list[dict]:
    """Fetch a MaliTablo statement block for one company.

    periods: exactly 4 (year, period) tuples, e.g. [(2025,12),(2024,12),(2023,12),(2022,12)].
    Returns the raw rows (each with itemCode, itemDescTr, value1..value4). Raises
    MaliTabloError on soft-block / empty. period_i (i=1..4) maps to periods[i-1].
    """
    if len(periods) != _N_PERIODS:
        raise MaliTabloError(
            f"MaliTablo requires exactly {_N_PERIODS} periods (3 -> empty); got {len(periods)}"
        )
    own = session is None
    s = session or _make_session(timeout)
    params = {
        "companyCode": company_code.upper(),
        "exchange": "TRY",
        "financialGroup": financial_group,
    }
    for i, (yr, per) in enumerate(periods, start=1):
        params[f"year{i}"] = str(int(yr))
        params[f"period{i}"] = str(int(per))

    time.sleep(random.uniform(*_RATE_JITTER))
    try:
        resp = s.get(_MALITABLO_URL, params=params, timeout=timeout)
    except Exception as exc:              # noqa: BLE001
        raise MaliTabloError(f"MaliTablo GET failed: {company_code}: {exc}") from exc
    finally:
        if own:
            s.close()

    if resp.status_code != 200:
        raise MaliTabloError(f"MaliTablo HTTP {resp.status_code}: {company_code}")
    if not (resp.text or "").strip():
        raise MaliTabloError(f"MaliTablo SOFT-BLOCK (empty body): {company_code}")
    try:
        payload = resp.json()
    except Exception as exc:              # noqa: BLE001
        raise MaliTabloError(f"MaliTablo non-JSON: {company_code}: {exc}") from exc

    rows = _extract_rows(payload)
    if not rows:
        raise MaliTabloError(f"MaliTablo empty rows (soft-block?): {company_code}")
    return rows


def discover_item_codes(
    company_code: str = "THYAO",
    periods: list[tuple[int, int]] | None = None,
    financial_group: str = "XI_29",
) -> list[tuple[str, str]]:
    """Live discovery helper: return [(itemCode, itemDescTr), ...] for mapping.

    Used ONCE during Stage 0 to map the needed leaves (EAOoP, operating profit,
    D&A, total liabilities, cash, issued capital) to their exact itemCodes by
    Turkish name, before freezing the map in faz0_config.
    """
    periods = periods or [(2024, 12), (2023, 12), (2022, 12), (2021, 12)]
    rows = fetch_malitablo(company_code, periods, financial_group)
    return [(_row_code(r), _row_name(r)) for r in rows]


def parse_values(
    rows: list[dict],
    item_codes: dict[str, str],
) -> dict[str, list[float | None]]:
    """Map rows -> {field: [value1..value4]} using a {field: itemCode} mapping.

    Returns one list of 4 period values per requested field; missing -> [None]*4.
    """
    by_code: dict[str, dict] = {_row_code(r): r for r in rows}
    out: dict[str, list[float | None]] = {}
    for field, code in item_codes.items():
        row = by_code.get(str(code))
        vals: list[float | None] = []
        for i in range(1, _N_PERIODS + 1):
            v = row.get(f"value{i}") if row else None
            try:
                vals.append(float(v) if v is not None and str(v) != "" else None)
            except (ValueError, TypeError):
                vals.append(None)
        out[field] = vals
    return out
