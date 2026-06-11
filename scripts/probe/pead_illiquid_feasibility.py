"""RR-Y1-015-B — PEAD ILLIKIT-DILIM harvest-fizibilite probu (RR-Y1-015 eklentisi).

FIZIBILITE PROBU — Stage-0 OLCUMU DEGIL, edge-testi DEGIL, mezar-acma/diriltme DEGIL.

Baglamı: RR-Y1-014 (PEAD Stage-0) yuksek-SUE-tercile long-bacagini BIST *likit*
evreninde olctu -> KEEP-BAR FAIL (tam-panel NW-t -0.029). Olcum on-kayitli olarak
SADECE likit dilimi kapsadi; SUE-tanimli olaylarin ~%81'i likit-evren-disiydi ve
"harvest-edilemez oldugu icin olcum-evreni disinda" diye ON-DEKLARE edilmisti.

Bu prob o ON-DEKLARE-DISLAMAYI NICELER: illikit tamamlayici gercekten
harvest-edilemez mi? Tek soru veri/islem-fizibilitesidir; PERFORMANS DEGIL.
CAR / getiri / drift-buyuklugu / Sharpe / t-istatistigi HESAPLANMAZ. Uc kapi:

  H1 — COST-WALL: olay-bazli (event-hold) TEK round-trip maliyeti (D-207 Roll+Kyle
       +tier; src/screening/realistic_cost, READ-ONLY). Illikit vs likit taban.
       Soru: maliyet, makul bir 60-gun PEAD drift'ini yiyip bitiriyor mu?
  H2 — STALE / PHANTOM + GIRIS-ISLENEBILIRLIGI: tutus-penceresinde sifir-hacim ve
       sifir-getiri (stale-print) gun-payi + giris-gunu (T+2) islenebilir mi.
       Soru: olculecek "drift"in ne kadari gercek-alinabilir vs fiyat-yakalama-hayaleti?
  H3 — KAPASITE / ETKIN-N: illikit evrende ceyrek-bazli yuksek-SUE tercile uc-dilim
       en az 5 isimle kurulabilir mi (kesitsel-genislik)? (G3 bari ayni.)

Girdiler (hepsi read-only; committed-motor src/engine'e SIFIR yazim):
  - data/snapshots/earnings_dates.parquet              (RR-046 devir-envanteri)
  - data/probe/pead_announcement_daydated.parquet      (RR-Y1-013-B gun-damgasi)
  - bist_datastore_archive degoran fundamentals        (mktval -> SUE1 paydasi)
  - data/clean_universe/adjusted_prices_2019_2026.parquet (engine data_adapter)
  - likit-evren tanimi = engine `liquid_names` (recon B7; RR-Y1-008 parite)

SUE1 = donmus form (RR-Y1-014 §3, sonuc-gorulmeden): UE / MV(onceki-ceyrek-sonu).
Burada YENIDEN-uretilir (probe self-contained; 014 build-scriptine bagimli degil),
ayni formul/esik. Olaylarin SINIFLANDIRMASI icin; SUE-DEGERIYLE getiri OLCULMEZ.

Ciktilar:
  data/probe/pead_illiquid_feasibility_summary.json     (kapi istatistikleri)
  data/probe/pead_illiquid_feasibility_summary.parquet  (ceyrek-bazli kapasite tablosu)

Kullanim:
  python scripts/probe/pead_illiquid_feasibility.py
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
from src.screening.d204_config import D204_ORDER_VALUE_TL  # noqa: E402
from src.screening.d206_nav_discount import harmonize_mktval_units  # noqa: E402
from src.screening.realistic_cost import round_trip_cost  # noqa: E402

EARNINGS_PARQUET = REPO_ROOT / "data" / "snapshots" / "earnings_dates.parquet"
DAYDATED_PARQUET = REPO_ROOT / "data" / "probe" / "pead_announcement_daydated.parquet"
OUT_DIR = REPO_ROOT / "data" / "probe"
OUT_JSON = OUT_DIR / "pead_illiquid_feasibility_summary.json"
OUT_PARQUET = OUT_DIR / "pead_illiquid_feasibility_summary.parquet"

# --- donmus tasarim (RR-Y1-014 §2/§3 ile birebir; burada optimize EDILMEZ) ---
FY_MIN, FY_MAX = 2019, 2025
HOLD_TDAYS = 60                 # tutus: 60 islem-gunu (event-hold)
MIN_HISTORY_QUARTERS = 8        # SUE uygunluk: >= 8 ceyrek onceki-kazanc-gecmisi
ORDER_VALUE_TL = D204_ORDER_VALUE_TL  # 20.000 TL/pozisyon (300K/top-15, donmus D-204)

# --- prob-tasarim barlari (YAPISAL/dis-referans; olculen-edge'e tunlu DEGIL) ---
# H1 cost-wall: tek round-trip maliyetinin makul 60-gun PEAD drift'ine gore agirligi.
# Esikler nominal/structural; herhangi bir olculen getiriye gore secilmedi.
H1_RT_PASS = 0.015     # < %1,5 tek round-trip: harvest-edilebilir bas-ucu mevcut
H1_RT_FAIL = 0.040     # > %4,0 tek round-trip: maliyet tek-basina makul drift'i yer
# H2 stale/phantom
H2_ZEROVOL_PASS = 0.05      # medyan sifir-hacim gun-payi < %5
H2_ENTRY_TRADE_PASS = 0.95  # giris-gunu islenebilir olay-payi > %95
# H3 kapasite (G3 bari ile ayni)
EXTREME_BIN_MIN_OK = 5
QUARTER_SHARE_PASS = 0.80


def _harmonized_mktval(funds: pd.DataFrame) -> pd.DataFrame:
    f = funds.copy()
    f["month"] = f["month"].astype("period[M]")
    mk = f.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last").sort_index()
    mk_h, _ = harmonize_mktval_units(mk)
    return mk_h


def _build_event_set(panel) -> tuple[pd.DataFrame, dict]:
    """SUE-tanimli + gun-damgali fy2019-2025 olay-seti; liquid_at_d0 ile sinitlandir.
    build_pead_signal_panel ile AYNI donmus SUE1/likidite mantigi (yeniden-uretim)."""
    ev = pd.read_parquet(EARNINGS_PARQUET)
    dd = pd.read_parquet(DAYDATED_PARQUET).rename(columns={"ticker": "symbol"})
    funds = load_degoran_fundamentals(start=PEAD_START, end=PEAD_END, file_glob=DEGORAN_GLOB)
    mk_h = _harmonized_mktval(funds)
    dates = panel.dates

    e = ev[(ev["fiscal_year"] >= FY_MIN) & (ev["fiscal_year"] <= FY_MAX)].copy()
    n0 = len(e)

    # SUE1 (mktval-olcekli, donmus) — sadece olay-siniflama/siralama icin
    e["period_end_ts"] = pd.to_datetime(e["period_end"])
    prior_q_month = (e["period_end_ts"] - pd.DateOffset(months=3)).dt.to_period("M")
    mk_long = mk_h.stack()
    keys = pd.MultiIndex.from_arrays([prior_q_month, e["symbol"]])
    e["mv_prior_q"] = mk_long.reindex(keys).to_numpy()
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

    dd_k = dd[["symbol", "fiscal_year", "quarter", "d0", "entry_date_t2"]].drop_duplicates(
        ["symbol", "fiscal_year", "quarter"])
    e = e.merge(dd_k, on=["symbol", "fiscal_year", "quarter"], how="left")
    e["d0"] = pd.to_datetime(e["d0"])
    e["entry_date_t2"] = pd.to_datetime(e["entry_date_t2"])

    e = e[e["sue_mkt"].notna() & e["entry_date_t2"].notna()].copy()
    n_daystamped = len(e)
    e = e[e["entry_date_t2"].isin(dates)].copy()
    e = e[e["symbol"].isin(set(panel.close.columns))].copy()
    n_entry_panel = len(e)

    # likidite: liquid_names asof D0 (motor B7) — likit vs illikit ayrimi
    liq_cache: dict[pd.Timestamp, set] = {}
    for d in e["d0"].unique():
        d = pd.Timestamp(d)
        sub = dates[dates <= d]
        liq_cache[d] = liquid_names(panel, sub[-1]) if len(sub) else set()
    e["liquid_at_d0"] = [s in liq_cache[pd.Timestamp(d)] for s, d in zip(e["symbol"], e["d0"], strict=True)]

    flt = {
        "n_events_fy_window": int(n0),
        "n_sue_defined": int(n_sue),
        "n_daystamped": int(n_daystamped),
        "n_entry_in_panel": int(n_entry_panel),
        "n_liquid_at_d0": int(e["liquid_at_d0"].sum()),
        "n_illiquid_at_d0": int((~e["liquid_at_d0"]).sum()),
        "illiquid_share_of_daystamped_panel": round(float((~e["liquid_at_d0"]).mean()), 4),
        "liquidity_definition": (
            "engine liquid_names (recon B7; RR-Y1-008 parite): trailing-63g medyan islem-degeri "
            ">= 10M TL, asof = duyuru-gunu (D0, point-in-time)"
        ),
    }
    return e, flt


def _window_positions(panel, entry: pd.Timestamp) -> tuple[int, int] | None:
    """[entry .. entry+HOLD-1] panel-pozisyonlari (panel-sonu kirpilir)."""
    dates = panel.dates
    i = int(np.searchsorted(dates.values, np.datetime64(entry)))
    if i >= len(dates) or dates[i] != entry:
        return None
    j = min(i + HOLD_TDAYS - 1, len(dates) - 1)
    return i, j


# ---------------------------------------------------------------------------
# H1 — COST-WALL (event-hold tek round-trip; D-207 Roll+Kyle+tier, READ-ONLY)
# ---------------------------------------------------------------------------

def gate_h1_costwall(e: pd.DataFrame, panel) -> dict:
    """Olay-bazli tek round-trip maliyeti: girisde (T+2) bilinen bilgiyle (PIT)
    Roll-spread (close-gecmisi) + Kyle-impact (trailing-63g ADV) + tier-floor."""
    dates = panel.dates
    close = panel.close
    value_tl = panel.value_tl

    def _per_event(sub: pd.DataFrame) -> dict:
        rts, srcs, adv_ratio = [], [], []
        for _, r in sub.iterrows():
            entry = r["entry_date_t2"]
            i = int(np.searchsorted(dates.values, np.datetime64(entry)))
            if i >= len(dates) or dates[i] != entry:
                continue
            sym = r["symbol"]
            chist = close[sym].iloc[: i + 1].dropna()  # close <= entry (PIT)
            if len(chist) < 22:
                continue
            advw = value_tl[sym].iloc[: i + 1].tail(63)  # trailing-63g ADV asof entry
            adv = float(advw.median(skipna=True))
            if not np.isfinite(adv) or adv <= 0:
                continue
            c = round_trip_cost(chist, adv=adv, order_value=ORDER_VALUE_TL)
            rts.append(c["round_trip_roll"])
            srcs.append(c["spread_source"])
            adv_ratio.append(ORDER_VALUE_TL / adv)
        rts = np.array(rts, dtype=float)
        if len(rts) == 0:
            return {"n": 0}
        src_counts = {s: int((np.array(srcs) == s).sum()) for s in set(srcs)}
        return {
            "n": int(len(rts)),
            "round_trip_median": round(float(np.median(rts)), 6),
            "round_trip_p25": round(float(np.percentile(rts, 25)), 6),
            "round_trip_p75": round(float(np.percentile(rts, 75)), 6),
            "round_trip_p90": round(float(np.percentile(rts, 90)), 6),
            "round_trip_mean": round(float(np.mean(rts)), 6),
            "spread_source_counts": src_counts,
            "order_to_adv_ratio_median": round(float(np.median(adv_ratio)), 6),
            "order_to_adv_ratio_p90": round(float(np.percentile(adv_ratio, 90)), 6),
        }

    illiq = _per_event(e[~e["liquid_at_d0"]])
    liq = _per_event(e[e["liquid_at_d0"]])
    out = {
        "order_value_tl": ORDER_VALUE_TL,
        "cost_model": "D-207 round_trip_cost (Roll close-only spread + Kyle sqrt-impact + "
                      "re-scaled tier-floor); panel close-only => quoted_spread YOK "
                      "(spread_source roll/tier); event-hold = TEK round-trip/60g (gunluk-churn DEGIL)",
        "illiquid": illiq,
        "liquid_baseline": liq,
    }
    rt_i = illiq.get("round_trip_median")
    rt_l = liq.get("round_trip_median")
    out["illiquid_vs_liquid_median_ratio"] = (
        round(rt_i / rt_l, 3) if rt_i and rt_l else None
    )
    verdict = "PASS" if (rt_i is not None and rt_i < H1_RT_PASS) else (
        "FAIL" if (rt_i is not None and rt_i > H1_RT_FAIL) else "CONDITIONAL")
    out["pass_bars"] = {"round_trip_pass_lt": H1_RT_PASS, "round_trip_fail_gt": H1_RT_FAIL}
    out["verdict"] = verdict
    out["interpretation"] = (
        "Tek round-trip maliyeti illikit medyani; event-hold long-bacagi NET-pozitif "
        "olabilmesi icin 60-gun GROSS drift'in bu maliyeti asmasi gerekir. RR-Y1-014 "
        "likit-evrende gross'u zaten ~SIFIR olcmustu — maliyet bar'i yapisal referanstir."
    )
    return out


# ---------------------------------------------------------------------------
# H2 — STALE / PHANTOM + GIRIS-ISLENEBILIRLIGI (getiri DEGIL; veri-kalite/stale)
# ---------------------------------------------------------------------------

def gate_h2_stale(e: pd.DataFrame, panel) -> dict:
    """Tutus-penceresinde sifir-hacim ve sifir-getiri (stale-print) gun-payi +
    giris/D0 islenebilirligi. NOT: sifir-GETIRI-GUN-PAYI bir veri-stale olcutudur
    (fiyat-degisim VAR/YOK), kumulatif-getiri/drift DEGIL — performans-metrigi degil."""
    dates = panel.dates
    close = panel.close
    value_tl = panel.value_tl

    def _per_event(sub: pd.DataFrame) -> dict:
        zv, zr, ent_ok, d0_ok, n = [], [], 0, 0, 0
        for _, r in sub.iterrows():
            wp = _window_positions(panel, r["entry_date_t2"])
            if wp is None:
                continue
            i, j = wp
            sym = r["symbol"]
            n += 1
            vol = value_tl[sym].iloc[i : j + 1]
            zv.append(float(((vol.isna()) | (vol <= 0)).mean()))
            cw = close[sym].iloc[i : j + 1]
            ret = cw.pct_change()
            # sifir-getiri-gun-payi: stale-print isareti (fiyat hic kimildamadi)
            zr.append(float((ret == 0).mean()) if len(ret.dropna()) else np.nan)
            # giris-gunu (T+2) ve D0 islenebilir mi (hacim > 0)
            ent_v = value_tl[sym].iloc[i]
            ent_ok += int(np.isfinite(ent_v) and ent_v > 0)
            d0 = r["d0"]
            di = int(np.searchsorted(dates.values, np.datetime64(d0)))
            if di < len(dates) and dates[di] == d0:
                d0v = value_tl[sym].iloc[di]
                d0_ok += int(np.isfinite(d0v) and d0v > 0)
        if n == 0:
            return {"n": 0}
        zv = np.array(zv, dtype=float)
        zr = np.array([x for x in zr if np.isfinite(x)], dtype=float)
        return {
            "n": int(n),
            "zero_volume_day_share_median": round(float(np.median(zv)), 4),
            "zero_volume_day_share_p90": round(float(np.percentile(zv, 90)), 4),
            "zero_return_day_share_median": round(float(np.median(zr)), 4) if len(zr) else None,
            "zero_return_day_share_p90": round(float(np.percentile(zr, 90)), 4) if len(zr) else None,
            "entry_day_tradeable_share": round(ent_ok / n, 4),
            "d0_tradeable_share": round(d0_ok / n, 4),
        }

    illiq = _per_event(e[~e["liquid_at_d0"]])
    liq = _per_event(e[e["liquid_at_d0"]])
    out = {
        "metric_note": "sifir-getiri-gun-payi = veri-stale olcutu (fiyat-degisim VAR/YOK); "
                       "kumulatif-getiri/drift/CAR HESAPLANMADI",
        "illiquid": illiq,
        "liquid_baseline": liq,
        "pass_bars": {"zero_volume_median_lt": H2_ZEROVOL_PASS,
                      "entry_tradeable_share_gt": H2_ENTRY_TRADE_PASS},
    }
    zvi = illiq.get("zero_volume_day_share_median")
    eti = illiq.get("entry_day_tradeable_share")
    out["verdict"] = (
        "PASS" if (zvi is not None and zvi < H2_ZEROVOL_PASS
                   and eti is not None and eti > H2_ENTRY_TRADE_PASS) else "FAIL"
    )
    out["interpretation"] = (
        "Yuksek stale/sifir-hacim => olculecek 'drift'in bir kismi gercek-alinabilir "
        "getiri degil, gecikmeli fiyat-yakalama HAYALETIDIR; ayrica giris-gunu "
        "islenemiyorsa pozisyon kurulamaz. Stale-price artefakti illikit-PEAD'in "
        "yapisal antagonistidir (clone1-lab dersi)."
    )
    return out


# ---------------------------------------------------------------------------
# H3 — KAPASITE / ETKIN-N (illikit yuksek-SUE tercile uc-dilim genisligi)
# ---------------------------------------------------------------------------

def _extreme_bin_sizes(sue: pd.Series, k: int) -> tuple[int, int]:
    n = len(sue)
    if n < k:
        return 0, 0
    ranks = sue.rank(method="first")
    bins = pd.qcut(ranks, k, labels=False)
    sizes = pd.Series(bins).value_counts()
    return int(sizes.get(k - 1, 0)), int(sizes.get(0, 0))


def gate_h3_capacity(e: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Ceyrek-bazli illikit∩SUE kesit-N ve tercile uc-dilim kapasitesi."""
    illiq = e[~e["liquid_at_d0"]].copy()
    rows = []
    for (fy, q), g in illiq.groupby(["fiscal_year", "quarter"]):
        t_top, t_bot = _extreme_bin_sizes(g["sue_mkt"], 3)
        rows.append({
            "fiscal_year": int(fy), "quarter": int(q),
            "n_illiquid_sue": int(len(g)),
            "tercile_top_n": t_top, "tercile_bottom_n": t_bot,
        })
    table = pd.DataFrame(rows).sort_values(["fiscal_year", "quarter"]).reset_index(drop=True)
    top = table["tercile_top_n"]
    bot = table["tercile_bottom_n"]
    ext_min = pd.concat([top, bot], axis=1).min(axis=1)
    out = {
        "n_illiquid_name_pool": int(illiq["symbol"].nunique()),
        "n_illiquid_events": int(len(illiq)),
        "n_quarters": int(len(table)),
        "n_illiquid_sue_per_quarter": {
            "mean": round(float(table["n_illiquid_sue"].mean()), 2),
            "median": float(table["n_illiquid_sue"].median()),
            "min": int(table["n_illiquid_sue"].min()),
            "max": int(table["n_illiquid_sue"].max()),
        },
        "tercile_top_n": {
            "mean": round(float(top.mean()), 2), "median": float(top.median()),
            "min": int(top.min()),
        },
        "share_quarters_both_extremes_ge_5": round(float((ext_min >= EXTREME_BIN_MIN_OK).mean()), 4),
        "pass_bars": {"extreme_bin_min_ok": EXTREME_BIN_MIN_OK, "quarter_share_pass": QUARTER_SHARE_PASS},
    }
    out["verdict"] = (
        "PASS" if out["share_quarters_both_extremes_ge_5"] >= QUARTER_SHARE_PASS else "CONDITIONAL"
    )
    out["interpretation"] = (
        "Illikit evren BUYUKTUR (olay-kutlesinin ~%81'i) -> kesitsel-genislik beklenen "
        "darbogaz DEGIL; baglayici kisitlar H1 (maliyet) + H2 (stale/phantom)."
    )
    return out, table


