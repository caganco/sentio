# D-206 NAV-iskonto-Z mean-reversion -- YENI PARADIGMA (time-series), NAV-discount ilk turu (N<=3)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d206.json` (config_version d206-v1, sonuclardan ONCE
> donduruldu; evren + iskonto-Z-tanimi + trailing-pencere + horizon + lag-konvansiyon + unit-
> harmonizasyon EDGE-GORMEDEN donmus). Ham sonuc: `docs/yol1/d206_results.json`. Motor:
> `src/screening/d206_nav_discount.py` (committed D-203/D-204 motorlarina SIFIR-dokunus -- bu
> modul onlarin yardimcilarini READ-ONLY cagirir ve KENDI panelini hesaplar). Maliyet mekanigi:
> D-204 harness'i (`per_stock_cost_panel`/`d204_basket_net_series`/`breakeven_cost_bps`/
> `holding_period_stats`) REUSE. Olcum geometrisi: `src/screening/d206_config.py`. Karar esikleri:
> `src/signals/thresholds.py` (D206_* blok).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N=1 aday (nav-discount-mr). YENI-paradigma:
> cross-sectional faktor-secimi TUKENDI (hi52 KAPANDI D-205, lowvol63 ELENDI NRR-007, value-regime
> ELENDI NRR-008 -- 3/3 kapandi). Bu CROSS-SECTIONAL DEGIL: her holding KENDI iskonto-zaman-
> serisine sahip ve KENDI gecmisine gore standardize edilir. **NAV-discount ilk turu = N<=3 kilidi
> 1.** Sinyal-VARSA tam RR-013 mimarisi AYRI-sonraki-adim (O+Cagan); bu yalniz ilk-okuma.

## 1. Soru

Cagan+O karari (pre-condition RR-044 tamam): holding-sirketi **NAV-iskonto mean-reversion** --
TIME-SERIES, dusuk-turnover, retail-uygun. Literatur (Pontiff 1995; CEF premia mean-revert,
yari-omur 7.7-10.3 ay): bir holding'in NAV-iskontosu KENDI tarihsel ortalamasina geri-doner.
Hipotez: **iskonto-Z YUKSEK** (iskonto genis -> holding ucuz) -> **forward-return POZITIF** (MR).

**Beklenti-kalibrasyonu (durust, ONCEDEN): BELIRSIZ.** Holding-iskonto-MR ABD CEF'leri icin
iyi-belgelenmis ama BIST-holding'lerinde TEST-EDILMEMIS; N kucuk (6 holding). Eleme TEMIZ ve
DEGERLI bir sonuc. Kutlama-beklentisi YOK. Sonuc-ne-olursa durust raporlanir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren (FROZEN):** 6 holding -- KCHOL, SAHOL, AGHOL, BRYAT, ALARK, DOHOL. Builder-curate;
  her holding `listed_subsidiaries[ticker, stake_pct]` + dogrulama-flag. ALARK/DOHOL
  `listed_fraction_low` flagli (DIKKAT: listelenmemis-istirak payi yuksek). AGHOL kisa (2018+).
  CCOLA HARIC (AEFES uzerinden cift-sayim).
- **Sinyal (iskonto-Z, look-ahead-safe):** `NAV(t) = sum_i stake_i * istirak_mktval(t-1)`
  (istirak-tarafi 1-ay-yayin-lag); `discount(t) = (NAV(t) - holding_mktcap(t)) / NAV(t)`,
  holding'in KENDI market-cap'i ayni-ay t (canli-fiyat, lag YOK -- asimetri kasitli+belgeli);
  `discount-Z(t)` = discount'un trailing-36ay (min 24) ortalama/std'sine gore standardize
  (mevcut-ay KENDI penceresinde DEGIL -> look-ahead-safe). 24/48/60-supurme YOK (grid = p-hacking).
- **Return (FROZEN):** mktval-implied toplam-getiri `mktcap(t+h)/mktcap(t)-1 + dyld(t)*h/12`,
  UNIFORM 2009-2026. **primary horizon = 6 ay** (TEK; yari-omur ortasi; HAC lags=6). 1/3-ay
  SECONDARY-context, ASLA gate'lenmez.
