# NRR-008 ASAMA-1 -- VALUE-REJIM-KOLU: rejim-degiskeni GEREKCELI-onerisi (edge-OLCULMEDI)

> **Bu dosya ASAMA-1 ciktisidir.** arastirma katmani 3-aday rejim-degiskenini EKONOMIK/LITERATUR
> gerekceyle onerir. **EDGE HIC-OLCULMEDI** (bu asamada hicbir geri-getiri/t-istat/gate
> hesaplanmadi). Amac: maintainer'nun TEK-degisken + esik onaylamasi -> sonra Stage-0 DONAR ->
> ASAMA-2 tam-test. Grid-supurme (3-degisken-deneyip-en-iyiyi-secmek) = p-hacking = YASAK;
> bu yuzden secim edge-GORMEDEN, yalniz gerekce-temelinde yapilir.
>
> **Baglam:** value-statik iki kez olculdu -- D-203 = **SERAP** (Gate-2 t=0.76, illikit-yogun)
> ve D-Y1-001 = **KIRILGAN/REJIM-BAGIMLI** (P/B mekanik-PASS ama E/P celisik + OOS-cokus +
> disinflasyon-primi-yok). Test-EDILMEMIS tek-kol: "value-tilt yalniz uygun-makro-rejimde aktif".
> **NRR-008 = value'nun 3. ve SON turu (N<=3). Dorduncu-YOK.**

## 1. Neden rejim-kolu? (literatur + onceki-bulgular)

