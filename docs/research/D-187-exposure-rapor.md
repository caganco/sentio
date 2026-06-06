# D-187 Dürüst-Benchmark + Maruziyet-Rejimi Ayrım Testi -- Sonuç Raporu

**Tarih:** 31 May 2026
**Tür:** Ölçüm + Stage 0 ön-kayıt + backtest
**Dayanak:** D-185/186 (giriş-alfası yok → Yol 2), doğrulama-agent kör-nokta tespiti, DEC-045, DEC-039
**Stage 0:** `docs/exposure_test/STAGE0_exposure_regime_preregistration.json` (commit e31117a, sonuç ÖNCESİ)
**Ham sonuç:** `docs/exposure_test/exposure_results.json`

---

## 1. TL;DR -- DEC-045 VERDICT

İki ayrı soru, iki ayrı cevap:

- **S-A (BAZ TAHSİS, statik barbell): GEÇER** -- ama AĞIR ŞERHLİ.
  En iyi sabit oran (SA_70, %70 equity) reel **+%10.2/yıl**, B1-TLREF (+%0.06) ve B5-TÜFE (%0)
  reel geçiyor. Frozen kurala göre baz-tahsis "değerli." **AMA teşhis-benchmark ALTIN (+%22.1
  reel) bunu 2 KATINDAN fazla geçiyor** → bu "değer" büyük ölçüde **debasement-beta** (TL
  değer-kaybı rejiminde herhangi sert-varlık tutmak nakdi/enflasyonu geçer), equity-spesifik
  beceri DEĞİL. Doğrulama-agent'ın tam uyarısı doğrulandı.

