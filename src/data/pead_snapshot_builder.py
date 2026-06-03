"""RR-046 ASAMA-2a -- PEAD earnings-date + SUE snapshot (degoran month-proxy, 2009+).

DATA ACQUISITION ONLY (no edge-test, no optimization, committed-engine zero-touch).

Builds a look-ahead-safe panel of earnings-announcement *months* and seasonal-random-walk
SUE surprises for the full degoran fundamentals universe (2009-2026), entirely from LOCAL
data -- no KAP fetch (that is the budgeted Katman-2, NOT in scope here).

Why a month-proxy (RR-046 Q3): degoran `net_profit` is YEAR-TO-DATE cumulative, carried
FLAT between reports, so the month in which it STEP-CHANGES ~ the report-publication month
(validated against KAP disclosureDetail.time: THYAO FY2022 step at 2023-03 == KAP 01.03.2023).
Month resolution is sufficient for the FIRST PEAD read (drift is monthly-scale); exact-day
KAP refinement (Katman-2) opens only if the first read is promising.

Pipeline:
  1. load degoran 2009-2026 monthly long (mktval, net_profit) via the committed loader's
     legacy-inclusive glob (read-only; loader untouched).
  2. harmonize the market-wide power-of-10 redenomination breaks (reuse the FROZEN D-206
     detector on mktval; apply the SAME cumulative scale to net_profit). This puts net_profit
     on a consistent unit AND makes the uniform break-month jump cancel -> non-reporting
     symbols show NO false step at a redenomination month. Data cleaning, NOT optimization.
  3. per symbol, detect step-change months on harmonized net_profit -> announce_month proxy +
     the YTD net_profit reported at that step.
  4. map each announce_month to its fiscal (year, quarter, period_end) via the regulated
     Turkish reporting calendar (FY ~Feb-Apr, Q1 ~May, H1 ~Aug, 9M ~Nov).
  5. de-cumulate YTD -> single-quarter net_profit, RESETTING at the fiscal-year boundary
     (Q1 = raw YTD; Q_n = YTD_n - YTD_{n-1}); gap-aware (missing quarter -> NaN, never faked).
  6. SUE = (Q_t - Q_{t-4q}) / trailing-std(UE), seasonal-random-walk, look-ahead-safe.
  7. consume_from_month = announce_month + 1 (degoran month-M known at end-M; lag >=1).

Output (git-local; *.parquet/*.meta.json are gitignored -- force-add to track, mirroring
the committed exposure_*/faz0_* snapshot convention):
  data/snapshots/earnings_dates.parquet
  data/snapshots/earnings_dates.meta.json

CAVEATS (honest, see RR-046 Durustluk): month-resolution only; calendar bucket is a
heuristic (boundary months Apr/Jun/Jan less certain); nominal SUE is dominated by TL
inflation 2021-2024 -- real-deflation/scaling is an EDGE-TEST design choice (separate D),
deliberately NOT applied here.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.clean_universe_fundamentals import load_degoran_fundamentals
from src.screening.d206_nav_discount import harmonize_mktval_units

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
SNAPSHOTS_DIR = _REPO_ROOT / "data" / "snapshots"
_OUT_PARQUET = SNAPSHOTS_DIR / "earnings_dates.parquet"
_OUT_META = SNAPSHOTS_DIR / "earnings_dates.meta.json"

# --- frozen builder geometry (data-acquisition; no grid-sweep) ---
PEAD_START = "2009-01"
PEAD_END = "2026-12"
DEGORAN_GLOB = "degoran*.zip"          # legacy 2009-2019 monthly + modern 2019+; loader dedups
SUE_SEASONAL_LAG_Q = 4                  # same quarter, prior year
SUE_STD_WINDOW_Q = 8                    # trailing quarters for UE std
SUE_STD_MIN_PERIODS_Q = 6               # min non-NaN UE in window to standardize
LOOK_AHEAD_LAG_MONTHS = 1               # announce month M known at end-M -> consume >= M+1
SOURCE_TAG = "degoran-month-proxy"

# announce month-of-year -> (fiscal_year offset, quarter, period_end month/day).
# Regulated TR reporting windows: FY (Dec-31) ~Feb-Apr; Q1 (Mar-31) ~May-Jun;
# H1 (Jun-30) ~Jul-Sep; 9M (Sep-30) ~Oct-Dec; late 9M can slip to Jan.
_CAL_BUCKET = {
    1:  (-1, 3, (9, 30)),   # late 9M of prior year
    2:  (-1, 4, (12, 31)),  # annual (prior FY)
    3:  (-1, 4, (12, 31)),
    4:  (-1, 4, (12, 31)),
    5:  (0, 1, (3, 31)),    # Q1
    6:  (0, 1, (3, 31)),
    7:  (0, 2, (6, 30)),    # H1
    8:  (0, 2, (6, 30)),
    9:  (0, 2, (6, 30)),
    10: (0, 3, (9, 30)),    # 9M
    11: (0, 3, (9, 30)),
    12: (0, 3, (9, 30)),
}


def _build_unit_scale(months: list[pd.Period], breaks: list[dict]) -> pd.Series:
    """Per-month cumulative power-of-10 scale from D-206 break list (applied_factor at each
    break month, carried forward). Dividing a monetary series by this scale undoes the
    market-wide redenomination so cross-month values are comparable."""
    factor_at = {b["month"]: float(b["applied_factor"]) for b in breaks}
    cum = 1.0
    out = {}
    for m in months:
        if str(m) in factor_at:
            cum *= factor_at[str(m)]
        out[m] = cum
    return pd.Series(out)


def _harmonized_net_profit_long(funds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return long [month, symbol, net_profit_h] with the market-wide redenomination undone,
    plus harmonize meta. Breaks are detected on mktval (always positive -> clean median MoM
    ratio) and the SAME cumulative scale is applied to net_profit (uniform redenomination)."""
    f = funds.copy()
    f["month"] = f["month"].astype("period[M]")
    mk = f.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last").sort_index()
    _, hmeta = harmonize_mktval_units(mk)
    scale = _build_unit_scale(list(mk.index), hmeta["breaks"])
    f = f.merge(scale.rename("unit_scale"), left_on="month", right_index=True, how="left")
    f["net_profit_h"] = f["net_profit"] / f["unit_scale"]
    return f[["month", "symbol", "net_profit_h"]], hmeta


