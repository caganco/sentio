"""Multiple-testing harness (MTH) -- minimal core: a promotion GATE that asks
whether the best of a searched strategy universe beats the benchmark by more
than search-luck can explain.

Where the conjugate engine (Mod-A/B/C) interrogates a SINGLE prototype, this
module interrogates a UNIVERSE. Given K candidate strategies all searched on the
same development sample, the best in-sample performer is selected BECAUSE it was
best -- so its apparent edge is inflated by the search itself (data-snooping). The
harness corrects for that search and returns a three-way verdict. It is the guard
that protects the single-shot confirmation test (X2): it consumes NO X2 data,
opens no Stage-0, and computes no verdict on any real research candidate -- it is
validated only against synthetic fixtures (tests/test_engine_multiple_testing.py).

Performance is always measured as EXCESS RETURN over the benchmark (the BIST100
TOTAL-RETURN series -- dividend-reinvested, corporate-action adjusted, matched
gross/net to how the strategy returns are produced). A price-only index is an
unfairly-easy null and is never the benchmark. Returns fed in are assumed already
net of the costs the caller wishes to charge; the harness does not re-cost them.

Two complementary nulls are computed, and BOTH are reported (the F1 safeguard --
a single p-value is never emitted alone):

1. Reality Check / SPA (data-snooping correction across the universe). This WRAPS
   ``arch.bootstrap.SPA`` (Hansen 2005; White 2000 is the special case) -- the
   statistic is NOT hand-rolled. The benchmark-loss series is the zero baseline
   and each model loss is ``-excess`` (loss = negative excess return, arch's
   smaller-is-better convention), so the loss-differential SPA tests IS the excess
   series. Config is LOCKED: ``bootstrap='stationary'``, ``studentize=True``,
   ``reps`` and a fixed ``seed``; the stationary block length is computed ONCE via
   ``arch.bootstrap.optimal_block_length`` on the differential matrix (the mean of
   the per-strategy stationary optima, floored at 1). The reported RC p-value is
   the SPA ``consistent`` (SPA_c) bound; ``lower``/``upper`` are kept in the detail.

2. Matched permutation null (a non-stationarity-robust cross-check, implemented
   directly here -- shuffle -> recompute studentised max -> count):
   * CROSS-SECTIONAL strategies: at each time step a single asset-axis permutation
     is applied to every strategy's signal (which asset receives which signal
     value is randomised), holding each asset's own return series fixed. This
     destroys only the cross-sectional signal->return alignment.
   * TIMING strategies: a block sign-flip of the excess series (the same sign
     vector across all strategies, preserving cross-strategy dependence), holding
     the benchmark path fixed.
   The caller declares the strategy type; the harness selects the matched null.
   Both nulls studentise the per-strategy mean and take the max over the universe,
   so the data-snooping correction and the cross-strategy correlation are both
   honoured. The permutation path must pass the SAME size/power fixtures as the RC
   path (it is a verdict-giver, so calibration is a hard gate, not a nicety).

Agreement rule (the F1 verdict logic):
   * both p-values significant (<= locked alpha) AND economic size positive
     -> PROMOTE-CANDIDATE;
   * both non-significant -> REJECT (indistinguishable from luck);
   * they DISAGREE (one significant, one not), or both significant with a
     non-positive economic size -> FLAG-INCONCLUSIVE ("non-stationarity-sensitive /
     cannot tell"). A divergence is a valid output, not an error.

Universe-honesty (the F2 safeguard): the harness consumes a PRE-REGISTERED,
code-exhaustive strategy family. It is handed a frozen manifest -- the full grid
declared before any computation -- and ASSERTS the submitted universe equals it
(no add, no drop), raising ``MTHManifestError`` on mismatch. This makes honest
inclusion mechanical rather than a matter of trust. It is necessary-not-sufficient:
cross-family meta-search must be logged separately and X2 remains the backstop.

Boundary conditions (read before trusting an output):
   * timing strategies have low power on short BIST samples -- a non-rejection
     there is weak evidence, not a clean "no";
   * signals must be checked stationary / suitably transformed before testing --
     the nulls assume the differential series is well-behaved;
   * too few strategies make the max-distribution meaningless (a guard message is
     emitted below ``_MIN_STRATEGIES``);
   * RC / permutation divergence is reported as INCONCLUSIVE, never silently
     resolved;
   * the harness is a GUARD that will MOSTLY reject -- a rigorous NO is its normal,
     correct output, not a failure of the machinery.

Public surface (pure / deterministic given the fixed seed):
   ``run_mth(...)`` -> ``MTHReport``; ``decide_verdict(...)`` (the F1 rule);
   ``MTHConfig`` (locked defaults via ``LOCKED_MTH_CONFIG``); ``StrategyType``;
   ``CrossSectionalPanel``; ``MTHVerdict``; ``MTHManifestError``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
import numpy.typing as npt
import pandas as pd
from arch.bootstrap import SPA, optimal_block_length

# --- frozen structural constants (single source; not tunable per run) ------------ #
_MIN_STRATEGIES = 2  # below this the cross-universe max-distribution is meaningless
_TRADING_DAYS_YR = 252.0  # annualisation of the per-period economic size
_PERM_REP_CHUNK = 1000  # vectorised permutation batch (memory vs speed; result-invariant)


class StrategyType(StrEnum):
    """Declared by the caller; selects the matched permutation null."""

    CROSS_SECTIONAL = "cross_sectional"  # asset-axis signal permutation
    TIMING = "timing"  # block sign-flip of the excess series


class MTHVerdict(StrEnum):
    """The three-branch promotion-gate output (the F1 agreement rule)."""

    PROMOTE_CANDIDATE = "PROMOTE-CANDIDATE"
    REJECT = "REJECT"
    FLAG_INCONCLUSIVE = "FLAG-INCONCLUSIVE"


class MTHManifestError(ValueError):
    """Raised when the submitted universe != the frozen pre-registered manifest (F2)."""


@dataclass(frozen=True)
class MTHConfig:
    """Locked statistical configuration. ``alpha`` is a DECISION constant -- it is
    locked in spec and must not be varied per run. ``reps`` is a Monte-Carlo COMPUTE
    budget (not a decision knob): the locked production value is 10000; calibration
    fixtures may lower it purely for runtime, holding every decision constant fixed.
    """

    alpha: float = 0.05
    reps: int = 10000
    bootstrap: str = "stationary"
    studentize: bool = True
    seed: int = 20260613
    annualization: float = _TRADING_DAYS_YR

    def __post_init__(self) -> None:
        if not (0.0 < self.alpha < 0.5):
            raise ValueError(f"alpha must be in (0, 0.5) (got {self.alpha})")
        if self.reps < 1:
            raise ValueError(f"reps must be >= 1 (got {self.reps})")
        if self.bootstrap != "stationary":
            raise ValueError("bootstrap is LOCKED to 'stationary' (SPA wiring)")


LOCKED_MTH_CONFIG = MTHConfig()


@dataclass(frozen=True)
class CrossSectionalPanel:
    """Asset-level inputs the cross-sectional matched null needs (the strategy
    return matrix alone cannot express an asset-axis permutation).

    - ``signals``: one wide (T x N) signal panel per strategy id (index=date,
      columns=asset). Each strategy in the manifest IS one signal.
    - ``asset_excess_returns``: a single wide (T x N) panel of per-asset returns
      already in EXCESS of the benchmark. Each strategy's return is the lagged
      cross-sectional (unit-gross, dollar-neutral) signal weights dotted with these.
    """

    signals: Mapping[str, pd.DataFrame]
    asset_excess_returns: pd.DataFrame
    lag: int = 1  # weights at t use the signal at t-lag (look-ahead-safe; embargo >= 1)


@dataclass(frozen=True)
class MTHReport:
    """The F7 report object -- RC p-value, permutation p-value, verdict AND economic
    size are always emitted together. ``*_detail`` carry the audit trail."""

    rc_pvalue: float
    permutation_pvalue: float
    verdict: MTHVerdict
    economic_size: float  # best strategy's annualised after-cost excess-return magnitude
    economic_size_per_period: float  # the same, unannualised (per-period mean excess)
    best_strategy: str
    n_strategies: int
    n_obs: int
    strategy_type: StrategyType
    manifest_ok: bool
    config: MTHConfig
    rc_detail: dict[str, object] = field(default_factory=dict)
    permutation_detail: dict[str, object] = field(default_factory=dict)
    guard_messages: tuple[str, ...] = ()


# --- internals -------------------------------------------------------------------- #
def _studentized_mean(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Column-wise t-stat of the mean (H0: mean=0) for a (T, K) matrix.

    Returns 0.0 for a degenerate (non-positive-dispersion) column rather than inf,
    so a constant series cannot fake a winning max statistic.
    """
    n = x.shape[0]
    mean = x.mean(axis=0)
    sd = x.std(axis=0, ddof=1)
    se = sd / math.sqrt(n)
    out = np.zeros_like(mean)
    ok = se > 0.0
    out[ok] = mean[ok] / se[ok]
    return out


