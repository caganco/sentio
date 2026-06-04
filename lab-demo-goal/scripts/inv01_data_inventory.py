"""lab-demo-goal inv-01: precise schema + coverage inventory of all local panels.

READ-ONLY. Prints columns, dtypes, row counts, date span, symbol count, NaN frac
for every research-relevant parquet so the lab knows EXACTLY what is measurable.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CU = ROOT / "data" / "clean_universe"
SN = ROOT / "data" / "snapshots"

TARGETS = [
    CU / "adjusted_prices_2019_2026.parquet",
    CU / "d207_quoted_spread_panel.parquet",
    CU / "fundamentals_2019_2026.parquet",
    CU / "pit_membership_2019_2026.parquet",
    SN / "earnings_dates.parquet",
    SN / "macro_event_dates.parquet",
    SN / "trend_v1_ohlcv_2019-01-01_2026-04-30.parquet",
    SN / "faz0_macro_aux.parquet",
    SN / "exposure_d187_gold_tl.parquet",
    SN / "exposure_d187_tlref.parquet",
    SN / "exposure_d187_tufe.parquet",
    SN / "exposure_d187_xu100.parquet",
]


def describe(p: Path):
    print("=" * 78)
    print(f"FILE: {p.relative_to(ROOT)}")
    if not p.exists():
        print("  MISSING")
        return
    df = pd.read_parquet(p)
    print(f"  shape: {df.shape}")
    print(f"  index: {df.index.name} dtype={df.index.dtype}")
    try:
        idx = pd.to_datetime(df.index)
        print(f"  index span: {idx.min()} .. {idx.max()}  (n={len(idx)})")
    except Exception:
        pass
    cols = list(df.columns)
    print(f"  n_cols: {len(cols)}")
    # If looks like a long/tidy frame (date/symbol columns) vs wide panel
    lower = [str(c).lower() for c in cols]
    if "date" in lower or "symbol" in lower or "ticker" in lower:
        print(f"  COLUMNS: {cols[:40]}{' ...' if len(cols) > 40 else ''}")
        for c in cols:
            s = df[c]
            extra = ""
            if s.dtype == object or str(s.dtype).startswith("datetime"):
                nun = s.nunique(dropna=True)
                extra = f" nunique={nun}"
                if nun <= 12:
                    extra += f" vals={sorted(map(str, s.dropna().unique()))[:12]}"
            print(f"    - {c}: dtype={s.dtype} nan_frac={s.isna().mean():.3f}{extra}")
        # date span if a date col
        for dc in cols:
            if str(dc).lower() in ("date", "ex_date", "exdate", "announce_date", "event_date"):
                try:
                    dd = pd.to_datetime(df[dc])
                    print(f"  date-col '{dc}' span: {dd.min()} .. {dd.max()}")
                except Exception:
                    pass
    else:
        # wide panel: columns are symbols
        print(f"  (wide panel; {len(cols)} symbol-columns) sample cols: {cols[:8]}")
        nanfrac = df.isna().mean().mean()
        print(f"  mean nan_frac across cells: {nanfrac:.3f}")
        # per-symbol coverage
        cov = (~df.isna()).sum(axis=0)
        print(f"  per-symbol non-nan rows: min={cov.min()} median={int(cov.median())} max={cov.max()}")


if __name__ == "__main__":
    for t in TARGETS:
        describe(t)
    print("=" * 78)
    print("INVENTORY DONE")