def _announce_to_fiscal(announce_month: pd.Period) -> tuple[int, int, pd.Timestamp]:
    """Map an announce month (Period[M]) -> (fiscal_year, quarter, period_end date)."""
    fy_off, q, (em, ed) = _CAL_BUCKET[announce_month.month]
    fy = announce_month.year + fy_off
    return fy, q, pd.Timestamp(year=fy, month=em, day=ed)


def _detect_announcements(npl: pd.DataFrame) -> pd.DataFrame:
    """Per symbol, a step-change in harmonized net_profit = a report publication.

    Returns rows [symbol, announce_month, net_profit_ytd, fiscal_year, quarter, period_end].
    The first observed value (carried from a pre-data report) is NOT a detectable step.
    """
    npl = npl.sort_values(["symbol", "month"])
    npl = npl[npl["net_profit_h"].notna()].copy()
    prev = npl.groupby("symbol")["net_profit_h"].shift(1)
    step = prev.notna() & (npl["net_profit_h"] != prev)
    ev = npl[step].rename(columns={"month": "announce_month", "net_profit_h": "net_profit_ytd"})
    fis = ev["announce_month"].map(_announce_to_fiscal)
    ev["fiscal_year"] = fis.map(lambda t: t[0])
    ev["quarter"] = fis.map(lambda t: t[1])
    ev["period_end"] = fis.map(lambda t: t[2])
    # de-dup: if two steps land on the same (symbol, fiscal_year, quarter), keep the earliest
    ev = ev.sort_values(["symbol", "fiscal_year", "quarter", "announce_month"])
    ev = ev.drop_duplicates(["symbol", "fiscal_year", "quarter"], keep="first")
    return ev[["symbol", "announce_month", "net_profit_ytd", "fiscal_year", "quarter", "period_end"]]


def _decumulate(ev: pd.DataFrame) -> pd.DataFrame:
    """YTD -> single-quarter net_profit, resetting each fiscal year. Gap-aware: a quarter
    whose immediate predecessor (quarter-1) is missing is left NaN (never fabricated)."""
    ev = ev.sort_values(["symbol", "fiscal_year", "quarter"]).copy()
    q_net = np.full(len(ev), np.nan)
    decum_ok = np.zeros(len(ev), dtype=bool)
    g_keys = ev[["symbol", "fiscal_year"]].values
    q = ev["quarter"].values
    ytd = ev["net_profit_ytd"].values
    for i in range(len(ev)):
        same_group = i > 0 and g_keys[i, 0] == g_keys[i - 1, 0] and g_keys[i, 1] == g_keys[i - 1, 1]
        if q[i] == 1:                                   # first quarter of the fiscal year
            q_net[i] = ytd[i]
            decum_ok[i] = True
        elif same_group and q[i] - q[i - 1] == 1:       # contiguous within-year predecessor
            q_net[i] = ytd[i] - ytd[i - 1]
            decum_ok[i] = True
        # else: starts mid-year or a gap -> leave NaN, decum_ok False
    ev["net_profit_q"] = q_net
    ev["decum_ok"] = decum_ok
    return ev


def _compute_sue(ev: pd.DataFrame) -> pd.DataFrame:
    """Seasonal-random-walk SUE per symbol on an absolute quarter index (gap-safe alignment):
    UE_t = Q_t - Q_{t-4q}; SUE_t = UE_t / trailing-std(UE). Look-ahead-safe (trailing-only)."""
    ev = ev.copy()
    ev["qid"] = ev["fiscal_year"] * 4 + (ev["quarter"] - 1)
    parts = []
    for sym, g in ev.groupby("symbol", sort=False):
        g = g.sort_values("qid").set_index("qid")
        full = pd.RangeIndex(int(g.index.min()), int(g.index.max()) + 1)
        q = g["net_profit_q"].reindex(full)            # NaN at absent quarters
        ue = q - q.shift(SUE_SEASONAL_LAG_Q)           # same quarter, prior year
        std = ue.rolling(SUE_STD_WINDOW_Q, min_periods=SUE_STD_MIN_PERIODS_Q).std()
        sue = ue / std.replace(0, np.nan)
        g["ue"] = ue.reindex(g.index).values
        g["sue"] = sue.reindex(g.index).values
        parts.append(g.reset_index())
    return pd.concat(parts, ignore_index=True)


