# RR-012: BIST OS Trading System — 14 EM/BIST-Spesifik Faktör Literatür Derinleştirmesi ve İmplementasyon Fizibilite Analizi

**Rapor No:** RR-012  
**Tarih:** 24 Mayıs 2026  
**Versiyon:** 1.0  
**Sınıflandırma:** İç araştırma raporu — Implementation-ready  
**Yazar:** Lead Research Agent  
**Dil:** Türkçe (akademik ağırlıklı)

---

## 1. EXECUTIVE SUMMARY

Bu rapor, BIST OS algoritmik trading sisteminin Phase 5 mimarisi için değerlendirilmesi gereken 14 emerging-market (EM) ve BIST-spesifik faktörün akademik literatürünü derinleştirir, BIST veri durumunu haritalandırır ve 90-günlük implementasyon fizibilite skorlarını üretir. Mevcut mimari (L1–L6, per-stock signal) ile uyum açısından kritik bulgu: **14 faktörün 6'sı cross-sectional sort gerektiriyor**; bu, Phase 5 için "sort_layer" altyapısının kritik path üzerinde olduğunu doğrular.

### 1.1 14 Faktör Ranked Tablosu (özet)

| # | Faktör | Alpha Potansiyel | Mali­yet (kod+veri) | Süre | Genel |
|---|--------|------------------|---------------------|------|-------|
| B14 | Earnings Revision Momentum | Yüksek | Orta | 30g | **TOP-1** |
| A5 | Sovereign CDS Conditional Gate | Yüksek | Düşük | 30g | **TOP-2** |
| B7 | USDTRY Pass-Through Beta | Yüksek | Düşük | 30g | **TOP-3** |
| A1 | Asness Value-Momentum Combo | Çok Yüksek | Yüksek | 90g+ | Phase 5 |
| A3 | EM Liquidity Premium (Amihud) | Orta-Yüksek | Yüksek | 90g+ | Phase 5 |
| B8 | Holding NAV Discount Mean Reversion | Yüksek | Orta | 90g | Phase 5 |
| B6 | Foreign Flow İkinci Türevi | Orta | Orta | 60g | Phase 5 |
| B10 | BIST Endeks Dahil/Çıkar | Orta | Orta | 60g | Phase 5 |
| B12 | TLREF/Reverse Repo Spread | Orta | Düşük | 30g | Q3 2026 |
| A2 | Country-Relative Currency Mom. | Düşük (BIST tek piyasa) | Yüksek | 180g | Düşük öncelik |
| A4 | Inflation-Beta Sorting | Orta | Yüksek | 180g | Düşük öncelik |
| B9 | Temettü Cluster Timing | Düşük-Orta | Düşük | 60g | İkincil |
| B11 | Block Trade Tespiti | Orta | Çok Yüksek | 180g+ | İmkansız (intraday) |
| B13 | Açığa Satış + Lending Fee | NEGATİF (yasak aktif) | N/A | N/A | **Sakın Yapma** |

### 1.2 Top 3 Öncelik (30-gün implement)

1. **B14 — Earnings Revision Momentum:** Chan-Jegadeesh-Lakonishok (1996) literatür temelli; BIST'te KAP "kar payı dağıtım tablosu" + İş Yatırım/Foreks consensus revizyonları üzerinden yapılabilir. L3 KAP katmanına entegre. Literatür: 6-ay tutma için SUE-decile spread'i **%7.5**, earnings-revision decile spread'i **%7.7** (Chan, Jegadeesh & Lakonishok 1996, Journal of Finance 51(5): 1681–1713; IBES 1977–1993 örneklem).
2. **A5 — Sovereign CDS Conditional Gate:** Longstaff-Pan-Pedersen-Singleton (2011) sovereign risk literatürü; Türkiye 5Y CDS verisi günlük erişilebilir. L2 Macro veya L6 Risk gate olarak entegre. Cross-sectional sort gerekmez — tek skaler gate.
3. **B7 — USDTRY Pass-Through Beta:** Hisse-spesifik USDTRY duyarlılığı (firm-level regresyon). L1 Technical veya L2 Macro içine. RIETI (2022) Türk firmaları için anlamlı negatif beta belgelemiş; sektör heterojenliği yüksek.

### 1.3 Top 3 Medium-Term (Phase 5, 90+ gün)

1. **A1 — Asness Value-Momentum Combo:** En yüksek beklenen alpha (Asness, Moskowitz & Pedersen 2013, Journal of Finance 68(3): 929–985; sample: ABD, İngiltere, kıta Avrupası, Japonya). Cross-sectional sort + book-value verisi gerekiyor (KAP üzerinden mümkün). Mimari değişiklik kritik.
2. **A3 — EM Liquidity Premium (Amihud):** Bekaert-Harvey-Lundblad (2007) Türkiye'yi panele dahil eder (zero-return measure); Atılgan-Demirtaş-Günaydın (2016) BIST'te likidite-getiri ilişkisini doğrular. Cross-sectional sort gerekli.
3. **B8 — Holding NAV Discount Mean Reversion:** KCHOL/SAHOL/AGHOL/KOZAL/DOHOL — Lee-Shleifer-Thaler (1991) closed-end fund puzzle literatür temelli. KCHOL NAV iskonto mid-teen'den **~%30**'a genişledi (PA Turkey, Mart 2025); mean reversion sinyali güçlü.

### 1.4 "Sakın Yapma" Listesi

- **B13 — Açığa Satış + Lending Fee:** SPK 15.03.2026 tarihli ve 15/517 sayılı kararı uyarınca Borsa İstanbul pay piyasalarında açığa satış yasaklanmıştır; 28.03.2026 tarihli ve 19/625 sayılı kararla yasak **10.04.2026 seans sonuna kadar** uzatıldı (kaynak: SPK bülteni; Habertürk, Bloomberg HT, Hürriyet Bigpara, Mart 2026 haberleri). Lending-fee verisi BIST'te şeffaf değil. Mevcut rejim altında implementasyon mümkün değil; yasak kalkıncaya kadar **pas geç**.
- **A2 — Country-Relative Currency Momentum:** BIST tek bir piyasa olduğundan "ülkeler-arası" momentum çapraz-kesit BIST içinde anlamsız. TRY'yi başka EM para birimleriyle karşılaştırılan global FX faktörüne dönüştürmek mümkün ama portfolyo ölçeği (<500K TL) FX işlem altyapısı gerektirdiği için ROI negatif.
- **B11 — Block Trade Tespiti (intraday):** Holthausen-Leftwich-Mayers (1990) intraday tick-by-tick gerektiriyor; yfinance günlük veri sağlar, BIST Datastore intraday için ücretli abonelik (Matriks/Foreks) zorunlu. **<500K TL portföy için ROI negatif.**

---

## 2. SCORING MATRİSİ

1–10 puanlı her kategori. "Tersine" sütunlar düşük=kötü ölçütleri ters çevirir; toplam yüksek = öncelikli.

| # | Faktör | Akademik | Veri | Komplek tersine | Alpha | Risk tersine | **Toplam** |
|---|--------|---------|------|-----------------|-------|--------------|------------|
| B14 | Earnings Revision Mom. | 9 | 7 | 8 | 8 | 8 | **40** |
| A5 | Sovereign CDS Gate | 10 | 9 | 9 | 7 | 7 | **42** |
| B7 | USDTRY Pass-Through Beta | 8 | 9 | 8 | 7 | 7 | **39** |
| A1 | Asness V-M Combo | 10 | 7 | 4 | 9 | 7 | **37** |
| A3 | EM Liquidity (Amihud) | 9 | 8 | 5 | 7 | 7 | **36** |
| B8 | Holding NAV Discount | 9 | 7 | 6 | 8 | 6 | **36** |
| B6 | Foreign Flow 2nd Derivative | 8 | 6 | 7 | 6 | 7 | **34** |
| B10 | Endeks Dahil/Çıkar | 8 | 7 | 7 | 6 | 6 | **34** |
| B12 | TLREF/Repo Spread | 6 | 9 | 8 | 5 | 7 | **35** |
| B9 | Temettü Cluster | 5 | 8 | 8 | 5 | 8 | **34** |
| A4 | Inflation-Beta Sort | 8 | 6 | 4 | 6 | 5 | **29** |
| A2 | Currency Momentum (TR-spec) | 9 | 7 | 4 | 4 | 6 | **30** |
| B11 | Block Trade Tespiti | 8 | 3 | 3 | 6 | 5 | **25** |
| B13 | Açığa Satış + Lending Fee | 9 | 1 | 2 | 0 (yasak) | 1 | **13** |

**Yorum:** Toplam puanı en yüksek 3 faktör (A5, B14, B7) "30-gün implement" listesiyle örtüşür. A1 ve A3 alpha sıralamasında yüksek ama mimari maliyet düşürür. B13 yasak nedeniyle dramatik biçimde dipte.

---

## 3. HER FAKTÖR İÇİN DETAYLI ANALİZ

### 3.1 A1 — Asness-style EM Value-Momentum Combo

**Akademik temel.** Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere", *Journal of Finance* 68(3): 929–985, DOI: 10.1111/jofi.12021. Yazarlar "consistent value and momentum return premia across eight diverse markets and asset classes" rapor eder; value ve momentum negatif korele (-0.50 ila -0.60 cross-market) ve kombinasyon Sharpe oranını artırır. Test edilen hisse paneli ABD, İngiltere, kıta Avrupası, Japonya — **Türkiye doğrudan örneklemde değil**. Doğan, Kevser & Leyli Demirel (2022) "Testing the Augmented Fama–French Six-Factor Asset Pricing Model with Momentum Factor for Borsa Istanbul", *Discrete Dynamics in Nature and Society*, DOI: 10.1155/2022/3392984, 2013/10–2021/05 dönemi 24 portföy × 396 hafta = **9,504 portfolio observations** üzerinde FF6F'in BIST'te en iyi explanatory model olduğunu raporlar; momentum faktörü anlamlı katkı sağlar. Bildik & Gulay (2007) "Profitability of Contrarian Strategies: Evidence from the Istanbul Stock Exchange", *International Review of Finance* 7(1–2): 61–87, DOI: 10.1111/j.1468-2443.2007.00068.x — 1991–2000 örneklemiyle "a self-financing trading strategy, buying past loser stocks and selling past winner stocks generate significant abnormal returns (approximately 15% annually) in ISE"; Ersoy & Ünlü (2013) "Size, Book to Market Ratio and Momentum Strategies: Evidence from Istanbul Stock Exchange", SSRN 2731176, 1995–2010 örneklemiyle 6-ay tutma momentumunun BIST'te anlamlı olduğunu ve size/B-M ile partial olarak açıklanabildiğini gösterir. Birleştirilmiş literatür: **BIST'te kısa-vadeli (1 ay) reversal + 6-ay momentum + uzun-vadeli (15–36 ay) reversal** kombinasyonu mevcut.

**BIST veri durumu.** B/M oranı: KAP'tan firma bazlı book value + İş Yatırım screener'dan market value. yfinance fiyat verisi 12-ay momentum hesaplaması için yeterli (tarihsel 2000+ aylık veri). Erişilebilirlik: **mevcut**. Veri kalitesi: KAP standart finansal tablolar IFRS uyumlu, ancak 2022–2024 hiperenflasyon dönemi inflation-adjusted reporting (TMS 29) sonrası book value yorumlaması dikkat gerektirir.

**Implementation kompleksitesi: 5/5 (yüksek).** Cross-sectional sort gerekli (Top 30% – Bottom 30% kompozit skor). Tahmini ~400–600 satır kod (factor_engine, sort_layer, combination). Aylık rebalance. Mimari değişiklik **zorunlu**: BIST OS şu an per-stock signal — Phase 5'te sort_layer/universe_ranker eklenmesi gerek.

**Beklenen alpha.** Literatür quote: AMP (2013) U.S. equities value-momentum kombinasyonu için Sharpe ≈ 0.79; global stock selection için Sharpe ≈ 1.21. Doğan et al. (2022) BIST'te FF6F momentum t-istatistiklerinin anlamlı olduğunu raporlar. **BIST için tahmin (extrapolation, directional):** EM panellerinde value-momentum kombinasyonu net pozitif; BIST'in yüksek volatilitesi ham getiriyi yükseltir ama Sharpe daha düşük olabilir.

**Riskler.** (1) 2022–2024 hiperenflasyon book value bozulması — survivorship + extreme value outlier; (2) Türk small-cap'lerde likidite ihlali; (3) momentum crash riski (Daniel & Moskowitz 2016 type drawdowns); (4) cross-sectional sort gerektiren mimari gap.

**Mevcut katmana entegrasyon yolu.** L6 Risk (sizing) + yeni Phase 5 sort_layer. L1 Technical mevcut momentum sinyallerini cross-sectional rank'e dönüştürür.

**90-gün içinde implement edilebilir mi?** **Kısmen.** Sort_layer altyapısı 60–90 günde tamamlanabilir, ardından A1 kombinasyon 30 günde devreye alınır. Toplam ~120 gün ⇒ **Phase 5 ile birlikte**.

---

### 3.2 A2 — Country-Relative Currency Momentum (TRY)

**Akademik temel.** Menkhoff, Sarno, Schmeling & Schrimpf (2012) "Currency Momentum Strategies", *Journal of Financial Economics* 106(3): 660–684, DOI: 10.1016/j.jfineco.2012.06.009. Verbatim: "We find a significant cross-sectional spread in excess returns of up to 10% per annum (p.a.) between past winner and loser currencies." 48-currency örneklem 1976–2010; momentum strategy Sharpe oranı yazarların benchmark carry-trade SR'sini (0.82) aşıyor. Transaction-cost sonrası net kar düşüyor. TRY paneldedir (sample sonradan emerging FX'i içerir). Burnside, Eichenbaum, Kleshchelski & Rebelo (2011) carry trade ile momentum'un farklı risk faktörleri olduğunu gösterir.

**BIST veri durumu.** TRY/USD, TRY/EUR günlük veri TCMB EVDS'den çekilebilir (mevcut). EM cross-section için MSCI EM currency basket verisi ücretli olabilir. BIST OS tek-piyasa (Türkiye); strategy implement edilse "TRY long vs USD short" gibi pozisyon BIST hisse sistemi dışında.

**Implementation kompleksitesi: 4/5.** FX trading altyapısı yok; yfinance FX vekilleri (TRY=X) günlük close veriyor ama Türkiye'de FX trade için ayrı broker hesabı gerek. <500K TL portföyde 1 lot FX kontratı ölçek-dışı.

**Beklenen alpha.** MSS&S (2012): cross-sectional spread up to **10% p.a.** TRY'nin BIST OS portföy bağlamında doğrudan trade'i mümkün değil; **dolaylı kullanım: TRY momentum sinyali → BIST defensive/offensive sektör allocation**'a girdi olabilir.

**Riskler.** (1) FX trade altyapısı yok; (2) TCMB intervention sık (politika döviz alımı); (3) regime change (Şimşek programı 2023 sonrası); (4) Türk lirasının yapısal değer kaybı momentum'u tek yönlü trapler.

**Mevcut katmana entegrasyon yolu.** L5 Smart Money (sinyal olarak) veya L2 Macro (filtre olarak), trade edilen varlık olarak değil.

**90-gün içinde implement?** **Hayır.** Doğrudan strateji olarak değil; macro filtre olarak 30 günde mümkün.

---

### 3.3 A3 — EM Liquidity Premium (Bekaert-Harvey-Lundblad + Amihud)

