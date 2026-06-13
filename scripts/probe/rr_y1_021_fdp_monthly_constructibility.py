"""Flow-driven-pressure (FDP) MONTHLY-variant constructibility probe (facts only; NO returns).

Phase-1b feasibility probe. NOT a pre-registration, NOT a measurement of returns, NOT an edge
test. It answers one descriptive question: can the MONTHLY FDP factor be built from KAP fund
portfolio-distribution reports, as the Phase-1b premise proposed?

    FDP_i,month = sum_f [ Flow_f,month * w_{f,i,month-1} ]
        Flow_f,month   = monthly net unit creation/redemption * NAV   (mechanical, saver-driven)
        w_{f,i,month-1}= per-stock weight from the PRIOR month's portfolio report (lagged)

CRITICAL -- this script reads NO returns. It never calls pct_change, never reads a forward
window, never touches tr_index_*. Constructibility facts only (DEC-053-safe). Whether monthly
FDP predicts returns is Phase-2 work, deliberately out of scope here.

DECISIVE FINDING (live-probed 2026-06, plain httpx + Chrome-UA, read-only): the premised
machine-readable monthly per-stock "Portföy Dağılım Raporu" is NOT filed as a KAP disclosure.
Funds map to KAP via their founder (portföy yönetim şirketi); the founder's disclosure stream
is fully reachable but carries only corporate-level filings (general announcements, info forms,
governance, the management company's own periodic financial reports) -- across two independent
founders (İş Portföy, Inveo Portföy) there were 0 portfolio-distribution reports, 0 per-stock
holdings, 0 unit-movement (katılma payı hareketleri) disclosures. The monthly per-stock portfolio
lives only on TEFAS (Akamai/Playwright-gated breakdown, confirmed in Phase-1) and MKK's platform
(public domain does not resolve). So both FDP legs are off the free read-only structured routes.

It does two things:
  1. Reports the read-only access map probed for the monthly FDP inputs, so the wall is
     reproducible from the code.
  2. If a per-stock monthly fund-holdings snapshot is supplied (--holdings PATH: one row per
     (fund_code, ticker, weight, as_of_month)), computes the universe-intersection counts.
     Counts only, no returns. If absent, prints the access map and exits 0 (the acquisition
     route, not the harness, is the wall).

Denominators (frozen, do not mint a new universe):
  - survivorship-clean panel  -> data/clean_universe/adjusted_prices_2019_2026.parquet
  - investable list (static)  -> config.yaml portfolio.tickers

Run: python scripts/probe/rr_y1_021_fdp_monthly_constructibility.py [--holdings PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRICES = REPO / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"
CONFIG = REPO / "config.yaml"
DEFAULT_HOLDINGS = REPO / "data" / "probe" / "fdp_monthly_holdings_snapshot.parquet"

# Read-only public routes probed for the monthly FDP inputs (no auth, no purchase). Results
# observed live during the probe; recorded so the feasibility wall is reproducible from code.
KAP_ROUTES = [
    ("TEFAS fonProfilBilgiGetir -> kapLink (fund -> KAP founder page mapping)",
     "200 OK -- maps a fund code to its KAP founder page /tr/fon-bilgileri/genel/<slug>"),
    ("KAP fund page /tr/fon-bilgileri/genel/<slug> (SSR)",
     "200 OK -- embeds founder mkkMemberOid + fundCode + kapMemberTypes [FK, PYS]"),
    ("KAP founder disclosure stream /tr/bildirim-sorgu-sonuc?member=<oid> (SSR)",
     "200 OK, reachable -- but ONLY corporate disclosures (genel açıklama, bilgi formu, "
     "governance, mgmt-company financial/activity reports); 0 portfolio-distribution reports "
     "across 2 founders (İş Portföy 79 disclosures, Inveo Portföy 51) -- no per-stock holdings, "
     "no unit-movement (katılma payı hareketleri) filing"),
    ("KAP api/search/combined + api/disclosure/list/main (structured)",
     "666 / 500 -- WAF-blocked for automated access (moot: the report is not on KAP anyway)"),
]
ALT_ROUTES = [
    ("TEFAS per-stock portfolio breakdown (fon-detayli-analiz)",
     "Akamai/Playwright-gated for plain HTTP (Phase-1); no per-stock v2 JSON endpoint"),
    ("MKK fund platform fonbilgilendirme.com",
     "public domain does not resolve (DNS getaddrinfo failed)"),
    ("Monthly net unit creation/redemption (the mechanical numerator)",
     "off all free routes: not a KAP filing; TEFAS gives only a current size snapshot, no "
     "history; daily shares-outstanding history retired in 2026-04 (Phase-1)"),
]


def load_investable(path: Path) -> set[str]:
    import yaml
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(t).strip().upper() for t in cfg["portfolio"]["tickers"]}


def print_access_map() -> None:
    print(json.dumps({
        "id": "RR-Y1-021 FDP monthly-variant constructibility (facts only, NO returns)",
        "status": "NO_MONTHLY_HOLDINGS_SNAPSHOT",
        "note": "Phase-1b constructibility probe. The Phase-1b premise -- a machine-readable "
                "monthly per-stock Portföy Dağılım Raporu filed on KAP -- does not hold: that "
                "report is NOT a KAP disclosure. Founders file only corporate-level disclosures. "
                "The per-stock monthly portfolio lives only on TEFAS (browser-gated) and the "
                "monthly unit-movement numerator is off all free routes. The harness below "
                "computes the universe intersection the moment a (fund_code, ticker, weight, "
                "as_of_month) snapshot is supplied via --holdings. Counts only, no returns.",
        "kap_routes_probed": [{"route": r, "result": s} for r, s in KAP_ROUTES],
        "alternative_routes_probed": [{"route": r, "result": s} for r, s in ALT_ROUTES],
        "denominators_ready": {
            "survivorship_clean_panel": PRICES.exists(),
            "investable_list": CONFIG.exists(),
        },
    }, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdings", type=Path, default=DEFAULT_HOLDINGS,
                    help="per-stock monthly fund-holdings snapshot (parquet/csv: fund_code, "
                         "ticker, weight, as_of_month); counts only, no returns")
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
        "id": "RR-Y1-021 FDP monthly -- universe intersection (counts only, NO returns)",
        "class": "Phase-1b feasibility; NO return measurement; per-stock held names vs frozen denominators",
        "holdings_snapshot": str(args.holdings),
        "distinct_held_names": len(held_names),
        "held_names_in_clean_panel": len(in_panel),
        "held_names_in_investable_list": len(in_investable),
        "fraction_in_clean_panel": round(len(in_panel) / max(1, len(held_names)), 4),
        "fraction_in_investable_list": round(len(in_investable) / max(1, len(held_names)), 4),
        "investable_list_size": len(investable),
        "caveats": [
            "Counts only -- no returns / forward window examined (Phase-2 scope, DEC-053-safe).",
            "Intersection is NOT the binding constraint: the monthly report is not on KAP and "
            "the per-stock route is browser-gated, so the panel cannot be assembled free.",
            "Investable denominator is today's static config list; intra-span change not modelled.",
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
