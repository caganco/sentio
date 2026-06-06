# RR-032 — Faz 0b value Faktörü için BIST Fundamental Veri Envanteri (Fizibilite)

**Tarih:** 25 Mayıs 2026
**Yazar:** Arastirma katmani
**Status:** ⏳ Karar bekliyor (Yol A/B/C — maintainer, DEC-039 pattern)
**Bağlı:** NRR-002 metodoloji notu (sec.133), D-170/172 (MKK VYK), D-175 (yfinance fallback), D-178 (Faz 0 sonuçları), RR-020 (BIST veri atlası), RR-021 (EVDS3), RR-031 (KAP Next.js dead path)

---

## TL;DR

D-178 kanıtladı: salt-fiyat faktörler (RS, low-vol) BIST'te tek başına zayıf. NRR-002'nin önerdiği **USD-bazlı F/DD + EV/EBITDA value** faktörü hâlâ eksik. Kalite çıtası: **UFRS/TMS 29 zorunlu** (VUK yasak); nominal F/K yasak; 2022-2024 yapısal kırılma flaglenmeli.

**Mevcut kod 5 ham veriden (market cap, EBITDA, net borç, defter değeri, USD kuru) sadece 1'ini (USD kuru, EVDS) tam karşılıyor.** Geri kalan 4'ü için ya mevcut fetcher genişletilmeli, ya yeni kaynak entegre edilmeli.

**Üç fizibil yol** (artan kalite/maliyet):
- **Yol A — Quick Win (1-2 gün):** İş Yatırım `getScreenerDataNEW` connector'ı value alanlarına genişlet. **Önkoşul:** TMS 29 uyum testi (→ RR-033).
- **Yol B — Quality Bar (3-5 gün):** MKK VYK + XBRL parser extension. **Kısıt:** `disclosureIndex ≥ 538004` → sadece ~2024 sonrası.
- **Yol C — Hibrit (önerilen):** A baz + B doğrulama + Fintables manuel TMS 29 spot-check.

NRR-002 çıtasını + Faz 0b 24-ay IC zaman çerçevesini birlikte karşılayan tek seçenek **Yol C**.

---

## §1 Mevcut Envanter (Codebase Audit)

