"""RR-Y1-016-D confound control for the X1 sell-side post-disclosure drift.

DIAGNOSTIC ONLY. Stage-0-NOT, no keep-bar, no verdict. Decision-input. Uses the
SAME frozen ticker-split as RR-Y1-016-C (sha256 of ticker; X1 look-half only,
X2 sealed and never touched). Provenance: fresh KAP scrape lineage, NOT the
canonical panel.

Question: is the X1 sell-side negative drift (i) a real insider-direction signal,
(ii-a) a universe-selection confound, or (ii-b) a name-fixed confound?

Layer A (within-universe): three X1 groups -- sell-flagged, buy-flagged, and a
no-disclosure control (same universe, pseudo-events on dates with no insider
disclosure in the window). Primary comparison is the RAW within-universe drift of
sell vs non-sell (buy+control), NOT XU100-relative (market-relative is reported
only for comparison). Plus a size/liquidity-adjusted (decile-stratified) version.

Layer B (placebo): for the sell-flagged names, real sell events vs random
non-disclosure dates of the same names. If the sell drift does not separate from
the same names' placebo drift, the drift is name-fixed, not event-bound.

Stats: permutation-p (primary; small N + fat tails) + bootstrap CI. Event grain
is per-disclosure for every group (apples-to-apples; controls the buy=cluster vs
sell=event definition asymmetry flagged in RR-Y1-016-B).

Entry is look-ahead-safe: published_at + t+1 (correction-aware) for real events;
the pseudo-event date + t+1 for control/placebo. Run with the ingest venv:
    .venv/Scripts/python.exe scripts/probe/rr_y1_016_d_confound.py
"""
from __future__ import annotations

import asyncio
import bisect
import hashlib
import json
import random
import statistics
from collections import defaultdict
from datetime import date

import asyncpg

DSN = dict(user="flowuser", password="flowpass", host="localhost", port=5432, database="flow_intel")
HORIZONS = [21, 42, 63]
BENCHMARK = "XU100"
SEED = 42
N_PERM = 10000
N_BOOT = 10000
CONTROL_PER_TICKER = 3
PLACEBO_PER_TICKER = 3
EXCLUDE_DAYS = 90  # calendar days around any disclosure -> not a clean control/placebo date
FROZEN_RULE_SHA256 = "240514c3110b8d9322545d33655a7cd82a5bb14bcf0f841336ad58e3157ab41e"


def in_x1(ticker: str) -> bool:
    h = hashlib.sha256(ticker.strip().upper().encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 2 == 0


def _ret(series, ref: date, h: int) -> float | None:
    """Raw % return from t+1 (first trading day after ref) to t+1+h. series=(dates,closes)."""
    dates, closes = series
    i = bisect.bisect_right(dates, ref)  # first index strictly after ref == t+1
    if i >= len(dates) or i + h >= len(dates):
        return None
    e, x = closes[i], closes[i + h]
    if e is None or x is None or e <= 0:
        return None
    return (x / e - 1.0) * 100.0


def _mean(a):
    return statistics.fmean(a) if a else None


def _median(a):
    return statistics.median(a) if a else None


def _perm_p(a, b, rng, stat=statistics.fmean):
    """Two-sided permutation p for stat(a)-stat(b). stat=mean or median."""
    if len(a) < 2 or len(b) < 2:
        return None
    obs = abs(stat(a) - stat(b))
    pool = a + b
    n = len(a)
    ge = 0
    for _ in range(N_PERM):
        rng.shuffle(pool)
        d = abs(stat(pool[:n]) - stat(pool[n:]))
        if d >= obs - 1e-12:
            ge += 1
    return round((ge + 1) / (N_PERM + 1), 4)


def _boot_ci(a, b, rng):
    """95% bootstrap CI for mean(a)-mean(b)."""
    if len(a) < 2 or len(b) < 2:
        return None
    diffs = []
    for _ in range(N_BOOT):
        ra = [a[rng.randrange(len(a))] for _ in range(len(a))]
        rb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        diffs.append(statistics.fmean(ra) - statistics.fmean(rb))
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs))]
    return [round(lo, 4), round(hi, 4)]


def _strat_adjusted_diff(sell_by_dec, nonsell_by_dec):
    """Liquidity-decile-stratified sell-vs-nonsell mean diff (event-weighted over shared deciles)."""
    num = den = 0.0
    used = 0
    for d in range(10):
        s, ns = sell_by_dec.get(d, []), nonsell_by_dec.get(d, [])
        if len(s) >= 2 and len(ns) >= 2:
            w = len(s)
            num += w * (statistics.fmean(s) - statistics.fmean(ns))
            den += w
            used += 1
    if den == 0:
        return None, 0
    return round(num / den, 4), used


