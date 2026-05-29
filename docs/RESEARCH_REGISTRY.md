# Research Registry — Ham Araştırma Raporları İndeksi

> Ham research raporları [`docs/research/`](research/) altında **kalıcıdır**.
> Her yeni SPEC/spec, ilgili RR-XXX raporlarına `§section_number` ile referans
> vermek zorundadır (bkz. CLAUDE.md → RESEARCH REGISTRY kuralı).

| ID | Başlık | Tarih | Bağlı CB/SPEC | Status |
|----|--------|-------|---------------|--------|
| [RR-001](research/RR-001-fintables-takas-scraper.md) | Fintables takas scraper fizibilite | 21 May 2026 | D-116 | ✅ Applied |
| [RR-002](research/RR-002-akd-terminalleri-python.md) | AKD terminalleri Python entegrasyonu | 21 May 2026 | D-116 (Matriks reddedildi) | ✅ Applied |
| [RR-003](research/RR-003-composite-mimari-alternatifleri.md) | Composite mimari alternatifleri | 21 May 2026 | CB-002, CB-010 | ⏳ Aşama 1 SPEC bekliyor |
| [RR-005](research/RR-005-fetcher-map.md) | BIST fetcher haritası (robots/auth/format/rate-limit/ToS) | 22 May 2026 | — (fetcher SPEC bekliyor) | ⏳ Uygulanmadı |
| [RR-008](research/RR-008-evds-migration.md) | TCMB EVDS API migration: evds2→evds3, yeni base URL | 22 May 2026 | — (D-131 EVDS URL fix bekliyor) | ⏳ Uygulanmadı |
| [RR-010](research/RR-010-bist-ic-measurement.md) | IC ölçüm metodolojisi — Spearman IC, ICIR, Bayesian shrinkage weight kalibrasyonu | 23 May 2026 | CB-010 (statik weight savunulamazlığı) | ✅ Applied (Faz 1+2) — D-139/D-140 |
| [RR-011](research/RR-011-NLP-YAMA.md) | FinBERT-TR fizibilite — Yol 3 confirmed (BIST NLP pratik lens) | 24 May 2026 | — (L4 sentiment speci bekliyor) | ⏳ Uygulanmadı |
| [RR-012](research/RR-012-EM-Spesifik%20Fakt%C3%B6r%20Literat%C3%BCr%C3%BC%20Derinle%C5%9Ftirmesi.md) | 14 EM/BIST-spesifik faktör literatür derinleştirmesi — implementasyon fizibilite analizi | 24 May 2026 | — (Phase 5 faktör speci bekliyor) | ⏳ Uygulanmadı |
| [RR-013](research/RR-013_NAV_ISKONTO.md) | BIST holding NAV iskontosu hesabı ve mean reversion alpha stratejisi (KCHOL/SAHOL/AGHOL pilot) | 24 May 2026 | RR-012 §B8 (20× detay) | ⏳ Uygulanmadı |
| [RR-014](research/RR-014-SLIPPAGE.md) | BIST slippage ve market impact modellemesi — Almgren-Chriss, karekök etkisi, BIST mikroyapı bulguları | 24 May 2026 | — (execution SPEC bekliyor) | ⏳ Uygulanmadı |
| [RR-015](research/RR-015-TRANSACTION-COST.md) | Transaction cost modellemesi — broker tier karşılaştırması, round-trip maliyet, ~85K TL portföy erozyon analizi | 24 May 2026 | RR-014 §devam | ⏳ Uygulanmadı |
| [RR-016](research/RR-016-DRAWDOWN-AND-VOLATILITY-TARGETING.md) | Drawdown & volatility targeting — max drawdown kontrolü, volatility scaling, kriz dönemleri counterfactual analizi | 24 May 2026 | RR-012, RR-013, RR-014, RR-015 §devam | ⏳ Uygulanmadı |
| [RR-017](research/RR-017-HMM.md) | HMM Regime Detection — BIST kalibrasyon ve aktivasyon roadmap; ENABLE_HMM_WEIGHTS=False, AG-001 bekleniyor | 25 May 2026 | RR-003 §Aşama 1; CB-002 interaction §11 | ⏳ Uygulanmadı |
| [RR-018](research/RR-018-VERY-IMPORTANT.md) | López de Prado tabanlı backtesting framework — AUDIT_REPORT_001 D-061 C-1 closure, RR-014/015/016/017 entegrasyon | 25 May 2026 | RR-014, RR-015, RR-016, RR-017 §entegrasyon | ⏳ Uygulanmadı |
| [RR-019](research/RR-019-MULTI-LLM.md) | Multi-LLM Orchestration — BIST OS için AI jüri sistemi (Phase 6+, Q1 2027+, nice-to-have) | 24 May 2026 | RR-010/011/012 §devam; Phase 6 sonrası | ⏳ Uygulanmadı |
| [RR-020](research/RR-020-BIST-VERISI-MAP.md) | BIST veri kaynakları atlas (Rosetta Stone) — yfinance/Stooq/EVDS3/KAP/İş Yatırım/Takasbank stack haritası, single point of failure ve cross-validation kararları | 24 May 2026 | RR-005 §derinleştirme (fetcher atlas) | ⏳ Uygulanmadı |
| [RR-021](research/RR-021-TCMB.md) | TCMB EVDS3 API operasyonel referans — 16 seri envanteri, auth header, URL formatı, dead/aktif durumu | 25 May 2026 | RR-008 §devam (D-135/D-136 sonrası) | ⏳ Uygulanmadı |
| [RR-021b](research/RR-021-live-test-results.md) | EVDS3 canlı test sonuçları (script çıktısı) — 14 aktif, 2 dead; `scripts/test_evds3_connection.py` tarafından üretilir | 25 May 2026 | RR-021 §3 companion | ⏳ Snapshot |
| [RR-022](research/CRITIC-2605-STRATEJIK-MIMARI-DEGERLENDIRME.md) | Stratejik Mimari Değerlendirme — L1/L2/L6 mimari teşhis, bot vs. danışman kimlik sorusu, LLM'in gerçek rolü, yol haritası; D-153b/c backtest bulgularına dayalı | 26 May 2026 | RR-003 §CB-010 derinleştirme; RR-017 §HMM bağlantısı; CB-002 §L2 circular | ⏳ Orchestrator incelemesinde |
| [RR-031](research/RR-031-KAP-NEXTJS-MIGRATION.md) | KAP Next.js Migration — scraping infeasibility (memberDisclosureQuery ölü: tarpit/HTTP 666/429); MKK VYK API (D-170) YEŞİL kanal | 28 May 2026 | D-170 (MKK VYK API) | ✅ Applied → kap_scraper.py fallback confirmed |
| [RR-032](research/RR-032-FIZIBILITE.md) | Faz 0b value faktörü için BIST fundamental veri envanteri — 11 kaynak × 5 ham veri uyum matrisi; Yol A (İş Yatırım screener ext.) / B (MKK VYK + XBRL parser ext.) / C (hibrit, önerilen) | 25 May 2026 | NRR-002 (Faz 0b value); D-170/172/175; D-178 sonrası | ⏳ Karar bekliyor (Yol A/B/C — the project, DEC-039) |
| [RR-033](research/RR-033-isyatirim-tms29-uyum-testi.md) | İş Yatırım Screener TMS 29 uyum testi — 4 ticker (THYAO/EREGL/BIMAS/TUPRS) × screener vs UFRS-TMS 29 KAP karşılaştırma metodolojisi; RR-032 Yol A önkoşulu | 25 May 2026 | RR-032 §6 Yol A; NRR-002; D-179 execution | ⚠️ INTERIM (D-179 koşturuldu) — Verdict INCONCLUSIVE: dev MKK VYK gateway TMS 29 öncesi (Q3 2023 son). Kalıcı kazanım: İş Yatırım 6 value field ID kataloğu + `_XBRL_MAP` IssuedCapital≠Equity hatası onaylandı. Path 1 (D-170 prod token bekle) / Path 2 (IR PDF) ile re-run gerek. |

---

## Bölüm referans haritası (CB ↔ RR §section)

Kritik bulguların hangi rapor bölümüne dayandığı:

- **CB-002** (regime-blind weights) → RR-003 §3 (Regime-Conditional Weights — "CB-002 Derinleştirme") + Recommendations Aşama 1
- **CB-007** (foreign flow yanlış katmanda) → RR-001 §4 (yeni L5 mimarisi); akademik temel §2B (Ownership vs Flow)
- **CB-010** (linear additive mimari) → RR-003 §1 (Attention-Weighted), §2 (Multi-LLM Ensemble), §4 (Non-Linear Composite)

## Kayıt kuralları

- Her RR dosyası `docs/research/RR-XXX-{kısa-isim}.md` formatında, **silinmez**.
- Bir RR uygulandığında (SPEC/spece dönüştüğünde) Status `✅ Applied`, ilgili D-XXX yazılır.
- Henüz uygulanmamış RR → `⏳` + bekleyen aşama notu.
- Reddedilen alternatifler de raporda kalır (örn. RR-002'de Matriks reddi) — karar geçmişi korunur.
