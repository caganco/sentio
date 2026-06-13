"""Golden hard-gate for the multiple-testing harness (src/engine/multiple_testing.py).

The harness is a verdict-giver, so its calibration is a HARD GATE (same status as the
C12 golden): a regression here fails the build. Coverage:

  * determinism anchor  -- fixed synthetic data + fixed seed reproduce byte-identical
    p-values and a version-stable economic size (the anti-silent-error anchor);
  * differential ref    -- the Reality-Check wrapper reproduces a direct arch SPA call
    exactly (confirms the wrapping does not alter the statistic);
  * SIZE (both nulls, both strategy types) -- pure-noise universes must reject at ~=alpha,
    NOT materially above (over-rejection = false-positive factory = FAIL);
  * POWER (both nulls, both strategy types) -- a planted edge must be detected;
  * the F1 verdict table, the F2 manifest assertion, input guards, and the F7
    "always emit both p-values + economic size" contract.

All randomness is seeded (numpy ``default_rng`` PCG64 streams + arch's seeded bootstrap),
so every rate below is deterministic on a fixed toolchain. The asserted bounds are wide
enough to survive RNG-stream/library drift while still catching a real calibration
regression; the measured values are quoted in each assertion message.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from arch.bootstrap import SPA

from src.engine.multiple_testing import (
    CrossSectionalPanel,
    MTHConfig,
    MTHManifestError,
    MTHVerdict,
    StrategyType,
    decide_verdict,
    run_mth,
)

# --- shared synthetic universe geometry (fixed) ---------------------------------- #
T, K, N = 250, 10, 30
IDX = pd.bdate_range("2022-01-03", periods=T)
MAN = [f"s{i}" for i in range(K)]
ASSETS = [f"a{j}" for j in range(N)]
ALPHA = 0.05

# Frozen determinism-anchor constants (data seed 424242). The economic size is pure
# data arithmetic (mean excess x 252), so it is independent of reps/library version --
# the byte-stable anchor. rc=0 is saturated (a large planted edge); the permutation
# p-value is asserted significant + reproducible (an MC count, not a cross-version const).
_ANCHOR_TIMING_ECON = 0.6737244338
_ANCHOR_XS_ECON = 1.9536615681


def _timing(seed: int, edge: float = 0.0) -> tuple[pd.Series, pd.DataFrame]:
    """A timing universe: strategy = benchmark + idiosyncratic noise (excess ~ zero
    mean under H0). ``edge`` adds a constant excess to s3 (the planted winner)."""
    rng = np.random.default_rng(seed)
    bench = pd.Series(rng.normal(0.0004, 0.012, T), index=IDX)
    sr = pd.DataFrame(bench.values[:, None] + rng.normal(0, 0.01, (T, K)), index=IDX, columns=MAN)
    if edge:
        sr["s3"] = sr["s3"] + edge
    return bench, sr


def _xs(seed: int, scale: float = 0.0) -> tuple[pd.Series, pd.DataFrame, dict[str, pd.DataFrame]]:
    """A cross-sectional universe: random signals over random per-asset excess (H0).
    ``scale`` mixes a look-ahead-safe predictor of next-period asset excess into s5
    (the planted winner): signal_{t} ~ scale * z(excess_{t+1}) + (1-scale) * noise, so
    the harness's lagged weights (signal_{t-1}) align with excess_t."""
    rng = np.random.default_rng(seed)
    bench = pd.Series(rng.normal(0.0004, 0.012, T), index=IDX)
    aer = pd.DataFrame(rng.normal(0, 0.02, (T, N)), index=IDX, columns=ASSETS)
    sigs = {sid: pd.DataFrame(rng.normal(0, 1, (T, N)), index=IDX, columns=ASSETS) for sid in MAN}
    if scale:
        fut = aer.shift(-1)
        futz = fut.sub(fut.mean(axis=1), axis=0).div(fut.std(axis=1).replace(0, 1), axis=0).fillna(0.0)
        noise = pd.DataFrame(rng.normal(0, 1, (T, N)), index=IDX, columns=ASSETS)
        sigs["s5"] = scale * futz + (1 - scale) * noise
    return bench, aer, sigs


