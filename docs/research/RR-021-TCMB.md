# RR-021 — TCMB EVDS3 API Operasyonel Referans

**Sistem:** Sentio Trading System · **Snapshot:** Mayıs 2026 · **Önceki:** RR-009 (seri kod mapping), D-135/D-136 (evds2 → evds3 migration)

---

## 1. TL;DR

- **EVDS3 endpoint çalışıyor.** Base URL `https://evds3.tcmb.gov.tr/igmevdsms-dis/`. Eski `evds2.tcmb.gov.tr/service/evds/` tamamen kapalı; community raporuna göre 302 → SPA HTML dönüyor (kaynak: saidsurucu/borsapy README — *"eski evds2.tcmb.gov.tr/service/evds/?key=... URL'leri tamamen kapandı (302 → SPA HTML). PyPI'daki eski evds/evdsAPI paketleri kırıldı"*).
- **Aktif seriler (D-136 sonrası):** Politika faizi (TP.APIFON4), TLREF (TP.BISTTLREF.*), USD/EUR alış-satış (TP.DK.USD.A/S, TP.DK.EUR.A), TÜFE (TP.FE.OKTG01 veya TP.FG.J0), Yİ-ÜFE (TP.FG01 türevleri), BIST net işlemler (TP.MKNETHAR.*). Hepsi için "son canlı veri tarihi: **arastirma katmani API key ile teyit etmeli**".
- **Kritik uyarı — Auth header çatışması:** Brief'te `x-auth-token` header'ı geçiyor (D-136 fix). Ancak tüm güncel community wrapper'ları (borsapy, kaymal/tcmb, fatihmete/evds v0.4, lobehub skill) `key` header'ı kullanıyor — 05.04.2024 TCMB değişikliği sonrası kural. **arastirma katmani ilk testte her iki header'ı denemeli.**
- **Resmi rate limit BULUNAMADI.** Community: çağrı başına maks **1000 gözlem** + **400 seri**; bu limit aşılırsa TCMB sessizce keser (borsapy README: *"TCMB doğrudan çağrılırsa son 1000 gözlemi sessizce kesip getirir"*). EVDS3 hâlâ **beta** — 26 Ocak 2026 lansman (TCMB Basın Duyurusu, AA muhabiri Mahmut Çil 26.01.2026 haberi: *"Ocak 2026 itibarıyla ise EVDS, teknik altyapı, içerik ve tasarım olarak tekrar yenilenerek EVDS 3 beta sürüm olarak devreye alınmıştır"*).
- **30 dakikada başlatma:** (1) evds3.tcmb.gov.tr'den hesap + API key, (2) curl ping, (3) USD seri testi, (4) hata ayıklama. Detay §8.

---

## 2. Endpoint Haritası

### 2.1 Base URL ve Path Yapısı

```
https://evds3.tcmb.gov.tr/igmevdsms-dis/{ACTION}/{PARAMS}
```

**CRITICAL:** EVDS3'te `/service/evds/` segmenti kaldırıldı. Parametreler **path-segment formunda** (`a=b&c=d`) verilmeli — gerçek HTTP query-string değil. `requests.get(url, params={...})` ile gönderilirse 404 döner (kaynak: lobehub EVDS-Analiz skill: *"Query string ile parametre geçme ÇALIŞMAZ → 404 verir"*).

### 2.2 Endpoint Tablosu

| Endpoint | Amaç | Tipik Path |
|---|---|---|
| `/series=…` | Zaman serisi verisi (tek/çoklu) | `/igmevdsms-dis/series=TP.DK.USD.A&startDate=01-01-2024&endDate=31-12-2024&type=json` |
| `/categories` | Ana konu başlıkları | `/igmevdsms-dis/categories/type=json` |
| `/datagroups` | Veri grupları metadata | `/igmevdsms-dis/datagroups/mode=0&type=json` (tümü) veya `mode=1&code=bie_yssk&type=json` (tek) |
| `/serieList` | Bir veri grubundaki seriler / tek seri metadata | `/igmevdsms-dis/serieList/type=json&code=bie_tukfiy4` veya `…&code=TP.DK.USD.A` |

