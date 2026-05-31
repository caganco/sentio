# D-185 Trend-Motor Test -- Sonuc Raporu

**Tarih:** 31 May 2026
**Tur:** Olcum programi (Stage 0 on-kayitli) + adversarial dogrulama
**Dayanak:** RR-039 §6 (kural varyantlari), RR-038 (modern BIST rejim + maliyet modeli),
ARCHITECTURE v2.0 §3/§7.1, DEC-039
**Stage 0 on-kayit:** `docs/trend_test/STAGE0_trend_motor_preregistration.json` (commit bb90927, kod/sonuc ONCESI)
**Ham sonuc:** `docs/trend_test/trend_test_results.json`
**Veri:** frozen OHLCV snapshot `trend_v1_ohlcv_2019-01-01_2026-04-30` (content_hash `d1423f89`), 88 survivors-only ticker, XU100 1908 gozlem

---

## 1. TL;DR -- NIHAI VERDICT: PROMISING ama INCONCLUSIVE (Katman A insasi YOK)

3 varyant (A=S/R-flip retest, B=konsolidasyon-kirilim, C=Donchian+retest) × parabolik-filtre
on/off × 3 maliyet senaryosu = **18 hucre**. On-kayitli gate'e gore:

- **HICBIR varyant gate'i GECMEDI** -- hepsi YALNIZCA `max_dd_exceeded` ile takildi.
- **AMA bu tek basarisizlik bir OLCUM ARTEFAKTI** (adversarial denetim: `confirmed_artifact`,
  blocker). `max_dd` metrigi tam-sermaye ardisik bilesik (cumprod) ile hesaplandigi icin
  `total_net_return ~1e+26`, `max_dd ~0.99` deterministik cikar; ~500+ trade'li HER pozitif
  strateji bunu patlatir. **Gercek risk sinyali ICERMIYOR.**
- Look-ahead denetimi **TEMIZ** (`refuted`, 7 vektorun tamami): expectancy bir gelecek-sizdirma
  artefakti DEGIL. Kod guvenli.
- Per-trade expectancy TUM hucrelerde **pozitif** (0.72-1.34 R), HAC t 5.0-7.3, random
  benchmark'i ≥%99.7 dilimde yener, 3/3 piyasa rejiminde pozitif.

**Ama 3 MAJOR caveat bir "PASS" ilan etmeyi engelliyor (adversarial denetim):**
1. **Nominal-drift kontaminasyonu** (`partially_real`, major): 2019-2026 hiperenflasyon;
   esit-agirlik B&H = **+%2276 nominal**, random giris zaten +%5.7-8.2/trade kazaniyor.
   Getirinin ~%64'u TL suruklenmesi; temiz sinyal yalniz random-ustu **~+3pp/trade** ve O da
   yuksek-enflasyon bogasinda yogunlasiyor. Disinflasyon (2024-07+) diliminde edge marjinal.
2. **Random-null asimetrisi** (`refuted`, major): strateji stop+trailing ile cikiyor, random
   sabit-sure stop-suz tutuyor. +3pp edge buyuk olcude CIKIS-MEKANIZMASI (stop'un kaybedenleri
   kirpmasi) olabilir; ENTRY-zamanlama edge'i izole EDILMEDI.
3. **Anlamlilik abartisi** (`partially_real`, major): HAC lag-5 yalniz zaman-serisi
   otokorelasyonu yakaliyor; kesitsel ayni-gun kumelenmesini DEGIL -> t %20-40 abartili
   (efektif t ~3.8-4.8, hala >2). IID bootstrap BOOTSTRAP_BLOCK=21 config'ini yok sayiyor.

**Survivorship:** survivors-only -> expectancy UST-SINIR. (the maintainer cercevelemesi: random'i
maliyet-sonrasi gecemese kesin elenir; gectigi icin "kesin red" YOK -- ama UST-SINIR oldugu
icin "kesin kabul" de YOK.)

**KARAR (DEC-039, the project):** Edge sinyali umut verici ve look-ahead-temiz, AMA (i) risk/DD
boyutu olculemedi (bozuk metrik), (ii) getiri nominal-kontamine + rejim-yogun, (iii) edge
entry-timing'e temiz atfedilemedi. **Bu uc duzeltme yapilmadan Katman A motoru ilan
EDILMEMELI.** Oneri: yeni Stage 0 ile **D-186 duzeltme turu** (asagida §7).

---

## 2. Yontem (on-kayitli, ozet)

- **Evren:** BIST100 (faz0 frozen liste, 113 aday). 88 ticker ADV>=50M TL/gun tabanini gecip
  yfinance'ten cekildi. Survivorship gap: KOZAA/KOZAL/IPEKE/TRALT (+TRKCM) yfinance 404 ->
  haric, bias yonu (iyimser/ust-sinir) meta+raporda kayitli.
- **Zamanlama:** sinyal t-kapanis, giris t+1-acilis (look-ahead guard, dogrulandi TEMIZ).
- **Cikis:** baslangic stop + 20-gun Donchian-alt trailing (yukari rachet), MAX_HOLD 126 gun.
  Ticker basina tek acik pozisyon.
