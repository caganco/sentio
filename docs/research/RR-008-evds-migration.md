# RR-008 — TCMB EVDS API Migration: evds2 → evds3

**Tarih:** 22 Mayıs 2026  
**Araştıran:** Arastirma katmani  
**Durum:** ⏳ SPEC bekliyor — etkilenen dosyalar tespit edildi  
**Bağlı CB/SPEC:** — (EVDS endpoint güncelleme SPEC'i bekliyor)

---

## §1 Bulgular Özeti

`evds2.tcmb.gov.tr` HTTP 302 ile `evds3.tcmb.gov.tr`'ye yönlendirilmiştir. Eski
domaine gelen tüm istekler (API dahil) artık React/Angular SPA döndürüyor. Bu
nedenle projede `_BASE_URL` / `_EVDS_BASE` sabit URL'lerini kullanan 3 dosyada
sadece **domain değişikliği** gerekiyor — auth, query-string formatı ve tarih
formatı değişmemiştir.

| Değişen | Eski | Yeni |
|---------|------|------|
| **Base URL** | `https://evds2.tcmb.gov.tr/service/evds/` | `https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/` |
| Auth method | `key` HTTP header | **aynı** |
| Query format | `?series=X&startDate=DD-MM-YYYY&…` | **aynı** |
| Response format | `{"items": [...]}` | **aynı** |

---

## §2 Migration Tarihi

İki aşamalı değişiklik:

### Aşama 1 — 5 Nisan 2024: Auth Değişikliği
- API key URL parametresi (`?key=xxx`) → HTTP request header (`key: xxx`)
- **Proje kodu zaten header auth kullanıyor** — bu değişiklik zaten uygulanmış.

### Aşama 2 — 2024 sonrası (tam tarih belirsiz): Domain Migrasyonu
- `evds2.tcmb.gov.tr` → `evds3.tcmb.gov.tr`
- Yeni backend yolu: `/igmevdsms-dis/service/evds/` (eski: `/service/evds/`)
- Eski domain kalıcı HTTP 302 yönlendirmesi yapıyor; JSON yerine SPA HTML dönüyor.
- Python kütüphaneleri (`fatihmete/evds` v0.4, `kaymal/tcmb-py`) EVDS3 URL'ini
  hardcode olarak kullanıyor → yeni URL doğrulanmış (iki bağımsız kaynak).

SPEC.md:300'deki uyarı notu ("all /service/evds/* endpoints return HTML SPA …
Fallback YAML data active. Monitor for API stabilization") artık bu rapor ile
netleşti: API stabilize olmadı, kalıcı olarak migrate edildi.

---

## §3 Yeni Endpoint Detayları

### Base URL
```
https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/
```

### Authentication (Değişmedi)
```python
resp = requests.get(url, headers={"key": "EVDS_API_KEY"}, timeout=10)
```
Ücretsiz API key kaydı: `https://evds3.tcmb.gov.tr/` (eski evds2 kayıt formuyla aynı süreç)

### Seri İsteği URL Formatı (Değişmedi)
```
GET https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/
    ?series=<KOD>
    &startDate=DD-MM-YYYY
    &endDate=DD-MM-YYYY
    &type=json
```

Çoklu seri: `series=TP.APIFON4-TP.PY.P01` (tire ile ayrılır)  
Opsiyonel: `frequency=5` (aylık), `aggregationTypes=avg`

### Hata Durumları (Değişmedi)
- HTTP 403 → API key hatalı/eksik
- JSON yerine HTML → redirect/SPA (eski URL kullanılıyor)
- `"items": []` → seri kodu yanlış veya tarih aralığında veri yok

---

## §4 Seri Durumu

| Seri Kodu | Açıklama | Durum |
|-----------|----------|-------|
| `TP.APIFON4` | Ağırlıklı ortalama fonlama maliyeti (1-hafta repo / politika faizi) | ✅ **Aktif** — 2024+ örneklerinde birincil seri olarak kullanılıyor |
| `TP.PY.P01` | Politika (1-hafta repo) faizi | ✅ **Muhtemelen aktif** — PY prefix seriler EVDS3'te mevcut; benzer kodlar 2024/2025 tooling'de görülüyor |
| `TP.FAIZ.PYUVDL` | Geç likidite / politika koridoru | ⚠️ **Belirsiz** — kaynak kodda listeleniyor ama 2024+ örneklerinde referans yok; yeniden adlandırılmış olabilir |
| `TP.MK.IE.BSP` | Legacy kod | ❌ **Deprecated** — proje kodu "legacy, compatibility" notu ile tutmuş; aktif veri döndürmeme ihtimali yüksek |

Belirsiz seriler için doğrulama: EVDS3 portaldaki Seri Tarayıcı (`evds3.tcmb.gov.tr/tumSeriler`)
veya API key ile canlı istek atarak kontrol edilmeli.

---

## §5 tcmb.gov.tr Scraper Durumu

`src/data/tcmb_scraper.py` (D-095) fallback'i çalışıyor durumda. EVDS3'e migrate
olsa da `tcmb.gov.tr` PPK basın bültenleri URL yapısı değişmemiş:

```
https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/
    Temel+Faaliyetler/Para+Politikasi/PPK/{year}
```

Scraper şu adımları izliyor:
1. PPK listesi sayfasından yıla ait basın bülteni linklerini çekiyor
2. İlk 5 yeni bülteni deniyor
3. Regex ile 1-haftalık repo faizini metinden ayıklıyor (3 pattern, Türkçe metin)
4. Float döndürüyor (örn. 37.0) veya başarısız olursa None

Sonuç: Fallback chain'in orta katmanı (EVDS → tcmb.gov.tr → YAML) **operasyonel**
durumda. Sadece EVDS base URL düzeltilirse birincil kaynak yeniden devreye girer.

---

## §6 Etkilenen Dosyalar

Base URL değişikliği gereken 3 satır:

| Dosya | Satır | Mevcut Değer | Yeni Değer |
|-------|-------|--------------|------------|
| [src/data/evds_client.py](../../src/data/evds_client.py) | 25 | `"https://evds2.tcmb.gov.tr/service/evds/"` | `"https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/"` |
| [src/signals/local/bist_foreign_client.py](../../src/signals/local/bist_foreign_client.py) | 47 | `"https://evds2.tcmb.gov.tr/service/evds/"` | `"https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/"` |
| [src/signals/local/tcmb_client.py](../../src/signals/local/tcmb_client.py) | 115 | `"https://evds2.tcmb.gov.tr/service/evds/"` | `"https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/"` |

Dokümantasyon güncellemesi (sadece metin, logic değil):
- `src/data/evds_client.py` satır 3-4, 72 — `evds2.tcmb.gov.tr` referansları
- `SPEC.md` satır 300 — "Monitor for API stabilization" notu kaldırılabilir
- `docs/RESEARCH_REGISTRY.md` — bu RR-008 kaydı eklendi

### Etkilenmeyen Dosyalar
- `src/data/tcmb_scraper.py` — `tcmb.gov.tr` kullanıyor, EVDS bağımlılığı yok
- `src/signals/layers/connectors/bist_datastore_connector.py` — ayrı endpoint (datastore.borsaistanbul.com)
- `src/signals/local/cache_store.py` — yerelde çalışıyor, URL yok
- Tüm test dosyaları — mock/fallback YAML kullanıyor, canlı istek atmıyor

---

## §7 Örnek İstekler (Yeni URL)

### TP.APIFON4 — Politika Faizi (1 yıllık pencere)
```python
import requests

url = (
    "https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/"
    "?series=TP.APIFON4"
    "&startDate=01-01-2025"
    "&endDate=22-05-2026"
    "&type=json"
)
resp = requests.get(url, headers={"key": "YOUR_EVDS_API_KEY"}, timeout=10)
data = resp.json()  # {"items": [{"Tarih": "2025-01-03", "TP_APIFON4": "47.5"}, ...]}
```

### Çoklu Seri (TP.APIFON4 + TP.PY.P01)
```
https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/
    ?series=TP.APIFON4-TP.PY.P01
    &startDate=01-01-2025&endDate=22-05-2026&type=json
```

### TP.MKBRGN.A — Yabancı Pay Oranı (haftalık, son 6 ay)
```
https://evds3.tcmb.gov.tr/igmevdsms-dis/service/evds/
    ?series=TP.MKBRGN.A
    &startDate=01-12-2025&endDate=22-05-2026
    &type=json&frequency=5&aggregationTypes=avg
```

---

## §8 Karar & Önerilen Spec

**Minimum fix:** 3 satırda base URL değişikliği. Kod logic, auth, query format, date
format, response parse, fallback chain — hiçbiri değişmiyor.

Öneri: `D-131` olarak EVDS base URL migration speci açılmalıdır.

**Etkilenen Dosyalar (D-131 SPEC şablonu için):**
- `src/data/evds_client.py`
- `src/signals/local/bist_foreign_client.py`
- `src/signals/local/tcmb_client.py`
- `SPEC.md` (satır 300 notu güncelleme)

**Risk:** Düşük. URL değişikliği dışında hiçbir şey dokunulmuyor. Testler
YAML/mock kullanan — canlı EVDS isteği atmıyor — bu nedenle mevcut test suite
base URL değişikliğini doğrulayamaz. D-131 SPEC'i bir smoke-test (gerçek
EVDS_API_KEY ile `evds_client.py` integration testi) içermeli.

---

## Kaynaklar

- `fatihmete/evds` Python kütüphanesi v0.4 kaynak kodu — `_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"` hardcoded
- `kaymal/tcmb-py` PyPI — base_url parametresi için `evds3.tcmb.gov.tr/igmevdsms-dis/` referansı
- Python blog (urazakgul.github.io) — "TCMB/EVDS Nisan 2024 değişiklikleri" makalesi: auth header + domain migration
- Proje içi: `src/data/evds_client.py`, `tcmb_client.py`, `bist_foreign_client.py`, `tcmb_scraper.py`, `SPEC.md:300`
