# SPEC_STAGED_TP_1: Staged Take-Profit Mechanism (Technical Resistance-Based)

**Version:** 1.0 (Ruthless Alpha Philosophy)  
**Date:** 16 May 2026  
**Target Role:** Builder  
**Scope:** BIST30, staged exits via TP1/TP2/TP3 calculated from technical levels  
**Philosophy:** Systematic profit-taking at technical resistance + volatility inflection  

---

## 1. STAGED TP FRAMEWORK

### 1.1 Core Concept: Three-Tier Exit Strategy

```
Entry Signal → Position Opens → TP1 (50% exit) → TP2 (30% exit) → TP3 (20% exit)

Each TP tied to technical resistance level:
├─ TP1: First structural resistance (pivot, MA200, prior swing high)
├─ TP2: Fibonacci retracement (0.618 of move) or second resistance zone
└─ TP3: Trend breakout level or all-time high / extended fib (1.618)

Exit Execution:
├─ TP1: Market order or limit 1% above resistance (take liquidity)
├─ TP2: Limit order at fib level (patience, wait for pullback)
└─ TP3: Trailing stop or breakout confirmation (let winners run)
```

### 1.2 Exit Allocation

| TP Level | % of Position | Order Type | Execution Rule | Trigger Condition |
|---|---|---|---|---|
| **TP1** | 50% | Market/Limit | Hit or +1% buffer | Position reaches 5-10% gain or 2 days without new high |
| **TP2** | 30% | Limit | At fib 0.618 or pullback | Position reaches 15-20% gain or fib level touched |
| **TP3** | 20% | Trailing Stop | Dynamic (2-5% trail) | Position reaches 25%+ gain or trend breaks down |

---

## 2. TECHNICAL LEVEL DETECTOR MODULE

### 2.1 Module Interface (OHLCV Input → Resistance Output)

```python
class TechnicalLevelDetector:
    """
    Detects pivot points, Fibonacci levels, and structural resistance zones
    from OHLCV data. Used to calculate TP1, TP2, TP3 for staged exits.
    """
    
    def __init__(self, lookback_periods: dict = None):
        """
        Args:
            lookback_periods: {
                "pivot": 20,      # 20-day pivot calculation
                "swing_high": 60, # 60-day swing high for structural resistance
                "fib": 252,       # 252-day (1 year) for fib extension
                "ma200": 200      # 200-day moving average
            }
        """
        self.lookback = lookback_periods or {
            "pivot": 20,
            "swing_high": 60,
            "fib": 252,
            "ma200": 200
        }
    
    def detect_levels(self, ohlcv_data: pd.DataFrame) -> dict:
        """
        Main function: Detect all technical levels for position entry date.
        
        Args:
            ohlcv_data: DataFrame with columns [Date, Open, High, Low, Close, Volume]
                        Must include at least 252 days of history
        
        Returns:
            {
                "entry_price": float,
                "tp1": float,
                "tp2": float,
                "tp3": float,
                "tp1_type": str,        # "pivot", "ma200", "swing_high"
                "tp2_type": str,        # "fib_0.618", "2nd_resistance"
                "tp3_type": str,        # "trend_high", "fib_1.618"
                "support_1": float,     # Potential support for stop-loss
                "support_2": float,
                "confidence": float     # [0.6, 1.0] based on multiple level overlap
            }
        """
        pass
    
    def calculate_pivot_points(self, high: float, low: float, close: float) -> dict:
        """
        Standard pivot point calculation (daily).
        
        Returns:
            {
                "pivot": float,
                "resistance_1": float,
                "resistance_2": float,
                "support_1": float,
                "support_2": float
            }
        """
        pass
    
    def calculate_fibonacci_levels(self, ohlcv_data: pd.DataFrame, lookback: int) -> dict:
        """
        Calculate Fibonacci retracement and extension levels
        based on 252-day swing high/low.
        
        Returns:
            {
                "swing_high": float,
                "swing_low": float,
                "fib_0.236": float,  # Retracement
                "fib_0.382": float,
                "fib_0.618": float,
                "fib_1.000": float,  # 100% extension
                "fib_1.618": float   # 161.8% extension
            }
        """
        pass
    
    def calculate_moving_average_resistance(self, ohlcv_data: pd.DataFrame) -> dict:
        """
        Calculate MA50, MA100, MA200 as dynamic resistance levels.
        
        Returns:
            {
                "ma50": float,
                "ma100": float,
                "ma200": float,
                "ma_alignment": str  # "bullish" if 50>100>200, "bearish" if 50<100<200
            }
        """
        pass
    
    def identify_structural_resistance(self, ohlcv_data: pd.DataFrame, lookback: int) -> list:
        """
        Identify structural swing highs (local maxima) over lookback period.
        
        Returns:
            [
                {"price": 145.50, "date": "2026-03-15", "strength": 0.85},
                {"price": 148.30, "date": "2026-04-01", "strength": 0.92},
                ...
            ]
        """
        pass
    
    def calculate_atr_volatility(self, ohlcv_data: pd.DataFrame, period: int = 14) -> dict:
        """
        Average True Range for volatility-adjusted TP placement.
        
        Returns:
            {
                "atr": float,
                "atr_pct": float,  # ATR as % of current price
                "volatility_regime": str  # "low", "medium", "high"
            }
        """
        pass
```

