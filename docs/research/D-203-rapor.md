# D-203 KESIN-TEST -- value + EDGE-2 + 52wk-high, D-202 temiz-evren (681 sembol)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d203.json` (config_version d203-v1, sonuclardan
> ONCE donduruldu). Ham sonuc: `docs/yol1/d203_results.json`. Motor:
> `src/screening/d203_clean_universe_test.py`. Olcum geometrisi: `src/screening/d203_config.py`.
> Karar esikleri: `src/signals/thresholds.py` (D203_* blok, tek-kaynak).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N<=3 aday; agirlik/fraksiyon taramasi YOK.
> Verdict bir overlay ADAYI'dir en fazla; deployment karari ayri (the project).

## 1. Cozulen celiski

Iki kesif labi (her ikisi de junction'li, commit'siz; local build-homed) AYNI uc adayda
ZIT sonuca varmisti:

- **demo-edge** (88 survivor, 30 test): VALUE bir survivorship/small-cap SERAP'i;
  hicbir faktor random-null'i gecmiyor; tradeability gate'lerini gecen TEK sinyal
  52wk-high momentum AMA o da 2022-26 REJIM-TILT'i, regime-invariant alpha degil.
- **demo_smart_money**: EDGE-2 COMPOSITE (mom120+hi52+lowvol63, aylik top-15 EW) EN GUCLU
  edge; EDGE-6 "full evrende EW ustu +12.9pp'ye GENISLIYOR, survivorship-teyitli" iddiasi.

**KRITIK:** EDGE-6 BOZUK D-200 evrenini kullandi (392 isim, 291 yanlis dislanmis,
rights/TERP duzeltilmemis, getiriler +/-50% clip) -> +12.9pp iddiasi GECERSIZ. D-203 her
uc adayi da DUZELTILMIS D-202 temiz-evrende (681 sembol x 1848 gun, fiyat hash
`fd207550...`, mode yol-3-hybrid, +/-10% clip) AYNI 5-gate metodolojisiyle yeniden olctu.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren:** D-202 junction'li tek-kaynak fiyat paneli (681 sembol, delisted-dahil ->
  survivorship-CLEAN). Fundamentals: D-203 FAZ-0 evrensel freeze (degoran arsivi, hash
  `d72a6977...`, 677/681 kapsam). TUFE: D-187 donmus gunluk endeks.
- **Benchmark:** EW_FULL = tum uygun evrenin aylik esit-agirlik getirisi, delisted-dahil
  (durust bar; lab'larin survivor-only snapshot'larindan farkli).
- **Rebalance:** aylik (her ayin son islem gunu) -> demo_smart_money EDGE-2 kadansiyla esles.
- **Secim:** sabit top-15 EW (fraksiyon taramasi YOK); long-short = top15 - bottom15.
- **Getiri:** TL-real (TUFE-deflate), gunluk +/-10% clip, ay-ici buy-and-hold bilesik.
- **Maliyet:** flat 20bp VE 100bp / turnover (ilk giris tam round-trip).

### Pencere farki (the maintainer duzeltme-2 -- aciklikla belirtiliyor)
- **PRIMER ortak pencere 2019-07-01..2026-04-30** (degoran+TUFE ortak kapsam): UC adayin
  da apples-to-apples kiyaslandigi pencere. ADAY-A VALUE fundamentals'a bagli oldugu icin
  SADECE bu pencerede raporlanir.
- **EXTENDED pencere 2019-01-01..2026-04-30** (fiyat-only): ADAY-B ve ADAY-C EK olarak bu
  daha uzun pencerede de raporlanir. Iki pencere arasinda verdict DEGISMEDI (asagida).

