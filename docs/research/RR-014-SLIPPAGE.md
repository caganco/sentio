# BIST Slippage ve Market Impact Modellemesi: Ham Araştırma Bulguları

## TL;DR
- Almgren-Chriss (2001) lineer geçici/kalıcı etki çerçevesi 2005'te Almgren et al. tarafından Citigroup verisiyle empirik olarak revize edilmiştir; modern literatürde temporary impact ∝ (Q/ADV)^0.6 (Almgren et al. 2005, *Risk* 18(7), 58-62) ve I ∝ σ·√(Q/V) (Tóth et al. 2011, *Phys. Rev. X*; Gatheral 2010, *Quant. Finance*) baskın iki form olarak öne çıkmakta; lineer model artık empirik destek bulamamaktadır.
- BIST pay piyasası 2024 yılında toplam 34,3 trilyon TL işlem hacmi (Borsa İstanbul 2024 Annual Integrated Report; ~250 işlem gününe bölünerek hesaplanan günlük ortalama ≈ 137 milyar TL — raporda günlük ortalama doğrudan yayımlanmamıştır), WFE'ye göre dünyada turnover velocity sıralamasında 3.; 1 Mart 2026'da başlatılan açığa satış yasağı en az altı kez uzatılmış, son durumda SPK'nın 08.05.2026 tarih ve 30/903 sayılı kararıyla 26 Mayıs 2026 seans sonuna kadar yürürlükte kalmıştır.
- BIST'e özgü Almgren-Chriss kalibrasyonu yapılmış birincil akademik çalışma bulunamamıştır; Türk literatüründe Ekinci (2003, SSRN 410842), Çobandağ Güloğlu & Ekinci (2016, JEFA 3(3)), Ersan & Ekinci (2016, *Borsa İstanbul Review* 16(4)) ve Şensoy (2019, *Borsa İstanbul Review* 19) BIST mikroyapı/spread/likidite konularını işlemekte, ancak BIST-spesifik market impact (η, γ) katsayıları yayımlanmış kaynaklarda doğrulanamamıştır.

---

## Key Findings

### A. AKADEMİK TEMEL

#### A1. Almgren-Chriss (2001)

**SORU:** Almgren-Chriss (2001) framework'ünün orijinal bulguları ve varsayımları nedir?

**BULGULAR:**
- Almgren, R. & Chriss, N. (2001). "Optimal Execution of Portfolio Transactions." *Journal of Risk* 3(2), 5-39. DOI: 10.21314/JOR.2001.041. — Kaynak: https://www.scirp.org/reference/referencespapers?referenceid=1700171 ; https://scispace.com/papers/optimal-execution-of-portfolio-transactions-34npaowqcj
- Abstract verbatim: "We consider the execution of portfolio transactions with the aim of minimizing a combination of volatility risk and transaction costs arising from permanent and temporary market impact. For a simple linear cost model, we explicitly construct the efficient frontier in the space of time-dependent liquidation strategies." — Kaynak: https://scispace.com/papers/optimal-execution-of-portfolio-transactions-34npaowqcj
- Model **lineer cost model** (linear impact) varsayımı kullanır. Temporary impact (kısa süreli, sadece o periyot fiyatını etkiler) ve permanent impact (kalıcı, gelecek fiyatları etkiler) ayrımı yapılır. — Kaynak: Vaes & Hauser (2020), arxiv 1810.11454: "the impact of the trades on the price dynamics is divided in a temporary and a permanent impact. The temporary component refers to the price shift due to the lack of resilience of the limit orders in the book… The permanent impact, on the other hand, refers to the shift of the market prices in future trading periods due to the temporary exhaustion of the market order book."
- Risk aversion parametresi (λ) Mean-Variance / kuadratik fayda fonksiyonu içinde efficient frontier konstrüksiyonunda kullanılır; L-VaR (Liquidity-adjusted VaR) kavramı bu paper'da tanıtılmıştır. — Kaynak: https://scispace.com/papers/optimal-execution-of-portfolio-transactions-34npaowqcj
- Atıf sayısı: 1.621 (SciSpace verisi).

**BULUNAMADI:** Almgren-Chriss framework'ünün özellikle retail trader veya küçük portföy için adapte edilmiş bir versiyonu literatürde doğrudan bulunmamaktadır. Çerçeve kurumsal yatırımcılar için tasarlanmış olup retail uyarlama orijinal kaynaklarda yer almamaktadır.

#### A2. Linear vs Square-Root Market Impact

**SORU:** Lineer ve karekök etki modelleri empirik olarak hangisi daha doğru?