def _excess_cross_sectional(
    panel: CrossSectionalPanel, manifest: Sequence[str]
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], list[str]]:
    """Build (weights W [T' x N x K], asset excess R [T' x N], strategy ids) from a
    cross-sectional panel. Weights at row t come from the signal at t-lag (look-ahead
    safe), cross-sectionally demeaned and scaled to unit gross exposure (dollar
    neutral). The first ``lag`` rows are dropped (undefined weights)."""
    ids = list(manifest)
    r_df = panel.asset_excess_returns
    lag = int(panel.lag)
    if lag < 1:
        raise ValueError(f"CrossSectionalPanel.lag must be >= 1 (got {lag})")
    assets = list(r_df.columns)
    weights = []
    for sid in ids:
        sig = panel.signals[sid].reindex(index=r_df.index, columns=assets)
        s = sig.shift(lag).to_numpy(dtype=float)  # row t uses signal at t-lag
        s = np.nan_to_num(s, nan=0.0)
        s = s - s.mean(axis=1, keepdims=True)  # cross-sectional demean (dollar neutral)
        gross = np.abs(s).sum(axis=1, keepdims=True)
        gross[gross == 0.0] = 1.0
        weights.append(s / gross)  # unit gross
    w = np.stack(weights, axis=2)[lag:]  # (T', N, K)
    r = r_df.to_numpy(dtype=float)[lag:]  # (T', N)
    return w, np.nan_to_num(r, nan=0.0), ids


