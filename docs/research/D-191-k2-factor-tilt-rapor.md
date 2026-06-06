# D-191 -- K2 Factor-Tilt PORTFOLIO Backtest Raporu

**VERDICT (DEC-K2): GECMEZ** -- K2 modest-factor tilt Yol 2'ye GIRMEZ; saf-zemin (K0+K1) kalir.

**Tarih:** 1 Haziran 2026 | **Branch:** feat/k2-factor-tilt-backtest | **Karar sahibi:** maintainer (DEC-039)
**Dayanak:** SPEC_YOL2 v3.0 sec.1 KATMAN 2 + sec.4; ARCHITECTURE v3.0; RR-OMEGA (kanit-boslugu); D-177/D-178/D-183; D-185/D-186 (armored-backtest dersleri)

---

## 1. TL;DR (7 madde)

1. **K2 composite tilt (value+profitability+lowvol) GECMEZ.** Frozen 4-kapili DEC-K2'nin 3 kapisi dusuyor (gate1 TL-reel anlamlilik, gate2 adil-null, gate3 out-of-sample). Sadece gate4 (en az bir faktor) gecti -- o da YALNIZ value sayesinde.
2. **Adil-null kesin konustu:** composite_tercile'in net TL-reel beklentisi (+%11.9/donem) random ayni-boyut sepetin **%62.7 dilimi**nde (null ort. +%11.4). Yani **faktor-secimi sanstan ayirt edilemiyor** -- getiri faktor-becerisi degil, sadece havuza maruziyet (D-186'nin "drift, beceri degil" dersinin tekrari).
3. **Profitability (ONCELIK faktor, RR-OMEGA/EM-FF5 umudu) BIST'te DESTEKLENMEDI:** tek-faktor null dilimi %51.9 (= random). EM-profitability priori bu evren/pencerede tutmadi.
4. **Tek istisna VALUE:** value-only tek-faktor TL-reel anlamli (CI sifiri disliyor) ve adil-null'i geciyor (%99.6 dilim). Ama composite, value'yu calismayan iki faktorle (profitability+lowvol) seyreltince null'i gecemiyor.
5. **Out-of-sample cokuyor:** in-sample (2019-2022) guclu-pozitif (+%23.4/donem) ama out-of-sample (2023-2026) **NEGATIF** (-%1.6). Sadece dusuk-guc degil; nokta-tahmin isaret degistiriyor -> kalicilik yok (overfit/rejim imzasi).
6. **Survivorship iyimser ust-sinir:** delisted haric (iyimser). EDGE ZATEN bu iyimser olcumde bile yok -> gercek evrende daha kotu olur -> GECMEZ sonucu GUCLENIR.
7. **Karar:** K2 Yol 2'ye girmez; K0+K1 zemini kalir. Value-only tilt ayrica incelenmeyi hak ediyor (oneri, karar O+C) ama spesifik value+quality+lowvol composite hipotezi reddedildi.

---

## 2. Metot (Stage-0'da donduruldu -- post-hoc gevsetme YOK)

