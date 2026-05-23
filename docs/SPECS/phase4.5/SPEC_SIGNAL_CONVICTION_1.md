# SPEC_SIGNAL_CONVICTION_1: Conviction Threshold Calibration (Quality-Based)

**Version:** 1.0 (Ruthless Alpha Philosophy)  
**Date:** 16 May 2026  
**Target Role:** Builder  
**Scope:** Signal composite formula reweighting for quality-based high-conviction signals  
**Objective:** Generate high-conviction entry signals via mathematical thresholds (frequency emerges naturally)  

---

## 1. CONVICTION THRESHOLD PHILOSOPHY (Quality-Based, Not Frequency-Based)

### 1.1 Core Principle

```
Conviction threshold is MATHEMATICAL, not TARGET-BASED.

Question is NOT: "How many BUY-STRONG signals should we generate per month?"
Question IS: "What composite score represents genuine high conviction?"

Result: 
├─ Some months: 0 BUY-STRONG signals (market doesn't offer high conviction)
├─ Other months: 6+ BUY-STRONG signals (multiple high-conviction setups)
└─ System adapts to market conditions, not to frequency target

Quality > Quantity. Threshold ensures each signal is REAL high-conviction, not arbitrary.
```

### 1.2 Conviction Tier Definitions (Quality-Based)

```
BUY-STRONG (≥0.68): Genuine high conviction
├─ Multiple layers (L1, L2, L3) align to >0.65 each
├─ Macro context supportive (L2 > 0.50)
├─ Corporate action or momentum clear (L3 or L1 >0.70)
├─ Frequency: Whatever emerges naturally (0-10 per month acceptable)

BUY-MEDIUM (0.55-0.67): Moderate conviction, intermediate bet
├─ 2-3 layers support (e.g., L1 + L2, or L3 + L1)
├─ Macro neutral (0.45-0.60)
├─ Allows smaller position sizing (15-20% vs 30-35%)
├─ Frequency: Whatever emerges naturally

BUY-WEAK (0.45-0.54): Weak signal, watchlist only
├─ Single layer strong, others weak
├─ No position sizing
└─ Monitor for upgrade to BUY-MEDIUM or BUY-STRONG
```

### 1.3 NO Frequency Validation

```python
# REMOVED from conviction_validator.py
# The following frequency checks are NO LONGER NEEDED:
# - validate_conviction_frequency() — DELETE
# - frequency_pct tracking — DELETE
# - "OPTIMAL" / "OUT_OF_RANGE" alerts — DELETE
# - Monthly adjustment based on count — DELETE

# Instead: System generates signals when quality meets threshold.
# Accept that some months have 0, others have 5+.
```

---

## 2. CURRENT SIGNAL FORMULA ANALYSIS

### 2.1 Baseline Composite Formula (Phase 4.4)

```
composite_score = (
    l1_score * 0.18 +      # Tech/Momentum (quick signal)
    l2_score * 0.30 +      # Macro (regime confirmation)
    l3_score * 0.25 +      # KAP/Corporate (event-driven)
    l4_score * (0.12 * l4_confidence) +  # Sentiment (scaled by confidence)
    l5_score * (0.10 * l5_confidence) +  # Smart Money (pending)
    l6_score * 0.15        # Risk/Position Sizing (not signal)
) / normalizer

Range: [0, 1] (approximately)
Current BUY-STRONG threshold: ≥0.75
```

### 2.2 Signal Quality Calibration (Historical Analysis)

```
Baseline Analysis Period: Jan-May 2026 (120 trading days)
Previous Threshold (0.75):
├─ Signal count: 6 signals across 5 months (avg 1.2/month)
├─ Observation: This count reflects mathematical threshold, not frequency target
├─ Key finding: Multiple high-conviction signals (L1, L2, L3 layers aligned >0.65) were rare
├─ Reason: L2 macro (30% weight) acted as gatekeep → veto power too high

New Threshold (0.68) Rationale:
├─ Reduces L2 gatekeeping (20% weight instead of 30%)
├─ Increases L1/L3 agility (0.25 + 0.30 weights, event-responsive)
├─ Applies macro as modulation (confidence scaling) not hard veto
├─ Expected result: More frequent signal generation when market conditions align
└─ Signal frequency is outcome of quality threshold, not input target

Quality-Based Principle:
System generates signals when composite score genuinely represents high conviction.
Signal count adapts to market conditions: 0 signals in choppy markets, 5+ in strong trends.
This is CORRECT behavior, not failure to hit frequency target.
```

