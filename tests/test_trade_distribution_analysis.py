"""D-176: trade dagilimi analizi saf yardimcilarinin testleri (ag/state yok)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# Script'i dosya yolundan modul olarak yukle (scripts/ paket degil).
_MOD_PATH = Path(__file__).parent.parent / "scripts" / "analyze_trade_distribution.py"
_spec = importlib.util.spec_from_file_location("analyze_trade_distribution", _MOD_PATH)
atd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atd)


class TestTrailingExit:
    def test_exits_at_peak_retracement(self):
        """100->120 yukselip 108'e (peak'ten -10%) dusunce trailing -10% cikmali."""
        closes = pd.Series([105.0, 110.0, 120.0, 108.0, 130.0])
        res = atd.simulate_trailing_exit(closes, entry_price=100.0, trail_pct=0.10, commission=0.0)
        # peak=120, 120*0.90=108 -> 108<=108 -> idx 3'te cikis
        assert res["marked_to_end"] is False
        assert res["exit_idx"] == 3
        assert res["exit_price"] == 108.0
        assert res["pnl_pct_net"] == pytest.approx(0.08)

    def test_marks_to_end_when_no_retrace(self):
        """Hep yukselen seri -> hic trailing tetiklenmez -> son Close'da mark-to-end."""
        closes = pd.Series([110.0, 120.0, 130.0, 140.0])
        res = atd.simulate_trailing_exit(closes, entry_price=100.0, trail_pct=0.10, commission=0.0)
        assert res["marked_to_end"] is True
        assert res["exit_price"] == 140.0
        assert res["pnl_pct_net"] == pytest.approx(0.40)

    def test_empty_series_returns_zero(self):
        res = atd.simulate_trailing_exit(pd.Series([], dtype=float), 100.0, 0.10)
        assert res["pnl_pct_net"] == 0.0
        assert res["marked_to_end"] is True


class TestSkewness:
    def test_right_skew_positive(self):
        """Az sayida buyuk pozitif -> pozitif carpiklik."""
        vals = [1, 1, 1, 1, 1, 1, 1, 1, 1, 50]
        assert atd.compute_skewness(vals) > 0

    def test_left_skew_negative(self):
        """Az sayida buyuk negatif -> negatif carpiklik."""
        vals = [1, 1, 1, 1, 1, 1, 1, 1, 1, -50]
        assert atd.compute_skewness(vals) < 0

    def test_too_few_points_nan(self):
        import math
        assert math.isnan(atd.compute_skewness([1.0, 2.0]))


class TestExposureReconstruction:
    def test_intervals_and_daily_stats(self):
        """BUY->SELL ciftleri dogru tutulus araligi + gunluk exposure verir."""
        d = pd.to_datetime
        trades = [
            {"symbol": "AAA", "type": "BUY", "date": d("2024-01-01"), "shares": 10, "price": 10.0},
            {"symbol": "AAA", "type": "SELL", "date": d("2024-01-03"), "shares": 10, "price": 12.0,
             "entry_price": 10.0, "pnl": 20.0, "pnl_pct": 0.2, "reason": "signal"},
        ]
        last = d("2024-01-04")
        intervals = atd.build_holding_intervals(trades, last)
        assert len(intervals) == 1
        start, end, cost = intervals[0]
        assert cost == pytest.approx(100.0)  # 10 shares * 10.0

        daily = [d("2024-01-01"), d("2024-01-02"), d("2024-01-03"), d("2024-01-04")]
        equity = [1000.0, 1000.0, 1000.0, 1000.0]
        stats = atd.daily_exposure_stats(intervals, daily, equity)
        # 01-01..01-03 acik (3 gun), 01-04 nakit
        assert stats["max_open_positions"] == 1
        assert stats["pct_days_all_cash"] == 25.0  # 1/4
        assert stats["avg_open_positions"] == pytest.approx(0.75)

    def test_open_at_end_closed_at_last_date(self):
        """SELL'i olmayan BUY sonda last_date'te kapatilir."""
        d = pd.to_datetime
        trades = [{"symbol": "BBB", "type": "BUY", "date": d("2024-01-01"), "shares": 5, "price": 20.0}]
        intervals = atd.build_holding_intervals(trades, d("2024-01-05"))
        assert len(intervals) == 1
        assert intervals[0][1] == d("2024-01-05")


class TestWinLoss:
    def test_expectancy_and_payoff(self):
        # 2 kazanc (+20%, +10%), 2 kayip (-5%, -5%)
        stats = atd.winloss_stats([0.20, 0.10, -0.05, -0.05])
        assert stats["win_rate_pct"] == 50.0
        assert stats["avg_win_pct"] == pytest.approx(15.0)
        assert stats["avg_loss_pct"] == pytest.approx(5.0)
        assert stats["payoff_ratio"] == pytest.approx(3.0)
        # E = 0.5*15 - 0.5*5 = 5.0
        assert stats["expectancy_pct_per_trade"] == pytest.approx(5.0)


class TestRunnerCounterfactual:
    def test_runner_vs_gaveback(self):
        """profit_target trade: trailing daha yuksek cikis -> runner sayilir."""
        d = pd.to_datetime
        # entry 100, +20% cap'te (gercek pnl_pct=0.20) cikti; sonra fiyat 150'ye gitti
        sells = [{
            "symbol": "AAA", "type": "SELL", "reason": "profit_target",
            "entry_date": d("2024-01-01"), "entry_price": 100.0, "shares": 10,
            "pnl_pct": 0.20, "pnl": 200.0, "date": d("2024-01-05"),
        }]
        # entry sonrasi: surekli yukselen -> trailing mark-to-end ~ +50%
        idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06"])
        price_data = {"AAA": pd.DataFrame({"Close": [110, 120, 135, 145, 150.0]}, index=idx)}
        res = atd.analyze_runners(sells, price_data, [10.0])
        assert res["n_profit_target"] == 1
        bucket = res["by_trail"]["10.0"]
        assert bucket["runners"] == 1
        assert bucket["gaveback"] == 0
        assert bucket["gross_delta_tl"] > 0