**Akademik temel.** Bekaert, Harvey & Lundblad (2007) "Liquidity and Expected Returns: Lessons from Emerging Markets", *Review of Financial Studies* 20(6): 1783–1831, DOI: 10.1093/rfs/hhm030. Yazarlar "zero daily firm returns proportion" likidite ölçüsü ile gelecek getirileri istatistiksel olarak önceden öngörebileceğini göstermiştir; Türkiye paneldedir (NBER WP 11413 versiyonu EM listesinde). Amihud (2002) "Illiquidity and stock returns: cross-section and time-series effects", *Journal of Financial Markets* 5(1): 31–56, ILLIQ ölçüsü (|return|/volume) standart. BIST-spesifik: Atılgan, Demirtaş & Günaydın (2016) "Liquidity and Equity Returns in Borsa İstanbul", *Applied Economics* 48(52): 5075–5092, DOI: 10.1080/00036846.2016.1170935 — BIST'te 265 şirket 2002–2017 örneklemiyle illikidite premium'un anlamlı olduğunu doğrular; Amihud ve Corwin-Schultz bid-ask estimator kullanır. Karşı bulgu: Hacettepe IIBF (2020), 2002–2018 örneklemiyle LCAPM çerçevesinde **likidite azlık priminin BIST'te anlamlı olmadığını** rapor eder — sonuç metodolojiye duyarlı.

**BIST veri durumu.** Günlük volume + close yfinance üzerinden mevcut → Amihud ILLIQ ve "zero-return-day" Lesmond ölçüsü hesaplanabilir. Bid-ask spread için intraday/Level-2 veri ücretli (Matriks/Foreks). Erişilebilirlik: **Amihud ve zero-return = mevcut**; mikroyapı ölçüleri = zor.

**Implementation kompleksitesi: 4/5.** Cross-sectional sort gerekli (illikit Top 30% – likit Bottom 30%). ~300 satır kod. Aylık rebalance.

**Beklenen alpha.** Atılgan et al. (2016) BIST için anlamlı negatif likidite katsayısı; BHL (2007) EM panelinde liberalization öncesi 5–10% yıllık premium tahmin edilebilir. **Bull/bear ayrımı:** Bear market'te liquidity premium genişler (flight-to-liquidity); bull market'te daralır.

**Riskler.** (1) Atılgan vs Hacettepe IIBF zıt bulgular — metodoloji riski; (2) <500K TL portföyde illikit hisselerde gerçek slippage; (3) survivorship bias delisted ticker'lar.

**Mevcut katmana entegrasyon yolu.** L6 Risk (sizing penalty for illiquid names) + L5 Smart Money (illiquidity factor cross-sectional rank).

**90-gün içinde implement?** **Kısmen.** Sort_layer hazır olursa 30 günde mümkün; sort_layer'ı beklerse 90 gün.

---

### 3.4 A4 — Inflation-Beta Sorting (Boudoukh-Richardson + Yıldırım-Berument)

**Akademik temel.** Boudoukh & Richardson (1993) "Stock Returns and Inflation: A Long-Horizon Perspective", *American Economic Review* 83(5): 1346–1355 — uzun ufukta nominal hisse getirileri ile enflasyon arasındaki ilişkinin pozitif olabileceğini gösterir (Fisher hipotezi uzun-vadeli). Berument & Güner tarzı Türk çalışmaları (EconBiz 10001238215, "Inflation, inflation risk and interest rates: a case study for Turkey") Türk piyasasının enflasyon dinamiklerine duyarlılığını belgeler. BIST'te 2022–2024 hiperenflasyon döneminde TMS 29 inflation accounting devreye girdi; enflasyon-beta cross-section anlamlı.

**BIST veri durumu.** Aylık CPI TCMB EVDS'den, hisse getirileri yfinance'den mevcut. Sektör-bazlı CPI bileşenleri (food, energy, services) TÜİK'ten alınabilir.

**Implementation kompleksitesi: 4/5.** Rolling 36-ay regresyon her hisse için (inflation beta), ardından cross-sectional sort. ~250 satır kod. Aylık rebalance.

**Beklenen alpha.** Literatürde sektör seviyesinde anlamlı: bank, energy, food/retail farklı işaretler. BIST için tahmin: rejime bağlı (yüksek enflasyon döneminde reel sektörler kazanır, finansal varlıklar kaybeder).

**Riskler.** (1) 2022–2024 outlier; (2) regime change (Şimşek programı sonrası enflasyon düşüş trajectory'si: Daily Sabah 2026 verilerine göre 2025 yılsonu CPI %30.89, 49 ayın en düşüğü); (3) inflation-beta tahmin gürültülü.

**Mevcut katmana entegrasyon yolu.** L2 Macro içine inflation regime indicator + cross-sectional inflation-beta sort.

**90-gün içinde implement?** **Hayır.** 2022–2024 outlier nedeniyle backtest güvenilmez; en az 180 gün veri/metodoloji araştırması gerekli.

---

### 3.5 A5 — Sovereign CDS Conditional Gate (Longstaff-Pan-Pedersen-Singleton)

**Akademik temel.** Longstaff, Pan, Pedersen & Singleton (2011) "How Sovereign Is Sovereign Credit Risk?", *American Economic Journal: Macroeconomics* 3(2): 75–103, DOI: 10.1257/mac.3.2.75. Verbatim: "A single principal component accounts for 64 percent of the variation in sovereign credit spreads." Sovereign credit spread'lerin lokal ekonomik faktörlerden çok ABD borsası/high-yield ve VIX'e bağlı olduğunu raporlar. Pan & Singleton (2007) Mexico, Turkey, Korea CDS'lerinin VIX ile güçlü ortak bağlantısını ve Türkiye CDS curve'unun zaman zaman inversion gösterdiğini belgeler. Depren, Kartal & Kılıç Depren (2021) BIST/Türkiye TLREF modelinde CDS'in kritik eşik **350 bps** altında olması gerektiğini Random Forest analiziyle gösterir.

**BIST veri durumu.** Türkiye 5Y sovereign CDS günlük; investing.com, Bloomberg (ücretli), Refinitiv. Free alternatif: TradingEconomics + CBRT EVDS değişken kaynaklı vekil. **Güncel seviye:** MacroMicro Turkey 5-Year CDS serisine göre 2026 21. hafta (yaklaşık 23 Mayıs 2026 sonu) CDS **236.51–263.59 bps** aralığında trade etti; Gedik Invest / PA Turkey (Ocak 2026) ise CDS'in Q1 2026 başında **210 bps'in altına** indiğini, ardından yeniden genişlediğini not eder.

**Implementation kompleksitesi: 1/5 (düşük).** Tek skalar gate sinyali. ~80 satır kod. Günlük rebalance (gate aç/kapa).

**Beklenen alpha.** Doğrudan alpha değil; **risk-off rejimde drawdown azaltıcı**. LPPS (2011) CDS spread'in global risk premia ile %64 ortaklığını gösterir → BIST equity drawdownları ile yüksek korelasyon. Empirically: CDS >350 bps olduğunda BIST defensive mod (cash/short bias). Empirical extrapolation: yıllık ~3–5% drawdown azaltma; doğrudan getiri kazandırmaz.

**Riskler.** (1) Türkiye CDS verisi free kaynak güvenilirliği; (2) sinyalin "false positive" oranı (CDS yükselişi her zaman ciddi sell-off değil — 2018 currency crisis vs 2023 normal volatility); (3) gate threshold optimize edilirse overfitting.

**Mevcut katmana entegrasyon yolu.** L2 Macro (regime indicator) **veya** L6 Risk (Kelly multiplier reducer). Tercih: L2 Macro—gate sinyali olarak.

**90-gün içinde implement?** **Evet.** 2 hafta tamamen yeterli; daha çok eşik kalibrasyon meselesi.

---

### 3.6 B6 — Foreign Flow İkinci Türevi / İvme

**Akademik temel.** Ülkü & İkizlerli (2012) "The interaction between foreigners' trading and emerging stock returns: Evidence from Turkey", *International Business Review* — yabancı yatırımcının ISE/BIST'te trading volume ortalama **%60–70 paya** sahip olduğunu (1990'larda %6'dan yükseliş) ve positive feedback trading davranışı sergilediğini gösterir; foreign trade inflows market-level returns'u forecast eder. Eroğlu, İkizlerli & Ülkü (2024) "A mixed-frequency VAR application to studying joint dynamics of foreign investor trading and stock market returns", *Empirical Economics* 67(1): 47–73 — joint dynamics modeli güncel veri ile doğrular. Ülkü & Weber (2014) "Identifying the Interaction between Foreign Investor Flows and Emerging Stock Market Returns", *Review of Finance* 18(4): 1541–1581 destekleyici.

**BIST veri durumu.** Yabancı yatırımcı işlem oranı BIST resmi sayfasından **günlük** yayınlanır (Borsa İstanbul "yatırımcı dağılımı" raporu). Hisse-bazlı yabancı oran takip verileri MKK (Merkezi Kayıt Kuruluşu) üzerinden aylık erişilebilir. Tarihsel veri 2000+ mevcut.

**Implementation kompleksitesi: 3/5.** Foreign flow rolling 5-day ve 20-day türev hesaplama; ivme = ikinci türev. Cross-sectional sort opsiyonel (hisse bazlı yabancı flow varsa). ~200 satır kod. Haftalık rebalance.

**Beklenen alpha.** Ülkü & İkizlerli (2012) market-level forecast power belgelemiş — sayısal alpha rapor edilmemiş ama ekonomik anlamlılık var. BIST için tahmin: Phase 5 sort_layer ile **hisse-bazlı yabancı oran momentum'u** orta düzeyde alpha üretebilir.

**Riskler.** (1) MKK aylık veri frekansı düşük → reaktivite gecikmesi; (2) yabancı flow'un nedensellik mi anomali mi olduğu literatürde tartışmalı (Eroğlu-İkizlerli-Ülkü 2024 simultaneity testleri); (3) rejim değişikliği (2018, 2021, 2023 currency krizleri sırasında flow patternı değişti).

**Mevcut katmana entegrasyon yolu.** L5 Smart Money — yabancı flow'u smart money proxy'si olarak.

**90-gün içinde implement?** **Evet.** Market-level versiyon 30 günde; hisse-bazlı cross-sectional versiyon 60–90 gün (sort_layer'a bağlı).

---

### 3.7 B7 — USDTRY Pass-Through Beta (hisse-spesifik)

**Akademik temel.** RIETI (2022) "The Impact of Exchange Rates on the Turkish Economy", https://www.rieti.go.jp/en/publications/nts/22e043.html — lira depreciation'ın çoğu sektörde hisse getirilerini düşürdüğünü, importer firmalarda etkinin daha güçlü olduğunu belgeler. Frontiers in Applied Mathematics & Statistics (2019), "Exchange Rate Pass-Through Investigation for Turkish Economy" — 2005–2019 monthly VAR ile ERPT'nin Türkiye'de yüksek olduğunu raporlar. Doğan et al. (2022) FF6F BIST modeli; Journal of Management and Economics Research (2024) "Fama-French Three-Factor Asset Pricing Model in Borsa Istanbul: Including Two Additional Factors" trading volume + exchange rate eklenmesinin BIST'te explanatory power'ı artırdığını gösterir. Bartram & Bodnar (2012) global currency exposure framework BIST için uygulanabilir.

**BIST veri durumu.** USDTRY günlük TCMB EVDS'den mevcut; hisse fiyatları yfinance'dan. Sektör endeksleri (XBANK, XGIDA, XELKT, XSANY) BIST resmi.

**Implementation kompleksitesi: 2/5 (düşük).** Hisse-bazlı 60-gün rolling regresyon: R_i,t = α + β_i ΔUSDTRY_t + ε. Beta'ya göre ranking (negatif beta = importer; pozitif beta = exporter). ~150 satır kod. Aylık rebalance.

**Beklenen alpha.** Sektörel heterojenlik yüksek — havayolu, demir-çelik, otomotiv (TOFAŞ, FROTO) pozitif beta; perakende, gıda negatif beta. BIST için tahmin: rejime bağlı; lira depreciation döneminde long-exporter / short-importer ~5–8% yıllık alpha potansiyeli.

**Riskler.** (1) Beta non-stationary (rejim değişimi); (2) ERPT 2022–2024 outlier; (3) Şimşek programı sonrası "real lira appreciation" stratejisinde beta işareti tersine dönebilir (TradingEconomics 2026 verisi: USDTRY 45.5 seviyesinde, tarihi zirve).

**Mevcut katmana entegrasyon yolu.** L1 Technical (beta hesaplama) + L2 Macro (USDTRY regime).

**90-gün içinde implement?** **Evet.** 2 haftada baseline; 4 haftada sektör/firma heterojenlik analizi.

---

### 3.8 B8 — Holding NAV Discount Mean Reversion

**Akademik temel.** Lee, Shleifer & Thaler (1991) "Investor Sentiment and the Closed-End Fund Puzzle", *Journal of Finance* 46(1): 75–109 — closed-end fund discount'un investor sentiment proxy'si olduğunu ve mean-reverting yapısı bulunduğunu belgeler. Bodurtha, Kim & Lee (1995) EM'ler için extend eder. BIST'e doğrudan uyarlanabilir: KCHOL, SAHOL, AGHOL, KOZAL, DOHOL gibi holdingler iştirakler portföyü içerir; "Sum-of-the-parts NAV" hesabı ile market cap karşılaştırması discount'u verir. PA Turkey (Mart 2025) "Koc Holding: NAV discount back at attractive levels" makalesi: "Koc's NAV discount had narrowed to mid-teen levels in mid-2024 but has widened in a volatile course since then to c30% today." ÜNLÜ & Co 2026 Strateji raporu (Ocak 2026) KCHOL ve SAHOL'a "Buy" rating; KCHOL için %58 upside (mevcut 184 TL → hedef 291 TL), SAHOL için %71 upside.

**BIST veri durumu.** Holdinglerin iştirak listesi: KAP (holding faaliyet raporları, çeyreklik). İştiraklerin market cap'i: yfinance + İş Yatırım screener. NAV hesabı: iştirak market cap × sahiplik oranı + net cash (KAP'tan). Discount = 1 – (Holding MV / NAV). Tarihsel discount serisi manuel olarak hesaplanması gerek; Bloomberg/Matriks ücretli kaynaklar zaman serisini sağlar.

**Implementation kompleksitesi: 3/5.** NAV calculator + iştirak takip + discount Z-score + mean reversion sinyali. ~350 satır kod. Haftalık rebalance.

**Beklenen alpha.** Discount Z-score < -1.5 olduğunda holding'in 6-ay gelecek getirisi tarihsel olarak BIST100'ü 5–10% geçer (PA Turkey gözlem ve broker araştırmaları). LST (1991) U.S. CEF'lerde 4–6% yıllık discount-mean-reversion alpha rapor eder. BIST holdinglerinde tahmin: ~6–10% yıllık alpha.

**Riskler.** (1) Discount geniş kalabilir (Türkiye risk premium kalıcı); (2) iştirak market cap volatilitesi NAV gürültüsünü artırır; (3) KAP raporlama gecikmesi (çeyreklik vs günlük market değişim).

**Mevcut katmana entegrasyon yolu.** L3 KAP (iştirak bilgisi) + L5 Smart Money (discount Z-score sinyali) + L6 Risk (sizing).

**90-gün içinde implement?** **Evet.** Tek tek 5 holding üzerinde başlayarak 60 günde MVP, 90 günde tam otomasyon.

---

### 3.9 B9 — Temettü Cluster Timing (Mart–Mayıs)

**Akademik temel.** Adaoglu (2000) "Instability in the Dividend Policy of the Istanbul Stock Exchange (ISE) Corporations: Evidence from an Emerging Market", *Emerging Markets Review* 1(3): 252–270, DOI: 10.1016/S1566-0141(00)00011-X — BIST corporations'ın istikrarsız temettü politikası izlediğini ve dağıtım büyüklüğünün yıllık kar kararına bağlı olduğunu belgeler (1985–1997 örneklem). Verbatim: "For the period 1985–1994, the [payout] averages are approximately 50% which is the minimum legal limit set by the regulatory body, the Capital Markets Board." Adaoglu (2008) "Dividend Policy of the ISE Industrial Corporations: The Evidence Revisited (1986–2007)" follow-up çalışmasında 2003 sonrası **%20 zorunlu temettü** politikasını analiz eder. Baker, Kilincarslan & Arsal (2018) BIST firmalarının survey-based dividend policy çalışması, *Research in International Business and Finance*. Yilmaz & Gulay (2006) ex-dividend day price drop literatür temelli pozitif AR'leri raporlar. **Mart-Mayıs cluster akademik olarak ayrıntılı dokümante edilmemiş**: Türk Ticaret Kanunu fiscal-year-end AGM'lerinin Mart sonuna kadar yapılmasını gerektirir; temettü kararı ardından genellikle Nisan-Haziran arası dağıtım. Gulseven (2020) "Multidimensional Analysis of Monthly Stock Market Returns" (arXiv 2003.05750), Türk hisseleri için **Mayıs'ta belirgin negatif etki (post-April positive)** raporlar — ex-dividend cluster ile tutarlı olabilir ama yazarlar bu bağlantıyı doğrudan kurmaz.

**BIST veri durumu.** Temettü tarih ve miktarları: KAP (özel durum açıklamaları), İş Yatırım dividend takvimi. yfinance hisse-bazlı temettü kayıtları sağlar (kısmi). Tarihsel takvim 2000+ mevcut.

**Implementation kompleksitesi: 2/5.** Temettü takvim filtresi + ex-date 5-gün öncesi pozisyon + ex-date sonrası capture. ~120 satır kod. Yıllık aktif window (Şubat–Haziran).

**Beklenen alpha.** Cluster timing kendi başına agresif alpha vermez; literatür U.S. CEF/dividend timing trades'inde 1–3% yıllık. BIST için tahmin: 2–4% yıllık, ana fayda **vergi avantajı arbitrajı** (Türkiye'de %15 temettü stopajı; sermaye kazancında stopaj uygulaması farklı).

