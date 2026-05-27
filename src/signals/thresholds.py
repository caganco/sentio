"""All threshold constants for the Signal Engine. No magic numbers elsewhere."""

# -----------------------------------------------------------------------------
# PHASE 4.5 LAYER MAPPING (D-052) -- engine internal name <-> SPEC L# number.
# Verified against SPEC_SIGNAL_CONVICTION_1.md (l.75-77, 129-131, 283-291) and
# OS_STATE.md (l.87-93). DO NOT reorder without re-verifying both sources.
#
#   engine name   SPEC   weight        runtime            note
#   -----------   ----   ------        ----------------   -------------------------
#   technical     L1     0.25/0.97     fixed              -
#   macro         L2     0.20/0.97     fixed              also drives macro modulation
#   kap           L3     0.30/0.97     fixed              -
#   sentiment     L4     0.12/0.97     x l4_confidence    SUSPENDED -> conf=0 -> 0 contrib
#   smart_money   L5     0.10/0.97     x l5_confidence    data-collection, conf~=0 early
#   risk          L6     REMOVED       D-154: composite'ten cikarildi; pos sizing tarafinda kalir
#
# Static sum = 1.00 (stays in architecture-safety band [0.85, 1.05]).
# Effective runtime Sigma in [0.7732, 1.00] via L4/L5 confidence scaling at
# LayerScore creation (engine.py). The 0.7732 floor is the EMERGENT normalizer
# -- see docs/decisions/DEC-009. (D-154: was 0.78 before L6 removal)
# -----------------------------------------------------------------------------
MASTER_WEIGHTS: dict[str, float] = {
    "technical":   round(0.25 / 0.97, 10),  # L1 ~0.2577 (D-154: renormalized ex-L6)
    "macro":       round(0.20 / 0.97, 10),  # L2 ~0.2062 (D-154: renormalized ex-L6)
    "kap":         round(0.30 / 0.97, 10),  # L3 ~0.3093 (D-154: renormalized ex-L6)
    "sentiment":   round(0.12 / 0.97, 10),  # L4 ~0.1237 (x l4_confidence; SUSPENDED)
    "smart_money": round(0.10 / 0.97, 10),  # L5 ~0.1031 (x l5_confidence)
    # risk/L6: removed D-154 (weight was 0.03 = noise; pos sizing unchanged)
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

# --- TREND rejim RSI skorlari (D-164) ---
RSI_SCORES_TREND: dict[str, float] = {
    "oversold":             80.0,  # RSI < 30 — RSI_SCORES ile ayni
    "weak_bearish":         65.0,  # RSI 30-45 — RSI_SCORES ile ayni
    "neutral":              50.0,  # RSI 45-55 — RSI_SCORES ile ayni
    "mild_bearish":         45.0,  # RSI 55-70 — hafif duzeltme (was 60.0)
    "overbought":           50.0,  # RSI 70-80 — NOTR (trend devam ediyor)
    "extreme_overbought":   35.0,  # RSI > 80  — dikkat ama ceza yok
}

MA_SCORES: dict[int, float] = {3: 80.0, 2: 60.0, 1: 40.0, 0: 20.0}

VOLUME_SURGE_SCORE: float = 65.0       # legacy binary True → kept for backward compat
VOLUME_NO_SURGE_SCORE: float = 50.0    # legacy binary False → kept for backward compat

# Volume surge gradient thresholds (D-160) — vol_ratio = volume / vol_20d_avg
VOLUME_SURGE_WEAK: float = 1.10     # ×1.10 → zayıf (60.0 sub-score)
VOLUME_SURGE_STRONG: float = 1.50   # ×1.50 → güçlü (75.0 sub-score)
VOLUME_SURGE_EXTREME: float = 3.00  # ×3.00 → ekstrem (90.0 sub-score)

PROXIMITY_HIGH_THRESHOLD: float = 0.95  # price / 52w_high > 0.95
PROXIMITY_LOW_THRESHOLD: float = 0.05   # proximity_below_52w_high < 0.05
PROXIMITY_HIGH_SCORE: float = 70.0
PROXIMITY_LOW_SCORE: float = 30.0
PROXIMITY_NEUTRAL_SCORE: float = 50.0

# ── ADX regime thresholds (D-155) ─────────────────────────────────────────────
# ADX > ADX_TREND_THRESHOLD → TREND  (MA/momentum dominant)
# ADX < ADX_RANGE_THRESHOLD → RANGE  (RSI/proximity dominant)
# ADX_RANGE_THRESHOLD <= ADX <= ADX_TREND_THRESHOLD → TRANSITION (equal weights)
# adx=None (no data feed yet) → TRANSITION — geriye dönük uyumlu (D-156: ADX fetch)
ADX_TREND_THRESHOLD: float = 25.0
ADX_RANGE_THRESHOLD: float = 20.0

# L1 internal sub-score weights per regime (each must sum to 1.0) (D-155)
L1_WEIGHTS_TREND: dict[str, float] = {
    "ma_alignment":  0.40,
    "momentum":      0.30,
    "volume":        0.15,
    "52w_proximity": 0.10,
    "rsi":           0.05,
}
L1_WEIGHTS_RANGE: dict[str, float] = {
    "rsi":           0.40,
    "52w_proximity": 0.20,
    "volume":        0.15,
    "ma_alignment":  0.15,
    "momentum":      0.10,
}
L1_WEIGHTS_TRANSITION: dict[str, float] = {
    "ma_alignment":  0.20,
    "momentum":      0.20,
    "volume":        0.20,
    "52w_proximity": 0.20,
    "rsi":           0.20,
}

# KAP layer category impacts (added to base 50)
KAP_CATEGORY_IMPACT: dict[str, float] = {
    "temettu":          25.0,
    "sermaye_artirimi": 15.0,
    "ozel_durum":        0.0,
    "finansal_rapor":    0.0,   # DEPRECATED D-158: parse_earnings_surprise() kullanılır; Faz 2'de silinecek
    "insider":          10.0,
    "genel_kurul":       5.0,
    "diger":             0.0,
}
KAP_BASE_SCORE: float = 50.0
KAP_DUPLICATE_MULTIPLIER: float = 0.5  # extra events of same category

# ── KAP Earnings numeric parser thresholds (D-158) ────────────────────────────
KAP_EARNINGS_NEUTRAL_BAND: float = 0.05     # ±%5 delta → score=0.0 (beklenti içinde)
KAP_EARNINGS_STRONG_THRESHOLD: float = 0.20 # ±%20 delta → ±1.0 (güçlü sürpriz)
KAP_EARNINGS_IMPACT_SCALE: float = 40.0    # surprise_score × scale → L3 impact (-40..+40)

# D-131 (CB-004): KAP L3 event-triggered weight boost. KAP filings episodik --
# sessiz gunlerde sabit weight KAP'in notr skorunu fazla sayar. Per-call carpan
# kap layer'in EFEKTIF weight'ine uygulanir; MASTER_WEIGHTS degismez, composite
# Sigma(weights)'e bolundugu icin otomatik re-normalize olur. Notr durum = 1.0.
KAP_EVENT_BOOST_MULTIPLIER: float = 1.4   # boost-kategori event varsa
KAP_NO_EVENT_MULTIPLIER: float = 0.7      # window icinde hic relevant event yoksa
KAP_BOOST_CATEGORIES: list[str] = ["pay_sahipligi", "temettu", "sermaye_artirimi"]

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
    "USDTRY":          -1.0,
    "EURTRY":          -1.0,
    "VIX":             -1.0,
    "BRENT":           +0.5,
    "GOLD":            -0.3,
    "SP500":           +1.0,
    # "BIST100": +1.0  — D-154: removed (circular: benchmark = signal). Replaced by EM_RELSTRENGTH.
    "EM_RELSTRENGTH":  +1.0,  # D-154: BIST100/EEM 20d ratio momentum; bullish when BIST outperforms EM
}