**BULGULAR:**
- Almgren, R., Thum, C., Hauptmann, E. & Li, H. (2005). "Direct Estimation of Equity Market Impact." *Risk* 18(7), 58-62. Working paper tarihi 10 Mayıs 2005; Risk Magazine'in Temmuz 2005 sayısında yayımlandı. Veri seti: yaklaşık 700.000 ABD hisse senedi emri, alış/satış yönü her emir için bilinen, Citigroup equity trading desks tarafından Aralık 2001-Haziran 2003 (19 ay) periyodu için yürütülmüş. — Kaynak: https://www.cis.upenn.edu/~mkearns/finread/costestim.pdf
- Verbatim: "We reject the common square-root model for temporary impact as function of trade rate, in favor of a **3/5 power law** across the range of order sizes considered." — Kaynak: https://www.cis.upenn.edu/~mkearns/finread/costestim.pdf (Almgren et al. 2005, abstract).
- Gatheral, J. (2010). "No-Dynamic-Arbitrage and Market Impact." *Quantitative Finance* 10(7), 749-759. DOI: 10.1080/14697680903373692. Received 31 Oct 2008, accepted 25 Sep 2009, published online 6 April 2010. — Kaynak: https://www.tandfonline.com/doi/abs/10.1080/14697680903373692
- Verbatim: "We show that the widely-assumed exponential decay of market impact is compatible only with linear market impact. We derive various inequalities relating the typical shape of the observed market impact function to the decay of market impact, noting that empirically, these inequalities are typically close to being equalities." — Kaynak: https://ideas.repec.org/a/taf/quantf/v10y2010i7p749-759.html
- Bucci, F. & Mastromatteo, I. ve diğerleri (2019) "Impact is not just volatility" — square-root law'ı 0.1–0.5 power exponent aralığında doğrulayan kapsamlı literatür özeti içerir. — Kaynak: https://arxiv.org/pdf/1905.04569
- Empirik sonuç: Square-root yasası exponent metriğe göre 0.5'in altında veya üstünde olabilmektedir; L1 estimasyonda daha düşük, log-log fitte daha yüksek değerler. — Kaynak: https://arxiv.org/pdf/1412.0217 (Market impacts and the life cycle of investors orders)

**BULUNAMADI:** "1% ADV trade → 5 bps (linear) vs 15-25 bps (square-root)" şeklindeki kullanıcı sorusunda verilen kalibrasyon değerlerinin literatürdeki sayısal kaynağı doğrudan tespit edilemedi; bu değerler farklı paper'larda farklı σ ve ADV varsayımlarıyla türetilebilir.

#### A3. Emerging Market Market Impact Literatürü

**SORU:** EM piyasalar için spesifik bulgular nelerdir, BIST araştırması mevcut mu?

**BULGULAR:**
- Tóth, B., Lempérière, Y., Deremble, C., de Lataillade, J., Kockelkoren, J. & Bouchaud, J.-P. (2011). "Anomalous Price Impact and the Critical Nature of Liquidity in Financial Markets." *Physical Review X* 1(2), 021006, 31 Ekim 2011. — Kaynak: https://link.aps.org/doi/10.1103/PhysRevX.1.021006
- Abstract verbatim: "We propose a dynamical theory of market liquidity that predicts that the average supply/demand profile is V shaped and vanishes around the current price. … the anomalously small local liquidity induces a breakdown of the linear response and a diverging impact of small orders, explaining the 'square-root' impact law, for which we provide additional empirical support." — Kaynak: https://link.aps.org/doi/10.1103/PhysRevX.1.021006
- Bouchaud, J.-P., Farmer, J.D., Lillo, F. "How markets slowly digest changes in supply and demand" — kalıcı etki / order flow uzun hafıza tezi (Tóth 2011 ve diğer paperlarda atıflı).
- Bouchaud, J.-P., Gefen, Y., Potters, M. & Wyart, M. (2004). "Fluctuations and response in financial markets: the subtle nature of 'random' price changes." *Quantitative Finance* 4(2), 176-190. DOI: 10.1088/1469-7688/4/2/007 — Paris borsası Trades-and-Quotes verisi kullanılmıştır. — Kaynak: IDEAS/RePEc handle taf:quantf:v:4:y:2004:i:2:p:176-190 ; arXiv: cond-mat/0307332.
- Lesmond, D. (2005). "Liquidity of Emerging Markets." *Journal of Financial Economics*. Verbatim: "Transaction costs are 10 basis points higher, using the LOT measure, and **price impact costs are 1.7% higher**, using Amihud's measure, for countries and times of reduced political stability." — Kaynak: https://www.sciencedirect.com/science/article/abs/pii/S0304405X05000176
- Kang, W. & Zhang, H. (2014). "Measuring liquidity in emerging markets." *Pacific-Basin Finance Journal* 27, 49-71. — AdjILLIQ measure önerisi. — Kaynak: https://ideas.repec.org/a/eee/pacfin/v27y2014icp49-71.html
- BIST literatürü:
  - Ekinci, C. (2003). "A Statistical Analysis of Intraday Liquidity, Returns and Volatility of an Individual Stock from the Istanbul Stock Exchange." SSRN. Verbatim: "The results show that liquidity-related variables' path can be described by an asymmetric 'W' curve, namely an 'inverse J' curve in the morning session and a 'U' curve in the afternoon session." — Kaynak: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=410842
  - Çobandağ Güloğlu, Z. & Ekinci, C. (2016). "A Comparison of Bid-Ask Spread Proxies: Evidence from Borsa Istanbul Futures." *Journal of Economics, Finance and Accounting* 3(3), 244-254. — Kaynak: https://dergipark.org.tr/en/pub/jefa/article/350095 ; SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3823761
  - Ersan, O. & Ekinci, C. (2016). "Algorithmic and High-frequency Trading in Borsa Istanbul." *Borsa Istanbul Review* 16(4), 233-248.
  - Şensoy, A. (2019). "Commonality in liquidity in an emerging market: Liquidity risk in Borsa Istanbul." *Borsa İstanbul Review* 19, 297-309. https://doi.org/10.1016/j.bir.2019.06.002
  - Çobandağ Güloğlu, Z. (2018). PhD Thesis, İTÜ: "Bid-Ask Spread, Liquidity and the Effects of Firm-Level and Market-Level Features." — Kaynak: https://sites.google.com/view/cumhurekinci/research
  - TCMB Working Paper 12/26 (Bildik/Ekinci): "An Analysis of Intraday Patterns and Liquidity on the Istanbul Stock Exchange." — Kaynak: https://www.tcmb.gov.tr/wps/wcm/connect/d1fb3451-8746-4c38-a8a9-dba0648c6760/WP1226.pdf
  - DergiPark / Ömer Halisdemir IIBF: "We examine the effect of liquidity on return in the stock market of Turkey using data of 265 companies for the period 2/01/2002 through 2/02/2017. We use Corwin-Schultz bid-ask spread estimator, high–low ratio and Amihud illiquidity measure as liquidity variables… We find that illiquidity has negative effect on both daily and monthly returns… negative effect is stronger for smaller companies." — Kaynak: https://dergipark.org.tr/en/pub/ohuiibf/article/317710

