# RR-018: BIST OS Trading System — López de Prado Tabanlı Backtesting Framework

**Versiyon:** 1.0 | **Tarih:** 25 Mayıs 2026 | **Yazan:** Research Agent
**Bağlam:** AUDIT_REPORT_001 D-061 C-1 closure + RR-014/015/016/017 entegrasyon
**Hedef Kitle:** Builder (implementation-ready); the maintainer (karar-verici); Public release recruiter testi

---

## 1. TL;DR

- **Mevcut `backtest/engine.py` yapısı akademik standartların altındadır ve go-live'ı tek başına bloke eder.** AUDIT C-1 bulgusu (production engine'den diverged hardcoded formula, current MASTER_WEIGHTS değişikliklerini yansıtmama) tüm raporlanmış Sharpe'ı şüpheli kılar. Ek beş yapısal eksiklik: (i) single-path walk-forward, (ii) IID varsayan k-fold yokluğu, (iii) survivorship bias (yfinance delisted ticker'ları kapsamaz), (iv) çoklu-deneme penaltısı olmadan raporlanmış Sharpe, (v) 6 aylık pencere içinde 7 kriz döneminden hiçbirini içermeyen "crisis-untested" tablo. Bu kombinasyon, bugünkü Sharpe raporlarının %30-60 aralığında enflasyonist olmasını beklenir kılar (Bailey & López de Prado 2014'ün selection bias büyüklüğü ile uyumlu).
- **Önerilen yapı López de Prado (2018) *Advances in Financial Machine Learning* Bölüm 7 (Purged K-Fold s.103-111), Bölüm 12 (Combinatorial Purged CV), Bölüm 14 (Backtest Statistics) ve Bölüm 15 (Strategy Risk s.211-220) üzerine kuruludur**; Bailey-Borwein-López de Prado-Zhu (2014 Notices of AMS / 2017 JCF 20(4):39-69) Deflated Sharpe + Probability of Backtest Overfitting (PBO) ile tamamlanır. BIST OS kalibrasyon: **k=5 Purged K-Fold, purge=10 gün, embargo=5 gün** (RR-010 ile tutarlı), **CPCV: N=6, k=2, 15 patika**, geçiş eşikleri **DSR > 0.95 + PBO < 0.5**.
- **the maintainer'ın $0 maliyet hedefi karşılanabilir.** Hudson & Thames mlfinlab Aralık 2020 "Unlocking the Commons" sponsorluk hedefini tutturamayıp tamamen ticarileşti — bugün **£100 + KDV / ay / kullanıcı**, sadece QuantConnect Cloud üzerinden (verbatim QC docs). Buna karşılık (i) **sam31415/timeseriescv 0.2 MIT** (CombPurgedKFoldCV, PurgedWalkForwardCV — ancak Issue #6'da unit testler "all your tests are failing" raporlu; kendi test suite şart), (ii) **esvhd/pypbo** (CSCV + MinBTL + DSR), (iii) **quantstats 0.0.81 Apache 2.0 + empyrical-reloaded** (metric library + HTML tear sheet), (iv) **vectorbt 1.0.0 Apache 2.0 + Commons Clause** (Faz 3 parameter sweep — "may not sell products or services that are primarily this software"), (v) **mlfinpy** (mlfinlab'ın açık kaynak rewrite alternatifi) kombinasyonu, paid mlfinlab'ın işlevselliğinin %90'ından fazlasını ücretsiz karşılar. **5 fazlı implementation roadmap toplam ~10-11 hafta** (paralel ile 8-9 hafta): (1) production sync C-1 closure — 1-2 hafta; (2) Purged K-Fold + DSR — 2 hafta; (3) CPCV + PBO — 1 ay; (4) 7 kriz stres testi — 2 hafta; (5) HTML/PDF/JSON raporlama — 1 hafta.

---

## 2. Akademik Temel

### 2.1 López de Prado Metodolojisi

López de Prado'nun *Advances in Financial Machine Learning* (Wiley 2018, ISBN 978-1119482086) finansal makine öğrenmesi ve backtesting'in de facto standardını belirler. RR-018 için kritik bölümler:

- **Bölüm 7 — "Cross-Validation in Finance"** (ETHZ ToC s.103-111): 7.3 "Why K-Fold CV Fails in Finance" (s.104), 7.4 "A Solution: Purged K-Fold CV" (s.105), 7.4.1 "Purging the Training Set" (s.105), 7.4.2 "Embargo" (s.107), 7.4.3 "The Purged K-Fold Class" (s.108), 7.5 "Bugs in Sklearn's Cross-Validation" (s.109).
- **Bölüm 12 — "Backtesting through Cross-Validation"**: CPCV tanımı. mlfinlab dokümantasyonu verbatim: *"Given a number φ of backtest paths targeted by the researcher, CPCV generates the precise number of combinations of training/testing sets needed to generate those paths, while purging training observations that contain leaked information."*
- **Bölüm 14 — "Backtest Statistics"**: 14.1 Motivation, 14.2 Types of Backtest Statistics, 14.3 General Characteristics, 14.4 Performance, 14.5 Runs, 14.6 Implementation Shortfall, 14.7 Efficiency (PSR/DSR), 14.8 Classification Scores, 14.9 Attribution. mlfinlab implementasyon listesi verbatim: `['HHI_pos', 'HHI_neg', 'HHI_time', 'DD_95th', 'TuW_95th', 'Annualized_Avg_Return', 'Avg_Hit_Return', 'Avg_Miss_Return', 'Ann_SR', 'PSR', 'DSR']`.
- **Bölüm 15 — "Understanding Strategy Risk"**: 15.2 Symmetric Payouts (s.211) — stratejinin ±π bahisleri için SR formülü; payout π **iptal olur**, sadece (p precision, n frequency) belirler. 15.3 Asymmetric Payouts (s.213) — π+ profit target ve π− stop-loss farklı, payout artık iptal olmaz. 15.4 Probability of Strategy Failure (s.216).
- **Bölüm 16 — "Machine Learning Asset Allocation"**: Hierarchical Risk Parity (HRP) — Markowitz Lanetinin (yakın-tekil Σ'da konveks MV optimizasyonun istikrarsızlığı) çözümü.

López de Prado'nun **Birinci Yasası** (Bölüm 1'den): *"Backtesting is not a research tool. Feature importance is."* BIST OS'un mevcut backtest-merkezli mimarisi bu yasaya aykırı; özellik önem analizi (RR-010 IC framework) merkeze çekilmelidir.

### 2.2 Multiple Testing Problem (Harvey-Liu-Zhu 2016)

**Harvey, C.R., Liu, Y. & Zhu, H. (2016)** "...and the Cross-Section of Expected Returns", *Review of Financial Studies* 29(1):5-68, DOI 10.1093/rfs/hhv059 (NBER WP 20592):

> *"Hundreds of papers and hundreds of factors attempt to explain the cross-section of expected returns. Given this extensive data mining, it does not make any economic or statistical sense to use the usual significance criteria for a newly discovered factor, e.g., a t-ratio greater than 2.0… The estimation of our model suggests that a newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0. Echoing a recent disturbing conclusion in the medical literature, we argue that most claimed research findings in financial economics are likely false."*

BIST OS implikasyonu: L1–L6 toplam **m=12 indicator değişkeni** denenmektedir (RR-010 ile tutarlı). Standart t-stat > 2 eşiği overfitting riski taşır; **Benjamini-Hochberg FDR α=0.10 m=12** doğru kalibrasyondur.

### 2.3 IID Violation (LdP Bölüm 7.3)

> *"Because observations cannot be expected to be drawn via an IID process, k-fold CV fails in finance. Another cause for CV's failure is that the testing set is employed several times during the development of a model, resulting in multiple testing and selection bias."* (Reasonable Deviations notları, LdP 2018 Ch.7'den)

BIST 5-günlük forward return etiketleri (RR-010) doğası gereği örtüşür: bugün başlayan etiket t+5'e kadar uzanır; t+1, t+2... etiketler de bu pencereyle çakışır. Standart sklearn `KFold(shuffle=True)` bu örtüşmeyi tamamen ihmal eder → **train/test arasında label leakage kaçınılmazdır**.

### 2.4 Deflated Sharpe + PBO

**Bailey, D.H. & López de Prado, M. (2014)** "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *Journal of Portfolio Management* 40(5):94-107, SSRN 2460551:

> *"(1) Non-normal returns. Skew, fat tails, volatility clustering: all of these break the naive mapping from SR to the standard normal distribution. (2) Selection bias under multiple testing. When researchers try many variations and keep the best one, the maximum SR will be inflated even if all candidates are [random]."*

**Bailey, Borwein, López de Prado & Zhu (2014)** "Pseudo-Mathematics and Financial Charlatanism", *Notices of the AMS* 61(5):458-471 — **Minimum Backtest Length** Theorem 3.1:
$$\text{MinBTL} < \frac{2\ln N}{E[\max_N]^2} \quad \text{(yıl)}$$

**Bailey, Borwein, López de Prado & Zhu (2017)** "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4):39-69, DOI 10.21314/JCF.2016.322 — Combinatorially Symmetric Cross-Validation (CSCV) + PBO.

---

## 3. Klasik Backtest Sorunları

### 3.1 Standart K-Fold Neden Geçersiz

Sklearn `KFold(shuffle=True)` finansal verilerde üç kanaldan başarısız olur:

1. **Auto-correlation**: BIST log-return ρ(1) ≈ 0.05-0.10 (anlamlı 1. gecikme; RR-010 measurement framework). Train ve test'te komşu günler look-ahead bias yaratır.
2. **Label overlap**: 5-günlük forward return etiketleri 5-gün boyunca örtüşür.
3. **Vol clustering** (GARCH yığılma): IID varsayımını doğrudan ihlal eder.

**Caveat:** sklearn default'una bağlı bazı vectorbt/bt parametre tarama örnekleri **production-grade backtest değildir** — sadece prototip.

### 3.2 Walk-Forward Limitasyonları

LdP Bölüm 12 (GARP whitepaper'dan): *"Like WF, a single backtest path is simulated… CV has no clear historical interpretation. The output does not simulate how the strategy would have performed in the past, but how it may perform in the future under various stress scenarios."*

Yani walk-forward **tek bir tarihsel patika** üretir: 2019→2020→2021 sırası neyse o. Robust assessment için **patika dağılımı** gerekir — bu CPCV'nin temel katkısıdır.

### 3.3 Survivorship Bias (BIST Spesifik)

BIST 2010-2026 döneminde delisted/işlemden men edilmiş şirketler: ASYAB (Asya Katılım Bankası, 2016 KHK ile el konuldu), DGZTE, ULUUN, TAT konserve geçmişi gibi vakalar; yıllık ortalama 10-15 delisting/iptal kaydı vardır (KAP duyuruları — RR-006 bulgusu). yfinance bu şirketleri döküm tarihinden sonra erişilemez kılar; tarihsel universe yeniden inşası için **KAP delisted listesi paralel veri kaynağı olarak tutulmalı**.

Pratik öneri: Backtest her ay başında o gün BIST 100'de yer alan ticker listesini (point-in-time) referans almalı; mevcut üyelik listesinden geriye projeksiyon yapmamalı.

### 3.4 Look-Ahead Bias Kaynakları

- **Earnings revision bias**: Bugün bilinen 2023 Q1 düzeltilmiş finansal — backtest tarihinde henüz yayımlanmamıştı. KAP açıklama zaman damgası şart.
- **Stop-loss hindsight**: %15 hard exit kuralı (RR-016) sonradan optimize edildiyse dolaylı look-ahead taşır.
- **Index reconstitution**: BIST 100 üyelikleri yarıyılda bir değişir.

---

## 4. Purged K-Fold CV Tasarımı

### 4.1 Metodoloji (LdP 2018 Bölüm 7.4)

Purging (Wikipedia "Purged cross-validation"): *"involves removing from the training set any observation whose label overlaps in time with the labels in the testing set."*
Embargo: *"addresses a more subtle form of leakage: even if an observation does not directly overlap the test set, it may still be affected by test events due to market reaction lag. To guard against this, a percentage-based embargo is imposed after each test fold. For example, with a 5% embargo and 1000 observations, the 50 observations following each test fold are excluded from training."*

Formal:
```
test_set = fold_indices
train_set = all_indices 
            \ test_set
            \ {i : label_i overlaps any label in test_set}    # purge
            \ {i : i ∈ (end(test_set), end(test_set) + embargo]}  # embargo
```

### 4.2 BIST OS Parametreleri (RR-010 ile Tutarlı)

| Parametre | Değer | Gerekçe |
|---|---|---|
| k (fold) | 5 | Standart, RR-010 IC framework |
| Label window | 5 gün | RR-010 5-day forward return |
| Auto-corr lag | 10 gün | Konservatif BIST ACF gözlemi |
| **Purge** | **10 gün** | max(label_window, autocorr_lag) |
| **Embargo** | **5 gün** | RR-010 ile aynı |

### 4.3 Kavramsal Python İskeleti (production-ready DEĞİL)

```python
class BISTPurgedKFold:
    """LdP (2018) Bölüm 7.4. Sklearn-uyumlu generator.
    Production-ready DEĞİL — Builder implement edecek."""
    def __init__(self, n_splits=5, purge_days=10, embargo_days=5):
        self.n_splits = n_splits
        self.purge_days = purge_days
        self.embargo_days = embargo_days

    def split(self, X: pd.DataFrame, pred_times: pd.Series, 
              eval_times: pd.Series):
        n = len(X)
        fold_bounds = np.linspace(0, n, self.n_splits + 1, dtype=int)
        for k in range(self.n_splits):
            test_start, test_end = fold_bounds[k], fold_bounds[k+1]
            test_idx = np.arange(test_start, test_end)
            # Purge: train'de label_end > test_start_time olan örnekleri çıkar
            test_t_start = pred_times.iloc[test_start]
            test_t_end = eval_times.iloc[test_end - 1]
            mask_purge = ~((eval_times >= test_t_start) & 
                          (pred_times <= test_t_end))
            # Embargo: test'in sağında embargo_days
            embargo_end = min(test_end + self._days_to_idx(
                test_t_end, self.embargo_days, pred_times), n)
            mask_embargo = ~np.isin(np.arange(n), 
                                    np.arange(test_end, embargo_end))
            train_idx = np.where(mask_purge & mask_embargo)[0]
            train_idx = train_idx[~np.isin(train_idx, test_idx)]
            yield train_idx, test_idx
```

### 4.4 Sanity Test Senaryoları

1. **Embargo testi**: Test sağındaki `embargo_days` train'de olmamalı.
2. **Purge testi**: Test'ten 4 gün önce başlayan 5-gün etiketli observation train'de olmamalı.
3. **Idempotent split**: Aynı veri ile iki çağrı aynı bölünmeyi vermeli.

### 4.5 Ücretsiz Implementation Seçenekleri

- **sam31415/timeseriescv 0.2 (MIT)**: `PurgedWalkForwardCV`, `CombPurgedKFoldCV`. setup.py verbatim: `version='0.2'`, `license='MIT'`, `author='Samuel Monnier'`. **Bilinmesi gereken**: Issue #6'da unit test'ler "all your tests at … test_cross_validation.py are failing" raporlandı; çekirdek sınıflar kullanılabilir fakat **kendi test suite zorunlu**.
- **hudson-and-thames/mlfinlab fork (jmrichardson, snapshot pre-paywall)**: PurgedKFold + CombinatorialPurgedKFold içerir. Ancak Issue #295: *"PurgedKFold class creates folds such that events in the training set can overlap with events in the test set."* Upstream repo LICENSE dosyası yok → yeniden dağıtım hukuki gri alan.
- **Custom implementation** (önerilen): ~200 satır, 1-2 günde; the maintainer budget + audit isolation.

---

## 5. Combinatorial Purged CV (CPCV)

### 5.1 Tanım (LdP 2018 Bölüm 12, GARP Whitepaper)

> *"Consider T observations partitioned into N groups without shuffling, where groups n=1,…,N−1 are of size ⌊T/N⌋, the Nth group is of size T−⌊T/N⌋(N−1)… For a testing set of size k groups, the number of possible training/testing splits is C(N, N−k)=C(N,k). And since we have computed all possible combinations, these tested groups are uniformly… Exhibit 7 illustrates the composition of train/test splits for N=6 and k=2. There are 15 splits, indexed as S1,…,S15."*

CPCV'nin avantajı: **Patika çoğulluğu**. Walk-forward = 1 patika, K-fold = 5 patika (tek senaryo lineer dizilim), CPCV = C(N,k) patika. Robust istatistiksel çıkarım (Sharpe dağılımı, std, percentile) için çok-patika gerekli.

### 5.2 BIST için Kalibrasyon: N=6, k=2 → 15 Patika

| N | k | C(N,k) | Per-patika OOS |
|---|---|---|---|
| 5 | 2 | 10 | %40 |
| **6** | **2** | **15** | **%33** |
| 8 | 2 | 28 | %25 |
| 10 | 3 | 120 | %30 |

5 yıllık BIST backtest (~1,250 gün) için **N=6 (yıl-bazlı blok: 2019, 2020, 2021, 2022, 2023, 2024)**, **k=2 (her seferinde 2 yıl test)** → **15 farklı patika**, her patika ~835g train + ~415g test.

### 5.3 Computational Cost

- Per-path: 6 katman × 5,000 obs × 12 trial ≈ 360K signal evaluation; ~30s/patika.
- 15 patika single-thread ~7-8 dakika; 4-core multi-thread ~2 dakika. **Kabul edilebilir maliyet.**

### 5.4 Çıktı

Her 15 patika için OOS Sharpe → dağılım:
- **Median Sharpe** (robust point estimate)
- **Mean Sharpe**, **Std(Sharpe)**, **5%-95% interval**
- **% paths with Sharpe > 1.0** (stability metric)

Bu dağılım hem nihai backtest raporuna girer hem PBO hesabının girdisi olur.

---

## 6. Deflated Sharpe + PBO

### 6.1 DSR Formulasyonu (Bailey-LdP 2014)

Probabilistic Sharpe Ratio (ön-aşama):
$$\text{PSR}[\text{SR}^*] = \Phi\left[\frac{(\hat{\text{SR}} - \text{SR}^*)\sqrt{n-1}}{\sqrt{1 - \hat{\gamma}_3 \hat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4}\hat{\text{SR}}^2}}\right]$$

Deflated Sharpe (selection bias düzeltmesi eklenir):
$$\text{DSR} = \Phi\left[\frac{(\hat{\text{SR}} - \widehat{\text{SR}}_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \hat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4}\hat{\text{SR}}^2}}\right]$$

Deflated benchmark:
$$\widehat{\text{SR}}_0 = \sqrt{V[\{\widehat{\text{SR}}_n\}]} \cdot \left[(1-\gamma_E)\Phi^{-1}\!\left(1 - \tfrac{1}{N}\right) + \gamma_E \Phi^{-1}\!\left(1 - \tfrac{1}{Ne}\right)\right]$$

$\gamma_E \approx 0.5772156649$ (Euler-Mascheroni), $N$ bağımsız trial sayısı, $V[\{\hat{\text{SR}}_n\}]$ trial Sharpe varyansı.

### 6.2 BIST'e Uygulama (N=12, RR-010 ile tutarlı)

- **N = 12** (RR-010'da m=12 IC testi)
- **T**: 5 yıl × 252 = **1,260 günlük** return
- **γ̂₃ (BIST tipik)**: -0.3 ile -0.8 (sol-skew)
- **γ̂₄ (BIST tipik)**: 5-9 (fat-tail)
- **V[{SR̂ₙ}]**: 12 trial Sharpe varyansı (CPCV'den çıkarsanır)

**Eşik (RR-010 ile uyumlu): DSR > 0.95** → güçlü kanıt. DSR 0.50-0.95 marjinal; <0.50 yetersiz.

### 6.3 PBO via CSCV (Bailey-Borwein-LdP-Zhu 2017)

Algoritma (davidhbailey.com PDF Algorithm 2.3 verbatim):

1. T×N performans matrisi M (T zaman, N strateji denemesi).
2. M'i satır boyunca S adet (S=16 önerilen) eşit submatrise böl: M_s, s=1…S, her biri (T/S × N).
3. Tüm C(S, S/2) kombinasyonları kur (S=16 → **12,780 kombinasyon**).
4. Her kombinasyon c için:
   - Train set J = S/2 submatris birleşimi
   - Test set J̄ = M'in J'ye complementi
   - n* = J üzerinde en iyi performanslı strateji indeksi (IS best)
   - r̄_c,n* = OOS performansı; relative rank ω̄_c = r̄_c,n*/(N+1) ∈ (0,1)
   - **Logit: λ_c = ln[ω̄_c / (1 − ω̄_c)]**
5. **PBO = Prob[λ_c < 0] = ∫_{-∞}^{0} f(λ) dλ**

Verbatim (BLPZ 2017 Section 4): *"As a consequence, if ω_c are distributed close to uniformly (the case when the backtest appears to be informationless), the distribution of the logits will approximate the standard Normal."*

Verbatim (Section 3.1): *"For φ ≈ 0, a low proportion of the optimal IS strategy outperformed the median of trials in most of the testing sets indicating no significant overfitting. On the flip side, φ ≈ 1 indicates high likelihood of overfitting."*

**Eşikler:** PBO < 0.50 güvenilir; 0.50-0.70 şüpheli; **> 0.70 overfit, deploy etmeyin**.

### 6.4 MinBTL Hesabı

N=12 trial, hedef Sharpe 1.5:
$$\text{MinBTL} < \frac{2 \ln 12}{1.5^2} = \frac{2 \times 2.485}{2.25} \approx 2.21 \text{ yıl}$$

the maintainer'ın 6 aylık backtest'i ≈ 0.5 yıl << 2.21 yıl → **N=12 deneme için teorik minimum altında**. 5-yıl önerimiz (Bölüm 7) bu hesabı rahatlıkla karşılar.

### 6.5 Reporting

Her backtest raporu zorunlu olarak içermeli:
- Raw Sharpe (gross + net, RR-015)
- PSR
- **DSR** (N=12, V[SR_trials])
- **PBO** (S=16, CSCV)
- Median CPCV Sharpe + 5%-95% IQR
- MinBTL karşılaştırma (T ≥ MinBTL mi?)

---

## 7. Crisis Period Stres Testi

### 7.1 7 Kriz Dönemi (RR-016 ile Tam Tutarlı)

| # | Kriz | Tarih | BIST 100 Etkisi | Süre |
|---|---|---|---|---|
| 1 | TRY krizi | Ağustos 2018 | Lira Ağustos 2018'de USD karşısında **%33.7 değer kaybı** (ScienceDirect "Turkish currency crunch" 2023); BIST 100 Y/Y 2018'de **-%17.3** (PWC Aralık 2018 raporu) | 6 hafta akut |
| 2 | COVID | Mart 2020 | Küresel S&P 500 19 Şub-23 Mar **-%33.9** (Oxford RAPS 10(4):742); BIST-specific peak-to-trough doğrulanmadı (sample edilmedi) | ~4 hafta akut |
| 3 | Kahramanmaraş depremi | 6-15 Şubat 2023 | **-%16.2 toplam 2.5 günde**; 7 Şubat -%8.62 tek gün; 8 Şubat saat 11:00'de devre kesici → BIST **5 işlem günü kapalı (8-14 Şubat)**; 15 Şubat **+%9.74 açılış rally** (BES alımları) | 1 hafta akut + 5g kapalı |
| 4 | Cumhurbaşkanlığı 2. tur | 15 Mayıs 2023 | Açılışta **-%6.4**; bankacılık endeksi **-%9.5**; devre kesici 09:55; günü **-%6.14 kapanış**; 14-28 Mayıs aralığında **-%4.5 toplam** (Midas raporu) | 2 hafta |
| 5 | Şimşek-Erkan post-election rally | Haziran 2023 | 28 Mayıs-28 Haziran **+%25.7**; 28 Mayıs-28 Temmuz **+%54.3** (Midas raporu, getmidas.com — kaynak: para piyasası blog, peer-review değil) | 2 ay rally |
| 6 | Yerel seçim | 31 Mart 2024 | -%6 estimate (RR-016 referans; **doğrulanmadı** — The National 1 Nisan 2024'e göre seçim sonrası ilk Pazartesi +%0.17 kapanış) | 1 hafta |
| 7 | CHP "mutlak butlan" kararı | 21 Mayıs 2026 | **-%6.05 tek gün** (13.163,88 puanda kapanış); bankacılık endeksi **-%8.63**; 5 yıllık tahvil faizi +58bp → **%40.27**; CDS 361bp; ertesi gün açılış -%1.5 (Cumhuriyet, Odatv, BorsaGundem) | 2-3 gün akut |

**Opsiyonel (10-yıl backtest)**: 2008 küresel kriz (BIST yıllık ~-%60); Mart 2025 İmamoğlu gözaltı (Mayıs 2026 karşılaştırma referansı).

### 7.2 Stres Test Metodolojisi

1. **Historical replay (öncelikli)**: Her kriz penceresinde gerçek BIST verisi üzerinde sistemin verdiği kararları simüle et; PnL, MDD, recovery time hesapla.
2. **Synthetic stress**: Tarihsel volatilite × log-return shift edilmiş Monte Carlo bootstrap.
3. **Sensitivity analysis**: MASTER_WEIGHTS ±%20 perturbasyonu altında crisis MDD değişimi.
4. **Counterfactual v2 vs v3**: Vol-targeting v3 (RR-016) vs v2 (statik); vol_scalar ve DD scalar etkisini izole et.

### 7.3 Crisis-Specific Metrikler (per krize)

- **Crisis MDD** (peak-to-trough)
- **Recovery time** (gün cinsinden; eski peak'e dönüş)
- **Crisis-period Sharpe** (akut dönem annualized)
- **Post-crisis 90-day Sharpe**
- **vs BIST 100 outperformance** (%)
- **Crisis Ulcer Index**, **Crisis Calmar ratio**

### 7.4 Minimum Backtest Periyodu

| Süre | Crisis Coverage | Öneri |
|---|---|---|
| 6 ay | 0-1/7 (sadece 2026 May) | **Yetersiz** — Critic raporu haklı |
| 2 yıl | 1-2/7 | Sınırda |
| **5 yıl (2019-2024)** | **6/7** (2018 TRY hariç) | **ÖNERİLEN** |
| 7 yıl (2018-2024) | 7/7 | İdeal |
| 10 yıl (2014-2024) | 7/7 + 2008 | Reel return distorsiyonu sınırlı |

**Hiperenflasyon caveat (2022-2024)**: TÜFE yıllık **%72.31 (2022 World Bank verisi via Macrotrends)**, **%53.86 (2023)**, zirve **%85.5 Ekim 2022 (TurkStat)**. 2023 Nisan'a kadar %43.7'ye gerileyip 2024 ortasında ~%75 seviyesine yeniden yükseldi (TurkStat via Al Jazeera Haziran 2023). Nominal BIST getirileri reel anlamda yanıltıcı — **hem nominal hem CPI-deflated reel rapor zorunlu**. Risk-free rate: **%37 (TCMB Mayıs 2026 PPK)** — Press Release 2026-12 verbatim: *"The Monetary Policy Committee has decided to keep the policy rate (the one-week repo auction rate) at 37 percent. The Committee has also maintained the Central Bank overnight lending rate and the overnight borrowing rate at 40 percent and 35.5 percent, respectively."*

---

## 8. `backtest/engine.py` AUDIT C-1 — Solution Roadmap

### 8.1 Mevcut Divergence

- `backtest/engine.py` içinde sinyal puanlama formülü **hardcoded**.
- `src/signals/engine.py` (production) MASTER_WEIGHTS, layer aggregation, threshold mantığını **dinamik (config-driven)** okur.
- Faz 0'da yapılan weight değişikliği (L4 suspended, L6=0.03) production'a yansıdı ama **backtest hâlâ eski formülü kullanıyor**.
- Sonuç: Backtest "yeşil" rapor üretirken production farklı sinyal üretebilir — **false confidence riski**.

### 8.2 Üç Çözüm Seçeneği

**(a) Production engine'i backtest'te doğrudan kullan**
- Pros: Tek source of truth.
- Cons: Production sinyali günlük real-time için optimize; 1,250g × 50 ticker = 62K signal eval yavaş.
- **Önerilmez** — performans cezası ağır.

**(b) Shared abstraction (signal_calculator.py) — ÖNERİLEN**
- `src/signals/calculator.py` saf, side-effect'siz module.
- Hem `src/signals/engine.py` hem `backtest/engine.py` aynı `SignalCalculator`'ı import.
- Production → real-time data feed; backtest → historical data loop.
- Pros: DRY, single source, test edilebilir. Cons: Refactor ~3-4 gün.

**(c) Sync test script**
- CI/CD'de günlük backtest output == production output kontrolü.
- Pros: Mevcut kodu az değiştirir. Cons: Root-cause çözmez.

### 8.3 Önerilen Yol: (b) + (c) Hibrit

Faz 1'de **(b)** uygula; Faz 1.5'te **(c)** drift detection CI ekle.

### 8.4 Migration Roadmap (Builder-Implementable)

**Faz 1a — Sync Test (3 gün):**
```python
# tests/test_backtest_production_parity.py
def test_signal_parity_today():
    today = pd.Timestamp.now().normalize()
    universe = load_bist100_universe(today)
    prod_signals = production_engine.score(universe, today)
    bt_signals = backtest_engine.score(universe, today, mode='realtime_replay')
    assert_frame_equal(prod_signals, bt_signals, rtol=1e-4)
```
**DoD:** CI'de yeşil; failure → alarm.

**Faz 1b — Quantify Drift (1 gün):**
- Son 30 günün her günü için parity testi tarihsel olarak çalıştır.
- Drift gün sayısı, ticker, magnitude rapor et.
- **Eğer drift > 0 → mevcut backtest raporları RETRACT.**

**Faz 1c — SignalCalculator Refactor (4-5 gün):**
```python
# src/signals/calculator.py
class SignalCalculator:
    """Saf, stateless. Hem production hem backtest tarafından import."""
    def __init__(self, master_weights: Dict[str, float], 
                 layer_configs: Dict[str, 'LayerConfig']):
        self.master_weights = master_weights
        self.layer_configs = layer_configs
    
    def score(self, market_snapshot: 'MarketSnapshot', 
              as_of: pd.Timestamp) -> pd.DataFrame:
        l1 = self._compute_layer('L1', market_snapshot, as_of)
        l2 = self._compute_layer('L2', market_snapshot, as_of)
        l3 = self._compute_layer('L3', market_snapshot, as_of)
        # L4 suspended; placeholder döner
        l5 = self._compute_layer('L5', market_snapshot, as_of)
        l6 = self._compute_layer('L6', market_snapshot, as_of)
        return self._aggregate([l1, l2, l3, l5, l6])
```
`MarketSnapshot` interface hem real-time hem historical implementation kabul etsin.

**Faz 1d — Backtest Refactor (2 gün):** `backtest/engine.py` artık `SignalCalculator` import etsin; hardcoded formula sil; eski testleri yeni interface ile güncelle.

**Faz 1e — CI Architecture Test (1 gün):** Pre-commit hook AST-level check; `backtest/engine.py` içinde manuel weight veya formula varsa fail.

**Toplam C-1 closure: ~10-12 iş günü.** Bu sprintin tek odak noktası.

---

## 9. Library Karşılaştırma — the maintainer $0 Budget Analizi

### 9.1 mlfinlab (Hudson & Thames) — Paid Status 2024-2025

- **Fiyat**: **£100 + KDV / ay / kullanıcı**, sadece **QuantConnect Cloud** üzerinden erişim (QuantConnect docs verbatim).
- **"Unlocking the Commons" sponsorluk modeli** Aralık 2020 aylık $4,000 hedefini tutturamadı (jmrichardson fork README'sinde verbatim korunuyor) → 2021'den itibaren **closed-source ticari lisans**.
- **Eski PyPI mlfinlab 0.4.1 (4 Eylül 2019, BSD-3-Clause)** hâlâ `pip install mlfinlab` ile yüklenebilir; ancak Snyk advisor "discontinued" işaretlemekte; 2021 Ağustos'tan beri sürüm yayımlanmadı. PurgedKFold içerir ama **Issue #295 bug fix'lenmemiş**: *"PurgedKFold class creates folds such that events in the training set can overlap with events in the test set."*
- **GitHub upstream (hudson-and-thames/mlfinlab)**: **LICENSE dosyası yok** → yeniden dağıtım hukuki gri alan.
- **Community forks (jmrichardson, nasgoncalves/mlfinlab-updated, Roh-codeur/mlfinlab-1)**: Pre-paywall snapshot, sıfır maintenance.
- **QC forum thread** (discussion 16833): *"The licensing system H&T used was broken, and the fix for the issue was not available in the near term, so we removed it from the foundational"* — erişim intermittent.

**the maintainer $0 hedefi için sonuç: Hudson & Thames mlfinlab kullanılmaz.**

### 9.2 Ücretsiz Alternatifler Matrisi

| Modül | Paid (mlfinlab) | Ücretsiz Alternatif | Lisans | Olgunluk |
|---|---|---|---|---|
| Purged K-Fold | `mlfinlab.cross_validation.PurgedKFold` | `timeseriescv.PurgedWalkForwardCV` (sam31415) | MIT | Alpha (test fail Issue #6) |
| CombPurgedKFold | `mlfinlab.cross_validation.CombinatorialPurgedKFold` | `timeseriescv.CombPurgedKFoldCV` | MIT | Alpha |
| Deflated Sharpe | `mlfinlab.backtest_statistics.deflated_sharpe_ratio` | `pypbo` (esvhd) + custom ~50 satır | Open source | Functional |
| PBO (CSCV) | `mlfinlab.backtest_statistics.probability_of_backtest_overfitting` | `esvhd/pypbo` | Open | Functional |
| MinBTL | `mlfinlab.backtest_statistics.min_backtest_length` | Custom 5-satır formula | — | Trivial |
| Triple-Barrier | `mlfinlab.labeling.triple_barrier` | `mlfinpy` (open-source rewrite) | Open | Beta |
| Fractional Diff | `mlfinlab.features.fracdiff` | `mlfinpy` / `fracdiff` (kondoyu) | Open | Stable |
| Backtest stats (PSR, HHI, runs) | `mlfinlab.backtest_statistics` | `empyrical` + custom HHI ~10 satır | Apache 2.0 | Stable |

### 9.3 Diğer Backtest Library'leri

- **bt (pmorissette)**: BSD, basit; LdP metodolojisi yok; rapid prototyping uygun, production değil.
- **vectorbt 1.0.0 (polakowo)**: **Apache 2.0 + Commons Clause** (verbatim: *"The source code is publicly available, and everyone (individuals and organizations) may use it for free. However, you may not sell products or services that are primarily this software."*). Numba JIT — saniyede binlerce parametre kombinasyonu. LdP metodolojisi yok ama Faz 3 parameter sweep için ideal. **vectorbt PRO** ayrı, davet bazlı, ücretli — kullanılmayacak.
- **backtrader**: Event-driven; LdP yok; yavaş; topluluk maintenance düşük; **önerilmez**.
- **pyfolio (Quantopian)**: Archived; **pyfolio-reloaded (stefan-jansen fork)** aktif. **quantstats 0.0.81 (ranaroussi, Apache 2.0)**: HTML tear sheet, Sharpe/Sortino/Calmar/MaxDD/Win Rate. **empyrical-reloaded**: metric library, quantstats bağımlılığı.

### 9.4 BIST OS Önerilen Stack ($0 Budget)

```
Core: Custom (src/signals/calculator.py + backtest/runner.py)
CV: timeseriescv 0.2 forklamak + Issue #6 test fix VEYA custom 200-satır
Metrik: quantstats 0.0.81 + empyrical-reloaded
PBO/DSR: esvhd/pypbo + custom DSR (Bailey-LdP 2014)
Parameter Sweep: vectorbt (sadece Faz 3 trial generation)
Reporting: quantstats HTML + custom JSON schema
```

**Toplam maliyet: $0**. Custom implementation effort: **~5-10 gün** (Faz 2-3 içinde).

---

## 10. Metrikler Framework

### 10.1 Mevcut (Korunacak)
Total return, annualized return, Sharpe (gross), Max drawdown, Win rate.

### 10.2 Eklenecek (Zorunlu)

| Metrik | Formül | Kaynak | RR Bağlantısı |
|---|---|---|---|
| **Deflated Sharpe** | Bailey-LdP 2014 | JPM 40(5):94-107 SSRN 2460551 | §6.1 |
| **PBO** | CSCV logit | JCF 20(4):39-69 DOI 10.21314/JCF.2016.322 | §6.3 |
| **MinBTL** | 2ln(N)/E[max]² | BLPZ 2014 Notices AMS 61(5) Thm 3.1 | §6.4 |
| **Calmar Ratio** | annual return / |MaxDD| | Young (1991) Futures | RR-016 |
| **Sortino Ratio** | excess return / downside dev | Sortino & Price (1994) JoI 3(3) | RR-016 |
| **Ulcer Index** | √(Σ DD_i² / n) | Martin & McCann (1989) | RR-016 |
| **Martin Ratio (UPI)** | excess return / Ulcer | Martin & McCann (1989) | RR-016 |
| **IC** (Spearman) | ρ_S(score, fwd_return) | RR-010 | RR-010 |
| **ICIR** | mean(IC)/std(IC)·√N | Standard alpha research | RR-010 |
| **HHI of returns** | Σ(r_i/Σr)² | LdP Bölüm 14 s.200 | — |
| **Turnover** | Σ\|Δw_i\| / 2 | Standart | RR-015 |
| **PSR** | Bailey-LdP 2012 | — | DSR ön-koşulu |

### 10.3 Crisis-Specific Metrikler (per krize, Bölüm 7)
Crisis MDD, recovery time, crisis Sharpe, post-crisis 90d Sharpe, vs BIST 100 outperformance, crisis Ulcer.

### 10.4 Cost-Aware (RR-015 Entegrasyon)
- **Gross vs Net Sharpe**: $(E[r_p] - r_f - c_{yıllık}) / \sigma(r_p)$, $c_{yıllık} = N_{trade} \times \text{RT cost}$
- **Net Calmar**, **Net Sortino**
- **Tradeable Alpha indicator**: Gross Sharpe ≥ 1.5 hurdle (RR-015 BUY-STRONG)
- **BUY tier ayrı**: BUY-STRONG (≥0.68), BUY-MEDIUM (0.55-0.67), BUY-WEAK (<0.55)
- **Per-broker**: Tier A (İş %0.2) / B (Garanti %0.195) / C (Midas %0) ayrı

---

## 11. Backtest Output Standardizasyonu

### 11.1 JSON Schema

```json
{
  "strategy_name": "BIST_OS_v3",
  "version": "RR-018.1.0",
  "backtest_period": {"start": "2019-01-01", "end": "2024-12-31"},
  "data_source": "yfinance + KAP + EVDS",
  "broker_tier_assumed": "B",
  "cv_method": "CPCV",
  "cv_params": {"N": 6, "k": 2, "n_paths": 15, 
                "purge_days": 10, "embargo_days": 5},
  "metrics": {
    "gross": {
      "annualized_return_pct": 18.5,
      "annualized_volatility_pct": 22.3,
      "sharpe_ratio": 0.83,
      "sortino_ratio": 1.21,
      "calmar_ratio": 1.02,
      "max_drawdown_pct": 18.2,
      "ulcer_index": 8.5,
      "martin_ratio": 1.45
    },
    "net": {
      "annualized_return_pct": 13.7,
      "sharpe_ratio": 0.55,
      "calmar_ratio": 0.75
    },
    "statistical_inference": {
      "psr": 0.92,
      "deflated_sharpe": 0.45,
      "pbo": 0.32,
      "min_btl_years_required": 2.21,
      "min_btl_satisfied": true,
      "n_trials": 12,
      "trial_sharpe_variance": 0.41
    },
    "cpcv_distribution": {
      "n_paths": 15,
      "sharpe_median": 0.81,
      "sharpe_mean": 0.79,
      "sharpe_std": 0.18,
      "sharpe_p05": 0.42,
      "sharpe_p95": 1.08,
      "pct_paths_sharpe_above_1": 0.27
    },
    "turnover_annual": 24,
    "ic_metrics": {
      "ic_mean": 0.034, "ic_ir": 1.12,
      "ic_t_stat": 2.85, "bh_fdr_pass": true
    }
  },
  "crisis_periods": [
    {"name": "2018_TRY_aug", "drawdown_pct": 28.1, "recovery_days": 145},
    {"name": "2020_COVID_mar", "drawdown_pct": 22.1, "recovery_days": 95},
    {"name": "2023_feb_quake", "drawdown_pct": 16.2, "recovery_days": 38,
     "exchange_closed_days": 5},
    {"name": "2023_may_election", "drawdown_pct": 6.14, "recovery_days": 14},
    {"name": "2023_jun_simsek_rally", "drawdown_pct": 0.0, "rally_pct": 54.3},
    {"name": "2024_mar_local", "drawdown_pct": 6.0, "recovery_days": 22},
    {"name": "2026_may_butlan", "drawdown_pct": 6.05, "recovery_days": null,
     "banking_index_drop_pct": 8.63, "cds_change_bp": 19}
  ],
  "buy_tier_separated": {
    "BUY_STRONG": {"sharpe_net": 0.82, "n_trades": 142},
    "BUY_MEDIUM": {"sharpe_net": 0.31, "n_trades": 218},
    "BUY_WEAK": {"sharpe_net": -0.12, "n_trades": 96}
  },
  "regime_segmented": {"hmm_enabled": false, "static_weights_used": true},
  "audit_compliance": {
    "C1_production_sync": "PASS",
    "C1_drift_quantified": "0 days drift in last 30d",
    "shared_calculator_module": "src/signals/calculator.py v1.0"
  }
}
```

### 11.2 Reporting Formats
- **JSON**: machine-readable, CI/CD entegrasyonu, otomatik regresyon.
- **HTML (quantstats tear sheet + custom CPCV plots)**: interaktif, recruiter-friendly.
- **PDF (matplotlib + reportlab)**: publication-ready, public release.
- **Markdown summary**: README + LinkedIn paylaşımı.

### 11.3 Comparison Tables
İki nüsha: **v2_static** ve **v3_vol_aware** (RR-016 aktif). Yan yana hücreler — Sharpe, MDD, Calmar, Ulcer, Net Sharpe, crisis MDD; Δ kolonu.

---

## 12. Position Sizer + Backtest Entegrasyonu (RR-014/015/016/017)

### 12.1 Vol-Targeting Backtest (RR-016)

```
realized_vol_20d = std(log_returns[-20:]) * sqrt(252)
vol_scalar = clip(0.15 / realized_vol_20d, 0.20, 1.50)
```

DD soft gate:
```
if dd < 0.05:  dd_scalar = 1.00
elif dd < 0.10: dd_scalar = 0.50
elif dd < 0.15: dd_scalar = 0.25
else:           dd_scalar = 0.00  # hard exit
```

**CB-002 × vol_scaler × dd_scalar → min() kuralı** ("the most binding constraint wins"). Kelly (Thorp quarter-Kelly) ek. **Counterfactual: v2 vs v3 yan yana zorunlu**.

### 12.2 Cost-Aware (RR-015)

$$\text{RT cost} = 2 \times \text{komisyon} \times 1.05 + \text{spread} + 2 \times \text{slippage}$$

- Tier A (İş Yatırım): %0.2 + BSMV
- Tier B (Garanti): %0.195 sabit / hacme bağlı 1.99→0.90
- Tier C (Midas): %0

MIN_NET_EXPECTED_VALUE_PCT=0.5 her trade. Üç tier sonuç ayrı + BUY-STRONG/MEDIUM/WEAK ayrı.

### 12.3 Slippage (RR-014)
- **Tier 1 ADV**: trade_size > %10 ADV → BLOCK; > %5 → WARN.
- **Tier 2 sqrt-impact**: $\sigma_{impact} = \eta_{BIST} \cdot \sigma \cdot \sqrt{\text{size}/\text{ADV}}$, $\eta_{BIST}=0.40$.
- **Tier 3 Almgren-Chriss** (ileri faz, retail için aşırı).

### 12.4 HMM Regime (RR-017)
ENABLE_HMM_WEIGHTS=True: 3-state Gaussian HMM (Bull/Neutral/Bear). Features: [BIST log-return, 20g vol, USDTRY log-return, 5Y CDS change]. State-conditional MASTER_WEIGHTS. Bull/Neutral/Bear ayrı segment performans. CB-002 × HMM min() entegrasyon. **Aktivasyon kararı: AG-001 sonrası 90+ gün OOS + Sharpe iyileşme ≥ +0.15.**

### 12.5 Entegrasyon Şeması

```
backtest/runner.py
├── for t in date_range:
│   ├── snap = data_loader.snapshot(t)
│   ├── raw_signals = SignalCalculator.score(snap, t)        # SHARED w/ prod
│   ├── regime = HMMDetector.predict(snap, t)                # RR-017
│   ├── weights = MasterWeights.get(regime if hmm else 'static')
│   ├── target_pos = PortfolioConstructor.build(raw_signals, weights)
│   ├── vol_s = VolTargeter.compute(t)                       # RR-016
│   ├── dd_s = DrawdownGate.compute(equity_curve)
│   ├── kelly_s = KellyCriterion.compute()
│   ├── scaler = min(vol_s, dd_s, kelly_s)                   # min() kuralı
│   ├── for trade in proposed_trades:
│   │   ├── if SlippageModel.adv_check(trade) == BLOCK: skip # RR-014 T1
│   │   ├── slip = SlippageModel.sqrt_impact(trade)          # RR-014 T2
│   │   ├── cost = CostModel.round_trip(trade, broker_tier)  # RR-015
│   │   ├── if net_ev < 0.5%: skip                           # RR-015 EV gate
│   │   └── exec_price = px + slip
│   └── update equity_curve, position log
└── compute_metrics() + crisis_analysis() + dsr() + pbo()
```

---

## 13. Python Implementation Hintleri

### 13.1 Framework Class (kavramsal, production-ready DEĞİL)

```python
class BISTBacktestFramework:
    """López de Prado-style backtest framework.
    - PurgedKFold / CPCV cross-validation
    - DSR (Bailey-LdP 2014) + PBO (BLPZ 2017)
    - 7 kriz dönemi stress testing
    - Production engine sync (Audit C-1 closure)
    - RR-014/015/016/017 entegrasyon
    Production-ready DEĞİL — Builder implement edecek.
    """
    def __init__(self, strategy_engine: 'SignalCalculator',
                 start_date: str, end_date: str,
                 cv_method: str = 'cpcv',
                 cpcv_N: int = 6, cpcv_k: int = 2,
                 purge_days: int = 10, embargo_days: int = 5,
                 broker_tier: str = 'B',
                 vol_targeting: bool = True,
                 hmm_enabled: bool = False,
                 n_trials_for_dsr: int = 12):
        self.engine = strategy_engine  # SHARED dependency (C-1 closure)
        # ...

    def run_backtest(self) -> dict: ...
    def run_cpcv(self) -> pd.DataFrame: ...
    def stress_test(self, crisis_periods: List['CrisisPeriod']) -> dict: ...
    
    def compute_deflated_sharpe(self, returns: pd.Series, 
                                 n_trials: int,
                                 trial_sr_variance: float) -> float:
        """Bailey & López de Prado (2014) JPM 40(5):94-107."""
        from scipy.stats import norm, skew, kurtosis
        EULER = 0.5772156649015329
        T = len(returns)
        sr_hat = (returns.mean() / returns.std()) * np.sqrt(252)
        g3 = skew(returns)
        g4 = kurtosis(returns, fisher=False)
        sr0 = np.sqrt(trial_sr_variance) * (
            (1 - EULER) * norm.ppf(1 - 1/n_trials) +
            EULER * norm.ppf(1 - 1/(n_trials * np.e))
        )
        denom = np.sqrt(1 - g3 * sr_hat + ((g4 - 1) / 4) * sr_hat**2)
        return norm.cdf((sr_hat - sr0) * np.sqrt(T - 1) / denom)

    def compute_pbo(self, trial_pnl_matrix: np.ndarray, S: int = 16) -> float:
        """CSCV via logit (BLPZ 2017 JCF 20(4):39-69).
        T×N matrix → S row-blocks → C(S, S/2) combinations.
        Per combo: rank IS-best in OOS → λ_c = ln[ω/(1−ω)].
        Return P[λ < 0]."""
        from itertools import combinations
        T, N = trial_pnl_matrix.shape
        block_size = T // S
        blocks = [trial_pnl_matrix[i*block_size:(i+1)*block_size] 
                  for i in range(S)]
        logits = []
        for combo in combinations(range(S), S // 2):
            train_idx = list(combo)
            test_idx = [i for i in range(S) if i not in train_idx]
            train = np.vstack([blocks[i] for i in train_idx])
            test = np.vstack([blocks[i] for i in test_idx])
            # SR per strategy IS and OOS
            sr_is = train.mean(axis=0) / train.std(axis=0)
            sr_oos = test.mean(axis=0) / test.std(axis=0)
            n_star = np.argmax(sr_is)
            rank = (sr_oos.argsort().argsort()[n_star] + 1)
            omega = rank / (N + 1)
            omega = np.clip(omega, 1e-6, 1 - 1e-6)
            logits.append(np.log(omega / (1 - omega)))
        logits = np.array(logits)
        return (logits < 0).mean()  # PBO

    def compute_min_btl(self, n_trials: int, 
                        expected_max_sharpe: float) -> float:
        """BLPZ 2014 Notices of AMS 61(5) Thm 3.1."""
        return 2 * np.log(n_trials) / expected_max_sharpe**2
```

### 13.2 Ücretsiz Library Integration

```python
from timeseriescv.cross_validation import CombPurgedKFoldCV
from pypbo.pbo import pbo, dsr  # esvhd/pypbo
import quantstats as qs
import empyrical as ep
import vectorbt as vbt  # sadece Faz 3 trial generation

def ulcer_index(returns: pd.Series) -> float:
    """Martin & McCann (1989). UI = sqrt(mean(D_i^2)) where D_i = 
    drawdown since previous peak."""
    cum = (1 + returns).cumprod()
    drawdown = (cum / cum.cummax() - 1) * 100
    return np.sqrt((drawdown ** 2).mean())

def calmar_ratio(returns: pd.Series, periods_per_year=252) -> float:
    """Young (1991) Futures Magazine."""
    ann_return = returns.mean() * periods_per_year
    cum = (1 + returns).cumprod()
    max_dd = abs((cum / cum.cummax() - 1).min())
    return ann_return / max_dd if max_dd > 0 else np.nan

def hhi_returns(returns: pd.Series) -> float:
    """López de Prado (2018) Bölüm 14 s.200."""
    pos = returns[returns > 0]
    return (pos / pos.sum()).pow(2).sum()
```

---

## 14. BIST 2024-2026 Sektör Pratiği

### 14.1 Türk Pratisyenler Backtest Disiplini

- LinkedIn quant pozisyon ilanlarında "backtest framework" sıklığı düşük; "Python, pandas, ML" daha sık. **Spesifik "mlfinlab" veya "Purged K-Fold" ilan terimi BULUNAMADI.**
- Broker araştırma birimleri (İş Yatırım Quant, Ünlü & Co, Garanti BBVA Yatırım) çoğunlukla teknik analiz + fundamental kombinasyonu raporluyor; akademik backtest disiplini görünür değil.
- Foreks Pro, Matriks IQ retail backtest araçları Pine Script benzeri; walk-forward seçeneği var ama purged K-Fold yok.
- Türk fintwit topluluğu TradingView dominant; "in-sample optimize ettim, çalışıyor" yaygın söylem. **Twitter/X login-wall nedeniyle sistematik sample edilmedi.**

### 14.2 Akademik Pratisyen Boşluğu

DergiPark araması 2022-2024: López de Prado metodolojisi (purged CV, deflated Sharpe) Türk finansal akademisinde yeni tanınmakta. Mevcut yayınlar (örn. Ege Academic Review 2023 ML for financial distress) backtest disiplini periferik kalıyor.

### 14.3 Quant Community Türkiye

- LinkedIn quant analyst pozisyonları sayısı 2024'te artış (Akbank, İş Yatırım, Garanti BBVA, Anadolu Sigorta).
- Boğaziçi, ODTÜ Endüstri Mühendisliği, Sabancı MS in Financial Engineering programlarında "ML in Finance" dersleri mevcut; López de Prado metodolojisinin müfredata sistematik girdiği **doğrulanamadı**.

### 14.4 Ordinal Skala (RR-011/017 yama formatıyla)

| Pratik | Yaygınlık |
|---|---|
| HMM/Markov regime detection kurumsal BIST | **BULUNAMADI** |
| Purged K-Fold + DSR broker quant | **Düşük** |
| CPCV + PBO Türkiye'de | **BULUNAMADI** |
| Walk-forward backtest retail | **Orta** (TradingView dominant) |
| In-sample only ("ben yaptım çalıştı") | **Yüksek** (forum söylem) |
| Crisis period stress test | **Düşük** (BDDK kurumsal pozisyon limit testlerinde) |
| QuantStats/empyrical Türk quants kullanımı | **Belirsiz** (sample edilmedi) |

**Not:** Twitter/X login-wall, fintwit forum gözlemi yapılamadı.

---

## 15. Implementation Roadmap (5 Faz)

### Faz 1 — Production Sync (1-2 hafta) — C-1 closure
- 1a Parity test (3g), 1b Quantify drift (1g), 1c SignalCalculator refactor (4-5g), 1d Backtest refactor (2g), 1e CI architecture test (1g).
- **Val Checklist**: ☐ Shared module mevcut ☐ Hardcoded silindi ☐ CI parity yeşil ☐ Drift=0 ☐ Eski raporlar RETRACT işaretli.

### Faz 2 — Purged K-Fold + DSR (2 hafta)
- 2a PurgedKFold custom (3g), 2b Unit tests purge/embargo (2g), 2c DSR impl (2g), 2d MinBTL helper (0.5g), 2e Integration runner (2g), 2f Backward-compat report (1g).
- **Val Checklist**: ☐ k=5/purge=10/embargo=5 default ☐ DSR>0.95 threshold konfigure ☐ MinBTL kontrol JSON'da ☐ Coverage >%90.

### Faz 3 — CPCV + PBO (1 ay)
- 3a CPCV custom impl (5g), 3b Multi-thread runner (3g), 3c PBO CSCV impl (5g), 3d Trial matrix generator (4g, vectorbt sweep), 3e Sharpe dağılım plots (2g), 3f PBO threshold gates (1g), 3g Integration test (3g).
- **Val Checklist**: ☐ 15 patika dağılımı oluşuyor ☐ PBO JSON'a giriyor ☐ PBO>0.7 deploy bloke ☐ CPCV run ≤ 5 dakika.

### Faz 4 — Crisis Stress Test (2 hafta)
- 4a Crisis window catalog (2g), 4b Replay engine (3g), 4c Crisis metrics impl (3g), 4d Counterfactual v2 vs v3 (2g), 4e Sensitivity ±%20 (2g), 4f Monte Carlo 1000 senaryo (2g).
- **Val Checklist**: ☐ 7 kriz dönemi otomatik replay ☐ Crisis MDD ≤ %25 (göstergesel) ☐ v3 vol-aware her krizde v2 ≥ MDD ☐ MC %95 CI Sharpe pozitif.

### Faz 5 — Reporting (1 hafta)
- 5a JSON schema (1g), 5b HTML quantstats (2g), 5c PDF matplotlib (2g), 5d Markdown summary (1g), 5e CI/CD pipeline (1g).
- **Val Checklist**: ☐ `bist_bt report --all` tek komut ☐ Recruiter testi README'de yanıt ☐ Otomatik PR'larda rapor üretim.

### Toplam
| Faz | Süre |
|---|---|
| 1 | 1-2 hafta |
| 2 | 2 hafta |
| 3 | 4 hafta |
| 4 | 2 hafta |
| 5 | 1 hafta |
| **Toplam** | **10-11 hafta** (~2.5 ay) |

Paralel çalışma (1 dev tam zaman) ile **8-9 haftaya** inebilir.

---

## 16. the maintainer Portföyü Analizi

### 16.1 Mevcut Backtest Güvenilirlik Tahmini (6 aylık)

- T ≈ 125 trading günü; N=12 trial (RR-010 m=12 ile uyumlu)
- **MinBTL gerekli (E[max]=1.5)**: 2.21 yıl ≈ 557 gün
- **Gerçek**: 125 gün << 557 gün → **MinBTL ihlal**
- **Tahmini DSR**: 0.30-0.50 (zayıf kanıt; T küçük + N=12 penaltısı)
- **Tahmini PBO**: 0.40-0.60 (sample yetersiz, overfit suspected)
- **Crisis coverage**: 1/7 (sadece 2026 Mayıs butlan)

### 16.2 Sistem Güvenilirlik Skoru (ordinal 1-10)

| Boyut | Şu an | RR-018 sonrası hedef |
|---|---|---|
| Production sync | 2 (C-1 açık) | 9 |
| Crisis coverage | 1 (0-1 kriz) | 8 (6-7 kriz) |
| Statistical inference (DSR/PBO) | 0 | 8 |
| CV methodology | 2 (basit holdout) | 8 (Purged + CPCV) |
| Cost-awareness | 6 (RR-015 design) | 8 |
| Vol-targeting realism | 4 (RR-016 design) | 8 |
| Reporting standardization | 3 (ad-hoc) | 8 |
| **Overall** | **3/10** | **8/10** |

### 16.3 the maintainer'ın Bu Rapor Sonrası Öğrenecekleri

1. **Mevcut Sharpe raporu enflasyonist olabilir** — DSR ile geriye gidip hesaplanmalı; tahmini %30-60 düşüş beklenir.
2. **6 aylık pencere göründüğünden çok daha zayıf** — N=12 deneme için MinBTL teoremi 2.21 yıl gerektirir; mevcut 0.5 yıl bunun çok altında.
3. **C-1 audit bulgusu kapatılmadan hiçbir backtest rakamına güvenilemez** — "yeşil backtest, kırmızı production" somut risk; eski raporlar RETRACT statüsünde olmalı.

---

## 17. Akademik Kaynak Özeti (BIST katkıları)

1. **López de Prado, M. (2018)** *Advances in Financial Machine Learning*, Wiley, ISBN 978-1119482086. **Bölüm 7** (Purged K-Fold) s.103-111, **12** (CPCV), **14** (Backtest Statistics) s.194-211, **15** (Strategy Risk) s.211-220, **16** (HRP) s.221-242. Tüm metodolojik iskelet; Purged K-Fold + CPCV BIST L1-L6 sinyal değerlendirmesinin akademik tabanı.

2. **López de Prado, M. (2020)** *Machine Learning for Asset Managers*, Cambridge UP. Daha kısa, BIST OS Faz 2-3 dokümantasyonu için pratisyene yönelik referans.

3. **Bailey, D.H. & López de Prado, M. (2014)** "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *Journal of Portfolio Management* 40(5):94-107, SSRN 2460551. DSR formülünün doğrudan referansı; §6.1 formulasyonu burdan.

4. **Bailey, D.H., Borwein, J.M., López de Prado, M. & Zhu, Q.J. (2014)** "Pseudo-Mathematics and Financial Charlatanism", *Notices of the AMS* 61(5):458-471. MinBTL teoremi (Thm 3.1) — the maintainer 6-aylık backtest'inin yetersizliğinin matematiksel kanıtı.

5. **Bailey, D.H., Borwein, J.M., López de Prado, M. & Zhu, Q.J. (2017)** "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4):39-69, DOI 10.21314/JCF.2016.322, SSRN 2326253. CSCV algoritması + PBO formülü; §6.3 doğrudan referans.

6. **Harvey, C.R., Liu, Y. & Zhu, H. (2016)** "...and the Cross-Section of Expected Returns", *Review of Financial Studies* 29(1):5-68. Multiple testing penaltısı; t-stat > 3 yeni hurdle BIST OS L1-L6 IC validation'da uygulanmalı.

7. **Harvey, C.R. (2017)** "The Scientific Outlook in Financial Economics", *Journal of Finance* 72(4):1399-1440, DOI 10.1111/jofi.12530. Replication crisis ve pre-registration disiplini; §11 reporting standardization felsefi tabanı.

8. **Sharpe, W.F. (1966)** "Mutual Fund Performance", *Journal of Business* 39(1):119-138. Klasik Sharpe ratio tanımı; DSR'ın baseline'ı.

9. **Sortino, F.A. & Price, L.N. (1994)** "Performance Measurement in a Downside Risk Framework", *Journal of Investing* 3(3):59-64. Sortino ratio formulasyonu (RR-016 zorunlu metrik).

10. **Martin, P. & McCann, B. (1989)** *The Investor's Guide to Fidelity Funds*, John Wiley & Sons. Ulcer Index tanımı: UI = √(Σ D'_i² / n), D'_i = drawdown since previous peak. Kriz dönem stres testi metriği (§10.2, RR-016).

11. **Young, T.W. (1991)** "Calmar Ratio: A Smoother Tool", *Futures Magazine*. Calmar ratio — RR-016 zorunlu metrik.

12. **Benjamini, Y. & Hochberg, Y. (1995)** "Controlling the False Discovery Rate", *Journal of the Royal Statistical Society, Series B* 57(1):289-300. RR-010 BH-FDR α=0.10 m=12 doğrudan kullanım.

13. **Hudson & Thames mlfinlab documentation** — paid £100+VAT/ay/kullanıcı, QuantConnect only. Reference implementation; ücretsiz alternatif aramada karşılaştırma noktası.

14. **vectorbt documentation (polakowo)** — vectorbt.dev. Faz 3 trial generation; parameter sweep optimization.

15. **timeseriescv (sam31415)** — MIT, version 0.2. CombPurgedKFoldCV implementation.

---

## 18. Kısıtlar & Caveat'lar

1. **mlfinlab paid version sorunu**: Hudson & Thames mlfinlab artık £100/ay/kullanıcı, sadece QuantConnect Cloud. Bu rapor sıfır maliyetli alternatif önerir (timeseriescv + pypbo + custom DSR ~150-200 satır). Custom implementation Bailey-LdP orijinal makalelere sadık olabilir; ancak peer-review edilmiş bir paket olmadığı için **kendi unit test suite şart**.

2. **Computational cost**: CPCV 15 patika × 6 katman × 5 yıl ≈ 7-8 dakika single-thread, 2 dakika 4-core. the maintainer'ın laptop spec'ine bağlı.

3. **BIST veri kalitesi**: yfinance delisted şirketleri kapsamaz; KAP delisted listesi paralel veri kaynağı olarak tutulmalı. **Survivorship bias kalıcı** if yfinance only — sonuçlar %5-10 yukarı yanlı olabilir.

4. **Hiperenflasyon non-stationarity (2022-2024)**: TÜFE yıllık **%72.31 (2022 World Bank)**, **%53.86 (2023)**; zirve **%85.5 Ekim 2022 (TurkStat)**. Nominal getiriler reel anlamda yanıltıcı; **hem nominal hem CPI-deflated reel ikili rapor zorunlu**. Aksi halde Sharpe ratio aşırı şişer.

5. **Crisis period sample size**: Her kriz unique (TRY ≠ COVID ≠ deprem ≠ siyasi). Generalization sınırı var; "sistem 2018 TRY krizinden çıktı" ≠ "2026 başka bir kriz benzer çıkar".

6. **2023 Haziran Şimşek-Erkan rally +%54.3 figürü**: Midas (getmidas.com) bloga dayanır; peer-review yok. Doğrulanmalı veya geri çekilmeli; bu rapor 'kaynak Midas, doğrulanmadı' kaydıyla kullanıyor.

7. **2024 Mart yerel seçim -%6 figürü**: RR-016'da "tahmin" etiketli. The National 1 Nisan 2024'e göre ertesi gün BIST +%0.17 kapanış; sert düşüş **doğrulanmadı**. Faz 4 backtest'inde gerçek veri ile teyit/güncelleme zorunlu.

8. **2020 COVID BIST-specific peak-to-trough**: Küresel S&P 500 -%33.9 (Oxford RAPS 10(4):742) doğrulandı; BIST-100 spesifik figürü authoritative kaynaktan **doğrulanmadı**; ~-%25 hedge tutuldu.

9. **Twitter/X login-wall**: Türk fintwit pratisyen yaklaşımları sistematik gözlem yapılamadı. §14.4 ordinal skala kısmen sezgisel.

10. **the maintainer broker bilgisi belirsizliği**: RR-015 Tier A/B/C paralel hesap. Backtest 3 tier ayrı senaryo üretmeli; nihai karar broker netleştiğinde verilir.

11. **2026 Mart CHP "mutlak butlan" krizi (21 Mayıs 2026)**: Bu rapor yazılırken yaşandı (≤4 gün önce); tam OOS verisi yok. Faz 4 backtest'inde bu kriz **live forward test** olarak izlenebilir.

12. **HMM aktivasyonu (RR-017)**: ENABLE_HMM_WEIGHTS=False default; aktivasyon AG-001 sonrası muhafazakar varsayım. RR-018 framework HMM-on/off her iki durumu destekler.

13. **DİSCLAİMER**: Bu rapor **implementation taslak — production-ready kod DEĞİL**. Builder her formül için unit test + sanity check yapmalı; Bailey-LdP orijinal makalelerine birebir referans göstererek implement etmeli. RR-018 sadece **roadmap + kavramsal iskelet**.

14. **timeseriescv olgunluk uyarısı**: sam31415/timeseriescv version 0.2 (Development Status: 3 - Alpha). Tests fail (Issue #6). Çekirdek CombPurgedKFoldCV sınıfı kullanılabilir ama **kendi test suite yazmadan production'a koymayın**.

15. **mlfinlab upstream LICENSE eksik**: hudson-and-thames/mlfinlab GitHub repo'sunda LICENSE dosyası yok. Community fork'ları (jmrichardson, nasgoncalves, Roh-codeur) hukuki gri alanda; ticari kullanım için lisans araştırması yapılmalı.

---

## Önerilen Karar Eşikleri (the maintainer için)

| Karar | Eşik | Aksiyon |
|---|---|---|
| **C-1 audit closed mu?** | drift = 0 gün son 30g | Aksi halde **deploy bloke** |
| **Backtest güvenilir mi?** | T ≥ MinBTL VE DSR > 0.95 VE PBO < 0.5 | Aksi halde **live para riski yok** |
| **Crisis robust mu?** | 7 krizden 5+ tanesinde crisis MDD ≤ %30 | Aksi halde **position size 0.5×** |
| **Tradeable alpha?** | Gross Sharpe ≥ 1.5 (RR-015 hurdle) | Aksi halde **commission kazanmaz** |
| **HMM aktivasyon?** | 90+g OOS + Sharpe iyileşme ≥ +0.15 | Aksi halde **statik weights** |

Bu eşiklerin **tamamı** karşılanmadan canlı para konulmamalıdır.

---

**RR-018 SONU**