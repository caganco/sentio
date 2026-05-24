# RR-010: BIST OS Trading System — Information Coefficient (IC) Ölçüm Metodolojisi

**Versiyon:** 1.0 | **Tarih:** 23 Mayıs 2026 | **Hedef dosya:** `docs/research/RR-010-bist-ic-measurement.md`
**Önceki referanslar:** CB-002 (regime detection), CB-010 (statik weight savunulamazlığı), RR-002 (KAP), RR-005 (custody), RR-006 (short/VIOP), RR-008 (Türkçe NLP).

---

## 1. EXECUTIVE SUMMARY

BIST OS sisteminin **statik (felsefe-tabanlı) layer weight'leri** (L1=0.25, L2=0.20, L3=0.30, L4=0.12, L5=0.10, L6=0.03) CB-010'da "savunulamaz" olarak işaretlendi; bu rapor, akademik literatür standardına uygun, **ölçüm-tabanlı** bir IC framework'ünü ~660 listelenmiş şirketten (CEIC Mart 2026) aktif ~300, BIST OS pre-filter 50-100 ticker'lık evrene uyarlar. Önerilen mimari: **5-günlük cross-sectional Spearman rank IC** (layer'a göre 5-20d), **120-günlük rolling window**, **Benjamini-Hochberg FDR düzeltmesi**, **ICIR-tabanlı + Bayesian shrinkage** weight kalibrasyonu. Minimum 60 işlem günü `signal_logger.py` birikimi sonrası faza geçilmesi zorunludur; o zamana kadar statik prior'lar korunur.

**5 maddelik yapılacaklar:**
1. `signal_logger.py` çıktısını **panel formatına** (date × ticker × layer_score) dönüştür ve **forward returns** tablosu (1d/5d/10d/20d) hesapla; survivorship için delisted ticker'ları koruyan ayrı tablo tut.
2. Günlük **cross-sectional Spearman IC** hesabını her layer × her horizon için yap (`scipy.stats.spearmanr`, NaN pairwise drop, sektör-içi `group_adjust=True` paralel hesap).
3. 60 günde ilk **ICIR raporu** + Holm-Bonferroni/BH-FDR düzeltmeli p-value tablosu; 120 günde **rolling IC trend** + decay tespiti.
4. Weight güncellemesini **Bayesian shrinkage** ile aşamalı yap: prior = mevcut statik, likelihood = gözlenen ICIR. τ schedule 60d %20, 180d %50, 365d %80, 730d %95. Min-max: 0.05 ≤ wᵢ ≤ 0.50.
5. **Re-calibration trigger'ları:** (a) son 60d ICIR < 0, (b) CB-002 rejim değişimi flag'i, (c) layer kümülatif IC −2σ kırılması, (d) yeni layer ekleme (RR-008 hybrid, RR-006 short).

### Tablo 1 — Önerilen IC Parametreleri (BIST OS)

| Parametre | Seçim | Kaynak |
|---|---|---|
| Korelasyon tipi | **Spearman rank IC** | Grinold & Kahn (2000); Alphalens default |
| Forward window (birincil) | **5 gün** | Li & Zhang (2018 IEEE doc 8690416) |
| Forward window (matrix) | 1d, 5d, 10d, 20d | Multi-horizon dispersion analizi |
| Cross-section vs TS | **Cross-sectional (panel)** | Grinold (1989); Fama-MacBeth |
| Rolling window | **120 gün** | Asness et al. (2013) JF 68(3):929 |
| Multiple testing | **BH-FDR (α=0.10), m=12** | Benjamini & Hochberg (1995) JRSS-B |
| t-stat hurdle (yeni layer) | **t > 3.0** | Harvey, Liu, Zhu (2016) RFS 29(1):5 |
| Weight formülü | **ICIR-weighted + Bayesian shrinkage** | Qian & Hua (2004); Black & Litterman (1992) |
| CV framework | **Purged K-Fold (K=5) + Embargo (h=10d)** | López de Prado (2018) AFML Ch.7 |
| Sektör nötralizasyon | **`group_adjust=True` paralel** | Clarke et al. (2002); Alphalens |
| Minimum panel gözlem | **N ≥ 60 gün × ~75 ticker ≈ 4500** | Lewellen (2015) CFR 4(1):1 |
| Hit rate metriği | sign-agreement % | İkincil teyit |

---

## 2. METODOLOJİ — A/B/C/D/E ALANLARI

### A1. Information Coefficient Temel Tanımları

**Tanım:** IC, bir alfa sinyalinin (layer skoru) gerçekleşen forward getirilerle ne ölçüde korele olduğunun ölçüsüdür. Cross-sectional yorumda: belirli bir günde, evrendeki tüm ticker'lar için `skor(i,t)` ile `forward_return(i, t→t+h)` arasındaki rank korelasyon.

**Formüller:**
```
Pearson IC_t  = corr(score_t, fwd_return_t)
Spearman IC_t = corr(rank(score_t), rank(fwd_return_t))
ICIR          = mean(IC_t) / std(IC_t)            # Qian & Hua (2004) "strategy risk"
IR            ≈ IC × √Breadth                     # Grinold (1989) Fundamental Law
Hit Rate      = (1/T) Σ 1[sign(score_t) == sign(fwd_return_t)]
```

**Pearson vs Spearman seçimi:** Pearson lineer ilişkiyi ölçer ve outlier'lara duyarlıdır. BIST'te (a) günlük getiri dağılımları kalın kuyrukludur — TL volatilitesi ve TCMB politika sürprizleri (TCMB PPK 27 Nisan 2026 kararı: bir hafta vadeli repo ihale faizi %37'de sabit) outlier üretir; (b) layer skorları farklı ölçeklerdedir (RSI 0-100, sentiment z-score, KAP event flag binary). Bu nedenle **Spearman rank IC zorunlu**, Pearson sadece ikincil teyit olarak raporlanır.

**"Anlamlı IC" eşikleri (literatür konsensüsü):**
- IC ~ 0.02-0.05: zayıf ama ölçeklenebilir sinyal
- IC ~ 0.05-0.10: makul faktör (US large-cap için tipik)
- IC > 0.10: güçlü; nadir, dikkatli doğrulama gerek
- ICIR ≥ 0.5 (annualized) → fonlanabilir; ≥ 1.0 mükemmel (Grinold & Kahn, 2000)

**Akademik kaynaklar:** Grinold, R. (1989) *JPM* 15(3):30-37; Qian & Hua (2004) *JOIM* 2(3), SSRN 569281.

**BIST'e uyarlama:** Breadth (N) düşük. Grinold formülünde N = ticker × yıldaki bağımsız tahmin. BIST OS pre-filter ~75 ticker × 250 işlem günü / holding(5d) ≈ **3750 efektif bet/yıl** — US tipik 36 000 bet'in ~%10'u. Aynı IC ile IR ~√10 = 3.16 kat düşer; **multi-horizon ve sektör-içi paralel hesap kritik**.

---

### A2. Forward Return Window Seçimi

**Window etkisi:**
- **1-gün IC:** Gürültü dominant. Sadece event-driven (L3 KAP, L4 sentiment shock); teknik için tipik IC −0.02 ile +0.02 gürültü bandı.
- **5-gün IC:** Endüstri standardı. Li & Zhang (2018 IEEE doc 8690416) XGBoost ile çoğu pratisyen 5-10d benimser; back-test'leri yıllık %22.54 getiri raporlamıştır.
- **10-20 gün IC:** Value/momentum uzun horizon (Asness, Moskowitz, Pedersen 2013 JF 68(3):929-985, doi:10.1111/jofi.12021).
- **60-gün IC:** L2 Macro (TCMB faiz, CDS, USDTRY) için makul.

**Multi-horizon IC matrix:** layer × {1d, 5d, 10d, 20d, 60d} tablosu, *information horizon* (Qian-Sorensen-Hua 2007 JPM) gösterir.

**BIST tipik holding period:** 2-4 hafta. **Layer-specific window:**
- L1, L4, L5 → **5d primary**
- L2 → **20d primary**
- L3 → **1d (event) + 5d (drift)**
- L6 → ICIR yerine portfolio Sharpe attribution

---

### A3. Cross-sectional vs Time-series IC

**Cross-sectional (CS) IC** (önerilen): Belirli bir günde, evrendeki tüm ticker'lar arasında rank(skor) vs rank(forward_return). Çıktı: günlük IC zaman serisi → mean(IC) ve ICIR. Alphalens default: `factor_information_coefficient(factor_data, group_adjust=False, by_group=False)` Spearman IC döndürür.

**Time-series (TS) IC:** Tek ticker, zamanda skor vs return. Faktör literatüründe nadir; market timing için kullanılır.

**Hybrid Panel IC (önerilen):** Fama-MacBeth tarzı — günlük CS IC, T gün ortalama, Newey-West düzeltilmiş t-stat:
```
IC_panel = (1/T) Σ_t IC_t
t-stat   = IC_panel · √T / std(IC_t)     # Newey-West lag = horizon h
```
Lewellen (2015) *Critical Finance Review* 4(1):1-44 (doi:10.1561/104.00000024): 15 firm karakteristik ile expected return tahminleri için **predictive slope 0.74 (SE 0.07)** raporlar.

**BIST'te darlık:** 50-100 ticker cross-section US'deki 3000+ stock'a göre dar; bkz. B8 sample size analizi.

---

### B4. Multiple Testing Problem

**Sorun:** 6 layer × 4 forward window = 24 hipotez. Geleneksel α=0.05 ile en az 1 false positive olasılığı 1−(1−0.05)²⁴ ≈ **%71**. CB-010'un "savunulamaz" yorgusu kısmen bu testin yapılmamış olmasındandır.

**Düzeltme alternatifleri:**
1. **Bonferroni:** α' = α/m. m=24 → α'=0.0021. Aşırı muhafazakar.
2. **Holm-Bonferroni step-down:** Sıralı, k. p-değerini α/(m−k+1) ile karşılaştır.
3. **Benjamini-Hochberg FDR (1995):** *JRSS-B* 57(1):289-300 (doi:10.1111/j.2517-6161.1995.tb02031.x). k. p-değerini (k/m)·α ile karşılaştır. **Modern standart.**
4. **Harvey, Liu, Zhu (2016) "...and the Cross-Section of Expected Returns"** *Review of Financial Studies* 29(1):5-68 (doi:10.1093/rfs/hhv059, NBER w20592): verbatim *"Our collection of 316 factors likely underrepresents the factor population"* (1967-2014 ana dergiler); yeni faktör için **t-stat > 3.0 hurdle** gerekir.
5. **Deflated Sharpe Ratio (DSR)** — Bailey & López de Prado (2014) *JPM* 40(5):94-107 (SSRN 2460551):

```
DSR = Φ[ (SR̂ − SR̂₀) · √(T−1) / √(1 − γ̃₃·SR̂ + ((γ̃₄−1)/4)·SR̂²) ]

SR̂₀ = √V[{SR̂ₙ}] · [(1−γ_E)·Φ⁻¹(1−1/N) + γ_E·Φ⁻¹(1−1/(N·e))]
```
γ_E ≈ 0.5772 (Euler-Mascheroni); N = bağımsız trial sayısı; T = obs; γ̃₃, γ̃₄ = skewness/kurtosis. DSR ≥ 0.95 hurdle (verbatim örnek: SR̂=2.5, T=1250, N=100 → DSR=0.9004, %95'i geçmez).

**BIST OS için öneri:** 6 layer × 2 birincil window (5d, 20d) = **12 test, BH-FDR α=0.10**. Yeni layer için |t|>3.0 ve DSR>0.95 zorunlu.

---

### B5. Non-stationarity

**Sorun:** IC zaman-değişken (Asness et al. 2013): rejim-bağımlı.

**Rolling window:**
- **60 gün:** Çok gürültülü; sadece ön gösterge.
- **120 gün:** **Önerilen** — yarı yıllık siklus + makul SE; CB-002 ile uyumlu.
- **250 gün (1 yıl):** Daha stabil ama stale; TCMB 2023-2026 sertleşme döngüsü eski IC'leri irrelevant kılabilir.

**Expanding window:** Tüm geçmiş. **Dual-track raporlama:** rolling + expanding.

**IC half-life (exponential decay):**
```
IC(t) ≈ IC(0) · exp(−t/τ_HL)
τ_HL = ln(2) / |decay_rate|
```
McLean & Pontiff (2016) *JF* 71(1):5-32 (doi:10.1111/jofi.12365): 97 karakteristik için verbatim *"Portfolio returns are 26% lower out-of-sample and 58% lower post-publication."* BIST için extrapolasyon: literatürden alınan faktörler için %30-60 decay; in-house sinyallere (RR-002 KAP NLP, RR-008 hybrid sentiment) daha yavaş ancak liquidity-driven shock'lar (small caps) hızlandırıcı.

---

### B6. Sektör-Nötr IC

**Sorun:** Raw IC sektör bias içerir; XBANK haftalık yükseliyorsa banka-yoğun layer skorları IC'yi şişirir.

**İki yöntem:**
1. **Industry-neutralization (önerilen):** Forward return'ü sektör ortalamasından çıkar:
```
residual_return(i,t) = return(i,t) − mean(return(j,t) | j ∈ sector(i))
IC_neutral = corr(rank(score), rank(residual_return))
```
Alphalens: `factor_information_coefficient(factor_data, group_adjust=True)`.

2. **Within-sector IC:** Her sektör için ayrı IC. BIST'te 50-100 ticker × ~15 sektör = sektör başına ~5-7 ticker → statistik güç düşük.

**BIST sektör endeksleri (Borsa İstanbul resmî):** XU30, XU100, XBANK, XELKT, XGIDA, XHOLD, XINSA, XKAGT, XKMYA, XMADE, XMANA, XMESY, XTAST, XTEKS, XTRZM, XULAS — `borsaistanbul.com` *Sector* endeks ailesi.

**Pratik karar:** `IC_raw` ve `IC_group_adjust=True` paralel raporlanır; fark > 0.05 → sektör bias uyarısı (Clarke et al. 2002; Ehsani & Harvey QuantRocket / Alpha Architect tartışması).

---

### B7. Kod-Seviyesi İmplementasyon

**Python kütüphane seçimi:**
- `scipy.stats.spearmanr(a, b, nan_policy='omit')` — pairwise NaN drop, tied-rank default "average."
- `pandas.DataFrame.corr(method='spearman')` — kolon-kolon; pairwise.complete default.
- `scipy.stats.kendalltau` — O(n²); spot kontrol.
- **`alphalens-reloaded`** (alphalens.ml4trading.io) — production-ready; `factor_information_coefficient`, `mean_information_coefficient`, `plot_ic_ts`, `plot_ic_hist`, `plot_ic_qq`.
- **`mlfinlab`** / `timeseriescv` (sam31415) — Purged K-Fold, CombPurgedKFoldCV.
- `statsmodels.stats.multitest.multipletests(pvals, alpha=0.10, method='fdr_bh')` — BH-FDR.

**NaN handling:** Layer skor eksikleri yaygındır (KAP olayı olmayan ticker için L3=NaN). **Pairwise drop** kullan; full-row drop gözlemi yarıya indirir.

**Tied ranks:** scipy default "average" istatistiksel doğru. Discrete skorlarda (binary KAP flag) IC magnitude doğal düşer.

**Walk-forward CV (López de Prado 2018 Ch.7):**
```
Purged K-Fold (K=5):
  - Fold sınırlarında embargo h gün (h = forward horizon)
  - Test fold'una sızan train sample'larını purge et
Combinatorial Purged CV (CPCV):
  - N gruba böl, k tanesini test seç (C(N,k) kombinasyon)
  - Her path için DSR hesabı
```

**Daily IC pseudo-code:**
```python
import pandas as pd, numpy as np
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

def daily_ic(scores_df, fwd_returns_df, layer, horizon):
    out = []
    for dt, day in scores_df.groupby(level='date'):
        s = day[layer].droplevel('date')
        r = fwd_returns_df.loc[dt][f'fwd_{horizon}d']
        merged = pd.concat([s, r], axis=1).dropna()
        if len(merged) < 20:        # min cross-section
            continue
        ic, p = spearmanr(merged.iloc[:,0], merged.iloc[:,1])
        out.append({'date':dt, 'ic':ic, 'p':p, 'N':len(merged)})
    return pd.DataFrame(out).set_index('date')

def sector_adjusted_fwd_return(returns_df, sector_map):
    grp = returns_df.groupby(sector_map)
    return returns_df - grp.transform('mean')

def fdr_correction(pvals, alpha=0.10, method='fdr_bh'):
    reject, p_adj, _, _ = multipletests(pvals, alpha=alpha, method=method)
    return reject, p_adj

def ic_summary(ic_series):
    mean_ic = ic_series['ic'].mean()
    std_ic  = ic_series['ic'].std(ddof=1)
    icir    = mean_ic / std_ic if std_ic>0 else 0
    T       = len(ic_series)
    t_stat  = mean_ic * np.sqrt(T) / std_ic if std_ic>0 else 0
    return {'mean':mean_ic, 'std':std_ic, 'icir':icir, 't':t_stat, 'T':T}
```

**SQLite şeması:**
```sql
CREATE TABLE layer_scores (
    date TEXT, ticker TEXT, layer TEXT, score REAL,
    PRIMARY KEY(date, ticker, layer));

CREATE TABLE forward_returns (
    date TEXT, ticker TEXT, h1 REAL, h5 REAL, h10 REAL, h20 REAL,
    h5_sector_adj REAL, h20_sector_adj REAL,
    PRIMARY KEY(date, ticker));

CREATE TABLE ic_history (
    date TEXT, layer TEXT, horizon INTEGER,
    ic REAL, p_value REAL, n_obs INTEGER, group_adjust INTEGER,
    PRIMARY KEY(date, layer, horizon, group_adjust));

CREATE TABLE weight_history (
    date TEXT, layer TEXT, weight REAL, method TEXT,
    icir_60d REAL, icir_120d REAL,
    PRIMARY KEY(date, layer, method));

CREATE TABLE delisted_tickers (
    ticker TEXT PRIMARY KEY, delist_date TEXT, reason TEXT);
```

**Reporting dashboard (Streamlit/Plotly):**
1. Günlük IC heatmap (6 layer × 4 horizon × group_adjust on/off)
2. Rolling 120d IC çizgisi (layer renk; ±2σ bandı)
3. ICIR bar chart (annualized; benchmark 0.5 ve 1.0 referans çizgileri)
4. Sektör-içi vs raw IC fark histogramı
5. BH-FDR adjusted p-value tablosu + significant flag
6. Decay slope trend (30/60/120d rolling)

---

### B8. Sample Size Gereksinimleri

**Standard error:**
```
SE(IC) = √((1 − IC²) / (N − 2))
t-stat = IC · √(N − 2) / √(1 − IC²)
95% CI = IC ± 1.96 · SE(IC)
```

**BIST OS minimum:**
- Cross-section: N=20 sıkı, 50 ideal, **75 pre-filter sonrası tipik**.
- Toplam panel: 60d × 75 = **4500 gözlem** — yeterli ama dar.
- IC=0.05 için: SE = √(0.9975/4498) ≈ 0.0149; t ≈ 3.36 → anlamlı.
- IC=0.02 için: t ≈ 1.34 → anlamsız; 250d × 75 = 18 750'de t ≈ 2.74.

**Lewellen (2015):** Fama-MacBeth slopes 10-yıl rolling, 15 karakteristik → expected return σ_CS = 0.87% aylık; predictive slope 0.74 (SE 0.07).

**BIST extrapolasyon:** US literatür N>50 000 varsayar (3000 stock × monthly × 20+ yıl). BIST OS panel iki sıra (10²) daha küçük → **IC > 0.03 eşik**, **6 aydan az tarihçeli sinyalleri "deneysel"** statüde tut.

---

### B9. IC'den Weight'e Dönüşüm

**Naive (Li & Zhang 2018 baseline):** `wᵢ ∝ ICᵢ`, negatif IC'leri sıfırla, normalize. Verbatim *"the performance of dynamic weighting strategy is superior to the equal weighting strategy and IC weighting strategy."* — yani Li & Zhang IC-weighting'i baseline kabul edip XGBoost ile aşmıştır.

**IC-weighted mutlak:** `wᵢ = |ICᵢ| / Σ|ICⱼ|`. Negatif IC'li layer'ı contrarian olarak kullan.

**ICIR-weighted (önerilen):** `wᵢ ∝ ICRᵢ`. Qian & Hua (2004) verbatim: *"a more consistent estimation of information ratio is the ratio of average information coefficient to the standard deviation of information coefficient."*

**Maximally Diversified / mean-variance:** 6×6 IC kovaryans, Markowitz instabilite riski. Bu raporda **önerilmez**; ileri faz.

**Black-Litterman implied Bayesian shrinkage (önerilen):**
```
w_post = [Σ_prior⁻¹ + Σ_data⁻¹]⁻¹ · [Σ_prior⁻¹·w_prior + Σ_data⁻¹·w_data]
```
τ ölçek faktörü: Black-Litterman geleneği 0.025-0.05 (Idzorek; He & Litterman 1999). BIST için **heuristik time-varying tau:**
- 60d → τ_data = 0.20
- 180d → 0.50
- 365d → 0.80
- 730d → 0.95

**Constraints (Clarke, de Silva, Thorley 2002 *FAJ* 58(5):48-66, doi:10.2469/faj.v58.n5.2468):**
- Σwᵢ = 1.0
- 0.05 ≤ wᵢ ≤ 0.50
- Transfer Coefficient (TC) — verbatim: *"the correlation between the risk-adjusted alphas and active weights"*; constraint'ler altında IR = IC × TC × √N. BIST OS retail (long-only, lot, likidite) tipik TC ≈ 0.3-0.7.

---

### B10. Black-Litterman Tarzı Bayesian Update

Black & Litterman (1992) *FAJ*:
```
E[R]_post = [(τΣ)⁻¹ + Pᵀ·Ω⁻¹·P]⁻¹ · [(τΣ)⁻¹·Π + Pᵀ·Ω⁻¹·Q]
```
Π = equilibrium prior; Q = views; P = view-asset mapping; Ω = view uncertainty (He & Litterman 1999: Ω_diag = τ·P·Σ·Pᵀ); τ ∈ [0.025, 0.05].

**BIST OS uyarlama (weight-space):**
- Prior: statik weight (L1=0.25, ..., L6=0.03), Σ_prior = I · 0.10² (uzman uncertainty).
- Data: ICIR-implied w_data; Σ_data = diag(SE(ICIR)²).
- τ_eff = N_observed / N_target.

**Pratik:**
```python
def bayesian_layer_weights(w_prior, w_data, Σ_prior, Σ_data, tau_eff):
    Σp_eff = Σ_prior / max(tau_eff, 1e-6)
    invP = np.linalg.inv(Σp_eff); invD = np.linalg.inv(Σ_data)
    cov_post  = np.linalg.inv(invP + invD)
    mean_post = cov_post @ (invP @ w_prior + invD @ w_data)
    w = np.clip(mean_post, 0.05, 0.50)
    return w / w.sum()
```

---

### B11. Bias Kaynaklar

**Survivorship bias:** Delisted BIST tickers (ASYAB, ULUUN benzeri) yfinance'te eksik → IC şişirilmiş. **Çözüm:** `delisted_tickers` SQL tablo + KAP/Borsa İstanbul historical listings.

**Look-ahead bias:** t+5 günün price'ını t skor üretiminde kullanmak. **Önlem:** close-of-day timestamp, fwd_return t+1 open'dan; embargo h gün CV fold'larında.

**Selection bias:** Sadece in-sample iyi performans gösteren kombinasyonu raporlama. **Önlem:** Pre-registered hipotezler (6 layer × 2 window = 12 test sabit), yeni layer için ayrı HLZ t>3.0.

**Data snooping:** Parametre denemeleri. **Önlem:** López de Prado (2018) Ch.11 ve Bailey & López de Prado (2014) DSR zorunlu.

---

### B12. Decay Analizi

**IC decay vs alpha decay:** IC decay = predictive correlation kaybı; alpha decay = realized return kaybı. İlişkili ama farklı (Clarke et al. 2002 transfer coefficient ikisini birleştirir).

**Exponential fit:**
```
ln IC_h(t) ≈ ln IC₀ − t/τ_HL          # OLS ile τ_HL tahmin
```

**Test:** Son 30d ile önceki 30d IC ortalama karşılaştırması (t-test veya Wilcoxon).

**McLean & Pontiff (2016):** %58 post-publication decay. BIST için extrapolasyon: literatür-orjinli faktörlerde %30-60 decay; in-house RR-002/RR-008 sinyaller bilinmiyor ama foreign flow ve liquidity-driven shock'lar (small caps; RR-005 custody data triangulate edebilir) decay hızlandırıcı.

**Decay monitör:**
- 30/60/120d rolling IC trend slope (OLS).
- Slope < −0.001/gün → uyarı.
- Slope < −0.002/gün → "review" durumu.

---

## 3. KARARLAR TABLOSU

| # | Karar Konusu | Seçim | Alternatif | Neden | Akademik Kaynak |
|---|---|---|---|---|---|
| 1 | Korelasyon tipi | Spearman rank IC | Pearson | BIST kalın kuyruk + farklı ölçekli layer skorları | Grinold & Kahn (2000); Alphalens default |
| 2 | Birincil forward window | 5 gün | 1d (gürültü), 20d (sparse) | BIST holding 2-4 hafta orta noktası | Li & Zhang (2018 IEEE 8690416); endüstri standardı |
| 3 | Sekonder window matrix | 1d, 10d, 20d | 60d, 90d | Multi-horizon IC + information horizon | Qian, Sorensen, Hua (2007) JPM |
| 4 | IC method | Cross-sectional panel | Time-series | Faktör literatür standardı | Grinold (1989); AQR pratiği |
| 5 | Rolling window | 120 gün | 60d (gürültü), 250d (stale) | Yarı yıllık siklus + CB-002 uyumu | Asness et al. (2013) JF 68(3):929 |
| 6 | Multiple testing | BH-FDR (α=0.10), m=12 | Bonferroni m=24 α=0.05 | Modern, az conservative | Benjamini & Hochberg (1995) JRSS-B |
| 7 | Yeni layer hurdle | t > 3.0 + DSR > 0.95 | t > 2.0 klasik | Factor zoo, data mining | Harvey, Liu, Zhu (2016) RFS 29(1):5 |
| 8 | Backtest stats | Deflated Sharpe Ratio | Raw Sharpe | N trial deflation; selection bias | Bailey & López de Prado (2014) JPM 40(5) |
| 9 | Weight formülü | ICIR-weighted + Bayesian | Naive IC-prop | Strategy risk; prior'a smooth geçiş | Qian & Hua (2004); Black & Litterman (1992) |
| 10 | τ schedule | 0.20 (60d) → 0.95 (730d) | Sabit τ=0.05 | BIST'te 60d veri ile prior dominant | He & Litterman (1999); Idzorek |
| 11 | Min/max weight bound | 0.05 ≤ wᵢ ≤ 0.50 | Unconstrained | Yoğunlaşma koruması; TC'yi korur | Clarke et al. (2002) FAJ 58(5):48 |
| 12 | CV framework | Purged K-Fold (K=5) + Embargo h=10d | Standard CV, walk-forward | Time-series leakage; embargo h≥horizon | López de Prado (2018) AFML Ch.7 |
| 13 | Sektör nötralizasyon | group_adjust=True paralel | Sadece raw IC | XBANK ağırlığı; bias kontrol | Clarke et al. (2002); Alpha Architect |
| 14 | Decay monitör | 30/60/120d rolling slope | Yıllık snapshot | Rejim değişimi erken yakalama | McLean & Pontiff (2016) JF 71(1):5 |
| 15 | Survivorship | delisted_tickers tablo | yfinance only | Şişirilmiş IC önlenir | López de Prado (2018) genel |
| 16 | Layer-specific window | L1/L4/L5=5d; L2=20d; L3=1d+5d | Uniform 5d | Frequency mismatch (macro haftalık) | Qian-Sorensen-Hua information horizon |

---

## 4. IMPLEMENTATION PSEUDOCODE — Daily IC + Weight Pipeline

```python
# bist_ic_pipeline.py
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

DB = "data/bist_signals.db"
LAYERS = ['L1','L2','L3','L4','L5','L6']
HORIZONS = [1, 5, 10, 20]
PRIMARY_WIN = {'L1':5, 'L2':20, 'L3':5, 'L4':5, 'L5':5, 'L6':20}
ROLLING_DAYS = 120

# ---------- 1) Daily cross-sectional IC ----------
def compute_daily_ic(date, layer, horizon, group_adjust=False):
    conn = sqlite3.connect(DB)
    q_s  = "SELECT ticker, score FROM layer_scores WHERE date=? AND layer=?"
    sfx  = '_sector_adj' if group_adjust else ''
    q_r  = f"SELECT ticker, h{horizon}{sfx} AS r FROM forward_returns WHERE date=?"
    s = pd.read_sql(q_s, conn, params=(date, layer)).set_index('ticker')
    r = pd.read_sql(q_r, conn, params=(date,)).set_index('ticker')
    df = pd.concat([s, r], axis=1).dropna()
    if len(df) < 20:
        return None
    ic, p = spearmanr(df['score'], df['r'])
    return {'date':date, 'layer':layer, 'horizon':horizon,
            'ic':ic, 'p_value':p, 'n_obs':len(df),
            'group_adjust':int(group_adjust)}

# ---------- 2) Rolling IC summary + ICIR ----------
def rolling_ic_summary(layer, horizon, window=ROLLING_DAYS, group_adjust=False):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT date, ic, p_value, n_obs FROM ic_history "
        "WHERE layer=? AND horizon=? AND group_adjust=? "
        "ORDER BY date DESC LIMIT ?",
        conn, params=(layer, horizon, int(group_adjust), window))
    if len(df) < 20:
        return {'status':'insufficient_data'}
    mean_ic = df['ic'].mean()
    std_ic  = df['ic'].std(ddof=1)
    icir    = mean_ic / std_ic if std_ic>0 else 0
    t_stat  = mean_ic * np.sqrt(len(df)) / std_ic if std_ic>0 else 0
    slope, _ = np.polyfit(np.arange(len(df)), df['ic'].values, 1)
    return {'mean':mean_ic, 'std':std_ic, 'icir':icir,
            't_stat':t_stat, 'n_days':len(df), 'decay_slope':slope}

# ---------- 3) Multiple testing (12 tests = 6 layer × 2 win) ----------
def fdr_test_panel(date, alpha=0.10):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT layer, horizon, ic, p_value FROM ic_history "
        "WHERE date=? AND horizon IN (5,20) AND group_adjust=0",
        conn, params=(date,))
    if len(df) != 12:
        return None
    reject, p_adj, _, _ = multipletests(df['p_value'].values,
                                       alpha=alpha, method='fdr_bh')
    df['p_adj'] = p_adj
    df['significant'] = reject
    return df

# ---------- 4) ICIR-weighted + Bayesian update ----------
W_PRIOR = np.array([0.25, 0.20, 0.30, 0.12, 0.10, 0.03])
SIGMA_PRIOR = np.eye(6) * 0.10**2

def tau_schedule(days):
    if days < 60:   return 0.0
    if days < 180:  return 0.20
    if days < 365:  return 0.50
    if days < 730:  return 0.80
    return 0.95

def compute_layer_weights(date):
    icir_vec, se_vec, n_days_vec = [], [], []
    for L in LAYERS:
        r = rolling_ic_summary(L, PRIMARY_WIN[L])
        if r.get('status') == 'insufficient_data':
            return W_PRIOR, 'prior'
        icir_vec.append(max(r['icir'], 0))
        se_vec.append(1.0/np.sqrt(r['n_days']))
        n_days_vec.append(r['n_days'])
    icir_vec = np.array(icir_vec)
    if icir_vec.sum() == 0:
        return W_PRIOR, 'prior'
    w_data = icir_vec / icir_vec.sum()
    Σ_data = np.diag(np.array(se_vec)**2 + 1e-6)
    tau = tau_schedule(min(n_days_vec))
    if tau == 0:
        return W_PRIOR, 'prior'
    Σp_eff = SIGMA_PRIOR / max(tau, 1e-6)
    invP, invD = np.linalg.inv(Σp_eff), np.linalg.inv(Σ_data)
    cov_post  = np.linalg.inv(invP + invD)
    mean_post = cov_post @ (invP @ W_PRIOR + invD @ w_data)
    w = np.clip(mean_post, 0.05, 0.50)
    return w / w.sum(), f'bayesian_tau={tau}'

# ---------- 5) Re-calibration triggers ----------
def check_recalibration_triggers(date):
    triggers = []
    for L in LAYERS:
        r = rolling_ic_summary(L, PRIMARY_WIN[L], window=60)
        if r.get('icir', 0) < 0:
            triggers.append(f'{L}_ICIR_negative_60d')
        if r.get('decay_slope', 0) < -0.002:
            triggers.append(f'{L}_decay_accelerated')
    conn = sqlite3.connect(DB)
    rej = pd.read_sql(
        "SELECT regime_change FROM regime_log "
        "WHERE date<=? ORDER BY date DESC LIMIT 1",
        conn, params=(date,))
    if len(rej) and rej.iloc[0,0]:
        triggers.append('regime_change_CB002')
    return triggers
```

---

## 5. AKADEMİK KAYNAK ÖZETİ

### Grinold, R. (1989) "The Fundamental Law of Active Management" *JPM* 15(3):30-37
IR = IC × √N (breadth). Tüm IC framework'ünün matematiksel temeli. **BIST katkısı:** N küçük olduğu için (~3750 bet/yıl), aynı IC seviyesinde IR ABD'ye kıyasla ~√10 ≈ 3.16 kat düşük — daha sıkı sinyal kalitesi gerekir.

### Grinold, R.C. & Kahn, R.N. (2000) *Active Portfolio Management* 2nd ed., McGraw-Hill
Active portfolio'nun kanonik kitabı; IC, IR, breadth, transfer coefficient kavramları. **BIST katkısı:** Layer weight'lerin "philosophy" yerine ICIR-tabanlı olması gerekliliğinin standart referansı.

### Qian, E. & Hua, R. (2004) "Active Risk and Information Ratio" *JOIM* 2(3), SSRN 569281
ICIR = mean(IC)/std(IC) — *strategy risk* (σ_IC) Grinold'a ek bağımsız risk. **BIST katkısı:** Yüksek-ortalama-yüksek-varyans layer, düşük-ortalama-yüksek-tutarlılık layer'dan daha az değerli olabilir.

### Clarke, R., de Silva, H., Thorley, S. (2002) "Portfolio Constraints and the Fundamental Law" *FAJ* 58(5):48-66, doi:10.2469/faj.v58.n5.2468
Transfer Coefficient TC ∈ [0,1]; IR = IC × TC × √N. **BIST katkısı:** Long-only, lot, likidite limitleri TC'yi 0.3-0.7'de tutar; "kağıt IC" ile "uygulanan IC" arasındaki açık.

### Li, J. & Zhang, R. (2018 IEEE doc 8690416) "Dynamic Weighting Multi-Factor Stock Selection Based on XGBoost"
XGBoost ile IC tahmini → dinamik weight; back-test yıllık %22.54 getiri. Verbatim: *"the performance of dynamic weighting strategy is superior to the equal weighting strategy and IC weighting strategy."* **BIST katkısı:** ML-tabanlı dinamik weight bir sonraki faz (RR-011); bu RR-010 ICIR-weighted'ı baseline kabul eder.

### López de Prado, M. (2018) *Advances in Financial Machine Learning*, Wiley
Ch.7 Purged K-Fold + Embargo; Ch.8 feature importance; Ch.11 Backtest Stats (DSR, PBO). **BIST katkısı:** Time-series leakage'ı engelleyen tek tutarlı framework; embargo h ≥ horizon zorunlu.

### Bailey, D.H. & López de Prado, M. (2014) "The Deflated Sharpe Ratio" *JPM* 40(5):94-107, SSRN 2460551
DSR formülü (B4'te tam); DSR ≥ 0.95 hurdle. **BIST katkısı:** Birden fazla weight kombinasyonu denenince selection bias düzeltmesi.

### Tomtosov, A. (2024) "Overlapping portfolio holdings and unique sources of emerging market risk" *Borsa Istanbul Review* 24(2):201-217
**Türkiye sample'da yok** (10 EM: Brazil, China, HK, India, Indonesia, Malaysia, Russia, Taiwan, Thailand, Vietnam). 12-ay holding; long top 30% / short bottom 30%; momentum/size/low-vol. Verbatim: *"On average, momentum loses 45% of duplicated portfolio holdings, size loses 43%, and low volatility is 47%."* **BIST katkısı:** EM faktör portföyleri 15-35% örtüşür; rejim dönemlerinde 66-82%'ye çıkar → layer korelasyon riskine işaret; ileride Maximally Diversified weight için kovaryans tahmini gerekir.

### Asness, C.S., Moskowitz, T.J., Pedersen, L.H. (2013) "Value and Momentum Everywhere" *JF* 68(3):929-985, doi:10.1111/jofi.12021
Value+momentum primleri 8 piyasada tutarlı; ortak faktör yapısı, global funding liquidity risk. **BIST katkısı:** L1 technical momentum ve değer sinyallerinde pozitif IC beklentisi; BIST'in liquidity shock'larına aşırı duyarlılığı bu primleri rejim-bağımlı kılar.

### Harvey, C.R., Liu, Y., Zhu, H. (2016) "...and the Cross-Section of Expected Returns" *RFS* 29(1):5-68, doi:10.1093/rfs/hhv059, NBER w20592
316+ yayınlanmış faktör. Verbatim: *"Our collection of 316 factors likely underrepresents the factor population"* ve *"a newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0."* **BIST katkısı:** Yeni layer eklenirken (RR-008 hybrid) t > 3.0 hurdle uygulanmalı.

### Benjamini, Y. & Hochberg, Y. (1995) "Controlling the False Discovery Rate" *JRSS-B* 57(1):289-300, doi:10.1111/j.2517-6161.1995.tb02031.x
FDR control'un kurucu makalesi. **BIST katkısı:** m=12 hipotez için BH-FDR α=0.10; `statsmodels` ile direkt uygulanır.

### McLean, R.D. & Pontiff, J. (2016) "Does Academic Research Destroy Stock Return Predictability?" *JF* 71(1):5-32, doi:10.1111/jofi.12365
Verbatim: *"Portfolio returns are 26% lower out-of-sample and 58% lower post-publication."* **BIST katkısı:** Literatürden alınan klasik faktörler (B/M, momentum) BIST'te de decay riski; in-house sinyaller monitör altında (decay slope).

### Lewellen, J. (2015) "The Cross-section of Expected Stock Returns" *CFR* 4(1):1-44, doi:10.1561/104.00000024
Fama-MacBeth 15 karakteristikle composite expected return; predictive slope 0.74 (SE 0.07). **BIST katkısı:** Panel Fama-MacBeth (= günlük CS IC + zaman ortalaması) ve çok-karakteristikli composite skor literatürde desteklidir.

### Black, F. & Litterman, R. (1992) "Global Portfolio Optimization" *FAJ* 48(5):28-43
Bayesian posterior; τ ∈ [0.025, 0.05]. **BIST katkısı:** Layer weight güncelleme için Bayesian; CB-010 statik weight prior, gözlenen IC likelihood.

### Atilgan, Y., Bali, T.G., Demirtas, K.O., Gunaydin, A.D. (2013) "Return Predictability of Turkish Stocks" *EMFT* 49(5)
Ocak 1997 – Temmuz 2011; beta, total/idiosyncratic volatility, **book-to-market** predictive — B/M en güçlü; **large-cap stocks en az predictable**. **BIST katkısı:** BIST OS pre-filter'ında likidite gereği large-cap yoğunluğu → small-cap'lere genişletme (RR-005 custody data triangulasyon) IC'yi artırabilir. (Tam coefficient tabloları paywall arkasında.)

### Gokcen, U. (2023) "Factor Investing in the Turkish Equity Market" SSRN 4588551
BIST üzerinde size, B/M, 12-mo momentum, volatility, gross profitability. Verbatim: *"Value is the strongest and the most robust factor, generating spreads of 19% annualized over growth in the full sample, and 14% in the latter part. A multifactor portfolio based on the composite z-scores of the stock characteristics delivers an alpha of 20% (in dollars) relative to the emerging markets index and a Sharpe ratio of 0.82."* **BIST katkısı:** Value faktörünün BIST'te en güçlü ampirik kanıt; L3 KAP layer'ında fundamental value sinyalleri (P/B, P/E) önceliklendirilmesine destek.

### Atak, A. (2023) "Exploring the sentiment in Borsa Istanbul with deep learning" *Borsa Istanbul Review* 23(Suppl 2):S84-S95, doi:10.1016/j.bir.2023.12.010
1998-2022 BIST disclosure'lar; transformer-tabanlı sentiment + system-GMM. IC raporlanmıyor ancak Türkçe finansal NLP feasibility kanıtı. **BIST katkısı:** RR-008 hybrid yaklaşımı için empirik öncül; L4 sentiment için aspect-bazlı (polarity-ötesi) NLP önerisine destek.

---

## 6. KISITLAR & CAVEAT'LAR

1. **BIST 50-100 ticker scope'unda IC ölçüm limitleri:** ABD literatürü 3000+ stock varsayar. IC=0.05 için t-stat 75 ticker × 120 gün = 9000 gözlemde ~3.4 (anlamlı); 30 × 60 = 1800'de ~1.7 (sınırda). **Eylem:** N<60d veya cross-section<30 günlerde IC raporlanmaz, eşik altında flag'lenir.

2. **Cross-section sample size:** Sektör-içi IC ~5-7 ticker/sektör → neredeyse imkansız. **Eylem:** Sektör nötralizasyon yalnızca `group_adjust=True` ile forward return demean.

3. **ABD literatür extrapolation limitleri:** HLZ t > 3.0 hurdle US 1967-2014 datasından kalibrasyon. BIST için muhafazakar olabilir (daha az factor zoo basıncı) ama TR enflasyon/kur volatilitesi bias kaynağı; **t > 2.5 alternatif tartışılabilir, varsayılan t > 3.0**.

4. **Minimum 60 işlem günü zorunlu:** Layer weight güncelleme (τ=0), ICIR raporlama, decay slope tahminleri 60d'den önce yapılmaz. Yapılabilir: günlük IC snapshot, schema testleri.

5. **Re-calibration trigger'ları:** (a) son 60d ICIR < 0; (b) CB-002 rejim flag; (c) kümülatif IC −2σ kırılması; (d) yeni layer ekleme (RR-008/RR-006); (e) >180 gün geçmiş ve τ_eff güncelleme; (f) survivorship liste güncellemesi.

6. **Tomtosov (2024) Türkiye'yi içermiyor.** Gokcen (2023) ve Atilgan et al. (2013) BIST-spesifik referansların belkemiği. Framework önerileri BIST'e *parametrize* edilmiştir ancak *empirik olarak BIST'te kanıtlanmış değildir* → 60+120 gün gözlem zorunluluğu kritik.

7. **Survivorship & data kalitesi:** yfinance BIST tickers'ında bilinen NaN/gap problemleri. KAP delisted listesi entegrasyonu manuel; Borsa İstanbul resmî `BIST Stock Indices Codes and Initial Values` referans.

8. **Risk-free rate** (TCMB PPK 27 Nisan 2026: bir hafta vadeli repo ihale faizi %37'de sabit; trading-economics doğrulamalı). Günlük rf ≈ (1.37)^(1/250) − 1 ≈ %0.126. Yıl içi rf değişikliği DSR'de noise üretebilir; rolling rf önerilir.

9. **L4 SUSPENDED (RR-008 hybrid'e geçişte):** Mevcut framework'te L4 = 0; RR-008 tamamlandığında t > 3.0 hurdle'ı geçmesi gerek; aksi W_PRIOR[3] = 0 kalır ve diğer layer'lar yeniden normalize edilir.

10. **L6 Risk/Kelly = 0.03 statik prior:** Risk layer'ı ICIR-tabanlı kalibre edilemez (alfa sinyali değil, pozisyon büyütücü). Bayesian update L6'ya uygulanmaz; diğer 5 layer 0.97 toplamında yeniden ölçeklenir.

11. **Multi-model parametre selection bias:** Pre-registration zorunlu — kombinasyonlar kod commit'inde sabit; sonradan "iyi çıkanı" seçmek yasak. DSR ile N_trials raporlanır.

12. **Retail ölçek (<500K TL) transaction cost realitesi:** Garanti BBVA Yatırım komisyon tarifesi: "azami %0,105 (binde 1,05) oranında komisyon" (tek yön); Ziraat Yatırım internet kanalı "binde 1,50 + BSMV" tek yön. Round-trip komisyon %0.21-0.315 aralığı; BSMV (%5 komisyon üzerinden) ve bid-ask spread eklenince **gerçek round-trip cost %0.25-0.40 aralığında** — bu rapor önceki taslakta %0.10-0.20 söylüyordu, **düzeltildi**. Algoritmik/yüksek hacim indirimleriyle %0.10'a yakın seviye mümkün (hisse.net, "Borsa İstanbul'da bakım ve komisyon ücretleri 2026," Mayıs 2026). **Net IC formülü:** net_IC ≈ gross_IC × (1 − turnover × 0.003). Yüksek turnover × düşük gross_IC = net negatif riski.

---

## RECOMMENDATIONS — Aşamalı Eylem Planı

**Faz 1 (Sprint mevcut, 0-30 gün):**
- `signal_logger.py` panel formatına revize edilsin; SQLite şema kurulsun (Bölüm 4).
- yfinance forward return + sektör eşleme (`groupby` BIST sector indices) tabloları doldurulsun.
- `delisted_tickers` manuel olarak son 5 yıl için KAP'tan çekilsin.
- Günlük `compute_daily_ic` cron job production'a alınsın; çıktı `ic_history`'ye yazılsın.

**Faz 2 (30-60 gün):**
- İlk ön IC istatistikleri (deneysel, anlamsız t-stat'lar bekleniyor).
- BH-FDR pipeline doğrulanır (m=12 panel).
- Dashboard MVP (Streamlit) — heatmap + rolling IC çizgisi.

**Faz 3 (60-120 gün — IC framework "live"):**
- İlk Bayesian weight update (τ=0.20).
- Sektör-içi vs raw IC dispersion raporu.
- Decay slope ilk değerlendirmesi.

**Faz 4 (120-365 gün):**
- τ=0.50, sonra 0.80 ile weight'ler IC'ye daha bağımlı hale gelir.
- RR-008 hybrid sentiment L4 olarak entegre edilir; t > 3.0 hurdle uygulanır.
- DSR ile multi-model kombinasyonu raporlanır.

**Faz 5 (365+ gün):**
- τ=0.95; statik prior neredeyse tamamen IC-tabanlı kalibrasyona yerini bırakır.
- RR-011 (önerisi): XGBoost IC tahmini ile dinamik weight (Li & Zhang 2018 metodu).

**Re-calibration / staj eşikleri:**
- ICIR < 0 (60d) → otomatik prior'a geri dönüş (τ=0).
- Decay slope < −0.002/gün → layer "review".
- CB-002 rejim flag → tüm rolling pencereler resetlenir, yeni 60d başlatılır.
- DSR < 0.95 yeni model kombinasyonu için → reddet, kombinasyon kaydedilir ama production'a alınmaz.

---

## CAVEATS (Özet Tekrar)

- Bu framework akademik literatürün BIST'e *parametrize* edilmesidir; empirik BIST validasyonu mevcut değildir (Tomtosov 2024 Türkiye'yi içermez; Atilgan 2013 ve Gokcen 2023 kısmi ampirik destek sağlar).
- IC'lerin BIST'te ABD'ye göre daha gürültülü olması beklenir (kalın kuyruk, rejim kırılmaları, TCMB sürprizleri).
- 60 günlük minimum birikme süresi MUTLAK — öncesinde statik prior'larla devam edilmeli; "şu an çalıştırıp sonuca bakmak" data snooping olur.
- t > 3.0 hurdle US standartlarından alınmış muhafazakar bir kalibrasyon; BIST'te (daha az factor zoo) t > 2.5 tartışılabilir ama varsayılan 3.0 olmalı.
- Transaction cost (%0.25-0.40 round-trip retail komisyon + BSMV + spread) net IC hesabına dahil edilmelidir; net negatif olabilecek senaryolar mevcuttur.
- RR-010 sürümü 1.0; builder'a teslim edilebilir. Implementation pseudocode bölümü doğrudan kodlanabilir.

*Sonraki sürümler için açık konular:* L6 Risk/Kelly'nin Bayesian framework'üne entegrasyonu; Maximally Diversified weight (kovaryans tabanlı); XGBoost ICR tahmin (RR-011 hedef).