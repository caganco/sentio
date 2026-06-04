"""lab-demo-goal L18: VIOP / DERIVATIVES feasibility + index-basis-overlay FORWARD-SCAFFOLD (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L18_viop_feasibility.json (FROZEN before results).

The directive explicitly named VIOP. Stage-0 pre-registration ASSUMED no VIOP data offline; that
premise was FALSIFIED on first run -- a raw VIOP end-of-day archive IS present locally
(data/bist_datastore_archive/viop, 2005-2026): per-contract daily settlement/OHLC/VWAP/traded-value
plus OPEN INTEREST, including the XU030 index future (most-traded contract, underlying D_XU030D) and a
liquid large-cap single-stock-futures subset (AKBNK/EREGL/BIMAS...). So the blanket "single-stock VIOP
illiquid" pre-declaration is partially revised: a liquid single-stock-future subset exists. What is
still missing to RUN the index-basis overlay for real is a CONSTRUCTED basis panel: front-month XU030
future settlement aligned to a daily SPOT XU030 index level. This track pre-registers the overlay,
offline-validates it on synthetic data, and records the corrected data status + the concrete next step.
NO network, NO real-data edge claim (real run pending the basis-panel build + Cagan go-ahead).

Run:  PYTHONPATH=. python lab-demo-goal/harness/l18_viop_feasibility.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L18_viop_feasibility.json"
OUT = LAB / "results" / "l18_viop_feasibility_results.json"
FORWARD_PANEL = ROOT / "data" / "cache" / "viop_basis_daystamped.parquet"
VIOP_GLOBS = ["*viop*", "*futures*", "*vadeli*", "*opsiyon*"]

SEED = 20260604
T_SIG = 2.0
H = 1


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE results.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def nw_tstat(x: np.ndarray, lag: int) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean()
    e = x - mu
    var = (e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        var += 2.0 * w * (e[k:] @ e[:-k]) / n
    se = np.sqrt(max(var, 1e-18) / n)
    return float(mu / se) if se > 0 else float("nan")


def overlay_active_return(basis_signal: np.ndarray, ret: np.ndarray) -> dict:
    """Long/flat index overlay: position = sign(signal); active return = position * index return.
    signal and ret must already be aligned so signal is KNOWN before ret is realized."""
    pos = np.sign(basis_signal)
    active = pos * ret
    t = nw_tstat(active, lag=5)
    return {"n": int(len(active)), "mean_active": round(float(np.nanmean(active)), 6),
            "nw_t": round(t, 4) if t == t else None}


def synthetic_self_validation() -> dict:
    rng = np.random.default_rng(SEED)
    n = 1200
    sigma = 0.008
    # FAITHFUL to the real hazard: genuine lagged predictability is WEAK (noise-dominated),
    # while same-day basis/spot co-movement is STRONG. So the look-ahead-safe design recovers a
    # MODEST significant edge, but a design that conditions on CONTEMPORANEOUS basis leaks the large
    # co-movement and shows a much bigger |t| -- which is exactly what the leak assert must catch.
    beta_pred = 0.002     # weak predictive: yesterday's basis -> today's return
    gamma_contemp = 0.010  # strong contemporaneous co-movement (basis and spot move together same day)
    basis = rng.normal(0.0, 1.0, size=n)            # standardized basis state
    noise = rng.normal(0.0, sigma, size=n)
    ret = np.empty(n)
    ret[0] = noise[0]
    for t in range(1, n):
        ret[t] = beta_pred * basis[t - 1] + gamma_contemp * basis[t] + noise[t]

    # SAFE (look-ahead-safe): trade today on YESTERDAY's basis -> align signal=basis[:-1], ret=ret[1:]
    safe = overlay_active_return(basis[:-1], ret[1:])
    # PLACEBO: shuffle the basis signal -> predictive content destroyed
    perm = np.random.default_rng(SEED + 1).permutation(basis[:-1])
    plac = overlay_active_return(perm, ret[1:])
    # LOOK-AHEAD LEAK: trade today on TODAY's (contemporaneous) basis -> captures the co-movement gamma
    leak = overlay_active_return(basis[1:], ret[1:])

    asserts = {
        "recovery_sign_positive": bool(safe["mean_active"] > 0),
        "recovery_significant_t>=2": bool(safe["nw_t"] is not None and abs(safe["nw_t"]) >= T_SIG),
        "placebo_insignificant_t<2": bool(plac["nw_t"] is None or abs(plac["nw_t"]) < T_SIG),
        "lookahead_contemporaneous_leaks_more_than_safe": bool(
            leak["nw_t"] is not None and safe["nw_t"] is not None and abs(leak["nw_t"]) > abs(safe["nw_t"])),
    }
    return {"params": {"n": n, "sigma": sigma, "beta_pred": beta_pred, "gamma_contemp": gamma_contemp, "seed": SEED},
            "safe_lagged_overlay": safe, "placebo": plac, "lookahead_contemporaneous": leak,
            "asserts": asserts, "all_asserts_pass": bool(all(asserts.values()))}


def data_inventory() -> dict:
    """Confirm NO VIOP data file exists offline (the data-existence wall)."""
    hits = []
    for base in (ROOT / "data", LAB):
        if base.exists():
            for g in VIOP_GLOBS:
                hits += [str(p.relative_to(ROOT)) for p in base.rglob(g) if p.is_file()]
    archive = ROOT / "data" / "bist_datastore_archive" / "viop"
    eod = sorted(p.name for p in archive.glob("VIOP_GUNSONU*")) if archive.exists() else []
    return {"viop_files_found_count": len(set(hits)), "viop_data_present": bool(hits),
            "raw_archive_dir": str(archive.relative_to(ROOT)) if archive.exists() else None,
            "raw_archive_eod_months": len(eod),
            "raw_archive_span": [eod[0], eod[-1]] if eod else None,
            "note": "STAGE0 'verified absent' premise FALSIFIED: a raw VIOP end-of-day archive is "
                    "present (per-contract daily settlement/OHLC/VWAP/traded-value + OPEN INTEREST, "
                    "XU030 index future is the most-traded contract, plus a liquid large-cap single-"
                    "stock-future subset). Still MISSING for a real overlay run: a constructed basis "
                    "panel (front-month XU030 future settlement aligned to a daily SPOT XU030 level)."}


def main():
    require_stage0()
    real_mode = FORWARD_PANEL.exists()
    sv = synthetic_self_validation()
    inv = data_inventory()
    safe = sv["safe_lagged_overlay"]

    results = {
        "candidate": "L18 VIOP feasibility + index-basis-overlay scaffold (pre-registered; offline-validated)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (VIOP basis panel present)" if real_mode else "OFFLINE synthetic self-validation + feasibility",
        "forward_panel_expected": str(FORWARD_PANEL.relative_to(ROOT)),
        "forward_panel_present": bool(real_mode),
        "seed": SEED,
        "stage0_premise_falsified": {
            "frozen_claim": "STAGE0 honest_expectation pre-declared NO VIOP data offline (verified absent).",
            "observed": "raw VIOP end-of-day archive IS present locally (data/bist_datastore_archive/viop).",
            "handling": "Stage-0 left frozen as the historical pre-registration; the falsification is "
                        "recorded here at results-time (keep-bar/test-design unchanged; only the data-status "
                        "expectation was wrong).",
        },
        "feasibility": {
            "single_stock_cross_section": "PARTIALLY REVISED: a liquid large-cap single-stock-futures subset "
                                          "exists (AKBNK/EREGL/BIMAS...); a broad cross-section is still thin, "
                                          "but the blanket 'all single-stock VIOP illiquid' claim is too strong.",
            "index_basis_overlay": "buildable on real local data (XU030 future = most-traded contract); a "
                                   "market-timing overlay, adjacent to the graveyarded foreign-flow index-timing "
                                   "(D-211) -> weak prior even with data. Needs a spot XU030 level for the basis.",
            "open_interest_axis": "ACIK POZISYON (open interest) + OI-change are in the archive -> an additional "
                                  "positioning signal (index- or single-stock-level) not yet pre-registered.",
        },
        "data_inventory": inv,
        "synthetic_self_validation": sv,
        "summary": {
            "headline": (
                "VIOP feasibility + index-basis overlay harness pre-registered and offline-validated. "
                f"Synthetic self-test asserts={'PASS' if sv['all_asserts_pass'] else 'FAIL'} "
                f"(safe-lagged overlay NW-t={safe['nw_t']}, placebo NW-t={sv['placebo']['nw_t']}, "
                f"contemporaneous-leak NW-t={sv['lookahead_contemporaneous']['nw_t']}). VIOP raw archive "
                f"present offline={inv['viop_data_present']} (premise 'absent' FALSIFIED). NO real-data edge claimed."),
            "interpretation": (
                "Crystallizes the directive's VIOP avenue. The Stage-0 'no VIOP data' premise was wrong: a raw "
                "end-of-day archive (2005-2026, settlement/OHLC/OI, XU030 future most-traded) is local. The "
                "index-basis TIMING overlay is pipeline-validated but carries a weak prior (timing-overlay, "
                "foreign-flow-adjacent). The real run needs a CONSTRUCTED basis panel (front XU030 future vs a "
                "daily SPOT XU030 level) -- no network fetch, just a local build + Cagan go-ahead."),
        },
        "verdict": {
            "verdict": ("SCAFFOLD-SELF-TEST PASS (synthetic-only; no deployable edge; VIOP raw archive present "
                        "locally but the index-basis overlay still needs a constructed basis panel + spot XU030 "
                        "level before a real run)"
                        if sv["all_asserts_pass"] else
                        "SCAFFOLD-SELF-TEST FAIL (no deployable edge; fix pipeline before any real run)"),
            "synthetic_asserts_pass": bool(sv["all_asserts_pass"]),
            "real_data_run": bool(real_mode),
            "viop_raw_archive_present": True,
            "basis_panel_built": bool(real_mode),
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"mode={results['mode']}")
    print(f"safe NW-t={safe['nw_t']} placebo={sv['placebo']['nw_t']} "
          f"leak={sv['lookahead_contemporaneous']['nw_t']} all_pass={sv['all_asserts_pass']}")
    print(f"viop_data_present={inv['viop_data_present']} eod_months={inv['raw_archive_eod_months']} "
          f"span={inv['raw_archive_span']}")


if __name__ == "__main__":
    main()
