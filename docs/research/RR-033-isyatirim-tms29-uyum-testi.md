# RR-033 — İş Yatırım Screener TMS 29 Uyum Testi (Veri Kalitesi Doğrulama)

**Tarih:** 25 Mayıs 2026
**Yazar:** Claude Code (Builder) — research plan
**Status:** ⏳ Bekleyen Builder execution (DEC-039 kategori-a, veriyle test)
**Bağlı:** [RR-032 §6 Yol A önkoşulu](RR-032-FIZIBILITE.md#§6-öneri-karar-değil--orchestrator--the maintainer-dec-039-pattern); NRR-002 ([SPEC_PIVOT_ARCHITECTURE_1.md:133](../SPECS/SPEC_PIVOT_ARCHITECTURE_1.md#L133)); D-170/172

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
- **Build YOK.** Bu RR sadece veri karşılaştırma çıktısı üretir; herhangi bir production fetcher değişikliği YAPMAZ. RR-032 §6 Yol A/B/C kararı sonrası ayrı spec açılır.

---

## Sonraki Adım

Bu RR-033 bir Builder execution specine dönüştürülür (örn. D-XXX-rr033-tms29-test). Builder:
1. 4 ticker için İş Yatırım screener probe scripti yazar (throwaway, `scripts/_probe_*.py`)
2. 4 ticker için 2023 yıllık KAP UFRS-TMS 29 finansallarını parse eder
3. Karşılaştırma tablosunu doldurur
4. Bu dosyaya **"Sonuç"** bölümü ekler (karar ağacı çıktısı)
5. RR-032 §6 ve RESEARCH_REGISTRY status alanlarını günceller
