"""RR-046 ASAMA-2a -- macro-event-dates snapshot (TUIK CPI + TCMB PPK).

DATA ACQUISITION ONLY (secondary; macro edge-prior is WEAK per RR-046 -- the calendar is
recorded, no edge claimed). committed-engine zero-touch.

Two event types, honestly tiered by what is reliably obtainable OFFLINE:

  cpi_release  -- TUIK CPI for reference month M is released on a regulated schedule, the
                  3rd of month M+1 at 10:00 (TUIK "Ulusal Veri Yayimlama Takvimi"). We emit a
                  deterministic RULE-PROXY date = 3rd of M+1 rolled forward past weekends.
                  Reproducible, network-free; actual dates land within ~1-2 days. (2019-01..)

  ppk_decision -- TCMB Para Politikasi Kurulu rate decisions. The full historical calendar is
                  NOT available offline: EVDS endpoints 404/migrated (see tcmb_client notes),
                  local_macro.db holds only the 2 most-recent meetings, and per-year press-release
                  scraping is a budgeted/fragile fetch (RR-042-style). We record the locally-known
                  meetings (source-tagged) and DEFER the 2019-2025 history to a live recorder /
                  budgeted scrape (Katman-2-style), rather than hardcode unverifiable dates.

Output (git-local; gitignored -> force-add to track, mirroring exposure_*/faz0_* convention):
  data/snapshots/macro_event_dates.parquet
  data/snapshots/macro_event_dates.meta.json
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
SNAPSHOTS_DIR = _REPO_ROOT / "data" / "snapshots"
_OUT_PARQUET = SNAPSHOTS_DIR / "macro_event_dates.parquet"
_OUT_META = SNAPSHOTS_DIR / "macro_event_dates.meta.json"
_PPK_FALLBACK_YAML = _REPO_ROOT / "src" / "signals" / "local" / "data" / "local_macro_fallback.yaml"

# --- frozen geometry ---
CPI_FIRST_REF_MONTH = "2019-01"     # reference month; release in M+1
CPI_LAST_REF_MONTH = "2026-04"
CPI_RELEASE_DAY = 3                 # TUIK: 3rd of M+1 (rolled past weekends)


def _cpi_release_rows() -> list[dict]:
    """Deterministic TUIK CPI release-date proxy: 3rd of M+1, rolled forward off weekends."""
    rows = []
    for ref in pd.period_range(CPI_FIRST_REF_MONTH, CPI_LAST_REF_MONTH, freq="M"):
        rel_month = ref + 1
        d = pd.Timestamp(year=rel_month.year, month=rel_month.month, day=CPI_RELEASE_DAY)
        while d.weekday() >= 5:                     # Sat=5, Sun=6 -> next business day
            d += pd.Timedelta(days=1)
        rows.append({
            "event_type": "cpi_release",
            "event_date": d.strftime("%Y-%m-%d"),
            "reference_period": str(ref),
            "source": "tuik-rule-proxy",
            "exact": False,
        })
    return rows


def _ppk_rows() -> list[dict]:
    """Locally-known PPK meetings from the macro fallback (source-tagged, exact)."""
    if not _PPK_FALLBACK_YAML.exists():
        return []
    data = yaml.safe_load(_PPK_FALLBACK_YAML.read_text(encoding="utf-8")) or {}
    decisions = (data.get("tcmb") or {}).get("decisions") or []
    rows = []
    for d in decisions:
        if not d.get("decision_date"):
            continue
        rows.append({
            "event_type": "ppk_decision",
            "event_date": str(d["decision_date"]),
            "reference_period": str(d["decision_date"])[:7],
            "source": f"local_macro_fallback:{d.get('source', 'na')}",
            "exact": True,
        })
    return rows


def build_macro_events() -> tuple[pd.DataFrame, dict]:
    rows = _cpi_release_rows() + _ppk_rows()
    df = pd.DataFrame(rows).sort_values(["event_type", "event_date"]).reset_index(drop=True)
    n_cpi = int((df["event_type"] == "cpi_release").sum())
    n_ppk = int((df["event_type"] == "ppk_decision").sum())
    meta = {
        "schema_version": 1,
        "directive": "RR-046 ASAMA-2a (macro, secondary)",
        "phase": "macro-event-dates (data acquisition only; edge-prior WEAK, no edge claimed)",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cpi_release": {
            "method": "TUIK rule-proxy: 3rd of M+1 rolled past weekends",
            "exact": False,
            "note": "actual TUIK dates land within ~1-2 days; refine via Ulusal Veri "
                    "Yayimlama Takvimi if the edge-test needs exact-day.",
            "ref_months": f"{CPI_FIRST_REF_MONTH}..{CPI_LAST_REF_MONTH}",
            "n": n_cpi,
        },
        "ppk_decision": {
            "exact": True,
            "n": n_ppk,
            "deferred_note": "full 2019-2025 PPK history NOT available offline (EVDS 404/migrated; "
                             "local_macro.db has only the 2 latest). 2019-2025 dates DEFERRED to a "
                             "live recorder / budgeted TCMB press-release scrape (Katman-2-style); "
                             "unverifiable dates deliberately NOT hardcoded.",
            "source": "local_macro_fallback.yaml",
        },
        "look_ahead_note": "event_date is the public release/decision day; consumers enter t+1 "
                           "(release is 10:00 / intraday).",
        "n_rows": int(len(df)),
    }
    return df, meta


def build_and_write(force_rebuild: bool = False) -> tuple[pd.DataFrame, dict]:
    if _OUT_PARQUET.exists() and _OUT_META.exists() and not force_rebuild:
        df = pd.read_parquet(_OUT_PARQUET)
        meta = json.loads(_OUT_META.read_text(encoding="utf-8"))
        return df, meta
    df, meta = build_macro_events()
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_OUT_PARQUET, index=False)
    _OUT_META.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    logger.info("[macro-events] frozen: %s rows=%d (cpi=%d ppk=%d)",
                _OUT_PARQUET.name, meta["n_rows"], meta["cpi_release"]["n"], meta["ppk_decision"]["n"])
    return df, meta


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    panel, m = build_and_write(force_rebuild=True)
    print(json.dumps(m, indent=2))
    print("\nhead:\n", panel.head(4).to_string(index=False))
    print("\ntail:\n", panel.tail(4).to_string(index=False))