**BULUNAMADI:** 
- "EM markets ABD'den 2-3× yüksek impact" iddiasının spesifik sayısal doğrulaması bulunamadı. Lesmond (2005) sadece "1.7% higher price impact for politically unstable countries" diyor.
- Şinasi Sözer 2018 BIST market impact çalışmasına dair kaynak bulunamadı.
- BIST'e özgü Almgren-Chriss kalibrasyonu (η, γ katsayıları için spesifik sayısal değerler) içeren akademik çalışma bulunamadı.

#### A4. Retail-relevant Frameworks: Perold, Roll

**SORU:** Implementation Shortfall ve Roll spread measure formülleri nedir?

**BULGULAR:**
- Perold, A.F. (1988). "The Implementation Shortfall: Paper versus Reality." *Journal of Portfolio Management* 14(3), 4-9 (Spring 1988). — Kaynak: https://www.hbs.edu/faculty/Pages/item.aspx?num=2083 ; https://www.proquest.com/openview/18cd0f25dd0ff3bbf37b0aadf33d17c6/1
- Tanım: "Implementation Shortfall (IS) is defined as the difference in price between the time a portfolio manager makes an investment decision and the actual price achieved. Another component is the opportunity cost of any quantity unexecuted during the implementation." — Kaynak: https://www.quantitativebrokers.com/blog/a-brief-history-of-implementation-shortfall
- Roll, R. (1984). "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market." *Journal of Finance* 39(4), 1127-1139. DOI: 10.1111/j.1540-6261.1984.tb03897.x — Kaynak: https://www.bauer.uh.edu/rsusmel/phd/roll1984.pdf
- Formül: **Spread = 2·√(−cov(Δp_t, Δp_{t-1}))** koşuluyla cov < 0. Verbatim: "the effective bid-ask spread can be measured by Spread = √2−cov where 'cov' is the first-order serial covariance of price changes." — Kaynak: https://authors.library.caltech.edu/records/afwsc-6bb61 (Caltech kayıt). 
- Kısıt: "the more sophisticated model of Roll (1984), which uses autocovariance of price changes, has the well-known limitation of validity only for observations that exhibit negative autocovariance between asset returns. … instances of positive autocovariance result in complex numbers in the model formulation." — Kaynak: https://www.yu.edu/sites/default/files/inline-files/20201202_AbsRoll.pdf
- VWAP/TWAP execution BIST retail kullanımı için orijinal akademik kaynak bulunamadı.

**BULUNAMADI:** BIST'te retail VWAP/TWAP kullanım istatistikleri.

---

### B. BIST LİKİDİTE YAPISI (2024-2026)

#### B1. BIST Hacim Tier'ları

**SORU:** BIST endeksleri ve mega/mid/small-cap hisseler için gerçek hacim verileri nedir?

