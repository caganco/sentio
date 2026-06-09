# RR-Y1-011-C — KAP Endeks-Duyuru İlan-Tarihi Yapı Yoklama Raporu

| Alan | Değer |
|------|-------|
| **ID** | RR-Y1-011-C |
| **Tür** | Yalnızca yapı-yoklama (Sinyal / ölçüm YOK) |
| **Tarih** | 2026-06-09 |
| **İlişkili RR** | RR-Y1-011, RR-Y1-011-B |
| **Dayanak** | RR-Y1-011 §4 (look-ahead-safe panel fizibilite engeli F-2) |
| **Status** | ✅ F-2 kalkabilir — yapı doğrulandı, Stage-0 kararı Orchestrator+Çağan'a |

---

## 1. İki Kritik Sorunun Yanıtı

| Soru | Yanıt | Gerekçe |
|------|-------|---------|
| **(a) Makine-okunur dahil/çıkar listesi var mı?** | **EVET** | PDF ek tablo: `[sıra, ticker, ad]` × {IN / OUT / RESERVE}, per-index (§3) |
| **(b) PIT-damgalı ilan-tarihi var mı?** | **EVET** | KAP HTML saniye-hassasiyetli timestamp (§2) |
| IN/OUT açık ayrım | **EVET** | "ALINACAK PAYLAR" vs "ÇIKARILACAK PAYLAR" her tabloda sütun başlığı |
| Tier (BIST 30/50/100) bilgisi | **EVET** | Her tablo ayrı index başlığı altında (BIST 30 / BIST 50 / BIST 100 ayrı bölüm) |
| İlan→efektif gün farkı | **11–13 takvim günü** (~9–10 iş günü) | 3 bildirimdeki gözlemler (§2) |
| F-2 durumu | **KALKABİLİR** | Yeterli koşullar mevcut; scraper direktifi ayrı task (§5) |

---

## 2. Bildirim Ritmi ve Giriş Penceresi

| Bildirim ID | Yayım Tarihi | Efektif Tarih | Gap |
|------------|-------------|--------------|-----|
| 1450711 | 2025-06-20 | 2025-07-01 | **11 gün** |
| 1528220 | 2025-12-19 | 2026-01-01 | **13 gün** |
| 1574461 | 2026-03-19 | 2026-04-01 | **13 gün** |

> **Gözlem:** BIST çeyreksel değişikliklerini efektif tarihten **11–13 takvim günü**
> (~9–10 iş günü) önce yayınlıyor. Bu pencere demand-shock stratejisi için yeterlidir
> (giriş T+1 ila T+5 hedefi, pasif-sermaye yeniden dengeleme etkisini efektif tarihten
> önce yakalar).

---

## 3. KAP Bildirim Yapısı — Teknik Detay

### 3.1 HTML Sayfası (PIT Timestamp)

- **URL:** `https://www.kap.org.tr/tr/Bildirim/{disclosure_id}`
- **Timestamp formatı:** `GG.AA.YYYY SS:DD:SS` — saniye hassasiyetli, sayfada 2 adet
- **Auth:** Yok — public erişim
- **Ticker listesi (ana gövde):** Toplu virgüllü metin (yapısal-DEĞİL)
  — IN/OUT ayrımı yok, tier yok; "ilgili şirketler" meta alanı

```
Örnek — Disclosure 1574461:
  19.03.2026 14:21:51  (oluşturma)
  19.03.2026 14:37:48  (yayın — ilan tarihi olarak kullanılır)
```

### 3.2 PDF Ek Dosyaları (IN/OUT + Tier)

Her bildirimde 2 ek PDF dosyası: Türkçe (`2026_2_Donemsel_Degisiklikler.pdf`) + İngilizce.

