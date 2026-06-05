"""Tier-A tests for the real CSCV median-rank PBO (Section 4.1/5).

The probe must land at the three reference points that distinguish it from the
``sum(s<0)/len`` proxy: an order that transfers IS->OOS gives PBO ~ 0, pure noise
gives ~ 0.5, and an inverted order gives ~ 1. Degenerate buckets (NaN) must be
excluded, not crash.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.engine.pbo import cscv_pbo

_R, _B = 400, 10


class TestReferencePoints:
    def test_transferring_order_gives_low_pbo(self):
        # Every split: bucket value increases with column in BOTH arms -> the
        # IS-best bucket (last column) is also OOS-best -> omega ~ 1 -> lambda > 0.
        rng = np.random.default_rng(0)
        base = np.arange(_B, dtype=float)
        m_is = base[None, :] + rng.normal(0, 0.01, size=(_R, _B))
        m_oos = base[None, :] + rng.normal(0, 0.01, size=(_R, _B))
        assert cscv_pbo(m_is, m_oos) < 0.05

    def test_pure_noise_gives_half(self):
        rng = np.random.default_rng(1)
        m_is = rng.normal(size=(_R, _B))
        m_oos = rng.normal(size=(_R, _B))
        assert abs(cscv_pbo(m_is, m_oos) - 0.5) < 0.08

    def test_inverted_order_gives_high_pbo(self):
        # OOS is the negated IS ranking -> the IS-best bucket is the OOS-worst ->
        # omega ~ 1/(B+1) < 0.5 -> lambda < 0 for every split.
        rng = np.random.default_rng(2)
        m_is = rng.normal(size=(_R, _B))
        m_oos = -m_is
        assert cscv_pbo(m_is, m_oos) > 0.95


class TestDegenerateBuckets:
    def test_nan_bucket_excluded_not_crashed(self):
        rng = np.random.default_rng(3)
        base = np.arange(_B, dtype=float)
        m_is = base[None, :] + rng.normal(0, 0.01, size=(_R, _B))
        m_oos = base[None, :] + rng.normal(0, 0.01, size=(_R, _B))
        m_is[:, 4] = np.nan  # one degenerate bucket across all splits
        m_oos[:, 4] = np.nan
        out = cscv_pbo(m_is, m_oos)
        assert math.isfinite(out) and out < 0.05  # still transfers on the live buckets

    def test_row_below_min_valid_is_dropped(self):
        # A split with fewer than two jointly-valid buckets carries no rank and is
        # dropped; the remaining single good row drives the fraction.
        m_is = np.array([[1.0, 2.0, 3.0], [np.nan, np.nan, 5.0]])
        m_oos = np.array([[1.0, 2.0, 3.0], [np.nan, np.nan, 9.0]])
        assert cscv_pbo(m_is, m_oos) == 0.0  # only row 0 ranks; its IS-best is OOS-best

    def test_all_nan_returns_nan(self):
        m = np.full((5, _B), np.nan)
        assert math.isnan(cscv_pbo(m, m))


class TestContract:
    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError):
            cscv_pbo(np.zeros((3, 4)), np.zeros((3, 5)))

    def test_non_2d_raises(self):
        with pytest.raises(ValueError):
            cscv_pbo(np.zeros(4), np.zeros(4))
