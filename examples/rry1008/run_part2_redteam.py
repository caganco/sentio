"""RR-Y1-008 PART 2 -- ADVERSARIAL RED-TEAM (validator-validation).

Deliberately manufacture a garden-of-forking-paths overfit and check the engine
CATCHES it. The recipe (the maintainer's "optimize on X_1, push into X_2"):

  (a) freeze a K=24 mom-variant family (lookback x sign x winsorize) BEFORE any
      measurement -- ``signals.mom_variant_family()``;
  (b) on a deterministic FIXED name-split half X_1, compute every variant's in-arm
      mean rank-IC vs the 21-day forward total return, and CHERRY-PICK the X_1-best;
  (c) FREEZE that winner and evaluate it on the DISJOINT half X_2 (single-split) --
      pre-registered expectation: the in-sample IC COLLAPSES (selection tax);
  (d) push the frozen winner through the full conjugate engine
      ``harness(..., SplitMode.PANEL, stage0_path=...)`` with Stage-0
      ``denenen_konfig_sayisi = K = 24`` so Mod-B's DSR is N=24-deflated.

PRE-REGISTERED three-layer expectation (the overfit must be CAUGHT):
  conjugate-agreement FAIL (agreement_pass == False) | bucket-PBO HIGH (>= 0.5) |
  DSR insignificant (deflated at N=24).

This is NOT edge-hunting (C10-SAFE). An X_2/engine PASS is NOT a discovered edge:
flag common-factor / insufficient-overfit / engine-bug and REPORT; the "edge varmis"
interpretation is FORBIDDEN. This red-team probes name-specific + search overfit
(conjugate + PBO + DSR's job); it does NOT probe regime-overfit (known limit, out of
scope).

Coupling note (moda.py:427): every variant's construction_window = 21 is BOTH the
engine construction_window AND the Mod-A IC forward-return horizon h; each variant's
own lookback/sign/winsorize lives inside scores(). NW lag=21 corrects overlapping
21-day forward-return autocorrelation.

Standalone research script (real data git-ignored -> NOT a CI pytest). ASCII-only.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from examples.rry1008.signals import MomVariantSignal, mom_variant_family
from src.engine.contracts import DialConfig, Frequency, SplitMode, SplitSpec
from src.engine.data_adapter import continuous_basket, forward_return, load_panel
from src.engine.harness import harness
from src.engine.stats import nw_tstat

IC_HORIZON_H = 21
NW_LAG = 21
SPLIT_SEED = 0  # deterministic X_1 / X_2 name-split half
_MIN_NAMES_PER_DATE = 20  # min finite (score, fwd) pairs to score a cross-section
# COVERAGE-PRECONDITION (KAPSAM-GUARD, frozen BEFORE re-measurement; see Part-1 + Stage-0).
# The full-2019 survivorship-honest liquid universe is too small for a default Mod-A
# arm-pair (~38 < 100), so the engine's conjugate leg degenerates to a breadth-guard
# FAIL. Restricting to the recent window where the 10M floor (KEPT) yields enough
# continuous names, with the arm floor at the engine's per-cross-section minimum,
# actually exercises Mod-A. Chosen by a COVERAGE sweep (orthogonal to the verdict).
# UNDERPOWERED by construction (small arms). The single-split layer (my own naive IC
# on 50/50 halves) needs no such breadth and is reported on the same window.
COVERAGE_WINDOW_START = "2024-01-02"
MIN_NAMES_PER_ARM = 30
_STAGE0_PATH = Path(__file__).resolve().parent / "stage0" / "part2_redteam_mom_variant.json"


def _split_names(names: list[str], seed: int) -> tuple[list[str], list[str]]:
    """Deterministic balanced 50/50 name-split into (X_1, X_2)."""
    rng = np.random.default_rng(seed)
    perm = list(rng.permutation(np.asarray(names)))
    half = len(perm) // 2
    return sorted(perm[:half]), sorted(perm[half:])


def _per_date_ic(scores: pd.DataFrame, fwd: pd.DataFrame, names: list[str]) -> np.ndarray:
    """Per-date cross-sectional Spearman rank-IC over ``names`` (raw, un-neutralized).

    This is the deliberately-naive red-teamer SEARCH metric -- the engine does the
    proper market-neutralized conjugate IC internally. NaN dates dropped by caller.
    """
    cols = [c for c in names if c in scores.columns and c in fwd.columns]
    s = scores[cols]
    f = fwd.reindex(index=s.index, columns=cols)
    out = np.full(len(s.index), np.nan, dtype=float)
    for i, dt in enumerate(s.index):
        x = s.loc[dt].to_numpy(dtype=float)
        y = f.loc[dt].to_numpy(dtype=float)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < _MIN_NAMES_PER_DATE:
            continue
        xr = rankdata(x[m])
        yr = rankdata(y[m])
        if xr.std() == 0.0 or yr.std() == 0.0:
            continue
        out[i] = float(np.corrcoef(xr, yr)[0, 1])
    return out


def _mean_ic(ic: np.ndarray) -> float:
    f = ic[np.isfinite(ic)]
    return float(f.mean()) if f.size else float("nan")


def main() -> int:
    print("RR-Y1-008 PART 2 -- ADVERSARIAL RED-TEAM (cherry-pick X_1-best -> X_2 + engine)")
    print(f"  IC horizon h = {IC_HORIZON_H}; NW lag = {NW_LAG}; split seed = {SPLIT_SEED}")
    print(f"  COVERAGE-PRECONDITION: window start={COVERAGE_WINDOW_START}, "
          f"min_names_per_arm={MIN_NAMES_PER_ARM}, ADV floor=10M (kept). UNDERPOWERED.")
    print("  loading real panel (data/clean_universe) ...")
    panel = load_panel(start=COVERAGE_WINDOW_START)
    d0, d1 = panel.dates[0], panel.dates[-1]
    print(f"  panel: {len(panel.dates)} dates x {len(panel.names)} names "
          f"[{d0.date()} .. {d1.date()}]")

    # continuously-present names -> deterministic balanced X_1 / X_2 halves.
    basket = continuous_basket(panel, d0, d1)
    x1, x2 = _split_names(basket, SPLIT_SEED)
    print(f"  continuous basket: {len(basket)} names -> X_1={len(x1)}, X_2={len(x2)}\n")

    fwd = forward_return(panel, IC_HORIZON_H)

    # (a)+(b) cherry-pick: each frozen variant's in-arm (X_1) mean rank-IC; pick best.
    family = mom_variant_family()
    print(f"  K-family (frozen, N={len(family)}): cherry-picking X_1-best by mean rank-IC ...")
    scored: list[tuple[str, float, MomVariantSignal]] = []
    for v in family:
        sc = v._compute(panel)
        ic1 = _per_date_ic(sc, fwd, x1)
        scored.append((v.name, _mean_ic(ic1), v))
    scored.sort(key=lambda t: (-t[1] if np.isfinite(t[1]) else np.inf))
    winner_name, winner_x1_ic, winner = scored[0]
    print(f"  X_1 leaderboard (top 5 of {len(scored)}):")
    for nm, ic, _ in scored[:5]:
        print(f"    {nm:<22} X_1 mean-IC = {ic:+.5f}")
    print(f"  --> CHERRY-PICKED WINNER (FROZEN): {winner_name}  X_1 mean-IC = {winner_x1_ic:+.5f}\n")

    # (c) single-split: evaluate the FROZEN winner on the disjoint X_2 half.
    win_scores = winner._compute(panel)
    ic2 = _per_date_ic(win_scores, fwd, x2)
    x2_mean_ic = _mean_ic(ic2)
    x2_t = nw_tstat(ic2[np.isfinite(ic2)], lag=NW_LAG)
    shrink = (winner_x1_ic - x2_mean_ic)
    print("[LAYER 1] single-split (cherry-pick X_1 -> frozen -> disjoint X_2):")
    print(f"  X_1 mean-IC = {winner_x1_ic:+.5f}  ->  X_2 mean-IC = {x2_mean_ic:+.5f}  "
          f"(selection tax = {shrink:+.5f})")
    print(f"  X_2 NW t-stat (lag={NW_LAG}) = {x2_t:+.3f}   "
          f"single-split FAIL (|t| < 2)? {abs(x2_t) < 2.0}\n")

    # (d) full conjugate engine on the frozen winner: Mod-A+B, N=24-deflated DSR.
    print("[LAYER 2+3] frozen winner through full engine harness (SplitMode.PANEL, N=24):")
    spec = SplitSpec(
        split_mode=SplitMode.PANEL,
        frequency=Frequency.DAILY,
        embargo_h=IC_HORIZON_H,
        min_names_per_arm=MIN_NAMES_PER_ARM,
    )
    dial = DialConfig(nw_lag=NW_LAG)
    out = harness(panel, winner, spec, dial, stage0_path=_STAGE0_PATH)

    agree_caught = out.agreement_pass is False
    pbo_caught = out.pbo is not None and out.pbo >= 0.5
    dsr_caught = out.dsr is not None and out.dsr < 0.95
    print(f"  agreement_pass = {out.agreement_pass!s:>5}   "
          f"(t_cross={out.agreement_t_cross_median}, sign={out.sign_consistency})")
    print(f"  pbo            = {out.pbo}   (>= 0.5 -> overfit caught? {pbo_caught})")
    print(f"  dsr            = {out.dsr}   (N={out.dsr_n_trials}; < 0.95 -> insignificant? {dsr_caught})")
    if out.guard_messages:
        for g in out.guard_messages:
            print(f"  guard: {g}")

    print("\n" + "=" * 78)
    print("THREE-LAYER VERDICT (overfit must be CAUGHT):")
    print(f"  layer-1 single-split X_2 FAIL : {abs(x2_t) < 2.0}")
    print(f"  layer-2 conjugate-agreement   : agreement_pass={out.agreement_pass} "
          f"(caught={agree_caught})")
    print(f"  layer-2 bucket-PBO high       : pbo={out.pbo} (caught={pbo_caught})")
    print(f"  layer-3 DSR insignificant     : dsr={out.dsr} (caught={dsr_caught})")
    print("=" * 78)

    caught = (abs(x2_t) < 2.0) and agree_caught and pbo_caught and dsr_caught
    if caught:
        print("\nOVERFIT CAUGHT on all layers: the validator rejected the deliberate "
              "garden-of-forking-paths construction. Machine works.")
    else:
        print("\nNOT fully caught on some layer. Per C10 this is NOT an edge -- flag "
              "common-factor / insufficient-overfit / engine-bug and REPORT. "
              "'Edge varmis' interpretation is FORBIDDEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
