"""D-189 saf fonksiyon testleri (ağ bağlantısı, dosya I/O yok).

Test kapsamı:
  1. Per-trade reel getiri formülü (TÜFE deflasyonu)
  2. Per-trade XU100-relative getiri formülü
  3. Adil-null deterministik (seed=42, n_iter=2)
  4. Verdict logic (§4 frozen karar kuralı)
  5. Attribution aritmetiği (closed_pnl + open_contribution = actual_gain)
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Script'i importlib ile yükle (paket kurulumundan bağımsız)
_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "d189_edge_isolation.py"
_spec = importlib.util.spec_from_file_location("_d189_module", _SCRIPT_PATH)
_d189 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_d189)

compute_per_trade_metrics = _d189.compute_per_trade_metrics
compute_expectancy = _d189.compute_expectancy
run_fair_null = _d189.run_fair_null
compute_verdict = _d189.compute_verdict
compute_attribution = _d189.compute_attribution
_simulate_exit = _d189._simulate_exit

TUFE_UNAVAILABLE = _d189.TUFE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Yardımcı fabrikalar
# ---------------------------------------------------------------------------

def make_trade(
    symbol="AKBNK",
    entry_date="2024-03-01",
    exit_date="2024-04-01",
    entry_price=50.0,
    exit_price=60.0,
    shares=10,
    pnl_pct=0.20,
    pnl=100.0,
    commission=0.5,
) -> pd.DataFrame:
    return pd.DataFrame([{
        "symbol": symbol,
        "type": "SELL",
        "exit_date": pd.Timestamp(exit_date),
        "exit_price": exit_price,
        "shares": shares,
        "entry_price": entry_price,
        "entry_date": pd.Timestamp(entry_date),
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "commission": commission,
        "holding_days": (pd.Timestamp(exit_date) - pd.Timestamp(entry_date)).days,
    }])


def make_tufe(factor: float = 1.10, days: int = 100) -> pd.Series:
    """Basit lineer büyüyen TÜFE serisi. base=1.0, factor'a ulaşır `days` gün sonra."""
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    values = np.linspace(1.0, factor, days)
    return pd.Series(values, index=dates, name="tufe")


def make_xu100(factor: float = 1.05, days: int = 100) -> pd.Series:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    values = np.linspace(1000.0, 1000.0 * (1 + factor), days)
    return pd.Series(values, index=dates, name="xu100")


# ---------------------------------------------------------------------------
# 1. Per-trade reel formülü
# ---------------------------------------------------------------------------

class TestReelFormula:
    def test_reel_deflation_known_value(self):
        """Nominal %20 + %10 enflasyon → reel ≈ %9.09."""
        tufe = make_tufe(factor=1.10, days=365)
        xu100 = make_xu100(factor=0.0, days=365)  # sabit XU100

        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31", pnl_pct=0.20,
        )
        enriched = compute_per_trade_metrics(trade, tufe, xu100)
        reel = enriched["reel_pnl_pct"].iloc[0]
        # (1 + 0.20) / (1 + ~0.10) - 1 ≈ 0.0909
        assert isinstance(reel, float)
        assert abs(reel - 0.0909) < 0.005

    def test_short_hold_reel_approx_nominal(self):
        """Kısa hold (<1 ay): TÜFE ayından çıkmaz, reel ≈ nominal."""
        tufe = make_tufe(factor=1.30, days=365)
        xu100 = make_xu100(factor=0.0, days=365)
        trade = make_trade(
            entry_date="2024-03-15", exit_date="2024-03-20", pnl_pct=0.05,
        )
        enriched = compute_per_trade_metrics(trade, tufe, xu100)
        reel = enriched["reel_pnl_pct"].iloc[0]
        # Çok kısa hold: cum_inf ≈ küçük pozitif, reel yaklaşık nominal
        assert isinstance(reel, float)
        assert abs(reel - 0.05) < 0.02

    def test_tufe_unavailable_sentinel(self):
        """TÜFE None → sentinel döner."""
        xu100 = make_xu100(factor=0.0, days=365)
        trade = make_trade(pnl_pct=0.10)
        enriched = compute_per_trade_metrics(trade, None, xu100)
        assert enriched["reel_pnl_pct"].iloc[0] == TUFE_UNAVAILABLE

    def test_negative_pnl_reel(self):
        """Zarar eden işlemde reel kaybı daha küçük (nominal -8%, enflasyon %10 → reel daha az kaybettirdi)."""
        tufe = make_tufe(factor=1.10, days=365)
        xu100 = make_xu100(factor=0.0, days=365)
        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31", pnl_pct=-0.08,
        )
        enriched = compute_per_trade_metrics(trade, tufe, xu100)
        reel = enriched["reel_pnl_pct"].iloc[0]
        # (1 - 0.08) / (1 + 0.10) - 1 = 0.92/1.10 - 1 ≈ -0.1636
        assert isinstance(reel, float)
        assert reel < -0.08  # reel kayıp, nominal kaybından büyük (satın alma gücü kaybı)


