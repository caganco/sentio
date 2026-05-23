# SPEC: Kelly Criterion Position Sizing (KELLY_1) — Signal-Driven Risk Allocation

## 1. Overview

**Current Problem:**
- Position sizing today: Fixed % per position OR naive Kelly without conviction
- No integration between signal strength and position size
- Result: High-conviction positions same size as low-conviction — inefficient, misses upside/downside
- Risk: Portfolio concentration in mediocre ideas, miss conviction trades

**Target:**
- Conviction-aware position sizing via signal scores
- Kelly Criterion formula adapted for intraday/swing trading
- Fractional Kelly (conservative) to avoid ruin risk
- Portfolio heat management: per-position + portfolio-level limits

**Scope:**
1. Map signal engine scores (0-1) → conviction levels (high/medium/low)
2. Derive Kelly % from conviction + edge estimate
3. Apply fractional Kelly (0.25x) for real-world risk management
4. Enforce portfolio heat limits (position max 3%, portfolio max 15%)
5. Handle edge cases (negative Kelly, new positions, etc.)

---

## 2. Signal Engine Integration

### 2.1 Current Signal Structure

From daily_update.py pipeline:
```json
{
  "ticker": "AKSEN",
  "signals": {
    "tech": {
      "score": 0.45,      // Technical signals: momentum, MA, RSI (0-1)
      "weight": 0.20
    },
    "macro": {
      "score": 0.62,      // Macro alignment: USD/TRY, Brent, VIX, regime
      "weight": 0.333
    },
    "kap": {
      "score": 0.55,      // Disclosure quality, timing, volume
      "weight": 0.267
    },
    "risk": {
      "score": 0.38,      // Volatility, sector drawdown, liquidity
      "weight": 0.067
    }
  },
  "overall_score": 0.53,  // Weighted average
  "p_l_pct": -4.67,       // Current position P&L
  "stop_loss_pct": 5.0,   // Risk per position
  "ma_cross": "BUY",      // MA 20 > MA 50
  "rsi": 45.2
}
```

---

## 3. Conviction Mapping Algorithm

### 3.1 Conviction Calculation

**Input:**
- `overall_score` (0-1): Weighted average of all signal layers
- `signal_agreement` (0-1): How many layers agree with majority direction
- `macro_strength` (0-1): Macro score directly (0.333 weight × raw macro signal)

**Conviction Tiers:**

```
overall_score distance from 0.5 → Conviction Level

LOW:
  - Distance from 0.5 < 0.15 (scores 0.35-0.65)
  - OR signal_agreement < 0.5 (conflicting signals)
  - Examples: 0.52, 0.48, 0.55 with disagreement
  
MEDIUM:
  - Distance from 0.5 in [0.15, 0.30) (scores 0.20-0.80)
  - AND signal_agreement >= 0.5
  - Examples: 0.65, 0.40, 0.70
  
HIGH:
  - Distance from 0.5 >= 0.30 (scores <= 0.20 OR >= 0.80)
  - AND macro_strength >= 0.50
  - AND signal_agreement >= 0.75
  - Examples: 0.82, 0.18, 0.88 (with aligned macro)
```

**Algorithm:**
```python
def _map_conviction(self, signal_data: Dict[str, Any]) -> str:
    score = signal_data['overall_score']
    distance = abs(score - 0.5)
    agreement = self._calculate_agreement(signal_data['signals'])
    macro_strength = signal_data['signals']['macro']['score']
    
    if distance < 0.15 or agreement < 0.5:
        return "LOW"
    elif distance < 0.30:
        return "MEDIUM"
    elif distance >= 0.30 and macro_strength >= 0.50 and agreement >= 0.75:
        return "HIGH"
    else:
        return "MEDIUM"
```

### 3.2 Signal Agreement Calculation

Count how many signal layers point in same direction (> 0.5 or < 0.5):

