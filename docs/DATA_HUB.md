# DATA HUB — Merkezi Veri Router

**Tarih:** 2 Haziran 2026 (v3 — rate limiting + clean/typed kaynaklar)
**Dayanak:** SPEC_YOL2.md v3.0
**Dosyalar:** `src/data/data_hub.py`, `src/data/_hub_sources.py`, `src/data/_hub_types.py`

---

## Neden?

Eskiden her modul kendi veri baglantisinı kuruyordu:

```
macro_layer.py  ──►  EvdsClient()          (dogrudan)
backtest.py     ──►  yf.download()         (dogrudan)
smart_money.py  ──►  IsYatirimConnector()  (dogrudan)
```

Baska bir proje ayni veriyi almak istediginde tum ic yapiyi ogrenmek zorundaydi.
DataHub bu baglantilari kayit altina alir; disaridan tek bir API ile erisim saglanir.

**v1 -> v2:** import yolu + metod adi duzeltmeleri, 8 yeni kaynak.

**v2 -> v3:**
- `_RateLimiter` eklendi: yfinance (1/s), evds (1/3s), kap (1/2s), isyatirim (1/2s), fintables (1/5s), macro_global (1/5s)
- Paylasimli ham fetcher fonksiyonlari: raw + clean ayni limiter'i kullanir
- Clean/typed kaynaklar: `yfinance_clean`, `macro_global_clean`, `kap_clean`, `evds_clean`
- `src/data/_hub_types.py`: `MacroSnapshot` + `KAPItem` dataclass'lari

---

## Mimari

```
Kaynak A                      DataHub                    Consumer B
--------                     ---------                  ----------
Yahoo Finance     ------►   .get("yfinance", ...)       --► Backtest / L1
EVDS              ------►   .get("evds", ...)           --► L2 Macro / Exposure
KAP API           ------►   .get("kap", ...)            --► L3 KAP
                        \   .get("kap_scraper", ...)    --► (kap fallback)
Is Yatirim        ------►   .get("isyatirim", ...)      --► L5 Smart Money
Mynet News        ------►   .get("news", ...)           --► L4 Sentiment
VIOP CSV          ------►   .get("viop", ...)           --► L6 Risk
Fintables         ------►   .get("fintables", ...)      --► K2/K3
CDS (WGB)         ------►   .get("cds", ...)            --► L2 Macro Gate
TCMB              ------►   .get("tcmb", ...)           --► L2 Macro
BIST Foreign      ------►   .get("bist_foreign", ...)   --► L2 Macro
DXY               ------►   .get("dxy", ...)            --► L2 Macro
Global Macro      ------►   .get("macro_global", ...)   --► L2 Macro
EM Rel. Strength  ------►   .get("em_relative_strength",...) --► L2 Macro
BIST DataStore    ------►   .get("bist_datastore", ...) --► L5 Smart Money
Event Signals (*)------►   .get("event_signals", ...)  --► K4 Analiz
Event Returns (*) ------►   .get("event_returns", ...)  --► K4 IC
```

(*) FORWARD-ONLY — bkz. asagida.

**Mevcut moduller degismez.** Hub, mevcut fetcher'lari wrapper olarak register eder.

---

## Cache Tutarliligi

`macro_layer.py` -> `EvdsClient()` -> `data/snapshots/tlref.parquet`
`DataHub.get("evds")` -> `EvdsClient()` -> **ayni** `data/snapshots/tlref.parquet`

Hub yeni bir cache katmani eklemez. `_hub_sources.py`'deki fetcher fonksiyonlari
mevcut fetcher'lari cagirir; yazilan cache dosyalari ayni kalir.

---

## Kayitli Kaynaklar — Ozet Tablo

### Dis Kaynaklar (Canli API / Scrape)