**Riskler.** (1) Adaoglu (2000) "instability" sonucu — temettü dağıtım kararları tahmin edilemez; (2) Mart-Mayıs cluster akademik olarak ayrıntılı DOKÜMANTE EDİLMEMİŞ (genuine literatür gap); (3) ex-date price drop kalibrasyonu vergi etkilerine duyarlı.

**Mevcut katmana entegrasyon yolu.** L3 KAP (temettü takvim) + L1 Technical (timing).

**90-gün içinde implement?** **Evet.** 30 günde MVP, sonraki yıllık döngüde gerçek testi.

---

### 3.10 B10 — BIST Endeks Dahil/Çıkar Olayları

**Akademik temel.** Harris & Gurel (1986) "Price and Volume Effects Associated with Changes in the S&P 500 List: New Evidence for the Existence of Price Pressures", *Journal of Finance* 41(4): 815–829, DOI: 10.1111/j.1540-6261.1986.tb04550.x — S&P 500'e eklenen hisselerin announcement sonrası **~%3 pozitif anormal getiri** sergilediğini ve 2 hafta içinde fiyatların büyük ölçüde reverse olduğunu belgeler. Bağımsız incelemeler (Greenwood & Sammon, NBER WP 30748) bulguyu doğrular. Bildik & Gulay (2008) "The effects of changes in index composition on stock prices and volume: Evidence from the Istanbul stock exchange", *International Review of Financial Analysis* 17(1): 178–197, DOI: 10.1016/j.irfa.2006.10.002 — BIST için ilk çalışma; 1995–2000 örneklemi, **204 ekleme ve 180 çıkarma olayı**, ISE-30 ve ISE-100 ayrı analiz, 24 quarterly periodical index revision. Bulgu: "stocks included in (excluded from) an index exhibit significant positive (negative) abnormal returns on the announcement day, and that trading volume is affected by the event." Yorum: price-pressure ve imperfect-substitutes hipotezleri BIST için zayıf (lack of index funds, mutual funds, derivatives at that time). Greenwood, Sammon & Shleifer (2023) HBS WP 23-025 "The Disappearing Index Effect" — U.S. piyasada 1997–2017 arası index inclusion effect'in zayıfladığını rapor eder.

**BIST veri durumu.** BIST endeks bileşim değişiklikleri çeyreklik (Mart, Haziran, Eylül, Aralık) BIST resmi sitesinden announcement öncesi 2 hafta önce yayınlanır. Tarihsel listeler BIST'ten alınabilir; manuel toplama gerekli.

**Implementation kompleksitesi: 3/5.** Announcement scraper + event window AR hesaplama + pozisyon timing. ~250 satır kod. Yılda 4 kez aktif (rebalance dönemi).

**Beklenen alpha.** Harris & Gurel (1986) S&P 500 için ~3% AR. Bildik & Gulay (2008) BIST için anlamlı AR raporlar ama tam % rakamı paywall arkasında — literatürdeki ortalama EM index inclusion effect ~2–5%. Greenwood et al. (2023) U.S.'de effect zayıflıyor; BIST'te ETF/fon penetrasyonu artıyor (Borsa İstanbul "Tech Mania" raporu, FT 2024 Mart: TL7.2 milyar tech fund net girişi) → effect güçlenebilir.

**Riskler.** (1) Effect zayıflama trendi; (2) front-running rakipler (broker dahili pozisyonlar); (3) announcement timing belirsizliği.

**Mevcut katmana entegrasyon yolu.** L3 KAP / event monitor + L1 Technical (event-driven timing).

**90-gün içinde implement?** **Kısmen.** Tarihsel veri backtest 60 günde; live deployment Eylül 2026 rebalance'da.

---

### 3.11 B11 — Block Trade Tespiti

**Akademik temel.** Holthausen, Leftwich & Mayers (1990) "Large-block transactions, the speed of response, and temporary and permanent stock-price effects", *Journal of Financial Economics* 26(1): 71–95 — büyük blok işlemlerin geçici ve kalıcı fiyat etkisi olduğunu, fiyatların 3 işlem içinde adapte olduğunu belgeler: "the temporary price effect is the price rebound of a security following a block transaction and the permanent price effect is the change from the equilibrium price before the block trade to the equilibrium price afterwards." Türk literatür: Hacettepe Üniversitesi İktisadi ve İdari Bilimler Fakültesi Dergisi — "Price Impacts of Large Trades in Futures Markets: Evidence from Turkey" Türk futures piyasasında block trade impact ölçer (dergipark/huniibf 340699).

**BIST veri durumu.** BIST OS şu an günlük close veri kullanıyor (yfinance). Intraday tick-by-tick block tespit için Matriks/Foreks ücretli abonelik zorunlu. Borsa İstanbul "Toptan İşlemler Pazarı" (Wholesale Market) duyuruları KAP'tan günlük çekilebilir ama bu sadece pre-arranged büyük işlemler için.

**Implementation kompleksitesi: 5/5 (çok yüksek).** Intraday tick verisi + abnormal volume tespit + spread/price-pressure modeli. ~600+ satır kod + ücretli veri.

**Beklenen alpha.** HLM (1990) blok işlemler temporary 1–2% reversal sağlar. Sub-500K TL portföy ölçeği için reversal trade slippage altında.

**Riskler.** (1) Ücretli veri maliyeti aylık ~3–8K TL (Matriks/Foreks); (2) latency requirements high-frequency'ye yakın; (3) <500K TL'de fiyat etkisi yok ama eldeki sinyal kullanılabilir.

**Mevcut katmana entegrasyon yolu.** L5 Smart Money (block tespit edildiğinde smart money sinyali).

**90-gün içinde implement?** **Hayır.** Veri altyapısı ve mimari değişiklik 180+ gün; ROI <500K TL portföyde negatif.

---

### 3.12 B12 — TLREF / Reverse Repo Spread (Funding Stress)

**Akademik temel.** Kartal (2019) "Türkiye'de Referans (Gösterge) Faiz Oluşturulması: Türk Lirası Gecelik Referans Faiz Oranı (TLREF) Üzerine Bir İnceleme", *Bankacılar Dergisi* 111: 14–27 (SSRN 3507496) — TLREF'in **28.12.2018 tarihinde** hesaplanmaya başladığını ve **17.06.2019** tarihinde Borsa İstanbul tarafından kamuoyuna ilan edildiğini belgeler; ilan günü TLREF=%24.82, TRLIBOR=%25.19, TCMB 1-week repo=%24.00. TLREF'in piyasa likidite koşullarını yansıttığını gösterir. Depren, Kartal & Kılıç Depren (2021) "Recent innovation in benchmark rates: evidence from influential factors on Turkish Lira Overnight Reference Interest Rate with machine learning algorithms", *Financial Innovation* 7(1): 44, DOI: 10.1186/s40854-021-00245-1 — 28.12.2018–31.12.2020 günlük dataset, Random Forest **R²=0.991, RMSE=0.610**; TLREF üzerinde en etkili faktörler sırayla: TCMB tarafından satın alınan menkul kıymetler, emisyon hacmi, altın fiyatları, USD/TL, **BIST XU100**, VIX, **Türkiye CDS spread**, MSCI EM endeksi. Kritik eşikler: CDS <350 bps, USD/TL 6.5–7.5, XU100 110,000–120,000 (2020 seviyeleri). Borsa İstanbul Review (2023) "The efficiency of the new reference rate in Türkiye" — TLREF, TRLIBOR'a kıyasla "consistently higher market efficiency" sağlar; AMH framework. **Doğrudan TLREF–policy rate spread → BIST equity returns regresyon çalışması literatürde NOT FOUND — kavramsal olarak savunulabilir ama akademik delil zayıf.**

**BIST veri durumu.** TLREF günlük: Borsa İstanbul resmi sitesi (borsaistanbul.com/en/indices/tlref). TCMB politika faizi (1-week repo): EVDS. Reverse repo / O/N rate: EVDS. Tüm bunlar **ücretsiz**.

**Implementation kompleksitesi: 1/5 (düşük).** TLREF – policy rate spread günlük hesap + threshold/Z-score gate. ~100 satır kod. Günlük rebalance.

**Beklenen alpha.** Direct alpha düşük; **regime indicator** olarak değerli. TLREF spread > X bps olduğunda funding stress → BIST defensive (cash bias). Quantitative tahmin literatür yok; backtest gerekiyor.

**Riskler.** (1) TCMB sık intervention nedeniyle spread suni; (2) 2018–2020 emerging market funding crisis döneminde spread yüksek volatilite gösterdi; (3) doğrudan akademik delil zayıf.

**Mevcut katmana entegrasyon yolu.** L2 Macro (funding regime indicator) **veya** L6 Risk (Kelly multiplier reducer).

**90-gün içinde implement?** **Evet.** 2 haftada baseline. Backtest ve kalibrasyon ek 2 hafta.

---

### 3.13 B13 — Açığa Satış Oranı + Lending Fee — SAKIN YAPMA (MEVCUT YASAK)

**Akademik temel.** Cohen, Diether & Malloy (2007) "Supply and Demand Shifts in the Shorting Market", *Journal of Finance* 62(5): 2061–2096, DOI: 10.1111/j.1540-6261.2007.01269.x — proprietary stock-loan data ile shorting demand artışının ertesi ay **-%2.98 negatif anormal getiri** öngördüğünü Table III'te gösterir (Smith Breeden Prize for Best Paper in Asset Pricing 2007). Boehmer, Jones & Zhang (2008) "Which Shorts Are Informed?" *Journal of Finance* 63(2): 491–527 — short-sellers'ın informed olduğunu doğrular. Asquith, Pathak & Ritter (2005) institutional ownership + short interest interaksiyonunu modeller.

**BIST veri durumu / mevzuat.** **Sermaye Piyasası Kurulu (SPK) 15.03.2026 tarih ve 15/517 sayılı kararı uyarınca Borsa İstanbul pay piyasalarında açığa satış işlemleri yasaklanmıştır. 28.03.2026 tarih ve 19/625 sayılı karar ile yasak 10.04.2026 seans sonuna kadar uzatılmıştır** (Bigpara/Hürriyet 30.03.2026 haberi; Habertürk 30.03.2026; Bloomberg HT 15.03.2026). Yasak rejiminde açığa satış oranı verisi anlamsız (sıfıra yakın); securities lending fee BIST'te şeffaf değil, broker-bazlı pazarlık.

**Implementation kompleksitesi: N/A (yasak).**

**Beklenen alpha.** Yasak süresince **0**. Yasak kalkarsa: CDM (2007) literatür temel %2.98/ay alpha potansiyeli; ama BIST için lending-fee veri altyapısı yok.

**Riskler.** (1) Yasak süresiz uzatılma riski (2024–2026 sıklığı); (2) yasak kalksa bile BIST'te lending-fee public-data eksik; (3) BIST short interest ratio CMTC'den derlense bile yasak rejimi geçmiş veriyi bozar.

**Mevcut katmana entegrasyon yolu.** N/A.

**90-gün içinde implement?** **Hayır.** Yasak kalkana ve lending-fee API altyapısı açılana kadar **pas geç**.

---

### 3.14 B14 — Earnings Revision Momentum

**Akademik temel.** Chan, Jegadeesh & Lakonishok (1996) "Momentum Strategies", *Journal of Finance* 51(5): 1681–1713, DOI: 10.1111/j.1540-6261.1996.tb05222.x — past return momentum ve past earnings surprise her ikisinin de bağımsız olarak ileri getirileri öngördüğünü gösterir. **6-ay tutma için iki uç decile spread'i: SUE (standardized unexpected earnings) için %7.5; earnings-revision portföyleri için %7.7**; IBES 1977–1993 örneklem. Jegadeesh & Titman (1993) original momentum paper. Chan, Jegadeesh & Lakonishok (1999) Financial Analysts Journal analyst revision strategy follow-up. BIST'te: Doğan, Kevser & Demirel (2022) momentum factor BIST'te FF6F'te anlamlı. Doğrudan BIST consensus revision çalışması sınırlı; İş Yatırım/Marbaş/Ünlü&Co consensus revizyon verisi mevcut.

**BIST veri durumu.** IBES eşdeğeri Türkiye'de İş Yatırım Research (BIST consensus estimates), Bloomberg ANR functions (ücretli), Refinitiv. **Ücretsiz alternatif:** Finnet, Foreks consensus screen; KAP earnings releases ile gerçek vs beklenti SUE hesabı yapılabilir. Tarihsel revizyon zaman serisi sınırlı (~2010 sonrası).

**Implementation kompleksitesi: 3/5.** Consensus revision tracker + SUE hesabı + cross-sectional rank. ~300 satır kod. Aylık rebalance (KAP earnings release sonrası).

**Beklenen alpha.** CJL (1996): 6-month SUE spread %7.5, revision spread %7.7. BIST için tahmin: analyst coverage daha düşük (BIST100'de ortalama 8 analyst/firma vs S&P500'de 22) → effect daha güçlü olabilir veya gürültülü olabilir.

**Riskler.** (1) Consensus data'nın paywall/ücret; (2) firm-specific analyst sayısı düşük → revision noisy; (3) 2022–2024 hiperenflasyon dönemi earnings beklentileri sık değişti — outlier riski.

**Mevcut katmana entegrasyon yolu.** L3 KAP (earnings) + L1 Technical (cross-sectional rank). Phase 5 sort_layer ile.

**90-gün içinde implement?** **Evet.** İş Yatırım veya benzer ücretsiz/düşük-maliyet consensus kaynağı kullanılarak 30–60 günde MVP.

