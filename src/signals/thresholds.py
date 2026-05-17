"""All threshold constants for the Signal Engine. No magic numbers elsewhere."""

MASTER_WEIGHTS: dict[str, float] = {
    "technical": round(0.20 / 1.00, 10),   # 0.2000 (unchanged)
    "macro":     round(0.35 / 1.00, 10),   # 0.3500 (unchanged)
    "kap":       round(0.15 / 1.00, 10),   # 0.1500 (unchanged)
    "risk":      round(0.05 / 1.00, 10),   # 0.0500 (unchanged)
    "smart_money": round(0.25 / 1.00, 10), # 0.2500 (was 0.20, +0.05 from sentiment)
    "sentiment": round(0.00 / 1.00, 10),   # 0.0000 (deactivated, awaiting DistilBERT Phase 4.2.1)
}

SIGNAL_THRESHOLDS: dict[str, float] = {
    "buy_strong":  72.0,
    "buy_weak":    60.0,
    "hold_upper":  60.0,
    "hold_lower":  48.0,
    "sell_weak":   32.0,
    # sell_strong: < sell_weak
}

CONFLICT_THRESHOLD: float = 40.0

RISK_OFF_CONDITIONS: dict[str, float] = {
    "vix_threshold":      30.0,
    "usdtry_1d_change":   0.03,
    "bist100_1d_change": -0.04,
}

KAP_EVENT_WINDOW_DAYS: int = 3
KAP_HIGH_PRIORITY_MULTIPLIER: float = 1.5

# Technical layer sub-score thresholds
RSI_THRESHOLDS: dict[str, float] = {
    "oversold":         30.0,
    "weak_bearish":     45.0,
    "neutral_upper":    55.0,
    "mild_overbought":  70.0,
    "overbought":       80.0,
}

RSI_SCORES: dict[str, float] = {
    "oversold":         80.0,  # RSI < 30
    "weak_bearish":     65.0,  # RSI 30-45
    "neutral":          50.0,  # RSI 45-55
    "mild_bullish":     60.0,  # RSI 55-70
    "overbought":       25.0,  # RSI 70-80
    "extreme_overbought": 10.0, # RSI > 80
}

MA_SCORES: dict[int, float] = {3: 80.0, 2: 60.0, 1: 40.0, 0: 20.0}

VOLUME_SURGE_SCORE: float = 65.0
VOLUME_NO_SURGE_SCORE: float = 50.0

PROXIMITY_HIGH_THRESHOLD: float = 0.95  # price / 52w_high > 0.95
PROXIMITY_LOW_THRESHOLD: float = 0.05   # proximity_below_52w_high < 0.05
PROXIMITY_HIGH_SCORE: float = 70.0
PROXIMITY_LOW_SCORE: float = 30.0
PROXIMITY_NEUTRAL_SCORE: float = 50.0

# KAP layer category impacts (added to base 50)
KAP_CATEGORY_IMPACT: dict[str, float] = {
    "temettu":          25.0,
    "sermaye_artirimi": 15.0,
    "ozel_durum":        0.0,
    "finansal_rapor":    0.0,
    "insider":          10.0,
    "genel_kurul":       5.0,
    "diger":             0.0,
}
KAP_BASE_SCORE: float = 50.0
KAP_DUPLICATE_MULTIPLIER: float = 0.5  # extra events of same category

# Risk layer base and penalties
RISK_BASE_SCORE: float = 70.0
RISK_RSI_OVERBOUGHT_PENALTY: float = 20.0   # RSI > 80
RISK_VOLUME_ANOMALY_PENALTY: float = 15.0   # volume surge + price drop
RISK_USDTRY_SPIKE_PENALTY: float = 25.0     # USDTRY 1d change > 2%
RISK_VIX_HIGH_PENALTY: float = 20.0         # VIX > 25
RISK_VIX_EXTREME_PENALTY: float = 35.0      # VIX > 30

RISK_USDTRY_SPIKE_THRESHOLD: float = 0.02
RISK_VIX_HIGH_THRESHOLD: float = 25.0

# Macro layer
ASSET_DIRECTIONS: dict[str, float] = {
    "USDTRY":  -1.0,
    "EURTRY":  -1.0,
    "VIX":     -1.0,
    "BRENT":   +0.5,
    "GOLD":    -0.3,
    "SP500":   +1.0,
    "BIST100": +1.0,
}