```python
def _calculate_agreement(signals: Dict) -> float:
    layers = ['tech', 'macro', 'kap', 'risk']
    bullish = sum(1 for l in layers if signals[l]['score'] > 0.5)
    return bullish / len(layers)  # 0 to 1
```

---

## 4. Kelly Criterion Position Sizing

### 4.1 Win Probability Derivation

Map conviction → estimated win probability (edge estimate):

```
LOW conviction:
  - p (win probability) = 0.50 (fair coin flip, no edge)
  - Used for: New positions, conflicting signals, medium-confidence trades
  
MEDIUM conviction:
  - p = 0.52 (2% edge)
  - Used for: Aligned signals, macro confirmation, momentum
  
HIGH conviction:
  - p = 0.58 (8% edge)
  - Used: Strong macro + tech + KAP alignment, major trend confirmation
```

**Rationale:**
- BIST equity market: 50-58% win rates are realistic (not 60%+)
- Avoid over-confidence: conservative edge prevents ruin
- Tied to signal agreement + macro strength (not pure probability)

### 4.2 Kelly Formula

**Standard Kelly:**
```
K = (p × b - q) / b

Where:
  p = win probability (0.50 - 0.58)
  q = 1 - p (loss probability)
  b = reward/risk ratio (typically 1.0 for stop-loss defined positions)
  
Example:
  HIGH conviction: p = 0.58, b = 1.0
  K = (0.58 × 1.0 - 0.42) / 1.0 = 0.16 (16% of portfolio)
  
  MEDIUM conviction: p = 0.52, b = 1.0
  K = (0.52 × 1.0 - 0.48) / 1.0 = 0.04 (4% of portfolio)
  
  LOW conviction: p = 0.50, b = 1.0
  K = (0.50 × 1.0 - 0.50) / 1.0 = 0.00 (no edge, skip position)
```

### 4.3 Fractional Kelly (Conservative)

**Apply 0.25x Kelly to real positions:**

```
Fractional Kelly = K × 0.25

Rationale:
  - Reduces volatility (1/4 of full Kelly variance)
  - Prevents catastrophic ruin (full Kelly can wipe accounts on bad streak)
  - Optimal for multi-position portfolio (not single bet)
  - Industry standard for risk-averse traders

Examples:
  HIGH conviction: 0.16 × 0.25 = 4% position size
  MEDIUM conviction: 0.04 × 0.25 = 1% position size
  
Effective portfolio allocations:
  5 HIGH conviction positions: 5 × 4% = 20% (remaining 80% cash/hedges)
  10 MEDIUM conviction positions: 10 × 1% = 10%
  Mixed: 2 HIGH + 5 MEDIUM = 8% + 5% = 13%
```

---

## 5. Portfolio Heat Management

### 5.1 Portfolio Heat Definition

**Heat = Sum of (position_size% × stop_loss%) across all positions**

```
Example portfolio:
  AKSEN:   size=4%, stop=5% → heat = 0.04 × 0.05 = 0.20%
  TTKOM:   size=3%, stop=4% → heat = 0.03 × 0.04 = 0.12%
  TAVHL:   size=2%, stop=6% → heat = 0.02 × 0.06 = 0.12%
  ──────────────────────────────────────────────────
  Total heat = 0.44%
  
Max portfolio heat = 10% (development stage limit)
  → Can sustain ~23 simultaneous stop-losses @ avg 5% stop
  → Prudent for swing/position trading (not day trading)
```

### 5.2 Position Sizing Limits

```
Per-Position Limits:
  - Max single position: 3% of portfolio
  - Min position (skip): < 0.5%
  - Stop loss: Determined per signal (volatility-based, typically 4-6%)

Portfolio Heat Limits:
  - Development stage: Max 10%
  - Production stage: Max 5-8% (TBD after Kelly validation)
  
Heat Calculation:
  heat = sum(size[i] × stop[i]) for all positions
  if heat > limit:
    ACTION: Rebalance (scale down lowest conviction) OR exit oldest position
```

### 5.3 Heat Rebalancing Strategy

