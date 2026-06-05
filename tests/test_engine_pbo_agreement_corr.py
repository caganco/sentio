"""FAZ-4 (c) DIAGNOSTIC: does the 3-part Mod-A agreement PASS triple-count one
piece of evidence?

The Section-4.1 PASS bar (``moda.conjugate_agreement``) requires ALL THREE of:
  cond1 = agreement_t_cross_median  (min over arms of the median residual rank-IC t)
  cond2 = sign_consistency          (cross-arm mean-IC sign agreement, frac of R)
  cond3 = pbo                       (real CSCV bucket-transfer; LOW is good)
All three consume the SAME resid_fwd + scores + splits, so they are *expected* to
correlate. The question this measurement answers is whether each condition still
carries INDEPENDENT information once the common cause -- the latent factor
strength -- is controlled (partial correlation). If the partials collapse to ~0,
the 3-way AND is effectively counting one piece of evidence three times.

This is a MEASUREMENT, not a gate: the asserts pin only that the sweep runs,
spans weak->strong, and reproduces deterministically. The measured matrices are
printed (run with -s) and transcribed into docs/research/RR-Y1-005-FAZ4-HARDENING.md,
where the verdict + any condition-independence PROPOSAL live -- explicitly NOT a
keep-bar change, explicitly deferred to the project.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine import config
from src.engine.contracts import DialConfig, Frequency, Panel, SplitMode, SplitSpec
from src.engine.moda import run_moda

_ALPHAS = (0.0, 0.0006, 0.0012, 0.0025, 0.0050)  # embedded factor loading: noise -> strong
_SEEDS = (0, 1, 2, 3, 4)
_R = 12  # name-splits per run (< the frozen 50 default: this is a diagnostic, keep it cheap)


class _VecSignal:
    """Parameter-free static scorer: the embedded factor loading, same per name each date."""

    construction_window = 1

    def __init__(self, vec: np.ndarray, names: list[str]) -> None:
        self.name = "sweep"
        self._s = pd.Series(np.asarray(vec, dtype=float), index=names)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        return self._s.reindex(names)


def _sweep_panel(
    alpha: float, seed: int, *, n_names: int = 120, n_dates: int = 180
) -> tuple[Panel, np.ndarray, list[str]]:
    """Faz-2 'factor' construction with a TUNABLE loading ``alpha`` (0 -> pure noise)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    names = [f"S{i:03d}" for i in range(n_names)]
    mkt_ret = rng.normal(0.0, 0.01, size=n_dates)
    market = pd.Series(100.0 * np.cumprod(1.0 + mkt_ret), index=dates)
    beta = rng.uniform(0.4, 1.6, size=n_names)
    idio = rng.normal(0.0, 0.02, size=(n_dates, n_names))
    f = rng.normal(0.0, 1.0, size=n_names)
    f -= f.mean()  # market-neutral loading by construction
    daily = beta[None, :] * mkt_ret[:, None] + alpha * f[None, :] + idio
    tr = pd.DataFrame(100.0 * np.cumprod(1.0 + daily, axis=0), index=dates, columns=names)
    value_tl = pd.DataFrame(
        np.tile(1e8 * (1.0 + np.arange(n_names) / n_names), (n_dates, 1)),
        index=dates, columns=names,
    )
    one = pd.Series(1.0, index=dates)
    panel = Panel(
        close=tr.copy(), tr_gross=tr, tr_net=tr, value_tl=value_tl,
        membership={}, market=market, tufe=one, tlref=one, frequency=Frequency.DAILY,
    )
    return panel, f, names


def _run_one(alpha: float, seed: int) -> dict[str, float]:
    panel, f, names = _sweep_panel(alpha, seed)
    spec = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY, seed=seed, R=_R)
    o = run_moda(panel, _VecSignal(f, names), spec, DialConfig())
    return {
        "alpha": alpha,
        "cond1_t_cross": float(o["agreement_t_cross_median"]),
        "cond2_sign": float(o["sign_consistency"]),
        "cond3_pbo": float(o["pbo"]),
    }


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def _partial(x: np.ndarray, y: np.ndarray, *controls: np.ndarray) -> float:
    """Partial correlation of x,y controlling for ``controls`` (residualize-then-correlate).

    Regress x and y on [1, controls...] by least squares; correlate the residuals.
    Standard partial-correlation definition, valid for one or many controls.
    """
    Z = np.column_stack([np.ones_like(x), *[np.asarray(c, float) for c in controls]])
    bx, *_ = np.linalg.lstsq(Z, x, rcond=None)
    by, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return _pearson(x - Z @ bx, y - Z @ by)


