"""VBTS measure-event universe-intersection harness (counts only; NO returns).

Phase-1 feasibility probe. NOT a pre-registration, NOT a measurement of returns,
NOT an edge test. It answers one descriptive question: of the volatility-based
surveillance-measure events on BIST, what fraction land on names inside the
survivorship-clean panel and the investable list, broken down by measure level.

CRITICAL — this script reads NO returns. It never calls pct_change, never reads a
forward window, never touches tr_index_*. Counts only. Return behaviour around a
measure entry is Phase-2 work, deliberately out of scope here.

Point-in-time discipline (look-ahead-safe): a ticker is classified as BIST30 /
BIST100 / outside using its index-membership flag AS OF the event date — the last
trading day on or before the event — never today's membership. Classifying with
current membership would contaminate the intersection ratio with hindsight.

Input: a measure-event table (parquet or csv) with one row per
(ticker, level, start_date, end_date, announce_ts, is_escalation). Path defaults to
data/probe/vbts_events.parquet and can be overridden with --events. If the table is
absent, the script prints the read-only access-route status recorded during the
feasibility probe and exits 0 (the acquisition route, not the harness, was the wall).

Denominators (frozen, do not mint a new universe):
  - survivorship-clean panel  -> data/clean_universe/adjusted_prices_2019_2026.parquet
  - investable list (static)  -> config.yaml portfolio.tickers
Caveat: the investable list is today's static list; intra-span membership change is
not modelled (honesty note, not a correction).

Run: python scripts/probe/rr_y1_019_vbts_universe_intersection.py [--events PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRICES = REPO / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"
PIT = REPO / "data" / "clean_universe" / "pit_membership_2019_2026.parquet"
CONFIG = REPO / "config.yaml"
DEFAULT_EVENTS = REPO / "data" / "probe" / "vbts_events.parquet"

# Read-only public access routes probed for the per-(ticker, level, date) measure
# stream (no auth, no purchase). Recorded so the wall is reproducible from the code.
ACCESS_STATUS = [
    ("KAP legacy memberDisclosureQuery (cookie-warmed POST)", "ReadTimeout — WAF tarpit, endpoint retired"),
    ("KAP frontend backend host (site data API)", "DNS getaddrinfo failed — not publicly resolvable"),
    ("Exchange site root + announcements list (bare-path GET)", "200 OK, but rule-level notices only; zero per-stock measure rows"),
    ("Exchange site www deep-links", "server disconnect (RemoteProtocolError)"),
    ("Third-party aggregator disclosure data endpoint", "401 Unauthorized — auth-gated"),
    ("Exchange historical measure archive", "paid data product — excluded by no-purchase constraint"),
]


def load_investable(path: Path) -> set[str]:
    import yaml
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(t).strip().upper() for t in cfg["portfolio"]["tickers"]}


def load_pit_index(path: Path):
    """Return {symbol: (sorted_dates, in30_list, in100_list)} for as-of lookups."""
    import pandas as pd
    pm = pd.read_parquet(path)
    pm["date"] = pd.to_datetime(pm["date"]).dt.date
    idx: dict[str, tuple[list, list, list]] = {}
    for sym, g in pm.sort_values("date").groupby("symbol"):
        idx[str(sym).upper()] = (
            list(g["date"]),
            list(g["in_bist30"].astype(bool)),
            list(g["in_bist100"].astype(bool)),
        )
    return idx


def membership_as_of(idx, symbol: str, on_date):
    """PIT lookup: flags on the last panel date <= on_date. None if no prior date."""
    rec = idx.get(symbol.upper())
    if rec is None:
        return None  # ticker absent from clean panel
    dates, in30, in100 = rec
    pos = bisect_right(dates, on_date) - 1
    if pos < 0:
        return None  # event predates the panel for this symbol
    return {"in_bist30": in30[pos], "in_bist100": in100[pos], "as_of": dates[pos]}


def classify(flags, in_panel: bool, in_investable: bool) -> str:
    if not in_panel:
        return "outside_clean_panel"
    if flags is None:
        return "in_panel_no_pit"
    if flags["in_bist30"]:
        return "bist30"
    if flags["in_bist100"]:
        return "bist100_ex30"
    return "in_panel_outside_index"


def print_access_status() -> None:
    print(json.dumps({
        "id": "RR-Y1-019 VBTS measure-event universe intersection (counts only, NO returns)",
        "status": "NO_EVENT_TABLE",
        "note": "Phase-1 acquisition hit a read-only access wall; no event panel available. "
                "The harness below computes the intersection the moment a (ticker, level, "
                "start_date, end_date, announce_ts, is_escalation) table is supplied via --events.",
        "read_only_access_routes_probed": [{"route": r, "result": s} for r, s in ACCESS_STATUS],
        "denominators_ready": {
            "survivorship_clean_panel": PRICES.exists(),
            "pit_membership": PIT.exists(),
            "investable_list": CONFIG.exists(),
        },
    }, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, default=DEFAULT_EVENTS,
                    help="measure-event table (parquet/csv); counts only, no returns")
    args = ap.parse_args()

    if not args.events.exists():
        print_access_status()
        return 0

    import pandas as pd
    if args.events.suffix == ".csv":
        ev = pd.read_csv(args.events)
    else:
        ev = pd.read_parquet(args.events)
    ev.columns = [c.lower() for c in ev.columns]
    ev["ticker"] = ev["ticker"].astype(str).str.strip().str.upper()
    ev["event_date"] = pd.to_datetime(ev["start_date"]).dt.date

    investable = load_investable(CONFIG)
    pit_idx = load_pit_index(PIT)
    import pyarrow.parquet as pq
    panel_syms = {s.upper() for s in pq.read_table(PRICES, columns=["symbol"])["symbol"].to_pylist()}

    per_level = defaultdict(Counter)
    per_year = Counter()
    overall = Counter()
    investable_hits = Counter()
    distinct = set()

    for row in ev.itertuples(index=False):
        lvl = int(row.level)
        d = row.event_date
        sym = row.ticker
        distinct.add(sym)
        per_year[d.year] += 1
        flags = membership_as_of(pit_idx, sym, d)
        cls = classify(flags, sym in panel_syms, sym in investable)
        per_level[lvl][cls] += 1
        overall[cls] += 1
        if sym in investable:
            investable_hits[lvl] += 1

    out = {
        "id": "RR-Y1-019 VBTS measure-event universe intersection (counts only, NO returns)",
        "class": "Phase-1 feasibility; NO return measurement; PIT membership as-of event date",
        "events_table": str(args.events),
        "total_events": int(len(ev)),
        "distinct_tickers": len(distinct),
        "per_year": dict(sorted(per_year.items())),
        "intersection_overall": dict(overall),
        "intersection_by_level": {str(k): dict(v) for k, v in sorted(per_level.items())},
        "investable_list_hits_by_level": {str(k): int(v) for k, v in sorted(investable_hits.items())},
        "investable_list_size": len(investable),
        "caveats": [
            "Counts only — no returns / CAR / price reaction examined (Phase-2 scope).",
            "Membership classified PIT as-of the event date (last panel day <= start_date).",
            "Investable denominator is today's static config list; intra-span change not modelled.",
            "BIST50 not available in the PIT panel; classification is BIST30 / BIST100(>30) / outside.",
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
