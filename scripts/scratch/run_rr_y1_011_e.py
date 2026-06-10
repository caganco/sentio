"""
RR-Y1-011-E: XU030 periodic reconstitution IN events — abnormal return event study.
Stage-0 pre-registered at docs/yol1/STAGE0_INDEX_RECON_XU030_IN.json (frozen).
Run AFTER Stage-0 commit. Results written to docs/yol1/RESULTS_INDEX_RECON_XU030_IN.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Config — frozen, mirrors Stage-0
# ---------------------------------------------------------------------------
STAGE0_PATH = ROOT / "docs/yol1/STAGE0_INDEX_RECON_XU030_IN.json"
RESULTS_PATH = ROOT / "docs/yol1/RESULTS_INDEX_RECON_XU030_IN.json"

PANEL_FILE = ROOT / "data/snapshots/index_recon_events_2019_2025.parquet"
PRICES_FILE = ROOT / "data/clean_universe/adjusted_prices_2019_2026.parquet"
TUFE_FILE = ROOT / "data/snapshots/exposure_k3_d192_tufe.parquet"

HASH_PANEL = "d94b910003c7d11b"
HASH_PRICES = "ccabef3d6622841b"
HASH_TUFE = "28052c6f46d08446"

DIRECTION = "IN"
TIER = "XU030"
KEEP_NW_T = 2.0

# D-207 realistic_cost XU030-tier (large-cap; conservative — nearest Roll+Kyle tier)
HALF_SPREAD_BPS = 13.4  # large-cap EOD kote medyan (D-207 FIX-2/FIX-3)
KYLE_BPS_APPROX = 10.0  # large-cap impact per side estimate
COST_ONE_WAY_BPS = HALF_SPREAD_BPS + KYLE_BPS_APPROX  # ~23.4bp per side
ROUND_TRIP_BPS = 2 * COST_ONE_WAY_BPS  # ~46.8bp full round trip


# ---------------------------------------------------------------------------
# Guard: assert Stage-0 exists and is frozen
# ---------------------------------------------------------------------------
def _assert_stage0() -> None:
    if not STAGE0_PATH.exists():
        raise RuntimeError(f"Stage-0 not found: {STAGE0_PATH}. Commit it first.")
    s0 = json.loads(STAGE0_PATH.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results", False):
        raise RuntimeError("Stage-0 frozen_before_results != true. Freeze before running.")


# ---------------------------------------------------------------------------
# Guard: assert input file hashes
# ---------------------------------------------------------------------------
def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _assert_hashes() -> None:
    checks = [
        (PANEL_FILE, HASH_PANEL, "event_panel"),
        (PRICES_FILE, HASH_PRICES, "adjusted_prices"),
        (TUFE_FILE, HASH_TUFE, "tufe"),
    ]
    for fpath, expected, label in checks:
        got = _sha16(fpath)
        if got != expected:
            raise RuntimeError(
                f"Hash mismatch for {label}: expected {expected}, got {got}. "
                "Data file changed after Stage-0 commit."
            )


# ---------------------------------------------------------------------------
# NW-HAC t-statistic
# ---------------------------------------------------------------------------
def _nw_tstat(series: np.ndarray, lag: int) -> tuple[float, float, float]:
    """Return (mean, nw_se, nw_t) for a 1-D series using Newey-West HAC."""
    n = len(series)
    mu = float(np.mean(series))
    e = series - mu
    gamma0 = float(np.mean(e**2))
    nw_var = gamma0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1)
        gk = float(np.mean(e[k:] * e[:-k]))
        nw_var += 2 * w * gk
    nw_var = max(nw_var, 1e-12)
    se = math.sqrt(nw_var / n)
    t = mu / se if se > 0 else float("nan")
    return mu, se, t


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
def _load_prices() -> pd.DataFrame:
    df = pd.read_parquet(PRICES_FILE)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _load_panel() -> pd.DataFrame:
    df = pd.read_parquet(PANEL_FILE)
    df["ann_date"] = pd.to_datetime(df["ann_date"])
    df["eff_date"] = pd.to_datetime(df["eff_date"])
    return df


# ---------------------------------------------------------------------------
# Compute event CARs
# ---------------------------------------------------------------------------
def _compute_cars(events: pd.DataFrame, prices: pd.DataFrame, direction: str) -> list[dict]:
    """
    For each event, compute CAR = stock_return - EW_benchmark_return
    over the [ann_date, eff_date] window.
    Benchmark = EW daily return of bist30=1 members as of ann_date (PIT-frozen).
    """
    records = []
    price_wide = prices.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    bist30_wide = prices.pivot(index="date", columns="symbol", values="bist30").sort_index().fillna(0)

    for _, ev in events.iterrows():
        sym = ev["symbol"]
        ann = ev["ann_date"]
        eff = ev["eff_date"]

        # Entry date: first available trading day >= ann_date
        avail_dates = price_wide.index
        entry_dates = avail_dates[avail_dates >= ann]
        if len(entry_dates) == 0:
            records.append(_gap_record(ev, "no_price_after_ann"))
            continue
        entry = entry_dates[0]

        # Exit date: first available trading day >= eff_date
        exit_dates = avail_dates[avail_dates >= eff]
        if len(exit_dates) == 0:
            records.append(_gap_record(ev, "no_price_after_eff"))
            continue
        exit_date = exit_dates[0]

        if entry >= exit_date:
            records.append(_gap_record(ev, "entry_ge_exit"))
            continue

        # Stock price
        if sym not in price_wide.columns:
            records.append(_gap_record(ev, "symbol_not_in_prices"))
            continue
        p_entry = price_wide.loc[entry, sym]
        p_exit = price_wide.loc[exit_date, sym]
        if pd.isna(p_entry) or pd.isna(p_exit) or p_entry <= 0:
            records.append(_gap_record(ev, "price_nan_or_zero"))
            continue
        stock_ret = float(p_exit / p_entry - 1)

        # Benchmark: EW of bist30=1 members on ann_date (PIT-frozen)
        # Find the last trading day <= ann_date for membership snapshot
        snap_dates = avail_dates[avail_dates <= ann]
        if len(snap_dates) == 0:
            records.append(_gap_record(ev, "no_bist30_snap_before_ann"))
            continue
        snap_date = snap_dates[-1]
        bm_members = bist30_wide.columns[bist30_wide.loc[snap_date] == 1].tolist()
        # Remove the event stock (it's being ADDED, not yet a member — sanity check)
        bm_members = [m for m in bm_members if m != sym]
        if len(bm_members) == 0:
            records.append(_gap_record(ev, "empty_benchmark"))
            continue

        # Benchmark return: EW of available members over [entry, exit]
        bm_prices = price_wide.loc[[entry, exit_date], bm_members]
        bm_valid = bm_prices.dropna(axis=1)
        if len(bm_valid.columns) == 0:
            records.append(_gap_record(ev, "benchmark_all_nan"))
            continue
        bm_entry = bm_valid.iloc[0]
        bm_exit = bm_valid.iloc[1]
        bm_rets = (bm_exit / bm_entry - 1).dropna()
        bm_ret = float(bm_rets.mean())
        bm_n = len(bm_rets)

        # CAR (nominal relative — TUFE cancels in relative form)
        car = stock_ret - bm_ret
        # Cost: round-trip on entry+exit
        cost_rt = ROUND_TRIP_BPS / 10000.0
        car_net = car - cost_rt

        # Calendar days in window
        actual_days = (exit_date - entry).days

        records.append({
            "symbol": sym,
            "ann_date": str(ann.date()),
            "eff_date": str(eff.date()),
            "entry_date": str(entry.date()),
            "exit_date": str(exit_date.date()),
            "gap_days_spec": int(ev["gap_days"]),
            "actual_window_days": actual_days,
            "stock_ret": round(stock_ret, 6),
            "bm_ret": round(bm_ret, 6),
            "car_gross": round(car, 6),
            "cost_rt_bps": ROUND_TRIP_BPS,
            "car_net": round(car_net, 6),
            "bm_n_members": bm_n,
            "gap_flag": None,
            "direction": direction,
        })

    return records


def _gap_record(ev: pd.Series, reason: str) -> dict:
    return {
        "symbol": ev["symbol"],
        "ann_date": str(ev["ann_date"].date()),
        "eff_date": str(ev["eff_date"].date()),
        "entry_date": None,
        "exit_date": None,
        "gap_days_spec": int(ev["gap_days"]),
        "actual_window_days": None,
        "stock_ret": None,
        "bm_ret": None,
        "car_gross": None,
        "cost_rt_bps": ROUND_TRIP_BPS,
        "car_net": None,
        "bm_n_members": None,
        "gap_flag": reason,
        "direction": ev["direction"],
    }


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------
def _run_stats(cars_net: np.ndarray, cars_gross: np.ndarray, label: str) -> dict:
    n = len(cars_net)
    lag = max(1, math.ceil(n ** (1 / 3)))  # frozen NW lag
    mu_net, se_net, t_net = _nw_tstat(cars_net, lag)
    mu_gross, se_gross, t_gross = _nw_tstat(cars_gross, lag)

    # Simple t (no HAC) for reference
    t_simple_net = mu_net / (np.std(cars_net, ddof=1) / math.sqrt(n)) if n > 1 else float("nan")

    return {
        "label": label,
        "n_events": n,
        "nw_lag": lag,
        "mean_car_gross_pct": round(mu_gross * 100, 4),
        "mean_car_net_pct": round(mu_net * 100, 4),
        "nw_se_net": round(se_net, 6),
        "nw_t_net": round(t_net, 4),
        "nw_t_gross": round(t_gross, 4),
        "t_simple_net": round(t_simple_net, 4),
        "pct_positive_gross": round(float(np.mean(cars_gross > 0)) * 100, 1),
        "pct_positive_net": round(float(np.mean(cars_net > 0)) * 100, 1),
        "breakeven_bps": round(mu_gross * 10000, 1),  # raw gross CAR in bps
        "cost_rt_bps": ROUND_TRIP_BPS,
        "cost_covered": bool(mu_gross * 10000 > ROUND_TRIP_BPS),
    }


# ---------------------------------------------------------------------------
# Keep-bar evaluation
# ---------------------------------------------------------------------------
def _evaluate_keep_bar(full_stats: dict, half_stats: list[dict]) -> dict:
    t_net = full_stats["nw_t_net"]
    kb1 = bool(t_net >= KEEP_NW_T)
    kb2 = all(h["mean_car_net_pct"] > 0 for h in half_stats) if len(half_stats) == 2 else False
    kb3 = full_stats["cost_covered"]
    verdict = "TRADEABLE" if (kb1 and kb2 and kb3) else "NOT-TRADEABLE"
    return {
        "kb1_nw_t_ge_2": {"pass": kb1, "nw_t": t_net, "threshold": KEEP_NW_T},
        "kb2_sign_both_halves": {
            "pass": kb2,
            "half_a_mean_net_pct": round(half_stats[0]["mean_car_net_pct"], 4) if half_stats else None,
            "half_b_mean_net_pct": round(half_stats[1]["mean_car_net_pct"], 4) if len(half_stats) > 1 else None,
        },
        "kb3_exceeds_breakeven": {
            "pass": kb3,
            "mean_gross_bps": full_stats["breakeven_bps"],
            "cost_rt_bps": ROUND_TRIP_BPS,
        },
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _assert_stage0()
    _assert_hashes()

    prices = _load_prices()
    panel = _load_panel()

    # Select IN and OUT events for XU030
    in_events = panel[(panel["index_tier"] == TIER) & (panel["direction"] == "IN")].reset_index(drop=True)
    out_events = panel[(panel["index_tier"] == TIER) & (panel["direction"] == "OUT")].reset_index(drop=True)

    print(f"XU030-IN events: {len(in_events)}")
    print(f"XU030-OUT events: {len(out_events)}")

    # Compute CARs
    in_records = _compute_cars(in_events, prices, "IN")
    out_records = _compute_cars(out_events, prices, "OUT")

    # Filter valid records
    in_valid = [r for r in in_records if r["gap_flag"] is None]
    in_gap = [r for r in in_records if r["gap_flag"] is not None]
    out_valid = [r for r in out_records if r["gap_flag"] is None]

    print(f"IN valid: {len(in_valid)}, gap/excluded: {len(in_gap)}")
    if in_gap:
        for g in in_gap:
            print(f"  GAP: {g['symbol']} {g['ann_date']} reason={g['gap_flag']}")

    # Arrays for stats
    in_cars_net = np.array([r["car_net"] for r in in_valid])
    in_cars_gross = np.array([r["car_gross"] for r in in_valid])

    # Full stats
    full_stats = _run_stats(in_cars_net, in_cars_gross, "IN_full")

    # Temporal halves (split by median ann_date)
    in_sorted = sorted(in_valid, key=lambda r: r["ann_date"])
    mid = len(in_sorted) // 2
    half_a = in_sorted[:mid]
    half_b = in_sorted[mid:]
    h_a_cars_net = np.array([r["car_net"] for r in half_a])
    h_a_cars_gross = np.array([r["car_gross"] for r in half_a])
    h_b_cars_net = np.array([r["car_net"] for r in half_b])
    h_b_cars_gross = np.array([r["car_gross"] for r in half_b])
    half_stats = [
        _run_stats(h_a_cars_net, h_a_cars_gross, f"IN_half_A_n{len(half_a)}"),
        _run_stats(h_b_cars_net, h_b_cars_gross, f"IN_half_B_n{len(half_b)}"),
    ]
    half_a_split = in_sorted[mid - 1]["ann_date"] if mid > 0 else None
    half_b_start = in_sorted[mid]["ann_date"] if mid < len(in_sorted) else None

    # OUT symmetry check (non-deployable, reported only)
    out_cars_net = np.array([r["car_net"] for r in out_valid])
    out_cars_gross = np.array([r["car_gross"] for r in out_valid])
    out_stats = _run_stats(out_cars_net, out_cars_gross, "OUT_symmetry") if len(out_valid) > 0 else {}

    # Keep-bar
    keep_bar = _evaluate_keep_bar(full_stats, half_stats)

    # Per-event summary for review
    in_summary = [
        {
            "symbol": r["symbol"],
            "ann_date": r["ann_date"],
            "eff_date": r["eff_date"],
            "actual_window_days": r["actual_window_days"],
            "stock_ret_pct": round(r["stock_ret"] * 100, 3),
            "bm_ret_pct": round(r["bm_ret"] * 100, 3),
            "car_gross_pct": round(r["car_gross"] * 100, 3),
            "car_net_pct": round(r["car_net"] * 100, 3),
        }
        for r in in_valid
    ]

    # Print key results
    print()
    print("=" * 60)
    print(f"FULL IN STATS (N={full_stats['n_events']}, NW-lag={full_stats['nw_lag']})")
    print(f"  Mean CAR gross: {full_stats['mean_car_gross_pct']:.2f}%")
    print(f"  Mean CAR net:   {full_stats['mean_car_net_pct']:.2f}%")
    print(f"  NW-t (net):     {full_stats['nw_t_net']:.4f}  [threshold={KEEP_NW_T}]")
    print(f"  NW-t (gross):   {full_stats['nw_t_gross']:.4f}")
    print(f"  % positive (gross): {full_stats['pct_positive_gross']:.0f}%")
    print(f"  Gross CAR bps:  {full_stats['breakeven_bps']:.1f}  cost={ROUND_TRIP_BPS:.1f}bp")
    print()
    print(f"TEMPORAL HALVES")
    for h in half_stats:
        print(f"  {h['label']}: mean_net={h['mean_car_net_pct']:.2f}%  NW-t={h['nw_t_net']:.3f}")
    print()
    print("KEEP-BAR EVALUATION")
    print(f"  KB1 NW-t>=2.0:         {'PASS' if keep_bar['kb1_nw_t_ge_2']['pass'] else 'FAIL'}  ({keep_bar['kb1_nw_t_ge_2']['nw_t']:.4f})")
    print(f"  KB2 both-halves pos:   {'PASS' if keep_bar['kb2_sign_both_halves']['pass'] else 'FAIL'}")
    print(f"  KB3 exceeds breakeven: {'PASS' if keep_bar['kb3_exceeds_breakeven']['pass'] else 'FAIL'}")
    print(f"  VERDICT: {keep_bar['verdict']}")
    print("=" * 60)

    # Assemble results
    results = {
        "directive": "RR-Y1-011-E",
        "stage0_path": str(STAGE0_PATH.relative_to(ROOT)),
        "stage0_hash_prefix": hashlib.sha256(STAGE0_PATH.read_bytes()).hexdigest()[:16],
        "full_stats": full_stats,
        "temporal_half_split_at": half_a_split,
        "temporal_half_b_starts": half_b_start,
        "half_stats": half_stats,
        "out_symmetry_stats": out_stats,
        "keep_bar": keep_bar,
        "in_events_valid_n": len(in_valid),
        "in_events_gap_n": len(in_gap),
        "in_gap_details": in_gap,
        "in_event_details": in_summary,
        "cost_model": {
            "half_spread_bps": HALF_SPREAD_BPS,
            "kyle_bps": KYLE_BPS_APPROX,
            "round_trip_bps": ROUND_TRIP_BPS,
            "source": "D-207 large-cap tier Roll+Kyle FIX-2/FIX-3",
        },
    }

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