---

## 3. PROPOSED SIGNAL REWEIGHTING (OPTION A: Recommended)

### 3.1 Weight Adjustment Rationale

**Problem:** Macro layer (L2, 30% weight) is too gatekeeping.
- L2 requires strong regime confirmation → acts as hard veto for bullish signals
- When macro uncertain (0.45-0.60 score), all other layers muted
- Result: Fewer BUY-STRONG signals overall

**Solution:** Reduce L2 veto power, increase L1/L3 agility
- L1 (Tech): Faster signal generation (momentum-based, responds to 5-10 day moves)
- L3 (KAP): Event-driven (ownership changes, insider trades are discrete events)
- L2 (Macro): Modulate signal (scale conviction 0.8-1.2) instead of veto

**New Formula:**
```
composite_score = (
    l1_score * 0.25 +      # ↑ Tech from 0.18 → 0.25 (more responsive)
    l2_score * 0.20 +      # ↓ Macro from 0.30 → 0.20 (less gatekeeping)
    l3_score * 0.30 +      # ↑ KAP from 0.25 → 0.30 (events matter more)
    l4_score * (0.12 * l4_confidence) +  # Sentiment unchanged
    l5_score * (0.10 * l5_confidence) +  # Smart Money unchanged
    l6_score * 0.03        # ↓ Position Sizing from 0.15 → 0.03 (signal-only, not position size)
)

Then apply macro modulation (see Section 3.2)
```

**Weight Justification:**
- L1 (0.25): Tech signals are frequent, need representation
- L2 (0.20): Macro is context, not entry trigger
- L3 (0.30): KAP events are high-conviction, discrete
- L4 (0.12): Sentiment supplementary
- L5 (0.10): Smart Money supplementary (pending L5a VERDA)
- L6 (0.03): Removed as signal contributor (only affects position sizing downstream)

### 3.2 Macro Modulation Layer (Conviction Confidence Scaling)

```python
def apply_macro_modulation(base_composite_score: float, 
                          l2_macro_score: float,
                          macro_regime_scaling: float) -> float:
    """
    Macro modulation: L2 acts as confidence multiplier, not veto.
    
    Args:
        base_composite_score: Composite from reweighted formula
        l2_macro_score: Macro score [0, 1]
        macro_regime_scaling: Regime gate scaling [0.0, 1.0]
    
    Returns:
        conviction_adjusted_score: Final score after macro modulation
    """
    
    # Macro confidence multiplier
    if l2_macro_score >= 0.65:
        confidence_multiplier = 1.2  # Macro bullish, strengthen signal
    elif l2_macro_score >= 0.50:
        confidence_multiplier = 1.0  # Macro neutral, no change
    else:
        confidence_multiplier = 0.85  # Macro bearish, weaken signal slightly
    
    conviction_score = base_composite_score * confidence_multiplier
    
    # Cap at [0, 1] (overconfidence protection)
    conviction_score = min(1.0, conviction_score)
    
    return conviction_score
```

### 3.3 Conviction Thresholds (Quality-Based)

```
BUY-STRONG threshold: ≥0.68
├─ Definition: Score at or above this represents genuine high conviction
├─ Interpretation: Multiple signal layers + macro context align
├─ Position sizing: 30-35% (full conviction bet)
├─ Max concurrent: 4 positions

BUY-MEDIUM threshold: 0.55-0.67
├─ Definition: Moderate conviction, 2-3 layers support
├─ Position sizing: 15-20% (intermediate bet)
├─ Max concurrent: 2 positions
├─ Purpose: Capture setups with solid but not overwhelming conviction

These thresholds are FIXED (not monthly targets).
Signal frequency emerges naturally from market conditions.
```

---

## 4. ALTERNATIVE REWEIGHTING (OPTION B: More Conservative)

**If Option A produces too many false signals (backtest shows >50% loss rate):**

```
composite_score = (
    l1_score * 0.22 +
    l2_score * 0.25 +
    l3_score * 0.28 +
    l4_score * (0.12 * l4_confidence) +
    l5_score * (0.10 * l5_confidence) +
    l6_score * 0.03
)

BUY-STRONG threshold: ≥0.72
(more conservative: higher threshold, fewer but higher-quality signals)
```