**BULGULAR:**
- **Borsa İstanbul 2024 Annual Integrated Report (resmi):** Pay piyasası toplam işlem değeri 2024 = **34,3 trilyon TL** (2023: 32,7 trilyon TL). Verbatim: "Total traded value: TL 34.3 trillion (2023: TL 32.7 trillion)." — Kaynak: https://www.borsaistanbul.com/files/2024-annual-integrated-report.pdf
- Tek gün rekoru: "The equity market transaction volume broke a record with a daily traded value of TL 276.2 billion on 21 May." (2024). — Kaynak: aynı annual report.
- Toplam piyasa değeri 31.12.2024 = 13,42 trilyon TL (2023: 10,04 trilyon TL). — aynı kaynak.
- HFT payı: "The ratio of High Frequency Trading (HFT) transactions in the Equity Market's total traded volume became 30% on yearly average." — aynı kaynak.
- Dünya sıralaması 2024: Turnover velocity'de 3., traded value'da 16., market cap'te 25. — aynı kaynak.
- Tüm Borsa İstanbul işlemleri (tüm pazarlar) 2024 = 225,6 trilyon TL (+%188 YoY). — aynı kaynak.
- BIST 100 zirve 22 Temmuz 2024: 11.172,75; BIST 30 intraday zirve aynı gün: 12.263,04. — aynı kaynak.
- Yatırımcı sayısı: bakiyeli bireysel yatırımcı sayısı 7,7 milyon (2023) → 6,8 milyon (2024) düşmüştür. — aynı kaynak.
- **WFE 2025 verisi** (Borsa İstanbul resmi paylaşımı): "Average daily trading value reached USD 35 billion in debt securities, **USD 5 billion in equities** and USD 2 billion in derivatives in 2025." — Kaynak: https://focus.world-exchanges.org/articles/borsa-istanbul-64thwfega ; https://gaam2025.wfecm.com/
- Türetilmiş yaklaşık ortalama (kaynaktan değil hesaplama): 34,3 trilyon TL / ~250 işlem günü ≈ **137 milyar TL/gün** (2024). Borsa İstanbul 2024 Annual Integrated Report günlük ortalama hacmi ayrıca yayımlamamaktadır; bu değer yıllık toplamdan türetilmiştir. 21 Mayıs 2024 rekor günü bu türetilmiş ortalamanın ~2 katıdır.
- **Hisse bazlı veriler (snapshot, ortalama değil):**
  - **AKBNK:** Investing.com 12-aylık ortalama: 78.516.965 lot/gün, 52-hafta aralığı 47,88-93,50 TL. — Kaynak: https://www.investing.com/equities/akbank-historical-data
  - **AKBNK** tek gün örnek (Bullsyatirim verisi): "Günlük İşlem Hacmi (TL): 9.913.742.524,00 TL" (~9,9 milyar TL tek gün). — Kaynak: https://bullsyatirim.com/hisse-analiz/akbnk
  - **GARAN:** Investing.com ortalama: 34.997.831 lot/gün, 52-hafta aralığı 98,75-169,70 TL. Implied ~4,7 milyar TL/gün ortalama. — Kaynak: https://www.investing.com/equities/garanti-bankasi-historical-data
  - **GARAN** 31 Ekim 2025 tek gün örnek (StockInvest.us): "57 million shares … for approximately TRY 7.68 billion." — Kaynak: https://stockinvest.us/stock/GARAN.IS
  - **THYAO:** Investing.com ortalama: 56.263.294 lot/gün, 52-hafta aralığı 249,20-352,50 TL. — Kaynak: https://www.investing.com/equities/turk-hava-yollari-historical-data

**BULUNAMADI:** TUPRS, KCHOL, TCELL, ASELS, OTKAR, FROTO, PETKM, EREGL, ISCTR, YKBNK için spesifik ortalama günlük işlem hacmi sayıları (TL). ENERY, AKSEN, AGYO small/mikro-cap hisseleri için verim hacim verisi. BIST 30/BIST 50 endeks bazında ayrıştırılmış günlük hacim ortalamaları (annual reportta sadece toplam pay piyasası verisi var).

#### B2. BIST Spread / Tick Size

**SORU:** BIST tick size kuralları ve tipik bid-ask spread'leri nedir?

**BULGULAR:**
- Borsa İstanbul 28.08.2023 tarihli 19412 sayılı duyuru, 6 Kasım 2023'ten itibaren geçerli yeni fiyat adımı tablosu. — Kaynak: https://borsaistanbul.com/tr/sayfa/493/pay-piyasasi-piyasa-isleyisi ; https://gedik.com/duyurular-ve-kampanyalar/duyurular/bist-fiyat-adimi-ve-kotasyon-yayilma-araliklari-duzenlemeleri
- **Pay senetleri için fiyat adımı tablosu (6 Kasım 2023 itibarıyla):**
  - 0,01-19,90 TL → fiyat adımı 0,01 TL
  - 20,00-49,98 TL → fiyat adımı 0,02 TL
  - 50,00-99,95 TL → fiyat adımı 0,05 TL
  - 100,00 TL ve üzeri → fiyat adımı 0,10 TL
