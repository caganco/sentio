# RR-037 — Smart Money Veri-Erisim + Kalite Dogrulama (Faz 0c On-kosulu)

**Tarih:** 30 Mayis 2026
**Yazar:** Claude Code (Builder) — canli probe + kod-okuma
**Status:** 4-kanal IC-hazirlik matrisi tamamlandi. Faz 0c baslatma onerileri net.
**Bagli:** RR-032-V3 §B (smart money kanallari); RR-001 (Fintables takas); RR-002 (AKD);
RR-020 (BIST veri haritasi); DEC-014 (VIOP weight=0 karari).

---

## TL;DR

| Kanal | Canli | Hisse-bazli | Gecmis derinlik | IC-hazir? | Ucret |
|---|---|---|---|---|---|
| **Foreign flow** (screener f40) | Kod evet, DB YOK | Evet (~520 ticker) | **SIFIR** (hic calistirilmamis) | **HAYIR** — ~12ay birikim lazim | Ucretsiz |
| **VIOP** (BIST Datastore CSV) | **Evet** | **Evet** (SSF per-ticker) | **2018+** (8 yil) | **EVET** (kucuk kod duzeltmesi ile) | Ucretsiz |
| **Takas** (Fintables) | STUB | Evet (tasarimda) | Tanimlanmamis | **HAYIR** — auth bloke | L79/ay + gelistirme |
| **AKD** | Yok | Evet (teorik) | Teorik | **HAYIR** | L139+/ay + API yok |

