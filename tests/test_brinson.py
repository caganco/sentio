"""Brinson-Fachler attribution tests (D-107, SPEC_ALPHA_INFRASTRUCTURE_1 Phase 5)."""
from __future__ import annotations

import pytest

from src.analytics.brinson_attribution import BrinsonAttributor, BrinsonPeriodResult


class TestBrinsonAttribution:

    def test_allocation_effect_formula(self):
        """A_j = (w_p,j - w_b,j) * (R_b,j - R_b) -- analytical check."""
        # 2 sectors equally split in benchmark; portfolio overweights sector A.
        # Sector A symbols: AKBNK (banking), GARAN (banking)
        # Sector B symbols: THYAO (airline), TAVHL (airline)
        portfolio_w = {"AKBNK": 0.6, "GARAN": 0.2, "THYAO": 0.1, "TAVHL": 0.1}
        portfolio_r = {"AKBNK": 0.05, "GARAN": 0.05, "THYAO": 0.02, "TAVHL": 0.02}
        benchmark_r = {"AKBNK": 0.05, "GARAN": 0.05, "THYAO": 0.02, "TAVHL": 0.02}
        result = BrinsonAttributor().compute_period(portfolio_w, portfolio_r, benchmark_r)
        # Active return = portfolio - benchmark
        # When sector returns match benchmark exactly (selection=0, interaction=0)
        # all active return collapses to allocation.
        assert result.active_return == pytest.approx(
            result.total_allocation, abs=1e-6,
        )

    def test_effects_sum_to_active_return(self):
        """Sum(A + S + I) across all sectors = R_p - R_b."""
        portfolio_w = {"AKBNK": 0.4, "THYAO": 0.4, "TUPRS": 0.2}
        portfolio_r = {"AKBNK": 0.08, "THYAO": 0.02, "TUPRS": -0.01}
        benchmark_r = {"AKBNK": 0.05, "THYAO": 0.03, "TUPRS": 0.01, "ASELS": 0.02}
        result = BrinsonAttributor().compute_period(portfolio_w, portfolio_r, benchmark_r)
        total_effects = (result.total_allocation + result.total_selection +
                         result.total_interaction)
        assert total_effects == pytest.approx(result.active_return, abs=1e-5)

    def test_zero_active_return_when_portfolio_equals_benchmark(self):
        """w_p = w_b, R_p,j = R_b,j -> all effects = 0."""
        # Equal-weight portfolio matching benchmark exactly
        weights = {"AKBNK": 0.25, "GARAN": 0.25, "THYAO": 0.25, "TUPRS": 0.25}
        returns = {"AKBNK": 0.04, "GARAN": 0.05, "THYAO": 0.03, "TUPRS": 0.02}
        result = BrinsonAttributor().compute_period(weights, returns, returns)
        assert result.active_return == pytest.approx(0.0, abs=1e-6)
        assert result.total_allocation == pytest.approx(0.0, abs=1e-6)
        assert result.total_selection == pytest.approx(0.0, abs=1e-6)
        assert result.total_interaction == pytest.approx(0.0, abs=1e-6)

    def test_carino_link_preserves_total_active(self):
        """2-period Carino linking sums to the geometric total active return."""
        attr = BrinsonAttributor()
        w = {"AKBNK": 0.5, "THYAO": 0.5}
        r1 = {"AKBNK": 0.05, "THYAO": 0.03}
        r2 = {"AKBNK": 0.02, "THYAO": 0.04}
        b1 = {"AKBNK": 0.03, "THYAO": 0.03, "TUPRS": 0.02}
        b2 = {"AKBNK": 0.01, "THYAO": 0.03, "TUPRS": 0.01}
        p1 = attr.compute_period(w, r1, b1, "2026-Q1", "2026-Q1")
        p2 = attr.compute_period(w, r2, b2, "2026-Q2", "2026-Q2")
        linked = attr.carino_link([p1, p2])
        # Sum of allocation+selection+interaction approximates total active return
        active_calc = linked["allocation"] + linked["selection"] + linked["interaction"]
        assert linked["active_return"] == pytest.approx(active_calc, abs=1e-6)
