# Audit Report

# === AUDIT REPORT — 2026-05-13 ===
### Risk Yöneticisi Masası | "Önce Kaybetme" Protokolü

---

## ⚠️ ÖN UYARI: FIYAT VERİSİ EKSİKLİĞİ

Analyst raporu birden fazla pozisyon için "fiyat verisi eksik" notu düşmüş. **RSI ve momentum hesaplamaları güncel fiyat olmadan yapılıyorsa tüm teknik sinyaller güvenilirlik sorunu taşır.** Bu audit boyunca bu kısıtı göz önünde bulunduruyorum.

---

## ANALİST SİNYALLERİ DEĞERLENDİRMESİ

---

### 🔴 AKSEN.IS — SELL-WEAK: **ONAYLANDI + GÜÇLENDİRİLDİ**

**Thesis Kırma:**
Analyst'ın en güçlü argümanı: *"Brent 107$'da enerji hissesi satmak duygusal olarak zor ama risk limiti kural."* Bu doğru bir çerçeve — ancak zayıf nokta şu: **Brent 107$'ın sürdürülebilirliği sorgulanmıyor.** Eğer bu rallinin arkında spekülatif pozisyon birikimi varsa (CFTC net long pozisyonlarına bakılmadı) ve Brent 2 hafta içinde 95$'a geri dönerse, AKSEN hem satış baskısı hem de ralliden faydalanamamış olma gerçeğiyle karşı karşıya kalır.

**Karşı Senaryo:** *AKSEN'i satmak için Brent rallisini kullanıyoruz — ya rally devam ederse?* Cevap: %54.6 konsantrasyon ile portföy zaten asimetrik risk altında. Rally devam etse bile konsantrasyon riski varlığını korur; kayıp Brent düşüşünde katlanarak gelir. Satış kararı doğru, timing gerekçesi yeterince savunulamaz ama sonuç değişmiyor.

**Risk Skorlama:**
| Risk Boyutu | Skor |
|---|---|
| Likidite | 2 |
| Konsantrasyon | **5** |
| Makro (Brent bağımlılığı) | 4 |
| Şirket | 2 |
| Timing | 3 |
| **TOPLAM** | **16/25** |

**Worst-Case:**
- Brent aniden 90$'a gerilerse (OPEC+ sürpriz üretim artışı / talep yıkımı): AKSEN mevcut pozisyonla %20-25 drawdown potansiyeli
- Satış 150-180 lot ile sınırlandırılırsa bile, kalan pozisyon + ENERY birlikte enerji konsantrasyonu %35-40'ta kalabilir — yeterli değil
- **Stop-loss mevcut:** ✅ (maliyet altı %8)

**Audit Kararı:** ONAYLANDI. Ancak satış miktarı 150-180 lot değil, **minimum 200 lot** olarak revize edilmeli. Hedef: enerji toplam konsantrasyonu (AKSEN + ENERY) %25 altına çekmek.

---

### 🟡 TTKOM.IS — HOLD: **ONAYLANDI**

