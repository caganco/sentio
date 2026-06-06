# SPEC_IC_FRAMEWORK_1 — Information Coefficient Ölçüm ve Weight Kalibrasyon Çerçevesi

**Spec:** D-132  
**Versiyon:** 1.0 | **Tarih:** 24 Mayıs 2026  
**Durum:** 📋 maintainer Review — arastirma katmani başlamaz  
**Tahmini uygulama süresi:** 6–8 saat (4 faz paralel geliştirilebilir, merge sırası önemli)  
**Dayanak:** RR-010 §2 (metodoloji), §3 (16 karar), §4 (pseudocode), §5 (akademik kaynaklar)  
**Bağlı:** CB-010 (statik weight savunulamazlığı), DEC-015 (Alpha Attribution Faz 1)

---

## 0. Özet

BIST OS'un mevcut Alpha Attribution altyapısı (DEC-015) Layer × forward-return kaydını parquet formatında yapıyor ve `ICCalculator` ile Spearman IC hesaplıyor. Ancak framework **eksik** bileşenler içeriyor: BH-FDR çoklu test düzeltmesi yok, sektör-nötr IC yok, `ic_history` kalıcı zaman serisi yok, Bayesian weight kalibrasyonu yok, decay monitörü yok, delisted ticker koruması yok. Bu SPEC, DEC-015 üzerine kurularak RR-010'un öngördüğü eksiksiz IC framework'ünü 4 aşamalı arastirma katmani specleriyle tanımlar.

**Kapsam sınırı:** `src/` üretim lojiği değişmez. Yeni bileşenler `src/analytics/` ve `src/data/` altında eklenir; `thresholds.py` yeni sabitleri alır; `MASTER_WEIGHTS` τ=0 aşamasında statik kalır.

---

## BÖLÜM 1 — Gap Analizi: Mevcut Durum vs RR-010 Faz 1

### Q1 — `signal_logger.py` çıktısı panel formatında mı?

**Cevap: ✅ MEVCUT — Wide format, IC hesabı için yeterli**

`src/data/signal_logger.py` (`SignalLogger` + `ReturnFiller`) iki paralel depolama katmanı yazar:

| Format | Yol | Kimden yazılır |
|--------|-----|----------------|
| Hive-partitioned parquet | `data/signal_logs/year=YYYY/month=MM/day=DD/signals.parquet` | `SignalLogger.log_signal()` |
| Flat daily parquet | `data/signal_logs/YYYY-MM-DD.parquet` | `alpha_attribution.write_daily_snapshot()` |
| Forward returns (append-only) | `data/signal_logs/returns.parquet` | `ReturnFiller.fill()` |

`SignalLogRecord` şeması: `date × symbol × {l1_tech_score, l2_macro_score, l3_kap_score, l4_sent_score, l5_sm_score, l6_risk_score, viop_score, composite_score, conviction_score, regime_label, liquidity_tier, …}`. Bu wide-format bir paneldir; `ICCalculator` bunu doğrudan tüketir (`groupby("date")` ile cross-sectional IC hesabı).

**Kalan gap'ler (yeni spec ile kapatılacak):**

| Gap | Kök neden |
|-----|-----------|
| `IC_HORIZON_T10 = 10` yok | thresholds.py'de tanımlanmamış (sadece T1/T5/T20/T60 var) |
| Sector-adjusted returns yok | `ReturnFiller` sektör demean uygulamıyor |
| `h5_sector_adj`, `h20_sector_adj` kolonu yok | `ReturnRecord` şemasında tanımsız |

---

### Q2 — SQLite şeması: hangi tablolar mevcut, hangileri yeni?

**Cevap: ⚠️ Kısmi — Analitik katman parquet tabanlı; kritik IC tablolar eksik**

**Mevcut tablolar (bist_data.db):**

```sql
prices            (date, ticker, open, high, low, close, volume)
portfolio         (ticker, quantity, avg_cost, updated_at)
watchlist         (ticker, reason, date_added)
kap_events        (disclosure_index, symbol, published_at, …)
```

**RR-010 §4 tablolarının eşleme durumu:**

| RR-010 §4 tablosu | Mevcut durum | Notlar |
|-------------------|--------------|--------|
| `layer_scores` | ✅ KARŞILANMIŞ | Flat daily parquets ile karşılanmış; SQLite versiyonu gerekmez |
| `forward_returns` | ⚠️ KARŞILANMIŞ (eksik) | `returns.parquet` mevcut, T10 ve sector_adj eksik |
| `ic_history` | ❌ YOK | Günlük JSON rapor var ama persistent zaman serisi yok |
| `weight_history` | ❌ YOK | Hiç yok |
| `delisted_tickers` | ❌ YOK | Hiç yok |

**Mimari karar:** RR-010 §4 SQLite şemasını birebir uygulama. Bu SPEC analitik verilerini parquet'te tutar (mevcut tasarım ile tutarlı); SQLite'a IC/weight verisi yazılmaz. Yeni dosyalar:

```
data/analytics/
  ic_history.parquet        ← ic_history tablosu yerine
  weight_history.parquet    ← weight_history tablosu yerine
  delisted_tickers.json     ← delisted_tickers tablosu yerine
```

---

### Q3 — `forward_returns` hesabı production'da mı?

**Cevap: ✅ KISMEN — ReturnFiller çalışıyor; T10 ve sector_adj eksik**

