"""BIST DataStore haftalık short interest CSV connector (D-058)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from io import StringIO

import pandas as pd
import requests

from src.signals.layers.connectors.smart_money_connector import HealthStatus

logger = logging.getLogger(__name__)

BIST_DATASTORE_URL = "https://datastore.borsaistanbul.com/"  # public, lisanssız


@dataclass(frozen=True)
class ShortInterestPoint:
    symbol: str
    week: date
    short_volume_ratio: float  # % of free float
    fetched_at: datetime = field(default_factory=datetime.utcnow)


class BISTDataStoreConnector:
    """Connects to BIST DataStore for weekly short interest ratios."""

    def __init__(self, timeout: float = 20.0, stale_days: int = 10):
        self._timeout = timeout
        self._stale_days = stale_days
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0"})
        self._last_fetch: datetime | None = None
        self._cache: dict[str, float] = {}

    def fetch_weekly_csv(self, week: date) -> pd.DataFrame:
        """CSV'yi indir, DataFrame döndür. Hata halinde boş DataFrame."""
        try:
            resp = self._session.get(BIST_DATASTORE_URL, timeout=self._timeout)
            resp.raise_for_status()
            self._last_fetch = datetime.utcnow()
            return pd.read_csv(StringIO(resp.text))
        except Exception as exc:
            logger.warning("BISTDataStore fetch failed: %s", exc)
            return pd.DataFrame()

    def parse_short_interest(self, df: pd.DataFrame) -> dict[str, float]:
        """DataFrame → {symbol: short_volume_ratio}. Geçersiz satırları atla."""
        result: dict[str, float] = {}
        if df.empty:
            return result
        for _, row in df.iterrows():
            try:
                symbol = str(row.get("symbol", row.get("Sembol", ""))).strip()
                ratio = float(row.get("short_volume_ratio", row.get("AcigaSatisOrani", 0)))
                if symbol and 0.0 <= ratio <= 100.0:
                    result[symbol] = ratio
            except (TypeError, ValueError):
                continue
        return result

    def is_stale(self) -> bool:
        """Check if last fetch is older than stale_days."""
        if self._last_fetch is None:
            return True
        return (datetime.utcnow() - self._last_fetch) > timedelta(days=self._stale_days)

    def health_check(self) -> HealthStatus:
        """Check if BIST DataStore is accessible."""
        try:
            resp = self._session.get(BIST_DATASTORE_URL, timeout=5.0)
            ok = resp.status_code == 200
            return HealthStatus(
                healthy=ok,
                latency_ms=0.0,
                error=None if ok else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            return HealthStatus(healthy=False, latency_ms=0.0, error=str(exc))
