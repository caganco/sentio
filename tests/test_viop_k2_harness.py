"""Integration tests for VIOP K2 Stage-2 harness helpers.

Tests are synthetic — no real parquet files required.
All 9 tests validate public behaviour, not implementation internals.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.signals.viop_k2_split import (
    LiquiditySplit,
    ViOpK2Signal,
    _OI_PREV_FLOOR,
    compute_liquidity_split,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_k2_df(
    tickers: list[str],
    n_months: int = 6,
    oi_base: int = 1000,
    oi_prev_base: int = 1000,
) -> pd.DataFrame:
    """Synthetic K2 DataFrame with known OI values."""
    dates = pd.date_range("2023-01-31", periods=n_months, freq="ME")
    rows = []
    for i, ticker in enumerate(tickers):
        for j, date in enumerate(dates):
            oi = oi_base * (i + 1) * (j + 1)
            oi_prev = oi_prev_base * (i + 1) * j if j > 0 else 0
            k2 = (oi - oi_prev) / oi_prev if oi_prev > 0 else float("nan")
            rows.append({
                "date": date,
                "ticker": ticker,
                "K2": k2,
                "OI": float(oi),
                "OI_prev": float(oi_prev),
            })
    return pd.DataFrame(rows)


def _make_k2_df_with_outlier(
    tickers: list[str],
    n_months: int = 6,
) -> pd.DataFrame:
    """K2 DataFrame where SECOND ticker (index 1) has OI_prev < floor (outlier)."""
    dates = pd.date_range("2023-01-31", periods=n_months, freq="ME")
    rows = []
    for i, ticker in enumerate(tickers):
        for j, date in enumerate(dates):
            # i==1 is the "tiny" ticker — OI_prev=1 (below _OI_PREV_FLOOR=500)
            oi_prev = 1 if (i == 1 and j > 0) else 1000 * (i + 1) * j if j > 0 else 0
            oi = 2000 * (i + 1)
            k2 = (oi - oi_prev) / oi_prev if oi_prev > 0 else float("nan")
            rows.append({
                "date": date,
                "ticker": ticker,
                "K2": k2,
                "OI": float(oi),
                "OI_prev": float(oi_prev),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. compute_liquidity_split basic split
# ---------------------------------------------------------------------------

def test_liquidity_split_basic():
    """compute_liquidity_split returns LiquiditySplit with high/low groups."""
    tickers = ["AAA", "BBB", "CCC", "DDD"]
    df = _make_k2_df(tickers, oi_base=500, oi_prev_base=500)
    result = compute_liquidity_split(df)
    assert isinstance(result, LiquiditySplit)
    assert len(result.high_liq) + len(result.low_liq) == len(tickers)
    assert set(result.high_liq) | set(result.low_liq) == set(tickers)


# ---------------------------------------------------------------------------
# 2. compute_liquidity_split OI_prev floor filtering
# ---------------------------------------------------------------------------

def test_liquidity_split_floor_filtering():
    """Tickers with OI_prev < floor are excluded from both groups."""
    tickers = ["BIGOI", "TINYOI"]
    df = _make_k2_df_with_outlier(tickers, n_months=4)
    result = compute_liquidity_split(df)
    all_tickers = set(result.high_liq) | set(result.low_liq)
    assert "BIGOI" in all_tickers
    # TINYOI has OI_prev=1 < _OI_PREV_FLOOR; it should be excluded
    assert "TINYOI" not in all_tickers


# ---------------------------------------------------------------------------
# 3. compute_liquidity_split rank order
# ---------------------------------------------------------------------------

def test_liquidity_split_rank_order():
    """High-liq group contains the highest median-OI tickers."""
    tickers = ["LOW", "MID", "HIGH"]
    dates = pd.date_range("2023-01-31", periods=3, freq="ME")
    rows = [
        {"date": d, "ticker": "HIGH", "K2": 0.1, "OI": 3000.0, "OI_prev": 1000.0}
        for d in dates
    ] + [
        {"date": d, "ticker": "MID", "K2": 0.1, "OI": 2000.0, "OI_prev": 1000.0}
        for d in dates
    ] + [
        {"date": d, "ticker": "LOW", "K2": 0.1, "OI": 1000.0, "OI_prev": 1000.0}
        for d in dates
    ]
    df = pd.DataFrame(rows)
    result = compute_liquidity_split(df)
    # high_liq = top half: with 3 tickers, top 2 (HIGH + MID); low = [LOW]
    assert "HIGH" in result.high_liq
    assert "MID" in result.high_liq
    assert "LOW" in result.low_liq


# ---------------------------------------------------------------------------
# 4. compute_liquidity_split empty input
# ---------------------------------------------------------------------------

def test_liquidity_split_empty():
    """compute_liquidity_split handles empty DataFrame gracefully."""
    result = compute_liquidity_split(pd.DataFrame(columns=["ticker", "OI", "OI_prev", "K2"]))
    assert result.high_liq == []
    assert result.low_liq == []
    assert result.median_oi.empty


# ---------------------------------------------------------------------------
# 5. ViOpK2Signal scores returns K2 at month-end
# ---------------------------------------------------------------------------

def test_signal_scores_at_month_end():
    """ViOpK2Signal.scores returns K2 values for known month-end dates."""
    tickers = ["AAAA", "BBBB", "CCCC"]
    df = _make_k2_df(tickers, n_months=3, oi_base=1000, oi_prev_base=1000)
    signal = ViOpK2Signal(df, oi_prev_floor=_OI_PREV_FLOOR)

    # Use the second month-end (j=1 → OI_prev > 0 → K2 is defined)
    dates = sorted(df["date"].unique())
    asof = pd.Timestamp(dates[1])

    # panel arg is not used by ViOpK2Signal.scores; pass None
    result = signal.scores(None, tickers, asof)  # type: ignore[arg-type]
    assert isinstance(result, pd.Series)
    assert set(result.index).issubset(set(tickers))
    assert result.notna().any()


# ---------------------------------------------------------------------------
# 6. ViOpK2Signal scores returns empty at non-month-end
# ---------------------------------------------------------------------------

def test_signal_scores_empty_at_nonmonthend():
    """ViOpK2Signal.scores returns empty Series for dates not in K2 index."""
    tickers = ["AAAA", "BBBB"]
    df = _make_k2_df(tickers, n_months=3)
    signal = ViOpK2Signal(df, oi_prev_floor=_OI_PREV_FLOOR)

    asof = pd.Timestamp("2023-01-15")  # mid-month, not in K2 index
    result = signal.scores(None, tickers, asof)  # type: ignore[arg-type]
    assert isinstance(result, pd.Series)
    assert result.empty


# ---------------------------------------------------------------------------
# 7. ViOpK2Signal OI_prev floor suppresses outliers
# ---------------------------------------------------------------------------

def test_signal_scores_floor_suppresses_outlier():
    """Scores for tickers with OI_prev < floor are NaN."""
    tickers = ["NORMAL", "OUTLIER"]
    dates = pd.date_range("2023-01-31", periods=3, freq="ME")
    rows = []
    for j, d in enumerate(dates):
        rows.append({
            "date": d, "ticker": "NORMAL",
            "K2": 0.1 if j > 0 else float("nan"),
            "OI": 2000.0, "OI_prev": 1000.0 if j > 0 else 0.0,
        })
        rows.append({
            "date": d, "ticker": "OUTLIER",
            "K2": 999.0 if j > 0 else float("nan"),
            "OI": 2000.0, "OI_prev": 2.0 if j > 0 else 0.0,  # below floor
        })
    df = pd.DataFrame(rows)
    signal = ViOpK2Signal(df, oi_prev_floor=_OI_PREV_FLOOR)

    asof = dates[1]  # second month
    result = signal.scores(None, tickers, asof)  # type: ignore[arg-type]
    # NORMAL should be present; OUTLIER filtered by floor (OI_prev=2 < 500)
    assert "NORMAL" in result.index
    assert "OUTLIER" not in result.index


# ---------------------------------------------------------------------------
# 8. ViOpK2Signal PM-1 compliance
# ---------------------------------------------------------------------------

def test_signal_pm1_compliance():
    """Top-tercile equal-weight portfolio from K2 scores satisfies PM-1."""
    from src.engine.signal_protocol import assert_pm1_compliant

    tickers = [f"T{i:02d}" for i in range(12)]
    df = _make_k2_df(tickers, n_months=3, oi_base=1000, oi_prev_base=1000)
    signal = ViOpK2Signal(df, oi_prev_floor=_OI_PREV_FLOOR)

    dates = sorted(df["date"].unique())
    asof = pd.Timestamp(dates[1])
    scores_series = signal.scores(None, tickers, asof)  # type: ignore[arg-type]
    valid = scores_series.dropna()
    if valid.empty:
        pytest.skip("No valid scores at this date")

    n_top = max(1, len(valid) // 3)
    top = valid.nlargest(n_top)
    weights = pd.Series(
        [1.0 / n_top] * len(top), index=top.index, name="viop_k2_oi_growth"
    )
    # Should not raise
    assert_pm1_compliant(weights, name="viop_k2_oi_growth")


# ---------------------------------------------------------------------------
# 9. Stage-0 content hash integrity
# ---------------------------------------------------------------------------

def test_stage0_content_hash_stable():
    """STAGE0_VIOP_SSF_OI.json content_hash matches computed hash (integrity lock)."""
    import hashlib
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "docs" / "yol1" / "STAGE0_VIOP_SSF_OI.json"
    if not path.exists():
        pytest.skip("Stage-0 JSON not found")

    doc = json.loads(path.read_text(encoding="utf-8"))
    stored = str(doc.get("content_hash", ""))
    if not stored or stored == "__PLACEHOLDER__":
        pytest.skip("content_hash placeholder/empty")

    doc_clean = {k: v for k, v in doc.items() if k != "content_hash"}
    canonical = json.dumps(doc_clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    assert computed == stored, (
        f"Stage-0 content_hash drift: expected {stored!r}, got {computed!r}. "
        "Stage-0 was modified after the hash was computed."
    )
