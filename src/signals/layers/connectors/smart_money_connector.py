"""Smart Money L5 connector: ABC + İş Yatırım screener implementation.

Endpoint: getScreenerDataNEW
Criterion 40 = Cari Yabancı Oranı (%)
Criterion 44 = 1 Haftalık Değişim (bps)
Criterion 45 = 1 Aylık Değişim (bps)
Criterion 26 = 3 Aylık Hacim (mn USD) — for ADV filter

No login required. Rate limit: max 30 req/min (1-2s jitter).
Soft-block: HTTP 200 + empty response → explicit ALERT, never silent.
"""
from __future__ import annotations

import abc
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

logger = logging.getLogger(__name__)


class DataFreshness(StrEnum):
    T_PLUS_1 = "t_plus_1"
    EOD = "eod"


@dataclass(frozen=True, slots=True)
class ForeignRatioPoint:
    """Immutable foreign ownership snapshot for a single ticker."""
    symbol: str
    as_of: date
    foreign_ratio: Decimal           # 0–100 %
    free_float_ratio: Decimal | None
    source: str                      # "isyatirim_screener" | "finnet" | "mock"
    fetched_at: datetime
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Pipeline health snapshot."""
    healthy: bool
    latency_ms: float
    last_successful_fetch: datetime | None
    error: str | None = None

_SCREENER_URL = (
    "https://www.isyatirim.com.tr/tr-tr/analiz/_Layouts/15/IsYatirim.Website/"
    "StockInfo/CompanyInfoAjax.aspx/getScreenerDataNEW"
)
_PAGE_URL = (
    "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/"
    "gelismis-hisse-arama.aspx"
)

_CRIT_FOREIGN_RATIO = "40"
_CRIT_CHANGE_1W = "44"
_CRIT_CHANGE_1M = "45"
_CRIT_VOLUME_3M = "26"


class SmartMoneyConnectorBase(abc.ABC):
    """Abstract base for Smart Money data sources."""

    @abc.abstractmethod
    def fetch_all_tickers(self) -> dict[str, dict]:
        """
        Fetch current foreign ownership snapshot for all BIST tickers.

        Returns: {
            "AKBNK": {
                "foreign_ratio":     25.3,   # Cari Yabancı Oranı (%)
                "change_1w_bps":    -15.0,   # 1w change in basis points
                "change_1m_bps":    -32.0,   # 1m change in basis points
                "volume_3m_mn_usd":  42.5,   # 3-month avg volume (mn USD)
            },
            ...
        }
        Returns {} on any failure. Never returns None.
        Implementations MUST log ALERT on empty/soft-block responses.
        """

    @abc.abstractmethod
    def is_healthy(self) -> bool:
        """Check if data source is reachable. Must not raise."""


class IsYatirimScreenerConnector(SmartMoneyConnectorBase):
    """
    İş Yatırım getScreenerDataNEW → foreign ownership for all BIST.

    Covers ~520 BIST tickers. T+1 data (updated each morning).
    Soft-block detection: HTTP 200 + empty body is an alert condition.
    """

    _RATE_JITTER = (1.0, 2.0)

    def __init__(self, timeout: float = 15.0):
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.isyatirim.com.tr",
            "Referer": _PAGE_URL,
        })
        self._timeout = timeout
        self._ready = False

    def _init_session(self) -> None:
        if self._ready:
            return
        try:
            self._session.get(_PAGE_URL, timeout=self._timeout)
        except Exception as exc:
            logger.warning("IsYatirim session init failed (continuing): %s", exc)
        finally:
            self._ready = True

    def _jitter(self) -> None:
        time.sleep(random.uniform(*self._RATE_JITTER))

    def fetch_all_tickers(self) -> dict[str, dict]:
        self._init_session()
        self._jitter()

        payload = {
            "sektor": "",
            "endeks": "",
            "takip": "",
            "oneri": "",
            "criterias": [
                [_CRIT_FOREIGN_RATIO, "0", "100", "False"],
                [_CRIT_CHANGE_1W, "-10000", "10000", "False"],
                [_CRIT_CHANGE_1M, "-10000", "10000", "False"],
                [_CRIT_VOLUME_3M, "0", "100000", "False"],
            ],
            "lang": "1055",
        }

        try:
            resp = self._session.post(_SCREENER_URL, json=payload, timeout=self._timeout)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("ALERT SmartMoney.fetch_all_tickers: network error — %s", exc)
            return {}

        try:
            outer = resp.json()
        except Exception as exc:
            logger.error("ALERT SmartMoney.fetch_all_tickers: JSON parse failed — %s", exc)
            return {}

        result_str = outer.get("d", "[]")
        try:
            results = json.loads(result_str)
        except Exception as exc:
            logger.error("ALERT SmartMoney.fetch_all_tickers: inner JSON parse failed — %s", exc)
            return {}

        if not results:
            logger.error(
                "ALERT SmartMoney.fetch_all_tickers: soft-block — "
                "HTTP 200 but empty response (rate limit or session expiry). "
                "Caller must use last valid cache."
            )
            return {}

        out: dict[str, dict] = {}
        for item in results:
            hisse = item.get("Hisse", "")
            symbol = hisse.split(" - ", 1)[0].strip() if " - " in hisse else hisse.strip()
            if not symbol:
                continue
            try:
                out[symbol] = {
                    "foreign_ratio":    float(item.get(_CRIT_FOREIGN_RATIO) or 0),
                    "change_1w_bps":    float(item.get(_CRIT_CHANGE_1W) or 0),
                    "change_1m_bps":    float(item.get(_CRIT_CHANGE_1M) or 0),
                    "volume_3m_mn_usd": float(item.get(_CRIT_VOLUME_3M) or 0),
                }
            except (ValueError, TypeError) as exc:
                logger.debug("SmartMoney: skip %s parse error — %s", symbol, exc)

        logger.info("SmartMoney.fetch_all_tickers: %d tickers fetched", len(out))
        return out

    def is_healthy(self) -> bool:
        try:
            resp = self._session.get(_PAGE_URL, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
