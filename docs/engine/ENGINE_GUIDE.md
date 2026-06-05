# RR-Y1-005 Doğrulama Motoru — Kullanım Kılavuzu ve Matematiksel Model

> **Kapsam:** `src/engine/` paketi — genel amaçlı, ayarlanabilir, post-hoc denetlenebilir
> strateji-doğrulama harness'i.
> **Tasarım:** RR-Y1-005-TEST-MOTORU-TASARIM v0.2 (ne/neden) · **Matematik:** RR-Y1-005B-MATEMATIKSEL-SPEC v1.1 (biçimsel çekirdek)
> **Sürüm:** `src.engine.__version__` · **Yazar:** Cagan

---

## 0. Bir cümlede ne yapar?

Motor, bir **prototip sinyali** alır ve onun "gerçek mi yoksa overfit mi" olduğunu
tek bir pass/fail bitine indirgemeden, **Section-7 çıktı VEKTÖRÜ** olarak raporlar:

```
harness(panel, signal, split_spec, dial_config) -> EngineOutput
```

Çıktı bir karar değil, bir **kanıt panosudur**: getiri/maliyet, anlamlılık (PBO/DSR/NW-t),
conjugate uyum, rejim kırılımı, parametre platosu, ve her ölçümün **güven niteliği**.
Kararı okuyan insan verir; motor sadece dürüst sayıları üretir.

### Tasarım ilkeleri (değişmez)

| İlke | Anlamı |
|------|--------|
| **Strangler** | Motor, commit edilmiş motorları (`src/screening`, `src/backtest`) **salt-okunur** import eder; hiçbir commit'li dosyaya dokunmaz, lab kodu import etmez. |
| **Vektör çıktı** | `EngineOutput` bir bit değil, ~30 alanlı bir vektördür. Pass/fail yorumu okuyucuya aittir. |
| **Partial-leg sözleşmesi** | Bir bacak (Mod-A/B/C) tamamlanamazsa harness **asla raise etmez**; ilgili alanlar `None` kalır, `guard_messages`'a sebep yazılır. |
| **PM-1 yasası** | Motor asla bir nakit-kapısı (cash-gate) sinyali değerlendirmez. Boşta = tam-yatırımlı eşit-ağırlık; tetik sepet İÇİNDE yeniden-tilt yapar. |
| **Stage-0 dondurma** | Hipotez ölçümden ÖNCE dondurulur. `stage0_path` verildiğinde dosya yoksa/sürüklendiyse motor **çalışmayı reddeder**. |
| **Anti-slop golden** | C12 gerçek-veri determinizm çıpası (NW-t gross 6.928414 / net -6.274774 @ lag10, n=1375) byte-byte yeniden üretilir. |

---

## 1. Mimari ve veri akışı

```
                         ┌─────────────────────────────────────────────┐
   data_adapter.load_panel ──► Panel  (close/tr_gross/tr_net/value_tl/   │
                         │            market/tufe/tlref, wide frames)    │
                         └─────────────────────────────────────────────┘
                                          │
   Signal (protokol: scores(panel,names,asof) -> Series)                 │
   SplitSpec  (split yapısı: mode, embargo, R, CPCV, holdout_start)      │
   DialConfig (8 ayar düğmesi)                                           │
                                          ▼
                         ┌──────────────  harness()  ──────────────┐
                         │  dispatch by split_mode:                 │
                         │   A   -> run_moda  (isim-bölme conjugate)│
                         │   B   -> run_modb  (zamansal CPCV)       │
                         │   A+B -> her ikisi (PANEL)               │
                         │   C   -> run_modc  (rejim-içi time-holdout)
                         │                                          │
                         │  + her zaman: tradeable tilt getiri/    │
                         │    maliyet (D-207 stack), benchmark floor│
                         │    (TUFE/TLREF), per-regime, plateau     │
                         └──────────────────┬───────────────────────┘
                                            ▼
                                       EngineOutput  (Section-7 vektör)
```

### Modül haritası