# EM Relative Strength constants (D-154, RR-022 §B)
EM_RELSTRENGTH_LOOKBACK: int = 20    # days — (XU100/EEM) ratio momentum window
EM_RELSTRENGTH_SCALE: float = 0.15   # +/-15% ratio move → +/-1.0 normalized score

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

# =============================================================================
# EVDS TUFE + YI-UFE CANONICAL CODES (D-151, RR-021 section 3.3)
# Gozlem modu -- inflation signals not yet integrated into L2 layer.
# =============================================================================
# TUFE: TP.FG.J0 last obs 2026-1 (active); TP.FE.OKTG01 last obs 2025-12 (stale).
# TP.FG.J0 canonical (D-151 live test 2026-05-26).
EVDS_TUFE_SERIES: str = "TP.FG.J0"    # D-151 canonical (fresher than TP.FE.OKTG01)
EVDS_TUFE_STALE_DAYS: int = 45        # monthly; TUIK publishes ~day 3 of each month
# YI-UFE: TP.FG01 DEAD (HTTP 400). TP.FG.J01 empirically inferred as Yi-UFE Genel
# (2003=100) -- values match TUIK historical (662 vs 537 TUFE in May 2021).
# EVDS serieList API returned 404 for bie_tukfiy4; inference from value levels only.
# Confirm with TUIK/EVDS documentation before integrating into a live signal.
EVDS_YI_UFE_SERIES: str = "TP.FG.J01"  # EMPIRICAL -- not confirmed via metadata API

