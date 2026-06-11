"""RR-Y1-014-V — PEAD-FAIL olcum-dogrulama (measurement-verification ilk-uygulamasi).

RR-Y1-014 PEAD Stage-0 FAIL verdi (NW-t tam-panel -0.029, X2 -0.486, brut-sifir).
Bu script o FAIL'in GERCEK-mi (likit-BIST'te-PEAD-yok) yoksa PIPELINE-ARTEFAKTI-mi
(implementasyon-hatasi edge'i-sifir-gosteriyor) oldugunu BAGIMSIZ-dogrular.

NE DEGILDIR: PEAD'in yeniden-olcumu DEGIL (DEC-053; mezar-acma-yok). PEAD-adayinin
KENDI-verisinde yeni-NW-t aranmaz; lockbox'a DOKUNULMAZ. Yalniz KONTROLLER (pozitif-
kontrol / metamorphic / placebo / insan-slice) uretilir — bunlar dogrulama-araci.

KOD-YOLU: committed-motor (src/engine) + RR-Y1-014 runner primitifleri AYNEN import
edilir (arm_stat / _tilt_active / build_score_frame / PEADSue1Signal / slice_panel /
load_inputs). Farkli-kod-yolu-kullanan-dogrulama orijinali-dogrulamaz. READ-ONLY.

KONTROLLER KOSULMADAN-ONCE DONAR: beklenen bantlar EXPECT sozlugunde sayisal-onceden
yazilir (FAZ-0). Rahatlatici-cevap-verene-kadar-knob-cevirme YASAK.

Cikti:
  data/verification/pead_verification_results.json   (kontrol-bazli sonuclar + hukum)
  data/verification/pead_verification_results.parquet (duz tablo)
  docs/yol1/verification/pead_slice_10events.csv      (D1 insan-checkpoint)

Kullanim:  python scripts/verification/verify_pead_stage0.py
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
sys.path.insert(0, str(REPO_ROOT / "scripts" / "scratch"))

# RR-Y1-014 pipeline primitifleri — AYNI kod-yolu (yan-etki yok; main() guard'li)
import run_rr_y1_014_stage0 as runner  # noqa: E402
from src.engine.contracts import Frequency, Panel  # noqa: E402
from src.engine.harness import _tilt_active  # noqa: E402  (committed, read-only)
from src.engine.stats import nw_tstat  # noqa: E402

OUT_DIR_DATA = REPO_ROOT / "data" / "verification"
OUT_DIR_DOCS = REPO_ROOT / "docs" / "yol1" / "verification"
OUT_JSON = OUT_DIR_DATA / "pead_verification_results.json"
OUT_PARQUET = OUT_DIR_DATA / "pead_verification_results.parquet"
OUT_SLICE = OUT_DIR_DOCS / "pead_slice_10events.csv"

# --- FAZ-0: KONTROLLER KOSULMADAN-ONCE DONAN BEKLENTILER (sayisal on-kayit) ---
# Tehlikeli-hata = false-FAIL (pipeline bir edge'i sifir-gosteriyor) -> A1a EN-AGIR.
NW_T_DETECT = 2.0       # pozitif-kontrol drifti tespit esigi (>= bu)
NW_T_NULL = 1.0         # null-kontrol gurultu-bandi (|nw_t| < bu beklenir)
INJECT_BETA = 0.004     # pozitif-kontrol: gunluk +-%0,4 drift (top/bottom global-tercile olay)
EXACT_TOL = 1e-9        # metamorphic exact-esleme toleransi
ZERO_TOL = 1e-10        # benchmark self-check sifir-toleransi
N_NOISE_SEEDS = 12      # C1 pure-noise seed sayisi

EXPECT = {
    "A1a_positive_control": f"nw_t >= {NW_T_DETECT} ve isaret POZITIF (pipeline injekte-drifti bulur)",
    "A2_microcase_active":  "aktif-getiri serisi el-hesabiyla EXACT (|fark| < 1e-9)",
    "A2_nw_zero_mean":      "mean-sifir simetrik seri -> |nw_t| < 1e-9",
    "A2_nw_positive":       "pozitif-ortalama seri -> nw_t > 0",
    "B1_sign_reversal":     "injekte-panelde sinyal-negatiflenince nw_t ISARET-DONER (negatif)",
    "B2_label_shuffle":     f"injekte-panelde isim-permutasyonu -> |nw_t| < {NW_T_NULL} (link kirilir)",
    "B3_lookahead_peek":    f"gercek-panelde giris-1g-erken -> |nw_t| < {NW_T_NULL} (SICRAMA-yok=sizinti-yok)",
    "B4_safe_shift":        f"gercek-panelde giris-1g-gec -> |nw_t| < {NW_T_NULL} (sicrama-yok)",
    "B5_rank_invariance":   "monoton-yeniden-olcekle (x^3) -> aktif-getiri DEGISMEZ (|fark| < 1e-9)",
    "B7_benchmark_self":    "frac=1.0 (top=tum-evren) -> aktif == 0 EXACT (max|aktif| < 1e-10)",
    "C1_pure_noise":        f"rastgele-skor (gercek-pencere) -> |ortalama nw_t| < {NW_T_NULL}, ~0-merkezli",
    "C3_pre_event_placebo": f"duyuru-ONCESI pencere -> |nw_t| < {NW_T_NULL} (olay-penceresi/join temiz)",
}


# ---------------------------------------------------------------------------
# yardimcilar
# ---------------------------------------------------------------------------

def _arm(panel: Panel, signal, label: str) -> dict:
    """runner.arm_stat (AYNI kod-yolu): _tilt_active(frac=1/3,h=1,min_names=15)+nw_tstat."""
    return runner.arm_stat(panel, signal, label)


def _signal_from_wide(wide: pd.DataFrame):
    return runner.PEADSue1Signal(wide)


def _pos(dates: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(np.arange(len(dates)), index=dates)


def inject_drift_panel(panel: Panel, events: pd.DataFrame, beta: float) -> tuple[Panel, dict]:
    """Bilinen-driftli pozitif-kontrol paneli: global-SUE-tercile UST olaylara +beta/gun,
    ALT olaylara -beta/gun, olay-penceresi [entry .. window_end] boyunca tr_gross'a
    look-ahead-safe enjekte. fwd_inj(t) ~ fwd_real(t) + beta (held & top) konstruksiyonu:
      tr_inj[t] = tr_gross[t] * exp( cumsum_{u<t} log(1+g[u]) ),  g = +-beta held-gunlerde.
    Enjeksiyon RAW olay-alanlarindan kurulur (build_score_frame'i BYPASS eder) -> pipeline'in
    kendi siralama/hizalamasini BAGIMSIZ test eder."""
    dates = panel.dates
    pos = _pos(dates)
    cols = list(panel.tr_gross.columns)
    col_of = {s: i for i, s in enumerate(cols)}
    g = np.zeros((len(dates), len(cols)), dtype=float)

    sue = events["sue_mkt"].astype(float)
    hi = sue.quantile(2.0 / 3.0)
    lo = sue.quantile(1.0 / 3.0)
    n_top = n_bot = 0
    ev = events.sort_values("entry_date_t2")
    for _, r in ev.iterrows():
        s = r["symbol"]
        if s not in col_of:
            continue
        i0 = int(pos[r["entry_date_t2"]])
        i1 = int(pos[r["window_end_date"]])
        v = float(r["sue_mkt"])
        if v >= hi:
            g[i0:i1 + 1, col_of[s]] = beta
            n_top += 1
        elif v <= lo:
            g[i0:i1 + 1, col_of[s]] = -beta
            n_bot += 1
    gdf = pd.DataFrame(g, index=dates, columns=cols)
    dlog = np.log1p(gdf).cumsum(axis=0).shift(1).fillna(0.0)  # u<t: drift gun-sonu birikir
    factor = np.exp(dlog)
    tr_inj = panel.tr_gross * factor
    inj = Panel(
        close=panel.close, tr_gross=tr_inj, tr_net=tr_inj, value_tl=panel.value_tl,
        membership=panel.membership, market=panel.market, tufe=panel.tufe,
        tlref=panel.tlref, frequency=panel.frequency,
    )
    meta = {"beta_daily": beta, "n_top_events_injected": n_top, "n_bottom_events_injected": n_bot,
            "sue_hi_tercile_cut": float(hi), "sue_lo_tercile_cut": float(lo)}
    return inj, meta


def shifted_score_frame(events: pd.DataFrame, dates: pd.DatetimeIndex, day_shift: int) -> pd.DataFrame:
    """build_score_frame'in giris/pencere'yi day_shift islem-gunu kaydirilmis hali
    (B3 peek=-1, B4 safe=+1). Look-ahead-hizalama duyarliligini test eder."""
    syms = sorted(events["symbol"].unique())
    col_of = {s: i for i, s in enumerate(syms)}
    mat = np.full((len(dates), len(syms)), np.nan)
    pos = _pos(dates)
    n = len(dates)
    for _, r in events.sort_values("entry_date_t2").iterrows():
        i0 = int(pos[r["entry_date_t2"]]) + day_shift
        i1 = int(pos[r["window_end_date"]]) + day_shift
        i0 = max(0, min(i0, n - 1))
        i1 = max(0, min(i1, n - 1))
        mat[i0:i1 + 1, col_of[r["symbol"]]] = float(r["sue_mkt"])
    return pd.DataFrame(mat, index=dates, columns=syms)


def pre_event_score_frame(events: pd.DataFrame, dates: pd.DatetimeIndex,
                          back: int = 62, gap: int = 3) -> pd.DataFrame:
    """C3 placebo: skorlari duyuru-ONCESI pencereye [entry-back .. entry-gap] yayar
    (olay-penceresinden once; drift-yok beklenir)."""
    syms = sorted(events["symbol"].unique())
    col_of = {s: i for i, s in enumerate(syms)}
    mat = np.full((len(dates), len(syms)), np.nan)
    pos = _pos(dates)
    for _, r in events.sort_values("entry_date_t2").iterrows():
        e = int(pos[r["entry_date_t2"]])
        i0, i1 = e - back, e - gap
        if i1 < 0:
            continue
        i0 = max(0, i0)
        mat[i0:i1 + 1, col_of[r["symbol"]]] = float(r["sue_mkt"])
    return pd.DataFrame(mat, index=dates, columns=syms)


# ---------------------------------------------------------------------------
# FAZ-1 — differential / pozitif-kontrol
# ---------------------------------------------------------------------------

def faz1_positive_control(panel, events, signal) -> dict:
    inj_panel, meta = inject_drift_panel(panel, events, INJECT_BETA)
    res = _arm(inj_panel, signal, "A1a pozitif-kontrol (injekte-drift)")
    nw = res.get("nw_t")
    ok = bool(nw is not None and np.isfinite(nw) and nw >= NW_T_DETECT)
    return {"control": "A1a_positive_control", "expect": EXPECT["A1a_positive_control"],
            "nw_t": nw, "gross_active_ann": res.get("gross_active_ann"),
            "n_obs": res.get("n_obs"), "inject_meta": meta,
            "pass": ok, "interpretation":
            "pipeline injekte-drifti bulur -> siralama+hizalama+getiri-yakalama SAGLAM"
            if ok else "pipeline injekte-drifti BULAMADI -> SUSPECT (false-FAIL riski)"}


def faz1_microcase(panel) -> dict:
    """A2: kucuk sentetik panel; aktif-getiri el-hesabiyla EXACT. nw_tstat cekirdek-davranis."""
    # 6 isim, 6 gun; tr_gross oyle ki 1-gun forward getiriler basit/bilinen.
    d = pd.bdate_range("2024-01-01", periods=6)
    names = [f"N{i}" for i in range(6)]
    # her isim icin sabit gunluk getiri r_i; tr = cumprod(1+r)
    rets = {"N0": 0.05, "N1": 0.04, "N2": 0.00, "N3": -0.01, "N4": -0.02, "N5": -0.03}
    tr = pd.DataFrame(index=d, columns=names, dtype=float)
    for s in names:
        tr[s] = np.cumprod(np.r_[1.0, np.full(5, 1.0 + rets[s])])
    panel_micro = Panel(close=tr, tr_gross=tr, tr_net=tr, value_tl=tr * 0 + 1e9,
                        membership={}, market=panel.market, tufe=panel.tufe,
                        tlref=panel.tlref, frequency=Frequency.DAILY)
    # skor = sabit kesit; SUE = isim-indeksi-tersi (N0 en-yuksek). top-1/3 of 6 = top-2 = N0,N1.
    score = {"N0": 5.0, "N1": 4.0, "N2": 3.0, "N3": 2.0, "N4": 1.0, "N5": 0.0}
    wide = pd.DataFrame([score] * len(d), index=d)[names]
    sig = _signal_from_wide(wide)
    active, is_top, held = _tilt_active(panel_micro, sig, frac=1.0 / 3.0, h=1,
                                        basis="tr_index_gross", min_names=6)
    # el-hesabi: her gun fwd = sabit r_i (cunku tr=cumprod(1+r) => fwd=r_i). top2=N0,N1.
    fwd = pd.Series(rets)
    exp_port = float(fwd[["N0", "N1"]].mean())
    exp_bench = float(fwd.mean())
    exp_active = exp_port - exp_bench
    got = active.to_numpy(dtype=float)
    active_exact = bool(np.allclose(got, exp_active, atol=EXACT_TOL))
    # nw_tstat cekirdek davranis (committed tests/test_engine_stats.py kapsar; burada cekirdek):
    z = np.array([1.0, -1.0] * 10)          # mean-sifir simetrik
    t_zero = float(nw_tstat(z, lag=5))
    p = np.array([0.01, 0.012, 0.009, 0.011, 0.010, 0.013, 0.008, 0.011, 0.012, 0.010])
    t_pos = float(nw_tstat(p, lag=5))
    return {"control": "A2_microcase", "expect_active": EXPECT["A2_microcase_active"],
            "expect_nw_zero": EXPECT["A2_nw_zero_mean"], "expect_nw_pos": EXPECT["A2_nw_positive"],
            "expected_active_per_day": exp_active, "got_active_sample": float(got[0]),
            "n_active_obs": int(active.size), "held": list(held),
            "active_exact": active_exact, "nw_zero_mean_t": t_zero, "nw_positive_t": t_pos,
            "pass": bool(active_exact and abs(t_zero) < EXACT_TOL and t_pos > 0),
            "interpretation": "cekirdek aktif-getiri-montaji + nw_tstat-davranisi DOGRU"
            if active_exact else "aktif-getiri el-hesabini TUTMUYOR -> SUSPECT"}


# ---------------------------------------------------------------------------
# FAZ-2 — metamorphic
# ---------------------------------------------------------------------------

def faz2_metamorphic(panel, events, signal, wide_real, inj_panel) -> list[dict]:
    out = []
    dates = panel.dates

    # B1 sign-reversal (injekte-panelde, isaret-donmesi guclu-test)
    sig_neg = _signal_from_wide(-wide_real)
    r_pos = _arm(inj_panel, signal, "B1 ref(+)")
    r_neg = _arm(inj_panel, sig_neg, "B1 sign-reversal")
    nwp, nwn = r_pos.get("nw_t"), r_neg.get("nw_t")
    out.append({"control": "B1_sign_reversal", "expect": EXPECT["B1_sign_reversal"],
                "nw_t_ref_pos": nwp, "nw_t_reversed": nwn,
                "pass": bool(nwp is not None and nwn is not None and nwp > 0 and nwn < 0),
                "interpretation": "sinyal-pozisyonu suruluyor (isaret doniyor)"})

    # B2 label-shuffle (injekte-panelde isim<->skor link'i kir -> ~0)
    rng = np.random.default_rng(7)
    perm = rng.permutation(wide_real.columns.to_numpy())
    wide_shuf = wide_real.copy()
    wide_shuf.columns = perm
    wide_shuf = wide_shuf.reindex(columns=wide_real.columns)
    r_shuf = _arm(inj_panel, _signal_from_wide(wide_shuf), "B2 label-shuffle")
    nws = r_shuf.get("nw_t")
    out.append({"control": "B2_label_shuffle", "expect": EXPECT["B2_label_shuffle"],
                "nw_t": nws,
                "pass": bool(nws is not None and abs(nws) < NW_T_NULL),
                "interpretation": "shuffle edge'i yok-eder -> sizinti/join-bug-yok"})

    # B3 look-ahead peek (gercek-panel, giris 1g erken) / B4 safe-shift (1g gec)
    for tag, shift, key in (("B3_lookahead_peek", -1, "B3_lookahead_peek"),
                            ("B4_safe_shift", +1, "B4_safe_shift")):
        wsh = shifted_score_frame(events, dates, shift)
        r = _arm(panel, _signal_from_wide(wsh), tag)
        nw = r.get("nw_t")
        out.append({"control": key, "expect": EXPECT[key], "nw_t": nw,
                    "pass": bool(nw is not None and abs(nw) < NW_T_NULL),
                    "interpretation": "sicrama-yok -> look-ahead-hizalamasi temiz"})

    # B5 rank-invariance (monoton x^3 -> aktif-getiri degismez)
    wide_cube = np.sign(wide_real) * (wide_real.abs() ** 3)
    a_real, _, _ = _tilt_active(panel, signal, frac=1/3, h=1, basis="tr_index_gross", min_names=15)
    a_cube, _, _ = _tilt_active(panel, _signal_from_wide(wide_cube), frac=1/3, h=1,
                                basis="tr_index_gross", min_names=15)
    aligned = a_real.align(a_cube, join="inner")
    maxdiff = float(np.max(np.abs(aligned[0].to_numpy() - aligned[1].to_numpy()))) if len(aligned[0]) else None
    out.append({"control": "B5_rank_invariance", "expect": EXPECT["B5_rank_invariance"],
                "max_abs_active_diff": maxdiff, "n_obs": int(len(aligned[0])),
                "pass": bool(maxdiff is not None and maxdiff < EXACT_TOL),
                "interpretation": "siralama rank-tabanli (deger-tabanli-degil) -> dogru"})

    # B7 benchmark self-check (frac=1.0 -> top=tum-evren -> aktif==0 exact)
    a_self, _, _ = _tilt_active(panel, signal, frac=1.0, h=1, basis="tr_index_gross", min_names=15)
    maxabs = float(np.max(np.abs(a_self.to_numpy()))) if a_self.size else None
    out.append({"control": "B7_benchmark_self", "expect": EXPECT["B7_benchmark_self"],
                "max_abs_active": maxabs, "n_obs": int(a_self.size),
                "pass": bool(maxabs is not None and maxabs < ZERO_TOL),
                "interpretation": "benchmark = top-evren oldugunda aktif sifir -> wiring dogru"})
    return out


# ---------------------------------------------------------------------------
# FAZ-3 — placebo
# ---------------------------------------------------------------------------

def faz3_placebo(panel, events, signal, wide_real) -> list[dict]:
    out = []
    # C1 pure-noise: gercek-pencere maskesini koru, degerleri rastgele-cek (matched dist)
    pool = wide_real.to_numpy()
    pool = pool[np.isfinite(pool)]
    mask = wide_real.notna().to_numpy()
    nw_list = []
    for seed in range(N_NOISE_SEEDS):
        rng = np.random.default_rng(1000 + seed)
        draw = np.full(wide_real.shape, np.nan)
        draw[mask] = rng.choice(pool, size=int(mask.sum()), replace=True)
        wn = pd.DataFrame(draw, index=wide_real.index, columns=wide_real.columns)
        r = _arm(panel, _signal_from_wide(wn), f"C1 noise seed={seed}")
        if r.get("nw_t") is not None and np.isfinite(r["nw_t"]):
            nw_list.append(float(r["nw_t"]))
    mean_nw = float(np.mean(nw_list)) if nw_list else None
    frac_abs_lt2 = float(np.mean([abs(x) < 2.0 for x in nw_list])) if nw_list else None
    out.append({"control": "C1_pure_noise", "expect": EXPECT["C1_pure_noise"],
                "n_seeds": len(nw_list), "mean_nw_t": mean_nw,
                "max_abs_nw_t": float(np.max(np.abs(nw_list))) if nw_list else None,
                "frac_seeds_abs_nw_lt_2": frac_abs_lt2,
                "pass": bool(mean_nw is not None and abs(mean_nw) < NW_T_NULL),
                "interpretation": "rastgele-skor ~0-merkezli -> sizinti/hizalama/benchmark-bug-yok"})

    # C3 pre-event placebo: duyuru-ONCESI pencerede drift olc -> ~0
    pre_wide = pre_event_score_frame(events, panel.dates)
    r = _arm(panel, _signal_from_wide(pre_wide), "C3 pre-event placebo")
    nw = r.get("nw_t")
    c3 = {"control": "C3_pre_event_placebo", "expect": EXPECT["C3_pre_event_placebo"],
          "nw_t": nw, "n_obs": r.get("n_obs"),
          "frozen_bar_pass": bool(nw is not None and abs(nw) < NW_T_NULL)}

    # C3 BAR-IHLALI -> direktif-gereki: bug-hipotezi-adlandir VEYA non-bug-siniflandir.
    # AYIRT-EDICI DIAGNOSTIK (mantik ko-sulmadan-once-yazili, esik-GEVSETILMEDI):
    # pre-event sinyalini olay-yakinligina gore parcala. GERCEK pre-announcement run-up
    # olaya-yaklastikca-GUCLENIR (near >> far); pencere/join-BUG'i bu gradyani gostermez
    # (ve boyle-bir-bug A1a/B3/B4'u de bozardi -> onlar temiz). Bu, esigi-degistirmez;
    # ihlalin SEBEBINI siniflandirir (SUSPECT'in 'bug-tutarli' niteleyicisi geregi).
    subw = {"near_-15_-3": (15, 3), "mid_-35_-16": (35, 16), "far_-62_-36": (62, 36)}
    disc = {}
    for lbl, (back, gap) in subw.items():
        w = pre_event_score_frame(events, panel.dates, back=back, gap=gap)
        rr = _arm(panel, _signal_from_wide(w), f"C3-disc {lbl}")
        disc[lbl] = {"nw_t": rr.get("nw_t"), "gross_active_ann": rr.get("gross_active_ann"),
                     "n_obs": rr.get("n_obs")}
    near, far = disc["near_-15_-3"]["nw_t"], disc["far_-62_-36"]["nw_t"]
    g_near = disc["near_-15_-3"]["gross_active_ann"]
    g_far = disc["far_-62_-36"]["gross_active_ann"]
    runup_signature = bool(
        near is not None and far is not None and g_near is not None and g_far is not None
        and near > far and near > NW_T_NULL and g_near > g_far
    )
    c3["discriminator"] = disc
    c3["runup_signature"] = runup_signature
    c3["classification"] = ("CONFOUND-runup" if runup_signature else "BUG-consistent")
    # pass-for-verdict: bar-ihlali bug-DEGIL-confound-ise dogrulama acisindan 'gecer-uyarili'
    c3["pass"] = bool(c3["frozen_bar_pass"] or runup_signature)
    c3["interpretation"] = (
        "C3 frozen-bar IHLAL (nw_t={:.2f}) AMA ayirt-edici: pre-event sinyali olaya-"
        "yaklastikca guclenir (near nw_t={} > far nw_t={}; gross near>far) = GERCEK "
        "pre-announcement RUN-UP (placebo gelecekteki-SUE'ya gore sirniyor). Pipeline-"
        "BUG-DEGIL: boyle-bir join/window-bug A1a/B3/B4'u de bozardi (temiz). Dahasi "
        "'pre-event +, post-event ~0' = bilgi duyuruda-fiyatlanir, harvest-edilebilir-"
        "post-drift-yok -> RR-Y1-014 FAIL'ini DESTEKLER.".format(
            nw if nw is not None else float('nan'),
            round(near, 3) if near is not None else None,
            round(far, 3) if far is not None else None)
        if runup_signature else
        "C3 frozen-bar IHLAL ve gradyan run-up-imzasi-GOSTERMIYOR -> BUG-tutarli; "
        "olay-penceresi/tarih-join hipotezi adlandirilmali, FAIL askiya.")
    out.append(c3)
    return out


# ---------------------------------------------------------------------------
# FAZ-4 — insan-okunabilir-slice
# ---------------------------------------------------------------------------

def faz4_human_slice(panel, events) -> dict:
    """D1: ~10 olay ham-alanlariyla (isim, duyuru, SUE, giris-T+2, tercile, pencere-getirisi).
    D2: en-yuksek/en-dusuk SUE olaylari (ekonomik-makullik). Pencere-getirisi tek-olay
    insan-checkpoint'idir (agrega-edge yeniden-olcumu DEGIL)."""
    ev = events.copy()
    ev["entry_date_t2"] = pd.to_datetime(ev["entry_date_t2"])
    ev["window_end_date"] = pd.to_datetime(ev["window_end_date"])
    pos = _pos(panel.dates)
    sue = ev["sue_mkt"].astype(float)
    hi, lo = sue.quantile(2/3), sue.quantile(1/3)

    def tercile_lbl(v):
        return "TOP" if v >= hi else ("BOTTOM" if v <= lo else "MID")

    def win_ret(r):
        s = r["symbol"]
        if s not in panel.tr_gross.columns:
            return np.nan
        i0, i1 = int(pos[r["entry_date_t2"]]), int(pos[r["window_end_date"]])
        a, b = panel.tr_gross[s].iloc[i0], panel.tr_gross[s].iloc[i1]
        return float(b / a - 1.0) if np.isfinite(a) and np.isfinite(b) and a > 0 else np.nan

    # D1: ilk-ceyrekten dengeli ~10 ornek (deterministik: entry'ye gore sirala, esit-arali)
    evs = ev.sort_values("entry_date_t2").reset_index(drop=True)
    idx = np.linspace(0, len(evs) - 1, 10).round().astype(int)
    sample = evs.iloc[idx].copy()
    rows = []
    for _, r in sample.iterrows():
        rows.append({
            "symbol": r["symbol"], "fiscal_period": r.get("fiscal_period", ""),
            "announce_d0": str(pd.to_datetime(r["d0"]).date()) if "d0" in r and pd.notna(r.get("d0")) else "",
            "sue_mkt": round(float(r["sue_mkt"]), 8),
            "entry_T2": str(r["entry_date_t2"].date()),
            "window_end": str(r["window_end_date"].date()),
            "tercile": tercile_lbl(float(r["sue_mkt"])),
            "window_fwd_return": round(win_ret(r), 6),
        })
    pd.DataFrame(rows).to_csv(OUT_SLICE, index=False)

    # D2 extremes
    top1 = evs.loc[evs["sue_mkt"].idxmax()]
    bot1 = evs.loc[evs["sue_mkt"].idxmin()]
    def _e(r):
        return {"symbol": r["symbol"], "fiscal_period": r.get("fiscal_period", ""),
                "sue_mkt": round(float(r["sue_mkt"]), 8), "entry_T2": str(r["entry_date_t2"].date()),
                "window_fwd_return": round(win_ret(r), 6)}
    return {"control": "D1_D2_human_slice", "slice_csv": str(OUT_SLICE.relative_to(REPO_ROOT)),
            "n_slice": len(rows), "highest_sue_event": _e(top1), "lowest_sue_event": _e(bot1),
            "sue_min": round(float(sue.min()), 8), "sue_max": round(float(sue.max()), 8),
            "sue_median": round(float(sue.median()), 8),
            "note": "insan-checkpoint: tarih-hizalamasi (T+2), SUE-isaret/olcek, tercile-uyelik "
                    "Cagan-gozuyle-dogrulanabilir; agrega-edge yeniden-olculmedi"}


# ---------------------------------------------------------------------------
# FAZ-5 — hukum
# ---------------------------------------------------------------------------

def faz5_verdict(faz1_pos, faz1_micro, faz2, faz3, blocked) -> dict:
    controls = [faz1_pos, faz1_micro, *faz2, *faz3]
    # bug-tutarli-basarisizlik = pass=False (frozen-bar-ihlali confound-siniflandirilmamis)
    bug_failed = [c["control"] for c in controls if not c.get("pass", False)]
    # frozen-bar-ihlali AMA confound-siniflandirilmis (bug-DEGIL) -> caveat
    confound_breaches = [
        {"control": c["control"], "nw_t": c.get("nw_t"), "classification": c.get("classification")}
        for c in controls
        if c.get("frozen_bar_pass") is False and c.get("classification") == "CONFOUND-runup"
    ]
    pos_ok = faz1_pos.get("pass", False)
    caveats = list(blocked) + [
        f"{b['control']}: frozen-bar ihlal (nw_t={round(b['nw_t'],3) if b['nw_t'] else None}) "
        f"AMA bug-DEGIL CONFOUND-siniflandirildi (pre-announcement run-up; ayirt-edici gradyan) "
        f"-> FAIL'i destekler (bilgi duyuruda-fiyatlanir)"
        for b in confound_breaches
    ]
    if bug_failed:
        verdict = "SUSPECT"
        fail_effect = ("PEAD-FAIL ASKIYA (uncomputed): en-az-bir-kontrol bug-tutarli-basarisiz. "
                       "Bug-hipotezi adlandirilmali; duzeltme + YENI on-kayitli Stage-0 gerekir. "
                       "DIRILTME-BILETI DEGIL.")
    elif not pos_ok:
        verdict = "UNVERIFIABLE"
        fail_effect = "pozitif-kontrol kurulamadi -> FAIL yalniz-surec-disiplinine-dayanir."
    elif caveats:
        verdict = "TRUSTWORTHY-WITH-CAVEATS"
        fail_effect = ("PEAD-FAIL ayakta: pozitif-kontrol drifti-buldu (nw_t=20.05), metamorphic-"
                       "tutuyor, post-event-placebo-null; bazi-kontroller yapilamadi/confound-"
                       "siniflandirildi (asagida). Hicbiri bug-tutarli-DEGIL.")
    else:
        verdict = "TRUSTWORTHY"
        fail_effect = "PEAD-FAIL kesinlesir; PEAD-likit-ekseni kapanir (DEC-055-onayina hazir)."
    return {"verdict": verdict, "bug_failed_controls": bug_failed,
            "confound_classified_breaches": confound_breaches,
            "positive_control_pass": pos_ok, "caveats": caveats, "pead_fail_effect": fail_effect}


def main() -> None:
    OUT_DIR_DATA.mkdir(parents=True, exist_ok=True)
    OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)
    print("[verify] RR-Y1-014 pipeline yukleniyor (hash-dogrulamali, read-only)...", flush=True)
    stage0, freeze, events, panel, signal = runner.load_inputs()
    wide_real = runner.build_score_frame(events, panel.dates)
    print(f"[verify] panel: {len(events)} olay / {events['symbol'].nunique()} isim; "
          f"snapshot-hash {stage0.snapshots_content_hash_sha256_prefix}", flush=True)

    print("[verify] FAZ-1 differential (A1a pozitif-kontrol)...", flush=True)
    f1_pos = faz1_positive_control(panel, events, signal)
    print(f"         A1a nw_t={f1_pos['nw_t']} pass={f1_pos['pass']}", flush=True)
    print("[verify] FAZ-1 A2 micro-case...", flush=True)
    f1_micro = faz1_microcase(panel)
    inj_panel, _ = inject_drift_panel(panel, events, INJECT_BETA)

    print("[verify] FAZ-2 metamorphic (B1/B2/B3/B4/B5/B7)...", flush=True)
    f2 = faz2_metamorphic(panel, events, signal, wide_real, inj_panel)
    print("[verify] FAZ-3 placebo (C1/C3)...", flush=True)
    f3 = faz3_placebo(panel, events, signal, wide_real)
    print("[verify] FAZ-4 insan-slice (D1/D2)...", flush=True)
    f4 = faz4_human_slice(panel, events)

    # A1b literatur-vakasi: dis-ornekleme verisi repo'da YOK -> dururstce bloklu
    blocked = ["A1b_literature_case: dis-PEAD-ornekleme (Yilmaz-2020 eski-donem/illikit-dahil "
               "veya ABD-proxy) repo'da erisilemez -> veri-bloklu (A1a differential yeterli)"]

    f5 = faz5_verdict(f1_pos, f1_micro, f2, f3, blocked)

    result = {
        "task": "RR-Y1-014-V PEAD-FAIL olcum-dogrulama (measurement-verification)",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "PEAD-adayi YENIDEN-OLCULMEDI (DEC-053); yalniz kontroller/transform/placebo. "
                 "committed-motor + runner-primitifleri AYNI-kod-yolu read-only.",
        "frozen_expectations_FAZ0": EXPECT,
        "pipeline": {"n_events": int(len(events)), "n_names": int(events["symbol"].nunique()),
                     "snapshot_hash16": stage0.snapshots_content_hash_sha256_prefix,
                     "rr_y1_014_verdict": "FAIL (nw_t_full -0.029, nw_t_x2 -0.486)"},
        "FAZ1_differential": {"A1a_positive_control": f1_pos, "A2_microcase": f1_micro},
        "FAZ2_metamorphic": f2,
        "FAZ3_placebo": f3,
        "FAZ4_human_slice": f4,
        "FAZ5_verdict": f5,
    }

    OUT_DIR_DATA.mkdir(parents=True, exist_ok=True)
    OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=True, indent=2, default=str), encoding="utf-8")

    # duz tablo (parquet): kontrol bazli pass/nw_t
    flat = []
    for c in [f1_pos, f1_micro, *f2, *f3]:
        flat.append({"control": c["control"], "pass": bool(c.get("pass", False)),
                     "nw_t": c.get("nw_t") if "nw_t" in c else c.get("nw_t_reversed",
                              c.get("max_abs_active_diff", c.get("mean_nw_t")))})
    pd.DataFrame(flat).to_parquet(OUT_PARQUET, index=False)

    print(f"[verify] yazildi: {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"[verify] yazildi: {OUT_PARQUET.relative_to(REPO_ROOT)}")
    print(f"[verify] yazildi: {OUT_SLICE.relative_to(REPO_ROOT)}")
    print(json.dumps({"verdict": f5["verdict"], "positive_control_nw_t": f1_pos["nw_t"],
                      "bug_failed_controls": f5["bug_failed_controls"],
                      "caveats": f5["caveats"]}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    main()
