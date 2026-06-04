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

# Backtest entry gatekeeping — kriz esikleri (D-166: L2 binary gate kaldirildi)
# Macro Gate V2 (0.3x-1.0x scaling) dusuk-makro gunleri yonetiyor; sadece gercek krizde block.
BACKTEST_MACRO_CRISIS_VIX: float = 35.0           # VIX > 35 = panic kriz, entry block
BACKTEST_MACRO_CRISIS_USDTRY_SPIKE: float = 0.03  # USDTRY +%3/gun = EM outflow krizi, entry block

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

# --- BIST DataStore ucretsiz-edinme otomasyonu (D-130b) ---
# Sepet (basket) tamamen client-side; sunucuya giden tek sey checkout POST'u.
# Ucretsiz urunler POST /api/add-library (vPosInfo=null) -> HTTP 204 ile
# dogrudan kutuphaneye eklenir; sepet/odeme UI'i baypas edilir.
DATASTORE_LIBRARY_PAGE_SIZE: int = 100      # /api/library sayfa boyutu (tum sayfalar gezilir)
DATASTORE_CATALOG_PAGE_SIZE: int = 100      # /api/product-type/{id}/products sayfa boyutu
DATASTORE_ADD_LIBRARY_BATCH_SIZE: int = 20  # add-library tek istekte urun sayisi (cart-size bug'ini yener)
DATASTORE_SENDER_APP: str = "DataStore"     # add-library / payment senderApp alani
# add-library Customer DTO B2C-profil'in alt-kumesi; FAIL_ON_UNKNOWN ile bilinmeyen
# alanlari 400 reddeder. Profil'den gelen ama add-library'nin tanimadigi alanlar atilir.
DATASTORE_ADD_LIBRARY_CUSTOMER_DROP_FIELDS: tuple[str, ...] = ("surName",)

# --- BIST DataStore Archive (D-199) ---
# Fazli veri-edinme + arsiv. Ham payload gitignore; yalniz _manifest.json commit.
DATASTORE_ARCHIVE_ROOT: str = "data/bist_datastore_archive"
DATASTORE_ARCHIVE_MANIFEST: str = "_manifest.json"
DATASTORE_PRODUCT_PRICES_DAILY: int = 3196        # PP_GUNSONUFIYATHACIM.M.* gunluk EOD CSV
DATASTORE_PRODUCT_INDEX_COMPONENTS: int = 3184    # exsrk{YYYY}.zip yillik endeks bilesimi
DATASTORE_PRODUCT_DIVIDENDS: int = 100462         # temettu
DATASTORE_PRODUCT_PRICES_WEEKLY: int = 3156       # PP_HAFTALIKOZET.W.* haftalik ozet
DATASTORE_PRODUCT_FUND_RATIOS_A: int = 100464     # temel oranlar A
DATASTORE_PRODUCT_FUND_RATIOS_B: int = 100465     # temel oranlar B
DATASTORE_PRODUCT_VIOP: int = 3208                # VIOP
DATASTORE_PRODUCT_CORP_ACTION_A: int = 100460     # sermaye artirim/ruchan A
DATASTORE_PRODUCT_CORP_ACTION_B: int = 100461     # sermaye artirim/ruchan B
DATASTORE_PRODUCT_CORP_ACTION_C: int = 100471     # sermaye artirim/ruchan C
DATASTORE_ARCHIVE_LAYOUT: dict[int, str] = {
    3153: "foreign_flow", 3196: "prices_official", 3184: "index_components",
    100462: "dividends", 3156: "prices_weekly",
    100464: "fundamental_ratios", 100465: "fundamental_ratios",
    3155: "short_selling", 3208: "viop",
    100460: "corporate_actions", 100461: "corporate_actions", 100471: "corporate_actions",
}
DATASTORE_ARCHIVE_FREQUENCY: dict[int, str] = {
    3153: "monthly", 3196: "daily-packaged-monthly", 3184: "yearly",
    100462: "event", 3156: "weekly", 100464: "quarterly", 100465: "quarterly",
    3155: "daily", 3208: "daily", 100460: "event", 100461: "event", 100471: "event",
}
DATASTORE_PHASE_1: tuple[int, ...] = (3153, 3196, 3184)
DATASTORE_PHASE_2: tuple[int, ...] = (100462, 3156, 100464, 100465)
DATASTORE_PHASE_3: tuple[int, ...] = (3155, 3208, 100460, 100461, 100471)
DATASTORE_SURVIVORSHIP_PROBE_TYPE: int = 3196
DATASTORE_SURVIVORSHIP_KNOWN_DELISTED: tuple[str, ...] = ("KOZAA", "KOZAL", "IPEKE", "TRALT")