| Kaynak | data_type | Auth | Fallback | Forward-Only | Staleness |
|--------|-----------|------|----------|--------------|-----------|
| `yfinance` | price | hayir | — | HAYIR | anlik |
| `macro_global` | macro | hayir | — | HAYIR | anlik |
| `evds` | macro | EVDS_API_KEY | `evds_snapshot` | HAYIR | gunluk/haftalik |
| `evds_snapshot` | macro | hayir | — | HAYIR | snapshot tarihi |
| `kap` | kap | kap-client | `kap_scraper` | HAYIR | ~24h |
| `kap_scraper` | kap | hayir | — | HAYIR | ~24h |
| `isyatirim` | foreign | hayir | — | HAYIR | 24h |
| `news` | news | hayir | — | HAYIR | 24h |
| `viop` | viop | hayir | — | HAYIR | gunluk |
| `fintables` | foreign | EMAIL+PASS | — | HAYIR | manuel |

### Yerel Makro Cache (SQLite: data/local_macro.db)

| Kaynak | data_type | Auth | Fallback | Forward-Only | Staleness |
|--------|-----------|------|----------|--------------|-----------|
| `cds` | macro | hayir | `cds_fallback` | HAYIR | CDS_STALE_DAYS |
| `cds_fallback` | macro | hayir | — | HAYIR | — |
| `tcmb` | macro | hayir | — | HAYIR | TCMB_STALE_DAYS |
| `bist_foreign` | macro | EVDS_API_KEY | YAML | HAYIR | 7 gun |
| `dxy` | macro | hayir | — | HAYIR | DXY_STALE_DAYS |
| `em_relative_strength` | macro | hayir | — | HAYIR | gunluk |

### Disk Magazalari

| Kaynak | data_type | Forward-Only | Baslangic | Not |
|--------|-----------|--------------|-----------|-----|
| `bist_datastore` | foreign | **EVET** | 2024-12 | aylik USD islem; SQLite |
| `event_signals` | kap | **EVET** | 2026-06-01 | immutable, on-kayit, clone3 |
| `event_returns` | kap | **EVET** | 2026-06-01+ | horizon olgunlasinca dolar |

### Clean / Typed Kaynaklar (v3)

| Kaynak | Ham Karsiligi | Donus Tipi | Rate Limit | Fallback |
|--------|--------------|-----------|-----------|----------|
| `yfinance_clean` | `yfinance` | `pd.DataFrame` (lowercase, DatetimeIndex) | paylasimli (_rl_yfinance) | — |
| `macro_global_clean` | `macro_global` | `MacroSnapshot` dataclass | paylasimli (_rl_macro) | — |
| `kap_clean` | `kap_scraper` | `list[KAPItem]` dataclass | paylasimli (_rl_kap) | — |
| `evds_clean` | `evds` | `pd.DataFrame` (DatetimeIndex, sutun=seri_kodu) | paylasimli (_rl_evds) | — |

**Clean kaynaklar icin fallback yok:** tip garantisi bozulamasin diye kasitli.
Ham kaynak + snapshot fallback icin raw kaynagi kullan.

---

## Kaynak Detaylari ve Parametreler

### `yfinance`
```python
DataHub.get("yfinance",
    ticker   = "AKBNK.IS",   # str -- ZORUNLU
    lookback = "1y",          # "1d","5d","1mo","3mo","6mo","1y","2y","5y","max"
    interval = "1d",          # "1d" | "1wk" | "1mo"
)
# -> pd.DataFrame  columns=[Open,High,Low,Close,Volume], DatetimeIndex
```

Yaygin ticker'lar:
- BIST hisseleri: `"AKBNK.IS"`, `"THYAO.IS"`, `"EREGL.IS"`
- Makro: `"USDTRY=X"`, `"^VIX"`, `"BZ=F"` (Brent), `"^GSPC"` (SP500), `"GC=F"` (Altin)
- BIST endeksleri: `"XU100.IS"`, `"XBANK.IS"`, `"TUR"` (iShares Turkey ETF)
- DXY: `"DX-Y.NYB"`

---

### `macro_global`
```python
DataHub.get("macro_global")
# -> dict {
#     "usdtry": float,              "usdtry_change_pct": float,
#     "vix": float,                 "vix_change_pct": float,
#     "oil_brent": float,           "oil_brent_change_pct": float,
#     "sp500": float,               "sp500_change_pct": float,
#     "gold": float,                "gold_change_pct": float,
# }
# Her deger son kapanis veya None (indir basarisiz oldugunda)
```

---

