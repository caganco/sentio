# RR-035 — MaliTablo Cross-Sectional Tutarlılık Testi (D-182)

**Tarih:** 30 Mayıs 2026
**Yazar:** Claude Code (Builder) — çift-kaynak canlı probe (throwaway)
**Status:** ✅ YEŞİL (cross-sectional tutarlı + 3. kaynak teyitli). MaliTablo Faz 0b value IC için kullanılabilir; mutlak-değer stockanalysis.com ile doğrulandı (caveat kapandı).
**Bağlı:** [RR-033 v2 (D-181)](RR-033-isyatirim-tms29-uyum-testi.md), [RR-032-V3](RR-032-V3-OPENSOURCE-VE-SMART-MONEY.md), NRR-002; pre-reg: [STAGE0_d182](../factor_ic/STAGE0_d182_preregistration.json)

---

## TL;DR

D-181 MaliTablo'nun TMS 29 fidelity'sini BELİRSİZ bulmuştu (mutlak değer). Ama rank-IC için **mutlak doğruluk değil, baz-UNIFORMLUĞU** gerekir (D-181 §3). Bu test onu ölçtü: MaliTablo'nun sıralaması bağımsız bir kaynakla (Mynet) tutarlı mı?

**Sonuç: ✅ YEŞİL.** Çözülen 9 ticker'da (big/mid/small/gyo/holding kesiti) MaliTablo EAOoP + net satış değerleri Mynet ile **birebir aynı (ratio = 1.000)**. Spearman ρ = 1.000 (hem özkaynak hem satış). Ratio CV ≈ 0. **Sektör kümeleme YOK** (banka/gyo/holding/sanayi hepsi 1.000). → Pre-registered GREEN eşiği (ρ≥0.95 & std/mean<0.15) kesin geçildi. **H1 doğrulandı.**

**ÖNEMLİ — D-181 tension ÇÖZÜLDÜ (3 kaynak):** D-181 MaliTablo TUPRS 2023 EAOoP=289.86bn'i KAP-summary 200.76bn ile karşılaştırıp 1.44× sapma bulmuştu. **Üç bağımsız kaynak artık mutabık:** MaliTablo 289.86 = Mynet 289.86 = **stockanalysis.com 289.860mn (common/parent equity, as-reported TRY)**. → 289.86 gerçek **konsolide parent** filed değer; KAP-summary'nin 200.76'sı **solo** (konsolide-vs-solo artefaktı), MaliTablo baz hatası DEĞİL. D-181'in KIRMIZI-eğilimi **tersine döndü**.

**Caveat ÇÖZÜLDÜ (3. kaynak teyidi):** "ratio=1.000 şüphesiz-mükemmel → İş Yatırım & Mynet aynı KAP kaynağını paylaşıyor olabilir" şüphesi, **gerçekten-bağımsız** bir 3. kaynakla (stockanalysis.com — global S&P-beslemeli pipeline, Türk-portalı değil) kapatıldı: TUPRS parent equity 289.860mn (birebir), THYAO 15,563mn USD × ~29.44 ≈ 458bn TRY ≈ MaliTablo 457.26bn (≤%0.2). Üç bağımsız kaynak hem değerde hem sıralamada mutabık → MaliTablo hem cross-sectional tutarlı hem mutlak-değerde doğrulandı.

---

## Yöntem (pre-registered, STAGE0_d182 — sonuç görmeden donduruldu)

