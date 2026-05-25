# RR-017 · HMM Regime Detection — BIST Kalibrasyon ve Aktivasyon Roadmap

**Sistem:** BIST OS Trading System (Python, yfinance, EVDS API, KAP, long-only)
**Status:** ENABLE_HMM_WEIGHTS = False · AG-001 bekleniyor (>=90 gün OOS + Sharpe iyileşmesi ≥ +0.15)
**Bağlam:** RR-003 (4-aşamalı yol haritası — Aşama 1) · RR-012/013/015/016 yama disiplini
**Tamamlayıcılık:** HMM "rejim NE der" · RR-016 vol-targeting "rejim İÇİNDE ne kadar" · DD soft gate "pozisyon NASIL koru"
**CB-002 ile fark:** CB-002 continuous macro_score (soft floor) — HMM discrete state (MASTER_WEIGHTS değiştirir). Interaction matrix §11.

---

## TL;DR (§1)

> Hedef okuyucu: Cagan + Orchestrator. Builder §5–§12'yi okur.

- **Karar:** 3-state Gaussian HMM (Bull/Neutral/Bear). RR-003 §1 gerekçesi + 3 bağımsız argüman (sticky regime, Türk literatür kümesi, alternatiflere konum) §3'te.
- **Feature seti:** Tier 1 = BIST 100 log-return, 20-gün realized vol, USD/TRY log-return, Türkiye 5Y CDS değişimi. Tier 2/3 ablation amaçlı.
- **Alpha beklentisi:** Wang–Lin–Mikhelson (2020, *J. Risk and Financial Management* 13(12):311, DOI 10.3390/jrfm13120311) S&P 500'de 3-state HMM rotation modelinin Eylül 2017 – Nisan 2020 OOS penceresinde "higher annualized returns" ve "both a higher Sharpe ratio and a higher Treynor ratio when compared to the rest of the other models" verdiğini raporlar; **spesifik yıllık abnormal-return rakamı raporun makale içi Table 5'inde olup özetten doğrulanamadı**. Critic CB-002 "8–10 puan/yıl" finding'i BIST için **post-OOS doğrulanmadan kabul edilmez**.
- **Aktivasyon timeline (iki paralel senaryo):** Erken Q3 2026 (Şubat OOS başlangıç + 180g), Geç Q4 2026 (Mayıs OOS başlangıç + 180g). **Cagan açık soru:** Alpha Attribution Phase 1 IC dashboard OOS veri üretimine ne zaman başladı? Resmi log yoksa **muhafazakar Kasım 2026 varsayım**.
- **Bugünden iş YOK:** ENABLE_HMM_WEIGHTS=False, MASTER_WEIGHTS değişmez. Bu rapor AG-001 günü Builder'ın elinde bulunması gereken belgedir.

---

## §2. Akademik Temel + BIST Literatürü

> Hedef okuyucu: Cagan & Builder.

**Akademik dayanak:**
| Çalışma | Katkı | Kaynak |
|---|---|---|
| Hamilton (1989) | MS regime-switching pioneer | *Econometrica* 57(2):357–384 · DOI 10.2307/1912559 |
| Hamilton & Susmel (1994) | MS-ARCH; 2–4 rejim, Gauss & Student-t | *J. Econometrics* 64(1-2):307–333 · DOI 10.1016/0304-4076(94)90067-1 |
| Ang & Bekaert (2002) | Faiz rejim değişimi; OOS-üstün | *J. Business & Econ. Statistics* 20(2):163–182 · https://www.tandfonline.com/doi/abs/10.1198/073500102317351930 |
| Bulla & Bulla (2006) | Hidden Semi-Markov; slow autocorr | *CSDA* 51(4):2192–2209 · DOI 10.1016/j.csda.2006.10.014 |
| Mamon & Elliott (2007) | "HMM in Finance" — kitap referansı | Springer ISBN 978-0-387-71081-5 |
| Guidolin & Timmermann (2008) | Rejim altında int'l allocation; "rejim ihmali = diversifikasyon yanılgısı" | *RFS* 21(2):889–935 · DOI 10.1093/rfs/hhn006 |
| Nystrup vd. (2015, 2018) | Sürekli zamanda HMM; dinamik portföy | *Quant. Finance* 15(9), 18(1) |
| Aydınhan-Kolm-Mulvey-Shu (2024) | Statistical Jump Model — HMM hassasiyetini jump penalty ile çözer | *Annals of OR* (forthcoming) · SSRN 4556048 · DOI 10.1007/s10479-024-06035-z |
| Shu-Yu-Mulvey (2024) | JM ile downside reduction; US/DE/JP 1990–2023 OOS, HMM ve buy-and-hold'a karşı üstün | arXiv:2402.05272 · DOI 10.1057/s41260-024-00376-x |
| López de Prado (2018) | Combinatorial Purged CV | *Advances in Financial ML*, Wiley ISBN 978-1119482086 |

