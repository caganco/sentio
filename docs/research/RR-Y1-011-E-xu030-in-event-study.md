# RR-Y1-011-E: XU030 Periodic Reconstitution IN — Event Study

**Tarih:** 2026-06-09
**Stage-0:** `docs/yol1/STAGE0_INDEX_RECON_XU030_IN.json` (frozen, pre-registered)
**Direktif:** RR-Y1-011-E (N<=3, count=1)
**Dayanak:** RR-Y1-011-D §panel (1003 event, 25 XU030-IN), RR-Y1-011-C (PIT-safety)

---

## Hipotez (frozen)

XU030'a periyodik rekonstitüsyonla dahil edilen isimler, pasif fonların (ETF + endeks fonu) mekanik alımı nedeniyle ilan-tarihi → yürürlük-tarihi penceresinde, EW-XU030 benchmarkına göre pozitif anormal getiri sergiler.

---

## Veri ve Örneklem

| Parametre | Değer |
|-----------|-------|
| Evren | XU030-IN, 2019-2025 |
| Toplam olay | 25 |
| Geçerli olay (ölçülen) | 24 |
| Hariç tutulan | 1 (FROTO Q1-2019: ann=2018-12-21 tatil dönemi → giriş tarihi=çıkış tarihi=2019-01-02) |
| Pencere | ilan-kapanışı → yürürlük-kapanışı (olay-spesifik, ort. 13.5 gün) |
| Benchmark | EW daily return, bist30=1 üyeler AS OF ann_date (PIT-frozen; eklenen hisse dışlanır) |
| Maliyet modeli | D-207 large-cap Roll+Kyle: yarı-spread 13.4bp + Kyle ~10bp = ~23.4bp tek-yön, 46.8bp round-trip |

---

## Ölçüm Sonuçları

### Tam Örneklem (N=24)

| Metrik | Değer |
|--------|-------|
| Ortalama CAR (gross) | **+0.58%** |
| Ortalama CAR (net, maliyet sonrası) | **+0.11%** |
| NW-HAC t (net, lag=3) | **0.052** |
| NW-HAC t (gross) | 0.280 |
| Basit t (net) | 0.10 |
| Pozitif oran (gross) | **46%** |
| Gross CAR bps | 57.5 bp |
| Maliyet (round-trip) | 46.8 bp |

### Zamansal Yarı-Split (KB2)

| Yarı | N | Tarih aralığı | Ort. CAR net | NW-t |
|------|---|---------------|--------------|------|
| Yarı A (erken) | 12 | 2019-06 → 2023-06 | **+3.79%** | +4.11 |
| Yarı B (geç) | 12 | 2023-09 → 2025-09 | **-3.58%** | -0.90 |

### OUT Simetri Kontrolü (bilgi amaçlı, keep-bar değil)

| Metrik | Değer |
|--------|-------|
| OUT Ort. CAR gross | +0.96% |
| OUT NW-t gross | 0.51 |

OUT da gürültüde → simetrik sonuç.

### Per-Olay Detay

| Sembol | İlan-Tarihi | Pencere (gün) | CAR gross | CAR net |
|--------|-------------|---------------|-----------|---------|
| TSKB | 2019-06-21 | 10 | +2.79% | +2.32% |
| TRKCM | 2020-03-19 | 13 | +6.26% | +5.79% |
| MGROS | 2020-06-19 | 12 | +3.27% | +2.81% |
| OYAKC | 2020-09-18 | 13 | -3.44% | -3.91% |
| GUBRF | 2020-09-18 | 13 | +6.29% | +5.82% |
| TOASO | 2021-12-17 | 17 | +6.42% | +5.95% |
| HEKTS | 2022-03-22 | 10 | -0.75% | -1.22% |
| AKSEN | 2022-09-21 | 12 | +20.94% | +20.47% ⚠️ |
| ODAS | 2022-12-19 | 14 | -7.03% | -7.50% |
| ALARK | 2022-12-19 | 14 | -10.03% | -10.50% |
| ENKAI | 2023-03-16 | 18 | +9.65% | +9.18% |
| ASTOR | 2023-06-16 | 17 | +16.78% | +16.31% ⚠️ |
| KONTR | 2023-09-21 | 11 | +4.61% | +4.14% |
| OYAKC | 2023-09-21 | 11 | +4.22% | +3.75% |
| BRSAN | 2024-03-21 | 11 | -3.61% | -4.08% |
| DOAS | 2024-06-13 | 18 | -3.75% | -4.22% |
| ULKER | 2024-09-20 | 11 | -11.29% | -11.75% |
| MGROS | 2024-09-20 | 11 | -6.88% | -7.35% |
| TTKOM | 2024-09-20 | 11 | -0.06% | -0.53% |
| AEFES | 2024-12-20 | 13 | -29.16% | -29.63% ⚠️ |
| CIMSA | 2025-03-21 | 12 | -6.50% | -6.96% |
| TAVHL | 2025-03-21 | 12 | -8.45% | -8.92% |
| GUBRF | 2025-06-20 | 11 | -2.85% | -3.31% |
| DSTKF | 2025-09-12 | 19 | +26.39% | +25.92% ⚠️ |

