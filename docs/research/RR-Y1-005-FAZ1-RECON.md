# RR-Y1-005 -- FAZ-1 RECON RAPORU (Builder)

**Tip:** RECON / fizibilite. KOD-YOK, BUILD-YOK, KARAR-YOK. Sadece oku + olc + raporla + oner.
**Girdi:** RR-Y1-005-TEST-MOTORU-TASARIM.md (donmus-tasarim v0.1, 4 Haz 2026).
**Tarih:** 2026-06-04. **Clone:** local-build (panel verisi mevcut, olcumler burada kosuldu).
**Olcum kanidi:** tum sayilar read-only bir gecici-script ile uretildi (repoya yazilmadi); kaynak parquet
yollari + satir referanslari asagida.

> Hukum ozeti: tasarimin metodolojik iskeleti (split-taksonomisi, PBO/DSR, golden-fixture+synthetic-null,
> config-seffaflik) VERI ve CODEBASE ile UYGULANABILIR. Iki kavramsal duzeltme spec'i etkiler:
> (S1) "datahub (D-199/200)" yanlis-etiket -- panel kaynagi DataHub degil, clean_universe+snapshots
> parquet katmani; (S2) sarmalanacak tek "5-gate harness" YOK -- motor PARALLEL kurulmali. Geri kalan
> bulgular dial-tanimi netlestirmesi (embargo-h sinyale-gore) ve guc-uyarilari (aylik temporal-CPCV ince).

---

## A. CODEBASE ENVANTERI

