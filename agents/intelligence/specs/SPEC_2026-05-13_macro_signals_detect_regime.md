# SPEC: Macro Signals — Risk Regime Detection & Scoring

## Tanım

Makro ortamı analiz ederek RISK_ON/RISK_OFF/TRANSITION rejimini tespit et ve [-1,+1] arası ortam skorlaması yap. Mevcut macro feed'den (USDTRY, BRENT, VIX, BIST100) hesaplar, JSON çıktı ile intelligence klasörüne günlük kaydeder.

## Dosya Yapısı

```
src/
  signals/
    __init__.py
    macro_signals.py (200 lines)
    
agents/
  intelligence/
    macro_signal_YYYY-MM-DD.json (günlük çıktı)
    
tests/
  test_macro_signals.py (12 test)
  
scripts/
  macro_signals_example.py
```

## Fonksiyon İmzaları

```python
# src/signals/macro_signals.py

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json
import pandas as pd

@dataclass
class MacroSignal:
    """Makro sinyal yapısı."""
    timestamp: str  # ISO format
    regime: Literal["RISK_ON", "RISK_OFF", "TRANSITION"]
    
    # Bileşen skorları [-1, +1]
    vix_score: float      # VIX < 15: +1, VIX > 25: -1
    usdtry_score: float   # TRY kuvvetlenmesi: +1 (USDTRY düşüş)
    brent_score: float    # Brent yükselişi: +1 (petrol talebini gösterir)
    bist100_score: float  # BIST100 yükselişi: +1
    
    # Ağırlıklı ortalama skor
    macro_environment_score: float  # [-1, +1]
    
    # Meta
    data_date: str        # En son veri tarihi (YYYY-MM-DD)
    symbols: dict         # {"USDTRY": 45.39, "BRENT": 107.41, "VIX": 17.99, "BIST100": 9876}


def detect_regime(
    macro_data: pd.DataFrame,
    vix_threshold_low: float = 15.0,
    vix_threshold_high: float = 25.0
) -> Literal["RISK_ON", "RISK_OFF", "TRANSITION"]:
    """
    Makro ortamın rejimini tespit et.
    
    Rules:
    - RISK_ON: VIX < vix_threshold_low, BRENT ↑, BIST100 ↑, USDTRY ↓
    - RISK_OFF: VIX > vix_threshold_high, BRENT ↓, BIST100 ↓, USDTRY ↑
    - TRANSITION: else
    
    Input: DataFrame [date, symbol, close] (load_from_db çıktısı)
    Output: "RISK_ON" | "RISK_OFF" | "TRANSITION"
    """
    pass


def score_macro_component(
    symbol: str,
    current_close: float,
    prev_close: float,
    is_inverse: bool = False
) -> float:
    """
    Bileşen skoru hesapla [-1, +1].
    
    Mantık:
    - pct_change = (current - prev) / prev * 100
    - normal: pct_change > +2% → +1, < -2% → -1
    - inverse (USDTRY): -pct_change
    """
    pass


def calculate_macro_environment_score(
    vix_score: float,
    usdtry_score: float,
    brent_score: float,
    bist100_score: float,
    weights: dict = None
) -> float:
    """
    Ağırlıklı ortalama makro ortam skoru.
    
    Default weights:
    {"vix": 0.25, "usdtry": 0.15, "brent": 0.20, "bist100": 0.40}
    
    Output: [-1, +1]
    """
    pass


def generate_macro_signal(
    db_path: str = None,
    weights: dict = None
) -> MacroSignal:
    """
    Güncel makro feed'den signal üret.
    
    1. load_from_db() ile son 30 günü çek
    2. Her simge için son 2 veri noktasını al
    3. pct_change hesapla
    4. score_macro_component() ile skor tut
    5. calculate_macro_environment_score() ile toplam skor
    6. detect_regime() ile rejim
    7. MacroSignal nesnesi döndür
    """
    pass


def save_signal_json(signal: MacroSignal, output_dir: str = "agents/intelligence") -> str:
    """
    MacroSignal'ı JSON'a çevir ve kaydet.
    
    Output: agents/intelligence/macro_signal_2026-05-13.json
    
    JSON yapısı:
    {
        "timestamp": "2026-05-13T15:30:00Z",
        "regime": "RISK_ON",
        "vix_score": 0.85,
        "usdtry_score": 0.12,
        "brent_score": 0.45,
        "bist100_score": 0.70,
        "macro_environment_score": 0.58,
        "data_date": "2026-05-13",
        "symbols": {
            "USDTRY": 45.39,
            "BRENT": 107.41,
            "VIX": 17.99,
            "BIST100": 9876.50
        }
    }
    
    Return: Dosya yolu
    """
    pass
```

## Input/Output Formatları

### Input (load_from_db() DataFrame)
```
    date    symbol    open     high      low   close  volume
0  2026-05-12  USDTRY  45.25   45.50   45.20   45.30       0
1  2026-05-13  USDTRY  45.28   45.45   45.25   45.39       0
2  2026-05-12   BRENT 106.80  107.00  106.70  106.85   15000
3  2026-05-13   BRENT 107.10  107.50  107.00  107.41   18000
4  2026-05-12     VIX  18.15   18.50   17.85   18.05  100000
5  2026-05-13     VIX  17.80   18.20   17.60   17.99  120000
6  2026-05-12  BIST100 9800.00 9850.00 9795.00 9820.00 50000
7  2026-05-13  BIST100 9850.00 9900.00 9845.00 9876.50 65000
```

### Output (JSON)
```json
{
  "timestamp": "2026-05-13T15:42:30Z",
  "regime": "RISK_ON",
  "vix_score": 0.85,
  "usdtry_score": 0.12,
  "brent_score": 0.45,
  "bist100_score": 0.70,
  "macro_environment_score": 0.58,
  "data_date": "2026-05-13",
  "symbols": {
    "USDTRY": 45.39,
    "BRENT": 107.41,
    "VIX": 17.99,
    "BIST100": 9876.50
  }
}
```

## Bağımlılıklar

- pandas>=2.0 (already installed)
- dataclasses (stdlib)
- datetime (stdlib)
- json (stdlib)
- pathlib (stdlib)
- typing (stdlib)

**KAP bağımlılığı: SIFIR**

## Test Kriteri

Başarılı ise:
1. `generate_macro_signal()` güncel 4 sembolü döner
2. MacroSignal.regime ∈ {"RISK_ON", "RISK_OFF", "TRANSITION"}
3. Tüm skorlar [-1, +1] aralığında
4. JSON dosyası `agents/intelligence/macro_signal_YYYY-MM-DD.json` adında yazılır
5. Cron/scheduler'dan günlük çalışabilir

```python
# Test örneği
from src.signals.macro_signals import generate_macro_signal

signal = generate_macro_signal()
assert signal.regime in ["RISK_ON", "RISK_OFF", "TRANSITION"]
assert -1 <= signal.macro_environment_score <= 1
assert len(signal.symbols) == 4
```

---

**Oluşturma Tarihi:** 2026-05-13  
**Bağımlılık:** macro_feed.py  
**KAP:** Hayır