# Regime thresholds
REGIME_RISK_ON_VIX_MAX: float = 20.0
REGIME_NEUTRAL_VIX_MAX: float = 30.0

# Local macro signals (TCMB, CDS, BIST Foreign Weekly)
LOCAL_MACRO_ENABLED: bool = True  # Feature flag: enabled for live testing

# TCMB Policy Rate signals
TCMB_DECISION_MAP: dict[str, float] = {
    "hike": 25.0,   # Bearish: rate hike signals tightening/stress
    "cut": 75.0,    # Bullish: rate cut signals easing
    "hold": 50.0,   # Neutral
}
TCMB_STALE_DAYS: int = 45

# TCMB Trend Modeling (Gap 2 — SPEC_L2_ENHANCEMENT_1)
# Inflection: direction reversal between last two decisions → strongest signal.
TCMB_TREND_SCORES: dict[str, float] = {
    "cutting_cycle": 80.0,   # hike → cut inflection: very bullish
    "easing":        75.0,   # continued cuts: bullish (matches TCMB_DECISION_MAP["cut"])
    "holding":       50.0,   # neutral
    "tightening":    25.0,   # continued hikes: bearish (matches TCMB_DECISION_MAP["hike"])
    "hiking_cycle":  20.0,   # cut → hike inflection: very bearish
}

# CDS (Turkey 5Y spreads) thresholds
CDS_THRESHOLDS: dict[str, tuple[float, float]] = {
    "low_risk": (0.0, 250.0),          # < 250 bps -> bullish
    "neutral": (250.0, 350.0),         # 250-350 bps -> neutral
    "high_risk": (350.0, 500.0),       # > 350 bps -> bearish
    "extreme_risk": (500.0, float('inf')),  # > 500 bps -> critical
}
CDS_SCORES: dict[str, float] = {
    "low_risk": 75.0,
    "neutral": 50.0,
    "high_risk": 30.0,
    "extreme_risk": 10.0,
}
CDS_STALE_DAYS: int = 2

# BIST Foreign Ownership Weekly (macro context, not Bull Trap detection)
BIST_FOREIGN_STALE_DAYS: int = 10
BIST_FOREIGN_THRESHOLD_OUTFLOW: float = -0.2  # % daily change threshold
BIST_FOREIGN_THRESHOLD_INFLOW: float = 0.2    # % daily change threshold

# DXY — US Dollar Index (Gap 3 — SPEC_L2_ENHANCEMENT_1)
# Higher DXY (USD strength) → EM capital outflows → bearish for BIST.
# Thresholds: weekly % change → score. List ordered high-to-low; first match wins.
DXY_STALE_DAYS: int = 2
DXY_SCORE_THRESHOLDS: list[tuple[float, float]] = [
    ( 0.015, 25.0),   # ≥ +1.5% weekly: strong USD → very bearish BIST
    ( 0.005, 40.0),   # +0.5% to +1.5%: mild USD strength
    (-0.005, 50.0),   # ±0.5%: neutral
    (-0.015, 60.0),   # -0.5% to -1.5%: mild USD weakness → bullish BIST
]
DXY_SCORE_WEAK_USD: float = 75.0   # < -1.5% weekly: USD very weak → very bullish BIST

# TL Bond Yield Proxy via CDS (Gap 4 — SPEC_L2_ENHANCEMENT_1)
# Phase 5: Replace with native TL yields (ICDP/MINT data integration).
# Formula: implied_tl_yield (%) = TL_BOND_PROXY_BASE_YIELD + cds_bps / 100
# Higher implied yield → higher equity discount rate → bearish.
TL_BOND_PROXY_BASE_YIELD: float = 4.5   # US 10Y proxy as floor rate (%)
TL_BOND_PROXY_THRESHOLDS: dict[str, float] = {
    "low":    5.0,    # implied yield < 5%  → low duration risk
    "medium": 8.0,    # 5–8%               → medium
    "high":   12.0,   # 8–12%              → high
                      # ≥ 12%              → extreme
}
TL_BOND_PROXY_SCORES: dict[str, float] = {
    "low":     70.0,
    "medium":  50.0,
    "high":    30.0,
    "extreme": 15.0,
}

