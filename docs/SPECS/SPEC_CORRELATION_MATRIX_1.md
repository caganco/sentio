# SPEC: Correlation Matrix (Risk Management & Position Sizing)

**Title:** Stock Correlation Matrix for Portfolio Risk Management  
**Version:** 1.0  
**Date:** 16 May 2026  
**Author:** Architect  
**Status:** 🟡 READY FOR D-031 REVIEW  
**Affected Files:**
- `src/risk/correlation_matrix.py` (NEW)
- `src/risk/kelly_criterion.py` (modified to consume correlations)
- `config.yaml` (correlation_matrix section)
- `tests/test_correlation_*.py` (NEW, ~8 tests)

---

## EXECUTIVE SUMMARY

**Correlation Matrix** calculates rolling stock-to-stock price correlations (60-day window) from BIST 100 historical OHLCV data. It serves **two primary purposes:**

1. **Position Sizing Adjustment (Functional):** Reduces Kelly Criterion position sizes when stocks are highly correlated, preventing concentration risk
2. **Risk Reporting (Informational):** Daily heatmap showing sector/stock clusters for transparency and risk monitoring

**Architecture:** Independent module (doesn't modify signal layers), sits between portfolio scoring and L6 position sizing, feeds correlation data into Kelly adjustment logic.

**Integration Model:** 
- **Primary flow:** Portfolio Score → L6 (Kelly) → [Check correlations] → Adjusted position sizes
- **Secondary flow:** Report generator → [Correlation heatmap] → Daily portfolio report

**Timeline:** 2-3 weeks (Phase 4.3, mid-June 2026, after L4 Sentiment complete)

---

## 1. CONTEXT & MOTIVATION

### 1.1 Why Correlation Matrix?

**Problem:** Kelly Criterion position sizing assumes **independence** between positions:

```
Kelly Formula: f* = (p - q/odds) / odds
Assumption: Each position's win/loss independent of others
Reality in BIST 100: Stocks move together in clusters
```

**Example of the Problem:**

```
Scenario: Macro shock (CDS widens, USD/TRY spikes)
├─ Financial sector (GARAN, AKBANK, ISBANK) → all down -5%
├─ Kelly sizes them independently:
│  ├─ GARAN: 5% (high signal)
│  ├─ AKBANK: 4% (medium signal)
│  └─ ISBANK: 3% (lower signal)
│  └─ Total financial exposure: 12% (concentrated!)
│
└─ Portfolio impact: -60bp on 12% exposure = -7.2% portfolio loss
   (worse than Kelly formula predicted, because correlation not accounted for)
```

**Current Gap:**
- ✅ L1-L5 signals working (high quality)
- ✅ Kelly Criterion formula correct (position sizing per signal)
- ❌ **Missing:** Correlation adjustment for concentrated sectors
- ❌ **Missing:** Visibility into portfolio correlation risk

**Solution:** Correlation Matrix + Kelly adjustment logic

---

### 1.2 Why Not Modify Kelly Directly?

**Constraint:** DEC-006 specifies Kelly Criterion implementation independently. Correlation Matrix is **complementary**, not integrated.

**Why separate?**
1. **Modularity:** Kelly is pure position sizing (signal → size). Correlation is risk adjustment (size × risk_factor).
2. **Testability:** Each can be tested independently
3. **Flexibility:** Can enable/disable correlation adjustment without changing Kelly formula
4. **Future-proof:** If we add other risk adjustments (VIX hedge, sector limits), correlation is one input among many

**Model:**
```
Kelly Criterion Output: [position_sizes] = {GARAN: 5%, AKBANK: 4%, ISBANK: 3%}
                              ↓
                    Correlation Risk Check
                    ├─ Compute: correlation(GARAN, AKBANK) = 0.85
                    ├─ Compute: correlation(GARAN, ISBANK) = 0.80
                    ├─ Decision: Reduce correlated positions
                    └─ Adjusted output: {GARAN: 5%, AKBANK: 2.5%, ISBANK: 1.5%}
                              ↓
                    Final Position Sizes → Execute
```

This is a **second-order adjustment**, not an override of Kelly formula.

---

## 2. SPECIFICATION

### 2.1 Purpose & Scope

**Primary Purpose: Position Sizing Adjustment**
- Input: Kelly-sized positions + correlation matrix
- Output: Correlation-adjusted position sizes (cap concentrated exposure)
- Mechanism: Reduce position size if correlated with existing portfolio
- Implementation: Hard limit on sector concentration (e.g., financial ≤15% total)

**Secondary Purpose: Risk Reporting & Transparency**
- Input: Correlation matrix (daily rolling)
- Output: Daily heatmap in portfolio report
- Mechanism: Visualization of which stocks/sectors move together
- Implementation: Compact JSON heatmap (top 10 correlations)

**Scope:**
- ✅ BIST 100 stocks only (100 × 100 correlation matrix)
- ✅ Daily rolling 60-day window (updated EOD)
- ✅ Price-based correlations (OHLCV data only)
- ❌ NOT including: sector-to-sector correlations (future)
- ❌ NOT modifying: L1-L6 signal layers
- ❌ NOT replacing: Kelly formula (complementary only)

---

### 2.2 Data Specification

#### Input Data
```
Price History (60-day rolling window):
├─ Stock: BIST 100 (100 stocks)
├─ Data points: Daily OHLCV (5 data points × 100 stocks × 60 days = 30K data points)
├─ Calculation basis: Closing prices or log returns
├─ Source: BIST market data (same as L1 Tech layer)
├─ Frequency: Updated daily EOD
├─ Storage: PostgreSQL rolling window + in-memory cache
└─ Cost: Minimal (same data already fetched for L1)
```

#### Output Data
```
Correlation Matrix (100 × 100):
├─ Format: Dense symmetric matrix (100 × 100 values)
├─ Values: Pearson correlation coefficients (-1 to +1)
├─ Interpretation:
│  ├─ +0.8-1.0: Highly correlated (move together)
│  ├─ +0.5-0.8: Moderately correlated
│  ├─ 0-0.5: Weakly correlated
│  ├─ -0.5-0: Negatively correlated
│  └─ -0.8-1.0: Highly negatively correlated (hedges)
│
├─ Update frequency: Daily EOD (not real-time)
├─ Storage: PostgreSQL + Redis cache (24h)
└─ Size: ~40 KB (100 × 100 × 4 bytes float32)
```

#### Example Output (Top 10 Correlations for GARAN)
```json
{
  "GARAN": {
    "date": "2026-05-16",
    "confidence": "medium",
    "top_correlations": [
      {"symbol": "AKBANK", "correlation": 0.85, "sector": "Finance"},
      {"symbol": "ISBANK", "correlation": 0.81, "sector": "Finance"},
      {"symbol": "KREDIBIL", "correlation": 0.78, "sector": "Finance"},
      {"symbol": "SISE", "correlation": 0.42, "sector": "Cons. Goods"},
      {"symbol": "ASUAI", "correlation": 0.38, "sector": "Insurance"},
    ],
    "sector_exposure": {
      "Finance": 0.85,
      "Insurance": 0.38,
      "Energy": -0.12
    }
  }
}
```

---

### 2.3 Architecture & Integration

#### Module Structure
```
src/risk/
├─ correlation_matrix.py (NEW)
│  ├─ class CorrelationMatrix:
│  │  ├─ __init__(window_days=60, min_samples=50)
│  │  ├─ calculate(price_data: OHLCV) → correlation_matrix
│  │  ├─ get_correlation(stock_a, stock_b) → float
│  │  ├─ get_sector_exposure(stock) → dict
│  │  ├─ identify_clusters(threshold=0.75) → [[stocks]]
│  │  └─ cache_management(ttl=24h)
│  │
│  └─ CorrelationCache (Redis wrapper)
│     ├─ store(date, matrix, ttl)
│     ├─ retrieve(date)
│     └─ invalidate_on_new_data()
│
└─ kelly_criterion.py (MODIFIED)
   ├─ class KellyCriterion:
   │  ├─ __init__(correlation_matrix=None)  # NEW parameter
   │  ├─ calculate_position_size(...) → base_size
   │  ├─ adjust_for_correlation(base_size, stock, portfolio) → adjusted_size  # NEW method
   │  └─ apply_sector_limits(positions, max_sector_weight=0.15) → capped_positions  # NEW method
```

#### Data Flow (EOD)
```
1. Fetch 60-day price history (OHLCV)
   └─> CorrelationMatrix.calculate() → raw_matrix (100×100)

2. Cache correlation matrix
   └─> CorrelationCache.store(date, matrix, ttl=24h)

3. Apply to Kelly positions
   ├─ Step A: Get Kelly sizes [5%, 4%, 3%, ...] per signal
   ├─ Step B: For each position:
   │  ├─ Check: which positions already held?
   │  ├─ Compute: correlation(new_stock, portfolio)
   │  ├─ Decision: reduce position if corr > threshold?
   │  └─ Output: adjusted_size
   ├─ Step C: Apply sector limits
   │  ├─ Sum: positions by sector
   │  ├─ Cap: any sector >15% max
   │  └─ Output: final_positions
   └─> Position sizer complete

4. Generate report
   └─> Include top correlations + sector exposure heatmap
```

---

### 2.4 Correlation Adjustment Logic

#### Algorithm: Correlation-Aware Position Sizing

```
Input:
  ├─ kelly_positions = {GARAN: 5%, AKBANK: 4%, ISBANK: 3%}
  ├─ correlation_matrix = computed above
  ├─ existing_portfolio = {GARAN: 4%, AKBANK: 2%, ...}
  └─ sector_limits = {Finance: 15% max, Energy: 12% max, ...}

Algorithm (Adjusted Kelly):
  adjusted_positions = {}
  
  for stock, kelly_size in kelly_positions:
    # Step 1: Check correlation with existing portfolio
    portfolio_avg_correlation = mean([
      correlation(stock, held_stock) 
      for held_stock in existing_portfolio
    ])
    
    # Step 2: Compute correlation penalty
    correlation_factor = (1.0 - portfolio_avg_correlation)
    # If correlation = 0.0 (uncorrelated), factor = 1.0 (no reduction)
    # If correlation = 0.5, factor = 0.5 (50% reduction)
    # If correlation = 1.0 (perfectly correlated), factor = 0.0 (skip)
    
    # Step 3: Apply penalty
    adjusted_size = kelly_size * correlation_factor
    
    # Step 4: Apply hard minimum (avoid micro-positions)
    adjusted_size = max(adjusted_size, 0.5%)  # minimum 0.5%
    
    adjusted_positions[stock] = adjusted_size
  
  # Step 5: Apply sector limits
  adjusted_positions = apply_sector_limits(adjusted_positions, limits=0.15)
  
  return adjusted_positions
```

#### Example Calculation

```
Scenario: GARAN Kelly = 5%, existing portfolio has AKBANK 2%

Step 1: Correlation check
  correlation(GARAN, AKBANK) = 0.85
  portfolio_avg_correlation = 0.85

Step 2-3: Apply penalty
  correlation_factor = 1.0 - 0.85 = 0.15
  adjusted_size = 5% × 0.15 = 0.75%

Step 4: Check minimum
  adjusted_size = max(0.75%, 0.5%) = 0.75% ✓

Result: GARAN position capped at 0.75% (down from 5% Kelly)
  Rationale: High correlation with existing AKBANK holding
```

---

### 2.5 Sector Concentration Limits

**Definition:** Hard cap on portfolio exposure per sector

```
Sector Limits (Configurable):
├─ Financial (GARAN, AKBANK, ISBANK, KREDIBIL, SISE_Finance): 15% max
├─ Energy (TUPRS, KRDMD, PETRO): 12% max
├─ Industrials (ASELES, ARCELIK, ASUAI): 12% max
├─ Retail/Consumer (GOZDE, GARAN_Retail): 10% max
├─ Technology (ASELS, KASTL): 10% max
├─ Other: 8% max
└─ Total: 100% (by definition)

Enforcement:
  if sector_exposure > limit:
    ├─ Scale all positions in sector by (limit / current_exposure)
    ├─ Example: Finance at 18%, limit 15%
    │  └─ Scale factor = 15% / 18% = 0.833
    │  └─ All finance stocks × 0.833 (proportional reduction)
    └─ Move excess to cash or diversify into other sectors
```

---

### 2.6 Confidence & Stability

#### Rolling Window Stability
```
Correlation stability (60-day rolling):
├─ Day 1-20: Building up data (confidence LOW)
│  └─ Use historical correlation from archive as prior
├─ Day 21-50: Medium confidence (30-50 samples)
├─ Day 50+: High confidence (50+ samples)
└─ Update: Add new day, drop oldest day (rolling)

Quality metric:
  confidence = min(sample_count / 50, 1.0)
  # If <50 days data, scale confidence down
  # Example: 30 days → confidence 0.6 → weight adjustment reduced
```

#### Seasonal Adjustments
```
Correlation changes over time (market regimes):
├─ Bull market: correlations lower (stocks diverge)
├─ Crisis: correlations spike (all stocks fall together)
├─ Transition: correlations unstable

Handling:
  monitor_correlation_stability() → if coefficient_of_variation > 0.3:
    alert("Correlation regime shift detected, reduce position sizes")
    # Be more conservative on position adjustments
```

---

## 3. IMPLEMENTATION ARCHITECTURE

### 3.1 Code Structure

#### Part 1: Core Correlation Calculation
```python
# src/risk/correlation_matrix.py

class CorrelationMatrix:
    def __init__(self, window_days=60, min_samples=50):
        self.window = window_days
        self.min_samples = min_samples
        self.cache = CorrelationCache()
    
    def calculate(self, price_data_df):
        """
        Args:
            price_data_df: DataFrame with columns [stock, date, close, volume]
                          (100 stocks, 60 days = 6000 rows)
        
        Returns:
            corr_matrix: 100×100 correlation matrix
            confidence: dict of {stock: confidence_score}
        """
        # Step 1: Pivot to wide format (dates × stocks)
        pivot = price_data_df.pivot(index='date', columns='stock', values='close')
        
        # Step 2: Compute log returns (avoid spurious correlation from trend)
        log_returns = np.log(pivot / pivot.shift(1)).dropna()
        
        # Step 3: Calculate Pearson correlation
        corr_matrix = log_returns.corr()  # 100×100
        
        # Step 4: Compute confidence (sample count / min_samples)
        confidence = {
            stock: min(len(log_returns) / self.min_samples, 1.0)
            for stock in log_returns.columns
        }
        
        # Step 5: Cache result
        self.cache.store(date=price_data_df['date'].max(), 
                        matrix=corr_matrix, confidence=confidence)
        
        return corr_matrix, confidence
    
    def get_sector_exposure(self, stock, sector_map):
        """Return mean correlation of stock to its sector."""
        sector_stocks = sector_map[stock]
        correlations = [self.get_correlation(stock, s) for s in sector_stocks]
        return np.mean(correlations)
    
    def identify_clusters(self, threshold=0.75):
        """Find stocks that move together (correlation > threshold)."""
        clusters = []
        visited = set()
        
        for stock in self.stocks:
            if stock in visited:
                continue
            cluster = {stock}
            for other in self.stocks:
                if self.get_correlation(stock, other) > threshold:
                    cluster.add(other)
                    visited.add(other)
            clusters.append(cluster)
        
        return clusters
```

#### Part 2: Kelly Adjustment
```python
# src/risk/kelly_criterion.py

class KellyCriterion:
    def __init__(self, correlation_matrix=None):
        self.corr = correlation_matrix  # Optional
        self.sector_limits = config.sector_limits  # From config.yaml
    
    def adjust_for_correlation(self, kelly_position, stock, current_portfolio):
        """
        Reduce position size if highly correlated with existing holdings.
        
        Args:
            kelly_position: Kelly-sized position (%)
            stock: stock symbol
            current_portfolio: dict of {stock: current_size}
        
        Returns:
            adjusted_position: correlation-adjusted size (%)
        """
        if self.corr is None or len(current_portfolio) == 0:
            return kelly_position  # No adjustment if no correlation data
        
        # Compute average correlation to portfolio
        held_stocks = list(current_portfolio.keys())
        avg_correlation = np.mean([
            self.corr.get_correlation(stock, held) 
            for held in held_stocks
        ])
        
        # Correlation penalty: (1 - correlation)
        penalty = 1.0 - avg_correlation
        adjusted = kelly_position * penalty
        
        # Hard minimum
        adjusted = max(adjusted, 0.005)  # 0.5% minimum
        
        return adjusted
    
    def apply_sector_limits(self, positions):
        """
        Cap sector exposures to limits.
        
        Args:
            positions: dict of {stock: position_size}
        
        Returns:
            capped_positions: dict with sector limits applied
        """
        sector_exposure = defaultdict(float)
        
        # Sum by sector
        for stock, size in positions.items():
            sector = self.sector_map[stock]
            sector_exposure[sector] += size
        
        # Apply caps
        scaling_factors = {}
        for sector, exposure in sector_exposure.items():
            limit = self.sector_limits[sector]
            if exposure > limit:
                scaling_factors[sector] = limit / exposure
            else:
                scaling_factors[sector] = 1.0
        
        # Scale positions
        capped = {}
        for stock, size in positions.items():
            sector = self.sector_map[stock]
            capped[stock] = size * scaling_factors[sector]
        
        return capped
```

---

### 3.2 Testing Strategy (8 tests)

```
Unit Tests (4):
├─ test_correlation_calculation_matches_numpy
│  ├─ Input: 60 days × 100 stocks price data
│  ├─ Expected: Pearson correlation matrix matches numpy.corrcoef()
│  └─ Assertion: correlation ≤ 0.001 difference tolerance

├─ test_correlation_adjustment_reduces_correlated_positions
│  ├─ Input: kelly_size=5%, avg_correlation=0.8 to portfolio
│  ├─ Expected: adjusted = 5% × (1 - 0.8) = 1%
│  └─ Assertion: adjusted_size == expected_size

├─ test_sector_limits_cap_over_weight
│  ├─ Input: Finance sector at 18%, limit 15%
│  ├─ Expected: all finance stocks scaled by 15/18 = 0.833
│  └─ Assertion: sector total ≤ limit

└─ test_confidence_calculation_based_on_sample_count
   ├─ Input: 30 days data, min_samples = 50
   ├─ Expected: confidence = 30/50 = 0.6
   └─ Assertion: confidence matches formula

Integration Tests (4):
├─ test_correlation_matrix_feeds_into_kelly
│  ├─ Scenario: Kelly generates sizes, correlation matrix adjusts
│  ├─ Expected: Final sizes <√ Kelly sizes (due to correlation penalty)
│  └─ Assertion: adjusted sizes reasonable (0.5%-5%)

├─ test_sector_limits_integrated_with_kelly
│  ├─ Scenario: Kelly + correlation + sector limits all applied
│  ├─ Expected: Positions respect sector caps
│  └─ Assertion: no sector >15%

├─ test_correlation_cache_hit_retrieves_correct_matrix
│  ├─ Input: Store correlation matrix in Redis
│  ├─ Expected: Retrieve same matrix
│  └─ Assertion: cached matrix == stored matrix

└─ test_no_regression_in_existing_position_sizing
   ├─ Input: Run with correlation adjustment disabled
   ├─ Expected: positions match previous Kelly-only sizing
   └─ Assertion: <1% difference (accounting for rounding)
```

---

## 4. CONFIGURATION

```yaml
# config.yaml

correlation_matrix:
  enabled: true
  window_days: 60
  min_samples: 50
  update_frequency: "daily_eod"
  cache_ttl_hours: 24
  
  # Correlation adjustment
  adjustment:
    enabled: true
    method: "linear_penalty"  # (1 - correlation)
    min_position_size: 0.005  # 0.5% hard minimum
  
  # Sector limits
  sector_limits:
    Financial: 0.15
    Energy: 0.12
    Industrials: 0.12
    Retail_Consumer: 0.10
    Technology: 0.10
    Healthcare: 0.08
    Utilities: 0.08
    Real_Estate: 0.08
    Other: 0.08
  
  # Sector mapping
  sector_map:
    GARAN: "Financial"
    AKBANK: "Financial"
    ISBANK: "Financial"
    TUPRS: "Energy"
    # ... 100 stocks total

  # Monitoring
  monitoring:
    alert_on_regime_shift: true  # If correlation variation > 0.3
    alert_on_sector_concentration: true  # If >14% (below limit)
    log_adjustment_factors: true
```

---

## 5. RISKS & MITIGATIONS

### Risk 1: Over-Adjustment (Positions Too Small)
**Severity:** 🟡 MEDIUM

| Risk | Mitigation |
|---|---|
| Correlation penalty too aggressive | Hard minimum 0.5%, monitor actual vs Kelly sizes |
| Sector limits cap too low | Start at 15%, adjust up if no concentration issues |
| Interaction with Kelly | Test Kelly + correlation separately, then together |

### Risk 2: Stale Correlation Data
**Severity:** 🟡 MEDIUM

| Risk | Mitigation |
|---|---|
| 60-day window misses regime change | Monitor correlation coefficient of variation |
| Cache expires, fallback fails | Use archive as backup (historical correlation) |
| Weekend/holiday gaps in data | Handle in rolling window calculation |

### Risk 3: Integration with Existing L6
**Severity:** 🟡 MEDIUM

| Risk | Mitigation |
|---|---|
| Correlation adjustment conflicts with Kelly | Correlation is optional adjustment, not required |
| Regression in position sizing | Run 539 baseline tests with correlation disabled |
| Sector map maintenance | Document in config.yaml, update when BIST 100 changes |

### Risk 4: Computational Cost
**Severity:** 🟢 LOW

| Risk | Mitigation |
|---|---|
| 100×100 correlation calculation slow | O(n²) = 10K operations, <100ms on modern CPU |
| Daily cache invalidation | Batch calculate once per day (EOD) |
| Memory for matrix storage | 40 KB per matrix, negligible |

---

## 6. IMPLEMENTATION TIMELINE

**Phase 4.3 (Parallel with L4 Sentiment, or immediately after)**

```
Week 1 (June 9-13):
├─ Day 1-2: CorrelationMatrix class + calculate() method
├─ Day 3-4: Caching layer (Redis)
└─ Day 5: Unit tests (4 tests)

Week 2 (June 16-20):
├─ Day 1-2: Kelly adjustment logic
├─ Day 3-4: Sector limits enforcement
└─ Day 5: Integration tests (4 tests)

Week 3 (June 23-27):
├─ Day 1: Performance benchmarking
├─ Day 2: Regression tests (539 baseline)
├─ Day 3: Backtest validation (does correlation improve Sharpe?)
└─ Day 4-5: Documentation + go-live prep
```

---

## 7. DECISION: IMPLEMENTATION READINESS

**Status:** ✅ **YES — READY FOR IMPLEMENTATION (Phase 4.3)**

**Conditions:**

| Criterion | Status | Notes |
|---|---|---|
| Purpose clear | ✅ YES | Position sizing adjustment + risk reporting |
| Architecture mapped | ✅ YES | Sits in L6 decision layer, doesn't modify L1-L5 |
| Data source available | ✅ YES | OHLCV already fetched for L1 |
| Implementation path clear | ✅ YES | Modular structure, testable components |
| Integration with Kelly non-conflicting | ✅ YES | Optional adjustment, can be disabled |
| Configuration ready | ✅ YES | config.yaml template provided |
| Testing strategy | ✅ YES | 8 tests (unit + integration) |
| Risk mitigations | ✅ YES | 4 risks with mitigations documented |
| **READY FOR IMPLEMENTATION?** | **YES** | **Proceed after L4 (Phase 4.3, mid-June)** |

**Handoff Checklist for arastirma katmani:**

```
BEFORE starting:
☐ Review SPEC_CORRELATION_MATRIX_1.md
☐ Understand Kelly Criterion (DEC-006) design
☐ Confirm sector mapping with Strategist

Phase 4.3 Week 1:
☐ CorrelationMatrix.calculate() working + unit tests passing
☐ Cache layer functional
☐ Latency <100ms for 100×100 matrix (measure & document)

Phase 4.3 Week 2:
☐ Kelly adjustment logic working
☐ Sector limits capping correctly
☐ Integration tests passing (4/4)
☐ Regression test: 539 baseline tests <2% variance

Phase 4.3 Week 3:
☐ Backtest: Does correlation adjustment improve Sharpe?
  ├─ Target: Sharpe ≥0.84 (same as without correlation)
  └─ If lower: investigate adjustment logic or disable
☐ Performance: Correlation calculation <100ms
☐ Documentation complete
☐ Ready for production (no live trading yet, staging only)
```

---

## 8. FUTURE ENHANCEMENTS (Phase 5+)

- [ ] Sector-to-sector correlation matrix (correlate entire sectors, not just stocks)
- [ ] Factor-based correlations (correlation to macro factors: USD/TRY, VIX, oil)
- [ ] Conditional correlation (correlation changes by market regime)
- [ ] Copula-based risk (non-normal tail dependence)
- [ ] Machine learning: predict correlation changes before they happen
- [ ] Active hedging: automatically find uncorrelated pairs for hedge trades

---

**Spec Status:** ✅ READY FOR REVIEW  
**Date:** 16 May 2026  
**Next:** D-031 Architect Review (same session)