# --- 1. determinism anchor (byte-stable / version-stable) ------------------------ #
def test_anchor_reproducible_and_economic_size_stable():
    """Same data + same seed -> byte-identical p-values; economic size matches the
    frozen constant; the planted winner is recovered. The anti-silent-error gate."""
    cfg = MTHConfig(reps=500, seed=20260613)

    bench, sr = _timing(424242, edge=0.002)
    a = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                strategy_returns=sr, config=cfg)
    b = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                strategy_returns=sr, config=cfg)
    assert a.rc_pvalue == b.rc_pvalue
    assert a.permutation_pvalue == b.permutation_pvalue  # MC count reproduces exactly
    assert a.best_strategy == "s3"
    assert a.economic_size == pytest.approx(_ANCHOR_TIMING_ECON, rel=1e-9), a.economic_size
    assert a.rc_pvalue < 1e-9 and a.permutation_pvalue <= 0.01  # saturated edge -> significant
    assert a.verdict is MTHVerdict.PROMOTE_CANDIDATE

    benx, aer, sigs = _xs(424242, scale=0.25)
    x1 = run_mth(benchmark_returns=benx, strategy_type="cross_sectional", frozen_manifest=MAN,
                 cross_sectional_panel=CrossSectionalPanel(sigs, aer), config=cfg)
    x2 = run_mth(benchmark_returns=benx, strategy_type="cross_sectional", frozen_manifest=MAN,
                 cross_sectional_panel=CrossSectionalPanel(sigs, aer), config=cfg)
    assert x1.rc_pvalue == x2.rc_pvalue
    assert x1.permutation_pvalue == x2.permutation_pvalue
    assert x1.best_strategy == "s5"
    assert x1.economic_size == pytest.approx(_ANCHOR_XS_ECON, rel=1e-9), x1.economic_size
    assert x1.verdict is MTHVerdict.PROMOTE_CANDIDATE


# --- 2. differential reference: wrapper reproduces arch SPA exactly --------------- #
def test_reality_check_wraps_arch_spa_exactly():
    """The RC wrapper must equal a direct arch SPA call with the harness's block size
    -- confirms the loss=-excess / zero-benchmark wiring does not alter the statistic."""
    cfg = MTHConfig(reps=500, seed=20260613)
    bench, sr = _timing(424242, edge=0.002)
    r = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                strategy_returns=sr, config=cfg)
    excess = sr[MAN].sub(bench, axis=0).to_numpy()
    spa = SPA(np.zeros(excess.shape[0]), -excess, block_size=int(r.rc_detail["block_size"]),
              reps=cfg.reps, bootstrap=cfg.bootstrap, studentize=cfg.studentize, seed=cfg.seed)
    spa.compute()
    assert r.rc_pvalue == float(spa.pvalues["consistent"])
    assert r.rc_detail["pvalue_lower"] == float(spa.pvalues["lower"])
    assert r.rc_detail["pvalue_upper"] == float(spa.pvalues["upper"])


# --- 3. SIZE: pure noise must not over-reject ------------------------------------ #
def test_size_timing_no_over_rejection():
    """Pure-noise timing universes reject at ~=alpha, not materially above (measured
    rc=0.06, perm=0.07 at M=100). Over-rejection = false-positive factory = FAIL."""
    rc = perm = 0
    M = 100
    for m in range(M):
        bench, sr = _timing(1000 + m)
        r = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                    strategy_returns=sr, config=MTHConfig(reps=99, seed=700 + m))
        rc += r.rc_pvalue <= ALPHA
        perm += r.permutation_pvalue <= ALPHA
    assert rc / M <= 0.15, f"RC over-rejects under H0: {rc / M:.3f}"
    assert perm / M <= 0.15, f"permutation over-rejects under H0: {perm / M:.3f}"


def test_size_cross_sectional_no_over_rejection():
    """Pure-noise cross-sectional universes reject at ~=alpha (measured rc=0.05,
    perm=0.05 at M=60). Over-rejection fails the build."""
    rc = perm = 0
    M = 60
    for m in range(M):
        bench, aer, sigs = _xs(2000 + m)
        r = run_mth(benchmark_returns=bench, strategy_type="cross_sectional", frozen_manifest=MAN,
                    cross_sectional_panel=CrossSectionalPanel(sigs, aer), config=MTHConfig(reps=79, seed=700 + m))
        rc += r.rc_pvalue <= ALPHA
        perm += r.permutation_pvalue <= ALPHA
    assert rc / M <= 0.15, f"RC over-rejects under H0: {rc / M:.3f}"
    assert perm / M <= 0.15, f"permutation over-rejects under H0: {perm / M:.3f}"


# --- 4. POWER: a planted edge must be detected ----------------------------------- #
def test_power_timing_detects_edge():
    """A planted timing edge promotes at a high rate (measured 0.95 at M=100)."""
    promote = 0
    M = 100
    for m in range(M):
        bench, sr = _timing(5000 + m, edge=0.0025)
        r = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                    strategy_returns=sr, config=MTHConfig(reps=99, seed=800 + m))
        promote += r.verdict is MTHVerdict.PROMOTE_CANDIDATE
    assert promote / M >= 0.6, f"timing power too low: {promote / M:.3f}"