def _reality_check(excess: npt.NDArray[np.float64], cfg: MTHConfig) -> dict[str, object]:
    """Wrap arch SPA on the loss differentials. Benchmark loss = 0 baseline; model
    loss = -excess (smaller is better). The stationary block length is computed once
    on the differential matrix (mean of per-column stationary optima, floored at 1)."""
    losses = -excess  # (T, K) model losses
    benchmark_loss = np.zeros(excess.shape[0], dtype=float)  # zero baseline
    obl = optimal_block_length(excess)  # differential series = excess
    block_size = max(1, int(round(float(np.asarray(obl["stationary"]).mean()))))
    spa = SPA(
        benchmark_loss,
        losses,
        block_size=block_size,
        reps=cfg.reps,
        bootstrap=cfg.bootstrap,
        studentize=cfg.studentize,
        seed=cfg.seed,
    )
    spa.compute()
    pvals = spa.pvalues
    return {
        "pvalue": float(pvals["consistent"]),  # SPA_c -- the reported RC p-value
        "pvalue_lower": float(pvals["lower"]),
        "pvalue_upper": float(pvals["upper"]),
        "block_size": block_size,
        "reps": cfg.reps,
        "convention": "loss=-excess; benchmark loss=0; reported=SPA consistent",
    }


def _perm_pvalue_timing(
    excess: npt.NDArray[np.float64], block_size: int, cfg: MTHConfig
) -> dict[str, object]:
    """Block sign-flip null. One sign vector per rep is shared across all strategies
    (preserves cross-strategy dependence); within-block autocorrelation is preserved
    by flipping whole blocks. Statistic = max_k studentised mean of the excess."""
    n, k = excess.shape
    stat_obs = float(_studentized_mean(excess).max())
    n_blocks = max(1, math.ceil(n / block_size))
    rng = np.random.default_rng(cfg.seed)
    ge = 0
    done = 0
    while done < cfg.reps:
        batch = min(_PERM_REP_CHUNK, cfg.reps - done)
        block_signs = rng.choice(np.array([-1.0, 1.0]), size=(batch, n_blocks))
        signs = np.repeat(block_signs, block_size, axis=1)[:, :n]  # (batch, n)
        perm = excess[None, :, :] * signs[:, :, None]  # (batch, n, k)
        mean = perm.mean(axis=1)  # (batch, k)
        sd = perm.std(axis=1, ddof=1)  # (batch, k)
        se = sd / math.sqrt(n)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(se > 0.0, mean / se, 0.0)
        ge += int((t.max(axis=1) >= stat_obs).sum())
        done += batch
    pvalue = (1 + ge) / (cfg.reps + 1)  # Monte-Carlo permutation p-value
    return {
        "pvalue": float(pvalue),
        "stat_obs": stat_obs,
        "block_size": block_size,
        "reps": cfg.reps,
        "scheme": "block-sign-flip (shared signs; studentised max)",
    }


