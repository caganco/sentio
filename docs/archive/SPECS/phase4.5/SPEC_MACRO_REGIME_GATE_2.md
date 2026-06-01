# SPEC_MACRO_REGIME_GATE_2: Binary Gate → Position Scaling (Ruthless Alpha)

**Version:** 2.0 (Position Scaling Transformation)  
**Date:** 16 May 2026  
**Target Role:** Builder  
**Scope:** Transform macro regime gate from binary (on/off) to continuous scaling (0.0-1.0)  
**Philosophy:** Aggressive in bull regime, cautious in neutral, dormant in bear  

---

## 1. MACRO REGIME GATE TRANSFORMATION

### 1.1 Current State (Phase 4.4) vs New State (Phase 4.5)

| Aspect | Phase 4.4 (Binary) | Phase 4.5 (Scaling) | Change |
|---|---|---|---|
| **Bull (>60)** | ALLOW all trades | 100% position sizing | ✓ Same |
| **Neutral (45-60)** | ALLOW trades (cautious) | 80% position sizing | ✓ Scale down |
| **Bear (<45)** | BLOCK all trades | 0% position sizing | ✓ Disable |
| **Mechanism** | Gate (yes/no) | Continuous multiplier | ✓ Refined |

### 1.2 Core Transformation

```
OLD (Binary Gate):
─────────────────
macro_regime_score → Gate logic → {"ALLOW": true/false}
                                  → Position sizing: all-or-nothing

NEW (Position Scaling):
──────────────────────
macro_regime_score → Scaling function → Position scaling multiplier [0.0, 1.0]
                                       → Applied to conviction-based sizing
```

---

## 2. MACRO REGIME SCORING (UNCHANGED from L2)

### 2.1 Regime Score Source

```
L2_MACRO_SCORE = Composite from:
├─ USD/TRY trend (0.25 weight)
├─ Turkish CDS spread (0.25 weight)
├─ Brent oil price (0.20 weight)
├─ Yield curve (0.15 weight)
└─ TCMB rate trend (0.15 weight) [NEW in Phase 4.4, D-035]

Output range: [0, 1]
Daily update: EOD (16:45 Istanbul time)
```

### 2.2 Regime Classification (From L2 Score)

```
L2_MACRO_SCORE → Regime:
├─ ≥0.60 → BULL (strong Turkish macro, USD weak, CDS low, oil +, rates rising)
├─ 0.45-0.59 → NEUTRAL (mixed signals, no clear direction)
└─ <0.45 → BEAR (weak Turkish macro, USD strong, CDS high, oil -, rates falling)
```

---

## 3. POSITION SCALING ALGORITHM

### 3.1 Macro Scaling Multiplier Derivation

```python
def calculate_macro_regime_scaling(l2_macro_score: float) -> float:
    """
    Convert L2 macro score to position sizing multiplier.
    
    Args:
        l2_macro_score: [0, 1] from L2 layer
    
    Returns:
        scaling_multiplier: [0.0, 1.0] applied to conviction-based position size
    """
    
    if l2_macro_score >= 0.60:
        # BULL regime
        regime = "BULL"
        scaling_multiplier = 1.0  # Full position sizing
    elif l2_macro_score >= 0.45:
        # NEUTRAL regime: linear scaling from 0.8 to 1.0
        regime = "NEUTRAL"
        scaling_multiplier = 0.8 + ((l2_macro_score - 0.45) / 0.15) * 0.2
        # At 0.45: 0.8, at 0.525: 0.9, at 0.60: 1.0
    else:
        # BEAR regime
        regime = "BEAR"
        scaling_multiplier = 0.0  # No new trades, hold existing (trailing stops)
    
    return scaling_multiplier


# Example calculations:
# l2_score = 0.70 (Bull) → scaling = 1.0 → Full 32.5% position size
# l2_score = 0.52 (Neutral) → scaling = 0.8 + (0.07/0.15)×0.2 = 0.893 → 29% position size
# l2_score = 0.40 (Bear) → scaling = 0.0 → No new entries, exit open positions
```

### 3.2 Scaling Matrix (Conviction × Regime)

