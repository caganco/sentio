"""SignalLogger + ReturnFiller tests (D-107, SPEC_ALPHA_INFRASTRUCTURE_1 Phase 2)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.data.signal_logger import (
    SIGNAL_LOG_SCHEMA,
    ReturnFiller,
    ReturnRecord,
    SignalLogger,
    SignalLogRecord,
)
from src.signals.models import (
    AuditTrail,
    ConflictInfo,
    LayerScore,
    SignalResult,
)


def _make_signal_result(symbol: str = "AKBNK", as_of: date | None = None) -> SignalResult:
    as_of = as_of or date(2026, 5, 20)
    layers = [
        LayerScore("technical",  62.0, 0.8, 0.25, {}, "computed"),
        LayerScore("macro",      55.0, 0.7, 0.20, {}, "computed"),
        LayerScore("kap",        70.0, 0.9, 0.30, {}, "computed"),
        LayerScore("sentiment",  50.0, 0.0, 0.12, {}, "missing"),
        LayerScore("smart_money", 58.0, 0.5, 0.10, {}, "partial"),
        LayerScore("risk",       65.0, 0.6, 0.03, {}, "computed"),
    ]
    audit = AuditTrail(
        symbol=symbol,
        as_of_date=as_of,
        computed_at=datetime(2026, 5, 20, 18, 0, tzinfo=timezone.utc),
        layer_scores=layers,
        weighted_sum=60.5,
        pre_conflict_signal="BUY-WEAK",
        conflict=ConflictInfo(False, "", "", 0.0, "none"),
        regime="NEUTRAL",
        risk_off_override=False,
        risk_off_trigger=None,
        final_signal="BUY-WEAK",
        signal_summary="ok",
        conviction_score=0.62,
        conviction_tier="BUY-MEDIUM",
    )
    return SignalResult(symbol, "BUY-WEAK", 60.5, audit, 0.62, "BUY-MEDIUM")


# ---------------------------------------------------------------------------
# SignalLogger tests
# ---------------------------------------------------------------------------

class TestSignalLogger:

    def test_schema_round_trip(self, tmp_path: Path) -> None:
        """SignalLogRecord -> parquet -> read back yields matching scalar values."""
        sl = SignalLogger(base_path=str(tmp_path))
        result = _make_signal_result()
        record = sl.build_record(
            symbol="AKBNK",
            result=result,
            liquidity_tier="BIST30",
            position_weight=0.175,
            regime_label="BULL",
        )
        sl.log_signal(record)

        fpath = tmp_path / "year=2026" / "month=05" / "day=20" / "signals.parquet"
        assert fpath.exists()
        df = pd.read_parquet(fpath)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["symbol"] == "AKBNK"
        assert row["liquidity_tier"] == "BIST30"
        assert row["regime_label"] == "BULL"
        assert row["conviction_tier"] == "BUY-MEDIUM"
        assert row["l1_tech_score"] == pytest.approx(62.0, abs=0.01)
        assert row["l3_kap_score"] == pytest.approx(70.0, abs=0.01)
        # Forward-return columns null on write-day T
        assert pd.isna(row["return_t1"])
        assert pd.isna(row["return_t60"])

    def test_idempotent_write_same_record(self, tmp_path: Path) -> None:
        """Logging the same (date, symbol) twice should not duplicate."""
        sl = SignalLogger(base_path=str(tmp_path))
        record = sl.build_record(symbol="AKBNK", result=_make_signal_result())
        sl.log_signal(record)
        sl.log_signal(record)  # second call -- should skip

        fpath = tmp_path / "year=2026" / "month=05" / "day=20" / "signals.parquet"
        df = pd.read_parquet(fpath)
        assert len(df) == 1

    def test_hive_partition_path(self, tmp_path: Path) -> None:
        """date=2026-05-20 -> year=2026/month=05/day=20/signals.parquet."""
        sl = SignalLogger(base_path=str(tmp_path))
        record = sl.build_record(symbol="GARAN",
                                  result=_make_signal_result(as_of=date(2026, 3, 7)))
        sl.log_signal(record)
        expected = tmp_path / "year=2026" / "month=03" / "day=07" / "signals.parquet"
        assert expected.exists()

    def test_as_of_timestamp_is_utc(self, tmp_path: Path) -> None:
        """as_of_timestamp must be timezone-aware UTC."""
        sl = SignalLogger(base_path=str(tmp_path))
        record = sl.build_record(symbol="AKBNK", result=_make_signal_result())
        assert record.as_of_timestamp.tzinfo is not None
        assert record.as_of_timestamp.utcoffset() == timedelta(0)


# ---------------------------------------------------------------------------
# ReturnFiller tests
# ---------------------------------------------------------------------------

class TestReturnFiller:

    def test_t1_fill_writes_return_record(self, tmp_path: Path) -> None:
        """ReturnFiller computes return_t1 = (today_price/yesterday_price)-1."""
        returns_path = tmp_path / "returns.parquet"
        filler = ReturnFiller(returns_path=str(returns_path))

        # Today = Tuesday 2026-05-19 (Monday 2026-05-18 is 1 trading day back)
        today = date(2026, 5, 19)
        prior = date(2026, 5, 18)

        def price_fetcher(symbol, d):
            return 110.0 if d == today else 100.0

        def reader(d):
            if d == prior:
                return pd.DataFrame([{
                    "symbol": "AKBNK",
                    "date": prior,
                    "price_limit_hit": False,
                }])
            return None

        n = filler.fill(today, price_fetcher, reader)
        # Expect exactly 1 row written for T+1 horizon
        assert n >= 1
        assert returns_path.exists()
        df = pd.read_parquet(returns_path)
        t1_rows = df[(df["horizon"] == 1) & (df["symbol"] == "AKBNK")]
        assert len(t1_rows) == 1
        assert t1_rows.iloc[0]["forward_return"] == pytest.approx(0.10, abs=1e-4)
