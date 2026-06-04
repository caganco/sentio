# RR-Y1-003 -- ASAMA-0 VERI-FIZIBILITE PROBU (reel-faiz timing)

Yol-1-lab envanteri. Sinyal/backtest/model/HUKUM YOK. Sadece veri-gercekleri.
Tarih: 2026-06-04. Probe tek-kullanimlik (motora commit edilmedi). N<=3 sayaci HARCANMADI.

Pencere (KILITLI, baglamdan): bagimli XU100 TL-reel temiz-lokal yalniz 2019-01..2026-04
(D-210 gercegi). Bu prob SADECE reel-faiz prediktorunun 2019-2026 fizibilitesini sorar; 2010+
GEREKMEZ.

Kaynak konum (mutlak-yol commit edilmez; placeholder):
  <repo-root>/data/snapshots/                (frozen parquet snapshot'lari, tracked)
  EVDS3 API: https://evds3.tcmb.gov.tr/igmevdsms-dis/  (API-KEY bazli; CAPTCHA-Datastore DEGIL)

---

## 0. ON-NOT: API-KEY DURUMU (otonom test-pull yapilabildi mi?)

- Lokal `.env` dosyasinda **EVDS_API_KEY YOK** (mevcut, 46 byte, EVDS satiri 0).
  -> Bu prob, EVDS'ye **CANLI otonom test-pull YAPAMADI** (auth imkansiz).
- ANCAK ayni kod-tabaninda **onceden-calistirilmis canli bir EVDS testi** mevcut:
  `scripts/test_evds3_connection.py` -> `docs/research/RR-021-live-test-results.md`
  (test zamani **2026-05-25 19:55 UTC**, o-an-gecerli bir key ile, auth header='key', HTTP 200).
  Asagidaki "CONFIRMED-ACTIVE" damgalari **o testten** gelir (kod gercekten-veri-donuyor kanit).
- ONEMLI NITELIK: RR-021 testi **400-gunluk lookback** kullandi -> yalniz SON-VERI + recency
  kanitlar; **2019'a-kadar-tam-kapsam ISPATLAMAZ**. 2019-2026 tam-kapsam dogrulamasi icin
  key + 2019-01..2026-04 pull GEREKIR (bkz. PULL-SPEC, sec.5). 2019-kapsam asagida nerede
  "CIKARSAMA" ise oyle damgalandi (kanit-degil).

---

## 1. NOMINAL-FAIZ SERISI -- 2019-2026 temiz + PIT-guvenli var mi?

**EVET (EVDS-API ile; LOKAL rate-level YOK).** PIT-AVANTAJ: faiz-degisimi (PPK + gunluk
fonlama/TLREF) ayni-gun kamuya-acik -> **nominal-faiz T+0-knowable** (D-211'in ~6hf-gecikme
handikabi nominal-bacakta YOK).

### 1a. Aday EVDS kodlari (RR-021 canli-test bulgusu)

| Aday kod | aciklama | frekans | RR-021 durum (2026-05-25) | son-veri / son-deger | PIT |
|---|---|---|---|---|---|
| `TP.APIFON4` | TCMB agirlikli-ort. fonlama maliyeti (AOFM) | gunluk | **CONFIRMED-ACTIVE** | 25-05-2026 / 40.00 | T+0 |
| `TP.BISTTLREF.ORAN` | TLREF gecelik referans faiz -- ORAN (rate-level) | gunluk | **CONFIRMED-ACTIVE** | 22-05-2026 / 39.995 | T+0 |
| `TP.API.REP.ORT.G1` | repo ort. gecelik | gunluk | ACTIVE (lookback'te seyrek, 5 obs) | 2026-4 / 40.00 | T+0 |
| `TP.TCMB.PFAIZ` | (direktif-adayi, politika faizi) | ? | **UNVERIFIED** -- katalogda YOK, HIC test-edilmedi | -- | -- |
| `TP.FAIZ.PYUVDL` | eski TLREF kodu | -- | **DEAD** (HTTP 400) | -- | -- |

- **`TP.TCMB.PFAIZ`** (direktifin birincil-adayi) yalniz `src/data/evds_client.py` docstring-
  orneginde gecer; RR-021 katalogunda YOK, hicbir canli-testte denenmedi -> **TEYITSIZ**.
  Pratik-sonuc: redundant; ayni-amaca-hizmet-eden **CONFIRMED-ACTIVE** iki seri (APIFON4,
  BISTTLREF.ORAN) zaten var, dolayisiyla PFAIZ dogrulanmasa-da nominal-bacak fizibil.
- **Onerilen birincil nominal seri (Stage-0 lock-adayi):** `TP.APIFON4` (politika-fonlama
  maliyeti, T+0, gunluk) VEYA `TP.BISTTLREF.ORAN` (piyasa gecelik faiz, T+0). Ikisi-de
  CONFIRMED-ACTIVE; ikisi-de aylik-resample edilebilir.

### 1b. LOKAL nominal-faiz?

- **LOKAL rate-level seri YOK.** `data/snapshots/` icinde faiz-orani snapshot'i yok
  (`faz0_macro_aux` yalniz `usdtry`; rate-kolonu yok).
- Tek faiz-ilintili lokal: `exposure_d187_tlref.parquet` (`TP.BISTTLREF.KAPANIS`,
  return-INDEX; rate-level DEGIL). KRITIK NITELIK: degerler **yalniz 2022-07-01'den**
  basliyor (oncesi NaN; ilk-degisim 2022-07-04 OLCULDU). -> **2019-2022'yi KAPSAMIYOR**
  ve zaten endeks (rate degil). 2019-2026 nominal-faiz prediktoru olarak **OLDUGU-GIBI
  KULLANILAMAZ**.
- Sonuc: nominal-faiz 2019-2026 icin **EVDS-pull ZORUNLU** (APIFON4 / BISTTLREF.ORAN).

---

## 2. ENFLASYON BACAGI (reel-faiz = nominal - enflasyon)

### 2a. GERCEKLESEN (ex-post) CPI -- LOKAL, KESIN

| olcum | bulgu |
|---|---|
| seri | `TP.FG.J0` (TUFE) |
| lokal-dosya | `data/snapshots/exposure_k3_d192_tufe.parquet` (+ .meta.json) |
| kapsam | **2010-01-01 .. 2026-05-15** (5979 gozlem; gunluk-ffill cumprod) |
| 2019-2026 | **TAM KAPSAR** |
| YoY turetimi | EVET (aylik index -> 12-ay YoY veya MoM, trivially) |
| EVDS-teyit (RR-021) | CONFIRMED-ACTIVE (`TP.FG.J0`, aylik, son 2026-1); alternatif `TP.FE.OKTG01` de ACTIVE |
| yayin-gecikme | TUIK CPI, ay-sonrasi 3. is-gunu yayinlanir -> ay-t-sonu karar-aninda en-guncel-bilinen CPI = ay (t-1) -> efektif ~6hf bayat (~t+45g) |

ex-post enflasyon bacagi **sifir-pull, lokal-hazir**.

### 2b. BEKLENEN (ex-ante) ENFLASYON BEKLENTISI -- KRITIK, CONFIRMED-ACTIVE

Direktif bu serinin varligini "BELIRSIZ (kod-bilinmiyor)" saymisti. **BULUNDU + KANIT VAR:**

| olcum | bulgu |
|---|---|
| seri | **`TP.ENFBEK.PKA12ENF`** -- "12-ay ileri enflasyon beklentisi" (TCMB Piyasa Katilimcilari Anketi) |
| RR-021 durum (2026-05-25) | **CONFIRMED-ACTIVE** (aylik; son-veri **2026-5** / son-deger **23.82**) |
| lokal | YOK (snapshot degil) -> EVDS-pull gerekir |
| frekans | aylik |
| yayin-gecikme | TCMB PKA ~ay-ortasi yayinlanir -> ay-t-sonu karar-aninda ay-t-okumasi BILINIR; CPI'dan KISA (~t+15g, daha-az-bayat) |
| 2019-kapsam | **CIKARSAMA** (anket aylik ~2013'ten beri yayinlaniyor; tam-2019-kapsam key+pull ile dogrulanmali) |

-> **ex-ante reel-faiz ipligi MESRU** (seri mevcut + canli-kanit). D-211'in ~6hf-gecikme-tuzagindan
kacis-sansi burada (nominal T+0 + beklenti ~t+15g).

---

## 3. PIT / LOOK-AHEAD ENVANTERI (her iki reel-faiz varyanti icin knowable-tarih)

| varyant | tanim | knowable-lag | gecikmeyi-dayatan bacak |
|---|---|---|---|
| **ex-post** reel-faiz(t) | nominal(t, T+0) - CPI_YoY(t, ~t+45g) | **~t+45g** (~6hf) | CPI (TUIK ay-sonrasi-3.isgunu; ay-t-sonu en-guncel = ay-(t-1)) |
| **ex-ante** reel-faiz(t) | nominal(t, T+0) - beklenti(t, ~ay-ortasi) | **~t+15g** | PKA anketi (ay-ortasi); CPI'dan daha-taze |

- Nominal-bacak HER-IKI varyantta T+0-knowable (PPK/fonlama/TLREF ayni-gun-acik) -> gecikmeyi
  enflasyon-bacagi belirler.
- ex-ante varyant **daha-az-bayat** (~t+15g vs ~t+45g): D-211 gecikme-handikabina karsi yapisal-avantaj.
- Stage-0 lag-lock onerisi (HUKUM-DEGIL, yalniz fizibilite-notu): ex-post -> lag>=1-ay (CPI bayatligi);
  ex-ante -> ay-ici-knowable, lag~0-1-ay. Kesin-lag Stage-0'da donar.

---

## 4. OZET TABLO (her-soru -> cevap; hicbir hukum/sinyal-yorumu YOK)

| # | Soru | Cevap |
|---|---|---|
| 1 | Nominal-faiz 2019-2026 temiz+PIT-guvenli var mi? | **EVET (EVDS-API)**. `TP.APIFON4` + `TP.BISTTLREF.ORAN` CONFIRMED-ACTIVE (RR-021), T+0-knowable. LOKAL rate-level YOK. |
| 1b | Direktif-adayi `TP.TCMB.PFAIZ` calisiyor mu? | **TEYITSIZ** (katalogda yok, hic test-edilmedi). Redundant -- onaylanmis alternatif var. |
| 1c | TLREF lokal kullanilabilir mi? | HAYIR (return-index, rate-degil; degerler yalniz 2022-07+; 2019-2022 NaN). |
| 2a | ex-post CPI lokal + 2019-2026 + YoY? | **EVET, KESIN** -- `exposure_k3_d192_tufe` (TP.FG.J0), 2010-2026, YoY turetilir. |
| 2b | ex-ante enflasyon-beklentisi serisi var mi? | **EVET, CONFIRMED-ACTIVE** -- `TP.ENFBEK.PKA12ENF` (12-ay-ileri, aylik, ~ay-ortasi). Lokal-degil (pull gerek). Ex-ante-iplik MESRU. |
| 3 | PIT knowable-lag? | ex-post **~t+45g** (CPI dayatir); ex-ante **~t+15g** (PKA daha-taze). Nominal T+0. |
| 4 | Otonom canli-pull yapildi mi? | HAYIR -- lokal `.env`'de EVDS_API_KEY yok. Kanitlar RR-021 (2026-05-25) testinden. Tam-2019-kapsam re-pull gerektirir (sec.5). |

**Net fizibilite:** reel-faiz timing ipligi VERI-FIZIBIL. Gerekli ek-veri: 2 EVDS serisi
(nominal: APIFON4 veya BISTTLREF.ORAN; ex-ante: ENFBEK.PKA12ENF) -- ikisi-de kod-dogrulanmis,
yalniz API-KEY + 2019-2026 pull eksik. ex-post bacak (CPI) zaten lokal-hazir. CAPTCHA-Datastore
GEREKMEZ (EVDS API-KEY bazli).

---

## 5. PULL-SPEC (lokal-olmayan 2 seri; key + 2019-kapsam dogrulamasi icin)

Onkosul: ucretsiz EVDS key (https://evds3.tcmb.gov.tr/) -> `.env` icine `EVDS_API_KEY=...`.
Mevcut altyapi: `src/data/evds_client.fetch_series_df(code, start_date=, end_date=)`
(base URL + DD-MM-YYYY + header='key' ZATEN dogru, RR-021/D-151 invariant).

| seri | kod | start | end | frekans | resample | dogrulanacak |
|---|---|---|---|---|---|---|
| nominal-faiz (birincil) | `TP.APIFON4` | 01-01-2019 | 30-04-2026 | gunluk | aylik-son (ay-sonu) | 2019-01 obs donuyor mu? bosluk? |
| nominal-faiz (alt) | `TP.BISTTLREF.ORAN` | 01-01-2019 | 30-04-2026 | gunluk | aylik-son | 2019-01 kapsam |
| ex-ante beklenti | `TP.ENFBEK.PKA12ENF` | 01-01-2019 | 30-04-2026 | aylik | aylik (oldugu-gibi) | 2019-01 obs + aylik-sureklilik |

Pull sonrasi (Stage-0-ONCESI, ayri adim): her seri icin gercek-kapsam-tarihi, bosluk,
yayin-gecikme tekrar-RAPORLA; ham-veri snapshot'a donar (content-hash), **CI'a girmez**.
Bu prob hicbir ham-veri cekmedi/yazmadi.

---

## 6. DISIPLIN / STRANGLER

- Committed motorlara (d203/204/205/209/211 + realistic_cost + thresholds + evds_client +
  ballast) **SIFIR-dokunus**. Yeni src-modulu EKLENMEDI. Probe motora commit-EDILMEDI
  (yalniz bu envanter-artifact).
- Bu prob CANLI-pull YAPMADI (key yok); bulgular mevcut lokal-snapshot meta'lari +
  onceki RR-021 canli-test-raporu + kod-katalogu okunarak derlendi. Ham-veri CI'a girmedi.
- Mutlak-yol commit-edilmedi (placeholder). ASCII.

## 7. ONCEDEN-ILAN BEKLENTI vs OLCUM (kutlama-yok)

| onceden-ilan | olcum |
|---|---|
| CPI kesin-lokal | DOGRULANDI (exposure_k3_d192_tufe, 2010-2026). |
| Nominal-faiz EVDS ~50/50 | NETLESTI: direktif-adayi PFAIZ teyitsiz AMA 2 alternatif (APIFON4, BISTTLREF.ORAN) CONFIRMED-ACTIVE -> nominal-bacak fizibil. |
| Beklenti-anketi BELIRSIZ | **BULUNDU + CONFIRMED-ACTIVE** (`TP.ENFBEK.PKA12ENF`) -> ex-ante-iplik MESRU (beklenenden iyi sonuc, kayit-altinda). |

Sonuc duz kaydedildi; hukum/sinyal-yorumu YOK (Asama-0).