`ReturnFiller` (`src/data/signal_logger.py`, satır 251–355) `daily_update.py` içinde çağrılıyor (satır ~1070). Mevcut horizon'lar: T1, T5, T20, T60. `returns.parquet` append-only, hive-dışı. ReturnFiller `BISTCalendar` ile trading day'leri doğru hesaplıyor.

**Kalan gap'ler:**

| Gap | Etki | Çözüm |
|-----|------|-------|
| `IC_HORIZON_T10` yok | 10d horizon IC matrisi hesaplanamıyor | thresholds.py'e ekle |
| Sector-adjusted returns yok | `group_adjust=True` IC hesabı için raw IC kullanılıyor (sektör bias mümkün) | `ReturnFiller` sektör demean adımı ekle |
| `returns.parquet` şu an boş | Yalnızca 4 günlük veri; hiçbir horizon dolmadı | Veri birikimi gerekiyor (60 gün) |
| `price_limit_hit` her zaman False | Devre kesici (fiyat bandı) tespiti yapılmıyor | G-22 grunt task (kapsam dışı bu spec) |

---

### Q4 — `delisted_tickers` tablosu/mekanizması var mı?

**Cevap: ❌ TAMAMEN YOK**

`ic_dashboard.py` satır 87'de açıkça belgelenmiş: *"Survivorship: Faz 1 -- yfinance + manual snapshot (bias accepted)"*. Bu bilinçli bir Faz 1 kararı; ancak RR-010 §2 B11'e göre delisted ticker'lar (ASYAB, ULUUN türü) IC'yi şişirir.

**Sonuç:** Survivorship bias Faz 1'de kabul edilmiş, bilinçli trade-off. Bu SPEC `delisted_tickers.json` dosyası oluşturur ve `ReturnFiller`'ı uyarır; tam KAP entegrasyonu Faz 3'e ertelenir.

---

### Q5 — `compute_daily_ic` eşdeğeri bir job var mı?

**Cevap: ⚠️ KISMEN — ICCalculator mevcut; otomatik cron job yok; kritik bileşenler eksik**

**Mevcut:**
- `src/analytics/ic_calculator.py` — `ICCalculator` sınıfı: cross-sectional Spearman IC, rolling IC, Alphalens entegrasyonu, LOO attribution
- `src/reporting/ic_dashboard.py` — CLI + JSON rapor
- `src/analytics/layer_attribution.py` — LOO (Leave-One-Out) ve Shapley
- `data/analytics/ic_report_YYYY-MM-DD.json` — Günlük JSON raporlar (tümü NO_DATA; yalnızca 4 gün veri)

**Eksik:**

| Eksik bileşen | RR-010 referans | Öncelik |
|---------------|-----------------|---------|
| `daily_update.py`'den otomatik IC çalıştırma | §4 `compute_daily_ic()` | Faz 1 |
| BH-FDR çoklu test düzeltmesi | §2 B4, Karar #6 | Faz 1 |
| Sektör-nötr IC (`group_adjust=True`) | §2 B6, Karar #13 | Faz 1 |
| `ic_history.parquet` persistent birikimi | §4 `ic_history` tablosu | Faz 1 |
| Decay slope monitörü (30/60/120d rolling) | §2 B12, Karar #14 | Faz 2 |
| Bayesian shrinkage weight hesabı | §2 B9-B10, Karar #9-10 | Faz 3 |
| Re-calibration trigger'ları | §6 madde (a-f) | Faz 3 |
| `weight_history.parquet` | §4 `weight_history` | Faz 3 |
| `delisted_tickers.json` | §2 B11, Karar #15 | Faz 2 |
| `IC_HORIZON_T10 = 10` (thresholds.py) | Karar #3 (10d matrix) | Faz 1 |
| `IC_INVESTABLE_MONTHS_MIN` 24 → 2 revizyon | RR-010 §6 "60 gün minimum" | Faz 1 |

**Kritik Not — `IC_INVESTABLE_MONTHS_MIN = 24` uyumsuzluğu:**

`thresholds.py` satır 637: `IC_INVESTABLE_MONTHS_MIN: int = 24` → ~504 trading günü. Bu RR-010 §6'nın "60 işlem günü minimum" eşiğiyle çelişiyor. RR-010'da 60 gün ilk Bayesian update eşiği (τ=0.20), investability gate değil. Bu SPEC bu ayrımı korur:
- `IC_INVESTABLE_MONTHS_MIN = 24` → `IC_BAYESIAN_TAU_MIN_DAYS = 60` adlı yeni sabit eklenir
- `IC_INVESTABLE_MONTHS_MIN` 24'te kalır (uzun vadeli "INVEST" statüsü için doğru eşik)
- 60 gün eşiği weight calibrator gating içindir, investability için değil

---

## BÖLÜM 2 — Mimari Kararlar

Her gap için: hangi dosya değişiyor, ne ekleniyor, neden.

### K-01: T10 horizon ve thresholds.py yeni IC sabitleri

**Mevcut dosya:** `src/signals/thresholds.py`  
**Ne değişiyor:** Yeni sabitler eklenir, mevcut hiçbir sabit silinmez