**BIST literatürü (Türkçe):**
| Çalışma | Bulgu | Kaynak |
|---|---|---|
| Şenol (2020) | BIST 100 (4 Ocak 2010 – 30 Aralık 2019), MS(2)-AR, 2 rejim. Verbatim: *"1. rejim ayı piyasasını, 2. rejim ise boğa piyasasını temsil etmektedir. 2. rejimde ortalama kalma süresi (64) 1. rejimde ortalama kalma süresinden (11) daha yüksektir."* Birim çalışma özetinde açıkça verilmemiş (gün mü ay mı). USD/TRY 1. rejimde etkili, 2 yıllık tahvil her ikisi. | *Erciyes ÜSBE Dergisi* Sayı 49, ss. 246–256 · https://dergipark.org.tr/en/pub/erusosbilder/article/841936 |
| Samırkaş (2021) | BIST 100 (2010–2020) günlük log getiri; MS(2)-AR(0) ve TVTP-MS(2)-AR(0). TVTP modelinde verbatim: *"…boğa piyasası rejiminde kalma olasılığı … %96,20 olmuştur. Ayı piyasası rejimindeyken tekrardan ayı piyasasında kalma olasılığı ise yaklaşık %86'dır. … bir sonraki dönemde ayı piyasası rejimine geçme olasılığı yaklaşık %3,8 iken ayı piyasası rejiminden bir sonraki dönemde boğa piyasası rejimine geçme olasılığı yaklaşık %13,9."* MS(2)-AR(0) için ortalama sojourn: boğa **7.75 gün**, ayı **32.64 gün**. | İTOBİAD 10(3):2227–2249 · DOI 10.15869/itobiad.880539 |
| Wang-Lin-Mikhelson (2020) | 3-state Gaussian HMM (Bull/Bear/Kangaroo), S&P 500 ETF 2007–2017 IS / 2017–2020 OOS. Faktör modellere göre HMM rotation üstün — verbatim: *"both a higher Sharpe ratio and a higher Treynor ratio when compared to the rest of the other models."* **BIST verisi içermez** (görev brief'i bu konuda düzeltildi). | *JRFM* 13(12):311 · DOI 10.3390/jrfm13120311 |
| Cemal Öztürk (2025) | 2-rejim MRS, S&P 500 (2008–2024); BIST'e uygulama YOK; metodolojik referans. | Eğitim Yayınevi kitap bölümü · SSRN 5206522 |

**Karşılaştırma:** Türk literatüründe 2-state MS dominant; 3-state HMM Türkçe BIST çalışmalarında seyrek — §4 BIST için 3-state'in pratik gerekçesini kurar.

---

## §3. Neden HMM? (RR-003 referans + 3 bağımsız argüman)

> Hedef okuyucu: Cagan + Builder. RR-003 §1 Aşama 1 HMM gerekçesini detaylı verir (düşük parametre, hmmlearn olgunluğu, finansal HMM literatür, sklearn API). RR-017 bunu tekrar etmez; 3 ek argüman:

**3.1 Sticky regime — BIST'in deneysel imzası.** Samırkaş (2021, TVTP-MS) verbatim: *"BIST getiri serisinin boğa piyasası rejimindeyken bir sonraki dönemde tekrardan boğa piyasası rejiminde kalma olasılığı … %96,20 olmuştur. Ayı piyasası rejimindeyken tekrardan ayı piyasasında kalma olasılığı ise yaklaşık %86'dır."* HMM transition matrix diagonal'ı tam bu yapıyı modeller → uzun sojourn, düşük false-positive geçiş. CB-002 "64 ay bull / 11 ay bear" finding'i **Şenol (2020) sayısal değerleridir; orijinal çalışma birim "ay" mı "gün" mü açıkça belirtmemiş**, Samırkaş günde 7.75/32.64 raporlar — Builder §3.1 Validation not'unda bu birim ayrımını belgelemeli.

**3.2 Türk literatür dominant choice.** Türk BIST regime çalışmaları 2-state MS'e ağırlık veriyor; 3-state HMM seyrek. Bu **boşluk fırsat** (granular Bull/Neutral/Bear) ama **risk** (overfit). RR-017 §4 BIC ile doğrulama yaptırır.

**3.3 Alternatiflere konum.** **MS-GARCH** (Hamilton-Susmel 1994) parametre patlaması; hiperenflasyon altında local maxima. **TAR** rejim ekstra threshold gerektirir; multi-feature zor genişler. **HSMM** sojourn esnek ama R-paketi (`hsmm`), Python entegrasyonu zayıf. **Statistical Jump Model** (Aydınhan vd 2024, Shu-Yu-Mulvey 2024) HMM'in fazla-hassasiyet sorununu jump penalty ile çözer; **Faz 5'te (§15.5) review zorunlu**.

Verbatim Shu-Yu-Mulvey (2024, arXiv:2402.05272): *"the statistical jump model (JM) … distinguishes itself from traditional Markov-switching models by enhancing regime persistence through a jump penalty applied at each state transition. … consistent outperformance of the JM-guided strategy in reducing risk metrics such as volatility and maximum drawdown, and enhancing risk-adjusted returns like the Sharpe ratio, when compared to both hidden Markov model-guided strategy and the buy-and-hold strategy."* Test piyasaları: US, Germany, Japan, 1990–2023 (BIST yok).

---

## §4. State Sayısı Kararı

> Hedef okuyucu: Builder.

**4.1 Trade-off:**
| Boyut | 2-state | 3-state | 4-state | 5-state |
|---|---|---|---|---|
| Param sayısı (4 feature, diag) | 18 | 30 | 44 | 60 |
| Türk literatürde | Dominant | Sınırlı | Yok | Yok |
| BIST yorum | Bull/Bear yeterli, Neutral yok | Bull/Neutral/Bear | + Transition | Granular ama overfit |
| Overfit (BIST ~15y) | Düşük | Orta | Yüksek | Çok yüksek |
| RR-017 önerisi | Baseline | **Başlangıç** | Ablation | YASAK |

**4.2 BIC karşılaştırma (sanity test, kavramsal):**
```python
def select_n_states(X_train, max_states=5):
    """BIC monoton azalmıyorsa overfit eşiği bulundu.
    Karar: ΔBIC<10 → küçük state seç (Kass-Raftery 1995 Bayes Factors)."""
    results = {}
    for n in range(2, max_states+1):
        m = GaussianHMM(n_components=n, covariance_type="diag",
                        n_iter=200, tol=1e-3, random_state=42)
        m.fit(X_train)
        ll = m.score(X_train)
        k = n*n + 2*n*X_train.shape[1] - 1
        bic = -2*ll + k * np.log(len(X_train))
        results[n] = {"ll": ll, "bic": bic}
    return results
```
Beklenti: 2→3 BIC↓; 3→4 marjinal; 4→5 BIC↑.

**4.3 Öneri:** 3-state başlangıç + 4-state ablation post AG-001. 5-state YASAK.

**4.4 Builder Validation Checklist — State sayısı:**
- [ ] BIC tablosu 2/3/4/5 üretildi mi?
- [ ] Persistence (diag transmat) her state raporlandı mı?
- [ ] Walk-forward'da state etiketleri stabil (permutation çözüldü) mi?
- [ ] Neutral state ekonomik anlam (vol orta, return ≈ 0) taşıyor mu?
- [ ] "Neden 3, neden 4 değil" docstring'de tek paragraf mevcut mu?

---

## §5. Feature Engineering

> Hedef okuyucu: Builder.

**5.1 Tier 1 (minimum, production başlangıç):**
```
- BIST 100 log return (daily)
- 20-day realized volatility
- USD/TRY log return
- Türkiye 5Y CDS daily change
Boyut: 4
```
Gerekçe literatür-türevi: Şenol (2020) BIST + USD/TRY + tahvil faizi; Wang-Lin-Mikhelson (2020) return + vol. CDS: Adusobed (2023, https://dergipark.org.tr/en/pub/adusobed/issue/81044/1345429) Toda-Yamamoto'da BIST↔CDS↔exchange iki-yönlü nedensellik buldu.

**5.2 Tier 2 (ablation):** Tier 1 + (TCMB 1-haftalık repo delta, yabancı net akış USDmn, VIX).

**5.3 Tier 3 (research):** Tier 2 + (Brent log return, DXY log return, TLREF spread).

**5.4 Diagnostics:** VIF<5, ADF p<0.05 (log-return form zorunlu), KPSS rolling 6-ay structural break flag, Granger pairwise lag 5.

**Bilinen sorunlar:** USD/TRY ↔ CDS yüksek korel (β ≈ 0.7–0.85). Raw seviyeler kesin non-stationary → log/change form zorunlu. TLREF spread Mart 2023 sonrası rejim değişti (Şimşek programı sıkı para) → §6.5 structural break.

**5.5 Hiperenflasyon handling:** TÜFE serisi yüksek enflasyon dönemine girdi: TÜİK Aralık 2021 yıllık TÜFE %36.08, ENAG aynı dönem E-TÜFE %82.81; TÜİK zirvesi Ekim 2022'de %85.51. ENAG değerleri TÜİK'in çok üstünde devam etti; **"her iki seri >30%" yalnızca Aralık 2021 sonrası genel ifade**, kesin doğru aralık TÜİK %36–85.51 (Ara 2021 – Eki 2022) ve sonrasında %44.38 (Ara 2024) → %30.89 (2025), ENAG paralel olarak daha yüksek. Nominal BIST non-stationary; RR-013 reel/dolar paralel kolon. RR-017 önerisi: HMM log-return üzerinde (seviye değil), 20-gün realized vol kısa pencere, Mart 2023 sonrası re-calibration.

**5.6 Normalization:** Z-score rolling 180 gün (≈ 9 ay = ~1 dönemsel cycle), lookahead-free:
```
z_t = (x_t - mean(x_{t-180:t-1})) / std(x_{t-180:t-1})
```

**5.7 Builder Validation Checklist — Feature:**
- [ ] Tier 1 her feature ADF p<0.05 (log-return form) mu?
- [ ] Pairwise VIF<5 mi?
- [ ] Rolling 180-gün z-score lookahead-free mi?
- [ ] Mart 2023 pre/post Kolmogorov-Smirnov dağılımları farklı mı?
- [ ] Eksik veri forward-fill max 3 gün, sonra drop mu?

---

## §6. Kalibrasyon Metodolojisi

> Hedef okuyucu: Builder.

**6.1 hmmlearn baseline (v0.3.x, https://hmmlearn.readthedocs.io/en/stable/):**
```python
from hmmlearn.hmm import GaussianHMM
# Kavramsal — production refine gerektirir
model = GaussianHMM(
    n_components=3, covariance_type="diag", n_iter=200, tol=1e-3,
    init_params="stmc", params="stmc", random_state=42,
    min_covar=1e-3, algorithm="viterbi",
)
```
`covariance_type` seçimi: `diag` default + önerilen (Tier 1 küçük); `full` overfit; `tied`/`spherical` esneksizlik.

**6.2 Initial state prior:** `startprob_init = [0.7, 0.2, 0.1]` (Bull-dominant, Samırkaş 2021).

**6.3 Sticky transition prior:**
```
transmat_init = [
    [0.95, 0.04, 0.01],   # Bull persistence
    [0.10, 0.80, 0.10],   # Neutral
    [0.05, 0.05, 0.90],   # Bear persistence
]
```
Justification: Samırkaş (2021) sabit-geçiş MS(2)-AR(0) modeli için P(bull→bull)≈%87 / P(bear→bear)≈%97; TVTP modeli için %96.20 / %86. Prior'lar bu iki çalışmanın geometrik ortasından; EM 200 iterasyonda data'ya göre günceller.

**6.4 Walk-forward:** Training 36 ay rolling, Validation 6 ay, Test 6 ay OOS, Re-calibration her 3 ay. **CPCV ek katmanı:** López de Prado (2018) embargo 5 gün + label-overlap purging (https://en.wikipedia.org/wiki/Purged_cross-validation).

**6.5 Mart 2023 structural break:** 3 Haziran 2023 Mehmet Şimşek Hazine ve Maliye Bakanı atanması → TCMB politika faizi %8.5'ten kademeli olarak Mart 2024'te zirve %50'ye yükseldi. TCMB Basın Duyurusu 2024-14 (Mart 2024) verbatim: *"Para Politikası Kurulu (Kurul), politika faizi olan bir hafta vadeli repo ihale faiz oranının yüzde 45'ten yüzde 50 düzeyine yükseltilmesine karar vermiştir."* Faiz Kasım 2024'e kadar %50'de tutuldu; ilk indirim Aralık 2024'te %47.5 (TCMB Duyuru 2024-70). RR-017 önerisi: 2023 Haziran pre/post ayrı modeller; post 6-ay warm-up; rolling KPSS auto-flag.

**6.6 Sanity testleri:**
```python
assert model.monitor_.converged, "EM converge etmedi (n_iter↑ veya tol gevşet)"
assert (np.diag(model.transmat_) > 0.6).all(), "Sticky regime bozuldu"
assert means[bull_idx] > means[neutral_idx] > means[bear_idx], "State sıralama bozuk"
assert vols[bear_idx] > vols[bull_idx], "Bear vol Bull'dan düşük → anomali"
```

**6.7 Builder Validation Checklist — Kalibrasyon:**
- [ ] hmmlearn ≥0.3.0 (`requirements.txt`)?
- [ ] `random_state=42` tüm runs?
- [ ] Training 36 ay > min veri?
- [ ] EM converge (monitor_.converged True)?
- [ ] State permutation deterministik mapping (§12.2) ile çözüldü mü?

---

## §7. Validation Framework

> Hedef okuyucu: Builder + Cagan.

**7.1 In-sample metrikler:**
| Metrik | Hesap | Eşik | Sanity |
|---|---|---|---|
| Log-likelihood | `model.score(X_train)` | baseline (single-Gauss) +%5 | LL büyük = data açıklanmış |
| AIC | -2LL + 2k | düşük iyi | k = state + emission params |
| BIC | -2LL + k·log(N) | minimum | büyük N'de conservative |
| State persistence | mean diag transmat | > 0.85 | Sticky kanıt |

**7.2 OOS metrikler:**
| Metrik | Eşik AG-001 |
|---|---|
| OOS Sharpe (HMM) − OOS Sharpe (static) | ≥ +0.15 |
| Mean Viterbi confidence | ≥ 0.65 |
| State realized duration | 30–250 trading days |
| Crisis lag (kriz tarihi − HMM sinyal) | ≤ 2 ay (≈42 trading day) |

**7.3 Combinatorial Purged CV (López de Prado 2018):** N=6 grup, k=2 test → C(6,2)=15 path → ampirik Sharpe dağılımı → Deflated Sharpe Ratio (Bailey & López de Prado 2014). Eşik DSR>0 (one-sided p<0.05).

**7.4 Regime persistence test:** Geometrik beklenti `E[D_i] = 1 / (1 - P_ii)`. KS test realized vs expected.

**7.5 Crisis period test:** §8'de 5 dönem, hindsight bias açıkça flag.

**7.6 Builder Validation Checklist — Validation:**
- [ ] LL > baseline +%5?
- [ ] BIC k-state minimum?
- [ ] CPCV PBO < 0.5?
- [ ] DSR > 0 (one-sided p<0.05)?
- [ ] 5 kriz için lag ≤ 2 ay?

---

## §8. Crisis Period Kavramsal Simülasyon

> Hedef okuyucu: Builder + Cagan. **HINDSIGHT BIAS UYARISI:** Tüm "real-time HMM state" yorumları **retrospektif simülasyon**; gerçek zamanlı kalibre edilmiş model söz konusu değil. Her kriz için açıkça retrospektif olduğu işaretleniyor.

### 8.1 Ağustos 2018 — TRY krizi (Brunson)

**BIST hareketi (özet, detay RR-016 §3.1):** USD/TRY 4.8 → 7.24 (~%50, 6 hafta); BIST 100 nominal düşüş >%20 kısa pencerede; **Türkiye 5Y CDS yıl başı 165 bps → 13 Ağustos 2018 zirve 586 bps** (IHS Markit / Reuters, 13 Aug 2018 verbatim: *"Five-year credit default swaps (CDS) leapt 135 basis points (bps) from Friday's close to 586 bps according to IHS Markit data"*; Aralık 2018 research brief paralel: *"The CDS spreads have widened from 165 bps at the beginning of the year to a peak of 563 bps on August 13th"*). 10 Ağustos "Kara Cuma" BIST −%7.95, USD +%17.61 (https://eksisozluk.com/10-agustos-2018-ekonomik-krizi--5751171).

**HMM-spesifik analiz (retrospektif simülasyon — real-time DEĞİL):**
- **Öncesi (Mayıs–Temmuz 2018):** Tier 1 üzerinde muhtemel Neutral state (vol artıyor, USD/TRY drift up); Bull olasılığı Temmuz sonu 0.5 altına düşer.
- **Kriz haftası (10 Ağustos):** Viterbi Bear'a kesin geçiş, ama **muhtemelen 5–10 gün lag** ile. CDS feature (165→586 bps) kritik tetik.
- **Sonrası:** Eylül 2018 TCMB +625 bp (24%) → Bear olasılığı yavaş düşer; Neutral'e geçiş ~Q4 2018.

**Structural break vs state transition:** **State transition.** Politika çerçevesi değişmedi; model parametreleri korunmalı, sadece transition matrix update.

**Builder Validation Checklist — 2018 TRY krizi:**
- [ ] HMM 2018 Ağustos haftasında Bear geçişi ≤42 trading day içinde tespit etti mi?
- [ ] CDS feature çıkarılırsa lag artıyor mu (Tier 1 ablation)?
- [ ] Geçiş confidence min 0.55 üzerinde mi?
- [ ] Recovery (Q1 2019) timing realistik (1–2 ay) mı?
- [ ] Real-time vs retrospektif fark belgelendi mi (docstring uyarısı)?

### 8.2 Mart 2020 — COVID

**BIST hareketi (özet, detay RR-016 §3.2):** 3 hafta içinde BIST −%28.36 (BorsaGündem: https://www.borsagundem.com.tr/borsa-istanbulda-tarihi-dususler), Mart sonu V-recovery başladı.

**HMM-spesifik analiz (retrospektif):**
- **Öncesi (Ocak–Şubat 2020):** Neutral, VIX bölgesi alt. Tier 1 sadece BIST sinyaliyle COVID öncesi sürpriz yakalayamaz (Türkiye ilk vaka 13 Mart). Tier 2 VIX feature 21 Şubat 2020 sonrası uyarı.
- **Kriz pencere (9–18 Mart 2020):** Hızlı Bear geçiş, **V-recovery riski:** HMM Bear'a girer, 3 hafta sonra recovery başladığında hâlâ Bear'da olabilir → false-positive defensive 2–3 ay.
- **Sonrası:** Ultra-gevşek politika (Naci Ağbal Kasım 2020); yıl sonu nominal BIST %29 getiri (Anadolu Ajansı: https://www.aa.com.tr/tr/ekonomi/borsa-istanbulda-2020-boyle-gecti/2095448). HMM Bull'a dönüş ~Haziran-Temmuz 2020.

**Structural break vs state transition:** **State transition.**

**V-recovery handling kritik:** §13.5 — `manual_override_flag`; V-shape sırasında 7-gün MA smoothing.

**Builder Validation Checklist — 2020 COVID:**
- [ ] HMM Mart 2020 ilk yarısında Bear'a geçti mi?
- [ ] V-recovery sırasında (Nis-May 2020) Bear'da kalış süresi? >3 ay = false-defensive flag.
- [ ] VIX (Tier 2) erken-uyarı 21 Şub 2020 öncesi/sonrası fark sağladı mı?
- [ ] Manuel override path test edildi mi?
- [ ] Recovery'de transaction cost (RR-015) hesaba katıldı mı backtest'te?

### 8.3 Mart/Haziran 2023 — Şimşek atanma / Politika değişikliği

**BIST hareketi (özet, detay RR-016 §3.3):** 3 Haziran 2023 Şimşek Hazine; TCMB politika faizi %8.5'ten Mart 2024 zirvesi %50'ye (TCMB Duyuru 2024-14); Aralık 2024'te ilk indirim %47.5 (Duyuru 2024-70). BIST USD bazlı uzun düşüş 2023 başından itibaren konsolide.

**HMM-spesifik analiz (retrospektif):**
- **Öncesi (Q1 2023):** TLREF spread genişliyor (heterodox son aylar), Bear-leaning Neutral. Deprem (6 Şubat 2023) ek şok.
- **Kriz pencere:** 3 Haziran 2023 Şimşek atanması **politika çerçevesi değişimi** — parametreler güncel rejimi yansıtmaz. **Structural break, state transition değil.**
- **Sonrası (Q3 2023 – 2024):** Yeni ortodoks dönem, KKM çözümü, kademeli rezerv toparlanma. Şimşek (T24: https://t24.com.tr/haber/...,1252117): *"Rezervlerimiz mart ortasında 170 milyar doların üzerindeydi."*

**Structural break vs state transition:** **STRUCTURAL BREAK.** §6.5 — pre/post 2023 Haziran ayrı modeller; parametre miras yasak.

**Builder Validation Checklist — 2023 politika değişikliği:**
- [ ] Pre/post 2023 Haziran ayrı modeller fit edildi mi?
- [ ] KPSS rolling 6-ay TLREF spread için H0 reddediliyor mu (structural break sinyali)?
- [ ] Post-Haziran 2023 model warm-up 6 ay kullandı mı?
- [ ] State persistence pre/post karşılaştırması yapıldı mı?
- [ ] "Structural break = manual flag + re-fit" prosedürü docstring'de yazılı mı?

### 8.4 Mayıs 2023 — Seçim şoku

**BIST hareketi (özet, detay RR-016 §3.4):** 14 Mayıs 2023 ilk tur, 15 Mayıs açılış BIST 100 −%6.38 (4,489.58'e geriledi), endeks-bazlı devre kesici (Sözcü: https://www.sozcu.com.tr/2023/finans/secim-sonucuna-dair-piyasada-hangi-yorumlar-yapiliyor-7684904/). İki hafta volatilite, 28 Mayıs ikinci tur.

**HMM-spesifik analiz (retrospektif):**
- **Öncesi (Nis-May 2023):** Anketler Millet İttifakı önde → Bull-leaning Neutral.
- **Kriz pencere (15 Mayıs 2023):** Tek günlük devre-kesici şok — **HMM bu kadar kısa pencereyi yakalayamaz** (20-gün vol smoothing nedeniyle). Sinyal ~1 hafta gecikme.
- **Sonrası:** 28 Mayıs 2. tur, 3 Haziran Şimşek (§8.3).

**Structural break vs state transition:** **Kısa-süreli vol spike** — state transition formal tetiklenmeyebilir. HMM bu tip 1-hafta-içi olayları yakalamak için tasarlanmamış — RR-016 vol-targeting daha uygun katman.

**Builder Validation Checklist — 2023 Mayıs seçim:**
- [ ] HMM Mayıs 2023 haftasında state değiştirdi mi? Lag kaç gün?
- [ ] 14 Mayıs öncesi/sonrası 5-gün pencerede vol/return Z-score outlier flag tetikledi mi?
- [ ] Manual override (kısa-pencere şok) test edildi mi?
- [ ] "Kısa pencere kör nokta" docstring'de mevcut mu?
- [ ] RR-016 vol-targeting tetikleyici ile fark kontrast edildi mi?

### 8.5 Mart 2024 — Yerel seçim

**BIST hareketi (özet, detay RR-016 §3.5):** 31 Mart 2024, CHP İstanbul/Ankara galip; kısa vol spike, piyasa Şimşek programına devamı algıladı.

**HMM-spesifik analiz (retrospektif):**
- **Öncesi:** TCMB Mart 2024'te politika faizi %45 → %50 zirvesi (TCMB Duyuru 2024-14); piyasa sıkı politikayı fiyatlıyor.
- **Kriz pencere (1–2 Nisan 2024):** Kısa vol artışı, gün içinde toparlandı — HMM **muhtemelen state değişimi tetiklemedi**.
- **Sonrası:** Q2 2024 disinflation rally hızlandı.

**Structural break vs state transition:** **Non-event** (HMM açısından) — sadece bir günlük vol spike.

**Builder Validation Checklist — 2024 Mart yerel:**
- [ ] HMM bu pencerede state değiştirmediğini doğrula (false-positive yok mu)?
- [ ] Değiştiyse = overfit işareti, investigation.
- [ ] Vol spike RR-016 vol-targeting tarafından handle edildi mi?
- [ ] "HMM sessiz doğru davranış" benchmark olarak tutuldu mu?
- [ ] BIST realized vol Mart 2024 vs Mayıs 2023 karşılaştırması belgelendi mi?

### 8.6 5-kriz özet tablosu

| Kriz | Tür | HMM beklenen lag | RR-017 mekanizması | Manuel override |
|---|---|---|---|---|
| 2018 Ağu TRY (CDS 165→586 bps) | State transition | 5–10 gün | CDS (Tier 1) | Hayır |
| 2020 Mar COVID | State transition | 3–7g giriş, 30+g çıkış | Tier 2 VIX | **EVET (V-recovery)** |
| 2023 Haz politika | **Structural break** | N/A | Re-calibration | **EVET (manuel re-fit)** |
| 2023 May seçim | Kısa-pencere şok | HMM yakalayamaz | RR-016 vol-targeting | Opsiyonel |
| 2024 Mar yerel | Non-event | (tetiklenmez) | RR-016 yeterli | Hayır |

---

## §9. AG-001 Aktivasyon Detaylı

> Hedef okuyucu: Cagan (karar günü) + Builder.

**9.1 4 ana kriter:**

**a) Veri:** Min 90 gün OOS (mevcut AG-001); önerilen 180; cross-section 50+ ticker × 180 gün.

**b) Model fit:** LL > baseline (single-Gauss) +%5; BIC k=3 minimum; persistence (mean diag) > 0.85; realized duration 30–250 trading day.

**c) Trading-level:** OOS Sharpe (HMM) − OOS Sharpe (static) ≥ **+0.15**; turnover artışı ≤ %50 (excess RR-015 cost ≤ 0.5× alpha); max DD artmamış.

**d) Robustness:** 5 kriz testi geçti (§8 Val Checklist'leri); lag ≤ 42 trading day; Tier 1→Tier 2 Sharpe swing ≤ ±0.10; ±3σ outlier dirençli.

**9.2 9 maddelik aktivasyon checklist:**
```
□ 1. ≥180 gün OOS veri (muhafazakar)
□ 2. Tier 1 pipeline production-ready (EVDS + yfinance + KAP)
□ 3. BIC: 3-state minimum, 4-state ΔBIC<10
□ 4. CPCV DSR > 0 (one-sided p<0.05) — López de Prado 2018
□ 5. OOS Sharpe iyileşmesi ≥ +0.15 vs static MASTER_WEIGHTS
□ 6. 5 kriz testi geçti (§8 her Builder Val Checklist)
□ 7. Lag ≤ 42 trading day
□ 8. ENABLE_HMM_WEIGHTS toggle (off↔on, NAV continuity) test edildi
□ 9. Cagan + Builder dual sign-off (CB-002 protokolü)
```

**9.3 İki paralel senaryo:**
| Senaryo | OOS başlangıç | 180g bitiş | Aktivasyon |
|---|---|---|---|
| Erken | ~Şubat 2026 | ~Ağustos 2026 | Q3 2026 (Eylül) |
| Geç (muhafazakar) | ~Mayıs 2026 | ~Kasım 2026 | Q4 2026 (Aralık) |

**9.4 Cagan açık sorusu:**
> **Q:** Alpha Attribution Phase 1 IC dashboard OOS veri üretimine fiilen ne zaman başladı?
> **Net cevap:** Bu rapor tarihi itibarıyla (25 Mayıs 2026) Cagan notlarında resmi başlangıç tarihi belgelenmemiş.
> **Implementation önerisi:** **Muhafazakar Kasım 2026 varsayım**. Erken senaryo Cagan onayı ile aktive edilebilir, default geç.

**9.5 Karar protokolü:** Aylık Cagan review → 9 maddenin 9'u tikli + tüm Builder Val Checklist (§4.4, §5.7, §6.7, §7.6, §8.×, §10.5, §11.5, §12.5) yeşil → PR → main merge → `ENABLE_HMM_WEIGHTS=True` toggle + dual sign-off. Rollback: ilk 30 gün manuel gözlem; tek satır revert garantili.

---

## §10. HMM-Conditional Weights

> Hedef okuyucu: Builder. Mevcut MASTER_WEIGHTS DEĞİŞMEZ; paralel kolon.

**10.1 Statik (değişmez):**
```python
MASTER_WEIGHTS = {
    "L1_Technical": 0.25, "L2_Macro": 0.20, "L3_KAP": 0.30,
    "L4_Sentiment": 0.12, "L5_Smart": 0.10, "L6_Risk_Kelly": 0.03,
}  # Σ=1.00 ✅
```

**10.2 HMM-conditional (ENABLE_HMM_WEIGHTS=True iken):**
```python
HMM_WEIGHTS_BY_STATE = {
    "BULL":    {"L1": 0.35, "L2": 0.15, "L3": 0.25, "L4": 0.13, "L5": 0.10, "L6": 0.02},
    "NEUTRAL": {"L1": 0.25, "L2": 0.20, "L3": 0.30, "L4": 0.12, "L5": 0.10, "L6": 0.03},  # = MASTER
    "BEAR":    {"L1": 0.15, "L2": 0.35, "L3": 0.20, "L4": 0.12, "L5": 0.15, "L6": 0.03},
}  # Her state Σ=1.00 ✅
```
**Bull:** L1 (Technical) momentum dominant. **Bear:** L2 (Macro — CDS, USD/TRY) ön plan; L5 (Smart Money) yabancı kaçışı izle.

**10.3 Confidence-based blending:**
```python
def get_effective_weights(hmm_state, confidence):
    """confidence<0.70 → NEUTRAL'a blend; ≥0.70 → tam state weights."""
    if confidence < 0.70:
        alpha = (confidence - 0.50) / 0.20  # 0..1 lineer
        w_state = HMM_WEIGHTS_BY_STATE[hmm_state]
        w_neutral = HMM_WEIGHTS_BY_STATE["NEUTRAL"]
        return {k: alpha*w_state[k] + (1-alpha)*w_neutral[k] for k in w_state}
    return HMM_WEIGHTS_BY_STATE[hmm_state]
```
Günlük re-balance, ani jump değil.

**10.4 Backward compatibility:**
```python
def get_weights():
    if ENABLE_HMM_WEIGHTS:
        state, conf = hmm_model.predict_current()
        return get_effective_weights(state, conf)
    return MASTER_WEIGHTS  # default
```

**10.5 Builder Validation Checklist — Weights:**
- [ ] Her state Σ=1.00 ± 1e-6?
- [ ] Confidence 0.50/0.60/0.70 sınır blend test edildi mi?
- [ ] ENABLE_HMM_WEIGHTS=False default sabit mi?
- [ ] Toggle on/off NAV continuity test edildi mi?
- [ ] HMM_WEIGHTS_BY_STATE config (YAML/JSON) Cagan tarafından review edildi mi?

---

## §11. POSITION_SIZER_V3 + HMM Entegrasyonu

> Hedef okuyucu: Builder. RR-016 V3 + CB-002 macro gate interaction matrix.

**11.1 Architecture impact:**
```
HMM (RR-017)                       → state + confidence  ("rejim NE")
       ↓
MASTER_WEIGHTS (state-conditional, §10)
       ↓
composite score per ticker
       ↓
POSITION_SIZER_V3 (RR-016 §5)
  - Vol-targeting   ("rejim İÇİNDE ne kadar")
  - DD soft gate    ("pozisyon NASIL koru")
       ↓
Execution
```

**11.2 CB-002 macro gate × HMM interaction — min() yaklaşımı (RR-016 mirası):**

```python
def effective_exposure(static_target, cb002_macro_score, hmm_state, hmm_conf):
    """İki defansif mekanizmadan EN MUHAFAZAKAR olanı uygula (min). Çift sayma yok."""
    cb002_factor = compute_macro_floor(cb002_macro_score)   # RR-016 mirası
    hmm_factor   = {"BULL": 1.10, "NEUTRAL": 1.00, "BEAR": 0.40}[hmm_state]
    hmm_factor   = 1.0 + (hmm_factor - 1.0) * hmm_conf       # confidence ile yumuşat
    combined     = min(cb002_factor, hmm_factor)             # KRİTİK: min() çift sayma yok
    return static_target * combined
```

**11.3 Interaction matrix:**
| HMM state (conf) | CB-002 macro_score | Effective | Yorum |
|---|---|---|---|
| BULL (0.8) | 0 nötr | min(1.0, 1.08) = **1.00** | HMM Bull oversteer etmez |
| NEUTRAL | −1 zayıf | min(0.85, 1.00) = **0.85** | CB-002 dominant |
| BEAR (0.8) | 0 nötr | min(1.0, 0.52) = **0.52** | HMM dominant |
| BEAR (0.8) | −2 kriz | min(0.65, 0.52) = **0.52** | HMM hala conservative |
| BEAR (0.5) | 0 | min(1.0, 0.76) = **0.76** | Düşük conf → az defansif |

**11.4 Sanity test:**
```python
assert effective_exposure(1.0, +1, "BULL", 0.9) <= 1.10
assert effective_exposure(1.0, -2, "BEAR", 0.9) <= 0.55
# Backward compat:
ENABLE_HMM_WEIGHTS = False
assert effective_exposure(1.0, 0, "BULL", 0.9) == 1.0
```

**11.5 Builder Validation Checklist — Entegrasyon:**
- [ ] min() yaklaşımı RR-016 §5 ile bire-bir uyumlu mu?
- [ ] HMM_off + CB-002 yalnız çalışırken pre-RR-017 davranış korunuyor mu?
- [ ] HMM_on + CB-002 birlikte interaction matrix otomatik test edildi mi?
- [ ] Effective exposure max 1.10 (Bull bonus) / min 0.40 (Bear floor) arasına clip edildi mi?
- [ ] State değişim günü exposure jump >%20 ise warning log atıyor mu?

---

## §12. Python Implementation Hintleri

> Hedef okuyucu: Builder. **Production kod DEĞİL** — kavramsal template + docstring + comment.

**12.1 hmmlearn template:**
```python
# regime_detector.py — KAVRAMSAL şablon, production refine gerektirir
from hmmlearn.hmm import GaussianHMM
import numpy as np

class BISTRegimeDetector:
    """BIST 3-state regime detector.
    
    Tier 1 feature set: [bist_log_ret, vol_20d, usdtry_log_ret, cds_change]
    State mapping: 0=BULL, 1=NEUTRAL, 2=BEAR (deterministic, §12.2)
    
    Usage:
        detector = BISTRegimeDetector()
        detector.fit(X_train)
        state, conf = detector.predict_current(X_recent_window)
    
    NOT production-ready: error handling, monitoring, S3 persistence,
    CI/CD entegrasyonu Builder tarafından AG-001 öncesi tamamlanır.
    """
    def __init__(self, n_states=3, random_state=42):
        self.n_states = n_states
        self.model = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",        # Tier 1 küçük; full overfit
            n_iter=200, tol=1e-3,
            init_params="stmc", params="stmc",
            random_state=random_state,
            min_covar=1e-3, algorithm="viterbi",
        )
        self.state_mapping = None

    def fit(self, X_train):
        """X_train: (T,4) Tier 1 feature matrix, normalized (§5.6).
        Sanity: T >= 36*21 (≈ 36 ay), np.isfinite tüm, std>1e-6 her feature."""
        self.model.fit(X_train)
        assert self.model.monitor_.converged, "EM converge etmedi"
        self.state_mapping = self._deterministic_label_mapping()

    def _deterministic_label_mapping(self):
        """State permutation problemi: hmmlearn states random sıralı.
        Sıralama: mean log-return DESC → BULL/NEUTRAL/BEAR."""
        means_ret = self.model.means_[:, 0]  # feature[0] = log_ret
        sort_idx = np.argsort(-means_ret)     # descending
        return {sort_idx[0]: "BULL", sort_idx[1]: "NEUTRAL", sort_idx[2]: "BEAR"}

    def predict_current(self, X_recent):
        """Return (state_name, confidence)."""
        states = self.model.predict(X_recent)
        probs  = self.model.predict_proba(X_recent)
        return self.state_mapping[states[-1]], float(probs[-1].max())

    def save(self, path):
        """joblib pickle; production'da S3/Object Store + version tag."""
        import joblib
        joblib.dump({"model": self.model, "mapping": self.state_mapping}, path)
```

**12.2 Deterministic state labeling:** EM her run'da random state sıralar; çözüm mean return ile sort. Alternatif: mean vol (Bear vol > Bull vol). Çift sıralama Pareto sort Builder inisiyatifinde.

**12.3 Persistence:** Aylık kalibre, joblib pickle (`models/hmm_regime_v1_2026Q4.joblib`); production'da S3/Object Store + version tag.

**12.4 Pseudo-test scenarios:**
```python
# tests/test_hmm.py — pytest pattern
def test_state_persistence():
    """Sticky regime assumption holds."""
    diag = np.diag(detector.model.transmat_)
    assert (diag > 0.6).all(), f"State persistence too low: {diag}"

def test_state_mapping_stable():
    """Same data → same mapping."""
    d1 = BISTRegimeDetector(random_state=42); d1.fit(X)
    d2 = BISTRegimeDetector(random_state=42); d2.fit(X)
    assert d1.state_mapping == d2.state_mapping

def test_label_economic_meaning():
    """Bull mean ret > Neutral > Bear."""
    inv = {v: k for k, v in detector.state_mapping.items()}
    assert detector.model.means_[inv["BULL"], 0] > detector.model.means_[inv["BEAR"], 0]

def test_crisis_2018_bear_detected():
    """Aug 2018 retrospective lag <= 42 trading days."""
    states_crisis = detector.predict_window(X_crisis)
    first_bear = next(i for i, s in enumerate(states_crisis) if s == "BEAR")
    assert first_bear <= 42

def test_backward_compat_flag_off():
    """ENABLE_HMM_WEIGHTS=False → MASTER_WEIGHTS unchanged."""
    ENABLE_HMM_WEIGHTS = False
    assert get_weights() == MASTER_WEIGHTS
```

**12.5 Builder Validation Checklist — Implementation:**
- [ ] hmmlearn ≥0.3.0 (sklearn-compatible meta routing)?
- [ ] State mapping deterministik (test_state_mapping_stable passes)?
- [ ] Persistence path versioned (`model_v1_2026Q4`)?
- [ ] 5 kriz periodu pseudo-test'leri pytest paketinde mi?
- [ ] CI/CD'de model artifact build + smoke test var mı?

---

## §13. Risk & Failure Modes

> Hedef okuyucu: Cagan + Builder.

| # | Risk | Olasılık | Etki | Mitigation |
|---|---|---|---|---|
| 13.1 | **Overfit** (5-state + 8 feature → ~80 param, BIST ~3700 obs) | Orta | Yüksek | 3-state default + Tier 1 (4 feat); §4 BIC + §7 CPCV |
| 13.2 | **Regime detection lag** (Viterbi smoothing) | Yüksek | Orta | Tier 1 CDS; confidence threshold 0.70 vs 0.50 trade-off; AG-001 max 42 gün |
| 13.3 | **Stationarity violation** (hiperenflasyon, politika) | Yüksek | Yüksek | §6.5 re-calibration; rolling KPSS; pre/post 2023 ayrı model |
| 13.4 | **Single-source dependency** (EVDS, CDS) | Düşük | Orta | Tier 1 min 4 → Tier 0 (3 feat) fallback; RR-003 §5 ensemble |
| 13.5 | **Crisis recovery V-shape** (2020 örneği) | Orta | Orta | Manuel override; 7-gün MA smoothing; RR-016 vol-targeting alt katmanı |

**13.5 detayı:** HMM Bear'a hızlı geçer, V-recovery'de geç çıkar → false-defensive 2–3 ay. Çözüm: confidence düşükse blend (§10.3); RR-016 vol-targeting state İÇİNDE dinamik exposure ayarlar.

---

## §14. BIST 2024–2026 Sektör Pratiği

> Hedef okuyucu: Cagan. Ordinal skala (Yüksek/Orta/Düşük/Yok) + gözlem notu.

**14.1 Türk fon yöneticileri regime-based mi?**
| Aktör | Ordinal | Gözlem | Kaynak |
|---|---|---|---|
| TEFAS taktik allocation fonları | **Düşük** | "Taktik varlık dağılımı" pazarlama söylemi (Aktif Portföy, Tacirler TCC) var; **Markov/HMM rejim modeli** açıkça beyan eden resmi belge yok | https://www.aktifportfoy.com.tr/blog/tefas-nedir-tefas-fonu-nasil-alinir |
| SPK risk disclosure regime kavramı | **Yok / BULUNAMADI** | KAP fon izahnamelerinde "Markov" veya "rejim değişim modeli" geçen örnek bulunamadı | https://kap.org.tr/tr/YatirimFonlari/YF |
| Esas Yatırım (Esas Holding PE) | **Yok (kapsamsız)** | Private equity / VC odaklı (Tavuk Dünyası, MAC, UN Ro-Ro); public market regime detection değil | https://www.esas.com.tr/en/private-equity/turkiye |
| Mediterra Capital | **Yok (kapsamsız)** | Private equity (Fon 1/2/3); web'de erişilebilen yerel haberler bu varlık büyüklüğünü "Türkiye'nin önde gelen PE fonlarından" olarak nitelendiriyor — kesin AUM rakamı doğrulanamadı; public market regime detection değil | https://www.mediterracapital.com/ · https://webrazzi.com/2023/10/27/istanbul-portfoy-yonetimi-mediterra-3-gsyf/ |
| Tacirler TCC ("taktiksel" TEFAS fonu) | **Düşük** | "Olumsuz piyasa koşullarında koruma" söylemi; metodoloji belirtilmemiş | https://tacirlerportfoy.com.tr/tefas-uzerinden-satisa-acik-olan-fonlarimiz |
| Broker macro outlook (İş Yat, Garanti BBVA, Gedik) | **Orta** | "Yeni dönem", "disinflation rally" implicit regime söylemi; formal model yok | Sektör genel |

**Karar:** BIST'te formal HMM/MS regime detection sahaya çıkmış kurumsal pratik **YOK**. RR-017 piyasa öncesi pozisyon (fırsat ama doğrulama riski yüksek).

**14.2 Pratisyen söylem (forum, sosyal medya):**
| Kaynak | Söylem | Erişim |
|---|---|---|
| Twitter @muratsagman ("Borsada Oynanmaz" yazarı) | "Rejim değişti" sezgisel; formal HMM yok | Twitter login-wall; içerik **örneklenmedi** |
| Hisse.net / BigPara thread'ler | "Bull bitiyor / Bear başlıyor" tartışmaları | Erişilebilir, **sample edilmedi** |
| YouTube borsa kanalları (Doğukan Kasapoğlu vb) | Doğrudan regime-tematik içerik **BULUNAMADI** | Login-wall yok ama içerik **örneklenmedi** |
| Investing.com TR (Şub 2026) | "BIST 100'ü geride bırakın" yapay zeka stratejisi söylemi | https://tr.investing.com/news/investment-ideas/ |

**14.3 Broker araştırma — implicit regime:** İş Yat, Garanti BBVA, Gedik macro outlook raporları "yeni döneme geçiş", "disinflation rally", "Şimşek programı" söylemleri — kavramsal regime ama formal model yok. Deniz Yatırım 2024 Strateji Raporu (https://www.denizyatirim.com/Uploads/Deniz_Yat_r_m_2024_Strateji_Raporu_5472.pdf) BIST 12-aylık hedef + senaryo analizi; HMM yok.

**14.4 Türk finansal medya 2023–2024:** 2023 Haziran "yeni dönem" (Şimşek atanma) söylemi yaygın (T24/Cumhuriyet/Paraanaliz); 2024 disinflation rally (Mayıs zirvesi TÜFE %75.45, sektör rotasyonu); 2026 Mart-Mayıs CHP "mutlak butlan" siyasi şok söylemi.

**14.5 Ordinal skala özet:**
```
HMM/Markov bazlı kurumsal regime detection BIST'te:    YOK / BULUNAMADI
TEFAS "taktik allocation" pazarlama söylemi:           Düşük
Broker macro outlook implicit regime:                  Orta
Pratisyen sezgisel "rejim değişti" söylemi:           Yüksek
Sosyal medya / forum:                                  Yüksek (formal değil)
```

---

## §15. Implementation Roadmap

> Hedef okuyucu: Cagan + Builder.

**15.1 Faz 1 — Veri biriktirme (mevcut → ~Kasım 2026).** Alpha Attribution Phase 1 IC dashboard OOS üretmeye devam. Tetik: AG-001 ≥180 gün. Çıktı: OOS panel veri. **Bu fazda HMM kod deploy YOK.**

**15.2 Faz 2 — Kalibrasyon + OOS test (Kas 2026 ~ Oca 2027).** Builder Tier 1 pipeline + hmmlearn template refine; 5 kriz testleri çalıştır. Tetik: F1 done. Çıktı: Validation report (BIC, CPCV, lag). Gateway: §4.4, §5.7, §6.7, §7.6, §8.× Builder Val Checklist'leri.

**15.3 Faz 3 — Architecture entegrasyon (Oca 2027 ~ Şub 2027).** HMM_WEIGHTS_BY_STATE config + position_sizer_v3 + CB-002 interaction matrix testleri. Tetik: F2 passed. Çıktı: PR draft (ENABLE_HMM_WEIGHTS=False default, tüm path test edilmiş).

**15.4 Faz 4 — AG-001 aktivasyon (Şub 2027 — muhafazakar).** Dual sign-off → `ENABLE_HMM_WEIGHTS=True` commit + ilk 30 gün manuel gözlem. Tetik: 9-maddelik checklist (§9.2). Çıktı: Production'da HMM-aware weights. Rollback: tek satır revert.

**15.5 Faz 5 — Multi-model ensemble (Q3-Q4 2027).** RR-003 §2'de XGBoost ile birleşim; **alternatif: Statistical Jump Model (Aydınhan vd 2024, Shu-Yu-Mulvey 2024) review**. Tetik: F4 stable 6+ ay. Shu-Yu-Mulvey (2024) JM'in HMM'e net üstünlüğünü US/DE/JP'de gösterdi → **Faz 5 review'da JM alternatifi mutlaka değerlendirilmeli**, eğer BIST için JM Sharpe iyileşmesi varsa XGBoost yerine bypass mümkün.

**15.6 Roadmap özet tablo:**
| Faz | Tetikleyici | Hedef tarih | Çıktı | Karar gateway |
|---|---|---|---|---|
| 1 | Mevcut | Kas 2026 | 180g OOS veri | AG-001 §9.2 |
| 2 | F1 done | Oca 2027 | Validation report | Val Checklist'ler |
| 3 | F2 passed | Şub 2027 | PR draft | Code review |
| 4 | F3 reviewed | Şub 2027 | Production HMM | Cagan/Builder sign-off |
| 5 | F4 stable 6m | Q3 2027 | Ensemble HMM+? | JM vs XGBoost review |

---

## §16. Akademik Kaynak Özeti + Kısıtlar & Caveat'lar

> Hedef okuyucu: Cagan + future reviewer.

**16.1 Bu raporda kullanılan tam künyeler:** §2'deki iki tablo tam DOI/URL'lerle birlikte.

**16.2 Kısıtlar (caveat'lar):**

- **K1 — 3-state HMM Türk BIST literatüründe seyrek:** Bu rapor literatür-aşırı (3-state) hipotez önerir; 2-state MS dominant gerçeklik (Şenol 2020, Samırkaş 2021). **AG-001 BIC ile bu hipotezi doğrulamak zorunda.**
- **K2 — "8-10 puan/yıl alpha" iddiası post-OOS doğrulanmadan kabul edilmez:** Literatür kaynağı Wang-Lin-Mikhelson (2020) S&P 500 OOS'de HMM rotation modelinin Sharpe ve Treynor avantajı belgelenmiş ama spesifik yıllık abnormal-return rakamı raporun Table 5 ayrıntısı; verbatim olarak özetten doğrulanamadı. BIST için kalibrasyon + transaction cost (RR-015) sonrası rakam ölçülmeden iddia geçersiz.
- **K3 — Hiperenflasyon non-stationarity ciddi tehdit:** §5.5 + §6.5 protokolü hayati. TÜİK ve ENAG serileri arasındaki büyük fark (TÜİK Aralık 2021 %36.08 vs ENAG %82.81, Ekim 2022 TÜİK zirvesi %85.51) feature input'unun TÜİK mi ENAG mı olduğu Builder tarafından **belgelenmeli**.
- **K4 — Türk kurumsal ve pratisyen formal regime detection BULUNAMADI:** §14 ordinal skalası fırsat gösterir; doğrulama riski yüksek.
- **K5 — Crisis lag 2 ay eşiği muhafazakar:** 2018 Ağu (CDS 165→586 bps) ve 2023 May (devre kesici) gibi tek-haftalık şoklar HMM'in zayıf noktası; vol-targeting (RR-016) ile kapatılır ama gap kalır.
- **K6 — Statistical Jump Model alternatifi:** Shu-Yu-Mulvey 2024 HMM'i US/DE/JP'de geçmiş; Faz 5 (§15.5) review zorunlu.
- **K7 — Sayısal birim caveat'ı:** Samırkaş (2021) MS(2)-AR(0) için ortalama sojourn **7.75 gün boğa / 32.64 gün ayı**; TVTP modelinde transition olasılıkları farklı (%96.20 / %86). Şenol (2020) "64 / 11" birim çalışma özetinde açıkça verilmemiş. CB-002 finding'indeki "64 ay bull / 11 ay bear" yorumu **muhtemelen Şenol değerleri** ama birim ay/gün belirsiz — Builder §3.1 Val Checklist'inde belgelemeli.
- **K8 — TCMB faiz tepe noktası:** Görev brief'inde "Mayıs 2024 zirve" denmiş; TCMB resmi duyurularına göre **politika faizi Mart 2024'te %45'ten %50'ye yükseltilmiş (TCMB Duyuru 2024-14)** ve Kasım 2024'e kadar %50'de tutulmuştur; ilk indirim Aralık 2024 %47.5 (Duyuru 2024-70). RR-017 §6.5 ve §8.3 buna göre revize.
- **K9 — Production-ready kod kapsamı DEĞİL:** §12 sadece kavramsal template; error handling, monitoring, S3 persistence, CI/CD entegrasyonu Builder tarafından AG-001 öncesi tamamlanır.

**16.3 Erişim notları:**
- López de Prado (2018), Mamon & Elliott (2007), Bulla & Bulla (2006) ücretli; SSRN/EconPapers/Wiley üzerinden parça erişim.
- Hamilton (1989) JSTOR ücretli; her referans kitap özetler.
- Şenol (2020), Samırkaş (2021) Dergipark açık erişim Türkçe — Cagan/Builder okumalı.
- Wang-Lin-Mikhelson (2020) MDPI açık erişim — recommended.
- Aydınhan vd (2024) SSRN açık + DOI'li dergi.
- Shu-Yu-Mulvey (2024) arXiv açık erişim — recommended for Faz 5 review.

**16.4 Final caveat:** Bu rapor **kavramsal implementation belgesi**. AG-001 günü Builder bu raporu sıfırdan production kod yazmak için kullanır — her docstring, comment ve sanity test örneği refine edilir. **ENABLE_HMM_WEIGHTS=False default kalır**, hiçbir koşulda bu rapor sebebiyle production değişmez.

**RR-017 ile RR-016 entegrasyonu açıkça dokümante (§11); CB-002 macro gate × HMM interaction matrix min() yaklaşımı (§11.2); HMM "rejim NE der" (bu rapor), RR-016 vol-targeting "rejim İÇİNDE ne kadar" (RR-016 §5), DD soft gate "pozisyon NASIL koru" (RR-016 §6) üçlü ayrımı korunuyor.**

---

## Recommendations

1. **Bu raporu uygula(ma):** Cagan ENABLE_HMM_WEIGHTS=False bayrağını koru; bu rapor AG-001 günü Builder'ın eline geçer. Bugünden hiçbir kod değişikliği gerekmez.
2. **Faz 1 takip:** Alpha Attribution Phase 1 IC dashboard'ı her ay review et; OOS gün sayacı düzenli logla. Hedef Kasım 2026 (muhafazakar 180 gün).
3. **Faz 2 hazırlığı (Q4 2026):** Builder Tier 1 pipeline development için yeterli zamanı ayır; CDS veri tedariki (Investing.com / IHS Markit) için kaynak belirle.
4. **Faz 5 review notu:** RR-003 §2'de XGBoost listede ama Shu-Yu-Mulvey (2024) JM'in HMM'i geçtiğini gösterdi. F4 sonrası **JM vs XGBoost A/B karşılaştırması zorunlu**.
5. **Eşik değişiklik tetikleyicileri:** (a) AG-001 OOS Sharpe iyileşmesi < +0.15 ise HMM aktivasyonu yapma. (b) Crisis lag > 42 trading day ise Tier 1 → Tier 2 (VIX ekle). (c) BIST hiperenflasyon yeniden tetiklenirse (TÜİK yıllık >%50 veya ENAG >%80) re-calibration.

## Caveats

- Bu rapor RR-003 §1'i tekrar etmez; HMM seçim gerekçesi orada detaylıdır.
- Tüm §8 crisis analizleri **retrospektif simülasyon**; real-time HMM kararı temsil etmez.
- "8–10 puan/yıl alpha" rakamı **CB-002 finding'i**; literatür ile kısmen desteklenir ama BIST için doğrulanmadı.
- Sayısal değerlerde Şenol (2020) ve Samırkaş (2021) farklı modeller (sabit vs TVTP) ile farklı sojourn değerleri raporlar; iki çalışmanın doğrudan toplanması yanlış olur.
- Mediterra Capital AUM rakamı için kesin doğrulanmış kaynak bulunamadı (görev brief'indeki büyüklük tahmini referansa alınmamıştır).
- TÜİK / ENAG TÜFE farkı politik tartışmaya konu; RR-017 feature seçimi (TÜFE delta Tier 2/3'te kullanılırsa) Builder tarafından kaynak seçim notu ile belgelenmeli.
- Production-ready Python kod bu rapor kapsamı DEĞİL; §12 templates kavramsaldır.

*Rapor sonu. Sonraki: AG-001 dashboard takibi → Faz 1 OOS biriktirme → Kasım 2026 (muhafazakar) Faz 2 kalibrasyon.*