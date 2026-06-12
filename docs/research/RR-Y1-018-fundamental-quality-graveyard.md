# RR-Y1-018 — Accounting-fundamental quality faktörü: GRAVEYARD (graveyard-check gate)

**Sınıf:** Graveyard-check + eksen-kapanış kaydı. **Stage-0-DEĞİL**, yeni-ölçüm-YOK, yeni-kod-YOK.
Yalnız mevcut frozen-Stage-0 verdict'i **kayda geçirir** ve maintainer eksen-hükmünü dokümante eder.
Bu rapor bir **GATE**'tir: "fundamental/accounting quality faktörü daha önce test edildi mi?" sorusunu
yanıtladı → **EVET** → veri-fizibilite (Phase 2) **koşulmadı** (mezar-diriltme olurdu, maintainer kararı).

---

## Phase 1 — Graveyard check (GATE): açık yanıt

### ➤ **EVET.** Bir accounting-fundamental quality faktörü zaten ölçüldü, frozen-Stage-0 + negatif verdict ile.

**Profitability — GP/TA (Novy-Marx) + ROE — D-191 (K2 factor-tilt) altında test edildi.**

| Kanıt | Yer / olgu |
|---|---|
| Kod | `src/screening/k2_profitability.py` — `kind="gpa"` = `gross_profit/total_assets` (Novy-Marx 2013, **BİRİNCİL**); `kind="roe"` = `net_income/book_eaoop` (robustluk). Point-in-time, pub-date-lag'li. |
| Frozen Stage-0 | `docs/k2_test/STAGE0_factor_tilt_preregistration.json` (ön-kayıt 2026-06-01; DEC-K2 kuralı sonuç-görülmeden donduruldu). Profitability **ÖNCELİK** faktör ilan edildi (EM-FF5 prior). |
| Sonuç + verdict | `docs/k2_test/factor_tilt_results.json` + `docs/research/D-191-k2-factor-tilt-rapor.md`. **Verdict VAR:** `passes_DEC_K2 = false` ("GECMEZ"). Profitability tek-faktör diagnostiği gate-4 için gerekliydi ve **DÜŞTÜ** (`profitability_significant = false`; TL-reel-anlamlı-değil; fair-null'ı geçmiyor; out-of-sample negatif). |

**Verdict-olguları (yalnız olgu, magnitude-import-YOK ötesinde):**
- `gate1_tl_real_sig_positive = false` — TL-reel beklenti anlamlı-pozitif değil.
- `gate2_beats_fair_null_95 = false` — fair-portfolio-null'ı geçmiyor (random'dan ayırt-edilemez).
- `gate3_out_of_sample_positive = false` — out-of-sample negatif (in-sample-pozitif KALICI değil).
- Profitability tek-faktör: `tl_real_sig_positive = false`, `beats_fair_null_95 = false`.
- Rapor (D-191) açıkça: **EM-FF5 / RR-OMEGA profitability prior'ı BIST için negatif kapandı.**
- MaliTablo itemCode'ları Stage-0'da donduruldu (`gross_profit=3D`, `total_assets=1BL`, `net_income=3Z`); PIT (annual pub_date = period_end + 120g).

### Faktör → girdi-sınıfı → statü tablosu

| Faktör (test) | Girdi-sınıfı | Statü |
|---|---|---|
| **profitability GP/TA + ROE** (D-191, tek-faktör diagnostiği) | **FUNDAMENTAL / ACCOUNTING (quality)** | **TEST EDİLDİ — frozen-Stage-0 verdict VAR; negatif (anlamlı-değil)** |
| K2 composite value+**profitability**+lowvol (D-191) | karma (fundamental quality dahil) | TEST EDİLDİ — GECMEZ (graveyard) |
| value_static / value_only_regime / value_regime_arm (P/B, E/P) | valuation-ratio (fiyat ÷ accounting book/earnings) | graveyard (SERAP/FRAGILE, PERMANENT) |
| EDGE-2 composite; hi52; lowvol63/60/252; mom120 | price/structure | graveyard / not-kept |
| h2b_dividend_runup | price/structure (event) | graveyard |
| nav_discount_z | price/structure (NAV) | graveyard (SERAP) |
| foreign_flow_timing; real_rate_timing | orthogonal/macro-timing | graveyard |
| viop_ssf_oi_k2 | derivative-OI | graveyard (SEALED) |
| index_recon_xu030_in | mechanical-flow | graveyard |
| RS-vs-XU100 / faz0 lowvol | price/structure | not-kept (zayıf IC) |
| PEAD | event-tilt (earnings-surprise drift; earnings-data kullanır ama quality cross-section DEĞİL) | PENDING (RR-Y1-014 in-flight) |