```python
# Yeni eklenecek sabitler (RR-010 Karar #3)
IC_HORIZON_T10: int = 10           # 10d horizon — cross-window matrix için

# Bayesian weight kalibrasyon eşikleri (RR-010 §2 B10, Karar #9-10)
IC_BAYESIAN_TAU_MIN_DAYS:  int = 60    # τ=0.20 giriş eşiği
IC_BAYESIAN_TAU_FULL_DAYS: int = 730   # τ=0.95 tam bağımsızlık

# IC izleme eşikleri (RR-010 §2 B12)
IC_DECAY_SLOPE_WARN:    float = -0.001   # 30/60/120d rolling slope uyarı
IC_DECAY_SLOPE_REVIEW:  float = -0.002   # slope < bu → layer "review"
IC_FDR_ALPHA:           float = 0.10     # BH-FDR significance seviyesi
IC_FDR_M_TESTS:         int   = 12       # 6 layer × 2 primary horizon

# Veri yolu sabitleri (analytics katmanı)
IC_HISTORY_PATH:      str = "data/analytics/ic_history.parquet"
IC_WEIGHT_HISTORY_PATH: str = "data/analytics/weight_history.parquet"
DELISTED_TICKERS_PATH:  str = "data/analytics/delisted_tickers.json"
SECTOR_RETURNS_CACHE:   str = "data/analytics/sector_returns_cache.parquet"
```

**Neden:** thresholds.py tek sabit kaynağı prensibi (CLAUDE.md Dokunulmaz Prensipler). Yeni analitik sabitler de buraya girer.

---

### K-02: ReturnFiller — T10 ve sector-adjusted returns

**Mevcut dosya:** `src/data/signal_logger.py`  
**Ne değişiyor:** `ReturnRecord` ve `ReturnFiller._fill_horizon()` genişler

**Yeni `ReturnRecord` alanları:**
```python
class ReturnRecord(BaseModel):
    signal_date: date
    symbol: str
    horizon: int          # 1 | 5 | 10 | 20 | 60  ← T10 eklendi
    forward_return: float
    sector_adjusted_return: float | None = None   # ← YENİ
    sector: str | None = None                     # ← YENİ (sector_mapping.json'dan)
    price_limit_hit: bool
    filled_at: datetime
```

**`ReturnFiller` değişimi:** `_fill_horizon()` içinde `sector_mapping.json`'dan sektör okunur; sektör ortalaması hesaplanıp `sector_adjusted_return = fwd_return - sector_mean` olarak yazılır.

**Neden:** RR-010 Karar #13 ve §2 B6. `group_adjust=True` IC hesabı için sector-adjusted return gereklidir. `data/sector_mapping.json` zaten mevcut; ek veri kaynağı gerekmez.

---

### K-03: BH-FDR düzeltmesi — `ICCalculator.compute_fdr_panel()`

**Mevcut dosya:** `src/analytics/ic_calculator.py`  
**Ne değişiyor:** Yeni method eklenir; mevcut hiçbir method değişmez

```python
@dataclass
class FDRResult:
    """BH-FDR panel for 12 tests (6 layer × 2 primary horizon)."""
    as_of_date: date
    results: list[dict]    # [{layer, horizon, ic, p_raw, p_adj, significant}, ...]
    n_tests: int
    alpha: float
    method: str            # "fdr_bh"

def compute_fdr_panel(self, as_of_date: date) -> FDRResult:
    """
    Dayanak: RR-010 §2 B4, Karar #6
    12 hipotez: 6 layer × {5d, 20d} primary horizons
    statsmodels.stats.multitest.multipletests(method='fdr_bh')
    """
    ...
```

