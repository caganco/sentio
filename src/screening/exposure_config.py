"""D-187 Dürüst-Benchmark + Maruziyet-Rejimi Ayrım Testi -- Stage 0 frozen params.

Motivation: D-185/186 showed no entry-alpha. Dogrulama-agent identified a blind
spot: maruziyet-rejimi (equity<->TLREF switch) was adopted with ZERO testing.
D-187 applies the same discipline: base-allocation (static, no prediction) vs
active-timing (regime signal) SEPARATELY, measured against an honest "dumb barbell"
benchmark in REAL + post-cost terms.

These are MEASUREMENT params (not thresholds.py constants). Frozen at Stage 0
via dated commit; MUST NOT change after results are seen. Post-hoc relaxation
is FORBIDDEN. N-lock: STATIC_EQUITY_RATIOS is the only "parameter sweep" -- it
is pre-registered and frozen here.

Decision rule (DEC-045):
  S-A: best static ratio beats B1(TLREF) + B5(TUFE) in real terms -> base-alloc VALUABLE
  S-B: regime-switcher beats static barbell (B2/best-S-A) + random-switch null >95pctile
       in real terms -> active timing EARNS its place. Otherwise only S-A kept.
Post-hoc relaxation FORBIDDEN: no 'disinflation -> full-period', no threshold drop.
"""
from __future__ import annotations

from src.screening.trend_config import INFLATION_REGIMES

D187_CONFIG_VERSION = "exposure-d187-v1"

# ---------------------------------------------------------------------------
# Data window (consistent with D-185/D-186)
# ---------------------------------------------------------------------------
EXPOSURE_START = "2019-01-01"
EXPOSURE_END   = "2026-04-30"

# TLREF note (D-187 live-data correction): TP.BISTTLREF.KAPANIS is the official
# BIST TLREF RETURN INDEX (already compound-grown; monotone-increasing
# 1573->5827 over 2019-2026), NOT a rate. It is used DIRECTLY as the cash-park
# growth series -- NO /365 conversion (that would double-compound). The separate
# TP.BISTTLREF.ORAN (~46%) is the instantaneous rate; not used here. All
# comparisons use this index series, apples-to-apples with XU100 price + TUFE index.
TLREF_EVDS_SERIES   = "TP.BISTTLREF.KAPANIS"  # RR-021; return-index (not rate)
TUFE_EVDS_SERIES    = "TP.FG.J0"               # D-186 confirmed active
USDTRY_EVDS_SERIES  = "TP.DK.USD.A"            # faz0b fx snapshot

XU100_YFINANCE_SYMBOL = "XU100.IS"
GOLD_YFINANCE_SYMBOL  = "GC=F"                 # USD/oz futures

# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
# B1: 100% TLREF compound-growth (real competitor at ~40% nominal)
# B2: Static barbell 50/50 XU100+TLREF, monthly rebalance (the "dumb" baseline)
# B3: 100% XU100 price-index (dividend-free; equity-side caveat below)
# B4: Gold TL/gram (DIAGNOSTIC only -- not in decision rule; debasement check)
# B5: TUFE compound (real-zero line)
# XU100 caveat: yfinance XU100.IS is price-only (no dividends ~2-4%/yr).
# Equity side is DISADVANTAGED ~2-4%/yr vs true total-return. If S-A/S-B
# PASS with this handicap -> STRONGER result. If FAIL -> result is conservative
# but not over-penalised (real failure). Report states this explicitly.
BENCHMARKS = ("B1_TLREF", "B2_BARBELL", "B3_XU100", "B4_GOLD_DIAG", "B5_TUFE")
DECISION_BENCHMARKS = ("B1_TLREF", "B2_BARBELL", "B5_TUFE")  # B4 diagnostic only

# ---------------------------------------------------------------------------
# S-A: Static barbell -- base allocation (no prediction needed)
# ---------------------------------------------------------------------------
# N-LOCK: exactly these 3 ratios. No post-hoc additional ratios.
STATIC_EQUITY_RATIOS = (0.30, 0.50, 0.70)   # equity fraction; TLREF = 1 - equity
REBALANCE_FREQ = "monthly"                  # "monthly" or "quarterly"; frozen here

# Cost per round-trip rebalance leg (one-way allocation shift).
# Rebalancing incurs cost proportional to the drift from target (not full notional).
# Conservative assumption: full drift rebalanced at ROUND_TRIP_BPS cost.
REBALANCE_COST_BPS = 10   # very conservative for index-fund rebalance (10bps rt)

# ---------------------------------------------------------------------------
# S-B: Active timing (regime signal -- requires prediction -> null-test)
# ---------------------------------------------------------------------------
REGIME_MA_WINDOW = 200    # XU100 200-day MA; same as trend_config (consistency)
# Signal: close > MA AND MA rising (slope[MA]>0) -> equity; else -> TLREF.
# Look-ahead guard: signal computed at t-close, position applies from t+1-open.
# Cost per switch (full notional moves between equity and TLREF).
SWITCH_COST_BPS = 50      # RR-038 calibrated round-trip (same as trend test)

# ---------------------------------------------------------------------------
# Random-switch null (for S-B significance)
# ---------------------------------------------------------------------------
RANDOM_SWITCH_SEED      = 12345
RANDOM_SWITCH_NRESAMPLES = 1000

# ---------------------------------------------------------------------------
# Significance
# ---------------------------------------------------------------------------
SIG_BLOCK = 21       # block-bootstrap block (same as D-186, ~1 month)
SIG_N_BOOT = 2000
SIG_SEED   = 12345

# ---------------------------------------------------------------------------
# Decision rule DEC-045 (FROZEN -- no post-hoc relaxation)
# ---------------------------------------------------------------------------
# S-A PASSES if: best STATIC_EQUITY_RATIOS real annual return > B1_TLREF real
#   AND > B5_TUFE real (i.e., equity adds real value over pure cash/inflation).
# S-B PASSES if: S-B real annual return > best_S-A real AND S-B beats random-
#   switch null at >= DECISION_RANDOM_PCTILE_MIN.
DECISION_RANDOM_PCTILE_MIN = 0.95
# Disinflation slice is reported SEPARATELY (most current regime).
DECISION_SLICE = "disinflation"


def decision_slice_window() -> tuple[str, str]:
    for label, lo, hi in INFLATION_REGIMES:
        if label == DECISION_SLICE:
            return lo, hi
    raise ValueError(f"{DECISION_SLICE} not in INFLATION_REGIMES")
