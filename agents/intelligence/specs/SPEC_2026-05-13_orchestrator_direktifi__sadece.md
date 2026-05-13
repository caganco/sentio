# SPEC: Macro Signals Engine

## Tanım
Makroekonomik veri feedinden piyasa rejimi tespiti ve makro ortam skorlaması yapar. KAP bağımlılığı sıfır; sadece dışarıdan beslenen macro feed üzerinde çalışır.

## Dosya Yapısı
```
intelligence/
  specs/
    SPEC_2025-01-31_macro_signals.md   ← bu dosya
  signals/
    macro_signals.json                  ← output buraya
  macro_signals.py                      ← implementasyon
  __init__.py
```

## Fonksiyon İmzaları
```python
from dataclasses import dataclass
from typing import Literal

RegimeType = Literal["RISK_ON", "RISK_OFF", "STAGFLATION", "DEFLATION", "NEUTRAL"]
ScoreLevel = Literal["STRONG_BULL", "BULL", "NEUTRAL", "BEAR", "STRONG_BEAR"]

@dataclass
class MacroSignal:
    timestamp: str                  # ISO 8601, UTC
    regime: RegimeType
    regime_confidence: float        # 0.0 – 1.0
    macro_score: float              # -1.0 (tam bear) → +1.0 (tam bull)
    score_label: ScoreLevel
    dominant_factors: list[str]     # Skoru yönlendiren faktörler, max 3
    alerts: list[str]               # Kritik anomaliler, boş olabilir
    source_snapshot: dict           # Input olarak gelen ham macro feed

def detect_regime(macro_feed: dict) -> tuple[RegimeType, float]:
    """
    Macro feed'den piyasa rejimini tespit eder.

    Args:
        macro_feed: Aşağıda tanımlı standart macro feed dict'i

    Returns:
        (regime, confidence) tuple'ı
        regime: RegimeType literal
        confidence: 0.0-1.0 arası float
    """

def score_macro_environment(macro_feed: dict) -> MacroSignal:
    """
    Macro feed'i alır, detect_regime() çağırır,
    kapsamlı MacroSignal üretir ve
    intelligence/signals/macro_signals.json dosyasına yazar.

    Args:
        macro_feed: Standart macro feed dict'i

    Returns:
        MacroSignal dataclass instance'ı
    """
```

## Input/Output Formatları

### Input — Macro Feed
```python
# macro_feed: dict
{
    # Faiz & Tahvil
    "interest_rate_1w":   float,   # TCMB 1 haftalık repo, %
    "bond_yield_2y":      float,   # 2 yıllık gösterge tahvil faizi, %
    "bond_yield_10y":     float,   # 10 yıllık gösterge tahvil faizi, %
    "yield_curve_spread": float,   # 10y - 2y, baz puan

    # Enflasyon
    "cpi_yoy":            float,   # TÜFE yıllık, %
    "ppi_yoy":            float,   # ÜFE yıllık, %
    "inflation_trend":    Literal["RISING", "FALLING", "STABLE"],

    # Kur
    "usdtry":             float,   # USD/TRY spot
    "usdtry_1m_change":   float,   # Son 1 ay % değişim
    "eur_usd":            float,   # EUR/USD global gösterge

    # Global Risk İştahı
    "vix":                float,   # CBOE VIX
    "dxy":                float,   # Dolar endeksi
    "gold_usd":           float,   # Ons altın, USD

    # Büyüme Göstergeleri
    "gdp_growth_yoy":     float,   # GSYİH yıllık büyüme, %
    "pmi_manufacturing":  float,   # İmalat PMI (50 eşik)
    "pmi_services":       float,   # Hizmet PMI (50 eşik)

    # Likidite
    "m2_growth_yoy":      float,   # M2 para arzı yıllık büyüme, %
    "credit_growth_yoy":  float,   # Bireysel+ticari kredi büyümesi, %

    # Meta
    "as_of_date":         str,     # "YYYY-MM-DD"
    "data_source":        str      # "TCMB" | "TUIK" | "MANUAL" | "MIXED"
}
```

### Output — MacroSignal JSON
```json
{
    "timestamp": "2025-01-31T09:00:00Z",
    "regime": "RISK_ON",
    "regime_confidence": 0.74,
    "macro_score": 0.52,
    "score_label": "BULL",
    "dominant_factors": [
        "PMI_MANUFACTURING_ABOVE_50",
        "VIX_LOW",
        "YIELD_CURVE_POSITIVE"
    ],
    "alerts": [
        "CPI_ABOVE_50_CAUTION"
    ],
    "source_snapshot": {
        "as_of_date": "2025-01-31",
        "vix": 14.2,
        "...": "..."
    }
}
```