| Conviction Tier | Bull (1.0) | Neutral (0.8) | Bear (0.0) | Action |
|---|---|---|---|---|
| **BUY-STRONG** | 32.5% | 26% | 0% | ENTER bull/neutral; EXIT bear |
| **BUY-MEDIUM** | 17.5% | 14% | 0% | ENTER bull/neutral at 15-20% sizing; EXIT bear |
| **BUY-WEAK** | 0% | 0% | 0% | WATCHLIST (all regimes) |
| **HOLD** | Hold | Hold | Exit/Hold | Scale with regime |
| **SELL-SIGNAL** | TP1 | TP1 | Exit all | Regime-dependent exit |

**Interpretation:**
- Bull: Aggressive (full sizing for BUY-STRONG)
- Neutral: Cautious (80% sizing, more selective)
- Bear: Dormant (no new trades, close positions gracefully)

---

## 4. POSITION MANAGEMENT BY REGIME

### 4.1 BULL Regime (L2 ≥0.60)

```
New Entries:
├─ BUY-STRONG: Full 32.5% position size (max 4 concurrent)
├─ BUY-MEDIUM: Full 17.5% position size (max 2 concurrent)
├─ Scale-ins: Allowed on momentum continuation (add to existing <20% limit)
└─ Watchlist: BUY-WEAK positions monitored (no sizing)

Open Positions:
├─ TP1/TP2/TP3: Execute as normal (aggressive profit-taking)
├─ Trailing stops: 2-5% trail (let winners run)
└─ Conviction collapse: Execute TP1 immediately if score drops

Portfolio:
├─ Allocation: 95-100% deployed across 4 positions
├─ Cash: 0-5% (opportunistic)
└─ Leverage: Not applicable (cash account)
```

### 4.2 NEUTRAL Regime (L2 0.45-0.59)

```
New Entries:
├─ BUY-STRONG: 80% of sizing (26% instead of 32.5%, max 4 concurrent)
├─ BUY-MEDIUM: 80% of sizing (14% instead of 17.5%, max 2 concurrent)
├─ Scale-ins: NOT allowed (avoid adding to risk)
└─ Watchlist: Stricter criteria (wait for clarity)

Open Positions:
├─ TP1: Execute if triggered (prudent profit-taking)
├─ TP2/TP3: Hold but tighten trailing stops (5-3% instead of 2-5%)
├─ New tier entries: BUY-STRONG and BUY-MEDIUM both allowed at 80% scaling
└─ Conviction collapse: Execute all TPs (TP1 + TP2) immediately

Portfolio:
├─ Allocation: 65-80% (reduce from bull, wait for clarity)
├─ Cash: 20-35% (dry powder for bull clarification)
└─ Profit redeployment: Hold in cash, await clarity
```

### 4.3 BEAR Regime (L2 <0.45)

```
New Entries:
├─ BUY-STRONG: NOT allowed (0% sizing, no new positions)
├─ BUY-MEDIUM: NOT allowed (0% sizing, no new positions)
├─ Watchlist: Suspend (market too risky)
└─ Monitor: Wait for recovery signal (L2 > 0.50)

Open Positions:
├─ TP1: Execute immediately (reduce exposure)
├─ TP2: Execute (defensive exit)
├─ TP3: Execute or tight trailing stop (max 3% trail)
├─ Conviction collapse: Force close all (emergency liquidation)
└─ If positions remain: Hold TP3 only (trailing for technical recovery)

Portfolio:
├─ Allocation: 0-20% (liquidate majority)
├─ Cash: 80-100% (defensive position)
├─ Mode: WAIT for macro recovery (B

UY signals halted)
└─ Reentry: Only when L2 > 0.55 + BUY-STRONG signal
```

---

## 5. REGIME TRANSITIONS & HYSTERESIS

### 5.1 Transition Rules (Avoid Whipsaw)

```
Hysteresis: Prevent rapid regime flipping on single-day volatility

From BULL → NEUTRAL:
├─ Require: L2 drops below 0.60 for 2 consecutive days
├─ Action: Scale down from 100% → 80% (no emergency liquidation)
├─ Position: Continue with tighter stops (TP1 execution encouraged)

From NEUTRAL → BULL:
├─ Require: L2 rises above 0.60 for 1 day (fast recovery)
├─ Action: Scale up from 80% → 100% (enable full sizing)
├─ Position: Resume aggressive profit-taking (TP2/TP3 trails)

From NEUTRAL → BEAR:
├─ Require: L2 drops below 0.45 for 1 day (urgent deterioration)
├─ Action: Scale down from 80% → 0% (reduce exposure)
├─ Position: Execute TP1+TP2, hold TP3 with tight stop

From BEAR → NEUTRAL:
├─ Require: L2 rises above 0.50 for 2 days (recovery clarity)
├─ Action: Scale up from 0% → 80% (cautious re-entry)
├─ Position: Resume if BUY-STRONG signals available
```

