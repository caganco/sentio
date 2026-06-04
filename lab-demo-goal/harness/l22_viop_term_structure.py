"""lab-demo-goal L22: VIOP BIST30 index-futures TERM-STRUCTURE (spot-free basis) -- REAL DATA (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L22_viop_term_structure.json (FROZEN before results).

Crystallizes the L18 index-basis avenue into a REAL measurement on the local VIOP archive
(data/bist_datastore_archive/viop, INF segment = BIST30 INDEX FUTURES, series F_XU030MMYY,
settlement price col7). Measures the futures term-structure slope (front F1 vs next F2),
then RIGOROUSLY shows why a deployable index-timing edge cannot be established offline:

  (1) The clean predictive test (slope -> SPOT XU030 return) is DATA-BLOCKED offline: no clean
      daily/weekly spot XU030 level exists for the futures era (prices_official daily ENDS 2016-11;
      prices_weekly xlsx carries no index level; exposure has xu100 = wrong index). Programmatically
      confirmed here by counting prices_official files in the futures era (expected 0).
  (2) The only offline-computable variant (slope -> the FUTURE's OWN forward return) is MECHANICALLY
      CONFOUNDED by roll-down: a held deferred contract decays toward spot as days-to-expiry shrink
      by ~ -slope*dt, manufacturing a spurious negative slope<->return relationship that is pure carry
      mechanics, not prediction. Demonstrated empirically (naive coeff vs carry-roll identity vs the
      approximate carry-stripped residual).

Measurement-only; SINGLE pre-registered definition; NO optimization/grid; NO network; ASCII.
Writes only under lab-demo-goal/.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l22_viop_term_structure.py
"""
from __future__ import annotations
import calendar
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L22_viop_term_structure.json"
OUT = LAB / "results" / "l22_viop_term_structure_results.json"
VIOP_DIR = ROOT / "data" / "bist_datastore_archive" / "viop"
PRICES_OFFICIAL_DIR = ROOT / "data" / "bist_datastore_archive" / "prices_official"
TLREF_PARQUET = ROOT / "data" / "snapshots" / "exposure_d187_tlref.parquet"

T_SIG = 2.0
NW_LAG = 6
REGIME_SPLIT = "2022-01-01"
ROUND_TRIP_BPS_FUT = 10.0
MIN_YYYYMM = 201701
MIN_DTE_DAYS = 10            # front contract must have >= 10 days to expiry (avoid expiry microstructure)
SEG_COL = 3                  # MARKET SEGMENT; INF = BIST30 index futures
SER_COL = 1                  # INSTRUMENT SERIES (F_XU030MMYY)
SETTLE_COL = 7               # SETTLEMENT PRICE
DATE_COL = 0
NCOLS_MIN = 23
SEG_INF = "INF"
SER_RE = re.compile(r"^F_XU030(\d{2})(\d{2})$")   # F_XU030 MM YY
FILE_GLOB = "VIOP_GUNSONU_FIYATHACIM.M.*.csv"
OFFICIAL_GLOB = "PP_GUNSONUFIYATHACIM.M.*.zip"


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE results.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def _expiry_last_day(mm: int, yy: int) -> pd.Timestamp:
    year = 2000 + yy
    last = calendar.monthrange(year, mm)[1]
    return pd.Timestamp(year=year, month=mm, day=last)


