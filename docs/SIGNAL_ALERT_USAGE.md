# Signal Alert System — Usage Guide

## Stop-Loss Approach Warning

### Quick Reference

```python
from src.portfolio.monitor import (
    check_stop_loss_approach,
    format_stop_approach_alert,
    check_portfolio_alerts,
)
```

### Example 1: Check Single Position

```python
# Position: bought AKSEN at ₺100, currently trading at ₺93
alert = check_stop_loss_approach("AKSEN", current_price=93.0, entry_price=100.0)

# Returns PositionAlert with:
# - symbol: "AKSEN"
# - current_price: 93.0
# - entry_price: 100.0
# - stop_loss_price: 92.0  (entry * 0.92)
# - distance_to_stop_pct: 1.09%
# - is_approaching_stop: True

# Format for reporting:
if alert.is_approaching_stop:
    message = format_stop_approach_alert(alert)
    # Output: "⚠️ AKSEN STOP_APPROACHING — Stop: ₺92.00, Mevcut: ₺93.00, Mesafe: %1.1"
```

### Example 2: Check Entire Portfolio

```python
positions = {
    "AKSEN": {"entry_price": 100.0, "last_price": 93.0},
    "GARAN": {"entry_price": 50.0, "last_price": 49.0},
    "AKBNK": {"entry_price": 80.0, "last_price": 72.0},
}

current_prices = {
    "AKSEN": 93.0,
    "GARAN": 49.0,
    "AKBNK": 72.0,
}

alerts = check_portfolio_alerts(positions, current_prices)

# Filter for warnings only
warnings = [a for a in alerts if a.is_approaching_stop]
for alert in warnings:
    print(format_stop_approach_alert(alert))

# Output:
# ⚠️ AKSEN STOP_APPROACHING — Stop: ₺92.00, Mevcut: ₺93.00, Mesafe: %1.1
```

## Integration into Backtest Engine

```python
# In src/backtest/engine.py _update_portfolio() method:

from src.portfolio.monitor import check_portfolio_alerts, format_stop_approach_alert

# After updating positions at current_date:
current_prices_snapshot = {
    symbol: self.positions[symbol]["last_price"]
    for symbol in self.positions
}

alerts = check_portfolio_alerts(self.positions, current_prices_snapshot)

for alert in alerts:
    if alert.is_approaching_stop:
        msg = format_stop_approach_alert(alert)
        self.audit_trail.append({
            "date": current_date,
            "alert_type": "STOP_APPROACHING",
            "message": msg,
        })
        logger.warning(msg)
```

## Strategist Output Format

Every recommendation MUST include:

```
ACTION: [BUY | SELL | HOLD | WATCH]
PRICE: [₺amount or "piyasa"]
DEADLINE: [bugün | bu hafta | açık]
OVERRIDE_CONDITION: [condition to reverse this decision]
```

### Example Strategist Output

```
AKSEN:
- Aylar sonra ilk kez net 50 fiyatın altında (gerçekten yağmur).
- Teknik: RSI 38 (oversold), hacim ↓ (zayıf satış), 200MA'nın 8% altında.
- Makro: CDS artış, VIX 22 — müdahalenin avını tıksırıyor.
- Hikaye: Dış piyasalar baskıda, AKSEN'in tersine çevirmesi için daha çok veri lazım.

ACTION: WATCH
PRICE: piyasa
DEADLINE: bu hafta
OVERRIDE_CONDITION: CDS 350'yi kırsa SELL, VIX >25 ise HOLD'u devam, RSI <25 olursa BUY'a çevir
```

## Thresholds and Constants

### Defined in `src/signals/thresholds.py`

```python
EXIT_STOP_LOSS = 0.92          # Stop-loss at -8% from entry
EXIT_PROFIT_TARGET = 1.20      # Profit target at +20% from entry
STOP_APPROACH_BUFFER = 0.03    # Warning zone: 3% above stop
```

### Alert Trigger Logic

Position triggers `⚠️ STOP_APPROACHING` when:

```
stop_loss_price = entry_price * 0.92
approach_threshold = stop_loss_price * 1.03
alert = current_price <= approach_threshold AND current_price > stop_loss_price
```

Example with entry ₺100:
- Stop-loss price: ₺92.00
- Approach threshold: ₺94.76 (92 × 1.03)
- Alert triggers if price is ₺92.01 to ₺94.76
- No alert if price > ₺94.76 or ≤ ₺92.00

---

## Module Reference

### `check_stop_loss_approach(symbol: str, current_price: float, entry_price: float) → PositionAlert`

**Returns:**
- `PositionAlert` dataclass containing all position metrics and alert status

**Parameters:**
- `symbol`: Ticker symbol (e.g., "AKSEN")
- `current_price`: Current market price
- `entry_price`: Entry price at position open

---

### `format_stop_approach_alert(alert: PositionAlert) → str`

**Returns:**
- Alert message if `alert.is_approaching_stop` is True
- Empty string if position is safe

**Format:**
```
⚠️ SYMBOL STOP_APPROACHING — Stop: ₺X.XX, Mevcut: ₺Y.YY, Mesafe: %Z.Z
```

---

### `check_portfolio_alerts(positions: dict, current_prices: dict) → list[PositionAlert]`

**Returns:**
- List of `PositionAlert` objects for all positions in portfolio

**Parameters:**
- `positions`: Dictionary of open positions with structure:
  ```python
  {
    "AKSEN": {"entry_price": 100.0, ...},
    "GARAN": {"entry_price": 50.0, ...},
  }
  ```
- `current_prices`: Dictionary of current prices:
  ```python
  {
    "AKSEN": 93.0,
    "GARAN": 49.0,
  }
  ```

---

## Testing

All functionality is tested in `tests/test_signal_alert.py` (7 tests):

```bash
python -m pytest tests/test_signal_alert.py -v
```

- ✅ Approaching detection (within/outside buffer)
- ✅ Exact stop-loss handling
- ✅ Below stop-loss handling
- ✅ Alert message formatting
- ✅ Portfolio-wide checks