async def main() -> None:
    rng = random.Random(SEED)
    conn = await asyncpg.connect(**DSN)
    try:
        # ---- load prices into memory: ticker -> (sorted dates, closes), + liquidity ----
        prows = await conn.fetch(
            "SELECT ticker, price_date, close_try, volume FROM price_history ORDER BY ticker, price_date"
        )
        px = defaultdict(lambda: ([], []))
        dollarvol = defaultdict(list)
        for r in prows:
            d, c, v = r["price_date"], r["close_try"], r["volume"]
            px[r["ticker"]][0].append(d)
            px[r["ticker"]][1].append(float(c) if c is not None else None)
            if c is not None and v is not None:
                dollarvol[r["ticker"]].append(float(c) * float(v))
        liq = {t: statistics.median(vs) for t, vs in dollarvol.items() if vs}

        # ---- disclosures -> per-disclosure events (X1), signal_date, sides ----
        disc = await conn.fetch(
            "SELECT id, ticker, published_at FROM kap_disclosures WHERE published_at IS NOT NULL"
        )
        side_rows = await conn.fetch(
            "SELECT DISTINCT disclosure_id, transaction_type FROM kap_insider_transactions"
        )
        sides = defaultdict(set)
        for r in side_rows:
            sides[r["disclosure_id"]].add(r["transaction_type"])
        # correction-aware signal date per disclosure
        corr = await conn.fetch(
            "SELECT id, corrects_disclosure_id, published_at FROM kap_disclosures WHERE published_at IS NOT NULL"
        )
        corrections = defaultdict(list)
        pub = {}
        for r in corr:
            pub[r["id"]] = r["published_at"]
            if r["corrects_disclosure_id"] is not None:
                corrections[r["corrects_disclosure_id"]].append(r["published_at"])

        def signal_date(did, base):
            cands = [base] + corrections.get(did, [])
            return max(cands).date()

        sell_events, buy_events = [], []          # (ticker, signal_date)
        disc_dates = defaultdict(list)            # ticker -> [disclosure dates] for exclusion
        for r in disc:
            t = r["ticker"]
            sd = signal_date(r["id"], r["published_at"])
            disc_dates[t].append(sd)
            if not in_x1(t):
                continue
            s = sides.get(r["id"], set())
            if "SELL" in s:
                sell_events.append((t, sd))
            if "BUY" in s:
                buy_events.append((t, sd))

        # ---- control + placebo pseudo-events on no-disclosure dates ----
        def clean_dates(ticker, k):
            if ticker not in px:
                return []
            dts = px[ticker][0]
            dd = disc_dates.get(ticker, [])
            elig = []
            for d in dts:
                if any(abs((d - x).days) <= EXCLUDE_DAYS for x in dd):
                    continue
                i = bisect.bisect_right(dts, d)
                if i + max(HORIZONS) >= len(dts):  # need future bars for exit
                    continue
                elig.append(d)
            if len(elig) <= k:
                return elig
            return rng.sample(elig, k)

        x1_tickers = sorted({t for t, _ in sell_events} | {t for t, _ in buy_events}
                            | {t for t in px if in_x1(t)})
        control_events = [(t, d) for t in x1_tickers for d in clean_dates(t, CONTROL_PER_TICKER)]
        sell_tickers = sorted({t for t, _ in sell_events})
        placebo_events = [(t, d) for t in sell_tickers for d in clean_dates(t, PLACEBO_PER_TICKER)]

        # ---- liquidity deciles over the involved tickers ----
        involved = sorted({t for t, _ in sell_events + buy_events + control_events if t in liq},
                          key=lambda t: liq[t])
        dec_of = {}
        n = len(involved)
        for idx, t in enumerate(involved):
            dec_of[t] = min(9, int(idx * 10 / n)) if n else 0

        def returns(events, h, market_rel=False):
            out = []
            xu = px.get(BENCHMARK)
            for t, d in events:
                if t not in px:
                    continue
                r = _ret(px[t], d, h)
                if r is None:
                    continue
                if market_rel:
                    if xu is None:
                        continue
                    b = _ret(xu, d, h)
                    if b is None:
                        continue
                    r = r - b
                out.append((t, r))
            return out

        out = {
            "id": "RR-Y1-016-D X1 sell-side confound control",
            "class": "diagnostic-only; Stage-0-NOT; no verdict (decision-input)",
            "provenance": "fresh KAP scrape run-2 (2026-06-12); NOT the canonical panel",
            "split": "X1 look-half only (frozen, same as RR-Y1-016-C); X2 sealed/untouched",
            "frozen_rule_sha256": FROZEN_RULE_SHA256,
            "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT,
            "exclude_days_around_disclosure": EXCLUDE_DAYS,
            "group_counts": {
                "sell_events": len(sell_events), "buy_events": len(buy_events),
                "control_events": len(control_events), "placebo_events": len(placebo_events),
                "sell_tickers": len(sell_tickers), "x1_tickers": len(x1_tickers),
            },
            "layer_A_within_universe": {}, "layer_A_market_relative_ref": {},
            "layer_B_placebo": {}, "diagnosis": {},
        }

        for h in HORIZONS:
            sell_r = returns(sell_events, h)
            buy_r = returns(buy_events, h)
            ctrl_r = returns(control_events, h)
            sell_v = [r for _, r in sell_r]
            nonsell_v = [r for _, r in buy_r] + [r for _, r in ctrl_r]

            # raw within-universe
            raw_diff = (statistics.fmean(sell_v) - statistics.fmean(nonsell_v)) if sell_v and nonsell_v else None
            perm_p = _perm_p(sell_v, nonsell_v, rng)
            perm_p_med = _perm_p(sell_v, nonsell_v, rng, statistics.median)
            ci = _boot_ci(sell_v, nonsell_v, rng)

            # size/liquidity-adjusted (decile-stratified)
            sell_by_dec, nonsell_by_dec = defaultdict(list), defaultdict(list)
            for t, r in sell_r:
                if t in dec_of:
                    sell_by_dec[dec_of[t]].append(r)
            for t, r in buy_r + ctrl_r:
                if t in dec_of:
                    nonsell_by_dec[dec_of[t]].append(r)
            adj_diff, dec_used = _strat_adjusted_diff(sell_by_dec, nonsell_by_dec)

            out["layer_A_within_universe"][h] = {
                "n_sell": len(sell_v), "n_nonsell": len(nonsell_v),
                "sell_mean": round(_mean(sell_v), 4) if sell_v else None,
                "sell_median": round(_median(sell_v), 4) if sell_v else None,
                "nonsell_mean": round(_mean(nonsell_v), 4) if nonsell_v else None,
                "nonsell_median": round(_median(nonsell_v), 4) if nonsell_v else None,
                "raw_diff_sell_minus_nonsell": round(raw_diff, 4) if raw_diff is not None else None,
                "perm_p_mean": perm_p, "perm_p_median": perm_p_med, "boot_ci95": ci,
                "size_liq_adjusted_diff": adj_diff, "deciles_used": dec_used,
            }

            # market-relative reference
            sell_m = [r for _, r in returns(sell_events, h, True)]
            nonsell_m = [r for _, r in returns(buy_events, h, True)] + [r for _, r in returns(control_events, h, True)]
            out["layer_A_market_relative_ref"][h] = {
                "sell_median_mktrel": round(_median(sell_m), 4) if sell_m else None,
                "nonsell_median_mktrel": round(_median(nonsell_m), 4) if nonsell_m else None,
            }

            # Layer B placebo (same sell names)
            plac_v = [r for _, r in returns(placebo_events, h)]
            b_diff = (statistics.fmean(sell_v) - statistics.fmean(plac_v)) if sell_v and plac_v else None
            out["layer_B_placebo"][h] = {
                "n_sell": len(sell_v), "n_placebo": len(plac_v),
                "sell_mean": round(_mean(sell_v), 4) if sell_v else None,
                "placebo_mean": round(_mean(plac_v), 4) if plac_v else None,
                "placebo_median": round(_median(plac_v), 4) if plac_v else None,
                "diff_sell_minus_placebo": round(b_diff, 4) if b_diff is not None else None,
                "perm_p_mean": _perm_p(sell_v, plac_v, rng),
                "perm_p_median": _perm_p(sell_v, plac_v, rng, statistics.median),
                "boot_ci95": _boot_ci(sell_v, plac_v, rng),
            }

            # per-horizon diagnosis
            a = out["layer_A_within_universe"][h]
            b = out["layer_B_placebo"][h]
            # Diagnosis keyed to the robust (median) permutation given fat-tailed returns.
            a_sig = a["perm_p_median"] is not None and a["perm_p_median"] < 0.05 and (a["raw_diff_sell_minus_nonsell"] or 0) < 0
            b_sig = b["perm_p_median"] is not None and b["perm_p_median"] < 0.05 and (b["diff_sell_minus_placebo"] or 0) < 0
            if a_sig and b_sig:
                dx = "(i) real event-bound sell asymmetry"
            elif not a_sig:
                dx = "(ii-a) universe-confound (sell not separated from within-universe non-sell)"
            elif a_sig and not b_sig:
                dx = "(ii-b) name-fixed confound (separated from universe but not from own placebo)"
            else:
                dx = "mixed"
            out["diagnosis"][h] = {"a_significant": a_sig, "b_significant": b_sig, "call": dx}

        out["caveats"] = [
            "Within-universe RAW drift is primary; market-relative is reference-only.",
            "Per-disclosure event grain for ALL groups (controls buy=cluster vs sell=event def asymmetry).",
            "Control/placebo = pseudo-events on dates >90d from any disclosure of that ticker.",
            "Size/liquidity adjustment = liquidity-decile-stratified diff (thin cells dropped).",
            "Permutation-p primary (small N + fat tails); bootstrap CI on mean diff. seed=42.",
            "Fresh-scrape lineage, NOT canonical panel. Sell-side diagnostic-only (long-only).",
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
