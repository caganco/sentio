"""All threshold constants for the Signal Engine. No magic numbers elsewhere."""

MASTER_WEIGHTS: dict[str, float] = {
    "technical": round(0.20 / 1.00, 10),   # 0.2000 (unchanged)
    "macro":     round(0.35 / 1.00, 10),   # 0.3500 (unchanged)
    "kap":       round(0.15 / 1.00, 10),   # 0.1500 (unchanged)
    "risk":      round(0.05 / 1.00, 10),   # 0.0500 (unchanged)
    "smart_money": round(0.20 / 1.00, 10), # 0.2000 (NEW: Layer 5 active, was stub)
    "sentiment": round(0.05 / 1.00, 10),   # 0.0500 (reduced from 0.25, rationale: institutional flow stronger than retail)
}

SIGNAL_THRESHOLDS: dict[str, float] = {
    "buy_strong":  72.0,
    "buy_weak":    60.0,
    "hold_upper":  60.0,
    "hold_lower":  43.0,
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

# Composite macro weighting (global + local)
MACRO_WEIGHTS_COMPOSITE: dict[str, float] = {
    "global_signals": 0.50,      # MacroSignals (existing)
    "tcmb": 0.25,                # TCMB policy rate
    "cds": 0.25,                 # CDS spreads
    "bist_foreign_weekly": 0.0,  # Stub (Layer 5 will use daily version)
}
