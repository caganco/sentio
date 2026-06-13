"""Build a VBTS measure-event panel from public BIST daily bulletins (thm). No auth.

The equity daily bulletin file `thm{YYYYMMDD}{session}.csv` (public, machine-readable,
borsaistanbul.com/data/thm/...) carries each stock's daily trading-rule state, which
encodes the volatility-based surveillance measures directly:
  - BRUT TAKAS=1            -> gross settlement      (tier 2)
  - MAKSIMUM EMIR DEGERI cap -> order package        (tier 3, proxy)
  - ISLEM YONTEMI=TF        -> single-price method   (tier 4)
  - ACIGA SATIS=0           -> short-sale ban        (tier 1; masked by the market-wide ban)

A measure event is a day-over-day upward transition in that state. This is descriptive
only: NO returns, NO CAR, NO price reaction (Phase-2 scope). Raw bulletin CSVs are cached
locally and are NOT committed; only the counts-only intersection result is persisted.

Run: python scripts/probe/rr_y1_019_vbts_bulletin_build.py 2024-06-01 2026-06-12
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CACHE = Path("data/probe/_vbts_cache")
CACHE.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "tr,en;q=0.9"})


def fetch_day(d: dt.date) -> str | None:
    """Return the thm CSV text for a date, or None for a non-trading/missing day."""
    y, m, day = f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}"
    cached = CACHE / f"thm{y}{m}{day}.csv"
    if cached.exists():
        text = cached.read_text("utf-8")
        return text if len(text) > 1 else None
    for suffix in ("2", "1", "", "3"):
        url = f"https://borsaistanbul.com/data/thm/{y}/{m}/thm{y}{m}{day}{suffix}.zip"
        try:
            r = SESSION.get(url, timeout=20)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.content[:2] == b"PK":
            zf = zipfile.ZipFile(io.BytesIO(r.content))
            text = zf.read(zf.namelist()[0]).decode("iso-8859-9", "replace")
            cached.write_text(text, "utf-8")
            return text
    cached.write_text("", "utf-8")
    return None


def measure_level(row: dict) -> tuple[int, str]:
    """Highest active measure tier (0 = none) and the market segment."""
    method = (row.get("ISLEM YONTEMI") or "").strip()
    gross = (row.get("BRUT TAKAS") or "").strip()
    level = 0
    if gross == "1":
        level = max(level, 2)
    try:
        max_order = float((row.get("MAKSIMUM EMIR DEGERI(TL)") or "0").replace(",", "."))
        if 0 < max_order <= 1_000_000:
            level = max(level, 3)
    except ValueError:
        pass
    if method == "TF":
        level = max(level, 4)
    return level, (row.get("PAZAR (MARKET SEGMENT)") or "").strip()


def state_for_day(text: str) -> dict:
    state = {}
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        code = (row.get("ISLEM  KODU") or "").strip()
        if not code.endswith(".E"):
            continue
        state[code[:-2]] = measure_level(row)
    return state


def trading_days(start: str, end: str) -> list[dt.date]:
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out, cur = [], d0
    while cur <= d1:
        if cur.weekday() < 5:
            out.append(cur)
        cur += dt.timedelta(days=1)
    return out


def main(start: str, end: str) -> int:
    prev: dict = {}
    events: list[dict] = []
    population: dict = {}
    parsed = 0
    for d in trading_days(start, end):
        text = fetch_day(d)
        if not text:
            continue
        parsed += 1
        state = state_for_day(text)
        for ticker, (level, segment) in state.items():
            prev_level = prev.get(ticker, (None,))[0]
            if prev_level is not None and level > prev_level and level >= 2:
                events.append({"ticker": ticker, "level": level, "start_date": d.isoformat(),
                               "prev_level": prev_level, "pazar": segment,
                               "is_escalation": bool(prev_level >= 2)})
            if level >= 2:
                rec = population.get(ticker)
                if rec is None:
                    population[ticker] = {"level": level, "start_date": d.isoformat(), "pazar": segment}
                else:
                    rec["level"] = max(rec["level"], level)
        prev = state

    ev = pd.DataFrame(events)
    print(f"trading days parsed: {parsed} | transition-events: {len(ev)}")
    if len(ev):
        print("events by level:\n" + ev.groupby("level").size().to_string())
        print("distinct event tickers:", ev["ticker"].nunique())
        ev["end_date"] = ev["start_date"]
        ev["announce_ts"] = ev["start_date"]
        ev.to_parquet("data/probe/_vbts_events.parquet")

    pop = pd.DataFrame([{"ticker": k, **v} for k, v in population.items()])
    if len(pop):
        pop["end_date"] = pop["start_date"]
        pop["announce_ts"] = pop["start_date"]
        pop["is_escalation"] = False
        pop.to_parquet("data/probe/_vbts_population.parquet")
        print(f"\ndistinct names ever under measure (level>=2): {len(pop)}")
        print("population by max level:\n" + pop.groupby("level").size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
