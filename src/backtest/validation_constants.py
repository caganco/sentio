"""Backtest istatistiksel validation eşikleri ve sabitleri (D-150a).

src/signals/thresholds.py'den AYRI tutulur (domain separation).
Bu dosya src/ içinden sadece src/backtest/ tarafından import edilir.
Yalnızca stdlib + typing kullanır — başka src/ import YASAK.

Dayanak: SPEC_STATISTICAL_VALIDATION_1 §4.2; RR-018 §§5–7
"""
from __future__ import annotations

# ── Deployment Gates ─────────────────────────────────────────────────────────

DSR_THRESHOLD: float = 0.95    # Deflated Sharpe Ratio minimum (Bailey-LdP 2014)
PBO_THRESHOLD: float = 0.50    # Probability of Backtest Overfitting maksimum (LdP 2018)

# ── CPCV Parametreleri ────────────────────────────────────────────────────────

CPCV_N: int = 6          # Zaman dilim sayısı → C(6,2) = 15 path
CPCV_K: int = 2          # Test dilim sayısı per path
CPCV_MIN_PATHS: int = 15 # C(CPCV_N, CPCV_K) — hesap: math.comb(6, 2)

# ── Purged K-Fold Parametreleri ───────────────────────────────────────────────

PURGED_KFOLD_SPLITS: int = 5
PURGED_KFOLD_PURGE_DAYS: int = 10    # 5-günlük forward return × 2 güvenlik marjı
PURGED_KFOLD_EMBARGO_DAYS: int = 5   # Post-test leak koruması

# ── IID / Newey-West ──────────────────────────────────────────────────────────

NW_LAGS: int = 5   # Newey-West HAC lag sayısı (forward return window)

# ── MinBTL (Bailey-LdP 2014, RR-018 §6.1) ────────────────────────────────────

MIN_BACKTEST_DAYS: int = 553         # 2.21 yıl × 250 BIST trading günü
MIN_BACKTEST_YEARS: float = 2.21
RECOMMENDED_BACKTEST_DAYS: int = 750 # CPCV N=6 için konforlu minimum

# ── Kriz Dönemi Kapsaması ─────────────────────────────────────────────────────

CRISIS_COVERAGE_START: str = "2007-01-01"       # Kriz 2–7 kapsar
CRISIS_COVERAGE_START_FULL: str = "2000-01-01"  # Kriz 1 dahil (opsiyonel)
RECOMMENDED_START_DATE: str = "2007-01-01"

CRISIS_WINDOWS: dict[str, tuple[str, str]] = {
    "2001_banking":   ("2000-11-01", "2002-01-01"),
    "2008_gfc":       ("2008-01-01", "2009-04-01"),
    "2013_taper":     ("2013-05-01", "2013-10-01"),
    "2018_tl_crisis": ("2018-07-01", "2019-01-01"),
    "2020_covid":     ("2020-02-01", "2020-05-01"),
    "2021_tcmb":      ("2021-03-01", "2022-02-01"),
    "2023_quake":     ("2023-02-01", "2023-08-01"),
}

# ── Pass/Fail Esikleri (D-161) ────────────────────────────────────────────────
# TR %42 RF ortaminda Sharpe >= 1.0 matematiksel olarak erisilemez (8 ayda +31%
# gerektirir). Period-adjusted excess return pozitif olmasi yeterli esik.
# DSR/PBO bu esiklerden bagimsiz — Newey-West Sharpe kullanir (statistical_validation.py).
SHARPE_PASS_THRESHOLD: float = 0.0    # pozitif excess return (TR yuksek RF ortami)
SHARPE_WARN_THRESHOLD: float = 0.5    # iyi performans
SHARPE_STRONG_THRESHOLD: float = 1.0  # mukemmel — uzun vadeli hedef

# Information Ratio: IR = mean(active_return) / std(active_return) * sqrt(252)
# active_return = portfolio_daily - benchmark_daily (BIST100)
IR_PASS_THRESHOLD: float = 0.3        # anlamli alpha vs benchmark
