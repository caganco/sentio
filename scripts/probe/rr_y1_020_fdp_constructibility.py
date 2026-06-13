"""Flow-driven-pressure (FDP) factor constructibility probe (facts only; NO returns).

Phase-1 feasibility probe. NOT a pre-registration, NOT a measurement of returns, NOT an
edge test. It answers one descriptive question: can the FDP factor be BUILT at a usable
resolution from free public data?

    FDP_i,t = sum_f [ Flow_f,t * w_{f,i,t-k} ]
        Flow_f,t   = d(shares_outstanding_f,t) * NAV_f,t   (mechanical creation/redemption)
        w_{f,i,t-k}= weight of stock i in fund f at the last disclosed holdings date < t

CRITICAL -- this script reads NO returns. It never calls pct_change, never reads a forward
window, never touches tr_index_*. Constructibility facts only. Whether FDP predicts returns
is Phase-2 work, deliberately out of scope here (DEC-053-safe).

It does two things:
  1. Reports the read-only public-access map probed for the two FDP inputs (the mechanical
     flow numerator and the per-stock holdings weights), so the feasibility wall is
     reproducible from the code.
  2. If a per-stock fund-holdings snapshot is supplied (--holdings PATH: one row per
     (fund_code, ticker, weight, as_of_date)), computes the universe-intersection counts
     (what fraction of held stock names fall inside the survivorship-clean panel and the
     investable list). Counts only -- no returns. If absent, prints the access map and
     exits 0 (the acquisition route, not the harness, is the wall).

Denominators (frozen, do not mint a new universe):
  - survivorship-clean panel  -> data/clean_universe/adjusted_prices_2019_2026.parquet
  - investable list (static)  -> config.yaml portfolio.tickers

Run: python scripts/probe/rr_y1_020_fdp_constructibility.py [--holdings PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRICES = REPO / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"
PIT = REPO / "data" / "clean_universe" / "pit_membership_2019_2026.parquet"
CONFIG = REPO / "config.yaml"
DEFAULT_HOLDINGS = REPO / "data" / "probe" / "fdp_holdings_snapshot.parquet"

# Read-only public routes probed for the two FDP inputs (no auth, no purchase). Recorded so
# the feasibility wall is reproducible from the code. Results observed live during the probe.
FLOW_NUMERATOR_ROUTES = [
    ("TEFAS v2 fonFiyatBilgiGetir (JSON, no-auth)",
     "200 OK -- 5y DAILY NAV (unit price) history; price ONLY, no size/shares column"),
    ("TEFAS v2 fonBilgiGetir (JSON, no-auth)",
     "200 OK -- CURRENT snapshot: portBuyukluk (fund value), yatirimciSayi (investors); no history"),
    ("TEFAS legacy /api/DB/BindHistoryInfo (the canonical daily TEDPAYSAYISI/PORTFOYBUYUKLUK source)",
     "404 -- retired in the 2026-04 migration; daily shares-outstanding history no longer served"),
    ("TEFAS v2 size/shares history candidates (fonToplamDegerGetir, fonBuyuklukBilgiGetir, ...)",
     "404 -- no v2 endpoint replaces the retired daily size/shares history"),
    ("TEFAS fon-detayli-analiz SSR page (size/shares markers)",
     "200 body but Akamai-gated; carries no portBuyukluk/tedPaySayisi markers for plain HTTP"),
]
HOLDINGS_ROUTES = [
    ("TEFAS asset-class allocation (HS = stock %, aggregate)",
     "Akamai/Playwright-gated for plain HTTP; aggregate equity % only, NOT per-stock weights"),
    ("SPK / KAP monthly fund portfolio report (Portfoy Dagilim Raporu)",
     "per-stock weights published MONTHLY with publication lag (~weeks); not a daily feed"),
]


def load_investable(path: Path) -> set[str]:
    import yaml
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(t).strip().upper() for t in cfg["portfolio"]["tickers"]}


def print_access_map() -> None:
    print(json.dumps({
        "id": "RR-Y1-020 FDP factor constructibility (facts only, NO returns)",
        "status": "NO_HOLDINGS_SNAPSHOT",
        "note": "Phase-1 constructibility probe. The binding constraint is upstream of this "
                "harness: the mechanical flow numerator (daily shares-outstanding history) is "
                "forward-snapshot-only on free public data, and per-stock holdings weights are "
                "monthly + lagged. The harness below computes the universe intersection the "
                "moment a (fund_code, ticker, weight, as_of_date) holdings snapshot is supplied "
                "via --holdings. Counts only, no returns.",
        "flow_numerator_routes_probed": [{"route": r, "result": s} for r, s in FLOW_NUMERATOR_ROUTES],
        "holdings_routes_probed": [{"route": r, "result": s} for r, s in HOLDINGS_ROUTES],
        "denominators_ready": {
            "survivorship_clean_panel": PRICES.exists(),
            "pit_membership": PIT.exists(),
            "investable_list": CONFIG.exists(),
        },
    }, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdings", type=Path, default=DEFAULT_HOLDINGS,
                    help="per-stock fund-holdings snapshot (parquet/csv: fund_code, ticker, "
                         "weight, as_of_date); counts only, no returns")
    args = ap.parse_args()

    if not args.holdings.exists():
        print_access_map()
        return 0

    import pandas as pd
    if args.holdings.suffix == ".csv":
        h = pd.read_csv(args.holdings)
    else:
        h = pd.read_parquet(args.holdings)
    h.columns = [c.lower() for c in h.columns]
    h["ticker"] = h["ticker"].astype(str).str.strip().str.upper()

    investable = load_investable(CONFIG)
    import pyarrow.parquet as pq
    panel_syms = {s.upper() for s in pq.read_table(PRICES, columns=["symbol"])["symbol"].to_pylist()}

    held_names = set(h["ticker"])
    in_panel = {t for t in held_names if t in panel_syms}
    in_investable = {t for t in held_names if t in investable}

    out = {
        "id": "RR-Y1-020 FDP factor constructibility -- universe intersection (counts only, NO returns)",
        "class": "Phase-1 feasibility; NO return measurement; per-stock held names vs frozen denominators",
        "holdings_snapshot": str(args.holdings),
        "distinct_held_names": len(held_names),
        "held_names_in_clean_panel": len(in_panel),
        "held_names_in_investable_list": len(in_investable),
        "fraction_in_clean_panel": round(len(in_panel) / max(1, len(held_names)), 4),
        "fraction_in_investable_list": round(len(in_investable) / max(1, len(held_names)), 4),
        "investable_list_size": len(investable),
        "caveats": [
            "Counts only -- no returns / forward window examined (Phase-2 scope, DEC-053-safe).",
            "Intersection is NOT the binding constraint: the flow numerator (daily shares "
            "history) is forward-only and holdings weights are monthly+lagged on free data.",
            "Investable denominator is today's static config list; intra-span change not modelled.",
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
