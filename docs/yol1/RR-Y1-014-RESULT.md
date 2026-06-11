# RR-Y1-014 PEAD Stage-0 Ölçümü — Sonuç

> İlk resmi ölçüm (OLCUM, optimizasyon-DEĞİL). Ön-kayıt: [STAGE0_PEAD_SUE1_TERCILE.json](STAGE0_PEAD_SUE1_TERCILE.json)
> (freeze-commit `18c6ee0`, 2026-06-10, sonuç-görülmeden). Bu rapor yalnız
> **keep-bar hükmü + kanıt** teslim eder; karar-ağacı (RR-Y1-014 §8: graveyard-kaydı,
> DEC-numarası, sonraki-aday) ayrı bir değerlendirme adımıdır ve bu raporun
> kapsamı dışındadır. Sign-flip / post-hoc-gevşetme / diriltme yasakları donmuş
> ön-kayıtta kayıtlıdır (DISC-3, DEC-053).

## KEEP-BAR HÜKMÜ: **FAIL**

Donmuş tanım (Stage-0 `keep_bar`): tam-panel NW-t ≥ 2.0 **VE** X2 (lockbox, tek-atış) NW-t ≥ 2.0.

| Koşul | Eşik | Ölçülen | Sonuç |
|---|---|---|---|
| Birincil: tam-panel long-bacağı EW-relative NW-t (lag=5, 1.360 günlük gözlem) | ≥ 2.0 | **−0.029** | **FAIL** |
| Konjuge: X2 lockbox tek-atış NW-t (lag=5, 1.404 gözlem, 92 isim) | ≥ 2.0 | **−0.486** | **FAIL** |

Yüksek-SUE-tercile long-bacağının EW-aktif-olay-evrenine göre fazla-getirisi,
2019–2025 BIST likit-evreninde **istatistiksel sıfırdır** — brüt düzeyde bile
(maliyet-öncesi gross_active_ann = **−0.12%/yıl**). Edge yok; maliyet sorusu
hükme girmeden ölçüm kapanır.

## Stage-0 Disiplin Uyum Kaydı

