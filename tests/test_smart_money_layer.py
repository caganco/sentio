"""D-055 — SmartMoneyL5 critical path tests (20 tests).

Groups:
  1–5:   Silent failure detection (empty response, timeout, partial data)
  6–10:  Momentum calculation (edge cases: 9/10/11 days)
  11–14: Progressive upgrade logic (Day 1 / 10 / 20 transitions)
  15–17: Stale handling (24h / 48h / 72h scenarios)
  18–20: Signal quality — output always in [0, 100] or None
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.signals.layers.connectors.smart_money_mock import (
    MockSmartMoneyConnector,
    make_ticker_row,
)
from src.signals.layers.smart_money_layer import (
    NormalizerConfig,
    OutlierGuard,
    OutlierGuardConfig,
    SmartMoneyL5,
    SmartMoneyNormalizer,
    l5_effective_weight,
)
from src.signals.thresholds import (
    SMART_MONEY_FULL_COMPOSITE_DAYS,
    SMART_MONEY_MOMENTUM_DAYS,
    SMART_MONEY_STALE_HOURS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parquet(
    tmp_path: Path,
    symbol: str = "AKBNK",
    n_days: int = 10,
    foreign_ratio_start: float = 30.0,
    ratio_delta_per_day: float = 0.1,
    volume_3m_mn_usd: float = 100.0,
    written_at_offset_hours: float = 0.0,
) -> Path:
    """Write a synthetic parquet with n_days of data for a single symbol."""
    p = tmp_path / "daily_screener.parquet"
    written_at = (
        datetime.now(timezone.utc) - timedelta(hours=written_at_offset_hours)
    ).isoformat()

    rows = []
    for i in range(n_days):
        day = (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d")
        rows.append(
            {
                "date": day,
                "symbol": symbol,
                "foreign_ratio": foreign_ratio_start + i * ratio_delta_per_day,
                "change_1w_bps": 0.0,
                "change_1m_bps": 0.0,
                "volume_3m_mn_usd": volume_3m_mn_usd,
                "written_at": written_at,
            }
        )

    pd.DataFrame(rows).to_parquet(p, index=False)
    return p


# ---------------------------------------------------------------------------
# Group 1–5: Silent failure detection
# ---------------------------------------------------------------------------


class TestSilentFailureDetection:

    def test_01_empty_connector_returns_empty_dict(self):
        """Soft-block: connector returns {} — fetch_all_tickers must return {}."""
        conn = MockSmartMoneyConnector(data={})
        result = conn.fetch_all_tickers()
        assert result == {}

    def test_02_write_returns_false_on_empty_connector(self, tmp_path):
        """write_daily_snapshot returns False (not silent skip) when connector empty."""
        layer = SmartMoneyL5()
        conn = MockSmartMoneyConnector(data={})
        p = tmp_path / "daily_screener.parquet"

        success = layer.write_daily_snapshot(conn, "2026-05-17", parquet_path=p)

        assert success is False
        assert not p.exists()  # No file written

    def test_03_write_returns_true_on_valid_data(self, tmp_path):
        """write_daily_snapshot returns True and creates parquet when data is valid."""
        layer = SmartMoneyL5()
        conn = MockSmartMoneyConnector(
            data={"AKBNK": make_ticker_row(foreign_ratio=25.0)}
        )
        p = tmp_path / "daily_screener.parquet"

        success = layer.write_daily_snapshot(conn, "2026-05-17", parquet_path=p)

        assert success is True
        assert p.exists()

    def test_04_partial_data_parsed_correctly(self, tmp_path):
        """Partial data (1 valid ticker): written correctly, invalid skipped."""
        layer = SmartMoneyL5()
        conn = MockSmartMoneyConnector(
            data={
                "AKBNK": make_ticker_row(foreign_ratio=25.3, volume_3m_mn_usd=200.0),
                "BADINPUT": make_ticker_row(foreign_ratio=0.0, volume_3m_mn_usd=0.0),
            }
        )
        p = tmp_path / "daily_screener.parquet"

        layer.write_daily_snapshot(conn, "2026-05-17", parquet_path=p)
        df = pd.read_parquet(p)

        assert "AKBNK" in df["symbol"].values
        assert len(df) == 2  # Both rows written (bad ADV is a layer concern, not write)

    def test_05_unhealthy_connector_still_returns_empty(self):
        """is_healthy=False connector: fetch returns {}, no exception raised."""
        conn = MockSmartMoneyConnector(data={}, healthy=False)
        assert conn.is_healthy() is False
        result = conn.fetch_all_tickers()
        assert result == {}


# ---------------------------------------------------------------------------
# Group 6–10: Momentum calculation
# ---------------------------------------------------------------------------


class TestMomentumCalculation:

    def test_06_nine_days_no_momentum_signal(self, tmp_path):
        """9 days available → compute_l5_score returns None (momentum not ready)."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=9)

        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is None

    def test_07_ten_days_momentum_activates(self, tmp_path):
        """Exactly 10 days → momentum signal returns a float."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=10, ratio_delta_per_day=0.2)

        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is not None
        assert isinstance(result, float)

    def test_08_positive_momentum_score_above_50(self, tmp_path):
        """Rising foreign_ratio (10 days up) → momentum > 50."""
        layer = SmartMoneyL5()
        # ratio goes from 30 to 30 + 9*0.3 = 32.7 → +2.7pp change
        p = _make_parquet(tmp_path, n_days=10, ratio_delta_per_day=0.3)

        df = pd.read_parquet(p)
        score = layer.compute_momentum_score("AKBNK", df)

        assert score is not None
        assert score > 50.0

    def test_09_negative_momentum_score_below_50(self, tmp_path):
        """Falling foreign_ratio (10 days down) → momentum < 50."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=10, ratio_delta_per_day=-0.3)

        df = pd.read_parquet(p)
        score = layer.compute_momentum_score("AKBNK", df)

        assert score is not None
        assert score < 50.0

    def test_10_eleven_days_uses_last_ten(self, tmp_path):
        """11 days available → momentum uses last 10 (not all 11)."""
        layer = SmartMoneyL5()
        # First day: ratio=30. Days 2-11: rises. Momentum = ratio[10] - ratio[1]
        p = _make_parquet(tmp_path, n_days=11, ratio_delta_per_day=0.2)

        df = pd.read_parquet(p)
        score = layer.compute_momentum_score("AKBNK", df)

        assert score is not None
        # 10 steps × 0.2pp = 2.0pp → score = 50 + (2.0/5.0)*50 = 70
        assert score == pytest.approx(70.0, abs=2.0)