**Ek dosya ID keşfi:**
```python
import re, requests
html = requests.get(f"https://www.kap.org.tr/tr/Bildirim/{disc_id}").text
obj_ids = re.findall(r'/tr/api/file/download/([0-9a-f]{32})', html)
# obj_ids[0] = TR PDF, obj_ids[1] = EN PDF
```

**İndirme URL'si:**
```
GET https://www.kap.org.tr/tr/api/file/download/{objId}
Content-Type: application/pdf
Content-Disposition: inline; filename*=UTF-8''...pdf
Auth: Yok — public
```

### 3.3 Java Serialization Sarmalayıcı (Kritik)

Sunucu PDF'i Java `ObjectOutputStream` byte-array içinde paketleyerek gönderir.
Ham response `\xac\xed` ile başlar (Java serialization magic). Gerçek PDF ofset 27'de başlar.

```python
def extract_pdf(raw: bytes) -> bytes:
    idx = raw.find(b'%PDF')
    return raw[idx:] if idx >= 0 else raw
```

### 3.4 PDF İçerik Yapısı

`pdfplumber.extract_tables()` her sayfada 4 tablo üretir.

```
Sayfa 1 (4 tablo):  BIST 30  |  BIST 50  |  BIST 100  |  BIST 500
Sayfa 2 (4 tablo):  BIST Likit Banka  |  BIST Banka Dışı Likit 10
                    BIST Sürdürülebilirlik  |  BIST Sürdürülebilirlik 25
```

**Her tablo 9 sütun (3 grup × 3 kolon):**

```
ALINACAK PAYLAR (IN)     ÇIKARILACAK PAYLAR (OUT)     YEDEK PAYLAR (RESERVE)
sıra | ticker | şirket   sıra | ticker | şirket         sıra | ticker | şirket
  1  | VAKBN  | ...        1  | ULKER  | ...              1  | ULKER  | ...
```

---

## 4. Örnek Veri (Q2 2026 — Disclosure 1574461)

### 4.1 BIST 30 — Tablo 1 (Sayfa 1)

| Giriş (IN) | Çıkış (OUT) | Yedek |
|-----------|------------|-------|
| VAKBN (VAKIFLAR BANKASI) | ULKER (ULKER BISKUVI) | ULKER, OYAKC, HALKB |

### 4.2 BIST 50 — Tablo 2 (Sayfa 1)

| Giriş (IN) | Çıkış (OUT) | Yedek |
|-----------|------------|-------|
| CANTE, TURSG | DOHOL, SOKM | AKSEN, FENER, ENERY |

### 4.3 BIST 100 — Tablo 3 (Sayfa 1)

| Giriş (IN) | Çıkış (OUT) | Yedek |
|-----------|------------|-------|
| CVKMD, EUREN, PAHOL, PSGYO, SARKY | EGEEN, KCAER, TSPOR, TTRAK, YEOTK | BERA, IEYHO, LINK |

**Ham pdfplumber çıktısı (Tablo 3, ilk 2 satır):**
```python
['ALINACAK PAYLAR', None, None, 'ÇIKARILACAK PAYLAR', None, None, 'YEDEK PAYLAR', None, None]
['1', 'CVKMD', 'CVK MADEN', '1', 'EGEEN', 'EGE ENDUSTRI', '1', 'BERA', 'BERA HOLDING']
```

---

## 5. Scraper Mimarisi Taslağı (Stage-0 Öncesi Referans)

### Hedef çıktı:

```
(ticker, direction, index_tier, disclosure_id, ann_date, eff_date)

Örnek:
  VAKBN, IN,  BIST30, 1574461, 2026-03-19, 2026-04-01
  ULKER, OUT, BIST30, 1574461, 2026-03-19, 2026-04-01
  CANTE, IN,  BIST50, 1574461, 2026-03-19, 2026-04-01
```

### Adım 1: Disclosure ID Keşfi (Ana Açık Nokta)

