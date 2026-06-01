# SPEC_POSITION_SIZING_2: Conviction-Based Position Sizing Model (Ruthless Alpha)

**Version:** 2.0 (Ruthless Alpha Philosophy)  
**Date:** 16 May 2026  
**Target Role:** Builder  
**Scope:** BIST30, max 6 concurrent positions (4 BUY-STRONG + 2 BUY-MEDIUM), conviction-driven allocation  
**Philosophy:** Concentrated, aggressive alpha-seeking (replaces Kelly Criterion)  

---

## 1. POSITION SIZING FRAMEWORK

### 1.1 Core Model: Conviction × Macro Scaling

```
Position Size = Base Conviction Size × Macro Regime Scaling Factor × Conviction Score

Where:
- Base Conviction Size: Fixed allocation tier (BUY-STRONG, BUY-MEDIUM, BUY-WEAK)
- Macro Regime Scaling: Binary gate → continuous scaling (see SPEC_MACRO_REGIME_GATE_2)
- Conviction Score: [0, 1] from composite signal (see SPEC_SIGNAL_CONVICTION_1)
```

### 1.2 Conviction Tiers & Position Sizing

| Conviction Level | Composite Score | Portfolio Allocation | Position Type | Concurrent Limit | Action |
|---|---|---|---|---|---|
| **BUY-STRONG** | ≥0.68 | 30-35% per position | Active | Max 4 total | ENTER |
| **BUY-MEDIUM** | 0.55-0.67 | 15-20% per position | Active | Max 2 total | ENTER (reduced sizing) |
| **BUY-WEAK** | 0.45-0.54 | Watchlist (0% allocation) | Monitor | Unlimited | WATCH |
| **HOLD** | 0.35-0.44 | Hold existing (no scale) | Existing | — | HOLD |
| **SELL-SIGNAL** | <0.35 | EXIT staged TP | Exit | — | EXIT |

### 1.3 Sizing Algorithm

```python
def calculate_position_size(
    composite_signal_score: float,
    macro_regime_scaling: float,  # 0.0 - 1.0 (from SPEC_MACRO_REGIME_GATE_2)
    portfolio_equity: float,
    current_positions_count: int,
    strong_positions_count: int,
    medium_positions_count: int,
    existing_position_size: float = 0.0
) -> dict:
    """
    Calculate position size based on conviction + macro overlay.
    
    Args:
        composite_signal_score: [0, 1] from signal_combination.py
        macro_regime_scaling: 1.0 (bull), 0.8 (neutral), 0.0 (bear)
        portfolio_equity: Current portfolio value (e.g., $100K)
        current_positions_count: Total number of open positions (6 max)
        strong_positions_count: Number of BUY-STRONG positions currently held (4 max)
        medium_positions_count: Number of BUY-MEDIUM positions currently held (2 max)
        existing_position_size: If rebalancing, current size
    
    Returns:
        {
            "position_size_dollars": float,
            "conviction_tier": str,  # "BUY-STRONG", "BUY-MEDIUM", etc.
            "allocation_pct": float,
            "action": str,  # "ENTER", "WATCH", "HOLD", "EXIT"
            "macro_adjusted": float,  # Size after macro scaling
        }
    """
    
    # Step 1: Determine conviction tier
    if composite_signal_score >= 0.68:
        conviction_tier = "BUY-STRONG"
        base_allocation = 0.325  # 32.5% (mean of 30-35%)
    elif composite_signal_score >= 0.55:
        conviction_tier = "BUY-MEDIUM"
        base_allocation = 0.175  # 17.5% (mean of 15-20%)
    elif composite_signal_score >= 0.45:
        conviction_tier = "BUY-WEAK"
        base_allocation = 0.0  # Watchlist
    elif composite_signal_score >= 0.35:
        conviction_tier = "HOLD"
        base_allocation = existing_position_size / portfolio_equity if existing_position_size > 0 else 0.0
    else:
        conviction_tier = "SELL-SIGNAL"
        base_allocation = 0.0  # Initiate staged exit (see SPEC_STAGED_TP_1)
    
    # Step 2: Check position limits (max 4 BUY-STRONG, max 2 BUY-MEDIUM, max 6 total)
    # strong_positions_count and medium_positions_count passed as parameters
    
    if conviction_tier == "BUY-STRONG" and strong_positions_count >= 4:
        action = "WATCHLIST"  # At max BUY-STRONG limit
        allocation_pct = 0.0
        position_size = 0.0
    elif conviction_tier == "BUY-MEDIUM" and medium_positions_count >= 2:
        action = "WATCHLIST"  # At max BUY-MEDIUM limit
        allocation_pct = 0.0
        position_size = 0.0
    elif conviction_tier == "BUY-WEAK":
        action = "WATCH"
        allocation_pct = 0.0
        position_size = 0.0
    elif conviction_tier == "HOLD":
        action = "HOLD"
        allocation_pct = base_allocation
        position_size = base_allocation * portfolio_equity
    elif conviction_tier == "SELL-SIGNAL":
        action = "EXIT"
        allocation_pct = 0.0  # Trigger staged TP
        position_size = 0.0  # TP handles exit
    else:  # BUY-STRONG or BUY-MEDIUM
        action = "ENTER"
        # Macro scaling applied AFTER conviction sizing
        macro_adjusted_allocation = base_allocation * macro_regime_scaling
        allocation_pct = macro_adjusted_allocation
        position_size = macro_adjusted_allocation * portfolio_equity
    
    # Step 3: Return sizing decision
    return {
        "position_size_dollars": position_size,
        "conviction_tier": conviction_tier,
        "allocation_pct": allocation_pct,
        "macro_adjusted": position_size,  # After regime scaling
        "action": action,
        "regime_scaling_factor": macro_regime_scaling
    }
```

