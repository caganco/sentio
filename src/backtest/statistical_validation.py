"""DSR + PBO + MinBTL + Newey-West hesapları ve CPCV orchestration (D-150c).

BacktestEngine doğrudan import edilmez; factory callback pattern kullanılır.
metrics.calculate_sharpe() import edilir (DRY — kopyalama yasak).

Dayanak: SPEC_STATISTICAL_VALIDATION_1 §4.4; RR-018 §§5–7
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm  # Φ için

from src.backtest.metrics import calculate_sharpe  # DRY — kopyalama yasak
from src.backtest.validation_constants import (
    CPCV_K,
    CPCV_N,
    CRISIS_WINDOWS,
    DSR_THRESHOLD,
    MIN_BACKTEST_DAYS,
    NW_LAGS,
    PBO_THRESHOLD,
)

logger = logging.getLogger(__name__)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PathResult:
    """Tek CPCV path'in sonuçları."""

    path_id: int
    train_days: int
    test_days: int
    oos_sharpe_naive: float       # metrics.calculate_sharpe() (non-overlapping)
    oos_sharpe_nw: float          # sharpe_newey_west() (HAC düzeltmeli)
    oos_return_pct: float
    oos_max_drawdown_pct: float
    n_trades: int
    crisis_windows_covered: List[str]
    # Kritik: equity curve scope dışına çıkmadan önce sakla — DSR moment hesabı için
    oos_returns: np.ndarray = field(
        default_factory=lambda: np.array([0.0]),
        compare=False,
        repr=False,
    )


@dataclass
class ValidationResult:
    """CPCV + DSR + PBO + MinBTL tam validation sonucu."""

    # DSR
    dsr: float
    pass_dsr: bool              # dsr > DSR_THRESHOLD

    # PBO
    pbo: float
    pass_pbo: bool              # pbo < PBO_THRESHOLD

    # MinBTL
    actual_backtest_days: int
    min_btl_days_required: int
    pass_btl: bool              # actual >= required

    # CPCV istatistikleri
    n_paths: int
    paths_positive_sharpe: int
    sharpe_distribution: List[float]    # oos_sharpe_nw per path (sıralı)
    sharpe_mean: float
    sharpe_std: float
    sharpe_p25: float
    sharpe_median: float
    sharpe_p75: float

    # Deployment kararı
    deploy_ready: bool          # pass_dsr AND pass_pbo AND pass_btl
    failure_reasons: List[str]  # boş ise deploy_ready=True

    # Kriz coverage
    crisis_coverage: Dict[str, int]     # {crisis_name: paths_covering}

    # Path detayları — default'lu alanlar en sona
    path_results: List[PathResult] = field(default_factory=list)
    report_path: Optional[str] = None


# ── Core Matematik ────────────────────────────────────────────────────────────

def compute_dsr(
    sharpe_ratios: List[float],
    T: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    benchmark_sr: float = 0.0,
) -> float:
    """Deflated Sharpe Ratio — Bailey & López de Prado (2014).

    DSR = Φ(SR̂) burada:
      SR̂ = (SR_obs - SR_bm) × √(T-1) / √(1 - γ₃×SR_obs + (γ₄-1)/4×SR_obs²)

    Args:
        sharpe_ratios: CPCV path'lerin OOS Sharpe listesi (Newey-West)
        T: OOS trading günü sayısı (ortalama path uzunluğu)
        skewness: OOS return serisi skewness γ₃
        kurtosis: OOS return serisi kurtosis γ₄ (Gaussian = 3.0)
        benchmark_sr: Kıyaslama SR (konservatif = 0.0)

    Returns:
        DSR ∈ [0, 1]; >0.95 deployment gate'i
    """
    if not sharpe_ratios or T <= 1:
        return 0.0
    sr_obs = float(np.mean(sharpe_ratios))
    numerator = (sr_obs - benchmark_sr) * math.sqrt(T - 1)
    denominator_sq = (
        1.0 - skewness * sr_obs + ((kurtosis - 1.0) / 4.0) * sr_obs ** 2
    )
    if denominator_sq <= 0:
        return 0.0
    sr_hat = numerator / math.sqrt(denominator_sq)
    return float(norm.cdf(sr_hat))


def compute_pbo(oos_sharpe_list: List[float]) -> float:
    """Probability of Backtest Overfitting (konservatif frekans yaklaşımı).

    PBO = P(OOS Sharpe < 0) — tek konfigürasyon için CSCV logistic
    regresyon uygulanamaz; frekans bazlı konservatif hesap kullanılır.

    Returns:
        PBO ∈ [0, 1]; <0.50 deployment gate'i
    """
    if not oos_sharpe_list:
        return 1.0
    negative = sum(1 for s in oos_sharpe_list if s < 0)
    return negative / len(oos_sharpe_list)