# --- D-200 Clean Universe (survivorship-clean adjusted panel) ---
CLEAN_UNIVERSE_ROOT: str = "data/clean_universe"
CLEAN_UNIVERSE_ADJ_PRICES: str = "adjusted_prices_2019_2026.parquet"
CLEAN_UNIVERSE_PIT_MEMBERSHIP: str = "pit_membership_2019_2026.parquet"
CLEAN_UNIVERSE_META: str = "_meta.json"
CLEAN_UNIVERSE_START: str = "2019-01-01"
CLEAN_UNIVERSE_END: str = "2026-05-31"
CLEAN_UNIVERSE_CORP_ACTION_TYPES: tuple[int, ...] = (100460, 100461, 100471)
CLEAN_UNIVERSE_PRICE_TYPE: int = 3196
COL_3196_DATE: int = 0
COL_3196_TICKER: int = 1
COL_3196_BIST100: int = 11
COL_3196_BIST30: int = 12
COL_3196_CA_CODE: int = 14
COL_3196_CLOSE: int = 22
COL_3196_VWAP: int = 27
COL_3196_VALUE_TL: int = 28
COL_3196_VOLUME: int = 29
COL_3196_EXPECTED_COUNT: int = 52
CLEAN_UNIVERSE_DIVIDEND_WITHHOLDING: float = 0.15
# D-202 LAYER-3 self-validate tolerance: a price-implied corporate-action factor is
# accepted when it matches the raw 3196 close jump within this fraction. Set to 2% to
# allow for price-rounding on the official feed plus +/-1 trading-day ex-date drift
# between yfinance/col-14 calendars and the 3196 panel. FIXED pre-Stage-0; this value is
# NOT to be tuned post-hoc after seeing freeze results. Written (with rationale) into
# _meta.json for auditability.
CLEAN_UNIVERSE_SELF_VALIDATE_TOL: float = 0.02

# --- D-203 KESIN-TEST gate decision thresholds (single source per "tek kaynak") ---
# These are the FROZEN pass/fail thresholds for the 5-gate measurement of the three
# edge candidates (VALUE / EDGE-2 composite / 52wk-high) on the D-202 681-symbol clean
# universe. Decision constants live here; measurement GEOMETRY (lookbacks, regime
# splits, windows, snapshot hashes) lives in src/screening/d203_config.py. FIXED at
# Stage-0; NOT tuned after seeing results (measurement-only, optimization forbidden).
D203_GATE_NULL_PCTILE: float = 0.95      # gate-1: beat >=95th pctile fair random basket
D203_GATE_NW_T_MIN: float = 2.0          # gate-2: Newey-West HAC |t| >= 2.0
D203_GATE_COST_LOW_BPS: float = 20.0     # gate-5: still positive at 20bp per-turnover cost
D203_GATE_COST_HIGH_BPS: float = 100.0   # gate-5: still positive at 100bp per-turnover cost
D203_DAILY_RETURN_CLIP: float = 0.10     # daily return cap +/-10% (NOT broken D-200 +/-50%)
D203_LIQUIDITY_TERCILE: float = 1.0 / 3.0  # gate-4: liquid/mid/illiquid tercile split
D203_TOP_N: int = 15                     # fixed top-15 EW basket (no optimization path)