- **S-B (AKTİF ZAMANLAMA, 200-MA switch): GEÇMEZ** -- kesin.
  Reel **-%5.7/yıl** (en iyi S-A'nın çok altında), random-switch-null'ı geçemiyor
  (pctile 0.17 < 0.95). 200-MA rejim-sinyali whipsaw'a yakalandı, RASTGELE switch'ten bile kötü.
  **Aktif zamanlama HAK ETMİYOR -- elenir.**

- **DİSİNFLASYON (2024-07+, en güncel rejim) TERSİNE ÇEVİRİYOR:**
  TLREF reel **+%23.2**, ALTIN **+%35.4**, EQUITY (XU100) reel **-%5.7** (KAYBETTİ). En iyi barbell
  = en DÜŞÜK-equity (SA_30 +%14.4 > SA_70 +%2.9). Yani en güncel rejimde "equity maruziyeti değerli"
  YANLIŞ; nakit (TLREF) kraldı. "Baz-tahsis değeri" rejim-kırılgan.

**NET:** Baz-tahsis (varsayılan maruziyet) nakit/enflasyona göre değer katıyor AMA bu generic
debasement-beta (altın daha iyi yaptı, üstelik disinflasyonda TLREF equity'yi ezdi); equity-spesifik
prim KANITLANMADI. Aktif-zamanlama elendi. → premise/tasarım maintainer (DEC-039).

---

## 2. KRİTİK VERİ KISITI (raporun en önemli şerhi)

- **TLREF (TP.BISTTLREF.KAPANIS) EVDS kapsamı 2022-07'de BAŞLIYOR** (2019 değil). Etkin
  karşılaştırma penceresi = **2022-07 → 2026-04** (~956 işlem günü). TLREF içeren tüm
  karşılaştırmalar bu pencerede. **pre_surge (2019-2021) dilimi TLREF için YOK.**
- **Altın (B4) USDTRY kapsamı 2023-08'de başlıyor** (684 gün) → altın full-window sayısı
  S-A'dan KISA pencerede. **Adil altın kıyası DİSİNFLASYON diliminde** (aynı pencere): orada da
  altın (+%35.4) > en iyi barbell → debasement-beta bulgusu KOMPARABL pencerede de geçerli.
- KARAR DİLİMİ (disinflasyon 2024-07+) TLREF kapsamında TAM → DEC-045 verdict'i geçerli.
- **TLREF düzeltmesi:** KAPANIS bir ORAN değil, zaten-bileşik RETURN-INDEX (monoton-artan
  1573→5827); doğrudan kullanıldı (çifte-bileşikleme önlendi). Detay: commit 1dd353b.

---

## 3. Tam pencere (2022-07 → 2026-04) -- yıllık REEL (nominal ayrı)

| Seri | yıllık REEL | yıllık nominal | max-DD | gün |
|---|---|---|---|---|
| B1_TLREF (nakit) | +0.06% | +41.1% | 0.0% | 956 |
| B5_TUFE (reel-sıfır) | 0.0% | +41.0% | 0.0% | 956 |
| B2_BARBELL 50/50 | +7.8% | +51.9% | 10.4% | 956 |
| **S-A SA_30** (%30 eq) | +5.0% | +48.0% | 6.0% | 956 |
| **S-A SA_50** (%50 eq) | +7.8% | +51.9% | 10.4% | 956 |
| **S-A SA_70** (%70 eq) | **+10.2%** | +55.3% | 14.9% | 956 |
| B3_XU100 (%100 eq) | +13.0% | +59.4% | 22.9% | 956 |
| **B4_GOLD (teşhis)** | **+22.1%** | +65.5% | 16.5% | 684* |
| **S-B switcher** | **-5.7%** | +33.3% | 22.2% | 956 |

*Altın 2023-08+ (kısa pencere); adil kıyas §5 disinflasyon.

Gözlem: nominal HERKES ~+%33-66 (TL drift; B&H tuzağı, D-186 dersi). REEL'de ayrışma net:
TLREF/TÜFE reel-sıfır, equity-barbell reel-pozitif (risk arttıkça artıyor), **altın hepsini
geçiyor**, S-B reel-NEGATİF.

---

## 4. S-A verdict (DEC-045): GEÇER, ama gold-teşhis şerhi

Frozen kural: en iyi sabit-oran reel > B1-TLREF VE > B5-TÜFE.
- SA_70 reel +%10.2 > TLREF +%0.06 > TÜFE %0 → **GEÇER.** Equity maruziyeti nakit+enflasyona
  reel pozitif katkı yaptı (2022-07+ penceresinde).
- Risk-ayarlı: SA_70 reel %10.2 / maxDD %14.9; SA_50 %7.8 / %10.4; SA_30 %5.0 / %6.0. Daha çok
  equity = daha çok reel getiri AMA daha çok DD (lineer trade-off, sürpriz yok).

**GOLD-TEŞHİS (doğrulama-agent'ın kritik noktası):** Best S-A (+%10.2) altını (+%22.1) GEÇEMİYOR;
%100 equity (+%13.0) bile geçemiyor. → Baz-tahsisin reel-getirisi **debasement-beta**: TL
değer-kaybı rejiminde sert-varlık (equity VEYA altın) tutmak nakdi geçer; altın (pasif hedge) daha
iyi yaptı. "Baz-tahsis değerli" = generic maruziyet değeri, equity-spesifik beceri DEĞİL.

---

## 5. DİSİNFLASYON dilimi (2024-07+, en güncel & en ilgili rejim) -- TERSİNE

| Seri | yıllık REEL |
|---|---|
| **B4_GOLD** | **+35.4%** |
| **B1_TLREF (nakit)** | **+23.2%** |
| S-A SA_30 (%30 eq) | +14.4% |
| B2/SA_50 | +8.6% |
| S-A SA_70 (%70 eq) | +2.9% |
| **B3_XU100 (%100 eq)** | **-5.7%** |
| S-B switcher | -6.0% |

Disinflasyonda **nakit (TLREF) kraldı** (yüksek reel faiz; enflasyon nominal faizden hızlı düştü),
**altın ikinci**, **equity reel KAYBETTİ.** En iyi barbell = en az-equity. Yani "equity maruziyeti
değer katar" tezi en güncel rejimde GEÇERSİZ. Baz-tahsis değeri 2022-2023 equity boom'una bağımlı,
rejim-kırılgan. (Şerh: disinflasyon ~20 ay, istatistiksel güç düşük.)

---

## 6. S-B verdict (DEC-045): GEÇMEZ -- kesin

- S-B reel -%5.7 (full), -%6.0 (disinflasyon) << en iyi S-A (+%10.2) → statik barbell'i geçemiyor.
- 17 switch; random-switch-null: null_mean +%3.4, null_p95 +%21.1, S-B pctile **0.17** → random
  switch'ler S-B'den çok daha iyi (S-B'yi %83 oranında geçti). **200-MA rejim-sinyali değersiz**
  (whipsaw + switch maliyeti).
- İki failure: `does_not_beat_static_barbell` + `fails_random_switch_null`. **Aktif zamanlama ELENDİ.**

---

## 7. Ne anlama geliyor

- **Aktif zamanlama (equity↔TLREF switch) bir SERAP** -- giriş-alfası gibi (D-185/186), rejim-
  zamanlaması da random'ı geçemiyor, statik barbell'i bozuyor. Üç bağımsız test (giriş-alfası,
  trend-motoru, rejim-zamanlaması) hepsi: **sistematik tahmin bu evren/pencerede değer katmıyor.**
- **Baz-tahsis (statik maruziyet) değerli AMA generic:** nakit/enflasyonu geçer, fakat altın daha
  iyi yapar (debasement-beta) ve disinflasyonda nakit equity'yi ezer. Yani "değer" = sert-varlık
  maruziyeti + rejim, equity-seçimi/zamanlaması DEĞİL.
- Doğrulama-agent'ın iki tezi de doğrulandı: (a) baz-tahsis vs aktif-zamanlama AYRIMI kritikti;
  (b) altın olmadan "baz-tahsis değerli" demek kendi tuzağımıza düşmekti -- altın testi, değerin
  beceri değil debasement-beta olduğunu ortaya çıkardı.

---

## 8. Caveat'lar (açık)

- **TLREF kapsamı 2022-07+** → etkin pencere 2022-07–2026; pre_surge yok. Tam-tarihsel TLREF
  EVDS'de yok (gerçek kısıt).
- **XU100 fiyat-endeksi** (temettüsüz, ~%2-4/yıl): equity tarafı dezavantajlı → S-A reel-getirisi
  muhafazakâr (gerçek temettülü daha yüksek olurdu, ama yine altının altında kalması muhtemel).
- **Altın 2023-08+** kısa pencere; adil kıyas disinflasyon diliminde (orada da altın kazanıyor).
- **Disinflasyon ~20 ay** → istatistiksel güç düşük; "TLREF/altın kazandı" yönü güçlü ama
  magnitude belirsiz.
- BIST100 = endeks proxy (tek-hisse seçimi yok; bu maruziyet testi).
- TÜFE deflatör aylık ffill.

---

## 9. DEC-045 disiplini

Karar kuralı Stage 0'da (commit e31117a) sonuç öncesi donduruldu; gevşetilmedi. S-A frozen kurala
göre GEÇTİ (rapor sadık) -- ama gold-teşhis + disinflasyon-inversiyon zorunlu yorumsal bağlamı
sağlıyor (doğrulama-agent'ın istediği). Post-hoc "disinflasyon→full-period" veya eşik-değişimi
YAPILMADI. TLREF veri-semantiği düzeltmesi (KAPANIS=index) sonuç öncesi yapıldı + Stage 0/config'te
notlandı.

---

## 10. DEC-039 + Öneri

Bu program ÖLÇTÜ + frozen DEC-045 verdict üretti. Karar maintainer. arastirma katmani önerisi:

- **Aktif-zamanlama (rejim switch) ana-sisteme KONULMAMALI** -- elendi (statik barbell + random'ı
  geçemiyor). Üçüncü "sistematik tahmin" başarısızlığı.
- **Baz-tahsis (statik maruziyet) değerli ama equity-spesifik değil:** öneri, "maruziyet ortağı"nın
  equity-only barbell DEĞİL, **sert-varlık sepeti** (equity + altın + nakit/TLREF) olarak
  düşünülmesi -- çünkü altın 2x equity yaptı ve disinflasyonda TLREF kraldı. Hangi statik karışım
  (ve altın dahil mi) ayrı bir tasarım kararı.
- **Sonraki adım seçenekleri (maintainer):** (a) statik çok-varlık tahsis (equity+altın+TLREF) reel
  optimizasyonu; (b) "ne zaman switch" yerine "hangi sabit karışım" sorusu; (c) sistemin kimliğini
  "tahmin/zamanlama" değil "disiplinli statik maruziyet + maliyet kontrolü" olarak sabitlemek
  (RR-038/doğrulama-agent tezi).
