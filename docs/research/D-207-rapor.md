# D-207 realistic_cost RE-KALIBRASYON -- SISIK maliyet-modelini duzeltme (ADIM-3)

> Stage-0 on-kayit (EDGE-BLIND kalibrasyon): `docs/yol1/D207_CALIBRATION.json` (config_version
> d207-v1, FIDELITY-kontrolunden ONCE donduruldu; her D207_* sabiti GOZLENEN-gercege capali --
> EOD-kote-spread + clean_universe ADV-dagilimi -- HICBIR edge-ciktiya DEGIL). Edge-blind tier
> turetme: yerel kalibrasyon betiği. FIDELITY +
> microcap-kontrol: yerel fidelity-doğrulama betiği. Duzeltilen
> kod: `src/screening/realistic_cost.py` (FIX-1 + FIX-3), yeni `src/screening/quoted_spread.py`
> (kote-spread loader), `src/screening/d204_hi52_stress.py::per_stock_cost_panel` (FIX-2 enjeksiyon).
> Karar esikleri: `src/signals/thresholds.py` (D207_* blok, tek-kaynak). D204_* blok TARIHSEL-kayit
> olarak KORUNUR.
>
> **Bu bir KALIBRASYONDUR, optimizasyon DEGILDIR.** SISIK-model GOZLENEN-gercege (EOD-kote ~11bp)
> capalanir; "maliyeti-dusur-ki-edge-ciksin" = post-hoc = YASAK. **HARD KISIT:** D-204/D-205
> raporlari + STAGE0/results JSON'lari TARIHSEL-kayittir, DOKUNULMAZ. Duzeltilmis maliyetle motor-
> yeniden-kosumu (ADIM-1: D-205-replica / H2b / PA-overnight) AYRI-gelecek-spec, kapsam-DISI;
> D-204/D-205 hukmunu BOZMAZ.

## 1. Soru / motivasyon

NRR-010 (`edge-arastirma/NRR-010-maliyet-teshis.md`) paylasilan maliyet-modelini
(`src/screening/realistic_cost.py`) 6 bagimsiz kanitla **SISIK (likit-isimlerde ~12-25x sismis)**
teshis etti. Iki kok-neden:

1. **Birim cift-sayim (matematik-hatasi):** `combine_round_trip`, `round_trip = 2*(S + impact)`
   hesapliyordu (S = TAM Roll-spread). Oysa round-trip spread-maliyeti = S'nin KENDISI (giriste
   ask'ta S/2 + cikista bid'de S/2). Spread-baciagi ikiye-katlanmis; tier-baciagi zaten DOGRUydu.
