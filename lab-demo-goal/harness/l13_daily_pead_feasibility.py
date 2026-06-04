"""lab-demo-goal L13: DAILY-PEAD TWO-GATE FEASIBILITY BAR (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L13_daily_pead_feasibility.json (FROZEN before tabulating).

NO new edge, NO new data acquisition, NO optimization, NO re-test. Reads the FROZEN L8
(power band), L9 (empirical arrival rate), L10 (monthly liquid SUE effect + event sd) results
and the committed D-208 realistic-cost artifact, and folds the COST wall and the POWER wall
into ONE forward bar for the decisive daily-PEAD experiment: the MINIMUM gross announcement-
window CAR a daily-PEAD leg must deliver to clear BOTH gates (net |t|=2 after realistic
round-trip cost), by holding-window and horizon, decomposed into cost- vs power-component,
with the binding wall and the concentration requirement vs the measured monthly signal.

The daily-window effect is UNMEASURABLE offline; L13 bounds the REQUIREMENT (the bar), not
the effect, using only frozen measured inputs and the standard random-walk variance scaling.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l13_daily_pead_feasibility.py
"""
from __future__ import annotations
import json
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L13_daily_pead_feasibility.json"
OUT = LAB / "results" / "l13_daily_pead_feasibility_results.json"
L8 = LAB / "results" / "l8_power_results.json"
L9 = LAB / "results" / "l9_pead_volume_results.json"
L10 = LAB / "results" / "l10_pead_effect_results.json"
D208 = ROOT / "docs" / "yol1" / "d208_results.json"