---

## 5. CONVICTION SCORE DERIVATION (Post-Macro Modulation)

### 5.1 Conviction Tier Classification

```python
def classify_conviction_tier(conviction_score: float) -> str:
    """
    Map conviction score to tier (used by position sizer).
    
    Args:
        conviction_score: [0, 1] after macro modulation
    
    Returns:
        Tier: "BUY-STRONG", "BUY-MEDIUM", "BUY-WEAK", "HOLD", "SELL-SIGNAL"
    """
    
    if conviction_score >= 0.68:
        return "BUY-STRONG"
    elif conviction_score >= 0.55:
        return "BUY-MEDIUM"
    elif conviction_score >= 0.45:
        return "BUY-WEAK"
    elif conviction_score >= 0.35:
        return "HOLD"
    else:
        return "SELL-SIGNAL"
```

### 5.2 Conviction Score Output (Daily)

```
Daily Signal Output (per stock):
{
    "symbol": "ASELS",
    "date": "2026-05-16",
    "l1_score": 0.72,
    "l2_score": 0.58,
    "l3_score": 0.85,
    "l4_score": 0.65,
    "l5_score": 0.70,
    "base_composite": 0.712,          # Reweighted formula
    "macro_multiplier": 0.95,          # L2 < 0.65, slight bearish adjustment
    "conviction_score": 0.676,         # Base × multiplier
    "conviction_tier": "BUY-STRONG",
    "confidence": 0.75,                # Based on L4, L5 confidence
    "suggested_position_size": "32.5%"  # From SPEC_POSITION_SIZING_2
}
```

---

## 6. IMPLEMENTATION ARCHITECTURE

### 6.1 Code Changes

```python
# src/signals/signal_combination.py (MODIFIED)

def calculate_composite_signal(l1, l2, l3, l4, l5, l6, 
                              l4_confidence, l5_confidence) -> dict:
    """Calculate reweighted composite signal with macro modulation."""
    
    # Step 1: Reweighted base composite (OPTION A: recommended)
    normalizer = 0.78  # Sum of active weights (L1+L2+L3+L4+L5+L6 base: 0.25+0.20+0.30+0.12+0.10+0.03)
    base_composite = (
        l1 * 0.25 +
        l2 * 0.20 +
        l3 * 0.30 +
        l4 * (0.12 * l4_confidence) +
        l5 * (0.10 * l5_confidence) +
        l6 * 0.03
    ) / normalizer
    
    # Step 2: Apply macro modulation
    if l2 >= 0.65:
        macro_multiplier = 1.2
    elif l2 >= 0.50:
        macro_multiplier = 1.0
    else:
        macro_multiplier = 0.85
    
    conviction_score = min(1.0, base_composite * macro_multiplier)
    
    # Step 3: Classify tier
    if conviction_score >= 0.68:
        conviction_tier = "BUY-STRONG"
    elif conviction_score >= 0.60:
        conviction_tier = "BUY-MEDIUM"
    elif conviction_score >= 0.45:
        conviction_tier = "BUY-WEAK"
    elif conviction_score >= 0.35:
        conviction_tier = "HOLD"
    else:
        conviction_tier = "SELL-SIGNAL"
    
    return {
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "l4": l4,
        "l5": l5,
        "l6": l6,
        "base_composite": base_composite,
        "conviction_score": conviction_score,
        "conviction_tier": conviction_tier,
        "macro_multiplier": macro_multiplier
    }
```

### 6.2 Integration Points

- **Upstream:** L1-L6 signal layers (unchanged)
- **Downstream:** position_sizer_v2.py (consumes conviction_tier + conviction_score)
- **Validation:** Daily check on BUY-STRONG frequency (see Section 1.2)

---

## 7. BACKTESTING & VALIDATION

### 7.1 Backtest Requirements