When portfolio heat exceeds limit:

```
1. PROPORTIONAL SCALING (preferred):
   - Scale all new position sizes down by factor (limit / current_heat)
   - Example: heat=12%, limit=10% → scale=10/12=0.83x
   - Recommend: "SCALE positions to 83% to meet heat limit"
   
2. SELECTIVE EXIT (tactical):
   - Exit lowest conviction position (if in loss)
   - Exit oldest position (portfolio rotation)
   - Manually specified positions
   - Recommend: "EXIT TAVHL (LOW conviction, -3.5% P&L) to reduce heat to 8%"
   
3. NO NEW POSITIONS (restrictive):
   - Pause new position entry until heat drops
   - Only allow scaling existing HIGH conviction positions
```

---

## 6. Edge Cases & Error Handling

### 6.1 Negative Kelly (No Edge)

```
Scenario: LOW conviction signal
  - p = 0.50, b = 1.0
  - K = (0.50 - 0.50) / 1.0 = 0.0
  
Action: SKIP position
  - Do not size it at 0%
  - Return conviction="LOW" with sizing=None
  - Log: "AKSEN: LOW conviction (0.52), no edge — skip sizing"
  
Reasoning:
  - Fair coin flip: no statistical edge
  - Risk capital better deployed elsewhere
  - Prevents over-diversification into mediocre ideas
```

### 6.2 Stress Market (Elevated VIX)

```
Scenario: VIX > 25 (stress mode)
  - Reduce all Kelly estimates by 30%
  - Apply additional 0.75x factor
  
Formula:
  Adjusted Kelly = K × 0.75
  
Examples:
  HIGH conviction: 0.16 → 0.12 (3% fractional)
  MEDIUM conviction: 0.04 → 0.03 (0.75% fractional)
  
Rationale:
  - Higher volatility = wider stops = more heat
  - Stress markets favor smaller positions
  - Preserve capital for recovery opportunities
```

### 6.3 Losing Positions (Don't Add)

```
Scenario: Existing position down 3%
  - Next signal comes with HIGH conviction
  
Action:
  - DO NOT increase position size
  - Hold current size or reduce (if conviction changes to LOW)
  - Comment: "Position down 3%, hold sizing — evaluate next review"
  
Reasoning:
  - Avoid averaging down into failed thesis
  - Conviction ≠ profit guarantee
  - Let stop-loss work if thesis breaks
```

### 6.4 Signal Disagreement (Reduce)

```
Scenario: tech=0.85 (BUY), macro=0.35 (SELL), kap=0.60 (BUY)
  - Agreement = 2/4 = 0.5 (borderline)
  - Overall score = (0.85×0.20 + 0.35×0.333 + 0.60×0.267 + ?) = conflicting
  
Action:
  - Conviction = MEDIUM (not HIGH despite tech extreme)
  - Kelly reduced due to disagreement
  - Size to 1% instead of 4%
  - Log: "AKSEN: Conflicting signals (tech vs macro) — MEDIUM conviction"
```

### 6.5 New Portfolio (Bootstrap)

```
Scenario: No existing positions, starting fresh
  - Can size up to 10% portfolio heat with new positions
  - First position: 3% max (avoid over-concentration)
  - Second-fifth: Build up to 1-4% each based on conviction
  
Example plan:
  AKSEN (HIGH): 4%
  TTKOM (HIGH): 3%
  TAVHL (MEDIUM): 1%
  KCHOL (MEDIUM): 1%
  ─────────────────
  Total: 9% with ~0.5% heat (assuming 5-6% stops)
```

---

## 7. Implementation Specification

### 7.1 KellySizer Class (src/risk/kelly.py)