- **BYF/GYF/GSYF için tablosu:**
  - 0,01-49,99 TL → 0,01 TL
  - 50,00-99,98 TL → 0,02 TL
  - 100,00-249,95 TL → 0,05 TL
  - 250,00 TL ve üzeri → 0,10 TL
- Varant ve sertifikalarda fiyat adımı her seviyede 0,01 TL (1 kuruş), kuruş altı hassasiyette 10 bps (0,001 TL) gösterim. — Kaynak: https://borsaistanbul.com/tr/sayfa/493/pay-piyasasi-piyasa-isleyisi
- Maksimum kotasyon yayılma aralığı (piyasa yapıcılar için, 6 Kasım 2023):
  - 0,01-1 TL → 6 adım
  - 1,01-2,50 TL → 8 adım
  - 2,51-10 TL → 10 adım
  - 10,01 ve üzeri → %1
  - Kaynak: https://www.bloomberght.com/bist-ten-fiyat-adimi-ve-kotasyon-araliklarina-yeni-duzenleme-2337339
- BIST 30 paylarda **Orta Nokta (Mid-Point) emirler** mevcut. — Kaynak: https://borsaistanbul.com/tr/sayfa/493/pay-piyasasi-piyasa-isleyisi

**BULUNAMADI:** Mega-cap/mid-cap/small-cap için tipik proporsyonel bid-ask spread sayıları (bps) — Borsa İstanbul resmi istatistik yayımı erişilmedi. Çobandağ Güloğlu & Ekinci (2016) BIST Futures için spread proxy karşılaştırması yapmış olsa da pay piyasası için spesifik bps değeri bu araştırmada tespit edilemedi.

#### B3. BIST Intraday Volume Profile

**SORU:** BIST seans saatleri ve gün içi hacim dağılımı nasıl?

**BULGULAR:**
- **Pay piyasası seans saatleri (tam gün):**
  - 09:40-09:55: Açılış seansı emir toplama (tek fiyat)
  - 09:55-10:00: Açılış eşleştirme
  - 10:00-13:00: Sürekli işlem (sabah)
  - 13:00-13:55: Gün ortası tek fiyat emir toplama
  - 13:55-14:00: Eşleştirme
  - 14:00-18:00: Sürekli işlem (öğleden sonra)
  - 18:00-18:01: Tek fiyatlı marj yayını
  - 18:01-18:05: Kapanış seansı emir toplama (4 dakika)
  - 18:05-18:07: Fiyat belirleme ve kapanış seansı işlemleri (2 dakika)
  - 18:08-18:10: Kapanış fiyatından işlemler aşaması (2 dakika)
  - Kaynak: https://www.borsaistanbul.com/tr/sayfa/340/kapanis-seansi ; https://www.borsaistanbul.com/en/markets/equity-market/trading-hours
- Yarım gün (resmi tatil): 09:40 açılış, 12:30-12:40 arası kapanış. — Kaynak: https://slayz.app/borsa-istanbul-acilis-kapanis-saati-nedir
- Kapanış seansı fiyat marjı: Son işlem fiyatının ±%3'ü içinde, ancak ±%20 günlük fiyat marjı sınırını aşamaz. — Kaynak: https://www.borsaistanbul.com/en/markets/equity-market/market-functioning
- Market-Wide Circuit Breaker (MWCB): %6 eşik, gün içinde bir kez tetiklenir; tetiklenme durumunda açığa satış işlemlerinde "uptick rule" uygulanır. — Kaynak: aynı.
- Ekinci (2003) BIST intraday likidite paterni: "asymmetric 'W' curve, namely an 'inverse J' curve in the morning session and a 'U' curve in the afternoon session." — Kaynak: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=410842
- TCMB Working Paper 12/26 ISE intraday paterni analizi mevcut. — Kaynak: https://www.tcmb.gov.tr/wps/wcm/connect/d1fb3451-8746-4c38-a8a9-dba0648c6760/WP1226.pdf

**BULUNAMADI:** Gün içi hacim yüzdesel dağılım (örn. açılış %X, öğle %Y, kapanış %Z) için kantitatif sayısal değer; closing auction'ın günlük hacme oranı için BIST resmi raporu.

#### B4. SPK Açığa Satış Yasağı (Mart 2026)

**SORU:** Mart 2026 SPK açığa satış yasağının kapsamı ve mevcut durum nedir?

