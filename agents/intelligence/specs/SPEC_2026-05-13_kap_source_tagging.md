# SPEC: KAP Scraper Source Type Tagging

## Tanım
Haber çekme pipeline'ı şu an KAP resmi bildirimi ile haber medyasını aynı obje olarak işliyor. Her habere `source_type` alanı eklenecek: `kap_official` / `news_media` / `unknown`. Analyst bu bilgiyi güven seviyesi için kullanacak.

## Değiştirilecek Dosya
```
src/data/kap_scraper.py
```

## Fonksiyon İmzaları

```python
# Yeni sabit — dosya başında
SOURCE_TYPE = Literal["kap_official", "news_media", "unknown"]

KAP_OFFICIAL_DOMAINS: set[str] = {
    "kap.org.tr",
    "www.kap.org.tr",
}

NEWS_MEDIA_DOMAINS: set[str] = {
    "bloomberght.com",
    "ekonomim.com",
    "haberturk.com",
    "hurriyet.com.tr",
    "sabah.com.tr",
    "milliyet.com.tr",
    "dunya.com",
    "paraanaliz.com",
    # genişletilebilir liste
}

def classify_source_type(url: str) -> SOURCE_TYPE:
    """
    URL'den domain extract eder, SOURCE_TYPE döner.
    
    Args:
        url: Haberin tam URL'i (Google RSS'den gelen link)
    
    Returns:
        SOURCE_TYPE literal
    """

def parse_rss_item(raw_item: dict) -> NewsItem:
    """
    Mevcut parse fonksiyonu — artık source_type alanı da doldurur.
    raw_item: Google News RSS'den gelen ham dict
    """

# Veri modeli (dataclass veya TypedDict)
@dataclass
class NewsItem:
    title:       str
    url:         str
    published:   datetime
    symbol:      str
    source_type: SOURCE_TYPE        # ← YENİ ALAN
    source_domain: str              # ← YENİ ALAN (debug için)
    summary:     str | None = None
```

## Input/Output Formatları

```python
# Input (Google News RSS raw item)
raw_item = {
    "title": "THYAO: Yönetim Kurulu Kararı",
    "link":  "https://www.kap.org.tr/tr/Bildirim/1234567",
    "published": "Tue, 13 May 2026 10:00:00 +0000",
    "summary": "...",
}

# Output (NewsItem)
NewsItem(
    title        = "THYAO: Yönetim Kurulu Kararı",
    url          = "https://www.kap.org.tr/tr/Bildirim/1234567",
    published    = datetime(2026, 5, 13, 10, 0, 0),
    symbol       = "THYAO",
    source_type  = "kap_official",     # ← kap.org.tr → kap_official
    source_domain= "kap.org.tr",
    summary      = "...",
)

# Haber medyası örneği
raw_item["link"] = "https://www.bloomberght.com/thyao-kar-acikladi"
# → source_type = "news_media"

# Bilinmeyen domain
raw_item["link"] = "https://some-random-blog.com/thyao"
# → source_type = "unknown"
```

## Edge Case'ler

| Case | Beklenen Davranış |
|---|---|
| URL boş string | → `source_type = "unknown"`, exception yok |
| URL malformed (parse edilemiyor) | → `source_type = "unknown"`, WARNING log |
| KAP URL ama subdomain farklı (e.g. `api.kap.org.tr`) | → `kap_official` (domain suffix match) |
| RSS item'da `link` key yoksa | → `source_type = "unknown"`, `source_domain = ""` |
| KAP_OFFICIAL_DOMAINS ve NEWS_MEDIA_DOMAINS her ikisinde de yoksa | → `unknown` |
| URL http (non-https) KAP ise | → yine `kap_official` (schema dikkate alınmaz) |

## Downstream Etki
`analyst_agent.py` veya sinyali tüketen her modül `NewsItem.source_type` alanını okuyabilir:
```python
# Güven ağırlığı örneği (analyst tarafında, bu spec'in scope'u dışında)
weight = 1.0 if item.source_type == "kap_official" else 0.6
```
Bu spec sadece `kap_scraper.py`'ı değiştirir, downstream henüz kapsam dışı.

## Test Kriterleri

```python
# classify_source_type testleri
assert classify_source_type("https://www.kap.org.tr/tr/Bildirim/123") == "kap_official"
assert classify_source_type("https://kap.org.tr/tr/Bildirim/456")     == "kap_official"
assert classify_source_type("https://bloomberght.com/haber/thyao")    == "news_media"
assert classify_source_type("https://some-blog.com/post")             == "unknown"
assert classify_source_type("")                                        == "unknown"
assert classify_source_type("not-a-url")                              == "unknown"

# parse_rss_item entegrasyon testi
item = parse_rss_item({
    "title": "Test",
    "link": "https://www.kap.org.tr/tr/Bildirim/999",
    "published": "Tue, 13 May 2026 10:00:00 +0000",
})
assert item.source_type == "kap_official"
assert item.source_domain == "kap.org.tr"

# NewsItem field varlık testi
fields = NewsItem.__dataclass_fields__
assert "source_type" in fields
assert "source_domain" in fields
```

## Bağımlılıklar
```
urllib.parse   ← stdlib (urlparse için)
```
Yeni pip paketi gerekmez.