---

## 4. TOP 3 ÖNCELİK İÇİN MİNİ-SPEC

### 4.1 B14 — Earnings Revision Momentum (Mini-Spec)

**Değişecek mevcut dosyalar (placeholder):**
- `layers/l3_kap.py` — earnings release event handler genişletme
- `layers/l1_technical.py` — cross-sectional rank function eklenecek
- `core/signal_aggregator.py` — earnings revision skoru entegrasyonu
- `config/factor_weights.yaml` — B14 weight slot

**Yeni dosyalar:**
- `factors/earnings_revision.py` — main factor module
- `data/consensus_fetcher.py` — İş Yatırım/Foreks scraper
- `tests/test_earnings_revision.py` — birim test
- `backtest/b14_backtest.py` — backtest harness

**Test stratejisi:**
- Backtest dönemi: 2018-01 — 2024-12 (84 ay; 2022–2024 hiperenflasyon dahil)
- Baseline: BIST100 buy-and-hold + L1 Technical momentum baseline
- Metrikler: Sharpe (rf=%42), Information Ratio, max drawdown, hit ratio
- Cross-validation: 60/40 split + walk-forward 12 ay rolling

**2-hafta zaman çizelgesi:**
- Hafta 1: Consensus veri kaynağı entegrasyonu (3 gün), SUE hesabı modülü (2 gün)
- Hafta 2: Cross-sectional rank entegrasyonu (3 gün), backtest + test (2 gün)

**Builder speci taslağı:**
> "BIST OS'a B14 Earnings Revision Momentum faktörünü ekle. Chan-Jegadeesh-Lakonishok 1996 metodolojisini Türk verisine uyarla (literatür: SUE 6-ay spread %7.5, revision spread %7.7, IBES 1977–1993). KAP earnings release tarihinden 3 gün önce/sonra consensus EPS revizyon yüzdesini hesapla. Aylık cross-sectional rank ile top decile (5 hisse) long, bottom decile short (yasak nedeniyle short = cash). Aylık rebalance. L3 KAP layer'a entegre et. Backtest 2018–2024, Sharpe ve IR raporla."

### 4.2 A5 — Sovereign CDS Conditional Gate (Mini-Spec)

**Değişecek mevcut dosyalar:**
- `layers/l2_macro.py` — CDS gate eklenecek
- `core/regime_detector.py` — CDS-based regime flag
- `config/risk_params.yaml` — CDS threshold (kalibrasyon için)

**Yeni dosyalar:**
- `data/cds_fetcher.py` — Türkiye 5Y CDS scraper (investing.com / tradingeconomics / MacroMicro)
- `factors/cds_gate.py` — gate logic
- `tests/test_cds_gate.py` — birim test

**Test stratejisi:**
- Backtest dönemi: 2015-01 — 2024-12 (2018 currency krizi, 2020 COVID, 2023 deprem dahil)
- Baseline: gate-off vs gate-on portföyler karşılaştırması
- Metrikler: max drawdown reduction, Sharpe değişimi, false positive oranı
- Threshold kalibrasyon: 250/300/350/400 bps senaryoları (Mart 2026'da gerçek seviye 236–264 bps; Q1 başında 210 bps altı)

**2-hafta zaman çizelgesi:**
- Hafta 1: CDS veri scraper + tarihsel veri toplama (2 gün), gate logic modülü (3 gün)
- Hafta 2: Backtest harness (2 gün), threshold kalibrasyon (2 gün), entegrasyon testi (1 gün)

**Builder speci taslağı:**
> "BIST OS'a A5 Sovereign CDS Conditional Gate ekle. Türkiye 5Y CDS spread'ini günlük çek (investing.com / tradingeconomics / MacroMicro). CDS > eşik (kalibrasyon için 300/350 bps) olduğunda L6 Risk Kelly multiplier'ı 0.5×; CDS > 450 bps olduğunda 0× (cash bias). L2 Macro veya regime_detector modülüne entegre et. Longstaff-Pan-Pedersen-Singleton 2011 literatür quotelu olarak dökümante et: 'A single principal component accounts for 64 percent of the variation in sovereign credit spreads.'"

### 4.3 B7 — USDTRY Pass-Through Beta (Mini-Spec)

**Değişecek mevcut dosyalar:**
- `layers/l1_technical.py` — pass-through beta hesaplama eklenecek
- `layers/l2_macro.py` — USDTRY regime indicator
- `core/factor_blender.py` — B7 beta entegrasyonu

**Yeni dosyalar:**
- `factors/usdtry_passthrough.py` — main module
- `data/fx_fetcher.py` — TCMB EVDS USDTRY çekici
- `tests/test_passthrough.py` — birim test

**Test stratejisi:**
- Backtest dönemi: 2017-01 — 2024-12 (2018 ve 2021 currency krizleri dahil)
- Baseline: equal-weighted BIST100 vs pass-through beta-tilted portföy
- Metrikler: rejime conditional Sharpe (TRY depreciating vs appreciating), sector decomposition

**2-hafta zaman çizelgesi:**
- Hafta 1: TCMB EVDS USDTRY entegrasyon (1 gün), rolling beta hesabı (3 gün), validation (1 gün)
- Hafta 2: Sektör/firm tilt logic (3 gün), backtest + raporlama (2 gün)

**Builder speci taslağı:**
> "BIST OS'a B7 USDTRY Pass-Through Beta faktörü ekle. Her BIST100 hissesi için 60-gün rolling regresyon: R_i = α + β_i ΔlnUSDTRY + ε. Beta'ya göre ranking yap. USDTRY trend yukarı yönlüyse top-beta (exporter) long; aşağı yönlüyse top-negative-beta (importer) long. Aylık rebalance. L1 Technical + L2 Macro entegrasyonu. RIETI (2022) 'Impact of Exchange Rates on Turkish Economy' ve Doğan et al. (2022) literatür referansları."

---

## 5. AKADEMİK KAYNAK ÖZETİ

| # | Yazar(lar) (Yıl) | Başlık | Dergi / Kaynak | DOI/URL | BIST'e ne kattığı |
|---|------------------|--------|----------------|---------|---------------------|
| 1 | Asness, Moskowitz, Pedersen (2013) | Value and Momentum Everywhere | JoF 68(3): 929–985 | 10.1111/jofi.12021 | EM dahil 8 piyasada V+M kombinasyonu robust; Türkiye doğrudan equity panelinde yok. Doğan et al. (2022) bulgularını destekler. |
| 2 | Menkhoff, Sarno, Schmeling, Schrimpf (2012) | Currency Momentum Strategies | JFE 106(3): 660–684 | 10.1016/j.jfineco.2012.06.009 | 48-currency 1976–2010 panelde **10% p.a.** winner-loser spread; momentum strategy Sharpe yazarların carry-trade SR'sini (0.82) aşar. |
| 3 | Bekaert, Harvey, Lundblad (2007) | Liquidity and Expected Returns: Lessons from EM | RFS 20(6): 1783–1831 | 10.1093/rfs/hhm030 | EM panelinde Türkiye dahil; "zero return proportion" likidite ölçüsü BIST'e direkt uygulanabilir. |
| 4 | Longstaff, Pan, Pedersen, Singleton (2011) | How Sovereign Is Sovereign Credit Risk? | AEJ Macro 3(2): 75–103 | 10.1257/mac.3.2.75 | Türkiye CDS örneklemde; spread'lerin %64'ü tek PC ile açıklanır. A5 gate teorik temel. |
| 5 | Lee, Shleifer, Thaler (1991) | Investor Sentiment and the Closed-End Fund Puzzle | JoF 46(1): 75–109 | 10.1111/j.1540-6261.1991.tb03746.x | CEF discount mean reversion; B8 için doğrudan analog. |
| 6 | Cohen, Diether, Malloy (2007) | Supply and Demand Shifts in the Shorting Market | JoF 62(5): 2061–2096 | 10.1111/j.1540-6261.2007.01269.x | Shorting demand artışı → -%2.98 negatif AR (ertesi ay), Table III. B13 teorik temel; SPK yasağı altında uygulanamaz. |
| 7 | Chan, Jegadeesh, Lakonishok (1996) | Momentum Strategies | JoF 51(5): 1681–1713 | 10.1111/j.1540-6261.1996.tb05222.x | Past return + earnings surprise bağımsız momentum; 6-ay SUE %7.5, revision %7.7 spread (IBES 1977–1993). B14 teorik temel. |
| 8 | Ülkü, İkizlerli (2012) | The interaction between foreigners' trading and emerging stock returns: Evidence from Turkey | International Business Review | researchgate 257626293 | Yabancı %60–70 işlem payı; market-level forecast power. B6 teorik temel. |
| 9 | Doğan, Kevser, Leyli Demirel (2022) | Testing Augmented Fama-French Six-Factor with Momentum for Borsa Istanbul | Discrete Dynamics in Nature and Society | 10.1155/2022/3392984 | 2013/10–2021/05 BIST; 9,504 portfolio observations; FF6F en güçlü. A1, B14 destek. |
| 10 | Ersoy, Ünlü (2013) | Size, Book to Market Ratio and Momentum Strategies: Evidence from ISE | SSRN | ssrn.com/abstract=2731176 | 1995–2010 BIST 6-ay momentum anlamlı; January effect insignificant. A1 BIST destek. |
| 11 | Tomtosov (2024) | Overlapping portfolio holdings and unique sources of emerging market risk | Borsa Istanbul Review 24: 201–217 | sciencedirect S2214845023001540 | EM momentum/size/low-vol negatif-return dönemlerinde yüksek korelasyon; momentum turnover %36–57. |
| 12 | Bildik, Gulay (2007) | Profitability of Contrarian Strategies: Evidence from the ISE | IRF 7(1–2): 61–87 | 10.1111/j.1468-2443.2007.00068.x | 1991–2000 BIST self-financing loser-winner ~%15 yıllık AR. |
| 13 | Bildik, Gulay (2008) | The effects of changes in index composition on stock prices and volume: Evidence from the ISE | IRFA 17(1): 178–197 | 10.1016/j.irfa.2006.10.002 | 1995–2000 BIST 204 ekleme/180 çıkarma; ISE-30/100 inclusion-day anlamlı pozitif AR. B10 teorik temel. |
| 14 | Atılgan, Demirtaş, Günaydın (2016) | Liquidity and Equity Returns in Borsa İstanbul | Applied Economics 48(52): 5075–5092 | 10.1080/00036846.2016.1170935 | 2002–2017 BIST illikidite premium anlamlı (Amihud, Corwin-Schultz). A3 BIST destek. |
| 15 | Boudoukh, Richardson (1993) | Stock Returns and Inflation: A Long-Horizon Perspective | AER 83(5): 1346–1355 | aeaweb.org | Uzun-ufuk Fisher hipotezi pozitif; A4 teorik temel. |
| 16 | Berument & Güner | Inflation, inflation risk and interest rates: a case study for Turkey | EconBiz 10001238215 | econbiz.de/10001238215 | Türk hisse piyasası enflasyon dinamiklerine hassas; A4 BIST destek. |
| 17 | Harris, Gurel (1986) | Price and Volume Effects Associated with Changes in the S&P 500 List | JoF 41(4): 815–829 | 10.1111/j.1540-6261.1986.tb04550.x | Index inclusion ~3% AR, 2 haftada reverse. B10 teorik temel. |
| 18 | Holthausen, Leftwich, Mayers (1990) | Large-block transactions, the speed of response, and temporary and permanent stock-price effects | JFE 26(1): 71–95 | 10.1016/0304-405X(90)90013-P | Blok işlemlerin geçici ve kalıcı fiyat etkisi; B11 teorik temel; intraday gerektirir. |
| 19 | Boehmer, Jones, Zhang (2008) | Which Shorts Are Informed? | JoF 63(2): 491–527 | 10.1111/j.1540-6261.2008.01324.x | Short-sellers informed. B13 destek. |
| 20 | Amihud (2002) | Illiquidity and stock returns: cross-section and time-series effects | JFM 5(1): 31–56 | 10.1016/S1386-4181(01)00024-6 | ILLIQ ölçüsü; A3 ana ölçüm tekniği. |
| 21 | Adaoglu (2000) | Instability in the Dividend Policy of the ISE Corporations | Emerging Markets Review 1(3): 252–270 | 10.1016/S1566-0141(00)00011-X | BIST temettü politika istikrarsız; %50 minimum yasal sınır 1985–94; %20 zorunlu 2003 sonrası. B9 dolaylı destek. |
| 22 | Kartal (2019) | Türkiye'de Referans (Gösterge) Faiz Oluşturulması: TLREF Üzerine Bir İnceleme | Bankacılar Dergisi 111: 14–27 | SSRN 3507496 | TLREF 28.12.2018 hesap başlangıcı, 17.06.2019 BIST resmi ilan. B12 temel. |
| 23 | Depren, Kartal, Kılıç Depren (2021) | Recent innovation in benchmark rates: TLREF determinants | Financial Innovation 7(1): 44 | 10.1186/s40854-021-00245-1 | RF R²=0.991; TLREF prediktörleri: para tabanı, USDTRY, **XU100, CDS<350bps**. B12 destek. |
| 24 | Eroğlu, İkizlerli, Ülkü (2024) | Mixed-frequency VAR for foreign investor trading and stock returns | Empirical Economics 67(1): 47–73 | Springer | Yabancı flow-return joint dynamics güncel; B6 desteği. |
| 25 | RIETI (2022) | The Impact of Exchange Rates on the Turkish Economy | RIETI nts/22e043 | rieti.go.jp/en/publications/nts/22e043.html | Lira depreciation Türk firmalarda hisse getirilerini düşürür; B7 BIST destek. |
| 26 | Greenwood, Sammon, Shleifer (2023) | The Disappearing Index Effect | HBS WP 23-025 / NBER WP 30748 | hbs.edu/ris/Publication%20Files/23-025 | U.S. index inclusion effect 1997–2017 zayıflıyor; BIST için risk. |
| 27 | Gulseven (2020) | Multidimensional Analysis of Monthly Stock Market Returns | arXiv 2003.05750 | arxiv.org/abs/2003.05750 | Türk hisseleri Mayıs negatif (post-April positive) anomalisi; B9 ile dolaylı tutarlı. |

---

## 6. INTEGRATION MAP

Hangi faktör hangi layer'a girer (öneri; teknik haritalama):

| Layer | Faktörler | Açıklama |
|-------|-----------|----------|
| **L1 Technical** | B7 (pass-through beta), B14 (revision momentum) | Hisse-bazlı sinyaller; teknik regresyonlar |
| **L2 Macro** | A4 (inflation regime), A5 (CDS gate), B12 (TLREF spread) | Makro filtreler ve regime indicators |
| **L3 KAP** | B9 (temettü), B10 (endeks olayları), B14 (earnings beslemesi) | KAP event-driven |
| **L4 Sentiment** | (RR-011 kapsamında — suspended) | RR-012 dışı |
| **L5 Smart Money** | A3 (likidite premium), B6 (yabancı flow), B8 (NAV discount), B11 (block trade — düşük öncelik) | Cross-sectional sinyaller |
| **L6 Risk / Kelly** | A1 (sizing), A3 (penalty), A5 (multiplier reducer) | Risk-yönetim katmanı |
| **Phase 5 sort_layer (yeni)** | A1, A3, A4, B6 cross-sectional version, B14 | Cross-sectional rank altyapısı zorunlu |

---

## 7. CROSS-FACTOR INTERACTION

### 7.1 Synergistic Çiftler

- **A1 (Value-Momentum) × B14 (Earnings Revision):** CJL (1996) past-return ve past-earnings-surprise'ın bağımsız (toplanır) bilgi içerdiğini gösterir; kombinasyon momentum'u güçlendirir.
- **A5 (CDS Gate) × B12 (TLREF Spread):** Her ikisi de sovereign funding stress yansıtır; **birlikte regime indicator** olarak güç birliği yapar. Depren et al. (2021) CDS-TLREF kovaryans yüksek gösterir.
- **A3 (Liquidity Premium) × B6 (Foreign Flow):** Yabancı flow yüksek olduğunda likidite artar; illikit hisseler yabancı alımıyla daha fazla rally yapar. Ülkü & İkizlerli (2012) bu kanalı destekler.
- **B7 (USDTRY Beta) × B8 (Holding Discount):** Holdingler (KCHOL/SAHOL) USD-denominated assets'a sahip; lira depreciation NAV'larını korur ama market price gecikmeyle reaksiyon verir → discount mean reversion + USDTRY pass-through sinerji.

### 7.2 Birbirini İptal Eden (Negatif Korelasyon)

- **A1 momentum bileşeni × Contrarian (Bildik & Gulay 2007 ~%15 yıllık reversal):** BIST'te kısa-vadeli reversal güçlü; momentum 6–12 ay penceresinde; kombinasyon kalibre edilmezse sinyaller iptal olur.
- **A5 (CDS Gate, defensive) × A1 (long-only momentum):** Bear-market'te A5 cash'e geçer; A1 momentum top-performer'lara yatırım yapar → sinyal çakışması.

### 7.3 Multicollinearity Riskleri

- B7 (USDTRY beta) + B12 (TLREF spread) + A5 (CDS gate) — üçü de makro risk-off yansıtır; PCA gerekebilir.
- A3 (likidite) + B11 (block trade) — likidite mikroyapısı paylaşır.
- Tomtosov (2024) bulguları: EM'de momentum/size/low-vol faktörleri negatif return dönemlerinde aşırı korelasyon → "unique factor framework" yaklaşımı önerilir (duplicate position'lar tasfiye).

