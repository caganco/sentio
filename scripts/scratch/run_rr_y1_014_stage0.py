"""RR-Y1-014 — PEAD Stage-0 olcum-runner'i (DONMUS on-kayit uygulamasi).

Stage-0 dosyasi (docs/yol1/STAGE0_PEAD_SUE1_TERCILE.json) yoksa/sema-bozuksa/
snapshot-hash kaymissa KOSMAZ (require_stage0 + assert_snapshot_hash).
committed-motor src/engine READ-ONLY kullanilir; hicbir engine dosyasi degismez.

Fazlar (DEC-053 protokolu):
  --phase x1     X1 uygulama-dogrulamasi. Parametreler Stage-0'da donmus; X1
                 yalniz "pipeline dogru calisiyor mu" bakisidir. Bakis-sayaci
                 data/processed/pead_x1_looks.json'a yazilir; 3'u asan bakis REDDEDILIR.
  --phase final  (a) FULL-panel committed-harness kosusu (basligin NW-t'si, D-207
                 maliyet, benchmark-floor, per-rejim, Mod-A-agreement[breadth-
                 degenerate-beklenir], Mod-B DSR);
                 (b) X2 lockbox TEK-ATIS (assert_lockbox -> arm-istatistigi ->
                 consume_lockbox; marker COMMIT edilir);
                 (c) keep-bar degerlendirmesi -> docs/yol1/RR-Y1-014_engine_output.json

Arm-istatistigi (X1/X2): committed `harness._tilt_active` (read-only) frac=1/3,
h=1, basis=tr_index_gross, min_names=15 (yarim-evren icin breadth-orantili taban;
Stage-0'da donmus) + committed `stats.nw_tstat` (lag=5, gunluk).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.engine import config as engine_config  # noqa: E402
from src.engine.contracts import (  # noqa: E402
    DialConfig,
    Frequency,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.harness import _tilt_active, harness  # noqa: E402
from src.engine.lockbox import assert_lockbox, consume_lockbox, marker_path_for  # noqa: E402
from src.engine.data_adapter import load_panel  # noqa: E402
from src.engine.stage0_validator import assert_snapshot_hash, require_stage0  # noqa: E402
from src.engine.stats import nw_tstat  # noqa: E402

STAGE0_PATH = REPO_ROOT / "docs" / "yol1" / "STAGE0_PEAD_SUE1_TERCILE.json"
SIGNAL_PANEL = REPO_ROOT / "data" / "processed" / "pead_signal_panel.parquet"
FREEZE_INPUTS = REPO_ROOT / "data" / "processed" / "pead_stage0_freeze_inputs.json"
X1_LOOKS = REPO_ROOT / "data" / "processed" / "pead_x1_looks.json"
OUT_ENGINE = REPO_ROOT / "docs" / "yol1" / "RR-Y1-014_engine_output.json"

# --- donmus kosu-sabitleri (Stage-0 JSON'da deklare) ---
ARM_MIN_NAMES = 15        # yarim-evren gunluk-kesit tabani (= ceil(30/2))
TERCILE_FRAC = 1.0 / 3.0
H_DAYS = 1                # construction_window=1: gunluk takvim-zamani; 60g tutus skorda
NW_LAG = engine_config.NW_LAG_DAILY  # 5
NW_T_MIN = 2.0
MAX_X1_LOOKS = 3


class PEADSue1Signal:
    """Zero-discretion kesitsel skorlayici: olay-penceresi-ici SUE1 (mktval-olcekli).

    construction_window = 1 -> motor gunluk takvim-zamani artislariyla degerlendirir
    (60-islem-gunu tutus, skorun [entry .. entry+59] persistansinda kodlu). RR-Y1-008
    cift-rol uyarisi geregi Stage-0'da acikca deklare edilmistir: construction_window
    TUTMA-horizonu DEGILDIR.
    """

    name = "pead_sue1_tercile"
    construction_window = H_DAYS

    def __init__(self, wide: pd.DataFrame) -> None:
        self._wide = wide

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        if asof not in self._wide.index:
            return pd.Series(dtype=float)
        row = self._wide.loc[asof].dropna()
        if not len(row):
            return row
        keep = row.index.intersection(names)
        return row.loc[keep]


def build_score_frame(events: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Olay-bazli SUE skorlarini (gun x isim) karesine yayar.

    Olaylar giris-tarihine gore ARTAN sirada yazilir: cakisan ardisik olaylarda
    en-yeni giris eskisinin kalan gunlerini degistirir (donmus kural).
    """
    syms = sorted(events["symbol"].unique())
    col_of = {s: i for i, s in enumerate(syms)}
    mat = np.full((len(dates), len(syms)), np.nan)
    pos = pd.Series(np.arange(len(dates)), index=dates)
    ev = events.sort_values("entry_date_t2")
    for _, r in ev.iterrows():
        i0 = int(pos[r["entry_date_t2"]])
        i1 = int(pos[r["window_end_date"]])
        mat[i0:i1 + 1, col_of[r["symbol"]]] = float(r["sue_mkt"])
    return pd.DataFrame(mat, index=dates, columns=syms)


