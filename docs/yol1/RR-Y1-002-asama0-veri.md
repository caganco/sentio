# RR-Y1-002 -- ASAMA-0 VERI-FIZIBILITE PROBU

Yol-1-lab envanteri. Sinyal/backtest/model YOK. Sadece veri-gercekleri.
Tarih: 2026-06-04. Probe tek-kullanimlik (motora commit edilmedi).

Kaynak konum (mutlak-yol commit edilmez; placeholder):
  <repo-root>/data/bist_datastore_archive/   (git-ignored, ana-repodan symlink)
  <repo-root>/data/snapshots/                (frozen parquet snapshot'lari, tracked)

---

## 0. ON-NOT: DOSYA-SAYISI BEKLENTISI

Spec "~7264 lokal dosya" varsaydi. OLCULEN gercek:
- bist_datastore_archive TOPLAM: **2128 dosya** (9 alt-klasor).
- 7264 ile uyusmuyor. Olasi aciklama: 7264 baska bir kapsam (clean_universe
  parquet + tum repo data/, veya eski sayim). Bu prob yalnizca arsivi saydi.
- Alt-klasor dagilimi:
    foreign_flow ......... 351   prices_official ...... 461
    fundamental_ratios ... 229   prices_weekly ........ 546
    short_selling ........ 213   viop ................. 328
    corporate_actions .... 0     dividends ............ 0
    index_components ..... 0
- BOS klasorler (0 dosya): corporate_actions, dividends, index_components.
  (Sahiplik/kompozisyon ve temettu zaman-serisi LOKAL YOK.)

---

## 1. "3153 YABANCI ISLEMLER" LOKAL MI?

**KISMI-EVET (onemli nitelikle).**

Lokalde bir **yabanci-yatirimci islemleri** veri seti VAR: `foreign_flow/`.
ANCAK bu set AYLIK-agregedir; eger "3153" Datastore urunu GUNLUK bir seriyi
ifade ediyorsa, GUNLUK granulerlik LOKAL YOK (bkz. asagidaki nitelik).

Urun-kodu eslemesi (3153) KESINLESTIRILEMEDI:
- Lokal dosyalar urun-kodu metadata'si TASIMIYOR. Dosya-adi "yabanci",
  .xls basligi "YABANCI YATIRIMCI ISLEMLERI" -- icerik 3153'un tarifine
  uyuyor ama "3153" damgasi dosyada/icerikte hicbir yerde gecmiyor.
- Datastore urun-katalogu offline erisilebilir degil; filename -> 3153
  esleme catalog olmadan dogrulanamaz. (CAPTCHA-pull OTONOM DENENMEDI.)

---

## 2. LOKAL SETIN GERCEKLERI (foreign_flow)

| Boyut            | Deger |
|------------------|-------|
| Format           | aylik `.zip` -> icinde TEK `.xls` (eski-Excel; xlrd gerekir) |
| Dosya adi        | `yabanciYYYYMM.zip` (orn. `yabanci202604.zip`) |
| Tarih-araligi    | **1997-01 -> 2026-04** |
| Dosya sayisi     | 351 |
| Frekans          | **AYLIK** (gun-bazli satir YOK; bir ay = bir dosya) |
| Granulerlik      | **HISSE-BAZLI** (piyasa-agregat DEGIL) |
| Universe         | ~640 ticker, segment alt-basliklariyla (orn. "YILDIZ PAZAR") |

Alanlar (her ticker satiri, 8 sutun):
  - col0: ticker (`.E` sonekli, orn. `A1CAP.E`)
  - col1: sirket adi
  - Alis Islemleri: Nominal Deger (TL/lot), Tutar (TL), Tutar (ABD$)
  - Satis Islemleri: Nominal Deger (TL/lot), Tutar (TL), Tutar (ABD$)
  - => 3 alis + 3 satis = 6 numerik alan. NET-akim = (alis - satis) turetilir.

Satir yapisi: basliktan once 6 ust-satir (baslik + segment etiketleri).
Segment alt-basliklari satirlar arasina serpistirilmis -> filtre:
ticker col0 ~ `^[A-Z0-9]{2,6}\.E$`. (Calisan parser: `demo_smart_money/lab/ff_data.py`.)

### BOSLUKLAR / GAPLER
- **1 ay eksik: 2017-04 (`yabanci201704.zip` YOK).** Beklenen 352, mevcut 351.
- Diger tum aylar 1997-01..2026-04 araliginda kesintisiz.

### ZAMAN-DAMGASI / YAYIN KONVANSIYONU (look-ahead icin KRITIK)
- Frekans AYLIK oldugundan **T+0-EOD vs T+1 sorusu satir-seviyesinde GECERSIZ**;
  sinyal ay-seviyesindedir, gun-akimi degildir.
- **Dosya icinde GOMULU yayin-tarihi/zaman-damgasi alani YOK.** Sadece baslikta
  referans-ay var ("2026 YILI NISAN AYI ..."). PIT disiplini DISARIDAN
  uygulanmali.
- Dosya mtime'lari look-ahead icin KULLANILAMAZ: tum yakin dosyalar tek tarihte
  (2026-06-02) toplu-yeniden-cekilmis -> mtime != orijinal yayin-tarihi.
- Onceki bulgu (reference arsiv notu): yayin-gecikmesi **~6 hafta** (Ocak dosyasi
  ~14 Subat'ta yayinlanir). => ay-m sinyali ancak getiri-ay m+2'ye baglanmali.
  Bu KAYIT-ALTINA-ALINAN bir veri-gercegidir; bu probda yeniden olculmedi
  (toplu-cekim mtime'i bozdu), onceki demo_smart_money olcumune dayaniyor.

---

## 3. PULL-SPEC (eger GUNLUK 3153 gerekiyorsa)

Lokal AYLIK yeterliyse pull GEREKMEZ. RR-Y1-002 ipligi GUNLUK yabanci-akim
isterse, the maintainer'in sonraki manuel Datastore session'i (CAPTCHA, ~30g) icin:

- **Urun-kodu:** 3153 (Yabanci Islemler) -- katalogdan GUNLUK varyanti secilir.
- **Tarih araligi:** max-mevcut-gunluk -> 2026 (gunluk seri lokal sifir oldugu
  icin tam-gecmis cekilir; baslangic Datastore'un sundugu en eski gunluk-tarih).
- **Granulerlik:** HISSE-bazli gunluk (aylik zaten lokal; gunluk eksik olan).
- **Gerekli alanlar:** ticker, tarih(gunluk), yabanci alis nominal/TL/USD,
  yabanci satis nominal/TL/USD (aylik setle ayni 6 alan, gunluk frekansta).
- **Basket-order API akisi:** Datastore basket'ine 3153-gunluk eklenir,
  istenen tarih-araligi + alan-seti secilir, order olusturulur, indirilir.
  (Fiyat-pull basket'inde 3153-gunlugun girmis-olup-olmadigi belirsiz;
  girdiyse zaten lokal olabilir -- ASAMA-1'de gunluk-dosya aranarak dogrulanir.)
- **PIT notu:** gunluk seride yayin-konvansiyonu (T+0-EOD mi T+1 mi) Datastore
  alan-aciklamasindan teyit edilmeli; gomulu yayin-tarihi alani var mi bakilir.

---

## 4. EK ENVANTER: LOKAL EVDS KAPSAMI (reel-faiz insasi icin)

**ONEMLI:** EVDS verisi TOPLU-LOKAL-DOSYA olarak DEPOLANMIYOR. Erisim CANLI-API
uzerinden (`src/data/evds_client.py`, `EVDS_API_KEY` gerekir). Lokalde olan
yalnizca TURETILMIS FROZEN SNAPSHOT'lardir (`data/snapshots/*.parquet`).

### 4a. CPI / TUFE
- **Canonical seri-kodu:** `TP.FG.J0` (D-151, RR-021 sec3.3; aylik, 2003=100,
  TP.FE.OKTG01'den daha taze). YI-UFE: `TP.FG.J01` (empirik, metadata-teyitsiz).
- **Frozen lokal snapshot'lar:**
    - `exposure_d187_tufe.parquet`  : 2019-01-01 -> 2026-04-30 (gunluk-render)
    - `exposure_k3_d192_tufe.parquet`: 2010-01-01 -> 2026-05-15 (daha genis/taze)
  - Yapi: `date,value`. AYLIK CPI gunluge ileri-doldurma ile renderlanmis
    (2677 gun icinde sadece 85 deger-degisim-gunu = aylik basamak).
    value 2019-01-01'de 1.0'a normalize (indeks, ham-CPI degil).
- **CPI yayin-gecikmesi (PIT):** TUIK ay-m TUFE'sini ~m+1'in 3. gunu yayinlar.
  Kod-sabiti `EVDS_TUFE_STALE_DAYS = 45`. Yayin-takvimi lokalde:
  `macro_event_dates.parquet` (event_type=`cpi_release`, 88 satir,
  2019-02 -> 2026-05). ANCAK `exact=False`, `source=tuik-rule-proxy`
  => bunlar KURAL-TABANLI TAHMIN (her ayin ~3-4'u), SCRAPE-EDILMIS gercek
  yayin-tarihi DEGIL. PIT icin yeterli yaklasiklik ama "exact" degil.

### 4b. POLITIKA FAIZI
- **Lokal toplu-seri YOK.** Canli-API ornek kodlari: `TP.TCMB.PFAIZ`
  (politika faizi), `TP.APIFON4` (1-haftalik fonlama) -- bunlar evds_client
  docstring'inde ORNEK; uretimde KULLANILAN-teyitli kod degil.
- Politika-faizi uygulamada PPK-karar-haritasi ile takip ediliyor:
  `TCMB_DECISION_MAP` (thresholds.py) + `macro_event_snapshot_builder.py`.
- PPK karar-takvimi lokal: `macro_event_dates.parquet` event_type=`ppk_decision`
  -- ama YALNIZCA 2 satir (2026-04-10, 2026-05-08; `exact=True`, web-scrape).
  **Tarihsel PPK karar-takvimi lokalde EKSIK** (sadece 2 son tarih).
- Sabit: `RISK_FREE_RATE = 0.37` (metrics.py; TCMB Mayis-2026 MPK, hardcoded).

### 4c. GOSTERGE TAHVIL GETIRISI (benchmark bond yield)
- **GERCEK gosterge-tahvil getiri serisi LOKAL YOK.** Sistemdeki "tl_bond_proxy"
  bir GERCEK tahvil-getirisi DEGIL -- CDS-turetilmis SENTETIK proxy:
    `implied_tl_yield (%) = TL_BOND_PROXY_BASE_YIELD + cds_bps/100`
    (`src/signals/local/cds_client.py: get_tl_bond_proxy`).
  => reel-faiz insasi gercek DIBS/gosterge-tahvil getirisi isterse, bu LOKALDE
     YOK; ya CDS-proxy kullanilir ya da EVDS'den uygun seri cekilir (kod yok).

### 4d. TLREF (kisa-vade gosterge / politika-proxy)
- **Canli-API kodu:** `TP.BISTTLREF.KAPANIS` (data_hub ornegi).
- **Frozen lokal snapshot:** `exposure_d187_tlref.parquet`,
  2019-01-01 -> 2026-04-30 (date,value, getiri-indeksi).
  Not: config'e gore TLREF gercek-veri baslangici 2022-07; indeks 2019'a
  proxy-uzatilmis (D204_TLREF_AVAILABLE_START = 2022-07-01).

---

## 5. ASAMA-0 OZET (hukum yok, sadece envanter)

| Soru | Cevap |
|------|-------|
| 3153 (aylik yabanci-akim) lokal mi? | EVET icerik-olarak (1997-01..2026-04), urun-kodu eslemesi teyitsiz |
| 3153 GUNLUK lokal mi? | HAYIR -- gunluk granulerlik yok; pull-spec sec3'te |
| Aylik set: per-stock mi agregat mi? | HISSE-BAZLI, aylik-agrege |
| Aylik set bosluk? | 1 ay eksik: 2017-04 |
| Aylik set gomulu yayin-tarihi? | YOK; sadece referans-ay (~6hf gecikme disaridan) |
| CPI lokal? | Canli-API TP.FG.J0; frozen snapshot 2010/2019 -> 2026 (aylik) |
| CPI yayin-gecikmesi PIT? | ~m+1 gun-3; takvim lokal ama kural-proxy (exact=False) |
| Politika faizi lokal? | Toplu-seri YOK; PPK-harita + 2 scrape-tarih + hardcoded 0.37 |
| Gosterge tahvil getirisi lokal? | GERCEK seri YOK; sadece CDS-turetilmis proxy |
| TLREF lokal? | frozen snapshot 2019->2026 (gercek-veri 2022-07'den) |

ON-ILAN beklenti (~50/50 3153 lokal) sonuc: AYLIK lokal-VAR, GUNLUK lokal-YOK.
Kutlama yok; kayit altina alindi.
