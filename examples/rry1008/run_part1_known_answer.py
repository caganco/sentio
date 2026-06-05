"""RR-Y1-008 PART 1 -- KNOWN-ANSWER robustness exam (validator-validation).

Drive the three KNOWN-DEAD graveyard factors (value_static, mom120, hi52) through
the RR-Y1-005 validation engine's Mod-A (``SplitMode.NAME``) on REAL BIST data and
check the engine reproduces the pre-registered VERDICT: conjugate-agreement FAIL
(``agreement_pass == False``) for every factor.

This is NOT edge-hunting (C10-SAFE). The methodology differs from the original
graveyard tests, so the raw numbers will not match exactly -- only the VERDICT must
hold. An unexpected PASS is NOT a discovered edge: per the directive's interpretation
rule, flag one of (i) engine-bug, (ii) conjugate measures something different,
(iii) within-regime common-factor, and REPORT it; do NOT reopen the grave.

Pre-registration is enforced: each factor's frozen Stage-0 JSON (``stage0/``) is
passed to ``harness(..., stage0_path=...)``; an absent/unfrozen file makes the engine
REFUSE to run (Stage0Error).

Coupling note (moda.py:427): ``construction_window = 21`` on every signal is BOTH the
engine-facing construction_window AND the Mod-A IC forward-return horizon h. NW lag=21
(DialConfig) corrects the overlapping 21-day forward-return autocorrelation. See the
Stage-0 JSONs and RR-Y1-008 report for the full coupling declaration.

Standalone research script (real data is git-ignored -> NOT a CI-collected pytest).
ASCII-only.
"""
from __future__ import annotations

from pathlib import Path

from examples.rry1008.signals import Hi52Signal, Mom120Signal, ValueStaticSignal
from src.engine.contracts import DialConfig, Frequency, SplitMode, SplitSpec
from src.engine.data_adapter import load_panel
from src.engine.harness import harness

IC_HORIZON_H = 21
NW_LAG = 21
# COVERAGE-PRECONDITION (KAPSAM-GUARD, frozen BEFORE the conjugate re-measurement):
# the survivorship-honest full-2019 universe leaves only ~38 liquid+continuous names
# (10M-TL ADV floor) -- below the >= 2*50 a default Mod-A arm-pair needs, so the
# conjugate machinery degenerates to a breadth-guard FAIL (NOT an IC measurement).
# To actually exercise conjugate agreement we restrict to the recent window where the
# 10M floor (KEPT, highest -- no liquidity relaxation) yields enough continuous names,
# and shrink the arm floor to the engine's own per-cross-section minimum. Chosen by a
# COVERAGE sweep (orthogonal to the verdict), declared in every Stage-0 JSON. The
# resulting small arms are UNDERPOWERED: this confirms "the machine runs + direction
# sanity-check", NOT a high-confidence verdict (that stays in the synthetic fixtures).
COVERAGE_WINDOW_START = "2024-01-02"  # 10M floor -> 75 eligible names (sweep)
MIN_NAMES_PER_ARM = 30  # = MIN_NAMES_CROSS_SECTION; arms ~37 (margin over the floor)
_STAGE0_DIR = Path(__file__).resolve().parent / "stage0"

# (label, signal-factory, stage0 filename, pre-registered expectation)
_RUNS = (
    ("value_static", ValueStaticSignal, "part1_value_static.json", "FAIL (SERAP, cost-free t~0.76)"),
    ("mom120", Mom120Signal, "part1_mom120.json", "FAIL (negative / reversal-dominant)"),
    ("hi52", Hi52Signal, "part1_hi52.json", "FAIL (KESIN-KAPANDI, gate2 t~1.17)"),
)


def _fmt(x: float | None) -> str:
    return "   None" if x is None else f"{x:+.4f}"


def main() -> int:
    print("RR-Y1-008 PART 1 -- KNOWN-ANSWER robustness (Mod-A, real BIST data)")
    print(f"  IC horizon h = {IC_HORIZON_H} (construction_window, dual-role); NW lag = {NW_LAG}")
    print(f"  COVERAGE-PRECONDITION: window start={COVERAGE_WINDOW_START}, "
          f"min_names_per_arm={MIN_NAMES_PER_ARM}, ADV floor=10M (kept). UNDERPOWERED.")
    print("  loading real panel (data/clean_universe) ...")
    panel = load_panel(start=COVERAGE_WINDOW_START)
    print(f"  panel: {len(panel.dates)} dates x {len(panel.names)} names "
          f"[{panel.dates[0].date()} .. {panel.dates[-1].date()}]\n")

    spec = SplitSpec(
        split_mode=SplitMode.NAME,
        frequency=Frequency.DAILY,
        embargo_h=IC_HORIZON_H,
        min_names_per_arm=MIN_NAMES_PER_ARM,
    )
    dial = DialConfig(nw_lag=NW_LAG)

    rows: list[dict[str, object]] = []
    for label, factory, stage0_name, expectation in _RUNS:
        stage0_path = _STAGE0_DIR / stage0_name
        print(f"[{label}] Stage-0={stage0_name}  expectation: {expectation}")
        signal = factory()
        out = harness(panel, signal, spec, dial, stage0_path=stage0_path)
        verdict_held = out.agreement_pass is False
        rows.append({
            "label": label,
            "agreement_pass": out.agreement_pass,
            "t_cross_median": out.agreement_t_cross_median,
            "sign_consistency": out.sign_consistency,
            "pbo": out.pbo,
            "verdict_held": verdict_held,
        })
        print(f"  -> agreement_pass={out.agreement_pass!s:>5}  "
              f"t_cross_median={_fmt(out.agreement_t_cross_median)}  "
              f"sign_consistency={_fmt(out.sign_consistency)}  pbo={_fmt(out.pbo)}")
        print(f"     verdict held (FAIL)? {verdict_held}")
        if out.guard_messages:
            for g in out.guard_messages:
                print(f"     guard: {g}")
        print()

    print("=" * 78)
    print(f"{'factor':<14}{'agree_pass':<12}{'t_cross':<11}{'sign_con':<11}{'pbo':<10}{'verdict_held'}")
    print("-" * 78)
    for r in rows:
        print(f"{r['label']:<14}{str(r['agreement_pass']):<12}"
              f"{_fmt(r['t_cross_median']):<11}{_fmt(r['sign_consistency']):<11}"
              f"{_fmt(r['pbo']):<10}{r['verdict_held']}")
    print("=" * 78)

    all_held = all(r["verdict_held"] for r in rows)
    if all_held:
        print("\nALL verdicts held: every graveyard factor FAILed conjugate agreement. "
              "Engine reproduces the known answer.")
    else:
        flagged = [r["label"] for r in rows if not r["verdict_held"]]
        print(f"\nUNEXPECTED PASS for: {flagged}. Per C10 interpretation rule this is NOT "
              "an edge -- flag (i) engine-bug / (ii) conjugate-different / (iii) within-regime "
              "common-factor and REPORT. Do NOT reopen the grave.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