def slice_panel(panel: Panel, names: list[str]) -> Panel:
    keep = [c for c in panel.close.columns if c in set(names)]
    membership = {k: v[[c for c in v.columns if c in set(names)]] for k, v in panel.membership.items()}
    return Panel(
        close=panel.close[keep], tr_gross=panel.tr_gross[keep], tr_net=panel.tr_net[keep],
        value_tl=panel.value_tl[keep], membership=membership,
        market=panel.market, tufe=panel.tufe, tlref=panel.tlref, frequency=panel.frequency,
    )


def arm_stat(panel: Panel, signal: PEADSue1Signal, label: str) -> dict:
    """Yarim-evren (arm) istatistigi: committed _tilt_active (min_names=15) + nw_tstat."""
    active, _is_top, held = _tilt_active(
        panel, signal, frac=TERCILE_FRAC, h=H_DAYS,
        basis="tr_index_gross", min_names=ARM_MIN_NAMES,
    )
    yr = engine_config.TRADING_DAYS_YR
    out = {
        "label": label,
        "n_obs": int(active.size),
        "n_names_held": len(held),
        "min_names_floor": ARM_MIN_NAMES,
        "nw_lag": NW_LAG,
    }
    if active.empty:
        out.update({"nw_t": None, "gross_active_ann": None,
                    "guard": "hicbir gun kesit-tabanini gecmedi"})
        return out
    out["nw_t"] = float(nw_tstat(active.to_numpy(dtype=float), lag=NW_LAG))
    out["gross_active_ann"] = float(active.mean() * yr)
    out["d0"] = str(active.index[0].date())
    out["d1"] = str(active.index[-1].date())
    return out