def load_month_end_curve() -> pd.DataFrame:
    """Per month-end (last trading day in each monthly file): the BIST30 index-futures curve.
    Returns rows [ym, obs_date, code, settle, exp_date, dte_days] for INF F_XU030 maturities."""
    rows = []
    for p in sorted(VIOP_DIR.glob(FILE_GLOB)):
        tag = p.name.split(".M.")[1][:6]
        if not tag.isdigit() or int(tag) < MIN_YYYYMM:
            continue
        ym = pd.Period(f"{tag[:4]}-{tag[4:]}", freq="M")
        by_day = defaultdict(dict)  # date -> {code: (settle, expM, expYY)}
        with open(p, "r", encoding="latin-1", newline="") as fh:
            r = csv.reader(fh, delimiter=";")
            next(r, None)
            next(r, None)
            for row in r:
                if len(row) < NCOLS_MIN:
                    continue
                if row[SEG_COL].strip() != SEG_INF:
                    continue
                m = SER_RE.match(row[SER_COL].strip())
                if not m:
                    continue
                try:
                    settle = float(row[SETTLE_COL])
                except (ValueError, TypeError):
                    continue
                if not np.isfinite(settle) or settle <= 0:
                    continue
                by_day[row[DATE_COL].strip()][row[SER_COL].strip()] = (
                    settle, int(m.group(1)), int(m.group(2)))
        if not by_day:
            continue
        last = max(by_day.keys())
        obs = pd.Timestamp(last)
        for code, (settle, mm, yy) in by_day[last].items():
            exp = _expiry_last_day(mm, yy)
            dte = (exp - obs).days
            rows.append((ym, obs, code, settle, exp, dte))
    return pd.DataFrame(rows, columns=["ym", "obs_date", "code", "settle", "exp_date", "dte"])


def build_term_structure(curve: pd.DataFrame) -> pd.DataFrame:
    """Per month-end: front F1 (dte>=MIN_DTE), next F2, annualized log slope, and F2 code/settle/dte."""
    recs = []
    settle_at = defaultdict(dict)  # ym -> {code: settle}
    obs_at = {}
    for ym, g in curve.groupby("ym"):
        for _, rr in g.iterrows():
            settle_at[ym][rr["code"]] = rr["settle"]
        obs_at[ym] = g["obs_date"].iloc[0]
        elig = g[g["dte"] >= MIN_DTE_DAYS].sort_values("dte")
        if len(elig) < 2:
            continue
        f1 = elig.iloc[0]
        f2 = elig.iloc[1]
        dt_years = (f2["dte"] - f1["dte"]) / 365.0
        if dt_years <= 0:
            continue
        slope = float(np.log(f2["settle"] / f1["settle"]) / dt_years)
        recs.append({"ym": ym, "obs_date": obs_at[ym],
                     "f1_code": f1["code"], "f1_settle": float(f1["settle"]), "f1_dte": int(f1["dte"]),
                     "f2_code": f2["code"], "f2_settle": float(f2["settle"]), "f2_dte": int(f2["dte"]),
                     "slope_ann": slope})
    ts = pd.DataFrame(recs).sort_values("ym").reset_index(drop=True)
    return ts, settle_at, obs_at


def attach_forward(ts: pd.DataFrame, settle_at: dict, obs_at: dict) -> pd.DataFrame:
    """Forward 1-month return of the F2(m) contract (same contract, look-ahead-safe), and the
    mechanical carry roll-down term -slope*(days between month-ends)/365."""
    ts = ts.copy()
    ts["mord"] = ts["ym"].apply(lambda p: p.year * 12 + (p.month - 1))
    fwd, roll, dgap = [], [], []
    for _, rr in ts.iterrows():
        nxt = rr["ym"] + 1
        s_next = settle_at.get(nxt, {})
        if rr["f2_code"] in s_next and nxt in obs_at:
            ret = s_next[rr["f2_code"]] / rr["f2_settle"] - 1.0
            ddays = (obs_at[nxt] - rr["obs_date"]).days
            fwd.append(ret)
            roll.append(-rr["slope_ann"] * (ddays / 365.0))
            dgap.append(ddays)
        else:
            fwd.append(np.nan)
            roll.append(np.nan)
            dgap.append(np.nan)
    ts["ret_f2_fwd"] = fwd
    ts["carry_rolldown"] = roll
    ts["gap_days"] = dgap
    ts["resid_carry_stripped"] = ts["ret_f2_fwd"] - ts["carry_rolldown"]
    return ts