def sharpe_newey_west(returns: np.ndarray, lags: int = NW_LAGS) -> float:
    """Newey-West HAC düzeltmeli Sharpe oranı.

    Non-overlapping primary Sharpe'a alternatif; DSR γ₃/γ₄ hesabında kullanılır.
    Formül: SR_NW = mean(r) / std_nw(r) × √252
    HAC varyans: Bartlett kernel, bandwidth = lags
    """
    if len(returns) < lags + 2:
        return 0.0
    mu = float(np.mean(returns))
    var_nw = float(np.var(returns, ddof=1))
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1)  # Bartlett kernel
        cov = float(np.mean(
            (returns[lag:] - mu) * (returns[:-lag] - mu)
        ))
        var_nw += 2.0 * weight * cov
    if var_nw <= 0:
        return 0.0
    return float(mu / math.sqrt(var_nw) * math.sqrt(252))


def min_btl_days(
    n_trials: int = 12,
    target_sr: float = 1.5,
    annual_factor: int = 250,
) -> int:
    """MinBTL (Bailey-LdP 2014) — trading gün cinsinden parametrik form.

    E[max SR_N] = (1-γ)×Φ⁻¹(1-1/N) + γ×Φ⁻¹(1-1/(N×e))
    MinBTL = (E[max SR_N] / target_sr)² × annual_factor

    Not: RR-018 §6.1 BIST düzeltmeli bağlayıcı değer = 553 gün (2.21 yıl).
    Bu fonksiyon parametrik formdur; validation_constants.MIN_BACKTEST_DAYS
    bağlayıcı değerdir.
    """
    gamma = 0.5772156649  # Euler-Mascheroni sabiti
    z1 = float(norm.ppf(1.0 - 1.0 / n_trials))
    z2 = float(norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
    e_max_sr = (1.0 - gamma) * z1 + gamma * z2
    return int(round((e_max_sr / target_sr) ** 2 * annual_factor))


# ── CPCV Orchestration ────────────────────────────────────────────────────────

def run_cpcv_validation(
    engine_factory: Callable,
    price_data: Dict[str, pd.DataFrame],
    macro_ts: pd.DataFrame,
    dates: pd.DatetimeIndex,
    benchmark_series: Optional[pd.Series] = None,
    output_dir: str = "reports/backtest/cpcv",
    n_splits: int = CPCV_N,
    k_test: int = CPCV_K,
) -> ValidationResult:
    """Ana entry point — CPCV + DSR + PBO + MinBTL tek çağrıyla.

    engine_factory: parametresiz çağrılabilir; her çağrıda yeni BacktestEngine döner.
    Örnek:
        factory = lambda: BacktestEngine(start_date=..., end_date=...)
        result = run_cpcv_validation(factory, price_data, macro_ts, dates)
    """
    # Lazy import: engine.py doğrudan import YASAK — factory callback yeterli
    from src.backtest.cross_validation import CombinatorialPurgedCV
    from src.backtest.metrics import summarize as backtest_summarize

    cpcv = CombinatorialPurgedCV(N=n_splits, k=k_test)
    split_paths = cpcv.split(dates)

    path_results: List[PathResult] = []
    oos_sharpes_nw: List[float] = []

    for path_id, (train_idx, test_idx) in enumerate(split_paths):
        test_dates = dates[test_idx]
        start = str(test_dates[0].date())
        end = str(test_dates[-1].date())

        engine = engine_factory()
        engine.start_date = start
        engine.end_date = end
        engine.run(price_data, macro_ts, benchmark_series)

        metrics = backtest_summarize(engine, benchmark_series)

        # OOS returns — engine scope bitmeden kaydet (DSR moment hesabı için)
        eq = np.array(engine.equity_curve)
        oos_returns = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([0.0])

        sr_naive = calculate_sharpe(engine.equity_curve) if engine.equity_curve else 0.0
        sr_nw = sharpe_newey_west(oos_returns)
        oos_sharpes_nw.append(sr_nw)

        # Crisis coverage
        crisis_covered = [
            cname
            for cname, (cs, ce) in CRISIS_WINDOWS.items()
            if test_dates[0] <= pd.Timestamp(ce) and test_dates[-1] >= pd.Timestamp(cs)
        ]

        path_results.append(PathResult(
            path_id=path_id,
            train_days=len(train_idx),
            test_days=len(test_idx),
            oos_sharpe_naive=sr_naive,
            oos_sharpe_nw=sr_nw,
            oos_return_pct=metrics.get("total_return_pct", 0.0),
            oos_max_drawdown_pct=metrics.get("max_drawdown_pct", 0.0),
            n_trades=len([t for t in engine.trades if t.get("type") == "SELL"]),
            crisis_windows_covered=crisis_covered,
            oos_returns=oos_returns,  # Kritik fix: scope dışına çıkmadan sakla
        ))
        logger.debug(
            "Path %d/%d: train=%d test=%d OOS_SR_NW=%.3f",
            path_id + 1,
            cpcv.n_paths,
            len(train_idx),
            len(test_idx),
            sr_nw,
        )

    # ── DSR: tüm path OOS returns'lerinden skewness/kurtosis hesapla ──────────
    T_oos = int(np.mean([p.test_days for p in path_results])) if path_results else 0

    if path_results:
        all_oos_returns = np.concatenate([pr.oos_returns for pr in path_results])
    else:
        all_oos_returns = np.array([0.0])

    if len(all_oos_returns) > 1:
        mu_all = float(all_oos_returns.mean())
        sigma_all = float(all_oos_returns.std())
        if sigma_all > 0:
            std_ret = (all_oos_returns - mu_all) / sigma_all
            skew = float(np.mean(std_ret ** 3))
            kurt = float(np.mean(std_ret ** 4))
        else:
            skew, kurt = 0.0, 3.0
    else:
        skew, kurt = 0.0, 3.0

    dsr = compute_dsr(oos_sharpes_nw, T=T_oos, skewness=skew, kurtosis=kurt)
    pbo = compute_pbo(oos_sharpes_nw)
    actual_days = len(dates)

    # ── Failure reasons ───────────────────────────────────────────────────────
    failures: List[str] = []
    if dsr <= DSR_THRESHOLD:
        failures.append(f"DSR {dsr:.3f} <= {DSR_THRESHOLD} (threshold not met)")
    if pbo >= PBO_THRESHOLD:
        failures.append(f"PBO {pbo:.3f} >= {PBO_THRESHOLD} (overfitting risk)")
    if actual_days < MIN_BACKTEST_DAYS:
        failures.append(
            f"Backtest length {actual_days} < {MIN_BACKTEST_DAYS} days (MinBTL)"
        )

    # ── Crisis coverage summary ───────────────────────────────────────────────
    crisis_coverage: Dict[str, int] = {cname: 0 for cname in CRISIS_WINDOWS}
    for pr in path_results:
        for c in pr.crisis_windows_covered:
            crisis_coverage[c] += 1

    # ── ValidationResult ──────────────────────────────────────────────────────
    sharpe_arr = sorted(oos_sharpes_nw)
    n = len(oos_sharpes_nw)

    result = ValidationResult(
        dsr=dsr,
        pass_dsr=dsr > DSR_THRESHOLD,
        pbo=pbo,
        pass_pbo=pbo < PBO_THRESHOLD,
        actual_backtest_days=actual_days,
        min_btl_days_required=MIN_BACKTEST_DAYS,
        pass_btl=actual_days >= MIN_BACKTEST_DAYS,
        n_paths=cpcv.n_paths,
        paths_positive_sharpe=sum(1 for s in oos_sharpes_nw if s > 0),
        sharpe_distribution=sharpe_arr,
        sharpe_mean=float(np.mean(oos_sharpes_nw)) if n else 0.0,
        sharpe_std=float(np.std(oos_sharpes_nw)) if n else 0.0,
        sharpe_p25=float(np.percentile(oos_sharpes_nw, 25)) if n else 0.0,
        sharpe_median=float(np.median(oos_sharpes_nw)) if n else 0.0,
        sharpe_p75=float(np.percentile(oos_sharpes_nw, 75)) if n else 0.0,
        deploy_ready=len(failures) == 0,
        failure_reasons=failures,
        crisis_coverage=crisis_coverage,
        path_results=path_results,
        report_path=output_dir,
    )
    logger.info(
        "CPCV validation: DSR=%.3f(%s) PBO=%.3f(%s) BTL=%d/%d(%s) deploy=%s",
        result.dsr,
        "PASS" if result.pass_dsr else "FAIL",
        result.pbo,
        "PASS" if result.pass_pbo else "FAIL",
        result.actual_backtest_days,
        result.min_btl_days_required,
        "PASS" if result.pass_btl else "FAIL",
        result.deploy_ready,
    )
    return result
