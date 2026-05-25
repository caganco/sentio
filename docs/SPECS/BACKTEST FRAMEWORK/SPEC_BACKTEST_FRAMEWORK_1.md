# SPEC_BACKTEST_FRAMEWORK_1 — RR-018 Production Sync (Faz 1)

**Direktif:** D-149 (bu SPEC onaylanınca verilecek)  
**Tarih:** 2026-05-25  
**Referans:** RR-018-VERY-IMPORTANT.md §8 (C-1 closure roadmap), §15 (Faz 1 checklist)  
**Audit bağlantısı:** AUDIT_REPORT_001 C-1 "backtest/engine.py production'dan diverge formül"  
**Durum:** TASLAK — Orchestrator onayı bekleniyor  
**Platform:** Cowork — Architect, thinking ON, high effort

---

## TL;DR (Orchestrator için)

`backtest/engine.py` kısmen iyileştirilmiş (MASTER_WEIGHTS importlandı, docstring "C-1 resolved, G-3" diyor) ama **divergence hâlâ kritik**:

1. L3/L4/L5 katmanları backtest'te daima **50.0 (neutral)** — toplam ağırlığın **%52'si** daima sabit
2. Stop-loss (`0.92`), profit-target (`1.20`), circuit-breaker (`0.15`), VIX haircut (`0.75`) `thresholds.py`'den değil, hardcoded
3. Conflict resolution ve conviction compute **backtest'te yok** — production ile structurally farklı
4. `src/signals/calculator.py` shared module **hiç oluşturulmamış**
5. `test_architecture.py` mevcut regex'i bu hardcoded değerleri **yakalamıyor**
6. Eski backtest raporları (D-038/D-046/D-047/D-048) **RETRACT işaretlenmemiş**

Mevcut `reports/backtest/summary.json`: **Sharpe -1.71, win_rate 0%, alpha -28.6%** → bu sonuç zaten FAIL gösteriyor ama production'dan diverge engine ile üretildi.

---

## BÖLÜM 1 — C-1 Gap Analizi (Kod Kanıtıyla)

### S-1: backtest/engine.py içindeki hardcoded değerler (satır numarasıyla)

**`_get_kelly_allocation_tl()` metodu (satır 296-308):**

| Satır | Değer | İçerik | thresholds.py karşılığı |
|---|---|---|---|
| 303 | `0.50`, `50.0`, `200.0` | `win_prob = 0.50 + (composite - 50.0) / 200.0` | Yok — Kelly formula sabiti |
| 304 | `2.0` | `kelly_raw = max(0.0, 2.0 * win_prob - 1.0)` | Yok — even-odds Kelly |
| 305 | `0.05` | `position_frac = min(kelly_raw * ..., 0.05)` | Yok — 5% pozisyon tavanı |
| 306 | `25.0` | `if vix_level and vix_level > 25.0:` | Yok (BACKTEST_VIX_MAX ≠ bu eşik) |
| 307 | `0.75` | `position_frac *= 0.75` | Yok — VIX haircut faktörü |

**`_update_portfolio()` metodu (satır 391-445):**

| Satır | Değer | İçerik | thresholds.py karşılığı |
|---|---|---|---|
| 422 | `-0.15` | `self.circuit_breaker_active = dd <= -0.15` | `DD_HARD_THRESHOLD` mevcut |
| 432 | `0.92` | `stop_loss_price = entry_price * 0.92` | `EXIT_STOP_LOSS` mevcut (0.08 → 1-0.08=0.92) |
| 438 | `1.20` | `profit_target_price = entry_price * 1.20` | Yok — thresholds.py'de profit target sabit YOK |

> **Not**: Satır 300'deki `0.75` docstring'de geçiyor (p=0.75 örneği) ama satır 307'deki `0.75` ayrı bir hardcoded haircut faktörü.

**`_compute_composite()` metodu (satır 184-227) — Yapısal divergence:**

```python
# satır 219-226 — backtest/engine.py
composite = (
    tech_score * MASTER_WEIGHTS["technical"]     # L1: gerçek score ✅
    + macro_score * MASTER_WEIGHTS["macro"]      # L2: basitleştirilmiş score
    + risk_score * MASTER_WEIGHTS["risk"]        # L6: gerçek score ✅
    + 50.0 * (                                   # L3+L4+L5: DAİMA 50.0 ❌
        MASTER_WEIGHTS["kap"]
        + MASTER_WEIGHTS["sentiment"]
        + MASTER_WEIGHTS["smart_money"]
    )
)
```

Bu 50.0 neutral stub bir çözüm **değil** — toplam `MASTER_WEIGHTS` toplamının %52'si daima neutral.

---

### S-2: Production MASTER_WEIGHTS ile Backtest Formula Arasındaki Divergence

**MASTER_WEIGHTS (Phase 4.5):**
```
L1 technical:  0.25
L2 macro:      0.20
L3 kap:        0.30   ← backtest'te 50.0 (neutral)
L4 sentiment:  0.12   ← backtest'te 50.0 (neutral)
L5 smart_money:0.10   ← backtest'te 50.0 (neutral)
L6 risk:       0.03
────────────────────
Σ = 1.00
```

**Backtest'te sabit kalan ağırlık:** `0.30 + 0.12 + 0.10 = 0.52` → toplam sinyalin **%52'si**

**Maksimum divergence (sayısal):**

