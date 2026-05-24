# RR-016: Drawdown & Volatility Targeting — BIST OS Trading System

**Rapor No:** RR-016 | **Tarih:** 24 Mayıs 2026 | **Sistem:** BIST OS Trading System (Python, yfinance, EVDS API, KAP, long-only) | **Akademik / Pratik Ağırlık:** %40 / %60 | **Önceki Raporlar:** RR-012 (EM Faktörler), RR-013 (Holding NAV), RR-014 (Slippage), RR-015 (Transaction Cost)

---

## ERİŞİM NOTLARI (Rapor Başı)

- **Twitter / X Erişim Notu:** Twitter/X login-wall arkasındadır; bu rapor için Türk retail söylem örneklemesi yapılmamıştır. Söylem kaynakları: Hisse.net, Bigpara, Mynet Finans, halka açık aracı kurum içerikleri.
- **Hindsight Bias Notu:** Bölüm 4'teki tüm crisis period analizleri retrospektiftir. Her kriz altında "REAL-TIME bilgi vs RETROSPEKTİF bilgi" ayrımı yapılmıştır. Rapor "kriz öncesi sistemin nasıl davranacağı" hakkında **kavramsal counterfactual** sunar; gerçek backtest değildir.
- **Counterfactual Simulation Caveat:** Bölüm 4 ve 6'daki tüm sayısal "vol_scalar = 0.5" tipi tahminler **Builder validation framework**'ünde geçerli OHLCV verisi ile teyit edilmek zorundadır. Bu rapor yalnızca tasarım önerisi sunar.
- **Hiperenflasyon Distortion Notu:** Türkiye 2022–2024 hiperenflasyon dönemi nominal getiri serisi reel volatilite ile ciddi sapma gösterir. 252-gün lookback **tavsiye edilmez**.
- **Vol Hata Payı:** Tüm vol tahminleri ±%15 hata payına sahiptir (kapanış fiyatları intraday vol'u undersample).

---

## 1. TL;DR

**Soru: BIST OS şu anki risk yönetimi yeterli mi?** **Kısmen.** Mevcut sistem (sabit %15 hard exit + vol-aware stop tier %6/8/12/15 + CB-002 macro gate) **statik bir taban** sağlar, ancak rejim-bağımlı vol değişimine **adaptif değildir**. Türk hisse senedi yıllık nominal volatilitesi yaklaşık %30–45 bandında (Çelik 2021, Journal of BRSA Banking and Financial Markets 15(1):61–81 EGARCH analizine göre 2007–2010'da yüksek ve dirençli, COVID döneminde dramatik yükseliş — spesifik %30–45 bandı bu raporda proxy hesap, kaynaklı verbatim olarak BULUNAMADI), bu da sabit yüzde stop'larını yüksek vol rejimlerinde whipsaw tetikleyici, düşük vol rejimlerinde fazla geniş yapar.

**Üç spesifik öneri:**

1. **Vol-targeting katmanı** (PORTFOLIO_TARGET_VOL_ANNUAL = 0.15, 20-gün rolling realized vol lookback) **paralel kolon** olarak `position_sizer_v3`'e eklenmeli; mevcut Kelly + conviction + sector cap **korunmalı**, üzerine `min(vol_scalar, dd_scalar, CB-002 floor)` uygulanmalı.
2. **Soft DD gate** %5 / %10 / %15 ordinal kademe (1.0 → 0.5 → 0.25 → 0.0) mevcut sabit %15 hard exit'in üzerine eklenmeli — Bridgewater'ın "1/3 max DD" disiplinini retail ölçeğinde yeniden ölçekler.
3. **Ulcer Index + Calmar Ratio + Sortino** üçlüsü `daily_reporting.py` çıktısına eklenmeli; mevcut MDD tek başına süre cezalandırmıyor (Peter Martin 1987, Terry Young 1991 boşluğu).

**Sharpe artırım potansiyeli (literatür):** Moreira & Muir (2017, NBER WP 22208 verbatim): "For the market portfolio our strategy produces an alpha of 4.9%, an Appraisal ratio of 0.33, and an overall **25% increase in the buy-and-hold Sharpe ratio**" (https://www.nber.org/system/files/working_papers/w22208/w22208.pdf). Harvey, Hoyle, Rattray ve diğerleri (2018, JPM 45:1) yalnızca "risk varlıkları" (equity + kredi) için anlamlı Sharpe geliştirmesi bulur. **Türkiye 2022–2026 hiperenflasyon dönemi bu literatür dışıdır**; Cederburg et al. (JFE 2020) OOS performans düşüşü dikkate alındığında muhafazakâr alt sınır olarak %10–20 risk-adjusted iyileşme beklentisi tutulabilir ancak doğrudan kaynaklı tahmin değildir — Builder validation'a bırakılır.

**Implementation effort:** 2 hafta Faz 1 (vol-scaling temel), 1 ay Faz 2 (DD soft gate), Phase 5'te tam entegrasyon. Production-ready kod bu raporda **YOK**; kavramsal signature + thresholds + Builder validation checklist sağlanmıştır.

**Kritik bulgu uyarısı — ENERY:** Cagan portföyünde ENERY (small-cap doğal gaz dağıtım, yıllık +%111,71 getiri, halka arz Ağustos 2023, hisse adedi 49,1M) **portföyün ~%16'sı olduğu halde portföy volatilite katkısının muhtemelen %35–55'ini taşır**. Vol-aware sizing devreye girdiğinde ENERY ağırlığının bağlayıcı kısıt olması beklenir. Detay: Bölüm 9.

---

## 2. Akademik Temel Özeti

### 2.1 Drawdown Metrikleri

**A1. Maximum Drawdown (MDD).** `MDD = max_{t≤T} ((peak_t − trough_t) / peak_t)`. **Sanity Test 1:** 100→130→110→140→95 → MDD = 32,1%. **Sanity Test 2:** 100→120→85→130→90 → MDD = 29,2% (derin olan baskın). **Sanity Test 3:** 100→90 (3 ay)→100 (3 ay)→80 (1 ay)→100 → MDD = %20 ama kullanıcı 2 çukur yaşar; tek sayı yetersiz.

**A2. Average Drawdown.** Tüm underwater periyotların ortalaması.

**A3. Drawdown Duration.** Morgan Stanley Counterpoint Global (2024): ABD hisse senetlerinde %95–100 MDD ortalama 6,7 yıl trough'a iniş, 8,0 yıl recovery; %0–50 cohort 1,0/1,5 yıl (https://www.morganstanley.com/im/publication/insights/articles/article_drawdownsandrecoveries_ltr.pdf). BIST karşılığı **BULUNAMADI**.

**A4. Ulcer Index (Martin 1987).** `UI = sqrt((1/n) × Σ D'_i²)`. Peter Martin verbatim: "Ulcer Index measures the depth and duration of percentage drawdowns in price from earlier highs. The greater a drawdown in value, and the longer it takes to recover to earlier highs, the higher the UI. … The squaring effect penalizes large drawdowns proportionately more than small drawdowns" (https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index).

**Sanity Test 1:** Hep yeni peak → UI = 0. **Sanity Test 2:** Sabit %5 dip, n=14 → UI = 5,00%. **Sanity Test 3:** Tek günlük %20 dip + 13 gün peak → UI = 5,35% (derin ama kısa). **Sanity Test 4:** 14 gün %15 dipte kalış → UI = 15% (kalıcı yara). JournalPlus benchmark: UI<3 mükemmel, 3-5 iyi, 5-10 dikkat, >10 strateji revize (https://journalplus.co/metrics/ulcer-index/).

**A5. Calmar Ratio (Young 1991).** Wikipedia: "average annual rate of return for the last 36 months divided by the maximum drawdown for the last 36 months" (https://en.wikipedia.org/wiki/Calmar_ratio). **Sanity Test 1:** %30 getiri, MDD=%20 → Calmar=1,5. **Sanity Test 2:** %60/%50 → Calmar=1,2. **Sanity Test 3:** %15/%5 → Calmar=3,0. **Sanity Test 4 (BIST 2024 proxy):** XU100 +%32, MDD ~%15 → Calmar ≈ 2,1. QuantVPS benchmark: >1,0 iyi, >1,5 çok iyi, >3,0 mükemmel; retail çoğunlukla 0,5–1,5 (https://www.quantvps.com/blog/how-to-calculate-the-calmar-ratio).

**A6. Pain Index / Pain Ratio (Schwager & Stewart 2010).** Karelendirme yerine düz toplam.

### 2.2 Volatility Targeting Literatürü

**Moreira & Muir (2017), "Volatility-Managed Portfolios", Journal of Finance 72(4):1611–1644.** DOI 10.1111/jofi.12513. Verbatim: "Managed portfolios that take less risk when volatility is high produce large alphas, increase Sharpe ratios, and produce large utility gains for mean-variance investors. We document this for the market, value, momentum, profitability, return on equity, investment, and betting-against-beta factors, as well as the currency carry trade" (https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513). NBER WP 22208 piyasa portföyü sonucu: "**25% increase in the buy-and-hold Sharpe ratio**" (https://www.nber.org/system/files/working_papers/w22208/w22208.pdf).

**Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, Van Hemert (2018), "The Impact of Volatility Targeting", JPM 45(1):14–33.** DOI 10.3905/jpm.2018.45.1.014. Verbatim: "this result only holds for 'risk assets', such as equity and credit … it reduces the likelihood of extreme returns, across all asset classes … 'left-tail' events tend to be less severe, as they typically occur at times of elevated volatility, when a target-volatility portfolio has a relatively small notional exposure" (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538). Alpha Architect (60 varlık, 10% vol target): "the volatility of volatility is reduced from 4.6 percent for unscaled returns versus 1.8 percent for volatility-scaled returns" — vol-of-vol %60 düşüş (https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/).

**Kritik kısıt — out-of-sample meta-eleştiri (Cederburg et al. JFE 2020):** "the trading strategies implied by these regressions are not implementable in real time, and reasonable out-of-sample versions generally earn lower certainty equivalent returns and Sharpe ratios than do simple investments in the original, unmanaged portfolios" (https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X). **Vol-targeting "ücretsiz öğle yemeği" değildir.**

**Türkiye Boşluğu:** Çelik (2021), Journal of BRSA Banking and Financial Markets 15(1):61–81 BIST 100 EGARCH analizi var ancak vol-targeting değil pure vol-modeling. Verbatim: "Friday's anomaly, Public Holidays, and the COVID-19 pandemic create negative shocks on the volatility movements of the return series, increase the volatility movements, and consequently, asymmetric and leverage effect emerged" (https://www.researchgate.net/publication/354031179) — leverage effect güçlü, vol-targeting için **olumlu** sinyal. 2022–2026 hiperenflasyon vol-managed BIST literatürü bu rapor için **BULUNAMADI**.

### 2.3 Kelly Criterion + Vol Interaction

**Thorp (1969), "Optimal Gambling Systems for Favorable Games"** — Kelly criterion'u finansa taşıyan kurucu çalışma. Thorp 2006 retrospektif verbatim: "Most of the people who successfully use the Kelly criterion in fact aim for a bet or position size less than the Kelly bet — the amount determined by the uncertainties and any preference for less volatility" (https://gwern.net/doc/statistics/decision/2006-thorp.pdf). Thorp pratiği Princeton-Newport'ta **quarter-Kelly**: "Quarter-Kelly gave him gentler drawdowns. Instead of losing 50% peak-to-trough, he might lose 20%" (Medium analizi: https://medium.com/@anvesh.jhuboo/the-kelly-criterion-and-the-impossibility-of-knowing-cd4cd4d7f0a0).

Wikipedia Kelly criterion verbatim: "Due to the high drawdowns, gamblers in practice find fractional Kellies much better emotionally than full Kelly … A detailed paper by Edward O. Thorp and a co-author estimates Kelly fraction to be 117% for the American stock market SP500 index. Significant downside tail-risk for equity markets is another reason to reduce Kelly fraction from naive estimate (for instance, to reduce to half-Kelly)" (https://en.wikipedia.org/wiki/Kelly_criterion).

**Vince (2007), "The New Money Management"** — fractional Kelly + position sizing matematiksel formalizmi (ISBN 978-0470067321).

**Vol-adjusted Kelly formülü:** `f* = (μ − r_f) / σ²` ; `f_adj = f* × (σ_target / σ_realized) × α`, α∈{0.25, 0.5}, f_cap=1.0 (long-only).

**Sanity Test 1:** μ=0.08, σ=0.30, r_f=0.37 → f* negatif → no position. **Sanity Test 2:** μ=0.50, σ=0.35, r_f=0.37 → f*≈1.06, half-Kelly=0.53, vol-adj × (0.15/0.35)=0.23. **Sanity Test 3:** μ=0.45, σ=0.30, r_f=0.37 → f*=0.89, quarter-Kelly=0.22, vol-adj × 0.5 → 0.11.

**Kritik:** Türkiye hiperenflasyon dönemi nominal getiriler şişirilmiş; **excess return (μ − r_f)** ile çalışılmalı. r_f referansı: TCMB politika faizi %37 (Mayıs 2026), Press Release 2026-17 verbatim: "The Monetary Policy Committee (the Committee) has decided to keep the policy rate (the one-week repo auction rate) at 37 percent. The Committee has also maintained the Central Bank overnight lending rate and the overnight borrowing rate at 40 percent and 35.5 percent, respectively" (https://www.tcmb.gov.tr/wps/wcm/connect/en/tcmb+en/main+menu/announcements/press+releases/2026/ano2026-17).

---

## 3. Endüstri Pratiği Karşılaştırma

| Kurum | Strateji | Vol Target | Maksimum Tarihsel DD | Kaynak |
|---|---|---|---|---|
| Bridgewater Pure Alpha I | Sistematik makro | 12% | %13 (2020 Mart) | The Hedge Fund Journal (https://thehedgefundjournal.com/50-giants-bridgewaters-ray-dalio/) |
| Bridgewater Pure Alpha II | Sistematik makro | 18% | ~%20+ (2020 Mart) | Wikipedia Bridgewater |
| AQR Managed Futures (AQMRX) | Trend follow | 10% | -18,6% (12-ay Nisan 2025) | Investment Officer (https://cms.investmentofficer.com/en/news/morningstar-winton-vs-aqr-trend-following-strategies) |
| AQR Managed Futures HV (QMHRX) | Trend follow | 15% | — | aqr.com fund pages |
| Renaissance Medallion | Stat-arb, kapalı | Açıklanmıyor | Public **BULUNAMADI** | — |
| Retail hedge fund average | Karma | — | %15–25 | endüstri standardı |
| Family office (muhafazakâr) | Karma | ~6% | %8–12 | endüstri standardı |
| **BIST OS (mevcut)** | **Long-only Türk hisse** | **Yok** | **%15 hard exit** | Bu rapor |
| **BIST OS (öneri)** | **Long-only Türk hisse** | **%15** | **%18–20 hard + soft %5/10/15** | Bu rapor §6 |

Ray Dalio verbatim (The Hedge Fund Journal): **"We realized we did not want to have a drawdown greater than one third, because a 50% drawdown would require a 100% return for recovery, and a 75% drawdown would require a 300% recovery."** Bu cümle asymmetric DD math disiplinini özetler. Pure Alpha 12% vol class inception-to-2024 max DD **%13 (2020 Mart)**.

**BIST OS'un %15'i nerede oturuyor?** Family office üstünde, retail hedge fund altında, Bridgewater Pure Alpha II profiline yakın. **Cagan (21 yaşında) profiline %15 hard agresif**; soft floor (%5/%10) eklenmesi psikolojik DD hassasiyetini azaltır.

**Erişim Notu:** Hedge fund DD profilleri kamuya kısmi açıklamalardır; içsel risk dashboard verileri public değildir.

---

## 4. Crisis Period Analiz (7 Kriz — Kavramsal Counterfactual)

> **Önemli Uyarı:** Bu bölüm **kavramsal counterfactual simülasyondur**, gerçek backtest **değildir**. Tüm "vol_scalar", "dd_scalar" ve "BIST OS şu davranırdı" cümleleri Builder validation framework'ünde teyit edilmek zorundadır.

### E1. 2018 Ağustos Türk Lirası Krizi

**1. Gerçek BIST hareketi.** Trump 10 Ağustos 2018 çelik/alüminyum tarife ikiye katlama. Hürriyet verbatim: "10 Ağustos'ta … BIST 100 endeksi gün içinde 88.598–97.810 bandı içinde dalgalandı. 9 bin puanı aşan bir bant içinde hareket eden endeks günü yüzde 2,31 azalışla 94.940 puandan tamamladı" (https://www.hurriyet.com.tr/ekonomi/2018-borsa-yatirimcisi-icin-unutulmazlar-arasina-girdi-41070392). 13 Ağustos Pazartesi gün içi −%7 devre kesici (Bloomberg HT: "BİST'TE %7'LİK DÜŞÜŞÜN ARDINDAN 10.38 İTİBARİYLE TÜM PAZARLARDA DEVRE KESİCİ ÇALIŞTI … endeks günü yüzde 2,38 değer kaybıyla 92.684,55 puandan tamamladı, toplam işlem hacmi 15,5 milyar lira ile rekor seviyede gerçekleşti. Bankacılık endeksi yüzde 9,78 değer kaybederken …", https://www.bloomberght.com/piyasalar/haber/2147593). 29 Ocak 2018 zirvesi 121.532 → 17 Ağustos dibi 84.655 (~%30 TRY-bazlı). USD bazlı 2018 yıl kaybı −%44. Vol 30-gün %25 → ~%55–60 (proxy).

**2. BIST OS davranış.** Sabit %15 hard exit Ağustos ortasında tetiklenir; recovery 2019 Q1.

**3. Vol-targeting.** σ Ağustos ortasında ~%55. vol_scalar = 0.27. Pozisyon Temmuz sonu %50, Ağustos başı %30. Hard exit'ten **önce** de-leverage.

**4. Trade-off.** Kademeli çıkış recovery için hazırlık. Trump tweet intraday şoku akşamına kadar yakalanamaz; %2,31 düşüş yine yaşanır.

**5. Real-time vs Retrospektif.** Real-time 9 Ağustos akşamına kadar BIST 97.000+, vol_scalar = 0.8–0.9. Kayıpların %50–60'ı önlenir.

**6. Builder Validation Checklist:**
- ☐ DD trigger (hard %15) tarihi: 27 Temmuz–8 Ağustos 2018 aralığı
- ☐ Vol scalar < 0.5 tarihi: 3–10 Ağustos 2018
- ☐ Recovery re-entry: L2 score > 0.5 + σ < %30 → Mart 2019?
- ☐ AKBNK, GARAN, ISCTR sektör cap %40 tetik (13 Ağu)?

**Erişim Notu:** USD-bazlı kayıp rakamları ikinci dereceden hesap; resmi BIST yıllık raporundan teyit edilmedi.

### E2. 2020 Mart COVID

**1. Gerçek BIST hareketi.** BIST 100 21 Şubat 2020 peak ~122.000, 23 Mart 2020 trough ~%25 TRY (spesifik rakam doğrudan kaynaktan teyit edilmedi — Builder framework Borsa İstanbul historik veri üzerinden re-hesap önerilir). Çelik (2021, BRSA): EGARCH "Friday's anomaly, Public Holidays, and the COVID-19 pandemic create negative shocks on the volatility movements" — vol 20-gün %20 → ~%75. Hızlı V-recovery Q3 2020'a kadar.

**2. BIST OS davranış.** %15 hard exit Mart ortasında tetiklenir; CB-002 floor 0.3 re-entry'yi yavaşlatır.

**3. Vol-targeting.** σ Şubat sonu %30→%50→%75. vol_scalar 9 Mart haftası ≈ 0.30. Trough vol_scalar 0.20.

**4. Trade-off.** Karma çözüm tercih: vol-scaler küçültür, hard exit reset eder.

**5. Real-time vs Retrospektif.** Retrospektif: hızlı V bilindiği için "vol-targeting kötü". Real-time: 23 Mart V/U/L belli değildi; vol-scaling muhafazakâr (doğru).

**6. Builder Validation Checklist:**
- ☐ DD trigger tarihi: 9–13 Mart 2020 haftası
- ☐ Vol scalar < 0.5: 3–9 Mart 2020
- ☐ Recovery re-entry: σ < %30 + L2 > 0.5 → Haziran–Temmuz 2020?
- ☐ THYAO, MAALT idiosyncratic vol sektör cap yeterli mi?

### E3. 2023 Şubat Kahramanmaraş Depremi

**1. Gerçek BIST hareketi.** 6 Şubat 2023 M7.8 + M7.5. Nature 2024 verbatim: "A total death toll of about 60,000 (50,783 in Turkey and over 7000 in Syria) has been reported. Over 500,000 buildings suffered heavy damage or collapsed in Turkey alone" (https://www.nature.com/articles/s44172-024-00170-y). Borsa 8–15 Şubat kapalı. Açılışta sektörel sigorta/inşaat/gıda DD %5–8, geniş endeks ~%4.

**2. BIST OS davranış.** Trade yok (kapalı). 15 Şubat reaksiyon. Hard exit tetiklenmez.

**3. Vol-targeting.** Kapalıdan stale; 15 Şubat σ patlar, vol_scalar 0.5–0.7. Portfolyo-seviye vol → sektörel idiosyncratic yakalanamaz.

**4. Trade-off.** Tek hisse vol contribution kritik (Risk Parity lite, Bölüm 5.5).

**5. Real-time vs Retrospektif.** Real-time: 5 Şubat akşamına kadar fiyatlamada sinyal yok — vol-scaling **deprem riskini koruyamaz** (idiosyncratic exogenous shock).

**6. Builder Validation Checklist:**
- ☐ 8–15 Şubat kapanış nasıl handle edildi?
- ☐ 15 Şubat sigorta sektörü idiosyncratic vol spike?
- ☐ Sektör cap %40 override gerekti mi?

### E4. 2023 Haziran Şimşek-Erkan Politika Değişikliği

**1. Gerçek BIST hareketi.** Mayıs 2023 seçim sonrası Şimşek (Maliye Bakanı, 4 Haziran 2023) + Erkan (TCMB Başkanı, Haziran 2023) atamaları. TCMB politika faizi %8.5 → %50 (10 ay). OSW verbatim: "the main index of the Turkish stock exchange, BIST 100, gaining 20% in 2024" (https://www.osw.waw.pl/en/publikacje/analyses/2025-07-09/turbulent-stabilisation-turkeys-economy-under-simseks-supervision). 10-yıllık tahvil yield %26 (2023) → %15 (2024).

**2. BIST OS davranış.** Hard exit Haziran başında belirsizlik döneminde tetiklenebilir; sonra disinflation rally'yi full Kelly + sector cap ile yakalar.

**3. Vol-targeting.** Haziran yüksek vol → vol_scalar düşük. 2024 σ düşer, vol_scalar yükselir.

**4. Trade-off.** Rejim değişimi vol-targeting + L2 Macro bull onayı (CB-002 = 0.8–1.0) gerektirir. CB-002 = 0.3 (bear) ama vol = 1.0 (calm) → min() = 0.3 → bear false negative riski (rejim değişimini kaçırma) — interaction matrisinde Senaryo C.

**5. Real-time vs Retrospektif.** Retrospektif: Şimşek orthodoks rejim sinyali. Real-time: Haz–Eyl 2023 arası "yıl sonu U-turn" senaryosu fiyatlanıyordu. Vol-scaling muhafazakâr (doğru).

**6. Builder Validation Checklist:**
- ☐ Erkan atama (8 Haziran 2023) vol spike?
- ☐ TCMB rate hike günleri intraday vol patlama?
- ☐ L2 Macro bull onay 2024 başı ne zaman > 0.5?
- ☐ 2024 BIST +%20 nominal vs TÜFE +%44.38 (TurkStat, Aralık 2024 — https://www.intellinews.com/turkey-s-44-y-y-official-end-2024-inflation-release-suggests-another-250bp-rate-cut-in-late-january-359762/) reel −%17?

### E5. 2023 Mayıs Seçim Şoku

**1. Gerçek BIST hareketi.** 14 Mayıs 2023 1. tur, 28 Mayıs 2. tur. Haftalık vol %20 → ~%45 (proxy). DD ~%10. (Türkiye Today referans: "biggest one-day rally since May 11, 2023", https://www.turkiyetoday.com/business/turkish-exchange-sees-biggest-one-day-rally-since-may-2023-3203673).

**2. BIST OS davranış.** Hard exit %15 tetiklenmez; vol-aware stop %12 tetiklenebilir.

**3. Vol-targeting.** vol_scalar 14 Mayıs öncesi 0.4–0.5. Seçim sonrası iki senaryo: muhalefet zaferi rally'yi yavaş yakalar / Erdoğan zaferi belirsizlik devam.

**4. Trade-off.** Election uncertainty literatür (Białkowski et al. 2008): election haftasında vol iki katına çıkabilir (referans ScienceDirect: https://www.sciencedirect.com/science/article/abs/pii/S0275531925003605); BIST için spesifik teyit yok.

**5. Real-time vs Retrospektif.** Real-time: 28 Mayıs sonrası ekonomi politikası belirsizdi → vol-scaling doğru.

**6. Builder Validation Checklist:**
- ☐ 12 Mayıs σ_realized?
- ☐ 15 Mayıs vol_scalar?
- ☐ 29 Mayıs vol_scalar yükseliş?

### E6. 2024 Mart Yerel Seçim

**1. Gerçek BIST hareketi.** 31 Mart 2024 yerel seçim, CHP %37,74 1.parti (1977'den ilk). Mynet verbatim: "Borsa İstanbul'da BIST 100 endeksi, Mahalli İdareler Genel Seçimlerinin ardından haftaya yüzde 1,01 yükselişle 9.234,48 puandan başladı … Bankacılık endeksi yüzde 1,72 ve holding endeksi yüzde 2,04 artış kaydetti" (https://finans.mynet.com/haber/detay/doviz/dolardan-secim-sonuclarina-ilk-tepki-1-nisan-2024-dolar-tl-ne-kadar-oldu/480204/). Pozitif tepki, kısa vol spike.

**2. BIST OS davranış.** Hard exit tetiklenmez.

**3. Vol-targeting.** vol_scalar 0.7–0.8.

**4. Trade-off.** Vol-scaling overreact etmez (doğru).

**5. Real-time vs Retrospektif.** Real-time: sürpriz CHP zaferi → ekonomi politikası belirsizliği → kısa vol spike makul.

**6. Builder Validation Checklist:**
- ☐ 1 Nisan bankacılık (AKBNK, GARAN, ISCTR) overweight tetik?
- ☐ 28 Mart–1 Nisan haftası vol_scalar minimum?
- ☐ DD %5'i aşmadı doğrulanır mı?

### E7. 2024 Aralık – 2025 Ocak Fed Pivot

**1. Gerçek BIST hareketi.** Global EM rally, Fed faiz indirim sinyali. BIST 100 +%5–%10, vol düşüş.

**2. BIST OS davranış.** Rally-friendly; CB-002 floor 0.8–1.0, kısıt yok.

**3. Vol-targeting.** σ inerken vol_scalar yükselir. VOL_SCALAR_CAP = 1.5 bağlayıcı.

**4. Trade-off.** Long-only base zaten 1.0 cap; vol_scalar 1.5 fiilen kullanılmıyor ama formül yarın leverage destekli rejim için açık.

**5. Real-time vs Retrospektif.** Aralık FOMC pivot işareti gelişti; vol-scaling rally'yi tutar.

**6. Builder Validation Checklist:**
- ☐ Aralık 2024 başı vol_scalar?
- ☐ Ocak 2025 vol_scalar 1.5 cap?
- ☐ Position cap = 1.0 bağlayıcı mı?

---

## 5. Volatility Targeting Framework

### 5.1 Temel Formül

`portfolio_vol_scalar = clip(σ_target / σ_realized_20d, 0.20, 1.50)`  
`final_size = base × vol_scalar × dd_scalar × conviction × sector_cap`

**Sanity Test 1:** σ_target=0.15, σ_realized=0.30 → 0.5 (yarı pozisyon). **Sanity Test 2:** 0.15/0.10 = 1.5 (cap). **Sanity Test 3:** 0.15/0.75 (COVID) = 0.20 (floor). **Sanity Test 4:** 0.15/0.15 = 1.0 (rejim hedefte).

### 5.2 BIST için Target Vol Önerisi

| Profil | σ_target | Açıklama |
|---|---|---|
| Muhafazakâr | %10 | Family office tarzı |
| **Önerilen (Cagan)** | **%15** | Bridgewater Pure Alpha I |
| Orta-agresif | %20 | AQR HV |
| Agresif | %25+ | Bridgewater Pure Alpha II |

### 5.3 Lookback Window

| Lookback | Avantaj | Dezavantaj | Öneri |
|---|---|---|---|
| 20-gün | Hızlı reaksiyon | Whipsaw | **BIRINCIL** |
| 60-gün | Stabil | Gecikme | **İKINCIL kontrol** |
| 252-gün | Tam yıllık | **Hiperenflasyon distortion — TAVSIYE EDİLMEZ** | Yok |

### 5.4 Vol Estimation Method

| Method | Formula | BIST? |
|---|---|---|
| Historical rolling std | `σ = std(returns_20d) × √252` | **EVET Faz 1** |
| EWMA (RiskMetrics λ=0.94) | `σ²_t = λσ²_{t-1} + (1−λ)r²_{t-1}` | Faz 2 |
| GARCH(1,1) | `σ²_t = ω + αr²_{t-1} + βσ²_{t-1}` | Faz 3 (Çelik 2021 TGARCH öneriyor) |

### 5.5 Risk Parity Lite

`weight_i × σ_i ≤ 0.40 × σ_portfolio`. ENERY için kritik. **Sanity:** ENERY σ ≈ %50, ağırlık %16, portföy σ ≈ %25 → katkı = 0.32, eşik altında ama yakın. σ %60'a çıkarsa katkı 0.38 → bağlayıcı.

---

## 6. position_sizer_v3 Tasarımı (KAVRAMSAL)

> **KESIN UYARI:** Production-ready DEĞİL. Builder validation gerekli.

### 6.1 v2 İmza (referans)

```python
def calculate_position_size(conviction, expected_return, stop_loss_pct, sector, portfolio_value):
    """Mevcut Kelly + conviction tier + sector cap; static, vol-blind."""
```

### 6.2 v3 Kavramsal

```python
def calculate_position_size_v3(
    conviction, expected_return, stop_loss_pct, sector, portfolio_value,
    realized_vol_20d, realized_vol_60d, current_drawdown,
    cb002_floor=1.0, target_vol_annual=0.15
) -> float:
    """Vol-aware sizing. Production-ready DEĞİL. Builder validation gerekli."""
    base = v2_kelly_conviction_sector(...)
    vol_scalar = clip(target_vol_annual / max(realized_vol_20d, 0.05), 0.20, 1.50)
    if current_drawdown < 0.05:    dd_scalar = 1.0
    elif current_drawdown < 0.10:  dd_scalar = 0.5
    elif current_drawdown < 0.15:  dd_scalar = 0.25
    else:                          dd_scalar = 0.0
    final = base * min(vol_scalar, dd_scalar, cb002_floor)
    return clip(final, 0.0, 0.20)
```

### 6.3 thresholds.py

```python
PORTFOLIO_TARGET_VOL_ANNUAL = 0.15
VOL_LOOKBACK_DAYS = 20
VOL_LOOKBACK_DAYS_CHECK = 60
VOL_SCALAR_CAP = 1.5
VOL_SCALAR_FLOOR = 0.20
DD_SOFT_THRESHOLD = 0.05
DD_MID_THRESHOLD = 0.10
DD_HARD_THRESHOLD = 0.15
MAX_SINGLE_VOL_CONTRIB = 0.40
MAX_SINGLE_POSITION = 0.20
SECTOR_CAP = 0.40
```

### 6.4 CB-002 × Vol-Scaler — 3 Senaryo

**Senaryo A:** CB-002 = 0.3, vol_scaler = 0.5 → Mult: 0.15 (double-penalty haksız), **Min: 0.3 (kazanan)**. İkisi de "küçült" diyor; çift cezalandırma yanlış.

**Senaryo B:** CB-002 = 1.0, vol_scaler = 0.5 → Mult: 0.5, **Min: 0.5 (vol kazanır)**. Bull olsa bile yüksek vol koruma gerektirir.

**Senaryo C:** CB-002 = 0.3, vol_scaler = 1.0 → Mult: 0.3, **Min: 0.3 (bear kazanır)**. Düşük vol bear rejim işaretini iptal etmez.

### 6.5 Formal Interaction Matrisi

| CB-002 | vol_scaler | min() | mult() | Doğru |
|---|---|---|---|---|
| 1.0 (bull) | 1.0 | 1.0 | 1.0 | ≡ |
| 1.0 | 0.5 | 0.5 | 0.5 | ≡ |
| 0.8 | 0.7 | **0.7** | 0.56 | MIN |
| 0.5 | 0.5 | **0.5** | 0.25 | MIN |
| 0.3 | 1.0 | 0.3 | 0.3 | ≡ |
| 0.3 | 0.5 | **0.3** | 0.15 | MIN |
| 0.0 (hard exit) | any | 0.0 | 0.0 | ≡ |

**Kural:** `final = base × min(vol_scalar, dd_scalar, cb002_floor)` — "the most binding constraint wins".

### 6.6 Pseudo-Test Scenarios

- Normal: base=0.10, vol=1.0, dd=1.0, cb=1.0 → 0.10
- COVID: base=0.10, vol=0.3, dd=1.0, cb=0.5 → 0.10 × 0.3 = 0.03
- DD %8: base=0.10, vol=0.8, dd=0.5, cb=1.0 → 0.10 × 0.5 = 0.05
- Hard exit (DD %15+): dd=0.0 → 0.0
- Düşük vol rally: vol=1.5 cap, dd=1.0, cb=1.0 → 0.10 (long-only base bağlayıcı)

### 6.7 v2 → v3 Geçiş Yolu

1. **Faz 1 (2 hafta):** vol_20d ve drawdown gözlem modu, loglama.
2. **Faz 2 (1 ay):** vol_scalar ve dd_scalar paralel kolon, daily reporting.
3. **Faz 3 (Phase 5):** Karar mekanizmasına dahil, başlangıçta soft warning, sonra aktif kısıt.
4. **Faz 4:** Builder backtest v2 vs v3, 2018/2020/2023/2024 dönemleri.

---

## 7. Stop-Loss Revize Önerisi

| Method | Pro | Con | BIST OS |
|---|---|---|---|
| Sabit % (mevcut) %6/%8/%12/%15 | Basit | Vol-blind | **Korunur paralel** |
| ATR-based (Wilder 1978) k=2-3 | Vol-adaptive | Trend ayrı kural | **Tier 2 ek** |
| Vol-scaled K=2.5 | Akademik | Hesap karmaşık | Faz 3 |
| **Time-stop (YENİ)** | Sinyal yarı-ömrü | Trend kaçar | **ZORUNLU EKLE** |

Wilder ATR Wikipedia verbatim: "Current ATR value (or a multiple of it) can be used as the size of the potential adverse movement (stop-loss distance) when calculating the trade volume based on trader's risk tolerance. In this case, ATR provides a self-adjusting risk limit dependent on the market volatility" (https://en.wikipedia.org/wiki/Average_true_range).

**TTKOM sanity:** Giriş 60.65 TL, mevcut tier %8 stop = 55.80 TL. ATR(14) ≈ 2.40 TL, 2× ATR stop = 55.85 TL. İki yöntem yakın. Yüksek vol hisselerde ATR daha geniş, düşük vol'da daha dar.

**Time-stop sinyal-bazlı:** L1 Technical 15 gün, L2 Macro 90 gün, L3 KAP 45 gün, L5 Smart Money 30 gün. Tetiklenirse kademeli azaltma (%50 satış, re-evaluation).

**Paralel kolon disiplini:** Mevcut tier korunur; ATR-based **alternatif** olarak yan yana hesaplanır, ikisinin **MAX**'i (daha geniş olan) alınır → false stop azaltılır.

---

## 8. Alternatif Risk Metrikleri

| Metric | Formula | Implementation |
|---|---|---|
| MDD | peak-trough max | Mevcut |
| **Ulcer Index** | sqrt(mean(D'²)) | **EKLE Faz 1** |
| **Calmar** | CAGR / |MDD| | **EKLE Faz 1** |
| Pain Index | mean(D') | Faz 2 opsiyonel |
| **Sortino** | (R−MAR)/DownDev | **EKLE Faz 1** |
| Omega | upside/downside | Faz 3 opsiyonel |
| CVaR (Rockafellar-Uryasev 2000) | E[loss\|loss>VaR_α] | Faz 3, DOI 10.21314/JOR.2000.038 |

**Sortino Sanity Test:** Getiri serisi [+5,+3,−2,−4,+6,+1,−1,+4,+3,−3,+2,+5], MAR=0. Negatifler [−2,−4,−1,−3]. DownDev = sqrt((4+16+1+9)/12) = 1.58. Mean = 1.58. Sortino = 1.0.

**Calmar BIST 2024 Proxy:** XU100 +%20 nominal (OSW), MDD ~%15 → Calmar ≈ 1.33.

**Architecture impact:** `daily_reporting.py`'a 3 hesaplama fonksiyonu. Backward compat: mevcut MDD korunur, yeni metrikler ekstra satır. Test ortamında başla, prod 2 hafta sonra.

---

## 9. Cagan Portföy Analizi

### 9.1 Mevcut Pozisyonlar (24 Mayıs 2026)

| Hisse | Lot | Maliyet TL | Portföy % | Sektör | Cap |
|---|---|---|---|---|---|
| TTKOM | 329 | 60.65 | ~20% | Telekom | Large-cap |
| KCHOL | 81 | 188.83 | ~18% | Holding | Mega-cap |
| ENERY | 1543 | 9.07 | ~16% | Doğal gaz dağıtım | **Small-cap** |
| AKSEN | — | — | 0 (satıldı 24 May 2026) | Enerji | — |

### 9.2 Vol Profilleri (Mayıs 2026)

| Hisse | 52-h range | Haftalık Δ | Aylık Δ | Beta | σ tahmini | Kaynak |
|---|---|---|---|---|---|---|
| TTKOM | 47.48–75.65 | −11.68% | −13.80% | 0.97 | **~%30–35** | Bigpara (https://bigpara.hurriyet.com.tr/borsa/hisse-fiyatlari/ttkom-turk-telekom-detay/), TradingView (https://tr.tradingview.com/symbols/BIST-TTKOM/) |
| KCHOL | 139.40–229.10 | — | −8.71% | 0.30 (Yahoo 5Y) / 1.21 (TV haftalık) — **çelişki** | **~%30–35** | Yahoo (https://finance.yahoo.com/quote/KCHOL.IS/), TradingView |
| ENERY | 1.57–11.93 | −6.20% | +1.11% | **BULUNAMADI** (Ağu 2023 IPO) | **~%50–55** (proxy) | Mynet (https://finans.mynet.com/borsa/hisseler/enery-enerya-enerji/), TradingView |

**Lookback önerisi:** 20-gün birincil, 60-gün kontrol, 252-gün TAVSIYE EDİLMEZ.

### 9.3 Portföy Vol Hesabı

`σ_port² = Σ w_i² σ_i²` (korelasyonsuz proxy):
- TTKOM: 0.20² × 0.32² = 0.00410
- KCHOL: 0.18² × 0.32² = 0.00332
- ENERY: 0.16² × 0.52² = 0.00692
- Toplam (nakit ~%46, σ≈0): 0.01434 → σ_port ≈ **%12**

Tipik BIST korelasyon ρ ≈ 0.4–0.6 düzeltmesi → **gerçek σ_port ≈ %15–18**.

**Realized vs Target:** Target %15, Realized ≈ %16 → vol_scalar ≈ 0.94 → küçük revize. **Şu an hedefe yakın.**

### 9.4 ENERY KRİTİK BULGU — Vol Contribution Dominance

- ENERY ağırlık: %16
- ENERY σ: ~%50 (52-h range 1.57–11.93, yıllık +%111, IPO Ağu 2023, 49.1M hisse)
- **ENERY contribution: 0.16 × 0.50 = 0.080**
- TTKOM contribution: 0.20 × 0.32 = 0.064
- KCHOL contribution: 0.18 × 0.32 = 0.058
- **ENERY ≈ portföy vol kaynağının %40 + tek başına en büyük katkı**

ENERY σ %50→%60 olursa contribution 0.096 → Risk Parity Lite eşiği (0.40) bağlayıcı → küçültme zorunlu.

**Öneri:** ENERY %16 → %10–12, vol-contribution constraint aktif. Builder validation öncesi rebalance yapılmamalı, dashboard'da kırmızı flag.

### 9.5 Cagan Kelly Önerisi

21 yaş, ilk yatırımcı yılları, 5+ yıl horizon, psikolojik DD hassasiyeti yüksek.

**Full Kelly tehlikeli** (Thorp 2006): position size less than Kelly. Thorp pratiği quarter-Kelly: "Quarter-Kelly gave him gentler drawdowns. Instead of losing 50% peak-to-trough, he might lose 20%".

**Cagan için: half-Kelly (α=0.5) veya quarter-Kelly (α=0.25).** İlk 6 ay quarter-Kelly, performans tutarlı ise half-Kelly. Full Kelly **asla** retail uzun horizon için.

**Erişim Notu:** Vol tahminleri Mayıs 2026 itibariyle public kaynaklardan proxy. ENERY Beta resmi BULUNAMADI; 5Y monthly yetersiz veri. Daily veri ile σ tahminini Builder framework'ünde yfinance üzerinden re-hesap.

---

## 10. BIST 2023–2026 Sektör Pratiği

### 10.1 Türk Fon Yöneticisi (TEFAS/SPK)

SPK "Yatırım Fonlarına İlişkin Rehber" risk değeri 1–7 zorunlu (UCITS SRRI tarzı). Deniz Portföy verbatim: "Fon Risk değeri, fonun haftalık getirileri üzerinden, volatilitesi dikkate alınarak hesaplanır. 1 en az riskli, 7 en fazla riskli olmak üzere Risk Değeri 1 ile 7 arasındadır" (https://www.denizportfoy.com/About/RiskScale).

İş Portföy verbatim: "SPK'nın yayımladığı Yatırım Fonlarına İlişkin Rehber'de volatilite aralıklarının karşılık geldiği risk değerleri 1 ile 7 arasında bir değer almaktadır … hisse senedi, altın, gümüş gibi yüksek riskli varlıklara yatırım yapan fonlar ise yüksek risk seviyesi olarak görülen 6-7 aralığında yer almaktadır" (https://www.isportfoy.com.tr/medya-ve-blog/yatirim-fonlari-risk-degerleri-nelerdir). SPK PDF: https://spk.gov.tr/data/61e4a3a01b41c60d1404d7d2/Yatırım%20Fonlarına%20İlişkin%20Rehber.pdf

| Risk Değeri | Tip | UCITS SRRI proxy | Türk hisse fonları |
|---|---|---|---|
| 1 | Para piyasası | < %0.5 | — |
| 2 | Kısa vadeli borçlanma | %0.5–2 | — |
| 3 | Kamu borçlanma | %2–5 | — |
| 4 | Karma muhafazakâr | %5–10 | — |
| 5 | Karma agresif | %10–15 | — |
| **6** | **Hisse senedi** | **%15–25** | **Tipik** |
| **7** | **Tematik/yoğun** | **>%25** | Tematik |

**Conservative vs Aggressive max DD eşiği SPK'da explicit BULUNAMADI** — risk değeri std-based. Tek tek fon-bazlı max DD verbatim 2018/2020 TEFAS arşiv aramasında BULUNAMADI; proxy: BIST 100 2018 Ağustos peak-trough TRY −%30 (Hürriyet).

### 10.2 "Stop Koymam, Ortalama Düşürürüm" — Türk Retail Pattern

**Yoğunluk: Yüksek.** Hisse.net forum verbatim: "sen stop loss yaparsın kağıt sattığın anda yukarıya gider bende buna anlam veremem ben satmazsam adamın ekmeğine yağda sürmem satmıyorum arkadaş satmıyorum stop loss yerine ortalama yapmak daha mantıklı" (https://www.hisse.net/eforum/archive/index.php/t-101223.html).

Karşıt görüş Enuygun verbatim: "Borsa kuralı der ki; Aşağı doğru ortalama yapmayın. Önceden aldığınız bir hisse ucuzlayınca ek alımlar yaparak maliyetlerinizi düşürmeye çalışmayın. Aşağı giden fiyatlarda hiç bir zaman ortalama yapılmaz. Eldekilerin satışı daha doğrudur" (https://www.enuygun.com/bilgi/borsa-yatirimcilari-nelere-dikkat-etmeli/).

TradeAkademi verbatim: "Risk yönetimi konusunda en sık yapılan hatalar: Stop kullanmamak ya da çok geniş stop belirlemek" (https://www.tradeakademi.com/traderlarin-en-sik-yaptigi-5-strateji-hatasi). Hesaptablosu.net gibi siteler maliyet ortalama hesaplama araçları çok popüler — pattern bu kadar yaygın.

### 10.3 Pratisyen Söylem (Ordinal)

| Kategori | Yoğunluk |
|---|---|
| "Stop koymam, ortalama düşürürüm" | **Yüksek** |
| Disiplinli stop kullanımı | Orta-Düşük |
| ATR/teknik stop | Düşük |
| Time-stop | **Yok** |
| Drawdown metrik (UI/Calmar) | **Yok** retail |
| Vol-targeting | **Yok** retail |
| YouTube "risk yönetimi" Türk borsa | Orta-Yüksek (gözlem dolaylı, sample edilmedi) |

**Erişim Notu:** YouTube kanalları (Murat Sağman, Doğukan Kasapoğlu, Tugay Özek) referans olarak zikredildi ancak içerik **örneklenmedi**. Twitter/X login-wall.

### 10.4 Aktif vs Pasif

**Argüman:** "Buy-and-hold yeter, risk yönetimi gereksiz" — Türk retail'de yaygın 2023–2024 rally döneminde.

**Karşı:** 2024 BIST +%20 nominal, TÜFE +%44.38 (TurkStat, Aralık 2024 — bne IntelliNews verbatim: "Turkey's consumer price index (CPI) inflation officially stood at 44.38% y/y in December [2024] versus 47.09% y/y in November and 64.77% at end-2023, the Turkish Statistical Institute (TUIK, or TurkStat) said on December 3", https://www.intellinews.com/turkey-s-44-y-y-official-end-2024-inflation-release-suggests-another-250bp-rate-cut-in-late-january-359762/) → **reel −%17**. Aktif risk yönetimi 2018 USD −%44, 2020 −%25 dönemlerinde değer üretti.

**Sonuç:** Aktif vol-aware sizing + DD soft gate uzun horizon retail için **zorunlu**. Cagan profili için özellikle önemli.

**Erişim Notu / Limitations:** Türk hedge fund / family office DD pratik verisi public sınırlı; SPK UCITS-tarzı rehberi var, fon-bazlı detay TEFAS bireysel arama gerektirir.

---

## 11. Implementation Roadmap

### Faz 1 — Vol-Scaling Temel (2 Hafta)

**Definition of Done:**
- ✅ `realized_vol_20d(ticker)` ve `realized_vol_portfolio()` yfinance üzerinden.
- ✅ `vol_scalar = clip(target/realized, 0.20, 1.50)` hesaplanıyor.
- ✅ Daily reporting'da vol_scalar, σ_realized, σ_target.
- ✅ **Gözlem modu**, pozisyon kararına dahil değil.
- ✅ Builder pseudo-test outputs 7 kriz dönemi için.
- ✅ Sanity başarı: normal rejimde 0.7–1.1, kriz 0.2–0.5.

### Faz 2 — Drawdown Soft Gate (1 Ay)

**Definition of Done:**
- ✅ `current_drawdown` her gün; equity peak persistent storage.
- ✅ DD ordinal kademe (%5/%10/%15).
- ✅ Soft gate aktif: pozisyon × min(vol_scalar, dd_scalar).
- ✅ Mevcut hard exit %15 **korunuyor**.
- ✅ Ulcer Index, Calmar, Sortino daily reporting.
- ✅ Builder validation 7 kriz DD trigger ±5 gün tolerans.

### Faz 3 — Tam Kelly + Vol + DD Integration (Phase 5)

**Definition of Done:**
- ✅ `position_sizer_v3` v2 ile yan yana (a/b switch).
- ✅ CB-002 × vol_scaler × dd_scalar **min()** aktif.
- ✅ Risk Parity Lite (MAX_SINGLE_VOL_CONTRIB = 0.40).
- ✅ Time-stop sinyal-bazlı.
- ✅ ATR-based stop MAX alternatif.
- ✅ EWMA vol estimation.
- ✅ Cagan v3 simulated DD ≤ %12, Calmar ≥ 1.0, UI ≤ 6.0.

---

## 12. Akademik Kaynak Özeti

| Yazar (Yıl) | Başlık | Yayın | DOI/URL |
|---|---|---|---|
| Moreira & Muir (2017) | Volatility-Managed Portfolios | JoF 72(4):1611–1644 | 10.1111/jofi.12513 ; https://www.nber.org/papers/w22208 |
| Harvey et al. (2018) | Impact of Volatility Targeting | JPM 45(1):14–33 | 10.3905/jpm.2018.45.1.014 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538 |
| Thorp (1969) | Optimal Gambling Systems | Review Int Stat Inst | http://www.edwardothorp.com/wp-content/uploads/2016/11/KellySimulationsNew.pdf |
| Vince (2007) | The New Money Management | Wiley | ISBN 978-0470067321 |
| Martin & McCann (1989) | Investor's Guide / Ulcer Index | Wiley | https://chartschool.stockcharts.com/.../ulcer-index |
| Young (1991) | Calmar Ratio | Futures Magazine | https://en.wikipedia.org/wiki/Calmar_ratio |
| Subrahmanyam (1994) | Circuit Breakers and Market Volatility | JoF 49(1):237–254 | https://ideas.repec.org/a/bla/jfinan/v49y1994i1p237-54.html |
| Greenwald & Stein (1991) | Transactional Risk | JBusiness | — |
| DeBondt & Thaler (1985) | Does the Stock Market Overreact? | JoF 40(3):793–805 | 10.1111/j.1540-6261.1985.tb05004.x |
| Rockafellar & Uryasev (2000) | Optimization of CVaR | J Risk 2(3):21–41 | 10.21314/JOR.2000.038 ; https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf |
| Sortino & van der Meer (1991) | Downside Risk | JPM Summer 1991 | https://en.wikipedia.org/wiki/Sortino_ratio |
| Shadwick & Keating (2002) | Omega Ratio | J Perf Measurement | — |
| Wilder (1978) | New Concepts in Technical Trading (ATR) | Trend Research | https://en.wikipedia.org/wiki/Average_true_range |
| Hardin (2010) | Trading Halts and Investor Welfare | finance studio | — |
| Schwager & Stewart (2010) | Pain Index / Pain Ratio | trader literature | — |
| Çelik (2021) | Volatility of BIST 100 Returns After 2020 | J BRSA Banking Fin Markets 15(1):61–81 | https://www.researchgate.net/publication/354031179 |

---

## 13. Kısıtlar & Caveatlar

1. **Crisis period analiz forward-looking değil.** Bölüm 4 retrospektif; Builder validation framework'ü gerekli.
2. **Vol-targeting trend-following ile çelişebilir.** Harvey et al. 2018 kabul eder; Sharpe net pozitif.
3. **Türkiye 2022–2026 hiperenflasyon tam akademik analiz yok.** Moreira & Muir + Harvey et al. ABD odaklı; BIST literatür boşluğu (Çelik 2021 EGARCH var ama vol-managed değil).
4. **Long-only retail için tam Kelly tehlikeli.** Cagan profili → half/quarter-Kelly.
5. **Kavramsal counterfactual ≠ gerçek backtest.** ±%15 sapma realistic.
6. **Kapanış fiyatları intraday undersample.** ±%15 vol hata payı.
7. **Hiperenflasyon nominal-reel ayrımı.** TÜFE deflatörü uygulanmalı (kapsam dışı).
8. **CB-002 × vol_scaler iki-rejim varsayar.** Üçüncü rejim (rejim değişimi anı) aciliyet planı Phase 5.
9. **ENERY 5Y beta BULUNAMADI.** Ağu 2023 IPO, kısa geçmiş.
10. **Türk hedge fund DD verbatim public sınırlı.**
11. **YouTube içerikleri örneklenmedi.**
12. **Twitter/X login-wall.**
13. **AKSEN satış (24 May 2026)** post-mortem retrospektif değerlendirme önerilir.
14. **RR-014 Slippage entegrasyonu kapsam dışı**; vol-scaling pozisyon değişimleri slippage maliyeti artırabilir — RR-014 metodolojisi ile hesaplanmalı.
15. **BIST 100 2020 Mart trough TRY −%25** doğrudan kaynaklı verbatim BULUNAMADI; S&P 500 aynı dönem −%34 belgelenmiş (NBER/Avantis), BIST için Builder Borsa İstanbul historik veri kontrol önerilir.

---

**Rapor Sonu — Builder Validation Framework için Sonraki Adımlar:**

1. Bölüm 4'teki 7 kriz dönemi için DD trigger ve vol_scalar tarih tahminlerini OHLCV verisi üzerinde **post-hoc** test et.
2. Bölüm 6.6 pseudo-test scenarios'unu unit test olarak yaz.
3. Bölüm 9.4 ENERY vol contribution dominance flag'i daily reporting integration test.
4. Cagan portföyü için "kavramsal v3" pozisyon önerisinin "mevcut v2"den ne kadar saptığını yan-yana karşılaştır.
5. Faz 1 success criteria (vol_scalar normal 0.7–1.1, kriz 0.2–0.5) sağlandığında Faz 2'ye geç.