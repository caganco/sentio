# Research Registry — Ham Araştırma Raporları İndeksi

> Ham research raporları [`docs/research/`](research/) altında **kalıcıdır**.
> Her yeni SPEC/direktif, ilgili RR-XXX raporlarına `§section_number` ile referans
> vermek zorundadır (bkz. CLAUDE.md → RESEARCH REGISTRY kuralı).

| ID | Başlık | Tarih | Bağlı CB/SPEC | Status |
|----|--------|-------|---------------|--------|
| [RR-001](research/RR-001-fintables-takas-scraper.md) | Fintables takas scraper fizibilite | 21 May 2026 | D-116 | ✅ Applied |
| [RR-002](research/RR-002-akd-terminalleri-python.md) | AKD terminalleri Python entegrasyonu | 21 May 2026 | D-116 (Matriks reddedildi) | ✅ Applied |
| [RR-003](research/RR-003-composite-mimari-alternatifleri.md) | Composite mimari alternatifleri | 21 May 2026 | CB-002, CB-010 | ⏳ Aşama 1 SPEC bekliyor |
| [RR-005](research/RR-005-fetcher-map.md) | BIST fetcher haritası (robots/auth/format/rate-limit/ToS) | 22 May 2026 | — (fetcher SPEC bekliyor) | ⏳ Uygulanmadı |
| [RR-008](research/RR-008-evds-migration.md) | TCMB EVDS API migration: evds2→evds3, yeni base URL | 22 May 2026 | — (D-131 EVDS URL fix bekliyor) | ⏳ Uygulanmadı |
| [RR-010](research/RR-010-bist-ic-measurement.md) | IC ölçüm metodolojisi — Spearman IC, ICIR, Bayesian shrinkage weight kalibrasyonu | 23 May 2026 | CB-010 (statik weight savunulamazlığı) | ✅ Applied (Faz 1+2) — D-139/D-140 |
| [RR-011](research/RR-011-NLP-YAMA.md) | FinBERT-TR fizibilite — Yol 3 confirmed (BIST NLP pratik lens) | 24 May 2026 | — (L4 sentiment direktifi bekliyor) | ⏳ Uygulanmadı |
| [RR-012](research/RR-012-EM-Spesifik%20Fakt%C3%B6r%20Literat%C3%BCr%C3%BC%20Derinle%C5%9Ftirmesi.md) | 14 EM/BIST-spesifik faktör literatür derinleştirmesi — implementasyon fizibilite analizi | 24 May 2026 | — (Phase 5 faktör direktifi bekliyor) | ⏳ Uygulanmadı |
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
| [RR-032](research/RR-032-FIZIBILITE.md) | Faz 0b value faktörü için BIST fundamental veri envanteri — 11 kaynak × 5 ham veri uyum matrisi; Yol A (İş Yatırım screener ext.) / B (MKK VYK + XBRL parser ext.) / C (hibrit, önerilen) | 25 May 2026 | NRR-002 (Faz 0b value); D-170/172/175; D-178 sonrası | ⏳ Karar bekliyor (Yol A/B/C — Orchestrator+Cagan, DEC-039) |
| [RR-033](research/RR-033-isyatirim-tms29-uyum-testi.md) | İş Yatırım TMS 29 uyum testi — v1 (D-179, screener vs MKK dev) INCONCLUSIVE; **v2 (D-181, MaliTablo vs KAP-filed)**: TUPRS 2023 tek-tip ~%44 sapma (özkaynak/net kâr/satış 1.44×) + parasal-pozisyon satırı yok → MaliTablo'nun TMS29-restated olduğu DOĞRULANAMADI | 25-30 May 2026 | RR-032 §6 Yol A; RR-032-V3; NRR-002; D-179/D-181 | ⚠️ v2 BELİRSİZ→KIRMIZI eğilimli — MaliTablo Faz 0b value IC'ye OLDUĞU GİBİ bağlanmamalı; muhasebe-uzmanı full-statement doğrulaması + baz (nominal/restated) ayrımı şart. Karar O+C. |
| [RR-034](research/RR-034-isyatirim-usd-feasibility.md) | İş Yatırım USD-bazlı value fizibilite kontrolü — Q1 anlık TL÷spot (implied 45.71, EVDS ile %0.2), Q2 kapsama %99-100, Q3 snapshot-only (5 tarih param yok sayıldı), Q4 EVDS geçmiş kur hazır (584 gözlem/28 ay) | 30 May 2026 | RR-033 devam; RR-032 §6 Yol A; NRR-002; D-180 | ⚠️ Kontrol tamam — USD "Yol A" tarihsel IC için YEŞİL DEĞİL (snapshot-only); oranlar birimsiz → USD TMS 29'u baypas etmez; alternatif = geçmiş TL fund + EVDS kur (RR-032 Yol B/C'ye döner). Karar O+C. |
| [RR-032-V2](research/RR-032-V2-GENISLETILMIS-ENVANTER.md) | BIST fundamental veri kaynakları genişletilmiş envanter (RR-032 üstüne) — 9 kaynak grubu KESIN cevap: TradingView ✓✓ ücretsiz programatik (600 BIST, snapshot); Matriks IQ Pro retail fundamental API YOK; investpy ölü; Google/FMP/AV ✗; Finnhub premium; EODHD €60/ay trial-doğrula | 30 May 2026 | RR-032 genişletme; NRR-002; D-181 | ⏳ Karar bekliyor — Faz 0b: MKK VYK / EODHD trial; Faz 1+ canlı: TradingView. Orchestrator+Cagan. |
| [RR-032-V3](research/RR-032-V3-OPENSOURCE-VE-SMART-MONEY.md) | Açık-kaynak repo izleme + smart money kanal envanteri — **HEADLINE: İş Yatırım MaliTablo** (Data.aspx/MaliTablo, ücretsiz JSON, 2004+ UFRS, itemCode 2O=defter değeri) canlı teyitli → Faz 0b tarihsel fundamental darboğazını çözer, EODHD ödemesi ertelenebilir. Smart money: foreign flow+VIOP IC-hazır, takas/AKD bloke | 30 May 2026 | RR-032/V2 genişletme; RR-033/034 devam; RR-001/002/020; D-182 | ⏳ Karar bekliyor — Faz 0b birincil: İş Yatırım MaliTablo (ücretsiz) + RR-033 TMS29 testi; smart money Faz 0c: foreign flow+VIOP rank-IC. Orchestrator+Cagan. |
| [RR-035](research/RR-035-malitablo-cross-sectional-consistency.md) | MaliTablo cross-sectional tutarlılık testi (D-182) — 13 ticker stratified, MaliTablo vs bağımsız Mynet 2023 yıllık. EAOoP+satış ratio=1.000 (9-10 ticker), ρ=1.00, sektör kümeleme YOK → baz UNIFORM. D-181 mutlak-sapma (289.86 vs 200.76) konsolide-vs-solo olarak açıklandı (Mynet de 289.86) | 30 May 2026 | RR-033 v2 §3; RR-032-V3; NRR-002; D-182; pre-reg STAGE0_d182 | ✅ YEŞİL (cross-sectional tutarlı) — MaliTablo Faz 0b rank-IC için kullanılabilir; caveat: şüpheli-mükemmel eşleşme (paylaşılan KAP kaynağı) → 1 bağımsız 3. kaynak + konsolide-baz teyidi önerilir. D-181 KIRMIZI-eğilimi tersine döndü. Karar O+C. |

---

## Bölüm referans haritası (CB ↔ RR §section)

Kritik bulguların hangi rapor bölümüne dayandığı:

- **CB-002** (regime-blind weights) → RR-003 §3 (Regime-Conditional Weights — "CB-002 Derinleştirme") + Recommendations Aşama 1
- **CB-007** (foreign flow yanlış katmanda) → RR-001 §4 (yeni L5 mimarisi); akademik temel §2B (Ownership vs Flow)
- **CB-010** (linear additive mimari) → RR-003 §1 (Attention-Weighted), §2 (Multi-LLM Ensemble), §4 (Non-Linear Composite)

## Kayıt kuralları

- Her RR dosyası `docs/research/RR-XXX-{kısa-isim}.md` formatında, **silinmez**.
- Bir RR uygulandığında (SPEC/direktife dönüştüğünde) Status `✅ Applied`, ilgili D-XXX yazılır.
- Henüz uygulanmamış RR → `⏳` + bekleyen aşama notu.
- Reddedilen alternatifler de raporda kalır (örn. RR-002'de Matriks reddi) — karar geçmişi korunur.