### A1 -- Mevcut harness: wrap mi, parallel mi? (strangler)
**Bulgu:** Sarmalanabilecek TEK bir "5-gate harness" fonksiyonu/modulu YOK. Tasarimdaki "5-gate", kodda
bir modul degil bir DISIPLIN: "bes duvar" (short-side-only / turnover-cost / regime-instability /
illiquid-only / significance-power). Kanit: `lab-demo-clone1/notes/HANDOFF.md:95` ("the five walls hold
on the construction axis as they did on selection/timing/event/price-action"). Bu disiplin her scriptte
(her D-NNN ve C-N kendi `main()`'inde) YENIDEN-uygulanir; ortak olan PRIMITIVELER:
- `src/screening/d203_clean_universe_test.py` (eng): `clip_clean_returns`, `monthly_rebalance_dates:93`, universe.
- `src/screening/d204_hi52_stress.py`: `per_stock_cost_panel:100`, `_MICRO_RT:43` (=13.84 bps).
- `src/screening/realistic_cost.py`: `round_trip_cost:186`, `combine_round_trip:87` (D-207 cekirdegi).
- `lab-demo-clone1/harness/clib.py`: `load_panels:38`, `liquid_at:55`, `continuous_basket:61`,
  `per_name_round_trip:78`, `daily_matrix:93`, `sim_cadence/sim_band/sim_dynamic:107-193`,
  `real_cagr/regime_real_cagr:203-228`, maliyet-konvansiyonu `_cost_of_reset:102` (`0.5*|w-tw|*rt`).
- C9 istatistik primitifleri: `c9._nw_t` (HAC NW-t), `c9._exact_binom_one_sided`.

**Oneri (C-yetkisi):** Motoru PARALLEL kur -- bu primitifleri READ-ONLY tuketen yeni bir modul. Wrap
edilecek monolit olmadigi icin "wrap mi parallel mi" sorusunun cevabi zorunlu olarak PARALLEL'dir; bu
ayni zamanda strangler-uyumlu (committed motorlar D-203..213 + C7/C8/C9 hic dokunulmadan kalir, tasarim
§9 niyetine birebir uyar). Motorun `panel/sinyal/split_spec/dial_config -> ciktivektoru` arayuzu YENI
yazilir; en yakin yeniden-kullanilabilir yuzey `clib` + `eng` + `d204` + `realistic_cost`'tur.

### A2 -- cc_cont / C12 golden-fixture erisilebilir + donmus mu?
**Bulgu:** EVET, hem donmus hem byte-deterministik -- §8.1 golden-fixture olarak DOGRUDAN kullanilabilir.
- Donmus Stage-0: `lab-demo-clone1/stage0/STAGE0_C12_walkforward_microstructure.json` (`frozen_before_results=true`,
  `date_frozen=2026-06-04`, 6-kosulu sayisal `keep_bar`).
- Sonuc artefakti: `lab-demo-clone1/results/c12_walkforward_microstructure_results.json` -- kesin sayilar
  (ALL): `gross_active_ann=+0.226676`, gross `NW-t=+6.928`, `net_active_ann=-0.220398`, net `NW-t=-6.275`,
  kazanan combo `cc_cont` (11/11 fold), `mean_selection_tax=+0.000203`, `null_pctile_real=1.0`,
  `mirror_net=-0.002497`, `frac_folds_net_pos=0.1818`, `regime_gross pre=0.00062/post=0.00097`,
  `n_folds=11`, `n_pooled_days=1375`, `mean_rt_bps=46.78`.
- Reprodüksiyon: `PYTHONPATH=. python lab-demo-clone1/harness/c12_walkforward_microstructure.py`.
- Determinizm DOGRULANDI: null-bacagi seed-pinli -- `c12...py:250 rng=np.random.default_rng(NULL_SEED+s)`.
  Yani null-percentile dahil tum ciktilar tekrar-uretilebilir.

**Onemli not (C-yetkisi):** Golden-fixture'in VERI KAYNAGI ana panelden FARKLI. C12, `data/snapshots/
trend_v1_ohlcv_2019-01-01_2026-04-30.parquet`'i kullanir (88 survivor isim, `n_days=1910`, bitis 2026-04-29);
ana arastirma paneli (`clean_universe/adjusted_prices`) 681 isim / 1848 gun / bitis 2026-05-26. Golden-fixture
testi OHLCV snapshot'ini pinlemeli (clean_universe panelini DEGIL). STAGE0_d213'teki
`snapshots_content_hash_sha256_prefix` + engine-hash-assert kalibi (asagida A5) tam da bunun icin hazir;
fixture'a aynen tasinabilir.

### A3 -- realistic_cost (D-207) cagri-arayuzu
**Bulgu:** `src/screening/realistic_cost.py:186 round_trip_cost(close, adv, order_value, window,
lambda_kyle, quoted_spread) -> dict`; birlestirici `combine_round_trip:87`. Spread hiyerarsisi:
quoted (`data/clean_universe/d207_quoted_spread_panel.parquet`) > Roll > tier-floor. Labolar bunu
DOGRUDAN cagirmaz; `d204.per_stock_cost_panel:100` ile aylik per-isim maliyet paneli kurar, `clib.
per_name_round_trip:78` bunu median per-isim round-trip + `mean_rt_bps`'e sarar. Gunluk kitap maliyeti =
`sum_i 0.5*|w_i - tw_i| * rt_i` (`clib._cost_of_reset`), C12 gunluk olarak uygular.
**Oneri:** Motor D-207'yi AYNI `clib.per_name_round_trip` (quoted-primary) yolundan tuketsin -> sayilar
kardes-laboratuvarlarla birebir tutar. Yeni maliyet kodu gerekmez; read-only import.

### A4 -- Datahub (D-199/200): panel formati, frekans-donusumu, survivorship  **[SPEC-ETKILER: S1]**
**Bulgu (kavramsal duzeltme):** Tasarimin "datahub (D-199/200)" dedigi `src/data/data_hub.py`, bir
CANLI-API ROUTER'idir (yfinance/evds/kap/isyatirim...). `docs/DATA_HUB.md:599` aciktan soyler:
"tam ORM/data warehouse DEGIL -- kalici depolama, sorgu motoru, sema versiyonlama YOK". Donus tipleri
kaynaga-ozgu canli/snapshot nesneler; look-ahead-safe arastirma-paneli DEGIL. Yani motorun `panel`
girdisi DataHub tarafindan SERVIS EDILMEZ.

**Gercek panel = parquet katmani:**
- `data/clean_universe/adjusted_prices_2019_2026.parquet` -- LONG sema, kolonlar:
  `[date, symbol, close, vwap, value_tl, volume, bist100, bist30, ca_code, adj_factor, adjusted_close,
  adjusted_vwap, tr_index_gross, tr_index_net]`. 681 isim, 1848 gunluk satir (2019-01-02..2026-05-26).
  `pivot(date x symbol)` ile genis-matris (clib.load_panels). **tr_index_gross/net** = per-isim
  TOPLAM-getiri endeksleri MEVCUT (temettu-dahil; D-211/D-213'un price-only XU100 sorununu isim-seviyesinde cozer).
- `data/clean_universe/d207_quoted_spread_panel.parquet` (maliyet), `fundamentals_2019_2026.parquet`
  (AYLIK), `pit_membership_2019_2026.parquet` (point-in-time endeks uyeligi -> survivorship kontrolu).
- `data/snapshots/*.parquet` -- OHLCV (trend_v1_ohlcv), exposure (xu100/tufe/tlref/gold),
  makro (apifon4/enfbek), earnings_dates, macro_event_dates.

**Frekans-donusumu:** datahub ozelligi DEGIL; scriptlerde ad-hoc (gunluk->aylik rebal: `eng.
monthly_rebalance_dates`; fundamentals zaten aylik). Motorun kendi frekans-adaptoru olmali.
**Survivorship (cagri-seviyesinde dogrulanabilir mi? EVET):** olcum -> 681 ismin **73'u** panel-bitiminden
>20 gun once kapaniyor (in-sample delisted, korunmus) = survivorship-temiz; `pit_membership` PIT-uyelik
verir; `clib.continuous_basket` kapsama-zorlar.
**Oneri (C-yetkisi):** Spec'te panel-kaynagini "clean_universe + snapshots parquet katmani" diye
yeniden-adlandir; DataHub yalniz canli-fetch. Motorun veri-arayuzu = genellestirilmis bir `load_panels`
adaptoru. (S1.)

### A5 -- Stage-0 sistemi: §6 semasi mevcut semayi kaldirir mi, genisletir mi?  **[SPEC-ETKILER: S3]**
**Bulgu:** Mevcut Stage-0 dosyalari BESPOKE / FREEFORM JSON; ortak/tipli SEMA YOK. Iki aile:
- Production `docs/yol1/STAGE0_dNNN.json` (or. `STAGE0_d213.json`): zengin, spece-ozel alanlar
  (`predictor_FROZEN`, `keep_bar_FROZEN_all_required`, `snapshots_content_hash_sha256_prefix` +
  engine-hash-assert guard, `strangler_constraints`). Engine, dosya yoksa KOSMAYI REDDEDER (d213).
- Lab `stage0/STAGE0_CN.json`: freeform (candidate / frozen_before_results / kepbar-prose).

Hicbiri tasarim §6'nin generik makine-okur semasini (`tutunma_noktasi/split_modu/psi/embargo_h/...`)
karsilamaz; bu alanlar bugun ORTAK-VALIDE bir sema olarak YOK.
**Oneri:** §6 = ADDITIVE YENI sema (kaldirilacak kati-sema yok). "Makine-okur, motor split-modunu buradan
secer" vaadi icin (a) bugun olmayan kucuk bir sema/validator, (b) STAGE0_d213'te kanitlanmis content-hash
snapshot-guard kalibinin yeniden-kullanimi gerekir (bu kalip §8 anti-slop reprodüksiyonuna birebir hizmet
eder). YAML yerine JSON oneririm (mevcut tooling + hash-guard ile uyum). (S3.)

---

## B. VERI-FIZIBILITE (olculmus)

### B6 -- embargo-h: otokorelasyon-sonum-uzunlugu  **[SPEC-ETKILER: S4]**
Olcum (60 likit isim, gunluk, 2019-2026; ortalama per-isim ACF):

| Sinyal | lag1 | lag2 | lag3 | lag5 | lag8 | lag10 | lag21 | sonum |
|--------|------|------|------|------|------|-------|-------|-------|
| Gunluk clipped getiri (=C12 cc) | +0.099 | +0.039 | +0.039 | +0.029 | -0.006 | ~0 | +0.002 | ~1-2 gun |
| 21g trailing-sum momentum (ortusen) | +0.961 | -- | -- | +0.776 | -- | +0.543 | +0.039 | ~window (21) |

**Hukum:** embargo-h TEK-SABIT DEGIL; sinyale-ozgu. Olculmus kural: h ~= ozelligin bellek-uzunlugu;
nokta-anlik gunluk ozellik icin ~1, ortusen/trailing-window ozellik icin ~window. Tasarim §3.4'u
("olculen-sayi, sinyale-gore") DOGRULAR. Dial #4 default'u: `h := sinyalin construction-window'u (h>=1)`.
Dogrudan uygulanabilir; ama §5 tablosundaki "embargo (h)" tanimi "tek sayi" izlenimi vermemeli (S4).

### B7 -- isim-bolmesi fizibilitesi (§3.3)
Olcum (88 ay-sonu):
- LIQUID (trailing-63g median value_tl >= 1e7): per-ay **min=44, median=77, max=171**. Ikiye-bolununce
  median'da **arm basina ~38 isim**.
- TUM-isim (fiyati olan): per-ay **min=357, median=472, max=606** -> arm basina ~236.

**Hukum:** Gunluk Mod-A isim-bolmesi FEASIBLE. LIQUID floor'da ~38/arm (z-tilt icin calisir; decile
sortlari icin ince -> ~4 isim/decile). TUM-isimde bol. Aylik isim-sayilari ayni (uyelik aylik-stabil)
-> aylik Mod-A da feasible (tasarim §3.6 ile tutarli).
**Sub-teshis (C-yetkisi):** 1e7 floor'da derin (decile) cross-sectional sortlar gurultulu. Oneri:
LIQUID split'te TERCILE kullan ya da yumusak "top-N-by-ADV" floor -> her arm >=50 isim. Yeni dial:
"split-arm liquidity floor + sort-depth". (S5.)

### B8 -- faktor-notrleme verisi (§3.5)
Olcum -- mevcudiyet:
- **MARKET (beta):** `data/snapshots/exposure_d187_xu100.parquet` MEVCUT -> market-beta notrleme GUNLUK
  feasible. §3.5'in ZORUNLU minimumu -> KARSILANIYOR.
- **SIZE:** `fundamentals.mktval` MEVCUT (AYLIK).
- **SEKTOR:** degoran arsivi MEVCUT (`data/bist_datastore_archive/fundamental_ratios`, **229 aylik zip**,
  2019-07..2026-04) -> `lab-demo-clone1/harness/sector_map.py` (PIT, survivorship-temiz).
- **VALUE (bonus):** pe/pbv/bm/ey/dy/dyld MEVCUT (AYLIK).

**Hukum:** market-beta notrleme (Mod-A zorunlu) TAM FEASIBLE gunluk. Size/sektor/value notrleme feasible
ama AYLIK-granul (gunluk split'te betalar gunluk, size/sektor tiltleri aylik adimlar). Sektor kapsami
2019-07 baslar (fiyat 2019-01) -> kucuk sol-kirpma. Veri DUVARI yok; derinlik (market-only vs +size+sector)
guce-bagli bir dial karari, mevcudiyet sorunu degil.

### B9 -- CPCV (N,k) gozlem-butcesi (§3.4/§4.1)
Olcum: gunluk obs = **1848** (OHLCV fixture'da 1910).
- **Gunluk:** N=10 -> ~184 gun/blok; k=2 -> **45 path**. N=12,k=2 -> **66 path**. CPCV/PBO icin saglikli;
  embargo (h~1-21g) bir 184g blogun <=~%10'unu yer -> sorun degil.
- **Aylik:** 88 ay-sonu. N=8 -> ~11 ay/blok; k=2 -> 28 path ama her test-blogu ~11 ay ve embargo (1-2 ay)
  isirir -> INCE / guc-fakiri.

**Hukum:** temporal-CPCV (Mod B) gunluk IYI-GUCLU, aylik guc-fakiri -> tasarim §3.6'yi DOGRULAR
(aylikta Mod-A isim-bolmesi tasimali). PBO/DSR gunluk hesaplanabilir; aylik PBO genis guven-araligi.

---

## C. ACIK ALT-TESHISLER + ONERILER (the maintainer C-yetkisi; karar VERMEZ)

1. **datahub yanlis-etiket (A4):** DataHub canli-router; motorun paneli clean_universe+snapshots
   parquet'ten gelir. Oneri: spec'te panel-kaynagini yeniden-adlandir, motor veri-arayuzu = genellesmis
   `load_panels` adaptoru. [SPEC S1]
2. **Wrap edilecek harness yok (A1):** bes-duvar disiplini per-script. Oneri: motor PARALLEL, primitifleri
   read-only tuket; bu zaten strangler-uyumlu. [SPEC S2]
3. **Golden-fixture (A2):** seed PINLI (c12...py:250) -> tam-deterministik; KULLANILABILIR. Tek dikkat:
   fixture OHLCV snapshot'ini (clean_universe degil) ve onun content-hash'ini pinlemeli (STAGE0_d213 kalibi).
4. **Split-arm floor (B7):** 1e7'de ~38/arm -> decile gurultulu. Oneri: LIQUID split'te tercile veya
   top-N-by-ADV; her arm >=50 isim. Yeni dial. [SPEC S5]
5. **Total-return getiriler (A4):** clean_universe'de per-isim `tr_index_gross/net` VAR. Oneri: Mod-A
   getirilerini total-return uzerinden kur -> price-only sapmasini onler (D-211/213'un yasadigi sorun).
6. **Sektor sol-kirpma (B8):** sektor 2019-07 baslar. Oneri: sektor-notr testler effective-start 2019-07,
   ya da ilk 6 ay market-only. Kucuk; duvar degil.

---

## SPEC-DEGISTIREBILECEK BULGULAR (Orchestrator bakacak)

- **[S1]** Panel kaynagi = clean_universe + snapshots parquet katmani; DataHub (src/data/data_hub.py)
  canli-router, motorun panel-girdisi DEGIL. (A4)
- **[S2]** Sarmalanacak tek "5-gate harness" YOK; motor PARALLEL kurulmali, primitifleri read-only tuketmeli. (A1)
- **[S3]** §6 Stage-0 semasi YENI+additive (kaldirilacak kati-sema yok); freeform-JSON convention +
  STAGE0_d213 content-hash-guard kalibi ile uzlastir; YAML yerine JSON oner; makine-okur olmasi icin
  bugun olmayan kucuk bir validator gerek. (A5)
- **[S4]** embargo-h tek-sabit DEGIL, sinyal-construction-window fonksiyonu (gunluk-getiri ~1g,
  21g-momentum ~21g). §5 dial #4 tanimi netlestirilmeli. (B6)
- **[S5]** LIQUID isim-bolmesinde arm-floor + sort-depth yeni dial; 1e7 floor'da decile ince (~38/arm). (B7)
- **[S6]** Aylik temporal-CPCV guc-fakiri -> aylik icin Mod-A isim-bolmesi ZORUNLU (oneri-degil-kural). (B9, §3.6)

---

## FIZIBILITE HUKMU (dial-dial)

| Dial / bilesen | Hukum | Dayanak |
|---|---|---|
| #1 psi (durağan-ozellik: rank-IC/sign/magnitude) | UYGULANABILIR | getiriler+fundamentals mevcut (A4,B8) |
| #2 split-modu A/B/A+B | UYGULANABILIR (gunluk her ikisi; aylik yalniz A) | B7,B9 |
| #3 faktor-notrleme | UYGULANABILIR (market gunluk; size/sektor/value aylik, sektor 2019-07+) | B8 |
| #4 embargo-h | UYGULANABILIR; TANIM-REVIZE (sinyale-gore, sabit degil) | B6 |
| #5 CPCV (N,k)+PBO | UYGULANABILIR gunluk (N=10-12,k=2); aylik INCE | B9 |
| #6 DSR | UYGULANABILIR (saf formul) | -- |
| #7 cut-policy ailesi | UYGULANABILIR | B9 |
| §8.1 golden-fixture (cc_cont/C12) | UYGULANABILIR (deterministik, seed-pinli) | A2 |
| §8.2 synthetic-null | UYGULANABILIR (saf) | -- |
| Panel kaynagi (datahub) | REVIZE-GEREKIR (yeniden-adlandir) | A4 / S1 |
| Stage-0 §6 semasi | INSA-GEREKIR (additive validator) | A5 / S3 |

**Veri-duvari:** YOK. Hicbir dial veri-yoklugundan dusmuyor; iki kalem (panel-etiketi, §6-validator) insa/revizyon,
veri-engeli degil. En zayif nokta aylik-frekansta temporal-CPCV gucu (B9) -- tasarimin zaten Mod-A'ya yonlendirdigi yer.

---

## YAPILMAYANLAR (spec siniri)
Kod yazilmadi, motor kurulmadi, test kosulmadi (pytest calistirilmadi), mimari/spec karari verilmedi,
hicbir committed dosya degistirilmedi. Olcumler tek-seferlik read-only bir gecici-script ile uretildi
(OS temp'inde, repoya yazilmadi). Bu rapor docs/research/ altinda yeni bir teslimat dosyasidir;
RESEARCH_REGISTRY.md satiri + spec-karari the project'a birakildi.

*RR-Y1-005 Faz-1 recon -- 2026-06-04. Hukum: tasarim VERI+CODEBASE ile uygulanabilir; 2 kavramsal
duzeltme (panel-kaynagi, parallel-motor) + 4 netlestirme/guc-uyarisi. Veri-duvari yok.*