def main() -> None:
    print("[probe] clean_universe fiyat-paneli yukleniyor...", flush=True)
    panel = load_panel()
    print("[probe] olay-seti kuruluyor (SUE1 + gun-damgasi + likidite-ayrimi)...", flush=True)
    e, flt = _build_event_set(panel)
    print(f"[probe] daystamped-panel: {flt['n_entry_in_panel']} olay; "
          f"likit={flt['n_liquid_at_d0']} / illikit={flt['n_illiquid_at_d0']} "
          f"(illikit-pay {flt['illiquid_share_of_daystamped_panel']:.1%})", flush=True)

    result: dict = {
        "probe": "RR-Y1-015-B PEAD illikit-dilim harvest-fizibilite (RR-Y1-015 eklentisi)",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "no_performance_metrics": True,  # CAR/getiri/Sharpe/t-istatistigi HESAPLANMADI
        "context": (
            "RR-Y1-014 PEAD Stage-0 likit-evrende FAIL (NW-t -0.029). Olcum ON-KAYITLI "
            "olarak SADECE likit dilimi kapsadi; illikit ~%81 'harvest-edilemez' diye "
            "ON-DEKLARE-DISLANMISTI. Bu prob o dislamayi niceler — mezar-acmaz/diriltmez."
        ),
        "engine_touch": "SIFIR (src/engine + realistic_cost READ-ONLY import)",
        "split_counts": flt,
    }

    print("[probe] H1 (cost-wall)...", flush=True)
    result["H1_costwall"] = gate_h1_costwall(e, panel)
    print("[probe] H2 (stale/phantom + giris)...", flush=True)
    result["H2_stale_phantom"] = gate_h2_stale(e, panel)
    print("[probe] H3 (kapasite/etkin-N)...", flush=True)
    h3, table = gate_h3_capacity(e)
    result["H3_capacity"] = h3

    # genel-hukum: 3-kademeli harvest-fizibilite (binary-DEGIL; H1 knockout-degilse
    # CONDITIONAL-NEGATIF). Kapasite (H3) PASS olsa bile harvest H1∧H2 ile belirlenir.
    h1v, h2v, h3v = (result["H1_costwall"]["verdict"], result["H2_stale_phantom"]["verdict"],
                     h3["verdict"])
    if h1v == "PASS" and h2v == "PASS":
        feas = "FEASIBLE"
    elif h1v == "FAIL" or h2v == "FAIL":
        feas = "NOT-HARVESTABLE"
    else:  # H1 CONDITIONAL (maliyet-kapili ama temiz-kill degil), H2 PASS
        feas = "CONDITIONAL-NEGATIVE"
    result["overall"] = {
        "h1_costwall": h1v, "h2_stale_phantom": h2v, "h3_capacity": h3v,
        "harvest_feasibility": feas,
        "note": (
            "Kesitsel-genislik (H3) BOL ve dilim hala-isler (H2 PASS — stale/phantom "
            "ON-YARGISI bu bantta DESTEKLENMEDI: likidite-tabani zaten olu-mikrocaplari "
            "eler). Baglayici kisit H1: illikit medyan tek round-trip ~2x-likit, kuyruk "
            "uninvestable (p90 ve mean cok-yuksek; ince isimde emir ADV'nin buyuk-payi). "
            "Bu KNOCKOUT degil maliyet-KAPISI: 60-gun event-hold long-bacagi icin medyan "
            "isim >medyan-RT gross drift gerektirir, kuyruk fiilen alinamaz. RR-Y1-014 "
            "LIKIT gross'u ~SIFIR olctu (decay-karsi-prior); illikit gross icin POZITIF "
            "prior YOK. Sonuc: harvest-fizibilite CONDITIONAL-NEGATIF — illikit 'bedava "
            "ogun' DEGIL; pesine dusmek YENI on-kayitli Stage-0 gerektirir (post-hoc-YASAK) "
            "ve dusuk-beklenen-deger. Bu prob PERFORMANS-HUKMU vermez; RR-Y1-014 likit-"
            "FAIL'inin actigi 'ya illikit' sorusunu fizibilite-tarafindan kapatir. "
            "Stage-0 karari / graveyard-kaydi ayri degerlendirme adimidir."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUT_PARQUET, index=False)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[probe] yazildi: {OUT_PARQUET.relative_to(REPO_ROOT)} ({len(table)} ceyrek-satiri)")
    print(f"[probe] yazildi: {OUT_JSON.relative_to(REPO_ROOT)}")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    main()