### Rejim-split (the maintainer duzeltme-1 -- ikisi de raporlaniyor)
- **PRIMER 2022-01-01** (Gate-3'u KARARLASTIRIR): takvim-yili siniri, spec dili
  "2019-21 vs 2022-26" ile eslesir; TR enflasyon rejimi 2021 sonu->2022'de hizlandi (keyfi degil).
- **SEKONDER 2022-07-01** (robustness, raporlanir): demo-edge/demo_smart_money surekliligi +
  TLREF-carry verisinin basladigi tarih. Periyot START tarihine gore bir tarafa atanir.

## 3. Aday bazinda verdict

### ADAY-A VALUE-ONLY (bm=1/PBV primer, ey=E/P robustness) -> **SERAP**
*(ortak pencere 2019-07+, 81 periyot)*

| Olcu | Deger |
|------|-------|
| long real (aylik) | +2.63% |
| EW_FULL-relatif | +0.53%/ay (CI sifiri ICERIR) |
| long-short | +0.78%/ay (CI sifiri ICERIR) |
| Gate-1 selection-null | PASS (pctile 0.964) |
| Gate-2 Newey-West \|t\| | **FAIL (0.76 < 2.0)** |
| Gate-3 cross-regime | primer pre +0.10% / post +0.78% (ikisi de +) |
| Gate-4 likidite | likit-relatif +0.05%/ay vs illikit +1.36%/ay |
| Gate-5 after-cost | PASS (+0.50%@20bp, +0.36%@100bp) |

**E/P robustness legi de SERAP:** rel +0.59%/ay, Gate-2 t=1.06 (FAIL), long-short +0.13%/ay.

**Yorum:** VALUE nominal pozitif AMA istatistiksel olarak ANLAMSIZ (HAC |t| << 2) ve edge
neredeyse tamamen ILLIKIT tercilde yogunlasmis (likit-relatif ~0). Bu, "tradeable bir
deger primi" degil; kucuk/illikit isimlerde yasayan bir gurultu. Long-short spread'i de
sifiri iciyor -> kesitsel ucu-uca ayristirma yok. **demo-edge'i DOGRULAR:** VALUE bir
survivorship/small-cap serabidir, regime-invariant alpha degil.

### ADAY-B EDGE-2 COMPOSITE (mom120+hi52+lowvol63, esit-agirlik rank-avg) -> **GERCEK-EDGE**
*(ortak + extended pencere, ikisinde de ayni verdict)*

| Olcu | ortak (2019-07+) | extended (2019-01+) |
|------|------------------|---------------------|
| long real (aylik) | +3.14% | +3.17% |
| EW_FULL-relatif | +1.31%/ay (CI>0) | +1.31%/ay (CI>0) |
| long-short | +3.08%/ay (CI>0) | +3.09%/ay (CI>0) |
| Gate-1 null | PASS (0.999) | PASS (1.000) |
| Gate-2 \|t\| | PASS (2.29) | PASS (2.33) |
| Gate-3 primer (2022-01) | pre +1.71% / post +1.07% | pre +1.70% / post +1.07% |
| Gate-3 sekonder (2022-07) | pre +2.00% / post +0.75% | pre +1.99% / post +0.75% |
| Gate-4 likidite | likit +0.54% / illikit +1.83% | likit +0.54% / illikit +1.84% |
| Gate-5 after-cost | +1.21%@20bp, +0.82%@100bp | +1.21%@20bp, +0.82%@100bp |

**Yorum:** 5 gate'in HEPSI gecti, iki rejim de pozitif -> GERCEK-EDGE. AMA edge post-2022'de
GUCLENMIYOR, ZAYIFLIYOR (primer: +1.71% -> +1.07%; sekonder: +2.00% -> +0.75%).
**demo_smart_money'nin EDGE-6 "+12.9pp'ye genisliyor" iddiasi DOGRULANMADI** -- o buyukluk
bozuk D-200 artefaktiydi (yanlis evren + +/-50% clip). Temiz evrende edge gercek ve
rejim-dayanikli, fakat genisleyen degil daralan bir egilimde.

### ADAY-C 52WK-HIGH ISOLATED (George-Hwang proximity) -> **GERCEK-EDGE (en guclu)**
*(ortak + extended pencere, ikisinde de ayni verdict)*

| Olcu | ortak (2019-07+) | extended (2019-01+) |
|------|------------------|---------------------|
| long real (aylik) | +4.57% | +4.23% |
| EW_FULL-relatif | +2.57%/ay (CI>0) | +2.35%/ay (CI>0) |
| long-short | +5.15%/ay (CI>0) | +4.78%/ay (CI>0) |
| Gate-1 null | PASS (1.000) | PASS (1.000) |
| Gate-2 \|t\| | PASS (3.19) | PASS (3.00) |
| Gate-3 primer (2022-01) | pre +2.39% / post +2.67% | pre +1.89% / post +2.67% |
| Gate-3 sekonder (2022-07) | pre +3.07% / post +2.16% | pre +2.55% / post +2.16% |
| Gate-4 likidite | likit +1.35% / illikit +1.77% | likit +1.19% / illikit +1.70% |
| Gate-5 after-cost | +2.40%@20bp, +1.72%@100bp | +2.17%@20bp, +1.49%@100bp |

**Yorum:** Uc adayin EN GUCLUSU (en yuksek |t|, en yuksek long-short, en YAKIN likit/illikit
orani = en tradeable). Primer split'te post-2022 pre-2022'den DAHA GUCLU (+2.67% > +2.39%)
-> rejim-tilt DEGIL, rejim-dayanikli. **demo-edge'in "52wk-high yalnizca 2022-26 rejim-tilti"
sonucu temiz evrende CURUDU.** Lab'in bu yanlis sonucu muhtemelen survivor-only 88-isim
snapshot'inin daralmasindan (kucuk orneklem + survivorship) kaynaklandi.

## 4. Celiski cozumu -- net hukum

| Lab iddiasi | D-203 temiz-evren hukmu |
|-------------|-------------------------|
| demo-edge: VALUE = serap | **DOGRU** (Gate-2 fail, illikit-yogun, long-short ~0) |
| demo-edge: 52wk-high = rejim-tilt | **YANLIS** (rejim-dayanikli, post>=pre, en guclu aday) |
| demo_smart_money: EDGE-2 gercek/en guclu | **KISMEN** (gercek+dayanikli AMA en guclu C, B degil) |
| demo_smart_money: EDGE-6 +12.9pp genisliyor | **YANLIS** (D-200 artefakti; edge post-2022 DARALIYOR) |

**hi52 ~ kompoziti tek basina karsiliyor/asiyor** (long-short 5.15% vs 3.08%; |t| 3.19 vs
2.29) -> EDGE-2 kompozitinin BASKIN bileseni 52wk-high'dir; mom120+lowvol63 eklenmesi edge'i
SEYRELTIYOR. Bu, "kompozit en guclu" sezgisinin aksidir.

## 5. Onemli caveat'lar (deployment karari icin)

1. **EW_FULL zayif bir bar.** Buyuk EW_FULL-relatif sayilari kismen benchmark'in
   zayifligini yansitir (full evren yuzlerce illikit mikro-cap icerir). DURUST tradeable
   rakam LIKIT-TERCIL excess'idir: edge2 ~+0.54%/ay, hi52 ~+1.35%/ay. Bunlar hala pozitif
   ama EW_FULL-relatiften cok daha kucuk.
2. **Sadece olcum, deployment degil.** GERCEK-EDGE verdict'i bile bir overlay ADAYI'dir;
   canliya alma ayri bir the project karari.
3. **Maliyet modeli flat 20/100bp** -- broker-tier degil. Gercek BIST mikroyapi-maliyeti
   ve slippage (RR-014/015) ayrica modellenmeli.
4. **Optimizasyon yapilmadi.** Sabit top-15, esit-agirlik. Fraksiyon/agirlik taramasi edge'i
   sismdirabilir -> bilincli olarak YAPILMADI (data-snooping kacinma).

## 6. Cikti dosyalari
- `docs/yol1/STAGE0_d203.json` -- on-kayit (sonuclardan once donmus).
- `docs/yol1/d203_results.json` -- aday x pencere -> 5 gate + iki rejim-split + verdict.
- `docs/research/D-203-rapor.md` -- bu rapor.
