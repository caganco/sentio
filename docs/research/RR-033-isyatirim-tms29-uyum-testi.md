# RR-033 — İş Yatırım Screener TMS 29 Uyum Testi (Veri Kalitesi Doğrulama)

**Tarih:** 25 Mayıs 2026
**Yazar:** Claude Code (Builder) — research plan
**Status:** ⏳ Bekleyen Builder execution (DEC-039 kategori-a, veriyle test)
**Bağlı:** [RR-032 §6 Yol A önkoşulu](RR-032-FIZIBILITE.md#§6-öneri-karar-değil--orchestrator--cagan-dec-039-pattern); NRR-002 ([SPEC_PIVOT_ARCHITECTURE_1.md:133](../SPECS/SPEC_PIVOT_ARCHITECTURE_1.md#L133)); D-170/172

---

## Amaç

İş Yatırım `getScreenerDataNEW`'in döndürdüğü fundamental değerler (market cap, P/B, EV/EBITDA, EBITDA) **TMS 29 enflasyon-muhasebesi ayarlı UFRS finansallarından mı**, yoksa **nominal/VUK'tan mı** türetiliyor?

Bu, **Yol A / Yol C'nin (value veri akışı) NRR-002 kalite çıtasını geçip geçmediğini** belirler — value faktörünün tüm geçerliliği buna bağlı.

NRR-002 kuralı:
> *"Nominal F/K YASAK (TMS 29, S4). UFRS/TMS 29 finansalları ZORUNLU."*

Eğer İş Yatırım nominal değer veriyorsa, Yol A/C tek başına NRR-002'yi karşılamaz — MKK VYK'ya (Yol B) ağırlık verilmek zorunda kalınır. Eğer TMS 29-adjusted veriyorsa, Yol A entegre integration cost ile yeşil ışık alır.

---

## Yöntem (veriyle test, DEC-039 kategori-a — Build YOK, sadece veri karşılaştırma)

### 1. Ticker seçimi (örneklem sağlamlığı için 3-4 adet)

Farklı sektörlerden, **TMS 29 etkisi belirgin olanlar** (yüksek maddi duran varlık / stok → enflasyon ayarı büyük olur):

| Ticker | Sektör | Neden seçildi |
|---|---|---|
| **THYAO** | Havayolu | Yüksek uçak filosu (maddi duran varlık) → TMS 29 etkisi belirgin |
| **EREGL** | Demir-çelik | Ağır makine + büyük stok → enflasyon ayarı büyük |
| **BIMAS** | Perakende | Yoğun stok devri + mağaza yatırımı → ayar farkı görünür |
| **TUPRS** | Rafineri | Devasa sabit yatırım + ham petrol stoku → en agresif ayar adayı |

> Not: Tek ticker'la test yapmak fragiledir; 3-4 ticker = uyum/uyumsuzluk sinyallerinin tutarlılığı doğrulanabilir.

### 2. Veri Kaynakları (her ticker için 2023-Q4 veya 2024 dönemi)

**A. İş Yatırım Screener çıktısı:**
- `IsYatirimScreenerConnector` ([`smart_money_connector.py:93`](../../src/signals/layers/connectors/smart_money_connector.py#L93)) field ID'leri reverse-engineer edilecek
- Toplanacak alanlar:
  - Market cap (piyasa değeri)
  - Defter değeri (book value) — veya P/B'den çıkarılabilir
  - EBITDA
  - EV/EBITDA
- Yöntem: Browser DevTools → İş Yatırım gelişmiş-hisse-arama → her alanın criteria ID'sini yakala → connector'a sadece o ticker için filter ile çağrı (ek dosya yazma yok; throwaway probe)

**B. KAP'a filed UFRS-TMS 29 konsolide finansalları (gerçek kaynak):**
- KAP filing detayından çekilecek (XBRL veya PDF konsolide finansal tablo)
- Her ticker için 2023-Q4 yıllık finansalları (TMS 29 ilk uygulanan dönem)
- Hesaplanacak değerler:
  - Market cap = `hisse sayısı × kapanış fiyatı` (kapanış 2023-12-29 BIST)
  - Defter değeri = `EquityAttributableToOwnersOfParent` (XBRL leaf)
  - EBITDA = `ProfitFromOperatingActivities + DepreciationAndAmortisation` (XBRL)
  - EV = `Market cap + TotalLiabilities − CashAndCashEquivalents`
  - EV/EBITDA = türetildi

### 3. Karşılaştırma + Karar Mantığı

Her ticker için tablo:

| Alan | İş Yatırım | UFRS-TMS 29 (KAP) | Fark (%) | Yargı |
|---|---|---|---|---|
| Market cap | … | … | … | EŞLEŞİYOR / NOMİNAL / KARIŞIK |
| Defter değeri | … | … | … | … |
| EBITDA | … | … | … | … |
| EV/EBITDA | … | … | … | … |

**Eşleşme eşiği:**
- **≤%2 fark** → "EŞLEŞİYOR" (TMS 29-adjusted — yuvarlama/period-end farkı kabul edilir)
- **%2-%15 fark** → "BELİRSİZ / KARIŞIK" (alan-bazlı detay incelenir)
- **>%15 fark** → "NOMİNAL" (TMS 29-adjusted DEĞİL — fark enflasyon ayarı büyüklüğüne yakın)

### 4. Çıktı — Net Karar Ağacı

```
Tüm 4 ticker'da tüm 4 alan EŞLEŞİYOR
    → İş Yatırım = TMS 29-adjusted UFRS
    → RR-032 Yol A/C YEŞİL — kullan
    
Tüm 4 ticker'da tüm 4 alan NOMİNAL
    → İş Yatırım nominal kullanıyor
    → RR-032 Yol A/C KIRMIZI — NRR-002 çıtasını geçmez
    → MKK-ağırlıklı Yol B'ye geç (tarihsel derinlik feda edilir)
    
KARIŞIK (bazı alan adjusted, bazı nominal)
    → Hangi alanların güvenilir olduğunu işaretle
    → Güvenilir alanları kullan, diğerlerini MKK VYK'dan çek
    → Yol C hibrit (RR-032 §6) doğrulanır — alan-bazlı routing
```

### 5. Beklenen Bulgular (hipotez, test ile teyit edilecek)

- **H1 (en olası):** İş Yatırım market cap ✓ (anlık hisse fiyatı × sayı, ayarsız native), defter değeri/EBITDA muhtemel TMS 29 (KAP feed), EV/EBITDA türevsel → "KARIŞIK". → Yol C hibrit doğrulanır.
- **H2:** Tümü nominal (eski cache / ayar yapılmamış legacy görünüm). → Yol B zorunlu.
- **H3:** Tümü TMS 29 (İş Yatırım 2024+ tam dönüşmüş). → Yol A en uygun.

Test sonucu hangi hipotezi destekliyor: rapor edilir.

---

## Kısıtlar ve Caveat'lar

- **Sadece 2023-Q4 / 2024 dönem testi.** 2022 öncesi (TMS 29 öncesi) ayrıca test edilmez — RR-032 §2'deki "yapısal kırılma" ayrı bir konu.
- **TMS 29 hesaplama nüansları.** Standart farklı bilanço kalemleri için farklı tarihsel-maliyet endeksleme kullanır. KAP filed UFRS-TMS 29 zaten bunu yapıyor olduğu için referans olarak güvenli — ancak %2 eşleşme eşiği bu nedenle "%0 fark" beklenmez.
- **İş Yatırım veri yayım periyodu.** Şirket finansalları KAP'a filed sonrası belirsiz bir gecikme ile İş Yatırım'a yansır. Test gününde son finansal periyot tutarlı seçilmeli (örn. 2023 yıllık → tüm ticker'larda 2024 Q1 sonrasında erişilebilir olmalı).
- **Build YOK.** Bu RR sadece veri karşılaştırma çıktısı üretir; herhangi bir production fetcher değişikliği YAPMAZ. RR-032 §6 Yol A/B/C kararı sonrası ayrı direktif açılır.

---

## Sonraki Adım

Bu RR-033 bir Builder execution direktifine dönüştürülür (örn. D-XXX-rr033-tms29-test). Builder:
1. 4 ticker için İş Yatırım screener probe scripti yazar (throwaway, `scripts/_probe_*.py`)
2. 4 ticker için 2023 yıllık KAP UFRS-TMS 29 finansallarını parse eder
3. Karşılaştırma tablosunu doldurur
4. Bu dosyaya **"Sonuç"** bölümü ekler (karar ağacı çıktısı)
5. RR-032 §6 ve RESEARCH_REGISTRY status alanlarını günceller

---

## Sonuç (D-179 execution — 25 May 2026)

**Verdict: ⚠️ INCONCLUSIVE.** MKK VYK *dev gateway* TMS 29 dönemine ait veri içermiyor — clean apples-to-apples karşılaştırma imkânsız. Pipeline + İş Yatırım field ID'leri başarıyla doğrulandı; TMS 29 conformance verdict için **prod MKK VYK token (D-170)** ya da **IR PDF fallback** şart.

### Yürütüldü (throwaway probe'lar, src/ dokunulmadı)

| # | Probe | Sonuç |
|---|---|---|
| 1 | İş Yatırım field-ID resolution (HTML scrape `data-tanimid`) | ✅ 307 field bulundu, 52'si value-relevant. Kullanılacak 6 ID kesinleşti |
| 2 | İş Yatırım `getScreenerDataNEW` value probe (4 ticker) | ✅ 4 ticker × 6 alan: HTTP 200 in 0.2s, tüm değerler çekildi |
| 3 | MKK VYK XBRL probe (KAP referans, EquityAttributableToOwnersOfParent) | ⚠️ Pipeline OK ama dev gateway'in son verisi **2023 Q3** — TMS 29 ÖNCESİ |
| 4 | TUPRS IR PDF cross-check | ⏭️ Yapılmadı (Sonuç ⚠️ olduğu için manuel PDF zaten önerilen sonraki adım) |
| 5 | Karşılaştırma + karar | Apples-to-oranges (period mismatch); discriminative olmayan signal |

### İş Yatırım Field-ID Tablosu (Yol A integrasyonu için kalıcı referans)

| tanimid | Açıklama | Kullanım |
|:---:|---|---|
| **8** | Piyasa Değeri (mn TL) | Market cap TRY |
| **9** | Piyasa Değeri (mn $) | Market cap **USD** — NRR-002 USD-bazlı value için ideal |
| **29** | Cari FD/FAVÖK | Current EV/EBITDA |
| **30** | Cari PD/DD | Current P/B — F/DD için ana sinyal |
| **163** | Cari Net Nakit (mn TL) | Net cash (negatif = net borç) |
| **388** | Yıllık Cari FAVÖK (mn TL) | TTM EBITDA |

`getScreenerDataNEW` payload örneği: criterias = `[["8","-1e9","1e9","False"], ...]` — mevcut [smart_money_connector.py:93](../../src/signals/layers/connectors/smart_money_connector.py#L93) connector pattern'i bire bir genişletilebilir.

### Karşılaştırma Tablosu (Apples-to-Oranges — Caveat'lı)

| Ticker | Alan | KAP Q3 2023 (TL) | İş Yatırım Cari implied (TL) | %fark | Yön |
|---|---|---:|---:|---:|:---:|
| **THYAO** | Book Value (EAOoP) | 343,276,000,000 | 975,035,714,286 | **+184%** | UP |
| | Net Cash (cash − liab) | -582,032,000,000 | -530,401,000,000 | +8.9% | UP |
| **EREGL** | Book Value (EAOoP) | 161,817,534,000 | 294,903,225,806 | **+82%** | UP |
| | Net Cash | -91,947,088,000 | -31,471,280,000 | +65.8% | UP |
| **BIMAS** | Book Value (EAOoP) | 29,804,484,000 | 188,860,759,494 | **+534%** | UP |
| | Net Cash | -66,123,867,000 | -28,117,310,000 | +57.5% | UP |
| **TUPRS** | Book Value (EAOoP) | 71,853,782,000 | 352,797,767,442 | **+391%** | UP |
| | Net Cash | -95,067,246,000 | +74,706,220,000 | +178.6% | UP |

**Yön (user vurgusu):** 4/4 ticker, defter değerinde İş Yatırım > KAP Q3 2023 (UP). Aynı şekilde net cash'te de İş Yatırım daha az borçlu görünüyor (UP).

### Neden Bu Verdict Discriminative DEĞİL

Karşılaştırma iki çakışan etkiyi ayırt edemiyor:
1. **TMS 29 inflation restatement** (KAP Q3 2023'ten sonra zorunlu, 2023-Q4'te ilk uygulandı) — özkaynağı/fixed-asset'leri YUKARI taşır
2. **Period gap (Q3 2023 → May 2026, ~2.5 yıl):**
   - Türkiye CPI bu dönemde yaklaşık **2.5-3x kümülatif artış** gösterdi
   - Şirket retained earnings (THYAO/BIMAS/TUPRS pozitif net kâr; EREGL zarar)

THYAO için: KAP Q3 2023 EAOoP = 343 bn TL, İş Yatırım implied BV = 975 bn TL → ratio **2.84x**. CPI restatement TEK BAŞINA aşağı yukarı bu büyüklüğü açıklayabilir. Yani:
- **(a)** İş Yatırım TMS 29-adjusted + 2.5 yıl retained earnings → muhtemel +184%
- **(b)** İş Yatırım nominal + 2.5 yıl retained earnings + revaluation → muhtemel +184%

İkisi de aynı yöne ve büyüklüğe çıkar. **Discriminative olmayan signal.**

### Kök Neden — MKK VYK Dev Gateway

[kap_api_client.py:62](../../src/data/kap_api_client.py#L62) ile `https://apigwdev.mkk.com.tr`'ye live test:
- ✅ Token çalışıyor (Basic auth, HTTP 200, `lastDisclosureIndex=1231017`)
- ✅ XBRL pipeline çalışıyor (12-14 FR/ticker pagination + leaf extraction OK)
- ❌ **Dev gateway TEST SANDBOX** — son veri 2023 Q3 (THYAO/EREGL/BIMAS/TUPRS hepsi için aynı). 2023-Q4 (TMS 29 ilk dönem) ve sonrası YOK.

Bu, dev gateway'in inherent limit'i — `_MIN_DISCLOSURE_INDEX=538004` (KAP 4.0+) constraint'iyle ilgili değil; dev'de o data hiç var değil.

### Bel Kemiği Doğrulaması — EquityAttributableToOwnersOfParent (User Vurgusu)

D-179'un en önemli teknik validasyonu: doğru XBRL leaf'i kullanıldı.

| Ticker | EquityAttributableToOwnersOfParent | Equity (top-level) | IssuedCapital (YANLIŞ — paid-in capital) | EAOoP / IssuedCapital |
|---|---:|---:|---:|---:|
| THYAO | 343,276,000,000 | 343,400,000,000 | 1,380,000,000 | **249× büyük** |
| EREGL | 161,817,534,000 | 166,083,088,000 | 3,500,000,000 | **46×** |
| BIMAS | 29,804,484,000 | 30,043,083,000 | 607,200,000 | **49×** |
| TUPRS | 71,853,782,000 | 72,564,910,000 | 1,926,796,000 | **37×** |

`IssuedCapital` defter değerinin **% 0.4-3'ü** kadar. Mevcut [`kap_historical_fetcher.py:58`](../../src/data/kap_historical_fetcher.py#L58) `_XBRL_MAP`'in `IssuedCapital → equity` eşlemesi **value faktör için katastrofik yanlış** — RR-032 §1 #1 doğru flag attı. Bu, Yol B (MKK VYK + parser ext.) için zorunlu düzeltme — `_XBRL_MAP`'e `EquityAttributableToOwnersOfParent → equity_attributable` satırı eklenmeli ve hangisi var olursa o tercih edilmeli.

### EBITDA XBRL Element Adı Sorunu

Test edilen 3 element ismi (`ProfitFromOperatingActivities`, `DepreciationAndAmortisation`, `DepreciationAndAmortisationExpense`) hiçbir ticker'da BULUNAMADI. UFRS taxonomy'sinde aday alternatifler:
- `OperatingProfitLoss`
- `ProfitLossFromOperatingActivities`
- `ProfitBeforeFinancialIncomeExpenses`
- D&A için: cash flow statement leaf'leri (`AdjustmentsForDepreciationExpense`)

Bu, **Yol B parser extension'ı sırasında ayrı bir mini-research gerektirir** — XBRL element isimleri firma/sektör/sürüm bazında değişebilir. RR-032 §6 Yol B'nin "3-5 gün" tahmini bu nüansı içermeli.

### Hipotez Sonucu (RR-033 §5)

- **H1 (karışık):** ❌ Test edilemedi (discriminative değil)
- **H2 (tüm nominal):** ❌ Doğrudan reddedilemiyor ama veriyle eşleşmiyor da
- **H3 (tümü TMS 29):** ❌ Doğrudan onaylanamıyor

**Yeni hipotez (D-179 sonrası):** **H4 — INCONCLUSIVE: Comparison apparatusu sound, KAP referans data infrastructure (dev gateway) TMS 29 dönemini kapsamıyor.**

### Karar (RR-033 §4 ağacı): RR-032 Yol A/B/C için

**Yol A/B/C kararı VERILEMEZ — D-179 TMS 29 conformance sorusunu cevaplayamadı.**

İki yol açık:

**Path 1 — Wait-and-rerun:** D-170 prod MKK VYK token gelince D-179'u tekrar koş. Aynı 4 ticker × 2024 yıllık (TMS 29-adjusted) referansı ile. Apples-to-apples karşılaştırma → kesin verdict. **Süre:** D-170 timeline'a bağlı.

**Path 2 — IR PDF fallback (RR-032'nin opsiyonel "ek doğrulama" path'i şimdi mandatory):** 4 şirket için 2023 yıllık konsolide UFRS-TMS 29 finansal raporlar (KAP üzerinden PDF + şirket IR siteleri) — `pdfplumber` ile manuel/yarı-otomatik 4 alan ekstraksiyonu. **Süre:** ~1-2 saat. **Risk:** PDF taxonomy varyasyonu, dipnot karmaşıklığı.

**Öneri (yine karar değil — DEC-039):**
- Eğer D-170 prod token < 1 hafta içinde geliyorsa → Path 1 (bekle, temiz test)
- Eğer D-170 timeline belirsiz/uzaksa → Path 2 (IR PDF, en az TUPRS + EREGL için)
- Her iki path de İş Yatırım field ID kataloğunu (yukarıdaki 6 ID) zaten kalıcı kazanım olarak verir — Yol A integrasyonu kaliteden bağımsız hazır

### Kalıcı Çıktılar (D-179'dan)

1. **İş Yatırım `getScreenerDataNEW` value field haritası:** 6 ID tabloda kayıtlı, Yol A integrasyonu için hazır
2. **MKK VYK pipeline doğrulaması:** Auth + pagination + XBRL extraction çalışıyor, prod token gelince kullanıma hazır
3. **`_XBRL_MAP` hatası onaylandı:** `IssuedCapital ≠ Equity` (37-249× fark) — Yol B için kritik fix
4. **EBITDA XBRL element ismi taxonomy sorunu:** Yol B parser extension'ında ayrı çözülmeli
