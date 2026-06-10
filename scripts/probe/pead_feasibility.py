"""RR-Y1-013 — PEAD veri-fizibilite probu (DISC-5 kapsam-guard).

FIZIBILITE PROBU — Stage-0 OLCUMU DEGIL, edge-testi DEGIL, sinyal DEGIL.

Tek soru: "Look-ahead-safe + survivorship-temiz + etkin-N-yeterli bir PEAD
olcum-paneli BIST verisiyle kurulabilir mi?" Dort kapi (G1-G4) RR-Y1-013
bolum-3 olcutleriyle test edilir; YALNIZ veri-kurulabilirlik istatistikleri
uretilir. CAR / getiri / drift-buyuklugu / Sharpe / t-istatistigi HESAPLANMAZ
(sonuc-gorme = Stage-0 kirletme). Tasarim-parametreleri (SUE1, T+2, 60g,
decile/tercile) dis-literaturle sabittir; burada yeniden-turetilmez.

Girdiler (hepsi read-only; committed-motor src/engine'e SIFIR yazim):
  - data/snapshots/earnings_dates.parquet (+ meta)  [devir-envanteri, RR-046 2a]
  - bist_datastore_archive degoran fundamentals (committed loader uzerinden)
  - data/clean_universe/adjusted_prices_2019_2026.parquet (engine data_adapter)
  - likit-evren tanimi = engine `liquid_names` (recon B7; RR-Y1-008 parite)
  - OPSIYONEL: MKK VYK KAP API spot-dogrulamasi (--kap-spot N; hard butce
    <= 40 cagri, L4-precedent; kimlik yoksa/sample=0 ise atlanir)

Ciktilar:
  - data/probe/pead_feasibility_summary.json     (kapi istatistikleri, kanit)
  - data/probe/pead_feasibility_summary.parquet  (G3 ceyrek-bazli etkin-N tablosu)
  - stdout: JSON ozet

Kullanim:
  python scripts/probe/pead_feasibility.py [--kap-spot 6] [--no-kap]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.clean_universe_fundamentals import load_degoran_fundamentals  # noqa: E402
from src.data.pead_snapshot_builder import (  # noqa: E402
    DEGORAN_GLOB,
    PEAD_END,
    PEAD_START,
    _announce_to_fiscal,
    _harmonized_net_profit_long,
)
from src.engine.data_adapter import liquid_names, load_panel  # noqa: E402
from src.screening.d206_nav_discount import harmonize_mktval_units  # noqa: E402

EARNINGS_PARQUET = REPO_ROOT / "data" / "snapshots" / "earnings_dates.parquet"
EARNINGS_META = REPO_ROOT / "data" / "snapshots" / "earnings_dates.meta.json"
OUT_DIR = REPO_ROOT / "data" / "probe"
OUT_PARQUET = OUT_DIR / "pead_feasibility_summary.parquet"
OUT_JSON = OUT_DIR / "pead_feasibility_summary.json"

# --- RR-Y1-013 bolum-3 kapi-olcutleri (direktif sabitleri; optimize edilmez) ---
EXTREME_BIN_MIN_OK = 5        # G3 PASS: her iki uc-dilimde >= 5 firma
EXTREME_BIN_MIN_HARD = 3      # G3 hard-floor: hicbir uc-dilim < 3
QUARTER_SHARE_PASS = 0.80     # G3 PASS: ceyreklerin >= %80'i
QUARTER_SHARE_COND_LO = 0.60  # G3 CONDITIONAL alt-siniri (tercile-only)
G1_PIT_VERIFIABLE_MIN = 0.95  # G1 PASS: kayitlarin >= %95'i KAP-PIT-dogrulanabilir
# TMS-29 (enflasyon muhasebesi) ilk uygulama: FY2023 yillik finansallar.
# UE_t = Q_t - Q_{t-4q}; straddle = Q_t TMS-29-donemi AMA Q_{t-4q} oncesi.
TMS29_FIRST_PERIOD_END = pd.Timestamp("2023-12-31")
MKTVAL_JUMP_HI = 5.0          # harmonizasyon-sonrasi residual MoM sicrama esigi
MKTVAL_JUMP_LO = 0.2
DELIST_BUFFER_TDAYS = 60      # panel sonundan >= N islem-gunu once susan isim = delist-adayi
DRIFT_WINDOW_TDAYS = 60       # sabit tasarim-parametresi (bolum-2): 60 isgunu tutus
HEADLINE_FY_MIN = 2019        # G3 baslik-tablosu: likidite-verisinin tam oldugu mali-yillar
HEADLINE_FY_MAX = 2025
KAP_SPOT_MAX_CALLS = 40       # hard API butcesi (clean_universe L4 precedent)
KAP_SPOT_DETAILS_PER_SYM = 4
KAP_MIN_DISCLOSURE_INDEX = 538004  # KAP 4.0 oncesi html-only (fetcher ile ayni esik)
KAP_SPOT_SYMBOLS = ["THYAO", "ASELS", "TUPRS", "BIMAS", "SISE", "AKSEN"]


def _month_period(s: pd.Series) -> pd.PeriodIndex:
    return pd.PeriodIndex(s.astype(str), freq="M")


def _load_inputs() -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Frozen earnings paneli + meta + degoran fundamentals (read-only)."""
    ev = pd.read_parquet(EARNINGS_PARQUET)
    meta = json.loads(EARNINGS_META.read_text(encoding="utf-8"))
    funds = load_degoran_fundamentals(start=PEAD_START, end=PEAD_END, file_glob=DEGORAN_GLOB)
    return ev, meta, funds