**Thesis Kırma:**
Analyst argümanı: *"Defansif telekom bu belirsiz makroda kalkan."* Zayıf nokta: **TCMB faiz indirim beklentisi çift taraflı kılıç.** Faiz indirilirse telekom re-rating pozitif — bu doğru. Ancak faiz indiriminin TRY üzerinde baskı yaratması (TRY zaten 45.39'da, kırılgan) ve enflasyonist beklentileri yeniden fiyatlaması halinde TTKOM'un kur bağımlı maliyet yapısı baskı altına girer. Analyst bu riski görmüş ama hafife almış.

**Karşı Senaryo:** *TCMB beklentilerin aksine faiz artırırsa?* → Telekom değerlemesi DCF bazında ciddi şekilde sıkışır, TRY güçlenir ama TTKOM'un borç yapısı ve altyapı harcamaları faiz duyarlı. RSI 62 → aşırı alım bölgesine yakın, momentum zayıflama riski var.

**Risk Skorlama:**
| Risk Boyutu | Skor |
|---|---|
| Likidite | 1 |
| Konsantrasyon | 2 |
| Makro (faiz/kur) | 3 |
| Şirket | 2 |
| Timing | 2 |
| **TOPLAM** | **10/25** |

**Worst-Case:**
- TCMB sürpriz faiz artışı → TTKOM %15 drawdown, stop ₺56.4'te tetiklenir
- Portföy etkisi: 329 lot × (₺60.65 - ₺56.40) = ~**₺1,400 stop-loss kaybı** — yönetilebilir

**Audit Kararı:** ONAYLANDI. Stop-loss seviyesi ₺56.4 yerinde. Ek öneri: TCMB karar gününde pozisyon yarıya indirilmiş olmalı, karar sonrası yeniden değerlendirme.

---

### 🔴 TAVHL.IS — SELL-WEAK: **ONAYLANDI + ACİLİYET ARTTIRILDI**

**Thesis Kırma:**
Analyst'ın en güçlü argümanı: *"Brent 107$'da havacılık = asimetrik kötü setup."* Bu doğru. Ancak buradaki gerçek zayıflık: **%50-60 satış önerisi neden %100 değil?**

Analyst "kalan için stop koy" diyor. Ama şunu sormak gerekiyor: *Bu pozisyonda tutulmayı hak eden ne var?* RSI=39 (momentum kaybı), Brent 107$ (yakıt baskısı), zaten ⚠️ işaretli pozisyon, sektörel headwind makro tarafından teyit edilmiş. "Brent 100$ altına dönerse geri al" senaryosu için pozisyon tutmak, **kayıp pozisyonu umutla taşımak** değil mi?

**Karşı Senaryo:** *Brent 107$'da bile TAVHL'yi tutmanın gerekçesi nedir?* Yok. Hedging aracı değil. Bağımsız katalizör yok. Druckenmiller zinciri: Makro (Brent↑) → Sektör (Havacılık↓) → Hisse (TAVHL↓) → Timing (şimdi çık). Zincirin dört halkası da aynı yönü gösteriyor.

**Risk Skorlama:**
| Risk Boyutu | Skor |
|---|---|
| Likidite | 2 |
| Konsantrasyon | 2 |
| Makro (Brent bağımlılığı) | **5** |
| Şirket | 3 |
| Timing | **4** |
| **TOPLAM** | **16/25** |

**Worst-Case:**
- Brent 115$'a yükselirse (İran/Rusya eskalasyonu): TAVHL %25-30 düşüş
- 68 lot × ₺286.50 = ~₺19,482 pozisyon → %30 düşüş = **₺5,844 kayıp**
- Stop ₺266.6'da tetiklenirse: 68 lot × (₺286.50 - ₺266.60) = **₺1,353 kayıp** — ama Brent şoku senaryosunda gap-down riski stop'u işlevsiz kılabilir

**Audit Kararı:** ONAYLANDI ancak **DEĞİŞTİRİLDİ.** Önerilen %50-60 satış yetersiz. **Minimum %75 satış (51 lot), kalan 17 lot için ₺266.6 hard stop.** Gerekçe: Druckenmiller zincirinin dört halkası da satışı gösteriyor; kısmi tutmanın rasyonel gerekçesi yok.

---

### 🟢 KCHOL.IS — HOLD/BUY-WEAK: **ONAYLANDI (KOŞULLU)**

**Thesis Kırma:**
Analyst argümanı: *"Düşük VIX ortamında holding değer açar."* Zayıf nokta: **KCHOL'un Koç Holding olduğu varsayılıyor ancak portföyündeki enerji ağırlığı (Tüpraş, Opet) nedeniyle "saf holding" değil, dolaylı enerji maruziyeti var.** AKSEN satılırken KCHOL'a kaynak yönlendirmek enerji riskini dolaylı yoldan sürdürmek anlamına gelebilir.

**Karşı Senaryo:** *KCHOL holding iskontosu genişlerse?* Türk holdingleri tarihsel olarak belirsizlik dönemlerinde derin iskontoya düşer. TRY volatilitesi artar, kurumsal çıkış başlarsa holding iskontosu %30-40'a ulaşabilir.

**Risk Skorlama:**
| Risk Boyutu | Skor |
|---|---|
| Likidite | 2 |
| Konsantrasyon | 2 |
| Makro (TRY/faiz) | 3 |
| Şirket (dolaylı enerji) | 3 |
| Timing | 2 |
| **TOPLAM** | **12/25** |

**Worst-Case:**
- TRY ani değer kaybı + holding iskontosu genişlemesi: %20-25 düşüş potansiyeli
- 81 lot × ₺188.83 = ~₺15,295 → %25 düşüş = **₺3,824 kayıp**

**Audit Kararı:** ONAYLANDI. Ancak **BUY-WEAK sinyali reddedildi.** AKSEN/TAVHL satışından gelen nakit KCHOL'a değil, önce nakitte bekletilmeli. Gerekçe: Fiyat verisi eksik, dolaylı enerji maruziyeti belirsiz, holding iskontosu riski ölçülmemiş. "Satıştan gelen nakdi buraya yönlendir" önerisi erken.

---

### 🟡 ENERY.IS — WATCH: **ONAYLANDI + SATIŞ EŞİĞİ DÜŞÜRÜLDÜ**

**Thesis Kırma:**
Analyst'ın en güçlü argümanı: *"Brent 107$'da ENERY sadece +0.5% → distribüsyon işareti."* Bu audit'in en değerli tespiti. **Güçlü sektör rallisinde zayıf kalan hisse = kurumsal çıkış sinyali.** Bu gözlem doğru ve kritik.

Zayıf nokta: **Stop seviyesi ₺8.40 çok aşağıda.** Mevcut fiyat ~₺9.07 (maliyet), stop %7.4 aşağıda. Distribüsyon tespit edilmişse neden bu kadar geniş stop? Distribüsyon devam ederse ₺8.40'a ulaşmadan önce önemli hasar oluşabilir.

**Karşı Senaryo:** *ENERY kurumsal ilgi görmeye başlarsa?* Olası ama kanıt yok. Momentum skoru negatif (-0.11), Brent rallisinden kopukluk. Bekleme maliyeti yüksek.

**Risk Skorlama:**
| Risk Boyutu | Skor |
|---|---|
| Likidite | **4** |
| Konsantrasyon | 3 |
| Makro | 3 |
| Şirket (küçük enerji) | **4** |
| Timing | **4** |
| **TOPLAM** | **18/25** |

> ⚠️ **En yüksek risk skoru. 1543 lot küçük enerji hissesi = likidite tuzağı riski.**

**Worst-Case:**
- Distribüsyon tamamlanır, kurumsal çıkış hızlanır: %20-25 düşüş
- 1543 lot × ₺9.07 = ~₺13,995 → %25 düşüş = **₺3,499 kayıp**
- Likidite sorunu: 1543 lot küçük hissede tek seansta çıkış mümkün olmayabilir → **gap-down + düşük hacim = stop çalışmaz**

**Audit Kararı:** ONAYLANDI ancak **DEĞİŞTİRİLDİ.** Stop ₺8.40 → **₺8.70'e yükseltildi** (maliyet altı %4). Gerekçe: Distribüsyon işareti varsa erken çıkış daha az zararlı. Ayrıca bugün içinde **%25 pozisyon küçültmesi (385 lot satış) önerilir** — likidite riskini azaltmak için.

---

## FIRSAT RADAR DEĞERLENDİRMESİ

**AKBNK.IS — WATCH→BUY-WEAK:** ⚠️ **KOŞULLU ONAY**
Giriş kriteri (MA20 + 1.5x hacim) yerinde. Ancak fiyat verisi eksikken pozisyona girmek için nakit hazır tutulması yeterli. Aktif alım için TCMB belirsizliği geçmeli.

**EREGL.IS — UZAK DUR:** ✅ **TAM ONAY**
RSI=79 geri dönüş riski yüksek. Analyst'ın "iki kural aynı anda çiğneniyor" tespiti yerinde.

**THYAO.IS — WATCH (Negatif):** ✅ **TAM ONAY**
TAVHL varken THY eklemek sektör konsantrasyonunu havacılıkta katlar. Kesinlikle yaklaşılmaz.

---

## PORTFÖY SAĞLIK KONTROLÜ

### Konsantrasyon Analizi
```
AKSEN  (~591 lot × ₺87.59)  = ~₺51,765  → %30.5  ⚠️ (satış sonrası ~%18'e inmeli)
TTKOM  (329 lot × ₺60.65)   = ~₺19,954  → %11.7  ✅
TAVHL  (68 lot × ₺286.50)   = ~₺19,482  → %11.5  ⚠️ (satış sonrası ~%3'e inmeli)
KCHOL  (81 lot × ₺188.83)   = ~₺15,295  → %9.0   ✅
ENERY  (1543 lot × ₺9.07)   = ~₺13,995  → %8.2   ⚠️ (küçültme sonrası ~%6'ya inmeli)
NAKİT                        = ~₺49,509  → %29.1
TOPLAM                       = ~₺170,000
```

| Kontrol | Durum |
|---|---|
| Sektör max %30 kuralı | ❌ Enerji (AKSEN+ENERY) = %38.7 → KURAL İHLALİ |
| Max 2 hisse/sektör | ✅ Her sektörde max 2 |
| Korelasyon riski | ⚠️ AKSEN-ENERY yüksek korelasyon, KCHOL dolaylı enerji |
| Nakit tamponu | ✅ %29 nakit sağlıklı |

### Drawdown Durumu
- **TAVHL:** ⚠️ işaretli pozisyon, maliyet ₺286.50 — mevcut RSI=39 momentum kaybı devam ediyorsa zaten zararda olma ihtimali yüksek
- **ENERY:** ⚠️ -1% zarar mevcut, büyüme riski var
- **Genel portföy:** Nakit %29 ile korunaklı görünse de enerji konsantrasyonu ani Brent tersine dönüşünde portföyü ciddi etkiler

### Stop-Loss Durumu
| Hisse | Stop Seviyesi | Durum |
|---|---|---|
| AKSEN | Maliyet altı %8 (₺80.58) | ✅ Mevcut |
| TTKOM | ₺56.40 | ✅ Mevcut |
| TAVHL | ₺266.60 | ⚠️ Mevcut ama gap-down riski var |
| KCHOL | ₺177.50 | ✅ Mevcut |
| ENERY | **₺8.70 (revize)** | ⚠️ Revize gerekiyor |

---

## TUZAK DENETİMİ

```
☑ Retail davranışı tuzağı:
  "Brent rallisi var, ENERY/AKSEN'e ek alım" → 
  Analyst bunu açıkça uyardı ✅
  Audit teyit eder: ENERY'nin Brent'e olan zayıf tepkisi 
  retail FOMO'nun karşısında kurumsal çıkış olduğuna işaret ediyor.

☑ FOMO sinyali:
  EREGL RSI=79 → "Momentum var, kaçırıyorum" hissi → 
  Analyst doğru reddetmiş ✅

☑ Kurumsal akış analizi:
  ENERY: Brent +3% ama hisse +0.5% → 
  Kurumsal akış önerinin TERSİNE → distribüsyon 
  Bu portföydeki en kritik kurumsal sinyal ⚠️

☑ Haberle alım tuzağı:
  Brent spike haberi çıktıktan sonra enerji almak = 
  geç kalmış pozisyon → Analyst ve audit aynı fikirde ✅
```

---

## WORST-CASE SENARYOLAR

### Senaryo 1: Brent %30 Düşüşü (Talep Yıkımı / OPEC+ Sürpriz)
*Brent 107$ → 75$*
- AKSEN: Tahmini %30-35 düşüş → Mevcut pozisyon (₺51,765) → **₺15,530-18,118 kayıp**
- ENERY: %35-40 düşüş (küçük hisse, likidite sorunu) → **₺4,898-5,598 kayıp**
- KCHOL: Dolaylı enerji etkisi %10-15 → **₺1,530-2,294 kayıp**
- TAVHL: Yakıt maliyeti düşer ama trafik yavaşlarsa karışık etki → ±%5
- **Toplam potansiyel zarar: ₺22,000-26,000 (portföyün ~%13-15'i)**

### Senaryo 2: Black Swan — TCMB Sürpriz Faiz Artışı
*+500 baz puan acil artış*
- TRY güçlenir, TRY varlıklar yeniden fiyatlanır
- KCHOL: Holding iskontosu genişler → %20 düşüş → ₺3,059 kayıp
- TTKOM: Faiz artışı DCF'yi ezer → %15 düşüş → stop tetiklenir → ₺1,400 kayıp
- AKSEN: Yatırım maliyetleri artar → %10 düşüş
- **Toplam etki: ₺6,000-9,000 (yönetilebilir, nakit tampon nedeniyle)**

### Senaryo 3: Jeopolitik Kriz (Bölgesel Eskalasyon)
*Türkiye doğrudan etkilenen taraf*
- Tüm pozisyonlar %20-30 gap-down açılış riski
- Stop-loss'lar gap nedeniyle çalışmayabilir
- 1543 lot ENERY = **likit olmayan pozisyon, çıkış imkansız**
- **Portföy zararı: ₺34,000-51,000 (%20-30)**
- **Nakit %29 bu senaryoda kurtarıcı**

### Stop-Loss Tetikleme Toplam Etkisi (Normal Piyasa)
```
TTKOM stop (₺56.40):  329 × (₺60.65-₺56.40) = ₺1,398 kayıp
TAVHL stop (₺266.60): 17 × (₺286.50-₺266.60) = ₺338 kayıp (75% satış sonrası)
ENERY stop (₺8.70):  1,158 × (₺9.07-₺8.70) = ₺429 kayıp (25% satış sonrası)
KCHOL stop (₺177.50): 81 × (₺188.83-₺177.50) = ₺918 kayıp
Toplam stop kayıpları: ~₺3,083 (%1.8 portföy) ✅ KABUL EDİLEBİLİR