⚠️ = Hisse-spesifik olaylar (AKSEN enerji krizi, ASTOR momentum, AEFES kurumsal haber, DSTKF yeni halka arz etkisi); bu olaylar rekonstitüsyon mekanizmasından değil gürültüden kaynaklanıyor.

---

## Keep-Bar Değerlendirmesi

| Kriter | Sonuç | Detay |
|--------|-------|-------|
| KB1: NW-t ≥ 2.0 | **FAIL** | NW-t = 0.052 (eşiğin çok altında) |
| KB2: Her iki yarıda pozitif işaret | **FAIL** | Yarı A +3.79%, Yarı B -3.58% (işaret tersine döndü) |
| KB3: Gross CAR > maliyet | PASS | 57.5 bp > 46.8 bp (zar-zor) |

**HÜKÜM: NOT-TRADEABLE (SERAP)**

---

## Teşhis: Neden Başarısız?

### 1. Etki tam örneklemde sıfırda
NW-t = 0.052, pratikte sıfır. 24 olayın ortalaması ~0.6% gross — istatistiksel olarak gürültüden ayırt edilemiyor.

### 2. Dramatik zamansal kararsızlık
Erken dönem (2019-06 → 2023-06): ort. +3.79% net — güçlü ve yönde tutarlı gibi görünüyor.
Geç dönem (2023-09 → 2025-09): ort. -3.58% net — tam tersine döndü.

Bu post-hoc bilgidir; Stage-0'da split donmuştur ve keep-bar ikinci yarının negatifliğini yakalar.

**Olası mekanizma bozulma açıklaması:**
- 2023 öncesi: BIST pasif fon evreni küçük → talep şoku daha az fiyatlanmış → öne konumlanma ödüllü
- 2023 sonrası: Pasif fon evreni büyüdü + piyasa yapısı değişti → talep şoku ilan anında fiyatlanıyor → pencere arbitraj fırsatı kalmıyor
- Büyük gürültü olayları (AEFES -29%, DSTKF +26%) zamansal ortalamayı boğuyor

### 3. Yüksek hisse-spesifik gürültü
N=24 ile tek hisse-özgü olaylar (AKSEN enerji krizi, AEFES kurumsal negatif haber, DSTKF halka arz etkisi) havuzu domine ediyor. Rekonstitüsyon mekanizmasının "sinyali" bu gürültüye gömülü.

### 4. Neden düzeltme teklif etmiyorum
- "2019-2022 alt-örneğini alalım" → post-hoc, KB2 freeze'i bunu keser (Stage-0 bunu tam bu sebeple dondurdu)
- "XU100'e genişletelim" → K1/K3 zincir bloku: farklı tez, sıfırdan Stage-0
- "Büyük gürültü olaylarını çıkaralım" → post-hoc outlier temizliği yasak, graveyard kaydına gider

---

## Mezarlık Kaydı

**Dosya:** `docs/yol1/graveyard/INDEX_RECON_XU030_IN.md`

**Özet:**
Etki tam örneklemde istatistiksel sıfırda (NW-t=0.05). Dramatik zamansal kırılma: erken dönem (2019-2023) apparent güç, geç dönem (2023-2025) tam tersine döndü → efektif talep-şoku anomalisi BIST'te zaten fiyatlanmış veya mekanizma bozulmuş. Hüküm: SERAP. Yeni-aday açılmaz (K1/K3 zincir bloku).

---

## Sonuç

**XU030 periodic-reconstitution IN penceresi SERAP — pasif talep şoku etkisi BIST'te ölçülebilir bir alfa üretmiyor.**

Birincil sebep ilan anında fiyatlanma (priced-in at announcement), ikincil sebep N=24 örneklemde hisse-spesifik gürültünün hakimiyeti. Zamansal yarılma erken dönemde apparent güç gösterse de bu post-hoc bilgidir ve Stage-0 bunu keeps-bar'a sokmamıştır.

Negatiif sonuç değerlidir: BIST'te index-inclusion anomalisinin 11-19 günlük kamuya açık pencerede retail-erişilebilir olmadığı, ampirik olarak teyit edildi.