# ---------------------------------------------------------------------------
# 2. XU100-relative formülü
# ---------------------------------------------------------------------------

class TestRelativeFormula:
    def test_relative_zero_when_matches_index(self):
        """Hisse XU100 ile aynı hareket → relative ≈ 0."""
        xu100 = make_xu100(factor=0.20, days=365)  # XU100 da %20 arttı
        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31", pnl_pct=0.20,
        )
        enriched = compute_per_trade_metrics(trade, None, xu100)
        rel = enriched["rel_pnl_pct"].iloc[0]
        assert isinstance(rel, float)
        assert abs(rel) < 0.01  # ~0 (küçük geometrik fark kabul edilebilir)

    def test_relative_positive_when_outperforms(self):
        """Hisse XU100'ü geçerse relative pozitif."""
        xu100 = make_xu100(factor=0.05, days=365)  # XU100 %5
        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31", pnl_pct=0.20,
        )
        enriched = compute_per_trade_metrics(trade, None, xu100)
        rel = enriched["rel_pnl_pct"].iloc[0]
        assert rel > 0.10  # belirgin pozitif

    def test_relative_negative_when_underperforms(self):
        """XU100 altında kalan işlem → relative negatif."""
        xu100 = make_xu100(factor=0.20, days=365)  # XU100 %20
        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31", pnl_pct=0.05,
        )
        enriched = compute_per_trade_metrics(trade, None, xu100)
        rel = enriched["rel_pnl_pct"].iloc[0]
        assert rel < -0.10


# ---------------------------------------------------------------------------
# 3. Adil-null deterministik
# ---------------------------------------------------------------------------

class TestFairNull:
    def _make_sym_prices(self, n_days: int = 400) -> dict[str, pd.Series]:
        """Sabit fiyatlı sembol serisi (simülasyonda max-hold'a girer)."""
        dates = pd.date_range("2024-01-02", periods=n_days, freq="B")
        prices = pd.Series(np.full(n_days, 100.0), index=dates, name="AKBNK")
        return {"AKBNK": prices}

    def test_deterministic_same_seed(self):
        """Aynı seed → aynı sonuç."""
        xu100 = make_xu100(factor=0.0, days=400)
        sym_prices = self._make_sym_prices()
        trades = make_trade(entry_date="2024-03-01", exit_date="2024-04-01")

        r1 = run_fair_null(trades, sym_prices, xu100, n_iter=2, seed=42)
        r2 = run_fair_null(trades, sym_prices, xu100, n_iter=2, seed=42)
        assert r1["null_win_rate_p50"] == r2["null_win_rate_p50"]
        assert r1["null_expectancy_p50"] == r2["null_expectancy_p50"]

    def test_different_seed_may_differ(self):
        """Farklı seed genellikle farklı sonuç üretir (not guaranteed ama olası)."""
        xu100 = make_xu100(factor=0.0, days=500)
        sym_prices = {
            "AKBNK": pd.Series(
                np.random.default_rng(99).uniform(90, 110, 400),
                index=pd.date_range("2024-01-02", periods=400, freq="B"),
            )
        }
        trades = make_trade()
        r1 = run_fair_null(trades, sym_prices, xu100, n_iter=10, seed=42)
        r2 = run_fair_null(trades, sym_prices, xu100, n_iter=10, seed=99)
        # Deterministik değil — sadece hata vermediğini doğrula
        assert "null_win_rate_p50" in r1
        assert "null_win_rate_p50" in r2


# ---------------------------------------------------------------------------
# 4. Simulate exit
# ---------------------------------------------------------------------------

class TestSimulateExit:
    def _prices(self, closes: list[float]) -> tuple[np.ndarray, np.ndarray]:
        dates = pd.date_range("2024-01-01", periods=len(closes), freq="B")
        arr = np.array(closes, dtype=float)
        return arr, dates.values

    def test_tp_hit(self):
        """TP fiyatına ulaşıldığında pozitif döner."""
        closes = [100.0] * 5 + [121.0] + [100.0] * 20
        arr, dates = self._prices(closes)
        pnl = _simulate_exit(arr, dates, pd.Timestamp("2024-01-01"))
        assert pnl is not None
        assert pnl > 0.15

    def test_sl_hit(self):
        """SL fiyatına ulaşıldığında negatif döner."""
        closes = [100.0] * 3 + [91.0] + [100.0] * 20
        arr, dates = self._prices(closes)
        pnl = _simulate_exit(arr, dates, pd.Timestamp("2024-01-01"))
        assert pnl is not None
        assert pnl < 0

    def test_max_hold_exit(self):
        """30 gün dolduğunda MTM fiyatla çıkar."""
        closes = [100.0] * 50  # ne SL ne TP
        arr, dates = self._prices(closes)
        pnl = _simulate_exit(arr, dates, pd.Timestamp("2024-01-01"), max_hold=5)
        assert pnl is not None
        assert abs(pnl) < 0.01  # sabit fiyat → ~0


