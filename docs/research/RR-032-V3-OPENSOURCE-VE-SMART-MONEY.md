# RR-032-V3 — Açık-Kaynak Repo İzleme + Smart Money Veri Kanalları

**Tarih:** 30 Mayıs 2026
**Yazar:** Claude Code (Builder) — GitHub recon (kopyalama YOK) + codebase grep + canlı GET teyidi
**Status:** ⏳ Karar bekliyor (the project, DEC-039)
**Bağlı:** [RR-032](RR-032-FIZIBILITE.md), [RR-032-V2](RR-032-V2-GENISLETILMIS-ENVANTER.md), [RR-033](RR-033-isyatirim-tms29-uyum-testi.md), [RR-034](RR-034-isyatirim-usd-feasibility.md), [RR-001](RR-001-fintables-takas-scraper.md), [RR-002](RR-002-akd-terminalleri-python.md), [RR-020](RR-020-BIST-VERISI-MAP.md)

> **Etik/lisans:** Hiçbir repo kodu kopyalanmadı. Sadece **kaynak-kanal keşfi** (endpoint URL'leri) yapıldı. borsapy (Apache-2.0) ve borsa-mcp (MIT) permissive → kanal bilgisi serbest. Kanallar kendi isteğimizle (repo kodu çalıştırmadan) canlı GET ile teyit edildi.

---

## TL;DR — HEADLINE bulgu

**★★ İş Yatırım MaliTablo endpoint = Faz 0b tarihsel fundamental darboğazını ÇÖZEN ücretsiz kanal.**

borsapy'nin (Apache-2.0) izini sürerek bulundu, canlı teyit edildi:
```
GET https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo
    ?companyCode=THYAO&exchange=TRY&financialGroup=XI_29
    &year1=2024&period1=12&year2=2023&period2=12&...   (4 dönem/çağrı, sayfalanır)
→ HTTP 200, JSON, 147 satır bilanço+gelir+nakit; value1..value4 = dönem kolonları
```
- **Tarihsel:** 2004 → Q1 2026 (~15 yıllık / ~40 çeyreklik, şirket kartında dropdown).
- **UFRS:** `financialGroup=XI_29` (Seri XI No:29, sanayi) / `UFRS` (banka) — KAP'a filed konsolide UFRS.
- **Defter değeri:** itemCode **`2O` = "Ana Ortaklığa Ait Özkaynaklar"** = `EquityAttributableToOwnersOfParent` — RR-033'ün "MUTLAKA bu leaf, IssuedCapital DEĞİL" dediği tam kalem. `3C` Satış Gelirleri, `2N` Toplam Özkaynak da var.
- **Ücretsiz, programatik (JSON AJAX), login yok.** ToS gri (`/_layouts/` robots-disallowed — RR-005 ile aynı sınıf).
- **Çapraz doğrulama:** THYAO 2024 özkaynak 890bn TL ÷ mktcap 409bn → P/B 0.46 ≈ TradingView 0.447 ≈ İş Yatırım screener PD/DD 0.42. İçsel tutarlı.

**Sonuç (kullanıcı çerçevesi: "yeni kanal bulunursa EODHD kararı erteleyebilir"):** EODHD €60/ay kararı **ertelenebilir** — İş Yatırım MaliTablo aynı veriyi (UFRS geçmiş fundamental) ÜCRETSİZ + daha derin (2004+) veriyor. RR-034'ün "darboğaz = geçmiş TL fundamental kaynağı" sonucu bu kanalla kapanır. Kalan tek açık: TMS 29 doğrulaması (RR-033) — ama artık MKK prod token beklemeden bu ücretsiz geçmiş seriyle test edilebilir.

---

## BÖLÜM A — Açık-Kaynak Repo İzleme

GitHub recon (gh API metadata + kaynak dosya URL tespiti, kod indirme yok):

| Repo | Lisans | Son commit | Fundamental? | Kaynak kanalı | Geçmiş | RR-032-V2'de yeni mi? |
|---|---|---|---|---|---|---|
| **saidsurucu/borsapy** | Apache-2.0 | 04 May 2026 | ✓ | İş Yatırım **MaliTablo** (Data.aspx/MaliTablo, XI_29/UFRS); kap.py; tradingview×5; canlidoviz/dovizcom; hedeffiyat; viop | **time-series** (2004+) | ★★ **MaliTablo = YENİ** |
| **saidsurucu/borsa-mcp** | MIT | 04 May 2026 | ✓ | **Mynet** (`finans.mynet.com/borsa/hisseler/`) bilanço+gelir tablosu; isyatirim_provider; kap_provider; dovizcom FX | dönemsel (Q1/Q2/Q3/Yıllık) | **Mynet statements = YENİ** |
| **serkankoci61/isyatirim-bist-screener** | (kontrol) | 09 May 2026 | ✓ | İş Yatırım **sirket-karti.aspx** (şirket kartı HTML); **stockanalysis.com/list/borsa-istanbul/**; getmidas.com (temettü) | snapshot+hedef | **stockanalysis.com = YENİ** |
| labyrinthmomenta/bist-momentum-screener | — | 29 May 2026 | ✗ (momentum) | fiyat | — | hayır |
| korayas/bist-panel, gorkemmeteer/* | — | May 2026 | ✗ (teknik) | fiyat/teknik | snapshot | hayır |

### RR-032-V2'de OLMAYAN yeni kanallar (canlı teyitli)

1. **★★ İş Yatırım MaliTablo** — yukarıda (HEADLINE). Ücretsiz, JSON, 2004+, UFRS, itemCode 2O=defter değeri. **Faz 0b çözücü.**
2. **Mynet financial statements** (`finans.mynet.com/borsa/hisseler/{slug}/`) — borsa-mcp MIT kullanıyor; BilancoKalemi+KarZararKalemi dönemsel (Q1-Q4/Yıllık). HTML scrape, dinamik slug (url_map önce çekilir). RR-032-V2 Türk portalları "snapshot ratio" demişti — aslında **tam finansal tablo** var. İş Yatırım MaliTablo'dan aşağı (JSON değil, scrape) ama ikinci kaynak/cross-validation.
3. **stockanalysis.com** — 608 BIST hissesi listeli; free tier mktcap+revenue+fiyat; **derin fundamental + geçmiş = Pro (paywall)**. Free yetersiz, Pro ücretli (~$30/ay). İkincil.
4. **doviz.com / canlidoviz.com** (borsapy FX providers) — EVDS USD/TRY'ye ücretsiz alternatif/yedek.
5. **getmidas.com/temettu-takvim** — temettü takvimi (dar kapsam, nice-to-have).

### Lisans disiplini
- borsapy Apache-2.0, borsa-mcp MIT → kanal-URL bilgisi serbestçe kullanılabilir (kod kopyalanmadı; sadece endpoint adresleri öğrenildi — bunlar zaten kamuya açık HTTP endpoint'ler).
- serkankoci61 lisansı LICENSE dosyasında belirsiz → yalnızca kullandığı **kaynak URL'leri** (kamuya açık) not edildi, kodu okunmadı/alınmadı.

---

## BÖLÜM B — Smart Money Veri Kanalları (codebase envanteri)

| Kanal | Durum | Kaynak | Geçmiş derinlik | Kapsama | Faz 1 IC hazır? |
|---|---|---|---|---|---|
| **1. Foreign flow** (yabancı oran) | ✅ Çalışıyor | İş Yatırım screener field 40 (`getScreenerDataNEW`), `isyatirim_scraper.py` | T+1 snapshot + 30g seed (biriken) | ~520 ticker | ✅ **tek hazır kanal** |
| **2. Takas/custody** (MKK saklama) | ⚠️ STUB | Fintables scrape (`fintables_scraper.py`, Playwright+login+CAPTCHA, live doğrulanmamış) | 90g backfill tasarım, min 10g | BIST50 (~49) | ❌ live auth bloke |
| **3. AKD** (aracı kurum dağılımı) | ❌ YOK | Hepsi ücretli (Matriks ₺139/ay, Fintables, VERDA); Python API yok | EOD snapshot, tarihsel lisanslı | ~500 | ❌ ücretli, API yok |
| **4. VIOP** (vadeli) | ⚠️ Veri var, weight=0 | **BIST Datastore CSV** `borsaistanbul.com/data/vadeli/viop_YYYYMMDD.csv` (ücretsiz/public, **2015-12+**, win-1254) | time-series 2015+ | XU030 sınıfı + futures | ⚠️ veri+sinyal hazır, engine wiring yok (DEC-014) |

**Kod referansları:** `smart_money_layer.py` (L5 compute_l5_score: level 50% + change 30% + persistence 20%), `smart_money_connector.py` (IsYatirimScreenerConnector), `viop_fetcher.py` + `viop_layer.py` (`_VIOP_WEIGHT=0`), `thresholds.py` (FOREIGN_FLOW_*, CUSTODY_*, VIOP_*).

**Bölüm A'dan smart money için yeni kaynak?**
- Takas/AKD: İncelenen hiçbir ücretsiz repo takas/AKD'yi ücretsiz çözmüyor (borsapy/borsa-mcp `kap_holdings.py` = KAP major-shareholder, custody/AKD değil). → **AKD/takas ücretli kalıyor** (RR-002 teyidi).
- VIOP: borsapy `viop.py` provider mevcut kanalı (BIST Datastore CSV) doğruluyor — yeni kaynak yok ama wiring referansı var.
- Yeni değil ama önemli: BIST Datastore'da `/data/vadeli/` altında ücretsiz public CSV ekosistemi var — takas/AKD CSV'si YOK (sadece vadeli/viop).

---

## BÖLÜM C — Sentez

### 1. RR-032-V2'ye yeni kanal eklendi mi? → EVET (1 game-changer + 2 ikincil)
- **★★ İş Yatırım MaliTablo** = ücretsiz, programatik (JSON), 2004+ tarihsel, UFRS fundamental. **Faz 0b value için birincil aday** oldu.
- Mynet statements + stockanalysis.com = ikincil/cross-validation.

### 2. Smart money Faz 1 Katman A hazırlık matrisi (her kanal kendi rank-IC testinden geçecek — D-177/178 disiplini)
| Kanal | Veri | Sinyal | IC test edilebilir? | Aksiyon |
|---|---|---|---|---|
| Foreign flow | ✅ | ✅ | ✅ **şimdi** | rank-IC testine al |
| VIOP | ✅ (2015+) | ✅ (weight=0) | ✅ (veri var) | engine-bağımsız IC testi yapılabilir |
| Takas | ❌ | ✅ kod | ❌ | Fintables live auth çöz veya MKK prod |
| AKD | ❌ | ❌ | ❌ | ücretli; ertelenir |

→ **Foreign flow + VIOP** Faz 1 Katman A IC testine HAZIR (ikisi de geçmiş veriye sahip). Takas/AKD bloke.

### 3. Güncellenmiş birleşik veri yolu önerisi (DEC-039: önerir, seçmez)

**Value (Faz 0b):**
1. **★ Birincil: İş Yatırım MaliTablo** (ücretsiz, 2004+, UFRS, itemCode 2O=defter değeri) → USD'ye EVDS dönem-sonu kuruyla çevir (RR-034 altyapısı hazır). **MKK prod token + EODHD ödemesi beklemeye GEREK YOK.**
2. Doğrulama: TMS 29 testi (RR-033) — artık bu ücretsiz geçmiş seriyle koşturulabilir (MKK donuk gateway beklemeden); MaliTablo 2023 özkaynak vs KAP-filed 2023 TMS29 karşılaştır.
3. Yedek: Mynet statements (ikinci kaynak cross-validation), MKK VYK (prod token gelince), EODHD (yalnızca MaliTablo TMS29 testi başarısız olursa).

**Smart money (Faz 0c? — kullanıcı önerisi):**
1. Foreign flow + VIOP → her biri standalone rank-IC (D-177/178 gating).
2. Takas/AKD → veri erişimi çözülene kadar ertele.

**Eleme/erteleme:** EODHD ödemesi (ertele — MaliTablo ücretsiz çözüyor), Matriks IQ Pro (fundamental API yok, RR-032-V2), stockanalysis Pro (MaliTablo varken gereksiz), AKD ücretli kanallar (Faz 1+ sonrası).

---

## Kısıtlar
- Probe'lar tek oturum (30 May 2026), throwaway (silindi). MaliTablo canlı GET ile teyit (HTTP 200, 147 satır, 4 dönem) — gerçek kanıt raporda.
- İş Yatırım MaliTablo / Mynet / screener fundamental'lerinin **TMS 29-adjusted mı nominal mi** sorusu hâlâ RR-033'e bağlı (MaliTablo `XI_29` UFRS grubu ama enflasyon-düzeltme satır-bazı doğrulanmalı).
- ToS: `/_layouts/` İş Yatırım endpoint'leri robots-disallowed (RR-005 sınıfı, gri ToS — kişisel/araştırma kullanım); MaliTablo public JSON ama resmi API değil.
- borsapy/borsa-mcp kodu **kopyalanmadı**; yalnızca kullandıkları kamuya-açık endpoint adresleri öğrenildi + kendi isteğimizle teyit edildi.
- Build/production değişiklik YOK. `src/` dokunulmadı.