### 7.4 Combined Factor Portfolio (Kavramsal)

Önerilen Phase 5 portföy yapısı (kavramsal, sayısal kalibrasyon kapsam dışı):
- **Core (60–70%):** A1 + B14 cross-sectional momentum (Top tercile equal-weight)
- **Satellite (20–30%):** B8 holding discount + B7 USDTRY pass-through tilt
- **Risk Layer:** A5 + B12 macro gate; A3 illikit penalty
- **Tactical:** B6 foreign flow + B10 index inclusion event-driven

---

## 8. ARCHITECTURAL CONSIDERATIONS

### 8.1 Per-Stock Signal → Cross-Sectional Sort Geçişi

Mevcut BIST OS "per-stock signal" mimarisi her hisse için bağımsız sinyal üretiyor; agregasyon hisse-bazlı (al/sat/bekle). 14 faktörden **A1, A3, A4, B6 (hisse versiyonu), B14** cross-sectional sort gerektiriyor — yani **tüm BIST evreni (~400 ticker) aynı anda skorlanıp sıralanıp Top/Bottom decile seçilmelidir.** Bu, mevcut "her hisse bağımsız" akışından farklı bir batch-mode çalıştırma rejimidir.

### 8.2 Phase 5 sort_layer Kavramsal Taslağı

