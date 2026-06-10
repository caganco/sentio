"""RR-Y1-013-B — KAP Katman-2 gun-damgasi backfill (G1-PASS onkosulu).

VERI-BACKFILL GOREVI — Stage-0 OLCUMU DEGIL, edge-testi DEGIL.
Performans-metrigi (CAR/getiri/Sharpe/t-istatistigi) URETILMEZ.

Tek amac: RR-Y1-013 earnings-olaylarina gun-cozunurluklu, point-in-time,
ILK-DUYURU tarih-damgasi eklemek; frozen T+2 giris-parametresini (RR-Y1-013 §2)
BIST verisinde uygulanabilir kilmak. RR-Y1-013 probe-scripti ve ciktilari
DEGISTIRILMEZ; bu katman ustune eklenir. src/engine read-only.

VERI-KANALI MIMARISI (kosu-oncesi olculen kisitla belirlendi, raporda aciklanir):
  - MKK VYK API retention-tabani ~2023-02 (bu gorevde olculdu: start_index=538004
    bile en-eski FY2022-yilligini donduruyor) => 2019-2022 duyurulari MKK'dan
    damgalanamaz.
  - TOPLU kaynak: KAP public `byCriteria` listesi (RR-Y1-011-C/D'de kanitlanan yol;
    publishDate saniye-hassasiyetli + stockCodes + year/period listede mevcut,
    arsiv 2019-oncesine iner).
  - CAPRAZ-DOGRULAMA: MKK VYK API (kimlikli, bagimsiz altyapi) ayni disclosureIndex
    uzerinden >= 20 isim exact-day karsilastirmasi (retention-ici, 2023+).
  - UCUNCU kanal: degoran step-month (RR-046 devir-envanteri) tam-panel ay-uyusmasi.

Ham yanitlar frozen-snapshot: data/bist_datastore_archive/kap_fr_daydate_raw/
(junction'li ortak arsiv; git-ignored, CI-disi — RR-Y1-011-D recon_cache precedenti).
Turetilmis panel + meta commit edilir.

Ciktilar:
  - data/probe/pead_announcement_daydated.parquet  (olay-bazli gun-damgali panel)
  - data/probe/pead_daydate_backfill_summary.json  (kapsam/dogrulama kaniti)
  - stdout: JSON ozet

Kullanim:
  python scripts/probe/pead_daydate_backfill.py [--skip-fetch] [--mkk-spot 24]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.engine.data_adapter import liquid_names, load_panel  # noqa: E402

EARNINGS_PARQUET = REPO_ROOT / "data" / "snapshots" / "earnings_dates.parquet"
RAW_DIR = REPO_ROOT / "data" / "bist_datastore_archive" / "kap_fr_daydate_raw"
OUT_DIR = REPO_ROOT / "data" / "probe"
OUT_PARQUET = OUT_DIR / "pead_announcement_daydated.parquet"
OUT_JSON = OUT_DIR / "pead_daydate_backfill_summary.json"

# --- KAP public byCriteria (RR-Y1-011-D precedenti) ---
KAP_BASE = "https://www.kap.org.tr"
KAP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
KAP_RECORD_LIMIT = 2000          # API sayfa-tavani; n==2000 => pencere bisect edilir
KAP_SLEEP_S = 0.8                # nazik istek-temposu (RR-Y1-011-D ile ayni)
FETCH_FROM = "2019-01-01"        # fiyat-paneli/likidite penceresinin basi
FETCH_TO = "2026-06-10"          # koshu gunu

# KAP `stockCodes` alani BUGUNKU (yeniden-adlandirilmis) kodu tasir — retroaktif.
# Tarihsel degoran/clean_universe kodlariyla join icin dogrulanmis alias'lar
# (kanit: ham-cache kapTitle eslesmesi, bu gorevde teshis edildi; veri-temizligi,
# optimizasyon DEGIL). guncel-KAP-kodu -> tarihsel-panel-kodu:
TICKER_ALIASES = {
    "DGNMO": "DGKLB",  # DOGTAS KELEBEK MOBILYA
    "BESLR": "KERVT",  # KEREVITAS GIDA
    "TRALT": "KOZAL",  # KOZA ALTIN
    "TRMET": "KOZAA",  # KOZA ANADOLU METAL
    "TRENJ": "IPEKE",  # IPEK DOGAL ENERJI
    "LRSHO": "ITTFH",  # ITTIFAK HOLDING
}

# --- sabit tanimlar (RR-Y1-013 §2'den devralinir; DEGISTIRILMEZ) ---
SESSION_CUTOFF_HOUR = 18         # >= 18:00 duyuru -> ertesi-isgunu D0
ENTRY_LAG_TDAYS = 2              # giris = D0 + 2 isgunu (frozen T+2)
HEADLINE_FY_MIN = 2019
HEADLINE_FY_MAX = 2025

# --- MKK VYK capraz-dogrulama butcesi ---
MKK_SPOT_DEFAULT = 24            # >= 20 isim bari (RR-Y1-013-B §4)
MKK_SPOT_MAX_CALLS = 80          # hard butce; kullanilan sayi raporlanir
# Kimlikteki gateway TEST'tir (apigwdev) ve dar bir veri-snapshot'i servis eder:
# vintage-taramasi (bu gorev): 2023-03/05/08/11 detail OK; 2024-03+ ve 2026-05 ER005.
# Spot-ornek guvenli ic-banda alinir; bant raporlanir.
MKK_BAND_FROM = "2023-04-01"
MKK_BAND_TO = "2023-11-30"


# ---------------------------------------------------------------------------
# Adim 2a — KAP public toplu cekim (pencereli, 2000-limit'te recursive bisect)
# ---------------------------------------------------------------------------

def _kap_query(session: requests.Session, d0: str, d1: str) -> list[dict]:
    body = {
        "fromDate": d0, "toDate": d1, "disclosureClass": "FR",
        "subjectList": [], "mkkMemberOidList": [], "inactiveMkkMemberOidList": [],
        "bdkMemberOidList": [], "fromSrc": False, "disclosureIndexList": [],
    }
    r = session.post(f"{KAP_BASE}/tr/api/disclosure/members/byCriteria",
                     headers=KAP_HEADERS, json=body, timeout=45)
    r.raise_for_status()
    return r.json()


def _fetch_window(session: requests.Session, d0: pd.Timestamp, d1: pd.Timestamp,
                  stats: dict) -> list[dict]:
    """Bir [d0, d1] penceresini cek; cache'le; 2000-tavaninda bisect (kayip-yok)."""
    key = f"{d0.date()}_{d1.date()}"
    cache = RAW_DIR / f"byCriteria_FR_{key}.json.gz"
    if cache.exists():
        recs = json.loads(gzip.decompress(cache.read_bytes()))
        stats["windows_cached"] += 1
    else:
        recs = _kap_query(session, str(d0.date()), str(d1.date()))
        stats["windows_fetched"] += 1
        stats["http_requests"] += 1
        time.sleep(KAP_SLEEP_S)
        if len(recs) >= KAP_RECORD_LIMIT and d0 != d1:
            # tavana carpti -> ikiye bol (ham cache YALNIZ tavan-alti pencerelere yazilir)
            mid = d0 + (d1 - d0) / 2
            left = _fetch_window(session, d0, pd.Timestamp(mid.date()), stats)
            right = _fetch_window(session, pd.Timestamp(mid.date()) + pd.Timedelta(days=1), d1, stats)
            return left + right
        if len(recs) >= KAP_RECORD_LIMIT:
            # tek-gun doygunlugu: sessiz-kirpma YOK -> yuksek-sesle isaretle
            stats["saturated_days"].append(key)
        cache.write_bytes(gzip.compress(json.dumps(recs, ensure_ascii=False).encode("utf-8")))
    return recs