def _clean(o):
    """JSON-temiz serilestirme: NaN/inf -> None, enum/tuple -> str/list."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if isinstance(o, (np.floating, np.integer)):
        return _clean(float(o)) if isinstance(o, np.floating) else int(o)
    if hasattr(o, "value") and not isinstance(o, (str, int, float, bool)):  # StrEnum vb.
        return str(o)
    return o


def load_inputs() -> tuple:
    stage0 = require_stage0(STAGE0_PATH)
    assert_snapshot_hash(stage0, SIGNAL_PANEL)
    freeze = json.loads(FREEZE_INPUTS.read_text(encoding="utf-8"))
    events = pd.read_parquet(SIGNAL_PANEL)
    events["entry_date_t2"] = pd.to_datetime(events["entry_date_t2"])
    events["window_end_date"] = pd.to_datetime(events["window_end_date"])
    panel = load_panel()
    wide = build_score_frame(events, panel.dates)
    signal = PEADSue1Signal(wide)
    return stage0, freeze, events, panel, signal


def phase_x1() -> None:
    stage0, freeze, events, panel, signal = load_inputs()
    looks = json.loads(X1_LOOKS.read_text(encoding="utf-8")) if X1_LOOKS.exists() else []
    if len(looks) >= MAX_X1_LOOKS:
        raise SystemExit(f"X1 bakis-butcesi tukenmis ({len(looks)}/{MAX_X1_LOOKS}) — REDDEDILDI")
    panel_x1 = slice_panel(panel, freeze["x1_names"])
    res = arm_stat(panel_x1, signal, "X1 (uygulama-dogrulamasi)")
    looks.append({"at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "n_obs": res["n_obs"], "purpose": "implementation-verification"})
    X1_LOOKS.write_text(json.dumps(looks, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(_clean(res), ensure_ascii=True, indent=2))
    print(f"[x1] bakis {len(looks)}/{MAX_X1_LOOKS} kaydedildi")


def phase_final() -> None:
    stage0, freeze, events, panel, signal = load_inputs()

    # (a) FULL-panel committed-harness basligi (Mod-A agreement + Mod-B DSR dahil)
    spec = SplitSpec(
        split_mode=SplitMode.PANEL, frequency=Frequency.DAILY, embargo_h=H_DAYS,
        seed=0, sort_depth=SortDepth.TERCILE,
    )
    dial = DialConfig()
    print("[final] FULL-panel harness kosuyor (Mod-A+B)...", flush=True)
    full_out = harness(panel, signal, spec, dial, stage0_path=None)  # stage0 manuel-dogrulandi;
    # lockbox X2'ye-ozgu oldugundan FULL kosuya stage0_path GECIRILMEZ (lockbox X2-dilimini bekler)

    # (b) X2 lockbox TEK-ATIS (committed lockbox primitifleriyle)
    print("[final] X2 lockbox tek-atis...", flush=True)
    panel_x2 = slice_panel(panel, freeze["x2_names"])
    marker = marker_path_for(STAGE0_PATH)
    assert_lockbox(stage0, panel_x2, marker)
    x2_res = arm_stat(panel_x2, signal, "X2 (lockbox, tek-atis)")
    consume_lockbox(stage0, marker)

    # X1 kaydi (zaten gorulmus yarim; simetrik raporlama icin)
    panel_x1 = slice_panel(panel, freeze["x1_names"])
    x1_res = arm_stat(panel_x1, signal, "X1 (gelistirme-yarisi, kayit)")

    # (c) keep-bar degerlendirmesi (Stage-0 §4 donmus tanim)
    nw_full = full_out.nw_t
    nw_x2 = x2_res.get("nw_t")
    kb = {
        "nw_t_min": NW_T_MIN,
        "nw_t_full": nw_full,
        "nw_t_x2": nw_x2,
        "cond_full": bool(nw_full is not None and np.isfinite(nw_full) and nw_full >= NW_T_MIN),
        "cond_x2": bool(nw_x2 is not None and np.isfinite(nw_x2) and nw_x2 >= NW_T_MIN),
    }
    kb["keep_bar_pass"] = bool(kb["cond_full"] and kb["cond_x2"])

    out = {
        "task": "RR-Y1-014 PEAD Stage-0 olcumu",
        "stage0": str(STAGE0_PATH.relative_to(REPO_ROOT)),
        "stage0_snapshot_hash16": stage0.snapshots_content_hash_sha256_prefix,
        "lockbox_hash": stage0.lockbox_content_hash,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_events": int(len(events)),
        "n_event_names": int(events["symbol"].nunique()),
        "full_panel_engine_output": _clean(asdict(full_out)),
        "x1": _clean(x1_res),
        "x2": _clean(x2_res),
        "keep_bar": _clean(kb),
        "x1_looks_used": (json.loads(X1_LOOKS.read_text(encoding="utf-8"))
                          if X1_LOOKS.exists() else []),
    }
    OUT_ENGINE.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[final] yazildi: {OUT_ENGINE.relative_to(REPO_ROOT)}")
    print(json.dumps(_clean(kb), ensure_ascii=True, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="RR-Y1-014 Stage-0 runner")
    ap.add_argument("--phase", choices=["x1", "final"], required=True)
    args = ap.parse_args()
    if args.phase == "x1":
        phase_x1()
    else:
        phase_final()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    main()