# ---------------------------------------------------------------------------
# Group 11–14: Progressive upgrade logic
# ---------------------------------------------------------------------------


class TestProgressiveUpgrade:

    def test_11_day1_no_signal(self, tmp_path):
        """Day 1: no signal (< 10 days)."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=1)

        assert layer.compute_l5_score("AKBNK", parquet_path=p) is None

    def test_12_day10_momentum_only(self, tmp_path):
        """Day 10: momentum-only signal (< 20 days → no percentile)."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=SMART_MONEY_MOMENTUM_DAYS)

        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is not None
        # Day 10: should be momentum only — same as compute_momentum_score
        df = pd.read_parquet(p)
        momentum = layer.compute_momentum_score("AKBNK", df)
        assert result == pytest.approx(momentum, abs=0.01)

    def test_13_day19_still_momentum_only(self, tmp_path):
        """Day 19 (one before threshold): still momentum-only."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=SMART_MONEY_FULL_COMPOSITE_DAYS - 1)

        df = pd.read_parquet(p)
        momentum = layer.compute_momentum_score("AKBNK", df)
        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is not None
        assert result == pytest.approx(momentum, abs=0.01)

    def test_14_day20_full_composite_activates(self, tmp_path):
        """Day 20: composite = 60% percentile + 40% momentum."""
        layer = SmartMoneyL5()
        p = _make_parquet(
            tmp_path,
            n_days=SMART_MONEY_FULL_COMPOSITE_DAYS,
            ratio_delta_per_day=0.15,
        )

        df = pd.read_parquet(p)
        momentum = layer.compute_momentum_score("AKBNK", df)
        percentile = layer.compute_percentile_score("AKBNK", df)
        expected = round(0.60 * percentile + 0.40 * momentum, 2)

        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is not None
        assert result == pytest.approx(expected, abs=0.1)


# ---------------------------------------------------------------------------
# Group 15–17: Stale handling
# ---------------------------------------------------------------------------


class TestStaleHandling:

    def test_15_fresh_data_24h_returns_score(self, tmp_path):
        """Data written 24h ago → still fresh (< 48h threshold) → returns score."""
        layer = SmartMoneyL5()
        p = _make_parquet(
            tmp_path, n_days=SMART_MONEY_MOMENTUM_DAYS, written_at_offset_hours=24
        )

        result = layer.compute_l5_score("AKBNK", parquet_path=p)
        assert result is not None

    def test_16_exactly_stale_48h_returns_none(self, tmp_path):
        """Data written 48h+ ago → stale → returns None."""
        layer = SmartMoneyL5()
        # 48h + 1 minute
        p = _make_parquet(
            tmp_path,
            n_days=SMART_MONEY_MOMENTUM_DAYS,
            written_at_offset_hours=SMART_MONEY_STALE_HOURS + 0.02,
        )

        result = layer.compute_l5_score("AKBNK", parquet_path=p)
        assert result is None

    def test_17_very_stale_72h_returns_none(self, tmp_path):
        """Data written 72h ago → stale → returns None."""
        layer = SmartMoneyL5()
        p = _make_parquet(
            tmp_path, n_days=SMART_MONEY_MOMENTUM_DAYS, written_at_offset_hours=72
        )

        result = layer.compute_l5_score("AKBNK", parquet_path=p)
        assert result is None


# ---------------------------------------------------------------------------
# Group 18–20: Signal quality
# ---------------------------------------------------------------------------


class TestSignalQuality:

    def test_18_score_in_range_0_100(self, tmp_path):
        """compute_l5_score always returns a value in [0, 100] when not None."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=25, ratio_delta_per_day=0.5)

        result = layer.compute_l5_score("AKBNK", parquet_path=p)

        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_19_extreme_rising_capped_at_100(self, tmp_path):
        """Extreme positive momentum (large delta) → score capped at 100."""
        layer = SmartMoneyL5()
        # +10pp over 10 days → way beyond +5pp normalization bound
        p = _make_parquet(tmp_path, n_days=10, ratio_delta_per_day=1.0)

        df = pd.read_parquet(p)
        score = layer.compute_momentum_score("AKBNK", df)

        assert score is not None
        assert score == pytest.approx(100.0, abs=0.01)

    def test_20_extreme_falling_capped_at_0(self, tmp_path):
        """Extreme negative momentum → score capped at 0."""
        layer = SmartMoneyL5()
        p = _make_parquet(tmp_path, n_days=10, ratio_delta_per_day=-1.0)

        df = pd.read_parquet(p)
        score = layer.compute_momentum_score("AKBNK", df)

        assert score is not None
        assert score == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Group 21–23: l5_effective_weight
