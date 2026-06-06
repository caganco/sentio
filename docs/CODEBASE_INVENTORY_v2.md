# CODEBASE INVENTORY v2.0 — Faz 0 Sonrasi

**Tarih:** 2026-05-31
**Tur:** Salt-okuma envanter (BUILD YOK, kod yazma YOK, src/ dokunulmaz)
**Kapsam:** D-177 → D-184 (PR #124-138) + ARCHITECTURE v2.0 gecis analizi
**Dayanak:**
- ARCHITECTURE.md v2.0 (30 Mayis 2026 — yeni, guncel)
- ARCH_V2_PARADIGM_DECISION.md (30 Mayis 2026, untracked)
- PIVOT_ARCHITECTURE_AUDIT.md (2026-05-29 — Faz 0 oncesi)
- Git log: PR #124-138 commit dosya listesi (dogrulanmis)
- Kaynak dosya okumalari: factor_ic_harness.py, factors.py, snapshot.py,
  faz0_config.py, factor_ic_d184_audit.py, isyatirim_malitablo_fetcher.py,
  PIVOT_ARCHITECTURE_AUDIT.md, ARCHITECTURE.md v2.0, ARCH_V2_PARADIGM_DECISION.md

**Celiski onceligi:** ARCHITECTURE.md v2.0 > ARCH_V2_PARADIGM_DECISION > bu belge > arastirma katmani yorumu
**DEC-039:** Bu belge OLCER/HARITALAR. Trend-test tasarimi + reusable secimi maintainer karari.

---

## SORU 1 — Faz 0 ne ekledi / degistirdi?

### 1.1 Eklenen dosyalar (D-177 → D-184)

#### src/screening/ — TAMAMEN YENI MODUL

| Dosya | Spec | Icerik ozeti |
|-------|----------|--------------|
| `src/screening/__init__.py` | D-177 | Bos init |
| `src/screening/faz0_config.py` | D-177 + D-178 + D-183 + D-184 | Frozen Stage 0 parametreleri: snapshot penceresi, RS/vol window, IC horizons, keep eslikleri (KEEP_HONEST_T_MIN=2.0, KEEP_ICIR_NONOVERLAP_MIN=0.5), ADV floor, FAZ0B degerler, D-184 audit config. thresholds.py'ye kasitli BAGSIZ (olcum parametresi, production esik degil) |
| `src/screening/factors.py` | D-177 + D-178 + D-183 | Saf matematiksel faktor hesabi: `rs_vs_xu100()`, `realized_vol()`, `forward_returns()`, `value_ratios()`. Composite/engine import YOK. `_pit_index()` + `_latest_as_of()` = strict point-in-time look-ahead korumasi |
| `src/screening/snapshot.py` | D-177 + D-178 + D-183 | Frozen parquet snapshot mekanizmasi: `freeze_price_snapshot()`, `freeze_fundamental_snapshot()`, `freeze_fx_snapshot()`, `freeze_par_guard()`, `to_close_panel()`, `resolve_universe_v2()`. Idempotent (parquet var ise yeniden fetch yok) |
| `src/screening/factor_ic_harness.py` | D-177 + D-178 + D-183 | Ana IC harness orchestratori: `run_faz0()`, `run_faz0b()`, cross-sectional Spearman IC, Newey-West HAC, non-overlapping ICIR, honest_t keep/drop karari. Composite/engine import YOK (satir 19) |
| `src/screening/factor_ic_d184_audit.py` | D-184 | CB-017 4-test audit: T1 (D-rejim kosullu IC), T2 (makro reziduel IC OLS+NW-HAC), T3 (coklu test duzeltmesi: Holm-Bonferroni + BH-FDR), T4 (OOS 2019-2023). Composite/engine import YOK (satir 22) |

#### src/data/ — Yeni veri kanali

| Dosya | Spec | Icerik ozeti |
|-------|----------|--------------|
| `src/data/isyatirim_malitablo_fetcher.py` | D-183 | Is Yatirim MaliTablo HTTP kanali: `fetch_malitablo()`, `parse_values()`, `discover_item_codes()`. Chrome UA + warm GET + rate jitter (1-2s). Soft-block sessiz degil (MaliTabloError). Signal/engine import YOK |

#### data/snapshots/ — Frozen veri dosyalari

| Dosya | Spec |
|-------|----------|
| `faz0_prices_{start}_{end}.parquet` + `.meta.json` | D-177 |
| `faz0_v2_prices_2024-01-01_2026-04-30.parquet` + `.meta.json` | D-178 |
| `faz0b_fundamentals.parquet` + `.meta.json` | D-183 |
| `faz0b_fx_usdtry.parquet` + `.meta.json` | D-183 |
| `faz0b_parguard.json` | D-183 |
| `faz0_macro_aux.parquet` | D-184 |
| `faz0_oos_2019_2023_prices_*.parquet` + `.meta.json` | D-184 |

#### docs/factor_ic/ — Stage 0 on-kayitlar + sonuclar

| Dosya | Spec |
|-------|----------|
| `STAGE0_preregistration.json` | D-177 |
| `faz0_results.json` | D-177 |
| `STAGE0_v2_preregistration.json` | D-178 |
| `faz0_v2_results.json` | D-178 |
| `STAGE0_d182_preregistration.json` | D-182 |
| `STAGE0_faz0b_preregistration.json` | D-183 |
| `faz0b_results.json` | D-183 |
| `STAGE0_d184_preregistration.json` | D-184 |
| `d184_lowvol_validation.json` | D-184 |

#### tests/ — Yeni test dosyalari

| Dosya | Spec |
|-------|----------|
| `tests/test_factor_ic_harness.py` | D-177 + D-178 + D-183 (buyuyen kapsam) |
| `tests/test_malitablo_fetcher.py` | D-183 |
| `tests/test_factor_ic_d184.py` | D-184 |

#### docs/research/ + docs/RESEARCH_REGISTRY.md

D-179→D-184 + PR #139 (RR-037) ile eklendi:
RR-028 → RR-037 (TMS 29, USD fizibilite, MaliTablo tutarlilik, kaynak envanteri, smart money veri erisim).
Detay: `docs/RESEARCH_REGISTRY.md`.

---

### 1.2 STRANGLER DISIPLINi VERDiKTi

**STRANGLER KORUNDU ✅**

Git log (PR #124-138) kanitli kontrol: D-177 → D-184 commit'lerinde asagidaki dosyalar **YOKTUR** (dokunulmadi):

| Dosya | Durum |
|-------|-------|
| `src/signals/engine.py` | DOKUNULMADI |
| `src/signals/calculator.py` | DOKUNULMADI |
| `src/signals/conviction_validator.py` | DOKUNULMADI |
| `src/signals/thresholds.py` | DOKUNULMADI |
| `src/backtest/engine.py` | DOKUNULMADI |
| `src/signals/layers/technical_layer.py` | DOKUNULMADI |
| `src/signals/layers/macro_layer.py` | DOKUNULMADI |
| `src/signals/layers/kap_layer.py` | DOKUNULMADI |
| `src/signals/layers/smart_money_layer.py` | DOKUNULMADI |
| (tum diger `src/signals/layers/*`) | DOKUNULMADI |

Faz 0, `src/screening/` modulunu ve `src/data/isyatirim_malitablo_fetcher.py`'yi **YANINA** ekledi.
Eski composite / engine / conviction mimarisine sifir dokunuş. ARCHITECTURE v2.0 §8 hukmu:
"Faz 0 cross-sectional kodlari + eski composite SILINMEZ, pasif kalir."

---

### 1.3 src/screening/ bucket Siniflandirmasi

PIVOT_ARCHITECTURE_AUDIT.md bucket 1/2/3'e ek olarak yeni sinif:

```
YENI: FAZ 0 IC HARNESS (OLCUM — Strangler Pasif)
  src/screening/__init__.py
  src/screening/faz0_config.py
  src/screening/factors.py
  src/screening/snapshot.py
  src/screening/factor_ic_harness.py
  src/screening/factor_ic_d184_audit.py
```

- Rol: Cross-sectional IC harness, measurement-only, on-paradigma dogrulama (D-177/178/183/184)
- bucket 1/2/3'ten bagimsiz: composite'e bagIi DEGIL, production signal uretmiyor (olcum)
- ARCHITECTURE v2.0 karari: pasif kalir (silinmez), yeni trend-test altyapisi olarak kismen yeniden kullanilir
- Test dosyalari: `tests/test_factor_ic_harness.py`, `tests/test_malitablo_fetcher.py`, `tests/test_factor_ic_d184.py`

`src/data/isyatirim_malitablo_fetcher.py` → **bucket 1'e eklenir** (veri kanali, signal/engine import YOK, kalite-suzgec fundamental veri kaynagidir)

---

## SORU 2 — PIVOT_ARCHITECTURE_AUDIT.md Guncel mi?

PIVOT_ARCHITECTURE_AUDIT.md tarihi: **2026-05-29** (D-177 → D-184 ONCESI).

### 2.1 Hala Dogru Olan Bolumler

| Bolum | Durum | Not |
|-------|-------|-----|
| **bucket 1/2/3 ana yapisi** | GECERLI | Faz 0 bu yapiya dokunmadi |
| **Q1-Q5 cevaplari** | GECERLI | backtest/engine.py composite yuzey dar (~60-80 satir), bucket 1 temiz ayriliyor, 0 dngusal bagimlilik |
| **bucket 3 blast radius** | GECERLI | Faz 0 composite'e dokunmadi, yayilim degismedi |
| **Sessiz kirIlma riski** (`conviction_score` default `0.0`/`"WATCH"`) | GECERLI | models.py:53-54,64-65 — refactor'da hala gecerli uyari |
| **Strangler yol haritasi** | GECERLI | ARCHITECTURE v2.0 §8 ayni siralari korudu |
| **§1.3 adjacency list** | KISMI (eksik) | src/screening/ ve isyatirim_malitablo_fetcher.py yok; digerleri hala dogru |

### 2.2 Eskiyen / Guncellenmesi Gereken Bolumler

| Bolum | Sorun | Guncelleme |
|-------|-------|-----------|
| **§0 PIVOT BAGLAMI** | "Katman A = ardisik filtre veya rank" v1.x tanimi. v2.0 Katman A = trend/swing motoru (trend-basi + parabolik-kacinma + kalite-suzgec + rejim teyidi) | ARCHITECTURE.md v2.0 §3 referansi ile guncelle |
| **§2.1 bucket 1 tablosu** | `src/data/isyatirim_malitablo_fetcher.py` eksik (D-183 ile eklendi) | bucket 1 tablosuna satir ekle |
| **§1.2 Dependency map mermaid** | FAZ 0 HARNESS subgraph yok; `isyatirim_malitablo_fetcher` yok | Yeni subgraph ekle: `screening/[factor_ic_harness, factors, snapshot, d184_audit]` → DATA baglanisi |
| **§1.3 Adjacency list** | `src/screening/*` ve `isyatirim_malitablo_fetcher.py` listede yok | Ekle: `src.screening.factor_ic_harness → screening.faz0_config, screening.factors, screening.snapshot, analytics.ic_calculator, data.short_interest_normalizer`; composite import YOK |
| **Test sayilari** | Audit: 1.467 test, 94 dosya. 3 yeni test dosyasi eklendi. Gunceli: `python -m pytest tests/ -q | tail -3` calistir | Yeni sayiyi yansitin |
| **src/ dosya sayisi** | Audit: 130 Python dosyasi. +7 (src/screening/ 6 dosya + isyatirim_malitablo_fetcher.py). Gunceli: ~137 | Guncelle |
| **§2.2 bucket 2 tablosu** | ARCHITECTURE v2.0 §3.5 guncellemesini yansiitmiyor: `technical.detail[adx, momentum_score, ...]` artik "ANA MOTOR primitive" (icaret), `Snapshot/IC/look-ahead guard` artik "trend-test'te reusable". v2.0 status sutunu eksik. | v2.0 status sutunu ekle |
| **ARCHITECTURE referanslari** | Audit v1.x referanslari kullaniyor. Yeni: ARCHITECTURE.md v2.0 + ARCH_V2_PARADIGM_DECISION.md | Referanslari guncelle |

### 2.3 Onerilen Eylem

PIVOT_ARCHITECTURE_AUDIT.md'yi **TAM YENIDEN YAZMAK GEREKMIYOR**. Minimum guncelleme:
1. §2.1 bucket 1'e satir ekle: `isyatirim_malitablo_fetcher.py`
2. Yeni §2.4 ekle: "FAZ 0 IC HARNESS" → `src/screening/` tam listesi + v2.0 pasif/reusable siniflandirmasi
3. §0 Katman A motorunu v2.0'a (trend/swing) guncelle
4. Test sayisini guncelle (`pytest --collect-only` yeniden calistir)

---

## SORU 3 — v2.0 Trend-Test Icin Reusable Envanter

**Paradigma notu (ARCHITECTURE v2.0 §7.1):** v2.0 trend-motor dogrulama **birincil kanit = per-trade expectancy + event-study** (cross-sectional IC DEGIL). Altyapi ihtiyaclari: Stage 0 on-kayit, frozen snapshot, event-study istatistik fonksiyonlari, ADV sert kapi, look-ahead koruma.

---

### 3.1 REUSABLE — Trend-Test Stage 0'da Kullanilabilir

| Bilesen | Dosya:satir | Trend-test'te nasil kullanilir |
|---------|-------------|-------------------------------|
| **Snapshot dondurma** | `src/screening/snapshot.py:88-186` (`freeze_price_snapshot`) | Trend-test evrenini (2019-2026) idempotent frozen parquet'e yaz. Stage 0 reproducibility. Ayni fonksiyon, yeni `tag` + `adv_floor_tl` ile cagrilir. |
| **Fundamental snapshot** | `src/screening/snapshot.py:223-313` (`freeze_fundamental_snapshot`) | Kalite-suzgec icin fundamental veri dondurma (point-in-time, idempotent). MaliTablo fundamentals ayni kanaldan. |
| **Point-in-time look-ahead guard** | `src/screening/factors.py` ici `_pit_index()` + `_latest_as_of()` (~satir 85-110) | Fundamental kalite-suzgec icin strict look-ahead korumasi. Lag mantigi ayni (pub_date <= asof); yeni faktorler icin de zorunlu. |
| **realized_vol (BIST-ozel)** | `src/screening/factors.py:realized_vol():35-48` | Dusuk-volatilite kalite-suzgec bileseni. `min_periods=ceil(0.75*window)` BIST halt/tatil icin kritik: bu satir silinirse halt sonrasi cross-section NULL'a duser. Suzgec olarak `rank_panel(vol, invert=True)` ile birlikte. |
| **forward_returns** | `src/screening/factors.py:forward_returns():51-63` | Per-event forward return etiketi. Trend-test per-event expectancy hesabinda ayni mantik. |
| **ic_stats** | `src/screening/factor_ic_harness.py:108-145` | NW-HAC t-stat + ICIR + CI hesabi. Trend-test event serisi icin: ic_stats'in matematigini (mean/std/NW-SE/CI) per-trade return uzerinde kullan — IC'nin kendisi degil, istatistik fonksiyonu. |
| **newey_west_se** | `src/screening/factor_ic_harness.py:89-105` | Bartlett kernel HAC standart hatasi. Trend-test per-event return ortalamasinin NW-HAC SE'si icin dogrudan reusable. |
| **nonoverlap_stats** | `src/screening/factor_ic_harness.py:148-165` | Non-overlapping stride orneklemesi + ICIR/t. Urtüen holding window artefaktini test icin. |
| **ADV filtresi (snapshot)** | `src/screening/snapshot.py:_compute_adv():41-53` + `faz0_config.py:FAZ0_ADV_FLOOR_TL` | Sert kapi (likit BIST30/50/100). `adv_floor_tl=` parametresi trend-test evrenini ayni sekilde daraltir. |
| **Survivorship kayit** | `src/screening/snapshot.py` meta["survivorship"] yapisi (satir 163-178) | halt/delist gap dokumantasyonu — trend-test icin de zorunlu (KOZAA/KOZAL/IPEKE/TRALT sinifi). Ayni meta yapisi korunur. |
| **content_hash** | `src/screening/snapshot.py:content_hash():57-64` | Snapshot determinizm kaniti. Trend-test Stage 0 on-kayitta hash kaydi zorunlu (reproducibility). |
| **_nw_hac_intercept_t** | `src/screening/factor_ic_d184_audit.py:317-340` | OLS reziduel NW-HAC t-stat (genel formul). Trend-test event'larinin makro-reziduel alpha testi (T2 analogu) icin reusable. |
| **T3 Holm-Bonferroni / BH-FDR** | `src/screening/factor_ic_d184_audit.py:100-210` | Coklu test duzeltmesi. Trend-test N konfigurasyon ARCHITECTURE §7.1 maks. N<=3 oldugu icin genellikle gerekmez, ama birden fazla kurulum denenirse kullanilabilir. |
| **compute_universe_percentiles** | `src/data/short_interest_normalizer.py` | Cross-sectional rank primitifi. Kalite-suzgec rank'lamasi icin. ARCHITECTURE v2.0 §3.5: "suzgecte kullanilabilir". |
| **is_adv_eligible** | `src/signals/layers/smart_money_layer.py` (~satir 980+) | ADV boolean sert kapi. ARCHITECTURE v2.0 §3.5: "sert kapi (korunur)". |
| **technical.detail[adx, momentum_score, ...]** | `src/signals/layers/technical_layer.py:196-204` | ADX + momentum_score + bollinger_position + ma_above vb. ham faktorler. ARCHITECTURE v2.0 §3.5: "ANA MOTOR primitive (yildiz)". Trend-basi tanimlama icin dogrudan reusable. |
| **SmartMoneyNormalizer._rolling_percentile** | `src/signals/layers/smart_money_layer.py` | Rolling percentile. Rejim teyidi (yabanci/kurumsal akis) icin. ARCHITECTURE v2.0 §3.5: "rejim/akis icin". |
| **ICCalculator** | `src/analytics/ic_calculator.py` | Authoritative Spearman IC/ICIR/t/p primitifi. factor_ic_harness equivalence assertion ile dogrulanmis. Event-study metrik katmani icin reusable. |
| **Backtest infra** | `src/backtest/metrics.py`, `src/backtest/cross_validation.py` (Purged K-Fold), `src/backtest/statistical_validation.py` (CPCV/DSR/PBO/NW-Sharpe) | Sinyal-agnostik validation altyapisi. bucket 1. Trend-test per-trade equity curve'u bu harness'tan gecer. |
| **isyatirim_malitablo_fetcher.py** | `src/data/isyatirim_malitablo_fetcher.py:104-153` | Kalite-suzgec fundamental veri kanali (P/B, EV/EBITDA, borclanma, karlillik). Trend-test suzgeci icin ayni fetcher. |

---

### 3.2 CROSS-SECTIONAL ONLY — Pasif Kalacak (Trend-Test'te Kullanilmaz)

| Bilesen | Dosya:satir | Neden pasif |
|---------|-------------|-------------|
| **rs_vs_xu100** | `src/screening/factors.py:rs_vs_xu100():18-33` | "Hisseleri birbirine gore RS'ye gore sirala" paradigmasi. Modern BIST'te reversal-baskin oldugu icin reddedildi (ARCH_V2_PARADIGM_DECISION: "cross-sectional kazananlar → reversal"). NOT: RS'nin zaman-serisi kullanimi (bir hissenin kendi gegcmisine gore guclenip guclenmedigi) farklι bir sey — bu fonksiyon cross-sectional ranking icin, o kullanim pasif. |
| **build_factor_ranks** | `src/screening/factor_ic_harness.py:182-198` | `(ranks[COMPOSITE_RS] + ranks[COMPOSITE_VOL]) / 2.0` — cross-sectional esit-agirlik rank composite. v2.0 Katman A = trend-basi (her hisse kendi gegcmisine gore), cross-sectional siralama DEGIL. |
| **build_signal_df** | `src/screening/factor_ic_harness.py:201-211` | Cross-sectional IC icin [date, symbol, factor] long format. Trend-test per-event formati (her sinyal bir row) farkli. |
| **build_returns_df** | `src/screening/factor_ic_harness.py:213-226` | Cross-sectional IC icin [signal_date, symbol, horizon, forward_return]. Trend-test per-event yeterli; bu format cross-sectional. |
| **daily_ic_series** | `src/screening/factor_ic_harness.py:63-86` | "Her gunde tum hisseler arasi cross-sectional Spearman IC" hesabi. Trend-test birincil kanit per-trade expectancy — cross-sectional IC DEGIL (ARCHITECTURE v2.0 §7.1). Istatistik fonksiyonlari (ic_stats / newey_west_se) reusable, bu fonksiyon degil. |
| **run_faz0 / run_faz0b** | `src/screening/factor_ic_harness.py:388-640` | Faz 0 cross-sectional IC olcum pipeline'lari. Trend-test farkli paradigma; yeni `run_trend_test()` tipi orkestrator gerekecek. |
| **rank_panel (sinyal amacli)** | `src/screening/factor_ic_harness.py:47-59` | Sinyal siralama araci olarak pasif. Ancak SUZGEC amacli kullanim (lowvol60 suzgec bileşeni) v2.0'da hala mesru. Iki rol ayrimi kritik. |
| **Composite formula** | `src/signals/engine.py:_compute_weighted_sum()`, `src/signals/calculator.py:compute_composite_score():26-53` | bucket 3. L1*0.25 + ... linear-additive composite. Trend-test bu formulü kullanmaz. ARCHITECTURE v2.0 §8 son adimda budanacak. |
| **MASTER_WEIGHTS** | `src/signals/thresholds.py:22-29` | bucket 3. Agirliklar composite ile birlikte oler. |
| **compute_conviction** | `src/signals/conviction_validator.py:48-63` | bucket 3. `(composite/100) × macro_mult`. Composite gidince anlamsiz. Yeni Katman C conviction uretimi gerekecek (ARCHITECTURE v2.0 §5). |
| **kelly_win_prob(composite)** | `src/signals/calculator.py:83-92` | bucket 3. Composite → win_prob → Kelly. Katman C'de EV/rank tabanli yeniden turetilmeli. |
| **D-184 run_d184_audit** | `src/screening/factor_ic_d184_audit.py:595-722` | CB-017 4-test audit cross-sectional faktor icin yazildi. Fonksiyon katmanlari (T1-T4 bileşen fonksiyonlari, NW-HAC) reusable, audit pipeline degil. |

---

### 3.3 Baglam Notu (DEC-039)

Bu tablo OLCER/HARITALAR. "Reusable" isareti "kullanilabilir" demektir, "kullanilacak" anlamina gelmez — trend-test Stage 0 tasarimi maintainer karari.

Kritik ayrimlar:
- `daily_ic_series` pasif; `ic_stats` / `newey_west_se` reusable. Trend-test istatistik katmani bunlari kullanabilir.
- `rank_panel` suzgec rolunde mesru; sinyal siralama rolunde pasif.
- `technical.detail[adx, ...]` ham faktor — trend-basi tanimi icin reusable; ama trend parametreleri on-kayitli ve minimal olmali (ARCHITECTURE §7.1: maks. N<=3 konfigurasyon, post-hoc secim yasak).
- Backtest infra (bucket 1) tamamen reusable — per-trade equity curve trend-test icin de bu harness'tan gecer.
- `rs_vs_xu100` cross-sectional ranking icin pasif; zaman-serisi trend kuvveti (bir hissenin gecen N gune gore guclenip guclenmedigi) farkli bir hesap ve v2.0 ANA MOTOR'un parcasidir — `technical.detail[momentum_score]` bu icin zaten mevcuttur.

---

## EK — Docs Durumu (2026-05-31)

| Dosya | Durum |
|-------|-------|
| `docs/ARCHITECTURE.md` | v2.0 — guncel (30 Mayis 2026, maintainer tarafindan yazildi) |
| `docs/ARCH_V2_PARADIGM_DECISION.md` | Yun karari belgesi, untracked (commit edilmedi) |
| `docs/PIVOT_ARCHITECTURE_AUDIT.md` | 2026-05-29, Faz 0 oncesi — kismi guncel (Soru 2 liste) |
| `docs/factor_ic/` | Faz 0 Stage 0 kayitlari + sonuclar, kalici |
| `docs/RESEARCH_REGISTRY.md` | RR-001 → RR-037 kayitli, guncel |
