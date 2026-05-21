# BIST Algoritmik Trading: Linear Additive Composite Ötesinde 4 Kurumsal Alternatif — Bulgu Raporu

## TL;DR

- **Önce yapılması gereken**: Regime-Conditional Weights (HMM tabanlı) — akademik temeli en sağlam (Hamilton 1989; Asness/Moskowitz/Pedersen 2013), Borsa İstanbul'da empirik olarak doğrulanmış MS-AR/HMM çalışmaları mevcut (Şenol 2020; Samırkaş 2021; Yağcılar 2021; Doğan & Bilge 2022), mevcut Python (hmmlearn) altyapısıyla 1-2 hafta içinde entegre edilebilir ve bootstrap literatür-priorları ile IC verisi olmadan başlatılabilir; literatürde Sharpe iyileşmesi ~+0.29 (Northern Trust "Dynamic Factor Timing") ila +%80 göreceli (Neuhierl et al. AEA 2024: 0.31 → 0.53 large-cap CRSP) düzeyinde raporlanıyor.
- **İkinci öncelik**: Non-Linear Composite (XGBoost ile dinamik IC ağırlıklandırması) — Liao & Li (2019, IEEE) XGBoost-tabanlı dinamik ağırlığın hem eşit hem statik-IC ağırlığını ampirik olarak geçtiğini gösteriyor; ancak <500K TL ölçek + ayda <20 işlem rejiminde overfitting riski yüksek, López de Prado'nun (2018) Purged K-Fold + CPCV CV protokolü ve Deflated Sharpe Ratio mecburi.
- **Şu an yapılmamalı**: Tam Transformer/Attention composite (BIST için doğrulanmış çalışma bulunamadı, veri açlığı, 5/5 karmaşıklık) ve tam 5-LLM jüri (TradingAgents v7: günde 11 LLM çağrısı + 20+ tool çağrısı; iMAD 2025 (arXiv:2511.11306) ortalama maliyeti tam olarak "three to five times more tokens than single-agent" şeklinde belgeliyor) — pilot olarak ucuz "2-LLM cross-check + disagreement-aware sizing" ile başlanabilir.

## Key Findings

| Alternatif | Akademik Temel | BIST Uygulanabilirlik | Entegrasyon (1-5) | Alpha Katkısı (Literatür) | Öncelik |
|---|---|---|---|---|---|
| **1. Attention/Transformer Composite** | Vaswani 2017; Liu et al. 2022 (TEANet) | Düşük: BIST-özel çalışma yok, veri açlığı, overfit | 5/5 | BIST için bilinmiyor; ABD'de fiyat tahmini iyileşmesi var, composite-ağırlık için doğrudan değil | 4 |
| **2. Multi-LLM Jüri** | Du et al. 2023; Liang et al. 2024 (EMNLP); Xiao et al. 2024 (TradingAgents); Zhang et al. 2024 (FinAgent KDD) | Orta: dil-agnostik, ama Türkçe finansal ince-ayarlı LLM yok | 3/5 | TradingAgents: 3-aylık ABD testinde CR +%6-25, SR aşırı yüksek (8.21) ve yazarlarca uyarılmış; reasoning benchmark'ta +%7-15 puan; cost 3-5× | 3 |
| **3. Regime-Conditional Weights (HMM)** | Hamilton 1989 (Econometrica); Asness/Moskowitz/Pedersen 2013 (J. Finance, doi:10.1111/jofi.12021); Lo 2004 (JPM) | Yüksek: BIST'te 6+ ampirik MS/HMM çalışması | 2/5 | Sharpe +0.29 ortalama (Northern Trust); +%80 göreceli (Neuhierl et al. 0.31→0.53) | **1** |
| **4. Non-Linear Composite (XGBoost/Trees)** | Chen & Guestrin 2016; Liao 2019 (IEEE); López de Prado 2018 | Orta-Yüksek: tree-based BIST stock selection çalışmaları mevcut, overfit riski | 3/5 | Dinamik XGBoost > statik IC ağırlığı (Liao 2019); FactorMiner: 8 faktör Lasso ile full library'nin %95 IC iyileşmesini yakalıyor (ICIR=1.38, win rate %92.6) | **2** |

---

## Details

### BÖLÜM 1: Attention-Weighted Composite

**A. Teorik Temel.** Attention mekanizması Vaswani et al. (2017) "Attention is All You Need" (arXiv:1706.03762) ile başladı. Finansal zaman serisi uygulamaları:

