"""lab-demo-goal L7: FEASIBILITY-FRONTIER ledger (SYNTHESIS, READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L7_feasibility.json (FROZEN before tabulating).

NO new edge, NO new data. Reads the FROZEN lab result JSONs (L1,L2,L3,L6), extracts each
deployable leg's gross/cost/net numbers, and classifies it against pre-declared gates:
  SIGNIFICANCE/SIGN gate -> gross right-signed AND |t|>=2 (else SIGNIFICANCE-or-SIGN-WALL)
  COST gate              -> net stays positive AND |t|>=2 after realized cost (else COST-WALL)
Surfaces the TWO-GATE structure (LIQUID: significance binds first; ALL/microcap: cost binds)
and emits a reusable forward go/no-go rule.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l7_feasibility_frontier.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "lab-demo-goal" / "results"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L7_feasibility.json"
OUT = RES / "l7_feasibility_frontier_results.json"

T_GATE = 2.0


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def _load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def classify(gross_mean, gross_t, net_mean, net_t, cost_frac) -> dict:
    """Apply the frozen two gates. cost_frac = realized round-trip as a return fraction."""
    sig = bool(gross_mean is not None and gross_mean > 0
               and gross_t is not None and abs(gross_t) >= T_GATE)
    cost = bool(sig and net_mean is not None and net_mean > 0
                and net_t is not None and abs(net_t) >= T_GATE)
    # would cost also bind if the (insignificant) gross were taken at face value?
    cost_would_bind = bool(gross_mean is not None and cost_frac is not None
                           and gross_mean <= cost_frac)
    if cost:
        label = "NO-WALL"
    elif sig and not cost:
        label = "COST-WALL"
    else:
        label = "BOTH" if cost_would_bind else "SIGNIFICANCE-or-SIGN-WALL"
    return {"sig_gate_pass": sig, "cost_gate_pass": cost,
            "cost_would_bind_at_face_value": cost_would_bind, "classification": label}


def row(candidate, variant, scope, leg, freq, gross_mean, gross_t,
        turnover, realized_cost_bps, breakeven_bps, net_mean, net_t, sign_stable):
    cost_frac = realized_cost_bps / 1e4 if realized_cost_bps is not None else None
    cl = classify(gross_mean, gross_t, net_mean, net_t, cost_frac)
    return {"candidate": candidate, "variant": variant, "scope": scope, "leg": leg,
            "rebalance_freq": freq, "gross_mean": gross_mean, "gross_t": gross_t,
            "turnover": turnover, "realized_cost_bps": realized_cost_bps,
            "breakeven_bps": breakeven_bps, "net_mean": net_mean, "net_t": net_t,
            "sign_stable": sign_stable, **cl}


def extract_l1(d: dict) -> list[dict]:
    rows = []
    for grp in ("BIST100-add", "BIST30-add"):  # long-deploy on inclusion
        for win in ("post_[+1,+5]", "post_[+1,+10]"):
            for scope in ("ALL", "LIQUID"):
                node = d["groups"][grp]["windows"][win][scope]
                dc, cost, reg = node["date_clustered"], node["cost"], node["regime"]
                rows.append(row("L1 index-rebalance", f"{grp} {win}", scope, "long-add",
                                "event(single round-trip)", dc["mean_of_date_means"],
                                dc.get("nw_t", dc.get("t")), None,
                                cost.get("median_round_trip_bps"), None,
                                cost.get("net_mean_after_cost"), cost.get("net_t"),
                                reg.get("sign_stable")))
    return rows


def extract_l2(d: dict) -> list[dict]:
    rows = []
    for spec in ("REV_1M", "REV_1W"):
        for scope in ("ALL", "LIQUID"):
            leg = d["specs"][spec]["scopes"][scope]["long_losers"]  # pre-registered contrarian deploy
            gf, nf = leg["rel_costfree"], leg["rel_net_after_cost"]
            rows.append(row("L2 short-reversal", spec, scope, "long-losers(contrarian)",
                            "monthly" if spec == "REV_1M" else "weekly",
                            gf["mean"], gf["nw_t"], leg["mean_turnover"],
                            leg["realized_cost_bps"], leg["breakeven_bps"],
                            nf["mean"], nf["nw_t"], gf["regime"].get("sign_stable")))
    return rows


def extract_l3(d: dict) -> list[dict]:
    rows = []
    for K in ("1", "3"):
        for scope in ("ALL", "LIQUID"):
            leg = d["by_K"][K][scope]["long_tercile"]  # long-edge deploy leg
            gf, nf = leg["rel_costfree"], leg["rel_net_after_cost"]
            rows.append(row("L3 PEAD", f"K={K}", scope, "long-top-SUE-tercile",
                            "monthly", gf["mean"], gf["nw_t"], leg["mean_turnover"],
                            leg["realized_cost_bps"], leg["breakeven_bps"],
                            nf["mean"], nf["nw_t"], gf["regime"].get("sign_stable")))
    return rows


def extract_l6(d: dict) -> list[dict]:
    rows = []
    rt = d["data"]["index_roundtrip_bps_conservative"]
    smap = {"PRIMARY_xu100": "LIQUID(XU100)", "SECONDARY_ew_full": "ALL(EW-full)"}
    for key, scope in smap.items():
        for win in ("post_tight", "post_wide"):
            w = d[key]["windows"][win]
            rows.append(row("L6 macro-event(CPI)", win, scope, "post-release-long",
                            "event(single round-trip)", w["mean_car"], w["clustered_t"],
                            None, rt, None, w.get("net_car_after_index_cost"),
                            w["clustered_t"], w["regime"]["sign_stable"]))
    return rows


def main():
    require_stage0()
    ledger = []
    ledger += extract_l1(_load("l1_index_rebalance_results.json"))
    ledger += extract_l2(_load("l2_short_reversal_results.json"))
    ledger += extract_l3(_load("l3_pead_results.json"))
    ledger += extract_l6(_load("l6_macro_event_results.json"))

    liquid = [r for r in ledger if r["scope"].startswith("LIQUID")]
    allsc = [r for r in ledger if r["scope"].startswith("ALL")]

    def tally(rows):
        out = {}
        for r in rows:
            out[r["classification"]] = out.get(r["classification"], 0) + 1
        return out

    n_nowall = sum(1 for r in ledger if r["classification"] == "NO-WALL")
    summary = {
        "n_rows": len(ledger), "n_deploy_candidates_NO_WALL": n_nowall,
        "LIQUID_gate_tally": tally(liquid), "ALL_gate_tally": tally(allsc),
        "two_gate_finding": (
            "On LIQUID names the BINDING gate is SIGNIFICANCE/SIGN: the gross (cost-free) edge "
            "is insignificant or wrong-signed BEFORE cost is applied. On the ALL/microcap universe "
            "the gross edge is larger but turnover-driven realized cost (~46-140bp) triggers the "
            "COST-WALL. No leg reaches NO-WALL. The apparent edge lives in microcap and does not "
            "survive the move to liquid names -- cost is the microcap killer, significance is the "
            "liquid killer."),
        "forward_go_no_go_rule": (
            "Test a NEW candidate fully only if a cheap pre-check plausibly clears BOTH gates on "
            "LIQUID names: (1) right-signed gross mean with enough INDEPENDENT observations for "
            "|t|>=2 (favour LOW-turnover / event-driven so n is not inflated by overlap), AND "
            "(2) turnover-implied breakeven below a realistic ~28-46bp liquid round-trip. If a "
            "candidate's only visible edge is in microcap, or its turnover-implied breakeven "
            "exceeds plausible gross, SKIP it -- it will hit one of the two walls."),
    }

    results = {"candidate": "L7 feasibility-frontier (synthesis over L1,L2,L3,L6)",
               "stage0": str(STAGE0.relative_to(ROOT)), "t_gate": T_GATE,
               "ledger": ledger, "summary": summary,
               "verdict": {"verdict": "DESCRIPTIVE-SYNTHESIS (two-gate frontier; reusable go/no-go rule)",
                           "deploy_candidates": n_nowall}}
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"rows={len(ledger)}  NO-WALL deploy-candidates={n_nowall}")
    print("LIQUID tally:", summary["LIQUID_gate_tally"])
    print("ALL    tally:", summary["ALL_gate_tally"])
    print(f"{'candidate':22s} {'variant':16s} {'scope':14s} {'grossbp':>8s} {'t':>6s} {'netbp':>8s} {'class'}")
    for r in ledger:
        gb = "" if r["gross_mean"] is None else f"{r['gross_mean']*1e4:7.1f}"
        tt = "" if r["gross_t"] is None else f"{r['gross_t']:6.2f}"
        nb = "" if r["net_mean"] is None else f"{r['net_mean']*1e4:7.1f}"
        print(f"{r['candidate']:22s} {r['variant'][:16]:16s} {r['scope']:14s} {gb:>8s} {tt:>6s} {nb:>8s} {r['classification']}")


if __name__ == "__main__":
    main()