### `evds`
```python
DataHub.get("evds",
    series   = "TP.BISTTLREF.KAPANIS",  # str -- ZORUNLU; EVDS_API_KEY gerekli
    lookback = "1y",                     # "1y","2y","5y" vb.
)
# -> pd.DataFrame  columns=[date, value], tarih azalan sirali
```

Yaygin seri kodlari:

| Seri | Aciklama |
|------|---------|
| `TP.BISTTLREF.KAPANIS` | TLREF kapanis endeksi (gunluk) |
| `TP.BISTTLREF.ORAN` | TLREF faiz orani |
| `TP.MKBRGN.A` | BIST yabanci pay orani (haftalik %) |
| `TP.TUFE` | TUFE enflasyon endeksi |
| `TP.APIFON4` | TCMB agirlikli ort. fonlama orani |

---

### `evds_snapshot`
```python
DataHub.get("evds_snapshot",
    series = "TP.BISTTLREF.KAPANIS",
)
# -> pd.DataFrame -- dondurulmus tarihsel veri
# Dosya: data/snapshots/{seri_kucuk}_series.parquet
# FileNotFoundError: snapshot yoksa
```

---

### `kap`
```python
DataHub.get("kap",
    ticker = "THYAO",  # str -- ZORUNLU
    days   = 90,       # int -- kac gun geriye
)
# -> list[dict]  {index, publish_datetime, company_name, subject, summary, ...}
# Not: HT endpoint ~May 2026 bozuk; bos liste donebilir -> kap_scraper fallback
```

---

### `kap_scraper`
```python
DataHub.get("kap_scraper",
    ticker            = "THYAO",                 # str | list[str] | None
    watchlist_tickers = ["AKBNK", "EREGL"],      # list[str] | None
    company_names     = {"THYAO": "Turk Hava"},  # dict[str,str] | None
)
# -> list[dict]  {source, ticker, title, published, category, url}
# category: "CRITICAL" | "IMPORTANT" | "NOISE"
# ticker=None -> PORTFOLIO_TICKERS config
```

---

### `isyatirim`
```python
# Tek ticker
DataHub.get("isyatirim", ticker="AKBNK")
# -> dict  {foreign_ratio: float, delta_1w_bps: float, delta_1m_bps: float}

# Tum tickers
DataHub.get("isyatirim")
# -> dict[str, dict]  {"AKBNK": {...}, "THYAO": {...}, ...}
```

---

### `news`
```python
DataHub.get("news",
    ticker = "EREGL",  # str -- ZORUNLU
    days   = 7,        # int -- kac gun geriye
)
# -> list[dict]  [{title, date, source}, ...]
# Cache: data/news_cache.json (24h TTL)
```

---

### `viop`
```python
DataHub.get("viop",
    target_date = None,  # date | str | None -- None = bugun
)
# -> pd.DataFrame | None
# Sutunlar: ticker, type (call/put/future), expiry, strike, open_interest, volume
# Encoding: windows-1254; ayirici ";"; ondalik ","
```

---

### `fintables`
```python
DataHub.get("fintables")
# -> dict[str, bool]  {"AKBNK": True, "THYAO": False, ...}
# Gereksinim: FINTABLES_EMAIL + FINTABLES_PASSWORD env
# ~30sn surebilir; sadece BIST50 kapsami
```

---

### `cds`
```python
DataHub.get("cds")
# -> dict | None  {data_date, cds_bps, source, confidence, fetched_at}
# cds_bps: Turkiye 5Y CDS baz puan
# Kaynak: World Gov Bonds API -> cds_fallback (yfinance proxy)
```

---

### `cds_fallback`
```python
DataHub.get("cds_fallback")
# -> dict | None  {data_date, cds_bps, source, confidence, fetched_at}
# Model: CDS_est = base + a*(USDTRY - baseline) + b*VIX + c*TUR_return
# Sinirlar: [100, 800] bps
```

---

### `tcmb`
```python
DataHub.get("tcmb")
# -> dict | None  {decision_date, decision_type, rate_before, rate_after,
#                  source, confidence, fetched_at}
# decision_type: "RATE_HOLD" | "RATE_HIKE" | "RATE_CUT"
# Kaynak: tcmb.gov.tr + EVDS (ikili)
```