**BULGULAR:**
- **İlk yasak:** SPK Karar Organı'nın 01.03.2026 tarih ve 11/417 sayılı kararı uyarınca, **2 Mart 2026'dan 6 Mart 2026 seans sonuna kadar** BIST pay piyasalarında açığa satış işlemleri yasaklandı. Ayrıca aynı kararla "kredili sermaye piyasası aracı işlemlerinin devamı süresince özkaynak koruma oranının asgari yüzde 35 olması hususundaki hükmün … özkaynak oranı asgari yüzde 20 olacak şekilde esnek olarak uygulanabilmesine" karar verildi (Seri:V No:65 Tebliğ md. 17 esnetildi). Gün içi açığa satış tuşuna basılmadan açılıp kapatılan pozisyonlar da kapsamda. — Kaynak: https://bigpara.hurriyet.com.tr/haberler/borsa-istanbul-haberleri/borsada-aciga-satisa-yasak-karari_ID1625473/ ; https://www.sozcu.com.tr/spk-aciga-satis-islemlerinin-yasaklanmasina-karar-verdi-p297891
- **1. uzatma:** 8 Mart 2026 / 13/473 sayılı karar → **13 Mart 2026 seans sonuna** kadar uzatıldı. — Kaynak: https://www.bloomberght.com/spk-dan-aciga-satis-icin-sure-uzatma-karari-3771269 ; https://tr.investing.com/news/economy-news/spk-acga-sats--yasag-13-mart-seans-sonuna-kadar-devam-edecek-3799466
- **2. uzatma:** 15 Mart 2026 / 15/517 sayılı karar → **27 Mart 2026 seans sonuna** kadar. — Kaynak: https://www.endeks24.com/spk-borsada-aciga-satis-yasagini-mart-sonuna-uzatti ; https://www.borsaningundemi.com/haber/spkdan-aciga-satis-yasagi-icin-sure-uzatma-karari-1887871
- **3. uzatma:** 28 Mart 2026 / 19/625 sayılı karar → **10 Nisan 2026 seans sonuna** kadar. — Kaynak: https://www.bloomberght.com/aciga-satis-yasagi-uzatildi-3773107 ; https://www.paraanaliz.com/2026/ekonomi/spk-tedbirleri-uzatti-aciga-satis-yasagi-devam-ediyor-g-138002/
- **4. uzatma:** 11 Nisan 2026 / 24/722 sayılı karar → **24 Nisan 2026 seans sonuna** kadar. — Kaynak: https://www.paraanaliz.com/2026/borsa/spk-duyurdu-aciga-satis-yasagi-ve-kredili-islem-esnekligi-uzatildi-g-139215/ ; https://www.karar.com/ekonomi-haberleri/borsada-aciga-satis-yasaginin-suresi-uzatildi-2041829
- **5. uzatma:** 25.04.2026 / 27/807 sayılı karar → **8 Mayıs 2026 seans sonuna** kadar. (Bloomberght 25.04.2026: "Borsa İstanbul pay piyasalarında uygulanan açığa satış yasağını 8 Mayıs 2026'ya kadar uzattı.")
- **6. uzatma:** SPK 08.05.2026 tarih ve 30/903 sayılı kararı → **26 Mayıs 2026 seans sonuna** kadar. (Yatirimx.com.tr ve Finansopia, 11.05.2026 tarihli haberleri; ayrıca Borsaningündemi 25.04.2026 sonrası tarih düzeltmesinde "düzenleme altıncı kez uzatılmış oldu" ifadesi.) — Kaynak: https://www.borsaningundemi.com/haber/spkdan-aciga-satis-yasagina-bir-uzatma-daha-1894164
- Gerekçe (gazete kaynakları): "28 Şubat 2026 tarihinde başlayan ABD-İran savaşı, küresel ve yerel piyasalarda sert dalgalanmalara neden olmuştu." — Kaynak: https://www.paraanaliz.com/2026/borsa/spk-duyurdu-aciga-satis-yasagi-ve-kredili-islem-esnekligi-uzatildi-g-139215/
- İlgili paralel önlem: Borsa İstanbul 1 Mart 2026 kararıyla pay piyasası emir/işlem oranını (OTR) **5:1'den 3:1'e** düşürdü. — Kaynak: https://www.sozcu.com.tr/spk-aciga-satis-islemlerinin-yasaklanmasina-karar-verdi-p297891

**BULUNAMADI:** Açığa satış yasağının bid-ask spread veya günlük hacim üzerinde gerçek etkisini ölçen ampirik veri / akademik çalışma (2026 yasak dönemine özgü) — yasak hala devam etmekte (rapor tarihi: 24 Mayıs 2026).

---

### C. KÜÇÜK PORTFÖY / RETAIL BIST'TE

#### C1. Retail Transaction Costs

**SORU:** BIST retail trader maliyetleri nedir?

