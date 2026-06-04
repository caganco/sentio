"""lab-demo-goal L9: EMPIRICAL PEAD EVENT-VOLUME + power-shortfall bound (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L9_pead_volume.json (FROZEN before tabulating).

NO new edge, NO new data acquisition, NO optimization. Replaces L8's ASSUMED daily-PEAD
arrival rate (~120/yr) with the REAL liquid, SUE-testable earnings event volume from the
existing monthly panel, and bounds whether a day-stamped daily-PEAD test could reach the L8
n_required band [95, 759] for |t|=2.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l9_pead_volume.py
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L9_pead_volume.json"
OUT = LAB / "results" / "l9_pead_volume_results.json"
L8 = LAB / "results" / "l8_power_results.json"
EARNINGS = ROOT / "data" / "snapshots" / "earnings_dates.parquet"
PRICES = ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"

ADV_MIN_TL = 1.0e7
TRADING_DAYS_PER_MONTH = 21
ROLL = 63
MIN_PERIODS = 20
WINDOW_FY_MIN = 2019


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE tabulating.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def monthly_liquidity() -> pd.DataFrame:
    """Per (symbol, year-month): trailing-63d-median value_tl as of that month's last trading day."""
    p = pd.read_parquet(PRICES, columns=["date", "symbol", "value_tl"])
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["symbol", "date"])
    p["med63"] = (p.groupby("symbol")["value_tl"]
                  .transform(lambda s: s.rolling(ROLL, min_periods=MIN_PERIODS).median()))
    p["ym"] = p["date"].dt.strftime("%Y-%m")
    m = p.groupby(["symbol", "ym"])["med63"].last().reset_index()
    return m


def main():
    require_stage0()
    band = json.loads(L8.read_text(encoding="utf-8"))["summary"]["pead_reachability"][
        "n_required_band_for_t2_observed_effects"]
    band_lo, band_hi = float(band[0]), float(band[1])

    e = pd.read_parquet(EARNINGS)
    e = e[(e["fiscal_year"] >= WINDOW_FY_MIN) & (e["sue"].notna())].copy()
    e["ym"] = e["announce_month"].astype(str)
    e["yr"] = e["ym"].str.slice(0, 4)

    m = monthly_liquidity()
    e = e.merge(m, how="left", left_on=["symbol", "ym"], right_on=["symbol", "ym"])
    # keep only events whose announce-month is inside the price-panel coverage
    e = e[e["med63"].notna()].copy()
    e["liquid"] = e["med63"] >= ADV_MIN_TL

    total_events = int(len(e))
    liquid_events = int(e["liquid"].sum())
    distinct_months = int(e["ym"].nunique())
    distinct_months_liquid = int(e.loc[e["liquid"], "ym"].nunique())
    years = sorted(e["yr"].unique())
    n_years = len(years)

    # month->day bounded independent date-clusters (LIQUID): per month, min(events, 21 trading days)
    per_month_liq = e[e["liquid"]].groupby("ym").size()
    bounded_dates_liquid = int(per_month_liq.clip(upper=TRADING_DAYS_PER_MONTH).sum())

    liquid_per_year = liquid_events / n_years if n_years else None
    bounded_dates_per_year = bounded_dates_liquid / n_years if n_years else None

    def years_to(n_req, rate):
        return round(n_req / rate, 2) if rate else None

    reach = {
        "l8_n_required_band_for_t2": [band_lo, band_hi],
        "empirical_liquid_events_per_year": round(liquid_per_year, 1) if liquid_per_year else None,
        "bounded_daily_date_clusters_per_year": round(bounded_dates_per_year, 1) if bounded_dates_per_year else None,
        "years_to_band_at_bounded_date_rate": [
            years_to(band_lo, bounded_dates_per_year), years_to(band_hi, bounded_dates_per_year)],
        "years_to_band_at_liquid_event_rate": [
            years_to(band_lo, liquid_per_year), years_to(band_hi, liquid_per_year)],
        "l8_assumed_rate_was": 120.0,
        "empirical_vs_assumed_note": (
            "L8 assumed ~120 independent disclosure-dates/yr. L9 measures the bounded daily "
            "date-cluster rate from the REAL liquid SUE-testable panel; compare to confirm or "
            "revise the L8 reachability estimate."),
    }

    verdict_reach = (
        bounded_dates_per_year is not None and bounded_dates_per_year > 0
        and (band_hi / bounded_dates_per_year) <= 10.0)

    results = {
        "candidate": "L9 empirical PEAD event-volume + power-shortfall bound",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "window": f"fiscal_year>={WINDOW_FY_MIN}, SUE-testable (sue non-null), price-panel-covered months",
        "adv_min_tl": ADV_MIN_TL, "roll": ROLL, "trading_days_per_month": TRADING_DAYS_PER_MONTH,
        "counts": {
            "total_testable_events": total_events,
            "liquid_testable_events": liquid_events,
            "liquid_fraction": round(liquid_events / total_events, 4) if total_events else None,
            "distinct_announce_months": distinct_months,
            "distinct_announce_months_liquid": distinct_months_liquid,
            "bounded_daily_date_clusters_liquid": bounded_dates_liquid,
            "years_covered": years, "n_years": n_years,
        },
        "reachability": reach,
        "summary": {
            "headline": (
                f"Real liquid SUE-testable earnings volume = {liquid_events} events over {n_years} yr "
                f"(~{round(liquid_per_year,0) if liquid_per_year else 0:.0f}/yr); day-stamping bounds this "
                f"to ~{round(bounded_dates_per_year,0) if bounded_dates_per_year else 0:.0f} independent "
                f"date-clusters/yr. The L8 n_required band [{band_lo:.0f}, {band_hi:.0f}] for |t|=2 would "
                f"accrue in ~{reach['years_to_band_at_bounded_date_rate'][0]}-"
                f"{reach['years_to_band_at_bounded_date_rate'][1]} yr at that rate."),
            "interpretation": (
                "Grounds L8's assumed ~120/yr with measured volume. If the bounded date-cluster rate "
                "is within ~2x of 120 and the band clears in <~10 yr, daily-PEAD remains the only "
                "power-reachable event class -- now on EMPIRICAL volume. CAVEAT: month-resolution gives "
                "a CEILING on date-clusters (true daily spread unknown until day-stamps are fetched); "
                "SUE coverage limits the testable subset."),
        },
        "verdict": {
            "verdict": "DESCRIPTIVE-VOLUME-VIEW (data-grounded daily-PEAD reachability bound; no edge)",
            "daily_pead_band_reachable_under_10yr": bool(verdict_reach),
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"total_testable={total_events}  liquid_testable={liquid_events}  "
          f"liquid_frac={results['counts']['liquid_fraction']}")
    print(f"distinct_announce_months={distinct_months} (liquid {distinct_months_liquid})  "
          f"years={n_years}")
    print(f"liquid events/yr={reach['empirical_liquid_events_per_year']}  "
          f"bounded date-clusters/yr={reach['bounded_daily_date_clusters_per_year']}")
    print(f"L8 band={band}  years_to_band(bounded)={reach['years_to_band_at_bounded_date_rate']}")
    print(f"daily-PEAD band reachable <10yr: {verdict_reach}")


if __name__ == "__main__":
    main()