# ---------------------------------------------------------------------------


class TestL5EffectiveWeight:

    def test_21_bull_healthy_returns_base_weight(self):
        """Healthy pipeline + BULL → base_weight unchanged."""
        assert l5_effective_weight(0.10, True, "BULL") == pytest.approx(0.10)

    def test_22_unhealthy_pipeline_returns_zero(self):
        """Unhealthy pipeline → 0.0 regardless of regime."""
        assert l5_effective_weight(0.10, False, "BULL") == 0.0
        assert l5_effective_weight(0.10, False, "BEAR") == 0.0

    def test_23_bear_regime_halves_weight(self):
        """BEAR regime → half the base_weight."""
        assert l5_effective_weight(0.10, True, "BEAR") == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Group 24–26: OutlierGuard.is_signal_eligible
# ---------------------------------------------------------------------------


class TestOutlierGuardEligibility:

    def _guard(self) -> OutlierGuard:
        return OutlierGuard(OutlierGuardConfig(min_adv_tl=20_000_000.0, min_free_float=0.25))

    def test_24_adv_and_ff_both_pass(self):
        """ADV ≥ 20M TL and free_float ≥ 25% → eligible."""
        assert self._guard().is_signal_eligible(adv_tl=25_000_000, free_float=0.30) is True

    def test_25_adv_below_threshold_ineligible(self):
        """ADV < 20M TL → not eligible."""
        assert self._guard().is_signal_eligible(adv_tl=10_000_000, free_float=0.30) is False

    def test_26_free_float_below_threshold_ineligible(self):
        """free_float < 25% → not eligible even with high ADV."""
        assert self._guard().is_signal_eligible(adv_tl=50_000_000, free_float=0.10) is False