```
Period: Jan 2024 - May 2026 (29 months)
Stocks: BIST30 (30 stocks)
Metrics:
├─ Win rate: % of BUY-STRONG signals with +5% gain within 5 days
├─ Win rate (BUY-MEDIUM): % with +3% gain within 5 days
├─ Sharpe ratio: Unchanged or improved (>0.81)
├─ Max drawdown: ≤15% (Ruthless Alpha tolerance)
└─ 539 regression tests: ±3% variance

Acceptance Criteria:
├─ BUY-STRONG win rate ≥55% (better than random)
├─ BUY-MEDIUM win rate ≥50% (lower bar, intermediate positioning)
└─ Sharpe ≥0.81 (baseline maintained)

NO frequency target — signal count is outcome, not input.
```

### 7.2 NO Daily Frequency Validation

```python
# REMOVE from daily batch job:
# - signal_validator.check_frequency()
# - frequency alerts
# - adjustment logic based on monthly count

# System operates on quality thresholds only.
# Accept that frequency varies by market conditions.
```

---

## 8. MONITORING & TUNING

### 8.1 Feedback Loop (Quality-Based Tuning)

```
If signal quality degrades (win rate <55%):
├─ Raise threshold by 0.02 (e.g., 0.68 → 0.70)
├─ Increase L1/L2/L3 layer requirement (all must >0.65, not just majority)
├─ Review L1-L6 layer calibration (check for signal drift)
└─ Adjust monthly or quarterly (not daily to avoid whipsaw)

If signal quality strengthens (win rate >65%):
├─ Maintain current threshold (0.68 is mathematically sound)
├─ Do NOT lower to chase frequency — resist frequency pressure
└─ Use confidence level (Section 5.2) to filter false positives
```

### 8.2 Granular Tracking

```
Daily signal.json output:
{
    "date": "2026-05-16",
    "all_symbols": [
        {"symbol": "ASELS", "conviction_score": 0.76, "tier": "BUY-STRONG", ...},
        {"symbol": "GARAN", "conviction_score": 0.55, "tier": "BUY-WEAK", ...},
        ...
    ],
    "stats": {
        "buy_strong_count": 1,
        "buy_medium_count": 3,
        "buy_weak_count": 5,
        "hold_count": 12,
        "sell_signal_count": 9,
        "quality_check": {
            "win_rate_30d": 0.62,      # For feedback loop monitoring
            "avg_conviction_score": 0.68,
            "confidence_level": 0.78
        }
    }
}
```

---

## 9. BUILDER REQUIREMENTS

### 9.1 Code Changes Summary

- **Modify:** `src/signals/signal_combination.py` (reweighting + macro modulation)
- **Add:** `src/signals/conviction_validator.py` (frequency tracking)
- **Update:** Daily batch job to validate frequency

### 9.2 Testing Strategy

- **3 unit tests:** Macro modulation formula, tier classification, quality score mapping
- **2 integration tests:** Reweighted formula with L1-L6 inputs, tier propagation to position sizer
- **Regression:** 539 baseline ±3% variance, quality score consistency

### 9.3 Timeline

- **Timeline:** 1 week Phase 4.5 (concurrent with position sizer)
- **Blockers:** None
- **Builder Readiness:** YES (clear formulas, well-scoped)

---

## 10. THRESHOLD DECISION

**Approved:** OPTION A (aggressive reweighting) + BUY-MEDIUM active tier

**Thresholds (FIXED, not frequency-based):**
- BUY-STRONG: ≥0.68 (30-35% position sizing, max 4)
- BUY-MEDIUM: 0.55-0.67 (15-20% position sizing, max 2) — **NEW ACTIVE TIER**
- BUY-WEAK: 0.45-0.54 (watchlist only)

**Rationale:**
- 0.68 threshold represents genuine high conviction (not arbitrary frequency target)
- 0.55 threshold enables intermediate conviction bets (captures good setups below high-conviction bar)
- Reweighting (L1: 0.25, L2: 0.20, L3: 0.30) produces quality-based signals
- Max 6 positions (4 BUY-STRONG + 2 BUY-MEDIUM) balances aggression with discipline
- Signal frequency emerges naturally — may be 0/month or 6+/month (acceptable)

**Validation:** Win rate ≥55% (BUY-STRONG), ≥50% (BUY-MEDIUM), Sharpe ≥0.81.

---

**Document:** SPEC_SIGNAL_CONVICTION_1.md  
**For:** Builder (Phase 4.5 Implementation)  
**Philosophy:** Quality-driven conviction thresholds (frequency emerges naturally from market conditions)
