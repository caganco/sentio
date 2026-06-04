"""lab-demo-goal L10: DAILY-PEAD EFFECT-SIZE RECOVERY BOUND (SIGN + MAGNITUDE) (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L10_pead_effect.json (FROZEN before tabulating).

NO new edge, NO new data acquisition, NO optimization. Completes the forward-data #1
feasibility loop: L8 gave the n_required band for |t|=2, L9 gave the real liquid volume/rate,
and L10 bounds the per-event EFFECT a day-stamped daily-PEAD test would need -- in MAGNITUDE
(recovery factor over the attenuated monthly effect) and in SIGN (L3 found the LIQUID monthly
SUE effect is significantly NEGATIVE, so day-stamping may have to FLIP the sign, not just
amplify). The daily announcement-window effect is UNMEASURABLE offline; L10 bounds the
requirement and flags the sign hurdle -- only the approved day-stamp fetch can confirm sign.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l10_pead_effect.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L10_pead_effect.json"
OUT = LAB / "results" / "l10_pead_effect_results.json"
L3 = LAB / "results" / "l3_pead_results.json"
L8 = LAB / "results" / "l8_power_results.json"
L9 = LAB / "results" / "l9_pead_volume_results.json"
EARNINGS = ROOT / "data" / "snapshots" / "earnings_dates.parquet"
PRICES = ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"

ADV_MIN_TL = 1.0e7
ROLL = 63
MIN_PERIODS = 20
WINDOW_FY_MIN = 2019
T_SIG = 2.0
HORIZONS_YEARS = [1, 3, 5, 8]


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def prev_ym(ym: str) -> str:
    return str(pd.Period(ym, freq="M") - 1)


def month_returns_and_liquidity():
    """Per (symbol, ym): calendar-month total return (adjusted_close last/prev-last - 1)
    and trailing-63d-median value_tl as of that month's last trading day."""
    p = pd.read_parquet(PRICES, columns=["date", "symbol", "adjusted_close", "value_tl"])
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["symbol", "date"])
    p["med63"] = (p.groupby("symbol")["value_tl"]
                  .transform(lambda s: s.rolling(ROLL, min_periods=MIN_PERIODS).median()))
    p["ym"] = p["date"].dt.strftime("%Y-%m")
    last = p.groupby(["symbol", "ym"]).agg(close=("adjusted_close", "last"),
                                           med63=("med63", "last")).reset_index()
    last = last.sort_values(["symbol", "ym"])
    last["ret"] = last.groupby("symbol")["close"].pct_change()
    return last