# --- D-204 hi52 STRES-TEST decision/cost constants (single source per "tek kaynak") ---
# D-203 found hi52 = GERCEK-EDGE (strongest). D-204 stress-tests deploy-readiness under
# REALISTIC per-stock cost (vs D-203 flat 20/100bp). MEASUREMENT-ONLY: these are FROZEN
# at Stage-0 and NOT tuned after seeing results. Cost MECHANICS live in
# src/screening/realistic_cost.py; stress GEOMETRY in src/screening/d204_config.py.
D204_LAMBDA_KYLE: float = 1.0            # Kyle impact coefficient -- FROZEN placeholder
#   (ballast-documented value; XU030-calibrated ~1.4-1.6). Calibration = optimization =
#   FORBIDDEN in D-204, so the ballast default 1.0 is frozen as-is.
D204_ROLL_WINDOW: int = 21               # Roll(1984) serial-cov rolling window (trading days)
D204_COMMISSION_PCT: float = 0.0         # Midas BIST equities = 0 commission (RR-015 Tier C)

# RR-015 sec.3.1 empirical BIST liquidity-tier ONE-WAY half-spreads (fraction) + the TL-ADV
# tier boundaries. Cross-check anchor for Roll (which can be noisy / floored to 0 on thin
# names). Monotone mega < large < mid < micro. Half-spread midpoints of the RR-015 ranges:
#   mega (KCHOL ~5B TL ADV, 0.05-0.08%) / large (TTKOM ~1B, 0.08-0.12%) /
#   mid (AKSEN, 0.20-0.35%) / micro (ENERY ~150M, 0.30-0.50%).
D204_TIER_MEGA_ADV_TL: float = 2_000_000_000.0
D204_TIER_LARGE_ADV_TL: float = 500_000_000.0
D204_TIER_MID_ADV_TL: float = 100_000_000.0
D204_TIER_MEGA_HALF_SPREAD: float = 0.00065   # ~0.065%
D204_TIER_LARGE_HALF_SPREAD: float = 0.0010   # ~0.10%
D204_TIER_MID_HALF_SPREAD: float = 0.00275    # ~0.275%
D204_TIER_MICRO_HALF_SPREAD: float = 0.0040   # ~0.40%

# Deploy hurdle (EKLEME-B, Cagan): NOT an arbitrary number. Project principle is
# "real > max(TUFE, TLREF)". hi52 returns are already TUFE-deflated (real), so the hurdle
# is the mean monthly REAL TLREF carry (deposit/repo real return) -- "does liquid-tercile
# hi52 after realistic cost beat holding a TLREF deposit?". DERIVED + FROZEN from the
# frozen TLREF return-index (exposure_d187_tlref) deflated by frozen TUFE over the
# TLREF-available window 2022-07-01..2026-04-30 (TLREF index begins 2022-07; n=45 months):
# mean monthly real carry = +0.000222. The engine RECOMPUTES this from the snapshots and
# asserts it matches (reproducibility guard, like the price content-hash assert).
D204_DEPLOY_MIN_LIQUID_NET: float = 0.000222  # +0.0222%/mo real (TLREF deposit hurdle)

# Verdict safety margin: DEPLOY-ADAY requires the breakeven cost to be at least this
# multiple of the REALIZED realistic cost (breakeven >> cost, not breakeven ~ cost).
# Frozen at Stage-0 (the "breakeven >> gerceklci-maliyet" rule), not tuned post-hoc.
D204_BREAKEVEN_SAFETY_MULT: float = 2.0