---

### `bist_foreign`
```python
DataHub.get("bist_foreign")
# -> dict | None  {week_ending_date, foreign_ownership_pct,
#                  pct_change_weekly, source, confidence, fetched_at}
# Kaynak: EVDS TP.MKBRGN.A
# Not: L2 makro context; L5 icin bkz. isyatirim (gunluk) / bist_datastore (aylik)
```

---

### `dxy`
```python
DataHub.get("dxy")
# -> dict | None  {data_date, close, weekly_change_pct, fetched_at}
# Ticker: DX-Y.NYB
# Yorum: Yuksek DXY = USD guclu = EM sermaye cikisi = BIST icin negatif
```

---

### `em_relative_strength`
```python
DataHub.get("em_relative_strength",
    lookback_days = 20,  # int | None -- None: EM_RELSTRENGTH_LOOKBACK sabitini kullanir
)
# -> float | None  [-1.0, +1.0]
# +1.0 = BIST EM endeksini (EEM) guclu sekilde geciyor
# -1.0 = BIST EM endeksinin guclu sekilde gerisinde
# None = veri indirilemedi veya yetersiz tarih
```

---

### `bist_datastore` -- FORWARD-ONLY
```python
DataHub.get("bist_datastore",
    ticker = "AKBNK",  # str | None -- None: tum tablo
)
# -> pd.DataFrame  columns=[date, ticker, usd_net_trades, ...]
# FORWARD-ONLY: 2024-12'den itibaren birikimli; onceki veri yoktur.
# Guncelleme: scripts/sync_datastore.py (aylik ZIP indir + parse)
# DB: data/bist_datastore/foreign_monthly.db
```

---

### `event_signals` -- FORWARD-ONLY
```python
DataHub.get("event_signals",
    ticker = "THYAO",       # str | None -- None: tum kayitlar
    after  = "2026-06-01",  # str | None -- "YYYY-MM-DD" baslangic filtresi
)
# -> pd.DataFrame  columns=[natural_key, event_date, ticker, event_type,
#                            surprise_real, technical_confirm, signal_fired, as_of_timestamp]
# FORWARD-ONLY: 2026-06-01'den itibaren birikimli
# Immutable: (event_date, ticker, event_type) uzerinde idempotent
# Task Scheduler: clone3/data/event_logs/, 19:00 gunluk kayit
# DIKKAT: clone3 silinirse veri kaybolur
```

---

### `event_returns` -- FORWARD-ONLY
```python
DataHub.get("event_returns",
    ticker  = "THYAO",  # str | None
    horizon = 20,       # int | None -- 1 | 5 | 20 | 60 (gun)
)
# -> pd.DataFrame  columns=[natural_key, ticker, event_date, event_type,
#                            horizon, entry_date, exit_date,
#                            gross_return, rel_net_return, filled_at]
# FORWARD-ONLY: on-kayitlar olgunlasinca dolar
#   t+1  -> min 1 is gunu sonra
#   t+5  -> yaklasik Haziran 2026'dan itibaren
#   t+20 -> yaklasik Temmuz 2026'dan itibaren
#   t+60 -> yaklasik Agustos 2026'dan itibaren
# Not: event_signals dolmadan bu tablo bos kalabilir -- normaldir.
```

---

## Rate Limiting

`_hub_sources.py` modul seviyesinde 6 `_RateLimiter` instance'i tutar.
Tum cagrilar arasinda **paylasimli state** — singletons, process-level.

| Limiter | Kaynak(lar) | Limit | Neden |
|---------|------------|-------|-------|
| `_rl_yfinance` | `yfinance`, `yfinance_clean` | 1 istek/sn | Yahoo Finance soft rate limit |
| `_rl_macro` | `macro_global`, `macro_global_clean` | 1 istek/5 sn | ic olarak 5 yfinance cagrisi yapar |
| `_rl_evds` | `evds`, `evds_clean` | 1 istek/3 sn | TCMB devlet API'si; agresif polling yasak |
| `_rl_kap` | `kap_scraper`, `kap_clean` | 1 istek/2 sn | RSS/scraping —礼儀 (kibarca) |
| `_rl_isyatirim` | `isyatirim` | 1 istek/2 sn | Is Yatirim screener scraping |
| `_rl_fintables` | `fintables` | 1 istek/5 sn | Playwright oturumu, zaten yavas |