---

## 2. POSITION LIMITS & CONSTRAINTS

### 2.1 Portfolio Concentration Rules

```
Maximum 6 Concurrent Positions (4 BUY-STRONG + 2 BUY-MEDIUM):
├─ BUY-STRONG: Max 4 positions × 32.5% = 130%
├─ BUY-MEDIUM: Max 2 positions × 17.5% = 35%
├─ Combined max deployment: 165% (normalized to 100% via macro scaling + concurrent enforcement)
├─ Allocation per position: 
│  ├─ BUY-STRONG: 22.5-32.5% (after macro scaling)
│  └─ BUY-MEDIUM: 11.2-17.5% (after macro scaling)
└─ Cash reserve: 0-5% (opportunistic cash, not risk reserve)

Sector Concentration Limit (inherited from existing risk mgmt):
├─ No single sector > 40% (max 2 BIST30 financials if both meet BUY-STRONG)
├─ Diversification: Min 2 sectors across 4 positions
└─ Example: ASELS (Tech) 32.5% + GARAN (Finance) 32.5% + ARCLK (Consumer) 32.5% + SISE (Retail) 2.5%

Position Rebalancing:
├─ When macro regime changes (BULL → NEUTRAL): Scale down by 20%
├─ When macro regime changes (NEUTRAL → BEAR): Close all (staged TP) or hold for TP2/TP3
├─ No rebalancing on conviction score drift (only on new signal entry)
```

### 2.2 Entry Size Mechanics

**First Entry (New Position):**
```
Position Size = 32.5% × macro_scaling × portfolio_equity
Example: $100K portfolio, Bull regime (1.0), BUY-STRONG
         → 32.5% × 1.0 × $100K = $32.5K entry
```

**Scaling Rules (Do NOT scale in on conviction alone):**
```
NO additional entries if:
├─ Position already open > 20% (no pyramiding)
├─ Macro regime deteriorates (wait for re-entry after TP close)
├─ Max BUY-STRONG positions (4) already open OR max BUY-MEDIUM (2) already open for given tier
├─ Total positions at 6 concurrent max

YES scale into existing position ONLY if:
├─ New BUY-STRONG signal from different SECTOR (new composite peak)
├─ AND BUY-STRONG count <4 (available slot)
└─ AND macro regime strengthens (NEUTRAL → BULL)
```

---

## 3. POSITION EXITS & ROLLING FORWARD

### 3.1 Exit Hierarchy

**Tier 1: Staged TP (Primary)**
```
Exit via TP1, TP2, TP3 levels (see SPEC_STAGED_TP_1)
├─ TP1: 50% exit at first technical resistance
├─ TP2: 30% exit at second resistance (fib 0.618)
└─ TP3: 20% exit at trend breakout or all-time high
```

**Tier 2: Conviction Collapse (BUY-STRONG → SELL-SIGNAL)**
```
If composite score drops below 0.35:
├─ Initiate immediate TP1 (sell 50%)
├─ Hold TP2/TP3 for recovery window (24h)
└─ If score stays <0.35 for 2 days → force TP2+TP3 close
```

**Tier 3: Macro Gate Hard Stop (BULL → BEAR)**
```
If macro regime drops below 45 (BEAR):
├─ Close positions immediately (execute all TPs at market)
├─ No new entries until regime recovery
└─ Wait for NEUTRAL (45-60) + new BUY-STRONG signal
```

**Tier 4: Max Drawdown Hard Stop (Portfolio Risk)**
```
If portfolio drawdown > 15%:
├─ Pause all new entries
├─ Liquidate smallest position (by contribution)
├─ Resume when DD recovers to <10%
```