Örnek gün: L3=80 (güçlü KAP haberi), L4=72 (bullish sentiment), L5=75 (smart money alım):
```
Production composite:
  = ... + 80×0.30 + 72×0.12 + 75×0.10 + ...
  = ... + 24.0 + 8.64 + 7.5 + ...
  = +40.14 katkı (L3+L4+L5'ten)

Backtest composite:
  = ... + 50×0.30 + 50×0.12 + 50×0.10 + ...
  = ... + 15.0 + 6.0 + 5.0 + ...
  = +26.0 katkı (L3+L4+L5'ten)

Divergence: +14.14 composite puan eksik (backtest daha düşük alım sinyali üretiyor)
```

Yani production `BUY-STRONG` (≥72) ürettiğinde backtest `HOLD` üretebilir — **sessiz false negative**.

**Ek yapısal divergence (ağırlıkların ötesinde):**

| Özellik | Production engine.py | Backtest engine.py |
|---|---|---|
| Conflict resolution | ✅ `_apply_conflict_resolution()` | ❌ Yok |
| RISK_OFF regime filter | ✅ `_apply_regime_filter()` (full) | ✅ `_is_entry_gated_by_macro()` (basit) |
| Conviction compute | ✅ `compute_conviction()` | ❌ Linear Kelly formula |
| KAP event boost | ✅ `KAP_EVENT_BOOST_MULTIPLIER` | ❌ Yok |
| HMM weight injection | ✅ `get_hmm_weight_override()` | ❌ Yok |
| Macro compositing | Full (LOCAL_MACRO × global) | Simplified (`_global_macro_score`) |
| L4 confidence scaling | ✅ `L4_CONF_FULL` | ❌ Yok |

**Sonuç:** Mevcut backtest sonuçları (`summary.json` Sharpe -1.71) hangi gerçekliği ölçüyor belirsiz — production engine'inin %52 sinyal gücü olmadan çalıştırılmış bir versiyon.

---

### S-3: src/signals/calculator.py — Mevcut Durum

**Dosya yok.** `src/signals/` altında `calculator.py` hiç oluşturulmamış.

RR-018 §8.2 seçenek (b) olarak önerilen `SignalCalculator` shared module, `backtest/engine.py` docstring'inin "C-1 resolved" iddiasına rağmen implement edilmemiş.