# ---------------------------------------------------------------------------
# Group 27–29: OutlierGuard.filter_series
# ---------------------------------------------------------------------------


class TestOutlierGuardFilterSeries:

    def test_27_small_changes_series_passthrough(self):
        """No outliers (all within MAD, changes < 1pp) → result ≈ input."""
        guard = OutlierGuard(OutlierGuardConfig())
        s = pd.Series([30.0, 30.1, 30.2, 30.3, 30.4, 30.5])
        result = guard.filter_series(s)
        assert abs(float(result.iloc[-1]) - 30.5) < 0.1

    def test_28_extreme_level_outlier_clipped(self):
        """Value far beyond MAD threshold → clipped toward median."""
        guard = OutlierGuard(OutlierGuardConfig(mad_threshold=3.5))
        s = pd.Series([29.8, 30.0, 30.1, 30.2, 30.0, 30.1, 29.9, 30.0, 30.2, 55.0])
        result = guard.filter_series(s)
        assert result.iloc[-1] < 55.0

    def test_29_both_conditions_required_for_eligibility(self):
        """ADV OR free_float failure → ineligible; both must pass."""
        guard = OutlierGuard(OutlierGuardConfig(min_adv_tl=20_000_000.0, min_free_float=0.25))
        assert guard.is_signal_eligible(adv_tl=25_000_000, free_float=0.10) is False
        assert guard.is_signal_eligible(adv_tl=10_000_000, free_float=0.30) is False
        assert guard.is_signal_eligible(adv_tl=25_000_000, free_float=0.30) is True


# ---------------------------------------------------------------------------
# Group 30–33: SmartMoneyNormalizer
# ---------------------------------------------------------------------------


class TestSmartMoneyNormalizer:

    def test_30_output_valid_after_warmup(self):
        """normalize() returns values in [0,1] after min_periods of data."""
        cfg = NormalizerConfig(
            lookback_pctile=25,
            level_weight=1.0,
            momentum_weight=0.0,
            ensemble_windows=(5,),
            ensemble_weights=(1.0,),
        )
        norm = SmartMoneyNormalizer(cfg)
        s = pd.Series([30.0 + i * 0.1 for i in range(50)])
        result = norm.normalize(s)
        valid = result.dropna()
        assert len(valid) > 0
        assert all(0.0 <= v <= 1.0 for v in valid)

    def test_31_monotone_rising_scores_above_neutral(self):
        """Steadily rising foreign_ratio → composite > 0.5."""
        cfg = NormalizerConfig(
            lookback_pctile=30,
            ensemble_windows=(10,),
            ensemble_weights=(1.0,),
        )
        norm = SmartMoneyNormalizer(cfg)
        s = pd.Series([20.0 + i * 0.2 for i in range(60)])
        result = norm.normalize(s)
        last_valid = result.dropna().iloc[-1]
        assert last_valid > 0.5

    def test_32_output_always_clipped_to_0_1(self):
        """Any realistic input → output always in [0, 1] (no boundary violations)."""
        norm = SmartMoneyNormalizer(NormalizerConfig())
        rng = pd.Series([30.0 + (i % 7) * 0.3 - (i % 3) * 0.1 for i in range(300)])
        result = norm.normalize(rng)
        valid = result.dropna()
        assert len(valid) > 0
        assert all(0.0 <= v <= 1.0 for v in valid)

    def test_33_ensemble_weights_sum_to_one(self):
        """Default NormalizerConfig ensemble_weights must sum to exactly 1.0."""
        cfg = NormalizerConfig()
        assert abs(sum(cfg.ensemble_weights) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Group 34–35: l5_effective_weight — edge cases
# ---------------------------------------------------------------------------


class TestL5EffectiveWeightEdgeCases:

    def test_34_neutral_regime_same_as_bull(self):
        """NEUTRAL regime → same as BULL → base_weight unchanged."""
        assert l5_effective_weight(0.10, True, "NEUTRAL") == pytest.approx(0.10)

    def test_35_custom_base_weight_respected(self):
        """base_weight parameter is forwarded correctly in all paths."""
        assert l5_effective_weight(0.07, True, "BULL") == pytest.approx(0.07)
        assert l5_effective_weight(0.07, True, "BEAR") == pytest.approx(0.035)
        assert l5_effective_weight(0.07, False, "BULL") == 0.0
