"""Layer Marginal Contribution via Leave-One-Out (DEC-015).

LOO: leave layer L_i out, recompute composite -> R_full - R_{full\\L_i}.
Positive LOO = removing L_i hurts -> L_i contributes positively.

Optional Shapley decomposition (2^6=64 coalitions) -- weekly batch only.

CLAUDE.md compliance: layer weights imported from thresholds.MASTER_WEIGHTS
(no hardcoded dict). Mapping signal-log column names (l1_tech_score, ...) to
engine layer names (technical, ...) via _LAYER_COL_TO_NAME.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from src.signals.thresholds import MASTER_WEIGHTS

logger = logging.getLogger(__name__)

# Map signal_log column names (Phase 4.5 schema) -> engine layer names
_LAYER_COL_TO_NAME: dict[str, str] = {
    "l1_tech_score":  "technical",
    "l2_macro_score": "macro",
    "l3_kap_score":   "kap",
    "l4_sent_score":  "sentiment",
    "l5_sm_score":    "smart_money",
    "l6_risk_score":  "risk",
}

LAYER_COLS = tuple(_LAYER_COL_TO_NAME.keys())


def _w_for_col(col: str) -> float:
    """Lookup MASTER_WEIGHTS for a signal_log column."""
    layer_name = _LAYER_COL_TO_NAME.get(col)
    if layer_name is None:
        return 0.01
    return MASTER_WEIGHTS.get(layer_name, 0.01)


@dataclass
class LOOResult:
    """Leave-One-Out attribution for one layer."""
    layer: str
    marginal_ic: float      # IC_full - IC_full_minus_layer
    marginal_return: float
    direction: str          # "positive" | "negative" | "neutral"


class LayerAttributor:
    """Compute LOO marginal contribution per layer + optional Shapley.

    Usage:
        attr = LayerAttributor(signal_df, returns_df)
        results = attr.compute_loo(horizon=5)
    """

    def __init__(self, signal_df: pd.DataFrame, returns_df: pd.DataFrame) -> None:
        self._sig = signal_df
        self._ret = returns_df

    def compute_loo(self, horizon: int = 5, universe: str = "all") -> list[LOOResult]:
        """Daily LOO attribution for each of 6 layers."""
        from src.analytics.ic_calculator import ICCalculator

        if self._sig.empty or self._ret.empty:
            return [LOOResult(layer=l, marginal_ic=0.0, marginal_return=0.0,
                              direction="neutral") for l in LAYER_COLS]

        calc_full = ICCalculator(self._sig, self._ret)
        full_ic = calc_full.compute_ic("composite_score", horizon, universe)
        full_val = 0.0 if np.isnan(full_ic.mean_ic) else float(full_ic.mean_ic)

        results: list[LOOResult] = []
        for col in LAYER_COLS:
            loo_df = self._build_loo_composite(col)
            calc_loo = ICCalculator(loo_df, self._ret)
            loo_ic = calc_loo.compute_ic("loo_composite", horizon, universe)
            loo_val = 0.0 if np.isnan(loo_ic.mean_ic) else float(loo_ic.mean_ic)
            marginal = full_val - loo_val
            direction = ("positive" if marginal > 0.001
                         else "negative" if marginal < -0.001 else "neutral")
            results.append(LOOResult(
                layer=col, marginal_ic=round(marginal, 5),
                marginal_return=0.0, direction=direction,
            ))
        return results

    def _build_loo_composite(self, excluded_col: str) -> pd.DataFrame:
        """Recompute composite WITHOUT excluded_col."""
        df = self._sig.copy()
        remaining = [c for c in LAYER_COLS if c != excluded_col and c in df.columns]
        total_w = sum(_w_for_col(c) for c in remaining)
        if total_w <= 0:
            df["loo_composite"] = 50.0
            return df
        composite = sum(df[c] * (_w_for_col(c) / total_w) for c in remaining)
        df["loo_composite"] = composite
        return df

    def compute_shapley_weekly(
        self,
        horizon: int = 5,
        n_symbols_sample: int = 50,
    ) -> dict[str, float]:
        """Shapley value decomposition (2^6=64 coalitions). Slow -- weekly batch only."""
        from src.analytics.ic_calculator import ICCalculator
        if self._sig.empty or self._ret.empty:
            return {c: 0.0 for c in LAYER_COLS}

        n = len(LAYER_COLS)
        shapley = {c: 0.0 for c in LAYER_COLS}
        df_sample = (self._sig.sample(min(n_symbols_sample, len(self._sig)),
                                       random_state=42)
                      if len(self._sig) > n_symbols_sample else self._sig.copy())

        for layer in LAYER_COLS:
            others = [c for c in LAYER_COLS if c != layer]
            for coalition_size in range(n):
                for coalition in combinations(others, coalition_size):
                    coalition_list = list(coalition)
                    with_layer = coalition_list + [layer]
                    without_layer = coalition_list
                    ic_with = self._coalition_ic(df_sample, with_layer, horizon)
                    ic_without = self._coalition_ic(df_sample, without_layer, horizon)
                    marginal = ic_with - ic_without
                    s = len(coalition_list)
                    weight = (math.factorial(s) * math.factorial(n - s - 1)
                              / math.factorial(n))
                    shapley[layer] += weight * marginal
        return {k: round(v, 5) for k, v in shapley.items()}

    def _coalition_ic(self, df: pd.DataFrame, layers: list[str], horizon: int) -> float:
        from src.analytics.ic_calculator import ICCalculator
        if not layers:
            return 0.0
        total_w = sum(_w_for_col(c) for c in layers)
        if total_w <= 0:
            return 0.0
        df_c = df.copy()
        df_c["coalition_composite"] = sum(
            df[c] * (_w_for_col(c) / total_w) for c in layers if c in df.columns
        )
        calc = ICCalculator(df_c, self._ret)
        r = calc.compute_ic("coalition_composite", horizon)
        return 0.0 if np.isnan(r.mean_ic) else float(r.mean_ic)