# D-144 Multi-window foreign flow (CB-011)
# ASCII-only comments (cp1254 architecture-test safety).
FOREIGN_FLOW_WINDOWS: tuple = (3, 5, 10)       # analysis windows (days)
FOREIGN_FLOW_PERSISTENCE_MIN: int = 3           # min consecutive days for +20% boost
FOREIGN_FLOW_QNB_TICKER: str = "QNBFB.IS"      # structural bias ticker
FOREIGN_FLOW_QNB_FILTER_ENABLED: bool = True    # apply QNB correction
FOREIGN_FLOW_SIGNAL_VERSION: str = "v2"         # audit trail

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
# macro_layer.py redistributes DXY/foreign weight back to global_signals when
# those signals are absent (confidence=0), so total effective weight stays 1.0.
# D-118 (CB-007): bist_foreign_weekly activated 0.0 -> 0.15 (Ulku & Ikizlerli
# 2012 -- weekly net foreign flow Granger-causes BIST returns). DXY took the
# largest cut (0.25 -> 0.19, asymmetric): its BIST effect is indirect via
# USDTRY (already in global_signals -> double-count risk) and often confidence=0.
# Sum = 0.22 + 0.22 + 0.22 + 0.19 + 0.15 = 1.00 (tl_bond_proxy stub stays 0.0).
MACRO_WEIGHTS_COMPOSITE: dict[str, float] = {
    "global_signals":    0.22,   # D-118: was 0.25; DXY/foreign fallback restores when absent
    "tcmb":              0.22,   # D-118: was 0.25 -- TCMB policy rate
    "cds":               0.22,   # D-118: was 0.25 -- CDS spreads
    "dxy":               0.19,   # D-118: was 0.25 -- asymmetric cut (indirect via USDTRY)
    "bist_foreign_weekly": 0.15, # D-118: was 0.0 -- CB-007 activation (market-level net flow)
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
# --- Volatility-aware stop-loss (SPEC_STOPLOSS_VOLATILITY_AWARE_1, D-110) ----
# ATR/P ratio (ATR_20 / close) defines stop width tier. Hard floor caps the
# widest stop at -20% (catastrophic loss cap). Risk parity sizes position so
# the dollar loss at stop equals RISK_PER_TRADE_PCT of equity across all tiers.
# EXIT_STOP_LOSS (0.92) preserved as legacy / mid-vol default.

STOP_ATR_WINDOW: int = 20              # Stop-specific ATR window (wider than TP's 14d)

# ATR/Price ratio tier boundaries (% of price)
STOP_ATR_PCT_LOW_MAX:  float = 2.0     # ATR/P < 2% -> low vol tier
STOP_ATR_PCT_MID_MAX:  float = 4.0     # ATR/P < 4% -> mid vol tier
STOP_ATR_PCT_HIGH_MAX: float = 6.0     # ATR/P < 6% -> high vol tier
                                        # >= 6% -> extreme (microcap)

# Stop distances (positive fractions; applied as entry * (1 - stop_distance))
STOP_LOSS_LOW_VOL:     float = 0.06    # -6% for ATR/P < 2%
STOP_LOSS_MID_VOL:     float = 0.08    # -8% for ATR/P 2-4% (matches EXIT_STOP_LOSS)
STOP_LOSS_HIGH_VOL:    float = 0.12    # -12% for ATR/P 4-6%
STOP_LOSS_EXTREME_VOL: float = 0.15    # -15% for ATR/P >= 6% (microcap)
STOP_HARD_FLOOR:       float = 0.20    # -20% absolute maximum (catastrophic loss cap)

# Risk parity: target position dollar-risk fixed across all vol tiers.
# position_size = (equity * RISK_PER_TRADE_PCT) / stop_distance
RISK_PER_TRADE_PCT: float = 0.01

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
L5_CONF_PARTIAL: float = 0.5                 # Day 10-19 confidence (momentum-only phase)
L5_CONF_FULL: float = 0.8                    # Day 20+ confidence (full composite phase)
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

# D-127 PaySahipligi / Major Holder Change (SPK XI.29.1)
MAJOR_HOLDER_CHANGE_THRESHOLD_PCT: float = 5.0      # SPK zorunlu bildirim esigi
MAJOR_HOLDER_CHANGE_LOOKBACK_DAYS: int = 30          # Olay gecerliligi (gun)
L5_MAJOR_HOLDER_WEIGHT: float = 0.10                 # Blend agirligi L5 kompozitinde
L5_MAJOR_HOLDER_ENTRY_SCORE: float = 75.0            # BULL: kurumsal giris >= %5
L5_MAJOR_HOLDER_EXIT_SCORE: float = 25.0             # BEAR: kurumsal cikis

# =============================================================================
# PHASE 4.5 -- RUTHLESS ALPHA (D-052). SPEC_SIGNAL_CONVICTION_1 /
# POSITION_SIZING_2 / MACRO_REGIME_GATE_2 / STAGED_TP_1.
# Single source of truth -- no magic numbers elsewhere.
# =============================================================================

# --- Conviction tiers (SPEC_SIGNAL_CONVICTION_1) ---
# conviction_score (0-1) = (composite_0_100 / 100) * macro_multiplier, clamp 1.0.
# Tiers authoritative per task criteria + SPEC Sections 1.2/3.3/5.1/10.
CONVICTION_STRONG: float = 0.68       # >= -> BUY-STRONG
CONVICTION_MEDIUM: float = 0.55       # 0.55-0.67 -> BUY-MEDIUM; < -> WATCH (entry tiers)
# Position-sizing lifecycle boundaries (SPEC_POSITION_SIZING_2 1.2):
CONVICTION_WEAK: float = 0.45         # 0.45-0.54 -> BUY-WEAK watchlist
CONVICTION_COLLAPSE: float = 0.35     # 0.35-0.44 -> HOLD; < -> SELL/forced staged exit

# Macro modulation multiplier (L2 macro score on 0-100 engine scale).
CONVICTION_MACRO_BULL_MIN: float = 65.0    # L2 ≥ 65 → ×1.2
CONVICTION_MACRO_NEUTRAL_MIN: float = 50.0  # L2 ≥ 50 → ×1.0; < 50 → ×0.85
CONVICTION_MACRO_MULT_BULL: float = 1.2
CONVICTION_MACRO_MULT_NEUTRAL: float = 1.0
CONVICTION_MACRO_MULT_BEAR: float = 0.85

# Emergent runtime normalizer floor (DEC-009). Dynamic normalizer preserved;
# this is the documented floor when L4 (suspended) + L5 (conf≈0) contribute 0.
# D-154: L6 removed → floor changes from 0.78 to ~0.7732 (tech+macro+kap renormalized).
RUNTIME_NORMALIZER_FLOOR: float = round(0.75 / 0.97, 10)  # ≈ 0.7731958763
# Static MASTER_WEIGHTS sum must stay within this architecture-safety band.
MASTER_WEIGHTS_SUM_MIN: float = 0.85
MASTER_WEIGHTS_SUM_MAX: float = 1.05

# --- Macro regime gate (SPEC_MACRO_REGIME_GATE_2) ---
# L2 macro score (0-100 engine scale) → position sizing multiplier.
# Task criteria authoritative: flat 0.8 in NEUTRAL (no interpolation).
MACRO_GATE_BULL_MIN: float = 60.0      # L2 ≥ 60 → BULL, 1.0×
MACRO_GATE_NEUTRAL_MIN: float = 45.0   # 45 ≤ L2 < 60 → NEUTRAL, 0.8×; < 45 → BEAR, 0.0×
MACRO_GATE_SCALING_BULL: float = 1.0
MACRO_GATE_SCALING_NEUTRAL: float = 0.8
# --- Macro regime gate v2 (SPEC_MACRO_GATE_SOFTENING_1, D-108) -----------
# CDS percentile-conditional softening of BEAR hard gate.
# Ref: Longstaff, Pan, Pedersen, Singleton (2011) NBER 16563.
# Legacy MACRO_GATE_SCALING_BEAR = 0.0 preserved below (v1 callers unchanged).

CDS_PERCENTILE_WINDOW: int = 252           # Rolling window for CDS percentile rank
CDS_PERCENTILE_LOW:  float = 0.50          # <= LOW -> overlay = 1.0 (no dampening)
CDS_PERCENTILE_HIGH: float = 0.90          # >= HIGH -> overlay = CDS_SCALING_HIGH
CDS_SCALING_HIGH: float = 0.25             # Max dampening multiplier
MACRO_GATE_SOFT_BEAR_BASE: float = 0.25    # L2<45 + CDS normal -> 0.25x (was hard 0.0x)
MACRO_GATE_HARD_EXIT_CDS_BPS: float = 600.0    # CDS >= 600 bps -> unconditional 0.0x
MACRO_GATE_HARD_EXIT_USDTRY_SIGMA: float = 3.0 # USDTRY z-score >= 3 -> unconditional 0.0x
                                                # (Phase 1: placeholder; z-score not yet computed)
MACRO_GATE_SCALING_BEAR: float = 0.0

# CB-002: L2-step soft scaling floor. v2 base scaling = first band whose
# threshold L2 does not reach; >= 60 -> MACRO_GATE_SCALING_BULL (1.0). Replaces
# the L2<45 -> 0.0 full block with a positive floor (CDS overlay + hard exits
# still apply on top). DEC-017 CDS overlay preserved as a multiplicative dampener.
MACRO_GATE_FLOOR: float = 0.3
MACRO_GATE_THRESHOLDS: list[tuple[float, float]] = [(30.0, 0.3), (45.0, 0.5), (60.0, 0.8)]

# --- Position sizing (SPEC_POSITION_SIZING_2) ---
POSITION_SIZE_STRONG: float = 0.325    # 32.5% base per BUY-STRONG
POSITION_SIZE_MEDIUM: float = 0.175    # 17.5% base per BUY-MEDIUM
MAX_POSITIONS_STRONG: int = 4
MAX_POSITIONS_MEDIUM: int = 2
MAX_POSITIONS_TOTAL: int = 6
MAX_SECTOR_CONCENTRATION: float = 0.40  # Single sector cap
MAX_DRAWDOWN_HARD_STOP: float = 0.15    # Portfolio DD → liquidate / pause entries

# --- ADV cap + execution timing (D-145, RR-014) ---
# Ref: Almgren (2005) optimal execution / Ekinci (2003) BIST intraday pattern.
# Max position = min(conviction-based TL, POSITION_MAX_ADV_PCT x ADV_20d).
# Prevents oversized entries in illiquid BIST names (market impact control).
POSITION_MAX_ADV_PCT: float = 0.05   # 5% of 20-day Average Daily Volume (TL)

# Ekinci (2003) BIST intraday: sabah ters-J + ogleden sonra U-sekli likidite.
# Acilis (09:30-10:30) ve kapanis oncesi (15:30+) likidite dusuk -> bu
# pencereler disinda islem onerilmez. Yalnizca rapor notu; otomatik emir degil.
EXECUTION_WINDOW_MORNING_START:   str = "10:30"
EXECUTION_WINDOW_MORNING_END:     str = "11:30"
EXECUTION_WINDOW_AFTERNOON_START: str = "14:00"
EXECUTION_WINDOW_AFTERNOON_END:   str = "15:30"

# --- Net EV check + transaction cost (D-146, RR-015) ---
# Ref: Almgren & Chriss (2001), Ekinci (2003) BIST spread/commission analysis.
# net_ev = expected_return - round_trip_cost; enter only if net_ev >= MIN_NET_EV.
ROUND_TRIP_COST_PCT_DEFAULT: float = 0.009   # %0.9 fallback (unknown broker tier)
MIN_NET_EXPECTED_VALUE_PCT:  float = 0.005   # %0.5 minimum net EV to enter
BROKER_TIER: str = "A"                       # Default broker: Garanti BBVA (Tier A)
# Hisse-bazlı override: mikro-cap / dar spread likidite (1.3% round-trip)
HIGH_COST_TICKERS: tuple = ("ENERY", "AYGAZ", "GUBRF")
HIGH_COST_RT_PCT: float = 0.013             # %1.3 mikro-cap round-trip

# --- Staged take-profit (SPEC_STAGED_TP_1) ---
TP1_PCT_EXIT: float = 0.50             # First resistance
TP2_PCT_EXIT: float = 0.30             # Fib 0.618
TP3_PCT_EXIT: float = 0.20             # Trailing / trend break
ATR_TP1_MULTIPLE: float = 1.5          # Fallback when no detected levels (NEUTRAL/BEAR)
ATR_TP2_MULTIPLE: float = 3.0
ATR_TP3_MULTIPLE: float = 5.0
# --- Staged TP regime-conditional (SPEC_TP_REGIME_CONDITIONAL_1, D-109) -----
# BULL: wider TP fallbacks + minimum-distance filter so winners can run.
# NEUTRAL/BEAR behavior unchanged (uses ATR_TP*_MULTIPLE above).
ATR_TP1_MULTIPLE_BULL: float = 2.5
ATR_TP2_MULTIPLE_BULL: float = 4.0
ATR_TP3_MULTIPLE_BULL: float = 6.5
ATR_TP1_MIN_DISTANCE_BULL: float = 2.0  # Real TP1 candidates must be >= entry + 2*ATR
TP_PIVOT_LOOKBACK: int = 20
TP_SWING_HIGH_LOOKBACK: int = 60
TP_FIB_LOOKBACK: int = 252
TP_MA200_LOOKBACK: int = 200
TP_CONFIDENCE_FLOOR: float = 0.6       # confidence = 0.6 + overlap × 0.15
TP_CONFIDENCE_OVERLAP_BONUS: float = 0.15
TP3_TRAIL_BULL: float = 0.02           # Trailing-stop % by regime
TP3_TRAIL_NEUTRAL: float = 0.03
TP3_TRAIL_BEAR: float = 0.02
TP2_DAYS_HOLD: int = 3                 # Limit not filled → lower price
TP3_DAYS_HOLD: int = 10                # Max hold before TP3 review
CONVICTION_COLLAPSE_HOLD_HOURS: int = 24  # Recovery window before TP2+TP3 force-close

# =============================================================================
# L4 NEWS SENTIMENT — D-094 (SPEC_L4_NEWS_1)
# borsa-mcp + Mynet Finans + FinBERT pipeline
# =============================================================================

# Haber çekme
L4_NEWS_LOOKBACK_DAYS: int = 7            # son kaç günlük haber
L4_NEWS_CACHE_TTL_HOURS: int = 6          # borsa-mcp önbellek yenileme süresi
L4_NEWS_RECENCY_DECAY: float = 0.85       # recency weight = 0.85^age_days

# Aktivasyon kapısı
L4_MIN_ARTICLES_ACTIVATE: int = 3         # < 3 → confidence = 0.0 (no signal)
L4_MIN_ARTICLES_FULL_CONF: int = 10       # >= 10 → volume_conf = 1.0

# FinBERT modeli (Phase 1: İngilizce finansal; TR modeli ayrı micro-SPEC)
L4_FINBERT_MODEL: str = "ProsusAI/finbert"
L4_FINBERT_MAX_TOKENS: int = 512          # BERT truncation limit

# FinBERT kategorilendirme eşikleri — [-1, 1] normalized score
L4_BULLISH_THRESHOLD: float = 0.15        # score > +0.15 → bullish
L4_BEARISH_THRESHOLD: float = -0.15       # score < -0.15 → bearish

# Hybrid NLP tier thresholds (D-124)
LEXICON_TIER1_HIGH: float = 1.0     # |raw_score| > 1.0 → definite, bypass Tier-2
LEXICON_TIER1_LOW: float = 0.3      # |raw_score| ≤ 0.3 → neutral, bypass Tier-2
HAIKU_TIMEOUT_S: float = 10.0       # Claude Haiku 4.5 per-request timeout (seconds)
HAIKU_MAX_RETRIES: int = 2          # Transient failure retry count

# Confidence bileşen ağırlıkları (toplam 1.00)
L4_CONF_VOLUME_WEIGHT: float = 0.35
L4_CONF_AGREEMENT_WEIGHT: float = 0.40
L4_CONF_QUALITY_WEIGHT: float = 0.25

# Ticker-haber eşleştirme relevans ağırlıkları
TICKER_MATCH_WEIGHTS: dict[str, float] = {
    "exact_ticker":  1.00,
    "company_name":  0.85,
    "sector_theme":  0.30,
    "no_match":      0.10,
}

# Ticker → şirket adı alias'ları (Türkçe haberlerde geçen isimler, küçük harf)
TICKER_COMPANY_ALIASES: dict[str, list[str]] = {
    # — Bankacılık ——————————————————————————————————————
    "AKBNK": ["akbank", "ak bank"],
    "GARAN": ["garanti", "garanti bbva", "garanti bankası"],
    "ISCTR": ["iş bankası", "işbank", "türkiye iş bankası"],
    "YKBNK": ["yapı kredi", "yapı ve kredi"],
    "HALKB": ["halkbank", "halk bankası", "türkiye halk bankası"],
    "VAKBN": ["vakıfbank", "vakıf bankası"],
    "SKBNK": ["şekerbank"],
    "ALBRK": ["albaraka", "albaraka türk"],
    "QNBFB": ["qnb finansbank", "finansbank"],
    # — Holdingler ———————————————————————————————————————
    "KCHOL": ["koç holding", "koç", "koç grubu"],
    "SAHOL": ["sabancı holding", "sabancı"],
    "TKFEN": ["tekfen holding", "tekfen"],
    "ENKAI": ["enka", "enka inşaat"],
    # — Enerji ————————————————————————————————————————————
    "TUPRS": ["tüpraş", "türkiye petrol rafinerileri"],
    "AKSEN": ["aksa enerji", "aksa"],
    "ENERY": ["enerya", "enerya enerji"],
    "ODAS":  ["odaş elektrik", "odaş"],
    # — Perakende / Gıda ——————————————————————————————————
    "BIMAS": ["bim", "bim mağazaları"],
    "MGROS": ["migros", "migros ticaret"],
    "ULKER": ["ülker", "ülker bisküvi"],
    "CCOLA": ["coca-cola içecek", "cci"],
    "AEFES": ["anadolu efes", "efes"],
    # — Teknoloji / Telekom ———————————————————————————————
    "TTKOM": ["türk telekom"],
    "ASELS": ["aselsan"],
    "LOGO":  ["logo yazılım", "logo"],
    # — Ulaşım ————————————————————————————————————————————
    "THYAO": ["türk hava yolları", "thy", "turkish airlines"],
    "TAVHL": ["tav havalimanları", "tav"],
    "PGSUS": ["pegasus", "pegasus hava yolları"],
    "TOASO": ["tofaş", "tofaş otomobil"],
    "FROTO": ["ford otosan", "ford"],
    # — Sanayi / Hammadde ——————————————————————————————————
    "EREGL": ["ereğli demir çelik", "erdemir"],
    "SISE":  ["şişecam", "türkiye şişe ve cam"],
    "KRDMD": ["kardemir"],
    "PETKM": ["petkim"],
}

# =============================================================================
# L5b VIOP (Derivatives) signal thresholds — D-099
# VERDA-independent foundation: direct BIST CSV download, T+1 EOD.
# Not yet wired into engine.py (MASTER_WEIGHTS["viop"] absent → weight=0.0).
# =============================================================================

VIOP_STALE_DAYS: int = 3
VIOP_MIN_OI: int = 500          # Below this → "partial" signal, confidence 0.3

# Put/Call OI ratio interpretation (open interest basis):
#   < 0.50 = strong call dominance → very bullish derivatives positioning
#   0.50-0.80 = moderate call dominance → bullish
#   0.80-1.00 = slight call edge → neutral-bullish
#   1.00-1.20 = slight put edge → neutral-bearish
#   1.20-2.00 = put dominance → bearish
#   >= 2.00 = strong puts → very bearish hedge positioning
VIOP_PC_THRESHOLDS: dict[str, float] = {
    "very_bullish": 0.50,
    "bullish":      0.80,
    "neutral_low":  1.00,
    "neutral_high": 1.20,
    "bearish":      2.00,
}
VIOP_PC_SCORES: dict[str, float] = {
    "very_bullish": 82.0,
    "bullish":      68.0,
    "neutral_low":  55.0,
    "neutral_high": 45.0,
    "bearish":      32.0,
    "very_bearish": 18.0,
}
VIOP_OI_DELTA_BOOST: float = 5.0        # Score nudge when OI delta confirms direction
VIOP_OI_DELTA_THRESHOLD: float = 0.10   # 10% OI change considered a meaningful move

# --- Takasbank market-wide PCR thresholds (CB-008) ---
VIOP_PCR_BEARISH: float = 1.2   # PCR >= 1.2 -> put baskisi (kontraryen bullish tetikleyici)
VIOP_PCR_BULLISH: float = 0.6   # PCR <= 0.6 -> call baskisi (kontraryen bearish tetikleyici)

# =============================================================================
# L5b CUSTODY / MKK TAKAS SCRAPER (D-116, SPEC_FINTABLES_TAKAS_SCRAPER_1)
# Fintables MKK takas verisi → custody_snapshots.db → L5 foreign signal.
# =============================================================================

# --- Storage ---
CUSTODY_DB_PATH: str = "data/custody/custody_snapshots.db"

# --- Scraper rate limiting ---
CUSTODY_SCRAPE_RATE_LIMIT_SEC: float = 2.0   # saniye / ticker (saygılı rate limit)
CUSTODY_SCRAPE_TIMEOUT_SEC: int = 30         # Playwright sayfa yükleme timeout
CUSTODY_MAX_RETRIES: int = 3                 # Hata sonrası yeniden deneme
CUSTODY_RETRY_BACKOFF_SEC: float = 5.0       # İlk bekleme (exponential: ×2 her retry)

# --- Session management ---
CUSTODY_SESSION_FILE: str = ".fintables_session.json"
CUSTODY_SESSION_MAX_AGE_HOURS: int = 24      # Bu süreden eski cookie → yeniden login

# --- History & activation ---
CUSTODY_STALE_HOURS: int = 48                # >48h → None (sinyal dışı, parquet fallback)
CUSTODY_BACKFILL_DAYS: int = 90              # İlk çalışmada geriye dönük çekim
CUSTODY_MIN_HISTORY_DAYS: int = 10           # Bu kadar günden az → score=None

# --- L5 custody signal sub-weights (yalnızca custody DB yolu aktifken geçerli) ---
# Toplam = 1.00 (L5 foreign component içi ağırlıklar).
CUSTODY_FOREIGN_LEVEL_WEIGHT: float = 0.50   # 252d rolling persentil
CUSTODY_MOMENTUM_30D_WEIGHT: float = 0.30    # 30-gün Δ yabancı %
CUSTODY_PERSISTENCE_WEIGHT: float = 0.20     # streak skoru (≤10 gün)

# Normalisation için sabitler
CUSTODY_CHANGE_30D_MAX_PP: float = 10.0      # ±10 pp → [0, 100]
CUSTODY_PERSISTENCE_MAX_DAYS: int = 10       # streak cap

# =============================================================================
# L5b FOREIGN FLOW — Is Yatirim SCREENER BRIDGE (D-126, SPEC_FOREIGN_FLOW_ISYATIRIM_1)
# Custody/MKK abonelik duvarına takıldığı için (D-116), yabancı oran sinyali
# İş Yatırım getScreenerDataNEW (robots-güvenli, login yok) üzerinden köprülenir.
# Günlük foreign_ratio snapshot'ları isyatirim.db'ye birikir → L5'te custody ile
# AYNI makine (_compute_from_custody) change_30d/level/persistence üretir.
# =============================================================================
FOREIGN_FLOW_DB_PATH: str = "data/foreign_flow/isyatirim.db"
FOREIGN_FLOW_STALE_HOURS: int = 48           # screener T+1; >48h → sinyal dışı (parquet fallback)
FOREIGN_FLOW_MIN_HISTORY_DAYS: int = 2       # gün-1 seed (today + 30g-önce) → change_30d çalışır
# İş Yatırım criterion 45 (1 aylık değişim) ZATEN puan (pp) cinsinden — canlı
# doğrulandı (örn. -0.02 = -0.02 pp; bps degil). Bu yüzden bölme gerekmez.
FOREIGN_FLOW_CHANGE_UNIT_DIVISOR: float = 1.0

# =============================================================================
# L5c BIST DATASTORE AYLIK YABANCI ISLEM (D-129, SPEC_FOREIGN_MONTHLY_DATASTORE_1)
# BIST Datastore "Foreign Investor Transactions" aylik .xls (RR-005 s2). Net
# yabanci USD akisinin son aylardaki trendi L5'te fallback tier olur:
# precedence custody -> foreign_flow -> foreign_monthly -> parquet.
# =============================================================================
FOREIGN_MONTHLY_DB_PATH: str = "data/bist_datastore/foreign_monthly.db"
FOREIGN_MONTHLY_LOOKBACK_MONTHS: int = 3      # trend penceresi (son N ay net_usd)
FOREIGN_MONTHLY_ENTRY_SCORE: float = 70.0     # net_usd trend artis -> giris
FOREIGN_MONTHLY_EXIT_SCORE: float = 30.0      # net_usd trend azalis -> cikis

# --- Is Yatirim Aciga Satis PDF Parser (D-132) ---
# Kaynak: arastirma.isyatirim.com.tr gunluk PDF raporu (robots-safe).
# NOT: SPK yasagi nedeniyle short_ratio veri var ama sinyal agirligi
# yakin vadede 0'a yakin kalir; veri toplama altyapisi hazir tutulur.
SHORT_INTEREST_PDF_BASE_URL: str = (
    "https://arastirma.isyatirim.com.tr/wp-content/uploads/{YYYY}/{MM}/"
    "Aciga_Satis_Raporu_{DDMMYYYY}.pdf"
)
SHORT_INTEREST_CACHE_DIR: str = "data/cache"
SHORT_INTEREST_CACHE_FILE_TPL: str = "isyatirim_short_interest_{YYYYMMDD}.json"
SHORT_INTEREST_FETCH_TIMEOUT_SEC: int = 30
SHORT_INTEREST_STALE_DAYS: int = 3            # cache gecerlilik suresi (gun)

# --- BIST DataStore Client (D-130) ---
DATASTORE_SESSION_FILE: str = "datastore_session.json"
DATASTORE_SESSION_MAX_AGE_DAYS: int = 25
DATASTORE_PRODUCT_FOREIGN: int = 3153
DATASTORE_PRODUCT_SHORT: int = 3155
DATASTORE_PRODUCT_PRICES: int = 3156
DATASTORE_RATE_LIMIT_SEC: float = 2.0

# --- BIST50 ticker universe (D-116, quarterly review) ---
# Kaynak: BIST 50 endeksi Mayıs 2026 kompozisyonu. Her çeyrek dönemde BIST web
# sitesinden güncellenmeli. NOT: SPEC'teki taslakta "TKFEN" iki kez geçiyordu;
# duplikasyon kaldırıldı → 49 unique ticker (50. üye doğrulanınca eklenecek).
CUSTODY_BIST50_TICKERS: tuple[str, ...] = (
    "AKBNK", "AKSEN", "AEFES", "ARCLK", "ASELS",
    "BIMAS", "CCOLA", "DOHOL", "EREGL", "ENERY",
    "ENKAI", "FROTO", "GARAN", "HALKB", "ISCTR",
    "KCHOL", "KRDMD", "LOGO",  "MGROS", "ODAS",
    "PETKM", "PGSUS", "SAHOL", "SISE",  "TAVHL",
    "THYAO", "TKFEN", "TOASO", "TTKOM", "TUPRS",
    "ULKER", "VAKBN", "YKBNK", "AKGRT", "ALBRK",
    "CIMSA", "ECILC", "EGEEN", "GUBRF", "IPEKE",
    "NETAS", "OTKAR", "QNBFB", "SKBNK", "SODA",
    "TCELL", "VESTL", "DEXYS", "AGHOL",
)

# =============================================================================
# ALPHA ATTRIBUTION & IC MEASUREMENT — DEC-015 (SPEC_ALPHA_INFRASTRUCTURE_1)
# Faz 1: measurement infrastructure only. No weight changes.
# References: Lopez de Prado (2018), Bailey & Lopez de Prado DSR (2460551),
#             Ulku & Ikizlerli BIST Foreign Flows (2012),
#             Bildik & Gulay BIST Contrarian (2007)
# =============================================================================

# IC forward return horizons (trading days)
IC_HORIZON_T1:  int = 1
IC_HORIZON_T5:  int = 5
IC_HORIZON_T10: int = 10   # D-139: cross-window matrix horizon (RR-010 Karar #3)
IC_HORIZON_T20: int = 20
IC_HORIZON_T60: int = 60

# Rolling IC window sizes (trading days)
IC_ROLLING_SHORT: int = 30
IC_ROLLING_MID:   int = 90
IC_ROLLING_LONG:  int = 252

# Minimum observations for Spearman IC computation
IC_MIN_OBSERVATIONS: int = 10

# Layer "investable" (active weight) gating
IC_INVESTABLE_MEAN_MIN:   float = 0.03   # mean(IC) >= 0.03
IC_INVESTABLE_TSTAT_MIN:  float = 2.0    # t-stat >= 2.0
IC_INVESTABLE_MONTHS_MIN: int = 6        # D-139: was 24; Cagan override (SPEC sec.6) -> 6 = ~126 trading days

# Layer watchlist / weight-halve / drop thresholds (Faz 2 reporting)
IC_WATCHLIST_TSTAT_MAX:   float = 1.5    # t-stat < 1.5 last 6m -> watch
IC_HALVE_CANDIDATE_TSTAT: float = 1.0    # t-stat < 1.0 last 12m -> halve candidate

# D-139 IC framework Faz 1 (SPEC_IC_FRAMEWORK_1 K-01). New analytics constants;
# all comments ASCII-only (cp1254 architecture-test safety, no capital S/G-cedilla).
# Bayesian weight calibration gating (RR-010 sec.2 B10, Karar #9-10; Faz 3 uses these)
IC_BAYESIAN_TAU_MIN_DAYS:  int = 60      # tau=0.20 entry threshold (first calibration)
IC_BAYESIAN_TAU_FULL_DAYS: int = 730     # tau=0.95 full independence from prior

# IC monitoring thresholds (RR-010 sec.2 B12; Faz 2 decay monitor uses these)
IC_DECAY_SLOPE_WARN:   float = -0.001    # 30/60/120d rolling IC slope -> warn
IC_DECAY_SLOPE_REVIEW: float = -0.002    # slope below this -> layer "review"
IC_FDR_ALPHA:          float = 0.10      # BH-FDR significance level
IC_FDR_M_TESTS:        int   = 12        # 6 layers x 2 primary horizons (T5, T20)

# New-layer admission hurdle (G-22, Harvey-Liu-Zhu 2016 RFS 29(1):5)
# A candidate layer must clear this t-stat before receiving any MASTER_WEIGHTS share.
# 3.0 corrects for multiple-comparison bias in factor discovery (vs naive 2.0).
IC_NEW_LAYER_TSTAT_HURDLE: float = 3.0

# Analytics data-path constants (runtime parquet/json; gitignored personal data)
IC_HISTORY_PATH:        str = "data/analytics/ic_history.parquet"
IC_WEIGHT_HISTORY_PATH: str = "data/analytics/weight_history.parquet"
DELISTED_TICKERS_PATH:  str = "data/analytics/delisted_tickers.json"
SECTOR_RETURNS_CACHE:   str = "data/analytics/sector_returns_cache.parquet"

# ----------------------------------------------------------------
# NAV Discount Tracker (D-143, RR-013 sec.5.2 + sec.8)
# KCHOL holding NAV iskonto z-skor sinyal esikleri.
# ASCII-only comments (cp1254 architecture-test safety).
# ----------------------------------------------------------------
NAV_ZSCORE_BUY:      float = 2.0    # z > +2.0 -> BUY
NAV_ZSCORE_BUY_LEAN: float = 1.0    # z > +1.0 -> BUY-LEAN
NAV_ZSCORE_TRIM:     float = -1.0   # z < -1.0 -> TRIM
NAV_ZSCORE_AVOID:    float = -2.0   # z < -2.0 -> AVOID
NAV_LOOKBACK_DAYS:   int   = 252    # 252 trading-day rolling window

# Hard thresholds (RR-013 sec.8 pre-set, absolute discount levels)
NAV_DISCOUNT_KADEME1_KAPATMA: float = 0.30  # iskonto < %30 -> trim/kapatma
NAV_DISCOUNT_KADEME2_ALIM:    float = 0.45  # iskonto > %45 -> ek alim

# NAV data paths (gitignored runtime artifacts, not committed)
NAV_HISTORY_PATH:   str = "data/analytics/nav_history.parquet"
HOLDINGS_YAML_PATH: str = "config/holdings.yaml"

# Brinson-Fachler benchmark
BRINSON_BENCHMARK: str = "equal_weight"   # "equal_weight" | "market_cap_weight"

# Volatility regime (rolling 20d realized vol, annualized %)
VOLATILITY_REGIME_LOW_MAX:  float = 15.0   # < 15% -> Low
VOLATILITY_REGIME_HIGH_MIN: float = 30.0   # > 30% -> High
# 15-30% -> Mid

# =============================================================================
# HMM REGIME-CONDITIONAL WEIGHTS (D-123, SPEC_HMM_REGIME_WEIGHTS_1)
# Dayanak: RR-003 §3 (CB-002 + CB-010 Aşama 1)
# Ref: Hamilton (1989), Asness/Moskowitz/Pedersen (2013), Lo (2004)
# BIST empirical: Senol 2020, Dogan&Bilge 2022, Wang et al. 2020
# =============================================================================

ENABLE_HMM_WEIGHTS: bool = False   # True → daily_update.py aktive eder; env var override mümkün

# GaussianHMM model hyperparameters
HMM_N_COMPONENTS: int    = 3            # BULL / NEUTRAL / BEAR
HMM_COVARIANCE_TYPE: str = "full"       # 3×3 full covariance matrix
HMM_N_ITER: int          = 500          # EM iteration upper bound
HMM_TOL: float           = 1e-4         # EM convergence tolerance
HMM_RANDOM_STATE: int    = 42           # reproducibility

# Walk-forward retrain schedule
HMM_WALK_FORWARD_WINDOW_MONTHS: int = 36   # rolling train window (3 years)
HMM_RETRAIN_INTERVAL_DAYS: int      = 30   # retrain when model older than this
HMM_MIN_TRAIN_DAYS: int             = 252  # minimum samples required (1 year)
HMM_PREDICT_MIN_DAYS: int           = 30   # Viterbi sequence minimum length

# Storage
HMM_MODEL_PATH: str = "data/hmm/regime_model.pkl"

# Feature definition (3-dim observation vector)
# [0] bist_log_return  [1] roll_vol_20d (annualized)  [2] usdtry_log_change
HMM_FEATURE_NAMES: tuple[str, ...] = ("bist_log_return", "roll_vol_20d", "usdtry_log_change")
HMM_VOL_LOOKBACK: int = 20   # rolling vol window in trading days

# Regime-conditional weight tables — Σ = 1.00 each; keys == MASTER_WEIGHTS.keys()
# D-154: L6/risk removed from all tables (renormalized by dividing each by Σ_ex_risk).
# BULL: momentum (L1) + smart money (L5) lead; macro (L2) less marginal in bull
# Original ex-risk Σ = 0.98; each value divided by 0.98.
HMM_WEIGHTS_BULL: dict[str, float] = {
    "technical":   round(0.32 / 0.98, 10),  # L1 ↑ momentum premium peaks in bull (Asness et al. 2013)
    "macro":       round(0.17 / 0.98, 10),  # L2 ↓ already supportive background in bull
    "kap":         round(0.27 / 0.98, 10),  # L3    corporate events always informative
    "sentiment":   round(0.10 / 0.98, 10),  # L4    suspended (confidence=0), kept for activation
    "smart_money": round(0.12 / 0.98, 10),  # L5 ↑ institutional flows reliable in bull
    # risk/L6: removed D-154
}  # Σ = 1.00

# NEUTRAL: identical to MASTER_WEIGHTS (architecture-tested invariant)
HMM_WEIGHTS_NEUTRAL: dict[str, float] = {
    "technical":   round(0.25 / 0.97, 10),  # D-154: mirrors new MASTER_WEIGHTS
    "macro":       round(0.20 / 0.97, 10),
    "kap":         round(0.30 / 0.97, 10),
    "sentiment":   round(0.12 / 0.97, 10),
    "smart_money": round(0.10 / 0.97, 10),
    # risk/L6: removed D-154
}  # Σ = 1.00  — must equal MASTER_WEIGHTS (test_architecture.py enforces this)

# BEAR: macro (L2) dominant; technical (L1) reduced (false bullish risk in bear)
# Original ex-risk Σ = 0.94; each value divided by 0.94.
HMM_WEIGHTS_BEAR: dict[str, float] = {
    "technical":   round(0.15 / 0.94, 10),  # L1 ↓↓ oversold bounces produce false bullish signals
    "macro":       round(0.30 / 0.94, 10),  # L2 ↑↑ macro dominant; CDS+USDTRY+TCMB critical
    "kap":         round(0.32 / 0.94, 10),  # L3 ↑  corporate disclosures early warning in bear
    "sentiment":   round(0.07 / 0.94, 10),  # L4 ↓  noisy in bear environment
    "smart_money": round(0.10 / 0.94, 10),  # L5    monitoring institutional exits
    # risk/L6: removed D-154
}  # Σ = 1.00

# Signal log storage paths
SIGNAL_LOG_BASE_PATH:   str = "data/signal_logs"
RETURNS_LOG_PATH:       str = "data/signal_logs/returns.parquet"
UNIVERSE_SNAPSHOT_PATH: str = "data/universe_snapshots"
IC_CACHE_PATH:          str = "data/analytics/ic_cache.parquet"

# =============================================================================
# VOL TARGETING + SOFT DD GATE (D-147, RR-016 §6.3)
# Gözlem modu Faz 1 — pozisyon kararına ETKİ YOK.
# Dayanak: Moreira & Muir (2017), Harvey et al. (2018), RR-016 §5–6.
# =============================================================================
PORTFOLIO_TARGET_VOL_ANNUAL: float = 0.15   # Bridgewater Pure Alpha I tarzı hedef
VOL_LOOKBACK_DAYS: int = 20                 # Birincil lookback (hızlı reaksiyon)
VOL_LOOKBACK_DAYS_CHECK: int = 60           # İkincil kontrol (stabil ama gecikmeli)
VOL_SCALAR_CAP: float = 1.50               # vol_scalar üst sınırı (kaldıraç kısıtı)
VOL_SCALAR_FLOOR: float = 0.20             # vol_scalar alt sınırı (COVID-seviye vol)
DD_SOFT_THRESHOLD: float = 0.05            # DD < %5  → dd_scalar = 1.00
DD_MID_THRESHOLD: float = 0.10             # DD < %10 → dd_scalar = 0.50
DD_HARD_THRESHOLD: float = 0.15            # DD < %15 → dd_scalar = 0.25; ≥ → 0.0
MAX_SINGLE_VOL_CONTRIB: float = 0.40       # Tek hisse vol katkısı üst sınırı (Risk Parity Lite)

# --- Backtest Kelly + Position constants (D-149c, RR-018 §8.2) ---
KELLY_WIN_PROB_BASE: float = 0.50            # composite=50 → p=0.50 (neutral)
KELLY_WIN_PROB_SLOPE: float = 0.005          # composite=100 → p=0.75; composite=0 → p=0.25
BACKTEST_KELLY_VIX_THRESHOLD: float = 25.0  # VIX bu eşiğin üstünde → haircut uygulanır
BACKTEST_KELLY_VIX_HAIRCUT: float = 0.75    # Yüksek VIX'te Kelly fraksiyonu çarpanı
BACKTEST_MAX_POSITION_FRAC: float = 0.05    # Tek pozisyon maksimum portföy oranı

# --- BIST100 MA Trend Scalar (D-163) ---
BIST_TREND_SCALAR_BULL:    float = 1.25  # price > MA20 > MA50 (confirmed uptrend)
BIST_TREND_SCALAR_NEUTRAL: float = 1.00  # price > MA50 only (weak uptrend / normal)
BIST_TREND_SCALAR_BEAR:    float = 0.75  # price < MA50 (downtrend, reduce size)
