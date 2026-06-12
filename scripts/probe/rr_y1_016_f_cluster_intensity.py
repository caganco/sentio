"""RR-Y1-016-F cluster-intensity power prior (counts only; NO returns).

DIAGNOSTIC POWER CHECK. Stage-0-NOT, not a hypothesis test, not an edge test.
Single question: does the cluster-intensity axis have enough high-intensity
coordinated-buy mass to support a future frozen Stage-0? X1 look-half only, X2
sealed/untouched, no new data, fresh-scrape lineage.

CRITICAL: this script DOES NOT look at returns. Looking at the cluster-return
relationship before a frozen Stage-0 pre-registration would be peeking at the
signal (DEC-053). Power first, returns later (a separate, cold-headed decision).

Cluster definition follows the project's own config (config/base.yaml):
window_days=30, a cluster = >=2 distinct insiders BUYing the same ticker within a
30-day window (the Seyhun-type net-insider-pressure / cluster_score metric).
Intensity = number of distinct insiders in the window.

Output: distribution of cluster intensity over X1 BUY events (per-window events,
deduped) and per-ticker maxima, distinct high-intensity names, and breakdown by
year and liquidity tertile (liquidity is a characteristic, not a return).

Run with the ingest venv: .venv/Scripts/python.exe scripts/probe/rr_y1_016_f_cluster_intensity.py
"""
from __future__ import annotations

import asyncio
import bisect
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from datetime import timedelta

import asyncpg

DSN = dict(user="flowuser", password="flowpass", host="localhost", port=5432, database="flow_intel")
WINDOW_DAYS = 30          # config/base.yaml signals.cluster.window_days
PROJECT_MIN_COUNT = 2     # config/base.yaml signals.cluster.min_insider_count
FROZEN_RULE_SHA256 = "240514c3110b8d9322545d33655a7cd82a5bb14bcf0f841336ad58e3157ab41e"


