"""Brinson-Fachler Attribution (DEC-015).

Formulas (Brinson, Hood & Beebower 1986; Fachler 1994):
    Allocation:  A_j = (w_p,j - w_b,j) * (R_b,j - R_b)
    Selection:   S_j = w_b,j * (R_p,j - R_b,j)
    Interaction: I_j = (w_p,j - w_b,j) * (R_p,j - R_b,j)
    Total active = A + S + I = R_p - R_b

Multi-period: Carino (1999) geometric linking.
Benchmark: BIST100 equal-weight (DEC-015 default).
Sector classification: get_sector() from src/data/database.py (DEC-014: no MAP duplication).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from src.data.database import get_sector

logger = logging.getLogger(__name__)


@dataclass
class BrinsonResult:
    sector: str
    w_portfolio: float
    w_benchmark: float
    r_portfolio: float
    r_benchmark: float
    r_benchmark_total: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_active: float


@dataclass
class BrinsonPeriodResult:
    period_start: str
    period_end: str
    portfolio_return: float
    benchmark_return: float
    active_return: float
    total_allocation: float
    total_selection: float
    total_interaction: float
    by_sector: list[BrinsonResult]


class BrinsonAttributor:
    """Single-period Brinson-Fachler + multi-period Carino linking."""

    def compute_period(
        self,
        portfolio_weights: dict[str, float],
        portfolio_returns: dict[str, float],
        benchmark_returns: dict[str, float],
        period_start: str = "",
        period_end: str = "",
    ) -> BrinsonPeriodResult:
        sectors = _get_sectors(portfolio_weights, benchmark_returns)
        n_b = len(benchmark_returns)
        w_b_equal = 1.0 / n_b if n_b > 0 else 0.0

        r_b_total = (np.mean(list(benchmark_returns.values()))
                     if benchmark_returns else 0.0)
        r_p_total = sum(portfolio_weights.get(s, 0) * portfolio_returns.get(s, 0)
                        for s in portfolio_weights)

        sector_results: list[BrinsonResult] = []
        for sector, symbols in sectors.items():
            p_syms = [s for s in symbols if s in portfolio_weights]
            w_p_j = sum(portfolio_weights.get(s, 0) for s in p_syms)
            r_p_j = (
                sum(portfolio_weights.get(s, 0) * portfolio_returns.get(s, 0) for s in p_syms) / w_p_j
                if w_p_j > 0 else 0.0
            )

            b_syms = [s for s in symbols if s in benchmark_returns]
            w_b_j = len(b_syms) * w_b_equal
            r_b_j = float(np.mean([benchmark_returns[s] for s in b_syms])) if b_syms else 0.0

            a_j = (w_p_j - w_b_j) * (r_b_j - r_b_total)
            s_j = w_b_j * (r_p_j - r_b_j)
            i_j = (w_p_j - w_b_j) * (r_p_j - r_b_j)

            sector_results.append(BrinsonResult(
                sector=sector,
                w_portfolio=round(w_p_j, 6),
                w_benchmark=round(w_b_j, 6),
                r_portfolio=round(r_p_j, 6),
                r_benchmark=round(r_b_j, 6),
                r_benchmark_total=round(r_b_total, 6),
                allocation_effect=round(a_j, 6),
                selection_effect=round(s_j, 6),
                interaction_effect=round(i_j, 6),
                total_active=round(a_j + s_j + i_j, 6),
            ))

        return BrinsonPeriodResult(
            period_start=period_start,
            period_end=period_end,
            portfolio_return=round(r_p_total, 6),
            benchmark_return=round(r_b_total, 6),
            active_return=round(r_p_total - r_b_total, 6),
            total_allocation=round(sum(r.allocation_effect for r in sector_results), 6),
            total_selection=round(sum(r.selection_effect for r in sector_results), 6),
            total_interaction=round(sum(r.interaction_effect for r in sector_results), 6),
            by_sector=sector_results,
        )

    def carino_link(self, period_results: list[BrinsonPeriodResult]) -> dict:
        """Geometric linking via Carino (1999) for multi-period attribution."""
        if not period_results:
            return {}
        total = {"allocation": 0.0, "selection": 0.0, "interaction": 0.0}
        r_p_total = 1.0
        for pr in period_results:
            r_p_total *= (1 + pr.portfolio_return)
        R_p = r_p_total - 1.0
        K = np.log(1 + R_p) / R_p if abs(R_p) > 1e-8 else 1.0

        for pr in period_results:
            r_p = pr.portfolio_return
            k_t = (np.log(1 + r_p) / r_p) / K if abs(r_p) > 1e-8 else 1.0 / K
            total["allocation"]  += k_t * pr.total_allocation
            total["selection"]   += k_t * pr.total_selection
            total["interaction"] += k_t * pr.total_interaction
        total["active_return"] = sum(total.values())
        return {k: round(v, 6) for k, v in total.items()}


def _get_sectors(portfolio_weights: dict, benchmark_returns: dict) -> dict[str, list[str]]:
    """Group all symbols by get_sector(). Unknown -> 'OTHER'."""
    all_symbols = set(portfolio_weights) | set(benchmark_returns)
    sectors: dict[str, list[str]] = {}
    for sym in all_symbols:
        try:
            sector = get_sector(sym) or "OTHER"
        except Exception:
            sector = "OTHER"
        sectors.setdefault(sector, []).append(sym)
    return sectors