| Modül | Sorumluluk |
|-------|------------|
| `contracts.py` | Tüm tipler: enum'lar, `Panel`, `SplitSpec`, `DialConfig`, `EngineOutput`. |
| `config.py` | Donmuş yapısal sabitler + dial varsayılanları (tek doğru kaynak). |
| `data_adapter.py` | `load_panel`, `liquid_names`, `forward_return` (ileri getiri). |
| `stats.py` | Matematiksel çekirdek: `rank_ic_series`, `ic_ir`, `nw_tstat` (Newey-West HAC). |
| `neutralizer.py` | `rolling_beta` (look-ahead-safe), `residualize`, `market_neutral_forward`. |
| `moda.py` | Mod-A: likidite-katmanlı isim-bölme conjugate çekirdek + residual korelasyon. |
| `modb.py` | Mod-B: zamansal CPCV → OOS Sharpe dağılımı → PBO/DSR. |
| `modc.py` | Mod-C: rejim-içi ileri time-holdout persistence (RR-Y1-010). |
| `pbo.py` | Gerçek CSCV median-rank PBO (Lopez de Prado) — Mod-A çekirdeğinin kullandığı. |
| `dsr.py` | DSR trial-count deflation benchmark (Bailey-LdP E[max] dereceli-istatistik). |
| `benchmark.py` | Reel-getiri deflate + benchmark-floor: reel getiri > max(TUFE, TLREF). |
| `confidence.py` | Mod-A güven niteliği (`assess_agreement_confidence`). |
| `holdout_confidence.py` | Mod-C güven niteliği (`assess_holdout_confidence`). |
| `signal_protocol.py` | `Signal` protokolü + `assert_pm1_compliant` (PM-1 gardı). |
| `stage0_validator.py` | Stage-0 ön-kayıt: yoksa-reddet + snapshot içerik-hash gardı. |
| `lockbox.py` | Tek-atışlık held-out kilidi (single-shot held-out subset seal). |
| `harness.py` | Üst-düzey assembler — tek giriş noktası. |

---

## 2. Hızlı başlangıç

```python
import pandas as pd
from src.engine.contracts import (
    DialConfig, Frequency, Panel, SplitMode, SplitSpec,
)
from src.engine.data_adapter import load_panel
from src.engine.harness import harness

# 1) Paneli yükle (clean_universe + snapshots; DataHub DEĞİL -- strangler)
panel = load_panel()                       # config.PRICES_PARQUET'ten

# 2) Bir prototip sinyali tanımla (zero-discretion cross-sectional scorer)
class MomentumSignal:
    name = "mom_12_1"
    construction_window = 21               # = Mod-B embargo h (Section 3.4)
    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        px = panel.close.loc[:asof, names]
        return (px.iloc[-1] / px.iloc[-self.construction_window] - 1.0)

# 3) Bölme yapısı + ayarlar
spec = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY)
dials = DialConfig()                        # donmuş v1.1 varsayılanları

# 4) Çalıştır
out = harness(panel, MomentumSignal(), spec, dials)

print(out.agreement_pass, out.agreement_confidence)
print(out.net_active_ann, out.beats_benchmark_floor)
print(out.pbo, out.dsr, out.nw_t)
```

**Ön-kayıtlı (pre-registered) çalıştırma** için `stage0_path` geç:

```python
out = harness(panel, sig, spec, dials, stage0_path="data/stage0/RR-Y1-XXX.json")
# Dosya yoksa veya snapshot içerik-hash'i sürüklendiyse -> Stage0Error (motor reddeder)
```

---

## 3. Sözleşmeler (Contracts)

### 3.1 `Panel` — yüklü veri

Tüm frame'ler **wide**: index=tarih, sütun=sembol.