# --- D-205 hi52 LIKIT-ONCE decision constants (single source per "tek kaynak") ---
# D-204 found hi52 = GERCEK-ama-tradeable-DEGIL on the naive prototype (252g + top15 + EW +
# monthly + no-filter): realized realistic cost ~340bp > breakeven ~302bp, root cause ~88%
# turnover x ~98% microcap (median picked ADV 1.65M-TL). NRR-005 showed the root cause is the
# COST-RATE (microcap), not the turnover-LEVEL, and that the hi52 SIGNAL lives in liquid names
# (liquid-pool rank-IC 0.048 ~ full-universe 0.047). D-205 attacks the cost-rate: restrict the
# UNIVERSE to absolute-liquid names FIRST (signal UNCHANGED), then apply hi52. The threshold
# below is FROZEN at Stage-0 on POOL-FEASIBILITY + Cagan-deploy grounds (NRR-006 ADIM-1, EDGE
# NOT seen) -- NOT tuned after seeing any edge result (post-hoc selection FORBIDDEN). D-205 is
# the 3rd and FINAL hi52 measurement (N<=3). Cost MECHANICS reuse D204_* (realistic_cost.py).
D205_LIQUID_ADV_MIN_TL: float = 1.0e7    # trailing-63d-median ADV floor for the liquid universe
#   FROZEN (NRR-006 ADIM-1, edge-unseen). Rationale (3-criteria, edge-not-measured): (1) Cagan
#   deploy -- 20K-TL order = ADV %0.08 at the 24.9M median liquid ADV (impact-negligible);
#   (2) N=15 feasibility -- pool min 44 / median 78, top-15 feasible 100% of rebalances, healthy
#   >=30 100%; (3) real liquidity -- median liquid ADV 24.9M = ~15x the microcap 1.65M trap.
#   2e6 leaves a still-thin pool (median ADV 6.4M); 5e7+ makes the universe too narrow (N=15-fail).
D205_LIQUID_ADV_TRAILING_DAYS: int = 63  # ADV trailing window (== D203/D204 liquidity window)
D205_SUBTIER_SPLIT: float = 0.5          # gate-4: upper/lower-half ADV split within liquid universe

# --- D-206 NAV-iskonto-Z mean-reversion decision constants (single source per "tek kaynak") ---
# Cross-sectional factor selection is EXHAUSTED (hi52/lowvol63/value all closed). D-206 is a
# NEW TIME-SERIES paradigm: per-holding NAV-discount mean-reversion (Pontiff 1995 CEF premia).
# Each holding has its OWN discount time-series; high discount-Z (cheap) -> positive forward
# return. MEASUREMENT-ONLY: FROZEN at Stage-0, NOT tuned post-hoc. The discount-Z GEOMETRY +
# holding composition live in src/screening/d206_config.py + docs/yol1/STAGE0_d206.json. Cost
# MECHANICS reuse D204_* (realistic_cost.py). N<=3 (NAV first round = 1).
D206_TRAILING_WINDOW_MONTHS: int = 36    # per-holding trailing mean/std window for discount-Z
#   FROZEN (~3x the 7.7-10.3mo CEF half-life -> stable trailing moments). NO 24/48/60 sweep.
D206_TRAILING_MIN_PERIODS: int = 24      # min months before a discount-Z is defined (warmup)
D206_PRIMARY_HORIZON_MONTHS: int = 6     # PRIMARY forward-return horizon (straddles half-life)
D206_SECONDARY_HORIZONS: tuple[int, ...] = (1, 3)  # reported as context only, NEVER gated
D206_PUBLICATION_LAG_MONTHS: int = 1     # subsidiary mktval t-1 lag (look-ahead-safe NAV leg)
D206_GATE_NW_T_MIN: float = 2.0          # gate-2: |t| >= 2.0 (Driscoll-Kraay PRIMARY; T>>N)
D206_GATE_NULL_PCTILE: float = 0.95      # gate-3: real beta beats >=95th pctile circular-shift null
D206_GATE_SAME_SIGN_FRAC: float = 0.80   # gate-2: >= 80% of holdings share the positive sign
D206_NULL_N_RESAMPLES: int = 2000        # circular-shift null draws (gate-3)
D206_NULL_SEED: int = 12345              # reproducible null/bootstrap seed (D203/204 idiom)
D206_WILD_BOOT_N: int = 2000             # wild-cluster bootstrap draws (gate-2 corroboration)
D206_REGIME_PRIMARY: str = "2022-01-01"  # gate-4 primary split (high-inflation onset)
D206_REGIME_LOWINFL_END: str = "2017-01-01"  # gate-4: the genuine 2009-2016 low-inflation regime
D206_STRATEGY_ENTRY_Z: float = 1.0       # gate-5 strategy: long holding when discount-Z >= +1.0
D206_STRATEGY_EXIT_Z: float = 0.0        #   exit when discount-Z reverts to <= 0 (hysteresis)
#   FROZEN economic rule ("buy >1std cheap, exit at the mean"), NOT an optimized parameter; the
#   G1-G4 gates are regression-based (threshold-free). Entry/exit only drives the G5 turnover read.
D206_FIDELITY_MIN_CORR: float = 0.95     # FIDELITY-GUARD: mktval-implied-TR vs frozen adjusted_close
#   monthly-return correlation (per core holding, 2019-2026 overlap) must be >= this, else the
#   engine RAISES (the mktval-implied total-return proxy is invalid -> test STOPS). This validates
#   using the mktval-implied TR uniformly across 2009-2026 (corp-action archive is empty -> no
#   adjusted prices pre-2019; mktcap is continuous through splits/bonus, dividends added via net_div).
D206_FIDELITY_MAX_MAE: float = 0.03      # FIDELITY-GUARD: monthly-return mean-abs-error ceiling

