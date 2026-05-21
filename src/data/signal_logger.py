"""Signal logger for alpha attribution (DEC-015, SPEC_ALPHA_INFRASTRUCTURE_1).

Two responsibilities:
1. SignalLogger    -- write SignalLogRecord rows to Hive-partitioned parquet
2. ReturnFiller    -- backfill forward returns at T+1/T+5/T+20/T+60

Storage layout:
  data/signal_logs/year=YYYY/month=MM/day=DD/signals.parquet
  data/signal_logs/returns.parquet   (append-only, all horizons)

Append-only design: returns never overwrite signal records. The join happens at
IC calculation time on (date, symbol). as_of_timestamp guards against lookahead.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from src.data.bist_calendar import BISTCalendar
from src.signals.thresholds import (
    IC_HORIZON_T1,
    IC_HORIZON_T5,
    IC_HORIZON_T20,
    IC_HORIZON_T60,
    RETURNS_LOG_PATH,
    SIGNAL_LOG_BASE_PATH,
    VOLATILITY_REGIME_HIGH_MIN,
    VOLATILITY_REGIME_LOW_MAX,
)

if TYPE_CHECKING:
    from src.signals.models import SignalResult

logger = logging.getLogger(__name__)

_HORIZONS: tuple[int, ...] = (IC_HORIZON_T1, IC_HORIZON_T5, IC_HORIZON_T20, IC_HORIZON_T60)


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class SignalLogRecord(BaseModel):
    """One row in signal_log parquet: one symbol x one day x all layers.

    as_of_timestamp records signal-compute time (not the date it refers to).
    Critical for lookahead audit: signal_t must be < return_{t+H} fill time.

    regime_label uses code's existing labels (BULL/NEUTRAL/BEAR) -- not SPEC's
    title-case variant. NEUTRAL semantically equals SPEC's "Transition".
    """
    # Identity
    date: date
    symbol: str
    as_of_timestamp: datetime

    # Layer scores (raw, before composite normalization)
    l1_tech_score: float = 50.0
    l1_tech_conf:  float = 0.0
    l2_macro_score: float = 50.0
    l2_macro_conf:  float = 0.0
    l3_kap_score:  float = 50.0
    l3_kap_conf:   float = 0.0
    l4_sent_score: float = 50.0
    l4_sent_conf:  float = 0.0
    l5_sm_score:   float = 50.0
    l5_sm_conf:    float = 0.0
    l6_risk_score: float = 50.0
    l6_risk_conf:  float = 0.0
    viop_score:    float | None = None
    viop_conf:     float | None = None
    l5_foreign_flow_raw: float | None = None  # D-108 baseline (market-level)

    # Composite output
    composite_score:  float = 50.0
    conviction_score: float = 0.0
    conviction_tier:  str = "WATCH"
    final_signal:     str = "HOLD"
    position_weight:  float = 0.0

    # Context (no lookahead)
    regime_label:      Literal["BULL", "NEUTRAL", "BEAR"] = "NEUTRAL"
    volatility_regime: Literal["Low", "Mid", "High"] = "Mid"
    liquidity_tier:    Literal["BIST30", "BIST100", "Outside"] = "Outside"

    # Forward returns (None on write-day T; filled at T+N)
    return_t1:  float | None = None
    return_t5:  float | None = None
    return_t20: float | None = None
    return_t60: float | None = None
    price_limit_hit: bool = False


class ReturnRecord(BaseModel):
    """Forward return row filled retroactively at T+N. Joined with SignalLogRecord
    at IC calc time on (date, symbol). Append-only.
    """
    signal_date: date
    symbol: str
    horizon: int          # 1 | 5 | 20 | 60
    forward_return: float
    price_limit_hit: bool
    filled_at: datetime


# ---------------------------------------------------------------------------
# PyArrow schema (enforced at write time)
# ---------------------------------------------------------------------------

SIGNAL_LOG_SCHEMA = pa.schema([
    pa.field("date",             pa.date32()),
    pa.field("symbol",           pa.string()),
    pa.field("as_of_timestamp",  pa.timestamp("us", tz="UTC")),
    pa.field("l1_tech_score",    pa.float32()),
    pa.field("l1_tech_conf",     pa.float32()),
    pa.field("l2_macro_score",   pa.float32()),
    pa.field("l2_macro_conf",    pa.float32()),
    pa.field("l3_kap_score",     pa.float32()),
    pa.field("l3_kap_conf",      pa.float32()),
    pa.field("l4_sent_score",    pa.float32()),
    pa.field("l4_sent_conf",     pa.float32()),
    pa.field("l5_sm_score",      pa.float32()),
    pa.field("l5_sm_conf",       pa.float32()),
    pa.field("l6_risk_score",    pa.float32()),
    pa.field("l6_risk_conf",     pa.float32()),
    pa.field("viop_score",       pa.float32()),
    pa.field("viop_conf",        pa.float32()),
    pa.field("l5_foreign_flow_raw", pa.float32()),
    pa.field("composite_score",  pa.float32()),
    pa.field("conviction_score", pa.float32()),
    pa.field("conviction_tier",  pa.string()),
    pa.field("final_signal",     pa.string()),
    pa.field("position_weight",  pa.float32()),
    pa.field("regime_label",     pa.string()),
    pa.field("volatility_regime",pa.string()),
    pa.field("liquidity_tier",   pa.string()),
    pa.field("return_t1",        pa.float32()),
    pa.field("return_t5",        pa.float32()),
    pa.field("return_t20",       pa.float32()),
    pa.field("return_t60",       pa.float32()),
    pa.field("price_limit_hit",  pa.bool_()),
])


# ---------------------------------------------------------------------------
# SignalLogger
# ---------------------------------------------------------------------------

class SignalLogger:
    """Write daily signal records to Hive-partitioned parquet.

    Usage:
        logger = SignalLogger()
        for symbol, result in results.items():
            record = logger.build_record(symbol, result, liquidity_tier="BIST30", ...)
            logger.log_signal(record)
    """

    def __init__(self, base_path: str = SIGNAL_LOG_BASE_PATH) -> None:
        self._base = Path(base_path)

    def build_record(
        self,
        symbol: str,
        result: "SignalResult",
        liquidity_tier: str = "Outside",
        position_weight: float = 0.0,
        regime_label: str = "NEUTRAL",
        realized_vol_pct: float | None = None,
        viop_score: float | None = None,
        viop_conf: float | None = None,
        l5_foreign_flow_raw: float | None = None,
    ) -> SignalLogRecord:
        audit = result.audit
        ls_map = {ls.layer: ls for ls in audit.layer_scores}

        def _s(layer: str) -> float:
            return ls_map[layer].score if layer in ls_map else 50.0

        def _c(layer: str) -> float:
            return ls_map[layer].confidence if layer in ls_map else 0.0

        return SignalLogRecord(
            date=audit.as_of_date,
            symbol=symbol,
            as_of_timestamp=datetime.now(timezone.utc),
            l1_tech_score=_s("technical"),
            l1_tech_conf=_c("technical"),
            l2_macro_score=_s("macro"),
            l2_macro_conf=_c("macro"),
            l3_kap_score=_s("kap"),
            l3_kap_conf=_c("kap"),
            l4_sent_score=_s("sentiment"),
            l4_sent_conf=_c("sentiment"),
            l5_sm_score=_s("smart_money"),
            l5_sm_conf=_c("smart_money"),
            l6_risk_score=_s("risk"),
            l6_risk_conf=_c("risk"),
            viop_score=viop_score,
            viop_conf=viop_conf,
            l5_foreign_flow_raw=l5_foreign_flow_raw,
            composite_score=result.score,
            conviction_score=result.conviction_score,
            conviction_tier=result.conviction_tier,
            final_signal=result.final_signal,
            position_weight=position_weight,
            regime_label=regime_label if regime_label in ("BULL", "NEUTRAL", "BEAR") else "NEUTRAL",
            volatility_regime=_classify_vol(realized_vol_pct),
            liquidity_tier=liquidity_tier if liquidity_tier in ("BIST30", "BIST100", "Outside") else "Outside",
        )

    def log_signal(self, record: SignalLogRecord) -> None:
        """Append record to day-partitioned parquet. Idempotent on (date, symbol)."""
        d = record.date
        path = self._base / f"year={d.year}" / f"month={d.month:02d}" / f"day={d.day:02d}"
        path.mkdir(parents=True, exist_ok=True)
        fpath = path / "signals.parquet"

        row = pd.DataFrame([record.model_dump()])
        table = pa.Table.from_pandas(row, schema=SIGNAL_LOG_SCHEMA, safe=False)

        if fpath.exists():
            existing = pq.read_table(fpath)
            existing_df = existing.to_pandas()
            mask = ((existing_df["date"].astype(str) == str(record.date)) &
                    (existing_df["symbol"] == record.symbol))
            if mask.any():
                logger.debug("signal_logger: %s %s already logged, skip",
                             record.date, record.symbol)
                return
            combined = pa.concat_tables([existing, table])
            pq.write_table(combined, fpath, compression="snappy")
        else:
            pq.write_table(table, fpath, compression="snappy")

        logger.debug("signal_logger: logged %s %s composite=%.1f",
                     record.date, record.symbol, record.composite_score)


# ---------------------------------------------------------------------------
# ReturnFiller
# ---------------------------------------------------------------------------

class ReturnFiller:
    """Fill forward returns for past signal records.

    For each horizon H in {1, 5, 20, 60}:
        signal_date = today - H trading days
        forward_return = (price_today / price_{signal_date}) - 1
    """

    def __init__(self, returns_path: str = RETURNS_LOG_PATH) -> None:
        self._path = Path(returns_path)
        self._cal = BISTCalendar()

    def fill(self, today: date, price_fetcher, signal_log_reader) -> int:
        """Fill all horizons. Returns count of rows written.

        price_fetcher(symbol, d) -> float | None
        signal_log_reader(d)     -> pd.DataFrame | None
        """
        n = 0
        for horizon in _HORIZONS:
            n += self._fill_horizon(today, horizon, price_fetcher, signal_log_reader)
        return n

    def _fill_horizon(self, today, horizon, price_fetcher, signal_log_reader) -> int:
        signal_date = self._trading_days_back(today, horizon)
        df = signal_log_reader(signal_date)
        if df is None or df.empty:
            return 0

        already = self._already_filled(signal_date, horizon)
        symbols = [s for s in df["symbol"].tolist() if s not in already]
        if not symbols:
            return 0

        rows: list[ReturnRecord] = []
        for symbol in symbols:
            try:
                base_price = price_fetcher(symbol, signal_date)
                curr_price = price_fetcher(symbol, today)
                if base_price is None or curr_price is None or base_price == 0:
                    continue
                fwd_return = float(curr_price) / float(base_price) - 1.0
                row_df = df[df["symbol"] == symbol]
                rows.append(ReturnRecord(
                    signal_date=signal_date,
                    symbol=symbol,
                    horizon=horizon,
                    forward_return=round(fwd_return, 6),
                    price_limit_hit=bool(row_df["price_limit_hit"].values[0])
                                   if "price_limit_hit" in row_df else False,
                    filled_at=datetime.now(timezone.utc),
                ))
            except Exception as exc:
                logger.debug("return_filler: %s h=%d failed: %s", symbol, horizon, exc)

        if rows:
            self._append_rows(rows)
        return len(rows)

    def _already_filled(self, signal_date: date, horizon: int) -> set[str]:
        if not self._path.exists():
            return set()
        df = pd.read_parquet(self._path)
        if df.empty:
            return set()
        mask = ((df["signal_date"].astype(str) == str(signal_date)) &
                (df["horizon"] == horizon))
        return set(df[mask]["symbol"].tolist())

    def _append_rows(self, rows: list[ReturnRecord]) -> None:
        new_df = pd.DataFrame([r.model_dump() for r in rows])
        if self._path.exists():
            existing = pd.read_parquet(self._path)
            combined = pd.concat([existing, new_df], ignore_index=True)
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            combined = new_df
        combined.to_parquet(self._path, index=False, compression="snappy")

    def _trading_days_back(self, today: date, n: int) -> date:
        """Walk back n trading days, skipping BIST holidays and weekends."""
        cur = today
        steps = 0
        while steps < n:
            cur = cur - timedelta(days=1)
            if cur.weekday() >= 5:  # Saturday=5, Sunday=6
                continue
            if self._cal.is_holiday(cur.isoformat()):
                continue
            steps += 1
        return cur


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_vol(realized_vol_pct: float | None) -> str:
    if realized_vol_pct is None:
        return "Mid"
    if realized_vol_pct < VOLATILITY_REGIME_LOW_MAX:
        return "Low"
    if realized_vol_pct > VOLATILITY_REGIME_HIGH_MIN:
        return "High"
    return "Mid"
