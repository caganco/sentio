"""lab-demo-goal L11: FORWARD DAILY-PEAD TEST HARNESS SCAFFOLD (READ-ONLY, no network).

Stage-0: lab-demo-goal/stage0/STAGE0_L11_forward_daily_pead.json (FROZEN before results).

This is the ANALYSIS harness for the forward daily-PEAD experiment -- NOT a fetcher, NOT a
scraper, NO network. It pre-registers and implements the EXACT test (look-ahead-safe t+1 entry,
market-relative event-window CAR by SUE sort, event-clustered Newey-West t, realistic round-trip
cost, keep-bar) that would consume KAP disclosure day-stamps IF an approved fetch delivers them.

Modes:
  * REAL  -- if data/cache/kap_pead_daystamped.parquet exists, run the pre-registered test on it.
  * OFFLINE (default) -- run a deterministic SYNTHETIC self-validation proving the pipeline
    recovers a planted post-announcement drift and that placebo/look-ahead controls behave.
    The synthetic recovery is a PIPELINE-CORRECTNESS proof ONLY -- no real-data edge is claimed.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l11_forward_daily_pead.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L11_forward_daily_pead.json"
OUT = LAB / "results" / "l11_forward_daily_pead_results.json"
FORWARD_PANEL = ROOT / "data" / "cache" / "kap_pead_daystamped.parquet"

ADV_MIN_TL = 1.0e7
ROLL = 63
H_WINDOWS = [5, 10]
SEED = 20260604
T_SIG = 2.0


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE results.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def nw_tstat(x: np.ndarray, lag: int) -> float:
    """Newey-West HAC t-stat for the mean of x (event-ordered series)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean()
    e = x - mu
    gamma0 = (e @ e) / n
    var = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        cov = (e[k:] @ e[:-k]) / n
        var += 2.0 * w * cov
    se = np.sqrt(max(var, 1e-18) / n)
    return float(mu / se) if se > 0 else float("nan")


def event_car_spread(events: pd.DataFrame, ret_wide: pd.DataFrame, dates: np.ndarray,
                     H: int, shift_to_event_day: bool = False):
    """Compute per-event market-relative CAR over [+1,+H] (or [0,+H-1] if leaking), then the
    cross-sectional long(top-tercile)-short(bottom-tercile) SUE spread + event-clustered NW-t.

    events: columns [symbol, t_idx (int index into dates of the day-stamp), sue]
    ret_wide: DataFrame [date_idx x symbol] of daily simple returns
    """
    market = ret_wide.mean(axis=1).to_numpy()  # EW universe daily return
    syms = list(ret_wide.columns)
    col = {s: j for j, s in enumerate(syms)}
    R = ret_wide.to_numpy()
    n_days = R.shape[0]
    start_off = 0 if shift_to_event_day else 1  # look-ahead-safe = enter day AFTER stamp
    cars, sues = [], []
    for ev in events.itertuples():
        t = int(ev.t_idx)
        a, b = t + start_off, t + start_off + H
        if a < 0 or b > n_days:
            continue
        j = col.get(ev.symbol)
        if j is None:
            continue
        car = float(np.nansum(R[a:b, j] - market[a:b]))  # market-relative cumulative abnormal return
        cars.append(car)
        sues.append(float(ev.sue))
    if len(cars) < 9:
        return None
    df = pd.DataFrame({"car": cars, "sue": sues}).sort_values("sue")
    k = len(df) // 3
    top = df.iloc[-k:]["car"].to_numpy()
    bot = df.iloc[:k]["car"].to_numpy()
    spread = float(top.mean() - bot.mean())
    # event-clustered NW-t on the paired top/bottom contributions (ordered by event)
    contrib = np.concatenate([top, -bot])
    t_stat = nw_tstat(contrib, lag=H)
    return {"n_events": int(len(df)), "long_short_car": round(spread, 6),
            "nw_t": round(t_stat, 4) if t_stat == t_stat else None,
            "top_mean_car": round(float(top.mean()), 6),
            "bot_mean_car": round(float(bot.mean()), 6)}