RR-Y1 tezi: **BIST-value makro-rejim-bagimli** (yayin-rekabeti-decay'i DEGIL). Kanitlar:
- **Aras/Cam ve ark. (2018):** 2005-2017 value-faktoru NEGATIF (aylik HML = -%1.09, t = -2.90)
  -- ters-prim, istatistiksel-anlamli.
- **Eraslan (2013):** value-etkisi var ama zayif ve "kalici-degil" (HML ~ +%0.50/ay).
- **Molla Ahmetoglu / Dogan:** value post-2013 anlamsizlasiyor, momentum tarafindan ikame.
- **Jacobs & Muller (2020):** yayin-sonrasi-decay BIST'te gozlenmiyor -> value-zayifligi
  rekabet-kaynakli-degil, **makro-rejim-kaynakli**.

D-Y1-001 (3-way INFLATION_REGIMES split) bunu dogruladi:
- **pre_surge (2019-01..2021-09):** value P/B +%26 (CI sifiri-disliyor, GUCLU).
- **high_inflation (2021-10..2024-06):** P/B +%18 (pozitif ama CI sifiri-iciyor).
- **disinflation (2024-07..2026-04):** P/B +%2.1 (sifira-yakin), E/P **-%2.1** (NEGATIF) -> **cokus**.

**Cikarim:** value-primi disinflasyon-rejiminde tasimiyor. Test-edilecek kol: **value-tilt'i
yalniz uygun-rejimde (yuksek/yukselen-enflasyon) AC, disinflasyonda KAPAT** -> kirilganlik
giderilir mi? (Honest beklenti BELIRSIZ: statik-value zaten SERAP/kirilgandi; rejim-gating
otherwise-fragile-value'yu kurtarabilir veya disinflasyon-kapatmak-bile yetmeyebilir.)

## 2. Look-ahead-safe ilkesi (her aday icin ZORUNLU)

Rebal-ayi t'de rejim-etiketi **yalniz t-veya-oncesi makro-veriyle** belirlenir; gelecek-bilgi
sizmasi YASAK. **Onemli ayrim:** D-Y1'in kullandigi 3-way takvim (INFLATION_REGIMES,
`trend_config.py:148-152`) sinirlari **gecmise-bakarak cizildi** -- bir *tradeable kural* icin
look-ahead-DEGIL. Bu yuzden adaylar takvim-etiketi DEGIL, **trailing-veriden-canli-hesaplanan**
kurallardir (yayin-lag >= 1 ay, `value_factor_panel`'in lag-deseniyle ayni).

## 3. Aday rejim-degiskenleri (3 aday; edge-olculmedi)

### Aday-A (ONERILEN) -- Enflasyon-yonu (trailing-TUFE, look-ahead-safe)

| ozellik | tanim |
|---|---|
| **Ekonomik gerekce** | En-dogrudan BIST-ozel-kanit: D-Y1 value pre_surge+%26 / high_infl+%18 / **disinflasyon-cokus**; RR-Y1 enflasyon-rejim-tezi. Hipotez: value-tilt yuksek/yukselen-enflasyonda ACIK, disinflasyonda KAPALI. |
| **Look-ahead-safe tanim** | Rebal-ayi t'de, yalniz **t-1-ay-veya-oncesi** TUFE ile trailing-12ay YoY-enflasyon (yayin-lag >= 1 ay). Rejim "uygun" = YoY-enflasyon esik-USTU; "uygun-degil" = esik-ALTI (disinflasyon). |
| **Esik (gerekce-temelli)** | TCMB-hedef-bandi / yapisal-seviye gerekcesiyle YoY ~ **%25-35** araligi. Kesin-sayi bu-asamada DONMAZ -- maintainer-onayinda donar. Sonuc-temelli-secim YASAK. |
| **Veri** | `data/snapshots/exposure_d187_tufe.parquet` (TAM 2019-2026, gunluk TUFE index; TP.FG.J0). |
| **Ornek yeterligi** | **YETERLI** -- gate-3 cross-regime icin her-iki-alt-donem (uygun/uygun-degil) dolu; rejim-degisimi ornek-icinde gerceklesiyor. |
| **Look-ahead** | Gercekten-safe: trailing-TUFE canli-hesaplanabilir; takvim-sinirina bagli-degil. |

### Aday-B -- Reel-faiz-yonu (TLREF-real) [VERI-KISITLI]

| ozellik | tanim |
|---|---|
| **Ekonomik gerekce** | En-temiz iskonto-orani-kanali: value (uzun-defter/kazanc-getirisi) reel-faiz dusuk/dususte favori, yuksek/yukseliste zararli. D-187: disinflasyonda TLREF-real hakim, equity-reel KAYBETTI (-%5.7). |
| **Look-ahead-safe tanim** | Ay-sonu t'de TLREF-return TUFE-ile-deflate -> reel-faiz; rejim "uygun" reel-faiz esik-ALTI/dususte. |
| **Esik** | Ex-ante reel-faiz seviyesi (gerekce-temelli). |
| **Veri** | `data/snapshots/exposure_d187_tlref.parquet`. |
| **CIDDI-KISIT (durust)** | TLREF snapshot'i **2022-07'de basliyor** (~46 ay) -- **pre_surge'i TAMAMEN kaciriyor**. gate-3 cross-regime (her-iki-alt-donem dolu) icin **ornek-YETERSIZ**. Bu Aday-B'yi pratikte ELER. |

### Aday-C -- TL-kur-stresi (USDTRY realize-vol) [TAM-ORNEK, DOLAYLI]

| ozellik | tanim |
|---|---|
| **Ekonomik gerekce** | RR-Y1 "tekrarlayan-kur-krizleri"ni value-zayifligi-surucusu sayar; value-tuzak-riski TL-stresinde en-yuksek. Hipotez: kur-stresinde tilt-KAPALI (tuzak), sakinde ACIK. |
| **Look-ahead-safe tanim** | Ay-sonu t'de trailing-Ng USDTRY log-getiri realize-vol; rejim "stres" = vol esik-USTU -> tilt-KAPALI; "sakin" -> ACIK. |
| **Esik** | Ex-ante yillik-vol seviyesi (gerekce-temelli). |
| **Veri** | `data/snapshots/k2_fx_usdtry.parquet` (veya `faz0b_fx_usdtry.parquet`); TAM 2019-2026. |
| **Not** | Dolayli: global-USD-hareketi de vol-yaratir; value-baglantisi risk-primi-uzerinden, fundamental-degil. Tam-ornek avantaji var. |

## 4. arastirma katmani-onerisi: **Aday-A (enflasyon-yonu)**

Gerekce (hepsi EKONOMIK/VERI-temelli, edge-temelli DEGIL):
1. **En-dogrudan BIST-ozel-prior:** D-Y1'in disinflasyon-cokus bulgusu + RR-Y1 enflasyon-rejim-tezi
   tam-da bu degiskeni isaret-ediyor.
2. **TAM-ornek:** gate-3 cross-regime feasible (Aday-B bu nedenle ELENIR).
3. **Gercekten look-ahead-safe-trailing-kural:** D-Y1'in ex-post-takviminin canli-tradeable
   versiyonu.
4. **Tek-temiz-esik** ex-ante-ekonomik-gerekceyle (TCMB-hedef / yapisal-enflasyon-seviyesi).

**Aday-B** ornek-uzunlugundan ELENIR (durustce flag'lendi). **Aday-C** maintainer FX-stres-cercevesi
tercih-ederse alternatif (tam-ornek ama dolayli).

> **KRITIK disiplin-notu:** Bu oneri edge-OLCULMEDEN, yalniz gerekce-temelinde yapildi.
> Adaylar-arasinda edge'e-gore-secim = p-hacking = YASAK. maintainer TEK-degisken + esik onaylayinca
> Stage-0 DONAR ve ASAMA-2 tam-test (value-tanim D-203-BIREBIR, rejim-maskeli, 5-gate
> `run_gates_on_score` replica MATCH=True, gate5-gercekci, 3-yollu+maliyet-eki verdict) baslar.

## 5. ONAYLANDI (maintainer, 2026-06-03) -- Aday-A, YON-tanimi

maintainer **Aday-A'yi YON-tanimiyla** onayladi (seviye-esigi DEGIL):

- **Rejim-sinyali:** trailing-12ay-YoY-TUFE'nin **6-ay-onceye gore yonu**, **t-1-lag** (look-ahead-safe).
- **KAPALI (disinflasyon/dusus):** `YoY(M-1) < YoY(M-7)` -> value-tilt KAPALI -> EW_FULL-notr
  (o ay EW_FULL-relatif-fazla = 0).
- **ACIK (sabit/yukselis):** `YoY(M-1) >= YoY(M-7)` -> value-tilt ACIK -> D-203 value top-15.
- **6-ay-pencere DONUK** (gerekce: yon-trendini gurultusuz-yakalama; 3/6/12-supurme YASAK).
- **Esik-degil-YON:** enflasyon-seviye-esigi YOK, yalniz 6-ay-degisimin isareti. Tek-tanim,
  post-hoc-yok. Gerekce D-Y1-prior + iskonto-mantigi -- edge-sonucundan-DEGIL (edge hic-olculmedi).

Bu karar **`docs/yol1/STAGE0_nrr008.json`'a sonuc-gormeden DONDURULDU** (2026-06-03).
**ASAMA-2** (value D-203-birebir, rejim-maskeli 5-gate `run_gates_on_score` replica MATCH=True,
gate5-gercekci, 3-yollu+maliyet-eki verdict) **#176 (NRR-007) merge-sonrasi** yurutulecek.