**BULGULAR:**
- **Damga vergisi:** Sermaye piyasasında yapılan hisse senedi alım-satım işlemleri damga vergisinden muaftır. — Kaynak: https://www.momento.com.tr/bsmv ; EY Türkiye: "Stopaj oranı ister yüzde 10, isterse de yüzde 0 olsun, BİST'te gerçekleştirilen hisse senedi işlemlerinden sağlanan kazançlar, tutarı ne olursa olsun ayrıca beyan edilmiyor." — https://www.ey.com/tr_tr/insights/tax/menkul-kiymetlerin-vergisi
- **BSMV (Banka ve Sigorta Muameleleri Vergisi):** Hisse senedi işleminde **işlem tutarı üzerinden değil, aracı kurumun komisyonu üzerinden %5** olarak uygulanır. — Kaynak: https://gedik.com/yazilar/vergilendirme/bsmv-nedir ; https://www.cottgroup.com/tr/blog/calisma-hayati/item/bsmv-nedir-bsmv-nasil-hesaplanir
- **Temettü stopajı:** 22 Aralık 2024 itibarıyla %10 → **%15**'e yükseltildi. — Kaynak: https://www.ey.com/tr_tr/insights/tax/menkul-kiymetlerin-vergisi
- **Aracı kurum komisyon oranları (örnek değerler 2024-2026):**
  - Garanti BBVA Yatırım sözleşme azami oranı: "yapılan her işlemde (alım/satım) kurum azami **%0,32 (binde 3,2)** oranında komisyon tahsilatı yapma hakkına sahiptir." Hesap açılışı sabit oranı: %0,1950 (binde 1,95). — Kaynak: https://www.garantibbvayatirim.com.tr/duyurular/bsmv-tahsilat-hk ; https://www.garantibbvayatirim.com.tr/urunlerimiz/ucret-ve-komisyonlar
- Midas: Matriks platformu üzerinden onbinde 1 komisyon + BSMV; bazı hesap tipi/promosyonda **%0 komisyon** kampanyaları (Midas, Ortak, Vakıfbank). — Kaynak: https://www.getmidas.com/ucretler/ ; https://yatirimadeger.com/yatirim-hesabi-ac/
- Genel kurum komisyon aralığı (YatırımaDeğer karşılaştırması, Nisan 2025): "komisyon oranları **on binde 1 ile 20** arasında değişmektedir." Verbatim örnek: "200.000 TL için on binde 4 komisyon ödemesi yapan bir borsa yatırımcısı, BSMV hariç 80 TL komisyon masrafı öder. BIST'te alış ve satış işlemlerinde BSMV oranı %5'tir. BSMV dahil bu yatırımcının komisyon masrafı 84 TL'ye ulaşır." — Kaynak: https://yatirimadeger.com/yatirim-hesabi-ac/
- Trive Yatırım: BIST Borçlanma Araçları %0.02 işlem üzerinden; BSMV ayrıca yansıtılır. — Kaynak: https://trive.com.tr/masraf-ve-komisyonlar

**BULUNAMADI:** BIST'te retail vs kurumsal komisyon oranlarının resmi karşılaştırması — KAP "Aracı Kurum Komisyon Oranları Raporu" (https://www.kap.org.tr/ek-indir/4028328d906f40790190a7e6a4bd342c) bu araştırmada açılmadı.

#### C2. Position Size / ADV Eşikleri

**BULUNAMADI:** %1, %5, %10 ADV eşiklerine BIST için ampirik gözlem veya BIST'e özgü emir büyüklüğü-impact regresyon çalışması bu araştırmada tespit edilemedi. Genel literatürde (Almgren 2005, Tóth 2011) impact ölçümleri ABD/AB pazarlarına yöneliktir.

---

### D. PRATİK BIST 2024-2026 PRATİĞİ

**BULUNAMADI:** Türk profesyonel/retail trader pratik gözlemleri (fintwit, YouTube), closing auction kullanım pratiği, mikro-cap pump-dump dinamikleri 2024-2025 BIST, yasak dönemi pratik likidite gözlemleri için doğrudan veri tabanı bu araştırma kapsamında erişilemedi.

---

### E. AKADEMİK KAYNAK DOĞRULAMA

**SORU:** Listedeki 6 kaynağın varlığı doğrulansın.