**Faz 0c onceligi:**
1. **VIOP** — data 2018+, hisse-bazli, ucretsiz; viop_fetcher.py SSF-parse duzeltmesi (~1-2 gun is).
2. **Foreign flow** — gunluk koleksiyonu SIMDI baslatilmali (12ay sonra IC'ye girer, ~Haz 2027).
3. **Takas/AKD** — yakin vadede ertele.

---

## §1 On-Okuma Bulgulari — Eski RR'lerde Yeni Kanal Var mi?

Adim 0 geregi RR-001/002/020 okundu. Ozet:

- **RR-001 (Fintables takas):** "Is Yatirim Gunluk Yabanci Oranlari JSON endpoint" ile "cok yillik gecmis" iddiasi var.
  Probe ile test edildi: **Bu iddia YANLIS** — HisseTekil endpoint fiyat/hacim/PD getiriyor (yabanci oran YOK).
  30 alan dogrulandi: HGDG_KAPANIS, HGDG_HACIM, PD, PD_USD, HAO_PD... Hicbiri yabanci_oran/YABANCI degil.
- **RR-002 (AKD):** BIST Duezey 2+ lisansi, MKK Pusula (kurum uyeleri), ForInvest, Matriks —
  hepsi ucretli/kapali. Ucretsiz programatik AKD yolu YOLAYIN yok.
- **RR-020 (veri haritasi):** BIST Datastore 3153 "Yabanci Islemler" (2015+ akademik, CSV, ucretsiz) —
  AKIS verisi (transaction-based), saklama pozisyon seviyesi degil. Cross-sectional IC icin
  kullanilabilir ama screener field 40'tan farkli bir metrik olur; ayri probe gerekir.
- **Sonuc (adim 0):** Foreign flow sifir-gecmis sorununu cozen ucretsiz kanal BULUNAMADI.
  Datastore 3153 potansiyel alternatif ancak henuz test edilmedi (kapsam disi bu rapordan).

---

## §2 Kanal 1 — Foreign Flow (Yabanci Akis / Sahiplik Orani)

### 2.1 Kod Durumu

`src/data/isyatirim_scraper.py` — `ForeignFlowConnector`:
- Endpoint: `IsYatirimScreenerConnector.fetch_all_tickers()` → `getScreenerDataNEW` field 40
- Donen deger: `yabanci_toplam_pct` (yuzde, stok-pozisyon seviyesi)
- DB yazici: `ForeignFlowDBWriter` → `isyatirim.db::foreign_flow_summary(date, ticker, yabanci_toplam_pct, scraped_at)`
- "30g seed": ilk calistirmada yapay 30-gunluk gecmis entry olusturuluyor (gercek tarihsel veri degil)

### 2.2 Canli Test Sonucu

**`isyatirim.db` YOK.** ForeignFlowConnector hic calistirilmamis. DB yolu tanimli ama dosya olusturulmamis.

```
DB onceden var mi: False
```

`FOREIGN_FLOW_DB_PATH` konfigurasyon hatasi veya hic tetiklenmemis. Her iki durumda da:
- **Tarihsel veri: SIFIR gercek kayit**
- "30g seed" = sintetik, IC'de kullanamaz

### 2.3 HisseTekil Endpoint — RR-001 Iddiasi Yanlis

RR-001 HisseTekil JSON'inin "yabanci oran gecmisi" sagladigini iddia etmisti. Probe:

```
GET /Data.aspx/HisseTekil?hisse=THYAO&startdate=30-04-2026&enddate=30-05-2026
HTTP 200, 17 kayit
Alanlar: HGDG_KAPANIS, HGDG_HACIM, PD, PD_USD, HAO_PD, DOLAR_BAZLI_FIYAT, ...
```

**Sonuc: Bu endpoint FIYAT/HACIM/PIYASA_DEGERI verisi. Yabanci oran alani yok.**
HAO_PD = Halka Acik Ortaklik Piyasa Degeri (float-adjusted market cap) — yabanci holding degil.
RR-001'deki "yabanci oranlar" iddiasi dogrulanamiyor; endpoint farkli is.

**3 yil gecmis testi de basarili (2023 Q1)** — bu fiyat gecikmisinin derinligi, yabanci oran degil.

### 2.4 Screener Field 40 — Snapshot-Only (RR-034 Teyit)

`getScreenerDataNEW` field 40 (`yabancı_toplam_pct`) date parametresi almaz — her zaman
bugunun snapshot'ini dondurur. RR-034 §3 ile tutarli: **tarihsel seri YAPILAMAZ screener ile**.

### 2.5 IC-Hazirlik Degerlendirmesi

- **Canli test:** DB yok = toplama baslatilmamis.
- **Hisse-bazli:** Evet (~520 ticker screener kapsamasi).
- **Gecmis derinlik:** SIFIR (0 gercek kayit).
- **IC YAPILABILIR MI:** **HAYIR** — ~12ay gunluk biriktirme gerekli.
- **Ne zaman hazir:** ForeignFlowConnector gunluk kosuyor, ~Haziran 2027'den itibaren 12ay panel.
- **Eylem:** Connector'i SIMDI gunluk zamanlamaya bagla (CLAUDE.md scope disinda; bu araştırma).

### 2.6 BIST Datastore 3153 "Yabanci Islemler" (Test Edilmedi)

RR-020'de belgelendi: `borsaistanbul.com/data/yabanci_islemler_YYYYMMDD.csv` (ucretsiz/akademik, 2015+).
Bu AKIS verisi (net alis/satis TL) — sahiplik seviyesinden farkli. Ayri probe ile
IC-kullanilebilir mi test edilebilir. Bu raporun kapsamina alinmadi.

---

## §3 Kanal 2 — VIOP (Vadeli Islem ve Opsiyon Piyasasi)

### 3.1 Canli Test

```
GET https://borsaistanbul.com/data/vadeli/viop_20260526.csv
HTTP 200, 402208 bytes, 2570 satir
Sutunlar: TARIH, SOZLESME KODU, SOZLESME ADI, DAYANAK VARLIK, ACIK POZISYON, ISLEM HACMI...
```

Son is gunu: 2026-05-26 (Pazartesi-Cuma = Cuma). Hafta sonu = 404 (dogru).

### 3.2 Hisse-Bazli Kontratlar (SSF)

CSV ornek:
```
SOZLESME KODU: F_AEFES0626
SOZLESME ADI: AEFES_06/2026_VIS
DAYANAK VARLIK: AEFES.E
SOZLESME TIPI: D_EQ_FPD (equity SSF)
ACIK POZISYON: 176804
```

- Format: `DAYANAK VARLIK = "{TICKER}.E"` (hisse single-stock futures)
- Hisse-bazli: **EVET** — BIST'in likit hisseleri SSF olarak islem gorur
- THYAO/TUPRS/EREGL icin benzer kontratlar beklenebilir (`F_THYAO0626`, `F_TUPRS0626`)
- Probe "THYAO: 0" buldu cunku yanlis sutunu (TARIH) arandı; DAYANAK VARLIK veya SOZLESME ADI'nda arama dogru sonuc verir

### 3.3 Tarihsel Derinlik

| Tarih | HTTP | Boyut | Notlar |
|---|---|---|---|
| 2026-05-26 | 200 | 402KB | Canli, son is gunu |
| 2022-01-04 | 200 | 484KB | 4 yil oncesi |
| 2020-03-20 | 200 | 1MB | COVID krizi donemi, buyuk veri |
| 2018-01-03 | 200 | 642KB | 8 yil oncesi |
| 2016-01-04 | **404** | - | ~10 yil oncesi erisilemlyor |

**Sonuc: ~2018-2026 erisileblir (~8 yil). Faz 0c IC (12-24 ay) icin fazlasiyla yeterli.**

### 3.4 viop_fetcher.py Parser Uyumsuzlugu

`viop_fetcher.py::parse_contract_symbol()` regex: `^([A-Z0-9]{3,7})[EF](\d{4})([CP]?)(.*)$`
Bu opsiyon formatini hedefler: `THYAO0626C` (call) / `THYAO0626P` (put).

Ancak gercek VIOP CSV kontrat kodlari: `F_AEFES0626` (futures, F_ prefix).
Regex eslesmiyor → `compute_ticker_oi()` None doner → `len(None)` → TypeError.

**Gerekli duzeltme:** Parser'i SSF kodu formatina (`F_{TICKER}{YYYYMM}`) uyarla + ACIK POZISYON
sutununu "long SSF open interest" olarak kullan. IC sinyali: ticker OI degisimi (oi_delta),
normalize OI seviyesi. Put/call ratio VIOP icin gecerli degil (SSF); yerine net-OI veya OI-change.

**Duzeltme buyuklugu:** ~1-2 gun gelistirme (viop_fetcher.py + viop_layer.py reformulasyonu).

### 3.5 Engine Baglantisi

`MASTER_WEIGHTS.get("viop") = YOK` — thresholds.py'de VIOP agirligi tanimli degil.
`viop_layer.py::_VIOP_WEIGHT = 0` (DEC-014 karari: veri hazir degil, 0 beklet).

DEC-014 durumu: veri artik hazir (2018+ CSV, hisse-bazli) — parser duzeltildikten sonra
DEC-014 gozden gecirilmesi gundemde olabilir. Karar O+C.

### 3.6 IC-Hazirlik Degerlendirmesi

- **Canli test:** HTTP 200, veri tam.
- **Hisse-bazli:** EVET (SSF per-ticker, DAYANAK VARLIK = "{TICKER}.E").
- **Gecmis derinlik:** 2018-2026 (~8 yil). IC icin fazlasiyla yeterli.
- **IC YAPILABILIR MI:** **EVET** — kucuk parser duzeltmesi sonrasi.
- **Eylem:** viop_fetcher.py'de SSF-parse fix (~1-2 gun), sonra Faz 0c rank-IC denemesi.

---

## §4 Kanal 3 — Takas/Custody (Fintables)

### 4.1 Kod Durumu

`src/data/fintables_scraper.py` (656 satir) — STUB:
- Playwright + Fintables login (`FINTABLES_EMAIL` + `FINTABLES_PASSWORD` env vars)
- HTML selector'lar `# VERIFY AGAINST LIVE SITE` isaretli (hicbiri canli dogrulanmamis)
- `page.wait_for_selector(TABLE_SELECTOR)` — TABLE_SELECTOR dogrulanmamis → muhtemelen fail

### 4.2 L79/ay Fintables Abone Deger Analizi

Fintables aboneligi (L79/ay temel) NE saglar?
- **Web arayuzu:** Hisse baz takas analizi (kurum satir tablosu: lot, %, delta weekly/monthly/quarterly)
- **Programatik API:** Kanit yok. Web-only; rate-limiting + CAPTCHA + Playwright gerekir.
- **Eklentiler:** Playwright stub calistirmak icin: login test, selector dogrulama, CAPTCHA cozum (manuel veya 3. taraf)
- **Toplam maliyet:** L79/ay + gelistirme ~3-5 gun (selector dogrulama, CAPTCHA, test)

**Sonuc:** L79/ay + gelistirme maliyeti, IC sinyali (takas > foreign > VIOP mihinde BIST literaturunde zayif) ile orantisiz. Kisa vadede ertele.

### 4.3 Ucretsiz Takas Alternatifi

- **MKK Pusula:** Sadece aracu kurum uyeleri — erisim yok.
- **Takasbank saklama istatistikleri (halka acik PDF):** Aylik toplam (aggregate), hisse-bazli degil.
- **borsapy/borsa-mcp:** Takas kanalini cozmuyor (RR-032-V3 §A teyit).
- **Sonuc:** Ucretsiz programatik takas yolu BULUNAMADI (RR-032-V3 teyit).

### 4.4 IC-Hazirlik

- **Canli test:** STUB (canli test yapilmadi, gerekmez).
- **IC YAPILABILIR MI:** **HAYIR** — auth bloke + ucret + gelistirme.
- **Eylem:** Ertele. Gelecekte: BIST Datastore'da takas alternatif araştır.

---

## §5 Kanal 4 — AKD (Aracu Kurum Dagilimi)

- **Ucretsiz Python API:** YOK (RR-002 + RR-020 teyit).
- **Maliyet tablosu:** Matriks IQ L139/ay (sadece AKD modulu), Fintables Pro L149/ay + BIST AKD lisansi L173/ay, ForInvest Pro L549-2799/ay, VERDA API kurumsal.
- **IC potansiyeli:** Teorik olarak guclu (broker-level accumulation/distribution) ama BIST literaturunde reel IC kaniti sinirli.
- **Eylem:** Ertele (ucret + API yok + IC kaniti yok).

---

## §6 Faz 0c Hazirlik Matrisi — Net Karar Tablosu

| Kanal | Canli | Hisse-bazli | Gecmis | IC-Hazir | Engel | Maliyet | Oneri |
|---|---|---|---|---|---|---|---|
| Foreign flow (f40) | Kod evet, DB YOK | Evet | SIFIR | **HAYIR** | DB hic calistirilmamis | Ucretsiz | Gunluk koleksiyon SIMDI baslatilmali; 12ay sonra IC |
| VIOP SSF | **Evet** | **Evet** | **2018+** | **EVET** | viop_fetcher SSF-parse duzeltme lazim | Ucretsiz | Faz 0c **birincil kanal** — parser fix sonrasi |
| Takas | STUB | Tasarimda | Belirsiz | **HAYIR** | Playwright+login+CAPTCHA | L79/ay+dev | Ertele |
| AKD | Yok | Teorik | Yok | **HAYIR** | API yok, ucretli | L139+/ay | Ertele |

---

## §7 Oneri (DEC-039: onerir, secmez — karar Orchestrator + Cagan)

### Faz 0c Baslangic: VIOP Onceligi

1. **viop_fetcher.py SSF-parse fix (~1-2 gun):**
   - `parse_contract_symbol()` regex'ini `F_{TICKER}{YYYYMM}` formatina uyarla
   - `compute_ticker_oi()` yerine ACIK POZISYON toplamini kullan (net long OI)
   - IC sinyali: normalized OI ve OI-delta (put/call ratio yerine)
   - `_VIOP_WEIGHT` kararini DEC-014 uzerinden O+C gundeme al

2. **Foreign flow gunluk koleksiyon (~yarim gun):**
   - `ForeignFlowConnector` veya dogrudan screener cagrisi gunluk zamanlama ile baslat
   - Hedef: ~12ay panel → ~Haz 2027 IC deneyi
   - isyatirim.db hedef yolu kontrol edilmeli (`FOREIGN_FLOW_DB_PATH`)

3. **Takas/AKD:** Yakin vadede ertele.

### Cagan Maliyet Karari: L79/ay Takas?

"Gereksever odeyiz" icin degerlendir:
- L79/ay Fintables = web arayuzu (programatik kanit yok) + Playwright gelistirme ~3-5 gun
- Takas IC litaraturde foreign flow'dan daha dusuk alfa (BIST ozgul veri yok)
- VIOP ucretsiz + daha guvenilir = daha iyi alternatif
- **Oneri: L79 harcama VIOP canli olduktan sonrasi icin geri durun.** VIOP IC net pozitif cikmazsa takas gundeme alinabilir.

---

## §8 Kisitlar

- Probe tek oturum, throwaway (silindi). Canli HTTP GET kaniti yukarida.
- `src/` dokunulmadi; build YOK.
- ForeignFlowConnector import hatasi (ModuleNotFoundError cache_store) → import yolu hatasi
  veya ortam farki; IC-hazirlik degerlendirilmesi etkilenmiyor (DB yoklugu daha buyuk sorun).
- VIOP ticker-arama probe yanlis sutun aldi (TARIH), ama ornek kayitlar SSF varligini gosteriyor.
- BIST Datastore 3153 (yabanci islemler flow) test edilmedi — ayri probe ile degerlendirilebilir.

**Kaynaklar:** Canli HTTP probe (2026-05-30); RR-001/002/020/032-V3 on-okuma;
`src/data/isyatirim_scraper.py`, `viop_fetcher.py`, `fintables_scraper.py` kod okuma;
DEC-014 (VIOP weight=0 karari).