# --- D-207 realistic_cost RE-CALIBRATION constants (single source per "tek kaynak") ---
# NRR-010 (demo-pa/NRR-010-maliyet-teshis.md) diagnosed the D-204/D-205 cost model as SISIK
# (inflated ~12-25x on liquid names): (1) a unit double-count (round_trip = 2*full_Roll_S,
# but the round-trip spread cost is S itself), and (2) the 21-day Roll measures VOLATILITY not
# spread (Monte-Carlo: roll21 ~ 0.47*sigma even at literally-zero true spread). D-207 corrects
# the SHARED cost model anchored to OBSERVED reality (EOD quoted spreads), NOT to any edge
# outcome (calibration = optimization-risk; post-hoc tuning FORBIDDEN; frozen edge-blind at
# docs/yol1/D207_CALIBRATION.json). The D204_* block above is KEPT as the historical record;
# the LIVE cost mechanics (realistic_cost.py) now read these D207_* values.
#
# FIX-2 spread hierarchy per (date,name): EOD quoted (observed, vol-robust) -> longer-window
# Roll fallback (de-inflated vs 21d) -> re-scaled tier floor (ADV-only last resort). The quoted
# panel is built locally from the archive (src/screening/quoted_spread.py) and INJECTED into the
# cost harness (CI-safe: tests inject synthetic panels / None; no archive dependency in CI).
D207_QUOTED_WINDOW: int = 63             # trailing trading-day window for the median quoted spread
#   (matches the D203/D204/D205 63-day liquidity window family). Point-in-time, no look-ahead.
D207_QUOTED_MIN_COVERAGE: int = 21       # min valid quote-days required in the window, else "no quote"
#   (>=1 trading month of observed quotes -> a stable median; thin/halted names fall through to Roll).
D207_FALLBACK_ROLL_WINDOW: int = 252     # long Roll window for the FALLBACK leg (no quoted available)
#   FROZEN edge-blind. NRR-010 MC: long-window Roll ~25bp vs 21d ~106bp on the same names -> the long
#   window de-inflates the vol-bias of the asymmetric max(-cov,0) truncation. Residual vol-bias
#   remains (honest caveat: only affects no-quote names, e.g. 2019-Q1 / illiquid). The Kyle-impact
#   sigma window stays D204_ROLL_WINDOW (21) -- impact is FROZEN, D-207 corrects only the SPREAD leg.