```python
from typing import Any, Dict, Optional

class KellySizer:
    def __init__(
        self,
        portfolio_value_pct: float,
        kelly_fraction: float = 0.25,
        max_position_pct: float = 0.03,
        max_portfolio_heat_pct: float = 0.10,
    ):
        """
        Args:
            portfolio_value_pct: Portfolio size as % (for Kelly normalization)
            kelly_fraction: Fractional Kelly (0.25 = conservative)
            max_position_pct: Max single position size (3% default)
            max_portfolio_heat_pct: Max sum(size × stop_loss) (10% default)
        """
        
    def size_position(
        self,
        ticker: str,
        signal_data: Dict[str, Any],
        current_positions: Dict[str, Dict] = None,
    ) -> Dict[str, Any]:
        """
        Size a position based on signal conviction.
        
        Args:
            ticker: Stock ticker (e.g., "AKSEN")
            signal_data: {
                "overall_score": 0.65,
                "signals": {
                    "tech": {"score": 0.45, "weight": 0.20},
                    "macro": {"score": 0.62, "weight": 0.333},
                    "kap": {"score": 0.55, "weight": 0.267},
                    "risk": {"score": 0.38, "weight": 0.067}
                },
                "stop_loss_pct": 5.0
            }
            current_positions: {"AKSEN": {"size": 0.04, "pnl": -3.5}, ...}
        
        Returns: {
            "ticker": "AKSEN",
            "conviction": "HIGH",  # HIGH, MEDIUM, LOW
            "current_size_pct": 0.03,
            "recommended_size_pct": 0.04,
            "kelly_pct": 16,  # Full Kelly (before fraction)
            "kelly_fractional_pct": 4,  # After 0.25x
            "win_probability": 0.58,
            "reward_risk_ratio": 1.0,
            "action": "HOLD"  # HOLD, SCALE, ADD, REDUCE, EXIT
        }
        """
        
    def calculate_portfolio_heat(
        self,
        positions: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Calculate total portfolio heat.
        
        Args:
            positions: {
                "AKSEN": {"size": 0.04, "stop_loss": 0.05},
                "TTKOM": {"size": 0.03, "stop_loss": 0.04},
                ...
            }
        
        Returns: {
            "total_heat_pct": 0.44,
            "max_heat_pct": 10.0,
            "status": "OK",  # OK, WARNING, CRITICAL
            "recommendation": "Portfolio heat 0.44% is well within limit"
        }
        """
```

### 7.2 PortfolioHeat Class (src/risk/portfolio_heat.py)

```python
class PortfolioHeat:
    def __init__(self, max_heat_pct: float = 0.10):
        self.max_heat = max_heat_pct
        
    def add_position(self, ticker: str, size_pct: float, stop_loss_pct: float):
        """Add a position to heat tracking."""
        
    def check_heat(self) -> Dict[str, Any]:
        """Check current heat vs limit."""
        
    def rebalance(self, action: str = "scale") -> Dict[str, Any]:
        """
        Rebalance portfolio to meet heat limit.
        
        action: "scale" (proportional) | "exit_lowest" | "exit_oldest"
        """
```

### 7.3 Integration Points

1. **daily_update.py:**
   - After strategist_report, call kelly_sizer.size_position() for each ticker
   - Add Kelly sizing output to report_data["kelly_sizing"] for each position

2. **Strategist Agent Report:**
   - Include sizing recommendation: "AKSEN: 4% (HIGH conviction, 0.58 win prob)"
   - Add confidence indicator: conviction ± macro strength

3. **Portfolio Management:**
   - Track heat before entering new positions
   - Rebalance if heat > 10%
   - Manual override via config (pause new positions, scale existing, etc.)

---

## 8. Test Specification (15 Tests)

### 8.1 Conviction Mapping (3 tests)

1. **test_conviction_high_agreement:**
   - Input: score=0.82, agreement=0.75, macro=0.60
   - Expected: "HIGH"

2. **test_conviction_medium_distance:**
   - Input: score=0.65, agreement=0.5, macro=0.40
   - Expected: "MEDIUM"

3. **test_conviction_low_agreement:**
   - Input: score=0.52, agreement=0.25, macro=0.30
   - Expected: "LOW"

