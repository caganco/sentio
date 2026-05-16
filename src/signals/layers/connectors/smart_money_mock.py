"""Mock SmartMoneyConnector for testing — returns predefined data."""
from __future__ import annotations

from src.signals.layers.connectors.smart_money_connector import SmartMoneyConnectorBase


class MockSmartMoneyConnector(SmartMoneyConnectorBase):
    """
    Test double for SmartMoneyConnectorBase.

    Pass data={...} for success, data={} (default) to simulate soft-block/failure.
    Pass healthy=False to simulate is_healthy() returning False.
    """

    def __init__(
        self,
        data: dict[str, dict] | None = None,
        healthy: bool = True,
    ):
        self._data = data if data is not None else {}
        self._healthy = healthy

    def fetch_all_tickers(self) -> dict[str, dict]:
        return dict(self._data)

    def is_healthy(self) -> bool:
        return self._healthy


def make_ticker_row(
    foreign_ratio: float = 30.0,
    change_1w_bps: float = 0.0,
    change_1m_bps: float = 0.0,
    volume_3m_mn_usd: float = 100.0,
) -> dict:
    """Helper: build a single-ticker screener row for tests."""
    return {
        "foreign_ratio":    foreign_ratio,
        "change_1w_bps":    change_1w_bps,
        "change_1m_bps":    change_1m_bps,
        "volume_3m_mn_usd": volume_3m_mn_usd,
    }
