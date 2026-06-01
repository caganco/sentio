# DATA HUB — Merkezi Veri Router

**Tarih:** 1 Haziran 2026  
**Dayanak:** SPEC_YOL2.md v3.0, D-190 envanter  
**Dosyalar:** `src/data/data_hub.py`, `src/data/_hub_sources.py`

---

## Neden?

Eskiden her modül kendi veri bağlantısını kuruyordu:

```
macro_layer.py  ──►  EvdsClient()          (doğrudan)
backtest.py     ──►  yf.download()         (doğrudan)
smart_money.py  ──►  IsYatirimConnector()  (doğrudan)
```

Başka bir proje aynı veriyi almak istediğinde tüm iç yapıyı öğrenmek zorundaydı.  
DataHub bu bağlantıları kayıt altına alır; dışarıdan tek bir API ile erişilir.

---

## Mimari

```
Kaynak A                   DataHub                Consumer B
────────                  ─────────              ──────────
Yahoo Finance  ──────►   .get("yfinance", ...)  ──► Backtest
EVDS           ──────►   .get("evds", ...)      ──► Macro Layer
KAP API        ──────►   .get("kap", ...)       ──► Screening
Is Yatirim     ──────►   .get("isyatirim", ...) ──► Smart Money
Fintables      ──────►   .get("fintables", ...) ──► K2/K3
CDS            ──────►   .get("cds", ...)       ──► Macro Gate
VIOP           ──────►   .get("viop", ...)      ──► VIOP Layer
Mynet News     ──────►   .get("news", ...)      ──► Sentiment
BIST Datastore ──────►   .get("bist_datastore", ...) ──► L5
```

**Mevcut modüller değişmez.** Hub, mevcut fetcher'ları wrapper olarak register eder.  
`macro_layer.py` hâlâ `EvdsClient()` çağırabilir — bu bir zorunluluk değil.

---

## Cache Tutarlılığı

`macro_layer.py` → `EvdsClient()` → `data/snapshots/tlref.parquet`  
`DataHub.get("evds")` → `EvdsClient()` → **aynı** `data/snapshots/tlref.parquet`

Hub yeni bir cache katmanı eklemez. `_hub_sources.py`'deki fetcher fonksiyonları
mevcut fetcher'ları çağırır; yazılan cache dosyaları aynı kalır. İki farklı
okuyucu, tek cache.

---

## Kayıtlı Kaynaklar

| Kaynak | data_type | Auth | Fallback | Fetcher Modülü |
|--------|-----------|------|----------|----------------|
| `yfinance` | price | ❌ | — | `yfinance` SDK |
| `evds` | macro | ✅ EVDS_API_KEY | `evds_snapshot` | `src/data/evds_client.py` |
| `evds_snapshot` | macro | ❌ | — | `data/snapshots/*.parquet` |
| `kap` | kap | ✅ MKK_VYK_TOKEN | `kap_scraper` | `src/data/kap_fetcher.py` |
| `isyatirim` | foreign | ❌ | — | `src/signals/layers/connectors/smart_money_connector.py` |
| `news` | news | ❌ | — | `src/data/news_fetcher.py` |
| `viop` | viop | ❌ | — | `src/data/viop_fetcher.py` |
| `bist_datastore` | foreign | ❌ | — | `data/bist_datastore/foreign_monthly.db` |
| `fintables` | foreign | ✅ EMAIL/PASS | — | `src/data/fintables_scraper.py` |
| `cds` | macro | ❌ | `cds_fallback` | `src/signals/local/cds_client.py` |
| `cds_fallback` | macro | ❌ | — | `src/signals/local/cds_fallback.py` |

---

## Kullanım

### Bu repoda

```python
from src.data.data_hub import DataHub

# Fiyat verisi
df = DataHub.get("yfinance", ticker="AKBNK.IS", lookback="6mo")

# EVDS makro serisi
tlref = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS", lookback="1y")

# Yabancı saklama oranı
custody = DataHub.get("isyatirim", ticker="AKBNK")

# Haberler
news = DataHub.get("news", ticker="EREGL", days=14)

# VIOP Put/Call
viop = DataHub.get("viop")

# Tüm kaynak listesi
for src in DataHub.list_sources():
    print(f"{src['name']:20s} | {src['data_type']:8s} | auth={src['auth_required']}")
```

### Başka bir BIST projesinden

```python
import sys
sys.path.insert(0, r"<local-path>")

from src.data.data_hub import DataHub

# Aynı API — kaynak detayını bilmene gerek yok
df   = DataHub.get("yfinance", ticker="YKBNK.IS", lookback="1y")
tlref = DataHub.get("evds", series="TP.BISTTLREF.KAPANIS")
```

---

## Fallback Zinciri

Bir kaynak hata verirse DataHub otomatik olarak `fallback` kaynağa geçer.
Hem primary hem fallback hata verirse exception fırlatılır.

```
evds  ──fail──►  evds_snapshot  ──fail──►  Exception
kap   ──fail──►  kap_scraper    ──fail──►  Exception
cds   ──fail──►  cds_fallback   ──fail──►  Exception
```

---

## Yeni Kaynak Ekleme

`src/data/_hub_sources.py` dosyasına yeni bir `_make_*` fonksiyonu ekle:

```python
def _make_my_source(DataSource: type) -> DataSource:
    def fetch(ticker: str, **_):
        from src.data.my_fetcher import MyFetcher  # lazy import
        return MyFetcher().get(ticker)

    return DataSource(
        name="my_source",
        description="Açıklama",
        data_type="price",         # price | macro | kap | foreign | news | viop
        fetcher=fetch,
        fallback="yfinance",       # opsiyonel
        auth_required=False,
        tags=["price", "custom"],
    )
```

Sonra `register_all()` içindeki `makers` listesine `_make_my_source` ekle.  
Mevcut modüllere dokunma gerekmez.

---

## Mimari Kurallar

- `data_hub.py` ve `_hub_sources.py` **`engine.py` veya `MASTER_WEIGHTS` import etmez** (architecture testleri bunu zorunlu kılar).  
- Tüm fetcher importları fonksiyon gövdelerinde **lazy** yapılır (modül seviyesinde import yok).  
- Hub yeni bir DB/cache katmanı eklemez; mevcut fetcher'ların cache'ini kullanır.

---

## Ne Değil

- DataHub bir **ORM veya data warehouse değil** — sadece routing ve fallback.
- **Transformation/normalization yapmaz** — ham veriyi olduğu gibi döndürür.
- **Rate limiting / retry yapmaz** — bu sorumluluk fetcher modüllerine aittir.