### 5.2 Transition Logging

```python
class RegimeTransitionLog:
    def record_transition(self, from_regime: str, to_regime: str, trigger_l2_score: float):
        """
        Log macro regime transitions with timestamp and actions taken.
        
        Example:
        {
            "timestamp": "2026-05-16 16:45",
            "l2_score": 0.58,
            "from_regime": "NEUTRAL",
            "to_regime": "BULL",
            "action": "Scale up to 100%",
            "positions_affected": 2,
            "new_allocation": 0.95
        }
        """
        pass
```

---

## 6. INTEGRATION WITH POSITION SIZER V2

### 6.1 Data Flow

```
L2 Macro Layer (daily EOD)
        ↓
l2_macro_score [0, 1]
        ↓
calculate_macro_regime_scaling(l2_macro_score) → scaling_multiplier [0.0, 1.0]
        ↓
position_sizer_v2.calculate_size(
    composite_score,
    macro_scaling_multiplier,  ← NEW PARAMETER
    portfolio_equity,
    current_positions
) → Position size in dollars
        ↓
Order engine: ENTER / HOLD / EXIT
```

### 6.2 Code Architecture

```python
# src/signals/macro_regime_gate.py (NEW)

class MacroRegimeGate:
    def __init__(self):
        self.current_regime = "NEUTRAL"
        self.last_transition = None
    
    def calculate_scaling(self, l2_macro_score: float) -> dict:
        """
        Calculate position scaling multiplier from L2 macro score.
        
        Returns:
            {
                "l2_score": float,
                "regime": str,  # "BULL", "NEUTRAL", "BEAR"
                "scaling_multiplier": float,  # [0.0, 1.0]
                "regime_changed": bool,
                "new_regime": str  # If transition occurred
            }
        """
        # Implementation from Section 3.1
        pass
    
    def should_allow_new_entry(self, regime: str, conviction_tier: str) -> bool:
        """
        Gate logic: Does macro regime allow this conviction tier entry?
        BUY-STRONG and BUY-MEDIUM allowed in BULL/NEUTRAL; blocked in BEAR.
        
        Returns: True if entry allowed, False otherwise
        """
        allowed_tiers = {"BUY-STRONG", "BUY-MEDIUM"}
        
        if regime in ("BULL", "NEUTRAL"):
            return conviction_tier in allowed_tiers
        else:  # BEAR regime
            return False
    
    def get_position_scaling(self, regime: str) -> float:
        """Returns scaling multiplier [0, 1] for regime."""
        scaling_map = {"BULL": 1.0, "NEUTRAL": 0.8, "BEAR": 0.0}
        return scaling_map.get(regime, 0.8)
```

---

## 7. EXIT MECHANICS BY REGIME

### 7.1 TP Execution by Regime

```
BULL Regime:
├─ TP1: Standard (50% exit at first resistance)
├─ TP2: Standard (30% exit at fib 0.618)
└─ TP3: Trailing stop, aggressive (2% trail, let winners run)

NEUTRAL Regime:
├─ TP1: Encouraged (50% exit, reduce risk)
├─ TP2: Execute if touched (30% exit, don't be greedy)
└─ TP3: Tighter trailing (3% trail instead of 2%)

BEAR Regime:
├─ TP1: Execute immediately (reduce exposure)
├─ TP2: Execute immediately (lock in profits)
└─ TP3: Execute or hold with 2% hard stop (no trailing flexibility)
```

### 7.2 Forced Exit Triggers (Regime-Dependent)

```python
def should_force_exit_position(regime: str, position_age_days: int, conviction_score: float) -> bool:
    """
    Determine if position should be forcibly exited based on regime.
    """
    
    if regime == "BEAR":
        # Bear regime: exit aggressively
        return conviction_score < 0.50 or position_age_days > 5
    elif regime == "NEUTRAL":
        # Neutral: exit if conviction strong collapse or age >8 days
        return conviction_score < 0.35 or position_age_days > 8
    else:  # BULL
        # Bull: only exit on conviction collapse
        return conviction_score < 0.35
```

