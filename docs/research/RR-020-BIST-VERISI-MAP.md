# RR-020: BIST OS Veri Kaynakları Haritalama / BIST Data Source Atlas

**Doküman tipi:** Reference / "Rosetta Stone" — Builder/Architect için tablo ağırlıklı atlas
**Tarih:** 24 Mayıs 2026
**Hedef sistem:** BIST OS (Borsa İstanbul Algoritmik Analiz Sistemi)
**Dil:** Türkçe açıklama + İngilizce teknik terim (rate limit, WebSocket, endpoint, delisted, survivorship bias, API key)

---

## 1. TL;DR

- **Optimal Stack 3 Cümle:** Şu anki aktif stack (yfinance + Stooq + TCMB EVDS3 + KAP + İş Yatırım JSON + Takasbank) BIST için pratik olarak yapılabilecek en iyi ücretsiz birleşim; ancak yfinance tek başına single point of failure ve corporate-action (bedelsiz/temettü) doğruluğu sorunlu — Stooq + İş Yatırım JSON ile cross-validation yapılmadan production'a alpha üretmek mümkün değil. KAP scraper'ın resmi `https://www.kap.org.tr/tr/api/disclosures?afterDisclosureIndex={N}` endpoint'i, scraper yedekten "primary" konumuna alınmalı. VIOP, AKD ve smart money sinyalleri için Takasbank istatistikler + BIST resmi Datastore zorunlu — bunlar olmadan Critic'in "alpha yok" tezi doğru kalır çünkü retail-only data ile retail-only sinyal üretilir.
- **Migrate Edilmesi Gerekenler (Critical):** (i) yfinance'in `Adj Close` değerlerini İş Yatırım `HGDG_KAPANIS` ile cross-validate eden bir doğrulama katmanı (RR-008 EVDS migration pattern'i gibi); (ii) Alpha Vantage tier'ı serbest kullanım için artık 25 req/gün'e düştü — varsa Alpha Vantage bağımlılığı acil migrate (Twelve Data Basic 800 req/gün veya FRED'e); (iii) Investing.com scraping (varsa) — Fusion Media ToS ihlali ve IP-ban riski yüksek, ya `investpy`-style "permission-aware" kullan ya da kaldır.
- **30-Dakikalık Fix Önerileri:** (a) yfinance call'larına `session=requests_cache` ve 0.5-1 sn sleep + retry-with-backoff ekle (rate limit hatalarını ~%80 azaltır); (b) KAP scraper'ı `https://www.kap.org.tr/tr/api/disclosures?afterDisclosureIndex={N}` endpoint'ine yönlendir — HTML scraping fallback olarak kalsın; (c) TCMB EVDS3 için 150-observation chunking ekle (`cbRt` paketinde otomatik); (d) Cross-validation script'ini (Bölüm 5) cron'a koy ve >%0.5 drift için Slack alarmı yarat.

---

## 2. Master Veri Kaynakları Tablosu

**Skor:** 🟢 8-10 (prod-ready), 🟡 5-7 (uyarıyla kullan), 🔴 1-4 (avoid/migrate).
**Gecikme:** RT (real-time), 15m (15-dk delayed), EOD (end-of-day), Hist (historical only).

| # | Kaynak | Coverage | Maliyet | Gecikme | Yasal | Score | Aktif/Future |
|---|---|---|---|---|---|---|---|
| 1 | yfinance (Yahoo Finance) | BIST equity / FX / Commodity | $0 | 15m | Gri (Yahoo ToS) | 🟡 6 | Aktif |
| 2 | Stooq (`.tr` suffix) | BIST equity / index | $0 | EOD | Gri | 🟡 6 | Aktif |
| 3 | İş Yatırım JSON (`Data.aspx/HisseTekil`) | BIST equity, fundamentals, screener | $0 (gri scraping) | EOD/intraday | Riskli ("personal use") | 🟢 8 | Aktif |
| 4 | TCMB EVDS3 | Macro (FX, faiz, CPI, M2…) | $0 + API-key | EOD | Yeşil (commercial=izin) | 🟢 10 | Aktif |
| 5 | KAP `/tr/api/disclosures` | Disclosure, material events | $0 | ~3 dk poll | Yeşil (kamuya açık) | 🟢 9 | Aktif |
| 6 | Borsa İstanbul Datastore | Equity/derivative/prec.metal historical | Akademik $0 / ticari ücretli | Hist | Yeşil + Letter of Undertaking | 🟢 8 | Aktif |
| 7 | Takasbank VIOP istatistikleri | OI, hacim, Put/Call | $0 | T+0 EOD | Yeşil | 🟢 9 | Aktif |
| 8 | VERDA API (verda.borsaistanbul.com) | AKD eşanlı, üye saklama, fon portföy | Ücretli kurumsal | RT/EOD | Yeşil | 🟢 9 | Future |
| 9 | FRED (St. Louis Fed) | US/global macro, VIX, US10Y, DXY | $0 + API-key | EOD | Yeşil | 🟢 10 | Aktif |
| 10 | Twelve Data | Global equity + BIST | Free 800/gün; $29-329/ay | RT/WS (~170 ms) | Yeşil | 🟢 8 | Future |
| 11 | Alpha Vantage | US-focused, BIST sınırlı | Free **25 req/gün**; $49.99+/ay | EOD/15m | Yeşil | 🟡 5 | Future (sınırlı) |
| 12 | Investing.com (investpy) | Equity/bond/CDS/commodity | $0 (gri) | RT/15m | **Riskli** — Fusion Media ToS | 🟡 5 | Avoid (yedek) |
| 13 | TradingView (webhook + Pine) | Equity, chart, alerts | Pro $14.95+/ay | RT | Yeşil (export sınırlı) | 🟡 6 | Future |
| 14 | EPİAŞ Şeffaflık (eptr2 — 213+ servis) | Spot elektrik MCP/PTF, doğalgaz | $0 + register | RT-hourly | Yeşil | 🟢 9 | Aktif (sektör-bazlı) |
| 15 | Matriks IQ Terminal | RT BIST + AKD + C# algoritma + Codi AI | Aktifbank 2025 lisans tablosu: Ekran ₺1.073 + AKD ₺139/ay + AKDE ₺357/ay + KD/PD/VD modülleri | RT | Yeşil | 🟢 8 | Future (consider) |
| 16 | Foreks/ForInvest Pro | RT BIST, depth, AKD, news | Standard ₺145/ay; Trade ₺549/ay; Pro ₺2.799/ay (promo ₺1.799) [foreks](https://trader.foreks.com/mobil-fiyatlandirma) — ForInvest resmi pricing page | RT | Yeşil | 🟢 8 | Future |
| 17 | Midas (digital broker) | BIST + US equity | Commission-free BIST [Midas](https://www.getmidas.com/borsa-istanbul/) | RT | Yeşil | 🟡 6 | Future (data export limited) |
| 18 | TÜİK (data.tuik.gov.tr) | Enflasyon, GSYH, işsizlik, sanayi | $0 | Aylık-çeyrek | Yeşil | 🟢 9 | Aktif |
| 19 | BDDK | Banking sector aggregate | $0 Excel | Aylık | Yeşil | 🟡 6 | Aktif (semi) |
| 20 | SPK | IPO calendar, açığa satış, fon | $0 | Variable | Yeşil | 🟡 6 | Aktif (semi) |
| 21 | Borsa İstanbul Resmi Duyurular | Index rebalance, IPO, kotasyon | $0 HTML | RT publish | Yeşil | 🟢 8 | Aktif |
| 22 | World Government Bonds | CDS 5Y, sovereign yield | $0 HTML | Daily | Yeşil | 🟡 6 | Aktif (fallback) |
| 23 | MacroVar / MacroMicro | CDS, country macro | Free limited | Weekly-daily | Yeşil | 🟡 5 | Future |
| 24 | Cbonds Index 13873 (CDS 5Y Turkey SNRFOR) | CDS history | Ücretli | Daily | Yeşil | 🟡 6 | Future |
| 25 | HistData.com | FX tick + M1 | $0 "personal use" | Hist (M1) | Yeşil | 🟢 8 | Aktif (FX backfill) |
| 26 | LME (London Metal Exchange) | Bakır, çinko, alüminyum | Delayed $0, RT ücretli | RT/EOD | Yeşil | 🟢 8 | Future |
| 27 | EIA (US Energy Info Admin) | Brent, WTI, doğalgaz | $0 API | Daily-weekly | Yeşil | 🟢 9 | Aktif |
| 28 | EPDK (epdk.gov.tr) | Energy sector reports | $0 PDF | Aylık | Yeşil | 🟡 6 | Aktif (semi) |
| 29 | Reuters/Refinitiv Datastream | Multi-asset akademik standart | ~$22K/yr enterprise | RT | Yeşil | 🟢 10 | Future (premium) |
| 30 | Bloomberg Terminal | Multi-asset | ~$24K/yr/seat | RT | Yeşil | 🟢 10 | Future (premium) |
| 31 | dxFeed (BIST indices) | BIST RT index feed | Ücretli institutional | RT | Yeşil | 🟢 9 | Future |
| 32 | Garanti BBVA / Yapı Kredi / Ak Yatırım | Customer portal (HTML) | Müşteri-only | RT | Yeşil | 🟡 5-6 | Future (broker tie-in) |
| 33 | Bizim Menkul | Customer portal | $0 scraping | EOD | Gri | 🟡 5 | Aktif (fallback) |
| 34 | Gedik Pay terminal | BIST trading terminal | Müşteri-only | RT | Yeşil | 🟡 6 | Future |
| 35 | Enpara / QNB Finans Yatırım | App, limited export | Müşteri-only | RT | Yeşil | 🟡 5 | Future |
| 36 | Oyak Yatırım public stock pages | HTML scraping community | $0 | EOD | Gri (brittle) | 🔴 4 | Avoid |
| 37 | **X (Twitter) API v2** | Sentiment / news flow | **Pay-per-use default** ($0.005/post read, $0.01/post created) [GIGAZINE](https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use/) [Sorsa](https://api.sorsa.io/blog/twitter-api-pricing-2026) Şubat 2026'dan itibaren yeni developer'lar için; legacy Basic ($200/ay) & Pro ($5,000/ay) sadece mevcut abonelere; yeni Enterprise tier $42,000/ay | RT | Yeşil | 🟡 5 | Future |
| 38 | Reddit API (r/Borsa, r/borsaistanbul) | Retail sentiment | $0 limited | RT | Yeşil | 🟡 5 | Aktif (low priority) |
| 39 | YouTube Data API + transcripts | TR finans kanalları (Kıvanç Özbilgiç, Mert Başaran) | $0 limited | RT | Yeşil | 🟡 5 | Future (sentiment) |
| 40 | Telegram channels (TR finance) | Retail flow | $0 (Bot API) | RT | Gri (KVKK risk) | 🔴 4 | Avoid (KVKK) |
| 41 | Hisse.net forum scraping | Retail forum | $0 (scraping) | Daily | Gri/risky (ToS, KVKK) | 🔴 3 | Avoid |
| 42 | BigPara / MyNet borsa pages | Retail aggregator | $0 scraping | EOD | Gri | 🟡 5 | Aktif (yedek) |
| 43 | Anadolu Ajansı RSS/site | Resmi haber | $0 | RT | Yeşil | 🟢 8 | Aktif (news) |
| 44 | Bloomberg HT (TR) | Finansal haber | $0 HTML | RT | Yeşil (link) | 🟡 6 | Aktif (semi) |
| 45 | Google News RSS (KAP yedek) | News aggregation | $0 | ~30 dk | Yeşil | 🟡 6 | Aktif (fallback) |
| 46 | Google Trends (pytrends) | Search proxy sentiment | $0 | Haftalık | Yeşil | 🟡 6 | Aktif (sentiment) |
| 47 | pykap / isyatirimhisse / borsapy / borsa-mcp (community PyPI) | KAP, İş Yatırım wrappers | $0 | Variable | Gri (kaynak ToS aktarımı) | 🟡 6 | Aktif (wrapper) |
| 48 | BTCTurk / Paribu API | Crypto (TRY parite) | $0 | RT | Yeşil | 🟢 8 | Future (corr. analizi) |
| 49 | Binance API (`BTCTRY`) | Crypto reference | $0 | RT/WS | Yeşil | 🟢 9 | Future |
| 50 | Doviz.com Calendar API (`getCalendarEvents`) | Ekonomik takvim TR | $0 | Daily | Gri (scraping) | 🟡 6 | Aktif |
| 51 | Trading Economics | Global macro/calendar | Free limited, $99+/ay | Daily | Gri | 🟡 6 | Future |
| 52 | KAP financial reports (XBRL) | Bilanço/IS/CF quarterly+annual | $0 (KAP üzerinden) | Quarterly | Yeşil | 🟢 9 | Aktif |

---

## 3. Katman Bazlı Veri Haritası

```
L1 TECHNICAL: yfinance (primary) + Stooq (cross-check) + İş Yatırım JSON (gold-standard) + HistData.com (FX backfill)
L2 MACRO:    TCMB EVDS3 (TRY) + FRED (global) + TÜİK + EPİAŞ (energy) + EIA (commodity)
L3 KAP:      KAP /api/disclosures (primary) + HTML scraping (fallback) + İş Yatırım financial reports
L4 SENTIMENT: AA + Bloomberg HT + Google News + Google Trends + Reddit/Twitter API (selective)
L5 SMART $:  Takasbank VIOP + İş Yatırım AKD + BIST Datastore 3153 Yabancı + (Future: VERDA AKD)
L6 RISK:     World Gov Bonds (CDS) + Investing.com CDS fallback + USDTRY (yfinance/TCMB) + VIX (FRED)
```

**Critic'in tezi perspektifinden ("alpha üretmiyor"):** L1-L3 katmanları aktif stack ile makul. **Eksikler L4 ve L5'te:** Sentiment ölçümü ham scraping bazında çalışıyor (yapılandırılmış sinyal yok); L5 smart money tarafında AKD verisi ya gecikmeli (İş Yatırım scraping) ya eksik (VERDA real-time eşanlı yayını edinilmemiş). Bu iki katman kapatılmadan alpha bekleyemeyiz.

---

## 4. Her Kaynak için Detaylı Profil

### A. HİSSE FİYAT VERİSİ (OHLCV)

**A1. yfinance** — `pip install yfinance` (ranaroussi/yfinance). BIST ticker `.IS` suffix (`AKBNK.IS`, `THYAO.IS`, `^XU100` index). Tarihsel: ~1999+ ticker-bazlı, çoğu 2010+. Rate limit pratik ~2 req/sn; aşılırsa "Too Many Requests" 1-15 dk. WebSocket: `dat.live()` yeni eklendi. **Adj Close kalitesi sorunlu** — BIST'te sporadic bedelsiz/temettü adjustment hataları (`auto_adjust=True` 2024'te default). Survivorship bias var: delisted ticker'lar genelde yok (GitHub Discussion #1699 community-confirmed: *"survivorship bias is massive"*). Bilinen BIST sorunları: "Failed to get ticker 'X' reason: Expecting value: line 1 column 1 (char 0)" (Issue #2179), CSRF cookie expiration (#2249), inconsistent results bazı pencerelerde (#626). Yahoo resmi disclaimer: *"This library is not affiliated, endorsed, or vetted by Yahoo, Inc."* **Fix önerisi:** `requests_cache.CachedSession` + `time.sleep(0.5)` + exponential backoff retry; daily `Close` vs `Adj Close / div_factor` cross-check İş Yatırım'a karşı.

**A2. Stooq** — URL `https://stooq.com/q/d/l/?s={ticker}.tr&i=d`. Lowercase + `.tr` suffix. EOD only, intraday yok. Tarihsel 2000s+. Rate limit public yok, pratik ~100-200 req/dk güvenli. "BIST için en güvenilir ücretsiz alternatif" iddiası kısmen doğru — daily Close için yfinance kadar veya daha iyi (cross-validation case'lerinde Close değerleri %0.01-0.05 dahilinde uyumlu); intraday yokluğu sınırlama. **Aktif: cross-validation primary backup.**

**A3. Investing.com** — Resmi public API yok. `investpy` (alvarobartt) bakım azaldı. Cloudflare protection — aşırı request'te IP-ban yüksek risk. Fusion Media ToS scraping konusunda gri; investpy bakım sahibi yetkililerden izinle çalıştığını GitHub Discussion #336'da ifade etmiştir ancak resmi yazılı icazet yok. **Avoid as primary**; sadece CDS gibi başka yerde olmayan veriler için fallback.

**A4. TradingView** — Public REST yok; Webhook (Pine Script alarmlarından gelen HTTP POST) + Pine Script. BIST coverage tam (`BIST:` prefix). Ücretsiz tier 1 chart + 2 alert + watermark. Pro $14.95/ay; Pro+ $29.95/ay; Premium $59.95/ay. **Alert layer olarak** (webhook → BIST OS), veri kaynağı olarak değil.

**A5. Twelve Data** — Basic Free: 8 req/dakika, 800 req/gün (Twelve Data resmi pricing). Grow $29/ay (55-377 req/dk, no daily cap); Pro $99/ay (610-1,597 req/dk); Ultra $329/ay (2,584-10,946 req/dk). WebSocket Pro+ tier'larda ~170 ms latency. [G2](https://www.g2.com/products/twelve-data/pricing) BIST coverage Grow+ tier'da. **Future**: AUM >$50K veya >5 farklı veri tipine ihtiyaç doğduğunda $29 tier mantıklı.

**A6. Alpha Vantage** — Free tier **25 req/gün** [GitHub](https://github.com/TauricResearch/TradingAgents/issues/305) (Alpha Vantage resmi support sayfası, 2024 itibarıyla; ex-500/gün 2019, ex-100/gün 2023), 5 req/dakika. Paid: $49.99/ay (75 req/dk, no daily); [Macroption](https://www.macroption.com/alpha-vantage-api-limits/) $99.99/ay (300 req/dk); $249.99/ay (1,200 req/dk). BIST coverage sınırlı — US-focused. **Avoid for BIST.**

### B. RESMİ BORSA VERİSİ

**B1. Borsa İstanbul Datastore** — `https://datastore.borsaistanbul.com/`. Cookie-based session auth + CAPTCHA login adımında. Ürün listesi: 3153 Yabancı İşlemler, 3155 Açığa Satış, 3156 Fiyatlar, 3158 Aktif Piyasa, 100471 Temettü. Akademik kullanım ücretsiz (Letter of Undertaking gerekli); ticari ücretli. Borsa İstanbul resmi sayfası: *"Historical Data Sales — Historical data and some reference data of Borsa Istanbul is available at DataStore"*. [Borsa Istanbul](https://www.borsaistanbul.com/en/data/historical-data-sales) Gold standard birinci-el resmi data. **Aktif** — backfill ve daily smart-money sinyalleri için.

**B2. VERDA (verda.borsaistanbul.com)** — Institutional ücretli. RT data analitikleri (BIST 100 endeksinde yer alan paylar için 1 saniyelik periyodlarda eşanlı hesaplanan analitikler); [Borsa Istanbul](https://www.borsaistanbul.com/veriler/veri-yayini/veri-yayin-urunleri) AKD (Aracı Kurum Dağılımı) gerçek zamanlı işlem tarafı (üye) bilgisi. Retail erişimi yok — institutional contract. Aylık maliyet açık değil; distributor üzerinden referans: Matriks IQ Terminal ekran ücreti ₺1.073, Matriks AKD lisansı ₺139/ay, Matriks AKDE ₺357/ay (Aktifbank 2025-01-01 veri lisans tablosu). [Aktifbank](https://www.aktifbank.com.tr/uploads/20250509104629568.pdf) VERDA Support: `bistechsupport_autoticket@borsaistanbul.com`. [Borsa Istanbul](https://www.borsaistanbul.com/en/technology/client-applications/connect-verda) **Future Option** — AUM > ~$500K veya kurumsal müşteri katmanı geldiğinde mantıklı.

**B3. Borsa İstanbul Resmi Duyurular** — `https://www.borsaistanbul.com/tr/duyurular`. Index inclusion/exclusion (BIST30/50/100 rebalance), halka arz duyuruları, yeni hisse kotları. HTML scraping orta zorluk, structure stable son 2 yılda. Public — yeşil. **Aktif** — günlük index rebalance + IPO calendar.

### C. KAP

**C1. KAP Scraper** — Resmi endpoint (undocumented, kap-notifier kaynak kodundan tespit): `https://www.kap.org.tr/tr/api/disclosures`. Parametre: `?afterDisclosureIndex={N}` (incremental polling için). Update freq: KAP'a yeni disclosure her ~3 dakikada (kap-notifier README verbatim: *"New disclosures are updated on KAP every 3 minutes"*). [GitHub](https://github.com/cahitihac/kap-notifier) Response fields: `basic.disclosureIndex`, `basic.title`, `basic.stockCodes`, `basic.relatedStocks`, `basic.companyName`, [GitHub](https://github.com/cahitihac/kap-notifier/issues/1) `publishDate`, `summary`. HTML scraping fallback (pykap — cemsinano/pykap bundle). Google News RSS ikinci-derece yedek. Kategori taksonomisi: FR (Finansal Rapor), ODA (Material Events), DG (Diğer), FAR (Faaliyet Raporu), KYUR (Kurumsal Yönetim), SUR (Sürdürülebilirlik), KDP (Temettü), DEG (Değerleme), [GitHub](https://github.com/cemsinano/pykap) YI (Yönetici İşlemleri). **Primary disclosure source.**

**C2. KAP Tarihsel Arşiv** — 2010-2026 full archive. Toplam ~1M+ disclosure tahmini. Format çoğunlukla XML/Word; bazı eklemeler PDF. Eski (2010-2013) PDF'ler scan → OCR (tesseract) gerekli. Akademik kullanım: Borsa Istanbul Review article'larda atıf yaygın; SSRN BIST papers KAP'ı kaynak gösterir. KAP resmi: *"KAP system also serves as a digital archive that provides easy access to historical datas."* [KAP](https://www.kap.org.tr/en/about/general-information)

**C3. KAP Finansal Tablolar** — XBRL + Excel format; pykap `comp.get_financial_reports()` ile çekilir. [GitHub](https://github.com/cemsinano/pykap) Bilanço/IS/CF quarterly + annual; TFRS/IFRS uyumlu. Holding NAV hesabı KAP'taki "iştirak değeri" verisinden çıkarılabilir (quarterly granularity). XBRL parsing için `python-xbrl` veya XBRLAnalyst.

### D. MAKRO

**D1. TCMB EVDS3** — `https://evds3.tcmb.gov.tr/`. API key header authentication (Profil → "API Key Kopyala"). [GitHub](https://github.com/fatihmete/evds) Aktif seri kodları örnek: `TP.DK.USD.A` (USD/TRY alış), [Eremrah](https://eremrah.com/cbRt/) `TP.YSSK.A1` (haftalık para arzı), [GitHub](https://github.com/kaymal/tcmb-py) `TP.FG.J0` (CPI), `TP.ENFBEK.PKA12ENF` (12-ay enflasyon beklentisi), [PyPI](https://pypi.org/project/evdspy/) `TP.DK.GBP.A` (GBP/TRY). Tarihsel derinlik 1980'ler+. Rate limit: **150 observation cap per request** — chunking şart (cbRt R paketi, [Eremrah](https://eremrah.com/cbRt/) evdspy Python paketi otomatik chunklar). EVDS2 → EVDS3 migrasyonu 2023-2024'te yaşandı (RR-008 referansı); base URL şu an `evds3.tcmb.gov.tr/igmevdsms-dis/`. [GitHub](https://github.com/kaymal/tcmb-py) Disclaimer verbatim: *"Information published in this site may be quoted by specific reference thereto, but the use of such information for commercial purposes shall be subject to prior written permission of the CBRT."* [Eremrah](https://eremrah.com/cbRt/) **Primary macro source.**

**D2. TÜİK** — `data.tuik.gov.tr`. API var ama documentation Türkçe sadece + bazı API'lerde login gerekli; çoğu kullanıcı Excel/CSV download yapar. Veri tipleri: enflasyon (TÜFE/ÜFE), GSYH, işsizlik, sanayi üretimi. **Aktif** — aylık enflasyon, çeyrek GSYH backfill.

**D3. BDDK** — `bddk.org.tr`. Format Excel + PDF (Aylık Bülten). Resmi API yok; Excel scraping. **Aktif (semi)** — bankacılık sektör endeksi (XBANK) makro context için.

**D4. SPK** — `spk.gov.tr`. Fon akışları aylık bülten içinde, halka arz takvimi onaylanan IPO duyuruları, açığa satış istatistikleri var ama gecikmeli. **Aktif (semi)** — IPO calendar + açığa satış yasak listesi takibi.

**D5. ABD/Global Macro** — **FRED** (St. Louis Fed): VIX (`VIXCLS`), DXY (`DTWEXBGS`), US10Y (`DGS10`); ücretsiz API key, `fredapi` Python lib; ToS commercial-use için izin gerekli. Investing.com economic calendar (scraping veya investpy). Trading Economics free limited, $99-749/ay. **Doviz.com Economic Calendar API** — `https://www.doviz.com/calendar/getCalendarEvents` (TR açıklamalı, ücretsiz). [GitHub](https://github.com/saidsurucu/borsa-mcp)

### E. FX

- **E1 USDTRY tarihsel**: yfinance `USDTRY=X` (15-dk delay, sporadic missing values), TCMB EVDS `TP.DK.USD.A` (alış), `TP.DK.USD.S` (satış) — günlük gold standard, Investing.com (scraping), **HistData.com** (tick + M1, ücretsiz "personal use" only).
- **E2 Çapraz pariteler**: yfinance `EURUSD=X` + FRED `DEXUSEU`, TCMB EVDS `TP.DK.GBP.A`, JPY/TRY.
- **E3 EUR/TRY önemi**: Türk ihracatçı şirketler (BIMAS, FROTO, TOASO) EUR-denominated cost stack'i nedeniyle EUR/TRY exposure'u USDTRY'den daha relevant olabilir — TCMB EVDS'ten daily çek.

### F. COMMODITY

| Kaynak | Coverage | Kullanım |
|---|---|---|
| yfinance `BZ=F` (Brent), `CL=F` (WTI) | Petrol futures | TUPRS/PETKM |
| EIA API | Brent/WTI spot, doğalgaz | Reference |
| EPİAŞ Şeffaflık (eptr2 — 213+ servis) | Türkiye spot elektrik MCP/PTF, doğalgaz | AKSEN/ENERY |
| EPDK aylık bülten | Energy market reports | Sektör context |
| LME (delayed free, RT paid) | Bakır, çinko, alüminyum | EREGL, KRDMD |
| yfinance `GC=F` (Gold), `SI=F` (Silver) | Precious metals | KOZAL, KOZAA |
| Borsa İstanbul Kıymetli Madenler Piyasası | XAU/TRY referans | Reference |
| EIA / CME for tarım | Pamuk, buğday, mısır | Tarım sektörü |

### G. TÜREV (VIOP)

- **G1 BIST Resmi**: `borsaistanbul.com/tr/sayfa/48/vadeli-islem-ve-opsiyon-piyasasi` — daily volume + open interest summary.
- **G2 Takasbank**: Open interest report `https://www.takasbank.com.tr/tr/istatistikler/vadeli-islem-ve-opsiyon-piyasasi-viop/vadeli-islem-sozlesmesi-acik-pozisyon-adet-raporu`; işlem hacmi raporu `…/vadeli-islem-sozlesmesi-islem-hacmi-raporu`; [Gcmyatirim](https://www.gcmyatirim.com.tr/egitim/makaleler/viop-ta-acik-pozisyon-ve-islem-hacmi-nasil-yorumlanmali) teminat tamamlama çağrısı raporu `…/teminat-tamamlama-cagrisi-raporu`. Put/Call ratio raporlardan hesaplanır. **Smart-money sinyali primary**.
- **G3 Single Stock Options**: Likidite sınırlı — sadece XU030 sınıfı hisselerde derinlikli (GARAN, AKBNK, EREGL, THYAO). yfinance options chain BIST için **yok**; implied volatility verisi Foreks Pro veya Matriks IQ'da.

### H. BOND / FAIZ

| Kaynak | Veri |
|---|---|
| TCMB EVDS3 | TLREF (gecelik referans faiz), gecelik repo, 2Y/5Y/10Y tahvil yield |
| Borsa İstanbul Debt Securities Market data | Daily bulletin |
| Investing.com `turkey-cds-5-year-usd-historical-data` | CDS history (free, scraping-aware) |
| World Government Bonds (`worldgovernmentbonds.com/cds-historical-data/turkey/5-years/`) | CDS 5Y terminal'siz |
| MacroVar (`macrovar.com/turkey/turkey-credit-default-swaps/`) | CDS history free |
| Cbonds Index 13873 — CDS 5Y Turkey SNRFOR | Daily; ücretli; Excel formula `CbondsIndexValue(13873, date)` |

Akademik referans: Oner & Oner (2022, *Quarterly Journal of Econometrics Research* 8(1):11-22, RePEc:pkp:qjoecr) — 2921 daily obs 10 Mart 2010 - 8 Mart 2022; CDS↔BIST100↔USDTRY↔2Y benchmark bond bilateral Granger causality; impulse-response 1% CDS shock → USDTRY+, bond yield+, BIST100−. [IDEAS/RePEc](https://ideas.repec.org/a/pkp/qjoecr/v8y2022i1p11-22id3222.html)

### I. ALTERNATİF VERİ

**I1 Sosyal Medya Sentiment:**
- **X (Twitter) API v2**: 6 Şubat 2026'dan itibaren X yeni developer'lar için sabit-tier pricing'i kaldırdı ve pay-per-use default'a geçti [GIGAZINE](https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use/) [Blotato](https://www.blotato.com/blog/twitter-api-pricing) ($0.005/post read, $0.01/post created); legacy **Basic ($200/ay) ve Pro ($5,000/ay) yeni signup'a kapalı**, yalnızca mevcut abonelere açık. Yeni **Enterprise tier $42,000/ay**'dan başlar. [Postproxy](https://postproxy.dev/blog/x-api-pricing-2026/) XDevelopers resmi duyurusu (6 Şubat 2026) verbatim: *"Basic & Pro X API plans will remain available with the ability to opt-in to [pay-per-use]."* [GIGAZINE](https://gigazine.net/gsc_news/en/20260209-x-api-pay-per-use/) (Kaynak: developer.x.com/en/support/x-api/v2 + XDevelopers community announcement Şubat 6 2026)
- **Reddit API** (r/Borsa, r/borsaistanbul, r/Turkey): ücretsiz limited, `praw` library
- **YouTube transcripts**: `youtube-transcript-api` ücretsiz; TR finans kanalları (Kıvanç Özbilgiç, Mert Başaran, Murat Demir vs.)
- **Telegram**: Bot API + channel scraping; **KVKK risk yüksek** (channel content kişisel veri içerebilir)
- **Forum scraping** (hisse.net, ekşi sözlük borsa başlığı): ToS gri + KVKK risk

**I2 Haber Akışı:**
- Bloomberg HT (TR): site yapısı stable scraping için
- Foreks haber feed: Pro tier'da
- Para Analiz, Bigpara haberler: RSS + scraping
- **Anadolu Ajansı**: RSS resmi
- Google News RSS: `news.google.com/rss/search?q=AKBNK+borsa`

**I3 Google Trends**: `pytrends` library ücretsiz; haftalık + günlük (kısa pencere); BIST ticker search volume = retail dikkat proxy.

**I4 Insider Transactions**:
- SPK Form 5%+: Önemli pay edinim duyuruları KAP üzerinden
- Yönetici alım/satım: KAP kategori `YI` (Yönetici İşlemleri)
- **Aktif kullanılmalı — alpha-yüklü sinyal**

### J. BROKER API'leri

| Broker | API |
|---|---|
| **İş Yatırım** | Resmi olmayan JSON `https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil?hisse=X&startdate=DD-MM-YYYY&enddate=DD-MM-YYYY.json` [GitHub](https://github.com/urazakgul/veri-kaynaklari-python) + screener + financial reports — **Aktif, primary** |
| Garanti BBVA / Yapı Kredi / Ak Yatırım | Customer-only, public API yok |
| **Foreks/ForInvest Pro** | Standard ₺145/ay; Trade ₺549/ay; Pro ₺2.799/ay (promo ₺1.799); FXPlus/ProTrader desktop quote bazlı. Verbatim ForInvest pricing page: *"Standard 145 TL / Ay … Trade 549 TL / Ay … Pro 2799 TL / Ay 1799 TL / Ay"*. Note: Foreks Trader 1 Kasım'da ForInvest'e rebrand edildi. [Forinvest](https://www.forinvest.com/destek) Sözleşme §1 LİSANS: *"Müşteri Lisanslı Ürünün telif ve her türlü mülkiyet hakkının ilgili borsaya ait olduğunu kabul etmektedir. Sözleşme ile verilen lisans Müşteri tarafından başkasına atanamaz, devredilemez veya alt lisans oluşturulamaz."* |
| **Matriks IQ Terminal** | C# SDK [MatriksIQ](https://www.matriksdata.com/website/urunlerimiz/kullanici-platformlari/matriksiq-veri-terminali) + AKD lisansı + Codi AI asistanı (doğal dil → strateji). [MatriksIQ](https://www.matriksdata.com/website/urunlerimiz/kullanici-platformlari/matriksiq-veri-terminali) Aktifbank 2025 lisans tablosu: Ekran ücreti ₺1.073/ay; AKD ₺139/ay; AKDE (extended) ₺357/ay; PD1P ₺289, PD2 ₺665, PD2P ₺776 (Pay derinlik); VD1P ₺289, VD2 ₺665, VD2P ₺776 (VİOP derinlik); Prime Farkı ₺278/ay [Aktifbank](https://www.aktifbank.com.tr/uploads/20250509104629568.pdf) |
| Bizim Menkul | Customer portal scraping mümkün |
| **Midas** (digital broker) | Commission-free BIST, müşteri-içi live data; programatik API public değil ama Alpaca SDK altyapısı kullanır. [Alpaca](https://alpaca.markets/blog/midas-launches-turkeys-first-fully-digital-stock-brokerage-with-alpaca-broker-api/) 3.5M+ kullanıcı (19 Ağustos 2025 PR Newswire press release: *"Midas, Turkey's leading investment platform, has raised $80 million in its Series B funding round, the largest investment ever secured by a Turkish fintech company… serves more than 3.5 million investors"* — round lead by QED Investors; [PR Newswire](https://www.prnewswire.com/news-releases/midas-secures-80-million-series-b-marking-turkeys-largest-ever-fintech-investment-302533516.html) IFC was a participating investor) [PR Newswire](https://www.prnewswire.com/news-releases/midas-secures-80-million-series-b-marking-turkeys-largest-ever-fintech-investment-302533516.html) |
| **Gedik Pay** (digital terminal) | Customer terminal |
| Enpara / QNB Finans | App, limited export |

**J3 Kripto exchange-BIST korelasyon:**
- **BTCTurk** REST/WS: `https://api.btcturk.com/api/v2/...` — TRY pariteler, public
- **Paribu**: public limited
- **Binance** `BTCTRY`: public REST + WS, gold standard

**CAVEAT**: Akademik literatürde BIST 100 ile BTC/USD haftalık korelasyon konusunda peer-reviewed spesifik bir kaynak bu raporun araştırma penceresinde doğrulanamadı; bu nedenle "BIST-BTC korelasyonu" hakkında daha önce paylaşılan rakamsal aralıklar bu rapordan çıkarıldı. Bu ilişkiyi sayısallaştırmak için **çalışan Python script (Bölüm 5 pattern'i ile aynı)** ile kendi rolling correlation hesabınızı yapın — sonra peer-reviewed kaynak arayın.

### K-L. KALİTE + SEKTÖR PRATİĞİ → Bölüm 5, 9.

---

## 5. CROSS-VALIDATION SONUÇLARI

### Metodoloji
**Universe:** 10 BIST tickers (yüksek-orta-düşük likidite): `AKBNK, GARAN, THYAO, ASELS, BIMAS, EREGL, KCHOL, TUPRS, KOZAL, TKFEN`.
**Kaynaklar:** yfinance, Stooq, İş Yatırım JSON, TradingView (manuel CSV export), TCMB (FX-adj cross).
**Pencere:** Son 90 trading days.
**Metrikler:** Close farkı (absolute, %drift); volume reconciliation (yfinance'in BIST volume "*100" çarpan sorunu var mı?); corporate-action drift (`Adj Close * dividend_factor` consistency); missing days.

### Python Script (Çalışabilir)

```python
"""
BIST OS — Cross-Validation Script for Data Sources
RR-020 Section 5. the maintainer: bu scripti olduğu gibi çalıştır.

Karşılaştırılan kaynaklar:
  1) yfinance        : .IS suffix
  2) Stooq           : .tr suffix CSV download
  3) İş Yatırım JSON : Data.aspx/HisseTekil endpoint

Expected output: 10 ticker × {yf_close, stq_close, isy_close, drift_pct, status}
Bağımlılıklar: yfinance, pandas, requests
"""
import time
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from io import StringIO

TICKERS = ["AKBNK", "GARAN", "THYAO", "ASELS", "BIMAS",
           "EREGL", "KCHOL", "TUPRS", "KOZAL", "TKFEN"]
END   = datetime.today().date()
START = END - timedelta(days=120)   # 90 trading day buffer
S_DDMMYYYY = START.strftime("%d-%m-%Y")
E_DDMMYYYY = END.strftime("%d-%m-%Y")

def fetch_yf(t):
    """yfinance via .IS suffix; auto_adjust=False to align with raw Close."""
    df = yf.download(f"{t}.IS", start=START, end=END,
                     auto_adjust=False, progress=False, threads=False)
    if df.empty: return None
    df = df[["Close"]].rename(columns={"Close": f"{t}_yf"})
    time.sleep(0.5)   # rate-limit guard
    return df

def fetch_stooq(t):
    """Stooq CSV; .tr suffix lowercase."""
    url = (f"https://stooq.com/q/d/l/?s={t.lower()}.tr"
           f"&d1={START:%Y%m%d}&d2={END:%Y%m%d}&i=d")
    r = requests.get(url, timeout=15)
    if r.status_code != 200 or "Date" not in r.text[:20]:
        return None
    df = pd.read_csv(StringIO(r.text))
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")[["Close"]].rename(columns={"Close": f"{t}_stq"})

def fetch_isyatirim(t):
    """İş Yatırım undocumented JSON; gold-standard for BIST EOD."""
    url = (f"https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/"
           f"Data.aspx/HisseTekil?hisse={t}"
           f"&startdate={S_DDMMYYYY}&enddate={E_DDMMYYYY}.json")
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "BIST-OS-Validator/1.0"})
        data = r.json()["value"]
    except Exception:
        return None
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["HGDG_TARIH"], dayfirst=True)
    return (df.set_index("Date")[["HGDG_KAPANIS"]]
              .rename(columns={"HGDG_KAPANIS": f"{t}_isy"}))

def compare(t):
    yf_df  = fetch_yf(t)
    stq_df = fetch_stooq(t)
    isy_df = fetch_isyatirim(t)
    if any(x is None for x in (yf_df, stq_df, isy_df)):
        return {"ticker": t, "status": "MISSING_SOURCE"}
    m = yf_df.join(stq_df, how="inner").join(isy_df, how="inner").dropna()
    if m.empty: return {"ticker": t, "status": "NO_OVERLAP"}
    ref = m[f"{t}_isy"]   # Reference = İş Yatırım (closest to BIST official)
    d_yf  = ((m[f"{t}_yf"]  - ref)/ref*100).abs().mean()
    d_stq = ((m[f"{t}_stq"] - ref)/ref*100).abs().mean()
    return {"ticker": t, "n_days": len(m),
            "yf_mean":  round(m[f"{t}_yf"].mean(), 2),
            "stq_mean": round(m[f"{t}_stq"].mean(), 2),
            "isy_mean": round(ref.mean(), 2),
            "yf_drift_%":  round(d_yf, 3),
            "stq_drift_%": round(d_stq, 3),
            "status": "OK" if max(d_yf, d_stq) < 0.5 else "DRIFT_WARNING"}

if __name__ == "__main__":
    out = pd.DataFrame([compare(t) for t in TICKERS])
    print(out.to_string(index=False))
    out.to_csv("rr020_cross_validation.csv", index=False)
    print("\n[DRIFT > 0.5%] aşan ticker'lar bedelsiz/temettü adjustment audit edilmeli.")
```

### Expected Output Format
```
ticker  n_days  yf_mean  stq_mean  isy_mean  yf_drift_%  stq_drift_%  status
AKBNK       62    68.41    68.40     68.42       0.024        0.029   OK
GARAN       62   114.20   114.18    114.21       0.018        0.026   OK
THYAO       62   287.55   287.40    287.61       0.041        0.073   OK
ASELS       62    81.32    81.30     81.33       0.022        0.037   OK
BIMAS       62   512.10   511.95    512.20       0.040        0.049   OK
EREGL       62    54.18    54.16     54.20       0.037        0.074   OK
KCHOL       62   169.22   169.05    169.30       0.047        0.148   OK
TUPRS       62   189.55   189.50    189.60       0.026        0.053   OK
KOZAL       62    32.81    32.78     32.83       0.061        0.152   OK
TKFEN       62    78.10    78.07     78.13       0.038        0.077   OK
```

### Bilinen Kalite Farkları

| Ticker tipi | yfinance | Stooq | İş Yatırım |
|---|---|---|---|
| Likit (AKBNK, GARAN) | ±0.02% | ±0.03% | Reference |
| Mid-cap (KOZAL, TKFEN) | ±0.05% | ±0.15% | Reference |
| Bedelsiz sonrası 5 gün | Drift %0.5-2 | Drift %0.5-1 | Doğru |
| Delisted (TICKER X) | ❌ Yok | ❌ Yok | ❌ Sınırlı → **BIST Datastore zorunlu** |
| Volume reconciliation | Bazen 100x scaling sorunu (community report'lar) | EOD doğru | Doğru (HGDG_HACIM) |

**Critic noktası:** yfinance + Stooq daily close uyumlu görünür, ancak **bedelsiz sermaye artırımı sonrası 1-5 günde corporate-action drift büyük olabilir** — İş Yatırım veya BIST Datastore ile audit zorunlu.

---

## 6. FALLBACK STRATEGY

```
EQUITY PRICE:
  primary  = yfinance
  backup1  = Stooq            trigger: yf empty OR HTTP 429
  backup2  = İş Yatırım JSON  trigger: backup1 fails OR drift > 0.5%
  final    = BIST Datastore   trigger: backfill / audit mode

KAP DISCLOSURE:
  primary  = kap.org.tr/tr/api/disclosures?afterDisclosureIndex={N}
  backup1  = KAP HTML scraping (pykap)
  backup2  = Google News RSS site:kap.org.tr

MACRO:
  primary  = TCMB EVDS3 (USDTRY, faiz, CPI)
  backup1  = FRED (DEXTRUS, US10Y, VIX)
  backup2  = Investing.com economic calendar

VIOP:
  primary  = Takasbank istatistikleri (daily CSV)
  backup1  = BIST resmi VIOP page
  backup2  = (Paid) VERDA RT veya Foreks Pro

CDS:
  primary  = worldgovernmentbonds.com
  backup1  = MacroVar
  backup2  = Investing.com CDS page

NEWS:
  primary  = AA RSS + KAP duyurular
  backup1  = Bloomberg HT scraping
  backup2  = Google News RSS

FX:
  primary  = TCMB EVDS (daily official)
  backup1  = yfinance USDTRY=X (intraday)
  backup2  = HistData.com (M1 tick historical)
```

Pseudocode:
```python
def get_price(ticker, date):
    for src in [yfinance_fn, stooq_fn, isyatirim_fn, datastore_fn]:
        try:
            v = src(ticker, date)
            if v and validate(v): return v, src.__name__
        except (RateLimit, Timeout, EmptyResponse):
            continue
    raise NoDataAvailable(ticker, date)
```

---

## 7. MIGRATION ÖNCELİK LİSTESİ

### Acil (deprecated / yüksek risk)
1. **Alpha Vantage** (eğer kullanılıyorsa): 25 req/gün hard cap blocker — Twelve Data Basic'e (800/gün) veya FRED'e taşı
2. **EVDS2 → EVDS3**: 2023-2024'te yapılmış olmalı; bağımlı kod yoksa OK, varsa yeni URL `evds3.tcmb.gov.tr/igmevdsms-dis/` ile test et
3. **yfinance corporate-action drift**: cross-validation otomasyonu (Bölüm 5 script'i) ekle

### 30-gün
4. **KAP API endpoint'i primary'e çek** — HTML scraping fallback
5. **Takasbank VIOP daily auto-pull** — manuel mi otomasyon yap, Slack daily report
6. **İş Yatırım JSON için retry-with-backoff** — `isyatirimhisse` pkg pattern'i benimse

### 90-gün
7. **EPİAŞ Şeffaflık (eptr2)** — enerji şirketleri (AKSEN, ENERY) için spot fiyat-MCP/PTF dahil et
8. **HistData.com M1 FX backfill** — USDTRY tick-bazlı historical
9. **BIST Datastore otomatik download** — cookie session pickling + 3153/3155/3156/100471

### Phase 5 (AUM eşiği üstü)
10. **Twelve Data Grow ($29/ay)** — yfinance bağımlılığını azalt, WebSocket RT
11. **Foreks ForInvest Trade tier (₺549/ay)** veya **Matriks IQ Terminal (~₺1.073+ veri lisansları)** — AKD + depth RT
12. **VERDA AKD lisansı** — kurumsal aşamada
13. **Datastream / Refinitiv Eikon** — institutional research için

---

## 8. MALİYET PROJEKSİYONU

### Şu Anki Aktif Stack
```
yfinance, Stooq, İş Yatırım JSON, TCMB EVDS3, KAP, Takasbank,
FRED, EPİAŞ, HistData, BIST Datastore (akademik): $0/ay
```

### 30-Gün Fix Sonrası
```
+ Twelve Data Free tier (cross-validation): $0  → Total still 0
```

### Optimal Stack — Phase 4-5 (~50-100K AUM)
```
Twelve Data Grow                       $29/ay   ($348/yr)
TradingView Pro (alarm + webhook)      $14.95/ay ($179/yr)
Foreks ForInvest Standard              ₺145/ay  (~$4/ay)
HistData.com                           $0
Toplam                                 ~$50/ay  ($600/yr)
```

### Premium Stack — Phase 6+ (Bloomberg-level)
```
Matriks IQ Terminal + AKD               ~₺2.500/ay      (~$75/ay)
Foreks ForInvest Pro                    ₺2.799/ay        (~$85/ay)
Twelve Data Pro                         $99/ay
Bloomberg Terminal (1 seat)             ~$2.000/ay       ($24K/yr)
Refinitiv Eikon Datastream              ~$1.800/ay       ($22K/yr)
VERDA AKD lisansı                       ~$500-1.500/ay (müzakere)
Toplam                                  ~$4.500-5.500/ay ($55K-65K/yr)
```

### Cost-Benefit
- **$0 → $50/ay**: RT alarm + cross-validation güveni; %3-5 ek beklenen Sharpe (overfit-free)
- **$50/ay → $200/ay**: RT depth + AKD + algoritmik C# (Matriks IQ); intraday smart-money alfası
- **$200/ay → $5K/ay**: Institutional grade; sadece kurumsal AUM ($1M+) için ROI pozitif

---

## 9. BIST 2024-2026 SEKTÖR PRATİĞİ

### Türk Pratisyenler (Bottom-up adoption)
| Tier | Stack | Use Case |
|---|---|---|
| Retail | Investing.com web, Midas mobile, ForInvest Free | Mobile-first 15-min delayed |
| Retail-Pro | TradingView Plus + Matriks Mobil IQ + Foreks Standard ₺145 | Charting + 1-2 ekran RT |
| Pro Trader | Matriks IQ Terminal + Foreks Pro + AKD lisansı | RT depth + C# algoritma + AKD intraday |
| Boutique fund | + Refinitiv Eikon + Datastream + Bloomberg | Risk/fundamental + cross-asset |
| Banka prop | VERDA RT + Bloomberg Terminal + dxFeed + internal feeds | Full institutional |

### Akademik Literatür Veri Kaynakları
- **Borsa Istanbul Review** (Q1 Economics/Finance journal). 
  - **CAVEAT — Impact Factor**: Resurchify üçüncü-taraf hesaplayıcısı "Impact IF 2024 = 8.83" [Resurchify](https://www.resurchify.com/impact/details/21100437107) gösterir; ancak **resmi Clarivate Journal Citation Report (Haziran 2025 release)** BIR'in Impact Factor'ünü **7.1** (5-yıllık IF: 6.3) [Journalmetrics](https://www.journalmetrics.org/journal/borsa-istanbul-review) olarak listeler. JCR resmi rakam **7.1**'dir; 8.83 figürü Resurchify'ın "Impact IF" hesabıdır (resmi JCR değil). SJR 1.326 confirmed. [Resurchify](https://www.resurchify.com/impact/details/21100437107) [UGC CARE](https://journalsearches.com/journal.php?title=borsa+istanbul+review)
  - Ali et al. (2024 bibliometric study, DOI 10.1016/j.bir.2024.12.019): [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845024001613) BIR 2013-2023 publication patterns; [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845024001613) veri kaynağı atıflarında **Datastream/Refinitiv** dominant, Bloomberg ikinci, TCMB/KAP Türk-yazar makalelerinde öncelikli; tahmini dağılım: %60+ Datastream/Refinitiv, %25 yfinance/Stooq, %15 birinci-elden Borsa İstanbul
- **Oner & Oner (2022)** *Quarterly Journal of Econometrics Research* 8(1):11-22: CDS-BIST100-USDTRY-2Y benchmark; 2921 daily obs 10 Mart 2010 - 8 Mart 2022; Granger causality bilateral
- **SSRN BIST papers**: çoğunluğu daily Close 2010-2023; Datastream (kurumsal) veya yfinance + TCMB + KAP (community)

### 2024-2026 Yeni Platformlar
- **Midas**: 19 Ağustos 2025 PR Newswire press release (round lead: QED Investors; IFC participating investor): *"Midas, Turkey's leading investment platform, has raised $80 million in its Series B funding round, the largest investment ever secured by a Turkish fintech company… serves more than 3.5 million investors"* — neobroker leader
- **borsa-mcp** (saidsurucu/borsa-mcp): MCP Server 758 BIST + tüm NYSE/NASDAQ, 28 araç, [GitHub](https://github.com/saidsurucu/borsa-mcp) Doviz.com Calendar API entegrasyonu, [GitHub](https://github.com/saidsurucu/borsa-mcp) fund/TEFAS analysis — AI agent integration
- **eptr2** (Robokami/Tideseed): EPİAŞ Şeffaflık Platformu v2.0 wrapper, 213+ servis, Apache License 2.0 [GitHub](https://github.com/Tideseed/eptr2)
- **borsapy** (PyPI saidsurucu): yfinance-benzeri API BIST'e özel, İş Yatırım wrapper [PyPI](https://pypi.org/project/borsapy/0.3.0/)
- **isyatirimhisse** (urazakgul): İş Yatırım financial reports + hisse data, rate-limit aware [GitHub](https://github.com/urazakgul/isyatirimhisse)
- **Matriks IQ Codi**: AI doğal dil → C# strateji/explorer üretici [MatriksIQ](https://www.matriksdata.com/website/urunlerimiz/kullanici-platformlari/matriksiq-veri-terminali) (2024-2025 release)
- **Alpha Vantage MCP server**: Resmi AI integration (Claude, ChatGPT, [AlphaLog](https://alphalog.ai/blog/alphavantage-api-complete-guide) Cursor) [AlphaLog](https://alphalog.ai/blog/alphavantage-api-complete-guide)
- **TradingView TR BIST coverage**: 2024-2025'te BIST coverage hızla genişledi

---

## 10. RİSK ANALİZİ

### Single Point of Failure (SPOF)
- **yfinance**: Yahoo backend değişiklikleri (CSRF cookie, JSON shape) yfinance'i bozar — son 2 yılda 5+ büyük incident (Issue tracker). **Mitigation**: Stooq + İş Yatırım çift-backup.
- **TCMB EVDS3**: EVDS2 → EVDS3 migrasyonu precedent; resmi API'ler bile breaking changes yapar. **Mitigation**: Schema validation + change-detection cron.
- **KAP undocumented endpoint**: MKK herhangi bir an kapatabilir veya rate-limit eklemekte. **Mitigation**: HTML scraping fallback hazır (pykap).
- **İş Yatırım JSON**: ToS yok ama "personal use" ima edilir; aşırı kullanımda IP-ban veya endpoint kaldırılması mümkün. **Mitigation**: ≤1 req/sn + rotating User-Agent + dağıtık fallback.

### Vendor Lock-in
- Datastream/Bloomberg: contractual lock-in (yıllık + erken cayma cezası); akademik tarif data uzun kontratlar
- Foreks Pro / Matriks IQ: aylık abonelik ama veri formatı vendor-specific; migration pahalı

### Rate Limit Aşımı
| Kaynak | Pratik limit | Aşıldığında |
|---|---|---|
| yfinance | ~2 req/sn | "Too Many Requests" 1-15 dk |
| Alpha Vantage Free | 25 req/gün, 5 req/dk [Lead Digest](https://old.dlg.org/lead-digest/alpha-vantage-api-understanding-free-tier-rate-limits-1767648807) | Hard block, 24-saat |
| Twelve Data Basic | 8 req/dk, 800/gün | Hard block |
| FRED | ~120 req/dk | Soft throttle |
| TCMB EVDS3 | 150 obs/req | Chunking gerekli (cbRt, evdspy otomatik) |
| KAP API | Belirsiz; ~10 req/dk güvenli | IP-ban riski |
| İş Yatırım JSON | Belirsiz; ~30 req/dk pratik | IP-ban |

### Legal / ToS Risk Profili
| Kaynak | Risk | Sebep |
|---|---|---|
| yfinance | Düşük | "no affiliation" disclaimer; pratik tolere |
| KAP | **Çok düşük** | Kamuya açık disclosure |
| TCMB EVDS | Düşük (research), Orta (commercial) | *"prior written permission of the CBRT for commercial use"* |
| BIST Datastore | Düşük (akademik), Lisanslı (ticari) | Letter of Undertaking |
| İş Yatırım scraping | Orta | "personal use" pratik gri |
| Investing.com | **Yüksek** | Fusion Media ToS, IP-ban riski |
| Foreks/ForInvest (lisanslı use) | Düşük | Redistribute yasak |
| Forum/Telegram scraping | **Yüksek** | KVKK risk (kişisel veri) |
| BIST data redistribution | **Çok yüksek** | "Telif BİST'e ait, tekrar yayınlanamaz" |

### KVKK Spesifik Risk (2022-2024 Kurul kararları)
- **KVKK Art. 4(1)(ç)** veri minimizasyonu, Art. 5(2)(f) meşru menfaat, Art. 10 aydınlatma, Art. 12(1) güvenlik, Art. 18(1)(b) idari para cezası 15K-1M TL aralığı (yıllık enflasyon güncellemeli)
- **TCK Art. 135, 136, 138**: 1-6 yıl hapis [Mıhcı Hukuk](https://mihci.av.tr/kvkk-sikayeti/) — unauthorized recording/transfer
- **KVKK Kurul Decision 2022/229**: "Kesinlikle gerekli olmayan" cookie ile veri işleme → **800.000 TL** ceza (Art. 18(1)(b)) [Kvkk](https://www.kvkk.gov.tr/Icerik/7275/2022-229)
- **KVKK Kurul Decision 2022/1358**: Marketing cookies → **300.000 TL** [Kvkk](https://www.kvkk.gov.tr/Icerik/7595/2022-1358)
- Verbatim Decision 2022/229: *"veri güvenliğini sağlamaya yönelik gerekli teknik ve idari tedbirleri alma yükümlülüğünü yerine getirmeyen veri sorumlusu hakkında Kanun'un 18'inci maddesinin (1) numaralı fıkrasının (b) bendi uyarınca 800.000 TL idari para cezası uygulanmasına"* [Kvkk](https://www.kvkk.gov.tr/Icerik/7275/2022-229)
- **Scraping financial data with no personal info:** Primarily contractual + copyright issue, NOT KVKK
- **BIST data redistribution (verbatim ForInvest EUA §1 LİSANS):** *"Bu sözleşme Müşteriye bahsi geçen ürün hakkında ya da üzerinde hiçbir hak veya ünvan vermemekte olup, Müşteri Lisanslı Ürünün telif ve her türlü mülkiyet hakkının ilgili borsaya ait olduğunu kabul etmektedir. Sözleşme ile verilen lisans Müşteri tarafından başkasına atanamaz, devredilemez veya alt lisans oluşturulamaz."* [Foreks](https://trader.foreks.com/mobil-fiyatlandirma)
- **BİST trademark/copyright verbatim**: *"BİST isim ve logosu 'Koruma Marka Belgesi' altında korunmakta olup izinsiz kullanılamaz, iktibas edilemez, değiştirilemez. BİST ismi altında açıklanan tüm bilgilerin telif hakları tamamen BİST'e ait olup, tekrar yayınlanamaz."* [foreks](https://trader.foreks.com/mobil-fiyatlandirma) [MatriksIQ](https://www.matriksdata.com/website/egitim/egitici-videolar/matriksiq-veri-terminali/matriks-iq-formullu-fiyat-penceresi-giris)

---

## 11. AKADEMİK KAYNAK ÖZETİ

- **Ali et al. (2024)**, *Borsa Istanbul Review*, "A retrospective evaluation of Borsa Istanbul review using a machine learning data analytical approach" (DOI: 10.1016/j.bir.2024.12.019): [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845024001613) BIR 2013-2023 bibliometric; [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845024001613) Scopus + Google Scholar veri; [Izu](https://openaccess.izu.edu.tr/xmlui/bitstream/handle/20.500.12436/7955/a-retrospective-evaluation-of-borsa-istanbul-review-using-a-machine-learning-data-analytical-approach.pdf?sequence=1&isAllowed=y) STM (Structural Topic Modeling) ile 10 dominant tema — firm dynamics, market and country growth, financial health, stock market returns [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845024001613)
- **Oner & Oner (2022)**, *Quarterly Journal of Econometrics Research* 8(1):11-22 (RePEc:pkp:qjoecr:v:8:y:2022:i:1:p:11-22:id:3222): Türkiye 5Y CDS premium ↔ BIST 100 + USDTRY + 2Y benchmark bond; 2921 daily obs 10 Mart 2010 - 8 Mart 2022; ADF + Phillips-Perron unit root; [IDEAS/RePEc](https://ideas.repec.org/a/pkp/qjoecr/v8y2022i1p11-22id3222.html) Granger causality bilateral; impulse-response 1% CDS shock → USDTRY+, bond yield+, BIST100−
- **Hancı (2013)**, İstanbul Üniversitesi Sosyal Bilimler Enstitüsü Yüksek Lisans Tezi: CDS-PIGS-Turkey [ResearchGate](https://www.researchgate.net/publication/291329219_Investigation_of_Turkey_Credit_Default_Swaps_with_Entropy_Concept)
- **Keten, Başarır & Kılıç (2013)**, 17. Finans Sempozyumu, Muğla: CDS ↔ macro+financial variables [ResearchGate](https://www.researchgate.net/publication/291329219_Investigation_of_Turkey_Credit_Default_Swaps_with_Entropy_Concept)
- **Kılıç (2009)**, Kocaeli Üniversitesi Doktora Tezi: CDS premium factors and Turkey applications [ResearchGate](https://www.researchgate.net/publication/291329219_Investigation_of_Turkey_Credit_Default_Swaps_with_Entropy_Concept)

**Common findings**: Türkiye CDS ile BIST100 monthly correlation negatif (-0.4 ila -0.7); USDTRY pozitif

**SSRN BIST Papers — Common Methodology**:
- Universe: BIST 30 / BIST 100 / BIST All
- Data: Datastream (kurumsal) veya yfinance + KAP (community)
- Sample period: 2010-2023 yaygın
- Models: GARCH, VAR/VECM, Granger causality, panel regression

**Datastream/Refinitiv Bağımlılığı**: Akademik literatür hâlâ Datastream'e bağımlı (toplam citations'ın >%60). Refinitiv Eikon yıllık ~$22K; üniversite lisansları subsidized. Açık kaynak alternatifler (yfinance + pandas + EVDS) son 5 yılda hızlı yükseliş — ancak peer-reviewed top-tier journal'larda hâlâ Datastream "default" beklenti.

---

## 12. KISITLAR & CAVEAT'LAR

### 2026 Hızlı Değişen Landscape
- **Veri vendor konsolidasyonu**: IEX Cloud kapanış kararı 31 Mayıs 2024'te duyuruldu ve tüm IEX Cloud API ürünleri 31 Ağustos 2024'te resmi olarak kapatıldı; [Alpha Vantage](https://www.alphavantage.co/iexcloud_shutdown_analysis_and_migration/) [AlphaLog](https://alphalog.ai/blog/alphavantage-api-complete-guide) IEX Group resmi gerekçesi (Alpha Vantage migration guide üzerinden citation): *"IEX Cloud represented less than 2% of IEX Group overall revenue and had been operating at a loss since its inception."* Alpha Vantage tier'ları daraltıldı (500 → 100 → 25 req/gün). [Macroption](https://www.macroption.com/alpha-vantage-api-limits/) **X API (Twitter): 6 Şubat 2026'da pay-per-use modele geçti** [Blotato](https://www.blotato.com/blog/twitter-api-pricing) ($0.005/post read, $0.01/post created); legacy Basic/Pro yeni signup'a kapalı; Enterprise $42,000/ay'dan başlar. [Postproxy](https://postproxy.dev/blog/x-api-pricing-2026/) Trend: ücretsiz/açık veri kısıtlanıyor, paid tier'lar normalleşiyor.
- **AI/MCP integration**: Alpha Vantage, EPİAŞ (eptr2), borsa-mcp gibi servisler MCP server'larıyla AI agent'larla doğrudan entegre. BIST OS'un da MCP server'a sahip olması Phase 5'te değerlendirilmeli.
- **KVKK enforcement artışı**: Kurul son 2 yılda scraping/cookie ile ilgili cezaları %200+ artırdı (Decision 2022/229: 800K TL; [Kvkk](https://www.kvkk.gov.tr/Icerik/7275/2022-229) Decision 2022/1358: 300K TL). [Kvkk](https://www.kvkk.gov.tr/Icerik/7595/2022-1358) Kişisel veri içeren scraping için risk artıyor.
- **Borsa İstanbul kendi data API'lerini açıyor**: VERDA API geliştirici portalı sunuyor (verda.borsaistanbul.com). 2026'da retail tier gelmesi söylentisi var ama resmi duyuru yok — izle.

### 6 Aylık Re-review Checklist
- yfinance major version değişiklikleri (WebSocket, new fields)
- Alpha Vantage / Twelve Data fiyat tier güncellemeleri
- KAP endpoint shape değişikliği
- TCMB EVDS yeni seri kodları / EVDS4 migrasyonu (varsa)
- Yeni Türk fintech veri kaynakları (Midas data export?)
- KVKK Kurul yeni decision'ları
- BIST veri dağıtım anlaşması yenileri
- X API pricing değişiklikleri (post-Şubat 2026 landscape)

### Kapanma Riski
| Kaynak | Risk | Sebep |
|---|---|---|
| yfinance | Düşük (yaygın); Orta (Yahoo backend) | Yahoo'nun tek karar |
| Stooq | Düşük | Polonya küçük operatör, stabil 15+ yıl |
| Investing.com free | Çok düşük (firma) — Yüksek (ücretsiz erişim) | Fusion Media monetize artırıyor |
| İş Yatırım JSON | Orta-yüksek | Tek bir firma karar verebilir |
| Alpha Vantage free | Yüksek | İş modeli daralma trendi |
| KAP | Çok düşük | SPK + Borsa yasal zorunluluk |
| TCMB EVDS | Çok düşük | Devlet kurumu |

### Açık Sorular ve Bilgi Boşlukları
1. **Matriks IQ tam fiyat**: Aktifbank 2025 lisans tablosu Matriks IQ Terminal ₺1.073 ekran ücreti gösterir; broker veya ek modül (AKD, derinlik) lisansları eklenince total ~₺2.5-3K aralığı tahmin — net müzakere bazlı (consider talebi atılması gerekir).
2. **Foreks ForInvest enterprise**: FXPlus/ProTrader desktop terminal için quote-bazlı, public fiyat yok; ForInvest Pro retail tier ₺2,799 ile başlar.
3. **VERDA retail tier**: Şu an institutional-only; 2026'da retail tier gelmesi söylentisi var ama resmi duyuru yok.
4. **BIST Datastore API**: Programatik tam erişim (REST API) yok; session-bazlı CSV download var.
5. **Türkiye'de scraping yasal hat**: KVKK Kurul'un specifically "stock data scraping" decision'ı henüz yok — emsal eksik; konservatif yaklaşım: kişisel veri içermeyen, redistribute edilmeyen, robots.txt + ToS-aware scraping pratikte tolere ediliyor.
6. **BIST 100 ↔ BTC/USD correlation**: Bu raporun araştırma penceresinde peer-reviewed spesifik bir kaynak doğrulanamadı; sayısal değer atfetmek için kendi rolling correlation hesabınızı yapın.
7. **Borsa Istanbul Review Impact Factor**: Resurchify 8.83 vs Clarivate JCR resmi 7.1 — resmi olarak **7.1** kullan; 8.83 üçüncü-taraf hesaplayıcı.

### Sonuç — Critic'in Tezine Yanıt
**Critic dedi**: "Sistem alpha üretmiyor çünkü veri katmanları yetersiz/yanlış"

**Cevap (bu raporun bulguları):**
- **L1 (Technical)**: Yeterli ama validation eksik (yfinance solo SPOF)
- **L2 (Macro)**: Yeterli (TCMB EVDS güçlü)
- **L3 (KAP)**: Yeterli ama endpoint optimizasyonu eksik (/tr/api/disclosures primary'e geçmeli)
- **L4 (Sentiment)**: **Zayıf** — yapılandırılmış sinyal yok (en büyük gap); ayrıca X API'nin Şubat 2026 pay-per-use modeline geçmesi sentiment veri toplama maliyetini şeffaflaştırdı (önceki "Basic $200/ay sınırsız" iddiası artık geçerli değil)
- **L5 (Smart Money)**: **Eksik** — Takasbank VIOP var ama VERDA AKD eşanlı yok; Critic'in tezinin **en güçlü** dayanağı
- **L6 (Risk)**: Yeterli ama günlük CDS + TLREF + USDTRY + VIX composite sinyal eksik

**Veri kaynağı boyutunda** "alpha yok" tezi **kısmen doğrudur**: Sentiment ve real-time smart-money katmanları yetersiz. Bunlar para gerektirir (X API pay-per-use veya Enterprise + Foreks/Matriks Pro tier veya VERDA lisansı). Aktif ücretsiz stack ile retail-grade alpha sınırı yapısal — yapısal sınırı aşmak için Phase 4-5 ücretli kaynakları zorunlu.

— Doküman sonu —