T_SIG = 2.0
TD_PER_MONTH = 21
H_HOLD_DAYS = [5, 10]
HORIZONS_YEARS = [1, 3, 5, 8]


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    require_stage0()
    l9 = _load(L9)
    l10 = _load(L10)
    d208 = _load(D208)

    # --- frozen inputs (read programmatically; no hardcoded magic numbers) ---
    liq = l10["monthly_sue_effect_event_level"]["LIQUID"]
    sigma_month = float(l10["monthly_sue_effect_event_level"]["sd_event_liquid"])
    mu_ls_month = float(liq["effect_pos_minus_neg"])          # long-short half-split
    mu_long_month = float(liq["mean_pos"])                    # long-only high-SUE market-rel

    rate_cons = float(l9["reachability"]["bounded_daily_date_clusters_per_year"])
    rate_opt = float(l9["reachability"]["empirical_liquid_events_per_year"])

    c_rt = float(d208["cost"]["selected_picks_summary"]["mean_round_trip_roll"])  # liquid round-trip
    c_flat = float(d208["cost"]["realistic_cost_flat_bps_equiv"])

    legs = {
        "long_only_highSUE_mktrel": {"monthly_effect": mu_long_month, "round_trips": 1},
        "long_short_SUE_halfsplit": {"monthly_effect": mu_ls_month, "round_trips": 2},
    }
    rates = {"conservative_bounded": rate_cons, "optimistic_liquid": rate_opt}

    def bar_grid(monthly_effect: float, n_round_trips: int) -> dict:
        cost_comp = c_rt * n_round_trips
        cost_floor_vs_monthly = (monthly_effect / cost_comp) if cost_comp > 0 else None
        out = {
            "cost_component_floor": round(cost_comp, 6),
            "cost_floor_bps": round(cost_comp * 1e4, 1),
            "monthly_effect": round(monthly_effect, 6),
            "monthly_effect_bps": round(monthly_effect * 1e4, 1),
            "monthly_effect_over_cost_floor": round(cost_floor_vs_monthly, 3) if cost_floor_vs_monthly else None,
            "monthly_signal_covers_cost_floor": bool(monthly_effect > cost_comp),
            "by_window": {},
        }
        for hh in H_HOLD_DAYS:
            sigma_w = sigma_month * sqrt(hh / TD_PER_MONTH)
            per_rate = {}
            for rname, rate in rates.items():
                rows = []
                for hy in HORIZONS_YEARS:
                    n = rate * hy
                    power_comp = T_SIG * sigma_w / sqrt(n)
                    bar = cost_comp + power_comp
                    binding = "COST" if cost_comp >= power_comp else "POWER"
                    conc = (bar / monthly_effect) if monthly_effect > 0 else None
                    rows.append({
                        "horizon_years": hy,
                        "n_events": round(n, 1),
                        "power_component": round(power_comp, 6),
                        "power_component_bps": round(power_comp * 1e4, 1),
                        "two_gate_bar": round(bar, 6),
                        "two_gate_bar_bps": round(bar * 1e4, 1),
                        "binding_wall": binding,
                        "concentration_ratio_needed_vs_monthly": round(conc, 3) if conc else None,
                        "clearable_from_monthly_signal_if_fully_concentrated": bool(conc is not None and conc <= 1.0),
                    })
                per_rate[rname] = rows
            out["by_window"][f"hold_{hh}d"] = {
                "sigma_window": round(sigma_w, 6),
                "sigma_window_pct": round(sigma_w * 100, 2),
                "by_rate": per_rate,
            }
        return out

    leg_results = {name: bar_grid(meta["monthly_effect"], meta["round_trips"])
                   for name, meta in legs.items()}

    # binding-wall crossover (conservative rate, 5d hold) for the headline leg (long-short)
    head_leg = "long_short_SUE_halfsplit"
    head_rows = leg_results[head_leg]["by_window"]["hold_5d"]["by_rate"]["conservative_bounded"]
    crossover_year = None
    for r in head_rows:
        if r["binding_wall"] == "COST":
            crossover_year = r["horizon_years"]
            break

    # neither leg's monthly signal has margin? (key sobering test)
    both_margin_thin = all(not leg_results[n]["monthly_signal_covers_cost_floor"]
                           or leg_results[n]["monthly_effect_over_cost_floor"] < 1.5
                           for n in legs)

    results = {
        "candidate": "L13 daily-PEAD two-gate (cost + power) feasibility bar",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "inputs": {
            "sigma_month_liquid": round(sigma_month, 6),
            "monthly_long_only_highSUE_mktrel": round(mu_long_month, 6),
            "monthly_long_short_halfsplit": round(mu_ls_month, 6),
            "arrival_rate_conservative_per_yr": round(rate_cons, 1),
            "arrival_rate_optimistic_per_yr": round(rate_opt, 1),
            "liquid_round_trip_cost": round(c_rt, 6),
            "liquid_round_trip_cost_bps": round(c_rt * 1e4, 1),
            "realistic_cost_flat_bps_equiv": round(c_flat, 1),
        },
        "legs": leg_results,
        "binding_wall_crossover": {
            "headline_leg": head_leg,
            "rate": "conservative_bounded", "hold": "5d",
            "first_horizon_year_where_COST_binds": crossover_year,
            "note": ("At horizons shorter than the crossover the POWER wall binds (need a large "
                     "few-day drift fast); at/after it the fixed cost FLOOR binds (power-component "
                     "has shrunk below the round-trip cost). Beyond the crossover, more data cannot "
                     "help -- only a gross drift above the cost floor can."),
        },
        "cost_floor_summary": {
            "long_only_floor_bps": leg_results["long_only_highSUE_mktrel"]["cost_floor_bps"],
            "long_only_monthly_bps": leg_results["long_only_highSUE_mktrel"]["monthly_effect_bps"],
            "long_only_covers_floor": leg_results["long_only_highSUE_mktrel"]["monthly_signal_covers_cost_floor"],
            "long_short_floor_bps": leg_results["long_short_SUE_halfsplit"]["cost_floor_bps"],
            "long_short_monthly_bps": leg_results["long_short_SUE_halfsplit"]["monthly_effect_bps"],
            "long_short_covers_floor": leg_results["long_short_SUE_halfsplit"]["monthly_signal_covers_cost_floor"],
            "both_legs_margin_thin": bool(both_margin_thin),
        },
        "summary": {
            "headline": (
                f"Folding the D-208 cost wall (~{round(c_rt*1e4,1)}bp liquid round-trip) into the L8 "
                f"power wall gives a two-gate bar for daily-PEAD. Long-only high-SUE monthly market-"
                f"relative mean ({round(mu_long_month*1e4,1)}bp) is ~at a single round-trip "
                f"({round(c_rt*1e4,1)}bp); long-short half-split ({round(mu_ls_month*1e4,1)}bp) is "
                f"~at a double round-trip ({round(2*c_rt*1e4,1)}bp). So the measured MONTHLY signal "
                f"has little/no margin over the COST FLOOR, before any power requirement. Net-|t|=2 "
                f"viability therefore hinges entirely on whether announcement-window CONCENTRATION "
                f"lifts the few-day CAR materially above the monthly average -- UNMEASURABLE offline."),
            "interpretation": (
                "Upgrades the daily-PEAD case from significance-only (L8-L11) to a TWO-GATE bar: the "
                "decisive experiment must clear BOTH the realistic cost floor AND the power bar. The "
                "binding wall is POWER at short horizons and the fixed COST floor at long horizons. "
                "The measured monthly liquid SUE signal barely covers the cost floor, so daily-PEAD "
                "is NOT cost-comfortable; its viability rests on the (canonical-PEAD) hypothesis that "
                "post-announcement drift concentrates in the few-day window above the cost floor, with "
                "true window noise at/below sqrt-scaling. Both are exactly what the approved KAP day-"
                "stamp fetch would resolve. This TEMPERS but does not overturn the #1 ranking: still "
                "the only power-reachable class, but with a high net-deployable bar and a thin-margin "
                "prior, so a NULL fetch outcome is a real possibility. No edge is claimed."),
        },
        "verdict": {
            "verdict": ("DESCRIPTIVE-FEASIBILITY-VIEW (no edge; two-gate cost+power bar for daily-PEAD; "
                        "viability hinges on unmeasurable announcement-window concentration beating a "
                        "quantified cost floor; sharpens the FORWARD_DECISION_CARD go/no-go)"),
            "binding_wall_short_horizon": "POWER",
            "binding_wall_long_horizon": "COST-FLOOR",
            "monthly_signal_margin_over_cost_floor_thin": bool(both_margin_thin),
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"sigma_month={sigma_month:.4f} c_rt={c_rt*1e4:.1f}bp "
          f"rate(cons)={rate_cons:.1f}/yr rate(opt)={rate_opt:.1f}/yr")
    for name, meta in legs.items():
        lr = leg_results[name]
        print(f"\n[{name}] monthly={meta['monthly_effect']*1e4:.1f}bp "
              f"cost_floor={lr['cost_floor_bps']:.1f}bp covers_floor={lr['monthly_signal_covers_cost_floor']} "
              f"(monthly/floor={lr['monthly_effect_over_cost_floor']})")
        for hh in H_HOLD_DAYS:
            rows = lr["by_window"][f"hold_{hh}d"]["by_rate"]["conservative_bounded"]
            sw = lr["by_window"][f"hold_{hh}d"]["sigma_window_pct"]
            print(f"   hold={hh}d sigma_w={sw:.2f}%:")
            for r in rows:
                print(f"      H={r['horizon_years']}yr n={r['n_events']:.0f} "
                      f"bar={r['two_gate_bar_bps']:.1f}bp ({r['binding_wall']}) "
                      f"conc_needed={r['concentration_ratio_needed_vs_monthly']}x")
    print(f"\ncrossover (long-short,5d,cons): COST binds from H={crossover_year}yr")
    print(f"both legs margin thin = {both_margin_thin}")


if __name__ == "__main__":
    main()