- **Unit-harmonizasyon (FROZEN on-isleme):** degoran kaynak-dosyalari piyasa-capinda guc-un-10
  yeniden-degerleme (power-of-10) kirilmalari tasir (2026-02'de ~1052x; 2009-09/10 gecici). discount within-month
  oran oldugu icin SINYAL unit-dayanikli, ama cross-month RETURN degildir. Aylik cross-sectional
  medyan-MoM-oran |log10|>0.7 (>5x/<0.2x, tek-ayda-imkansiz) ise 10^round(log10) duzeltilir.
  **Veri-temizleme, optimizasyon DEGIL** (3 kirilma tespit: 2009-09 x0.1, 2009-10 x10, 2026-02 x1000).
- **FIDELITY-GUARD:** mktval-implied-TR proxy'si DONMUS adjusted total-return index'e (tr_index_net)
  2019-2026 ortusmesinde dogrulanir; medyan-corr<0.95 VEYA medyan-MAE>0.03 ise motor RAISE eder.
- **SIFIR-motor-dokunusu (Strangler):** loader'a SADECE alt-cizgisiz `degoran[0-9]{6}.zip` glob'u
  eklendi (read-only genisletme, varsayilan davranis korundu); committed D-203/D-204 fonksiyonlari
  yalniz CAGRILDI, degismedi.

## 3. 5 TIME-SERIES gate + kontroller (FROZEN)

| Gate | Tanim | Esik |
|---|---|---|
| **G1 sinyal-icerik** | pooled FE-panel (holding fixed-effects) within-beta isareti | beta > 0 (MR) |
| **G2 anlamlilik** | Driscoll-Kraay\|t\| (PRIMARY, T-dayali) + wild-cluster-bootstrap + per-holding-NW + ayni-isaret | DK\|t\|>=2 AND boot-p<0.05 AND >=80% (5/6) pozitif |
| **G3 null** | per-holding circular-shift (AC-koruyan) iskonto-Z null | pctile >= 0.95 |
| **G4 rejim** | dusuk-enflasyon (<2017) vs yuksek-enflasyon (>=2022) FE-beta | her-ikisi pozitif |
| **G5 maliyet** | entry/exit-Z stratejisi, D-204 Roll+Kyle gercekci-maliyet | maliyet-sonrasi relatif > 0 AND breakeven >= 2x gerceklesen |

Kontroller: **carry-trap** (reel-TLREF 2.regresor; tuzak ancak iskonto-Z carry-kontrolunden-sonra
pozitif+DK-anlamli kalirsa REDDEDILIR), **LOHO** (tek-holding-dominasyon: herhangi-birini-cikar,
isaret-doner-mi/DK\|t\|<2-mi), **trap-1 detrend** (per-holding lineer-zaman detrend = sabit-pay-bias
TREND'i), **trap-5** (cross-holding residual-korelasyon: DK'nin N'e ne-kadar-dayandigi seffaf).

## 4. Sonuc -- VERDICT: **SERAP**

NAV-discount mean-reversion BIST-holding'lerinde cost-free GERCEK-SINYAL DEGIL. Eleme TEMIZ ve
beklentiyle (BELIRSIZ) tutarli. Kutlama YOK.

**Panel:** 6 holding, 936 holding-ay gozlem (iskonto-Z coverage: KCHOL/SAHOL/ALARK 180, BRYAT 179,
DOHOL 178, AGHOL 75 ay). FIDELITY-GUARD **GECTI** (medyan-corr 0.999, medyan-MAE 0.0155; 6/6 holding).

| Gate | Sonuc | Deger | PASS? |
|---|---|---|---|
| **G1** sinyal-icerik | FE-within-beta = **-0.0185** (isaret YANLIS -- MR-DEGIL, momentum-yonu) | sign_positive=False | **FAIL** |
| **G2** DK\|t\| | t = **-0.807** (lags=6) | <2 | **FAIL** |
| **G2** wild-boot | p = **0.4335** | >0.05 | **FAIL** |
| **G2** ayni-isaret | **2/6** pozitif (frac 0.333; sadece KCHOL+DOHOL) | <0.80 | **FAIL** |
| **G3** circular-shift-null | pctile = **0.27** (null_p95 beta=0.051; gercek -0.0185 solda) | <0.95 | **FAIL** |
| **G4** rejim | dusuk-enf +0.034 (t=2.07), yuksek-enf **-0.038** (t=-0.81) | her-ikisi-poz DEGIL | **FAIL** |
| **G5** maliyet | maliyet-sonrasi relatif **-0.78%/ay**, breakeven **0bp** << gerceklesen 397bp | <0 | **FAIL** |

**Cross-check'ler:** statsmodels DK (beta -0.0185, t -0.802) numpy-DK'yi (t -0.807) DOGRULAR.

**Kontroller:**
- **carry-trap (available, n=234):** reel-TLREF kontrolunden SONRA iskonto-Z beta +0.0487'ye doner
  ama DK\|t\|=**1.58 (<2, anlamsiz)** -> `trap_rejected_signal_survives=False`. Carry kontrolu
  isareti pozitife cevirse-bile anlamliliga ulastirmaz; sinyal carry-kontrolunden-sonra-da yok.
- **LOHO: robust=False** (`any_weak_dk_t`). Tek-tek cikarmada isaret DONMEZ (hep-negatif,
  max delta-beta 0.016) ama her-fit DK\|t\|<2 -> zaten-anlamsiz sinyal her-alt-kumede-de anlamsiz.
- **trap-1 detrend:** detrend-sonrasi beta -0.0198 (isaret stabil) -> sonuc detrend'e duyarli-degil.
- **trap-5:** cross-holding residual-korelasyon **0.562** (yuksek; tum-holdco BIST ile ko-hareket).
  DK\|t\| efektif-N'e dayanir; raporlanan -0.81 zaten anlamsiz, bu seffaflik notu yalniz-bilgi.

**Yorum.** Pooled within-beta NEGATIF (-0.0185): genis-iskonto bir-sonraki-6-ayda DAHA-DUSUK
getiri ile birlikte -- MR'nin TERSI (momentum/devamlilik yonu), istatistiksel-anlamliliktan UZAK
(DK\|t\| 0.81, boot-p 0.43, null-pctile 0.27). Per-holding bile dagilik: KCHOL +0.083, DOHOL +0.034
pozitif ama SAHOL/AGHOL/BRYAT/ALARK negatif -> 2/6 ayni-isaret. Rejim-ayrimi tek-tutarli-ipucu
(dusuk-enflasyon-doneminde +0.034 t=2.07) ama yuksek-enflasyonda tersine-doner (-0.038) -> ikna-edici
degil ve OOS-zayif (asagi). Sonuc: BIST-holding NAV-iskontosu olculen-pencerede MR-gostermyor.

## 5. Durustluk / OOS-uyarisi

- **N=6, bugun-var-olan holding = secilim (survivorship).** LOHO kismi-azaltir; cross-sectional
  genelleme IDDIA-EDILMEZ. Time-series-only.
- **2009-2026 ornek yuksek-enflasyonla domine** + tek-kisa-disinflasyon-epizodu -> gercek
  rejim-normalizasyon OOS'u ZAYIF. gate4-dusuk-enflasyon-koluna asiri-yuklenme YANLIS-olur.
- **Sabit-pay-bias + rights-issue-bias ACIK-beyan** (Stage-0). discount within-month-oran ->
  sinyal-bias-duyarsiz; trap-1 detrend trend-bias'i ele-alir (sonuc stabil).
- **carry-availability:** ilk-kosuda bir Period.to_timestamp() ay-basi/ay-sonu anahtar-uyusmazligi
  carry'yi `available=False` gosteriyordu; duzeltildi (ay-sonu lookup) -> simdi available, n=234.
  VERDICT degismez (diger-gate'ler kesin-FAIL).

## 6. Sonraki adim

NAV-discount ilk-turu (N<=3, 1/3) = **SERAP**. Sinyal-VARSA tam RR-013 mimarisi AYRI-O+Cagan-adimi
olacakti; sinyal-YOK -> mimari-adim TETIKLENMEZ. Temiz-arsiv, kesin-okuma. Beklenti (BELIRSIZ)
dogrulandi; kutlama-yok. NAV-discount 2./3. turu (farkli-tanim/horizon) O+Cagan-karari -- bu
oturumda yeni-tur ACILMAZ (grid-supurme YASAK, N<=3 kilidi).