**Okuma-notu:** Prompt'taki FUNDAMENTAL/ACCOUNTING-quality girdi-sınıfına (profitability/ROE/gross-profit)
uyan *yegâne* eksen = **profitability (D-191)** — ve frozen-Stage-0 + negatif verdict taşır. **Value**
(P/B, E/P) ayrı bir valuation-ratio eksenidir (kalıcı-kapalı); accounting *girdilerini* kullanır ama
söz-konusu quality faktörü değildir. Ayrı **accruals / leverage / asset-growth / earnings-stability**
faktörünün kendi testi YOK — ama gate *herhangi bir* accounting-quality faktörünün frozen-Stage-0
verdict'iyle tetiklenir, ve gross-profitability + ROE bunu karşılar.

---

## Eksen hükmü: **GRAVEYARD** (gerçek frozen-Stage-0 negatif verdict; save/wait-DEĞİL)

RR-Y1-017-B'den (save/wait, çünkü X₂ hiç koşulmadı) farklı olarak, burada **gerçek bir ön-kayıtlı
Stage-0 koşuldu ve negatif sonuç verdi.** Bu ölçülmüş-negatif → **GRAVEYARD**.

**Maintainer eksen-hükmü (kayda geçirilir):**
- **AKSE (accounting-fundamental quality, flagship metrik = gross-profitability + ROE) MÜHÜRLÜdür.**
- Daha-geniş **test-edilmemiş üyeler (accruals / asset-growth / earnings-stability)** otomatik
  açılmaz. Yalnız şu üçü birlikte sağlanırsa yeniden-değerlendirilir:
  1. **Farklılaşmış BIST-spesifik mekanizma** (genel "quality iyidir" değil — neden BIST'te, neden bu üye),
  2. **Tanımlanabilir karşı-taraf** (kimin yanlış-fiyatladığı / kime karşı edge),
  3. **Öngörücü (accommodating-olmayan) prior-yükseltici** (sonradan-uydurma değil, ön-kayıtlı).
- **Genel-quality / Buffett-sezgisi bu barı KARŞILAMAZ** (kontrol edildi, kapalı): farklılaşmış-mekanizma
  yok, karşı-taraf-yok, accommodating-prior. Tek-başına "kaliteli şirket al-tut" bir faktör-edge gerekçesi değil.
- **Discretionary "anla-ve-tut"** ayrı kalır: bu falsifiye-edilemez bir **human-capital overlay**'dir,
  faktör-kaydının parçası DEĞİL; faktör-graveyard'ı onu ne onaylar ne reddeder (farklı kategori).

**Phase 2 (PIT fundamental veri-fizibilitesi) KOŞULMADI.** Bir profitability/quality ölçümünü
yeniden-koşmak D-191 negatif-sonucunun diriltilmesi olurdu — maintainer kararı, bir prob değil.

---

## Caveat'lar (maintainer için olgu, öneri-değil)
- D-191 profitability testi bir **portfolio-tilt** (factor-premium harvesting) idi: **survivors-only
  BIST-100, 2019-2026, yarı-yıllık, iyimser-üst-sınır** evren, **bilinçli-kabul ince-n** limiti —
  *temiz cross-sectional rank-IC* değil, accruals/leverage/asset-growth değil, delisting-survivorship-
  temiz PIT panel değil.
- *Farklı-spesifikasyonlu* bir quality faktörünün (farklı metrik, temiz cross-section, daha-dolu evren)
  "aynı eksen" (diriltme, mühürlü) mi yoksa "yeni eksen" mi sayılacağı **maintainer kararıdır** — gate
  beni her durumda burada durdurur (yeni-ölçüm-yok).
- Hiçbir dosya değiştirilmedi/çalıştırılmadı; OI ve tüm graveyard modülleri dokunulmadı; ölçüm-yok.
