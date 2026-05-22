"""Tests for D-127: PaySahipligi KAP filter + L5 major_holder_change signal.

SPK XI.29.1 — Pay Sahipligi Bildirimi (major shareholder notification) at 5% threshold.
No live KAP data fetched; all tests use inline fixtures.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_l5_df(symbol: str = "AKBNK", n_days: int = 15):
    """Synthetic L5 DataFrame: flat foreign_ratio → momentum score = 50.0."""
    import pandas as pd
    from datetime import date, timedelta as td
    today = date.today()
    dates = [(today - td(days=i)).isoformat() for i in range(n_days)]
    fresh = datetime.now(timezone.utc).isoformat()
    return pd.DataFrame({
        "symbol": [symbol] * n_days,
        "date": dates,
        "foreign_ratio": [0.30] * n_days,
        "volume_3m_mn_usd": [40.0] * n_days,
        "written_at": [fresh] * n_days,
    })


# ---------------------------------------------------------------------------
# kap_parser — EventCategory + classification
# ---------------------------------------------------------------------------

class TestKapParserPaySahipligi:
    def test_pay_sahipligi_literal_exists(self):
        """EventCategory Literal icinde 'pay_sahipligi' olmali."""
        import typing
        from src.data.kap_parser import EventCategory
        args = typing.get_args(EventCategory)
        assert "pay_sahipligi" in args

    def test_classify_category_entry_subject(self):
        from src.data.kap_parser import classify_category
        result = classify_category("Pay Sahipligi Bildirimi - Artti")
        assert result == "pay_sahipligi"

    def test_classify_category_generic_pay_subject(self):
        from src.data.kap_parser import classify_category
        result = classify_category("Onemli Pay Sahibi Degisikligi")
        assert result == "pay_sahipligi"

    def test_classify_category_long_form(self):
        from src.data.kap_parser import classify_category
        result = classify_category("Pay Sahipligi Bildirimi - Onemli Pay Sahipligi")
        assert result == "pay_sahipligi"

    def test_no_false_positive_temettu(self):
        from src.data.kap_parser import classify_category
        result = classify_category("Temettu Bildirimi 2.50 TL brut")
        assert result == "temettu"

    def test_no_false_positive_finansal(self):
        from src.data.kap_parser import classify_category
        result = classify_category("Finansal Rapor Q1 2026")
        assert result == "finansal_rapor"

    def test_extract_structured_data_entry(self):
        from src.data.kap_parser import extract_structured_data
        result = extract_structured_data("Pay Sahipligi Bildirimi - Pay Orani artis", "pay_sahipligi", [])
        assert result["direction"] == "ENTRY"
        assert result["threshold_pct"] == 5.0

    def test_extract_structured_data_exit(self):
        from src.data.kap_parser import extract_structured_data
        result = extract_structured_data("Pay Sahipligi Bildirimi - Pay Orani azaldi", "pay_sahipligi", [])
        assert result["direction"] == "EXIT"
        assert result["threshold_pct"] == 5.0

    def test_extract_structured_data_unknown(self):
        from src.data.kap_parser import extract_structured_data
        result = extract_structured_data("Pay Sahipligi Bildirimi", "pay_sahipligi", [])
        assert result["direction"] == "UNKNOWN"
        assert "threshold_pct" in result

    def test_extract_structured_data_other_categories_unchanged(self):
        """diger category hala {} donmeli."""
        from src.data.kap_parser import extract_structured_data
        result = extract_structured_data("Herhangi bir bildirim", "diger", [])
        assert result == {}


# ---------------------------------------------------------------------------
# kap_scraper — _is_pay_sahipligi + classify_disclosure
# ---------------------------------------------------------------------------

class TestKapScraperPaySahipligi:
    def test_is_pay_sahipligi_helper_true(self):
        from src.data.kap_scraper import _is_pay_sahipligi
        assert _is_pay_sahipligi("pay sahipligi bildirimi") is True
        assert _is_pay_sahipligi("onemli pay sahibi degisikligi") is True

    def test_is_pay_sahipligi_helper_false(self):
        from src.data.kap_scraper import _is_pay_sahipligi
        assert _is_pay_sahipligi("temettu bildirimi") is False
        assert _is_pay_sahipligi("finansal rapor") is False
        assert _is_pay_sahipligi("genel kurul toplantisi") is False

    def test_classify_disclosure_pay_sahipligi_critical(self):
        from src.data.kap_scraper import classify_disclosure
        result = classify_disclosure("Pay Sahipligi Bildirimi - Artti")
        assert result == "CRITICAL"

    def test_classify_disclosure_onemli_pay_sahibi_critical(self):
        from src.data.kap_scraper import classify_disclosure
        result = classify_disclosure("Onemli Pay Sahibi Azalis Bildirimi")
        assert result == "CRITICAL"


# ---------------------------------------------------------------------------
# smart_money_layer — major_holder_change_score blend
# ---------------------------------------------------------------------------

class TestSmartMoneyMajorHolder:
    def test_compute_l5_score_accepts_major_holder_param(self):
        """Fonksiyon imzasinda major_holder_change_score olmali."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        sig = inspect.signature(SmartMoneyL5.compute_l5_score)
        assert "major_holder_change_score" in sig.parameters

    def test_major_holder_default_is_none(self):
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        sig = inspect.signature(SmartMoneyL5.compute_l5_score)
        default = sig.parameters["major_holder_change_score"].default
        assert default is None

    def test_major_holder_entry_raises_score(self):
        """Entry score (75) ile blend yapilinca base'den yuksek olmali."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        df = _make_l5_df(n_days=15)  # momentum-only phase, flat → base ≈ 50.0
        with patch.object(layer, "_load_history", return_value=df):
            base = layer.compute_l5_score("AKBNK")
            result = layer.compute_l5_score("AKBNK", major_holder_change_score=75.0)
        assert base is not None
        assert result is not None
        assert result > base

    def test_major_holder_exit_lowers_score(self):
        """Exit score (25) ile blend yapilinca base'den dusuk olmali."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        df = _make_l5_df(n_days=15)
        with patch.object(layer, "_load_history", return_value=df):
            base = layer.compute_l5_score("AKBNK")
            result = layer.compute_l5_score("AKBNK", major_holder_change_score=25.0)
        assert base is not None
        assert result is not None
        assert result < base

    def test_major_holder_none_unchanged(self):
        """major_holder_change_score=None → ayni sonuc."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        df = _make_l5_df(n_days=15)
        with patch.object(layer, "_load_history", return_value=df):
            result_no_param = layer.compute_l5_score("AKBNK")
            result_none = layer.compute_l5_score("AKBNK", major_holder_change_score=None)
        assert result_no_param == result_none

    def test_major_holder_blend_clamped_to_100(self):
        """Yuksek entry score bile 100'u asmamali."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        df = _make_l5_df(n_days=15)
        with patch.object(layer, "_load_history", return_value=df):
            result = layer.compute_l5_score("AKBNK", major_holder_change_score=100.0)
        assert result is not None
        assert result <= 100.0

    def test_major_holder_blend_clamped_to_zero(self):
        """Dusuk exit score bile 0'in altina dusmemeli."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        df = _make_l5_df(n_days=15)
        with patch.object(layer, "_load_history", return_value=df):
            result = layer.compute_l5_score("AKBNK", major_holder_change_score=0.0)
        assert result is not None
        assert result >= 0.0

    def test_major_holder_no_data_returns_none(self):
        """Veri yokken (None) major_holder_change_score etkisiz olmali."""
        from src.signals.layers.smart_money_layer import SmartMoneyL5
        layer = SmartMoneyL5()
        with patch.object(layer, "_load_history", return_value=None):
            result = layer.compute_l5_score("AKBNK", major_holder_change_score=75.0)
        assert result is None


# ---------------------------------------------------------------------------
# thresholds — constant presence check
# ---------------------------------------------------------------------------

class TestMajorHolderThresholds:
    def test_constants_exist(self):
        from src.signals.thresholds import (
            MAJOR_HOLDER_CHANGE_THRESHOLD_PCT,
            MAJOR_HOLDER_CHANGE_LOOKBACK_DAYS,
            L5_MAJOR_HOLDER_WEIGHT,
            L5_MAJOR_HOLDER_ENTRY_SCORE,
            L5_MAJOR_HOLDER_EXIT_SCORE,
        )
        assert MAJOR_HOLDER_CHANGE_THRESHOLD_PCT == 5.0
        assert MAJOR_HOLDER_CHANGE_LOOKBACK_DAYS == 30
        assert 0.0 < L5_MAJOR_HOLDER_WEIGHT < 1.0
        assert L5_MAJOR_HOLDER_ENTRY_SCORE > 50.0
        assert L5_MAJOR_HOLDER_EXIT_SCORE < 50.0

    def test_entry_score_greater_than_exit(self):
        from src.signals.thresholds import L5_MAJOR_HOLDER_ENTRY_SCORE, L5_MAJOR_HOLDER_EXIT_SCORE
        assert L5_MAJOR_HOLDER_ENTRY_SCORE > L5_MAJOR_HOLDER_EXIT_SCORE
