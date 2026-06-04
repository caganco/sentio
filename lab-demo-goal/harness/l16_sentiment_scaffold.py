"""lab-demo-goal L16: NEWS-SENTIMENT factor FORWARD-SCAFFOLD (READ-ONLY, no network).

Stage-0: lab-demo-goal/stage0/STAGE0_L16_sentiment_scaffold.json (FROZEN before results).

The directive explicitly named SENTIMENT as a research target. The only sentiment/news data
present offline is a LIVE SNAPSHOT (data/news_cache.json) -- not a backtestable historical panel.
So, exactly like L11 (daily-PEAD), this track:
  (1) pre-registers + implements the look-ahead-safe cross-sectional sentiment test that WOULD run
      on a historical day-stamped news/sentiment panel,
  (2) OFFLINE-validates the pipeline on synthetic data (recovery / placebo / look-ahead-leak),
  (3) characterizes the REAL news_cache snapshot (descriptive) to quantify the data gap.
NO network, NO scraper, NO real-data edge claim.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l16_sentiment_scaffold.py
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L16_sentiment_scaffold.json"
OUT = LAB / "results" / "l16_sentiment_scaffold_results.json"
NEWS_SNAPSHOT = ROOT / "data" / "news_cache.json"
FORWARD_PANEL = ROOT / "data" / "cache" / "news_sentiment_daystamped.parquet"

H_WINDOWS = [5, 10]
SEED = 20260604
T_SIG = 2.0

POS_KW = ["geri al", "kar pay", "temettu", "kar dagit", "olumlu", "yukseltti", "yatirim tesvik", "uzun vadeli not"]
NEG_KW = ["sermaye art", "ihrac tavan", "bedelli", "devre kesici", "olumsuz", "dusurdu", "negatif",
          "temerrut", "konkordato", "halka arz"]

# Turkish-char -> ASCII fold, keyed by codepoint ordinal so this source file stays ASCII-clean.
_TR = {0x00E7: "c", 0x00C7: "c", 0x011F: "g", 0x011E: "g", 0x0131: "i",
       0x0130: "i", 0x00F6: "o", 0x00D6: "o", 0x015F: "s", 0x015E: "s",
       0x00FC: "u", 0x00DC: "u", 0x00E2: "a", 0x00EE: "i", 0x00FB: "u"}


def ascii_fold(s: str) -> str:
    return (s or "").translate(_TR).lower()


def polarity(title: str) -> int:
    t = ascii_fold(title)
    score = 0
    if any(k in t for k in POS_KW):
        score += 1
    if any(k in t for k in NEG_KW):
        score -= 1
    return score


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE results.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def nw_tstat(x: np.ndarray, lag: int) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean()
    e = x - mu
    var = (e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        var += 2.0 * w * (e[k:] @ e[:-k]) / n
    se = np.sqrt(max(var, 1e-18) / n)
    return float(mu / se) if se > 0 else float("nan")


def event_car_spread(events: pd.DataFrame, ret_wide: pd.DataFrame, H: int, leak: bool = False):
    """Per-event market-relative CAR over [+1,+H] (or [0,+H-1] if leaking); long(top-sentiment)-
    short(bottom) tercile spread + event-clustered NW-t. events: [symbol, t_idx, score]."""
    market = ret_wide.mean(axis=1).to_numpy()
    col = {s: j for j, s in enumerate(ret_wide.columns)}
    R = ret_wide.to_numpy()
    n_days = R.shape[0]
    off = 0 if leak else 1
    cars, scores = [], []
    for ev in events.itertuples():
        t = int(ev.t_idx)
        a, b = t + off, t + off + H
        if a < 0 or b > n_days:
            continue
        j = col.get(ev.symbol)
        if j is None:
            continue
        cars.append(float(np.nansum(R[a:b, j] - market[a:b])))
        scores.append(float(ev.score))
    if len(cars) < 9:
        return None
    df = pd.DataFrame({"car": cars, "score": scores}).sort_values("score")
    k = len(df) // 3
    top = df.iloc[-k:]["car"].to_numpy()
    bot = df.iloc[:k]["car"].to_numpy()
    contrib = np.concatenate([top, -bot])
    t_stat = nw_tstat(contrib, lag=H)
    return {"n_events": int(len(df)), "long_short_car": round(float(top.mean() - bot.mean()), 6),
            "nw_t": round(t_stat, 4) if t_stat == t_stat else None,
            "top_mean_car": round(float(top.mean()), 6), "bot_mean_car": round(float(bot.mean()), 6)}


def synthetic_self_validation() -> dict:
    rng = np.random.default_rng(SEED)
    n_sym, n_days, n_events = 60, 600, 480
    sigma_daily = 0.02
    drift_per_score = 0.020
    syms = [f"S{i:03d}" for i in range(n_sym)]
    R = rng.normal(0.0, sigma_daily, size=(n_days, n_sym))
    ev_sym = rng.integers(0, n_sym, size=n_events)
    ev_t = rng.integers(30, n_days - 30, size=n_events)
    ev_score = rng.normal(0.0, 1.0, size=n_events)
    H_plant = 10
    for s, t, sc in zip(ev_sym, ev_t, ev_score):
        R[t + 1: t + 1 + H_plant, s] += drift_per_score * sc / H_plant
        R[t, s] += 0.03 * np.sign(sc)
    ret_wide = pd.DataFrame(R, columns=syms)
    events = pd.DataFrame({"symbol": [syms[i] for i in ev_sym], "t_idx": ev_t, "score": ev_score})

    out = {"params": {"n_sym": n_sym, "n_days": n_days, "n_events": n_events,
                      "sigma_daily": sigma_daily, "drift_per_score": drift_per_score, "seed": SEED}}
    rec = event_car_spread(events, ret_wide, H=10, leak=False)
    plac_ev = events.copy()
    plac_ev["score"] = np.random.default_rng(SEED + 1).permutation(events["score"].to_numpy())
    plac = event_car_spread(plac_ev, ret_wide, H=10, leak=False)
    lk = event_car_spread(events, ret_wide, H=10, leak=True)
    asserts = {
        "recovery_sign_positive": bool(rec["long_short_car"] > 0),
        "recovery_significant_t>=2": bool(rec["nw_t"] is not None and abs(rec["nw_t"]) >= T_SIG),
        "placebo_insignificant_t<2": bool(plac["nw_t"] is None or abs(plac["nw_t"]) < T_SIG),
        "lookahead_entry_leaks_more_than_safe": bool(lk["nw_t"] is not None and rec["nw_t"] is not None
                                                     and abs(lk["nw_t"]) > abs(rec["nw_t"])),
    }
    out.update({"recovery_H10": rec, "placebo_H10": plac, "lookahead_leak_H10": lk,
                "asserts": asserts, "all_asserts_pass": bool(all(asserts.values()))})
    return out


def snapshot_characterization() -> dict:
    """DESCRIPTIVE parse of the real news_cache snapshot -- quantifies the data gap (no edge)."""
    if not NEWS_SNAPSHOT.exists():
        return {"present": False}
    d = json.loads(NEWS_SNAPSHOT.read_text(encoding="utf-8"))
    syms, n_art, classifiable, dates, types = set(), 0, 0, [], {}
    for k, v in d.items():
        syms.add(k.split(":")[0])
        for a in (v.get("articles", []) if isinstance(v, dict) else []):
            n_art += 1
            title = a.get("baslik", "") or ""
            dates.append(a.get("tarih", ""))
            if polarity(title) != 0:
                classifiable += 1
            for m in re.findall(r"\(([^)]+)\)", ascii_fold(title)):
                key = m.strip()[:40]
                types[key] = types.get(key, 0) + 1
    top_types = sorted(types.items(), key=lambda kv: -kv[1])[:8]
    return {"present": True, "distinct_symbols": len(syms), "total_articles": n_art,
            "polarity_classifiable_articles": classifiable,
            "classifiable_frac": round(classifiable / n_art, 4) if n_art else None,
            "date_span_sample": [dates[0] if dates else None, dates[-1] if dates else None],
            "is_backtestable_panel": False,
            "gap": ("snapshot only: a few symbols, ~1 month, headline-only, no per-day historical "
                    "sentiment scores -> NOT a historical day-stamped panel; needs approved fetch."),
            "top_disclosure_types": [{"type": t, "count": c} for t, c in top_types]}


def main():
    require_stage0()
    real_mode = FORWARD_PANEL.exists()
    sv = synthetic_self_validation()
    snap = snapshot_characterization()

    results = {
        "candidate": "L16 news-sentiment cross-sectional factor scaffold (pre-registered; offline-validated)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (historical sentiment panel present)" if real_mode else "OFFLINE synthetic self-validation + snapshot characterization",
        "forward_panel_expected": str(FORWARD_PANEL.relative_to(ROOT)),
        "forward_panel_present": bool(real_mode),
        "h_windows": H_WINDOWS, "seed": SEED,
        "synthetic_self_validation": sv,
        "snapshot_characterization": snap,
        "summary": {
            "headline": (
                "News-sentiment harness pre-registered and offline-validated. Synthetic self-test "
                f"asserts={'PASS' if sv['all_asserts_pass'] else 'FAIL'} "
                f"(recovery NW-t={sv['recovery_H10']['nw_t']}, placebo NW-t={sv['placebo_H10']['nw_t']}, "
                f"look-ahead-leak NW-t={sv['lookahead_leak_H10']['nw_t']}). Real news_cache is a "
                f"{snap.get('distinct_symbols')}-symbol / {snap.get('total_articles')}-article LIVE "
                "snapshot -- NOT a backtestable historical panel. NO real-data edge claimed."),
            "interpretation": (
                "Crystallizes the directive's SENTIMENT avenue into the L11 forward-scaffold form: the "
                "test is frozen and pipeline-validated; only a historical day-stamped news/sentiment "
                "fetch (Cagan-gated) is missing. The snapshot is dominated by KAP special-disclosures, "
                "so one approved KAP historical-text fetch would feed L16 (sentiment), L17 (NLP-type) "
                "and #1 daily-PEAD jointly."),
        },
        "verdict": {
            "verdict": ("SCAFFOLD-SELF-TEST PASS (synthetic-only; no deployable edge; awaiting approved "
                        "historical news/sentiment fetch)" if sv["all_asserts_pass"] else
                        "SCAFFOLD-SELF-TEST FAIL (no deployable edge; fix pipeline before any fetch)"),
            "synthetic_asserts_pass": bool(sv["all_asserts_pass"]),
            "real_data_run": bool(real_mode), "no_edge_claim": True,
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"mode={results['mode']}")
    print(f"recovery NW-t={sv['recovery_H10']['nw_t']} placebo={sv['placebo_H10']['nw_t']} "
          f"leak={sv['lookahead_leak_H10']['nw_t']} all_pass={sv['all_asserts_pass']}")
    print(f"snapshot: symbols={snap.get('distinct_symbols')} articles={snap.get('total_articles')} "
          f"classifiable_frac={snap.get('classifiable_frac')} backtestable={snap.get('is_backtestable_panel')}")


if __name__ == "__main__":
    main()