---

## 8. RISK MANAGEMENT BY REGIME

### 8.1 Max Drawdown Limits

```
BULL Regime:
├─ Portfolio drawdown limit: 15% (aggressive)
├─ Single position max loss: 8%
└─ Stop-loss: TP2 - 2% or support level (whichever higher)

NEUTRAL Regime:
├─ Portfolio drawdown limit: 12% (cautious)
├─ Single position max loss: 6%
└─ Stop-loss: TP2 - 3% (tighter)

BEAR Regime:
├─ Portfolio drawdown limit: 8% (defensive, avoid large losses)
├─ Single position max loss: 4%
└─ Stop-loss: TP1 level (tight protection, protect capital)
```

### 8.2 Position Limits by Regime

```
BULL: Max 6 concurrent positions (4 BUY-STRONG + 2 BUY-MEDIUM)
NEUTRAL: Max 5 concurrent (3-4 BUY-STRONG + 1-2 BUY-MEDIUM, reduce concentration)
BEAR: Max 0 new positions (BUY-STRONG blocked, BUY-MEDIUM blocked, liquidate majority)
```

---

## 9. MONITORING & ALERTS

### 9.1 Daily Regime Status Report

```json
{
    "date": "2026-05-16",
    "l2_macro_score": 0.58,
    "current_regime": "NEUTRAL",
    "scaling_multiplier": 0.893,
    "regime_changed_today": false,
    "days_in_regime": 3,
    "actions_applied": [
        "New BUY-STRONG entry sized at 26% (80% of 32.5%)",
        "TP1 exits executed on 2 trailing positions"
    ],
    "portfolio_allocation": 0.72,
    "cash_reserve": 0.28,
    "alert": null
}
```

### 9.2 Alert Conditions

```
ALERT: Regime weakening (BULL → NEUTRAL)
├─ L2 below 0.60 for 2 consecutive days
├─ Action: Scale down to 80%, execute TP1 on new entries
└─ Notify: Orchestrator (informational)

ALERT: Regime deteriorating (NEUTRAL → BEAR)
├─ L2 below 0.45
├─ Action: Execute TP1+TP2, liquidate 80% of portfolio
└─ Notify: Orchestrator (urgent, defensive mode)

ALERT: Regime improving (BEAR → NEUTRAL)
├─ L2 above 0.50 for 2 days
├─ Action: Enable NEUTRAL regime (80% sizing)
└─ Notify: Orchestrator (opportunity to re-enter)
```

---

## 10. BUILDER REQUIREMENTS

### 10.1 Implementation Scope

- **Modify:** src/signals/signal_combination.py (return scaling_multiplier alongside composite_score)
- **New:** src/signals/macro_regime_gate.py (MacroRegimeGate class)
- **Modify:** src/risk/position_sizer_v2.py (accept macro_scaling_multiplier input)
- **Update:** Daily batch job (regime transition logging, alerts)

### 10.2 Testing Strategy

- **4 unit tests:** Scaling calculation, regime classification, transition hysteresis, exit logic
- **3 integration tests:** Gate + position sizer, forced exit execution, regime transitions
- **2 edge case tests:** Rapid regime flipping, position management during transition
- **Regression:** 539 baseline ±3% (scaling-based positioning acceptable variance)

### 10.3 Timeline

- **Timeline:** 1 week Phase 4.5 (concurrent with position sizer + conviction)
- **Blockers:** None (standalone module)
- **Builder Readiness:** YES

---

## 11. PHASED ROLLOUT

### Phase 4.5 (Go-Live)
```
Implement full scaling (BULL: 100%, NEUTRAL: 80%, BEAR: 0%)
All TPs execute per regime
Position limits enforced
```

### Phase 5+ (Enhancements)
```
Optional:
├─ Macro regime forecast (predict BULL/BEAR 5 days ahead)
├─ Regime confidence scoring (0.6 BULL vs 1.0 BULL)
└─ Dynamic scaling (continuous 0.0-1.0 vs discrete 0.8/1.0)
```

---

**Document:** SPEC_MACRO_REGIME_GATE_2.md  
**For:** Builder (Phase 4.5 Implementation)  
**Philosophy:** Regime-aware position scaling (aggressive → cautious → dormant)
