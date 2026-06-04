# L11 -- FORWARD DAILY-PEAD TEST HARNESS SCAFFOLD (HUKUM: SCAFFOLD-SELF-TEST PASS)

Stage-0: `lab-demo-goal/stage0/STAGE0_L11_forward_daily_pead.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l11_forward_daily_pead_results.json`. ASCII. Bu bir VERI-CEKIMI DEGIL,
bir SCRAPER DEGIL, network YOK, yeni-edge YOK. L8/L9/L10 daily-PEAD feasibility-dongusunu kapatti;
L11 forward-deneyi CALISTIRILABILIR kilar: testi SIMDI donar (pre-registration), uygular ve
mekanigi SENTETIK gun-damgasiyla OFFLINE dogrular. Gercek gun-damgali panel geldiginde AYNI harness
on-kayitli testi calistirir; gelene-kadar yalniz sentetik self-test.

## Tasarim (Stage-0'da donmus -- forward gercek-mod)
- Olay: her (sembol, publication_date) SUE-nonnull; giris KESINLIKLE gun-damgasindan SONRAKI ilk
  islem-gunu t+1 (look-ahead-safe: ILAN-GUNU sicramasi DISLANIR -- PEAD = ilandan SONRAKI drift,
  olay-gunu getirisi DEGIL).
- Pencere: [+1,+H] kumulatif anormal getiri (CAR), H in {5,10}; anormal = sembol-getiri eksi o-gun
  LIKIT-evrenin EW-ortalama getirisi (market-relative, carry-immune).
- Likidite: trailing-63g-medyan value_tl >= 1e7 TL (t-aninda, look-ahead-safe). LIKIT = deploy-mercegi (L7).
- Sort: SUE terciles; PRIMARY deploy-leg = long ust-tercile market-relative CAR; korroborasyon = long-short.
- Stat: olay-kumeli Newey-West t (lag=H); keep-bar = rel-net-CAR>0 AND |t|>=2 AND regime-isaret-stabil
  (2022-01-01) AND gercekci per-isim round-trip-maliyet sonrasi yasar.
- Maliyet: gercek-kosumda production D-207 per-isim round-trip baglanir; scaffold parametreli flat
  placeholder kullanir ve ikame-noktasini isaretler.
- Verdict-kurali: keep-bar gecerse TRADEABLE-EDGE (deploy-aday -> the maintainer); yoksa NOT-TRADEABLE
  (daily-PEAD en-guclu-guc-sinifi tukenmis-olarak graveyard'a). Her-iki-halde on-kayitli, kaydedilir.

## Offline self-validation (sentetik, seed=20260604)
Seed'li sentetik gunluk-getiri evreni + 480 planted-olay (gun-damgali, SUE-degerli). Pozitif-SUE
olaylara [+1,+H]'de eklenen GUCLU post-ilan drift (drift_per_sue=0.020), negatif simetrik; ayrica
olay-GUNUNE +-3% sicrama eklenir (t+1 girisinin bunu DISLAMASI gerekir).

| assert | sonuc | NW-t |
|---|---|---:|
| RECOVERY (planted-drift geri-kazanilir, dogru-isaret, |t|>=2) | **PASS** | 5.91 |
| PLACEBO (SUE-etiketleri permute -> etki kaybolur, |t|<2) | **PASS** | 0.18 |
| LOOK-AHEAD (olay-gunu girisi sicramayi SIZDIRIR, |t| safe'ten buyuk) | **PASS** | 13.53 (vs 5.91) |

all_asserts_pass = **True**. Pipeline DOGRU ve look-ahead-GUVENLI.

## Okuma
- **Mekanik kanit, edge-kaniti DEGIL**: Sentetik RECOVERY yalniz tahminci-dogrulugunu kanitlar
  (bilinen-planted etkiyi geri-kazanir). GERCEK BIST daily-PEAD edge'i hakkinda HICBIR sey soylemez.
- **Look-ahead muhuru**: olay-gunu girisi (leak) t=13.5 verir; guvenli t+1 girisi t=5.9 -> aradaki
  fark planted +-3% ilan-sicramasinin t+1 ile DISLANDIGINI kanitlar. PEAD=drift, sicrama-DEGIL.
- **Placebo temiz**: etiket-permutasyonu t=0.18 -> tahminci spurious-etki uretmiyor.
- **DURUST sinir**: gecen sentetik self-test GEREKLI ama YETERLI degil. Gercek-test yine
  NOT-TRADEABLE donebilir (orn. gunluk-drift gercekci-maliyet sonrasi cok-kucukse, L3'un aylik
  null'unu yansitarak). Bunu yalniz onayli-fetch karara-baglar.

## Hukum: SCAFFOLD-SELF-TEST PASS
Yeni-edge iddiasi YOK. daily-PEAD sentezi (L8 n_required + L9 hacim + L10 etki/isaret) artik
CALISTIRILABILIR forward-deneyle taclandi: deney donmus ve gercek gun-damgasindan tek-komut uzakta.
Sentetik PASS yalniz pipeline-dogrulugu + look-ahead-guvenligi kanitlar; gercek BIST-edge'i
network-fetch'in the maintainer-onayina KAPILI -- otonom-faz herhangi bir cekimden ONCE kasitli durur.
N<=1 (scaffold). L11 ARSIVLENDI. SONUC: FORWARD_DATA_SPEC #1 artik (a) teorik-power [L8],
(b) gercek-hacim [L9], (c) makul-magnitude [L10] VE (d) on-kayitli+offline-dogrulanmis calistirilabilir-harness
[L11] ile DORT-yonden hazir; tek-kalan adim onayli KAP gun-damgasi cekimi.