# Composite macro weighting (global + local)
# Gap 3: DXY added at 0.25; global_signals reduced from 0.50 to 0.25.
# macro_layer.py redistributes DXY weight back to global_signals when DXY absent
# (confidence=0), so total effective weight always equals 1.0.
MACRO_WEIGHTS_COMPOSITE: dict[str, float] = {
    "global_signals":    0.25,   # Gap 3: was 0.50; DXY fallback restores to 0.50 when absent
    "tcmb":              0.25,   # TCMB policy rate
    "cds":               0.25,   # CDS spreads
    "dxy":               0.25,   # Gap 3: DXY global USD index
    "bist_foreign_weekly": 0.0,  # Stub (Layer 5 will use daily version)
    "tl_bond_proxy":     0.0,    # Gap 4 stub: Phase 5 activate with native TL yields
}

# Local-only macro composite weights (TCMB + CDS + BIST foreign weekly).
# Gap 1 (SPEC_L2_ENHANCEMENT_1): foreign flows activated from 0% -> 20%.
# Config-driven (NOT hard-coded) so weights can be retuned after Layer 5
# integration without touching local_macro_signals.py logic.
LOCAL_MACRO_WEIGHTS: dict[str, float] = {
    "tcmb": 0.40,
    "cds": 0.40,
    "bist_foreign_weekly": 0.20,
}

# Correlation Matrix (Phase 4.3 — portfolio risk / position sizing)
CORRELATION_WINDOW_DAYS: int = 60       # Rolling window for return correlations
CORRELATION_MIN_SAMPLES: int = 50       # Samples for full confidence (1.0)
CORRELATION_CLUSTER_THRESHOLD: float = 0.75  # Min corr to group stocks in a cluster

# Exit and risk alerting thresholds
EXIT_STOP_LOSS: float = 0.92        # Stop-loss at entry * 0.92 (-8%)
EXIT_PROFIT_TARGET: float = 1.20    # Profit target at entry * 1.20 (+20%)
STOP_APPROACH_BUFFER: float = 0.03  # Warning when price within 3% of stop-loss

# Backtest entry gatekeeping thresholds (prevent low-quality entries in risk-off regimes)
BACKTEST_MACRO_MIN_SCORE: float = 45.0      # Minimum macro score to allow entry (< 45 = no entry)
BACKTEST_VIX_MAX: float = 30.0              # VIX > 30 = no entry (extreme volatility risk-off)
BACKTEST_USDTRY_SPIKE_THRESHOLD: float = 0.02  # USDTRY daily change > +2% = no entry (EM stress)

# L5 Smart Money — D-055 (Phase 4.5 progressive build)
# MASTER_WEIGHTS["smart_money"] stays at 0.25; L5_SMART_MONEY_WEIGHT is the ACTIVE weight
# when L5 has valid data. Phase 4.5 normalizer divides by actual total_weight (0.78-0.85).
L5_SMART_MONEY_WEIGHT: float = 0.10          # Active weight when score is valid
SMART_MONEY_STALE_HOURS: int = 48            # >48h since last write → score=None, weight=0
SMART_MONEY_MOMENTUM_DAYS: int = 10          # Day 10+: momentum signal activates
SMART_MONEY_FULL_COMPOSITE_DAYS: int = 20    # Day 20+: full composite activates
SMART_MONEY_PERCENTILE_WINDOW: int = 252     # Rolling window for percentile rank
SMART_MONEY_PERCENTILE_WEIGHT: float = 0.60  # 60% percentile in composite
SMART_MONEY_MOMENTUM_WEIGHT: float = 0.40    # 40% momentum in composite
SMART_MONEY_ADV_MIN_TL: float = 20_000_000.0  # Min daily volume (TL) for eligibility
SMART_MONEY_OUTLIER_THRESHOLD_PP: float = 1.0  # Daily change > 1pp triggers MAD clipping

# L5 Sub-signal weights (D-058) — short interest integration
L5_FOREIGN_WEIGHT: float = 0.70       # Foreign ratio weight in L5 composite
L5_SHORT_INT_WEIGHT: float = 0.30     # Short interest weight in L5 composite

# Short interest thresholds
SHORT_INTEREST_HIGH: float = 15.0     # % free float — high crowding threshold
SHORT_INTEREST_STALE: int = 10        # days — no update → neutral fallback

# L3-L5 covariance dampening (D-058)
L5_KAP_OVERLAP_DAMP: float = 0.6      # Dampening factor when L3 KAP + L5 short overlap
