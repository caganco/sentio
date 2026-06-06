# D-Y1-001 -- Value-only Tilt REJIM-DAYANIKLILIK Testi Raporu (Yol-1 Asama-1)

**VERDICT (DEC-Y1): KIRILGAN / REJIM-BAGIMLI.** Frozen 4-kapili kural birincil metrik (P/B = defter/piyasa) uzerinde mekanik olarak GECER (4/4 kapi), ANCAK robustluk-metrigi (E/P) GECMEZ (gate-1 + gate-4 duser, 2-yol rejim-hizalamasi AYRISIK=KIRILGAN) ve birincil metrigin kendisi out-of-sample cokuyor. Toplam kanit: prim **2019-2022 yuksek-enflasyon surgesine yogunlasmis, kararli-rejim-bagimsiz bir prim DEGIL**. Yol-2 overlay'ine hizli-gecis ONERILMEZ; nihai karar maintainer (DEC-039).

**Tarih:** 2 Haziran 2026 | **Branch:** feature/d-y1-001-value-only-regime | **Karar sahibi:** maintainer (DEC-039); harness OLCER + ONERIR
**Dayanak:** RR-Y1.md sec.SORU-1 (celiski cozumu) + Recommendations Soru-1 #1 (ayni-orneklem rank-IC + decile MR) / #3 (tek alt-donem t>2 YETERSIZ; >=2 bagimsiz alt-donem gerekir). D-191 K2 altyapisi (k2_*) salt-okunur reuse; D-183 Faz-0 rank-IC metodu; D-186 INFLATION_REGIMES.

---

## 1. TL;DR (8 madde)

1. **Celiski COZULDU (AYAK-1):** Ayni orneklemde HEM zayif-honest-IC HEM guclu-tilt birlikte gozlendi -> RR-Y1 sec.SORU-1'in ongordugu metodolojik imza dogrulandi (bir hata degil). P/B rank-IC honest_t (NW HAC) = 4.67 (h=63) / 4.53 (h=126) -- aslinda bu evren/pencerede IC de pozitif-anlamli; Faz-0'in "zayif" okumasi farkli pencere/metrik kaynakli.
2. **Birincil metrik (P/B) frozen kurali GECER:** tercile net TL-reel +%17.7/donem, %95 CI [+%1.0, +%39.2] sifiri disliyor (gate-1); adil-null %99.6 dilim (gate-2); 3-yol rejimlerde 3/3 pozitif + 2-yol HIZALI (gate-3); decile profili acklanabilir (spread +%10.0, monotonluk Spearman +0.60) (gate-4).
3. **AMA robustluk-metrigi (E/P) GECMEZ:** tercile TL-reel +%16.6 ama %95 CI [-%0.5, +%40.2] sifiri ICIYOR (gate-1 DUSER); decile spread NEGATIF (-%2.5), gate-4 DUSER; 3-yol 2/3 pozitif (gate-3 gecer) ama 2-yol AYRISIK -> hizalama KIRILGAN. E/P verdict = GECMEZ.
4. **Iki value-metrigi ZIT verdict -> metrik-tanimina-duyarlilik.** Bu, AYAK-3'un rejim-hizalama mantiginin metrik-duzeyindeki karsiligi: prim olcum-tanimina hassas = KIRILGAN sinyali.
5. **Out-of-sample cokuyor (her iki metrikte):** P/B in-sample (2019-2022) +%30.6 (CI sifiri disliyor) -> out-of-sample (2023-2026) +%0.5 (CI sifiri iciyor). E/P out-of-sample NEGATIF (-%2.1). D-191'in in/out cokusuyle bire-bir tutarli.
6. **Disinflasyon rejimi prim tasimiyor:** P/B disinflation ort sadece +%2.1 (CI sifiri iciyor); E/P disinflation NEGATIF (-%2.1). Prim tamamen pre_surge (+%26) + high_inflation (+%18, CI sifiri iciyor) doneminden geliyor.
7. **Tek-donem dominansi:** 2022-06 -> 2022-12 tek holding'i P/B'de +%127.5 reel -- full-window ortalamasini tek basina sisiriyor. RR-Y1 #3'un "tek alt-donem YETERSIZ" uyarisinin somut karsiligi.
8. **Survivorship iyimser ust-sinir:** delisted haric. Bu iyimser olcumde bile prim rejim-bagimli/metrige-duyarli cikiyor -> gercek evrende daha zayif -> KIRILGAN okumasi GUCLENIR.