Rate-limit **uygulanmayan** kaynaklar (dogrudan local DB/disk okuma):
`cds`, `cds_fallback`, `tcmb`, `bist_foreign`, `dxy` — SQLite; `bist_datastore`, `event_*` — Parquet.

---

## Clean / Typed Kaynaklar

Ham kaynaklar (`yfinance`, `macro_global`, vb.) veriyi oldugu gibi dondurur.
Clean kaynaklar ayni ham fetcher fonksiyonunu cagirip normalize eder —
**ekstra HTTP cagrisi yok, rate limiter paylasimli.**

Tipler `src/data/_hub_types.py` dosyasinda tanimlanir.

### `yfinance_clean`
```python
DataHub.get("yfinance_clean",
    ticker   = "AKBNK.IS",   # str -- ZORUNLU
    lookback = "1y",          # yfinance period
    interval = "1d",          # "1d" | "1wk" | "1mo"
)
# -> pd.DataFrame
#    index   : DatetimeIndex(date), tz-naive, artan
#    sutunlar: [ticker, open, high, low, close, volume, adj_close]  (lowercase)
```

Ham karsiligi `yfinance` ile fark:
- Sutun adlari lowercase (`Open` -> `open`)
- `ticker` sutunu eklendi
- Timezone temizlendi (tz-naive)
- Artan sirali (yfinance varsayilani azalan olabilir)

---

### `macro_global_clean`
```python
snap = DataHub.get("macro_global_clean")
# -> MacroSnapshot | None
#    snap.usdtry               # float | None
#    snap.usdtry_change_pct    # float | None
#    snap.vix                  # float | None
#    snap.vix_change_pct       # float | None
#    snap.oil_brent            # float | None
#    snap.oil_brent_change_pct # float | None
#    snap.sp500                # float | None
#    snap.sp500_change_pct     # float | None
#    snap.gold                 # float | None
#    snap.gold_change_pct      # float | None
```

Ham karsiligi `macro_global` ile fark:
- `dict` yerine `MacroSnapshot` dataclass (IDE autocomplete + type checking)
- `snap.vix` daha okunabilir, `snap["vix"]` yok (KeyError riski yok)

---

### `kap_clean`
```python
items = DataHub.get("kap_clean",
    ticker            = "THYAO",
    watchlist_tickers = ["AKBNK"],
    company_names     = {"THYAO": "Turk Hava"},
)
# -> list[KAPItem]
#    item.source       # str   ("google_news" | "mynet" vb.)
#    item.ticker       # str | None
#    item.title        # str
#    item.published    # str   (ISO veya ham tarih string)
#    item.category     # "CRITICAL" | "IMPORTANT" | "NOISE"
#    item.url          # str
#    item.is_critical  # bool  (property: category == "CRITICAL")

criticals = [i for i in items if i.is_critical]
```

Ham karsiligi `kap_scraper` ile fark:
- `list[dict]` yerine `list[KAPItem]` (attribute erisimi, is_critical property)
- `dict.get()` yerine dogrudan `item.category` (KeyError riski yok)

---

### `evds_clean`
```python
df = DataHub.get("evds_clean",
    series   = "TP.BISTTLREF.KAPANIS",
    lookback = "1y",
)
# -> pd.DataFrame
#    index   : DatetimeIndex(date), artan
#    sutunlar: ["tp_bisttlref_kapanis"]  (nokta -> alt_cizgi, lowercase)
#
# Baska ornek:
# DataHub.get("evds_clean", series="TP.APIFON4")
# -> sutun: "tp_apifon4"
```

Ham karsiligi `evds` ile fark:
- `date` sutunu yerine `DatetimeIndex` (pandas iloc/loc ile kolay erisim)
- `value` sutunu yerine seri adini tasiyan sutun (hangi seri oldugu belli)
- Artan tarih sirasi (analiz icin daha kulisanisli)