- **Pencere:** 2019-01-01 -> 2026-04-30, **yari-yillik** rebalance (15 rebalance -> 14 holding; ilk donem 2019-06 lowvol-252 tanimsiz -> bos sepet, hem stratejide hem null'da dusuruluyor -> **n=13 etkin donem**).
- **Evren:** survivors-only BIST100 havuzu (112 fiyat / 109 fundamental yuklendi; 9 banka; null'lar: ANSGR/KLNMA/TRKCM/TURSG). **Bias: iyimser ust-sinir** (Stage-0'da deklare).
- **Faktorler:** value=1/(P/B); profitability=GP/TA (Novy-Marx, BIRINCIL) + ROE (robustluk); lowvol=252g realized-vol. Momentum YOK.
- **Composite:** esit-agirlik rank-ortalama (invariant 4; composite-optimize YASAK). Secim varyantlari (N<=3): tercile (birincil), quintile, tercile-kesisim.
- **Net:** round_trip cost (tier A) + 20bps slippage/donem turnover'a + temettu-stopaj drag (varsayim %3 getiri * %15, caveat).
- **Bazlar:** TL-reel (TUFE, **BIRINCIL kapi**), XU100-relative + USD (raporlanir). **Adil-null:** ayni N/tarih/holding/maliyet ile rastgele isim-secimi, 2000 resample, seed 12345.
- **DEC-K2 (donduruldu):** gate1 net TL-reel beklenti anlamli-POZITIF (block-bootstrap %95 CI > 0) VE gate2 adil-null >%95 dilim VE gate3 out-of-sample pozitif VE gate4 en az bir faktor (ozellikle profitability) bagimsiz-anlamli.

---

## 3. Sonuclar -- Composite varyantlar (net, TL-reel; donem = yari-yil)

| Varyant | TL-reel ort | TL-reel %95 CI | CI>0? | Adil-null dilim | Null'u gecer? | XU100-rel ort | USD(nominal) ort | Max DD | in-sample | out-sample |
|---|---|---|---|---|---|---|---|---|---|---|
| **composite_tercile** (birincil) | +11.9% | [-5.0%, +34.5%] | HAYIR | **0.627** | HAYIR | +4.7% | +2.4% | -33.2% | +23.4% | **-1.6%** |
| composite_quintile | +12.1% | [-4.5%, +34.1%] | HAYIR | 0.644 | HAYIR | +5.0% | +0.1% | -31.2% | +25.4% | -3.5% |
| tercile_intersection | +9.4% | [-9.3%, +33.1%] | HAYIR | 0.503 | HAYIR | +2.0% | -1.1% | -42.8% | +22.5% | -5.9% |

- Ortalama turnover %27-57; ortalama maliyet/donem %0.39-0.82 (dusuk-devir hedefi tutuyor).
- USD: US-CPI dondurulmus seri verilmedi -> **USD-NOMINAL** olarak etiketli (Stage-0 kurali: sessiz fallback yok). USD-nominal ~break-even.

## 4. Sonuclar -- Tek-faktor (gate 4 teshisi; tercile, net TL-reel)

| Faktor | TL-reel ort | CI sifiri disliyor? | Adil-null dilim | Null'u gecer? |
|---|---|---|---|---|
| **value** | +17.7% | **EVET** | **0.996** | **EVET** |
| profitability (oncelik) | +14.0% | HAYIR | 0.519 | HAYIR |
| lowvol | +11.5% | HAYIR | 0.651 | HAYIR |

---

## 5. Verdict -- gate-by-gate

| Kapi | Sonuc | Aciklama |
|---|---|---|
| gate1 -- TL-reel anlamli-pozitif | **DUSUK** | composite_tercile ort +%11.9 ama %95 CI [-5.0%, +34.5%] sifiri iciyor |
| gate2 -- adil-null >%95 | **DUSUK** | %62.7 dilim -> faktor-secimi random'dan ayirt edilemiyor |
| gate3 -- out-of-sample pozitif | **DUSUK** | out-sample -%1.6 (in-sample +%23.4 KALICI DEGIL) |
| gate4 -- en az bir faktor anlamli | GECTI | value gecti (profitability/lowvol gecmedi) |
| **DEC-K2 (hepsi)** | **GECMEZ** | 3/4 kapi dustu |

---

## 6. Yorum

- **Esas bulgu (adil-null):** Strateji net TL-reel beklentisi (~%11.9/donem) ile random ayni-boyut sepetin null ortalamasi (~%11.4) neredeyse esit. Faktor-rank ile secim, ayni havuzdan rastgele secime gore **istatistiksel ek-deger uretmiyor**. Getiri = havuza-maruziyet (BIST risk-primi + survivorship), faktor-becerisi degil. Bu, D-186'nin "edge = drift/mekanizma, beceri degil" dersinin K2 analogu.
- **Composite seyrelmesi:** value tek-basina sinyal tasiyor (null %99.6, CI>0) ama profitability+lowvol calismayinca esit-agirlik composite onu seyreltip null-alti birakiyor. Bu, "coklu-faktor her zaman daha iyi" varsayimina karsi bir kanit.
- **Profitability priori tutmadi:** RR-OMEGA/EM-FF5 "profitability EM'de spanning'i gecen tek faktor" priori, BIST survivors 2019-2026'da DESTEKLENMEDI (null %51.9 = sans). Kritik-agent'in "profitability oncelik" tezi bu olcumde gecerli cikmadi.
- **Kalicilik yok:** in/out kontrasti (in +%23 -> out -%1.6) puan-tahmin isaret degistirdigi icin sadece dusuk-guc degil; ampirik kalicilik yoklugu. (R4 ince-n caveat'i bilincli-kabuldu; ama burada sonuc dusuk-guctsen ote net isaret-donmesi.)

---

## 7. Caveat'lar

- **Survivorship:** iyimser ust-sinir. Edge bu iyimser olcumde bile yok -> gercek (delisted-dahil) evrende daha zayif -> GECMEZ guclenir. Adil-null AYNI havuzdan cektigi icin strateji-vs-null karsilastirmasi adil; sadece mutlak seviye sisik.
- **USD-reel:** US-CPI dondurulmus seri saglanmadi -> USD-NOMINAL raporlandi (etiketli). USD-reel TL-reel'den daha kotu olur (TRY reel deger kaybi). Karar TL-reel BIRINCIL kapidan verildi.
- **Ince in/out (R4, maintainer bilincli-kabul):** ~6-7 donem/dilim -> genis CI. Veri-siniri (faktor fundamental-gerektirir, temiz pre-2018 veri yok) -- plan-kusuru degil. Tek-dilim over-interpret edilmedi; in/out kontrasti yine de bilgilendirici.
- **Temettu-vergi:** auto_adjust temettuyu fiyata gomdugu icin %15 stopaj dondurulmus drag (varsayim %3 yillik getiri) ile yaklasildi. Mutlak seviyeyi ~%0.45/yil etkiler; karar-yonunu degistirmez.
- **Fair-null fix (metodoloji-duzeltmesi, esik-gevsetme DEGIL):** ilk run'da bos ilk-donem (lowvol-252 tanimsiz) null havuz-kontrolunu abort ediyordu (n=0). Strateji ile ayni sekilde bos donemi dusurecek sekilde duzeltildi (DEC-K2/esikler degismedi). Duzeltme sonrasi verdict yine GECMEZ.

---

## 8. Oneri (karar maintainer -- DEC-039)

1. **K2 (value+quality+lowvol composite) Yol 2'ye GIRMEZ.** Saf-zemin K0 (maliyet/vergi) + K1 (risk-primi statik maruziyet) kalir.
2. **Value-only tilt ayri incelenmeyi hak ediyor** (tek faktor null %99.6, CI>0) -- AMA bu yeni bir hipotez (yeni Stage-0 + kendi out-of-sample testi); bu raporun verdict'i degil. Composite-seyrelme bulgusu ona da uyari.
3. **Profitability BIST-net-reel'de desteklenmedi** -- RR-OMEGA kanit-boslugu bu yonde KAPANDI (negatif).
4. Tum testler (D-191 + sonrakiler) bitince maintainer tam-sistemi kurar (Secenek-2: once-tum-testler).

---

## 9. Reproducibility

- Stage-0 (pre-results): `docs/k2_test/STAGE0_factor_tilt_preregistration.json` (commit oncesi donduruldu)
- Sonuclar: `docs/k2_test/factor_tilt_results.json`
- Frozen snapshot hash'leri: price `e13eb2af...` (112 isim), fundamentals `e194fbf7...` (860 satir/109 isim), fx `6389bfae...` (688 obs)
- MaliTablo profit itemCode'lari (Faz B discovery, EREGL): gross_profit=3D, total_assets=1BL, net_income=3Z
- Kod: `src/screening/k2_factor_tilt.py` + `k2_profitability.py` + `k2_tilt_config.py`; testler `tests/test_k2_factor_tilt.py` (23 gecti)
- Tekrar: `python -m src.screening.k2_factor_tilt --run` (frozen snapshot'lari yukler -> birebir ayni JSON)
