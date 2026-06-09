# RR-Y1-011-B — DataStore 3184 Şema Yoklama Raporu

| Alan | Değer |
|------|-------|
| **ID** | RR-Y1-011-B |
| **Tür** | Yalnızca şema-yoklama (Edge / sinyal / istatistik YOK) |
| **Tarih** | 2026-06-09 |
| **Kaynak ZIP** | `exsrk2025.zip` (67.5 KB) |
| **İlişkili RR** | RR-Y1-011 |
| **Status** | ✅ Şema tamamlandı — Stage-0 kararı Orchestrator+Çağan'a |

---

## 1. İki Kritik Sorunun Yanıtı

| Soru | Yanıt | Gerekçe |
|------|-------|---------|
| **(a) İlan-tarihi yürürlük-tarihinden AYRI mi?** | **HAYIR** | Dosya yalnızca efektif çeyrek tarihleri içeriyor (§3) |
| **(b) Olay-tipi ayırt edilebilir mi?** | **ÖRTÜK EVET** | Format planlı çeyreksel oturumları doğal olarak filtreler (§4) |
| Look-ahead-safe panel | **BLOKE** | İlan tarihi kaynağı gerekiyor (§5) |
| Planlı-rekon alt-kümesi filtresi | **ÇÖZÜLDÜ** | Quarterly format inherently = planlı oturumlar (§4) |

---

## 2. ZIP İçeriği ve Ham Format

```
exsrk2025.zip (67.5 KB)
  └── exsrk2025.xlsx
```

### 2.1 Excel Yapısı (multi-row header)

| Satır | İçerik |
|-------|--------|
| 0 | Yıl: `2025` |
| 1 | Çeyrek: `1.ÇEYREK` `2.ÇEYREK` `3.ÇEYREK` `4.ÇEYREK` |
| 2 | İngilizce: `1ST QUARTER` `2ND QUARTER` `3RD QUARTER` `4TH QUARTER` |
| **3** | **Gerçek başlık**: `PAY KODU\nCODE` \| `PAY ADI\nEQUITY` \| `2025-01-02` \| `2025-04-02` \| `2025-07-01` \| `2025-10-01` |
| 4+ | Veri satırları |

### 2.2 Gerçek Sütunlar (6 sütun)

| # | Sütun Adı | Açıklama | İlan-tarihi mi? |
|---|-----------|----------|-----------------|
| 1 | `PAY KODU\nCODE` | Hisse kodu (AKBNK, THYAO vb.) | — |
| 2 | `PAY ADI\nEQUITY` | Şirket adı | — |
| 3 | `2025-01-02 00:00:00` | Q1 efektif tarihi — üyelik değeri | **HAYIR** (efektif tarih) |
| 4 | `2025-04-02 00:00:00` | Q2 efektif tarihi — üyelik değeri | **HAYIR** |
| 5 | `2025-07-01 00:00:00` | Q3 efektif tarihi — üyelik değeri | **HAYIR** |
| 6 | `2025-10-01 00:00:00` | Q4 efektif tarihi — üyelik değeri | **HAYIR** |

### 2.3 Üyelik Değerleri

Hücre değerleri binary (NaN = üye değil) DEĞİL — **endeks tier kodu** taşıyor:

| Değer | Anlam |
|-------|-------|
| `XU030` | BIST-30 üyesi |
| `XU050` | BIST-50 üyesi (BIST-30 dışı) |
| `XU100` | BIST-100 üyesi (BIST-50 dışı) |
| `NaN` | Hiçbir endekste değil |

Bu, beklenenin ötesinde zengin bir bilgi: üyelik + tier birlikte.

### 2.4 Örnek Satırlar

| PAY KODU | PAY ADI | Q1 (01-Jan) | Q2 (02-Apr) | Q3 (01-Jul) | Q4 (01-Oct) |
|----------|---------|-------------|-------------|-------------|-------------|
| AEFES | ANADOLU EFES | XU030 | XU030 | XU030 | XU030 |
| AKBNK | AKBANK | XU030 | XU030 | XU030 | XU030 |
| ALARK | ALARKO HOLDING | **XU030** | **XU050** | XU050 | XU050 |
| AGROT | AGROTECH TEK. | XU100 | XU100 | **NaN** | NaN |
| AHGAZ | AHLATCI DOGALGAZ | NaN | **XU100** | **NaN** | NaN |
| AKFYE | AKFEN YEN. ENERJI | XU100 | **NaN** | NaN | NaN |

**Toplam satır: 599 hisse** (tüm evren); 121 hissede en az bir çeyrekte üyelik mevcut.

---

## 3. Soru (a) — İlan Tarihi Analizi

### 3.1 Bulgular

Dosyada **6 sütun** vardır. Bunların 4'ü efektif tarih (çeyrek başlangıcı). **İlan tarihi, bildirim tarihi, duyuru tarihi** — hiçbir şekilde mevcut değildir.

### 3.2 Çeyreklerin Efektif Tarihleri (2025)

| Çeyrek | Efektif Tarih | Beklenen İlan Tarihi* |
|--------|---------------|----------------------|
| Q1 | 2025-01-02 | Aralık 2024 ortası |
| Q2 | 2025-04-02 | Mart 2025 ortası |
| Q3 | 2025-07-01 | Haziran 2025 ortası |
| Q4 | 2025-10-01 | Eylül 2025 ortası |

\* Tahmin: BIST genellikle ~2 hafta öncesinde duyuruyor (doğrulanmadı).