def _perm_pvalue_cross_sectional(
    w: npt.NDArray[np.float64], r: npt.NDArray[np.float64], cfg: MTHConfig
) -> tuple[dict[str, object], npt.NDArray[np.float64]]:
    """Asset-axis signal permutation null. At each time step a single permutation of
    the asset axis is applied to every strategy's weight vector (which asset receives
    which signal value is randomised), holding the asset return series fixed. Returns
    the detail dict and the OBSERVED per-strategy excess (so the caller reuses it for
    economic size). Statistic = max_k studentised mean of the portfolio excess."""
    n, _, _ = w.shape  # (T, N, K)
    p_obs = np.einsum("tnk,tn->tk", w, r)  # (T, K) observed excess
    stat_obs = float(_studentized_mean(p_obs).max())
    rng = np.random.default_rng(cfg.seed)
    t_idx = np.arange(n)[:, None]
    ge = 0
    for _ in range(cfg.reps):
        perm_idx = np.argsort(rng.random((n, w.shape[1])), axis=1)  # per-row asset perm
        w_perm = w[t_idx, perm_idx, :]  # permute the asset axis of the signal weights
        p = np.einsum("tnk,tn->tk", w_perm, r)
        ge += int(_studentized_mean(p).max() >= stat_obs)
    pvalue = (1 + ge) / (cfg.reps + 1)
    detail = {
        "pvalue": float(pvalue),
        "stat_obs": stat_obs,
        "reps": cfg.reps,
        "scheme": "asset-axis signal permutation (shared per-step perm; studentised max)",
    }
    return detail, p_obs


def decide_verdict(
    rc_pvalue: float, permutation_pvalue: float, economic_size: float, alpha: float
) -> MTHVerdict:
    """The F1 agreement rule (public so the verdict table is directly testable):

    * both p-values significant (<= alpha) AND economic size positive -> PROMOTE;
    * both non-significant -> REJECT;
    * a disagreement (one significant, one not), or both significant with a
      non-positive economic size -> FLAG-INCONCLUSIVE (cannot tell, not an error).
    """
    rc_sig = rc_pvalue <= alpha
    perm_sig = permutation_pvalue <= alpha
    if rc_sig and perm_sig:
        return MTHVerdict.PROMOTE_CANDIDATE if economic_size > 0.0 else MTHVerdict.FLAG_INCONCLUSIVE
    if not rc_sig and not perm_sig:
        return MTHVerdict.REJECT
    return MTHVerdict.FLAG_INCONCLUSIVE  # disagreement -> non-stationarity-sensitive