### 2.3 Parametre Listesi

| Parametre | Format | Zorunlu | Not |
|---|---|---|---|
| `series` | `TP.DK.USD.A` veya `KOD1-KOD2-KOD3` (tire ayrımlı) | Evet (series endpoint'inde) | Maksimum ~400 seri/çağrı (community) |
| `startDate` | **DD-MM-YYYY** | Evet | YYYY-MM-DD REDDEDİLİR — 400 Bad Request |
| `endDate` | **DD-MM-YYYY** | Evet | Aynı kural |
| `type` | `json` / `xml` / `csv` | Hayır (default xml) | Sentio'da `json` |
| `frequency` | 1=Günlük, 2=İşgünü, 3=Haftalık, 4=Ayda 2, 5=Aylık, 6=3 Aylık, 7=6 Aylık, 8=Yıllık | Hayır | Serinin orijinal frekansından düşük olamaz |
| `aggregationTypes` | `avg`, `min`, `max`, `first`, `last`, `sum` | Hayır | Çoklu seride tire ayrımlı |
| `formulas` | 0=Düzey, 1=% değişim, 2=Fark, 3=Yıllık %, 4=Yıllık fark, 5=YTD %, 6=YTD fark, 7=Har. ort., 8=Har. toplam | Hayır | Formül uygulanırsa orijinal None döner; ham veri için ayrı çağrı |
| `decimalSeperator` | `.` (default) / `,` | Hayır | — |

### 2.4 Auth Header — DİKKAT

| Kaynak | Header Adı |
|---|---|
| Brief / D-136 fix notu | `x-auth-token` |
| EVDS2 (05.04.2024 sonrası, urazakgul blog) | `key` |
| borsapy v3 (EVDS3 wrapper) | `key` |
| kaymal/tcmb-py v0.5.0 (PyPI: yayım tarihi 20 Şubat 2026) | `key` (default) |
| fatihmete/evds v0.4 (EVDS3 uyum changelog'lu, PyPI'da yayım tarihi CAPTCHA nedeniyle teyit edilemedi) | `key` |
| TCMB Kullanım Şartları (docId=18) | Header adı spesifiye edilmemiş |

**Karar:** arastirma katmani ilk test çağrısında `key` header'ını dene; 401 dönerse `x-auth-token` ile tekrarla. Mevcut Sentio kodu D-136 sonrası çalışıyorsa header'ı doğrula — muhtemelen `key` ile geçildi ve brief notu güncel değil.

### 2.5 Request Örnekleri

**curl:**
```bash
curl -H "key: $EVDS_API_KEY" \
  "https://evds3.tcmb.gov.tr/igmevdsms-dis/series=TP.DK.USD.A&startDate=01-05-2026&endDate=23-05-2026&type=json"
```

**Python (requests):**
```python
import os, requests
url = ("https://evds3.tcmb.gov.tr/igmevdsms-dis/"
       "series=TP.DK.USD.A&startDate=01-05-2026&endDate=23-05-2026&type=json")
r = requests.get(url, headers={"key": os.environ["EVDS_API_KEY"]}, timeout=15)
r.raise_for_status()
data = r.json()["items"]
```

### 2.6 Response Örneği

```json
{
  "totalCount": 16,
  "items": [
    {"Tarih": "02-05-2026", "TP_DK_USD_A": "32.4810", "UNIXTIME": {"_attributes": {"value": "..."}}},
    {"Tarih": "03-05-2026", "TP_DK_USD_A": null},
    {"Tarih": "04-05-2026", "TP_DK_USD_A": "32.5102"}
  ]
}
```

**Önemli:** Seri kodu nokta (`.`) yerine alt çizgi (`_`) ile döner (`TP_DK_USD_A`). Hafta sonu / tatil günlerinde `null` döner — D-135'te ele alınmış olması beklenen known issue.

### 2.7 Sektör Pratiği (minimal)

Türk quant community'sinde EVDS, Python tarafında üç paket etrafında konsolide olmuş durumda: `fatihmete/evds` (klasik, EVDS3 uyumu v0.4 ile geldi), `kaymal/tcmb-py` (modern, datagroup-aware), ve `saidsurucu/borsapy` (geniş finans suite içine gömülü EVDS provider). Bunlar resmi TCMB ürünü değil; hepsi MIT/Apache lisansla "kişisel kullanım" disclaim'i taşır. Pratikte tek satır seri çekme (`evds.get_data([...])` veya `tcmb.read(...)`) standart hâline gelmiş; üretim kodlarında çoğunlukla wrapper'ın altındaki `requests` çağrısı doğrudan kullanılıyor (bağımlılık azaltmak ve EVDS3 migration kırılganlığından kaçınmak için — Sentio yaklaşımıyla aynı).

---

## 3. Aktif Seri Envanteri

> Her seri için "Son canlı veri tarihi: **arastirma katmani API key ile teyit etmeli**" notu zorunlu. Lag tahminleri community kaynaklı (TCMB resmi SLA yok).

> **Canlı Doğrulama:** Bu envanter `scripts/test_evds3_connection.py` 
> ile 25-05-2026 tarihinde API'ye karşı test edildi.  
> Sonuçlar: `docs/research/RR-021-live-test-results.md`  
> **Özet:** 14/16 aktif, 2 dead (TP.FAIZ.PYUVDL, TP.FG01)

### 3.1 Politika Faizi & Para Piyasası

| Seri Kodu | Açıklama | Frekans | Lag | Durum | Son Canlı Veri |
|---|---|---|---|---|---|
| `TP.APIFON4` | TCMB Ağırlıklı Ortalama Fonlama Maliyeti (AOFM) | Günlük | 0–1 gün | ✅ | arastirma katmani API key ile teyit etmeli |
| `TP.API.REP.ORT.G1` | Repo ortalama oranı (gecelik) | Günlük | 0–1 gün | ⚠️ arastirma katmani ile aktiflik teyit edilmeli | arastirma katmani API key ile teyit etmeli |
| `TP.BISTTLREF.ORAN` / `TP.BISTTLREF.KAPANIS` | TLREF (Türk Lirası Gecelik Referans Faiz) | Günlük | 0–1 gün | ✅ (community'de `KAPANIS` variant) | arastirma katmani API key ile teyit etmeli |
| `TP.FAIZ.PYUVDL` | Eski TLREF kodu | — | — | ❌ DEAD (HTTP 400, doğrulandı)

### 3.2 Döviz Kurları

| Seri Kodu | Açıklama | Frekans | Lag | Durum | Son Canlı Veri |
|---|---|---|---|---|---|
| `TP.DK.USD.A` | USD/TRY Alış (Gösterge) | Günlük (işgünü) | 0–1 gün | ✅ | arastirma katmani API key ile teyit etmeli |
| `TP.DK.USD.S` | USD/TRY Satış | Günlük | 0–1 gün | ✅ | arastirma katmani API key ile teyit etmeli |
| `TP.DK.EUR.A` | EUR/TRY Alış | Günlük | 0–1 gün | ✅ | arastirma katmani API key ile teyit etmeli |
| `TP.DK.EUR.S` | EUR/TRY Satış | Günlük | 0–1 gün | ✅ | arastirma katmani API key ile teyit etmeli |
| `TP.DK.USD.A.YTL` | USD alış — eski .YTL suffix variant | Günlük | 0–1 gün | ⚠️ Community'de hâlâ kullanımda | arastirma katmani API key ile teyit etmeli |

### 3.3 Enflasyon

| Seri Kodu | Açıklama | Frekans | Lag | Durum | Son Canlı Veri |
|---|---|---|---|---|---|
| `TP.FE.OKTG01` | TÜFE Genel (2003=100, TÜİK Yeni Seri) | Aylık | ~3 gün (her ayın 3'ünde TÜİK yayını) | ⚠️ STALE (son veri 2025-9, ~8 ay eski)
| `TP.FG.J0` | TÜFE alternatif kodu (borsapy/evdspy örneklerinde) | Aylık | ~3 gün | ⚠️ Tek koda sabitle — `OKTG01` daha yaygın | arastirma katmani API key ile teyit etmeli |
| `TP.FG01` | Yİ-ÜFE | Aylık | ~3 gün | ❌ DEAD (HTTP 400, beklenmedik)
| `TP.ENFBEK.PKA12ENF` | 12-ay ileri enflasyon beklentisi (piyasa katılımcıları) | Aylık | ~10 gün | Nice-to-have | arastirma katmani API key ile teyit etmeli |

### 3.4 Borsa / Yatırımcı Davranışı

| Seri Kodu | Açıklama | Frekans | Lag | Durum | Son Canlı Veri |
|---|---|---|---|---|---|
| `TP.MKNETHAR.M7` | BIST net işlem (genel) — Veri grubu `bie_mknethar` | Haftalık | ~3–5 gün | ⚠️ Tam tanım için datagroups çağrısı ile doğrula | arastirma katmani API key ile teyit etmeli |
| `TP.MKNETHAR.M1` | Yabancı net işlem | Haftalık | ~3–5 gün | ⚠️ Aynı | arastirma katmani API key ile teyit etmeli |

### 3.5 Reel Sektör (Bekleyen Kontrol)

| Seri / Grup | Durum | Not |
|---|---|---|
| Sanayi Üretim Endeksi | EVDS'te mevcut (TÜİK kaynaklı, "Sanayi Üretim Endeksi" kategorisi) | Aylık, ~45–60 gün lag |
| İşsizlik Oranı | EVDS'te mevcut (TÜİK işgücü istatistikleri) | Aylık, ~45–60 gün lag |
| Brent / WTI ham petrol | EVDS'te DOĞRUDAN seri kodu BULUNAMADI; borsapy bunu TradingView/`TVC:UKOIL` üzerinden ayrı çekiyor | yfinance `BZ=F` / `CL=F`'e yönlendir |
| Altın TL (gram) | EVDS'te tarihsel "Altın Borsası İşlemleri" grubu var (`bie_mkbral` — Arşiv); günlük gram fiyat için EVDS pratik değil | Alternatif: borsapy `bp.FX("gram-altin")` |

---

## 4. Auth ve Güvenlik

### 4.1 API Key Alma — 5 Adım

1. `https://evds3.tcmb.gov.tr/login` → "Kayıt Ol" (ücretsiz, e-posta + parola).
2. E-postaya gelen "TCMB EVDS Aktivasyon Kodu" ile hesabı onayla.
3. Giriş yap, sağ üst köşeden kullanıcı adına tıkla → "Profilim".
4. Profil sayfasının altında CAPTCHA güvenlik kodunu yaz.
5. "API KEY KOPYALA" butonuna bas → key panoya kopyalanır (örn. `Ab1Cd2Ef3Gh4`).

Geçerlilik süresi resmi olarak BULUNAMADI; community'de "süresiz" varsayımı var. Hesap dondurulursa key invalid olur.

### 4.2 Header Format

```
key: <API_KEY>
```

Brief'teki `x-auth-token` ile community'deki `key` çatışması için §2.4'e bakın. **arastirma katmani ilk testte 401 dönerse header adını değiştirip tekrar dene.**

### 4.3 Rate Limit

| Sınır | Değer | Kaynak |
|---|---|---|
| Günlük istek limiti | **BULUNAMADI** (resmi rate limit duyurulmamış) | TCMB Kullanım Şartları docId=18 sınır içermiyor |
| Dakika başı | **BULUNAMADI** | — |
| Çağrı başına maks gözlem | ~1000 (aşılırsa sessizce kesilir) | borsapy README — community-doğrulamalı |
| Çağrı başına maks seri | ~400 (MAX_SERIES_PER_CALL) | borsapy README |
| HTTP 429 davranışı | Community'de raporlanmamış | — |
| Performans tavsiyesi | "günde bir kez veri toplama" | TCMB EVDS Web Service Usage Guide (Jan 2022) |

**Pratik öneri:** Sentio `daily_update.py`'da seri başına ayrı çağrı yerine **gruplu çağrı** (tire-ayrımlı çoklu seri, aynı tarih aralığı). 5 dakika içinde 200+ çağrı atmaktan kaçın.

### 4.4 IP Kısıtlaması

Resmi IP whitelisting/blacklisting mekanizması dokümante edilmemiş (BULUNAMADI). Cloud çalıştırma (GitHub Actions, AWS Lambda) sorun raporlanmamış.

### 4.5 Key Güvenliği

| Pratik | Uygulama |
|---|---|
| `.env` dosyası | `EVDS_API_KEY=...` — repo kökünde, gitignore'da |
| `.gitignore` | `.env`, `*.env.local` |
| GitHub Actions | Repo Settings → Secrets → `EVDS_API_KEY` |
| Rotasyon | Yılda 1 — TCMB profilinden "API Key Kopyala" yeniden bas (eskisi invalidate edilir) |
| Loglama | Key'i loglara YAZMA — `requests` debug modunda header maskelenmelidir |

---

## 5. Error Handling Referansı

### 5.1 Error Kodu Tablosu

| HTTP | Sebep | Sentio Response |
|---|---|---|
| 200 + `items: []` | Geçerli istek, ama seri için bu tarih aralığında veri yok / deprecated kod | WARN log + cached değere düş; seri kodu RR-009'a karşı kontrol |
| 200 + parsable | Normal | Devam |
| 400 Bad Request | En sık: `startDate` formatı YYYY-MM-DD verilmiş (DD-MM-YYYY zorunlu); ikincil: bilinmeyen parametre | Tarih formatını kontrol — `strftime("%d-%m-%Y")` |
| 401 Unauthorized | Header adı yanlış (`key` vs `x-auth-token`) veya API key invalid / dondurulmuş | Header'ı değiştirip retry; key'i regenerate |
| 403 Forbidden | URL'de `key=...` query-string olarak gönderilmiş (eski stil) | Header'a taşı |
| 404 Not Found | Endpoint path'i yanlış (örn. `requests.params={}` ile gönderim); seri kodu hiç yok | Path string'i doğrula; seri kodunu `/serieList` ile sorgula |
| 429 Too Many Requests | Community'de raporlanmamış ama olası | Exponential backoff (1s, 2s, 4s, 8s) |
| 500 / 502 / 503 / 504 | TCMB tarafı geçici | Retry 3x (jitter), sonra fail + cached değere düş |

### 5.2 Sessiz Başarısız Senaryolar

| Senaryo | Tespit | Aksiyon |
|---|---|---|
| Geçerli response, boş `items` | `len(items) == 0` ve tarih aralığı son 30 günü kapsıyorsa | Stale alert |
| Stale data (frekans gecikmesi) | Son veri tarihi > beklenen lag + 7 gün | WARN; alternatif kaynak araştır |
| JSON parse hatası | `response.text` HTML / SPA HTML döndü | Migration sinyali — EVDS4 ihtimali; §7 |
| Partial data (çoklu seri) | Bazı seriler dolu, bazıları null kolon | Seri kodlarını ayrı ayrı dene; biri deprecated olabilir |
| Hafta sonu `null` | USD/EUR günlük serilerinde Cmt/Paz | Beklenen — forward-fill veya skip |
| 1000+ gözlem isteği | TCMB sessizce son 1000'i keser, fail-silent | Chunk'la veya çağrı başına tarih aralığını kısalt |

### 5.3 Retry Mantığı (Kavramsal)

```python
def evds_get_with_retry(url: str, headers: dict, max_retries: int = 3) -> dict:
    """EVDS3 GET + retry. Production-ready DEĞİL.
    
    4xx hataları: tek seferde fail (parametre hatası, retry işe yaramaz)
    5xx hataları: exponential backoff (1s, 2s, 4s) + jitter
    429: backoff + Retry-After header'ı varsa onu kullan
    Connection error / timeout: 5xx gibi davran
    """
    ...
```

---

## 6. Fallback Stratejisi

### 6.1 EVDS3 Down Senaryosu

| Süre | Davranış |
|---|---|
| 0–24 saat | Cached son değer kullan; OS_STATE `evds_stale=false` |
| 24–48 saat | WARN log; daily_update.py partial fail; OS_STATE `evds_stale=true` |
| > 48 saat | ALERT (Slack/email); manual intervention; L2 Macro üretmeyi durdur veya yalnızca güvenilir cache ile çalıştır |

### 6.2 Alternatif Veri Kaynakları

| Veri | Birincil (EVDS3) | Yedek 1 | Yedek 2 (son çare) |
|---|---|---|---|
| USD/TRY | TP.DK.USD.A | Yahoo Finance `USDTRY=X` (yfinance) | canlidoviz.com (borsapy `bp.FX("USD")`) |
| EUR/TRY | TP.DK.EUR.A | yfinance `EURTRY=X` | canlidoviz.com |
| Politika faizi | TP.APIFON4 | borsapy `bp.TCMB().policy_rate` (TCMB web scrape) | TCMB karar duyurusu manuel |
| TÜFE / Yİ-ÜFE | TP.FE.OKTG01 | TÜİK data.tuik.gov.tr CSV | borsapy `bp.Inflation()` |
| Brent / WTI | (EVDS'de yok) | yfinance `BZ=F` / `CL=F` | borsapy `bp.FX("BRENT")` (TradingView) |
| Türkiye makro genel | EVDS3 | FRED (St. Louis Fed — sınırlı TR serisi) | World Bank Open Data API |

### 6.3 Graceful Degradation

| Seri Sınıfı | EVDS Olmadan L2 Macro Çalışır mı? |
|---|---|
| **Kritik** (USD/TRY, politika faizi, TÜFE) | Hayır — yfinance/scrape fallback ile çalışmalı |
| **Önemli** (TLREF, EUR/TRY, Yİ-ÜFE) | Sınırlı — cached değer + STALE flag |
| **Nice-to-have** (BIST net işlem, enflasyon beklentisi, sanayi üretim) | Evet — yokluk hata değil, feature flag ile devre dışı bırak |

---

## 7. Migration Riski (EVDS4?)

### 7.1 TCMB Migration Pattern

| Geçiş | Ne Zaman | Süre |
|---|---|---|
| EVDS1 → EVDS2 | 2017 yenileme (TCMB DUY2026-03 teyidi: *"2017 yılındaki güncelleme ile sistemin altyapısı geliştirilmiş ve tasarımı yenilenmişti"*) | Çift platform dönemi vardı |
| EVDS2 → EVDS3 | 26 Ocak 2026 (TCMB Basın Duyurusu DUY2026-03, AA muhabiri Mahmut Çil) | TCMB DUY2026-03 yalnızca *"EVDS 3 beta sürümü ile birlikte EVDS 2 de erişime açık olacaktır"* diyor; kesin kapanış tarihi resmi belgede yer almıyor — eksisözlük'teki "20 Şubat" iddiası bağımsız kaynaklarca doğrulanamadı |
| EVDS3 → EVDS4 | Belirsiz — TCMB DUY2026-03 EVDS3'ü açıkça "beta sürüm" olarak nitelendiriyor; EVDS4 için Mayıs 2026 itibarıyla resmi duyuru/tarih mevcut değil | — |

### 7.2 Erken Uyarı Sinyalleri

| Sinyal | İzleme Yeri |
|---|---|
| TCMB resmi duyuru | `https://evds3.tcmb.gov.tr/duyurular` |
| TCMB Twitter | `@Merkez_Bankasi` (resmi hesap) |
| Anadolu Ajansı / büyük basın | "EVDS yenileme" araması |
| HTTP response değişimi | Response body'sinde HTML SPA gelmesi (JSON yerine) → büyük sinyal |
| 5xx artışı | Birden bire son 24 saatte > %20 fail oranı |
| API key invalidation toplu duyuru | TCMB e-postası (`yenievds@tcmb.gov.tr` benzeri — 05.04.2024 değişikliğinde bu adres kullanıldı) |

### 7.3 Migration Checklist (Gelecek için)

```python
def daily_evds_health_check() -> dict:
    """Günlük EVDS3 sağlık kontrolü. KAVRAMSAL — production-ready DEĞİL.
    
    1. Base URL'e HEAD request → 200/302 kontrolü
    2. Aktif seri listesinden örnek seri (TP.DK.USD.A) çek → son 7 gün
    3. Response Content-Type 'application/json' mi?
    4. items[0]['Tarih'] son 3 işgünü içinde mi?
    5. Yeni domain (örn. evds4.tcmb.gov.tr) erişilebilir mi? (HEAD)
    
    Return: {healthy: bool, last_data_date: str, migration_signal: bool}
    """
    ...
```

Daily check öneri: `daily_update.py` başında 30 saniyelik smoke test. Migration sinyali alınırsa Slack alert.

---

## 8. 30 Dakikada EVDS (Yeni arastirma katmani)

### 8.1 4 Adım × 5 Dakika

| Adım | Süre | Çıktı |
|---|---|---|
| **1. API key alma** | 5 dk | EVDS3 hesabı + API key (§4.1) |
| **2. İlk istek** | 5 dk | curl ile USD/TRY son 7 gün — terminal'de JSON gör |
| **3. Aktif seri kontrolü** | 5 dk | §3'teki tüm seriler için `/serieList` ile doğrulama; deprecated olan var mı? |
| **4. Hata ayıklama** | 15 dk | Bilinen 5 hatayı tetikle ve nasıl çözüldüğünü gör (§8.2) |

### 8.2 Sık Yapılan 5 Hata

1. **Yanlış tarih formatı.** YYYY-MM-DD reddedilir → 400. Daima `strftime("%d-%m-%Y")` kullan.
2. **Series parametresinde virgül/boşluk.** Çoklu seri için `TP.DK.USD.A-TP.DK.EUR.A` (tire). Virgül 400 verir.
3. **Header adı karışıklığı.** `key` mi `x-auth-token` mı (§2.4)? 401 alınca header'ı değiştir.
4. **Eski base URL.** `evds2.tcmb.gov.tr/service/evds/` artık 302 → HTML. `evds3.tcmb.gov.tr/igmevdsms-dis/` kullan.
5. **`requests.get(url, params={…})` ile parametre gönderme.** EVDS3 query-string kabul etmiyor; URL string'i elle birleştir veya `urlencode` ile path'e gömül.

### 8.3 Test Script (Kavramsal Python)

```python
def test_evds3_connection(api_key: str) -> dict:
    """EVDS3 bağlantı + aktif seri doğrulama testi.
    Production-ready DEĞİL; signature + docstring + comment.
    
    Args:
        api_key: TCMB EVDS3 profil sayfasından alınan API anahtarı
    
    Returns:
        {
            'connection': bool,                  # base URL erişilebilir mi
            'auth_header': str,                  # 'key' | 'x-auth-token' (hangisi çalıştı)
            'active_series': dict[str, bool],    # seri_kodu → veri döndü mü
            'last_data_date': dict[str, str],    # seri_kodu → son tarih
            'errors': list[str]
        }
    """
    # 1. Base URL ping: GET /igmevdsms-dis/categories/type=json (key gerektirebilir)
    # 2. Auth header tespiti: önce 'key' ile dene, 401 ise 'x-auth-token'
    # 3. Her aktif seri (TP.APIFON4, TP.DK.USD.A, TP.FE.OKTG01, ...) için son 30 gün GET
    # 4. Response'ta items array boş mu kontrol → boşsa 'deprecated' işaretle
    # 5. items[-1]['Tarih']'i parse edip last_data_date'e yaz
    # 6. Hata varsa errors listesine ekle, devam et (fail-fast değil)
    ...
```

---

## 9. Kısıtlar & Caveat'lar

- **Snapshot Mayıs 2026.** EVDS3 hâlâ **beta** — TCMB Basın Duyurusu DUY2026-03 (26.01.2026) açıkça "EVDS 3 beta sürüm" diyor. EVDS2 paralel açık; kesin kapanış tarihi resmi belgede yok.
- **TCMB resmi Swagger/OpenAPI spec'i BULUNAMADI.** `https://evds3.tcmb.gov.tr/dokumanlar` SPA olarak yükleniyor; ham scraping çalışmıyor. Tüm endpoint bilgileri community wrapper'lardan tersine mühendislik (borsapy README, kaymal/tcmb-py v0.5.0 — 20 Şubat 2026 PyPI yayını, fatihmete/evds v0.4).
- **Auth header çelişkisi.** Brief `x-auth-token` diyor, community `key` diyor. Mevcut Sentio kodu çalışıyorsa header'ı kontrol et — muhtemelen kod yorumu güncel değil. İlk arastirma katmani testi her iki header'ı denemeli.
- **Rate limit resmi BULUNAMADI.** Çağrı başına ~1000 gözlem + ~400 seri community-sourced (borsapy: *"Max gözlem/çağrı: 1000 — TCMB doğrudan çağrılırsa son 1000 gözlemi sessizce kesip getirir"*). 429 davranışı raporlanmamış.
- **Lag tahminleri ampirik değil.** Tablolardaki "0–1 gün", "~3 gün", "~45–60 gün" değerleri community kullanım gözleminden; TCMB resmi SLA yok.
- **Son canlı veri tarihleri.** Her seri için "arastirma katmani API key ile teyit etmeli" notu — bu raporu yazan ajan API key'e erişmediği için canlı doğrulama yapamadı. İlk arastirma katmani seansında §8.3 test script ile envantere geç.
- **API key her arastirma katmani için ayrı alınmalı.** TCMB Kullanım Şartları docId=18 paylaşımı yasaklamıyor ama loglanabilir/denetlenebilir: *"Kullanıcılar, uygulama üzerinde gerçekleştirdikleri işlemlerin kaydedilebileceğini, kendilerine ait bilgilere erişilebileceğini ve gerektiğinde yetkili makamlara iletilebileceğini göz önünde bulundurmalıdırlar."*
- **EVDS4 timing belirsiz.** EVDS3 beta sürecinde olduğu için "stabil" sayılamaz; daily health check (§7.3) öneriliyor.
- **Brent/WTI/altın EVDS'de yok veya zor.** Bu emtiaları yfinance veya canlidoviz/TradingView üzerinden ayrı kaynaklardan çek.

---

**Kaynaklar (referans listesi — okuma değil teyit için):**
- `https://evds3.tcmb.gov.tr/` (TCMB resmi, 26 Ocak 2026 lansman)
- `https://evds3.tcmb.gov.tr/igmevdsms-dis/documents/showDocument?docId=18` (EVDS Kullanım Şartları)
- `https://github.com/saidsurucu/borsapy` (EVDS3 wrapper, açık endpoint dokümantasyonu)
- `https://github.com/kaymal/tcmb-py` (v0.5.0, PyPI yayın 20 Şubat 2026)
- `https://github.com/fatihmete/evds` (v0.4, EVDS3 uyum changelog'lu)
- `https://urazakgul.github.io/python-blog/posts/post_9/` (05.04.2024 key→header değişikliği)
- `https://www.aa.com.tr/tr/ekonomi/tcmb-elektronik-veri-dagitim-sistemini-yeniledi/3810927` (EVDS3 lansman duyurusu, AA muhabiri Mahmut Çil 26.01.2026)
- `https://www.alomaliye.com/2026/01/26/tcmb-elektronik-veri-dagitim-sisteminin-yenilenmesine-iliskin-basin-duyurusu/` (TCMB Basın Duyurusu tam metni)