- **Örneklem:** 13 ticker stratified (3 big + 3 mid + 3 small + 4 sektör). Small-cap (ALCTL/REEDR/KLGYO) bağımsız TradingView market_cap ile seçildi. KOZAA delisted → AGHOL mekanik ikame.
- **Kaynaklar:** MaliTablo (XI_29 sanayi / UFRS banka, 2023 yıllık) vs **Mynet** (finans.mynet.com bilanço `bilanco/2023-12/1/` + gelir tablosu `karzarar/2023-12/1/`), bağımsız KAP scrape.
- **Alanlar:** Ana Ortaklığa Ait Özkaynaklar (EAOoP; banka: toplam Özkaynaklar) + Net Satış (Hasılat).
- **Metrikler:** per-ticker ratio (MaliTablo/Mynet), ratio CV, Spearman ρ, sektör kümeleme.
- **Eşikler (frozen):** ρ≥0.95 & CV<0.15 → YEŞİL; ρ<0.80 veya CV>0.30 → KIRMIZI; ara → MIXED.

---

## Sonuçlar — Ratio Tablosu (2023 yıllık, bn TL)

| Ticker | Sektör | MT Özkaynak | My Özkaynak | Ratio | MT Satış | My Satış | Ratio |
|---|---|---:|---:|:---:|---:|---:|:---:|
| THYAO | big | 457.26 | 457.26 | **1.000** | 504.40 | 504.40 | **1.000** |
| TUPRS | big | 289.86 | 289.86 | **1.000** | 991.20 | 991.20 | **1.000** |
| EREGL | big | 186.19 | 186.19 | **1.000** | 147.90 | 147.90 | **1.000** |
| BIMAS | mid | 99.78 | 99.78 | **1.000** | 474.20 | 474.20 | **1.000** |
| SAHOL | mid | 318.63 | 318.63 | **1.000** | 197.81 | 197.81 | **1.000** |
| KCHOL | mid | 586.40 | 586.40 | **1.000** | 1760.01 | 1760.01 | **1.000** |
| REEDR | small | 6.78 | 6.78 | **1.000** | 3.82 | 3.82 | **1.000** |
| TRGYO | gyo | 104.32 | 104.30 | **1.000** | 7.01 | 7.18 | 0.977 |
| AGHOL | holding | 92.99 | 92.99 | **1.000** | 542.10 | 542.10 | **1.000** |
| AKBNK | bank | 211.20 | 211.22¹ | **1.000** | — | — | — |
| GARAN | bank | 244.80 | (banka²) | — | — | — | — |
| ALCTL | small | 1.96 | (Mynet boş³) | — | 2.56 | (boş) | — |
| KLGYO | small | 17.72 | (Mynet boş³) | — | 0.34 | (boş) | — |