| Disiplin maddesi | Durum |
|---|---|
| Ön-kayıt sonuç-görülmeden dondu | ✓ freeze-commit `18c6ee0` (Stage-0 JSON + sinyal-paneli + X1/X2-bölmesi + lockbox-hash, ölçümden önce ayrı commit) |
| Snapshot-hash guard | ✓ `e5dddae304d686cb` (pead_signal_panel.parquet) — runner her fazda doğruladı |
| X2 lockbox tek-atış | ✓ hash `5b0e50ec5854663f`; **tüketildi** 2026-06-10 23:49 UTC ([consumed-marker](STAGE0_PEAD_SUE1_TERCILE.lockbox-consumed.json) commit'li; ikinci koşu mekanik-reddedilir) |
| X1 bakış-bütçesi ≤ 3 | ✓ 2/3 kullanıldı ([pead_x1_looks.json](../../data/processed/pead_x1_looks.json)): bakış-1 pipeline-doğrulama; bakış-2 hizalama-düzeltmesi-sonrası birebir-aynılık teyidi (aşağıda) |
| denenen_konfig_sayisi = 1 | ✓ tek config; SUE-formu/eşik/evren aranmadı; DSR n_trials=1 |
| Parametre değişikliği | YOK — koşular arası tek değişiklik bir uygulama-hatası düzeltmesiydi (sinyal `scores()` kolon-hizalaması, committed motorun beklediği tam-evren-NaN-dolgulu form); X1 bakış-2, düzeltmenin X1 sayılarını **bit-düzeyinde değiştirmediğini** doğruladı (nw_t 0.07813864351827926 her iki bakışta) |
| Performans-metriği serbestliği | Bu bir Stage-0 ÖLÇÜMÜdür (probe değil) — getiri/t-istatistiği raporlanır |

## Kanıt Vektörü (engine_output — [RR-Y1-014_engine_output.json](RR-Y1-014_engine_output.json))

**Üç örneklemde NW-t (tutarlılık):**

| Örneklem | n_obs (gün) | NW-t | gross_active_ann |
|---|---|---|---|
| Tam panel (184 isim, 1.473 olay) | 1.360 | **−0.029** | −0.12%/yıl |
| X1 (geliştirme-yarısı, 92 isim) | 1.410 | +0.078 | +0.45%/yıl |
| X2 (lockbox, 92 isim) | 1.404 | **−0.486** | −3.24%/yıl |

**Motor başlık-vektörü (tam panel, committed harness):**

- gross_active_ann **−0.12%** / cost_ann 6.71% (D-207, günlük-tercile-churn; ort. round-trip 71,4bp) / tax_ann 0.45% → net_active_ann **−7.28%**
- real_active_ann **−33.0%** vs benchmark-floor (TÜFE-CAGR) **+38.4%** → `beats_benchmark_floor = false` (TLREF-straddle guard'ı TÜFE-only fallback'ine düştü — d213-precedent, kayıtlı)
- Mod-B DSR = 0.68 (n_trials=1; teşhis — hüküm-değiştirici değil, zaten FAIL)
- per-rejim: pre-2022 **−1.19%/yıl** (452 gün), post-2022 **+0.41%/yıl** (908 gün) — her iki rejimde sıfır; "rejim-maskeli edge" okuması desteklenmiyor
- plateau (sınırlı 4-nokta): tercile_h1 −0.12% / tercile_h2 −1.11% / decile_h1 −5.48% / decile_h2 −7.31% — **tüm komşu-noktalar ≤ 0**; daha keskin sıralama (decile) daha da negatif → sinyal-yönünde bilgi yok, şanslı-nokta yok
- Mod-A motor-agreement (R=50): **breadth-degenerate guard** — "only 38 eligible names; need >= 100" (RR-Y1-008 duvarı; Stage-0'da önceden deklare edilmişti; hüküm X1/X2-protokolünde) → `agreement_confidence = low`
- `pm1_guard_raised = true` alanı **PM-1 ihlali DEĞİLDİR**: harness bu bayrağı benchmark-floor guard'ından (TLREF-straddle) set eder; `assert_pm1_compliant` tüm fazlarda geçti (sepet-içi re-tilt, nakit-gate yok)

## Teşhis Okumaları (hüküm-kapamaz; kayıt)

1. **Decay-karşı-prior doğrulanmış görünüyor (§1):** drift her iki alt-rejimde ve
   her iki isim-yarısında sıfır. BIST-likit-evren-PEAD'i 2019-2025'te
   zaten-fiyatlanmış/yok okumasıyla tutarlı; Yılmaz et al. (2020) dönem-örneklemi
   (daha eski + illikit-dahil) ile çelişki, likidite-dışlama bulgusuyla (aşağıda)
   birlikte okunmalı.
2. **Likidite-dışlama sınırı (ön-kayıtlı, §2):** SUE-tanımlı olayların ~%81'i
   likit-evren-dışıydı; ölçüm driftin muhtemelen en-zayıf (likit) dilimini ölçtü.
   Bu bir ölçüm-kapsamı kaydıdır; FAIL hükmünü likit-evren-PEAD'i için verir,
   illikit-bölge ÖLÇÜLMEMİŞTİR (harvest-edilemez olduğu için ölçüm-evreni dışında).
3. **Maliyet yapısal olarak ağır:** günlük-yeniden-sıralanan tercile-üyelik motor-native
   churn üretir (cost_ann %6,7). Gross sıfır olduğundan hükme etkisiz; ileride
   herhangi bir olay-bazlı aday için çeyrek-kilitli-tutuş tasarımı maliyet-tarafını
   düşürürdü — bu bir gözlemdir, bu prototipe post-hoc uygulanamaz (DISC-3).
4. **X1↔X2 işaret-farkı (+0.08 vs −0.49):** her ikisi istatistiksel sıfır;
   fark gürültü-bandının içinde. Konjuge-yapı tam da bu tür "yarıda-pozitif-görünüm"
   yanılgısını tek-atışla kapatmak için vardı.

## Uygulama Kaydı

- Runner: [scripts/scratch/run_rr_y1_014_stage0.py](../../scripts/scratch/run_rr_y1_014_stage0.py) —
  committed motor READ-ONLY (harness, _tilt_active[min_names=15, Stage-0-deklare],
  nw_tstat, lockbox, stage0_validator); src/engine sıfır-dokunuş.
- Sinyal-paneli: [data/processed/pead_signal_panel.parquet](../../data/processed/pead_signal_panel.parquet)
  (1.473 olay / 184 isim; SUE1=UE/MV-önceki-çeyrek-sonu; giriş=RR-Y1-013-B T+2
  gün-damgası; 60-işgünü skor-persistansı; `construction_window=1` çift-rol-uyarısı
  gereği deklare).
- Bilinen uygulama-sınırı: delist-içi olaylarda son-gün getirisi forward-return-NaN
  nedeniyle dışarıda (Stage-0 evren-kaydında ön-deklare).