@pytest.fixture(scope="module")
def sweep():
    """Run the alpha x seed grid once. Temporarily shrink the residual-corr null
    (a save/restore on the module constant): that null feeds ONLY the residual_corr
    field, which this diagnostic ignores -- the three agreement metrics are computed
    upstream of it, so shrinking it changes runtime, never the measured numbers."""
    saved = config.RESIDUAL_NULL_RESAMPLES
    config.RESIDUAL_NULL_RESAMPLES = 8
    try:
        rows = [_run_one(a, s) for a in _ALPHAS for s in _SEEDS]
    finally:
        config.RESIDUAL_NULL_RESAMPLES = saved
    return rows


def _columns(rows: list[dict[str, float]]):
    alpha = np.array([r["alpha"] for r in rows])
    c1 = np.array([r["cond1_t_cross"] for r in rows])
    c2 = np.array([r["cond2_sign"] for r in rows])
    c3 = np.array([r["cond3_pbo"] for r in rows])
    finite = np.isfinite(c1) & np.isfinite(c2) & np.isfinite(c3) & np.isfinite(alpha)
    return alpha[finite], c1[finite], c2[finite], c3[finite]


def test_sweep_spans_weak_to_strong(sweep):
    # The measurement is only meaningful if the sweep actually varies factor strength:
    # cond1 (t) rises with alpha, cond3 (PBO) falls. Economically-grounded sanity, NOT
    # the double-count verdict.
    alpha, c1, c2, c3 = _columns(sweep)
    assert alpha.size >= 18  # most of the 25 runs are non-degenerate
    assert _pearson(c1, alpha) > 0.3
    assert _pearson(c3, alpha) < -0.3


def test_deterministic_reproduction():
    # Determinism anchor: a single (alpha, seed) re-run is byte-identical.
    a = _run_one(0.0012, 3)
    b = _run_one(0.0012, 3)
    assert a == b


def test_partial_correlation_matrix_is_well_formed(sweep, capsys):
    """Compute + PRINT the raw Pearson matrix and the two partial-correlation matrices
    (controlling for the third metric; controlling for latent alpha). Asserts the
    measurement is well-formed (finite, symmetric); the numbers go in the report."""
    alpha, c1, c2, c3 = _columns(sweep)
    labels = ("cond1_t_cross", "cond2_sign", "cond3_pbo")
    cols = (c1, c2, c3)

    pearson = {
        (labels[i], labels[j]): _pearson(cols[i], cols[j])
        for i in range(3) for j in range(i + 1, 3)
    }
    # partial controlling for the THIRD metric (the one not in the pair):
    # for pair (i, j) the leftover column index is 3 - i - j (0+1->2, 0+2->1, 1+2->0).
    partial_third = {
        (labels[i], labels[j]): _partial(cols[i], cols[j], cols[3 - i - j])
        for i in range(3) for j in range(i + 1, 3)
    }
    # partial controlling for the latent factor strength alpha (the common cause)
    partial_alpha = {
        (labels[i], labels[j]): _partial(cols[i], cols[j], alpha)
        for i in range(3) for j in range(i + 1, 3)
    }

    for d in (pearson, partial_third, partial_alpha):
        assert all(np.isfinite(v) and -1.0 <= v <= 1.0 for v in d.values())

    with capsys.disabled():
        print(f"\n[FAZ-4(c)] n_runs(finite)={alpha.size} of {len(_ALPHAS) * len(_SEEDS)}")
        print("  Pearson (raw):")
        for k, v in pearson.items():
            print(f"    {k[0]:>14} ~ {k[1]:<14} {v:+.3f}")
        print("  Partial | third metric controlled:")
        for k, v in partial_third.items():
            print(f"    {k[0]:>14} ~ {k[1]:<14} {v:+.3f}")
        print("  Partial | latent alpha controlled:")
        for k, v in partial_alpha.items():
            print(f"    {k[0]:>14} ~ {k[1]:<14} {v:+.3f}")
