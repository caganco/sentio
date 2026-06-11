"""RR-Y1-014 — PEAD sinyal-paneli kurucusu (Stage-0 FREEZE-ONCESI adim).

GETIRI HESAPLAMAZ, GETIRI OKUMAZ. Yalniz sinyal-tarafi insa eder:
  - SUE1 (donmus form, RR-Y1-014 §3): UE_t = Q_t - Q_{t-4q} (qid-hizali, gap-safe;
    RR-046 devir-envanterindeki `ue` kolonu), onceki-CEYREK-SONU harmonize-mktval'e
    olceklenmis: SUE = UE / MV(period_end - 3ay'in takvim-ayi).
    Uygunluk: >= 8 ceyrek onceki-kazanc-gecmisi (qid_t - qid_ilk >= 8).
    NOT (transkripsiyon-cozumu, sonuc-gorulmeden donduruldu): RR-Y1-013/014
    tablolarindaki "SUE formu" satiri iki direktifte de "onceki-ceyrek-sonu
    mktval'e olceklenmis" der; "8-ceyrek (payda)" satiri trailing-std formunun
    kalintisidir. EN-SPESIFIK ve IKI-KEZ-tekrarlanan tanim (mktval-olcekli) esas
    alindi; 8-ceyrek kosulu gecmis-tabani olarak uygulandi. Trailing-std formu
    HESAPLANMADI (ikinci-config yok; composite-optimize yasak).
  - Giris: RR-Y1-013-B gun-damgali panelden entry_date_t2 (T+2, seans-kurali).
  - Likidite: liquid_names(panel, asof=D0) (motor B7; RR-Y1-008 parite).
  - Pencere: 60 islem-gunu [entry .. entry+59] (panel-sonu kirpmasi dahil-tutulur).
  - Evren: fiscal 2019Q1..2025Q4 (RR-Y1-014 §2).
  - Cakisan ardisik olaylar: en-yeni giris eskisinin kalan penceresini degistirir
    (skor-karesi giris-sirasiyla yazilir).

Ayrica Stage-0 freeze-girdilerini uretir (yine getiri-gormeden):
  - X1/X2 isim-bolmesi: committed `moda._pair_randomize` (likidite-stratified,
    seed=0, R=1 semantigi). ADV-siralamasi her ismin KENDI ilk-olay-D0'inda
    trailing-63g medyan islem-degeri (look-ahead-safe; IPO-isimleri dislamaz).
  - hash16(pead_signal_panel.parquet) -> Stage-0 snapshot-hash alani.
  - lockbox_fingerprint(panel, names=X2) -> Stage-0 lockbox_content_hash.

Ciktilar:
  data/processed/pead_signal_panel.parquet
  data/processed/pead_stage0_freeze_inputs.json   (hash'ler + X1/X2 listeleri)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.clean_universe_fundamentals import load_degoran_fundamentals  # noqa: E402
from src.data.pead_snapshot_builder import DEGORAN_GLOB, PEAD_END, PEAD_START  # noqa: E402
from src.engine.data_adapter import liquid_names, load_panel  # noqa: E402
from src.engine.lockbox import lockbox_fingerprint  # noqa: E402
from src.engine.moda import _pair_randomize  # noqa: E402  (committed split primitive, read-only)
from src.engine.stage0_validator import hash16  # noqa: E402
from src.screening.d206_nav_discount import harmonize_mktval_units  # noqa: E402

EARNINGS_PARQUET = REPO_ROOT / "data" / "snapshots" / "earnings_dates.parquet"
DAYDATED_PARQUET = REPO_ROOT / "data" / "probe" / "pead_announcement_daydated.parquet"
OUT_DIR = REPO_ROOT / "data" / "processed"
OUT_PARQUET = OUT_DIR / "pead_signal_panel.parquet"
OUT_FREEZE = OUT_DIR / "pead_stage0_freeze_inputs.json"

# --- donmus tasarim (RR-Y1-014 §2/§3) ---
FY_MIN, FY_MAX = 2019, 2025
HOLD_TDAYS = 60                # tutus: 60 islem-gunu
MIN_HISTORY_QUARTERS = 8       # SUE uygunluk: >= 8 ceyrek onceki-kazanc-gecmisi
SPLIT_SEED = 0                 # X1/X2 isim-bolmesi (committed pair-randomize, R=1)


def _harmonized_mktval(funds: pd.DataFrame) -> pd.DataFrame:
    f = funds.copy()
    f["month"] = f["month"].astype("period[M]")
    mk = f.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last").sort_index()
    mk_h, _ = harmonize_mktval_units(mk)
    return mk_h


def build() -> None:
    print("[panel] girdiler yukleniyor...", flush=True)
    ev = pd.read_parquet(EARNINGS_PARQUET)
    dd = pd.read_parquet(DAYDATED_PARQUET).rename(columns={"ticker": "symbol"})
    funds = load_degoran_fundamentals(start=PEAD_START, end=PEAD_END, file_glob=DEGORAN_GLOB)
    mk_h = _harmonized_mktval(funds)
    panel = load_panel()
    dates = panel.dates

    # --- olay-evreni: fiscal 2019Q1..2025Q4 ---
    e = ev[(ev["fiscal_year"] >= FY_MIN) & (ev["fiscal_year"] <= FY_MAX)].copy()
    n0 = len(e)

    # --- SUE1 (mktval-olcekli, donmus) ---
    e["period_end_ts"] = pd.to_datetime(e["period_end"])
    prior_q_month = (e["period_end_ts"] - pd.DateOffset(months=3)).dt.to_period("M")
    mk_long = mk_h.stack()
    keys = pd.MultiIndex.from_arrays([prior_q_month, e["symbol"]])
    e["mv_prior_q"] = mk_long.reindex(keys).to_numpy()
    # 8-ceyrek gecmis-tabani: qid_t - (ismin ilk net_profit_q-tanimli qid'i) >= 8
    ev_all = ev[ev["net_profit_q"].notna()].copy()
    ev_all["qid"] = ev_all["fiscal_year"] * 4 + (ev_all["quarter"] - 1)
    first_qid = ev_all.groupby("symbol")["qid"].min()
    e["qid"] = e["fiscal_year"] * 4 + (e["quarter"] - 1)
    e["hist_q"] = e["qid"] - e["symbol"].map(first_qid)
    with np.errstate(invalid="ignore", divide="ignore"):
        e["sue_mkt"] = np.where(
            e["ue"].notna() & e["mv_prior_q"].notna() & (e["mv_prior_q"] > 0)
            & (e["hist_q"] >= MIN_HISTORY_QUARTERS),
            e["ue"] / e["mv_prior_q"],
            np.nan,
        )
    n_sue = int(e["sue_mkt"].notna().sum())

    # --- gun-damgasi join (RR-Y1-013-B) ---
    dd_k = dd[["symbol", "fiscal_year", "quarter", "first_announcement_ts", "d0",
               "entry_date_t2", "restate_step_flag"]].drop_duplicates(
        ["symbol", "fiscal_year", "quarter"])
    e = e.merge(dd_k, on=["symbol", "fiscal_year", "quarter"], how="left")
    e["d0"] = pd.to_datetime(e["d0"])
    e["entry_date_t2"] = pd.to_datetime(e["entry_date_t2"])

    # --- filtre zinciri (sayimlar raporlanir; getiri yok) ---
    flt = {
        "n_events_fy_window": n0,
        "n_sue_defined": n_sue,
        "n_daystamped": int((e["sue_mkt"].notna() & e["entry_date_t2"].notna()).sum()),
    }
    e = e[e["sue_mkt"].notna() & e["entry_date_t2"].notna()].copy()
    # giris panel-takvimi icinde olmali
    e = e[e["entry_date_t2"].isin(dates)].copy()
    flt["n_entry_in_calendar"] = len(e)

    # --- likidite: liquid_names asof D0 (motor B7) ---
    liq_cache: dict[pd.Timestamp, set] = {}
    for d in e["d0"].unique():
        d = pd.Timestamp(d)
        sub = dates[dates <= d]
        liq_cache[d] = liquid_names(panel, sub[-1]) if len(sub) else set()
    e["liquid_at_d0"] = [s in liq_cache[pd.Timestamp(d)] for s, d in zip(e["symbol"], e["d0"], strict=True)]
    e["in_price_panel"] = e["symbol"].isin(set(panel.close.columns))
    flt["n_liquid_at_d0"] = int((e["liquid_at_d0"] & e["in_price_panel"]).sum())

    e = e[e["liquid_at_d0"] & e["in_price_panel"]].copy()

    # --- pencere [entry .. entry+59] (panel-sonu kirpilir, dahil-tutulur) ---
    pos = pd.Series(np.arange(len(dates)), index=dates)
    e["entry_pos"] = e["entry_date_t2"].map(pos)
    e["window_end_pos"] = (e["entry_pos"] + HOLD_TDAYS - 1).clip(upper=len(dates) - 1)
    e["window_end_date"] = dates[e["window_end_pos"].to_numpy()]
    e["window_truncated"] = (e["entry_pos"] + HOLD_TDAYS - 1) > (len(dates) - 1)
    flt["n_final_universe"] = len(e)
    flt["n_window_truncated"] = int(e["window_truncated"].sum())
    flt["n_symbols"] = int(e["symbol"].nunique())

    # ceyrek-bazli kapasite-ekosu (yalniz sayim)
    per_q = e.groupby(["fiscal_year", "quarter"]).size()
    flt["per_quarter_n"] = {f"{fy}Q{q}": int(n) for (fy, q), n in per_q.items()}

    cols = ["symbol", "fiscal_year", "quarter", "period_end", "sue_mkt", "ue", "mv_prior_q",
            "hist_q", "first_announcement_ts", "d0", "entry_date_t2", "window_end_date",
            "window_truncated", "restate_step_flag"]
    out = e[cols].sort_values(["entry_date_t2", "symbol"]).reset_index(drop=True)
    out["fiscal_period"] = out["fiscal_year"].astype(str) + "Q" + out["quarter"].astype(str)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_PARQUET, index=False)
    print(f"[panel] yazildi: {OUT_PARQUET.relative_to(REPO_ROOT)} ({len(out)} olay)", flush=True)

    # --- X1/X2 isim-bolmesi (likidite-stratified, committed primitive, seed=0) ---
    pool = sorted(out["symbol"].unique())
    first_d0 = out.groupby("symbol")["d0"].min()
    adv_at_first: dict[str, float] = {}
    for s in pool:
        d = pd.Timestamp(first_d0[s])
        w = panel.value_tl.loc[panel.value_tl.index <= d, s].tail(63)
        adv_at_first[s] = float(w.median(skipna=True)) if len(w) else float("nan")
    ranked = [s for s, _ in sorted(adv_at_first.items(), key=lambda kv: -kv[1] if np.isfinite(kv[1]) else np.inf)]
    ranked = [s for s in ranked if np.isfinite(adv_at_first[s])]
    rng = np.random.default_rng(np.random.SeedSequence(SPLIT_SEED).spawn(1)[0])
    x1, x2 = _pair_randomize(ranked, rng)

    freeze = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signal_panel_hash16": hash16(OUT_PARQUET),
        "filter_chain": flt,
        "n_name_pool": len(pool),
        "n_ranked_finite_adv": len(ranked),
        "split_seed": SPLIT_SEED,
        "split_method": "liquidity-stratified pair-randomization (committed moda._pair_randomize, R=1)",
        "adv_asof_rule": "her ismin KENDI ilk-olay-D0'inda trailing-63g medyan value_tl",
        "x1_names": x1,
        "x2_names": x2,
        "lockbox_content_hash_x2": lockbox_fingerprint(panel, names=x2),
        "no_performance_metrics": True,
    }
    OUT_FREEZE.write_text(json.dumps(freeze, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[panel] yazildi: {OUT_FREEZE.relative_to(REPO_ROOT)}", flush=True)
    print(json.dumps({k: v for k, v in freeze.items() if k not in ("x1_names", "x2_names")},
                     ensure_ascii=True, indent=2))
    print(f"[panel] X1={len(x1)} isim, X2={len(x2)} isim")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    build()