### 2.2 Level Detection Algorithm (Pseudocode)

```python
def detect_levels(self, ohlcv_data: pd.DataFrame) -> dict:
    """
    Hierarchical level detection:
    1. Calculate pivot points (daily)
    2. Calculate Fibonacci levels (252-day)
    3. Identify structural resistance (60-day swings)
    4. Calculate MA200 (trend reference)
    5. Weight levels by frequency of overlap
    6. Output: TP1 (nearest), TP2 (second), TP3 (extended)
    """
    
    # Get current bar (entry point)
    current = ohlcv_data.iloc[-1]
    entry_price = current["Close"]
    
    # 1. Pivot points
    pivot = self.calculate_pivot_points(
        current["High"], current["Low"], current["Close"]
    )
    
    # 2. Fibonacci levels
    fib = self.calculate_fibonacci_levels(ohlcv_data, 252)
    
    # 3. Structural resistance
    resistance_zones = self.identify_structural_resistance(ohlcv_data, 60)
    
    # 4. Moving averages
    mas = self.calculate_moving_average_resistance(ohlcv_data)
    
    # 5. ATR for volatility adjustment
    atr_data = self.calculate_atr_volatility(ohlcv_data)
    
    # 6. Consolidate levels (entry_price < level < entry_price + 2×ATR)
    upside_levels = [
        {"price": pivot["resistance_1"], "type": "pivot_r1", "weight": 0.8},
        {"price": pivot["resistance_2"], "type": "pivot_r2", "weight": 0.6},
        {"price": mas["ma200"], "type": "ma200", "weight": 0.7},
        {"price": fib["fib_0.618"], "type": "fib_0.618", "weight": 0.8},
        {"price": resistance_zones[0]["price"] if resistance_zones else None, "type": "structural", "weight": 0.85},
        {"price": fib["fib_1.618"], "type": "fib_1.618", "weight": 0.6},
    ]
    
    # Filter valid levels (above entry, within 100%+ move)
    valid_levels = [
        l for l in upside_levels 
        if l["price"] and l["price"] > entry_price and l["price"] < entry_price * 2.0
    ]
    
    # Sort by price (ascending)
    valid_levels.sort(key=lambda x: x["price"])
    
    # Assign TP levels (nearest 3)
    tp1 = valid_levels[0] if len(valid_levels) > 0 else None
    tp2 = valid_levels[1] if len(valid_levels) > 1 else None
    tp3 = valid_levels[2] if len(valid_levels) > 2 else None
    
    # Fallback if not enough levels: use ATR multiples
    if not tp1:
        tp1 = {"price": entry_price + (1.5 * atr_data["atr"]), "type": "atr_1.5x"}
    if not tp2:
        tp2 = {"price": entry_price + (3.0 * atr_data["atr"]), "type": "atr_3.0x"}
    if not tp3:
        tp3 = {"price": entry_price + (5.0 * atr_data["atr"]), "type": "atr_5.0x"}
    
    # Calculate confidence (overlap of multiple level types)
    overlap_count = sum(1 for l in [tp1, tp2, tp3] if l["type"].startswith("structural") or "fib" in l["type"])
    confidence = 0.6 + (overlap_count * 0.15)  # [0.6, 0.95]
    
    return {
        "entry_price": entry_price,
        "tp1": tp1["price"],
        "tp2": tp2["price"],
        "tp3": tp3["price"],
        "tp1_type": tp1["type"],
        "tp2_type": tp2["type"],
        "tp3_type": tp3["type"],
        "support_1": pivot["support_1"],
        "support_2": pivot["support_2"],
        "confidence": confidence
    }
```

---

## 3. EXIT EXECUTION MECHANICS

### 3.1 TP1 Execution (50% exit, near-term profit-taking)

```
Trigger: 
├─ Price touches TP1 level OR
├─ 2 days elapsed without new high (exit conviction deterioration)
├─ OR conviction score drops (TP1 forced by signal collapse)

Order Type:
├─ Market order: Immediate exit if high-conviction
├─ Limit order: TP1 + 1% buffer (wait 1 hour, then market if not filled)

Example:
Entry: ASELS 120 TRY, volume 100K shares
TP1 calculated: 127.5 TRY (pivot R1)
TP1 order: Sell 50K shares at 127.5 TRY (or market if price exceeds)
Partial Fill Handling: Scale exit proportionally (if 40K filled, exit only 40K)
```