**Neden:** RR-010 §2 B4 (Benjamini & Hochberg 1995). Mevcut `ICCalculator.compute_all()` p-value üretir ama düzeltmez. 24 hipotez için naive α=0.05 → %71 false positive olasılığı (CB-010'un eleştirisi).

---

### K-04: `ic_history.parquet` — persistent IC zaman serisi

**Yeni dosya:** `src/analytics/ic_history.py`  
**Yazar:** Yeni `ICHistoryWriter` sınıfı

**Parquet şeması:**
```
date           (date32)
layer          (string)      # "l1_tech_score" | ...
horizon        (int32)
ic             (float32)
p_value        (float32)
p_adj          (float32)     # BH-FDR düzeltilmiş
significant    (bool)        # FDR sonrası
n_obs          (int32)
group_adjust   (bool)        # sector-nötr mi?
icir_120d      (float32)     # rolling 120d ICIR
decay_slope_30d (float32)    # 30d OLS slope
decay_slope_60d (float32)    # 60d OLS slope
```

**Neden:** Mevcut `ic_report_YYYY-MM-DD.json` günlük anlık görüntü; zaman serisi IC trendini tutmuyor. Bayesian weight update, ICIR hesabı ve decay monitoring için kalıcı geçmişe ihtiyaç var.

---

### K-05: `daily_update.py` entegrasyonu

**Mevcut dosya:** `scripts/daily_update.py`  
**Ne değişiyor:** Mevcut `_write_signal_logs_d107()` bloğundan sonra yeni IC computation adımı

```python
# --- Günlük IC computation (D-132) ---
logger.info(SEP)
logger.info("IC Framework — günlük hesaplama")
try:
    from src.analytics.ic_history import ICHistoryWriter
    writer = ICHistoryWriter()
    writer.run_daily(today)     # IC compute → ic_history.parquet append
except Exception as exc:
    logger.warning("IC daily compute başarısız (non-fatal): %s", exc)
```

**Neden:** RR-010 §4 `compute_daily_ic` cron job gereksinimi. Mevcut `ic_dashboard.py` yalnızca CLI araç; pipeline içine entegre değil. Non-fatal wrapper: IC compute hatası günlük pipeline'ı durdurmaz.

---

### K-06: `src/analytics/weight_calibrator.py` — Bayesian update (Faz 3)

**Yeni dosya:** `src/analytics/weight_calibrator.py`  
**Bağımlılık:** `ic_history.parquet` (K-04), `thresholds.MASTER_WEIGHTS`

**Temel tasarım kısıtı: MASTER_WEIGHTS KOD TARAFINDAN ASLA YAZILMAZ**

Bayesian posterior → `data/analytics/weight_history.parquet`'e yazılır. Üretime geçmesi için:
1. arastirma katmani `weight_history.parquet`'teki önerilen weight'leri rapor eder
2. maintainer değerlendirir
3. maintainer onaylar → ayrı spec ile `thresholds.py` güncellenir

```python
class WeightCalibrator:
    """
    Dayanak: RR-010 §2 B9-B10, Karar #9-10
    τ schedule: 60d→0.20, 180d→0.50, 365d→0.80, 730d→0.95
    min/max: 0.05 ≤ wᵢ ≤ 0.50
    MASTER_WEIGHTS asla değiştirilmez — öneriler weight_history.parquet'e yazılır
    """
    W_PRIOR = None              # thresholds.MASTER_WEIGHTS'ten yüklenir
    SIGMA_PRIOR_DIAG = 0.10**2  # prior uncertainty (He & Litterman 1999)

    def tau_schedule(self, days: int) -> float: ...
    def compute_posterior_weights(self, date: date) -> dict[str, float]: ...
    def check_recalibration_triggers(self, date: date) -> list[str]: ...
    def run_weekly(self, date: date) -> None: ...   # haftalık batch
```

**Neden:** CB-010 ("statik weight savunulamazlığı"). τ=0 aşamasında (< 60 gün) hiçbir şey değişmez. 60. günden itibaren posterior öneriler raporda görünür, uygulama maintainer onayına bağlı.

---

### K-07: `delisted_tickers.json` — survivorship bias koruması (Faz 2)

**Yeni dosya:** `data/analytics/delisted_tickers.json`  
**Bakımı:** arastirma katmani ilk sürümü KAP arşivinden son 5 yıl için manuel doldurur

**Format:**
```json
{
  "version": "1.0",
  "last_updated": "2026-05-24",
  "source": "KAP historical listings",
  "tickers": [
    {"ticker": "ASYAB", "delist_date": "2021-07-15", "reason": "tasfiye"},
    ...
  ]
}
```

`ReturnFiller` delisted ticker için return hesaplamayı atlar (NaN bırakır), `ic_calculator` pairwise drop ile NaN'ları zaten yoksayar.

**Neden:** RR-010 §2 B11, Karar #15. Faz 1'de kabul edilmiş bias (ic_dashboard.py satır 87). Faz 2'de kısmen kapatılır.

---

### K-08: `import-linter` kontrakt güvenliği

**Mevcut `.importlinter` kontratları:**
```ini
[importlinter:contract:signal-layering]   # engine > layers > thresholds
[importlinter:contract:layer-independence] # 6 layer birbirinden bağımsız
```

**Yeni bileşenlerin import güvenliği:**

| Yeni modül | İzin verilen import'lar | Yasak |
|------------|------------------------|-------|
| `src/analytics/ic_history.py` | `thresholds`, `scipy`, `statsmodels`, `pandas` | `engine`, `layers/*` |
| `src/analytics/weight_calibrator.py` | `thresholds.MASTER_WEIGHTS` (read-only), `ic_history` | `engine`, `layers/*` |
| `src/data/signal_logger.py` (değişiklik) | `thresholds`, `bist_calendar` | `engine`, `layers/*` |
| `scripts/daily_update.py` (değişiklik) | Tümü (`scripts/` kontratta yok) | — |

**Yeni kontrakt eklenmesi önerisi (test_architecture.py):**
```ini
[importlinter:contract:analytics-no-engine]
name = Analytics katmanı engine import etmez
type = forbidden
source_modules = src.analytics
forbidden_modules = src.signals.engine
                   src.signals.layers
```

**Neden:** `src/analytics/` → `src/signals/engine` bağlantısı oluşursa (örn. weight_calibrator canlı MASTER_WEIGHTS değiştirmeye çalışırsa) mimari ihlal olur. Kontrakt bu bağlantıyı CI düzeyinde engeller.

---

### K-09: `test_architecture.py` yeni invariant'lar

**Eklenmesi gereken 3 yeni test:**

```python
class TestICFrameworkInvariants:

    def test_master_weights_not_auto_mutated(self):
        """weight_calibrator.py MASTER_WEIGHTS dict'ine runtime'da yazamaz."""
        src = Path("src/analytics/weight_calibrator.py")
        if src.exists():
            content = src.read_text()
            assert "MASTER_WEIGHTS[" not in content, (
                "weight_calibrator.py MASTER_WEIGHTS'e doğrudan yazmaya çalışıyor. "
                "Önerilen weight'ler weight_history.parquet'e yazılmalı."
            )

    def test_ic_constants_single_source(self):
        """IC_BAYESIAN_TAU_MIN_DAYS, IC_FDR_ALPHA thresholds.py'de tanımlı olmalı."""
        from src.signals.thresholds import (
            IC_BAYESIAN_TAU_MIN_DAYS,
            IC_FDR_ALPHA,
            IC_DECAY_SLOPE_WARN,
        )
        assert IC_BAYESIAN_TAU_MIN_DAYS == 60
        assert IC_FDR_ALPHA == 0.10
        assert IC_DECAY_SLOPE_WARN < 0

    def test_analytics_not_importing_engine(self):
        """src/analytics/ modülleri src.signals.engine import edemez."""
        analytics_dir = Path("src/analytics")
        if not analytics_dir.exists():
            return
        for f in analytics_dir.glob("*.py"):
            content = f.read_text()
            assert "from src.signals.engine" not in content, (
                f"{f.name} src.signals.engine'i import ediyor — mimari ihlal"
            )
            assert "import src.signals.engine" not in content, (
                f"{f.name} src.signals.engine'i import ediyor — mimari ihlal"
            )
```

---

### K-10: `MASTER_WEIGHTS` τ=0 aşamasında statik kalır mı?

**Cevap: EVET — τ=0 aşamasında (`IC_BAYESIAN_TAU_MIN_DAYS = 60` dolmadan) mutlak statik**

RR-010 §6 madde 4: *"Minimum 60 işlem günü zorunlu: Layer weight güncelleme (τ=0)... 60d'den önce yapılmaz."*

Mevcut veri durumu: 4 günlük signal log, `returns.parquet` boş. `MASTER_WEIGHTS` (L1=0.25, L2=0.20, L3=0.30, L4=0.12, L5=0.10, L6=0.03) hiçbir değişime uğramaz.

**60. gün sonrası akış:**
1. `weight_calibrator.compute_posterior_weights()` çalışır → önerilen weight'ler `weight_history.parquet`'e yazılır
2. Dashboard bu öneriyi raporlar
3. **maintainer onay verir → ayrı Grunt task (`G-22`) ile thresholds.py güncellenir**
4. PR → CI → yeşil → merge

MASTER_WEIGHTS değeri her ne olursa olsun statik toplamı [0.85, 1.05] aralığında olmalı; `weight_validator.py` bunu CI'da doğrulamaya devam eder.

---

## BÖLÜM 3 — arastirma katmani Spec Taslakları (Faz Sırası)

> **Kural:** Aşağıdaki specler SPEC onayından önce başlamaz. Merge sırası önemli: D-133 → D-134 → D-135 → D-136.

---

### D-133 — IC Framework Faz 1: Temel Altyapı (ÖNCE MERGE ET)

```
GÖREV: IC framework'ü Faz 1 altyapısını kur

KISITLAR:
  - src/signals/engine.py, src/signals/layers/* değişmez
  - MASTER_WEIGHTS değişmez
  - Yeni sabitler SADECE thresholds.py'e gider
  - Tüm yeni analytics modülleri src/analytics/ veya src/data/ altında
  - Her değişiklikten sonra pytest yeşil: python -m pytest tests/ -q --tb=short

BAŞARI KRİTERİ:
  1. thresholds.py yeni sabitler: IC_HORIZON_T10, IC_BAYESIAN_TAU_MIN_DAYS,
     IC_BAYESIAN_TAU_FULL_DAYS, IC_DECAY_SLOPE_WARN, IC_DECAY_SLOPE_REVIEW,
     IC_FDR_ALPHA, IC_FDR_M_TESTS, IC_HISTORY_PATH, IC_WEIGHT_HISTORY_PATH,
     DELISTED_TICKERS_PATH, SECTOR_RETURNS_CACHE
  2. ReturnFiller T10 horizon ekle (thresholds'dan IC_HORIZON_T10 ile)
  3. ReturnRecord: sector_adjusted_return + sector alanları
  4. ReturnFiller._fill_horizon(): sektör demean hesabı (sector_mapping.json kullan)
  5. ICCalculator.compute_fdr_panel() → FDRResult dataclass
     (statsmodels.multipletests, fdr_bh, 6 layer × {T5, T20})
  6. src/analytics/ic_history.py → ICHistoryWriter sınıfı
     (ic_history.parquet append-only, şema K-04'te)
  7. daily_update.py → ICHistoryWriter.run_daily(today) bloğu (non-fatal try/except)
  8. test_architecture.py → TestICFrameworkInvariants (3 test, K-09'da)
  9. python -m pytest tests/test_ic_framework.py -v → min 10 test pass
 10. python -m pytest tests/ -q --tb=short → sıfır regresyon

ETKİLENEN DOSYALAR:
  - src/signals/thresholds.py (sabit ekle)
  - src/data/signal_logger.py (ReturnRecord + ReturnFiller genişlet)
  - src/analytics/ic_calculator.py (compute_fdr_panel ekle)
  - src/analytics/ic_history.py (YENİ)
  - scripts/daily_update.py (IC history writer entegrasyonu)
  - tests/test_architecture.py (3 yeni invariant)
  - tests/test_ic_framework.py (YENİ)

DAYANAK: RR-010 §2 B4 (FDR), §2 B6 (sector), §4 pseudocode, Karar #3/#6/#13

TAHMINI SURE: 2-3 saat
BRANCH: feature/d133-ic-framework-phase1
```

---

### D-134 — IC Framework Faz 2: Decay Monitörü ve Delisted Tickers

```
GÖREV: IC decay slope monitörü + delisted ticker survivorship koruması

KISITLAR:
  - D-133 merge edilmiş olmalı
  - ic_history.parquet mevcut olmalı (D-133 çıktısı)
  - Sadece src/analytics/ ve data/ değişir

BAŞARI KRİTERİ:
  1. ICCalculator.compute_decay(layer, horizon, window_days) → dict:
       {slope_30d, slope_60d, slope_120d, status: "ok"|"warn"|"review"}
     (OLS slope on rolling ic_history dates)
  2. ICHistoryWriter.run_daily() decay slope kolonu yazar (ic_history.parquet)
  3. data/analytics/delisted_tickers.json oluşturulur
     (son 5 yıl KAP arşivinden min 20 ticker, SPEC K-07 formatı)
  4. ReturnFiller: delisted_tickers.json yüklenir; delist_date sonrası
     return hesabı atlanır (NaN → pairwise drop zaten var)
  5. ic_dashboard.py decay slope sütunu ekler (WARN/REVIEW flag CLI'da görünür)
  6. python -m pytest tests/ -q --tb=short → sıfır regresyon

ETKİLENEN DOSYALAR:
  - src/analytics/ic_calculator.py (compute_decay ekle)
  - src/analytics/ic_history.py (decay slope yaz)
  - src/data/signal_logger.py (ReturnFiller delisted skip)
  - src/reporting/ic_dashboard.py (decay column)
  - data/analytics/delisted_tickers.json (YENİ — veri dosyası)
  - tests/test_ic_framework.py (decay test'leri)

DAYANAK: RR-010 §2 B12 (decay), Karar #14 + #15; McLean & Pontiff (2016)

TAHMINI SURE: 1.5-2 saat
BRANCH: feature/d134-ic-decay-delisted
```

---

### D-135 — IC Framework Faz 3: Bayesian Weight Kalibrasyon (60+ gün gerekir)

```
GÖREV: WeightCalibrator — Bayesian posterior weight önerileri

KISITLAR:
  - D-133 VE D-134 merge edilmiş olmalı
  - MASTER_WEIGHTS KESINLIKLE YAZILMAZ — öneriler weight_history.parquet'e
  - Sadece 60+ gün ic_history verisi varsa posterior hesaplanır; yoksa NOOP
  - src/signals/engine.py, src/signals/layers/* dokunulmaz

BAŞARI KRİTERİ:
  1. src/analytics/weight_calibrator.py → WeightCalibrator sınıfı
     - tau_schedule(days) → float (K-06 takvimi)
     - compute_posterior_weights(date) → dict[str, float]
       (Bayesian BL formülü, K-06 pseudocode; prior = MASTER_WEIGHTS)
     - check_recalibration_triggers(date) → list[str]
       (RR-010 §6: ICIR<0/60d, CB-002 rejim flag, kümülatif −2σ kırılması,
        yeni layer ekleme, 180d+ τ update, survivorship listesi değişimi)
     - run_weekly(date) → None (weight_history.parquet'e append)
  2. weight_history.parquet şeması:
       date, layer, weight_posterior, weight_prior, tau_eff,
       icir_60d, icir_120d, triggers (JSON list), method
  3. ic_dashboard.py haftalık weight öneri tablosu (--tier 2 argümanı)
  4. test_architecture.py TestICFrameworkInvariants::test_master_weights_not_auto_mutated pass
  5. src/analytics/weight_calibrator.py → src.signals.engine import YOK
     (K-08 importlinter kuralı)
  6. python -m pytest tests/ -q --tb=short → sıfır regresyon

ETKİLENEN DOSYALAR:
  - src/analytics/weight_calibrator.py (YENİ)
  - src/reporting/ic_dashboard.py (--tier 2 output)
  - data/analytics/weight_history.parquet (çalışma zamanında oluşur)
  - tests/test_weight_calibrator.py (YENİ)

DAYANAK: RR-010 §2 B9-B10, Karar #9-10-11; Black & Litterman (1992); Qian & Hua (2004)

TAHMINI SURE: 2-3 saat
BRANCH: feature/d135-ic-bayesian-calibration
```

---

### D-136 — IC Framework Faz 4: import-linter kontrakt + .importlinter güncelleme

```
GÖREV: analytics katmanı import-linter kontratı

KISITLAR:
  - D-133, D-134, D-135 tümü merge edilmiş olmalı
  - Yalnızca .importlinter ve test_architecture.py değişir

BAŞARI KRİTERİ:
  1. .importlinter'a yeni kontrakt:
       [importlinter:contract:analytics-no-engine]
       name = Analytics katmanı engine import etmez
       type = forbidden
       source_modules = src.analytics
       forbidden_modules = src.signals.engine
                          src.signals.layers
  2. CI'da import-linter çalışır: lint-imports pass
  3. python -m pytest tests/ -q --tb=short → sıfır regresyon

ETKİLENEN DOSYALAR:
  - .importlinter (yeni kontrakt)
  - tests/test_architecture.py (mevcut TestICFrameworkInvariants::
      test_analytics_not_importing_engine zaten var — CI doğrulama)

DAYANAK: CLAUDE.md "Her değişiklikten sonra pytest çalıştır", Dokunulmaz Prensipler

TAHMINI SURE: 20 dakika
BRANCH: feature/d136-ic-importlinter
```

---

## BÖLÜM 4 — Dokunulmazlar ve Riskler

### 4.1 import-linter kontratları — kırılma riski

**Risk:** `src/analytics/weight_calibrator.py` `MASTER_WEIGHTS`'e yazmak için `thresholds.py`'yi import edebilir — bu güvenli. Ancak `src/signals/engine.py`'yi import ederse `signal-layering` kontratı kırılır.

**Önlem:** K-08 + K-09 `test_analytics_not_importing_engine` invariantı. arastirma katmani, `weight_calibrator.py`'de `from src.signals.engine import …` satırı yazarsa CI fail olur.

**Mevcut kontrat güvenliği:**
- `src.analytics` şu an `signal-layering` kontratının dışında → mevcut CI doğrudan analytics'i test etmiyor
- D-136'dan önce `src.analytics` → `src.signals.engine` importu CI tarafından yakalanmaz
- Bu nedenle D-136 en son merge edilmeli (tüm analytics kodu yerleştikten sonra kontrakt eklenmeli)

---

### 4.2 `test_architecture.py` yeni invariant gereksinimi

**Gerekli:** 3 yeni test (K-09'da tam pseudocode verildi):
1. `test_master_weights_not_auto_mutated` — weight_calibrator MASTER_WEIGHTS'e yazmıyor
2. `test_ic_constants_single_source` — IC sabitleri thresholds.py'de
3. `test_analytics_not_importing_engine` — analytics → engine bağlantısı yok

**Mevcut test sayısı:** `python -m pytest tests/ -q | tail -3` ile doğrulama. D-133 sonrası en az +10 test bekleniyor.

---

### 4.3 `MASTER_WEIGHTS` statik kalıyor mu? (τ=0 aşamasında)

**Cevap: EVET, kesinlikle**

Şu an (24 Mayıs 2026): 4 günlük signal log, `returns.parquet` boş. `IC_BAYESIAN_TAU_MIN_DAYS = 60` dolmadan `WeightCalibrator.compute_posterior_weights()` erken çıkış yapar:

```python
def compute_posterior_weights(self, date: date) -> dict | None:
    days = self._count_history_days()
    if days < IC_BAYESIAN_TAU_MIN_DAYS:
        logger.info("WeightCalibrator: %d gün < %d min — prior korunuyor",
                    days, IC_BAYESIAN_TAU_MIN_DAYS)
        return None   # NOOP
```

60. günden itibaren üretilen `weight_history.parquet` öneri dosyasıdır; thresholds.py'yi sıfır otomatik değişiklik yapar. Üretime geçmesi için maintainer onayı (G-22 Grunt task) zorunludur.

---

### 4.4 L6 Risk/Kelly — Bayesian update dışı

RR-010 §6 madde 10: *"L6 Risk/Kelly = 0.03 statik prior: Risk layer'ı ICIR-tabanlı kalibre edilemez (alfa sinyali değil, pozisyon büyütücü). Bayesian update L6'ya uygulanmaz."*

`WeightCalibrator`'da L6 (`risk`) hariç tutulur:
```python
CALIBRATION_LAYERS = ["l1_tech_score", "l2_macro_score", "l3_kap_score",
                       "l4_sent_score", "l5_sm_score"]
# L6 kalibrasyona girmez; posterior normalize edilirken L6=0.03 sabit tutulur
```

**DEC-018 kaydı önerilir:** "L6 Bayesian dışı — statik 0.03 korunur, gerekçe RR-010 §6 madde 10"

---

### 4.5 L4 hybrid NLP weight — IC hurdle'a tabi

RR-010 §6 madde 9: *"L4 SUSPENDED (RR-008 hybrid'e geçişte): … t > 3.0 hurdle'ı geçmesi gerek; aksi W_PRIOR[3] = 0 kalır."*

Mevcut: `MASTER_WEIGHTS["sentiment"] = 0.12`. Bu specin kapsamında değiştirilmez. RR-008 (hybrid NLP) implement edildiğinde ayrı spec + t > 3.0 (`IC_INVESTABLE_TSTAT_MIN` değil, yeni layer için `IC_NEW_LAYER_TSTAT_HURDLE = 3.0` sabiti) uygulanır.

**G-23 Grunt task önerisi:** `IC_NEW_LAYER_TSTAT_HURDLE: float = 3.0` thresholds.py'e ekle (Harvey, Liu, Zhu 2016 RFS kaynağı; RR-010 Karar #7)

---

### 4.6 Transaction cost gerçekliği — IC investability yorumu

RR-010 §6 madde 12: Round-trip retail komisyon %0.25-0.40. `net_IC ≈ gross_IC × (1 − turnover × 0.003)`.

`IC_INVESTABLE_MEAN_MIN = 0.03` — bu gross IC eşiği. Net IC pozitif kalması için `0.03 × (1 − turnover × 0.003) > 0`. Weekly turnover ~%50 (5d holding) için: `net_IC ≈ 0.03 × 0.9985 ≈ 0.0297`. Sınırda; yüksek turnover senaryolarında net negatif riski var.

**Beklenti yönetimi:** `is_investable=True` işareti gross IC üzerinden; transaction cost düzeltmesi `weight_calibrator` raporuna ek not olarak eklenmeli (D-135 kapsamı).

---

## Etkilenen Dosyalar (Toplam — 4 spec)

### D-133 (Faz 1):
- `src/signals/thresholds.py` (sabit ekle — dokunulmaz prensip uyumlu)
- `src/data/signal_logger.py` (ReturnRecord + ReturnFiller genişlet)
- `src/analytics/ic_calculator.py` (compute_fdr_panel ekle)
- `src/analytics/ic_history.py` **YENİ**
- `scripts/daily_update.py` (IC history writer entegrasyonu)
- `tests/test_architecture.py` (3 yeni invariant)
- `tests/test_ic_framework.py` **YENİ**

### D-134 (Faz 2):
- `src/analytics/ic_calculator.py` (compute_decay ekle)
- `src/analytics/ic_history.py` (decay slope yaz)
- `src/data/signal_logger.py` (delisted skip)
- `src/reporting/ic_dashboard.py` (decay column)
- `data/analytics/delisted_tickers.json` **YENİ** (veri dosyası)
- `tests/test_ic_framework.py` (decay test'leri)

### D-135 (Faz 3):
- `src/analytics/weight_calibrator.py` **YENİ**
- `src/reporting/ic_dashboard.py` (--tier 2)
- `tests/test_weight_calibrator.py` **YENİ**

### D-136 (Faz 4):
- `.importlinter` (yeni kontrakt)
- `tests/test_architecture.py` (zaten D-133'te eklendi, CI doğrulama)

---

## Grunt Tasks (Bu SPEC'ten kaynaklanan)

| ID | Açıklama | Kapsam |
|----|----------|--------|
| G-22 | MASTER_WEIGHTS güncelleme protokolü — manuel onay süreci dokümante et | `docs/DECISIONS.md`'ye DEC-018 kaydı |
| G-23 | `IC_NEW_LAYER_TSTAT_HURDLE = 3.0` thresholds.py'e ekle (RR-008/L4 hybrid giriş kriteri) | thresholds.py |
| G-24 | `data/analytics/` dizinini `.gitignore`'a ekle (ic_history.parquet kişisel sinyal verisi) | .gitignore |

---

## RESEARCH_REGISTRY Güncellemesi (Merge Sonrası)

D-133 merge edilince `docs/RESEARCH_REGISTRY.md`'de RR-010 satırı şöyle güncellenir:

```
| [RR-010](research/RR-010-bist-ic-measurement.md) | IC ölçüm metodolojisi … | 23 May 2026 | D-132/D-133/D-134/D-135/D-136 | ✅ Applied (Faz 1) |
```

---

## Merge Önkoşulları (Her Spec)

**D-133:**
1. `python -m pytest tests/test_ic_framework.py -v` → min 10 test pass
2. `python -m pytest tests/ -q --tb=short` → sıfır regresyon
3. `python -m pytest tests/test_architecture.py -v` → 3 yeni IC invariant pass
4. maintainer onayı (PR review)

**D-134 (D-133 sonrası):**
1. `data/analytics/delisted_tickers.json` → min 20 ticker, son 5 yıl
2. `compute_decay()` testi: 30/60/120d slope hesabı mock data ile doğrulama
3. Sıfır regresyon

**D-135 (D-134 sonrası):**
1. `test_master_weights_not_auto_mutated` pass
2. `test_analytics_not_importing_engine` pass
3. `weight_calibrator.compute_posterior_weights()` → `tau < IC_BAYESIAN_TAU_MIN_DAYS` ise `None` dönmeli
4. Sıfır regresyon + maintainer onayı

**D-136 (D-135 sonrası):**
1. `lint-imports` CI geçer
2. Sıfır regresyon

---

## maintainer Notu

Bu SPEC CB-010 ("statik weight savunulamazlığı") ve RR-010'u doğrudan karşılıyor. Ancak BIST OS'ta **birincil kısıt veri birikimi**: şu an 4 günlük signal log, sıfır dolu forward return. D-133 uygulanıp 60 iş günü (yaklaşık Ağustos 2026 başı) beklenmeden D-135'in etkinleşmesi mümkün değil.

Pratik sıra önerisi:
1. **Bu hafta:** D-133 (Faz 1 altyapısı — hemen uygulanabilir)
2. **2-4 hafta içinde:** D-134 (decay + delisted — az önkoşul)
3. **Ağustos 2026 başı:** D-135 (Bayesian — 60 gün dolduğunda etkinleşir)
4. **D-135 merge sonrası:** D-136 (kontrakt — 20 dakika)

**Açık soru (arastirma katmani'a):** `IC_INVESTABLE_MONTHS_MIN = 24` çok muhafazakar mı? 2 yıl = ~504 günlük veri birikimi gerekiyor. BIST OS henüz 4 günlük; 2 yıl içinde hiçbir layer "INVEST" statüsüne giremeyecek. `IC_INVESTABLE_MONTHS_MIN = 6` (126 iş günü) daha uygun olabilir. maintainer kararı.

---

*SPEC_IC_FRAMEWORK_1 tamamlandı. arastirma katmani specleri SPEC onayı bekleniyor.*  
*Bağlı: RR-010 §2-§4 §6 (tüm bölümler), CB-010, DEC-015, CLAUDE.md Dokunulmaz Prensipler*