| Alan | Tip | Açıklama |
|------|-----|----------|
| `close` | DataFrame | Düzeltilmiş kapanış. |
| `tr_gross` / `tr_net` | DataFrame | Toplam-getiri endeksi (temettü reinvest), brüt/net. |
| `value_tl` | DataFrame | Günlük işlem hacmi (likidite proxy'si). |
| `membership` | dict | PIT endeks üyeliği (`{"bist100": 0/1, ...}`). |
| `market` | Series | Piyasa endeksi seviyesi (XU100); getiri = `pct_change`. |
| `tufe` / `tlref` | Series | TÜFE / TLREF seviye serileri (benchmark floor için). |
| `frequency` | Frequency | `DAILY` (varsayılan) / `MONTHLY`. |

Yardımcı property: `panel.dates`, `panel.names`. `eq=False` çünkü DataFrame `__eq__`
eleman-bazlıdır (oto-üretilmiş eşitlik "ambiguous truth value" hatası verirdi).

### 3.2 `SplitSpec` — bölme yapısı (Stage-0'da donar)

| Alan | Varsayılan | Anlam |
|------|------------|-------|
| `split_mode` | — | `A` / `B` / `A+B` / `C`. |
| `frequency` | — | `DAILY` / `MONTHLY`. |
| `embargo_h` | `1` | = sinyal construction-window'u (Section 3.4); `>= 1`. |
| `R` | `50` | Tohum-sabit isim-bölme sayısı (Mod-A). |
| `seed` | `0` | Tekrarlanabilirlik tohumu. |
| `cpcv_n` / `cpcv_k` | `10` / `2` | Mod-B CPCV blokları; `k < n` zorunlu. |
| `split_arm_floor_tl` | `1e7` | Kol-başına likidite tabanı (ADV). |
| `sort_depth` | `TERCILE` | `tercile` / `decile` / `topN`. |
| `min_names_per_arm` | `50` | Section 3.3: her kol >= 50 isim. |
| `name_split_method` | `LIQUIDITY` | `liquidity` (ADV-katmanlı) / `random`. |
| `holdout_start` | `None` | Mod-C sınırı (ISO tarih). `C` modunda **zorunlu**. |

`__post_init__` gardları: `embargo_h >= 1`; `cpcv_k < cpcv_n`; `R >= 1`;
`C` modunda `holdout_start` zorunlu; **monthly → yalnızca Mod-A** (zamansal-CPCV
aylık frekansta güç-fakiridir, Section 3.6).

### 3.3 `DialConfig` — 8 ayar düğmesi (Section 5)

Düğmeler 2 (split-mode), 4 (embargo), 8 (arm-floor + sort-depth) `SplitSpec`'te yaşar
(bölme yapısıdır); geri kalanı burada:

| Dial | Alan | Varsayılan | Rol |
|------|------|------------|-----|
| 1 | `psi` | `spearman` | Cross-sectional rank-IC tipi. |
| 3 | `neutralization` | `("market",)` | Nötrleme faktörleri (`market` minimum, Mod-A için zorunlu). |
| — | `return_basis` | `tr_index_gross` | Brüt/net toplam-getiri tabanı. |
| 7 | `cut_policies` | anchored/rolling/expanding | Cut-family (Faz-3'te wire değil). |
| 5 | `use_pbo` | `True` | PBO kapısı açık mı. |
| 6 | `use_dsr` | `True` | DSR kapısı açık mı. |
| — | `nw_lag` | `None` | `None` → frekanstan çözülür (daily 5 / monthly 3). |
| — | `winsorize` | `(0.01, 0.99)` | Winsorize sınırları. |
| — | `beta_window` | `126` | Beta tahmin penceresi (gün). |
| — | `agreement_t_min` | `2.0` | Conjugate t eşiği. |
| — | `sign_consistency_min` | `0.90` | İşaret-tutarlılık tabanı. |
| — | `pbo_max` | `0.50` | Gerçek CSCV PBO tavanı. |
| — | `dsr_min` | `0.95` | DSR tabanı. |
| — | `residual_corr_null_pctile` | `95` | Residual korelasyon null yüzdesi. |

`requires_market_neutralization(mode)`: Mod-A / PANEL'de `market` nötrleme yoksa raise.
`nw_lag_for(frequency)`: `nw_lag` None ise daily=5 / monthly=3 döndürür.

### 3.4 `EngineOutput` — Section-7 çıktı vektörü

Her alan `None`/boş varsayılanlıdır; kısmi bir koşu bile geçerli bir nesnedir.

| Grup | Alanlar |
|------|---------|
| **Getiri** | `gross_active_ann`, `net_active_ann`, `cost_ann`, `tax_ann`, `mean_rt_bps` |
| **Fair-null** (Faz-3'te None) | `null_percentile`, `mirror_active_ann` |
| **Benchmark floor** | `real_active_ann`, `benchmark_floor_ann`, `beats_benchmark_floor` |
| **Anlamlılık** | `pbo`, `deflated_oos_t` (None), `dsr`, `dsr_n_trials`, `nw_t` |
| **Conjugate (Mod-A)** | `agreement_pass`, `agreement_t_cross_median`, `sign_consistency`, `residual_cross_sectional_corr`, `residual_corr_flag` |
| **Mod-A güven** | `agreement_confidence`, `agreement_confidence_reasons` |
| **Holdout (Mod-C)** | `holdout_persistence_pass`, `holdout_ic_t/mean`, `train_ic_t/mean`, `holdout_sign_consistent`, `n_holdout_obs`, `n_train_obs`, `holdout_confidence`, `holdout_confidence_reasons` |
| **Rejim & plato** | `per_regime`, `plateau_map` |
| **Gardlar** | `pm1_guard_raised`, `guard_messages` |
| **Köken** | `n_obs`, `n_names`, `split_mode`, `notes` |

---

## 4. Matematiksel model

Aşağıdaki notasyon `src/engine/stats.py`, `neutralizer.py`, `moda.py`, `pbo.py`,
`dsr.py`, `benchmark.py` ile birebir tutarlıdır.

### 4.1 Cross-sectional rank-IC ve onun anlamlılığı

Her tarih `t` için, eligible isimler kümesi üzerinde sinyal skorları `s_{i,t}` ile
ileri rezidüel getiri `r_{i,t}` arasındaki **Spearman rank korelasyonu** hesaplanır:

```
IC_t = corr_spearman( rank(s_{·,t}), rank(r_{·,t}) ),   |{i: ikisi de finite}| >= 30
```

(`MIN_NAMES_CROSS_SECTION = 30`; tabanı geçmeyen tarih atlanır.) Bu, günlük IC
serisini `{IC_t}` verir (`rank_ic_series`).

**Information Ratio** (`ic_ir`): IC serisinin sinyal-gürültü oranı,

```
IR = mean_t(IC) / std_t(IC),   std ddof=1
```

**Newey-West HAC t-istatistiği** (`nw_tstat`) — IC serisinin ortalamasının,
otokorelasyona-dayanıklı t-değeri. Bartlett çekirdekli HAC varyans (POPÜLASYON
varyansı konvansiyonu, C12 golden ile tutarlı):

```
e   = IC - mean(IC)
γ_0 = (e·e) / n
γ_k = (e[k:]·e[:-k]) / n,                k = 1..L
s   = γ_0 + 2 · Σ_{k=1}^{L} (1 - k/(L+1)) · γ_k         (Bartlett ağırlıkları)
t   = mean(IC) / sqrt(s / n)
```

Gardlar:
- `n < L + 3` → `NaN` (HAC için yetersiz örnek).
- **FAZ-4 sıfıra-yakın-varyans tabanı:** `s <= eps · mean^2` (eps = `1e-12`) → `NaN`.
  Sayısal-sabit bir girdi, FP yuvarlamasından dolayı `s ~ 1e-32` gibi minik-ama-pozitif
  bir HAC varyansına sahip olabilir; bu `s <= 0` gardını atlayıp patlayan sahte bir t
  üretir. Göreli-varyans tabanı yalnızca dejenere girdide tetiklenir; C12 golden
  (~1e2 göreli varyans) ve d211/d213 denkliği asla tetiklemez.

`L` (lag) frekanstan çözülür: daily=5, monthly=3 (`NW_LAG_DAILY/MONTHLY`).

### 4.2 Piyasa-beta nötrleme (look-ahead-safe)

Faktörün anlamlı olabilmesi için piyasa-beta etkisi temizlenir (Section 3.5,
Mod-A'da **zorunlu**). `rolling_beta`, **bakışı-geleceğe-kaçırmaz**: pencereden önce
`shift(1)` uygulanır, böylece `t` günündeki beta yalnızca `t-1` ve öncesine dayanır.

```
β_{i,t} = Cov_{W}( r^{daily}_{i}, r^{daily}_{mkt} ) / Var_{W}( r^{daily}_{mkt} )
```

W = `BETA_WINDOW_DAYS = 126`, en az `0.8·W` gözlem (`BETA_MIN_COVERAGE`), popülasyon
varyansı. Rezidüalizasyon (kesişimsiz):

```
r̃_{i,t} = r_{i,t} - β_{i,t} · r_{mkt,t}            (residualize)
```

**İleri yön** (`market_neutral_forward`): GEÇMİŞ günlük getirilerden tahmin edilen beta,
İLERİ piyasa hareketine uygulanır → ileri rezidüel getiri `resid_fwd`. Bu, Mod-A ve
Mod-C'nin IC'yi üzerinde hesapladığı seridir.

### 4.3 Conjugate uyum — Mod-A'nın 3-parçalı PASS bariyeri

Section 4.1. Evren, **likidite-katmanlı çift-randomizasyon** ile iki kola (`X_1`, `X_2`)
ayrılır: isimler ADV'ye göre sıralanır, komşu çiftler tohum-sabit yazı-tura ile bölünür
(her kolda eşit likidite). `R = 50` tohum üzerinde tekrarlanır. Beta TÜM panelde **bir
kez** tahmin edilip kola dilimlenir (yapısal kol bağımsızlığı). PASS, **üç koşulun da**
sağlanmasıdır:

```
(1)  median_R( t_IC^{cross} )  >  2.0      HER İKİ yönde (X_1→X_2 ve X_2→X_1)
(2)  sign_consistency          >= 0.90     (IC işaretinin kollar arası tutarlılığı)
(3)  PBO_CSCV                  <  0.50      (gerçek median-rank PBO; proxy DEĞİL)
```

(`AGREEMENT_CROSS_IC_T_MIN=2.0`, `SIGN_CONSISTENCY_MIN=0.90`, `PBO_THRESHOLD=0.50`.)

### 4.4 Residual cross-sectional korelasyon (AYRI hesap, Section 4.2)

Conjugate uyumdan **kasıtlı olarak ayrı** tutulur (4.3 karıştırma-yasağı). İki kolun
aktif-getiri eş-hareketi bir **permütasyon null**'una karşı bayraklanır: gözlenen
kol-korelasyonu, `RESIDUAL_NULL_RESAMPLES=200` rastgele yeniden-bölmeden kurulan null
dağılımının `RESIDUAL_CORR_NULL_PCTILE=95`'inci yüzdesini aşıyorsa `residual_corr_flag=True`.
Bu, "kollar paylaşılan bir ortak-faktör tarafından sürülüyor mu?" dedektörüdür
(RR-Y1-008'in hi52 confound'unu yakalayan aynı makine).

### 4.5 Gerçek CSCV PBO (Bailey & Lopez de Prado) — `pbo.py`

Basit proxy (`P(OOS Sharpe < 0)`) overfit'i **göremez**: bir strateji pozitif OOS Sharpe
verip yine de birçok adayın IS-en-şanslısı olabilir. Gerçek CSCV, conjugate bağlama
şöyle eşlenir:
- Seçilen "config"ler **cross-sectional sort-bucket'ları** (decile'lar, `PBO_N_BUCKETS=10`),
  split'ler değil. (Config'ler split olsaydı, gerçek bir faktör her split'i iyi yapardı,
  aralarındaki sıralama gürültü olurdu, PBO → 0.5 — gömülü-faktör fixture'ını yanlışlıkla
  fail ederdi. Bucket-as-config bunu çözer.)
- Kombinatoryal yeniden-örnekleme = `R` isim-bölmesi.
- IS = kol `X_1`, OOS = kol `X_2` (ve simetriği; çağıran ortalar).

Her split için IS-en-iyi bucket `b*`'ın OOS göreli sırasının logit'i:

```
ω      = avg_rank(b* OOS değeri) / (n_valid + 1)            (Bailey-LdP ortalama-rank)
λ      = log( ω / (1 - ω) )
PBO    = (λ < 0 olan split oranı)
```

Saf gürültü → ~0.5; IS→OOS transfer eden bucket sırası → ~0; ters sıra → ~1. En az 2
ortak-geçerli bucket gerekir; dejenere bucket'lar (`MIN_NAMES_PER_BUCKET=3` altı) NaN
gelir ve dışlanır.

### 4.6 Deflated Sharpe Ratio — trial-count deflation (`dsr.py`)

Çoklu-test / arama-overfit'i **DSR'ın N-deflasyonu** yakalar (bucket-PBO DEĞİL — o
tek-prototip-içi overfit'i ölçer; farklı katman). Dürüst denenen-config sayısı `N`
(Stage-0 `denenen_konfig_sayisi`) Bailey-LdP `E[max]` dereceli-istatistiğini besler:

```
E[max_N] = (1 - γ)·Φ^{-1}(1 - 1/N) + γ·Φ^{-1}(1 - 1/(N·e)),   γ = Euler-Mascheroni
```

`N <= 1 → E[max]=0` (tek deneme çoklu-test şişmesi taşımaz; DSR pre-FAZ-4 ile
byte-özdeş). Deflation benchmark:

```
denom² = 1 - skew·SR + (kurt-1)/4 · SR²
se_SR  = sqrt( denom² / (T-1) )
benchmark_sr = se_SR · E[max_N]
```

Bu, commit'li `compute_dsr`'ye `benchmark_sr` olarak verilince kanonik deflated DSR
`Φ(SR/se_SR - E[max_N])`'yi tam olarak verir. **Strangler:** commit'li tahminci yeniden
KULLANILIR, asla yeniden yazılmaz. `DSR_MIN = 0.95`.

### 4.7 Benchmark floor — reel getiri eşiği (`benchmark.py`, Section 6)

Donmuş kural:
- **Reel-deflate:** her zaman TÜFE (2019+, panel boyunca finite).
- **Benchmark-floor:** 2022-07 öncesi = yalnız-TÜFE; 2022-07+ = `max(TÜFE, TLREF)`.
- **Sessiz-NaN tuzağı (d213 emsali):** temiz TLREF serisi 2022-07 öncesi NaN'dır. Floor
  penceresi bu bölgeye uzanırsa NaN'ın `max`'ı sessizce çökertmesine İZİN VERİLMEZ —
  gard-RAISE (mesaj kaydedilir) ve o pencere için yalnız-TÜFE'ye düşülür.

TÜFE/TLREF **seviye** serileridir, dolayısıyla yıllıklaştırma takvim-günü CAGR'dir
(`asof` ile, snapshot'ların aylık indeksine dayanıklı):

```
CAGR = (level(d1) / level(d0)) ^ (365.25 / days) - 1
real_active = (1 + nominal_active) / (1 + TÜFE_ann) - 1
beats = real_active > max(TÜFE_ann, TLREF_ann)
```

### 4.8 Mod-C — rejim-içi ileri time-holdout persistence (RR-Y1-010)

Çekirdek araştırma sorusunu doğrudan yanıtlar: bir cross-sectional faktörü bir EĞİTİM
zaman-penceresinde dondur, forward rank-IC'sini AYNI REJİM içindeki SONRAKİ bir held-out
penceresinde ölç; aralarına bir **embargo** (= ileri-getiri ufku) konularak inşa-dönemi
getirisinin sınırı geçmesi engellenir.

```
boundary  = holdout_start
holdout   = eval_dates[ >= boundary ]
pre       = eval_dates[ < boundary ]
train     = pre[ : len(pre) - embargo_h ]              (embargo purge)
```

Persistence PASS **mevcut bariyeri yeniden kullanır** (yeni tunable YOK):

```
persistence_pass = (holdout_ic_t > agreement_t_min[=2.0])  AND  sign(holdout_IC) == sign(train_IC)
```

Güç hakkındaki dürüstlük bariyeri yumuşatarak değil, **ayrı holdout güven niteliği** ile
taşınır (§5). Dejenere bölme (sınır eval penceresi dışında, ya da train/holdout `< lag+3`)
→ `holdout_persistence_pass=None` + guard mesajı, yanıltıcı sayı değil.

---

## 5. Güven nitelikleri (confidence qualifiers)

İkisi de **yalnızca ek (additive)**: pass/fail bayraklarını ASLA değiştirmez, keep-bar'lara
ortogonaldir (DEC-049 dokunulmaz). Bir ölçümün **güvenilirlik ön-koşullarının** sağlanıp
sağlanmadığını niteler. Öncelik her ikisinde de: **confounded > low > high**.

### 5.1 Mod-A — `assess_agreement_confidence` (RR-Y1-009)

| Grade | Tetikleyici |
|-------|-------------|
| `CONFOUNDED` | `residual_corr_flag` (paylaşılan ortak-faktör) **VEYA** tek-rejim eval penceresi. |
| `LOW` | kol < `AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE=50` **VEYA** R < `AGREEMENT_MIN_R_FOR_HIGH_CONFIDENCE=50`. |
| `HIGH` | hiçbiri tetiklenmedi. |

RR-Y1-008'in kapattığı boşluk: bilinen-ölü bir momentum-proxy, küçük-kollu tek-rejim
pencerede `agreement_pass=True` üretmişti. Conjugate'in dar sorusu ("isim-spesifik
overfit yok") doğru yanıtlanmıştı ama sonuç rejim-içi ortak-faktör artefaktıydı.

### 5.2 Mod-C — `assess_holdout_confidence` (RR-Y1-010)

| Grade | Tetikleyici |
|-------|-------------|
| `CONFOUNDED` | holdout `REGIME_SPLIT`'i geçiyor **VEYA** holdout penceresinde residual flag. |
| `LOW` | `n_holdout_obs < HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE=60`. |
| `HIGH` | hiçbiri tetiklenmedi. |

**Zıt-ama-tutarlı rejim semantiği (kritik nüans):**
- **Mod-A:** tek-rejim eval penceresi = ŞÜPHELİ (rejim-içi ortak-faktör artefaktı temiz
  bir conjugate PASS'i taklit edebilir).
- **Mod-C:** tek-rejim = TASARIM, confound değil (soru tam olarak "tek rejim içinde ileri
  taşır mı"). Buradaki confound, holdout penceresinin `REGIME_SPLIT`'i (2022-01-01)
  GEÇMESİDİR — train bir rejimde, holdout diğerine taşarsa "aynı-rejim persistence"
  sorusu kirlenir.

Bu yüzden iki ayrı enum'dur (`AgreementConfidence` vs `HoldoutConfidence`), tek bir
"single-regime → confounded" kuralı değil.

---

## 6. Ön-kayıt disiplini (Stage-0 + Lockbox)

### 6.1 Stage-0 — hipotezi ölçümden ÖNCE dondur (`stage0_validator.py`)

`harness(..., stage0_path=...)` verildiğinde motor `require_stage0` ile şunları zorlar:
dosya MEVCUT, şema-geçerli, `frozen_before_results is True`, ve (opsiyonel) frozen
snapshot içerik-hash'i (`sha256[:16]`, d213 emsali) tutuyor. Dosya yoksa → **çalışmayı
reddeder** (post-hoc-lock, Section 5).

Zorunlu alanlar (`REQUIRED_FIELDS`, 18 adet): `prototip_id`, `hipotez`, `tutunma_noktasi`
(`cross_sectional`/`timing`/`panel`), `split_modu` (`A`/`B`/`A+B`), `psi`,
`faktor_notrleme` (boş-olmayan liste, `market` minimum), `embargo_h`, `split_arm_floor`,
`sort_depth`, `hedef_rejim`, `frekans` (`daily`/`monthly`), `getiri_tabani`, `keep_bar`
(`pbo_max` + `dsr_min` anahtarları zorunlu), `denenen_konfig_sayisi` (→ DSR deflation N),
`frozen_before_results`, `date_frozen`, `snapshots_content_hash_sha256_prefix`,
`strangler_constraints`. **monthly → split_modu 'A'** zorunlu.

Opsiyonel alanlar (yoksa `None`, geriye dönük uyumlu): lockbox (`lockbox_spec`,
`lockbox_content_hash`) ve Mod-C kaydı (`eval_window_start`, `eval_window_end`,
`holdout_start`).

### 6.2 Lockbox — tek-atışlık held-out kilidi (`lockbox.py`)

İş akışı: discovery set'te yinele → DONDUR → bağımsız veride **bir KEZ** değerlendir.
Stage-0 *tasarımı* dondurur; lockbox ek olarak bir held-out veri alt-kümesini mühürler
(isme, zaman bloğuna ya da ikisine göre) ve şu koşullar sağlanmadıkça skorlamayı
reddeder: Stage-0 mevcut + frozen + `lockbox_fingerprint(panel)` == kayıtlı hash. Sonra
değerlendirmeyi **consumed** olarak işaretler — mühürlü set bir daha tuning yüzeyi
olamaz.

```
lockbox_fingerprint = sha256( names_sorted | dates_sorted | close_float64_bytes )[:16]
```

Marker dosyası (`{stem}.lockbox-consumed.json`) **commit edilmek üzere tasarlanmıştır** —
git-ignored DEĞİL. Taze `git checkout` sonrası marker mevcut olduğundan ikinci koşu
reddedilir (inkar-edilemez disiplin). Marker gerçek veri taşımaz: yalnız `prototip_id`,
16-karakter hash, `denenen_konfig_sayisi`, UTC `consumed_at`. Tüketim, harness'ın DÖNMEDEN
ÖNCEKİ SON eylemidir — koşu ortasında çökme lockbox'ı yakmaz.

---

## 7. Modlara göre kullanım örnekleri

### 7.1 Mod-A — isim-bölme conjugate (cross-sectional faktör)

```python
spec = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY,
                 R=50, sort_depth=SortDepth.TERCILE)
out  = harness(panel, sig, spec, DialConfig())
assert out.agreement_pass in (True, False)
# Oku: agreement_pass + agreement_confidence (HIGH/LOW/CONFOUNDED) + pbo
```

### 7.2 Mod-B — zamansal CPCV (timing sinyali)

```python
spec = SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.DAILY,
                 cpcv_n=10, cpcv_k=2, embargo_h=sig.construction_window)
out  = harness(panel, sig, spec, DialConfig())
# Oku: dsr, dsr_n_trials, pbo (proxy -- not'a bak), pooled OOS NW-t
```

### 7.3 Mod-C — rejim-içi ileri time-holdout (RR-Y1-010)

```python
spec = SplitSpec(split_mode=SplitMode.TIME_HOLDOUT, frequency=Frequency.DAILY,
                 holdout_start="2024-09-01", embargo_h=sig.construction_window)
out  = harness(panel, sig, spec, DialConfig())
# Oku: holdout_persistence_pass + holdout_confidence + (train_ic_t vs holdout_ic_t)
```

### 7.4 PANEL — A+B birlikte

```python
spec = SplitSpec(split_mode=SplitMode.PANEL, frequency=Frequency.DAILY)
out  = harness(panel, sig, spec, DialConfig())
# Hem agreement_* (Mod-A) hem dsr (Mod-B) dolar. Mod-C PANEL'e KATILMAZ (kasıtlı).
```

---

## 8. Çıktıyı okuma rehberi

Motor karar vermez; aşağıdaki **birlikte-okuma** mantığı önerilir:

1. **Tradeable mi?** `net_active_ann > 0` **ve** `beats_benchmark_floor is True`
   (reel getiri max(TÜFE,TLREF)'i yeniyor mu). Brüt pozitif ama net negatifse → maliyet-öldü.
2. **İstatistiksel olarak gerçek mi?** `nw_t` büyük, `pbo < 0.50`, `dsr >= 0.95`.
3. **Overfit değil mi (Mod-A)?** `agreement_pass is True` **ve** `agreement_confidence is HIGH`.
   `CONFOUNDED`/`LOW` ise PASS'e güvenme — `agreement_confidence_reasons`'ı oku.
4. **İleri taşıyor mu (Mod-C)?** `holdout_persistence_pass is True` **ve**
   `holdout_confidence is HIGH`.
5. **Rejim-kararlı mı?** `per_regime` pre/post 2022 her iki kolda da aynı işaret mi.
6. **Curve-fit değil mi?** `plateau_map` komşu (sort_depth × ufuk) noktalarında stabil mi.
7. **Gardlar:** `guard_messages` ve `notes` boş mu — değilse hangi alan neden `None`?

> **Altın kural:** `None` bir başarısızlık değil, **dürüst bir "üretilmedi"**dir. Mesela
> Mod-A-only koşuda `dsr` None'dur (DSR Mod-B'nin zamansal-Sharpe ölçüsüdür); `null_percentile`
> ve `deflated_oos_t` Faz-3'te bacaklar tarafından üretilmez.

---

## 9. Donmuş sabitler (tek doğru kaynak: `config.py`)

| Sabit | Değer | Rol |
|-------|-------|-----|
| `IC_TYPE` | `spearman` | Cross-sectional rank-IC. |
| `MIN_NAMES_CROSS_SECTION` | `30` | IC için min isim. |
| `NW_LAG_DAILY` / `NW_LAG_MONTHLY` | `5` / `3` | HAC bandwidth. |
| `NW_VAR_FLOOR_EPS` | `1e-12` | Sıfıra-yakın-varyans NaN tabanı. |
| `BETA_WINDOW_DAYS` | `126` | Beta penceresi. |
| `BETA_MIN_COVERAGE` | `0.8` | Min beta kapsamı. |
| `SPLIT_R_MIN` | `50` | Mod-A isim-bölme sayısı. |
| `MIN_NAMES_PER_ARM` | `50` | Kol-başına min isim. |
| `AGREEMENT_CROSS_IC_T_MIN` | `2.0` | Conjugate t eşiği. |
| `SIGN_CONSISTENCY_MIN` | `0.90` | İşaret tutarlılığı. |
| `PBO_THRESHOLD` | `0.50` | Gerçek CSCV PBO tavanı. |
| `PBO_N_BUCKETS` | `10` | PBO decile sayısı (sort_depth'ten DECOUPLED). |
| `MIN_NAMES_PER_BUCKET` | `3` | Dejenere-bucket gardı. |
| `RESIDUAL_CORR_NULL_PCTILE` | `95` | Residual korelasyon null yüzdesi. |
| `RESIDUAL_NULL_RESAMPLES` | `200` | Permütasyon null yeniden-bölmeleri. |
| `CPCV_DAILY_N` / `CPCV_DAILY_K` | `10` / `2` | Mod-B CPCV blokları. |
| `DSR_MIN` | `0.95` | DSR tabanı. |
| `DSR_DEFAULT_N_TRIALS` | `1` | Stage-0 yoksa → deflation yok. |
| `EULER_MASCHERONI` | `0.5772156649` | E[max] dereceli-istatistik. |
| `AGREEMENT_MIN_ARM/R_FOR_HIGH_CONFIDENCE` | `50` / `50` | Mod-A güven tabanı. |
| `HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE` | `60` | Mod-C güven tabanı (directional, deployable DEĞİL). |
| `REGIME_SPLIT` | `2022-01-01` | Manuel rejim sınırı. |
| `BENCHMARK_TLREF_FROM` | `2022-07` | TLREF floor'a girdiği tarih. |
| `LIQUID_ADV_MIN_TL` | `1e7` | Likidite tabanı (ADV-TL). |
| `TRADING_DAYS_YR` | `252.0` | Getiri-serisi yıllıklaştırma. |

**C12 golden çıpası:** `C12_GOLDEN_GROSS_NWT=6.928414`, `C12_GOLDEN_NET_NWT=-6.274774`
@ `C12_GOLDEN_NW_LAG=10`, `C12_GOLDEN_N_POOLED=1375`. Bu, motorun gerçek veride
determinist olduğunu kanıtlayan byte-yeniden-üretim testidir; metodolojik doğruluğun
kanıtı DEĞİL (o, 3 sentetik Mod-A fixture + sentetik-null üzerinde durur).

---

## 10. Garantiler ve sınırlar

**Garantiler:**
- **Sıfır regresyon:** ek alanlar/modlar varsayılan `None`; mevcut modlar byte-değişmez.
- **PM-1 uyumu:** her ağırlık vektörü `assert_pm1_compliant`'tan geçer; nakit-kapısı RAISE.
- **Look-ahead-safe:** beta `shift(1)` ile geçmişe dayanır; Mod-B/Mod-C embargo purge yapar.
- **Determinizm:** tohum-sabit (`seed`); C12 golden byte-byte yeniden-üretilir.
- **Strangler:** commit'li motorlar salt-okunur; `test_engine_no_lab_import.py` lab-import'u yasaklar.

**Dürüst sınırlar:**
- **Mod-C BIST 2019-2026'da yapısal olarak güç-fakiridir** (az sayıda örtüşmeyen rejim-içi
  ileri holdout). `HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE=60` bir directional tabandır,
  deployable-güven eşiği değil. Değer = kavramsal-doğru enstrüman + 2026-2027 ileri dönemine
  hazırlık.
- **Faz-3'te üretilmeyen alanlar:** `null_percentile`, `mirror_active_ann` (fair-null
  resampler kapsam dışı), `deflated_oos_t` (cut-family deflation wire değil). Hepsi `None` +
  not, asla uydurulmaz.
- **Mod-B PBO bir basit-proxy'dir** (`pbo_is_simplified_proxy=True`); gerçek CSCV
  median-rank PBO Mod-A çekirdeğine aittir.

---

## 11. İlgili belgeler

- Tasarım: `RR-Y1-005-TEST-MOTORU-TASARIM` v0.2
- Matematik: `RR-Y1-005B-MATEMATIKSEL-SPEC` v1.1
- Mod-C verdict: `docs/research/RR-Y1-010-intra-regime-time-holdout.md`
- Güven niteliği (Mod-A): `docs/research/RR-Y1-009-*`
- Registry: `docs/RESEARCH_REGISTRY.md`
- Karar geçmişi: `docs/DECISIONS.md`