def run_mth(
    *,
    benchmark_returns: pd.Series,
    strategy_type: StrategyType | str,
    frozen_manifest: Sequence[str],
    strategy_returns: pd.DataFrame | None = None,
    cross_sectional_panel: CrossSectionalPanel | None = None,
    config: MTHConfig = LOCKED_MTH_CONFIG,
) -> MTHReport:
    """Run the multiple-testing promotion gate over a pre-registered universe.

    Parameters
    ----------
    benchmark_returns : the BIST100 TOTAL-RETURN series (T,), matched gross/net to
        the strategy returns. A price-only index is forbidden (unfair-easy null).
    strategy_type : ``TIMING`` or ``CROSS_SECTIONAL`` -- selects the matched null.
    frozen_manifest : the full pre-registered, code-exhaustive set of strategy ids.
        The submitted universe MUST equal this set (F2), else ``MTHManifestError``.
    strategy_returns : (T x K) per-strategy returns. REQUIRED for ``TIMING``; for
        ``CROSS_SECTIONAL`` it is ignored and the returns are built from the panel.
    cross_sectional_panel : asset-level signals + per-asset excess returns. REQUIRED
        for ``CROSS_SECTIONAL`` (the asset-axis permutation cannot be expressed by a
        return matrix alone).
    config : locked statistical configuration (``LOCKED_MTH_CONFIG`` by default).

    Returns an :class:`MTHReport` (both p-values, verdict, economic size, audit).
    """
    stype = StrategyType(strategy_type)
    manifest = list(frozen_manifest)
    manifest_set = set(manifest)
    if len(manifest_set) != len(manifest):
        raise MTHManifestError("frozen_manifest contains duplicate strategy ids")

    guards: list[str] = []
    benchmark = benchmark_returns

    if stype is StrategyType.CROSS_SECTIONAL:
        if cross_sectional_panel is None:
            raise ValueError(
                "strategy_type=CROSS_SECTIONAL requires cross_sectional_panel "
                "(the asset-axis permutation needs signals + per-asset excess returns)"
            )
        submitted = set(cross_sectional_panel.signals)
        if submitted != manifest_set:
            raise MTHManifestError(
                f"submitted universe != frozen manifest (F2): "
                f"missing={sorted(manifest_set - submitted)}, "
                f"extra={sorted(submitted - manifest_set)}"
            )
        w, r, ids = _excess_cross_sectional(cross_sectional_panel, manifest)
        perm_detail, excess = _perm_pvalue_cross_sectional(w, r, config)
        n_obs = excess.shape[0]
    else:
        if strategy_returns is None:
            raise ValueError("strategy_type=TIMING requires strategy_returns (T x K)")
        submitted = set(map(str, strategy_returns.columns))
        if submitted != manifest_set:
            raise MTHManifestError(
                f"submitted universe != frozen manifest (F2): "
                f"missing={sorted(manifest_set - submitted)}, "
                f"extra={sorted(submitted - manifest_set)}"
            )
        sr = strategy_returns[manifest]  # canonical manifest order
        aligned = sr.sub(benchmark, axis=0).dropna(how="any")
        excess = aligned.to_numpy(dtype=float)  # (T, K) excess returns
        ids = manifest
        n_obs = excess.shape[0]

    n_strategies = excess.shape[1]
    if n_strategies < _MIN_STRATEGIES:
        guards.append(
            f"only {n_strategies} strategy in the universe (< {_MIN_STRATEGIES}); "
            "the cross-universe max-distribution is degenerate -- treat the verdict as void"
        )
    if stype is StrategyType.TIMING:
        guards.append(
            "timing strategy: power is low on short samples -- a non-rejection is weak "
            "evidence, not a clean negative"
        )

    # economic size: the strategy that drove the max statistic (studentised), and its
    # annualised mean excess. Sign of the economic size gates PROMOTE.
    t_per_strategy = _studentized_mean(excess)
    best_ix = int(np.argmax(t_per_strategy))
    best_strategy = ids[best_ix]
    econ_per_period = float(excess[:, best_ix].mean())
    economic_size = econ_per_period * config.annualization

    rc_detail = _reality_check(excess, config)
    rc_p = float(rc_detail["pvalue"])

    if stype is StrategyType.TIMING:
        perm_detail = _perm_pvalue_timing(excess, int(rc_detail["block_size"]), config)
    perm_p = float(perm_detail["pvalue"])

    verdict = decide_verdict(rc_p, perm_p, economic_size, config.alpha)

    return MTHReport(
        rc_pvalue=rc_p,
        permutation_pvalue=perm_p,
        verdict=verdict,
        economic_size=economic_size,
        economic_size_per_period=econ_per_period,
        best_strategy=best_strategy,
        n_strategies=n_strategies,
        n_obs=n_obs,
        strategy_type=stype,
        manifest_ok=True,
        config=config,
        rc_detail=rc_detail,
        permutation_detail=perm_detail,
        guard_messages=tuple(guards),
    )
