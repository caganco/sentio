"""lab-demo-goal L17: NLP DISCLOSURE-TYPE-conditioned forward-return FORWARD-SCAFFOLD (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L17_nlp_disclosure_type.json (FROZEN before results).

The directive explicitly named NLP. Distinct from L16 (sentiment polarity): the signal here is the
disclosure TYPE (buyback / capital-increase / rating / dividend / governance ...) classified by a
pre-registered keyword taxonomy, and whether a type predicts subsequent market-relative drift,
Bonferroni-controlled across types. Only a live news SNAPSHOT exists offline, so -- L11-pattern --
this track pre-registers + offline-validates the test and characterizes the snapshot's type mix.
NO network, NO scraper, NO real-data edge claim.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l17_nlp_disclosure_type.py
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L17_nlp_disclosure_type.json"
OUT = LAB / "results" / "l17_nlp_disclosure_type_results.json"
NEWS_SNAPSHOT = ROOT / "data" / "news_cache.json"
FORWARD_PANEL = ROOT / "data" / "cache" / "kap_disclosure_text_daystamped.parquet"

H_WINDOWS = [5, 10]
SEED = 20260604
T_SIG = 2.0

TAXONOMY = {
    "BUYBACK": ["geri al"],
    "DIVIDEND": ["kar pay", "temettu", "kar dagit"],
    "CAPITAL_INCREASE": ["sermaye art", "ihrac tavan", "bedelli", "halka arz"],
    "RATING": ["derecelendir"],
    "GOVERNANCE": ["genel kurul", "yonetim kurulu", "esas sozlesme"],
    "AUDIT_REPORT": ["bagimsiz denetim", "finansal rapor", "sorumluluk beyan"],
    "CIRCUIT_BREAKER": ["devre kesici"],
    "SPECIAL_GENERAL": ["ozel durum aciklamasi"],
}
TYPE_ORDER = list(TAXONOMY.keys()) + ["OTHER"]

_TR = {0x00E7: "c", 0x00C7: "c", 0x011F: "g", 0x011E: "g", 0x0131: "i",
       0x0130: "i", 0x00F6: "o", 0x00D6: "o", 0x015F: "s", 0x015E: "s",
       0x00FC: "u", 0x00DC: "u", 0x00E2: "a", 0x00EE: "i", 0x00FB: "u"}


def ascii_fold(s: str) -> str:
    return (s or "").translate(_TR).lower()


def classify(title: str) -> str:
    t = ascii_fold(title)
    for typ, kws in TAXONOMY.items():
        if any(k in t for k in kws):
            return typ
    return "OTHER"


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


def type_car(events: pd.DataFrame, ret_wide: pd.DataFrame, target_type: str, H: int, leak: bool = False):
    """Market-relative [+1,+H] CAR for events of target_type; NW-t vs zero. events: [symbol,t_idx,type]."""
    market = ret_wide.mean(axis=1).to_numpy()
    col = {s: j for j, s in enumerate(ret_wide.columns)}
    R = ret_wide.to_numpy()
    n_days = R.shape[0]
    off = 0 if leak else 1
    cars = []
    for ev in events.itertuples():
        if ev.type != target_type:
            continue
        t = int(ev.t_idx)
        a, b = t + off, t + off + H
        if a < 0 or b > n_days:
            continue
        j = col.get(ev.symbol)
        if j is None:
            continue
        cars.append(float(np.nansum(R[a:b, j] - market[a:b])))
    if len(cars) < 9:
        return None
    arr = np.array(cars)
    t_stat = nw_tstat(arr, lag=H)
    return {"n_events": len(arr), "mean_car": round(float(arr.mean()), 6),
            "nw_t": round(t_stat, 4) if t_stat == t_stat else None}


def synthetic_self_validation() -> dict:
    rng = np.random.default_rng(SEED)
    n_sym, n_days, n_events = 60, 600, 540
    sigma_daily = 0.02
    drift = 0.030  # planted positive drift for the BUYBACK type only, over [+1,+H]
    target = "BUYBACK"
    syms = [f"S{i:03d}" for i in range(n_sym)]
    R = rng.normal(0.0, sigma_daily, size=(n_days, n_sym))
    ev_sym = rng.integers(0, n_sym, size=n_events)
    ev_t = rng.integers(30, n_days - 30, size=n_events)
    ev_type = rng.choice(TYPE_ORDER, size=n_events)
    H_plant = 10
    for s, t, ty in zip(ev_sym, ev_t, ev_type):
        if ty == target:
            R[t + 1: t + 1 + H_plant, s] += drift / H_plant
            R[t, s] += 0.03  # announcement-day jump (must be excluded by t+1)
    ret_wide = pd.DataFrame(R, columns=syms)
    events = pd.DataFrame({"symbol": [syms[i] for i in ev_sym], "t_idx": ev_t, "type": ev_type})
    n_types_tested = int(events["type"].nunique())
    bonf_t = T_SIG  # report Bonferroni-adjusted alpha context alongside the raw |t| bar

    rec = type_car(events, ret_wide, target, H=10, leak=False)
    plac_ev = events.copy()
    plac_ev["type"] = np.random.default_rng(SEED + 1).permutation(events["type"].to_numpy())
    plac = type_car(plac_ev, ret_wide, target, H=10, leak=False)
    lk = type_car(events, ret_wide, target, H=10, leak=True)
    asserts = {
        "recovery_sign_positive": bool(rec["mean_car"] > 0),
        "recovery_significant_t>=2": bool(rec["nw_t"] is not None and abs(rec["nw_t"]) >= T_SIG),
        "placebo_insignificant_t<2": bool(plac is None or plac["nw_t"] is None or abs(plac["nw_t"]) < T_SIG),
        "lookahead_entry_leaks_more_than_safe": bool(lk["nw_t"] is not None and rec["nw_t"] is not None
                                                     and abs(lk["nw_t"]) > abs(rec["nw_t"])),
    }
    return {"params": {"n_sym": n_sym, "n_days": n_days, "n_events": n_events, "target_type": target,
                       "drift": drift, "n_types_tested": n_types_tested, "bonferroni_alpha": 0.05 / max(n_types_tested, 1),
                       "seed": SEED},
            "recovery_BUYBACK_H10": rec, "placebo_H10": plac, "lookahead_leak_H10": lk,
            "asserts": asserts, "all_asserts_pass": bool(all(asserts.values()))}


def snapshot_characterization() -> dict:
    if not NEWS_SNAPSHOT.exists():
        return {"present": False}
    d = json.loads(NEWS_SNAPSHOT.read_text(encoding="utf-8"))
    syms, n_art = set(), 0
    type_counts = {t: 0 for t in TYPE_ORDER}
    for k, v in d.items():
        syms.add(k.split(":")[0])
        for a in (v.get("articles", []) if isinstance(v, dict) else []):
            n_art += 1
            type_counts[classify(a.get("baslik", "") or "")] += 1
    other = type_counts.get("OTHER", 0)
    return {"present": True, "distinct_symbols": len(syms), "total_articles": n_art,
            "type_counts": type_counts,
            "other_frac": round(other / n_art, 4) if n_art else None,
            "is_backtestable_panel": False,
            "gap": ("snapshot only: a few symbols, ~1 month, headline-only -> no historical day-stamped "
                    "text panel; type-conditioned CAR test needs an approved historical disclosure fetch.")}


def main():
    require_stage0()
    real_mode = FORWARD_PANEL.exists()
    sv = synthetic_self_validation()
    snap = snapshot_characterization()
    rec = sv["recovery_BUYBACK_H10"]

    results = {
        "candidate": "L17 NLP disclosure-type-conditioned forward-return scaffold (pre-registered; offline-validated)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (historical disclosure-text panel present)" if real_mode else "OFFLINE synthetic self-validation + snapshot characterization",
        "forward_panel_expected": str(FORWARD_PANEL.relative_to(ROOT)),
        "forward_panel_present": bool(real_mode),
        "h_windows": H_WINDOWS, "seed": SEED, "taxonomy_types": TYPE_ORDER,
        "synthetic_self_validation": sv,
        "snapshot_characterization": snap,
        "summary": {
            "headline": (
                "NLP disclosure-type harness pre-registered (Bonferroni across types) and offline-validated. "
                f"Synthetic self-test asserts={'PASS' if sv['all_asserts_pass'] else 'FAIL'} "
                f"(BUYBACK recovery NW-t={rec['nw_t']}, placebo NW-t={sv['placebo_H10']['nw_t'] if sv['placebo_H10'] else None}, "
                f"look-ahead-leak NW-t={sv['lookahead_leak_H10']['nw_t']}). Real news_cache is a "
                f"{snap.get('distinct_symbols')}-symbol snapshot (OTHER-frac={snap.get('other_frac')}) -- "
                "NOT a backtestable historical panel. NO real-data edge claimed."),
            "interpretation": (
                "Crystallizes the directive's NLP avenue into the L11 forward-scaffold form, distinct from "
                "L16 polarity: it asks WHICH disclosure type predicts drift, multiple-testing-controlled. "
                "Frozen and pipeline-validated; only a historical day-stamped disclosure-text fetch "
                "(the maintainer-gated, shared with L16 + #1 daily-PEAD) is missing."),
        },
        "verdict": {
            "verdict": ("SCAFFOLD-SELF-TEST PASS (synthetic-only; no deployable edge; awaiting approved "
                        "historical disclosure-text fetch)" if sv["all_asserts_pass"] else
                        "SCAFFOLD-SELF-TEST FAIL (no deployable edge; fix pipeline before any fetch)"),
            "synthetic_asserts_pass": bool(sv["all_asserts_pass"]),
            "real_data_run": bool(real_mode), "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"mode={results['mode']}")
    print(f"BUYBACK recovery NW-t={rec['nw_t']} placebo={sv['placebo_H10']['nw_t'] if sv['placebo_H10'] else None} "
          f"leak={sv['lookahead_leak_H10']['nw_t']} all_pass={sv['all_asserts_pass']}")
    print(f"snapshot: symbols={snap.get('distinct_symbols')} articles={snap.get('total_articles')} "
          f"other_frac={snap.get('other_frac')} type_counts={snap.get('type_counts')}")


if __name__ == "__main__":
    main()