def fetch_all(skip_fetch: bool) -> tuple[pd.DataFrame, dict]:
    """FR-sinifi tum-piyasa duyuru listesi 2019->bugun, aylik pencerelerle."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stats: dict = {"windows_fetched": 0, "windows_cached": 0, "http_requests": 0,
                   "saturated_days": []}
    all_recs: list[dict] = []
    if skip_fetch:
        # bisect edilen aylarin AY-seviyesi cache'i yoktur (yalniz cocuk-pencereler
        # yazilir); ay-dongusu cocuklari atlardi (sessiz-kirpma). Tum cache'i yukle.
        for fp in sorted(RAW_DIR.glob("byCriteria_FR_*.json.gz")):
            all_recs.extend(json.loads(gzip.decompress(fp.read_bytes())))
            stats["windows_cached"] += 1
    else:
        months = pd.period_range(FETCH_FROM, FETCH_TO, freq="M")
        session = requests.Session()
        for m in months:
            d0 = pd.Timestamp(max(pd.Timestamp(FETCH_FROM), m.start_time).date())
            d1 = pd.Timestamp(min(pd.Timestamp(FETCH_TO), m.end_time).date())
            all_recs.extend(_fetch_window(session, d0, d1, stats))
            if stats["windows_fetched"] and stats["windows_fetched"] % 12 == 0:
                print(f"[fetch] {m} -> {len(all_recs)} kayit "
                      f"({stats['http_requests']} istek)", flush=True)

    df = pd.DataFrame(all_recs)
    if df.empty:
        return df, stats
    df = df.drop_duplicates("disclosureIndex").reset_index(drop=True)
    stats["n_records_raw"] = int(len(df))
    return df, stats


# ---------------------------------------------------------------------------
# Adim 3 — gun-damgasi turetme + seans-kurali + T+2
# ---------------------------------------------------------------------------

def build_daydated_panel(raw: pd.DataFrame, trading_days: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    """FR-kategori kayitlardan (ticker, fy, q) ilk-duyuru gun-damgali paneli kur."""
    notes: dict = {}
    fr = raw[raw["disclosureCategory"] == "FR"].copy()
    notes["n_fr_category"] = int(len(fr))
    notes["subject_breakdown_fr_category"] = {
        str(k): int(v) for k, v in fr["subject"].value_counts().head(8).items()
    }
    fr = fr[fr["year"].notna() & fr["period"].notna() & fr["stockCodes"].notna()]
    notes["n_fr_with_year_period_stock"] = int(len(fr))

    fr["publish_ts"] = pd.to_datetime(fr["publishDate"], format="%d.%m.%Y %H:%M:%S")
    fr["fiscal_year"] = fr["year"].astype(int)
    fr["quarter"] = fr["period"].astype(int)
    fr["ticker"] = fr["stockCodes"].astype(str).str.split(",")
    fr = fr.explode("ticker")
    fr["ticker"] = fr["ticker"].str.strip().str.upper()
    fr = fr[fr["ticker"].str.match(r"^[A-Z0-9]{3,6}$")]
    # rename-alias satirlari: ayni filing tarihsel kod altinda da anahtarlanir
    alias_rows = fr[fr["ticker"].isin(TICKER_ALIASES)].copy()
    alias_rows["ticker"] = alias_rows["ticker"].map(TICKER_ALIASES)
    fr = pd.concat([fr, alias_rows], ignore_index=True)
    notes["n_alias_rows_added"] = int(len(alias_rows))
    notes["ticker_aliases"] = dict(TICKER_ALIASES)
    notes["n_fr_exploded_rows"] = int(len(fr))
    notes["n_tickers"] = int(fr["ticker"].nunique())

    # ilk-duyuru = min(publish_ts) per (ticker, fy, q); sonrakiler restate/duzeltme
    fr = fr.sort_values("publish_ts")
    grp = fr.groupby(["ticker", "fiscal_year", "quarter"], sort=False)
    first = fr.drop_duplicates(["ticker", "fiscal_year", "quarter"], keep="first").copy()
    counts = grp.size().rename("n_filings")
    first = first.merge(counts, left_on=["ticker", "fiscal_year", "quarter"],
                        right_index=True, how="left")
    last_ts = grp["publish_ts"].max().rename("last_filing_ts")
    first = first.merge(last_ts, left_on=["ticker", "fiscal_year", "quarter"],
                        right_index=True, how="left")
    first["restate_step_flag"] = first["n_filings"] > 1
    notes["n_event_keys"] = int(len(first))
    notes["restate_share"] = round(float(first["restate_step_flag"].mean()), 4)

    # seans-kurali (RR-Y1-013-B §2 frozen): >= 18:00 VEYA tatil/hafta-sonu -> ertesi-isgunu
    td = trading_days.normalize()
    td_set = pd.DatetimeIndex(td)
    pub_date = first["publish_ts"].dt.normalize()
    post_session = first["publish_ts"].dt.hour >= SESSION_CUTOFF_HOUR
    is_tday = pub_date.isin(td_set)
    flag = np.where(~is_tday, "non_trading_day",
                    np.where(post_session, "post_session", "in_session"))
    first["intraday_session_flag"] = flag

    # D0: in_session -> ayni gun; digerleri -> ilk SONRAKI isgunu
    pos_next = np.searchsorted(td_set.values, pub_date.values, side="right")  # ilk > pub_date
    pos_same = np.searchsorted(td_set.values, pub_date.values, side="left")
    use_same = is_tday.values & ~post_session.values
    d0_pos = np.where(use_same, pos_same, pos_next)
    d0 = pd.Series(pd.NaT, index=first.index, dtype="datetime64[ns]")
    entry = pd.Series(pd.NaT, index=first.index, dtype="datetime64[ns]")
    ok_d0 = d0_pos < len(td_set)
    d0.iloc[:] = np.where(ok_d0, td_set.values[np.clip(d0_pos, 0, len(td_set) - 1)],
                          np.datetime64("NaT"))
    e_pos = d0_pos + ENTRY_LAG_TDAYS
    ok_e = e_pos < len(td_set)
    entry.iloc[:] = np.where(ok_e, td_set.values[np.clip(e_pos, 0, len(td_set) - 1)],
                             np.datetime64("NaT"))
    first["d0"] = d0
    first["entry_date_t2"] = entry
    notes["n_d0_beyond_calendar"] = int((~ok_d0).sum())
    notes["n_entry_beyond_calendar"] = int((~ok_e).sum())

    out_cols = ["ticker", "fiscal_year", "quarter", "publish_ts", "intraday_session_flag",
                "d0", "entry_date_t2", "n_filings", "restate_step_flag", "last_filing_ts",
                "disclosureIndex", "subject", "ruleType"]
    panel = first[out_cols].rename(columns={
        "publish_ts": "first_announcement_ts",
        "disclosureIndex": "source_disclosure_index",
    }).reset_index(drop=True)
    panel["fiscal_period"] = panel["fiscal_year"].astype(str) + "Q" + panel["quarter"].astype(str)
    panel["first_announcement_date_day"] = panel["first_announcement_ts"].dt.date.astype(str)
    return panel, notes


# ---------------------------------------------------------------------------
# Adim 1 + 4a — backfill-evreni (oncelik-1 = tercile-uc) ve kapsam-oranlari
# ---------------------------------------------------------------------------

def _tercile_membership(ev: pd.DataFrame, panel) -> pd.DataFrame:
    """RR-Y1-013 gate3 mantiginin birebir tekrari (probe-scripti degistirilmeden):
    likit∩SUE kesitinde rank-qcut tercile; uc-dilim uyeligi = oncelik-1."""
    dates = panel.close.index
    evs = ev[ev["sue"].notna()].copy()
    evs["am"] = pd.PeriodIndex(evs["announce_month"].astype(str), freq="M")
    p0, p1 = dates[0].to_period("M"), dates[-1].to_period("M")
    evs = evs[(evs["am"] >= p0) & (evs["am"] <= p1)].copy()
    liq_cache: dict = {}
    for m in evs["am"].unique():
        sub = dates[dates <= m.end_time]
        liq_cache[m] = liquid_names(panel, sub[-1]) if len(sub) else set()
    evs["liquid"] = [s in liq_cache[m] for s, m in zip(evs["symbol"], evs["am"], strict=True)]
    evs["tercile_extreme"] = False
    for (_fy, _q), g in evs.groupby(["fiscal_year", "quarter"]):
        liq = g[g["liquid"]]
        if len(liq) < 3:
            continue
        ranks = liq["sue"].rank(method="first")
        bins = pd.qcut(ranks, 3, labels=False)
        ext_idx = liq.index[(bins == 0) | (bins == 2)]
        evs.loc[ext_idx, "tercile_extreme"] = True
    return evs


def coverage_report(evs: pd.DataFrame, day_panel: pd.DataFrame) -> dict:
    """Oncelik-1 / toplam-SUE kapsam-oranlari + degoran ay-uyusmasi (ucuncu kanal)."""
    key = ["symbol", "fiscal_year", "quarter"]
    dp = day_panel.rename(columns={"ticker": "symbol"})
    dp = dp[["symbol", "fiscal_year", "quarter", "first_announcement_ts",
             "restate_step_flag"]].drop_duplicates(key)
    j = evs.merge(dp, on=key, how="left", indicator=True)
    j["stamped"] = j["_merge"] == "both"

    head = j[(j["fiscal_year"] >= HEADLINE_FY_MIN) & (j["fiscal_year"] <= HEADLINE_FY_MAX)]
    p1 = head[head["tercile_extreme"]]
    p2 = head

    # degoran ay-uyusmasi: KAP ilk-duyuru ayi vs panel announce_month (tam-panel olcek)
    s = head[head["stamped"]].copy()
    if len(s):
        kap_m = s["first_announcement_ts"].dt.to_period("M")
        pan_m = pd.PeriodIndex(s["announce_month"].astype(str), freq="M")
        diff_n = pd.Series([d.n for d in (kap_m.values - pan_m.values)])
        month_agree = {
            "n_compared": int(len(s)),
            "exact_share": round(float((diff_n == 0).mean()), 4),
            "within_1m_share": round(float((diff_n.abs() <= 1).mean()), 4),
            "diff_histogram": {str(k): int(v)
                               for k, v in diff_n.value_counts().sort_index().items()},
        }
    else:
        month_agree = {"n_compared": 0}
    return {
        "priority1_tercile_extreme": {
            "n_target": int(len(p1)),
            "n_stamped": int(p1["stamped"].sum()),
            "coverage": round(float(p1["stamped"].mean()), 4) if len(p1) else None,
        },
        "priority2_all_sue": {
            "n_target": int(len(p2)),
            "n_stamped": int(p2["stamped"].sum()),
            "coverage": round(float(p2["stamped"].mean()), 4) if len(p2) else None,
        },
        "degoran_month_agreement": month_agree,
    }


# ---------------------------------------------------------------------------
# Adim 4b — MKK VYK capraz-dogrulama (bagimsiz altyapi; ayni disclosureIndex)
# ---------------------------------------------------------------------------

def mkk_cross_validate(day_panel: pd.DataFrame, evs: pd.DataFrame, n_names: int) -> dict:
    """>= 20 isim: KAP-public publishDate vs MKK VYK disclosureDetail.time, exact-day.
    MKK retention-tabani (~2023-02, bu gorevde olculdu) nedeniyle ornek 2023-04+."""
    out: dict = {
        "attempted": True, "n_names_requested": n_names,
        "mkk_gateway": "TEST (apigwdev) — dar veri-snapshot'i",
        "mkk_serving_band_observed": "liste-tabani ~2023-02; detail OK 2023-03..2023-11, "
                                     "ER005 2024-03+ ve 2026-05 (vintage-taramasi)",
        "spot_sample_band": [MKK_BAND_FROM, MKK_BAND_TO],
    }
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass
    import os
    if not (os.getenv("MKK_VYK_BASE_URL") and os.getenv("MKK_VYK_TOKEN")):
        out["status"] = "skipped: MKK_VYK kimligi tanimsiz"
        return out
    from src.data.kap_api_client import KapApiError
    from src.data.kap_historical_fetcher import _make_client

    p1_keys = evs[evs["tercile_extreme"]][["symbol", "fiscal_year", "quarter"]]
    dp = day_panel.rename(columns={"ticker": "symbol"})
    cand = dp.merge(p1_keys, on=["symbol", "fiscal_year", "quarter"], how="inner")
    cand = cand[(cand["first_announcement_ts"] >= pd.Timestamp(MKK_BAND_FROM))
                & (cand["first_announcement_ts"] <= pd.Timestamp(MKK_BAND_TO))]
    # isim-basina en-guncel olay; farkli isimlerden n_names ornek (deterministik sira)
    cand = cand.sort_values("first_announcement_ts", ascending=False)
    cand = cand.drop_duplicates("symbol").head(n_names)
    out["n_candidates"] = int(len(cand))

    client = _make_client()
    calls = 0
    rows: list[dict] = []
    for _, r in cand.iterrows():
        if calls >= MKK_SPOT_MAX_CALLS:
            break
        try:
            detail = client.get_disclosure_detail(int(r["source_disclosure_index"]),
                                                  file_type="data")
            calls += 1
        except KapApiError as exc:
            calls += 1
            rows.append({"symbol": r["symbol"], "error": str(exc)[:120]})
            continue
        t = str(detail.get("time") or "")
        dpart = t.split(" ")[0].split(".")
        mkk_day = (f"{dpart[2]}-{dpart[1].zfill(2)}-{dpart[0].zfill(2)}"
                   if len(dpart) == 3 else None)
        pub_day = str(r["first_announcement_ts"].date())
        rows.append({
            "symbol": r["symbol"], "fiscal_period": f"{r['fiscal_year']}Q{r['quarter']}",
            "disclosure_index": int(r["source_disclosure_index"]),
            "kap_public_day": pub_day, "mkk_vyk_day": mkk_day,
            "exact_day_match": bool(mkk_day == pub_day),
        })
    ok = [x for x in rows if "exact_day_match" in x]
    out["api_calls_used"] = calls
    out["n_compared"] = len(ok)
    out["n_exact_day"] = sum(1 for x in ok if x["exact_day_match"])
    out["exact_day_share"] = round(sum(1 for x in ok if x["exact_day_match"]) / len(ok), 4) if ok else None
    out["n_errors"] = len(rows) - len(ok)
    out["evidence_rows"] = rows
    out["status"] = "ok"
    return out


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="RR-Y1-013-B gun-damgasi backfill")
    ap.add_argument("--skip-fetch", action="store_true",
                    help="yalniz mevcut ham-cache'i kullan (yeni HTTP istegi atma)")
    ap.add_argument("--mkk-spot", type=int, default=MKK_SPOT_DEFAULT,
                    help="MKK capraz-dogrulama isim-sayisi (0 = atla)")
    args = ap.parse_args()

    print("[backfill] KAP public FR listesi cekiliyor (2019-01 -> bugun)...", flush=True)
    raw, fetch_stats = fetch_all(skip_fetch=args.skip_fetch)
    print(f"[backfill] ham kayit: {len(raw)} ({fetch_stats})", flush=True)

    print("[backfill] fiyat-paneli / seans-takvimi yukleniyor...", flush=True)
    panel = load_panel()
    day_panel, build_notes = build_daydated_panel(raw, panel.close.index)
    print(f"[backfill] gun-damgali olay-anahtari: {len(day_panel)}", flush=True)

    print("[backfill] oncelik-evreni (tercile-uc) yeniden-turetiliyor...", flush=True)
    ev = pd.read_parquet(EARNINGS_PARQUET)
    evs = _tercile_membership(ev, panel)
    cov = coverage_report(evs, day_panel)

    if args.mkk_spot > 0:
        print("[backfill] MKK VYK capraz-dogrulama...", flush=True)
        mkk = mkk_cross_validate(day_panel, evs, args.mkk_spot)
    else:
        mkk = {"attempted": False, "status": "skipped: kullanici-istegi"}

    result = {
        "task": "RR-Y1-013-B KAP Katman-2 gun-damgasi backfill",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "no_performance_metrics": True,
        "channel_architecture": {
            "bulk": "KAP public byCriteria (publishDate saniye-PIT; 2019+ arsiv)",
            "cross_validation": "MKK VYK disclosureDetail.time (ayni index, bagimsiz altyapi)",
            "third_channel": "degoran step-month (RR-046 devir-envanteri) tam-panel ay-uyusmasi",
            "mkk_retention_finding": "MKK VYK liste-API'si ~2023-02 oncesini servis ETMIYOR "
                                     "(olculdu); 2019-2022 icin tek gun-damga kanali KAP public",
        },
        "fetch": fetch_stats,
        "build": build_notes,
        "coverage": cov,
        "mkk_cross_validation": {k: v for k, v in mkk.items() if k != "evidence_rows"},
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    day_panel.to_parquet(OUT_PARQUET, index=False)
    full = dict(result)
    full["mkk_cross_validation"] = mkk  # evidence dahil dosyaya
    OUT_JSON.write_text(json.dumps(full, ensure_ascii=True, indent=2, default=str),
                        encoding="utf-8")
    print(f"[backfill] yazildi: {OUT_PARQUET.relative_to(REPO_ROOT)} ({len(day_panel)} satir)")
    print(f"[backfill] yazildi: {OUT_JSON.relative_to(REPO_ROOT)}")
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    main()