def build_earnings_panel() -> tuple[pd.DataFrame, dict]:
    """Assemble the look-ahead-safe earnings-month + SUE panel from local degoran 2009-2026."""
    funds = load_degoran_fundamentals(start=PEAD_START, end=PEAD_END, file_glob=DEGORAN_GLOB)
    npl, hmeta = _harmonized_net_profit_long(funds)
    ev = _detect_announcements(npl)
    ev = _decumulate(ev)
    ev = _compute_sue(ev)
    ev["consume_from_month"] = ev["announce_month"] + LOOK_AHEAD_LAG_MONTHS
    ev["source"] = SOURCE_TAG
    ev["announce_month"] = ev["announce_month"].astype(str)
    ev["consume_from_month"] = ev["consume_from_month"].astype(str)
    ev["period_end"] = pd.to_datetime(ev["period_end"]).dt.strftime("%Y-%m-%d")
    cols = ["symbol", "fiscal_year", "quarter", "period_end", "announce_month",
            "consume_from_month", "net_profit_ytd", "net_profit_q", "decum_ok",
            "ue", "sue", "source"]
    ev = ev[cols].sort_values(["symbol", "fiscal_year", "quarter"]).reset_index(drop=True)

    meta = {
        "schema_version": 1,
        "directive": "RR-046 ASAMA-2a Katman-1",
        "phase": "PEAD earnings-month proxy + seasonal SUE (data acquisition only)",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "bist_datastore_archive/fundamental_ratios/degoran*.zip (local, read-only)",
        "announce_proxy": "month of net_profit YTD step-change ~ report publication month "
                          "(validated vs KAP disclosureDetail.time: THYAO FY2022 step 2023-03 "
                          "== KAP 01.03.2023)",
        "look_ahead_note": "announce_month M known at end-M; consume_from_month = M+1 "
                           "(look-ahead safe). SUE std is trailing-only.",
        "sue_definition": "seasonal-random-walk: UE = Q_t - Q_{t-4q}; "
                          f"SUE = UE / trailing-std(UE, window={SUE_STD_WINDOW_Q}q, "
                          f"min_periods={SUE_STD_MIN_PERIODS_Q}q). Konsensus GEREKMEZ.",
        "decumulation": "YTD -> single-quarter, fiscal-year reset (Q1=raw YTD; "
                        "Q_n=YTD_n-YTD_{n-1}); gap-aware (decum_ok=False -> q/ue/sue NaN).",
        "calendar_buckets": "FY~Feb-Apr / Q1~May-Jun / H1~Jul-Sep / 9M~Oct-Dec "
                            "(boundary months Apr/Jun/Jan less certain; documented proxy).",
        "unit_harmonization": hmeta,
        "caveats": [
            "month-resolution only (exact-day = budgeted KAP Katman-2, not in scope)",
            "nominal SUE dominated by TL inflation 2021-2024; real-deflation/scaling is an "
            "edge-test design choice (separate D), deliberately NOT applied",
            "calendar bucket is a heuristic; ~2009-2011 early-warmup quarters noisy",
            "survivorship: panel = today-available degoran symbols",
        ],
        "n_rows": int(len(ev)),
        "n_symbols": int(ev["symbol"].nunique()),
        "n_sue_defined": int(ev["sue"].notna().sum()),
        "fiscal_year_min": int(ev["fiscal_year"].min()),
        "fiscal_year_max": int(ev["fiscal_year"].max()),
    }
    return ev, meta


def build_and_write(force_rebuild: bool = False) -> tuple[pd.DataFrame, dict]:
    """Build and freeze the earnings/SUE snapshot. Idempotent unless force_rebuild."""
    if _OUT_PARQUET.exists() and _OUT_META.exists() and not force_rebuild:
        df = pd.read_parquet(_OUT_PARQUET)
        meta = json.loads(_OUT_META.read_text(encoding="utf-8"))
        logger.info("[pead] frozen-load: %s (%d rows)", _OUT_PARQUET.name, len(df))
        return df, meta
    df, meta = build_earnings_panel()
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_OUT_PARQUET, index=False)
    _OUT_META.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    logger.info("[pead] frozen: %s rows=%d symbols=%d sue_defined=%d",
                _OUT_PARQUET.name, meta["n_rows"], meta["n_symbols"], meta["n_sue_defined"])
    return df, meta


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    panel, m = build_and_write(force_rebuild=True)
    print(json.dumps({k: v for k, v in m.items() if k != "unit_harmonization"}, indent=2))
    print("\n[unit_harmonization]", json.dumps(m["unit_harmonization"], indent=2))