---

## 4. CASH MANAGEMENT & COMPOUNDING

### 4.1 Cash Allocation

```
Portfolio Composition:
├─ Active Positions: 95-100% (4 BUY-STRONG × 22.5-32.5% + 2 BUY-MEDIUM × 11.2-17.5%)
├─ Cash Reserve: 0-5% (tactical, not defensive)
└─ Total: 100%

Use of Cash:
├─ New BUY-STRONG entry (when <4 positions open)
├─ New BUY-MEDIUM entry (when <2 positions open)
├─ Scale existing position if macro strengthens
└─ NO cash dragging (all capital deployed unless at max positions)
```

### 4.2 Profit Reinvestment

```
When position exits via TP:
├─ TP1 exit (50% of position) → 50% reinvestment pool
├─ TP2 exit (30%) → 30% reinvestment pool
├─ TP3 exit (20%) → 20% reinvestment pool

Reinvestment Rules:
├─ IF BUY-STRONG signal exists for new stock → deploy immediately
├─ IF watchlist only → hold cash (max 2 days)
├─ IF macro regime weak → reinvest into trailing TP3 positions (compound gains)
```

---

## 5. INTEGRATION WITH EXISTING SYSTEM

### 5.1 Signal Input

**Source:** `signal_combination.py` composite score
```python
# Position sizer RECEIVES composite_score from signal_combination.py
# Do NOT recalculate here — consume as input only
composite_score  # Received from signal_combination.py [0, 1]

# Input to SPEC_POSITION_SIZING_2
conviction_tier = position_sizer.get_conviction_tier(composite_score)
position_size_usd = position_sizer.calculate_size(
    composite_score,
    macro_regime_scaling,  # From SPEC_MACRO_REGIME_GATE_2
    portfolio_equity,
    open_positions_count,
    strong_positions_count,  # Count of BUY-STRONG currently held
    medium_positions_count   # Count of BUY-MEDIUM currently held
)
```

### 5.2 Code Architecture

```python
# src/risk/position_sizer_v2.py (replaces conviction_scoring.py)

class PositionSizerV2:
    def __init__(self, max_positions: int = 6, max_strong: int = 4, max_medium: int = 2, base_allocation: float = 0.325):
        self.max_positions = max_positions
        self.max_strong = max_strong
        self.max_medium = max_medium
        self.base_allocation = base_allocation
    
    def get_conviction_tier(self, composite_score: float) -> str:
        """Map composite score to conviction tier."""
        if composite_score >= 0.68:
            return "BUY-STRONG"
        elif composite_score >= 0.55:
            return "BUY-MEDIUM"
        elif composite_score >= 0.45:
            return "BUY-WEAK"
        elif composite_score >= 0.35:
            return "HOLD"
        else:
            return "SELL-SIGNAL"
    
    def calculate_size(self,
                      composite_score: float,
                      macro_regime_scaling: float,
                      portfolio_equity: float,
                      current_positions_count: int,
                      strong_positions_count: int,
                      medium_positions_count: int) -> dict:
        """Main sizing calculation with tier-aware position limits."""
        # Implementation from Section 1.3
        pass
    
    def should_exit_position(self, 
                            composite_score: float,
                            position_age_days: int) -> bool:
        """Determine if position should trigger TP exit."""
        if composite_score < 0.35 and position_age_days > 1:
            return True  # Conviction collapse exit
        return False
```

---

## 6. BUILDER REQUIREMENTS

### 6.1 Dependencies

- **Input:** `signal_combination.py` composite score, macro regime scale (from SPEC_MACRO_REGIME_GATE_2)
- **Output:** Position size decision (dollars, tier, action) → sends to order placement engine
- **Integration Point:** `src/risk/position_sizer_v2.py` (standalone, no L1-L6 modifications)

### 6.2 Testing Strategy

- **5 unit tests:** Conviction tier mapping, size calculation, max position enforcement
- **3 integration tests:** With signal_combination.py, with macro gate, with existing position limits
- **2 edge case tests:** Drawdown hard stop, cash depletion scenarios
- **Regression:** 539 baseline tests ±3% variance (allows for more aggressive positioning)

### 6.3 Implementation Timeline

- **Timeline:** 2 weeks Phase 4.5 (after L5b VIOP complete)
- **Blockers:** None (independent of L1-L6)
- **Builder Readiness:** YES (clear algorithm, well-scoped)

---

**Document:** SPEC_POSITION_SIZING_2.md  
**For:** Builder (Phase 4.5 Implementation)  
**Philosophy:** Concentrated, conviction-driven, ruthless alpha pursuit
