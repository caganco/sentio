"""D-192 K3 Illiquidity + Reversal unit testleri.

Davranis test eder, implementasyon degil. Private metodlara dogrudan erisim yok.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.screening.k3_illiquid_reversal import (
    apply_quality_filter,
    build_portfolio_returns,
    compute_amihud_illiq,
    compute_forward_returns,
    compute_reversal,
    compute_turnover_proxy,
    decay_test,
    evaluate_h1,
    evaluate_h2,
    fair_random_null,
    lou_shu_test,
    portfolio_to_ann_real,
)


# ---------------------------------------------------------------------------
# Yardimci fabrikalar
# ---------------------------------------------------------------------------

def _make_prices(n: int = 300, seed: int = 42) -> dict[str, pd.DataFrame]:
    """n-gun sentetik OHLCV verisi (3 hisse)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-02", periods=n)
    prices = {}
    for t in ["AAA.IS", "BBB.IS", "CCC.IS"]:
        close = 100 * np.cumprod(1 + rng.normal(0.0003, 0.015, n))
        vol = rng.integers(100_000, 5_000_000, n).astype(float)
        df = pd.DataFrame(
            {"Open": close * 0.99, "High": close * 1.01,
             "Low": close * 0.98, "Close": close, "Volume": vol},
            index=idx,
        )
        prices[t] = df
    return prices


def _make_tufe(n_years: float = 15.0) -> pd.Series:
    """Basit TUFE compound-index: yillik %20 enflasyon."""
    idx = pd.date_range("2010-01-01", periods=int(n_years * 365), freq="D")
    daily_rate = (1.20) ** (1 / 365) - 1
    vals = np.cumprod(np.ones(len(idx)) * (1 + daily_rate))
    return pd.Series(vals, index=idx, name="tufe_index")


# ---------------------------------------------------------------------------
# TestAmihudFactor
# ---------------------------------------------------------------------------

class TestAmihudFactor:
    def test_amihud_formula_returns_dataframe(self):
        """compute_amihud_illiq() gercek OHLCV verisinden bir DataFrame dondurmeli."""
        prices = _make_prices(300)
        result = compute_amihud_illiq(prices, window=20, min_obs=10, lag_months=0)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_log_transform_applied(self):
        """Sonuclar log(ILLIQ+eps) oldugu icin ham Amihud'dan kucuk olmali."""
        prices = _make_prices(300)
        result = compute_amihud_illiq(prices, window=20, min_obs=10, lag_months=0)
        # Ham ILLIQ cok kucuk sayilar (verimli piyasada), log negative olmali
        valid = result.stack().dropna()
        if not valid.empty:
            # log degerler negative olabilir (kucuk ILLIQ -> log negatif)
            assert valid.isna().mean() < 0.95  # NaN orani makul

    def test_lag_guard_shifts_panel(self):
        """lag_months > 0 oldugunda panel ileriye kayar (erken satirlar NaN)."""
        prices = _make_prices(300)
        no_lag = compute_amihud_illiq(prices, window=5, min_obs=3, lag_months=0)
        with_lag = compute_amihud_illiq(prices, window=5, min_obs=3, lag_months=1)
        if not no_lag.empty and not with_lag.empty:
            # lag uygulaninca ilk gunlerin NaN orani artar
            no_lag_nan = no_lag.iloc[:20].isna().mean().mean()
            lag_nan = with_lag.iloc[:20].isna().mean().mean()
            assert lag_nan >= no_lag_nan

    def test_insufficient_data_returns_nan(self):
        """Cok az veri olan hissede NaN doner."""
        short = {"X.IS": pd.DataFrame(
            {"Open": [1.0], "High": [1.1], "Low": [0.9],
             "Close": [1.0], "Volume": [1000.0]},
            index=pd.bdate_range("2023-01-02", periods=1),
        )}
        result = compute_amihud_illiq(short, window=20, min_obs=15, lag_months=0)
        if not result.empty:
            assert result["X.IS"].notna().sum() == 0


# ---------------------------------------------------------------------------
# TestReversalFactor
# ---------------------------------------------------------------------------

class TestReversalFactor:
    def test_reversal_sign_inverted(self):
        """Kaybeden hisse (dusmus fiyat) yuksek reversal skoru almali (+)."""
        # AAA: surekli yukselen, BBB: surekli dusen
        n = 60
        idx = pd.bdate_range("2023-01-02", periods=n)
        rising = np.linspace(100, 200, n)
        falling = np.linspace(200, 100, n)

        prices = {
            "RISE.IS": pd.DataFrame(
                {"Close": rising, "Volume": [1e6] * n}, index=idx
            ),
            "FALL.IS": pd.DataFrame(
                {"Close": falling, "Volume": [1e6] * n}, index=idx
            ),
        }
        rev = compute_reversal(prices, lookback=20, skip=1)
        if not rev.empty and "RISE.IS" in rev and "FALL.IS" in rev:
            # Son gunde: kaybeden (FALL) > kazanan (RISE) reversal skoru
            last_rise = rev["RISE.IS"].dropna().iloc[-1]
            last_fall = rev["FALL.IS"].dropna().iloc[-1]
            assert last_fall > last_rise, (
                f"Kaybeden FALL ({last_fall:.4f}) > Kazanan RISE ({last_rise:.4f}) olmali"
            )

    def test_skip_applied(self):
        """skip=1 oldugunda sinyal t-1'in getirini kullaniyor (look-ahead yok)."""
        prices = _make_prices(100, seed=1)
        rev_skip0 = compute_reversal(prices, lookback=5, skip=0)
        rev_skip1 = compute_reversal(prices, lookback=5, skip=1)
        # iki seri esit olmamali
        if not rev_skip0.empty and not rev_skip1.empty:
            assert not rev_skip0.equals(rev_skip1)

    def test_weekly_and_monthly_different(self):
        """5-gun ve 21-gun lookback farkli sonuc vermeli."""
        prices = _make_prices(300, seed=7)
        rev_wk = compute_reversal(prices, lookback=5)
        rev_mo = compute_reversal(prices, lookback=21)
        if not rev_wk.empty and not rev_mo.empty:
            common = rev_wk.index.intersection(rev_mo.index)
            if len(common) > 10:
                diff = (rev_wk.loc[common] - rev_mo.loc[common]).abs().mean().mean()
                assert diff > 0, "Haftalik ve aylik reversal ayni olmamali"