- **Maliyet:** round-trip 30/50/80 bps (RR-038: BSMV komisyon-uzerinden).
- **Birincil kanit:** per-trade expectancy (R), Sharpe DEGIL.
- **Gate (AND):** expectancy>0 + HAC t>=2 + random'i %95 dilimde yener + rejim-tutarli (>=2
  market-state pozitif & tek dilim <=%80 PnL) + net-of-cost B&H'yi yener + max_dd<=%35.

---

## 3. Headline sonuclar (cost=50 bps, primary)

| Varyant | filtre | n_trade | expectancy_R | HAC t | win% | avgWin_R | avgLoss_R | random-ustu edge | gate |
|---|---|---|---|---|---|---|---|---|---|
| A_sr_flip_retest | parab_on | 1151 | **1.268** | 6.11 | 36.8 | 5.02 | -0.91 | +3.27 pp | FAIL (max_dd) |
| A_sr_flip_retest | parab_off | 1167 | 1.247 | 6.11 | 36.5 | 5.00 | -0.91 | +3.20 pp | FAIL (max_dd) |
| B_consolidation | parab_on | 857 | 0.741 | 6.39 | 50.1 | 2.02 | -0.54 | +4.79 pp | FAIL (max_dd) |
| B_consolidation | parab_off | 1014 | 0.716 | 7.19 | 51.1 | 1.90 | -0.52 | +4.86 pp | FAIL (max_dd) |
| C_donchian_retest | parab_on | 775 | 1.162 | 5.25 | 38.5 | 4.61 | -0.99 | +2.71 pp | FAIL (max_dd) |
| C_donchian_retest | parab_off | 823 | **1.307** | 5.63 | 38.9 | 4.91 | -0.98 | +3.52 pp | FAIL (max_dd) |

Maliyet duyarliligi: 30->80 bps gecisinde expectancy hafifce duser (A: 1.30->1.22) ama
isaret/anlamlilik korunur. Maliyet edge'i tek basina silmiyor (nominal drift baskin oldugu icin).

Referans: B&H esit-agirlik = **+%2276 nominal** (88 isim, 2019-2026); random null_mean ~+%5.7-8.2/trade.

---

## 4. Rejim ayristirma (cost=50) -- EN KRITIK BULGU

Edge **yuksek-enflasyon bogasinda yogunlasiyor, disinflasyonda cokuyor** (ama pozitif kaliyor):

| Varyant/filtre | pre_surge (2019-21) | high_inflation (2021-24) | disinflation (2024-26) | bear-state |
|---|---|---|---|---|
| A on | 1.17 R | **2.07 R** (PnL %66) | **0.30 R** | 1.82 R |
| A off | 1.16 R | 2.02 R | 0.29 R | 1.80 R |
| B on | 0.66 R | 1.15 R (PnL %68) | **0.18 R** | 2.43 R |
| B off | 0.59 R | 1.11 R | 0.16 R | 2.12 R |
| C on | 0.76 R | 1.69 R (PnL %64) | **0.54 R** | 3.57 R |
| C off | 0.73 R | 1.94 R (PnL %68) | **0.57 R** | 3.54 R |

- **Tum varyantlar 3/3 market-state'te (bull/bear/sideways) pozitif.** Bear-state expectancy
  en YUKSEK (az trade) -- trailing-stop trend trade'leri ayi piyasada hayatta kalanlarda iyi.
- **Disinflasyon (en ileri-donuk rejim) ayrimi belirleyici:** A 2.07->0.30 (cokus), B 0.18
  (zayif), **C 0.54-0.57 (en saglam).** RR-038'in tam uyarisi: edge rejime/nominal-drifte bagimli.
- Tek-dilim PnL payi 0.64-0.74 (<%80 gate esigi) -- gate'i gecer ama sinirda; yuksek-enflasyon
  bogasina belirgin bagimlilik var.

**Varyant C, disinflasyon ve bear rejimlerinde acik ara en dayanikli.** Bir varyant gecici
favorilenecekse C'dir -- ama bu, §1'deki 3 caveat duzeltilmeden bir Katman A karari DEGIL.

---

## 5. Parabolik-filtre AC/KAPA (RR-039 kanit boslugu #2 -- cevap)

| Varyant | expR (on) | expR (off) | n (on) | n (off) | hukum |
|---|---|---|---|---|---|
| A | 1.268 | 1.247 | 1151 | 1167 | filtre marjinal (+); ~%1 trade eler, expectancy ~ayni |
| B | 0.741 | 0.716 | 857 | 1014 | filtre marjinal (+); ~%15 trade eler |
| C | 1.162 | **1.307** | 775 | 823 | filtre **ZARARLI**: expectancy'yi 1.31->1.16 dusurur |