# ---------------------------------------------------------------------------
# 5. Verdict logic
# ---------------------------------------------------------------------------

class TestVerdictLogic:
    def _null(self, p95_wr: float = 0.50, p95_exp: float = 0.0) -> dict:
        return {
            "null_win_rate_p95": p95_wr,
            "null_expectancy_p95": p95_exp,
            "null_win_rate_p50": p95_wr - 0.05,
            "null_expectancy_p50": p95_exp - 0.01,
        }

    def _exp(self, wr: float, reel: float) -> dict:
        return {
            "win_rate_nominal": wr,
            "avg_reel_expectancy": reel,
            "avg_nominal_expectancy": reel,
            "avg_relative_expectancy": reel,
            "relative_win_rate": wr,
            "reel_win_rate": wr,
            "profit_factor_reel": 2.0,
            "n_trades": 100,
            "n_reel_available": 100,
            "avg_win_nominal": 0.1,
            "avg_loss_nominal": -0.05,
            "avg_win_reel": 0.08,
            "avg_loss_reel": -0.04,
        }

    def test_edge_var_all_gates_pass(self):
        """3 gate geçilince EDGE_VAR."""
        exp = self._exp(wr=0.60, reel=0.02)  # WR 60% > null_p95 50%
        null = self._null(p95_wr=0.50, p95_exp=0.0)
        v = compute_verdict(exp, null, tufe_available=True)
        assert v["verdict"] == "EDGE_VAR"

    def test_edge_yok_reel_negative(self):
        """Reel expectancy negatif → EDGE_YOK."""
        exp = self._exp(wr=0.60, reel=-0.01)
        null = self._null(p95_wr=0.50, p95_exp=0.0)
        v = compute_verdict(exp, null, tufe_available=True)
        assert v["verdict"] == "EDGE_YOK"

    def test_edge_yok_wr_fails_null(self):
        """Win rate null'ı geçemeyince EDGE_YOK."""
        exp = self._exp(wr=0.48, reel=0.02)
        null = self._null(p95_wr=0.50, p95_exp=0.0)
        v = compute_verdict(exp, null, tufe_available=True)
        assert v["verdict"] == "EDGE_YOK"

    def test_edge_yok_expectancy_fails_null(self):
        """Reel expectancy null_p95'i geçemeyince EDGE_YOK."""
        exp = self._exp(wr=0.60, reel=0.01)
        null = self._null(p95_wr=0.50, p95_exp=0.02)  # null_p95 > reel
        v = compute_verdict(exp, null, tufe_available=True)
        assert v["verdict"] == "EDGE_YOK"

    def test_tufe_unavailable_uses_nominal(self):
        """TÜFE yok → nominal proxy kullanılır, hata vermez."""
        exp = self._exp(wr=0.60, reel=0.02)
        null = self._null(p95_wr=0.50, p95_exp=0.0)
        v = compute_verdict(exp, null, tufe_available=False)
        assert v["verdict"] in ("EDGE_VAR", "EDGE_YOK")
        assert v.get("tufe_note") is not None


# ---------------------------------------------------------------------------
# 6. Attribution aritmetiği
# ---------------------------------------------------------------------------

class TestAttributionArithmetic:
    def test_open_pos_contribution_closes_the_gap(self):
        """closed_pnl + open_contribution = actual_gain."""
        trade = make_trade(pnl=5000.0, pnl_pct=0.05, entry_price=100.0, shares=100)
        enriched = compute_per_trade_metrics(trade, None, make_xu100(factor=0.0, days=365))

        summary = {
            "initial_capital_tl": 100000.0,
            "final_portfolio_tl": 110000.0,
            "total_commission_tl": 200.0,
            "total_trades": 10,
        }
        attr = compute_attribution(trade, enriched, summary)
        assert abs(
            attr["closed_trades_pnl_tl"] + attr["open_positions_contribution_tl"]
            - attr["actual_gain_tl"]
        ) < 0.01

    def test_inflation_erased_positive_when_tufe_rises(self):
        """Enflasyon yükseldikçe reel P&L < nominal P&L → inflation_erased > 0."""
        tufe = make_tufe(factor=1.50, days=365)  # %50 enflasyon
        xu100 = make_xu100(factor=0.0, days=365)
        trade = make_trade(
            entry_date="2024-01-01", exit_date="2024-12-31",
            pnl_pct=0.30, pnl=3000.0, entry_price=100.0, shares=100,
        )
        enriched = compute_per_trade_metrics(trade, tufe, xu100)
        summary = {
            "initial_capital_tl": 100000.0,
            "final_portfolio_tl": 103000.0,
            "total_commission_tl": 100.0,
            "total_trades": 1,
        }
        attr = compute_attribution(trade, enriched, summary)
        # reel < nominal → inflation_erased_tl > 0
        infl = attr["inflation_erased_tl"]
        if infl != TUFE_UNAVAILABLE:
            assert infl > 0