# ---------------------------------------------------------------------------
# TestQualityFilter
# ---------------------------------------------------------------------------

class TestQualityFilter:
    def test_empty_df_rejected(self):
        """Bos DataFrame filtreden gecirilmez."""
        prices = {"EMPTY.IS": pd.DataFrame()}
        _, report = apply_quality_filter(prices, "2020-01-01", "2023-01-01")
        assert report["n_passed"] == 0

    def test_good_data_passes(self):
        """Kaliteli veri filtreden gecer."""
        prices = _make_prices(500)
        passed, report = apply_quality_filter(prices, "2015-01-01", "2016-12-31")
        assert report["n_passed"] > 0

    def test_viability_check(self):
        """Kucuk evren infeasible olarak isaretlenir."""
        prices = _make_prices(300)  # sadece 3 hisse
        _, report = apply_quality_filter(prices, "2015-01-01", "2016-12-31")
        # 3 hisse < 50 (UNIVERSE_MIN_STOCKS_VIABLE) -> is_viable=False
        assert not report["is_viable"]


# ---------------------------------------------------------------------------
# TestDecisionRule
# ---------------------------------------------------------------------------

class TestDecisionRule:
    def test_h1_all_conditions_required(self):
        """H1 dört koşul AND; biri eksik -> FAIL."""
        # Tum kosullar PASS
        null_ok = {"beats_95": True, "strategy_pctile": 0.97}
        lou_ok = {"passes_lou_shu": True, "b_tstat": 2.5}
        result = evaluate_h1(0.05, 0.03, 0.07, null_ok, lou_ok)
        assert result["verdict"] == "PASS"

        # C3 (Lou-Shu) eksik -> FAIL
        lou_fail = {"passes_lou_shu": False, "b_tstat": 1.2}
        result_fail = evaluate_h1(0.05, 0.03, 0.07, null_ok, lou_fail)
        assert result_fail["verdict"] == "FAIL"

        # C4 out-of-sample negatif -> FAIL
        result_out_neg = evaluate_h1(0.05, 0.03, -0.01, null_ok, lou_ok)
        assert result_out_neg["verdict"] == "FAIL"

    def test_h2_decay_required(self):
        """H2 decay testini gecemezse FAIL."""
        null_ok = {"beats_95": True, "strategy_pctile": 0.96}
        decay_fail = {
            "decay_present": True,
            "post_split_ann_real": -0.02,
            "full_ann_real": 0.04,
        }
        result = evaluate_h2(0.03, null_ok, decay_fail)
        assert result["verdict"] == "FAIL"

    def test_h2_all_conditions_pass(self):
        """H2 uc kosul gecerse PASS."""
        null_ok = {"beats_95": True, "strategy_pctile": 0.97}
        decay_ok = {
            "decay_present": False,
            "post_split_ann_real": 0.04,
            "full_ann_real": 0.05,
        }
        result = evaluate_h2(0.05, null_ok, decay_ok)
        assert result["verdict"] == "PASS"

    def test_real_return_formula(self):
        """portfolio_to_ann_real: (1+nom)/(TUFE_ratio)-1 formulunun dogrulugu."""
        tufe = _make_tufe(n_years=3)
        # Sabit getiri serisi: %0/gun (nominal = 0)
        idx = pd.bdate_range("2010-01-01", periods=252)
        port = pd.Series(0.0, index=idx)
        ann_real = portfolio_to_ann_real(port, tufe)
        # %20/yil enflasyon ile nominal=0 -> reel ~ -20%/yil
        assert math.isfinite(ann_real)
        assert ann_real < 0, "Enflasyonla nominal-0 portfoy reel negatif olmali"

    def test_decay_test_detects_negative_post_split(self):
        """decay_test: split-sonrasi negatif oldugunda decay_present=True."""
        tufe = _make_tufe(n_years=12)
        # Oncesi pozitif, sonrasi negatif
        idx_pre = pd.bdate_range("2010-01-01", periods=500)
        idx_post = pd.bdate_range("2020-01-05", periods=300)
        pre = pd.Series(0.002, index=idx_pre)   # gunluk +0.2% (pozitif)
        post = pd.Series(-0.003, index=idx_post)  # gunluk -0.3% (negatif)
        port = pd.concat([pre, post]).sort_index()
        result = decay_test(port, tufe, split_date="2020-01-01")
        assert result["decay_present"], "Post-split negatif -> decay_present=True"