# FIX-3: re-scaled liquidity-tier ONE-WAY half-spreads (the LAST-RESORT floor when neither a
# quoted spread NOR a fallback Roll is available). The D204_TIER_* ladder (MEGA>=2e9 TL, half
# 6.5-40bp) was DOUBLY wrong: (a) the ADV boundaries were unreachable on BIST so EVERY name
# misclassified as MID/MICRO, and (b) the half-spreads were ~4-6x inflated. D-207 re-derives the
# ladder EDGE-BLIND from OBSERVED quoted spreads bucketed by the clean_universe ADV distribution
# (demo-pa/d207/derive_d207_tiers.py; provenance frozen in docs/yol1/D207_CALIBRATION.json).
# KEY OBSERVED FACT: the EOD quoted FULL spread is ~FLAT ~11bp across the whole BIST liquidity
# spectrum (per-ADV-bucket medians MEGA 10.6 / LARGE 13.4 / MID 11.2 / MICRO 11.2 bp; n=439).
# Microcaps are NOT wider on the QUOTED-spread dimension -- their extra cost is market IMPACT
# (Kyle, which grows as ADV shrinks), NOT spread. So the re-scaled ladder is nearly flat by
# design (a faithful reflection of reality, NOT a steep micro penalty); the monotone gradient is
# a small conservative tie-breaker for the no-data fallback, kept within the observed [10.6,13.4]bp
# full-spread envelope. Boundaries are round BIST-reality cut points (edge-blind). Monotone
# mega < large < mid < micro (architecture invariant). The microcap COST-RATE that drove the
# D-204 root cause stays valid -- it flows through the Kyle impact term, which is UNCHANGED.
D207_TIER_MEGA_ADV_TL: float = 50_000_000.0    # >= 50M TL trailing ADV (genuine BIST megas)
D207_TIER_LARGE_ADV_TL: float = 20_000_000.0   # >= 20M TL
D207_TIER_MID_ADV_TL: float = 5_000_000.0      # >= 5M TL ; below = micro
# Half-spreads = observed bucket-median quoted FULL spread / 2, frozen VERBATIM from the
# edge-blind derivation (demo-pa/d207/d207_derivation.json, tier_half_spread_frozen_monotone).
# Raw bucket halves were 5.28 / 6.72 / 5.59 / 5.59 bp (LARGE's 13.4bp median is a noisy high vs
# the ~11bp rest); strict-monotone enforcement ratchets MID/MICRO just above LARGE -> the 6.82 /
# 6.92bp values below. The ratchet is a conservative (cost-up) tie-breaker, all within the
# observed [10.6,13.4]bp full envelope. Tier floor is LAST-RESORT (liquid names get quoted), so
# the exact value barely moves any liquid result; it only shapes the no-data microcap narrative.
D207_TIER_MEGA_HALF_SPREAD: float = 0.000528   # 5.28bp half = 10.6bp full (observed MEGA median)
D207_TIER_LARGE_HALF_SPREAD: float = 0.000672  # 6.72bp half = 13.4bp full (observed LARGE median)
D207_TIER_MID_HALF_SPREAD: float = 0.000682    # raw 5.59bp -> ratcheted monotone above LARGE
D207_TIER_MICRO_HALF_SPREAD: float = 0.000692  # raw 5.59bp -> ratcheted monotone above MID