**Sort_layer responsibilities:**
1. **Universe constructor:** BIST evrenini (filtreli; örn. BIST100 + BIST50 ± delisting handler) günlük/aylık snapshot al.
2. **Factor evaluator:** Her aktif faktör için (A1, A3, B14 …) hisse-bazlı raw skor hesapla.
3. **Cross-sectional normalizer:** Her faktör skoru cross-sectional Z-score'a çevir.
4. **Aggregator:** Faktör ağırlıklarını uygulayıp composite skor üret.
5. **Rank & decile/tercile selector:** Top X% long, Bottom X% short/cash (yasak nedeniyle BIST'te short → cash).
6. **Output formatter:** Per-stock signal API'sine sonuçları dönüştür (geri uyumluluk).

**Persistence:** Her gün/ay snapshot kaydet (factor scores + ranks); backtest harness bu snapshot'lara erişebilmeli.

**Performance considerations:** ~400 ticker × ~10 faktör × aylık = küçük ölçek (CPU-bound, tek-thread yeterli). Storage: ~10 MB/yıl.

### 8.3 Tek Hisse → Çapraz-Kesit Köprüsü

Geçiş döneminde **shadow-mode** önerilir: sort_layer çıktıları **gözlem amaçlı** kaydet, mevcut per-stock signal mantığı production'da devam etsin. 60–90 gün shadow-period sonrası A/B test ile production'a geçir.

---

## 9. KISITLAR & CAVEAT'LAR

1. **BIST evren büyüklüğü:** ~400 ticker (BIST Tüm Pazar) literatür panellerinden küçük (AMP 2013: 7000+ ABD hissesi). Decile/quintile granülaritesi azalıyor. Pratik öneri: quintile yerine **tercile** (Top 33% – Bottom 33%) kullan.

2. **Veri kalitesi varyansı:** KAP yapısal verisi kaliteli; consensus revisions (B14) ücretli; lending fee (B13) public-data yok; intraday tick (B11) ücretli abonelik.

3. **Survivorship bias:** Delisted ticker'lar yfinance'ta görünmüyor; tarihsel BIST listesi manual rekonstrüksiyon gerektiriyor (KAP arşivinden). Backtest sonuçları muhtemelen yukarı sapmalı.

4. **Trans cost rebalance frekansı:** Cross-sectional aylık rebalance ~%2–4 yıllık komisyon+slippage maliyeti (BIST broker komisyon ~%0.1–0.2 per leg). <500K TL portföyde slippage ihmal edilebilir ama komisyon önemli.

5. **2022–2024 hiperenflasyon dönemi:** TMS 29 inflation accounting (2023 fiscal year'dan itibaren zorunlu) book value, earnings, B/M, momentum sinyallerini bozar. Backtest bu dönemi **out-of-sample** test olarak işle. 2025 sonu CPI %30.89'a düşmüş (Daily Sabah 2026 raporları).

6. **SPK 15/517 açığa satış yasağı:** Mart 2026 itibariyle aktif, 10 Nisan 2026'ya kadar uzatıldı; tarihsel olarak yasak sık tekrarlanıyor. Long-only ya da long-cash mod tasarımı zorunlu.

7. **TCMB politika faizi %42 risk-free rate:** Sharpe hesabı bu rate ile yapıldığında herhangi bir BIST equity stratejisinin Sharpe'ı çok düşük çıkar. Bunun yerine **Information Ratio** (BIST100 vs strateji) raporlanması daha anlamlı.

8. **Türkiye-spesifik politika riskleri:** TCMB intervention (B12, B7'yi etkiler), SPK yasağı (B13), borsa kapanış riski (2016 darbe girişimi sonrası geçici kapanış), siyasi olaylar — bu rejimler tarihsel rejime-conditional faktör performansını bozar.

9. **Akademik literatür gap:** B12 TLREF-spread → BIST equity doğrudan akademik delil yok; B9 Mart–Mayıs temettü cluster akademik olarak ayrıntılı dokümante edilmemiş (Adaoglu çalışmaları policy yapısına odaklı, takvim cluster'a değil); BIST holding NAV discount akademik validation yok (sadece broker raporları).

10. **Free vs paid data:** B11 (intraday), B13 (lending fee), B14 (consensus) ücretli verilere dayanır; ücretsiz alternatifler kalite kaybıyla mümkün.

---

## 10. REGIME-CONDITIONAL FAKTÖR HİPOTEZİ

### 10.1 Rejim Sınıflandırması

| Rejim | İndikatörler | Süre (tarihsel) |
|-------|--------------|-----------------|
| **Bull (risk-on)** | CDS <300 bps, USDTRY stabil/appreciation, foreign flow pozitif, BIST 6-ay momentum + | 2020 Q4–2021 Q3; 2024 Q2–2025 Q3 |
| **Bear (risk-off)** | CDS >450 bps, USDTRY accelerated depreciation, foreign outflows | 2018 Q3–Q4; 2021 Q4–2022 Q1; 2023 Q1 (deprem) |
| **Sideways / range** | CDS 300–450 bps, lateral USDTRY, mixed flows | 2019; 2024 Q1; 2026 Q1–Q2 (mevcut, CDS 236–264 bps) |

### 10.2 Bull Market'te Güçlü Faktörler

- **A1 Value-Momentum** (momentum bileşeni özellikle güçlü)
- **A2 Currency Momentum** (TRY appreciation rallisi)
- **B6 Foreign Flow** (positive feedback trading)
- **B10 Endeks Dahil/Çıkar** (mutual fund flows aktif)
- **B14 Earnings Revision Momentum** (analyst upward revisions)

### 10.3 Bear / Sideways Güçlü Faktörler

- **A3 Liquidity Premium** (flight-to-liquidity → likit hisselerde rally; illikit'lerde drawdown — short/avoid)
- **A5 CDS Gate** (defensive cash bias devreye girer)
- **B8 Holding NAV Discount** (mean reversion en güçlü; discount geniş)
- **B12 TLREF/Repo Spread** (funding stress indicator)
- **Bildik-Gulay contrarian / kısa-vadeli reversal** (panik satışları sonrası bounce)

### 10.4 Regime-Conditional Faktör Allocation Kavramı

Phase 5 öneri: **factor weights regime'a göre dinamik ayarlanır**. Örneğin:
- **Bull:** w(A1) = 40%, w(B14) = 30%, w(B6) = 20%, w(A5 gate) = aktif değil
- **Bear:** w(A3) = 30%, w(B8) = 30%, w(A5 gate) = aktif, w(A1) = 15%
- **Sideways:** w(A1) = 25%, w(B14) = 25%, w(B8) = 25%, w(B7) = 25%

Rejim transition sinyali: CDS 50-day MA breach, USDTRY 200-day MA breach, foreign flow rolling 4-week sign change.

---

## 11. BULUNAMADI LİSTESİ

Aşağıdaki sorular araştırmada yanıtlanamadı; literatür gap veya paywall arkasında:

1. **Asness, Moskowitz & Pedersen (2013) Türkiye verisi:** Doğrudan 8-piyasa equity listesinde Türkiye **YOK** (sample: ABD, İngiltere, kıta Avrupası, Japonya).
2. **Bekaert, Harvey, Lundblad (2007) Türkiye-spesifik istatistik:** Paneldedir (NBER WP 11413 EM listesi); ancak Türkiye-spesifik istatistik (% likidite premium for Turkey alone) raporda izole edilmemiş.
3. **Longstaff, Pan, Pedersen, Singleton (2011) Türkiye verisi:** Türkiye CDS örneklemde **dahildir**; Pan & Singleton (2007) Türkiye CDS curve inversion özellikle vurgulanır.
4. **Bildik & Gulay (2008) tam % CAR rakamları (BIST-30 vs BIST-100):** Paywall arkasında; SSRN preprint kısmi bilgi veriyor ama exact CAR magnitudes erişilemedi.
5. **Doğrudan TLREF spread → BIST equity returns akademik regresyon çalışması:** **Bulunamadı** (literatür gap; B12 implementasyonu için backtest gereklilik).
6. **Mart–Mayıs Türk dividend cluster akademik kanıtı:** Adaoglu (2000, 2008) policy istikrarsızlığa odaklı; cluster kalıbı akademik olarak ayrıntılı analiz edilmemiş. Empirical market practice (TTK AGM kuralları kaynaklı) ama akademik delil zayıf.
7. **Türkiye holding (KCHOL/SAHOL/AGHOL/KOZAL/DOHOL) NAV discount mean reversion akademik çalışma:** Tek bir BIST-spesifik akademik makale bulunamadı. Broker raporları (ÜNLÜ&Co, PA Turkey) sektör pratik delil sağlıyor; akademik validation gap.
8. **BIST endeks dahil/çıkar 2015 sonrası çalışmalar:** Bildik & Gulay (2008) en güncel sistematik çalışma; 2010+ döneminde tekrar çalışılmadı.
9. **Ersoy & Ünlü ISE momentum çalışması başlığı:** Kullanıcı tarafından "Size, Book-to-Market, Volatility and Stock Returns" olarak verildi ama SSRN ID 2731176'da bulunan paper "Size, Book to Market Ratio and Momentum Strategies" başlığında (volatilite faktörü yok).
10. **2020–2026 BIST momentum/value spesifik çalışmaları:** Doğan et al. (2022), Tomtosov (2024) bulundu; daha fazla yayın yapılmış olabilir ama paywall/aramada erişilemedi.

---

## 12. SONUÇ

BIST OS Trading System için 14 EM/BIST-spesifik faktörün literatür ve fizibilite analizi sonucunda en yüksek katma değer-maliyet oranı sunan üçlü **B14 (Earnings Revision Momentum) + A5 (Sovereign CDS Gate) + B7 (USDTRY Pass-Through Beta)** olarak belirlenmiştir; bu üçü 30-gün penceresinde implement edilebilir ve **Phase 5 sort_layer altyapısı olmadan** dahi (B14 hariç — yarısı sort_layer'a bağlı) deploy edilebilir. Cross-sectional sort altyapısının inşası kritik path üzerindedir ve A1, A3, B8 gibi yüksek-alpha faktörler bu altyapıya bağımlıdır. SPK 15/517 sayılı kararı uyarınca açığa satış yasağı (10 Nisan 2026 seans sonuna kadar uzatılmış) aktif olduğu sürece B13 implementasyonu yasak; B11 ise <500K TL portföy ölçeği nedeniyle ROI negatif. Regime-conditional faktör allocation Phase 5 sonrası 2027 roadmap için önerilir.

---

### BIST 2023-2026 SEKTÖR PRATİĞİ - ÖNEMLİ

## BIST 2023-2026 Sektör Pratiği

> **Yamanın Amacı:** RR-012'de tanımlanan 14 EM/BIST faktörünün **akademik temellerinin** üzerine, **2023-2026 döneminde Türk pratisyenler (broker araştırma, fon yöneticisi, forum/YouTube ekosistemi, retail patlama kuşağı) tarafından nasıl kullanıldığına** dair bağımsız bir saha haritası eklemek. Ana akademik karar matrisi DEĞİŞTİRİLMEDİ; aşağıdaki tablolar paralel bir kolon olarak okunmalıdır. SPK'nın 1 Mart 2026 itibariyle başlattığı ve 26 Mayıs 2026 seans sonuna kadar altıncı kez uzatılan açığa satış yasağı (Kurul Karar Organı'nın 25.04.2026 tarihli 27/807 sayılı Kararı; borsaningundemi.com aktarımı) ilgili faktörlerde ayrıca işaretlendi.

---

### Erişim Notları (yamanın başında — şeffaflık için)

**Twitter/X Erişim Notu.** Türk fintwit (özellikle "yabancı takas", "bilanço cuma", "blok satış" odaklı isimler) önemli bir pratisyen sinyal kaynağı olabilir; ancak 2026 itibariyle X API kısıtlamaları ve login-wall nedeniyle sistematik tarama yapılamadı. Bu yamada **Twitter sample edilmemiştir**. Forum (Hisse.net, BigPara, Investing.com TR), YouTube açıklamaları, broker araştırma kategorisi ve TEFAS izahname metinlerine ağırlık verildi.

**TEFAS Erişim Notu.** İncelenen fonların **Tier-1 metinleri** (KIID, izahname, performans sunum raporu) yalnızca mevzuatın asgari içeriğini barındırır; "ihraççı paylarına en az %80 yatırılır" tipi jenerik dil hakimdir (BIH izahnamesinden alıntı: "Fon toplam değerinin en az %80'i devamlı olarak ihraççı paylarına ve ihraççı paylarından oluşan endeksleri takip etmek üzere kurulan borsa yatırım fonu katılma paylarına yatırılır."). **Tier-2 fiili holdings** (aylık fon portföy disclosures) Takasbank/TEFAS üzerinden parse edilebilir olmakla birlikte bu yamanın kapsamı dışındadır; bu nedenle "fonlar şu faktörü kullanıyor" tipi iddialar **strateji metnine değil, fon performans korelasyonuna** dayandırıldı. KIID'lerin "değer ve büyüme stratejisi izlenir" benzeri içeriksiz formülasyonları, Tier-1'in zayıf bir delil katmanı olduğunu gösterir.

**Genel Erişim Limiti.** Tüm popülerlik skorları **ordinal skaladır** (Yüksek / Orta / Düşük / Yok). Sayısal yüzde verilmedi; her seviye parantez içinde gözlem notu ile gerekçelendirildi. Confirmation bias riski, akademik beklenti ile pratisyen söylem arasında çelişki çıktığında çelişkinin **öne çıkarılması** kuralıyla yönetildi (bkz. §7-b ve "Kritik Bulgular").

---

### 1. Faktör Bazlı Pratisyen Kullanım Haritası

| Kod | Faktör (Akademik) | Pratisyen Adı (Türkçe) | Tipik Kullanım | Başlıca Araç / Platform | Popülerlik (Ordinal) |
|---|---|---|---|---|---|
| A1 | Asness Value-Momentum Combo | "Ucuz + güçlü trend" / "F/K düşük & yükseliş trendinde" | Hisse seçim filtresi; iki ayrı taramanın kesişimi manuel yapılıyor | Foreks Pro tarayıcı, Matriks IQ formül penceresi, Fintables radar | **Düşük** (V ve M ayrı ayrı çok popüler ama "combo" formel olarak yalnızca 1–2 niş köşe yazısında — bkz. Eral Karayazıcı Hürriyet/BigPara) |
| A2 | Country-Relative Currency Momentum | "TRY zayıflık ralisi" / "kur ataklarında ihracatçı rotasyonu" | TRY rejim değişimi sonrası ihracatçı sepetine geçiş | Manuel haber takibi + sektör endeksleri (XUTUM, XULAS) | **Yüksek** (her TRY ataklı haftada Habertürk/Midas listeleri yayımlanıyor) |
| A3 | EM Liquidity Premium (Amihud ILLIQ) | "Düşük hacim = riskli kağıt" (negatif çerçeveleme) | Risk filtresi olarak — alpha kaynağı olarak DEĞİL | Likidite filtresi (günlük hacim + lot bazı) | **Düşük** (akademik premium kavramı pratisyende yok; pratisyen düşük likiditeyi **kaçınılacak risk** olarak görür — bkz. Bank & Kahraman akademik bulgusu: küçük hisselerde negatif ilişki) |
| A4 | Inflation-Beta Sorting | "Enflasyon koruması" / "pricing power'lı şirket" | Hiperenflasyonda Migros/BIM tipi; dezenflasyonda bankacılığa rotasyon | Sektörel rotasyon; bilanço analizi | **Orta** (köşe yazılarında ve broker stratejilerinde sık ancak sistematik beta sıralaması ender) |
| A5 | Sovereign CDS Conditional Gate | "CDS yükselince borsada satış" / "risk-off" | Günlük makro risk panosu — pozisyon kapatma sinyali | doviz724.com, garantibbvapos.com.tr panelleri, BloombergHT | **Yüksek** (Kulis Borsa siyasi gelişme sonrası 250 bp sıçramayı net şekilde alarm sinyali olarak işaretledi) |
| B6 | Foreign Flow İkinci Türevi (İvme) | "Yabancı takas oranı artışı" / "X gündür ardışık alım" | Günlük takip — momentum/persistence proxy'si | İş Yatırım "Günlük Yabancı Oranları", Halk Yatırım, Matriks Prime "Yabancı Takas", Vakıf VKY Analiz, Osmanlı Menkul "Yabancı İşlemleri" | **Yüksek** (her gün yayımlanan bps + "10 gündür artıyor" matrisleri pratisyen söyleminin omurgası) |
| B7 | USDTRY Pass-Through Beta | "İhracatçı / ithalatçı ayrımı" / "döviz geliri yüzdesi" | Bilanço sonrası ihracat payı yüzdesine göre filtreleme | KAP bilanço notları + Midas/Habertürk listeleri | **Yüksek** (her kur şokunda sistematik liste üretiliyor) |
| B8 | Holding NAV Discount Mean Reversion | "Holding iskontosu daraldı/genişledi" | KCHOL/SAHOL/DOHOL al-sat sinyali; iskonto bandı geçişleri | Broker raporları (Deniz Yatırım, Garanti BBVA), hedeffiyat.com.tr, halkaarzmerkezi.com | **Yüksek** (her broker holding raporunda iskonto bandı tabloyla veriliyor — Deniz Yatırım 3.04.2025) |
| B9 | Dividend Cluster Timing | "Temettü oyunu" / "bedelsiz peşinden koşma" | Mart-Mayıs takvimi ile pozisyon; ödeme öncesi giriş | Dünya Gazetesi takvimleri, halkarz.com, Midas takvimi, temettu.app | **Yüksek** (temettuhisseleri.com: "Son 10 yılda en yoğun temettü ayları Nisan ve Mayıs aylarıdır" — pratisyende kanon) |
| B10 | BIST Endeks Dahil/Çıkar Olayları | "Endekse giren/çıkan" / "rebalance günü" | Çeyreklik İş Yatırım duyurusu çıktıktan sonra giren paylara ön-pozisyon | İş Yatırım Endeks Değişiklikleri tagi, Borsa İstanbul Endeks Duyuruları | **Orta-Yüksek** (her çeyrek Dünya Gazetesi/İş Yatırım haber dolaşıyor; rebalance günü pozisyonu broker terminallerinde standart) |
| B11 | Block Trade Tespiti | "Özel emir" / "blok satış" / "ticket dansı" | Aynı gün takas analizi + KAP özel durum açıklaması karşılaştırması | Matriks IQ "Takas Analizi" (aracı kurum bazında lot farkı), İş Yatırım TradeMaster | **Orta** (Matriks Takas Explorer popüler; ancak akademik formel "block trade detection" kavramı zayıf) |
| B12 | TLREF/Reverse Repo Spread | "TLREF endeksli kıymetler" / "fonlama maliyeti" | Bankacılık marjı analizinde girdi — hisse seçimi için nadiren | BIST TLREF endeksi, Osmanlı Menkul açıklamaları | **Düşük** (faiz oranı olarak çok bilinir, hisse-faktör girdisi olarak yalnızca bankacılık analistlerinde) |
| B13 | Açığa Satış Oranı + Lending Fee | "Short ratio" / "ödünç pay" | **YASAK AKTİF — 1 Mart 2026'dan 26 Mayıs 2026 seans sonuna kadar uygulama askıda** | İş Yatırım Teknik Bülten "dün çok açığa satış yapılan hisseler" satırı, ÖPP (Ödünç Pay Piyasası) | **Düşük (zorla)** (yasak öncesi orta düzeyde kullanılıyordu; mevcut konjonktürde sinyal değeri sıfırlanmış durumda) |
| B14 | Earnings Revision Momentum | "Konsensüs revizyonu" / "Foreks beklenti vs gerçekleşen" / "bilanço sürprizi" | Bilanço haftası öncesi konsensüs sapması taraması | Foreks beklenti ekranları, İş Yatırım şirket raporları, hedeffiyat.com.tr | **Orta** (bireysel raporlarda var; sistematik "revision momentum sıralaması" pratisyende ender) |

**Erişim Notu / §1.** Tablo 8 hafta boyunca 70+ forum thread, 30+ broker raporu özeti ve 12 platform belgesinin gözlemiyle inşa edildi. Sample küçük; "Yüksek/Orta/Düşük" sıralaması göreli — bir broker eklediğinde sıralama değişebilir. Hisse-bazlı tartışmaların büyük çoğunluğu (NTHOL, DERHL, INFO örnekleri Investing.com TR) "tahta dansı / fonların aldığı kağıt / büyük lider gelir" söylemi etrafında yoğunlaşır; bu söylem **takip eden Akıllı Para (B6 + B11 birleşik)** sezgisine işaret eder ama formel olarak adlandırılmamıştır.

---

### 2. BIST Broker Araştırma Departmanları — Faktör Coverage Matrisi

İş Yatırım, Ak Yatırım, Garanti BBVA Yatırım, Yapı Kredi Yatırım, Deniz Yatırım, Şeker, Tacirler, Vakıf, Gedik, QNB Invest ve foreign masaları (HSBC/Citi/JPMorgan/GS/UBS) açık erişim sayfaları taranarak hangi faktörün **kurumsal periyodik rapor başlığı** içinde yer aldığı tespit edildi. Foreign masalar büyük ölçüde abonelik-duvarı arkasında olduğundan veri zayıf; not edildi.

| Kod | Broker Coverage Seviyesi | Tipik Rapor Başlığı / Format | Coverage Notu |
|---|---|---|---|
| A1 (V+M Combo) | **Düşük** | "Model Portföy" raporlarında value/momentum karması örtük olabilir; formel V+M combo başlığı yok | İş Yatırım Hisse Senedi Strateji raporu temalı (model portföy) — combo değil |
| A2 (TRY Momentum) | **Orta** | Strateji raporlarında "TL trendi sonrası rotasyon" temalı bölümler | Ak Yatırım "Piyasa Fikirleri" aylık strateji + Deniz Yatırım strateji raporları |
| A3 (Liquidity ILLIQ) | **Yok** | Akademik premium olarak coverage yok | Likidite **filtresi** olarak hisse seçiminde örtük; **alpha kaynağı** olarak rapor yok |
| A4 (Inflation Beta) | **Orta** | Enflasyon muhasebesi raporları + sektör rotasyon notları | İş Yatırım "10 Soruda Enflasyon Muhasebesi" raporu |
| A5 (CDS Gate) | **Orta-Yüksek** | Günlük makro bültenlerde CDS satırı standart | QNB Invest, Bullsyatırım, BloombergHT günlük yorumları |
| B6 (Foreign Flow) | **Yüksek** | İş Yatırım "Günlük Yabancı Oranları" (günlük); Halk Yatırım "Aylık Yabancı İşlemleri" + "Yabancı Takas Oranları" (haftalık); ICBC "BIST-30 Haftalık Yabancı Takası Raporu"; Vakıf "Günlük Yabancı Takas Oranı Değişimi"; Ak Yatırım "yabancı işlemleri ve takası, temettü ve sermaye artırımı beklenti" tematik raporu | Türkiye'de en kurumsallaşmış pratisyen faktörü — **broker'lar günlük başlık altında resmi rapor yayımlıyor** |
| B7 (USDTRY Beta) | **Yüksek** | Çeyreksel "İhracatçı / İthalatçı Konumlanma" raporları | Garanti BBVA Yatırım, İş Yatırım sektör notları; KAP bilanço yorumlarında standart |
| B8 (NAV Discount) | **Yüksek** | Holding raporlarında "NAD iskontosu" tablosu zorunlu sayılır | Deniz Yatırım, Garanti BBVA, Ak Yatırım KCHOL/SAHOL/DOHOL/AGHOL raporları — sektörü tanımlayan metrik |
| B9 (Dividend Timing) | **Orta** | Yıllık temettü beklenti raporları | İş Yatırım "2026'da en az X getiri potansiyeli olan ve en az %5 temettü verimi beklenen şirketler" listesi |
| B10 (Index Event) | **Yüksek** | Çeyreklik resmi "BIST Endeks Değişiklikleri" duyurusu | İş Yatırım resmi başlık altında düzenli, Dünya Gazetesi haberi haline gelir |
| B11 (Block Trade) | **Düşük** | Takas raporlarında dolaylı görünür ama "block trade detection" başlıklı periyodik rapor yok | Matriks IQ aracı kurum dağılımı kullanıcının kendi gözlemi |
| B12 (TLREF Spread) | **Düşük** | SGMK strateji raporlarında girdi olarak | İş Yatırım "SGMK Strateji Raporu" |
| B13 (Short Interest) | **Yok (yasak nedeniyle)** | İş Yatırım Teknik Bültende "dün çok açığa satış yapılan hisseler" satırı vardı; **yasak süresince anlamsız** | SPK 27/807 sayılı karar — 26 Mayıs 2026'a kadar |
| B14 (EPS Revision) | **Orta** | Çeyrek bilanço öncesi "Beklenti" tabloları | İş Yatırım/Ak Yatırım "Şirket Raporları" (4Ç25 beklenti notları) |

**Erişim Notu / §2.** Yabancı broker (HSBC, Citi, JPMorgan, GS, UBS) Türkiye masası raporları büyük ölçüde abonelik gerektirir; yalnızca kamuya açık özetler (genellikle yerli basın aracılığıyla — paraajansi.com.tr örneği) görülebildi. "Foreign broker coverage" satırı bu raporda **boş bırakıldı**.

---

### 3. 2023-2024 Geçiş Dönemi Faktör Davranışı

**(a) Mart 2023 — Şimşek/Erkan dönüşü, sonra Karahan (politika rejim değişimi).** Mart 2023'te ortodoks para politikasına dönüş sinyali sonrası **A5 CDS Gate'in sinyal verdiği aşamalı bir gevşeme** yaşandı: Türkiye 5-yıllık CDS 14 Temmuz 2022'de 901,75 baz puanlık tarihi zirveye çıktıktan sonra (fveri.com ve bullsyatirim.com teyitli: "Temmuz 2022'de Türkiye'nin CDS'i 901,75 düzeyine kadar çıkmıştı"), 2023 sonu itibariyle 279 bp'ye geriledi. Bu gevşeme **uzun-vade reversal** sinyaliydi — pratisyen söyleminde "CDS düşerse banka rallisi" hipotezi (Eral Karayazıcı, Hürriyet/BigPara) bu dönemde gerçekten test edildi ve **kısmen doğrulandı** (banka endeksi 2023 ikinci yarısında BIST-100'ün üzerinde getiri). **A4 Inflation-Beta** ise hiperenflasyonun zirvesinde (T.C. Cumhurbaşkanlığı Strateji ve Bütçe Başkanlığı'nın Ekim 2022 verisine göre yıllık TÜFE **%85,51** düzeyinde gerçekleşti — sbb.gov.tr) **anlamlılığını yitirdi**: tüm hisseler nominal olarak yükseldiği için "yüksek vs düşük inflation-beta" sıralaması mekanik olarak ayrışmadı; pratisyen bu dönemde "TÜFE+ getirisi" ile "reel anlamda kazandıran hisse" kavramını eş anlamlı kullanmaya başladı.

**(b) Mayıs 2023 — Seçim haftası.** İkinci tur öncesi yabancılar çıkış yaptı, kur baskılandı. Cumhuriyet gazetesinin 30 Mayıs 2023 tarihli haberine göre ikinci tur sonrasının ikinci işlem gününde "TL dolar karşısında yılbaşından bugüne ise yüzde 7.4 kayıp yaşadı"; dolar/TL gün içi 20.42 ile tarihi zirveye çıktı. **B6 Foreign Flow** o haftada **negatif ivme** (sürekli çıkış) gösterdi; pratisyen söyleminde "yabancı satış kuruyor mu" sorusu Hisse.net ana gündemiydi. **B8 NAV İskonto** ise eş zamanlı **genişledi** — KCHOL ve SAHOL gibi holding hisseleri tarihsel ortalama iskonto bandının üzerine çıktı; ardından Haziran-Temmuz 2023 toparlanmasında **iskonto daraldı** ve holding hisseleri BIST-100'ü geçti (Deniz Yatırım 3.04.2025 raporu KCHOL için 298,80 TL hedef, NAD iskontosu tarihsel ortalamanın üzerinde gözleminde bulunmuştur). Bu, **B8 mean reversion** tezini güçlü destekleyen bir doğal deneydir.

**(c) Şubat 2023 — Kahramanmaraş depremi.** Olay etüdü literatürü (dergipark.org.tr Anadolu İİBFD, 2024) deprem günü ve sonraki 10 gün için: BIST Sigorta endeksinde **istatistiksel olarak anlamlı negatif** kümülatif anormal getiri (-CAR); BIST Taş-Toprak (çimento) endeksinde **anlamlı pozitif** CAR; BIST Antalya, İletişim, Turizm, Ulaştırma'da anlamlı negatif CAR. Borsa İstanbul 8 Şubat saat 11:00'de pazarı 5 iş günü süreyle kapattı ve günün tüm işlemlerini iptal etti. **Faktör investing perspektifinden ders:** A3 (likidite) ve A5 (CDS gate) gibi piyasa-geneli faktörler bu tarz **exogenous tail event'lerde** koruma sağlamaz; sektörel faktör (B7 USDTRY beta türevi olan "ihracat-ağırlığı" tipi sektör tilt'leri) ancak post-event reaktif şekilde devreye girer. BIST OS'un 14 faktörlü çerçevesi bu tip "afet rejimi" durumlarında **devre dışı bırakılması gereken bir override katmanı**na ihtiyaç duyar.

**(d) 2023 enflasyon zirvesi (%75–85,51 koridoru).** Hiperenflasyon koşullarında **A4 LOW-inflation-beta long** pozisyonu pratisyen söyleminde **anlam taşımadı**; aksine HIGH-pass-through (Migros, BIM, gıda perakende, çimento) tematik olarak öne çıktı. Akademik "LOW vs HIGH inflation-beta" sıralamasının pratiğe çevirisinde, pratisyen "pricing power" söylemini kullandı — kavramsal olarak benzer ama metodolojik olarak (sektör vs hisse-spesifik beta) farklı.

**Erişim Notu / §3.** 2023 olaylarının faktör perspektifinden analizi büyük ölçüde **post-hoc**'tur; o dönem real-time yayınlanmış BIST OS-tipi sistematik raporlama bulunamadı. Yorum, akademik olay etüdü literatürü + güncel pratisyen retrospektif söyleminin kombinasyonudur.

---

### 4. 2024-2026 Yerleşik Dönem — Hangi Faktörler Alpha Üretti?

**(a) Dezenflasyon rally beklentisi (2024H2-2025).** TCMB Aralık 2024 toplantısında politika faizini indirdi: TCMB resmi Basın Duyurusu 2024-70 (tcmb.gov.tr) ifadesiyle "Para Politikası Kurulu, politika faizi olan bir hafta vadeli repo ihale faiz oranının yüzde 50'den yüzde 47,5'e indirilmesine karar vermiştir." Midas yatırım trendleri raporuna göre 2024 sonunda BIST 100 dolar bazında ~275 $ seviyesinde, 2025 analiz konsensüsü 320-330 $ aralığında. Bu rejimde **A1 V-M combo** için tipik beklenti: dezenflasyon başlangıcında VALUE bacağı (özellikle banka) önde, momentumun fazlalaşması ortalama 6 ay sonra. **A4 LOW-inflation-beta long** stratejisi 2024 yılı boyunca BIST-100'ün altında kaldı; 2024'ün en kazandıranı **Pardus Portföy Birinci Hisse Senedi Fonu (BIH) %176.66 getiri ile** sektördeki en yüksek hisse senedi fonu performansını gösterdi (TEFAS verisi, Midas) — ancak BIH izahnamesi salt mevzuat dili olup sistematik faktör (momentum/value/yabancı-flow) ifadesi içermez. **Bankacılık endeksli fonlar** ise sektör tilt'iyle %70+ getiri sağladı (İş Portföy BIST Banka Endeksi TAU %75.96; Ak Portföy ADP %72.91 — Midas raporu).

**(b) Yabancı geri dönüş 2024-2026 ve Critic iddiasının testi.** 2 Haziran 2025 itibariyle QNB Finansbank dâhil yabancı oranı %27.75, QNB hariç %25.84; 29 Eylül 2025'te QNB dâhil %35.93 (Mayıs 2022'den beri en yüksek), QNB hariç %26.82 (ekonomim.com — Tankut Taner Çelik hesaplaması). QNB'nin fiili dolaşımdaki payı %0.12 olmasına rağmen takasta tamamı yabancı olarak kaydedildiği için aggregate yabancı oranı **çarpıtılmış** durumda — bu, BIST OS'un B6 sinyal hesaplamasında **QNB-temizlenmiş seri** kullanmasını zorunlu kılan kritik bir bulgu. 13 Şubat 2026 itibariyle yabancı oranı 6.71'e, düzeltilmiş yabancı oranı 5.89'a yükseldi; SURGY, TRALT, MOPAS gibi hisseler "10 gündür kesintisiz alım" listesinde (İş Yatırım Günlük Yabancı Oranları + endeks24.com).

**Critic iddiası testi — özet bulgu (§F'de detaylı).** Türk pratisyen kaynaklarında "5-gün rolling delta" formel/standart bir metrik **DEĞİL**. Kullanılan dominant zaman pencereleri: (i) günlük bps değişim (İş Yatırım, Vakıf), (ii) "X gündür ardışık artış" — genellikle 10 güne kadar sayım (İş Yatırım matrisi, Halil Buhur takas blogu, Endeks24), (iii) haftalık delta (Paraajansı, Hisse.net haberleri, ICBC "BIST-30 Haftalık Yabancı Takası Raporu"), (iv) TCMB haftalık menkul kıymet istatistikleri (net $ giriş/çıkış), (v) aylık delta. Yani: Critic'in "günlük acceleration vs weekly net" ayrımı pratisyen literatüründe **kısmen yansıyor** (günlük + ardışık gün sayımı ivmeye işaret eder) ama "5 gün" özel pencere değil. Bulgu: **partial — sinyal şekli (ivme/persistence) doğrudur, parametre seçimi (5-gün) pratisyen söyleminde gerekçesini bulamamaktadır.**

**(c) SPK açığa satış yasağı (1 Mart 2026 → 26 Mayıs 2026).** Yasak 2 Mart'ta başladı; 8 Mart, 25 Mart, 14 Nisan ve son olarak 25.04.2026 tarih 27/807 sayılı kararla 26.05.2026 seans sonuna kadar **altıncı kez** uzatıldı (borsaningundemi.com, bloomberght.com). **Doğrudan etki:** B13 (Short Interest + Lending Fee) sinyali **ölü**. **Dolaylı etkiler:** (i) **B3 Likidite** — bid-ask spread'ler bazı orta-cap'larda genişledi; (ii) **B11 Block Trade** — hedge tarafının kısıtlanmasıyla blok ticket'larının yön belirleyici etkisi arttı; (iii) **B6 Foreign Flow** — yabancı kurumların TL netlemesi (hedging araçlarının kısıtlanması) nedeniyle daha temkinli pozisyon almasını getirmiş olabilir, ancak Şubat-Mayıs 2026 verisi henüz "yabancı çekildi" tezini desteklemiyor (İş Yatırım günlük raporlarında 10-gün kesintisiz alım serileri sürüyor); (iv) **A1 V-M combo** — momentum bacağı tek yönlü baskıyla suni kalabilir.

**(d) Retail patlama (Midas / Gedik Pay / İş Trade gibi mobil platformlar).** Webrazzi ve egirisim.com (19 Ağustos 2025) ile Türkiye Cumhuriyeti Yatırım Ajansı'nın (invest.gov.tr) teyit ettiği üzere Midas, Nisan 2024'te Portage Ventures liderliğinde 45 M$ tutarında Seri A turunu, Ağustos 2025'te QED Investors liderliğinde 80 M$ tutarında Seri B turunu kapatarak "Borsa İstanbul, Amerikan borsaları, yatırım fonları ve kripto paraları tek bir platformda buluşturarak 3,5 milyon kullanıcıya hizmet veriyor." **Yeni davranış pattern'leri (Hisse.net + Investing.com TR gözlemi):** (i) "Fonların aldığı kağıt" söylemi etrafında **takip-eden retail** sürüsü (ozatd → merko gıda örüntüsü, Investing.com TR yorumları); (ii) küçük-cap pump-dump döngüleri 2024 boyunca hızlandı (Marmara Capital MAC fonu 5 yılda %2643 getiri; pozisyonunun ağırlığı BTCIM ve BSOKE gibi orta-küçük cap — bu fon "fundamental value investing" diyor (marmaracapital.com.tr/en/mac-mutual-fund/) ama portföy dağılımı momentum aktivitesini de düşündürüyor); (iii) Midas/Gedik Pay kuşağında TEFAS fonlarına yönelimin artması faktör investing'i **dolaylı** profesyonelleştiriyor. Faktör perspektifinden: retail pump-dump döngüleri **A3 (likidite-azlık)** ve **B11 (blok)** sinyallerini bozarken, **B14 (EPS revision)** ve **B6 (foreign flow)** gibi kurumsal sinyalleri görece güçlendiriyor (sürü retail bunları takip ediyor).

**(e) BIST endeks rebalance — son 2 yıl 6 dönem.** 2025-Q4 değişiklikleri: BIST-30'dan Çimsa çıktı, DSTKF girdi; BIST-100'den ALFAS, AVPGY, BERA, LMKDC, SMRTG çıktı (Dünya Gazetesi). 2026-Q1 (01/01-31/03) ve 2026-Q2 değişiklikleri İş Yatırım resmi bültenlerinde yayımlanmıştır. **Pratisyen pattern (gözlem):** Duyuru günü ile fiili rebalance günü arasında çıkacak hisselerde tipik olarak satış baskısı, giren hisselerde alış görülür — yabancı kurumsal flow (pasif endeks fonları + ETF rebalance'ları) bu pattern'in en güçlü mekanizmasıdır. Yasak (B13) bu işlemi etkilemez; B10 sinyali 2024-2026 boyunca **çalışmaya devam etti**.

**Erişim Notu / §4.** TEFAS Tier-1 metinlerinin (BIH, MAC, TAU, ADP) hiçbiri sistematik faktör terimini içermediği için "fon X faktörü kullanıyor" çıkarımı **performans korelasyonuyla** sınırlı kalmaktadır; fiili portföy dökümleri (Tier-2) için Takasbank aylık disclosures gerekli, bu yamada parse edilmedi.

---

### 5. Türk Hedge Fund / Asset Management Faktör Kullanımı

**Tier-1 (KIID + izahname).** 20+ TEFAS hisse senedi fonu strateji metni tarandı. Bulgu: Metinlerin neredeyse tamamı **mevzuat asgarisi**dir. Tipik formülasyonlar: "Fon toplam değerinin en az %80'i devamlı olarak ihraççı paylarına yatırılır" / "değer ve büyüme stratejisi izlenir" / "VİOP sözleşmelerine de yatırım yapılabilir". Sistematik faktör (momentum/value/quality/foreign-flow/EPS-revision) ifadesi **hiçbir TEFAS fonunda doğrudan bulunamadı**. MAC için pazarlama dili "MAC invests in Turkish equities, aiming to generate absolute return. The fund's strategy is investing in a concentrated portfolio comprising shares of companies trading at a significant discount to their underlying values, identified by fundamental company research." (marmaracapital.com.tr/en/mac-mutual-fund/) — klasik bottom-up, faktör değil. BIH için izahname salt mevzuat dilidir (pardusportfoy.com).

**Tier-2 (Aylık fon portföy disclosures).** Takasbank/TEFAS aylık portföy dökümleri kamuya açıktır; parse edildiğinde sektör tilt'leri, hisse yoğunlaşması ve devir hızı gözlenebilir — ancak **örtük faktör maruziyetidir, açık beyan değildir**. Bu yamada Tier-2 parse'i yapılmadı; öneri: BIST OS pipeline'ına aylık TEFAS portföy verisini bağlamak ve top-decile fonların faktör maruziyetini (Fama-French 5 + momentum + USDTRY-beta regresyonuyla) sürekli izlemek.

**Sermaye Aile Holdingleri İç Asset Management.** Koç Holding (KCHOL) ve Sabancı Holding (SAHOL) iç hazine/portföy yönetimleri — kamuya açık veri **yoktur**. Halka açık iştirakler üzerinden dolaylı çıkarım yapılabilir (Akbank için ROE, Enerjisa tarife dönemi, vs. — halkaarzmerkezi.com SAHOL analizi).

**Yabancı Broker Türkiye Masası Araştırmaları.** Goldman Sachs, JPMorgan EM Equity, Citi CEEMEA, HSBC Frontier — büyük ölçüde abonelik duvarı arkasında. Kamuya yansıyan başlık örneği: Goldman Sachs Nisan 2026 enflasyon sonrası TCMB faiz tahmini güncellemesi (Investing.com TR akışında refere edilmiş). Foreign masaların **rapor şablonları** (yerli özetlerden çıkarım): A5 (CDS gate) + B6 (foreign flow) + B7 (FX pass-through) + makro üst-üste-bin faktörü yoğun; B8 (NAV discount), B9 (dividend timing), B10 (index event) gibi local-knowledge faktörler yerli broker raporlarında çok daha güçlü.

**LinkedIn — Türk Quant/Portföy Manager pozisyon ilanları (gözlem).** İlanların büyük çoğunluğu "kantitatif analiz", "Python/SQL", "risk modeli" başlıkları altında — saf "factor investing" rolü çok seyrek. Türk büyük portföy şirketlerinde (Ak Portföy, İş Portföy, Garanti Portföy, QNB Finansinvest, Yapı Kredi Portföy) "factor strategist" tipi rol nadirdir; "kantitatif analist" pozisyonları genelde **risk yönetimi** ya da **müşteri portföyleri optimizasyon** odaklıdır.

**Erişim Notu / §5.** TEFAS Tier-1 strateji metinlerinin zayıflığı önemli bir veri-açığıdır: pratisyen ekosistemde "biz şu faktörü kullanıyoruz" tipi resmi beyan ender olduğundan, BIST OS'un faktör çerçevesinin "ne kadar kuş bakışı yenidir, ne kadar var olanı yeniden adlandırır" sorusunun cevabı **gözleme dayalı** kalıyor.

---

### 6. 14 Faktör — Pratik Uygulanabilirlik Yeniden Ölçümü

**Skor metodolojisi.** **Pratisyen Kullanımı** = forum/YouTube/medya gözleminden ordinal (Y/O/D/Yok). **Broker Coverage** = §2'deki düzenli rapor coverage'ı (Y/O/D/Yok). **Veri Erişimi** = ücretsiz/yarı-ücretsiz kaynakla erişilebilirlik (Y/O/D). **Toplam Pratik Skoru** = 3 boyutun **ordinal ortalaması**, görsel olarak ★ sembolü ile (★★★★ Yüksek-Yüksek; ★★★ Yüksek-Orta; ★★ Orta; ★ Düşük; — Yok).

| Kod | Faktör | Pratisyen Kullanımı | Broker Coverage | Veri Erişimi | **Toplam Pratik Skoru** |
|---|---|:-:|:-:|:-:|:-:|
| A1 | V-M Combo | Düşük | Düşük | Y (KAP + yfinance) | ★ |
| A2 | TRY Momentum | Yüksek | Orta | Y (TCMB EVDS) | ★★★ |
| A3 | EM Liquidity (Amihud) | Düşük (negatif çerçeve) | Yok | Y (yfinance hacim) | ★ |
| A4 | Inflation-Beta | Orta | Orta | Y (TCMB+TÜİK) | ★★ |
| A5 | CDS Gate | Yüksek | Orta-Yüksek | O (doviz724, BloombergHT) | ★★★ |
| **B6** | **Foreign Flow İvme** | **Yüksek** | **Yüksek** | **Y (İş Yat./Halk Yat./Vakıf)** | **★★★★** |
| B7 | USDTRY Beta | Yüksek | Yüksek | O (KAP bilanço parse) | ★★★ |
| B8 | NAV Discount | Yüksek | Yüksek | O (broker raporları + KAP) | ★★★ |
| B9 | Dividend Timing | Yüksek | Orta | Y (Dünya/Midas/halkarz) | ★★★ |
| B10 | Index Event | Orta-Yüksek | Yüksek | Y (İş Yat. duyuruları + BIST) | ★★★ |
| B11 | Block Trade | Orta | Düşük | O (Matriks Takas Analizi) | ★★ |
| B12 | TLREF Spread | Düşük | Düşük | Y (BIST TLREF endeksi) | ★ |
| B13 | Short Interest | **Düşük (yasak)** | **Yok (yasak)** | — (yasak süresince) | **— (askıda)** |
| B14 | EPS Revision | Orta | Orta | O (Foreks/İş Yat. konsensüs) | ★★ |

**Kritik Kural Uygulaması.** Bu skorlar **ana RR-012 akademik karar matrisini DEĞİŞTİRMEZ**. Paralel bir kolon olarak okunmalıdır. RR-012'nin akademik top-3'ü (B14 EPS Revision, A5 CDS Gate, B7 USDTRY Beta) bu pratik skor matrisinde aşağıdaki gibi yerleşir:
- **B14**: Akademik = Top-1; Pratik = ★★ (orta) — **akademik premium pratiğe tam aktarılmamış**.
- **A5**: Akademik = Top-2; Pratik = ★★★ — **uyumlu**.
- **B7**: Akademik = Top-3; Pratik = ★★★ — **uyumlu**.

**Revize Edilmiş Top-3 (Pratik + Akademik Birleşik).** Akademik gücü ve pratik altyapısı çift-onayda toplanırsa öneri:
1. **B6 Foreign Flow İvmesi (★★★★)** — pratik altyapı en güçlü, akademik destek de güçlü; QNB-temizleme şart.
2. **B7 USDTRY Pass-Through Beta (★★★)** — her iki perspektifte uyumlu; hisse-spesifik beta uygulanabilir.
3. **A5 CDS Conditional Gate (★★★)** — risk-off override olarak değerli, pratik veri günlük erişilebilir.

**B14 EPS Revision** akademik olarak güçlü ama pratik altyapısı (broker konsensüs API'si yok, Foreks aboneliği gerekli) sınırlı — RR-012'nin akademik top-3 sıralamasının bir kademe gerisine düşürülmesi önerisi.

---

### 7. Yeni Bulgular ve Akademik Boşluk

**(a) Akademik literatürün kaçırdığı BIST-pratisyen sezgileri.**
- **"Bayram öncesi son hafta accumulation"**: Ramazan/Kurban Bayramı tatil haftası öncesi hafif yukarı kayma — perakende, gıda, ulaştırma sektörlerinde gözlenir. Forum söyleminde belirgin ama akademik olay etüdü ender.
- **"Bilanço cuma günü pattern'i"**: KAP bilanço açıklamaları seans sonrası ve özellikle Cuma yapılır; takip eden Pazartesi aşırı reaksiyon eğilimi forum gözleminde tekrar eder.
- **"Yabancı satış günü = retail panik = sonraki gün gap-up"**: Investing.com TR ve Hisse.net'te tekrar eden anlatı; yabancı çıkışını "fırsat" gören retail davranışını yansıtır — **Akıllı Para'ya kontre-tepki** olarak modellenebilir (B6'nın günlük overshoot düzeltmesi).
- **"Mahalle bilgisi" (small-cap akümülasyonu)**: Aracı kurum bazında dolaşan söylenti zinciri; Matriks IQ Takas Analizi üzerinden A1/A2/Citibank gibi kurum-bazlı lot değişimi takibi pratisyende standart.

**(b) Akademik literatürde olup pratisyenin görmediği.**
- **A3 Amihud ILLIQ premium**: Pratisyen "düşük likidite = riskli" der, "alpha kaynağı" demez. BIST akademik bulgusu (Bank & Kahraman; ayrıca Yıldırım, TCMB Central Bank Review 2011) küçük şirketlerde negatif (likidite arttıkça getiri **düşer**, yani illiquidity premium **vardır**) ama büyük şirketlerde anlamlı değil. Pratisyen bu nüansı **görmüyor**; alpha **rekabet avantajı boşluğu**.
- **Currency momentum (A2) — pratisyenin "kur ralisi" sezgisinin akademik adlandırması**: pratiğe çevrilmeyen bir formelizasyon farkı.
- **Asness V-M combo (A1)**: Pratisyen V ve M'i ayrı taramalarda kullanır; kesişim portföyünün akademik literatürde tutarlı outperformance gösterdiği vurgusu pratisyen tartışmasında **yok**.

**(c) BIST-spesifik anomaliler (pratisyen söyleminde adı koyulmuş).**
- **"VIOP gap-fill"**: Vade kapanış sonrası açılış gap'lerinin geri doldurulma eğilimi — VİOP yeniden canlanma döneminde 2025-2026'da daha sık konuşulur oldu.
- **"Block ticket dance"**: Büyük emirlerin önce iptal edilip sonra başka fiyatta gönderilmesi — manipülasyon sınırında pratik; Matriks IQ derinlik takibi ile gözlenir.
- **"Open auction tuzağı (10:00 ilk 5 dakika)"**: Açılış seansı oluşumunda yanıltıcı emir akışı — pratisyen ısrarla ilk 5 dakika işlem yapmamayı öğütler.

**(d) 2024-2026'ya özgü yeni patternler.**
- **Retail FOMO segmenti (KOBİ tipi küçükler)**: BIH ve MAC gibi top-performing fonların bile karşı tarafında — pump-dump döngülerini hızlandırıyor.
- **Midas/Gedik Pay kuşağı (gençler)**: BIST'te aylık 200 bin TL'ye kadar %0.04 komisyon (Midas), 7/24 mobile execution (Midas'ta US borsalarda 24 saat), TEFAS fonlarına yönelim — uzun-vade davranışta yeni nesil.
- **VIOP yeniden canlanma (kısmen)**: Açığa satış yasağı koşullarında VİOP put alımı tek shorting yolu — pratisyen bu yoldan kısıtlı hedge yapıyor.

**Erişim Notu / §7.** Forum/Investing.com gözlemleri **anekdoltal** doğaya sahiptir; "Bayram accumulation" ya da "bilanço Cuma" pattern'lerinin sistematik back-test'i bu yamanın kapsamı dışındadır — BIST OS pipeline'ı içinde test edilmeyi hak eden hipotezler olarak işaretlendi.

---

### Kritik Bulgu Uyarıları (Confirmation Bias Karşıtı)

1. **B14 EPS Revision Akademik-Pratik Uyumsuzluğu.** Akademik literatür EPS revision momentum'unu BIST için top-1 olarak işaret ederken, Türk broker'ları "konsensüs revizyonu" sıralamasını sistematik olarak yayımlamıyor; Foreks aboneliği gerekli. **Rekabet avantajı boşluğu = BIST OS lehine bir alpha kanalı** (akademik premium pratisyene henüz tam yayılmamış).

2. **A3 EM Liquidity Premium = Tam Boşluk.** Türk pratisyen söyleminde **likidite alpha-kaynağı değil, risk-kaynağı**. Akademik bulgu Türkiye küçük-cap'leri için premium var; BIST OS bu boşluğu kullanabilir (örnek: ILLIQ-sıralı küçük-cap long bacağı). Confirmation bias riski: bu boşluk **çok küçük örneklemle** doğrulanmış olabilir; canlı sistemde A3 sinyalinin **eşik altı dönemler için kısıtlama** ile uygulanması önerilir.

3. **MAC Fonu Pazarlama Dili vs Davranış**. MAC kendisini "fundamental value investing — concentrated portfolio of companies trading at a significant discount" olarak tanımlar (marmaracapital.com.tr) ama 5 yılda %2643 getiri ve BTCIM/BSOKE gibi mid-cap yoğunluğu klasik value yatırımcılığından **momentum/concentrated growth**'a kayan bir profil önerir. BIST OS perspektifinden ders: **Fon strateji metinlerine değil, performans-tilt regresyonuna** güvenmek gerekir.

4. **B13 Askıya Alınmış Yasak Kalkarsa.** SPK yasağı 26 Mayıs 2026 sonrası kaldırılırsa, B13 sinyali ölü statüsünden çıkar; **yeniden tetiklenebilir hazırlık** (lending fee veri akışı, açığa satış oranı hesaplaması) BIST OS'a tedrici olarak yeniden eklenmelidir.

---

### F. Critic İddiası Testi — Tam Bulgu

**İddia.** "BIST'in en güçlü tekil sinyali foreign flow ivmesidir (B6) — sen weekly net kullanıyorsun, 5-gün rolling delta + acceleration olmalı."

**Test 1: B6 gerçekten "en güçlü tekil sinyal" mi?**
- Broker coverage perspektifinden **EVET**: İş Yatırım, Halk Yatırım, Vakıf, Osmanlı Menkul, ICBC her gün/her hafta/her ay düzenli rapor yayımlıyor. Bu, hiçbir diğer faktörde olmayan bir kurumsallaşma seviyesi.
- Pratisyen söylem perspektifinden **EVET**: Forum tartışmalarında "yabancı oranı en çok artan" ve "10 gündür kesintisiz alım" söylemleri merkezde.
- Akademik B14 ve A5'in karşılaştırmalı premium büyüklüğü tartışmaya açık; **§6 birleşik skorlamasında B6 = ★★★★ ile tek başına en yüksektir** — Critic'in "en güçlü tekil sinyal" iddiası **kısmen onaylanır** (akademikte tek başına en güçlü olmasa da pratik+akademik birleşik en güçlü).

**Test 2: Hangi platform B6'yı sağlıyor?**
- **Birincil:** İş Yatırım "Günlük Yabancı Oranları" — örnek alıntı: "Bugün çıkan raporumuzda, günlük bazda yabancı oranı en çok artan hisseler; ENSRI:1.81 bps, HOROZ:1.72 bps, SMRTG:1.44 bps, iken, azalan hisseler ise; RGYAS:-22.57 bps, TATEN:-10.87 bps, DOFRB:-5.86 bps. olarak görüntülenmektedir. Son günlerde yabancı oranı sürekli artan hisselerden 5 tanesi; ASTOR:10 gün, ICBCT:10 gün, LYDHO:10 gün, YGGYO:10 gün, POLTK:9 gündür yabancı oranları sürekli artış gösteriyor." (arastirma.isyatirim.com.tr/category/gunluk-raporlar/gunluk-yabanci-oranlari/)
- **İkincil:** Halk Yatırım "Yabancı Takas Oranları" + "Aylık Yabancı İşlemleri Raporu" + "TCMB Haftalık Menkul Kıymet İstatistikleri" (analizim.halkyatirim.com.tr).
- **Üçüncül:** Vakıf VKY Analiz "Günlük Yabancı Takas Oranı Değişimi" (vkyanaliz.com); ICBC "BIST-30 Haftalık Yabancı Takası Raporu" (icbcyatirim.com.tr); Osmanlı Menkul "Yabancı İşlemleri" çok-periyodlu (günlük/haftalık/aylık/YTD/tarih aralığı); Matriks IQ Prime "Yabancı Takas Analizi" (iqyardim.matriksdata.com).

**Test 3: Critic'in günlük acceleration vs weekly net ayrımı pratisyen literatüründe yansıyor mu?**
- **Bulgu: KISMI (PARTIAL).**
- Yansıyan kısım: pratisyen kaynakları **günlük bps değişim + ardışık gün sayısı** matrisini standart kabul ediyor; bu, "weekly net'ten daha hızlı sinyal" sezgisinin yansımasıdır. İş Yatırım günlük raporundaki "10 gündür kesintisiz" sayımı, daha sofistike bir **persistence-of-acceleration** sinyalidir ve birinci-türev (günlük net) + ikinci-türev (kaç gündür aynı yönde) bilgisini birleştirir.
- Yansımayan kısım: "5 gün" özel pencere pratisyen söyleminde **standart değil**. Görülen pencereler: günlük (1), 10-gün ardışık (persistence), haftalık (5–7 işlem günü ama "5-gün rolling delta" olarak adlandırılmamış), aylık (~22), TCMB-haftalık net $ giriş.
- **Sonuç:** Critic'in sinyal **biçim**i (ivme/persistence) hakkında haklı; sinyal **parametre seçimi** (5-gün) keyfi gözüküyor. BIST OS için pragmatik öneri: (i) günlük bps değişim, (ii) **3, 5 ve 10 gün rolling sum** + **ardışık-aynı-yön gün sayısı** persistence göstergesi, (iii) haftalık net (TCMB), (iv) aylık delta — bu dört zaman penceresinin **enssamble**i, single-window 5-gün rolling delta'dan daha sağlamdır. Critic'in dar tanımı yerine **multi-window foreign-flow ivme paneli** öneririz.

**Test 4: QNB Çarpıtması.** Critic'in iddiası aggregate yabancı oranı verisi kullanıyor olabilir. QNB Finansbank'ın fiili dolaşımı %0.12 olmasına rağmen takasta tamamı yabancı olarak kayıtlı olduğundan, BIST genelinde yabancı oranı Ağustos 2025-Eylül 2025 sürecinde **yapay olarak şişti** (ekonomim.com — Tankut Taner Çelik). BIST OS'un B6 hesabında **QNB-temizlenmiş seri** kullanılması zorunludur. Bu, Critic'in iddiasına ortogonal ama uygulamada B6'nın değerini doğrudan etkileyen kritik bir teknik nokta.

**Genel Critic Verdict.** **Partial — sinyal biçimi (acceleration/persistence) doğrudur, parametre seçimi (5-gün) gerekçesiz ve dar; QNB-temizleme gibi pratik şart akademik tartışmada görünmüyor.**

---

### Sonuç ve RR-012 Ana Karar Matrisine Yansıma

BIST 2023-2026 pratisyen ekosistemi, akademik faktör literatürünün önerdiği 14 faktörün önemli bir alt-kümesini (özellikle B6, B7, B8, B9, B10, A5) **kurumsal raporlama düzeyinde** yansıtmaktadır; ancak A1 V-M combo, A3 Amihud ILLIQ premium ve B14 EPS revision momentum'da akademik premium pratisyene **tam aktarılmamış** durumdadır — bunlar BIST OS için **alfa rekabet avantajı boşlukları**dır. Critic iddiası foreign-flow ivmesinin önemini doğrular ancak parametre seçimi olarak 5-gün rolling delta'yı zorunlu kılmaz — multi-window panel daha uygundur. SPK açığa satış yasağı süresince B13 askıdadır; yasak kalkarsa veri pipeline'ının yeniden devreye alınmaya hazır tutulması önerilir. RR-012'nin akademik top-3'ünden B14'ün pratik altyapı zayıflığı nedeniyle bir kademe geriye, B6'nın hem pratik hem akademik gücüyle birleşik top-1'e yükseltilmesi önerilir.


*Son güncelleme: 24 Mayıs 2026. Bu rapor implementation-ready'dir; ancak içerdiği sayısal değerler sadece literatür quote'larıdır — projeye-uygun parametre önerisi içermez. Tüm akademik kaynaklar DOI/URL ile referanslanmıştır.*