def in_x1(ticker: str) -> bool:
    h = hashlib.sha256(ticker.strip().upper().encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 2 == 0


def _window_events(txs):
    """Replicate flow_intel _find_cluster_events with min_count=1 (full distribution).

    txs: list of (insider_name, transaction_date) sorted by date. Returns deduped
    (window_start, window_end, distinct_insider_count) per unique window key.
    """
    dates = [d for _, d in txs]
    events = []
    seen = set()
    for _, d in txs:
        lo = d - timedelta(days=WINDOW_DAYS)
        i0 = bisect.bisect_left(dates, lo)
        i1 = bisect.bisect_right(dates, d)
        win = txs[i0:i1]
        names = {nm for nm, _ in win}
        ws = win[0][1]
        key = (ws, d)
        if key in seen:
            continue
        seen.add(key)
        events.append((ws, d, len(names)))
    return events


async def main() -> None:
    conn = await asyncpg.connect(**DSN)
    try:
        rows = await conn.fetch(
            "SELECT ticker, insider_name, transaction_date FROM kap_insider_transactions "
            "WHERE transaction_type='BUY' ORDER BY ticker, transaction_date"
        )
        by_ticker = defaultdict(list)
        for r in rows:
            if in_x1(r["ticker"]):
                by_ticker[r["ticker"]].append((r["insider_name"], r["transaction_date"]))

        # liquidity characteristic (NOT a return): median close*volume per ticker
        prows = await conn.fetch(
            "SELECT ticker, close_try, volume FROM price_history"
        )
        dv = defaultdict(list)
        for r in prows:
            if r["close_try"] is not None and r["volume"] is not None:
                dv[r["ticker"]].append(float(r["close_try"]) * float(r["volume"]))
        liq = {t: statistics.median(v) for t, v in dv.items() if v}

        # per-ticker max intensity + all window events
        max_intensity = {}
        all_events = []          # (ticker, window_end, intensity)
        for t, txs in by_ticker.items():
            evs = _window_events(txs)
            max_intensity[t] = max((c for _, _, c in evs), default=0)
            for _ws, we, c in evs:
                all_events.append((t, we, c))

        def names_ge(k):
            return sorted(t for t, m in max_intensity.items() if m >= k)

        def events_ge(k):
            return [e for e in all_events if e[2] >= k]

        # per-ticker-max histogram
        max_hist = Counter(max_intensity.values())
        # per-window-event intensity histogram
        ev_hist = Counter(c for _, _, c in all_events)

        # merged episodes per ticker at >=3 (collapse overlapping >=3 windows)
        def episodes_ge(k):
            eps_n = 0
            eps_tickers = set()
            for t, txs in by_ticker.items():
                hot = sorted(we for _, we, c in [(t, we, c) for _ws, we, c in _window_events(txs)] if c >= k)
                if not hot:
                    continue
                eps_tickers.add(t)
                last = None
                for d in hot:
                    if last is None or (d - last).days > WINDOW_DAYS:
                        eps_n += 1
                    last = d
            return eps_n, len(eps_tickers)

        out = {
            "id": "RR-Y1-016-F cluster-intensity power prior (counts only, NO returns)",
            "class": "diagnostic power-check; Stage-0-NOT; NO return measurement (DEC-053-safe)",
            "provenance": "fresh KAP scrape run-2 (2026-06-12); NOT the canonical panel",
            "split": "X1 look-half only (frozen, same as 016-C/D/E); X2 sealed/untouched",
            "frozen_rule_sha256": FROZEN_RULE_SHA256,
            "cluster_def": f"window_days={WINDOW_DAYS}, distinct insiders BUYing same ticker in window "
                           f"(project min_insider_count={PROJECT_MIN_COUNT}); intensity = distinct insiders",
            "x1_buy_tickers": len(by_ticker),
            "x1_buy_transactions": sum(len(v) for v in by_ticker.values()),
            "per_ticker_max_intensity_hist": {str(k): max_hist.get(k, 0) for k in sorted(max_hist)},
            "per_window_event_intensity_hist": {str(k): ev_hist.get(k, 0) for k in sorted(ev_hist)},
            "high_intensity_summary": {},
            "by_year_ge3": {},
            "by_liquidity_tertile_ge3": {},
        }

        for k in (2, 3, 4):
            ng = names_ge(k)
            eg = events_ge(k)
            ep_n, ep_t = episodes_ge(k)
            out["high_intensity_summary"][f">={k}_insiders"] = {
                "distinct_names": len(ng),
                "window_events": len(eg),
                "merged_episodes": ep_n,
                "episode_names": ep_t,
                "names": ng if len(ng) <= 25 else ng[:25] + ["..."],
            }

        # by year (window_end year) for >=3 events
        yr = Counter(we.year for _, we, c in all_events if c >= 3)
        out["by_year_ge3"] = {str(y): yr[y] for y in sorted(yr)}

        # by liquidity tertile for >=3 NAMES
        ge3_names = names_ge(3)
        liq_vals = sorted((liq[t] for t in liq), )
        if liq_vals and ge3_names:
            t1 = liq_vals[len(liq_vals) // 3]
            t2 = liq_vals[2 * len(liq_vals) // 3]
            tert = {"low": 0, "mid": 0, "high": 0, "no_liq": 0}
            for t in ge3_names:
                if t not in liq:
                    tert["no_liq"] += 1
                elif liq[t] <= t1:
                    tert["low"] += 1
                elif liq[t] <= t2:
                    tert["mid"] += 1
                else:
                    tert["high"] += 1
            out["by_liquidity_tertile_ge3"] = tert

        out["caveats"] = [
            "COUNTS ONLY -- no returns examined (DEC-053-safe; power before returns).",
            "Cluster = project config (30d window, >=2 distinct insiders).",
            "'distinct insiders' = distinct insider_name; may include related parties (upper bound on independence).",
            "Window-events over-count overlapping windows; 'merged_episodes' and 'distinct_names' are the robust counts.",
            "X1 only; fresh-scrape lineage; X2 sealed.",
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
