"""RR-Y1-016-E confound re-run with a CLEAN baseline (audit remediation).

DIAGNOSTIC ONLY. Stage-0-NOT, no keep-bar, no verdict. Same frozen ticker-split
as RR-Y1-016-C/D (X1 look-half only; X2 sealed/untouched). No new data. Fresh-
scrape lineage, NOT the canonical panel.

Audit finding (D5): RR-Y1-016-D Layer A used "non-sell" = buy-flagged + control as
the baseline, but buy-flagged names themselves drifted negative (RR-Y1-016-C), so
the baseline was contaminated -> the sell-vs-non-sell difference was pulled toward
zero (null), which may have driven the confound verdict.

Remediation: re-run Layer A as THREE separate comparisons, each with raw +
liquidity-decile-stratified difference, permutation-p (mean+median) and a
stratified permutation-p for the adjusted diff, plus bootstrap CI:
  C1  sell vs no-disclosure-control ONLY   (clean baseline; PRIMARY)
  C2  sell vs buy-flagged                   (comparison)
  C3  buy  vs no-disclosure-control ONLY    (independent: how far buy itself drifts)
Layer B placebo (sell vs same-names random dates) is baseline-independent; it is
re-reported unchanged as reference.

PRE-FROZEN decision logic (no post-hoc loosening):
  - C1 (clean baseline, size/liquidity-adjusted) still NS  -> confound result
    SOLIDIFIED; insider buy/sell axis fully closed (save/wait reinforced).
  - C1 significant (sell deviates negative from clean baseline after size/liq)
    -> confound verdict CHALLENGED; sell-side becomes a live question again and
    growing N gains value.

Run with the ingest venv: .venv/Scripts/python.exe scripts/probe/rr_y1_016_e_baseline.py
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
EXCLUDE_DAYS = 90
FROZEN_RULE_SHA256 = "240514c3110b8d9322545d33655a7cd82a5bb14bcf0f841336ad58e3157ab41e"
DECISION_RULE_PREFROZEN = (
    "PRIMARY = C1 (sell vs no-disclosure-control-only), size/liquidity-adjusted. "
    "C1 still NS -> confound SOLIDIFIED, axis fully closed. "
    "C1 significant (sell negative-deviates after size/liq) -> confound CHALLENGED, sell-side live again."
)


def in_x1(ticker: str) -> bool:
    h = hashlib.sha256(ticker.strip().upper().encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 2 == 0


def _ret(series, ref: date, h: int) -> float | None:
    dates, closes = series
    i = bisect.bisect_right(dates, ref)
    if i >= len(dates) or i + h >= len(dates):
        return None
    e, x = closes[i], closes[i + h]
    if e is None or x is None or e <= 0:
        return None
    return (x / e - 1.0) * 100.0


def _perm_p(a, b, rng, stat=statistics.fmean):
    if len(a) < 2 or len(b) < 2:
        return None
    obs = abs(stat(a) - stat(b))
    pool = a + b
    n = len(a)
    ge = 0
    for _ in range(N_PERM):
        rng.shuffle(pool)
        if abs(stat(pool[:n]) - stat(pool[n:])) >= obs - 1e-12:
            ge += 1
    return round((ge + 1) / (N_PERM + 1), 4)


def _boot_ci(a, b, rng):
    if len(a) < 2 or len(b) < 2:
        return None
    diffs = []
    for _ in range(N_BOOT):
        ra = [a[rng.randrange(len(a))] for _ in range(len(a))]
        rb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        diffs.append(statistics.fmean(ra) - statistics.fmean(rb))
    diffs.sort()
    return [round(diffs[int(0.025 * len(diffs))], 4), round(diffs[int(0.975 * len(diffs))], 4)]


def _strat_diff(a_by_dec, b_by_dec):
    """Liquidity-decile-stratified mean diff (event-weighted over shared deciles)."""
    num = den = 0.0
    used = 0
    for d in range(10):
        a, b = a_by_dec.get(d, []), b_by_dec.get(d, [])
        if len(a) >= 2 and len(b) >= 2:
            w = len(a)
            num += w * (statistics.fmean(a) - statistics.fmean(b))
            den += w
            used += 1
    if den == 0:
        return None, 0
    return num / den, used


def _strat_perm_p(a_by_dec, b_by_dec, rng):
    """Stratified permutation p: shuffle labels WITHIN each decile."""
    obs, used = _strat_diff(a_by_dec, b_by_dec)
    if obs is None or used == 0:
        return None
    obs = abs(obs)
    decs = [d for d in range(10) if len(a_by_dec.get(d, [])) >= 2 and len(b_by_dec.get(d, [])) >= 2]
    pools = {d: (a_by_dec[d] + b_by_dec[d], len(a_by_dec[d])) for d in decs}
    ge = 0
    for _ in range(N_PERM):
        num = den = 0.0
        for d in decs:
            pool, na = pools[d]
            rng.shuffle(pool)
            num += na * (statistics.fmean(pool[:na]) - statistics.fmean(pool[na:]))
            den += na
        if abs(num / den) >= obs - 1e-12:
            ge += 1
    return round((ge + 1) / (N_PERM + 1), 4)


def _block(a_r, b_r, dec_of, rng):
    """Full comparison stats for group A vs group B; *_r are [(ticker, ret)]."""
    av = [r for _, r in a_r]
    bv = [r for _, r in b_r]
    a_by, b_by = defaultdict(list), defaultdict(list)
    for t, r in a_r:
        if t in dec_of:
            a_by[dec_of[t]].append(r)
    for t, r in b_r:
        if t in dec_of:
            b_by[dec_of[t]].append(r)
    adj, used = _strat_diff(a_by, b_by)
    return {
        "n_a": len(av), "n_b": len(bv),
        "a_mean": round(statistics.fmean(av), 4) if av else None,
        "a_median": round(statistics.median(av), 4) if av else None,
        "b_mean": round(statistics.fmean(bv), 4) if bv else None,
        "b_median": round(statistics.median(bv), 4) if bv else None,
        "raw_diff_a_minus_b": round(statistics.fmean(av) - statistics.fmean(bv), 4) if av and bv else None,
        "perm_p_mean": _perm_p(av, bv, rng),
        "perm_p_median": _perm_p(av, bv, rng, statistics.median),
        "boot_ci95": _boot_ci(av, bv, rng),
        "size_liq_adjusted_diff": round(adj, 4) if adj is not None else None,
        "size_liq_adjusted_perm_p": _strat_perm_p(a_by, b_by, rng),
        "deciles_used": used,
    }


async def main() -> None:
    rng = random.Random(SEED)
    conn = await asyncpg.connect(**DSN)
    try:
        prows = await conn.fetch(
            "SELECT ticker, price_date, close_try, volume FROM price_history ORDER BY ticker, price_date"
        )
        px = defaultdict(lambda: ([], []))
        dollarvol = defaultdict(list)
        for r in prows:
            px[r["ticker"]][0].append(r["price_date"])
            px[r["ticker"]][1].append(float(r["close_try"]) if r["close_try"] is not None else None)
            if r["close_try"] is not None and r["volume"] is not None:
                dollarvol[r["ticker"]].append(float(r["close_try"]) * float(r["volume"]))
        liq = {t: statistics.median(vs) for t, vs in dollarvol.items() if vs}

        disc = await conn.fetch(
            "SELECT id, ticker, published_at FROM kap_disclosures WHERE published_at IS NOT NULL"
        )
        side_rows = await conn.fetch(
            "SELECT DISTINCT disclosure_id, transaction_type FROM kap_insider_transactions"
        )
        sides = defaultdict(set)
        for r in side_rows:
            sides[r["disclosure_id"]].add(r["transaction_type"])
        corrections = defaultdict(list)
        corr = await conn.fetch(
            "SELECT id, corrects_disclosure_id, published_at FROM kap_disclosures "
            "WHERE published_at IS NOT NULL AND corrects_disclosure_id IS NOT NULL"
        )
        for r in corr:
            corrections[r["corrects_disclosure_id"]].append(r["published_at"])

        def signal_date(did, base):
            return max([base] + corrections.get(did, [])).date()

        sell_events, buy_events = [], []
        disc_dates = defaultdict(list)
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
                if i + max(HORIZONS) >= len(dts):
                    continue
                elig.append(d)
            return elig if len(elig) <= k else rng.sample(elig, k)

        x1_tickers = sorted({t for t, _ in sell_events} | {t for t, _ in buy_events}
                            | {t for t in px if in_x1(t)})
        control_events = [(t, d) for t in x1_tickers for d in clean_dates(t, CONTROL_PER_TICKER)]
        sell_tickers = sorted({t for t, _ in sell_events})
        placebo_events = [(t, d) for t in sell_tickers for d in clean_dates(t, PLACEBO_PER_TICKER)]

        involved = sorted({t for t, _ in sell_events + buy_events + control_events if t in liq},
                          key=lambda t: liq[t])
        n = len(involved)
        dec_of = {t: (min(9, int(i * 10 / n)) if n else 0) for i, t in enumerate(involved)}

        def returns(events, h):
            out = []
            for t, d in events:
                if t not in px:
                    continue
                r = _ret(px[t], d, h)
                if r is not None:
                    out.append((t, r))
            return out

        out = {
            "id": "RR-Y1-016-E clean-baseline confound re-run (audit remediation)",
            "class": "diagnostic-only; Stage-0-NOT; no verdict (decision-input)",
            "provenance": "fresh KAP scrape run-2 (2026-06-12); NOT the canonical panel",
            "split": "X1 look-half only (frozen, same as 016-C/D); X2 sealed/untouched",
            "frozen_rule_sha256": FROZEN_RULE_SHA256,
            "audit_finding": "016-D baseline (buy+control) contaminated by buy-flagged negative drift; re-run with control-only clean baseline.",
            "decision_rule_prefrozen": DECISION_RULE_PREFROZEN,
            "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT,
            "group_counts": {
                "sell_events": len(sell_events), "buy_events": len(buy_events),
                "control_events": len(control_events), "placebo_events": len(placebo_events),
                "sell_tickers": len(sell_tickers), "x1_tickers": len(x1_tickers),
            },
            "C1_sell_vs_control_only_PRIMARY": {}, "C2_sell_vs_buy": {},
            "C3_buy_vs_control_only": {}, "layer_B_placebo_ref": {}, "decision": {},
        }

        for h in HORIZONS:
            sell_r = returns(sell_events, h)
            buy_r = returns(buy_events, h)
            ctrl_r = returns(control_events, h)
            plac_r = returns(placebo_events, h)

            c1 = _block(sell_r, ctrl_r, dec_of, rng)
            c2 = _block(sell_r, buy_r, dec_of, rng)
            c3 = _block(buy_r, ctrl_r, dec_of, rng)
            out["C1_sell_vs_control_only_PRIMARY"][h] = c1
            out["C2_sell_vs_buy"][h] = c2
            out["C3_buy_vs_control_only"][h] = c3

            sv = [r for _, r in sell_r]
            pv = [r for _, r in plac_r]
            out["layer_B_placebo_ref"][h] = {
                "n_sell": len(sv), "n_placebo": len(pv),
                "diff_sell_minus_placebo": round(statistics.fmean(sv) - statistics.fmean(pv), 4) if sv and pv else None,
                "perm_p_median": _perm_p(sv, pv, rng, statistics.median),
            }

            # pre-frozen decision on C1, size/liquidity-adjusted
            adj_p = c1["size_liq_adjusted_perm_p"]
            adj_d = c1["size_liq_adjusted_diff"]
            challenged = adj_p is not None and adj_p < 0.05 and (adj_d or 0) < 0
            out["decision"][h] = {
                "C1_adjusted_diff": adj_d, "C1_adjusted_perm_p": adj_p,
                "C1_raw_perm_p_median": c1["perm_p_median"],
                "call": "CHALLENGED (sell negative-deviates from clean baseline)" if challenged
                        else "SOLIDIFIED (confound; clean baseline still NS)",
            }

        any_ch = any(v["call"].startswith("CHALLENGED") for v in out["decision"].values())
        out["overall_call"] = (
            "CHALLENGED -> sell-side live again; growing N (016-B) gains value" if any_ch
            else "SOLIDIFIED -> confound confirmed on clean baseline; insider buy/sell axis fully closed (save/wait)"
        )
        out["caveats"] = [
            "C1 (sell vs no-disclosure-control-only) is the clean-baseline PRIMARY; C2/C3 are context.",
            "Decision keyed to C1 size/liquidity-adjusted stratified-permutation p (pre-frozen rule).",
            "Per-disclosure event grain for all groups; control/placebo = pseudo-events >90d from any disclosure.",
            "10k permutation (mean+median+stratified) + 10k bootstrap, seed=42. Fat-tail-robust median reported.",
            "Underpowered-null possible (modest N); fresh-scrape lineage; sell-side diagnostic-only (long-only).",
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