**Not:** `evds_clean` icin EVDS_API_KEY gerekir; basarisiz olursa `evds_snapshot`'a
dusmez (tip garantisi bozulamasin diye). Ham `evds` + snapshot fallback icin:
```python
df_raw = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS")  # snapshot'a duser
```

---

## Kullanim

### Bu repoda

```python
from src.data.data_hub import DataHub

# Fiyat verisi
df = DataHub.get("yfinance", ticker="AKBNK.IS", lookback="6mo")

# Global makro bundle
macro = DataHub.get("macro_global")
print(f"USDTRY: {macro['usdtry']}, VIX: {macro['vix']}")

# EVDS makro serisi
tlref = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS", lookback="1y")

# TCMB son karar
tcmb = DataHub.get("tcmb")
if tcmb:
    print(f"{tcmb['decision_date']}: {tcmb['decision_type']}, faiz={tcmb['rate_after']}%")

# KAP haberler
news = DataHub.get("kap_scraper", ticker="EREGL")

# Forward-only olay sinyalleri (2026-06-01'den)
events = DataHub.get("event_signals", ticker="THYAO")

# Tum kaynak listesi
for src in DataHub.list_sources():
    print(f"{src['name']:25s} | {src['data_type']:8s} | auth={src['auth_required']}")
```

### Baska bir BIST projesinden

```python
import sys
sys.path.insert(0, r"<local-path>")

from src.data.data_hub import DataHub

# Kaynak detayini bilmene gerek yok
df    = DataHub.get("yfinance", ticker="YKBNK.IS", lookback="1y")
tlref = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS")
cds   = DataHub.get("cds")
macro = DataHub.get("macro_global")
tcmb  = DataHub.get("tcmb")
```

---

## Fallback Zincirleri

```
evds        --fail-->  evds_snapshot  --fail-->  Exception
kap         --fail-->  kap_scraper    --fail-->  Exception
cds         --fail-->  cds_fallback   --fail-->  Exception
```

Diger kaynaklar (tcmb, bist_foreign, dxy, vb.) kendi ic fallback mekanizmalarina sahip
(YAML cache, EVDS alternatif seriler) ama DataHub seviyesinde fallback tanimlamaz.
Bu kaynaklar basarisiz olursa None donebilir; exception fırlatılmaz.

---

## Yeni Kaynak Ekleme

`src/data/_hub_sources.py` dosyasina yeni bir `_make_*` fonksiyonu ekle:

```python
def _make_my_source(DataSource: type) -> DataSource:
    def fetch(ticker: str, **_):
        from src.data.my_fetcher import MyFetcher  # lazy import -- ZORUNLU
        return MyFetcher().get(ticker)

    return DataSource(
        name="my_source",
        description="Aciklama",
        data_type="price",         # price | macro | kap | foreign | news | viop
        fetcher=fetch,
        fallback="yfinance",       # opsiyonel
        auth_required=False,
        tags=["price", "custom"],
    )
```

Sonra `register_all()` icindeki `makers` listesine `_make_my_source` ekle.

---

## Mimari Kurallar

- `data_hub.py` ve `_hub_sources.py` **`engine.py` veya `MASTER_WEIGHTS` import etmez**
  (architecture testleri bunu zorunlu kilar).
- Tum fetcher importlari fonksiyon govdelerinde **lazy** yapilir (modul seviyesinde import yok).
- Hub yeni bir DB/cache katmani eklemez; mevcut fetcher'larin cache'ini kullanir.

---

## Ne Degil

- DataHub bir **tam ORM veya data warehouse degil** — kalici depolama, sorgu motoru,
  sema versiyonlama yok. ETL pipeline ihtiyaci varsa bu repoya degil ayri bir servise aittir.
- **Retry yapmaz** — gecici ag hatalarinda yeniden deneme fetcher modullerinin sorumlulugunda.
- **Yetkilendirme yapmaz** — `auth_required` bir bilgi etiketi, erisim kontrolu degil.
- **Ham kaynaklar hala normalize etmez** — `yfinance` hala `pd.DataFrame(Open=...)` dondurur.
  Normalize edilmis veri icin `yfinance_clean` gibi `_clean` varyantini kullan.