**Sonuc:** Parabolik-kacinma sezgisi bu testte expectancy'yi ANLAMLI ARTIRMIYOR. A/B'de
ihmal-edilebilir pozitif, C (Donchian) icin acikca NEGATIF (iyi trend trade'lerini erken eliyor).
RR-039 dogru tahmin etti: "icgudu, varsayilmamali, test edilmeli." Test edildi -> filtre
gerekcesi bu evren/pencerede dogrulanmadi. (Not: nominal-drift kontaminasyonu giderildikten
sonra yeniden bakilmali.)

---

## 6. Adversarial dogrulama (5 bagimsiz denetci -- workflow)

| Denetim | Iddia | Verdict | Severity | Ozet |
|---|---|---|---|---|
| DD-metrik | max_dd gate artefakt | **confirmed_artifact** | blocker | cumprod tam-sermaye; total_net_return 1e+26; max_dd~0.99 deterministik; gercek risk sinyali yok |
| Look-ahead | sizdirma yok | **refuted** (temiz) | none | 7/7 vektor temiz: entry t+1, stop<=t, Donchian shift(1), find_peaks confirm-lag, trailing, retest no-future |
| Nominal-drift | expectancy drift-baskin | **partially_real** | major | ~%64 drift, ~%36 (+3pp) temiz edge; high-inflation yogun; real/index-relative re-run sart |
| Random-null | adil null | **refuted** (adil degil) | major | strateji stop+trailing, random sabit-sure stop-suz; edge buyuk olcude cikis-mekanizmasi olabilir |
| Survivorship/stat | anlamlilik saglam | **partially_real** | major | survivorship ~%3-5 (minor); HAC t %20-40 abartili (kesitsel kumelenme); IID bootstrap block'u yok sayar |

Tam denetci kanitlari: workflow `wf_cd12b020-098` ciktisi.

---

## 7. Ne sonuclanabilir, ne sonuclanamaz

**Sonuclanabilir (guvenilir):**
- Kod look-ahead-temiz; expectancy peeking artefakti DEGIL.
- 3 varyant da random-entry'i maliyet-sonrasi anlamli yeniyor (nominal duzeyde, survivors-only ust-sinir).
- Edge guclu sekilde rejim-bagimli: high-inflation boga > sideways/pre > disinflation.
- Parabolik-filtre expectancy'yi artirmiyor (C'de zarar veriyor).
- C, disinflasyon+bear'da en dayanikli varyant.

**Sonuclanamaz (3 duzeltme gerektirir -- D-186):**
1. **Gercek risk/DD:** bozuk cumprod yerine pozisyon-boyutlu (sabit-fraksiyon/concurrency-limitli)
   portfoy equity egrisi + gercek max-DD.
2. **Drift'ten arindirilmis edge:** REEL (TUFE-deflate) VE/VEYA XU100-relative getiriyle yeniden
   kosu; her enflasyon dilimi icin AYRI random null.
3. **Entry-timing izolasyonu:** random null'a AYNI stop+trailing cikisini uygula (adil null) ->
   edge cikis-mekanizmasindan mi entry'den mi geliyor? Ek: blok-bootstrap / Driscoll-Kraay
   ile kesitsel-kumelenme-duzeltilmis anlamlilik.

Eger D-186 reel/relative + adil-null + dogru-DD ile **disinflasyon diliminde** random-ustu
anlamli edge gosterirse -> Katman A motoru (muhtemelen C tabanli) gerekcesi guclenir. Gostermezse
-> trend-motoru da (Faz 0 cross-sectional gibi) bu evren/pencerede zayif demektir -> premise
yeniden dusunulur.

---

## 8. Survivorship UST-SINIR cercevesi (the maintainer kosulu)

Tum sayilar survivors-only (88/113; delisted yfinance 404). Survivors-only expectancy'yi
SISIRIR -> her sonuc UST-SINIR. Denetci tahmini: delisted'lar sifir-edge olsa headline ~%3-5
duser (1.27->~1.23) -- materyal degil, ama YON iyimser. Pratik cerceveleme: random benchmark'i
maliyet-sonrasi GECEMESE gercekte kesinlikle gecemezdi; gectigi icin sinyal var ama UST-SINIR
oldugu icin gercek (alt-sinir) edge daha kucuk. §7'deki reel/adil-null testi alt-sinira yaklastirir.

---

## 9. Strangler + on-kayit disiplini

- Tum kod `src/screening/` altinda YENI (indicators/trend_config/trend_signals/trend_backtest/
  trend_snapshot/trend_test_runner). Eski cross-sectional/composite kod (engine/faz0/conviction/
  MASTER_WEIGHTS) DOKUNULMADI. test_architecture yesil.
- Stage 0 (commit bb90927) sonuc commit'inden ONCE; parametreler sonuc gorulduken sonra
  DEGISTIRILMEDI. Denetimde tespit edilen 3 tasarim defekti (DD-metrik, random-null asimetrisi,
  anlamlilik yontemi) **D-185 icinde post-hoc duzeltilMEDI** (data-snooping yasagi) -- bunlar
  yeni bir Stage 0 ile D-186'ya birakildi. Bu rapor D-185'in urettigini SADIK biçimde aktarir.

---

## 10. DEC-039

Bu program OLCTU + adversarial dogruladi + ONERIYOR. Hangi varyantin Katman A motoru olacagi,
D-186 duzeltmelerinin yapilip yapilmayacagi, premise'in korunup korunmayacagi the project karari.
Builder oneri sunar, karar vermez.
