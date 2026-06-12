"""RR-Y1-016 descriptive buy-vs-sell post-disclosure asymmetry on the X1 look-half.

DIAGNOSTIC ONLY. Computes market-relative (vs XU100) post-disclosure returns for
buy-side and sell-side KAP insider disclosure events, restricted to the FROZEN X1
look-half (see docs/research/RR-Y1-016-CONJUGATE-SPLIT-FREEZE.json). Sell-side is
diagnostic-only under the long-only/no-short invariant; this never emits a trade
signal or a keep-bar verdict. Output is a decision-input, NOT a verdict.

Event definition (symmetric, controls the buy/sell event-definition asymmetry):
one event per disclosure that reports >=1 transaction of that side. Entry is the
look-ahead-safe signal date = max(published_at) over {the disclosure} U {its
corrections} (correction-aware), then t+1 (first trading day strictly after);
exit is `horizon` trading days after entry. Identical timing to the buy-side
return harness (IS-1). Per-series trading-day offsets are used for both the stock
and the benchmark (a documented minor approximation for a descriptive diagnostic).

Provenance: fresh KAP scrape (run-2, post-UTF-8, 2026-06-12), NOT the canonical
panel. Run with the ingest service's venv python (has asyncpg):
    .venv/Scripts/python.exe scripts/probe/rr_y1_016_x1_asymmetry.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import date

import asyncpg

DSN = dict(user="flowuser", password="flowpass", host="localhost", port=5432, database="flow_intel")
HORIZONS = [5, 10, 21, 42, 63]
BENCHMARK = "XU100"
ENTRY_OFFSET = 1  # t+1: first trading day strictly after the public-disclosure day
FROZEN_RULE_SHA256 = "240514c3110b8d9322545d33655a7cd82a5bb14bcf0f841336ad58e3157ab41e"


def in_x1(ticker: str) -> bool:
    """Frozen, data-independent look-half rule (see the freeze JSON)."""
    h = hashlib.sha256(ticker.strip().upper().encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 2 == 0


async def nth_close(conn, ticker: str, after: date, n: int) -> float | None:
    """Close on the n-th trading day strictly after `after` (n>=1). OFFSET n-1."""
    row = await conn.fetchval(
        "SELECT close_try FROM price_history WHERE ticker=$1 AND price_date > $2 "
        "ORDER BY price_date ASC OFFSET $3 LIMIT 1",
        ticker, after, n - 1,
    )
    return float(row) if row is not None else None


async def signal_date(conn, disclosure_id: int) -> date | None:
    """Look-ahead-safe signal date: max published_at over the disclosure + its corrections."""
    ts = await conn.fetchval(
        "SELECT max(published_at) FROM kap_disclosures WHERE id=$1 OR corrects_disclosure_id=$1",
        disclosure_id,
    )
    return ts.date() if ts is not None else None


def _agg(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0, "hit_rate_pct": None, "median_pct": None, "mean_pct": None}
    hits = sum(1 for v in vals if v > 0)
    return {
        "n": len(vals),
        "hit_rate_pct": round(hits / len(vals) * 100, 2),
        "median_pct": round(statistics.median(vals), 4),
        "mean_pct": round(statistics.fmean(vals), 4),
    }


async def main() -> None:
    conn = await asyncpg.connect(**DSN)
    try:
        disclosures = await conn.fetch(
            "SELECT id, ticker, published_at FROM kap_disclosures WHERE published_at IS NOT NULL"
        )
        side_rows = await conn.fetch(
            "SELECT DISTINCT disclosure_id, transaction_type FROM kap_insider_transactions"
        )
        sides: dict[int, set] = defaultdict(set)
        for r in side_rows:
            sides[r["disclosure_id"]].add(r["transaction_type"])

        active: dict[str, dict[int, list[float]]] = {
            "BUY": defaultdict(list), "SELL": defaultdict(list)
        }
        events = {"BUY": 0, "SELL": 0}
        skipped: dict[str, int] = defaultdict(int)
        x1_tickers, x2_tickers = set(), set()

        for d in disclosures:
            ticker = d["ticker"]
            (x1_tickers if in_x1(ticker) else x2_tickers).add(ticker)
            if not in_x1(ticker):
                continue  # X2 sealed: never examined
            sd = await signal_date(conn, d["id"])
            if sd is None:
                skipped["no_signal_date"] += 1
                continue
            for side in ("BUY", "SELL"):
                if side not in sides.get(d["id"], ()):
                    continue
                events[side] += 1
                s_entry = await nth_close(conn, ticker, sd, ENTRY_OFFSET)
                b_entry = await nth_close(conn, BENCHMARK, sd, ENTRY_OFFSET)
                if not s_entry or not b_entry:
                    skipped[f"{side}_no_entry_price"] += 1
                    continue
                for h in HORIZONS:
                    s_exit = await nth_close(conn, ticker, sd, ENTRY_OFFSET + h)
                    b_exit = await nth_close(conn, BENCHMARK, sd, ENTRY_OFFSET + h)
                    if not s_exit or not b_exit:
                        continue
                    stock_ret = (s_exit / s_entry - 1.0) * 100.0
                    bench_ret = (b_exit / b_entry - 1.0) * 100.0
                    active[side][h].append(stock_ret - bench_ret)

        out = {
            "id": "RR-Y1-016 X1 descriptive buy-vs-sell asymmetry",
            "class": "diagnostic-only; market-relative; NOT a verdict (decision-input)",
            "provenance": "fresh KAP scrape run-2 (post-UTF-8, 2026-06-12); NOT the canonical panel",
            "split": "X1 look-half only (frozen); X2 sealed and untouched",
            "frozen_rule_sha256": FROZEN_RULE_SHA256,
            "benchmark": f"{BENCHMARK} (market-relative active return)",
            "entry": "look-ahead-safe signal date (max published_at, correction-aware) + t+1",
            "horizons_trading_days": HORIZONS,
            "x1_distinct_tickers": len(x1_tickers),
            "x2_distinct_tickers_sealed": len(x2_tickers),
            "buy_events_x1": events["BUY"],
            "sell_events_x1": events["SELL"],
            "skipped": dict(skipped),
            "buy_side": {h: _agg(active["BUY"][h]) for h in HORIZONS},
            "sell_side": {h: _agg(active["SELL"][h]) for h in HORIZONS},
            "caveats": [
                "Per-disclosure events both sides (symmetric); buy-side TRADING signal uses multi-insider clusters, not modelled here.",
                "Per-series trading-day offsets for stock vs benchmark (minor alignment approximation).",
                "Market-relative vs XU100 price index (not total-return); descriptive only.",
                "Sell-side is diagnostic-only (long-only invariant), never a trade candidate.",
            ],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