## Rejim Tespit Mantığı

```
Kural tablosu (detect_regime içine hardcode edilecek):

RISK_ON      → vix < 20 AND pmi_manufacturing > 50 AND usdtry_1m_change < 3%
RISK_OFF     → vix > 25 OR usdtry_1m_change > 5%
STAGFLATION  → cpi_yoy > 40 AND (gdp_growth_yoy < 3 OR pmi_manufacturing < 48)
DEFLATION    → cpi_yoy < 5 AND pmi_manufacturing < 48
NEUTRAL      → hiçbiri tam uymuyorsa

Confidence:
- Kaç kural tam eşleşiyor / toplam kural sayısı
- Çakışan rejim varsa confidence 0.5'i geçemez
```

## Skor Hesaplama Mantığı

```
score_macro_environment içinde, -1.0 ile +1.0 arası:

Her faktör ağırlıklı puana dönüştürülür:

Faktör                  Ağırlık   Bull Koşulu
─────────────────────────────────────────────
pmi_manufacturing         0.20    > 50 → +1, < 48 → -1
vix                       0.20    < 20 → +1, > 25 → -1
yield_curve_spread        0.15    > 0  → +1, < -50bp → -1
usdtry_1m_change          0.20    < 2% → +1, > 5% → -1
cpi_yoy (bağıl)           0.10    falling trend → +1, rising > 50 → -1
m2_growth_yoy             0.10    10-30% → +1, > 60% → -1
gdp_growth_yoy            0.05    > 4% → +1, < 1% → -1

Ara değerler lineer interpolasyon.
Toplam ağırlıklı skor → normalize → -1.0/+1.0

Score → Label:
  > 0.6   → STRONG_BULL
  > 0.2   → BULL
  > -0.2  → NEUTRAL
  > -0.6  → BEAR
  else    → STRONG_BEAR
```

## Bağımlılıklar
```
# requirements — sıfır dış finansal bağımlılık
python>=3.11
dataclasses   # stdlib
json          # stdlib
datetime      # stdlib
pathlib       # stdlib
typing        # stdlib
```

> **Not:** pandas, numpy, requests — hiçbiri zorunlu değil. Pure Python.

## Test Kriteri

```python
# Test: risk_on senaryosu
feed_risk_on = {
    "interest_rate_1w": 45.0,
    "bond_yield_2y": 42.0,
    "bond_yield_10y": 38.0,
    "yield_curve_spread": -400.0,
    "cpi_yoy": 65.0,
    "ppi_yoy": 55.0,
    "inflation_trend": "FALLING",
    "usdtry": 32.5,
    "usdtry_1m_change": 1.2,
    "eur_usd": 1.08,
    "vix": 16.0,
    "dxy": 103.5,
    "gold_usd": 2050.0,
    "gdp_growth_yoy": 5.1,
    "pmi_manufacturing": 52.3,
    "pmi_services": 54.1,
    "m2_growth_yoy": 45.0,
    "credit_growth_yoy": 30.0,
    "as_of_date": "2025-01-31",
    "data_source": "MIXED"
}

signal = score_macro_environment(feed_risk_on)

# Beklentiler:
assert signal.regime == "RISK_ON"
assert signal.regime_confidence >= 0.5
assert signal.macro_score > 0.0
assert signal.score_label in ("BULL", "STRONG_BULL", "NEUTRAL")
assert len(signal.dominant_factors) <= 3
assert isinstance(signal.alerts, list)

# Dosya yazıldı mı?
from pathlib import Path
assert Path("intelligence/signals/macro_signals.json").exists()

# JSON parse edilebilir mi?
import json
data = json.loads(Path("intelligence/signals/macro_signals.json").read_text())
assert "regime" in data
assert "macro_score" in data
assert -1.0 <= data["macro_score"] <= 1.0

print("✓ Tüm testler geçti")
```

---

**Builder'a Not:**
- `score_macro_environment` her çağrıda dosyayı **overwrite** eder (append değil)
- `source_snapshot` içinde hassas veri yok, direkt feed kopyası
- Eksik feed key'i → `KeyError` yerine `0.0` / `"STABLE"` default ile devam et, `alerts`'e ekle
- Tüm float hesapları `round(..., 4)` ile sınırla