"""Unit tests for TL Bond Yield Proxy via CDS (Gap 4 — SPEC_L2_ENHANCEMENT_1)."""
import tempfile
from datetime import datetime, timedelta

import pytest

from src.signals.local.cache_store import LocalMacroCache
from src.signals.local.cds_client import CDSClient
from src.signals.thresholds import TL_BOND_PROXY_BASE_YIELD, TL_BOND_PROXY_SCORES


def _make_cache() -> LocalMacroCache:
    td = tempfile.mkdtemp()
    return LocalMacroCache(db_path=f"{td}/tl_proxy_test.db")


def _date(days_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).date().isoformat()


class TestTlBondProxyFormula:
    """implied_tl_yield = TL_BOND_PROXY_BASE_YIELD + cds_bps / 100."""

    def test_formula_raw_value(self):
        """raw_value equals the implied yield computed from formula."""
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=300.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        expected = TL_BOND_PROXY_BASE_YIELD + 300.0 / 100.0   # 4.5 + 3.0 = 7.5
        assert sig.raw_value == pytest.approx(expected, abs=1e-4)

    def test_medium_bucket(self):
        """CDS=300bps → implied=7.5% → medium bucket → score 50."""
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=300.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.score == TL_BOND_PROXY_SCORES["medium"]

    def test_low_bucket(self):
        """CDS=40bps → implied=4.9% < 5.0 → low bucket → score 70."""
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=40.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.score == TL_BOND_PROXY_SCORES["low"]

    def test_high_bucket(self):
        """CDS=600bps → implied=10.5% → high bucket (8–12%) → score 30."""
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=600.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.score == TL_BOND_PROXY_SCORES["high"]

    def test_extreme_bucket(self):
        """CDS=800bps → implied=12.5% ≥ 12 → extreme bucket → score 15."""
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=800.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.score == TL_BOND_PROXY_SCORES["extreme"]

    def test_no_cds_data_neutral_zero_confidence(self):
        sig = CDSClient(_make_cache()).get_tl_bond_proxy()
        assert sig.score == 50.0
        assert sig.confidence == 0.0
        assert sig.data_freshness == "missing"
        assert sig.component == "tl_bond_proxy"

    def test_component_name(self):
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=300.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.component == "tl_bond_proxy"

    def test_fresh_data_confidence(self):
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=300.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert sig.confidence == 1.0
        assert sig.data_freshness == "fresh"

    def test_audit_msg_contains_implied_yield(self):
        cache = _make_cache()
        cache.store_cds(_date(0), cds_bps=300.0)
        sig = CDSClient(cache).get_tl_bond_proxy()
        assert "7.50" in sig.audit_msg or "implied_tl_yield" in sig.audit_msg
