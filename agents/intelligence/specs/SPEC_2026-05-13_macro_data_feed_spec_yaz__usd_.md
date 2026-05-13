# SPEC: Macro Data Feed

## Tanım
USD/TRY, Brent crude, VIX ve BIST100 verilerini Yahoo Finance'dan çekerek mevcut fetcher.py ile entegre eden, SQLite'a kaydeden ve günlük otomatik güncelleme yapan macro data feed modülü.

## Dosya Yapısı
```
src/
  data/
    fetcher.py          # MEVCUT - entegre edilecek
    macro_feed.py       # YENİ - ana modül
    macro_scheduler.py  # YENİ - günlük otomatik güncelleme
    db/
      schema.sql        # YENİ - SQLite tablo tanımları
intelligence/
  specs/
    SPEC_2025-01-31_macro-data-feed.md
data/
  market.db             # SQLite dosyası (oluşturulacak)
```

## Fonksiyon İmzaları

### macro_feed.py
```python
MACRO_TICKERS = {
    "USDTRY": "TRY=X",
    "BRENT":  "BZ=F",
    "VIX":    "^VIX",
    "BIST100": "XU100.IS"
}

def fetch_macro_snapshot(
    tickers: dict[str, str] = MACRO_TICKERS,
    period: str = "1d"
) -> pd.DataFrame:
    """
    Yahoo Finance'dan anlık/günlük macro veri çeker.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """

def fetch_macro_history(
    tickers: dict[str, str] = MACRO_TICKERS,
    start: str = "2020-01-01",
    end: str | None = None          # None → bugün
) -> pd.DataFrame:
    """
    Belirtilen tarih aralığı için tarihsel macro veri çeker.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """

def save_to_db(
    df: pd.DataFrame,
    db_path: str = "data/market.db",
    table: str = "macro_data"
) -> int:
    """
    DataFrame'i SQLite'a upsert eder (date+symbol unique).
    Returns: kaydedilen/güncellenen satır sayısı
    """

def load_from_db(
    symbols: list[str] | None = None,   # None → hepsi
    start: str | None = None,
    end: str | None = None,
    db_path: str = "data/market.db"
) -> pd.DataFrame:
    """
    SQLite'tan macro veri okur, filtreler.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """

def get_latest_snapshot(
    db_path: str = "data/market.db"
) -> pd.DataFrame:
    """
    Her sembol için en son kaydı döner.
    Returns: DataFrame [symbol, date, close, pct_change_1d]
    """
```

### macro_scheduler.py
```python
def run_daily_update(
    db_path: str = "data/market.db",
    log_path: str = "logs/macro_feed.log"
) -> dict:
    """
    Günlük güncelleme job'ı: fetch → save → log.
    Returns: {"updated_rows": int, "symbols": list, "timestamp": str, "errors": list}
    """

def schedule_daily(
    run_time: str = "18:30",        # TRY kapanış sonrası
    db_path: str = "data/market.db"
) -> None:
    """
    schedule kütüphanesi ile her gün run_time'da çalıştırır.
    Blocking loop - servis olarak çalışır.
    """

def backfill_missing(
    db_path: str = "data/market.db",
    start: str = "2020-01-01"
) -> int:
    """
    DB'de eksik tarihleri tespit edip doldurur.
    Returns: eklenen satır sayısı
    """
```

## Input/Output Formatları

### fetch_macro_snapshot() Output
```python
# DataFrame örneği
{
  "date":   ["2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31"],
  "symbol": ["USDTRY",     "BRENT",      "VIX",        "BIST100"],
  "open":   [35.21,        76.40,        15.30,        9821.50],
  "high":   [35.45,        77.10,        16.20,        9901.00],
  "low":    [35.18,        76.10,        15.10,        9780.00],
  "close":  [35.38,        76.85,        15.75,        9876.30],
  "volume": [0,            12500,        0,            45230000]
}
```