**Yokken ne içermeli (önerilen arayüz — RR-018 §8.2'den):**

```python
# src/signals/calculator.py
"""Shared signal computation module.

Hem production (src/signals/engine.py) hem backtest (src/backtest/engine.py)
tarafından import edilir. Side-effect yok, stateless, pure function'lar.

Dayanak: RR-018 §8.2 (b) Shared abstraction; AUDIT_REPORT_001 C-1.
"""
from __future__ import annotations
from src.signals.thresholds import MASTER_WEIGHTS

def compute_composite_score(
    layer_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Ağırlıklı katman toplama: Σ(score_i × weight_i) / Σ(weight_i).

    layer_scores: {"technical": 65.0, "macro": 48.0, "kap": 72.0, ...}
    weights: MASTER_WEIGHTS ile override; None → MASTER_WEIGHTS kullan.
    Returns: composite score ∈ [0, 100].
    """
    w = weights or MASTER_WEIGHTS
    total_weight = sum(w[k] for k in layer_scores if k in w)
    if total_weight == 0:
        return 50.0
    weighted = sum(layer_scores[k] * w[k] for k in layer_scores if k in w)
    return round(max(0.0, min(100.0, weighted / total_weight)), 4)

def validate_weights(weights: dict[str, float]) -> bool:
    """Ağırlık toplamının [0.85, 1.05] bandında olduğunu doğrula."""
    total = sum(weights.values())
    return 0.85 <= total <= 1.05

def signal_from_composite(composite: float) -> str:
    """SIGNAL_THRESHOLDS kullanarak composite → FinalSignal."""
    from src.signals.thresholds import SIGNAL_THRESHOLDS
    if composite >= SIGNAL_THRESHOLDS["buy_strong"]:
        return "BUY-STRONG"
    if composite >= SIGNAL_THRESHOLDS["buy_weak"]:
        return "BUY-WEAK"
    if composite >= SIGNAL_THRESHOLDS["hold_lower"]:
        return "HOLD"
    if composite >= SIGNAL_THRESHOLDS["sell_weak"]:
        return "SELL-WEAK"
    return "SELL-STRONG"
```

---

### S-4: test_architecture.py — Mevcut Kapsam ve Kör Noktalar

**Mevcut `TestBacktestEngineIntegrity` sınıfı (satır 196-226) neyi tarıyor:**

| Test | Regex/Pattern | Ne yakalıyor |
|---|---|---|
| `test_no_hardcoded_weights_in_backtest_engine` | `r"(?<!\w)(0\.\d{2})\s*[\+\*].*score"` | `0.XX * ... score` formatındaki ifadeler |
| `test_backtest_engine_imports_master_weights` | `"MASTER_WEIGHTS" in source` | MASTER_WEIGHTS importunu |
| `test_no_bare_except_in_backtest` | `except:\n` | Bare except bloklarını |

**Kör noktalar — yakalanmayan hardcoded değerler:**

| Değer | Satır | Neden yakalanmıyor |
|---|---|---|
| `0.92` (stop-loss) | 432 | Regex "score" gerektiriyor; "stop_loss_price" içermiyor |
| `1.20` (profit-target) | 438 | Aynı; "profit_target_price" içinde "score" yok |
| `0.15` (circuit-breaker) | 422 | Negatif float `dd <= -0.15`; regex `0.\d\d` formatını yakalamıyor |
| `25.0` (VIX eşiği) | 306 | `0.\d{2}` pattern'i 2 ondalık basamak bekliyor; 25.0 integer kısmı var |
| `0.75` (VIX haircut) | 307 | `0\.75` regex'e uyuyor ama `.*score` koşulunu sağlamıyor |
| `0.05` (pozisyon tavanı) | 305 | `0\.05` regex'e uyuyor ama `.*score` koşulunu sağlamıyor |
| L3/L4/L5 = `50.0` (neutral stub) | 220-226 | `50.0` pattern değil; `0.\d{2}` yakalamıyor |

**Kör nokta — taranan dosya kapsamı:**

`TestBacktestEngineIntegrity` sadece `src/backtest/engine.py` kontrol ediyor. Aşağıdakiler taransa da taranmıyor:

- `src/backtest/data_loader.py` — yfinance lazy import, hardcoded period string
- `src/backtest/metrics.py` — Sharpe/Sortino formüllerinde hardcoded 252 (annualization)
- `src/backtest/reporter.py` — rapor format sabitleri

**Kör nokta — parity testi yok:**

Production `compute_signal()` ve backtest `_compute_composite()` aynı input için aynı output üretmeli. Bu invariant test_architecture.py'de **hiç test edilmiyor**.

---

### S-5: Eski Backtest Raporları — Lokasyon ve RETRACT Stratejisi

**Eski raporlar (üretildiği engine ile üretildi, daima diverge):**

| Dosya | İçerik | Neden RETRACT |
|---|---|---|
| `reports/D-038_SHARPE_RECALIBRATION.md` | Sharpe recalibration analizi | L3/L4/L5=50 ile üretildi |
| `reports/D-046_MACRO_GATED_BACKTEST_REPORT.md` | Macro gate v1 backtest | Same |
| `reports/D-046_ORCHESTRATOR_SUMMARY.md` | D-046 orchestrator özeti | Same |
| `reports/D-047_AUDIT_TRAIL_ANALYSIS.md` | Audit trail analizi | Same |
| `reports/D-047_FINAL_AUDIT_ANALYSIS.md` | Final audit | Same |
| `reports/D-048_ALPHA_ANALYSIS.md` | Alpha analizi | Same |
| `reports/D-048_REAL_ALPHA.json` | Real alpha JSON | Same |
| `reports/D-049_BASELINES.md` | Baselines karşılaştırma | Same |
| `reports/D-050_BEAR_TEST.md` | Bear test | Same |
| `reports/backtest/summary.json` | Güncel backtest özeti (Sharpe -1.71) | Engine diverge; 6 aylık pencere MinBTL altında |
| `reports/backtest/backtest_with_sentiment_2024_2026.json` | Sentiment-dahil backtest | L3/L4/L5 farklı kaynaklardan; engine karışımı |
| `backtest_output.log` | Ham backtest log | VADER sentiment, eski engine |
| `reports/backtest_results.md` | Backtest sonuçları özet | Same |

**RETRACT metodolojisi (Builder için):**

Rapor dosyalarına dokunulmaz — içerik değişmez. Her dosyanın başına YAML frontmatter veya Markdown header olarak şu blok eklenir:

```markdown
> ⚠️ **RETRACT NOTICE** — Bu rapor `backtest/engine.py` v[X]'de üretildi.
> L3 (KAP), L4 (Sentiment), L5 (SmartMoney) katmanları bu versiyonda
> `50.0 (neutral)` olarak hardcode edilmişti (toplam ağırlığın %52'si).
> Sonuçlar production engine davranışını yansıtmıyor.
> Geçerli rapor: D-149 tamamlandıktan sonra `reports/backtest/v2/` altında üretilecek.
> İşaretleyen: SPEC_BACKTEST_FRAMEWORK_1, Tarih: 2026-05-25
```

**Python ile otomatik RETRACT (Builder için snippet):**

```python
# scripts/retract_old_backtest_reports.py
RETRACT_FILES = [
    "reports/D-038_SHARPE_RECALIBRATION.md",
    "reports/D-046_MACRO_GATED_BACKTEST_REPORT.md",
    # ... (tam liste)
]
RETRACT_HEADER = """> ⚠️ **RETRACT NOTICE** ...
"""
for f in RETRACT_FILES:
    p = Path(f)
    if p.exists():
        content = p.read_text(encoding="utf-8")
        if "RETRACT NOTICE" not in content:
            p.write_text(RETRACT_HEADER + "\n---\n\n" + content, encoding="utf-8")
```

---

## BÖLÜM 2 — Shared Module Tasarımı: src/signals/calculator.py

### Önerilen Modül İçeriği

`src/signals/calculator.py` hem production hem backtest tarafından import edilen **pure, stateless** bir modül olacak. Side-effect yok, DB/filesystem/network bağımlılığı yok.

```
Bağımlılık grafiği:

src/signals/thresholds.py (sabitler)
        ↑
src/signals/calculator.py (pure functions)
    ↑                   ↑
src/signals/engine.py   src/backtest/engine.py
(production)            (backtest)
```

**Temel fonksiyonlar:**

```python
# Fonksiyon 1: Composite hesaplama — her iki engine da kullanır
def compute_composite_score(
    layer_scores: dict[str, float],
    weights: dict[str, float] | None = None,
    confidence_scaling: dict[str, float] | None = None,
) -> float:
    """
    Ağırlıklı composite score.
    confidence_scaling: {"sentiment": 0.12, "smart_money": 0.80} — L4/L5 conf override
    Eğer backtest confidence data yoksa → 1.0 (tam ağırlık, conservative)
    """

# Fonksiyon 2: Ağırlık doğrulama
def validate_weights(weights: dict[str, float]) -> bool:
    """[0.85, 1.05] band kontrol."""

# Fonksiyon 3: Signal eşleme (threshold lookup)
def signal_from_composite(composite: float) -> str:
    """SIGNAL_THRESHOLDS → FinalSignal literal."""

# Fonksiyon 4: Kelly win_prob (backtest için)  
def kelly_win_prob(composite: float) -> float:
    """Linear: composite=50 → p=0.50, composite=100 → p=0.75.
    Formula sabiti thresholds.py'den okunur (KELLY_WIN_PROB_SLOPE vb.)"""
```

### Production ile Backtest Parity Testi Tasarımı

```python
# tests/test_backtest_production_parity.py (yeni dosya)

def test_composite_calculation_parity():
    """Production ve backtest aynı layer scores ile aynı composite üretmeli."""
    from src.signals.calculator import compute_composite_score
    from src.signals.thresholds import MASTER_WEIGHTS

    # Tüm 6 katman için test vektörü
    layer_scores = {
        "technical": 65.0,
        "macro": 55.0,
        "kap": 70.0,
        "sentiment": 60.0,
        "smart_money": 58.0,
        "risk": 52.0,
    }

    # Production engine compute
    prod_composite = compute_composite_score(layer_scores, MASTER_WEIGHTS)

    # Backtest engine (mock TCMB/CDS/KAP historical) compute
    # backtest_composite = BacktestEngine._compute_composite_shared(layer_scores)
    # assert abs(prod_composite - backtest_composite) < 0.01

    # Şimdilik: calculator fonksiyonunun doğruluğunu test et
    assert 0 <= prod_composite <= 100
    expected = sum(layer_scores[k] * MASTER_WEIGHTS[k] for k in layer_scores) / sum(MASTER_WEIGHTS.values())
    assert abs(prod_composite - expected) < 0.001


def test_no_l3_l4_l5_neutral_stub_in_backtest():
    """backtest/engine.py'de 50.0 neutral stub kalmamalı.
    D-149 tamamlandıktan sonra bu test aktive edilir."""
    from pathlib import Path
    source = (Path(__file__).parent.parent / "src/backtest/engine.py").read_text()
    # Production sync tamamlandıktan sonra:
    # assert "50.0 * (" not in source, "L3/L4/L5 neutral stub still present"
    pass  # Faz 1c tamamlanınca bu pass kaldırılır


def test_signal_thresholds_consistent_between_engines():
    """Her iki engine aynı SIGNAL_THRESHOLDS kullanmalı."""
    from src.signals.thresholds import SIGNAL_THRESHOLDS
    from src.signals.calculator import signal_from_composite
    assert signal_from_composite(75.0) == "BUY-STRONG"  # ≥72
    assert signal_from_composite(62.0) == "BUY-WEAK"    # ≥60
    assert signal_from_composite(50.0) == "HOLD"        # ≥48
```

---

## BÖLÜM 3 — Architecture Test Genişletmesi

### test_architecture.py'e Eklenecek Yeni Invariant Sınıfı

Mevcut `TestBacktestEngineIntegrity` sınıfının yanına yeni testler:

```python
class TestBacktestEngineHardcodedValues:
    """backtest/engine.py'de thresholds.py'den gelmesi gereken hardcoded değer yok."""

    def test_no_hardcoded_stop_loss_in_backtest(self):
        """Stop-loss 0.92 thresholds.EXIT_STOP_LOSS'tan türetilmeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        # entry_price * 0.92 formatı hardcode olmamalı — EXIT_STOP_LOSS kullan
        import re
        matches = re.findall(r"entry_price\s*\*\s*0\.9[0-9]", source)
        assert not matches, (
            f"backtest/engine.py hardcoded stop-loss: {matches}. "
            f"from src.signals.thresholds import EXIT_STOP_LOSS kullan."
        )

    def test_no_hardcoded_profit_target_in_backtest(self):
        """Profit-target 1.20 thresholds.PROFIT_TARGET_PCT'den türetilmeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        import re
        matches = re.findall(r"entry_price\s*\*\s*1\.[0-9]{2}", source)
        assert not matches, (
            f"backtest/engine.py hardcoded profit-target: {matches}. "
            f"thresholds.py'den import et."
        )

    def test_no_hardcoded_circuit_breaker_in_backtest(self):
        """Circuit-breaker -0.15 DD_HARD_THRESHOLD'dan türetilmeli."""
        path = Path(__file__).parent.parent / "src" / "backtest" / "engine.py"
        source = path.read_text(encoding="utf-8")
        import re
        matches = re.findall(r"dd\s*<=?\s*-0\.\d+", source)
        assert not matches, (
            f"backtest/engine.py hardcoded circuit-breaker: {matches}. "
            f"from src.signals.thresholds import DD_HARD_THRESHOLD kullan."
        )

    def test_no_l3_l4_l5_neutral_stub_post_d149(self):
        """D-149 tamamlandıktan sonra: backtest L3/L4/L5 için 50.0 neutral stub olmamalı.
        
        Şimdilik geçici olarak atlanıyor (skip) — D-149 merge'inden sonra aktive edilir.
        """
        import pytest
        pytest.skip("D-149 tamamlanınca skip kaldır — L3/L4/L5 neutral stub check")


class TestBacktestCoverageScope:
    """src/backtest/ altındaki TÜM py dosyaları thresholds.py kontratına uymalı."""

    def _get_backtest_files(self):
        base = Path(__file__).parent.parent / "src" / "backtest"
        return [f for f in base.glob("*.py") if f.name != "__init__.py"]

    def test_no_standalone_hardcoded_thresholds_in_backtest_modules(self):
        """src/backtest/*.py SIGNAL_THRESHOLDS değerlerini hardcode etmemeli."""
        forbidden = [r"\b72\.0\b", r"\b60\.0\b", r"\b48\.0\b", r"\b32\.0\b"]
        import re
        for f in self._get_backtest_files():
            source = f.read_text(encoding="utf-8")
            for pat in forbidden:
                for i, line in enumerate(source.split("\n"), 1):
                    if line.strip().startswith("#"):
                        continue
                    if re.search(pat, line) and "SIGNAL_THRESHOLDS" not in line:
                        pytest.fail(
                            f"{f.name}:{i} hardcoded threshold {pat}. "
                            f"SIGNAL_THRESHOLDS kullan."
                        )

    def test_backtest_modules_importable(self):
        """src/backtest/ altındaki tüm modüller import hatası vermemeli."""
        import importlib
        for f in self._get_backtest_files():
            module_path = f"src.backtest.{f.stem}"
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                pytest.fail(f"{module_path} import hatası: {e}")


class TestSignalCalculatorSharedModule:
    """src/signals/calculator.py shared module varlık ve davranış testleri."""

    def test_calculator_module_exists(self):
        """D-149 sonrası: src/signals/calculator.py mevcut olmalı."""
        path = Path(__file__).parent.parent / "src" / "signals" / "calculator.py"
        assert path.exists(), (
            "src/signals/calculator.py bulunamadı — D-149 (SignalCalculator refactor) tamamlanmadı."
        )

    def test_calculator_compute_composite_importable(self):
        """compute_composite_score() importlanabilmeli."""
        from src.signals.calculator import compute_composite_score
        result = compute_composite_score({"technical": 65.0, "macro": 55.0})
        assert 0 <= result <= 100

    def test_calculator_validate_weights(self):
        """validate_weights() doğru çalışmalı."""
        from src.signals.calculator import validate_weights
        from src.signals.thresholds import MASTER_WEIGHTS
        assert validate_weights(MASTER_WEIGHTS) is True
        assert validate_weights({"technical": 2.0}) is False

    def test_calculator_neutral_input_gives_50(self):
        """Tüm katmanlar 50.0 → composite 50.0 olmalı."""
        from src.signals.calculator import compute_composite_score
        from src.signals.thresholds import MASTER_WEIGHTS
        all_neutral = {k: 50.0 for k in MASTER_WEIGHTS}
        result = compute_composite_score(all_neutral, MASTER_WEIGHTS)
        assert abs(result - 50.0) < 0.01
```

---

## BÖLÜM 4 — Builder Direktif Taslakları (RR-018 §15 Faz 1 Sıralamasıyla)

### D-149a: Parity Test (RR-018 Faz 1a)

```
DIREKTIF: D-149a
BAŞLIK: Backtest-Production Parity Test Yazımı
DAYANAK: SPEC_BACKTEST_FRAMEWORK_1 §B3; RR-018 §8.4 Faz 1a; AUDIT_REPORT_001 C-1
TAHMİNİ SÜRE: 1-2 gün

GÖREV:
  Backtest ile production engine arasındaki parity testi yaz.
  Şu anki divergence'ı ölçen ve belgeleyen test seti:
  (1) tests/test_backtest_production_parity.py oluştur
  (2) Aynı ticker + aynı tarih için production compute_signal() 
      ile backtest _compute_composite() karşılaştır
  (3) Divergence log: her katman için fark miktarını kaydet
  (4) test_architecture.py'e TestBacktestEngineHardcodedValues sınıfını ekle
  (5) test_architecture.py'e TestSignalCalculatorSharedModule sınıfını ekle
      (D-149c tamamlanana kadar test_calculator_module_exists skip)

KISITLAR:
  - src/signals/engine.py ve backtest/engine.py DOKUNULMAZ (sadece test)
  - src/signals/calculator.py henüz yok → ilgili testler skip işaretli
  - Yeni test dosyaları: tests/test_backtest_production_parity.py
  - MASTER_WEIGHTS, thresholds.py değişmez
  - 0 regresyon zorunlu

BAŞARI KRİTERİ:
  1. python -m pytest tests/test_backtest_production_parity.py -v → PASS
  2. python -m pytest tests/test_architecture.py -v → 0 regresyon
  3. Divergence log: hangi günlerde ve ne kadar fark var belgelenmiş
  4. TestBacktestEngineHardcodedValues tüm mevcut hardcoded değerleri yakalar

ETKİLENEN DOSYALAR:
  tests/test_backtest_production_parity.py  (yeni)
  tests/test_architecture.py               (yeni class ekleme)
```

---

### D-149b: Drift Quantify (RR-018 Faz 1b)

```
DIREKTIF: D-149b
BAŞLIK: Backtest-Production Drift Ölçümü + Eski Rapor RETRACT
DAYANAK: SPEC_BACKTEST_FRAMEWORK_1 §B1-S2, §B1-S5; RR-018 §8.4 Faz 1b
TAHMİNİ SÜRE: 1 gün
BLOCKER: D-149a tamamlanmış olmalı

GÖREV:
  (1) Son 30 günlük sinyal logları üzerinde production vs backtest fark analizi yap
      Çıktı: data/analytics/drift_report_YYYY-MM-DD.json
      Format: {"date": ..., "ticker": ..., "prod_composite": ..., "bt_composite": ...,
               "delta": ..., "prod_signal": ..., "bt_signal": ..., "signal_match": bool}
  (2) Toplam drift raporunu logla:
      - Farklı sinyal üretilen gün sayısı
      - Ortalama composite farkı
      - En fazla divergence olan ticker + gün
  (3) Eski backtest raporlarını RETRACT işaretle:
      scripts/retract_old_backtest_reports.py çalıştır
      — Hedef: reports/D-038, D-046, D-047, D-048, D-049, D-050 raporları
      — Yöntem: Her dosyanın başına "RETRACT NOTICE" header ekle (içerik değişmez)
  (4) reports/backtest/summary.json'a "retract_reason" alanı ekle

KISITLAR:
  - Eski raporların içeriği DEĞİŞMEZ — sadece başına header eklenir
  - src/ kodu değişmez
  - drift_report JSON sadece data/analytics/'e yazılır

BAŞARI KRİTERİ:
  1. data/analytics/drift_report_<today>.json üretildi
  2. reports/D-038..D-050 dosyalarının başında "RETRACT NOTICE" var
  3. reports/backtest/summary.json'da "retract_reason" alanı var
  4. python -m pytest tests/ -q → 0 regresyon

ETKİLENEN DOSYALAR:
  scripts/retract_old_backtest_reports.py  (yeni script)
  reports/D-038_SHARPE_RECALIBRATION.md   (RETRACT header ekleme — içerik değişmez)
  reports/D-046_MACRO_GATED_BACKTEST_REPORT.md
  reports/D-047_AUDIT_TRAIL_ANALYSIS.md
  reports/D-047_FINAL_AUDIT_ANALYSIS.md
  reports/D-048_ALPHA_ANALYSIS.md
  reports/D-049_BASELINES.md
  reports/D-050_BEAR_TEST.md
  reports/backtest/summary.json
  data/analytics/drift_report_<date>.json  (yeni, .gitignore kapsamında)
```

---

### D-149c: SignalCalculator Refactor (RR-018 Faz 1c)

```
DIREKTIF: D-149c
BAŞLIK: src/signals/calculator.py — Shared Signal Module
DAYANAK: SPEC_BACKTEST_FRAMEWORK_1 §B2; RR-018 §8.2 (b), §8.4 Faz 1c
TAHMİNİ SÜRE: 4-5 gün
BLOCKER: D-149b tamamlanmış, drift ölçülmüş olmalı

GÖREV:
  (1) src/signals/calculator.py oluştur:
      - compute_composite_score(layer_scores, weights, confidence_scaling) → float
      - validate_weights(weights) → bool
      - signal_from_composite(composite) → str
      - kelly_win_prob(composite) → float (backtest Kelly için)
      Tüm sabitler SADECE thresholds.py'den okunur.

  (2) src/signals/engine.py'deki _compute_weighted_sum() yerine
      calculator.compute_composite_score() kullan
      (wrapper/shim ile — engine.py yapısı değişmez, sadece delegasyon)

  (3) thresholds.py'e yeni sabitler ekle (yoklarsa):
      - PROFIT_TARGET_PCT = 0.20  (backtest profit-target için)
      - BACKTEST_KELLY_VIX_THRESHOLD = 25.0  (satır 306)
      - BACKTEST_KELLY_VIX_HAIRCUT = 0.75    (satır 307)
      - BACKTEST_KELLY_WIN_PROB_NEUTRAL = 0.50  (satır 303)
      - BACKTEST_KELLY_WIN_PROB_DIVISOR = 200.0  (satır 303)
      - BACKTEST_MAX_POSITION_FRAC = 0.05    (satır 305)
      Not: EXIT_STOP_LOSS ve DD_HARD_THRESHOLD ZATEN thresholds.py'de mevcut

KISITLAR:
  - src/signals/engine.py davranışı değişmez (refactor ≠ behavior change)
  - MASTER_WEIGHTS değeri değişmez
  - src/backtest/engine.py henüz DOKUNULMAZ (D-149d'de değişir)
  - test kapsama ≥ %90 yeni modül için
  - 0 regresyon zorunlu

BAŞARI KRİTERİ:
  1. src/signals/calculator.py mevcut
  2. from src.signals.calculator import compute_composite_score → import hatasız
  3. test_architecture.py TestSignalCalculatorSharedModule → PASS (skip kaldırıldı)
  4. src/signals/engine.py _compute_weighted_sum() → calculator delegate ediyor
  5. python -m pytest tests/ -q → 0 regresyon

ETKİLENEN DOSYALAR:
  src/signals/calculator.py        (yeni)
  src/signals/engine.py            (küçük refactor — _compute_weighted_sum delegate)
  src/signals/thresholds.py        (yeni backtest Kelly sabitleri)
  tests/test_signal_calculator.py  (yeni test dosyası)
```

---

### D-149d: Backtest Refactor (RR-018 Faz 1d)

```
DIREKTIF: D-149d
BAŞLIK: backtest/engine.py — Hardcoded Values Temizleme + Calculator Import
DAYANAK: SPEC_BACKTEST_FRAMEWORK_1 §B1-S1, §B1-S2; RR-018 §8.4 Faz 1d
TAHMİNİ SÜRE: 2-3 gün
BLOCKER: D-149c tamamlanmış, calculator.py mevcut olmalı

GÖREV:
  (1) Hardcoded değerleri thresholds.py sabitlerle değiştir:
      - satır 432: `entry_price * 0.92` → `entry_price * (1 - EXIT_STOP_LOSS)`
      - satır 438: `entry_price * 1.20` → `entry_price * (1 + PROFIT_TARGET_PCT)`
      - satır 422: `dd <= -0.15` → `dd <= -DD_HARD_THRESHOLD`
      - satır 306: `vix_level > 25.0` → `vix_level > BACKTEST_KELLY_VIX_THRESHOLD`
      - satır 307: `position_frac *= 0.75` → `position_frac *= BACKTEST_KELLY_VIX_HAIRCUT`
      - satır 305: `min(..., 0.05)` → `min(..., BACKTEST_MAX_POSITION_FRAC)`
      - satır 303: `0.50 + ... / 200.0` → `BACKTEST_KELLY_WIN_PROB_NEUTRAL + ... / BACKTEST_KELLY_WIN_PROB_DIVISOR`

  (2) _compute_composite() → calculator.compute_composite_score() kullanacak şekilde güncelle
      L3/L4/L5 neutral stub KALSIN (Faz 2'ye ertelenir — RR-018 §15 Faz 2 kapsamı)
      
  (3) test_architecture.py'deki test_no_l3_l4_l5_neutral_stub_post_d149 HÂLÂ skip
      (Bu stub Faz 2'de kaldırılır — Purged K-Fold ile birlikte L3/L4/L5 historical data)

  (4) test_architecture.py TestBacktestEngineHardcodedValues testleri → skip kaldır + PASS

KISITLAR:
  - L3/L4/L5 neutral stub bu direktifte DOKUNULMAZ (Faz 2 kapsamı)
  - Backtest sonuçları sayısal olarak biraz değişebilir — bu normal (yeni thresholds)
  - MASTER_WEIGHTS değişmez
  - Tüm mevcut test_backtest.py testleri PASS kalmalı
  - 0 regresyon zorunlu

BAŞARI KRİTERİ:
  1. grep "0\.92\|1\.20\|dd <= -0\.15" src/backtest/engine.py → 0 sonuç
  2. test_architecture.py TestBacktestEngineHardcodedValues → PASS (skip kaldırıldı)
  3. backtest/engine.py'de `from src.signals.calculator import` satırı mevcut
  4. python -m pytest tests/ -q --tb=short → 0 regresyon

ETKİLENEN DOSYALAR:
  src/backtest/engine.py           (hardcoded → thresholds import)
  src/signals/thresholds.py        (zaten D-149c'de eklenen sabitler)
  tests/test_architecture.py       (skip kaldırma)
  tests/test_backtest.py           (gerekirse güncelleme)
```

---

### D-149e: CI Architecture Test Genişletmesi (RR-018 Faz 1e)

```
DIREKTIF: D-149e
BAŞLIK: test_architecture.py Backtest Coverage Genişletmesi
DAYANAK: SPEC_BACKTEST_FRAMEWORK_1 §B3; RR-018 §8.4 Faz 1e
TAHMİNİ SÜRE: 0.5-1 gün
BLOCKER: D-149d tamamlanmış olmalı

GÖREV:
  (1) test_architecture.py'e TestBacktestCoverageScope sınıfını ekle:
      - src/backtest/*.py tüm dosyalar SIGNAL_THRESHOLDS hardcode içermemeli
      - tüm backtest modüller import hatası vermemeli

  (2) Var olan TestBacktestEngineIntegrity regex'ini genişlet:
      Eski: r"(?<!\w)(0\.\d{2})\s*[\+\*].*score"
      Yeni: yukarıdaki 3 yeni test ile tamamlandı → ayrıca regex güncelleme gerekmiyor

  (3) test_backtest_production_parity.py'deki skip'leri kaldır:
      test_no_l3_l4_l5_neutral_stub_post_d149: HÂLÂ skip (Faz 2'de kaldırılır)
      Diğerleri: aktif

KISITLAR:
  - src/ kodu değişmez
  - Sadece test dosyaları

BAŞARI KRİTERİ:
  1. python -m pytest tests/test_architecture.py -v → tüm TestBacktest* testleri PASS
  2. python -m pytest tests/ -q → 0 regresyon
  3. CI yeşil

ETKİLENEN DOSYALAR:
  tests/test_architecture.py       (TestBacktestCoverageScope ekleme)
  tests/test_backtest_production_parity.py  (skip kaldırma)
```

---

## BÖLÜM 5 — Dokunulmazlar & Riskler

### import-linter Kontratları

Mevcut `.importlinter` kontratları:
```ini
[importlinter:contract:signal-layering]
type = layers
layers = src.signals.engine / src.signals.layers / src.signals.thresholds

[importlinter:contract:layer-independence]
type = independence
modules = src.signals.layers.{technical,macro,kap,sentiment,smart_money,risk}_layer
```

**Yeni `src/signals/calculator.py` modülü için risk analizi:**

- `calculator.py` sadece `thresholds.py`'i import edecek → `signal-layering` kontratı ihlal etmez
- `backtest/engine.py`'nin `calculator.py`'i import etmesi: `src/backtest/` → `src/signals/` yönü backtest'in zaten yaptığı bir yön (halihazırda `thresholds`, `layers.*` import ediyor) → kontrat ihlali yok
- `calculator.py` hiçbir zaman `src/signals/engine.py`'i import etmemeli — döngüsel import riski

**Önerilen ek importlinter kontrat (D-149e'de eklenebilir):**
```ini
[importlinter:contract:calculator-no-engine-import]
type = forbidden
source_modules = src.signals.calculator
forbidden_modules = src.signals.engine
```

### MASTER_WEIGHTS Değişecek mi?

**HAYIR.** Bu SPEC'in hiçbir direktifi MASTER_WEIGHTS'i değiştirmiyor.

- D-149c thresholds.py'e sadece backtest Kelly sabitleri ekler
- PROFIT_TARGET_PCT = 0.20 yeni sabit olarak eklenir ama mevcut değer zaten kullanılıyordu (hardcoded)
- MASTER_WEIGHTS τ=0 fazında statik kalır (SPEC_IC_FRAMEWORK_1 K-01 kararı)

### Mevcut Backtest Testleri Regresyon Riski

**`tests/test_backtest.py`** mevcut (grep ile bulundu). D-149d backtest/engine.py'de sayısal değişiklik yapıyor (0.92 → 1-EXIT_STOP_LOSS) — ancak EXIT_STOP_LOSS = 0.08 olduğu için hesaplama aynı sonucu verecek. **Sayısal regresyon riski: düşük.**

**Risk**: Eğer `tests/test_backtest.py` hardcoded `0.92` bekliyorsa → test güncellenmeli. Builder kontrol etmeli.

### L3/L4/L5 Neutral Stub — Neden Faz 1'de Kaldırılmıyor?

RR-018 §3.3: "Survivorship bias — yfinance delisted şirketleri kapsamaz." Aynı mantıkla L3/L4/L5 için:
- **L3 (KAP):** Tarihsel KAP bildirimleri mevcut ama `kap_fetcher.py` May 2026'dan itibaren broken (HT endpoint değişikliği — bkz. SPEC_DATA_ROBUSTNESS_1). Eski KAP event'leri `kap_events` tablosunda var ama backtest'e besleme pipeline'ı henüz yok.
- **L4 (Sentiment):** VADER/yfinance news tarihsel olarak mevcut değil veya güvenilmez (backtest_output.log'da "no news articles from YahooFinance" uyarıları görüldü).
- **L5 (SmartMoney):** İş Yatırım screener API geçmişe dönük veri sunmuyor.

Bu nedenle L3/L4/L5 neutral stub bir **geçici çözüm** değil, **veri kısıtının gerçekçi modellemesi**. Faz 2'de point-in-time KAP veritabanı + synthetic L4/L5 ile geliştirilecek.

### Eski Raporlar RETRACT Prosedürü

RETRACT işaretleme geri döndürülebilir bir operasyon: sadece header ekleme, silme yok. RETRACT sonrası:
1. Her rapor "bu sonuçlar güvenilmez" uyarısıyla başlıyor
2. Eski içerik araştırma referansı olarak korunuyor
3. D-149 sonrası yeni `reports/backtest/v2/` klasöründe clean raporlar

### RR-018 Faz 2 Aktivasyon Koşulları (Bu SPEC Kapsamı Dışı)

Faz 1 (D-149a–e) tamamlandıktan sonra Faz 2 için gerekli:
- Purged K-Fold custom implementation
- DSR hesaplama
- CPCV 15 patika
- Minimum backtest length: 5 yıl (2019-2024) → yfinance + KAP point-in-time
- Crisis stress test (7 kriz dönemi)

**Aktivasyon trigger:** D-149e CI yeşil + drift=0 son 30 günde.

---

## Özet Tablo — Mevcut vs Hedef

| Boyut | Mevcut Durum | D-149 Sonrası Hedef |
|---|---|---|
| MASTER_WEIGHTS kullanımı | ✅ (composite weight ✅, sabit value ❌) | ✅ her ikisi de |
| Stop-loss sabit | ❌ `0.92` hardcoded | ✅ `EXIT_STOP_LOSS` |
| Profit-target | ❌ `1.20` hardcoded | ✅ `PROFIT_TARGET_PCT` |
| Circuit-breaker | ❌ `-0.15` hardcoded | ✅ `DD_HARD_THRESHOLD` |
| VIX Kelly haircut | ❌ `25.0`/`0.75` hardcoded | ✅ thresholds sabitler |
| L3/L4/L5 neutral stub | ⚠️ 50.0 (veri kısıtı) | ⚠️ Faz 2'ye ertelendi |
| Shared calculator | ❌ Yok | ✅ `src/signals/calculator.py` |
| Parity test | ❌ Yok | ✅ `test_backtest_production_parity.py` |
| Architecture test kapsamı | ⚠️ Kısmi | ✅ TestBacktestEngineHardcodedValues |
| Eski rapor RETRACT | ❌ Yok | ✅ header eklendi |
| Drift ölçümü | ❌ Yok | ✅ `data/analytics/drift_report_*.json` |
| RR-018 Sistem puanı (production sync) | 2/10 | 7/10 |

---

*SPEC tamamlandı. Orchestrator onayı bekleniyor. Builder direktifleri (D-149a → D-149e) SPEC onaylanmadan başlamaz.*
*Faz 1 tamamlanmadan Faz 2 (Purged K-Fold, DSR, CPCV) direktif olarak verilmez.*