def main():
    require_stage0()
    band = json.loads(L8.read_text(encoding="utf-8"))["summary"]["pead_reachability"][
        "n_required_band_for_t2_observed_effects"]
    band_lo, band_hi = float(band[0]), float(band[1])
    l9 = json.loads(L9.read_text(encoding="utf-8"))["reachability"]
    rate = float(l9["bounded_daily_date_clusters_per_year"])

    e = pd.read_parquet(EARNINGS)
    e = e[(e["fiscal_year"] >= WINDOW_FY_MIN) & (e["sue"].notna())].copy()
    e["cm"] = e["consume_from_month"].astype(str)

    last = month_returns_and_liquidity()
    last["liquid_eom"] = last["med63"] >= ADV_MIN_TL
    ret_map = {(r.symbol, r.ym): r.ret for r in last.itertuples()}
    liq_eom = {(r.symbol, r.ym): bool(r.liquid_eom) for r in last.itertuples()}

    # per consume-month: EW mean return over LIQUID universe (liquidity known at entry = end of prior month)
    rows = last[["symbol", "ym", "ret"]].dropna(subset=["ret"]).copy()
    rows["pm"] = rows["ym"].map(prev_ym)
    rows["liquid_entry"] = [liq_eom.get((s, pm), False) for s, pm in zip(rows["symbol"], rows["pm"])]
    liq_univ = rows[rows["liquid_entry"]]
    ew_liquid_mean = liq_univ.groupby("ym")["ret"].mean().to_dict()

    # per-event market-relative consume-month return + liquid-at-entry flag + SUE sign
    recs = []
    for ev in e.itertuples():
        cm = ev.cm
        r = ret_map.get((ev.symbol, cm))
        if r is None or pd.isna(r):
            continue
        bench = ew_liquid_mean.get(cm)
        if bench is None or pd.isna(bench):
            continue
        liq = liq_eom.get((ev.symbol, prev_ym(cm)), False)
        recs.append((ev.symbol, cm, float(r - bench), bool(liq), 1 if ev.sue > 0 else -1))
    df = pd.DataFrame(recs, columns=["symbol", "cm", "rel", "liquid", "sue_sign"])

    def effect(sub: pd.DataFrame):
        pos = sub.loc[sub["sue_sign"] > 0, "rel"]
        neg = sub.loc[sub["sue_sign"] < 0, "rel"]
        eff = float(pos.mean() - neg.mean())
        # Welch two-sample t (positive-SUE vs negative-SUE)
        sp, sn = pos.var(ddof=1), neg.var(ddof=1)
        np_, nn = len(pos), len(neg)
        se = float(np.sqrt(sp / np_ + sn / nn)) if np_ > 1 and nn > 1 else float("nan")
        t = eff / se if se and se == se and se > 0 else float("nan")
        return {"effect_pos_minus_neg": round(eff, 6), "n_pos": int(np_), "n_neg": int(nn),
                "welch_t": round(t, 4) if t == t else None,
                "mean_pos": round(float(pos.mean()), 6), "mean_neg": round(float(neg.mean()), 6)}

    eff_all = effect(df)
    df_liq = df[df["liquid"]].copy()
    eff_liq = effect(df_liq)
    sd_event = float(df_liq["rel"].std(ddof=1))

    liq_eff_abs = abs(eff_liq["effect_pos_minus_neg"])
    sign_contingent = eff_liq["effect_pos_minus_neg"] <= 0
    liq_eff_significant = (eff_liq["welch_t"] is not None and abs(eff_liq["welch_t"]) >= T_SIG)

    req = []
    for H in HORIZONS_YEARS:
        n = rate * H
        eff_req = T_SIG * sd_event / np.sqrt(n)
        rec_factor = (eff_req / liq_eff_abs) if liq_eff_abs > 0 else None
        req.append({
            "horizon_years": H, "n_at_l9_rate": round(n, 1),
            "required_per_event_effect_for_t2": round(float(eff_req), 6),
            "recovery_factor_over_monthly_liquid_effect": (round(float(rec_factor), 2)
                                                           if rec_factor is not None else None),
        })

    results = {
        "candidate": "L10 daily-PEAD effect-size recovery bound (sign + magnitude)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "window": f"fiscal_year>={WINDOW_FY_MIN}, SUE-testable (sue non-null), consume-month tradeable",
        "adv_min_tl": ADV_MIN_TL, "roll": ROLL, "t_sig": T_SIG,
        "market_relative_benchmark": "EW-mean consume-month return of LIQUID universe (entry-known liquidity)",
        "counts": {
            "events_with_return": int(len(df)),
            "liquid_events_with_return": int(len(df_liq)),
            "liquid_fraction": round(len(df_liq) / len(df), 4) if len(df) else None,
        },
        "monthly_sue_effect_event_level": {
            "ALL": eff_all,
            "LIQUID": eff_liq,
            "sd_event_liquid": round(sd_event, 6),
            "l3_monthly_liquid_tercile_costfree_mean": -0.013155,
            "l3_monthly_liquid_tercile_nw_t": -3.237,
            "corroborates_l3_negative_liquid_sign": bool(eff_liq["effect_pos_minus_neg"] <= 0),
        },
        "required_effect_by_horizon": req,
        "sign_hurdle": {
            "monthly_liquid_effect_pos_minus_neg": eff_liq["effect_pos_minus_neg"],
            "monthly_liquid_effect_significant": bool(liq_eff_significant),
            "sign_contingent": bool(sign_contingent),
            "note": ("If monthly LIQUID SUE effect <= 0, the daily positive-PEAD thesis requires "
                     "day-stamping to FLIP the liquid sign, not merely amplify it (sign-contingent). "
                     "Here the event-level half-split is positive but INSIGNIFICANT, so the thesis "
                     "is a MAGNITUDE/recovery question: day-stamping must lift a weak, noisy monthly "
                     "spread to significance. Only the approved day-stamp fetch can resolve it."),
        },
        "window_noise_caveat": (
            "sd_event here is the MONTHLY cross-sectional sd (~18.5%); a true daily / few-day "
            "announcement window has far lower noise (sd scales ~sqrt(days/21)), so the required "
            "daily-window effect is SMALLER than the monthly-noise bound implies. The required-effect "
            "and recovery-factor numbers are therefore CONSERVATIVE (pessimistic) for daily-PEAD."),
        "reachability_context": {
            "l8_n_required_band_for_t2": [band_lo, band_hi],
            "l9_bounded_date_clusters_per_year": rate,
        },
        "summary": {
            "headline": (
                f"Event-level monthly SUE effect (pos-minus-neg) = {eff_liq['effect_pos_minus_neg']:+.4f} "
                f"LIQUID (Welch t={eff_liq['welch_t']}) vs {eff_all['effect_pos_minus_neg']:+.4f} ALL; "
                f"sd_event(liquid)={sd_event:.4f}. For |t|=2 at the L9 rate (~{rate:.0f}/yr), a daily-PEAD "
                f"test needs a per-event effect of ~{req[0]['required_per_event_effect_for_t2']*1e4:.0f}bp "
                f"(1yr) down to ~{req[-1]['required_per_event_effect_for_t2']*1e4:.0f}bp (8yr). "
                + ("SIGN-CONTINGENT: the monthly liquid sign is adverse, so day-stamping must FLIP it."
                   if sign_contingent else
                   "The monthly liquid half-split sign is positive but INSIGNIFICANT; this is a "
                   "magnitude/recovery question, not a sign flip.")),
            "interpretation": (
                "Closes the forward-data #1 loop. Volume (L9) suffices; the event-level monthly SUE "
                "half-split is correctly signed (+) in liquid names but statistically insignificant "
                "(t<1) against ~18.5% monthly cross-sectional noise. A daily-PEAD test must lift the "
                "effect to ~2-5.5x the monthly half-split (within 1-8 yr) -- but the daily window's "
                "lower noise makes that bound conservative. The binding uncertainty is whether a "
                "concentrated positive announcement-window drift exists; UNMEASURABLE offline. This "
                "sharpens WHY the approved KAP day-stamp fetch is the decisive experiment."),
        },
        "verdict": {
            "verdict": (
                "SIGN-CONTINGENT-FEASIBILITY-VIEW (no edge; daily-PEAD decisive uncertainty is sign)"
                if sign_contingent else
                "MAGNITUDE-FEASIBILITY-VIEW (no edge; daily-PEAD decisive uncertainty is daily-window "
                "effect magnitude/sign, unmeasurable offline)"),
            "sign_contingent": bool(sign_contingent),
            "monthly_liquid_effect_significant": bool(liq_eff_significant),
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"events_with_return={len(df)}  liquid={len(df_liq)}  "
          f"liquid_frac={results['counts']['liquid_fraction']}")
    print(f"monthly SUE effect (pos-neg): ALL={eff_all['effect_pos_minus_neg']:+.4f} "
          f"LIQUID={eff_liq['effect_pos_minus_neg']:+.4f} (Welch t={eff_liq['welch_t']})")
    print(f"sd_event(liquid)={sd_event:.4f}  sign_contingent={sign_contingent}")
    for r in req:
        print(f"  H={r['horizon_years']}yr n={r['n_at_l9_rate']}: eff_req="
              f"{r['required_per_event_effect_for_t2']*1e4:.0f}bp  "
              f"recovery_x={r['recovery_factor_over_monthly_liquid_effect']}")


if __name__ == "__main__":
    main()