| # | Fetcher | Konum | Sağladığı Alanlar | Eksikler (5 ham veri açısından) |
|---|---|---|---|---|
| 1 | **MKK VYK XBRL** (D-170/172) | [`src/data/kap_historical_fetcher.py:58`](../../src/data/kap_historical_fetcher.py#L58) + [`src/data/kap_api_client.py`](../../src/data/kap_api_client.py) | XBRL'den: `Revenue`, `GrossProfit`, `ProfitLoss`, `Assets`, `IssuedCapital` → 5 sütun | **Hiçbiri yok:** market cap, EBITDA, net borç, defter değeri, USD kuru. ⚠️ `IssuedCapital` ≠ defter değeri — sadece çıkarılmış sermaye. **Mevcut XBRL parser value için yetersiz.** |
| 2 | **yfinance fallback** (D-175) | [`src/data/yfinance_fundamentals_fetcher.py:29`](../../src/data/yfinance_fundamentals_fetcher.py#L29) | MKK VYK ile aynı 5 sütun (`revenue`, `gross_profit`, `net_income`, `total_assets`, `equity`) | Aynı. ⚠️ Yahoo'nun BIST verisinde bilinen accuracy sorunları (GitHub `ranaroussi/yfinance#1788`); TMS 29 ayarlaması garanti değil — büyük olasılıkla nominal TRY. |
| 3 | **İş Yatırım Screener** | [`src/signals/layers/connectors/smart_money_connector.py:93`](../../src/signals/layers/connectors/smart_money_connector.py#L93) | ⚠️ ŞU AN sadece 4 alan kullanıyor: `40` (foreign_ratio), `44/45` (1w/1m değişim), `26` (3m hacim). Endpoint 50+ kriter destekliyor. | **Untapped gold mine** — `getScreenerDataNEW` market cap / P/B / EV/EBITDA döndürüyor (Borsa MCP teyidi), kullanılmıyor. |
| 4 | EVDS | [`src/data/evds_client.py`](../../src/data/evds_client.py) ([RR-021](RR-021-TCMB.md)) | ✓ **USD/TRY** (TP.DK.USD.A, RR-021 ile teyit), TÜFE (TMS 29 deflator için) | Per-stock fundamental yok (sadece makro). |
| 5 | KAP XBRL Scorer | [`src/analytics/kap_xbrl_scorer.py`](../../src/analytics/kap_xbrl_scorer.py) | XBRL **surprise** (YoY GrossProfit/NetIncome/Revenue, TÜFE-deflate, cross-sectional rank → ±40 impact) | Surprise faktörü, value faktörü DEĞİL. value için XBRL parser'ı genişletilmesi gerek (yeni alan eşlemeleri). |

**Özet:** Mevcut kodda value için gerekli 5 ham veriden **1'i tam karşılanıyor** (USD kuru, EVDS'den). Diğer 4'ü için yeni integration veya mevcut fetcher genişletilmesi şart.

---

## §2 NRR-002 Kalite Çıtası

NRR-002 metodoloji notu (sec.133)'ten doğrudan alıntı:

> *"value: USD-bazlı F/DD + EV/EBITDA. Nominal F/K YASAK (TMS 29, S4). UFRS/TMS 29 finansalları ZORUNLU (VUK 2025-27 ertelendi). ⚠️ 2022-2024 yapısal kırılma (TMS 29 ilk 2023 sonu) backtest'te işaretlenir."*

Çevirir:
- **Sadece UFRS** — KAP'a filed konsolide IFRS finansalları. VUK (vergi) tabloları value sıralamasını bozar → kaynaktan eleminasyon kriteri.
- **Türkiye PIE statüsü:** BIST listeli tüm şirketler PIE (Public Interest Entity) → UFRS zorunlu ([IFRS Foundation, Turkey jurisdictional profile](https://www.ifrs.org/content/dam/ifrs/publications/jurisdictions/pdf-profiles/turkiye-ifrs-profile.pdf)).
- **TMS 29 (hiperenflasyon muhasebesi):** Türkiye 3-yıllık kümülatif TÜFE >%100 eşiğini aştığı için 2023 yıl sonu itibarıyla TMS 29 zorunlu hâle geldi. Bu, **2022 öncesi nominal vs 2023+ TMS 29-adjusted** arasında bir yapısal kırılma yaratıyor — backtest'te flaglenmesi şart.
- **Nominal F/K yasağı:** Net kâr enflasyon ortamında çok dalgalı + manipüle edilebilir; TMS 29 sonrası bile karşılaştırılabilirlik şüpheli. F/DD ve EV/EBITDA balance-sheet & cash-flow tabanlı olduğu için daha sağlam.

---

## §3 Kaynak Envanteri — Tüm Aday Kanallar

| Kaynak | Sağlar (value için) | UFRS/VUK | BIST kapsama | Erişim | Entegrasyon maliyeti | Notlar |
|---|---|---|---|---|---|---|
| **MKK VYK + XBRL parser extension** (D-170/172) | TEORİDE 5/5 — XBRL'de `TotalLiabilities`, `CashAndCashEquivalents`, `ProfitFromOperatingActivities`, `DepreciationAndAmortisation`, `EquityAttributableToOwnersOfParent` var; parser eklenir | ✅ **UFRS-native** (KAP'a UFRS XBRL filed) — gold standard | Tüm BIST PIE; **kısıt:** `disclosureIndex ≥ 538004` (KAP 4.0+, ~2024'ten sonra) — geçmiş veri çok kısıtlı | Prod token bekliyor (D-170 PR), bireysel/dev Basic auth | **Düşük-orta** ([`kap_historical_fetcher.py:58`](../../src/data/kap_historical_fetcher.py#L58) `_XBRL_MAP`'e 4-5 satır ekleme); piyasa cap için ayrı hisse-sayısı kaynağı gerek | TMS 29 mevcut XBRL'de native; 2022-2024 break otomatik. ⚠️ **Tarihsel derinlik darboğazı.** |
| **İş Yatırım `getScreenerDataNEW`** | LİKELİ 4/5 (market cap, P/B, EV/EBITDA, EBITDA değerleri pre-computed; defter değeri implicit) | ⚠️ Belirsiz — İş Yatırım KAP'tan besleniyor (UFRS) ama TMS 29 ayarı yapıp yapmadığı **kalite research gerektirir** → RR-033 | ~520 BIST ticker (kod confirme); pre-computed → daha derin geçmiş ihtimali | Login yok, robots-safe, ücretsiz | **Çok düşük** ([connector zaten var](../../src/signals/layers/connectors/smart_money_connector.py#L93), sadece criterias listesi genişletilir + field ID eşleme) | **Quick win adayı.** TMS 29 ayar sorusu Yol A'nın kritik önkoşulu — RR-033 ile teyit edilmeli |
| **yfinance** (D-175) | Kısmen — market cap + shares outstanding + financials | ⚠️ Yahoo'nun upstream sağlayıcısı belirsiz (büyük olasılıkla **nominal TRY**, TMS 29 ayarsız) | ~500+ BIST ticker; quarterly+annual ama Yahoo'nun bilinen accuracy sorunları | Ücretsiz, login yok | Düşük (mevcut) | NRR-002 kalite çıtasına uymama riski yüksek; **sadece fallback** olarak makul |
| **Fintables** | UFRS finansallar + ratios + enflasyon ayarı (Akademi'de açıkça anlatılmış) | ✅ UFRS + TMS 29 farkındalığı var ([Fintables Akademi](https://fintables.com/akademi/ekonomi-analizi-101/finansal-tablolarda-enflasyon-duzeltmesi-nasil-yapilir)) | Tüm BIST | Manuel Excel/CSV export var; bireysel **API yok** ([RR-001](RR-001-fintables-takas-scraper.md) teyidi); scraping → bot detection | Yüksek (scraping fragile, ToS gri) | Programatik pipeline için **uygun değil**. Manuel one-shot validation için iyi referans. |
| **Borsa MCP** (saidsurucu/borsa-mcp) | 50+ filtre (valuation/profitability/dividend/returns/market kategorileri) | KAP + Yahoo backed → ⚠️ KAP path RR-031'de ölü (Next.js); kalan path yfinance'e indirgenebilir | 758 BIST şirket iddiası | Ücretsiz, MCP server (Python 3.11+) | Düşük (external dep) ama **kalite risk:** kendi backend'i yfinance/dead-KAP karışımı → bilinmeyen kalite | **Kalite research gerektirir** — underlying data path doğrulanmadan güvenilmez |
| **Matriks Kurumsal REST API** ([RR-021 §2](RR-021-TCMB.md)) | AKD/takas + likely fundamentals | Belirsiz | Tüm BIST | Bireysel uygun, fiyat teklifi gerek (form), trial var | Düşük-orta (REST) | **Kalite research gerektirir** — fiyat + tam alan kapsama bilgisi yok |
| **Finnet Analiz Expert API** | "Türkiye sermaye piyasası verisi, 1200+ fonksiyon" | Belirsiz (Türk sağlayıcı → UFRS muhtemel) | Tüm BIST iddiası | Bireysel yıllık ~2,000-3,000 TL ([Finnet kampanya](https://www.finnet.com.tr/finnetstore/tr/kampanya/kampanyalarimiz)) | Düşük (REST) | **Kalite research gerektirir** — TMS 29 desteği ve API alan listesi belirsiz |
| **TradingEconomics API** | EPS, Net Income, Sales Revenue, Debt, **EBITDA**, Equity Capital | Belirsiz | Türkiye genel + select stocks | Freemium API key | Düşük | **Kalite research gerektirir** — per-ticker depth + UFRS uyumu doğrulanmalı |
| **FMP / Finnhub / Alpha Vantage** | Global fundamentals şablonu | ❌ — Türk hisse kapsaması doğrulanmadı; web search "BIST coverage" sorusuna spesifik cevap vermedi | Belirsiz | Freemium | Düşük | **Kalite research gerektirir.** Türk üye olmadıkları için TMS 29 nüansını yansıtma ihtimali düşük |
| **EVDS** | USD/TRY + TÜFE (USD bazına çevirme için ZORUNLU) | n/a (makro) | n/a | Ücretsiz ([RR-021](RR-021-TCMB.md)) | ✓ Entegre | Her senaryoda yan kaynak olarak gerekli — değiştirilemez |
| **KAP Next.js frontend scraping** | XBRL filing detay | UFRS | Tüm BIST | RR-031'de **ölü** (WAF, 429, Server Action rotasyonu) | Çok yüksek (fragile) | ❌ Eleminasyon — pratik değil |

---

## §4 Uyum Matrisi: 5 Ham Veri × Kaynak

| Kaynak | Market Cap | EBITDA | Net Borç | Defter Değeri | USD Kuru | UFRS? | Kapsama | Entegrasyon |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|:---:|
| MKK VYK + parser ext | △ (hisse adedi başka yerden) | ✅ (XBRL'de var, parser eklenir) | ✅ (XBRL) | ✅ (XBRL — `EquityAttributable...`) | n/a | ✅ | Tüm BIST, **≥2024 sonu** | düşük-orta |
| İş Yatırım Screener | ✅ pre-computed | ✅ pre-computed | △ (türevsel) | ✅ implicit | n/a | ⚠️ RR-033 | ~520 BIST, geçmiş ?, **TMS 29 kalite research** | **çok düşük** |
| yfinance | ✅ | ✅ | ✅ | ✅ | n/a | ❌ nominal | ~500, accuracy issues | düşük (mevcut) |
| Fintables (manuel) | ✅ | ✅ | ✅ | ✅ | n/a | ✅ | Tüm BIST | yüksek (no-API) |
| Borsa MCP | ✅ | ✅ | ✅ | ✅ | ✅ FX | ⚠️ kalite research | 758 iddia | düşük (ama kalite risk) |
| Matriks/Finnet/TE/FMP | ? | ? | ? | ? | n/a | ⚠️ kalite research | ? | düşük |
| EVDS | n/a | n/a | n/a | n/a | ✅ | n/a | n/a | ✓ mevcut |

NRR-002 çıtasını **netest karşılayanlar:** MKK VYK + parser extension (kalite ★★★, kapsama ★) **VEYA** İş Yatırım Screener (kalite ★★ kalite research'e bağlı, kapsama ★★★, integration ★★★).

---

## §5 MKK VYK Netleştirmesi

**Soru:** "MKK VYK production erişim value verilerini sağlar mı, yoksa sadece XBRL surprise mı?"

**Cevap:** MKK VYK *kaynak* olarak value için **yeterlidir** — KAP'a filed UFRS XBRL'de gerekli her şey var (`TotalLiabilities`, `CashAndCashEquivalents`, `ProfitFromOperatingActivities`, `DepreciationAndAmortisation`, `EquityAttributableToOwnersOfParent`). Mevcut kod **bir alt küme** parse ediyor:

[`kap_historical_fetcher.py:58`](../../src/data/kap_historical_fetcher.py#L58):
```python
_XBRL_MAP: dict[str, str] = {
    "Revenue":       "revenue",
    "GrossProfit":   "gross_profit",
    "ProfitLoss":    "net_income",
    "Assets":        "total_assets",
    "IssuedCapital": "equity",  # ⚠️ paid-in capital — değil book value
}
```

**MKK VYK şart değil ama tercih edilebilir.** Trade-off:
- **MKK VYK + parser extension:** UFRS-native, TMS 29 native, en yüksek kalite. **Aleyhine:** kapsama `disclosureIndex ≥ 538004` (geçmiş ~2024+), prod token bekleniyor.
- **İş Yatırım Screener:** Aynı UFRS verisinden türetilmiş ratio'lar (İş Yatırım da KAP'tan besleniyor). **Aleyhine:** TMS 29 ayar yapısı kalite research gerektirir (→ RR-033), "kara kutu" katmanı.

İkisi birden kullanmak → **cross-validation imkanı** (best practice). İş Yatırım baz, MKK VYK belirli ticker'larda doğrulama.

---

## §6 Öneri (KARAR DEĞİL — maintainer, DEC-039 pattern)

Üç yol, artan kalite/maliyet sırasıyla:

### Yol A — Quick Win (1-2 gün)
**`IsYatirimScreenerConnector`'ı value alanlarına genişlet.**

- Mevcut connector'da `criterias` listesi 4 alanla sınırlı; `getScreenerDataNEW` dokümante edilmiş 50+ field ID destekliyor (Borsa MCP teyidi).
- Adım 1: Browser DevTools ile İş Yatırım gelişmiş-hisse-arama formunda market cap / P/B / EV/EBITDA filtre ID'lerini yakala.
- Adım 2: Connector'a yeni döndürme alanları ekle (fetch ile dönen response zaten geniş JSON; sadece filter genişletme).
- Adım 3: Faz 0b USD-bazlı value: TRY ratio → USD/TRY (EVDS) ile çevir → cross-sectional rank.

**Kalite riski:** TMS 29 ayarı belirsiz — İş Yatırım'ın TMS 29-adjusted veriyi mi yoksa nominal mi sunduğu **ayrı research** gerektirir → **RR-033** (Yol A'nın önkoşulu).

### Yol B — Quality Bar (3-5 gün)
**MKK VYK + XBRL parser extension.**

- D-170 prod token gelince: [`_XBRL_MAP`](../../src/data/kap_historical_fetcher.py#L58)'e 4 satır ekle (`TotalLiabilities`, `CashAndCashEquivalents`, `ProfitFromOperatingActivities`, `DepreciationAndAmortisation`, `EquityAttributableToOwnersOfParent`).
- Market cap için hisse adedi: KAP genel kurul bildirimleri veya yfinance `sharesOutstanding`.
- USD kuru: EVDS (mevcut).

**Kısıt:** Sadece `disclosureIndex ≥ 538004` (post-2024). Faz 0b cross-sectional IC için 24 ay geçmiş gerek → MKK VYK tek başına yetmez, **eski tarih için fallback şart**.

### Yol C — Hibrit (önerilen)
**Yol A baz + Yol B doğrulama + yfinance/Fintables manuel cross-check.**

- **İş Yatırım Screener** → ana value veri akışı (en düşük entegrasyon maliyeti, en geniş kapsama).
- **MKK VYK + extension** → 2024+ kalite kontrolü (5-10 ticker'da spot check).
- **Fintables manuel Excel** → bir kez sabit dönem (örn. 2023-Q4 ilk TMS 29) için **TMS 29 adjustment doğrulaması**.
- **yfinance** → tarihsel derinlik fallback (kalite "stale"/uncertain bayraklı).

**NRR-002 çıtasını + Faz 0b 24-ay IC zaman çerçevesini birlikte karşılayan tek seçenek Yol C.**

---

## §7 Kalite Research Gerektiren Kaynaklar (ayrı RR adayları)

Aşağıdakiler için UFRS/TMS 29 uyumu + per-ticker derinlik **uzmanlık + ayrı canlı test** gerektirir; bu raporda kapsam dışı:

1. **İş Yatırım Screener TMS 29 ayar durumu** — kritik (Yol A'nın kalite riski buna bağlı). → **RR-033** olarak açıldı (bu PR ile).
2. **Borsa MCP** underlying data path (yfinance mi, başka mı).
3. **Finnet Analiz Expert** alan listesi + TMS 29 ayar.
4. **Matriks Kurumsal API** alan kapsama + TMS 29.
5. **TradingEconomics + FMP/Finnhub** BIST coverage derinliği ve UFRS uyumu.

---

## Bottom line

Faz 0b value Faktörü için **en hızlı + makul kalite yolu = Yol A (İş Yatırım Screener extension)**, ama TMS 29 mini-research'i (RR-033) Yol A'ya **ön-koşul** olmalı. Yol B daha kaliteli ama tarihsel derinlik darboğazı Faz 0b 24-ay IC için yetmiyor — yalnız başına olmaz. Yol C (hibrit) NRR-002 çıtasını + Faz 0b zaman çerçevesini birlikte karşılayan tek seçenek görünüyor.

Karar maintainer'da (DEC-039 paterni).