2. **21-gun Roll = volatilite-metresi, spread-metresi DEGIL:** Monte-Carlo, gercek-spread SIFIR-iken
   bile roll21 ~ 0.47*sigma gosterdi (`max(-cov,0)` truncation'i sigma-orantili yukari-yanli).
   Dogrudan EOD-kote-spread'ler (arsiv BEKLEYEN EN IYI ALIS/SATIS) likit-megalarin ~11bp TAM-spread
   ile islem gordugunu gosteriyor (RR-015 ortak: ~17-25bp round-trip), modelin 271-509bp'sine karsi.

## 2. Uc duzeltme (FIX-1/2/3)

- **FIX-1 (birim cift-sayim):** `combine_round_trip` artik HER spread-kaynagi BIR-YONLU YARI-spread
  katkisi verir, round-trip icin ikiye-katlanir (zaten-dogru tier-konvansiyonuyla eslesir):
  `one_way = kote_tam/2 | roll_tam/2 | tier_yari`; `round_trip = 2*(one_way + impact) + komisyon`.
  Geriye-uyumluluk: `round_trip_roll` / `round_trip_tier` / `roll_is_zero` / `kyle_impact` anahtarlari
  KORUNUR (d205/nrr007/nrr008/d206 cagiranlarina ripple-YOK); YENI `quoted_spread` + `spread_source`
  muhasebe-etiketleri eklendi.
- **FIX-2 (kote-birincil spread, vol-dayanikli):** kaynak-hiyerarsisi her (tarih,isim):
  **EOD-kote** (gozlenen, vol-dayanikli) -> **uzun-pencere Roll** (252-gun, 21d'ye gore de-sismis) ->
  **yeniden-olcekli tier-tabani** (ADV-only son-care). Yeni `src/screening/quoted_spread.py` arsivden
  trailing-medyan (ask-bid)/mid panelini kurar (oransal-spread corp-action-AYAR-degismez -> ham
  bid/ask, adj_factor-join-YOK). Panel **ENJEKTE** edilir (CI-guvenli: testler sentetik-panel/None
  enjekte eder; arsiv-bagimliligi CI'a girmez). Kyle-impact sigma-penceresi 21-gun KALIR (impact
  DONUK, D-207-kapsam-disi). Durust-uyari: fallback-Roll hala artik vol-yanli tasir -- yalniz
  kote-YOK isimleri etkiler (or. 2019-Q1 / ince).
- **FIX-3 (tier-tabani yeniden-olcekleme):** D204_TIER_* merdiveni CIFT-yanlisti: (a) ADV-sinirlari
  (MEGA>=2e9 TL) BIST'te ULASILMAZ -> her isim MID/MICRO yanlis-siniflaniyordu, (b) yari-spread'ler
  ~4-6x sismis. D-207 merdiveni EDGE-BLIND yeniden-turetti: clean_universe ADV-dagilimina gore
  bucket'lanan GOZLENEN-kote-spread'lerden (`derive_d207_tiers.py`). Sinirlar yuvarlak-BIST-gercegi
  kesim-noktalari (edge-gormeden); yari-spread = bucket-medyan-kote-TAM-spread / 2, monoton-zorunlu.

**KILIT GOZLEM:** EOD-kote TAM-spread tum-BIST-likidite-spektrumunda ~DUZ ~11bp (bucket-medyanlari
MEGA 10.6 / LARGE 13.4 / MID 11.2 / MICRO 11.2 bp; n=439). Microcap'ler KOTE-spread boyutunda DAHA-
GENIS DEGIL -- ekstra maliyetleri piyasa-ETKISI (Kyle, ADV-kuculdukce buyur), spread DEGIL. Bu
yuzden yeniden-olcekli merdiven tasarim-geregi neredeyse-duz (gercegin sadik-yansimasi, dik-micro-
cezasi DEGIL); monoton-gradyan no-data-fallback icin kucuk-muhafazakar-esitlik-bozucu, gozlenen
[10.6,13.4]bp envelope-icinde. D-204 kok-nedenini suren microcap MALIYET-ORANI gecerli kalir --
DEGISMEMIS Kyle-impact teriminden akar.

### Donmus sabitler (thresholds.py D207_* -- tek-kaynak)

| Sabit | Deger | Not |
|-------|-------|-----|
| D207_QUOTED_WINDOW | 63 | kote-medyan trailing trading-gun penceresi |
| D207_QUOTED_MIN_COVERAGE | 21 | penceredeki min gecerli kote-gun (yoksa "kote-yok") |
| D207_FALLBACK_ROLL_WINDOW | 252 | fallback Roll uzun-pencere (de-sismis) |
| D207_TIER_MEGA/LARGE/MID_ADV_TL | 5e7 / 2e7 / 5e6 | ulasilabilir BIST ADV-sinirlari |
| D207_TIER_*_HALF_SPREAD (MEGA..MICRO) | 5.28 / 6.72 / 6.82 / 6.92 bp | gozlenen bucket-medyan/2, monoton |
| D207_FIDELITY_BAND_LO/HI_BPS | 7 / 35 | DIS-capali dogrulama-bandi |

Ham bucket-yarilari 5.28 / 6.72 / 5.59 / 5.59 bp (LARGE'in 13.4bp medyani ~11bp-geri-kalana gore
gurultu-yuksek); strict-monoton-zorlama MID/MICRO'yu LARGE'in az-ustune raptlar -> 6.82 / 6.92bp.
Tier-tabani SON-CARE (likit-isimler kote-alir), bu yuzden tam-deger likit-sonucu neredeyse-hic
oynatmaz; yalniz no-data-microcap-anlatisini sekillendirir.

## 3. FIDELITY + MICROCAP-KONTROL (kalibrasyonun-gercege-capali-kaldiginin kaniti)

Fidelity-doğrulama betiği DUZELTILMIS fonksiyonu (`round_trip_cost`, kote-enjekte) gercek
clean_universe fiyatlari uzerinde kosar (re-turetme DEGIL).

**FIDELITY = GECTI (8/8 mega bantta).** Adi-likit-megalarda duzeltilmis round-trip [7,35]bp banda
oturdu (SISIK-model 271-509bp idi):

| Isim | kote_tam (bp) | impact_1yon (bp) | duzeltilmis_RT (bp) | kaynak | bantta |
|------|--------------:|-----------------:|--------------------:|--------|:------:|
| TTKOM | 10.2 | 7.7 | 25.6 | quoted | EVET |
| KCHOL | 6.7 | 8.1 | 22.9 | quoted | EVET |
| GARAN | 8.7 | 4.7 | 18.1 | quoted | EVET |
| AKBNK | 10.6 | 4.5 | 19.5 | quoted | EVET |
| ISCTR | 11.3 | 2.5 | 16.4 | quoted | EVET |
| THYAO | 7.9 | 4.6 | 17.0 | quoted | EVET |
| SAHOL | 8.5 | 6.5 | 21.5 | quoted | EVET |
| EREGL | 7.1 | 5.9 | 18.8 | quoted | EVET |

Band [7,35]bp DIS-capali: NRR-010 EOD-kote (~7.5-13.7bp TAM) + RR-015 round-trip (17-25bp);
turetmenin-kendi-ciktisi DEGIL (dairesellik-onlendi). Duzeltilmis RT-araligi 16.4-25.6bp, banda
oturur.

**MICROCAP-KONTROL (durust):** en-dusuk-ADV kote-bulunabilir 12 isimde gozlenen-kote-medyan
**11.7bp** (megalarla ~ayni-DUZ) AMA duzeltilmis-RT-medyan **104.5bp** -- fark TAMAMEN Kyle-IMPACT'tan
(microcap'lerde 31-71bp/yon, ~1M-TL-ADV'de 20K-emirle). Bu GERCEK (impact-suruculu), model-kusuru
DEGIL: model microcap'te de SADIK (sismis-DEGIL), ve **D-204 microcap-eleme kok-nedeni GECERLI
KALIR.** Microcap-kote-spread mega-kadar-ucuzdur; microcap'i pahali-yapan spread DEGIL impact'tir.

## 4. Etki / ne-degisti

- Paylasilan maliyet-modeli artik GERCEGE-SADIK: likit-megalar ~16-26bp round-trip (onceki SISIK
  271-509bp; ~12-20x de-sisme), microcap'ler impact-yoluyla hala-pahali (~100bp+, gercek).
- Cagiran motorlar (d205/nrr007/nrr008/d206) opsiyonel-kwarg-imzasiyla degismeden-calisir; kote-
  enjeksiyon-YOK-yolu (quoted_panel=None) uzun-Roll-fallback -> tier'i kullanir (FIX-1 yari-spread +
  FIX-3 yeniden-olcekli-tier duzeltmeleri yine-uygulanir). Davranis-degisimi paylasilan-modeli-
  duzeltmenin SONUCU; o dosyalar MODIFIYE-EDILMEDI (in-place-fix felsefesi).
- Tum hedefli + mimari + downstream-motor testleri YESIL; tam-regresyon SIFIR-regresyon.

## 5. Disiplin / kapsam

- Tum D207_* sabiti FIDELITY-kontrolunden ONCE `D207_CALIBRATION.json`'a donduruldu; post-hoc-
  gevsetme YASAK. FIDELITY = kalibrasyon-GECERLILIK kriteri (model ~11bp/17-25bp gercek-degeri
  yeniden-uretir-mi), edge-kriteri DEGIL. Mega-bant-disi-kalsa "FIX-hatali-demektir" idi (edge-cikti-
  diye-sevinmek-DEGIL); 8/8 oturdu.
- **D-204/D-205 raporlari + STAGE0/results JSON'lari DOKUNULMADI** (tarihsel-hukum-kaydi). Naive-
  prototip tradeable-DEGIL kalir (dogru).
- **Kapsam-disi (acik):** ADIM-1 re-test (duzeltilmis maliyetle D-205-replica/H2b/PA-overnight
  yeniden-kosumu) AYRI-gelecek-spec, KENDI yeni-kaydi; D-204/D-205'i USTUNE-YAZMAZ. Kyle-impact
  DONUK (lambda=1.0), D-207-kapsam-disi -- D-207 yalniz SPREAD-baciagi + tier-tabanini duzeltir.

## 6. HUKUM

**SISIK maliyet-modeli DUZELTILDI ve GERCEGE-CAPALANDI.** FIDELITY GECTI (8/8 mega [7,35]bp banta,
16-26bp; eski 271-509bp). MICROCAP-KONTROL durust: kote-spread ~duz ~11.7bp, round-trip impact-
yoluyla yuksek (~104bp) -- model sadik, microcap-eleme kok-nedeni gecerli. Kalibrasyon GOZLENEN-
gercege capali kaldi (edge-ciktiya DEGIL). Paylasilan maliyet-mekanigi artik dogru; bunun uzerine
kurulu gelecek-is (ADIM-1) sadik-maliyetle kosar.
