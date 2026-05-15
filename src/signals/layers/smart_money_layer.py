"""Smart Money layer (Layer 5): Institutional flow detection and bull trap prevention."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SmartMoneySignal:
    """Smart Money signal from institutional net flow."""

    def __init__(self):
        self.score = 0.5  # Default neutral
        self.confidence = 0.0
        self.institutional_net_pct = 0.0  # Daily net as % of volume
        self.net_3day_avg = 0.0
        self.trend = None  # ACCUMULATION, DISTRIBUTION, MIXED
        self.bull_trap_detected = False
        self.source = "none"  # "borsa", "halk_yatirim", "cache"

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 2),
            "institutional_net_pct": round(self.institutional_net_pct * 100, 2),
            "net_3day_avg_pct": round(self.net_3day_avg * 100, 2),
            "trend": self.trend,
            "bull_trap_detected": self.bull_trap_detected,
            "source": self.source
        }


class SmartMoneyLayer:
    """Compute Layer 5 score from institutional flows."""

    # Configuration
    NET_PECT_SCALE = 0.10  # +/- 10% maps to 0.0 - 1.0
    BULL_TRAP_TECH_THRESHOLD = 0.75  # STRONG-BUY
    BULL_TRAP_INST_THRESHOLD = -0.005  # -0.5% selling
    BULL_TRAP_DAYS_REQUIRED = 3
    BULL_TRAP_TECH_DOWNGRADE = 0.15

    def __init__(self):
        self.cache = {}  # {ticker: SmartMoneySignal}

    def calculate_score(self, ticker: str, institutional_flow: dict) -> SmartMoneySignal:
        """
        Calculate Smart Money score from institutional net flow.

        institutional_flow: {
            "ticker": "AKSEN",
            "date": "2026-05-14",
            "institutional_net_total": 100000,  # shares
            "daily_volume": 45000000,
            "net_pct": 0.00222,  # Already calculated
            "source": "borsa"
        }

        Returns: SmartMoneySignal with score [0.0, 1.0]
          0.0 = strong institutional selling
          0.5 = neutral
          1.0 = strong institutional buying
        """

        signal = SmartMoneySignal()

        if institutional_flow is None:
            logger.warning(f"Smart Money {ticker}: No flow data, neutral")
            signal.score = 0.5
            signal.confidence = 0.0
            signal.source = "none"
            return signal

        net_pct = institutional_flow.get("net_pct", 0.0)
        signal.institutional_net_pct = net_pct
        signal.source = institutional_flow.get("source", "unknown")

        # Map net % to score
        # -10% = 0.0, 0% = 0.5, +10% = 1.0
        # Formula: score = 0.5 + (net_pct / NET_PECT_SCALE)
        score = 0.5 + (net_pct / self.NET_PECT_SCALE)
        signal.score = max(0.0, min(score, 1.0))  # Clamp to [0, 1]

        # Confidence based on magnitude
        abs_net_pct = abs(net_pct)
        if abs_net_pct < 0.002:  # < 0.2%
            signal.confidence = 0.2  # Weak signal
        elif abs_net_pct < 0.005:  # < 0.5%
            signal.confidence = 0.5  # Moderate
        elif abs_net_pct < 0.010:  # < 1%
            signal.confidence = 0.7  # Good
        else:  # >= 1%
            signal.confidence = 0.9  # Strong signal

        logger.debug(f"Smart Money {ticker}: net={net_pct*100:.2f}%, score={signal.score:.3f}")

        return signal

    def calculate_3day_trend(
        self, ticker: str, daily_flows: list[dict]
    ) -> Optional[dict]:
        """
        Calculate 3-day rolling average of institutional flows.

        daily_flows: list of last 3 days' flow dicts
            [
                {"date": "2026-05-12", "net_pct": -0.012},
                {"date": "2026-05-13", "net_pct": -0.008},
                {"date": "2026-05-14", "net_pct": -0.007}
            ]

        Returns: {
            "day_1": -0.012,
            "day_2": -0.008,
            "day_3": -0.007,
            "avg_3day": -0.009,
            "direction": "DISTRIBUTION"
        }
        """

        if not daily_flows or len(daily_flows) < 3:
            logger.warning(f"Smart Money {ticker}: Less than 3 days data, can't calculate trend")
            return None

        recent_3 = daily_flows[-3:]
        net_pcts = [f.get("net_pct", 0.0) for f in recent_3]

        avg_3day = sum(net_pcts) / 3

        # Direction determination
        if all(pct > 0 for pct in net_pcts):
            direction = "ACCUMULATION"
        elif all(pct < 0 for pct in net_pcts):
            direction = "DISTRIBUTION"
        else:
            direction = "MIXED"

        trend = {
            "day_1": net_pcts[0],
            "day_2": net_pcts[1],
            "day_3": net_pcts[2],
            "avg_3day": avg_3day,
            "direction": direction
        }

        logger.debug(f"Smart Money {ticker}: 3-day trend {direction}, avg={avg_3day*100:.2f}%")

        return trend

    def detect_bull_trap(
        self,
        ticker: str,
        technical_score: float,
        institutional_flow_3day: Optional[dict]
    ) -> tuple[bool, str]:
        """
        Detect bull trap: strong technical + 3 days institutional selling.

        Bull trap = STRONG-BUY (tech > 0.75) + 3 consecutive days net sell <= -0.5%

        Returns: (is_bull_trap, reason)
        """

        # Condition 1: Technical signal is STRONG-BUY
        if technical_score < self.BULL_TRAP_TECH_THRESHOLD:
            return False, f"Tech not STRONG-BUY ({technical_score:.2f})"

        # Condition 2: 3-day institutional selling required
        if institutional_flow_3day is None:
            return False, "No 3-day flow data"

        days = [
            institutional_flow_3day.get("day_1", 0),
            institutional_flow_3day.get("day_2", 0),
            institutional_flow_3day.get("day_3", 0)
        ]

        # Check: all 3 days institutional selling >= threshold
        all_selling = all(d <= self.BULL_TRAP_INST_THRESHOLD for d in days)

        if not all_selling:
            return False, f"Not 3 days of {self.BULL_TRAP_INST_THRESHOLD*100:.1f}% selling: {[f'{d*100:.1f}%' for d in days]}"

        # BULL TRAP DETECTED
        reason = f"Bull trap: tech STRONG-BUY ({technical_score:.2f}) + 3 days inst. selling {[f'{d*100:.1f}%' for d in days]}"
        logger.warning(f"Smart Money {ticker}: {reason}")

        return True, reason

    def apply_bull_trap_override(
        self,
        ticker: str,
        technical_score: float,
        bull_trap_detected: bool
    ) -> float:
        """
        If bull trap detected, downgrade technical score.

        Returns: adjusted technical score
        """

        if not bull_trap_detected:
            return technical_score

        if technical_score < self.BULL_TRAP_TECH_THRESHOLD:
            return technical_score  # Already not STRONG-BUY

        adjusted = max(technical_score - self.BULL_TRAP_TECH_DOWNGRADE, 0.5)
        logger.warning(
            f"Smart Money {ticker}: Bull trap override — "
            f"tech downgraded {technical_score:.2f} → {adjusted:.2f}"
        )

        return adjusted

    def batch_calculate(self, tickers: list[str], market_data: dict) -> dict:
        """
        Calculate Smart Money signals for batch of tickers.

        market_data: {
            "AKSEN": {
                "institutional_flow": {...},
                "technical_score": 0.72,
                ...
            },
            ...
        }

        Returns: {
            "AKSEN": SmartMoneySignal,
            ...
        }
        """

        results = {}

        for ticker in tickers:
            if ticker not in market_data:
                logger.debug(f"Smart Money {ticker}: No market data, skipping")
                continue

            data = market_data[ticker]
            inst_flow = data.get("institutional_flow")
            tech_score = data.get("technical_score", 0.5)

            # Calculate base Smart Money score
            signal = self.calculate_score(ticker, inst_flow)

            # Calculate 3-day trend
            daily_flows = data.get("daily_flows", [])
            trend = self.calculate_3day_trend(ticker, daily_flows)
            if trend:
                signal.net_3day_avg = trend["avg_3day"]
                signal.trend = trend["direction"]

                # Detect bull trap
                bull_trap, reason = self.detect_bull_trap(ticker, tech_score, trend)
                signal.bull_trap_detected = bull_trap

            results[ticker] = signal
            self.cache[ticker] = signal

        return results