**BULGULAR:**
1. **Almgren & Chriss (2001)** — DOĞRULANDI. *Journal of Risk* 3(2), 5-39. DOI: 10.21314/JOR.2001.041. — Kaynak: https://scispace.com/papers/optimal-execution-of-portfolio-transactions-34npaowqcj
2. **Gatheral (2010)** "No-Dynamic-Arbitrage and Market Impact" — DOĞRULANDI. *Quantitative Finance* 10(7), 749-759. DOI: 10.1080/14697680903373692. — Kaynak: https://www.tandfonline.com/doi/abs/10.1080/14697680903373692
3. **Tóth, Lempérière, Deremble, de Lataillade, Kockelkoren, Bouchaud (2011)** — DOĞRULANDI. *Physical Review X* 1(2), 021006, 31 Ekim 2011. — Kaynak: https://link.aps.org/doi/10.1103/PhysRevX.1.021006 ; arXiv: 1105.1694.
4. **Bouchaud, Gefen, Potters, Wyart (2004)** "Fluctuations and response in financial markets: the subtle nature of 'random' price changes" — DOĞRULANDI. *Quantitative Finance* 4(2), 176-190. DOI: 10.1088/1469-7688/4/2/007. Paris borsası Trades-and-Quotes verisi kullanılmıştır. — Kaynak: IDEAS/RePEc handle taf:quantf:v:4:y:2004:i:2:p:176-190 ; arXiv: cond-mat/0307332.
5. **Perold (1988)** "The Implementation Shortfall: Paper versus Reality" — DOĞRULANDI. *Journal of Portfolio Management* 14(3), Spring 1988, 4-9. — Kaynak: https://www.hbs.edu/faculty/Pages/item.aspx?num=2083
6. **Roll (1984)** "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market" — DOĞRULANDI. *Journal of Finance* 39(4), Sept 1984, 1127-1139. DOI: 10.1111/j.1540-6261.1984.tb03897.x — Kaynak: https://www.bauer.uh.edu/rsusmel/phd/roll1984.pdf

---

## Details (Pratik Formül Seti — Ham Bulgular)

Kaynaklardan derlenen formül yığını (yorumsuz):

1. **Almgren-Chriss linear temporary impact:** I_temp = η · (Q/T) ; permanent: I_perm = γ · Q. — Kaynak (Vaes & Hauser 2020 özetlemesi): https://arxiv.org/pdf/1810.11454
2. **Almgren et al. (2005) ampirik form:** I_temporary ∝ σ · (v/V)^(3/5), burada v = trading rate, V = ADV. — Kaynak: https://www.cis.upenn.edu/~mkearns/finread/costestim.pdf
3. **Square-root law (Tóth 2011 / Gatheral 2010):** I = Y · σ · √(Q/V), burada Y, O(1) sabit. — Kaynak: https://link.aps.org/doi/10.1103/PhysRevX.1.021006
4. **Roll (1984) effective spread:** S = 2·√(−Cov(ΔP_t, ΔP_{t-1})), cov<0 koşulu altında. — Kaynak: https://www.bauer.uh.edu/rsusmel/phd/roll1984.pdf
5. **Perold (1988) Implementation Shortfall:** IS = (P_decision − P_executed) · Q_executed + (P_decision − P_current) · Q_unexecuted + komisyon ve diğer fees. — Kaynak: https://www.quantitativebrokers.com/blog/a-brief-history-of-implementation-shortfall
6. **Amihud illiquidity:** ILLIQ = |R| / (Volume·Price). (BIST için Kang & Zhang 2014 AdjILLIQ önerisi.) — Kaynak: https://ideas.repec.org/a/eee/pacfin/v27y2014icp49-71.html

---

## Recommendations
Bu rapor ham bulgu raporudur. Yorum, tavsiye veya kurallar içermez. Kullanım kararı son kullanıcıdadır.

## Caveats
- "EM impact ABD'den 2-3× yüksek" iddiasının literatür kaynağı bu araştırmada bulunmadı; Lesmond (2005) yalnızca "1.7% higher price impact" için politik istikrarsızlık değişkeni doğrulamış.
- BIST'e özgü Almgren-Chriss kalibrasyonu (BIST-spesifik η, γ, σ katsayıları) bulunamadı.
- "1% ADV → 5 bps lineer / 15-25 bps karekök" tipik rakamlarının literatürdeki orijinal kalibrasyon kaynağı tespit edilemedi.
- Hisse bazında günlük ortalama hacim (TL) verilerinin çoğu tek-gün snapshot veya Investing.com 12-aylık ortalamasıdır; Borsa İstanbul resmi monthly bulletin verisine ulaşılmadı.
- SPK açığa satış yasağı 24 Mayıs 2026 itibarıyla 26 Mayıs 2026 seans sonuna kadar uzatılmış (08.05.2026 / 30/903 sayılı SPK kararı), sonraki uzatma kararı bu rapor tarihinden sonra olabilir.
- BIST mega/mid/small-cap için proporsyonel bid-ask spread bps değerleri (resmi BIST veya akademik) doğrudan tespit edilemedi.
- 2024 yıllık toplam pay piyasası hacim verisi (34,3 trilyon TL) Borsa İstanbul resmi raporunda mevcut; günlük ortalama (~137 milyar TL) bu yıllık değerden ~250 işlem günü varsayımıyla türetilmiş olup raporda doğrudan yayımlanmamıştır.
- Tüm vergi/komisyon oranları rapor tarihinde (Mayıs 2026) geçerli olup ileride değişebilir.
- TCMB Working Paper 12/26 başlık ve içerik orijinal PDF okunmadan ikincil kaynaklardan alıntılanmıştır.