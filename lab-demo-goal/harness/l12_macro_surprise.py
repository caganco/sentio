"""lab-demo-goal L12: MACRO SURPRISE-CONDITIONING FORWARD-RANK RATIONALE (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L12_macro_surprise.json (FROZEN before tabulating).

NO new edge, NO new data acquisition, NO optimization, NO re-test. Reads the FROZEN L6
(unconditional CPI-event) + L8 (power) results and the REAL macro-event panel to quantify
FORWARD_DATA_SPEC #2 (surprise-conditioned macro): the effect-MULTIPLIER surprise-conditioning
would need for |t|=2 at the real CPI arrival rate over 3/5/10 yr, and whether the binding
constraint is MAGNITUDE or SIGN-COHERENCE. The conditional effect is unmeasurable offline
(data carries dates only, no consensus surprise) -- L12 bounds the REQUIREMENT, not the effect.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l12_macro_surprise.py
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L12_macro_surprise.json"
OUT = LAB / "results" / "l12_macro_surprise_results.json"
L6 = LAB / "results" / "l6_macro_event_results.json"
MACRO = ROOT / "data" / "snapshots" / "macro_event_dates.parquet"

T_SIG = 2.0
HORIZONS_YEARS = [3, 5, 10]


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def main():
    require_stage0()
    l6 = json.loads(L6.read_text(encoding="utf-8"))
    wins = l6["PRIMARY_xu100"]["windows"]

    m = pd.read_parquet(MACRO)
    cpi = m[m["event_type"] == "cpi_release"].copy()
    cpi["event_date"] = pd.to_datetime(cpi["event_date"])
    span_years = (cpi["event_date"].max() - cpi["event_date"].min()).days / 365.25
    n_cpi = int(len(cpi))
    rate = n_cpi / span_years if span_years > 0 else None

    def leg_analysis(name: str) -> dict:
        w = wins[name]
        t0 = float(w["clustered_t"])
        n0 = int(w["n_events"])
        sign_stable = bool(w["regime"]["sign_stable"])
        n_req_uncond = n0 * (T_SIG / abs(t0)) ** 2 if t0 != 0 else None
        years_to_uncond = ((n_req_uncond - n0) / rate) if (n_req_uncond and rate) else None
        by_h = []
        for H in HORIZONS_YEARS:
            n_h = rate * H
            t_uncond_h = abs(t0) * (n_h / n0) ** 0.5
            m_req = T_SIG / t_uncond_h if t_uncond_h > 0 else None
            by_h.append({
                "horizon_years": H, "n_at_rate": round(n_h, 1),
                "unconditional_t_at_horizon": round(t_uncond_h, 3),
                "required_surprise_multiplier_for_t2": round(m_req, 3) if m_req else None,
            })
        return {
            "window": w["window"], "mean_car": round(float(w["mean_car"]), 6),
            "clustered_t0": round(t0, 3), "n0": n0, "regime_sign_stable": sign_stable,
            "survives_bonferroni": bool(w.get("survives_bonf", False)),
            "n_required_for_t2_unconditional": round(n_req_uncond, 1) if n_req_uncond else None,
            "years_to_t2_unconditional_at_rate": round(years_to_uncond, 1) if years_to_uncond else None,
            "by_horizon": by_h,
        }

    post_tight = leg_analysis("post_tight")
    post_wide = leg_analysis("post_wide")

    # binding-constraint framing: strongest look-ahead-safe leg
    strongest = "post_tight" if abs(post_tight["clustered_t0"]) >= abs(post_wide["clustered_t0"]) else "post_wide"
    strong_leg = post_tight if strongest == "post_tight" else post_wide
    magnitude_near = (strong_leg["by_horizon"][-1]["required_surprise_multiplier_for_t2"] is not None
                      and strong_leg["by_horizon"][-1]["required_surprise_multiplier_for_t2"] <= 2.0)
    binding = ("SIGN-COHERENCE" if (magnitude_near and not strong_leg["regime_sign_stable"])
               else ("MAGNITUDE" if not magnitude_near else "MAGNITUDE+SIGN both modest"))

    results = {
        "candidate": "L12 macro surprise-conditioning forward-rank rationale",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "cpi_arrival": {"n_cpi_events": n_cpi, "span_years": round(span_years, 2),
                        "events_per_year": round(rate, 1) if rate else None},
        "legs": {"post_tight": post_tight, "post_wide": post_wide},
        "binding_constraint": {
            "strongest_lookaheadsafe_leg": strongest,
            "magnitude_reachable_with_modest_multiplier": bool(magnitude_near),
            "strongest_leg_sign_stable": bool(strong_leg["regime_sign_stable"]),
            "binding": binding,
            "note": ("Surprise-conditioning's plausible value is supplying directional coherence "
                     "(sign of surprise -> sign of response), which is exactly what the strongest "
                     "leg lacks when sign-unstable. The required magnitude-multiplier is modest, so "
                     "#2's bottleneck is SIGN, not power -- but both the conditional effect and its "
                     "sign-stability are UNMEASURABLE offline (no consensus-surprise data; CPI dates "
                     "are rule-proxy, not exact)."),
        },
        "ranking_vs_forward_1": (
            "#2 stays ranked BELOW #1 (daily-PEAD): #1 needs only a single fetch of an EXISTING "
            "schema and is fully built+validated (L8-L11); #2 needs consensus-surprise data that may "
            "require a licensed source, and its unconditional effect does not survive Bonferroni."),
        "summary": {
            "headline": (
                f"Real CPI arrival ~{round(rate,1) if rate else '?'}/yr. Strongest look-ahead-safe leg "
                f"({strongest}, t0={strong_leg['clustered_t0']}, sign_stable={strong_leg['regime_sign_stable']}) "
                f"needs only ~{strong_leg['by_horizon'][-1]['required_surprise_multiplier_for_t2']}x effect "
                f"(10yr) for |t|=2 -- magnitude is near-reachable. Binding constraint = {binding}; "
                "surprise-conditioning is the mechanism that could supply it, but is unmeasurable offline."),
            "interpretation": (
                "Upgrades FORWARD_DATA_SPEC #2 from asserted to quantified: the macro class is not "
                "power-hopeless on magnitude (a modest surprise-multiplier suffices), but its value "
                "hinges on SIGN-coherence that only consensus-surprise data can test. Confirms #2 "
                "ranked below the fully-built, single-fetch #1 (daily-PEAD)."),
        },
        "verdict": {
            "verdict": "FORWARD-RANK-RATIONALE-VIEW (no edge; quantified #2 bottleneck = sign-coherence, data-gated, below #1)",
            "binding_constraint": binding,
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"CPI arrival: n={n_cpi} span={span_years:.2f}yr rate={rate:.1f}/yr")
    for nm, leg in (("post_tight", post_tight), ("post_wide", post_wide)):
        print(f"{nm}: t0={leg['clustered_t0']} sign_stable={leg['regime_sign_stable']} "
              f"n_req(uncond)={leg['n_required_for_t2_unconditional']} "
              f"yrs={leg['years_to_t2_unconditional_at_rate']}")
        for h in leg["by_horizon"]:
            print(f"   H={h['horizon_years']}yr: uncond_t={h['unconditional_t_at_horizon']} "
                  f"M_req={h['required_surprise_multiplier_for_t2']}")
    print(f"binding constraint = {binding}")


if __name__ == "__main__":
    main()
