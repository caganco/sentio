"""Smart Money layer (Layer 5): Institutional flow detection and bull trap prevention.

SmartMoneySignal / SmartMoneyLayer — existing bull-trap logic (backward compat).
SmartMoneyL5 — D-055 progressive foreign ratio signal (İş Yatırım screener + parquet).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd

from src.signals.thresholds import (
    L5_SMART_MONEY_WEIGHT,
    SMART_MONEY_ADV_MIN_TL,
    SMART_MONEY_FULL_COMPOSITE_DAYS,
    SMART_MONEY_MOMENTUM_DAYS,
    SMART_MONEY_MOMENTUM_WEIGHT,
    SMART_MONEY_OUTLIER_THRESHOLD_PP,
    SMART_MONEY_PERCENTILE_WEIGHT,
    SMART_MONEY_PERCENTILE_WINDOW,
    SMART_MONEY_STALE_HOURS,
)

if TYPE_CHECKING:
    from src.signals.layers.connectors.smart_money_connector import SmartMoneyConnectorBase

logger = logging.getLogger(__name__)

_DEFAULT_PARQUET = Path("data/smart_money/daily_screener.parquet")


# ---------------------------------------------------------------------------
# SmartMoneyNormalizer — D-055 supplement (pandas port of Polars design)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizerConfig:
    lookback_pctile: int = 252
    momentum_window: int = 10
    level_weight: float = 0.60
    momentum_weight: float = 0.40
    ensemble_windows: tuple[int, ...] = (5, 10, 20)
    ensemble_weights: tuple[float, ...] = (0.25, 0.50, 0.25)
    calendar_dampening: dict[str, float] | None = None


class SmartMoneyNormalizer:
    """Composite normalizer: 60% rolling percentile + 40% multi-window momentum ensemble."""

    def __init__(self, config: NormalizerConfig) -> None:
        self.cfg = config

    def normalize(
        self,
        foreign_ratio: pd.Series,
        event_flags: pd.Series | None = None,
    ) -> pd.Series:
        level = self._rolling_percentile(foreign_ratio, self.cfg.lookback_pctile)

        mom_ensemble = pd.Series(
            np.zeros(len(foreign_ratio)), index=foreign_ratio.index, dtype=float
        )
        for w, weight in zip(self.cfg.ensemble_windows, self.cfg.ensemble_weights):
            mom = foreign_ratio.diff(w)
            mom_ensemble = mom_ensemble + (
                self._rolling_percentile(mom, self.cfg.lookback_pctile).fillna(0.5) * weight
            )

        composite = (
            self.cfg.level_weight * level.fillna(0.5)
            + self.cfg.momentum_weight * mom_ensemble
        )

        if event_flags is not None and self.cfg.calendar_dampening:
            damp = event_flags.map(
                lambda x: self.cfg.calendar_dampening.get(x, 1.0)  # type: ignore[arg-type]
            )
            composite = 0.5 + (composite - 0.5) * damp

        return composite.clip(0.0, 1.0)

    @staticmethod
    def _rolling_percentile(s: pd.Series, window: int) -> pd.Series:
        min_periods = max(20, window // 4)
        return s.rolling(window=window, min_periods=min_periods).apply(
            lambda x: float((x[:-1] < x[-1]).mean()) if len(x) > 1 else 0.5,
            raw=True,
        )


# ---------------------------------------------------------------------------
# OutlierGuard — D-055 supplement (MAD clipping + ADV eligibility)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OutlierGuardConfig:
    mad_threshold: float = 5.0
    daily_change_cap_pp: float = 1.0
    min_adv_tl: float = 20_000_000.0
    min_free_float: float = 0.25


class OutlierGuard:
    """MAD-based level clipping + daily change cap. BIST fat-tail robust."""

    def __init__(self, cfg: OutlierGuardConfig) -> None:
        self.cfg = cfg

    def filter_series(self, series: pd.Series) -> pd.Series:
        median = float(series.median())
        mad = float((series - median).abs().median())
        threshold = self.cfg.mad_threshold * mad

        if mad == 0:
            diff = series.diff().fillna(0.0)
            capped = diff.clip(-self.cfg.daily_change_cap_pp, self.cfg.daily_change_cap_pp)
            shifted = series.shift(1).fillna(series.iloc[0])
            return shifted + capped

        clipped = series.apply(
            lambda x: median + float(np.sign(x - median)) * threshold
            if abs(x - median) > threshold else x
        )
        diff = clipped.diff().fillna(0.0)
        capped = diff.clip(-self.cfg.daily_change_cap_pp, self.cfg.daily_change_cap_pp)
        shifted = clipped.shift(1).fillna(clipped.iloc[0])
        return shifted + capped

    def is_signal_eligible(self, adv_tl: float, free_float: float) -> bool:
        return adv_tl >= self.cfg.min_adv_tl and free_float >= self.cfg.min_free_float


# ---------------------------------------------------------------------------
# l5_effective_weight — pipeline-gated weight (D-055 supplement)
# ---------------------------------------------------------------------------

def l5_effective_weight(
    base_weight: float = 0.10,
    pipeline_healthy: bool = True,
    macro_regime: str = "BULL",
) -> float:
    """
    Return the effective L5 weight for the engine composite.

    Rules:
    - Unhealthy pipeline (stale/soft-block) → 0.0 (fully excluded)
    - BEAR regime → half weight (L5 cannot open new positions, only reduces sizing)
    - BULL / NEUTRAL → base_weight (default 0.10)
    """
    if not pipeline_healthy:
        return 0.0
    if macro_regime == "BEAR":
        return base_weight * 0.5
    return base_weight


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


# ---------------------------------------------------------------------------
# SmartMoneyL5 — D-055 Phase 4.5 progressive build
# ---------------------------------------------------------------------------

class SmartMoneyL5:
    """
    L5 Smart Money: progressive foreign ratio signal from İş Yatırım screener.

    Progressive activation (based on days of parquet history for the symbol):
        Day  1–9:  write data, return None (no signal yet)
        Day 10–19: momentum only (10-day foreign_ratio change → [0, 100])
        Day 20+:   full composite (60% rolling percentile + 40% momentum)

    Stale contract (>48h since last write):
        compute_l5_score() → None
        Engine sets LayerScore weight=0 → completely excluded from composite.

    ADV filter: daily TL volume < 20M TL → compute_l5_score() → None.
    Outlier: any single day's Δforeign_ratio > 1.0pp → MAD-based clipping.
    """

    DEFAULT_PARQUET_PATH: Path = _DEFAULT_PARQUET

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_daily_snapshot(
        self,
        connector: SmartMoneyConnectorBase,
        date_str: str,
        parquet_path: Optional[Path] = None,
    ) -> bool:
        """
        Fetch screener snapshot and append to parquet.

        Returns True on success. On empty connector response (soft-block),
        logs ALERT and returns False — never silently skips.
        """
        if parquet_path is None:
            parquet_path = self.DEFAULT_PARQUET_PATH

        data = connector.fetch_all_tickers()
        if not data:
            logger.error(
                "ALERT SmartMoneyL5.write_daily_snapshot: connector returned empty — "
                "no data written for %s. Check connector for soft-block or network error.",
                date_str,
            )
            return False

        written_at = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "date": date_str,
                "symbol": symbol,
                "foreign_ratio": vals["foreign_ratio"],
                "change_1w_bps": vals["change_1w_bps"],
                "change_1m_bps": vals["change_1m_bps"],
                "volume_3m_mn_usd": vals["volume_3m_mn_usd"],
                "written_at": written_at,
            }
            for symbol, vals in data.items()
        ]

        new_df = pd.DataFrame(rows)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if parquet_path.exists():
                existing = pd.read_parquet(parquet_path)
                existing = existing[existing["date"] != date_str]
                combined = pd.concat([existing, new_df], ignore_index=True)
            else:
                combined = new_df

            combined = combined.sort_values(["date", "symbol"]).reset_index(drop=True)
            combined.to_parquet(parquet_path, index=False)
        except Exception as exc:
            logger.error("ALERT SmartMoneyL5.write_daily_snapshot: parquet write failed — %s", exc)
            return False

        logger.info(
            "SmartMoneyL5.write_daily_snapshot: %d tickers written for %s",
            len(rows), date_str,
        )
        return True

    # ------------------------------------------------------------------
    # Read / stale check
    # ------------------------------------------------------------------

    def _load_history(self, parquet_path: Path) -> Optional[pd.DataFrame]:
        """
        Load parquet history. Returns None if:
        - File missing (no data written yet)
        - Stale: latest written_at > SMART_MONEY_STALE_HOURS old
        """
        if not parquet_path.exists():
            return None

        try:
            df = pd.read_parquet(parquet_path)
        except Exception as exc:
            logger.error("ALERT SmartMoneyL5._load_history: read failed — %s", exc)
            return None

        if df.empty:
            logger.error("ALERT SmartMoneyL5._load_history: parquet is empty")
            return None

        latest_written = df["written_at"].max()
        age = datetime.now(timezone.utc) - datetime.fromisoformat(latest_written)
        if age > timedelta(hours=SMART_MONEY_STALE_HOURS):
            logger.warning(
                "SmartMoneyL5: data stale (%.1fh > %dh) — score=None, weight=0",
                age.total_seconds() / 3600,
                SMART_MONEY_STALE_HOURS,
            )
            return None

        return df

    # ------------------------------------------------------------------
    # ADV filter
    # ------------------------------------------------------------------

    def is_adv_eligible(self, symbol: str, df: pd.DataFrame) -> bool:
        """
        Return True if symbol's estimated daily TL volume >= SMART_MONEY_ADV_MIN_TL.

        Approximation: volume_3m_mn_usd × 1e6 USD × 34 TL/USD ÷ 63 trading days.
        """
        sym_df = df[df["symbol"] == symbol]
        if sym_df.empty:
            return False
        latest = sym_df.sort_values("date").iloc[-1]
        vol_mn_usd = float(latest.get("volume_3m_mn_usd") or 0)
        daily_adv_tl = vol_mn_usd * 1_000_000 * 34 / 63
        return daily_adv_tl >= SMART_MONEY_ADV_MIN_TL

    # ------------------------------------------------------------------
    # Outlier clipping
    # ------------------------------------------------------------------

    def _mad_clip(self, series: pd.Series) -> pd.Series:
        """
        If any daily Δforeign_ratio > SMART_MONEY_OUTLIER_THRESHOLD_PP,
        apply MAD-based clipping to all daily changes and reconstruct.
        """
        if len(series) < 2:
            return series

        daily = series.diff().fillna(0.0)
        if not (daily.abs() > SMART_MONEY_OUTLIER_THRESHOLD_PP).any():
            return series

        median = daily.median()
        mad = (daily - median).abs().median()
        if mad == 0:
            return series

        lower = median - 3.5 * mad
        upper = median + 3.5 * mad
        clipped = daily.clip(lower, upper)
        result = series.iloc[0] + clipped.cumsum()
        result.iloc[0] = series.iloc[0]
        return result

    # ------------------------------------------------------------------
    # Momentum score (Day 10+)
    # ------------------------------------------------------------------

    def compute_momentum_score(self, symbol: str, df: pd.DataFrame) -> Optional[float]:
        """
        10-day momentum: Δforeign_ratio over last SMART_MONEY_MOMENTUM_DAYS → [0, 100].

        Normalization: [-5pp, +5pp] → [0, 100] (clamped).
        Returns None if fewer than SMART_MONEY_MOMENTUM_DAYS trading days available.
        """
        sym_df = df[df["symbol"] == symbol].sort_values("date")
        n_days = sym_df["date"].nunique()
        if n_days < SMART_MONEY_MOMENTUM_DAYS:
            return None

        recent = sym_df.tail(SMART_MONEY_MOMENTUM_DAYS)
        ratios = recent["foreign_ratio"].reset_index(drop=True)
        ratios = self._mad_clip(ratios)

        change_pp = float(ratios.iloc[-1] - ratios.iloc[0])
        score = 50.0 + (change_pp / 5.0) * 50.0
        return round(max(0.0, min(100.0, score)), 2)

    # ------------------------------------------------------------------
    # Percentile score (Day 20+)
    # ------------------------------------------------------------------

    def compute_percentile_score(self, symbol: str, df: pd.DataFrame) -> Optional[float]:
        """
        Rolling SMART_MONEY_PERCENTILE_WINDOW-day percentile rank of current
        foreign_ratio → [0, 100].

        Returns None if fewer than SMART_MONEY_FULL_COMPOSITE_DAYS days available.
        """
        sym_df = df[df["symbol"] == symbol].sort_values("date")
        if sym_df["date"].nunique() < SMART_MONEY_FULL_COMPOSITE_DAYS:
            return None

        window = sym_df.tail(SMART_MONEY_PERCENTILE_WINDOW)
        current = float(window["foreign_ratio"].iloc[-1])
        all_vals = window["foreign_ratio"].values
        pct = (all_vals < current).sum() / len(all_vals)
        return round(pct * 100.0, 2)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def compute_l5_score(
        self,
        symbol: str,
        parquet_path: Optional[Path] = None,
    ) -> Optional[float]:
        """
        Progressive L5 score for a single symbol.

        Returns None when:
        - No parquet history (Day 1–9)
        - Stale data (>48h since last write)
        - Symbol not ADV eligible (volume < 20M TL/day)
        - Fewer than SMART_MONEY_MOMENTUM_DAYS trading days for symbol

        Caller (engine) must set LayerScore.weight=0 when this returns None.
        """
        if parquet_path is None:
            parquet_path = self.DEFAULT_PARQUET_PATH

        df = self._load_history(parquet_path)
        if df is None:
            return None

        if not self.is_adv_eligible(symbol, df):
            logger.debug("SmartMoneyL5 %s: ADV < %.0fM TL — no signal", symbol, SMART_MONEY_ADV_MIN_TL / 1e6)
            return None

        sym_df = df[df["symbol"] == symbol]
        n_days = sym_df["date"].nunique()

        if n_days < SMART_MONEY_MOMENTUM_DAYS:
            logger.debug("SmartMoneyL5 %s: %d days < %d — no signal yet", symbol, n_days, SMART_MONEY_MOMENTUM_DAYS)
            return None

        momentum = self.compute_momentum_score(symbol, df)
        if momentum is None:
            return None

        if n_days < SMART_MONEY_FULL_COMPOSITE_DAYS:
            logger.debug("SmartMoneyL5 %s: Day %d — momentum-only %.1f", symbol, n_days, momentum)
            return momentum

        percentile = self.compute_percentile_score(symbol, df)
        if percentile is None:
            return momentum

        composite = round(
            SMART_MONEY_PERCENTILE_WEIGHT * percentile
            + SMART_MONEY_MOMENTUM_WEIGHT * momentum,
            2,
        )
        logger.debug(
            "SmartMoneyL5 %s: Day %d — pct=%.1f mom=%.1f composite=%.1f",
            symbol, n_days, percentile, momentum, composite,
        )
        return composite


# Module-level singleton used by engine.py
_l5_singleton: Optional[SmartMoneyL5] = None


def get_l5_layer() -> SmartMoneyL5:
    """Return module-level SmartMoneyL5 singleton (lazy init)."""
    global _l5_singleton
    if _l5_singleton is None:
        _l5_singleton = SmartMoneyL5()
    return _l5_singleton
