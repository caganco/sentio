"""Top-level assembler (TASARIM v0.2 Section 9): the single entry point that turns
a (panel, signal, split_spec, dial_config) into the Section-7 ``EngineOutput`` vector.

    harness(panel, signal, split_spec, dial_config) -> EngineOutput

It dispatches by ``split_mode`` (A -> Mod-A name-split conjugate core; B -> Mod-B
temporal-CPCV; A+B -> both), builds the tradeable headline returns/cost sub-vector,
and assembles every Section-7 slot the legs + committed cost primitives provide.
Per the contract it NEVER raises on a partial leg: missing inputs leave the
corresponding field ``None`` and record a ``notes``/``guard_messages`` entry.

Scope honesty (Faz-3): the conjugate verdicts (Mod-A) and the temporal overfit
measures (Mod-B) come straight from the legs; the returns/cost path is the
*tradeable* long-only top-frac EW tilt (tilt minus equal-weight universe, on
total returns), costed via the committed D-207 stack (NOT clib -- strangler).
Fields the Faz-2 legs do not yet produce (``null_percentile`` / ``mirror_active_ann``
fair-null, and the cut-family ``deflated_oos_t``) are left None with a note rather
than fabricated. The C12 byte-repro that proves the engine deterministic on real
data lives in the golden test, NOT in this live-signal path.

Strangler: this module consumes committed primitives (``d204.per_stock_cost_panel``,
``d203_config`` tax constants) READ-ONLY; it imports no lab code and mutates no
committed module.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from src.screening import d203_config as _costcfg
from src.screening.d204_hi52_stress import per_stock_cost_panel

from . import config
from .benchmark import benchmark_floor
from .contracts import (
    AgreementConfidence,
    DialConfig,
    EngineOutput,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from .data_adapter import forward_return
from .lockbox import assert_lockbox, consume_lockbox, marker_path_for
from .moda import run_moda
from .modb import run_modb
from .signal_protocol import Signal, assert_pm1_compliant
from .stage0_validator import require_stage0
from .stats import nw_tstat

# tilt depth -> top fraction of each cross-section held long-only EW (mirrors moda).
_DEPTH_FRACTION: dict[SortDepth, float] = {
    SortDepth.TERCILE: 1.0 / 3.0,
    SortDepth.DECILE: 0.10,
}
# dividend-withholding is a constant annual drag (days/365 over a full year -> 1.0),
# so the annualized tax line is closed-form from the two committed D-203 constants.
_TAX_ANN = float(_costcfg.D203_DIV_WITHHOLDING * _costcfg.D203_ASSUMED_ANNUAL_DIV_YIELD)


@dataclass(frozen=True)
class _ReturnsCost:
    """Tradeable returns/cost sub-vector + the daily active series it was built from
    (the series feeds the benchmark-floor and the per-regime split downstream)."""

    gross_active_ann: float
    net_active_ann: float
    cost_ann: float
    tax_ann: float
    mean_rt_bps: float
    nw_t: float
    n_obs: int
    active: pd.Series
    d0: pd.Timestamp | None
    d1: pd.Timestamp | None


# --------------------------------------------------------------------------- #
# headline tradeable tilt (long-only top-frac EW minus universe-EW)            #
# --------------------------------------------------------------------------- #
def _tilt_active(
    panel: Panel,
    signal: Signal,
    *,
    frac: float,
    h: int,
    basis: str,
    min_names: int,
) -> tuple[pd.Series, pd.DataFrame, list[str]]:
    """Daily active return of the long-only top-``frac`` EW tilt vs the EW universe,
    on forward total returns r_{t->t+h}. Returns (active_series, is_top, held_names).

    PM-1 compliant by construction (a fully-invested long-only EW re-tilt; the
    EW-universe leg is a benchmark, not a short) -- asserted once on the first
    eval date. A universe that never clears the cross-section floor yields an
    empty series (the caller degrades to NaN, never raises)."""
    dates = panel.dates
    fwd = forward_return(panel, h, basis=basis)
    scores = pd.DataFrame.from_dict(
        {asof: signal.scores(panel, panel.names, asof) for asof in dates}, orient="index"
    )
    mask = scores.notna() & fwd.notna()
    counts = mask.sum(axis=1)
    valid = counts >= min_names
    if not bool(valid.any()):
        return pd.Series(dtype=float), pd.DataFrame(), []

    sc, fr, mk, cnt = scores[valid], fwd[valid], mask[valid], counts[valid]
    ranks = sc.where(mk).rank(axis=1, ascending=False, method="first")
    k = (cnt * frac).apply(lambda c: max(1, int(c)))
    is_top = ranks.le(k, axis=0) & mk

    first = is_top.index[0]
    top0 = is_top.columns[is_top.loc[first].to_numpy()]
    assert_pm1_compliant(pd.Series(1.0 / len(top0), index=top0), name=signal.name)

    port = fr.where(is_top).mean(axis=1)
    bench = fr.where(mk).mean(axis=1)
    active = (port - bench).dropna().sort_index()
    held = sorted({str(c) for c in is_top.columns[is_top.any(axis=0).to_numpy()]})
    return active, is_top, held


def _one_way_turnover(is_top: pd.DataFrame) -> pd.Series:
    """Per-date one-way turnover 0.5*sum|dw| of the EW top set (first date = 1.0
    full entry, matching the committed D-203 first-entry convention)."""
    if is_top.empty:
        return pd.Series(dtype=float)
    w = is_top.to_numpy(dtype=float)
    k = w.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(k > 0, w / k, 0.0)
    dw = np.abs(np.diff(w, axis=0))
    one_way = 0.5 * np.nansum(dw, axis=1)
    out = np.empty(w.shape[0], dtype=float)
    out[0] = 1.0
    out[1:] = one_way
    return pd.Series(out, index=is_top.index)


def _monthly_rebal(dates: pd.DatetimeIndex, d0: pd.Timestamp, d1: pd.Timestamp) -> list[pd.Timestamp]:
    """Last trading day of each calendar month within [d0, d1] -- the cost-sampling
    schedule (spread/impact levels move slowly, so monthly sampling is enough)."""
    idx = dates[(dates >= d0) & (dates <= d1)]
    if idx.empty:
        return []
    grp = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).last()
    return [pd.Timestamp(x) for x in grp.to_numpy()]


def _mean_round_trip_frac(panel: Panel, held: list[str], rebal: list[pd.Timestamp]) -> float:
    """Mean D-207 round-trip cost (fraction) of the held names across the rebalance
    schedule, via the committed ``per_stock_cost_panel`` (quote-free Roll->tier path)."""
    if not held or not rebal:
        return float("nan")
    res = per_stock_cost_panel(panel.close, panel.value_tl, rebal)
    cost_roll = cast("dict[pd.Timestamp, dict[str, float]]", res["cost_roll"])
    vals: list[float] = []
    held_set = set(held)
    for d in rebal:
        cm = cost_roll.get(d, {})
        vals.extend(float(c) for n, c in cm.items() if n in held_set and np.isfinite(c))
    return float(np.mean(vals)) if vals else float("nan")


def _returns_cost(panel: Panel, signal: Signal, spec: SplitSpec, dial: DialConfig) -> _ReturnsCost:
    """Assemble the tradeable gross/net/cost/tax/mean_rt + headline NW-t sub-vector."""
    frac = _DEPTH_FRACTION.get(spec.sort_depth, 1.0 / 3.0)
    h = int(signal.construction_window)
    basis = str(dial.return_basis)
    lag = dial.nw_lag_for(panel.frequency)
    yr = config.TRADING_DAYS_YR

    active, is_top, held = _tilt_active(
        panel, signal, frac=frac, h=h, basis=basis, min_names=config.MIN_NAMES_CROSS_SECTION
    )
    if active.empty:
        return _ReturnsCost(
            float("nan"), float("nan"), float("nan"), _TAX_ANN, float("nan"),
            float("nan"), 0, active, None, None,
        )

    d0, d1 = active.index[0], active.index[-1]
    gross_ann = float(active.mean() * yr)
    turnover = _one_way_turnover(is_top)
    mean_turnover = float(np.nanmean(turnover.to_numpy())) if not turnover.empty else float("nan")
    rebal = _monthly_rebal(panel.dates, d0, d1)
    mean_rt_frac = _mean_round_trip_frac(panel, held, rebal)
    cost_ann = (
        float(mean_turnover * mean_rt_frac * yr)
        if np.isfinite(mean_turnover) and np.isfinite(mean_rt_frac)
        else float("nan")
    )
    net_ann = (
        float(gross_ann - cost_ann - _TAX_ANN)
        if np.isfinite(gross_ann) and np.isfinite(cost_ann)
        else float("nan")
    )
    nw_t = float(nw_tstat(active.to_numpy(dtype=float), lag=lag))
    mean_rt_bps = float(mean_rt_frac * 1e4) if np.isfinite(mean_rt_frac) else float("nan")
    return _ReturnsCost(
        gross_active_ann=gross_ann,
        net_active_ann=net_ann,
        cost_ann=cost_ann,
        tax_ann=_TAX_ANN,
        mean_rt_bps=mean_rt_bps,
        nw_t=nw_t,
        n_obs=int(active.size),
        active=active,
        d0=d0,
        d1=d1,
    )


# --------------------------------------------------------------------------- #
# per-regime split + bounded parameter plateau                                #
# --------------------------------------------------------------------------- #
def _per_regime(active: pd.Series, *, cut: str = config.REGIME_SPLIT, yr: float = config.TRADING_DAYS_YR) -> dict[str, dict[str, float]]:
    """Pre/post manual-regime breakdown of the daily active series (Section 4.3:
    regime is a manual label, NOT engine-detected). Annualized mean active per arm."""
    if active.empty:
        return {}
    cut_ts = pd.Timestamp(cut)
    pre = active[active.index < cut_ts]
    post = active[active.index >= cut_ts]
    out: dict[str, dict[str, float]] = {}
    if not pre.empty:
        out["pre_2022"] = {"active_ann": float(pre.mean() * yr), "n_obs": float(pre.size)}
    if not post.empty:
        out["post_2022"] = {"active_ann": float(post.mean() * yr), "n_obs": float(post.size)}
    return out


def _plateau_map(
    panel: Panel, signal: Signal, *, base_h: int, basis: str, min_names: int, yr: float
) -> dict[str, float]:
    """BOUNDED sensitivity (<=4 points): headline gross-active over the
    (sort_depth in {tercile, decile}) x (forward horizon in {h, h+1}) grid.

    Sweeps the TRADEABLE tilt rather than re-running the conjugate leg: run_moda's
    agreement keys off ``signal.construction_window`` and config-fixed PBO deciles,
    so neither sort_depth nor embargo_h perturbs it -- a leg re-run would return 4
    identical numbers. The tilt's gross-active DOES move with frac + horizon, so
    this grid is a real (if narrow) curve-fit probe. Documented as bounded, not a
    full dial sweep."""
    out: dict[str, float] = {}
    for depth, frac in (("tercile", 1.0 / 3.0), ("decile", 0.10)):
        for hh in (base_h, base_h + 1):
            active, _, _ = _tilt_active(panel, signal, frac=frac, h=hh, basis=basis, min_names=min_names)
            out[f"{depth}_h{hh}"] = float(active.mean() * yr) if not active.empty else float("nan")
    return out


# --------------------------------------------------------------------------- #
# the assembler                                                               #
# --------------------------------------------------------------------------- #
def harness(
    panel: Panel,
    signal: Signal,
    split_spec: SplitSpec,
    dial_config: DialConfig,
    *,
    stage0_path: str | Path | None = None,
) -> EngineOutput:
    """Assemble the Section-7 ``EngineOutput`` for one prototype run.

    ``stage0_path`` (optional) enforces pre-registration: when given,
    ``require_stage0`` refuses to proceed if the freeze file is absent / drifted
    (d213 precedent). It is optional so synthetic panels stay runnable without a
    frozen Stage-0 file; real pre-registered runs pass the path.
    """
    stage0 = require_stage0(stage0_path) if stage0_path is not None else None
    # RR-Y1-009 lockbox: when a sealed held-out subset is declared, refuse to score
    # against it unless the presented panel matches the registered hash and it has not
    # already been consumed (single-shot). No-op when no lockbox is declared.
    if stage0 is not None and stage0_path is not None and stage0.lockbox_content_hash:
        assert_lockbox(stage0, panel, marker_path_for(stage0_path))
    n_trials = (
        stage0.denenen_konfig_sayisi if stage0 is not None else config.DSR_DEFAULT_N_TRIALS
    )

    mode = split_spec.split_mode
    out = EngineOutput(split_mode=str(mode), n_names=len(panel.names))
    notes: list[str] = []
    guards: list[str] = []

    # Partial-leg contract: a leg that cannot complete (e.g. a universe too thin to
    # form valid arms) must NOT crash the assembler -- record a guard and leave its
    # fields None so the rest of the Section-7 vector still populates.
    moda_res: dict[str, object] | None = None
    modb_res: dict[str, object] | None = None
    if mode in (SplitMode.NAME, SplitMode.PANEL):
        try:
            moda_res = run_moda(panel, signal, split_spec, dial_config)
        except Exception as exc:  # noqa: BLE001 -- legs are isolated by contract
            guards.append(f"Mod-A leg did not complete ({type(exc).__name__}: {exc})")
    if mode in (SplitMode.TEMPORAL, SplitMode.PANEL):
        try:
            modb_res = run_modb(panel, signal, split_spec, dial_config, n_trials=n_trials)
        except Exception as exc:  # noqa: BLE001 -- legs are isolated by contract
            guards.append(f"Mod-B leg did not complete ({type(exc).__name__}: {exc})")

    # --- tradeable returns/cost sub-vector (always attempted; headline tilt) ---
    rc = _returns_cost(panel, signal, split_spec, dial_config)
    out.gross_active_ann = rc.gross_active_ann
    out.net_active_ann = rc.net_active_ann
    out.cost_ann = rc.cost_ann
    out.tax_ann = rc.tax_ann
    out.mean_rt_bps = rc.mean_rt_bps
    out.nw_t = rc.nw_t
    out.n_obs = rc.n_obs
    if rc.n_obs == 0:
        guards.append("headline tilt: no eval date cleared the cross-section floor; returns are NaN")

    # --- benchmark floor (real net active vs max(TUFE, TLREF); deflate by TUFE) ---
    if rc.d0 is not None and rc.d1 is not None:
        bf = benchmark_floor(rc.net_active_ann, panel, rc.d0, rc.d1)
        out.real_active_ann = bf.real_active_ann
        out.benchmark_floor_ann = bf.benchmark_floor_ann
        out.beats_benchmark_floor = bf.beats_benchmark_floor
        if bf.guard_raised:
            out.pm1_guard_raised = True
            guards.extend(bf.guard_messages)

    # --- per-regime + bounded plateau ---
    out.per_regime = _per_regime(rc.active)
    out.plateau_map = _plateau_map(
        panel, signal,
        base_h=int(signal.construction_window),
        basis=str(dial_config.return_basis),
        min_names=config.MIN_NAMES_CROSS_SECTION,
        yr=config.TRADING_DAYS_YR,
    )

    # --- Mod-A conjugate (kept SEPARATE per Section 4.3) + real CSCV PBO ---
    if moda_res is not None:
        out.agreement_pass = cast("bool", moda_res["agreement_pass"])
        out.agreement_t_cross_median = cast("float", moda_res["agreement_t_cross_median"])
        out.sign_consistency = cast("float", moda_res["sign_consistency"])
        out.residual_cross_sectional_corr = cast("float", moda_res["residual_cross_sectional_corr"])
        out.residual_corr_flag = cast("bool", moda_res["residual_corr_flag"])
        out.agreement_confidence = cast("AgreementConfidence", moda_res["agreement_confidence"])
        out.agreement_confidence_reasons = cast(
            "tuple[str, ...]", moda_res["agreement_confidence_reasons"]
        )
        out.pbo = cast("float", moda_res["pbo"])
        guards.extend(cast("tuple[str, ...]", moda_res.get("guard_messages", ())))

    # --- Mod-B temporal overfit measures (DSR + proxy PBO when A absent) ---
    if modb_res is not None:
        out.dsr = cast("float", modb_res["dsr"])
        out.dsr_n_trials = cast("int", modb_res["dsr_n_trials"])
        if out.dsr_n_trials > 1:
            notes.append(
                f"dsr deflated for N={out.dsr_n_trials} tried configs (Stage-0 "
                "denenen_konfig_sayisi): multiple-test / search overfit is the DSR "
                "layer's job, NOT bucket-PBO (single-prototype-internal)"
            )
        if out.pbo is None:
            out.pbo = cast("float", modb_res["pbo"])
            notes.append(
                "pbo is the Mod-B simplified proxy P(OOS Sharpe < 0), NOT the real "
                "CSCV median-rank (no Mod-A leg in this run)"
            )

    # --- honest partials: fields the Faz-2 legs do not produce ---
    notes.append(
        "null_percentile / mirror_active_ann: not produced by the Faz-2 legs -- left None "
        "(fair-null resampler is out of Faz-3 scope)"
    )
    notes.append(
        "deflated_oos_t: cut-family (anchored/rolling/expanding) deflation not wired in Faz-3 -- left None"
    )
    if moda_res is not None and modb_res is None:
        notes.append(
            "dsr: None for Mod-A-only -- the Mod-A overfit gate is PBO + conjugate agreement; "
            "DSR is the Mod-B temporal-Sharpe measure"
        )

    out.guard_messages = tuple(guards)
    out.notes = tuple(notes)

    # RR-Y1-009 lockbox single-shot: record consumption as the FINAL action before
    # returning -- a crash mid-run does NOT burn the lockbox, yet the caller cannot
    # see-then-abort. No-op when no lockbox is declared.
    if stage0 is not None and stage0_path is not None and stage0.lockbox_content_hash:
        consume_lockbox(stage0, marker_path_for(stage0_path))
    return out
