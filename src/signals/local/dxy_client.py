"""DXY (US Dollar Index) client — Gap 3 (SPEC_L2_ENHANCEMENT_1).

Fetches DX-Y.NYB (DXY futures) weekly data from Yahoo Finance via yfinance.
Higher DXY (USD strength) → EM capital outflows → bearish for BIST.
"""
import logging
from datetime import datetime

from ..models import LocalMacroSignal
from ..thresholds import (
    DXY_SCORE_THRESHOLDS,
    DXY_SCORE_WEAK_USD,
    DXY_STALE_DAYS,
)
from .cache_store import LocalMacroCache

logger = logging.getLogger(__name__)

_DXY_TICKER = "DX-Y.NYB"


class DXYClient:
    """DXY US Dollar Index signal client."""

    def __init__(self, cache: LocalMacroCache):
        self.cache = cache

    def dxy_to_score(self, weekly_change_pct: float) -> float:
        """Map weekly DXY % change to 0-100 score (higher = weaker USD = bullish BIST).

        DXY_SCORE_THRESHOLDS is ordered high-to-low; first threshold the change
        is >= wins.  Values below the last threshold get DXY_SCORE_WEAK_USD.
        """
        for threshold, score in DXY_SCORE_THRESHOLDS:
            if weekly_change_pct >= threshold:
                return score
        return DXY_SCORE_WEAK_USD

    def fetch_and_store(self) -> bool:
        """Fetch DXY weekly data from Yahoo Finance and cache it.

        Uses the last 14 calendar days to compute weekly % change
        (close[-1] vs close[-6] to approximate 5 trading days).

        Returns True on success, False on any failure (network / parse).
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(_DXY_TICKER)
            hist = ticker.history(period="14d")

            if hist.empty or len(hist) < 2:
                logger.error("DXYClient.fetch_and_store: insufficient history (<2 bars)")
                return False

            close_latest = float(hist["Close"].iloc[-1])
            # Use up to 5-bar-ago close for weekly change; fall back to oldest available
            lookback = min(5, len(hist) - 1)
            close_week_ago = float(hist["Close"].iloc[-(lookback + 1)])

            if close_week_ago == 0:
                logger.error("DXYClient.fetch_and_store: zero close price in history")
                return False

            weekly_change = (close_latest - close_week_ago) / close_week_ago
            today = datetime.utcnow().date().isoformat()
            self.cache.store_dxy(
                data_date=today,
                close=close_latest,
                weekly_change_pct=round(weekly_change, 6),
            )
            logger.info(
                "DXYClient.fetch_and_store: close=%.2f weekly_chg=%.4f",
                close_latest,
                weekly_change,
            )
            return True

        except ImportError:
            logger.error("DXYClient.fetch_and_store: yfinance not installed")
            return False
        except Exception as e:
            logger.error("DXYClient.fetch_and_store: %s: %s", type(e).__name__, e)
            return False

    def score(self) -> LocalMacroSignal:
        """Return DXY signal score.

        Confidence:
            1.0  — data age <= DXY_STALE_DAYS
            0.8  — data age 3-5 days (stale but usable)
            0.0  — older or missing (signal excluded from composite)
        """
        data = self.cache.get_latest_dxy()
        if not data:
            return LocalMacroSignal(
                component="dxy",
                score=50.0,
                confidence=0.0,
                raw_value=None,
                last_update=None,
                data_freshness="missing",
                audit_msg="No DXY data in cache",
            )

        data_date_str = data["data_date"]
        try:
            data_datetime = datetime.fromisoformat(data_date_str)
        except ValueError:
            data_datetime = datetime.strptime(data_date_str, "%Y-%m-%d")

        age_days = (datetime.utcnow() - data_datetime).days

        if age_days <= DXY_STALE_DAYS:
            confidence = 1.0
            freshness = "fresh"
        elif age_days <= 5:
            confidence = 0.8
            freshness = "stale"
        else:
            confidence = 0.0
            freshness = "very_stale"

        weekly_chg = data["weekly_change_pct"]
        dxy_score = self.dxy_to_score(weekly_chg)

        return LocalMacroSignal(
            component="dxy",
            score=dxy_score,
            confidence=confidence,
            raw_value=data["close"],
            last_update=data_date_str,
            data_freshness=freshness,
            audit_msg=(
                f"DXY close={data['close']:.2f} "
                f"weekly_chg={weekly_chg:+.4f} "
                f"score={dxy_score} conf={confidence} age={age_days}d"
            ),
        )