### 8.2 Kelly Calculation (4 tests)

4. **test_kelly_high_conviction:**
   - Input: conviction="HIGH", p=0.58, b=1.0
   - Expected: kelly_pct=16, fractional=4

5. **test_kelly_medium_conviction:**
   - Input: conviction="MEDIUM", p=0.52, b=1.0
   - Expected: kelly_pct=4, fractional=1

6. **test_kelly_no_edge:**
   - Input: conviction="LOW", p=0.50, b=1.0
   - Expected: kelly_pct=0, action="SKIP"

7. **test_kelly_stress_market:**
   - Input: HIGH conviction, VIX=30
   - Expected: kelly_pct reduced by 25% (0.75x factor)

### 8.3 Position Limits (3 tests)

8. **test_position_max_3_pct:**
   - Input: HIGH conviction, kelly=16%
   - Expected: size capped at 3%, kelly limits position

9. **test_position_min_0_5_pct:**
   - Input: MEDIUM conviction, kelly=1%
   - Expected: size=0.5% (below min → skip)

10. **test_position_loses_skip:**
    - Input: TAVHL down 5%, signal says "hold"
    - Expected: DO NOT increase size, hold current or reduce

### 8.4 Portfolio Heat (3 tests)

11. **test_heat_calculation:**
    - Positions: AKSEN (4%, 5%), TTKOM (3%, 4%)
    - Expected: heat = 0.20% + 0.12% = 0.32%

12. **test_heat_exceeds_limit:**
    - Positions total heat = 12%, limit = 10%
    - Expected: status="CRITICAL", recommend scale to 83%

13. **test_heat_rebalance_scale:**
    - Positions: 5 × 3%, stops: 5 × 5% → heat=7.5%
    - After scale to 6.67%: heat=5% (within 10%)

### 8.5 Edge Cases (5 tests)

14. **test_disagreement_signals:**
    - tech=0.85, macro=0.35, kap=0.60 (agreement=0.5)
    - Expected: conviction capped at "MEDIUM", size reduced

15. **test_new_portfolio_bootstrap:**
    - No existing positions, 5 signals
    - Expected: HIGH signals sized at 3-4%, MEDIUM at 1%, total heat ~0.5%

---

## 9. Success Criteria

| Criterion | Target | How to Verify |
|-----------|--------|---------------|
| Conviction accuracy | ±5% agreement error | 100+ position backtest, compare to manual review |
| Kelly formula correctness | Matches textbook formula | Math validation, test case validation |
| Fractional Kelly safety | 0.25x only | Code audit: all outputs × 0.25 |
| Position limits enforced | All positions ≤ 3% | Portfolio snapshot, max check |
| Portfolio heat tracked | ±0.1% error | 10+ heat calculations vs manual |
| Edge case handling | 5/5 scenarios covered | All 5 edge case tests pass |
| Test coverage | 15 tests, all pass | pytest result: 15/15 passing |
| Zero regression | 372 tests continue | Full suite: 387 passing (372 + 15 new) |

---

## 10. Acceptance Criteria

✅ SPEC_KELLY_1 is complete when:

1. `src/risk/kelly.py` with `KellySizer` class
   - Conviction mapping working
   - Kelly formula accurate
   - Fractional Kelly applied
   - Position limits enforced

2. `src/risk/portfolio_heat.py` with `PortfolioHeat` class
   - Heat calculation correct
   - Rebalancing logic working
   - Limit enforcement

3. `daily_update.py` integration
   - Kelly output added to report_data
   - Sizing info passed to Strategist agent

4. `Strategist agent` integration
   - Kelly sizing included in report narrative
   - Conviction displayed with position recommendation

5. Test coverage
   - 15 comprehensive tests (conviction, Kelly, limits, heat, edge cases)
   - All tests passing
   - 372+ total tests pass (zero regression)

6. Documentation
   - Code comments for non-obvious logic
   - Docstrings on public methods
   - Integration example in daily_update.py
