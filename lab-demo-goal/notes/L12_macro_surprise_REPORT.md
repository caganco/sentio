# L12 -- MACRO SURPRISE-CONDITIONING FORWARD-RANK RATIONALE (HUKUM: FORWARD-RANK-RATIONALE-VIEW)

Stage-0: `lab-demo-goal/stage0/STAGE0_L12_macro_surprise.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l12_macro_surprise_results.json`. ASCII. SENTEZ/feasibility -- yeni-edge
YOK, yeni-veri-CEKIMI YOK, optimizasyon YOK, RE-TEST YOK. FORWARD_DATA_SPEC #2'yi (surpriz-kosullu
makro) ON-KAYITLI L6 (kosulsuz CPI-olay) + L8 (power) + GERCEK makro-panelden SAYISALLASTIRIR:
kosulsuz CPI etkisi ve gercek gelis-hizi verildiginde, surpriz-kosullama makro-sinifini |t|=2'ye
insan-ufkunda getirmek icin hangi etki-CARPANINI saglamali, ve baglayan-kisit MAGNITUDE mi yoksa
ISARET-COHERENCE mi? #2'nin siralama-gerekcesini "iddia"dan "olculmus"e tasir.

## Olculen (GERCEK makro-panel + L6/L8)
- CPI gelis-hizi: 88 olay / 7.24 yil = **~12.1/yil** (L8'in varsaydigi 12'yi dogrular).
- En-guclu look-ahead-safe leg = **post_tight [+1,+5]**: kosulsuz +61bp, clustered_t=**1.478**, n=87,
  regime sign_stable=**FALSE**, Bonferroni-gecmez. Kosulsuz |t|=2 icin n_req=159 -> ~6 yil daha.
- post_wide [+1,+10]: +55bp, t=0.934, sign_stable=FALSE, n_req=399 -> ~26 yil.

Gereken surpriz-CARPANI (|t|=2 icin, ~12/yil hizda):
| leg | H=3yil | H=5yil | H=10yil |
|---|---:|---:|---:|
| post_tight (t0=1.48) | 2.09x | **1.62x** | **1.15x** |
| post_wide (t0=0.93) | 3.31x | 2.56x | 1.81x |

## Okuma (beklenti DOGRULANDI)
- **MAGNITUDE neredeyse-ulasilir**: post_tight ~5-10 yilda yalniz ~1.15-1.62x carpan ister. Yani #2'nin
  darbogazi POWER-MAGNITUDE DEGIL. (Kosulsuz t=1.48 zaten 2'ye yakin; sqrt(n) ile birikir.)
- **Baglayan-kisit = ISARET-COHERENCE**: en-guclu leg SIGN-UNSTABLE (rejim-bagimli yon). Surpriz-kosullama
  TAM-OLARAK bunu duzeltebilecek mekanizma: surpriz-ISARETI (gerceklesen vs konsensus) -> tepki-ISARETI.
  Kosulsuz etki yon-tutarsizken, surpriz-isaretine kosullamak yonu tutarli kilabilir. #2'yi
  "umutsuz" degil "gercek-forward-bahis" yapan budur.
- **AMA offline OLCULEMEZ**: panel surpriz-buyuklugu tasimaz (yalniz tarih, ustelik rule-proxy/exact-degil).
  Hem kosullu-etki hem isaret-stabilitesi yalniz konsensus-surpriz verisiyle test-edilir.
- **DURUST caveat**: kosulsuz etki Bonferroni-gecmiyor -> multiple-testing artifakti olabilir.
  Modest gereken-carpan, gercek bir kosullu-etkinin VAR oldugunu GARANTI ETMEZ.

## Siralama: #2 yine #1'in ALTINDA
- **#1 (daily-PEAD)**: MEVCUT semanin TEK fetch'i (publication_date hazir), L8-L11 ile 4-eksen
  TAM-KURULU + offline-dogrulanmis. Bir-komutla calisir.
- **#2 (surpriz-makro)**: konsensus-surpriz verisi AYRI (muhtemelen lisansli kaynak), kosulsuz-etki
  Bonferroni-gecmez. Magnitude-yakin + sign-coherence-vaadi VAR ama veri-kapili.
-> L12, #2 siralamasini SAYISAL gerekceyle TEYIT eder: magnitude yakin, odul sign-coherence, ama #1'in altinda.

## Hukum: FORWARD-RANK-RATIONALE-VIEW
Yeni-edge iddiasi YOK. #2'nin siralama-gerekcesi artik olculmus: makro-sinifi magnitude'da
umutsuz-degil (~1.1-1.6x carpan yeter), gercek-deger ISARET-coherence'da (surpriz-kosullamanin
saglayabilecegi sey), ama konsensus-surpriz verisi olmadan test-edilemez -> tam-kurulu tek-fetch
#1'in altinda kalir. N<=1 (sentez). L12 ARSIVLENDI. Forward-siralama #1>>#2 artik SAYISAL-gerekceli.