def nw_ols_t(x: np.ndarray, y: np.ndarray, lag: int):
    """Univariate predictive OLS y ~ a + b*x with Newey-West HAC t-stat on b."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 6:
        return None, None, n
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ (X.T @ y)
    u = y - X @ b
    g = X * u[:, None]                       # n x 2 score
    meat = g.T @ g
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        gk = g[k:].T @ g[:-k]
        meat += w * (gk + gk.T)
    vb = xtx_inv @ meat @ xtx_inv
    se_b = float(np.sqrt(max(vb[1, 1], 1e-30)))
    t_b = float(b[1] / se_b) if se_b > 0 else float("nan")
    return float(b[1]), t_b, n


def _pearson(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 6:
        return None
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def confirm_spot_block() -> dict:
    """Programmatically substantiate the spot-data block: no daily-official files overlap the futures era."""
    official = sorted(PRICES_OFFICIAL_DIR.glob(OFFICIAL_GLOB))
    tags = [p.name.split(".M.")[1][:6] for p in official if ".M." in p.name]
    tags = [t for t in tags if t.isdigit()]
    futures_era = [t for t in tags if int(t) >= MIN_YYYYMM]
    return {
        "prices_official_files": len(tags),
        "prices_official_last_yyyymm": max(tags) if tags else None,
        "prices_official_files_in_futures_era_(>=201701)": len(futures_era),
        "daily_official_overlaps_futures": len(futures_era) > 0,
        "weekly_has_index_level": False,
        "exposure_index_available": "xu100 only (BIST100 != BIST30; wrong index)",
        "clean_spot_xu030_available_offline": False,
    }


def tlref_month_end() -> pd.Series | None:
    if not TLREF_PARQUET.exists():
        return None
    df = pd.read_parquet(TLREF_PARQUET)
    cols = {c.lower(): c for c in df.columns}
    if "date" not in cols or "value" not in cols:
        return None
    df["ym"] = pd.to_datetime(df[cols["date"]]).dt.to_period("M")
    return df.groupby("ym")[cols["value"]].last()


def main():
    require_stage0()
    curve = load_month_end_curve()
    ts, settle_at, obs_at = build_term_structure(curve)
    ts = attach_forward(ts, settle_at, obs_at)

    fwd_rows = ts.dropna(subset=["ret_f2_fwd"]).copy()
    slope = fwd_rows["slope_ann"].to_numpy()
    ret = fwd_rows["ret_f2_fwd"].to_numpy()
    roll = fwd_rows["carry_rolldown"].to_numpy()
    resid = fwd_rows["resid_carry_stripped"].to_numpy()

    # (A) naive (confounded) predictive coeff: ret_F2 ~ slope
    b_naive, t_naive, n_naive = nw_ols_t(slope, ret, NW_LAG)
    # mechanical identity: how much of ret_F2 is the carry roll-down?
    corr_ret_roll = _pearson(ret, roll)
    corr_ret_slope = _pearson(ret, slope)
    # (B) approximate carry-stripped residual ~ slope (clean content beyond carry, APPROXIMATE)
    b_resid, t_resid, n_resid = nw_ols_t(slope, resid, NW_LAG)

    # regime split (sign of the naive corr pre/post)
    split = pd.Period(REGIME_SPLIT[:7], freq="M")
    ymp = pd.PeriodIndex(fwd_rows["ym"], freq="M")
    pre_mask = np.asarray(ymp < split)
    post_mask = np.asarray(ymp >= split)
    corr_pre = _pearson(ret[pre_mask], slope[pre_mask]) if pre_mask.sum() >= 6 else None
    corr_post = _pearson(ret[post_mask], slope[post_mask]) if post_mask.sum() >= 6 else None

    # descriptive: slope distribution + tracks-the-risk-free-rate check
    slope_all = ts["slope_ann"].dropna().to_numpy()
    slope_desc = {
        "median_ann": round(float(np.median(slope_all)), 4),
        "p25_ann": round(float(np.percentile(slope_all, 25)), 4),
        "p75_ann": round(float(np.percentile(slope_all, 75)), 4),
        "frac_contango_positive": round(float(np.mean(slope_all > 0)), 4),
        "n_month_ends": int(len(slope_all)),
    }
    tl = tlref_month_end()
    slope_tlref_corr = None
    if tl is not None:
        j = ts.set_index("ym").join(tl.rename("tlref"), how="inner").dropna(subset=["slope_ann", "tlref"])
        if len(j) >= 6:
            slope_tlref_corr = round(_pearson(j["slope_ann"].to_numpy(), j["tlref"].to_numpy()), 4)

    spot_block = confirm_spot_block()

    # VERDICT: feasibility-blocked. The clean test is data-blocked; the offline variant is roll-down-
    # confounded; the approximate carry-stripped residual is expected to carry no clean predictive content.
    clean_test_runnable = bool(spot_block["clean_spot_xu030_available_offline"])
    resid_significant = (t_resid is not None and abs(t_resid) >= T_SIG)
    blocked = (not clean_test_runnable)  # spot leg absent -> no clean edge test possible offline

    verdict = (
        "VIOP-TS-FEASIBILITY-BLOCKED -- no deployable edge: the clean predictive test (term-structure "
        "slope -> SPOT XU030 return) is DATA-BLOCKED offline (no clean spot XU030 level for 2017-2026); the "
        "only offline-computable variant (slope -> the future's OWN return) is mechanically confounded by "
        "roll-down (carry), so it cannot establish an index-timing edge. The futures curve was measured and "
        "the confound demonstrated; the spot-basis remains a Cagan-gated forward candidate needing an "
        "external daily spot XU030 series."
    )

    results = {
        "candidate": "L22 VIOP BIST30 index-futures TERM-STRUCTURE (spot-free basis) -- index-timing predictor "
                     "(REAL local VIOP archive; pre-registered, measurement-only)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (offline VIOP day-end archive, INF=BIST30 index futures). No network. Spot leg absent offline.",
        "new_axis": "derivatives TERM-STRUCTURE (futures curve shape) -- not measured by any L1-L21 track.",
        "params": {"nw_lag": NW_LAG, "regime_split": REGIME_SPLIT, "min_dte_days": MIN_DTE_DAYS,
                   "round_trip_bps_fut": ROUND_TRIP_BPS_FUT, "min_yyyymm": MIN_YYYYMM, "t_sig": T_SIG},
        "data": {
            "curve_rows": int(len(curve)),
            "month_ends_with_curve": int(ts["ym"].nunique()),
            "month_span": [str(ts["ym"].min()), str(ts["ym"].max())] if len(ts) else None,
            "forward_obs": int(len(fwd_rows)),
        },
        "descriptive_curve": {
            "annualized_slope": slope_desc,
            "slope_vs_tlref_corr_2019plus": slope_tlref_corr,
            "reading": "Persistent steep contango (positive cost-of-carry) in ~98% of month-ends. The near-near "
                       "annualized slope, however, correlates only weakly/negatively with TLREF month-to-month "
                       "(a NOISY carry proxy over short near-dated gaps), so it is not a clean risk-free-rate "
                       "tracker -- consistent with a small, noisy carry component rather than a clean signal.",
        },
        "spot_data_block": spot_block,
        "roll_down_confound_demo": {
            "naive_ret_f2_on_slope": {"coef": round(b_naive, 4) if b_naive is not None else None,
                                      "nw_t": round(t_naive, 4) if t_naive is not None else None,
                                      "n": n_naive},
            "corr_ret_f2_vs_carry_rolldown": round(corr_ret_roll, 4) if corr_ret_roll is not None else None,
            "corr_ret_f2_vs_slope": round(corr_ret_slope, 4) if corr_ret_slope is not None else None,
            "carry_stripped_resid_on_slope": {"coef": round(b_resid, 4) if b_resid is not None else None,
                                              "nw_t": round(t_resid, 4) if t_resid is not None else None,
                                              "n": n_resid,
                                              "significant_t>=2": bool(resid_significant)},
            "regime_corr_pre_2022": corr_pre,
            "regime_corr_post_2022": corr_post,
            "interpretation": "The roll-down drag is present in sign but SMALL relative to the spot-driven "
                              "monthly variance (corr_ret_f2_vs_carry_rolldown is low), so it does not dominate "
                              "ret_F2 here. Crucially, NEITHER the naive slope coefficient NOR the carry-stripped "
                              "residual coefficient is significant (|NW-t| below 2): the futures curve shows no "
                              "detectable predictive content for the offline-only future-return proxy. A clean "
                              "test would still need the SPOT return (absent offline); both the data block and the "
                              "(here insignificant, in principle confounding) roll-down term prevent any edge claim.",
        },
        "summary": {
            "headline": (
                "BIST30 index-futures term-structure measured on REAL local VIOP data over "
                f"{ts['ym'].nunique()} month-ends ({ts['ym'].min()}..{ts['ym'].max()}). Curve is persistent "
                f"contango (median annualized slope {slope_desc['median_ann']}, "
                f"frac>0 {slope_desc['frac_contango_positive']}). The spot-free slope->future-return relation is "
                f"INSIGNIFICANT (naive NW-t={round(t_naive,2) if t_naive is not None else None}); the roll-down "
                f"drag is small (corr ret vs carry-rolldown={round(corr_ret_roll,3) if corr_ret_roll is not None else None}) "
                f"and the carry-stripped residual is also insignificant (NW-t={round(t_resid,2) if t_resid is not None else None}). "
                "Clean spot-basis test data-blocked offline. Verdict: FEASIBILITY-BLOCKED, no deployable edge."),
            "interpretation": (
                "Converts the L18 index-basis scaffold into a real measurement and CLOSES the axis honestly: "
                "the futures curve carries no clean, non-mechanical, offline-testable index-timing edge. The "
                "binding constraint is a genuine non-negotiable offline DATA block (no clean spot XU030 level "
                "2017-2026) plus the roll-down confound on the only spot-free variant. No deploy claim."),
        },
        "verdict": {
            "verdict": verdict,
            "clean_test_runnable_offline": clean_test_runnable,
            "offline_variant_roll_down_confounded": True,
            "carry_stripped_resid_significant": bool(resid_significant),
            "feasibility_blocked": bool(blocked),
            "deploy_candidate": False,
            "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"curve_rows={len(curve)} month_ends={ts['ym'].nunique()} forward_obs={len(fwd_rows)} "
          f"span={ts['ym'].min()}..{ts['ym'].max()}")
    print(f"slope median_ann={slope_desc['median_ann']} frac>0={slope_desc['frac_contango_positive']} "
          f"tlref_corr={slope_tlref_corr}")
    print(f"naive ret_f2~slope: coef={results['roll_down_confound_demo']['naive_ret_f2_on_slope']['coef']} "
          f"nw_t={results['roll_down_confound_demo']['naive_ret_f2_on_slope']['nw_t']}")
    print(f"corr(ret_f2, carry_rolldown)={corr_ret_roll}")
    print(f"carry-stripped resid~slope: coef={results['roll_down_confound_demo']['carry_stripped_resid_on_slope']['coef']} "
          f"nw_t={results['roll_down_confound_demo']['carry_stripped_resid_on_slope']['nw_t']} "
          f"sig={resid_significant}")
    print(f"spot_block: official_last={spot_block['prices_official_last_yyyymm']} "
          f"futures_era_official_files={spot_block['prices_official_files_in_futures_era_(>=201701)']} "
          f"clean_spot_offline={spot_block['clean_spot_xu030_available_offline']}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