2019–2025 arası "BIST Pay Endeksleri - Dönemsel Endeks Değişiklikleri" bildirimlerinin
ID'lerini KAP'ta arama ile bul (~28 bildirim). **Bu ayrı bir direktif gerektirir.**

```python
# Olası yaklaşım — KAP bildirim arama endpoint (araştırılmadı):
# POST /tr/api/notification/query + subject/type filtresi
# VEYA: Bilinen efektif tarihlerden geriye doğru binary search
```

### Adım 2: HTML → PIT Timestamp + ObjID

```python
html = GET /tr/Bildirim/{disc_id}
ann_date = re.findall(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}', html)[-1]  # son timestamp
obj_ids = re.findall(r'/tr/api/file/download/([0-9a-f]{32})', html)
```

### Adım 3: PDF İndir + Sarmalayıcı Çöz

```python
raw = GET /tr/api/file/download/{obj_ids[0]}
pdf = raw[raw.find(b'%PDF'):]
```

### Adım 4: Tablo Parse

```python
with pdfplumber.open(io.BytesIO(pdf)) as f:
    for page in f.pages:
        for table in page.extract_tables():
            # 9-sütun: [sıra,ticker,ad] × 3 (IN|OUT|RESERVE)
            # Hangi index: sayfadaki tablo sırası (0=BIST30, 1=BIST50, 2=BIST100, 3=BIST500)
```

---

## 6. Açık Noktalar (Stage-0 Öncesi)

| # | Soru | Durum |
|---|------|-------|
| **O-1** | 2019–2025 disclosure ID'lerinin tamamı | ⏳ KAP arama direktifi gerekiyor |
| **O-2** | Eski PDF formatı (2019–2022) aynı mı? | ⏳ Test edilmedi (yalnız Q3-2025/Q1-Q2-2026 doğrulandı) |
| **O-3** | Scraper auth gerekiyor mu? | ✅ HAYIR — 3 bildirim × 2 PDF public doğrulandı |
| **O-4** | pdfplumber tablo hizalama tutarlı mı? | ✅ EVET — 6 PDF tutarlı (3 bildirim × TR+EN) |

---

## 7. Genel Hüküm

```
F-1 (archive boş)        : ÇÖZÜLDÜ (RR-Y1-011-B)
F-2 (ilan-tarihi)        : KALKABİLİR — KAP public PDF + pdfplumber ile çözüldü
F-3 (planlı filtresi)    : ÇÖZÜLDÜ (RR-Y1-011-B)
F-4 (acil ayrımı)        : ÇÖZÜLDÜ (RR-Y1-011-B)
```

> **F-2 için kalan iş:**
> 1. KAP'ta 2019–2025 "Dönemsel Endeks Değişiklikleri" bildirim ID'lerini derle (~28 adet)
> 2. Her bildirim için PDF indir + tablo parse → `(ticker, direction, tier, ann_date, eff_date)` paneli
> 3. clean_universe PIT bayraklarıyla join → look-ahead-safe olay paneli

**Stage-0 kararı:** F-2 teknik çözümü bu raporda kanıtlandı (3 bildirim × 2 PDF doğrulandı).
Efor: orta (~1-2 saatlik scraper + ID keşfi). Stage-0 açılıp açılmaması
Orchestrator + Çağan kararıdır.

---

## 8. Kapsam-Uyum Beyanı

Bu raporda sinyal / getiri / IC / NW-t / Sharpe / edge hükmü /
panel kurma / Stage-0 parametresi / eşik üretilmemiştir.

Committed pipeline dokunulmamıştır.

Scratch artefaktlar (gitignored):
- `scripts/scratch/probe_kap_index_disclosures.py` (ana probe script, güncellendi)
- `scripts/scratch/_kap_att_probe.py`, `_kap_att2.py`, `_kap_pdf_extract.py`, `_kap_full_parse.py` (geçici keşif)
- `data/bist_datastore_archive/kap_index_probe/` (gitignored — indirilen PDF'ler)