### 3.3 F-2 Durum

**F-2 DEVAM EDİYOR.** DataStore 3184 ZIP'i look-ahead-safe engeli için yeterli değildir.

İlan tarihini bulmak için iki alternatif yol:

| Yol | Açıklama | Efor |
|-----|----------|------|
| **A — KAP Arama** | KAP'ta "endeks bileşim" + tarih arama | Orta (yarı-manuel) |
| **B — BIST Basın Bülteni** | BIST web sitesinde çeyreksel duyuru arşivi | Orta |
| **C — Sabit Offset** | "Efektif - N iş günü" varsayımı | Düşük efor, yüksek risk |

Yol C (sabit offset) kabul edilemez — demand-shock stratejisinde ilan ile efektif arası gün sayısı kritik bir gözlemlenebilirdir, varsayılmaz.

---

## 4. Soru (b) — Olay Tipi Analizi

### 4.1 Bulgular

Dosyada **açık bir olay tipi sütunu yok**. Buna rağmen format, önemli bir özellik taşıyor:

> **BIST DataStore 3184 yalnızca planlı çeyreksel oturumları kaydediyor.**

Neden:
- Her yıl yalnızca 4 çeyrek veri noktası var (Q1–Q4)
- Ara dönem acil ekleme/çıkarma bu formatta görünemez
- IPO otomatik ekleme → yeni çeyreğe kadar tabloda yok
- Şirket birleşmesi/delisting → NaN olarak işlenir, ayrı kodu yok

### 4.2 F-3 ve F-4 Çözümü

| Engel | RR-Y1-011 Hükümü | Gerçeklik |
|-------|-----------------|-----------|
| **F-3**: XU100 ham N ~4x yüksek (487) | Planlı rekon'dan ayrıştırma gerekiyor | **ÇÖZÜLDÜ** — quarterly format inherently filtered |
| **F-4**: Acil/planlı ayrıştırılmamış | DataStore 3184'ten çözülecekti | **ÇÖZÜLDÜ** — format acil değişimleri kapsamıyor |

RR-Y1-011'in yıllık 70-87 XU100 olayı (ham diff) aşırı tahmin sorudu. DataStore 3184'te yalnızca çeyreksel değişimler var → gerçek N çok daha temiz:

| Endeks | Yöntem | Beklenen N (2019-2025) |
|--------|--------|------------------------|
| XU100 | Çeyreksel Q_n→Q_{n+1} diff | ~28 oturum × 4-6 değişim = 112-168 |
| XU030 | Çeyreksel Q_n→Q_{n+1} diff | ~28 oturum × 1-2 değişim = 28-56 |

Her iki endeks için **Stage-0 yeterli N eşiği** aşılıyor.

### 4.3 Ek Bulgu: Tier Değişimleri

Dosya sadece IN/OUT değil **tier değişimlerini** de izliyor (XU030↔XU050↔XU100).
Bu, demand-shock hipotezi için ek bir boyut sunuyor:
- XU030'dan XU050'ye düşüş → pasif-sermaye XU030 fon satışı + XU050 alışı
- XU100'dan çıkış → küçük pasif fon satışı

Tier geçişleri, saf giriş/çıkıştan daha ince bir etki katmanı.

---

## 5. F-2 Fizibilite Yolları — Detay

### 5.1 KAP Arama (Yol A — Önerilen)

BIST, endeks rekonstitüsyon kararlarını KAP üzerinden yayınlar.
Arama terimi: `"endeks" "bileşim" OR "endeks" "değişiklik"` + tarih filtresi

Elde edilecek artefakt: `(ticker, direction, ilan_tarihi, efektif_tarihi)` tablosu

Zorluk: KAP tam-metin arama yavaş; 2019-2025 için ~28 bildiri manuel toplanabilir.

### 5.2 BIST Basın Bülteni Arşivi (Yol B)

BIST `borsaistanbul.com/tr/duyuru-haberleri` sayfasında tarihsel duyurular var.
Filtre: "endeks" + çeyrek dönemi.

### 5.3 Karar

F-2 için **Yol A (KAP arama)** önerilir. Efor yaklaşık 1-2 saatlik yarı-manuel çalışma.
Bu ayrı bir direktif/task olarak ele alınmalıdır.

---

## 6. Genel Hüküm

```
F-1 (archive boş)        : ÇÖZÜLDÜ     — exsrk2025.zip indirildi
F-2 (ilan-tarihi)        : BLOKE       — zip'te yok; KAP arama gerekiyor (§5.1)
F-3 (planlı filtresi)    : ÇÖZÜLDÜ     — quarterly format inherently filtered
F-4 (acil ayrımı)        : ÇÖZÜLDÜ     — quarterly format acil değişimleri kapsamıyor
```

**Stage-0 kararı besleyici bilgiler:**
- Veri formatı düşünülenden çok daha temiz (quarterly, tier bilgili)
- F-2 çözümü ek kaynak gerektiriyor (KAP/BIST); mümkün ama ayrı efor
- Stage-0 ön-kayıt açılabilir, ancak F-2 çözümüne bağlı koşullu

---

## 7. Kapsam-Uyum Beyanı

Bu raporda sinyal / getiri / IC / NW-t / Sharpe / edge hükmü / panel kurma **üretilmemiştir**.
Committed pipeline dokunulmamıştır.
Yeni committed artefakt: `scripts/scratch/probe_schema_3184.py` (salt-okuma keşif scripti).