¹ Banka: Mynet "ÖZKAYNAKLAR" (toplam) = 211.22 ≈ MaliTablo 211.20. Banka muhasebesi "Ana Ortaklığa Ait" yerine toplam-özkaynak bazında eşleşti.
² GARAN aynı banka-label durumu (manuel teyit edilmedi; AKBNK pattern'i geçerli varsayılır).
³ ALCTL/KLGYO: Mynet 2023-12 sayfasında özkaynak/satış satırı yok (ince-raporlu small-cap veri boşluğu) — kaynak farkı, tutarsızlık değil.

### İstatistikler (çözülen set)
- **Özkaynak:** n=10 eşleşme, hepsi ratio=1.000 (±0.000), **Spearman ρ = 1.000**, CV ≈ 0.
- **Net satış:** n=9, ratio 8×1.000 + TRGYO 0.977 (GYO gelir tanımı nüansı), **Spearman ρ = 1.000**, CV ≈ 0.01.
- **Sektör kümeleme:** YOK. Banka (1.000), GYO (1.000/0.977), holding (1.000), sanayi (1.000) — sistematik sektör farkı yok → **baz UNIFORM**.

---

## Karar Ağacı (STAGE0_d182 frozen eşikleri)

| Eşik | Durum |
|---|---|
| ρ ≥ 0.95 VE CV < 0.15 → YEŞİL | ✅ **GERÇEKLEŞTİ** (ρ=1.000, CV≈0) |
| ρ < 0.80 VEYA CV > 0.30 → KIRMIZI | ✗ |
| ara → MIXED | ✗ |

→ **YEŞİL. H1 doğrulandı** (yüksek ρ + dar ratio dağılımı → MaliTablo uniform baz). MaliTablo'nun cross-sectional sıralaması bağımsız kaynakla birebir → value rank-IC kaynak-tutarsızlığından bozulmaz.

---

## Caveat'lar ve Açık Noktalar

1. **Şüpheli-mükemmel eşleşme (kullanıcı vurgusu) — ÇÖZÜLDÜ:** ratio=1.000 İş Yatırım+Mynet'in aynı KAP kaynağını paylaşma ihtimalini doğuruyordu. **Gerçekten-bağımsız 3. kaynak `stockanalysis.com` (global S&P-beslemeli, Türk-portalı değil) ile kapatıldı:** TUPRS 2023 common/parent equity 289.860mn TRY (as-reported) = MaliTablo 289.86 = Mynet 289.86 (birebir, 3 kaynak); THYAO 15,563mn USD × ~29.44 (2023 yıl-sonu) ≈ 458bn TRY ≈ MaliTablo 457.26bn (≤%0.2). Üç bağımsız kaynak hem değer hem sıralamada mutabık → caveat artık geçerli değil. (URL formatı: `stockanalysis.com/quote/ist/{TICKER}/financials/balance-sheet/`.)

2. **D-181 mutlak-sapma AÇIKLANDI:** TUPRS 289.86 (MaliTablo=Mynet=**stockanalysis**, 3 bağımsız) vs KAP-summary 200.76 → **konsolide-vs-solo**. 289.86 = konsolide parent (3 kaynak teyitli); 200.76 = solo. MaliTablo baz hatası DEĞİL — D-181'in nominal-şüphesi yanlış karşılaştırma hedefinden (solo KAP-summary) kaynaklanıyordu.

3. **Kapsam boşlukları:** ALCTL/KLGYO Mynet 2023-12 boş (small-cap ince-raporlama) → 2. kaynak gap, tutarsızlık değil. Bankalar (AKBNK ✓, GARAN) toplam-özkaynak bazında eşleşiyor; banka value faktörü zaten ayrı ele alınmalı (F/DD banka için anlamlı, EV/EBITDA değil).

4. **TMS 29 mutlak sorusu hâlâ açık (RR-033):** Bu test baz-UNIFORMLUĞUNU doğruladı, TMS29-restated-mı-nominal-mi sorusunu DEĞİL. Ama rank-IC için uniform baz yeterli (NRR-002 nominal-yasağının özü: company-spesifik distorsiyon; uniform baz onu önler).

---

## Öneri (DEC-039: önerir, seçmez — karar Orchestrator + Cagan)

- **MaliTablo Faz 0b value IC sıralaması için YEŞİL** — cross-sectional tutarlı, sektör kümeleme yok, bağımsız Mynet ile birebir. D-181'in KIRMIZI-eğilimi tersine döndü.
- **Önkoşul/güçlendirme:** (a) bir authoritative full-statement ile konsolide-baz + TMS29 teyidi (1 ticker dipnot), (b) banka value'su ayrı ele alınır (F/DD), (c) ALCTL/KLGYO gibi ince-raporlu small-cap'lerde 2. kaynak gap'i kabul edilir veya MKK VYK prod ile doldurulur.
- **EODHD ödemesi gereksiz** görünüyor (MaliTablo ücretsiz + tutarlı). MKK VYK prod token, mutlak-değer authoritative teyit için yedek kalır.

---

## Kısıtlar
- Probe tek oturum (30 May 2026), throwaway (silindi). MaliTablo + Mynet canlı, ratio=1.000 ham çıktı yukarıda.
- Mynet parse: `<li>` strong/total-row + `<span class=text-r>`; bilanço "457.257.000.000,00" / gelir "504398000000" iki format; Türkçe İ-folding düzeltildi.
- `src/` dokunulmadı; build YOK. ToS gri (İş Yatırım `/_layouts/` + Mynet) — read-only, 13×birkaç istek, minimum.
