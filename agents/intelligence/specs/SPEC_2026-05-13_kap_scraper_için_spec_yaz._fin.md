# SPEC: KAP Scraper - Finansal Tablolar ve Özel Durumlar

## Tanım
KAP (Kamuoyu Aydınlatma Platformu) üzerinden BIST şirketlerine ait finansal tablo açıklamalarını ve özel durum bildirimlerini çeken, yapılandırılmış formatta saklayan scraper modülü.

## Dosya Yapısı
```
src/
  scrapers/
    __init__.py
    kap_scraper.py        # Ana scraper sınıfı
    kap_parser.py         # HTML/JSON parse işlemleri
    kap_models.py         # Pydantic data modelleri
  data/
    raw/
      financials/         # Ham finansal tablo JSON'ları
      disclosures/        # Ham özel durum bildirimleri
    processed/
      financials/         # İşlenmiş finansal veriler
      disclosures/        # İşlenmiş özel durumlar
tests/
  test_kap_scraper.py
intelligence/
  specs/
    SPEC_2025-01-31_kap-scraper.md
```

## Fonksiyon İmzaları

### `kap_scraper.py`
```python
class KAPScraper:
    BASE_URL = "https://www.kap.org.tr"
    API_URL  = "https://www.kap.org.tr/tr/api"

    def __init__(
        self,
        delay: float = 1.5,
        timeout: int = 30,
        max_retries: int = 3
    ) -> None:
        """Rate-limited, retry destekli scraper."""

    def get_company_list(self) -> list[dict]:
        """Tüm BIST şirketlerini döner. [{ticker, name, kap_id}, ...]"""

    def get_financial_disclosures(
        self,
        ticker: str,
        year: int | None = None,
        period: str | None = None,   # "3", "6", "9", "12"
        limit: int = 10
    ) -> list["FinancialDisclosure"]:
        """Şirkete ait finansal tablo açıklamalarını çeker."""

    def get_special_disclosures(
        self,
        ticker: str,
        start_date: str | None = None,   # "YYYY-MM-DD"
        end_date:   str | None = None,
        limit: int = 50
    ) -> list["SpecialDisclosure"]:
        """Özel durum bildirimlerini çeker."""

    def get_financial_tables(
        self,
        disclosure_id: str
    ) -> "FinancialTables":
        """Tek bir açıklama ID'si için bilanço/gelir/nakit tablolarını çeker."""

    def _request(
        self,
        url: str,
        params: dict | None = None
    ) -> dict:
        """Rate-limited GET, retry logic ile. Ham JSON döner."""

    def _save_raw(
        self,
        data: dict,
        category: str,   # "financials" | "disclosures"
        filename: str
    ) -> str:
        """Ham veriyi data/raw/{category}/{filename}.json olarak kaydeder."""
```

### `kap_parser.py`
```python
def parse_balance_sheet(raw: dict) -> dict:
    """Ham JSON'dan bilanço kalemlerini {hesap_kodu: {dönem: değer}} şeklinde döner."""

def parse_income_statement(raw: dict) -> dict:
    """Ham JSON'dan gelir tablosu kalemlerini döner."""

def parse_cash_flow(raw: dict) -> dict:
    """Ham JSON'dan nakit akış tablosunu döner."""

def parse_special_disclosure(raw: dict) -> dict:
    """Özel durum bildiriminin başlık, tarih, özet, tam metin alanlarını ayıklar."""

def normalize_value(val: str | int | float) -> float | None:
    """'1.234.567,89' → 1234567.89 dönüşümü. Geçersiz → None."""

def detect_currency_unit(raw: dict) -> tuple[str, int]:
    """Para birimi ve çarpanı döner. ('TRY', 1000) gibi."""
```

### `kap_models.py`
```python
from pydantic import BaseModel
from datetime import date, datetime

class FinancialDisclosure(BaseModel):
    disclosure_id:  str
    ticker:         str
    company_name:   str
    period:         str          # "2024/12", "2024/9" vb.
    period_type:    str          # "annual" | "quarterly"
    disclosure_date: datetime
    financial_type: str          # "consolidated" | "standalone"
    url:            str

class SpecialDisclosure(BaseModel):
    disclosure_id:  str
    ticker:         str
    company_name:   str
    title:          str
    summary:        str | None
    full_text:      str | None
    disclosure_date: datetime
    disclosure_type: str         # KAP kategori kodu
    url:            str
    is_material:    bool         # Önemli gelişme mi?

class FinancialTables(BaseModel):
    disclosure_id:   str
    ticker:          str
    period:          str
    currency:        str         # "TRY", "USD"
    unit_multiplier: int         # 1, 1000, 1000000
    balance_sheet:   dict[str, dict[str, float | None]]
    income_statement: dict[str, dict[str, float | None]]
    cash_flow:       dict[str, dict[str, float | None]]
    scraped_at:      datetime
```