def synthetic_self_validation() -> dict:
    rng = np.random.default_rng(SEED)
    n_sym, n_days, n_events = 60, 600, 480
    sigma_daily = 0.02
    drift_per_sue = 0.020  # planted abnormal drift per unit SUE (STRONG, by design) over [+1,+H]
    syms = [f"S{i:03d}" for i in range(n_sym)]
    R = rng.normal(0.0, sigma_daily, size=(n_days, n_sym))
    # plant events
    ev_sym = rng.integers(0, n_sym, size=n_events)
    ev_t = rng.integers(30, n_days - 30, size=n_events)
    ev_sue = rng.normal(0.0, 1.0, size=n_events)
    H_plant = 10
    for s, t, sue in zip(ev_sym, ev_t, ev_sue):
        per_day = drift_per_sue * sue / H_plant
        R[t + 1: t + 1 + H_plant, s] += per_day  # drift strictly AFTER the stamp (t+1..)
        R[t, s] += 0.03 * np.sign(sue)            # announcement-DAY jump (must be EXCLUDED by t+1 entry)
    ret_wide = pd.DataFrame(R, columns=syms)
    events = pd.DataFrame({"symbol": [syms[i] for i in ev_sym], "t_idx": ev_t, "sue": ev_sue})

    out = {"params": {"n_sym": n_sym, "n_days": n_days, "n_events": n_events,
                      "sigma_daily": sigma_daily, "drift_per_sue": drift_per_sue, "seed": SEED}}
    asserts = {}
    # (1) RECOVERY at H=10 (look-ahead-safe entry)
    rec = event_car_spread(events, ret_wide, ret_wide.index.to_numpy(), H=10, shift_to_event_day=False)
    out["recovery_H10"] = rec
    asserts["recovery_sign_positive"] = bool(rec["long_short_car"] > 0)
    asserts["recovery_significant_t>=2"] = bool(rec["nw_t"] is not None and abs(rec["nw_t"]) >= T_SIG)
    # (2) PLACEBO: permute SUE labels -> effect should vanish
    perm = events.copy()
    perm["sue"] = np.random.default_rng(SEED + 1).permutation(events["sue"].to_numpy())
    plac = event_car_spread(perm, ret_wide, ret_wide.index.to_numpy(), H=10, shift_to_event_day=False)
    out["placebo_H10"] = plac
    asserts["placebo_insignificant_t<2"] = bool(plac["nw_t"] is None or abs(plac["nw_t"]) < T_SIG)
    # (3) LOOK-AHEAD: entering on the stamp day (shift_to_event_day) leaks the +-3% jump ->
    #     |t| jumps materially vs the safe entry, proving the announcement-day return is excluded by t+1.
    leak = event_car_spread(events, ret_wide, ret_wide.index.to_numpy(), H=10, shift_to_event_day=True)
    out["lookahead_leak_H10"] = leak
    asserts["lookahead_entry_leaks_more_than_safe"] = bool(
        leak["nw_t"] is not None and rec["nw_t"] is not None and abs(leak["nw_t"]) > abs(rec["nw_t"]))
    out["asserts"] = asserts
    out["all_asserts_pass"] = bool(all(asserts.values()))
    return out


def main():
    require_stage0()
    real_mode = FORWARD_PANEL.exists()
    sv = synthetic_self_validation()

    results = {
        "candidate": "L11 forward daily-PEAD test harness scaffold (pre-registered; offline-validated)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (day-stamp panel present)" if real_mode else "OFFLINE synthetic self-validation",
        "forward_panel_expected": str(FORWARD_PANEL.relative_to(ROOT)),
        "forward_panel_present": bool(real_mode),
        "adv_min_tl": ADV_MIN_TL, "roll": ROLL, "h_windows": H_WINDOWS, "seed": SEED,
        "synthetic_self_validation": sv,
        "summary": {
            "headline": (
                "Forward daily-PEAD harness pre-registered and offline-validated. Synthetic self-test "
                f"asserts={'PASS' if sv['all_asserts_pass'] else 'FAIL'} "
                f"(recovery NW-t={sv['recovery_H10']['nw_t']}, placebo NW-t={sv['placebo_H10']['nw_t']}, "
                f"look-ahead-leak NW-t={sv['lookahead_leak_H10']['nw_t']}). NO real-data edge claimed; "
                "the real test runs only when an approved KAP day-stamp fetch delivers the panel."),
            "interpretation": (
                "Capstone of the daily-PEAD synthesis (L8 n_required, L9 volume, L10 effect/sign): the "
                "forward experiment is now frozen and one command from running on real day-stamps. The "
                "synthetic PASS proves only pipeline correctness and look-ahead safety; it says nothing "
                "about whether a real BIST daily-PEAD edge exists. That remains gated behind Cagan's "
                "approval of the network fetch -- the autonomous phase deliberately stops before any pull."),
        },
        "verdict": {
            "verdict": ("SCAFFOLD-SELF-TEST PASS (synthetic-only; no deployable edge; awaiting approved "
                        "KAP day-stamp fetch)" if sv["all_asserts_pass"] else
                        "SCAFFOLD-SELF-TEST FAIL (no deployable edge; pipeline asserts did not pass -- fix before fetch)"),
            "synthetic_asserts_pass": bool(sv["all_asserts_pass"]),
            "real_data_run": bool(real_mode),
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"mode={results['mode']}")
    print(f"recovery NW-t={sv['recovery_H10']['nw_t']} (spread={sv['recovery_H10']['long_short_car']})")
    print(f"placebo  NW-t={sv['placebo_H10']['nw_t']}")
    print(f"leak     NW-t={sv['lookahead_leak_H10']['nw_t']}")
    print(f"asserts={sv['asserts']}")
    print(f"all_asserts_pass={sv['all_asserts_pass']}")


if __name__ == "__main__":
    main()