- **Liu, Lin, Liu et al. (2022) "Transformer-based attention network for stock movement prediction" (TEANet)** — Expert Systems with Applications (https://www.sciencedirect.com/science/article/abs/pii/S0957417422006170). Yazarlar açıkça "small-sample feature engineering network framework" tanımlıyor; sosyal medya metni + fiyat füzyonu; küçük örneklemde transformer kullanma denemesinin pratik referans noktası.
- **Li et al. (2022) "Incorporating Transformers and Attention Networks for Stock Movement Prediction"** — Complexity, Hindawi (https://www.hindawi.com/journals/complexity/2022/7739087/).
- **"A Survey on Deep Tabular Learning" (arXiv:2410.12034, 2024)** — TabNet (Arik & Pfister 2021), FT-Transformer (Gorishniy et al. 2021), SAINT, TabTransformer karşılaştırması. Survey: *"Hybrid architectures such as TabTransformer and FT-Transformer integrate attention mechanisms with multi-layer perceptrons (MLPs) to handle categorical and numerical data, with FT-Transformer adapting transformers for tabular datasets."*
- **TabPFN/TabPFNv2 (Hollmann et al. 2025)** — 10K örneklem altı tabular veriler için pre-trained transformer; finansal ince-ayar mümkün ama veri-gürültü oranı sorunu sürüyor.

**Pratik mekanizmalar — Mixture of Experts (MoE)**: Klasik MoE (Jacobs/Jordan/Hinton 1991) gating network ile uzmanları rejime göre seçer; finansal varyantı **MoE-F (ICLR 2025)** — paralel stokastik filtreler dinamik olarak en iyi LLM kombinasyonunu seçiyor (https://proceedings.iclr.cc/paper_files/paper/2025/file/d4c2f25bf0c33065b7d4fb9be2a9add1-Paper-Conference.pdf). "Different experts handle different market conditions" yorumu doğrudan rejim-koşullu mimari ile örtüşüyor.

**B. BIST Uygulanabilirlik.** BIST için doğrulanmış transformer veya attention-based **composite** mimari çalışması **bulunamadı** (arXiv/SSRN/Borsa Istanbul Review taramasında doğrudan eşleşme yok). Yakın eşler:
- Bangladesh borsası için transformer (World Scientific, https://www.worldscientific.com/doi/10.1142/S146902682350013X) — emerging market örneği; küçük veriden öğrenme zorluğunu vurguluyor.
- Türkiye için Karamollaoğlu (2025, Turk J Electr Power Energy Syst, doi:10.5152/tepes.2025.25029) elektrik üretiminde transformer kullanımını gösteriyor ama BIST hisse senedi için değil.

**Risk değerlendirmesi (akademik)**: Transformer'lar veri-açgözlüdür. "Improving Portfolio Performance Using a Novel Method for Predicting Financial Regimes" (arXiv:2310.04536) açıkça not eder: *"deep learning models have been less-used due to a relative scarcity of data and consequent risk of overfitting these complex models."* BIST'te CEIC Data'ya göre Mart 2026 itibarıyla 660 listelenmiş şirket × ~5000 işlem günü = teorik panel ~3.3M satır; ancak signal-to-noise oranı düşük, attention-head başına etkin örneklem küçük ve KAP/yfinance birleşik temiz panel çok daha küçüktür.

**C. Mevcut Mimariye Entegrasyon.** 6-layer composite üstüne attention layer eklemek için iki yol:
1. **Sıfırdan eğitim**: 6 layer skor zaman serisi → tek-başlık FT-Transformer/TabNet → composite skor. PyTorch + `pytorch-tabnet` veya `tab-transformer-pytorch` (lucidrains; https://github.com/lucidrains/tab-transformer-pytorch). Eğitim verisi gereksinimi: en az 10K etiketli BIST gözlem; yfinance + EVDS ile teorik olarak ulaşılabilir, ama label gürültüsü yüksek.
2. **Pre-trained finansal model**: BloombergGPT (proprietary, erişilemez), FinGPT (https://github.com/AI4Finance-Foundation/FinGPT) — ABD verisi üzerinde eğitilmiş; BIST transfer learning denenmemiş.

**Entegrasyon karmaşıklığı: 5/5.** Python araç zinciri mevcut (torch, hmmlearn, transformers) ama BIST-özel etiketleme, hyperparameter tuning, walk-forward CV, GPU veya en azından Apple Silicon MPS gerekir; mevcut Claude API kullanan asenkron mimariden ciddi sapma. Tipik bir prototip 4-8 hafta + dedicated ML engineer.

**D. Tahmini Alpha Katkısı.** **BIST için bilinmiyor.** Wang et al. (2022) transformer Çin/ABD indekslerinde RNN/LSTM'yi geçti ama bu fiyat tahmini, layer-composite ağırlıklandırması değil. **Doğrudan karşılaştırılabilir BIST sonucu yoktur**.

---

### BÖLÜM 2: Multi-LLM Ensemble Jüri

**A. Teorik Temel.** Multi-agent debate (MAD) literatürünün üç köşe taşı:

- **Du, Li, Torralba, Mordatch (2023) "Improving Factuality and Reasoning in Language Models through Multiagent Debate"** — arXiv:2305.14325; ICML 2024 (https://dl.acm.org/doi/10.5555/3692070.3692537). Verbatim sonuçlar (gpt-3.5-turbo-0301, 3 ajan × 2 tur):
  - Arithmetic: %67.0 → %81.8 (**+14.8 puan**)
  - GSM8K: %77.0 → %85.0 (**+8.0 puan**)
  - MMLU: %63.9 → %71.1 (**+7.2 puan**)
  - Biographies: %66.0 → %73.8 (**+7.8 puan**)
  - Chess Move Validity: %29.3 → %45.2 (**+15.9 puan**)
  - Çoklu-model debate (ChatGPT + Bard, 20 GSM8K): Bard 11, ChatGPT 14, debate 17 doğru.
- **Liang, He, Jiao et al. (2024) "Encouraging Divergent Thinking in LLMs through Multi-Agent Debate"** — EMNLP 2024 (doi:10.18653/v1/2024.emnlp-main.992; arXiv:2305.19118). "Moderate disagreement maksimum disagreement'tan daha iyi sonuç veriyor"; agent-heterogeneity (farklı model aileleri) anahtar bulgu.
- **Chan, Chen, Su et al. (2023) "ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate"** — arXiv:2308.07201; LLM-as-Judge paradigmasının jüri formuna evrimi.

**LLM-as-Judge kalibrasyon problemleri:**
- **Tan et al. (2025) "Overconfidence in LLM-as-a-Judge"** — arXiv:2508.06225. "Confidence exceeds accuracy" — LLM-as-Fuser ensemble framework JudgeBench'te +%47.14 doğruluk, ECE %53.73 iyileşme.
- **DISCOUQ (arXiv:2603.20975)**: 5-ajan Qwen3.5-27B sisteminde AUROC 0.802, ECE 0.036; "disagreement structure" sinyali kalibrasyonu en iyi LLM Aggregator baseline'ından (ECE 0.098) ciddi şekilde iyileştiriyor.

**B. Trading Spesifik (Quantitative Backtests).**

- **TradingAgents (Xiao, Sun, Luo, Wang 2024, arXiv:2412.20138 v7)** — fundamental/sentimental/technical analyst rolleri + bull/bear araştırmacı debate + risk yönetim ekibi. Test: 1 Oca–29 Mart 2024 (3 ay), 3 hisse. Verbatim sonuçlar (kağıt Tablo 1):

| Hisse | Strateji | CR % | SR | MDD % |
|---|---|---|---|---|
| AAPL | Buy & Hold | -5.23 | -1.29 | 11.90 |
| AAPL | TradingAgents | **26.62** | **8.21** | **0.91** |
| GOOGL | Buy & Hold | 7.78 | 1.35 | 13.04 |
| GOOGL | TradingAgents | **24.36** | **6.39** | **1.69** |
| AMZN | Buy & Hold | 17.10 | 3.53 | 3.80 |
| AMZN | TradingAgents | **23.21** | **5.60** | **2.11** |

  Yazarların **kendi uyarısı** (verbatim): *"The highest Sharpe Ratio exceeds our expected empirical range (SR above 2 – very good, above 3 – excellent)... we believe the exceptionally high SR resulted from the phenomenon that there were few pullbacks in TradingAgents during that period."* Maliyet: *"11 LLM calls & 20+ tool calls/prediction."*

- **FinAgent (Zhang et al. 2024, KDD '24; https://personal.ntu.edu.sg/boan/papers/KDD24_FinAgent.pdf)** — Test 2023-06-01 → 2024-01-01, 6 varlık. Verbatim: *"FinAgent significantly outperforms 12 state-of-the-art baselines in terms of 6 financial metrics with over 36% average improvement on profit. Specifically, a 92.27% return (a 84.39% relative improvement) is achieved on one dataset."* Ancak ETHUSD'da FinMem'in altında performans gösteriyor — homojen olmayan.
- **FinMem (Yu et al. 2023)** ve **FinGPT (Yang, Liu, Wang 2023, arXiv:2307.10485)**: ajan-tabanlı/açık-kaynak LLM trader'lar. BloombergGPT eğitimi: $2.67M, 0.65M GPU saat (kaynak: arXiv:2307.10485 Appendix A).

**C. Pratik Tasarım.**
- **Önerilen LLM'ler**: Claude 4 Sonnet (mevcut), GPT-4o/5, Gemini 2.0/2.5, Llama 3.3 70B, DeepSeek-V3. Heterojen aileler (Liang et al. 2024 bulgusu).
- **Karar protokolü**:
  - Simple majority (3/5) — Du et al. 2023 baseline.
  - Supermajority (4/5) — daha az false-positive ama daha çok abstain.
  - Disagreement score = entropy(votes); >0.7 ise pozisyon küçültme veya skip.
- **Maliyet analizi**: iMAD (Fan, Yoon, Ji 2025, arXiv:2511.11306) verbatim: *"Most MAD systems consume three to five times more tokens than single-agent baselines."* GroupDebate (Liu et al., arXiv:2409.14051): MAD token tüketimini %51.7'ye kadar azaltabilen optimizasyon mevcut. TradingAgents pratiğinde 11× çağrı çarpanı. <500K TL portföyde günlük 5-10 ticker × 5 LLM × ~$0.02 = $0.50-$1.00/gün; aylık ~$15-30 — kabul edilebilir.

**D. Mevcut Mimariyle Entegrasyon: 3/5.** Mevcut Claude tek-LLM Strategist'i, asyncio paralel jüri'ye evrilebilir (4-5 saatlik prototip mümkün). Audit trail için her LLM'in raw yanıtı + final vote JSON olarak loglanabilir. Disagreement score doğrudan L7 (yeni "consensus" katmanı) olarak composite'e eklenebilir. **BIST için**: Türkçe finansal jargon (KAP filings, TCMB metni) için Claude/GPT-4o iyi; DeepSeek-V3 ve Llama 3.3 Türkçe finansta zayıflar — heterojenite vs Türkçe kalite trade-off'u.

**Tahmini Alpha**: BIST için **bilinmiyor**. ABD 3-ay penceresinde +%6-25 cumulative return (TradingAgents, overfit şüphesi yüksek). Reasoning benchmark'larında +%7-15 puan; finansal alpha'ya çevrim doğrulanmadı.

---

### BÖLÜM 3: Regime-Conditional Weights (CB-002 Derinleştirme)

**A. Teorik Temel.**
- **Hamilton, J.D. (1989) "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle"** — Econometrica 57(2):357-384. Markov regime-switching'in pioneer makalesi.
- **Asness, C.S., Moskowitz, T.J., Pedersen, L.H. (2013) "Value and Momentum Everywhere"** — Journal of Finance 68(3):929-985; doi:10.1111/jofi.12021 (https://onlinelibrary.wiley.com/doi/10.1111/jofi.12021). Value ve momentum'un 8 piyasada tutarlı varlığı; -0.50 ile -0.60 arası korelasyon — rejim-koşullu rotasyon için akademik temel.
- **Lo, A.W. (2004) "The Adaptive Markets Hypothesis"** — Journal of Portfolio Management 30:15-29 (https://web.mit.edu/Alo/www/Papers/JPM2004_Pub.pdf). Faktör premia'larının rejim ve evrim ile değişimi; AMH = rejim-koşullu modelin teorik gerekçesi.
- **Guidolin & Timmermann (2008)**, **Ang & Bekaert (2002)**, **Ang (2023)** — regime-switching factor models literatürünün omurgası.

**B. BULL/BEAR/NEUTRAL Faktör Ağırlıkları (literatür konsensüs sentezi).**

| Rejim | Momentum | Value | Quality | Low-Vol | L1 (Tech) | L2 (Macro) | L5 (Smart Money) |
|---|---|---|---|---|---|---|---|
| BULL | Yüksek ↑ | Düşük ↓ | Orta | Düşük ↓ | Yüksek | Orta | Yüksek |
| BEAR | Negatif ↓ | Orta | Yüksek ↑ | Yüksek ↑ | Düşük | Yüksek | Orta |
| NEUTRAL | Orta | Yüksek ↑ | Orta | Orta | Orta | Orta | Orta |

Kaynak sentezi: Asness et al. 2013 + AQR araştırma raporları + **Northern Trust "Dynamic Factor Timing"** (https://ntam.northerntrust.com/content/dam/northerntrust/investment-management/global/en/documents/research/quantitative/dynamic-factor-timing.pdf). Verbatim: *"Over the past 18 years, the factor timing strategy improved the out-of-sample Sharpe ratio of the equally weighted portfolio by an average... improving the Sharpe ratio by 0.29 on average."* 6 farklı faktör kombinasyonunda dinamik timing eşit-ağırlıklı baseline'ı **her durumda** geçiyor.

**C. BIST'e Spesifik Empirik Kanıt.**
- **MDPI 2020 "Regime-Switching Factor Investing with Hidden Markov Models" (Wang, Wang, Zhang; https://www.mdpi.com/1911-8074/13/12/311)** — 3-state HMM (bull/bear/neutral), `hmmlearn` GaussianHMM kullanımı; mekanizma BIST'e doğrudan uygulanabilir.
- **Doğan & Bilge (2022) "Testing the Augmented Fama-French Six-Factor Asset Pricing Model with Momentum Factor for Borsa Istanbul"** — Discrete Dynamics in Nature and Society 2022:3392984; doi:10.1155/2022/3392984 (https://onlinelibrary.wiley.com/doi/10.1155/2022/3392984). 2013-2021 dönemi, 396 hafta, 9504 portföy: momentum faktörü BIST'te istatistiksel olarak anlamlı, Six-Factor Model en iyi açıklayıcı.
- **Şenol (2020), Samırkaş (2021), Yağcılar (2021)** — BIST100 üzerinde MSIH(2)-AR(1) Markov rejim modelleri: iki rejim (yüksek volatilite/düşük getiri = bear; düşük volatilite/yüksek getiri = bull); bull rejimde ortalama kalış süresi 64 ay vs bear 11 ay; rejim-içi kalma olasılığı yüksek (sticky regimes).
- **Borsa Istanbul Review 2024 "Conditional effects of higher order co-moments"** (https://www.sciencedirect.com/science/article/pii/S2214845024001005) — Co-skewness/co-kurtosis BIST'te up/down piyasalarda farklı pricing — koşullu (regime-conditional) faktör mantığını doğrudan destekleyen empirik bulgu.
- **MDPI 2025 BIST Sustainability Index Markov Regime Switching** — kriz rejimlerinde varyans yaklaşık 8.5 kat artıyor, normal rejimde Beta 0.76; BIST için iki-rejim yapısı sağlam.

**D. Bootstrap Stratejisi (IC olmadan).**
- **Adım 1**: Literatür-priorları olarak BULL/BEAR/NEUTRAL için yukarıdaki tablo ağırlıkları başlat (uzman görüş + Asness et al. ortalaması).
- **Adım 2**: HMM'i BIST100 daily return + 20-gün rolling volatility + USD/TRY change üzerinde eğit (`hmmlearn` GaussianHMM, `n_components=3, covariance_type="full", n_iter=500, tol=1e-4`). Referans implementasyon: QuantStart (https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/) ve PyQuantLab (https://www.pyquantlab.com/articles/Market%20Regime%20Detection%20using%20Hidden%20Markov%20Models.html).
- **Adım 3**: Bayesian updating — her ay sonunda gerçekleşen layer-getirisi (proxy IC ≈ Spearman(L_i_score, forward_return)) ile Beta veya normal-conjugate posterior güncellenir.
- **Adım 4**: Walk-forward calibration: 12 ay rolling pencerede, son 36 ay üzerinden retrain.
- **Out-of-sample test**: Limited Turkish data için Combinatorial Purged CV (López de Prado 2018) zorunlu — embargo ile veri sızıntısını engelle.

**HMM seçenekleri**: `hmmlearn` (en yaygın, sklearn-uyumlu), `pomegranate` (daha esnek), `statsmodels` MarkovRegression. **Alternatifler**: Markov Switching ARCH (Hamilton & Susmel 1994), Gaussian Mixture Models, Threshold Autoregressive (TAR), **Statistical Jump Models (Aydınhan, Kolm, Mulvey, Shu 2024, arXiv:2402.05272)** — HMM'in mis-estimation problemlerine çözüm önerisi; Bayesian Changepoint (BIST üzerinde uygulanmış, ScienceDirect S1051200415000433).

**Entegrasyon karmaşıklığı: 2/5.** Mevcut Python + yfinance/EVDS stack ile bütünüyle uyumlu. `pip install hmmlearn` ile kurulur. CB-002 için zaten geçici bir regime detector planlandı — bu derinleştirme HMM'i kalıcılaştırır + rejim-koşullu ağırlık tablosu ekler. 1-2 hafta için MVP, 4 hafta tam üretim.

**Tahmini Alpha Katkısı.**
- **Northern Trust**: Sharpe +0.29 ortalama (institutional, ABD; 18-yıl OOS).
- **Neuhierl, Randl, Reschenhofer, Zechner "Timing the Factor Zoo" (AEA 2024, SSRN:4376898)**: PLS1-timing ile *"Sharpe ratio by roughly 80% to 0.53 (relative to 0.31 for the market-weight CRSP large-cap universe)"* — %80 göreceli iyileşme.
- **"Dynamic Factor Allocation Leveraging Regime-Switching Signals" (Shu, Mulvey 2024, arXiv:2410.14841)**: statik tahsisi geçen information ratio + Sharpe iyileşmesi, max drawdown azalması.
- **BIST için spesifik alpha tahmini bulunamadı**; emerging market discount uygulayarak konservatif tahmin: yıllık **+150-300 bps** (eşit-ağırlık baseline üzerinde), Sharpe **+0.15-0.25** — **bu doğrulanmamış bir interpolasyondur**.

---

### BÖLÜM 4: Non-Linear Composite

**A. İnteraksiyon Terimleri.**
- L1 × L2 (momentum × macro favorable), L3 × L5 (KAP × smart money), L2 × L6 (macro × volatility) — domain-driven feature crosses.
- Polynomial (degree-2) features: 6 layer için C(6,2)=15 interaction; manageable.
- **Empirik kanıt (BIST)**: Doğrudan interaction çalışması bulunamadı. Ancak **Borsa Istanbul Review 2024 (S2214845024001005)** co-skewness × market direction'ın istatistiksel anlamlılığını gösteriyor — analog mantık L1 × L2 etkileşim terimi için savunulabilir empirik temel.

**B. Tree-Based Methods.**
- **Liao & Li (2019) "Dynamic Weighting Multi Factor Stock Selection Strategy Based on XGBoost Machine Learning Algorithm"** — IEEE; https://ieeexplore.ieee.org/document/8690416. Verbatim: *"The empirical results prove that XGBoost model is effective in predicting IC coefficients and the dynamic weighting based on XGBoost model can improve the performance of multi-factor stock selection strategy"* — eşit ağırlık ve statik IC'yi geçen ampirik bulgu.
- **MDPI 2020 "A Sustainable Quantitative Stock Selection Strategy Based on Dynamic Factor Adjustment"** (https://www.mdpi.com/2071-1050/12/10/3978): aylık rebalance XGBoost top-20 stock seçimi A-share'de uygulandı.
- **FactorMiner (arXiv:2602.14670)**: *"With only 8 factors, Lasso captures 95% of the IC improvement achievable by the full library."* XGBoost ICIR=1.38, win rate %92.6 — "Pareto principle: most predictive information is concentrated in a small subset" — küçük layer setiyle uyumlu bulgu.
- **Combined ML (arXiv:2508.18592, 2025)**: XGBoost + LightGBM + AdaBoost stacked ensemble, rolling IC ağırlıklarıyla.
- **SHAP** (Lundberg & Lee 2017) — interpretability için zorunlu; tree'lerin "kara kutu" eleştirisini kapatır.

**C. Neural Composite.** Shallow MLP (1-2 hidden layer, 32-64 unit, dropout 0.3) küçük datada XGBoost'a yakın çıkabilir ama interpretability düşük. TabNet (Arik & Pfister 2021) küçük tabular verilerde attention-mask ile feature selection yapıyor — orta seçenek; Wide & Deep (Cheng et al. 2016) feature crosses için klasik alternatif.

**D. Overfitting Riski (<500K TL).**
- Tipik retail BIST portföy ayda 5-15 trade, yılda 60-180 trade. Tree-based model için "n >> p" kuralı: 100+ trade per parameter; XGBoost varsayılan ~50 ağaç × 6 derinlik = ciddi kapasite. Sınırlı veride **L1/L2 regularization + `max_depth ≤ 3` + `early_stopping_rounds=20`** mecburi.
- **López de Prado (2018) "Advances in Financial Machine Learning"**: Standart k-fold CV finansta GEÇERSİZ (IID varsayımı çiğnenir). Purged K-Fold + Embargo + Combinatorial Purged CV (CPCV) zorunlu (https://www.quantbeckman.com/p/with-code-combinatorial-purged-cross). Verbatim: *"Because observations cannot be expected to be drawn via an IID process, k-fold CV fails in finance."*
- **Backtest Overfitting (Bailey, López de Prado et al.)**: Probability of Backtest Overfitting (PBO) hesaplaması, Deflated Sharpe Ratio uygulaması — multi-testing penalty.
- "Curse of dimensionality": 6 layer skor + 15 interaction = 21 feature; <200 trade örneklem için risk yüksek. **G-XGBoost (Tandfonline, 2021)**: synthetic data + XGBoost ile küçük örneklem problemi için akademik çözüm önerisi.
- **Lo & MacKinlay heuristik'i**: Strategy 50+ bps yıllık alpha üretmiyorsa ML overfit muhtemel.

**Entegrasyon karmaşıklığı: 3/5.** `xgboost`, `lightgbm`, `shap`, `mlfinlab` (López de Prado utility'leri) pip ile kurulur. Mevcut composite_score hesaplamasının yerine `model.predict()` koymak basit; ama doğru CV setup'ı, hyperparameter tuning (Optuna), feature engineering pipeline kurmak 2-3 hafta.

**Tahmini Alpha Katkısı.** Liao 2019 IEEE: statik IC ağırlığına göre dinamik XGBoost ağırlığı pozitif fark (kesin sayı paywall arkasında, abstract niteliksel doğrulama). MDPI 2020 strategy: A-share aylık rebalance ile market benchmark'ı geçen kümülatif getiri. **BIST'e direkt alpha tahmini yapılamıyor**; konservatif interpolasyon: yıllık **+50-150 bps** net (overfitting tax sonrası), Sharpe **+0.05-0.15** — **doğrulanmamış**.

---

## Recommendations

### Aşama 1 (Hemen — 1-2 Hafta): Regime-Conditional Weights MVP

1. `hmmlearn` ile 3-state GaussianHMM kur; input: BIST100 daily log-return + 20d rolling volatility + USD/TRY change + TCMB faiz değişimi.
2. State labeling: ortalama getiri + volatilite ile BULL/NEUTRAL/BEAR ata; sticky regime için `n_iter=500, tol=1e-4`.
3. Literatür-prior ağırlık tablosu (Bölüm 3-B matrisi) kodla; başlangıçta sabit.
4. Walk-forward: her ay sonu retrain (rolling 36-ay pencere).
5. CB-002'deki regime detection kodunu HMM ile değiştir; mevcut composite_score'u `composite_score = Σ(w_i(regime_t) × L_i_score)` formuna evrilt.
6. **Geçiş eşiği**: 3 ay boyunca eşit-ağırlık baseline'a karşı in-sample Sharpe ≥ +0.15 ve drawdown ≤ baseline; aksi takdirde priors revize.

### Aşama 2 (1-2 Ay Sonra): XGBoost Layer Combiner (Sadece IC Verisi Birikince)

1. Aşama 1'den ≥6 ay layer-skor + forward-return verisi biriktiğinde başla.
2. Feature set: 6 layer skor + rejim one-hot + 15 interaction term.
3. Model: XGBoost (`max_depth=3, n_estimators=100, eta=0.05, reg_alpha=0.1, reg_lambda=1.0, early_stopping_rounds=20`); hedef: forward 5-gün return (regresyon) veya kazanan/kaybeden sınıflandırma.
4. CV: `mlfinlab` Purged K-Fold (k=5, embargo=10 gün).
5. SHAP ile interpret; baseline-üstü PBO < %30 ise ürüne al.
6. **Eşik**: Out-of-sample Sharpe iyileşmesi rejim-koşullu ağırlık baseline'ına karşı ≥ +0.10 ve Deflated Sharpe > 0; aksi halde rolled back.

### Aşama 3 (3-6 Ay Sonra): Multi-LLM Cross-Check (Tam Jüri Değil)

1. Mevcut Claude Strategist'in çıktısını **2-LLM cross-check** ile doğrula: Claude (mevcut) + GPT-4o veya Gemini 2.0. Disagreement varsa pozisyon büyüklüğünü %50 kıs.
2. Tam 5-LLM jüri YALNIZCA Aşama 1+2 stabilize olduktan ve aylık $50+ API bütçesi onaylandıktan sonra.
3. Karar protokolü: 2/2 unanimous (defansif), 1/2 disagreement → abstain veya size-reduce.
4. **Eşik**: 3-ay paralel testte 2-LLM disagreement-aware sizing tek-LLM'i ≥ +%5 risk-adjusted return ile geçiyorsa tam jüri'ye geç.

### Aşama 4 (Belirsiz — Şimdi Yapılmamalı): Tam Transformer Composite

Şart: ≥3 yıl yüksek-kaliteli BIST etiketlenmiş veri + GPU/MPS hesap kaynağı + dedicated ML-engineer. Mevcut <500K TL retail ölçekte ROI yetersiz.

### Aksiyon Tetikleyicileri (Eşikler)

- **HMM aşamasını durdur**: Out-of-sample 6-ay Sharpe baseline'dan kötüyse → faktör ağırlıklarını uzman-prior yerine veriden öğrenmeye geç (Bayesian update agresifleştir).
- **XGBoost aşamasını başlat**: Aşama 1'den ≥150 layer-skor × forward-return paneli birikmişse.
- **Jüri aşamasını başlat**: Tek-LLM Strategist'in ardışık 3 ay false positive oranı ≥%30 ise.
- **Transformer aşamasını ertele**: Veri panel boyutu < 10.000 etiketli gözlem veya Sharpe iyileşmesi alt-aşamalar tarafından doyurulduysa.

---

## Caveats

1. **TradingAgents (Xiao 2024) Sharpe 5-8 değerleri 3-ay × 3 hisse'den**; istatistiksel olarak güvenilmez — yazarlar bunu kendileri uyarıyor. Multi-LLM jüri'nin BIST alpha'sı doğrulanmadı; sayılar ABD bull-rally penceresine fazla bağımlı.
2. **BIST-spesifik attention/transformer composite çalışması bulunamadı** — Bölüm 1'in alpha tahmini doğrudan literatürden değil, ABD/Çin/Bangladesh sonuçlarından interpolasyondur.
3. **Liao & Li (2019) XGBoost dinamik ağırlık makalesinin kesin alpha sayısı IEEE paywall arkasında** — abstract'tan "superior to equal/static IC" niteliksel doğrulamayla yetinildi.
4. **<500K TL ölçek + retail eli ile her ay <20 trade rejiminde** ML tabanlı alternatifler (Bölüm 4 + tam attention) overfitting riski yüksek; çoğu akademik backtest aylık 100+ rebalance + 1000+ menkul kıymet evren varsayar.
5. **HMM regime detection'ın sınırı**: Hidden Markov Model "regime change sonrası" tespit eder, **ön-tahmin etmez** — arXiv:2310.04536: *"HMM can in effect only predict continuations of already-changed regimes."* Bu, geç giriş/geç çıkış riski yaratır; Statistical Jump Models (arXiv:2402.05272) bu sorunu kısmen çözüyor.
6. **LLM-as-Judge overconfidence**: Tan et al. 2025 (arXiv:2508.06225) jüri konsensüsünün gerçek doğruluktan daha yüksek confidence raporladığını gösteriyor; finansal kararlarda risk-yönetim için kalibrasyon (TH-Score veya LLM-as-Fuser) eklenmeli.
7. **Türkçe finansal NLP boşluğu**: FinBERT-EN BIST için askıya alındı; FinGPT/BloombergGPT Türkçe için ince-ayar yapılmadı. KAP filings + TCMB raporları için Claude/GPT-4o tercih edilmeli; küçük açık-kaynak modeller Türkçe finansta zayıf.
8. **López de Prado'nun PBO uyarısı**: Birden fazla alternatif eş zamanlı backtest edilirse, multi-testing penalty (Deflated Sharpe Ratio) uygulanmalı; aksi takdirde Aşama 2 + Aşama 3'ün gerçek alpha'sı şişirilmiş görünür.
9. **CB-002 ile çakışma**: Mevcut CB-002 regime detection bir önceki sprint'te araştırılmıştı; bu rapor onu HMM'e bağlıyor ama mevcut implementation detaylarını teyit etmedi — entegrasyon sırasında çakışma çıkabilir.
10. **Risk-free oranı**: TCMB MPC son güncel kararı (2026-17, Mayıs 2026) verbatim: *"The Committee has decided to keep the policy rate (the one-week repo auction rate) at 37 percent."* Brief'te belirtilen %42 (2024 zirvesi) güncel değil — Sharpe hesaplamasında **%37 nominal TRY** kullanılmalı. USD-bazlı backtest karşılaştırmalarında bu kritik (emerging market Sharpe'ı para birimine duyarlıdır).
11. **BIST evren büyüklüğü güncelleme**: CEIC Data (Mart 2026): 660 listelenmiş şirket — universe size beklenenden büyük; bu, XGBoost cross-sectional rebalance stratejilerinde Aşama 2 için daha geniş örneklem demek (lehine).
12. **Multi-LLM cost realism**: iMAD (arXiv:2511.11306) verbatim: *"Most MAD systems consume three to five times more tokens than single-agent baselines"* — token maliyeti tahminini disiplinli tutar. GroupDebate gibi optimizasyonlar bu yükü yarıya indirebilir, ama production-ready BIST jürisinde önce 2-LLM ile başlamak rasyoneldir.