## Input/Output Formatları

```python
# get_financial_disclosures("THYAO", year=2024) → Liste
[
  {
    "disclosure_id": "1234567",
    "ticker": "THYAO",
    "company_name": "TÜRK HAVA YOLLARI A.O.",
    "period": "2024/9",
    "period_type": "quarterly",
    "disclosure_date": "2024-11-12T08:30:00",
    "financial_type": "consolidated",
    "url": "https://www.kap.org.tr/tr/Bildirim/1234567"
  },
  ...
]

# get_financial_tables("1234567") → FinancialTables
{
  "disclosure_id": "1234567",
  "ticker": "THYAO",
  "period": "2024/9",
  "currency": "USD",
  "unit_multiplier": 1000,
  "balance_sheet": {
    "Dönen Varlıklar": {"2024/9": 5432100.0, "2023/12": 4987600.0},
    "Nakit ve Nakit Benzerleri": {"2024/9": 1234000.0, "2023/12": 987000.0}
  },
  "income_statement": {
    "Hasılat": {"2024/9": 9876000.0, "2023/9": 8765000.0},
    "Brüt Kar": {"2024/9": 2345000.0, "2023/9": 2100000.0}
  },
  "cash_flow": {...},
  "scraped_at": "2025-01-31T14:22:00"
}

# get_special_disclosures("THYAO", start_date="2024-01-01") → Liste
[
  {
    "disclosure_id": "9876543",
    "ticker": "THYAO",
    "title": "Yönetim Kurulu Karar Bildirimi",
    "summary": "...",
    "full_text": "...",
    "disclosure_date": "2024-11-10T09:15:00",
    "disclosure_type": "YK",
    "is_material": true,
    "url": "..."
  }
]

# Ham kayıt: data/raw/financials/THYAO_1234567.json
# İşlenmiş: data/processed/financials/THYAO_2024Q3.json
```

## Bağımlılıklar
```
requests>=2.31
pydantic>=2.0
beautifulsoup4>=4.12
lxml>=5.0
tenacity>=8.2        # retry dekoratörü
pandas>=2.0          # tablo dönüşümleri
python-dateutil>=2.8
ratelimit>=2.2
fake-useragent>=1.4  # bot tespitini azalt
```

## Test Kriteri

```python
# tests/test_kap_scraper.py

def test_company_list():
    scraper = KAPScraper()
    companies = scraper.get_company_list()
    assert len(companies) > 400          # BIST'te 500+ şirket var
    assert all("ticker" in c for c in companies)
    assert any(c["ticker"] == "THYAO" for c in companies)

def test_financial_disclosures():
    scraper = KAPScraper()
    disclosures = scraper.get_financial_disclosures("THYAO", year=2024)
    assert len(disclosures) > 0
    assert all(d.ticker == "THYAO" for d in disclosures)
    assert all(d.period.startswith("2024") for d in disclosures)

def test_financial_tables():
    scraper = KAPScraper()
    disclosures = scraper.get_financial_disclosures("THYAO", limit=1)
    tables = scraper.get_financial_tables(disclosures[0].disclosure_id)
    assert tables.balance_sheet != {}
    assert tables.income_statement != {}
    assert isinstance(tables.unit_multiplier, int)
    # Bilanço kontrolü: Toplam Varlık = Toplam Kaynaklar (±%1 tolerans)

def test_special_disclosures():
    scraper = KAPScraper()
    disclosures = scraper.get_special_disclosures(
        "THYAO",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    assert len(disclosures) > 0
    assert all(d.disclosure_date.year == 2024 for d in disclosures)

def test_normalize_value():
    from src.scrapers.kap_parser import normalize_value
    assert normalize_value("1.234.567,89") == 1234567.89
    assert normalize_value("(500,00)")     == -500.0   # parantez = negatif
    assert normalize_value("-")            is None

def test_rate_limiting():
    import time
    scraper = KAPScraper(delay=1.0)
    start = time.time()
    for ticker in ["THYAO", "GARAN", "AKBNK"]:
        scraper.get_financial_disclosures(ticker, limit=1)
    elapsed = time.time() - start
    assert elapsed >= 2.0   # en az 2 delay geçmeli
```

---

**Notlar (Builder için):**
- KAP'ın undocumented JSON API'si mevcut: `/tr/api/memberDisclosureQuery` endpoint'i kullan, HTML parse'a gerek yok
- `disclosure_index` parametresi sayfalama için kullanılır
- Bazı tablolar nested JSON, bazıları düz tablo — parser her iki formatı handle etmeli
- Şirket bazlı `kap_member_id` gerekiyor, ticker → kap_id mapping önce çekilmeli