# FIDELITY validity band (NOT an edge criterion): the corrected round-trip on liquid megas must
# land in this OBSERVED ground-truth band (incl. the frozen Kyle impact at lambda=1.0). Anchored
# to NRR-010's EOD-quoted (~7.5-13.7bp full) + RR-015's round-trip (17-25bp) -- NOT to my own
# derivation output (independent external anchor). The corrected model must reproduce ~11-26bp,
# vs the SISIK model's 271-509bp. This validates the de-inflation; it does NOT prove any edge.
D207_FIDELITY_BAND_LO_BPS: float = 7.0
D207_FIDELITY_BAND_HI_BPS: float = 35.0

# --- D-209: H2b TEMETTU-RUNUP re-test under D-207 corrected cost (MEASUREMENT-only) ---
# The H2b signal (dividend pre-ex run-up) was eliminated in the demo-goal lab under a FLAT
# 20/100bp-per-side cost, but was NEVER measured with the D-207 corrected per-stock realistic
# cost. D-209 re-runs the FROZEN demo-goal H2 signal (NO new definition) under the corrected
# cost and decides: still tradeable, or a significance wall like hi52? These constants are the
# FROZEN geometry of the two frozen demo-goal signal variants -- pre-registered in
# docs/yol1/STAGE0_d209.json BEFORE any result. NO optimization, NO grid-sweep.
# V1 (daily-churn basket, demo-goal h2b_runup_basket.py BIREBIR): a name is HELD on day t iff
# its dividend ex-date is 1..5 trading days ahead (window [-5,-1]); exit before ex -> no tax.
D209_HOLD_LO: int = -5                    # V1 run-up window low (5 trading days before ex)
D209_HOLD_HI: int = -1                    # V1 run-up window high (1 trading day before ex)
# V2 (low-turnover discrete capture = demo-goal H2 "RUNUP_capture" leg, BIREBIR): per (symbol,
# ex) event ONE round-trip, compound return over window [-10,-1] (10 trading days = "hold-10g"),
# EW-combined per ex-month, exit before ex. add_div=False (no dividend captured -> no tax).
D209_V2_HOLD_LO: int = -10                # V2 discrete-capture window low (10 trading days before ex)
D209_V2_HOLD_HI: int = -1                 # V2 discrete-capture window high (1 trading day before ex)
D209_EX_GAP_MIN: float = 0.005            # ex-date detection: tr_index_gross.pct - adj_close.pct > this
D209_NW_LAG: int = 5                       # Newey-West HAC lag for the daily relative series (V1)
D209_REGIME_SPLIT: str = "2022-01-01"     # pre/post regime split for sign-stability gate
# Liquid universe + cost windows REUSE the D205/D204 single-source constants (>=1e7 ADV floor,
# 63-day trailing median; D204_ROLL_WINDOW / D204_LAMBDA_KYLE / D207 quoted-primary cost).

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

# D-167: BIST decoupling bonus — global macro stresli ama BIST kendi trendinde
# Yalnizca global_score < 50 VE BIST100 > MA50 oldugunda aktif.
BIST_DECOUPLING_BONUS: float = 8.0

# ---------------------------------------------------------------------------
# D-211 (RR-Y1-002) -- foreign-flow -> forward TL-real index return.
# ADDITIVE block (Strangler): zero edit to existing constants. Decision
# thresholds frozen at STAGE0_d211.json BEFORE measurement. The cost leg
# REUSES D207_TIER_MEGA_HALF_SPREAD + D204_COMMISSION_PCT (read-only).
# ---------------------------------------------------------------------------
D211_NW_LAG: int = 6                  # Newey-West HAC Bartlett bandwidth (directive lag>=6)
D211_KEEP_NW_T_MIN: float = 2.0       # keep-bar[1]: |t| of primary slope
D211_SIGNAL_THRESHOLD: float = 0.0    # deployable leg: NF_pct(t-2) > 0 -> index long, else cash
D211_REGIME_SPLIT: str = "2022-01-01" # regime-stability split (A: 2019-21, B: 2022-26)
D211_LOOKAHEAD_LAG_MONTHS: int = 2    # ~6wk publication lag -> NF_pct(t-2) predicts return-month t