### SQLite Tablo Şeması (schema.sql)
```sql
CREATE TABLE IF NOT EXISTS macro_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL    NOT NULL,
    volume      INTEGER DEFAULT 0,
    updated_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_macro_date   ON macro_data(date);
CREATE INDEX IF NOT EXISTS idx_macro_symbol ON macro_data(symbol);
CREATE INDEX IF NOT EXISTS idx_macro_ds     ON macro_data(date, symbol);
```

### run_daily_update() Output
```python
{
    "updated_rows": 4,
    "symbols": ["USDTRY", "BRENT", "VIX", "BIST100"],
    "timestamp": "2025-01-31T18:30:05",
    "errors": []          # hata varsa: ["VIX: timeout"]
}
```

## Mevcut fetcher.py Entegrasyonu
```python
# fetcher.py içinde ne tür bir yapı varsa buna uyum sağla:
# Seçenek A - fetcher.py'de yfinance kullanıyorsa:
from data.fetcher import fetch_yfinance          # mevcut fonksiyonu kullan

# Seçenek B - fetcher.py abstract base ise:
from data.fetcher import BaseFetcher
class MacroFetcher(BaseFetcher):
    def fetch(self, ticker: str, **kwargs) -> pd.DataFrame: ...

# Seçenek C - fetcher.py bağımsızsa:
# macro_feed.py doğrudan yfinance kullanır, fetcher.py'yi import etmez
# ama aynı DataFrame şemasını (date, symbol, open, high, low, close, volume) korur
```

## Bağımlılıklar
```
yfinance>=0.2.36
pandas>=2.0.0
numpy>=1.24.0
schedule>=1.2.0
sqlalchemy>=2.0.0    # opsiyonel, doğrudan sqlite3 de kullanılabilir
python-dotenv>=1.0.0 # db path env'den okunabilsin
```

## Hata Yönetimi
```python
# Her sembol bağımsız try/except içinde fetch edilmeli
# Bir sembol başarısız olursa diğerleri etkilenmemeli
# Retry: 3 deneme, 5 saniye ara
# Timeout: 30 saniye per request
# Partial success kabul edilir (3/4 sembol başarılı → kaydet, 1'i log'a yaz)
```

## Test Kriteri

```python
# test_macro_feed.py

def test_fetch_snapshot():
    df = fetch_macro_snapshot()
    assert len(df) == 4
    assert set(df["symbol"]) == {"USDTRY", "BRENT", "VIX", "BIST100"}
    assert df["close"].notna().all()
    assert "date" in df.columns

def test_save_and_load():
    df = fetch_macro_snapshot()
    rows = save_to_db(df, db_path="data/test.db")
    assert rows >= 1
    loaded = load_from_db(db_path="data/test.db")
    assert len(loaded) >= 4
    # Upsert testi - tekrar kaydetse duplicate olmamalı
    rows2 = save_to_db(df, db_path="data/test.db")
    loaded2 = load_from_db(db_path="data/test.db")
    assert len(loaded2) == len(loaded)  # satır artmamalı

def test_history_fetch():
    df = fetch_macro_history(start="2024-01-01", end="2024-01-31")
    assert len(df) > 0
    assert df["date"].min() >= "2024-01-01"
    assert df["date"].max() <= "2024-01-31"

def test_latest_snapshot():
    snap = get_latest_snapshot(db_path="data/test.db")
    assert "pct_change_1d" in snap.columns
    assert len(snap) == 4

def test_daily_update_job():
    result = run_daily_update(db_path="data/test.db", log_path="logs/test.log")
    assert result["updated_rows"] >= 1
    assert len(result["errors"]) == 0
    assert result["timestamp"] is not None

# Hızlı manuel smoke test:
# python -c "from src.data.macro_feed import fetch_macro_snapshot, get_latest_snapshot; print(get_latest_snapshot())"
```

## Notlar
- `date` kolonu her zaman `str` tipinde `YYYY-MM-DD` formatında saklanır
- BIST100 hafta sonu veri döndürmez → boş DataFrame normal davranış
- VIX ve USDTRY volume=0 olabilir → hata değil
- Scheduler log rotation yok, basit append log yeterli ilk versiyonda
- `data/market.db` `.gitignore`'a eklenmeli