def _harmonized_mktval_pivot(funds: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aylik mktval pivotu, market-capli D-206 redenominasyon-harmonizasyonu ile."""
    f = funds.copy()
    f["month"] = f["month"].astype("period[M]")
    mk = f.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last").sort_index()
    mk_h, hmeta = harmonize_mktval_units(mk)
    return mk_h, hmeta


# ---------------------------------------------------------------------------
# G1 — kazanc-duyuru-tarihi PIT-temizligi
# ---------------------------------------------------------------------------

def gate1_pit(ev: pd.DataFrame, funds: pd.DataFrame) -> dict:
    """Duyuru-tarihi kaynagi, restate-vs-ilk-duyuru ayrimi, gun-cozunurluk durumu."""
    out: dict = {}
    out["n_records"] = int(len(ev))
    out["source_breakdown"] = {str(k): int(v) for k, v in ev["source"].value_counts().items()}
    out["resolution"] = "month (degoran step-change proxy); gun-damgasi YOK"

    # restate-vs-ilk-duyuru: dedup'suz step-tespiti -> ayni (sym, fy, q)'ya birden
    # fazla step-ayi dusen vakalar (restate/duzeltme/ikinci-set ADAYI; ust-sinir).
    # Frozen panel en-ERKEN step'i tutar => ilk-duyuru korunur (insaat-geregi).
    npl, _ = _harmonized_net_profit_long(funds)
    npl = npl.sort_values(["symbol", "month"])
    npl = npl[npl["net_profit_h"].notna()].copy()
    prev = npl.groupby("symbol")["net_profit_h"].shift(1)
    steps = npl[prev.notna() & (npl["net_profit_h"] != prev)].copy()
    fis = steps["month"].map(_announce_to_fiscal)
    steps["fiscal_year"] = fis.map(lambda t: t[0])
    steps["quarter"] = fis.map(lambda t: t[1])
    grp = steps.groupby(["symbol", "fiscal_year", "quarter"]).size()
    out["redetect_n_steps_raw"] = int(len(steps))
    out["redetect_n_quarters"] = int(len(grp))
    out["multi_step_quarters"] = int((grp > 1).sum())
    out["multi_step_share"] = round(float((grp > 1).mean()), 4)
    out["first_announce_kept_by_construction"] = True

    # devir-envanteri butunlugu: frozen panel == bugunku arsivden re-detect mi?
    frozen_keys = set(map(tuple, ev[["symbol", "fiscal_year", "quarter"]].values))
    redet_keys = set(grp.index)
    inter = len(frozen_keys & redet_keys)
    out["frozen_vs_redetect"] = {
        "frozen_quarters": len(frozen_keys),
        "redetect_quarters": len(redet_keys),
        "frozen_found_in_redetect_share": round(inter / max(len(frozen_keys), 1), 4),
    }

    # gun-cozunurluklu KAP-PIT verisi LOKAL var mi? (kap_fr_* cache'leri)
    cache_dir = REPO_ROOT / "data" / "cache"
    kap_rows = 0
    kap_files = sorted(cache_dir.glob("kap_fr_*.parquet"))
    for fp in kap_files:
        try:
            kap_rows += len(pd.read_parquet(fp))
        except Exception:  # bozuk cache dosyasi sayilmaz
            pass
    out["local_kap_cache"] = {"n_files": len(kap_files), "n_rows": int(kap_rows)}
    out["kap_day_resolution_available_locally"] = bool(kap_rows > 0)
    out["kap_fetch_pathway"] = (
        "src/data/kap_historical_fetcher.py (D-170/172, MKK VYK API; publication_date alani) "
        f"— KAP 4.0 oncesi (disclosureIndex < {KAP_MIN_DISCLOSURE_INDEX}) html-only, XBRL yok"
    )
    out["weekend_afterhours_mapping"] = (
        "ay-cozunurlugunde UYGULANAMAZ; gun-damgasi (KAP Katman-2) gerektirir"
    )
    return out


# ---------------------------------------------------------------------------
# G2 — SUE-hesaplanabilirligi ve muhasebe-rejimi tutarliligi
# ---------------------------------------------------------------------------

def gate2_sue(ev: pd.DataFrame, mk_h: pd.DataFrame) -> dict:
    """IBQ/SUE firma-ceyrek sayilari, SUE1-payda kapsami, TMS-29 straddle isaretlemesi."""
    out: dict = {}
    out["n_events"] = int(len(ev))
    out["n_symbols"] = int(ev["symbol"].nunique())
    out["n_decum_ok"] = int(ev["decum_ok"].sum())
    out["n_net_profit_q"] = int(ev["net_profit_q"].notna().sum())
    out["n_ue_defined"] = int(ev["ue"].notna().sum())
    out["n_sue_defined"] = int(ev["sue"].notna().sum())
    out["sue_defined_share_of_events"] = round(float(ev["sue"].notna().mean()), 4)

    # SUE1 (direktif bolum-2 formu) paydasi: onceki-ceyrek-sonu ozkaynak-PIYASA-degeri.
    # degoran mktval aylik-surekli (2009-01..) => iki aday-ay icin kapsam olculur:
    #   (a) period_end ayi (ceyrek-sonu), (b) announce_month - 1 (duyuru-oncesi son ay).
    ue_ev = ev[ev["ue"].notna()].copy()
    am = _month_period(ue_ev["announce_month"])
    pe_m = pd.PeriodIndex(pd.to_datetime(ue_ev["period_end"]), freq="M")
    mk_long = mk_h.stack()
    keys_pe = pd.MultiIndex.from_arrays([pe_m, ue_ev["symbol"]])
    keys_pre = pd.MultiIndex.from_arrays([am - 1, ue_ev["symbol"]])
    cov_pe = mk_long.reindex(keys_pe).notna()
    cov_pre = mk_long.reindex(keys_pre).notna()
    out["sue1_denominator_coverage"] = {
        "n_ue_events": int(len(ue_ev)),
        "mktval_at_period_end_month": round(float(cov_pe.mean()), 4),
        "mktval_at_announce_minus_1": round(float(cov_pre.mean()), 4),
    }

    # muhasebe-rejimi: degoran TEK saglayici-serisidir (konsolide); TPC-vs-IFRS coklu-set
    # ayrimi lokal olarak YAPILAMAZ. Coklu-set/duzeltme imzasi = G1 multi_step_share.
    out["regime_note"] = (
        "degoran tek-seri (saglayici-secimi sabit); TPC/IFRS coklu-set ayrimi lokal "
        "yapilamaz — imza-istatistigi G1.multi_step_share"
    )

    # TMS-29 enflasyon-muhasebesi kirigi: UE_t = Q_t - Q_{t-4q}. Straddle-ceyrekler
    # (Q_t TMS-29-sonrasi, Q_{t-4q} oncesi) = period_end in [2023-12-31, 2024-12-30].
    sue_ev = ev[ev["sue"].notna()].copy()
    pe = pd.to_datetime(sue_ev["period_end"])
    straddle = (pe >= TMS29_FIRST_PERIOD_END) & (pe < TMS29_FIRST_PERIOD_END + pd.DateOffset(years=1))
    out["tms29"] = {
        "boundary_period_end": str(TMS29_FIRST_PERIOD_END.date()),
        "n_sue_straddle": int(straddle.sum()),
        "straddle_share_of_sue": round(float(straddle.mean()), 4),
        "flaggable_isolable": True,  # period_end panelde => mekanik filtre/isaret mumkun
        "note": "straddle-ceyrekler period_end ile isaretlenebilir/dislanabilir; "
                "2025+ ceyrekler TMS29-vs-TMS29 (tutarli cift)",
    }
    return out


# ---------------------------------------------------------------------------
# G3 — likit-evren kapasitesi (etkin-N)
# ---------------------------------------------------------------------------

def _extreme_bin_sizes(sue: pd.Series, k: int) -> tuple[int, int]:
    """Rank-tabanli k-dilim (qcut) altinda (ust-dilim N, alt-dilim N). n<k => (0,0)."""
    n = len(sue)
    if n < k:
        return 0, 0
    ranks = sue.rank(method="first")
    bins = pd.qcut(ranks, k, labels=False)
    sizes = pd.Series(bins).value_counts()
    return int(sizes.get(k - 1, 0)), int(sizes.get(0, 0))


def gate3_effective_n(ev: pd.DataFrame, panel) -> tuple[dict, pd.DataFrame]:
    """Ceyrek-bazli likit∩SUE-temiz kesit-N ve decile/tercile uc-dilim kapasitesi."""
    dates = panel.close.index
    panel_syms = set(panel.close.columns)

    evs = ev[ev["sue"].notna()].copy()
    evs["am"] = _month_period(evs["announce_month"])
    p0, p1 = dates[0].to_period("M"), dates[-1].to_period("M")
    evs = evs[(evs["am"] >= p0) & (evs["am"] <= p1)].copy()

    # her duyuru-ayi icin asof = ay-sonuna kadarki son islem-gunu; likit-set cache'li
    liq_cache: dict[pd.Period, set] = {}
    asof_cache: dict[pd.Period, pd.Timestamp | None] = {}
    for m in evs["am"].unique():
        sub = dates[dates <= m.end_time]
        asof = sub[-1] if len(sub) else None
        asof_cache[m] = asof
        liq_cache[m] = liquid_names(panel, asof) if asof is not None else set()

    evs["in_price_panel"] = evs["symbol"].isin(panel_syms)
    evs["liquid"] = [
        s in liq_cache[m] for s, m in zip(evs["symbol"], evs["am"], strict=True)
    ]

    rows = []
    for (fy, q), g in evs.groupby(["fiscal_year", "quarter"]):
        liq = g[g["liquid"]]
        d_top, d_bot = _extreme_bin_sizes(liq["sue"], 10)
        t_top, t_bot = _extreme_bin_sizes(liq["sue"], 3)
        rows.append({
            "fiscal_year": int(fy), "quarter": int(q),
            "n_sue_all": int(len(g)),
            "n_in_price_panel": int(g["in_price_panel"].sum()),
            "n_liquid_sue": int(len(liq)),
            "decile_top_n": d_top, "decile_bottom_n": d_bot,
            "tercile_top_n": t_top, "tercile_bottom_n": t_bot,
        })
    table = pd.DataFrame(rows).sort_values(["fiscal_year", "quarter"]).reset_index(drop=True)

    head = table[(table["fiscal_year"] >= HEADLINE_FY_MIN) & (table["fiscal_year"] <= HEADLINE_FY_MAX)]

    def _bin_stats(top: pd.Series, bot: pd.Series) -> dict:
        ext_min = pd.concat([top, bot], axis=1).min(axis=1)
        return {
            "quarters": int(len(head)),
            "top_mean": round(float(top.mean()), 2), "top_median": float(top.median()),
            "top_min": int(top.min()),
            "bottom_mean": round(float(bot.mean()), 2), "bottom_median": float(bot.median()),
            "bottom_min": int(bot.min()),
            "share_quarters_both_ge_5": round(float((ext_min >= EXTREME_BIN_MIN_OK).mean()), 4),
            "n_quarters_any_lt_3": int((ext_min < EXTREME_BIN_MIN_HARD).sum()),
        }

    out: dict = {
        "headline_fy_range": [HEADLINE_FY_MIN, HEADLINE_FY_MAX],
        "liquidity_definition": (
            "engine liquid_names (recon B7; RR-Y1-008 parite): trailing-63g medyan islem-degeri "
            ">= 10M TL, asof = duyuru-ayinin son islem-gunu (point-in-time)"
        ),
        "n_liquid_sue_per_quarter": {
            "mean": round(float(head["n_liquid_sue"].mean()), 2),
            "median": float(head["n_liquid_sue"].median()),
            "min": int(head["n_liquid_sue"].min()),
            "max": int(head["n_liquid_sue"].max()),
        },
        "decile": _bin_stats(head["decile_top_n"], head["decile_bottom_n"]),
        "tercile": _bin_stats(head["tercile_top_n"], head["tercile_bottom_n"]),
        # sinyal-en-guclu illikit bolge harvest-evreninin disinda mi? (bulgu, eleme degil)
        "liquidity_exclusion_share_mean": round(
            float((1.0 - head["n_liquid_sue"] / head["n_sue_all"]).mean()), 4
        ),
        "pass_bars": {
            "extreme_bin_min_ok": EXTREME_BIN_MIN_OK,
            "extreme_bin_min_hard": EXTREME_BIN_MIN_HARD,
            "quarter_share_pass": QUARTER_SHARE_PASS,
            "quarter_share_conditional_lo": QUARTER_SHARE_COND_LO,
        },
    }
    return out, table


# ---------------------------------------------------------------------------
# G4 — corporate-action / delisted butunlugu
# ---------------------------------------------------------------------------

def gate4_corpaction_delisted(ev: pd.DataFrame, mk_h: pd.DataFrame, panel) -> dict:
    """Harmonizasyon-sonrasi residual mktval sicramalari (+ ca_code aciklanabilirligi),
    delisted-duyuru kapsami, drift-penceresi-ici delisting sayimi."""
    out: dict = {}

    # 4a — SUE1-paydasi (mktval) corp-action zinciri: residual MoM sicramalar
    ratio = mk_h / mk_h.shift(1)
    valid = ratio.notna()
    jumps = ((ratio > MKTVAL_JUMP_HI) | (ratio < MKTVAL_JUMP_LO)) & valid
    out["mktval_residual_jumps"] = {
        "threshold": f">{MKTVAL_JUMP_HI}x veya <{MKTVAL_JUMP_LO}x (harmonizasyon-sonrasi)",
        "n_transitions": int(valid.values.sum()),
        "n_jumps": int(jumps.values.sum()),
        "jump_rate": round(float(jumps.values.sum() / max(valid.values.sum(), 1)), 6),
        "note": "ust-sinir: gercek bedelli/birlesme mktval'i mesru olarak sicratir "
                "(mcap split-notr; payda icin hata degil)",
    }

    # ca_code aciklanabilirligi (DISC-8-uyum yonunde): 2019+ sicramalarin kacinda ayni
    # ay clean_universe ca_code olayi var?
    px = pd.read_parquet(REPO_ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet",
                         columns=["date", "symbol", "ca_code"])
    px = px[px["ca_code"].notna() & (px["ca_code"].astype(str).str.strip() != "")]
    ca_months = set(zip(pd.to_datetime(px["date"]).dt.to_period("M"), px["symbol"], strict=True))
    j_long = jumps.stack()
    j_idx = j_long[j_long].index  # (month, symbol)
    j2019 = [(m, s) for m, s in j_idx if m >= pd.Period("2019-01", "M")]
    n_explained = sum(1 for m, s in j2019 if (m, s) in ca_months or (m - 1, s) in ca_months)
    out["mktval_jumps_2019plus_ca_explained"] = {
        "n_jumps_2019plus": len(j2019),
        "n_with_ca_code_same_or_prev_month": int(n_explained),
        "explained_share": round(n_explained / max(len(j2019), 1), 4),
    }

    # 4b — delisted-duyuru kapsami (survivorship)
    dates = panel.close.index
    last_valid = panel.close.apply(lambda s: s.last_valid_index())
    pos = pd.Series(np.arange(len(dates)), index=dates)
    cutoff_pos = len(dates) - 1 - DELIST_BUFFER_TDAYS
    delisted = last_valid[last_valid.map(lambda d: d is not None and pos[d] <= cutoff_pos)]
    ev_syms = set(ev["symbol"])
    delisted_syms = set(delisted.index)
    delisted_in_ev = delisted_syms & ev_syms
    # listede-iken duyurusu olan delisted isimler
    am_all = _month_period(ev["announce_month"])
    ev_m = pd.DataFrame({"symbol": ev["symbol"].values, "am": am_all})
    last_m = {s: d.to_period("M") for s, d in delisted.items()}
    has_live_ann = {
        s for s in delisted_in_ev
        if (ev_m[(ev_m["symbol"] == s)]["am"] <= last_m[s]).any()
    }
    out["delisted_coverage"] = {
        "buffer_trading_days": DELIST_BUFFER_TDAYS,
        "n_delisted_candidates_in_price_panel": int(len(delisted_syms)),
        "n_delisted_with_earnings_history": int(len(delisted_in_ev)),
        "n_delisted_with_announcement_while_listed": int(len(has_live_ann)),
        "earnings_symbols_not_in_price_panel": int(len(ev_syms - set(panel.close.columns))),
        "note": "price-panel 2019-2026; earnings-panel 2009+ (2019-oncesi delistler "
                "fiyat-panelinde olamaz — pencere-farki, survivorship-kirpma degil)",
    }

    # 4c — drift-penceresi-ici delisting (duyuru sonrasi <= ~60 islem-gunu icinde susan)
    evs = ev.copy()
    evs["am"] = am_all
    evs = evs[evs["symbol"].isin(set(panel.close.columns))]
    evs = evs[(evs["am"] >= dates[0].to_period("M")) & (evs["am"] <= dates[-1].to_period("M"))]
    n_in_window_all = 0
    n_in_window_sue = 0
    entry_pos_cache: dict[pd.Period, int | None] = {}
    for m in evs["am"].unique():
        # giris-proxy: consume_from_month'un (announce+1) ilk islem-gunu (ay-cozunurluk)
        start = (m + 1).start_time
        i = int(np.searchsorted(dates.values, np.datetime64(start)))
        entry_pos_cache[m] = i if i < len(dates) else None
    for _, r in evs.iterrows():
        s = r["symbol"]
        if s not in delisted_syms:
            continue
        ep = entry_pos_cache[r["am"]]
        lv = last_valid.get(s)
        if ep is None or lv is None:
            continue
        gap = int(pos[lv]) - ep
        if 0 <= gap < DRIFT_WINDOW_TDAYS + 2:  # T+2 + 60g tutusun ay-proxy karsiligi
            n_in_window_all += 1
            if pd.notna(r["sue"]):
                n_in_window_sue += 1
    out["delist_within_drift_window"] = {
        "n_events_all": int(n_in_window_all),
        "n_events_sue_defined": int(n_in_window_sue),
        "handleable": True,
        "note": "fiyat-paneli delist-gunune kadar dolu (insaat-geregi) => "
                "delist-gunune-kadar-getiri hesaplanabilir; vaka sayisi dusukse "
                "ele-alim Stage-0 tasarim-notu olur",
    }
    return out


# ---------------------------------------------------------------------------
# OPSIYONEL — KAP spot-dogrulamasi (G1 kaniti; hard butce <= 40 cagri)
# ---------------------------------------------------------------------------

def _map_period_to_quarter(period_raw: str) -> int | None:
    """KAP period metnini ceyrege esle (orn. '01.01.2024-31.12.2024' / 'Yillik')."""
    s = str(period_raw or "").lower()
    for em, q in ((".03.", 1), (".06.", 2), (".09.", 3), (".12.", 4)):
        if s.count(em) and s.rstrip().endswith(tuple(str(y) for y in range(1990, 2040))):
            # tarih-araligi formati: bitis-ayina gore
            tail = s.split("-")[-1]
            if em in tail:
                return q
    if "yıllık" in s or "yillik" in s or "annual" in s:
        return 4
    return None


def kap_spot_check(ev: pd.DataFrame, symbols: list[str]) -> dict:
    """Ornekleme-tabanli KAP-PIT spot-dogrulamasi: KAP yayin-tarihi (gun-damgasi) ile
    panel announce_month uyusuyor mu? Kimlik yoksa veya API hatasinda sessizce degrade."""
    out: dict = {"attempted": True, "symbols_requested": symbols}
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass
    import os
    if not (os.getenv("MKK_VYK_BASE_URL") and os.getenv("MKK_VYK_TOKEN")):
        out["status"] = "skipped: MKK_VYK kimligi tanimsiz (auth-gated)"
        return out

    from src.data.kap_api_client import KapApiError
    from src.data.kap_historical_fetcher import _make_client, build_company_map

    calls = 0
    rows: list[dict] = []
    try:
        client = _make_client()
        cmap = build_company_map()  # 24h-cache'li; cache-miss = 1 cagri
        calls += 1
        t2id = {v.upper(): k for k, v in cmap.items() if v}
        for sym in symbols:
            if calls >= KAP_SPOT_MAX_CALLS:
                break
            cid = t2id.get(sym)
            if cid is None:
                rows.append({"symbol": sym, "error": "companyId yok"})
                continue
            discs = client.get_disclosures(start_index=0, disclosure_class="FR",
                                           company_id=int(cid))
            calls += 1
            idxs = sorted(
                (int(d["disclosureIndex"]) for d in discs
                 if d.get("disclosureIndex") and int(d["disclosureIndex"]) >= KAP_MIN_DISCLOSURE_INDEX),
                reverse=True,
            )
            taken = 0
            for ix in idxs:
                if taken >= KAP_SPOT_DETAILS_PER_SYM or calls >= KAP_SPOT_MAX_CALLS:
                    break
                detail = client.get_disclosure_detail(ix, file_type="data")
                calls += 1
                subject = (detail.get("subject") or {})
                subj_en = subject.get("en") if isinstance(subject, dict) else str(subject)
                if subj_en != "Financial Report":
                    continue
                taken += 1
                period = detail.get("period") or {}
                period_raw = period.get("tr") if isinstance(period, dict) else str(period)
                t = str(detail.get("time") or "")
                pub = t.split(" ")[0]  # 'dd.mm.yyyy hh:mm:ss'
                p = pub.split(".")
                pub_iso = f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}" if len(p) == 3 else None
                rows.append({
                    "symbol": sym, "disclosure_index": ix,
                    "kap_year": detail.get("year"), "kap_period_raw": period_raw,
                    "kap_pub_date": pub_iso,
                })
    except KapApiError as exc:
        out["status"] = f"degraded: KAP API hatasi ({exc})"
    except Exception as exc:  # probe asla crash etmez; kanit eksikligi raporlanir
        out["status"] = f"degraded: {type(exc).__name__}: {exc}"

    out["api_calls_used"] = calls

    # eslestirme: KAP yayin-ayi vs panel announce_month (ayni symbol, fy, q)
    matched = []
    for r in rows:
        if not r.get("kap_pub_date"):
            continue
        q = _map_period_to_quarter(r.get("kap_period_raw"))
        r["quarter_mapped"] = q
        if q is None or r.get("kap_year") is None:
            matched.append({**r, "match": "period-eslesmedi"})
            continue
        hit = ev[(ev["symbol"] == r["symbol"])
                 & (ev["fiscal_year"] == int(r["kap_year"]))
                 & (ev["quarter"] == q)]
        if hit.empty:
            matched.append({**r, "match": "panelde-yok"})
            continue
        panel_m = pd.Period(hit.iloc[0]["announce_month"], "M")
        kap_m = pd.Period(r["kap_pub_date"][:7], "M")
        diff = (kap_m - panel_m).n
        matched.append({**r, "panel_announce_month": str(panel_m), "month_diff": int(diff),
                        "match": "exact" if diff == 0 else ("pm1" if abs(diff) == 1 else "far")})
    n_cmp = sum(1 for m in matched if "month_diff" in m)
    out["n_details_fetched"] = len(rows)
    out["n_comparable"] = n_cmp
    out["n_exact_month"] = sum(1 for m in matched if m.get("match") == "exact")
    out["n_within_1_month"] = sum(1 for m in matched if m.get("match") in ("exact", "pm1"))
    # restate imzasi: ayni (symbol, yil, ceyrek) icin birden fazla FR detayi
    seen: dict[tuple, int] = {}
    for m in matched:
        if m.get("quarter_mapped") is not None and m.get("kap_year") is not None:
            k = (m["symbol"], m["kap_year"], m["quarter_mapped"])
            seen[k] = seen.get(k, 0) + 1
    out["n_duplicate_period_filings"] = sum(1 for v in seen.values() if v > 1)
    out["evidence_rows"] = matched
    out.setdefault("status", "ok")
    return out


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="RR-Y1-013 PEAD veri-fizibilite probu")
    ap.add_argument("--kap-spot", type=int, default=len(KAP_SPOT_SYMBOLS),
                    help="KAP spot-dogrulamasi icin sembol sayisi (0 = atla)")
    ap.add_argument("--no-kap", action="store_true", help="KAP spot-dogrulamasini atla")
    args = ap.parse_args()

    print("[probe] frozen earnings paneli + degoran fundamentals yukleniyor...", flush=True)
    ev, meta, funds = _load_inputs()
    print(f"[probe] earnings: {len(ev)} satir, {ev['symbol'].nunique()} sembol; "
          f"degoran: {len(funds)} satir", flush=True)

    mk_h, hmeta = _harmonized_mktval_pivot(funds)
    print("[probe] clean_universe fiyat-paneli yukleniyor (engine data_adapter)...", flush=True)
    panel = load_panel()

    result: dict = {
        "probe": "RR-Y1-013 PEAD veri-fizibilite (DISC-5 kapsam-guard)",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "no_performance_metrics": True,  # CAR/getiri/Sharpe/t-istatistigi HESAPLANMADI
        "inputs": {
            "earnings_panel": str(EARNINGS_PARQUET.relative_to(REPO_ROOT)),
            "earnings_meta_timestamp": meta.get("timestamp_utc"),
            "degoran_rows": int(len(funds)),
            "mktval_harmonization": hmeta,
            "price_panel": "data/clean_universe/adjusted_prices_2019_2026.parquet "
                           f"({panel.close.shape[1]} sembol x {panel.close.shape[0]} gun)",
        },
    }

    print("[probe] G1 (PIT-temizlik)...", flush=True)
    result["G1_pit"] = gate1_pit(ev, funds)
    print("[probe] G2 (SUE/muhasebe)...", flush=True)
    result["G2_sue"] = gate2_sue(ev, mk_h)
    print("[probe] G3 (etkin-N)...", flush=True)
    g3, table = gate3_effective_n(ev, panel)
    result["G3_effective_n"] = g3
    print("[probe] G4 (corp-action/delisted)...", flush=True)
    result["G4_corpaction_delisted"] = gate4_corpaction_delisted(ev, mk_h, panel)

    if args.no_kap or args.kap_spot <= 0:
        result["kap_spot"] = {"attempted": False, "status": "skipped: kullanici-istegi"}
    else:
        print("[probe] KAP spot-dogrulamasi (butce <= 40 cagri)...", flush=True)
        result["kap_spot"] = kap_spot_check(ev, KAP_SPOT_SYMBOLS[: args.kap_spot])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUT_PARQUET, index=False)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"[probe] yazildi: {OUT_PARQUET.relative_to(REPO_ROOT)} ({len(table)} ceyrek-satiri)")
    print(f"[probe] yazildi: {OUT_JSON.relative_to(REPO_ROOT)}")
    print(json.dumps({k: v for k, v in result.items() if k != "kap_spot"}, ensure_ascii=True, indent=2))
    ks = dict(result["kap_spot"])
    ks.pop("evidence_rows", None)
    print("[kap_spot]", json.dumps(ks, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    main()
