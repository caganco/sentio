"""LayerAttributor LOO tests (D-107, SPEC_ALPHA_INFRASTRUCTURE_1 Phase 5 -- arastirma katmani coverage hygiene)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from src.analytics.layer_attribution import LAYER_COLS, LayerAttributor


def _build_signals_with_one_dominant_layer(
    dominant: str = "l1_tech_score",
    n_dates: int = 25,
    n_symbols: int = 12,
    seed: int = 7,
):
    """Build signal/return frames where one layer perfectly predicts returns,
    others are pure noise. compute_loo should attribute marginal_ic positively
    to the dominant layer and ~zero to noise layers.
    """
    rng = np.random.default_rng(seed)
    dates = [date(2026, 1, 5) + timedelta(days=i) for i in range(n_dates)]
    symbols = [f"SYM{j:02d}" for j in range(n_symbols)]
    returns_mat = rng.standard_normal((n_dates, n_symbols)) * 0.02

    sig_rows = []
    for i, d in enumerate(dates):
        for j, sym in enumerate(symbols):
            r = float(returns_mat[i, j])
            row = {
                "date": d, "symbol": sym,
                "regime_label": "BULL",
                "liquidity_tier": "BIST100",
                "price_limit_hit": False,
            }
            for col in LAYER_COLS:
                # Dominant layer carries the forward return signal; others are noise
                if col == dominant:
                    row[col] = 50.0 + r * 200.0
                else:
                    row[col] = 50.0 + float(rng.standard_normal()) * 2.0
            # Equal-weight composite as a stand-in (engine logic mirrored)
            row["composite_score"] = float(np.mean([row[c] for c in LAYER_COLS]))
            sig_rows.append(row)

    ret_rows = []
    for i, d in enumerate(dates):
        for j, sym in enumerate(symbols):
            ret_rows.append({
                "signal_date": d, "symbol": sym, "horizon": 5,
                "forward_return": float(returns_mat[i, j]),
                "price_limit_hit": False,
                "filled_at": datetime(2026, 5, 20, tzinfo=timezone.utc),
            })

    return pd.DataFrame(sig_rows), pd.DataFrame(ret_rows)


def test_compute_loo_basic_correctness():
    """Synthetic single-dominant-layer setup: removing dominant layer must hurt IC.

    marginal_ic = IC_full - IC_without_layer. When the dominant layer carries
    the signal, removing it drops IC -> marginal_ic > 0 (positive direction).
    Noise layers should have |marginal_ic| close to zero.
    """
    sig_df, ret_df = _build_signals_with_one_dominant_layer(dominant="l1_tech_score")
    results = LayerAttributor(sig_df, ret_df).compute_loo(horizon=5)
    assert len(results) == 6

    by_layer = {r.layer: r for r in results}
    # The dominant layer must show the largest absolute marginal IC and
    # a positive direction (removing it hurts the full-model IC).
    dominant_marg = by_layer["l1_tech_score"].marginal_ic
    other_margs = [abs(by_layer[l].marginal_ic) for l in LAYER_COLS if l != "l1_tech_score"]
    assert dominant_marg > 0.0, f"dominant layer marginal_ic={dominant_marg}"
    assert dominant_marg >= max(other_margs), \
        f"dominant {dominant_marg} not >= max noise {max(other_margs)}"


def test_compute_loo_empty_input_returns_neutral_results():
    """Empty signal_df / returns_df -> 6 LOOResult with marginal_ic=0 and neutral direction.

    Must NOT raise. Empty-state graceful handling is required for Phase 6
    dashboard CLI to render before data accumulates.
    """
    empty_sig = pd.DataFrame()
    empty_ret = pd.DataFrame()
    results = LayerAttributor(empty_sig, empty_ret).compute_loo(horizon=5)
    assert len(results) == 6
    assert all(r.marginal_ic == 0.0 for r in results)
    assert all(r.direction == "neutral" for r in results)
    assert {r.layer for r in results} == set(LAYER_COLS)