def test_power_cross_sectional_detects_edge():
    """A planted cross-sectional edge promotes at a high rate (measured 1.0 at M=60)."""
    promote = 0
    M = 60
    for m in range(M):
        bench, aer, sigs = _xs(6000 + m, scale=0.25)
        r = run_mth(benchmark_returns=bench, strategy_type="cross_sectional", frozen_manifest=MAN,
                    cross_sectional_panel=CrossSectionalPanel(sigs, aer), config=MTHConfig(reps=79, seed=800 + m))
        promote += r.verdict is MTHVerdict.PROMOTE_CANDIDATE
    assert promote / M >= 0.8, f"cross-sectional power too low: {promote / M:.3f}"


# --- 5. the F1 verdict table ----------------------------------------------------- #
def test_verdict_rule_all_branches():
    a = ALPHA
    assert decide_verdict(0.01, 0.02, 0.5, a) is MTHVerdict.PROMOTE_CANDIDATE
    assert decide_verdict(a, a, 0.5, a) is MTHVerdict.PROMOTE_CANDIDATE  # boundary: <= alpha is sig
    assert decide_verdict(0.2, 0.3, 0.5, a) is MTHVerdict.REJECT
    assert decide_verdict(0.01, 0.3, 0.5, a) is MTHVerdict.FLAG_INCONCLUSIVE  # disagree
    assert decide_verdict(0.3, 0.01, 0.5, a) is MTHVerdict.FLAG_INCONCLUSIVE  # disagree
    assert decide_verdict(0.01, 0.02, -0.1, a) is MTHVerdict.FLAG_INCONCLUSIVE  # sig but size<=0


# --- 6. the F2 manifest assertion ------------------------------------------------ #
def test_manifest_mismatch_raises():
    bench, sr = _timing(1)
    with pytest.raises(MTHManifestError):  # manifest has an id not submitted
        run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN + ["sX"],
                strategy_returns=sr, config=MTHConfig(reps=20))
    with pytest.raises(MTHManifestError):  # submitted has an id not in manifest
        run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN[:-1],
                strategy_returns=sr, config=MTHConfig(reps=20))
    with pytest.raises(MTHManifestError):  # duplicate in manifest
        run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN + ["s0"],
                strategy_returns=sr, config=MTHConfig(reps=20))


def test_cross_sectional_manifest_mismatch_raises():
    bench, aer, sigs = _xs(1)
    sigs_missing = {k: v for k, v in sigs.items() if k != "s9"}
    with pytest.raises(MTHManifestError):
        run_mth(benchmark_returns=bench, strategy_type="cross_sectional", frozen_manifest=MAN,
                cross_sectional_panel=CrossSectionalPanel(sigs_missing, aer), config=MTHConfig(reps=20))


# --- 7. input guards ------------------------------------------------------------- #
def test_missing_inputs_raise():
    bench, sr = _timing(1)
    with pytest.raises(ValueError, match="requires strategy_returns"):
        run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                strategy_returns=None, config=MTHConfig(reps=20))
    with pytest.raises(ValueError, match="requires cross_sectional_panel"):
        run_mth(benchmark_returns=bench, strategy_type="cross_sectional", frozen_manifest=MAN,
                strategy_returns=sr, config=MTHConfig(reps=20))


def test_single_strategy_emits_degenerate_guard():
    """A one-strategy universe makes the max-distribution degenerate -> guard message."""
    bench, sr = _timing(1)
    one = ["s0"]
    r = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=one,
                strategy_returns=sr[one], config=MTHConfig(reps=50))
    assert any("only 1 strategy" in g for g in r.guard_messages)


# --- 8. the F7 reporting contract ------------------------------------------------ #
def test_report_always_emits_both_pvalues_and_economic_size():
    bench, sr = _timing(3)
    r = run_mth(benchmark_returns=bench, strategy_type="timing", frozen_manifest=MAN,
                strategy_returns=sr, config=MTHConfig(reps=50))
    assert isinstance(r.rc_pvalue, float)
    assert isinstance(r.permutation_pvalue, float)
    assert isinstance(r.economic_size, float)
    assert r.verdict in set(MTHVerdict)
    assert r.manifest_ok is True
    assert "pvalue_lower" in r.rc_detail and "pvalue_upper" in r.rc_detail
