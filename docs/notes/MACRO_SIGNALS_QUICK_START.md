# Macro Signals — Quick Start

## One-Minute Usage

```python
from src.signals.macro_signals import generate_macro_signal, save_signal_json

# Generate signal
signal = generate_macro_signal()

# Check regime
print(signal.regime)                    # RISK_ON / RISK_OFF / TRANSITION

# Check macro score
print(signal.macro_environment_score)   # [-1, +1]

# Save to JSON
save_signal_json(signal)
# → agents/intelligence/macro_signal_2026-05-13.json
```

## What It Does

Analyzes 4 macro indicators:
- **VIX** — Volatility (lower is better)
- **USDTRY** — Currency (TRY strength is positive)
- **BRENT** — Oil prices (demand indicator)
- **BIST100** — Istanbul stock exchange (sentiment)

Scores each component [-1, +1], then determines market regime:
- **RISK_ON** (≥ 0.3) — Growth appetite, risk assets favored
- **RISK_OFF** (≤ -0.3) — Risk aversion, flight to safety
- **TRANSITION** — Regime change in progress

## Run Example

```bash
python scripts/macro_signals_example.py
```

Output shows:
```
Regime: RISK_ON
Macro Environment Score: 0.58
Component Scores:
  VIX:     0.85
  USDTRY:  0.12
  BRENT:   0.45
  BIST100: 0.70
Latest Prices:
  USDTRY: 45.39
  BRENT: 107.41
  VIX: 17.99
  BIST100: 9876.50
```

JSON saved to: `agents/intelligence/macro_signal_2026-05-13.json`

## Common Operations

### Get Current Regime

```python
from src.signals.macro_signals import generate_macro_signal

signal = generate_macro_signal()
print(f"Current regime: {signal.regime}")
```

### Check if Risk-On

```python
signal = generate_macro_signal()
is_risk_on = signal.macro_environment_score > 0.3
print(f"Risk-on environment: {is_risk_on}")
```

### Get Component Scores

```python
signal = generate_macro_signal()
print(f"Volatility (VIX):       {signal.vix_score:.3f}")
print(f"Currency (USDTRY):      {signal.usdtry_score:.3f}")
print(f"Oil (BRENT):            {signal.brent_score:.3f}")
print(f"Equities (BIST100):     {signal.bist100_score:.3f}")
```

### Get Latest Prices

```python
signal = generate_macro_signal()
for symbol, price in signal.symbols.items():
    print(f"{symbol}: {price:.2f}")
```

### Save Signal

```python
from src.signals.macro_signals import generate_macro_signal, save_signal_json

signal = generate_macro_signal()
filepath = save_signal_json(signal)
print(f"Saved: {filepath}")
```

### Use Custom Weights

```python
signal = generate_macro_signal(weights={
    "vix": 0.30,        # Emphasize volatility
    "usdtry": 0.10,
    "brent": 0.20,
    "bist100": 0.40,
})
```

## Integration Examples

### With Analyst Agent

```python
from src.signals.macro_signals import generate_macro_signal

signal = generate_macro_signal()

# Add to analyst system prompt
analyst_context = f"""
Makro Ortam: {signal.regime}
Ortam Skoru: {signal.macro_environment_score:.2f}
- Volatilite (VIX): {signal.vix_score:.2f}
- Para Birimi (USDTRY): {signal.usdtry_score:.2f}
- Enerji (BRENT): {signal.brent_score:.2f}
- Hisse Piyasası (BIST100): {signal.bist100_score:.2f}
"""
```

### With Daily Briefing

```python
from src.signals.macro_signals import generate_macro_signal
import json

signal = generate_macro_signal()

briefing = {
    "timestamp": signal.timestamp,
    "macro_signal": {
        "regime": signal.regime,
        "environment_score": signal.macro_environment_score,
        "components": {
            "vix": signal.vix_score,
            "usdtry": signal.usdtry_score,
            "brent": signal.brent_score,
            "bist100": signal.bist100_score,
        },
        "prices": signal.symbols,
    },
}

with open("agents/intelligence/daily_briefing.json", "w") as f:
    json.dump(briefing, f, indent=2)
```

### Scheduled Daily (Cron)

```bash
# Run every day at 19:00 (after market close)
0 19 * * * cd /path && python -c "from src.signals.macro_signals import generate_macro_signal, save_signal_json; save_signal_json(generate_macro_signal())"
```

## Interpretation Guide

### Positive Scores = Good for Risk Assets

| Component | Positive | Negative |
|-----------|----------|----------|
| **VIX** | Low volatility (<15) | High volatility (>25) |
| **USDTRY** | TRY strengthens (down) | TRY weakens (up) |
| **BRENT** | Oil rising (demand ↑) | Oil falling (demand ↓) |
| **BIST100** | Index up (sentiment ↑) | Index down (sentiment ↓) |

### Regime Signals

| Regime | Score | Meaning |
|--------|-------|---------|
| RISK_ON | ≥ +0.3 | Growth markets favor risk assets |
| TRANSITION | -0.3 to +0.3 | Uncertain, regime change in progress |
| RISK_OFF | ≤ -0.3 | Risk aversion, flight to safety |

### Decision Rules

```
IF regime == "RISK_ON":
   → Favor growth stocks, emerging markets, high-yield bonds
   → Reduce hedges (buy calls, sell puts)
   → BIST100 outperformance likely

IF regime == "RISK_OFF":
   → Favor defensive stocks, government bonds, USD
   → Increase hedges (buy puts, buy calls)
   → BIST100 underperformance likely

IF regime == "TRANSITION":
   → High uncertainty, watch for confirmation
   → Risk events pending
   → Reduce position size until regime stabilizes
```

## Testing

```bash
# Run all tests
python -m pytest tests/test_macro_signals.py -v

# Run specific test
python -m pytest tests/test_macro_signals.py::TestRegimeDetection -v
```

Expected: **24 tests passing** ✅

## Files

| File | Purpose |
|------|---------|
| `src/signals/macro_signals.py` | Core module (230 lines) |
| `src/signals/__init__.py` | Exports |
| `tests/test_macro_signals.py` | 24 unit tests |
| `scripts/macro_signals_example.py` | Usage demo |
| `agents/intelligence/macro_signal_YYYY-MM-DD.json` | Daily output |
| `agents/intelligence/specs/SPEC_2026-05-13_macro_signals_detect_regime.md` | Implementation spec |

## Troubleshooting

**"Cannot generate signal: no macro data"**
→ Fetch macro data first: `python scripts/macro_data_example.py`

**"All scores are 0.0"**
→ Need 2+ days of data. Wait or fetch history.

**"No data for BIST100"**
→ Normal on weekends/holidays. Script handles gracefully.

---

See [MACRO_SIGNALS_README.md](MACRO_SIGNALS_README.md) for full documentation.