### 3.2 TP2 Execution (30% exit, second-tier profit)

```
Trigger:
├─ Price touches TP2 level (fib 0.618) AND 
├─ Position in profit (>15%) AND
├─ Momentum not accelerating (RSI < 70)

Order Type:
├─ Limit order at TP2 (patience, don't chase)
├─ If not filled within 3 days → lower to TP2 - 0.5% (give up some upside)
├─ If conviction score strengthens → hold TP2 (let winner run)

Example:
Remaining position: 50K shares (after TP1)
TP2 calculated: 133.2 TRY (fib 0.618)
TP2 order: Sell 15K shares (30% of original) at 133.2 TRY
Hold TP3: 35K shares trailing (20% of position)
```

### 3.3 TP3 Execution (20% exit, trend extension)

```
Trigger:
├─ One of:
│  ├─ Price touches TP3 level (fib 1.618 or trend break)
│  ├─ OR 10 days elapsed since entry (exit to avoid reversal)
│  ├─ OR macro regime deteriorates (BULL → NEUTRAL)

Order Type:
├─ Trailing stop: 2-5% trail below highest high
├─ Move stop up as price makes higher lows
├─ No limit order (let trailing stop protect gains)

Example:
Remaining position: 35K shares
TP3 calculated: 145 TRY (structural resistance)
TP3 order: Trailing stop at 2% trail from highest high
Highest high reached: 142 TRY → Stop at 139 TRY
Price pulls back to 139 → Exit 35K shares at market (~139)
```

---

## 4. EDGE CASES & FORCED EXITS

### 4.1 Conviction Collapse Exit

```
IF composite_score drops below 0.35:
├─ TP1 executed immediately (50% at market)
├─ TP2 held for 24h recovery window
├─ If score recovers >0.45 → resume trailing TP3
└─ If score stays <0.35 → force TP2+TP3 close at market
```

### 4.2 Macro Regime Deterioration

```
IF macro scaling drops from 1.0 → 0.8 (BULL → NEUTRAL):
├─ TP1 executed if not already (take profits)
├─ Hold TP2/TP3 for trailing

IF macro scaling drops from 0.8 → 0.0 (NEUTRAL → BEAR):
├─ All remaining TPs execute at market (emergency close)
└─ No holding into bear regime
```

### 4.3 Drawdown Hard Stop

```
IF portfolio DD > 15%:
├─ All positions: Exit TP1 immediately
├─ Hold TP2/TP3 for recovery
├─ IF DD > 20% → force close all remaining positions
```

---

## 5. INTEGRATION WITH POSITION SIZER

### 5.1 Data Flow

```
Entry Signal (BUY-STRONG)
  ↓
position_sizer_v2.calculate_size() → position_size (e.g., $32.5K)
  ↓
technical_level_detector.detect_levels(OHLCV) → TP1/TP2/TP3 prices
  ↓
order_engine.place_entry_order() + set_staged_exits(TP1, TP2, TP3)
  ↓
Position Open with 3 exit orders (TP1 market, TP2 limit, TP3 trailing)
```

### 5.2 Code Architecture

```python
# src/risk/technical_level_detector.py

class TechnicalLevelDetector:
    def __init__(self, ...):
        pass
    
    def detect_levels(self, ohlcv_data: pd.DataFrame) -> dict:
        """Detect TP1/TP2/TP3 from technical levels."""
        # Implementation from Section 2.2
        pass

# src/order_engine/staged_exit_manager.py

class StagedExitManager:
    def __init__(self, broker_api):
        self.broker = broker_api
    
    def set_staged_exits(self,
                        symbol: str,
                        entry_price: float,
                        tp1: float,
                        tp2: float,
                        tp3: float,
                        position_qty: int) -> dict:
        """
        Place three exit orders (TP1, TP2, TP3) for position.
        
        Returns:
            {
                "tp1_order_id": str,
                "tp2_order_id": str,
                "tp3_order_id": str,
                "tp1_price": float,
                "tp2_price": float,
                "tp3_price": float
            }
        """
        pass
    
    def execute_forced_exit(self, symbol: str, reason: str):
        """Execute emergency close (signal collapse, macro deterioration)."""
        pass
```

---

## 6. TESTING STRATEGY

- **4 unit tests:** Pivot calculation, fib levels, MA resistance, ATR
- **3 integration tests:** Level detection end-to-end, TP order placement, forced exit execution
- **2 edge case tests:** Signal collapse, macro regime shift
- **Regression:** 539 baseline ±3% (more aggressive exits acceptable)

---

## 7. BUILDER READINESS

**Status:** ✅ **YES**

**Timeline:** 2 weeks Phase 4.5 (parallel with position sizer)

**Blockers:** None (independent module)

---

**Document:** SPEC_STAGED_TP_1.md  
**For:** Builder (Phase 4.5 Implementation)  
**Philosophy:** Systematic, technical resistance-based profit extraction
