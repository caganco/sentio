"""NAV Discount Calculator -- Tier-1 (D-143, RR-013).

Tier-1: listed subsidiaries only (yfinance market_cap x stake_pct).
Private subsidiaries + net_cash_holdco: yaml placeholder (manual input).
No signal engine import (K-08 invariant).

Usage:
    calc = NAVCalculator()
    result = calc.compute_tier1_nav("KCHOL")
    # result["discount_pct"] -> e.g. 0.33 (33% discount)
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import yaml

try:
    import yfinance as yf  # network dependency; mocked in tests
except ImportError:  # pragma: no cover
    yf = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class NAVDataError(Exception):
    """Raised when yfinance data is unavailable or invalid."""


class NAVCalculator:
    """Compute holding company Tier-1 NAV from yfinance market caps.

    Tier-1 methodology:
      NAV = sum(listed_sub_market_cap * stake_pct) + net_cash + private_bv
      nav_per_share = NAV / shares_outstanding
      discount_pct  = 1 - (price / nav_per_share)   # positive = cheap
    """

    def __init__(self, holdings_path: str | None = None) -> None:
        from src.signals.thresholds import HOLDINGS_YAML_PATH
        self._holdings_path = Path(holdings_path or HOLDINGS_YAML_PATH)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def compute_tier1_nav(
        self,
        ticker: str = "KCHOL",
        price_date: date | None = None,  # noqa: ARG002 (reserved for historical NAV)
    ) -> dict:
        """Compute Tier-1 NAV for a holding company.

        Returns:
            {
              ticker: str,
              nav_per_share: float,
              price: float,           # current market price (TL)
              discount_pct: float,    # positive = trading at discount
              listed_subs_value: float,  # TL, listed subs market_cap * stake sum
              net_cash: float,           # TL, from yaml (manual)
              shares_outstanding: float,
              source_date: str,
              subs_detail: list[dict],
            }

        Raises:
            FileNotFoundError: holdings.yaml not found
            KeyError: ticker not in holdings.yaml
            NAVDataError: yfinance returned invalid price/shares
        """
        if yf is None:  # pragma: no cover
            raise NAVDataError("yfinance yuklu degil: pip install yfinance")

        cfg = self._load_holdings(ticker)
        bist_ticker = ticker.upper() + ".IS"

        # Fetch parent company info (price + shares outstanding)
        parent = yf.Ticker(bist_ticker)
        parent_info = parent.fast_info
        price = float(
            parent_info.get("last_price")
            or parent_info.get("regularMarketPrice")
            or 0
        )
        shares = float(
            parent_info.get("shares")
            or parent_info.get("sharesOutstanding")
            or 0
        )

        if price <= 0 or shares <= 0:
            raise NAVDataError(
                f"{bist_ticker} fiyat veya hisse sayisi alinamadi: "
                f"price={price}, shares={shares}"
            )

        # Sum listed subsidiary market values
        listed_value_tl: float = 0.0
        subs_detail: list[dict] = []
        for sub in cfg.get("listed_subsidiaries", []):
            sub_ticker: str = sub["ticker"]
            stake: float = float(sub["stake_pct"])
            try:
                t = yf.Ticker(sub_ticker)
                mcap = float(
                    t.fast_info.get("market_cap")
                    or t.fast_info.get("marketCap")
                    or 0
                )
                contrib = mcap * stake
                listed_value_tl += contrib
                subs_detail.append(
                    {
                        "ticker": sub_ticker,
                        "stake_pct": stake,
                        "market_cap_tl": mcap,
                        "contribution_tl": contrib,
                    }
                )
                logger.debug(
                    "NAV sub: %s mcap=%.0f stake=%.1f%% contrib=%.0f",
                    sub_ticker, mcap, stake * 100, contrib,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("NAV: %s market_cap alinamadi: %s", sub_ticker, exc)

        net_cash = float(cfg.get("net_cash_holdco_tl", 0.0))
        private_bv = float(cfg.get("private_book_value_tl", 0.0))
        total_nav_tl = listed_value_tl + net_cash + private_bv

        nav_per_share = total_nav_tl / shares if shares > 0 else 0.0
        discount_pct = (
            1.0 - (price / nav_per_share) if nav_per_share > 0 else float("nan")
        )

        return {
            "ticker": ticker.upper(),
            "nav_per_share": round(nav_per_share, 4),
            "price": round(price, 4),
            "discount_pct": round(discount_pct, 6),
            "listed_subs_value": round(listed_value_tl, 2),
            "net_cash": round(net_cash, 2),
            "shares_outstanding": round(shares, 0),
            "source_date": cfg.get("last_verified", str(date.today())),
            "subs_detail": subs_detail,
        }

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _load_holdings(self, ticker: str) -> dict:
        """Load and return holdings config for given ticker."""
        if not self._holdings_path.exists():
            raise FileNotFoundError(
                f"holdings.yaml bulunamadi: {self._holdings_path}. "
                "config/holdings.yaml olusturun (gitignored)."
            )
        raw = yaml.safe_load(self._holdings_path.read_text(encoding="utf-8"))
        key = ticker.lower().replace(".is", "")
        if key not in raw:
            raise KeyError(f"holdings.yaml'da '{key}' bulunamadi")
        return raw[key]
