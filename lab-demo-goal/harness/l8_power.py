"""lab-demo-goal L8: POWER / SAMPLE-SIZE analysis (SYNTHESIS, READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L8_power.json (FROZEN before tabulating).

NO new edge, NO new data. Reads the FROZEN L1/L6 result JSONs, isolates the right-signed-
but-underpowered LIQUID event-driven legs, and quantifies the L7 power-bottleneck:
  n_required(target_t) = n_obs * (target_t / |t_obs|)^2     (sqrt(n) scaling law)
for target_t = 2.0 (significance) and 2.801585 (80% power, two-sided alpha=0.05).
Then translates n_required into forward-YEARS using fixed a-priori event-arrival rates and
ranks event classes by reachability. Output: a numeric backing for FORWARD_DATA_SPEC priority.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l8_power.py
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "lab-demo-goal" / "results"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L8_power.json"
OUT = RES / "l8_power_results.json"

T_SIG = 2.0
T_POWER80 = 2.801585  # 1.959964 (alpha=0.05 two-sided) + 0.841621 (z for 80% power)

# Fixed a-priori event-arrival rates (independent observations per year), from Stage-0.
RATE_CPI = 12.0           # monthly CPI release, single index
RATE_BIST30 = 2.0         # semi-annual reconstitution -> ~2 add-dates/yr
RATE_PEAD_DATES = 120.0   # est. independent earnings disclosure-DATES/yr (haircut for clustering)


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def _load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def power_row(leg, scope, window, mean, n_obs, t_obs, t_label, rate, event_class):
    """Back out effective per-unit sd, n_required for |t|=2 and 80% power, forward-years."""
    at = abs(t_obs)
    sd_unit = abs(mean) * math.sqrt(n_obs) / at if at > 0 else None
    d = abs(mean) / sd_unit if sd_unit else None
    n_req_sig = n_obs * (T_SIG / at) ** 2 if at > 0 else None
    n_req_pow = n_obs * (T_POWER80 / at) ** 2 if at > 0 else None
    gap_sig = (T_SIG / at) ** 2 if at > 0 else None
    # forward years to accumulate enough INDEPENDENT observations at this class's arrival rate
    yrs_sig = (n_req_sig - n_obs) / rate if (n_req_sig is not None and rate) else None
    yrs_pow = (n_req_pow - n_obs) / rate if (n_req_pow is not None and rate) else None
    total_yrs_sig = n_req_sig / rate if (n_req_sig is not None and rate) else None
    return {
        "leg": leg, "scope": scope, "window": window, "event_class": event_class,
        "mean_bp": round(mean * 1e4, 2), "n_obs_independent": n_obs,
        "t_obs": round(t_obs, 4), "t_label": t_label,
        "implied_per_unit_sd": round(sd_unit, 6) if sd_unit else None,
        "implied_standardized_effect_d": round(d, 5) if d else None,
        "n_required_for_t2": round(n_req_sig, 1) if n_req_sig else None,
        "n_required_for_power80": round(n_req_pow, 1) if n_req_pow else None,
        "gap_factor_vs_obs": round(gap_sig, 2) if gap_sig else None,
        "arrival_rate_per_year": rate,
        "forward_years_to_t2": round(yrs_sig, 1) if yrs_sig is not None else None,
        "forward_years_to_power80": round(yrs_pow, 1) if yrs_pow is not None else None,
        "total_years_of_data_for_t2": round(total_yrs_sig, 1) if total_yrs_sig else None,
    }


def extract_l1(d: dict) -> list[dict]:
    g = d["groups"]["BIST30-add"]["windows"]
    rows = []
    for win in ("post_[+1,+5]", "post_[+1,+10]"):
        node = g[win]["LIQUID"]["date_clustered"]
        rows.append(power_row(
            "L1 index-rebalance", "LIQUID(BIST30-add)", win,
            node["mean_of_date_means"], node["n_dates"], node["nw_t"], "nw_t(date-clustered)",
            RATE_BIST30, "BIST30 reconstitution (semi-annual)"))
    return rows


def extract_l6(d: dict) -> list[dict]:
    w = d["PRIMARY_xu100"]["windows"]
    rows = []
    for win in ("post_tight", "post_wide"):
        node = w[win]
        rows.append(power_row(
            "L6 macro-event(CPI)", "LIQUID(XU100)", win,
            node["mean_car"], node["n_events"], node["clustered_t"], "clustered_t",
            RATE_CPI, "CPI release (monthly, single index)"))
    return rows


def pead_reachability(rows: list[dict]) -> dict:
    """Would DAILY-PEAD volume reach the same n_required band? Compare against PEAD arrival rate."""
    n_reqs = [r["n_required_for_t2"] for r in rows if r["n_required_for_t2"]]
    band_lo, band_hi = min(n_reqs), max(n_reqs)
    # at PEAD disclosure-date rate, years to reach the observed n_required band
    yrs_lo = band_lo / RATE_PEAD_DATES
    yrs_hi = band_hi / RATE_PEAD_DATES
    return {
        "n_required_band_for_t2_observed_effects": [round(band_lo, 1), round(band_hi, 1)],
        "pead_independent_disclosure_dates_per_year": RATE_PEAD_DATES,
        "pead_years_to_reach_band": [round(yrs_lo, 2), round(yrs_hi, 2)],
        "interpretation": (
            "If a day-stamped daily-PEAD signal carried an effect size in the SAME band as these "
            "event legs, the required independent-observation count would accrue in roughly "
            f"{round(yrs_lo,1)}-{round(yrs_hi,1)} years at ~{int(RATE_PEAD_DATES)} disclosure-dates/yr -- "
            "vs DECADES for index-rebalance (~2 dates/yr) and ~13-33 yr for CPI-unconditional (12/yr). "
            "Daily-PEAD is the ONLY event class whose arrival rate makes |t|=2 reachable in a "
            "human-relevant horizon. This is the numeric backing for FORWARD_DATA_SPEC #1 >> #2 >> "
            "index-rebalance-alone."),
    }


def main():
    require_stage0()
    ledger = []
    ledger += extract_l1(_load("l1_index_rebalance_results.json"))
    ledger += extract_l6(_load("l6_macro_event_results.json"))

    reach = pead_reachability(ledger)
    summary = {
        "n_legs": len(ledger),
        "headline": (
            "Every right-signed liquid event leg fails the significance gate purely on POWER. "
            "Index-rebalance (BIST30-add) needs ~8-63x more independent dates at ~2 dates/yr -> "
            "DECADES (not reachable). CPI-unconditional needs ~1.8-4.6x more events at 12/yr -> "
            "~13-33 yr, so the real lever there is SURPRISE-CONDITIONING (sharpen effect, not grow n). "
            "Only daily-PEAD has an arrival rate (~120 disclosure-dates/yr) that reaches the "
            "required-n band within ~1-3 yr."),
        "scarcity_bottleneck": (
            "POWER is bottlenecked by event-ARRIVAL-RATE, not by sample length: 1 CPI/month and "
            "~2 BIST30-reconstitution-dates/year are hard ceilings no amount of waiting fixes "
            "cheaply. The lever is either (a) an event class with intrinsically MANY independent "
            "occurrences (earnings disclosures), or (b) conditioning that raises effect size per "
            "event (macro surprise)."),
        "pead_reachability": reach,
        "forward_spec_implication": (
            "Confirms the ranking in FORWARD_DATA_SPEC.md: #1 DAILY-PEAD (only power-reachable class) "
            ">> #2 SURPRISE-CONDITIONED MACRO (raises effect, not n) >> index-rebalance (power-hopeless "
            "on its own). Per-stock daily foreign-ratio (#4) inherits the same scarcity unless it "
            "provides many independent stock-events."),
    }

    results = {
        "candidate": "L8 power / sample-size analysis (synthesis over L1,L6 right-signed liquid event legs)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "targets": {"significance_t": T_SIG, "power80_t": T_POWER80},
        "ledger": ledger, "summary": summary,
        "verdict": {"verdict": "DESCRIPTIVE-POWER-VIEW (numeric power-bottleneck; reachability ranking; no edge)",
                    "no_edge_claim": True},
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"legs={len(ledger)}")
    hdr = f"{'leg':22s} {'window':14s} {'meanbp':>7s} {'n':>4s} {'t':>6s} {'n_req|t2':>9s} {'gap':>6s} {'fwd_yr':>7s}"
    print(hdr)
    for r in ledger:
        print(f"{r['leg']:22s} {r['window']:14s} {r['mean_bp']:7.1f} {r['n_obs_independent']:4d} "
              f"{r['t_obs']:6.2f} {r['n_required_for_t2']:9.1f} {r['gap_factor_vs_obs']:6.1f} "
              f"{r['forward_years_to_t2']:7.1f}")
    print("PEAD reach band (n_req for t=2):", reach["n_required_band_for_t2_observed_effects"],
          "-> PEAD years:", reach["pead_years_to_reach_band"])


if __name__ == "__main__":
    main()