**Honest okuma:** Frozen kural (birincil P/B) mekanik PASS verir ve kayit icin oyle raporlanir. Fakat uc bagimsiz robustluk sinyali (E/P metrigi celisiyor + cokuyor, P/B out-of-sample CI sifiri iciyor, disinflasyon rejimi duz/negatif) primin **kararli degil rejim-bagimli** oldugunu gosteriyor. Bu, "celiski metodolojiktir" (AYAK-1) ama "value kararli-prim degildir" (AYAK-3 + out-of-sample) seklindeki ikili dogru sonuctur -- RR-Y1'in "BIST value rejim-istikrarsiz" tezini dogrular.

---

## 2. Metot (Stage-0'da DONDURULDU -- post-hoc gevsetme YOK)

- **On-kayit:** `docs/yol1/STAGE0_value_only_regime_preregistration.json` sonuc gorulmeden ayri commit edildi (2e2f502). 4-kapili DEC-Y1 + AYAK-3 hizalama-okuma-kurali orada DONDU.
- **Pencere/takvim:** 2019-01-01 -> 2026-04-30, yari-yillik rebalance (15 rebalance -> 14 holding). K2 frozen takviminden miras -> AYAK-1 rank-IC ile tilt AYNI gozlemlerde olculuyor (celiski-cozumunun ana noktasi).
- **Evren:** survivors-only K2 BIST100 havuzu (112 fiyat yuklendi). Bias: **iyimser ust-sinir** (Stage-0'da deklare; adil-null AYNI havuzdan ceker -> karsilastirma adil).
- **Value metrikleri:** BIRINCIL = book-to-market = 1/(P/B) (low P/B -> yuksek rank); ROBUSTLUK = E/P = net_income/market_cap (high E/P -> yuksek rank). Ikisi de point-in-time (pub_date <= sinyal tarihi + 120g lag) -> look-ahead-safe. **Composite YOK** (value izole).
- **Secim (N<=3):** tercile (birincil, gated) + quintile (robustluk). Deciles AYAK-2 monotonluk DIAGNOSTIGI (sweep degil).
- **Net:** round_trip cost (tier A) + 20bps slippage/donem + temettu-stopaj drag (varsayim %3*%15, caveat). K2 knoblari verbatim.
- **Bazlar:** TL-reel (TUFE, BIRINCIL kapi) + XU100-relative + USD (raporlanir, gate degil). USD: US-CPI dondurulmus seri yok -> USD-NOMINAL etiketli; fx kapsamasi 2023-08'den (kismi) -> n=5, gate degil.
- **Adil-null:** ayni N/tarih/holding/maliyet ile rastgele isim-secimi, 2000 resample, seed 12345. **Anlamlilik:** block-bootstrap %95 CI, block=1 (yari-yil ortusmesiz), 2000 boot, seed 12345.

### DEC-Y1 (donduruldu) -- 4 kapi, verdict BIRINCIL (P/B) metrige bagli
1. **gate-1:** net TL-reel tercile-tilt ort > 0 VE block-bootstrap %95 CI sifiri disliyor (CI_low > 0).
2. **gate-2:** adil random-secim null'i >= %95 dilim.
3. **gate-3 (AYAK-3):** birincil 3-yol INFLATION_REGIMES'te >=2/3 tutarli-pozitif (tek alt-donem t>2 YETERSIZ). 2-yol (pre/post 2023-01-01) robustluk hizalamasi yan-okuma.
4. **gate-4 (AYAK-2):** decile profili acklanabilir (ucuz-eksi-pahali spread > 0 VE prim ucuz-ucta: Spearman(decile_idx_cheap_high, getiri) > 0).
- PASS -> Yol-2 overlay adayi (<=%10-20, ana-sisteme degil; O+C). PARTIAL (gate1&2&4 gecer, gate3 duser) -> "value rejim-bagimli". FAIL -> elendi.

---

## 3. AYAK-1 -- Rank-IC ve tilt AYNI orneklemde (celiski-imzasi DIAGNOSTIK)

| Metrik | Horizon | mean_IC | ICIR | naive_t | **honest_t (NW HAC=h)** | p (NW) |
|---|---|---|---|---|---|---|
| **P/B** | 63g | +0.0805 | 0.68 | 28.5 | **+4.67** | 3e-06 |
| **P/B** | 126g | +0.1117 | 0.95 | 39.3 | **+4.53** | 6e-06 |
| E/P | 63g | +0.0514 | 0.40 | 17.0 | +2.86 | 0.004 |
| E/P | 126g | +0.0785 | 0.73 | 30.2 | +3.55 | 4e-04 |

- **Celiski-imzasi dogrulandi:** ayni veride hem (gurultulu-orta-kesit yuzunden Faz-0'da "zayif" okunan) rank-IC hem guclu uc-tercile tilt birlikte. Bu pencere/evrende P/B IC'si honest_t>2 -- yani celiski "IC tamamen olu" degil, "Faz-0 farkli pencere/metrik (F/DD+EV/EBITDA) ile zayif olcmus" seklinde cozuluyor (RR-Y1 sec.SORU-1).
- DIAGNOSTIK: gate degil. Tilt'in yaninda raporlanir.

---

## 4. Tilt sonuclari (net, TL-reel; donem = yari-yil, n=14)

| Metrik / Varyant | TL-reel ort | %95 CI | CI>0? | Adil-null dilim | Null'u gecer? | XU100-rel | in-sample | out-sample | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| **P/B tercile** (BIRINCIL) | **+17.7%** | [+1.0%, +39.2%] | **EVET** | **0.996** | **EVET** | +9.9% | +30.6% | **+0.5%** | -40.4% |
| P/B quintile | +21.8% | [+4.0%, +44.1%] | EVET | 0.9995 | EVET | +13.9% | +36.5% | +2.2% | -40.2% |
| **E/P tercile** (ROBUSTLUK) | +16.6% | **[-0.5%, +40.2%]** | **HAYIR** | 0.9945 | EVET | +8.6% | +30.7% | **-2.1%** | -38.0% |
| E/P quintile | +18.3% | [+1.2%, +39.5%] | EVET | 0.992 | EVET | +10.8% | +33.5% | -2.1% | -40.9% |

- **Birincil P/B tercile gate-1 + gate-2 gecer.** Ama out-of-sample +%0.5 (CI [-%9.3, +%10.9] sifiri iciyor) -> kalicilik YOK.
- **E/P tercile gate-1 DUSER** (CI sifiri iciyor) ve out-of-sample NEGATIF. Robustluk metrigi birincili dogrulamiyor.
- USD-nominal pozitif ama n=5 (kismi fx kapsama), gate degil.

---

## 5. AYAK-2 -- Decile monotonluk (Gate-4)

Decile 0 = en pahali (en dusuk value rank) .. Decile 9 = en ucuz. Per-decile net TL-reel ort (n=14):

| | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | spread (D9-D0) | Spearman | gate-4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **P/B** | 13.8% | 6.4% | 6.6% | 12.0% | 14.9% | 14.4% | 13.7% | 10.0% | 19.4% | 23.8% | **+10.0%** | **+0.60** | **GECER** |
| E/P | 15.4% | 8.0% | 13.1% | 8.8% | 9.4% | 9.6% | 6.7% | 17.5% | 22.9% | 12.9% | **-2.5%** | +0.26 | **DUSER** |

- **P/B:** prim ucuz-ucta yogunlasiyor (D9=%23.8 > D0=%13.8), pozitif monotonluk -> acklanabilir profil, gate-4 gecer.
- **E/P:** en pahali decile (D0=%15.4) en ucuzdan (D9=%12.9) yuksek -> spread NEGATIF, gate-4 DUSER. Profil acklanamiyor.
- **Caveat:** survivors-only ~11-12 isim/decile, yari-yil -> genis gurultu; diagnostik, asiri-yorumlanmaz.

---

## 6. AYAK-3 -- Rejim-dayaniklilik (Gate-3, EN KRITIK)

### Birincil 3-yol (INFLATION_REGIMES, karar-gate)

| Rejim | n | P/B ort | P/B CI sifiri disliyor? | E/P ort | E/P isaret |
|---|---|---|---|---|---|
| pre_surge (2019-01..2021-09) | 5 | **+26.1%** | EVET | +24.2% | + |
| high_inflation (2021-10..2024-06) | 6 | +18.4% | HAYIR (CI iciyor) | +19.6% | + |
| disinflation (2024-07..2026-04) | 3 | **+2.1%** | HAYIR (CI iciyor) | **-2.1%** | - |
| **n_positive / gate-3** | | **3/3 -> GECER** | | **2/3 -> GECER** | |

### Robustluk 2-yol (pre/post 2023-01-01)

| | P/B pre | P/B post | E/P pre | E/P post |
|---|---|---|---|---|
| ort | **+30.6%** | **+0.5%** | +30.7% | **-2.1%** |
| CI sifiri disliyor? | EVET | HAYIR | EVET | HAYIR |
| her iki-donem pozitif? | **EVET** (hizali) | | **HAYIR** (ayrisik) | |

### Hizalama okumasi (Stage-0'da donduruldu)
- **P/B:** 3-yol (3/3 pozitif) ve 2-yol (her ikisi pozitif) **HIZALI -> karar GUCLU** (frozen kurala gore gate-3 gecer).
- **E/P:** 3-yol gate-3 gecer (2/3) AMA 2-yol AYRISIK (post-2023 negatif) -> **REJIM-TANIMINA-DUYARLI = KIRILGAN** (kararli-prim-degil, durust-kapanis yonunde).
- **Iki metrik arasi ayrisma** (P/B hizali-PASS vs E/P ayrisik-FRAGILE) primin olcum-tanimina hassas oldugunun ek kanitidir.
- **Not (frozen):** tek alt-donem t>2 YETERSIZDIR (RR-Y1 #3); rejim-bagimli etki != kararli prim. P/B'nin "hizali" gorunmesi, pozitif donemlerin CI'lerinin coguntan sifiri ICMESINE (high_inflation, disinflation) ve out-of-sample cokuse ragmendir.

---

## 7. Verdict -- gate-by-gate

| Kapi | P/B (BIRINCIL, verdict) | E/P (ROBUSTLUK) |
|---|---|---|
| gate-1 TL-reel anlamli-pozitif | **GECER** (CI_low +%1.0) | **DUSER** (CI sifiri iciyor) |
| gate-2 adil-null >=%95 | **GECER** (%99.6) | GECER (%99.5) |
| gate-3 rejim-dayanikli (3-yol >=2/3) | **GECER** (3/3) | GECER (2/3) ama 2-yol AYRISIK |
| gate-4 decile acklanabilir | **GECER** (spread +%10, rho +0.60) | **DUSER** (spread -%2.5) |
| 2-yol hizalama | HIZALI | **AYRISIK (KIRILGAN)** |
| **Frozen verdict** | **PASS (4/4)** | FAIL (gate1+gate4) |

**Mekanik DEC-Y1 (birincil P/B) = PASS.** Kayit icin boyle raporlanir; frozen kural post-hoc gevsetilmedi/sikilastirilmadi.

**Honest bilimsel okuma = KIRILGAN / REJIM-BAGIMLI:**
- Robustluk metrigi (E/P) celisiyor (gate1+gate4 duser, 2-yol ayrisik).
- Birincil metrigin (P/B) kendisi out-of-sample cokuyor (in +%30.6 anlamli -> out +%0.5 anlamsiz).
- Disinflasyon rejimi prim tasimiyor (P/B +%2.1 CI-iciyor; E/P -%2.1).
- Prim tek-donem (2022H2 +%127.5) ve pre-2023 surgesine yogunlasmis.

Bu tablo, RR-Y1'in "BIST value rejim-istikrarsiz; tek alt-donem t>2 yetersiz" tezinin ve D-191 in/out cokusunun bagimsiz tekrarli dogrulamasidir.

---

## 8. Oneri (karar maintainer, DEC-039)

1. **Value-only'yi Yol-2 overlay'ine HIZLI-GECIS yapma.** Mekanik PASS rejim-bagimli; kararli prim kaniti yok.
2. Eger O+C yine de degerlendirirse: agir rejim-kapisi sart (yalniz pre_surge/high_inflation benzeri ortamda; disinflasyonda devre-disi) ve <=%10 overlay tavani, P/B-tek-metrik degil iki-metrik-onayli giris.
3. **Durust-kapanis alternatifi:** value-only "denendi -- celiski metodolojik (AYAK-1), ama prim kararli-degil (AYAK-3 + out-of-sample)" olarak arsivlenir; ana-sistem (K0+K1 zemini) degismez. D-191 ile tam tutarli.
4. Ileri olcum (istege bagli, O+C): delisted-dahil tam-evren (survivorship duzeltme) primi muhtemelen daha da zayiflatir -> KIRILGAN okumasini test eder.

---

## 9. Repro / dosyalar

- **On-kayit (frozen, sonuc-oncesi):** `docs/yol1/STAGE0_value_only_regime_preregistration.json` (commit 2e2f502). Snapshot content-hash'leri orada; cevrimdisi tam tekrarlanabilir.
- **Sonuclar:** `docs/yol1/value_only_regime_results.json` (AYAK-1/2/3 + tercile/quintile x P/B,E/P + verdict).
- **Motor:** `src/screening/value_only_regime.py` (+ `value_only_regime_config.py`, `scripts/run_value_only_regime.py`). Strangler: k2_factor_tilt / factors / factor_ic_harness / trend_config salt-okunur reuse; composite/conviction/MASTER_WEIGHTS/signal-backtest-engine importu YOK (architecture invariant, `tests/test_value_only_regime.py` ile enforce).
- **Kosu:** `python -m src.screening.value_only_regime --run` (cevrimdisi frozen snapshot).
- **Testler:** unit 10/10, architecture+K2 80 pass (1 skip), full-regression 1626 pass (4 skip) -- sifir regresyon.
