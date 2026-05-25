"""
Alternatif risk metrikleri: Ulcer Index, Calmar Ratio, Sortino Ratio, Current DD.
GÖZLEM MODU — pozisyon kararına ETKİ YOK.
Dayanak: RR-016 §2.1, §8 (D-147).
"""
import math
from collections.abc import Sequence


def compute_ulcer_index(equity_series: Sequence[float], n: int = 14) -> float:
    """
    Ulcer Index (Peter Martin 1987).

    UI = sqrt( (1/n) × Σ D'_i² )
    D'_i = max(0, (peak_i − price_i) / peak_i × 100)

    peak_i = kümülatif tepe (max(equity_series[:i+1])).
    Son n değer üzerinden hesaplanır.

    Sanity Tests (RR-016 §2.1):
      S1: Hep yeni peak → UI = 0
      S2: Sabit %5 dip, n=14 → UI = 5.00
      S3: Tek %20 dip + 13 gün peak → UI ≈ 5.35
      S4: 14 gün %15 dipte kalış → UI = 15.0

    Args:
        equity_series: Portföy değer serisi (örn. günlük kapanış TL bazlı).
        n: Pencere boyutu (varsayılan: 14).

    Returns:
        Ulcer Index (float, ≥ 0). Boş seri → 0.0.
    """
    if not equity_series:
        return 0.0
    series = list(equity_series)
    # Kümülatif tepe hesapla
    peaks: list[float] = []
    current_peak = series[0]
    for price in series:
        if price > current_peak:
            current_peak = price
        peaks.append(current_peak)
    # Son n değer üzerinden hesapla
    tail_series = series[-n:]
    tail_peaks = peaks[-n:]
    sq_sum = 0.0
    count = len(tail_series)
    for price, peak in zip(tail_series, tail_peaks):
        if peak == 0.0:
            continue
        d_pct = max(0.0, (peak - price) / peak * 100.0)
        sq_sum += d_pct ** 2
    if count == 0:
        return 0.0
    return math.sqrt(sq_sum / count)


def compute_calmar_ratio(returns: Sequence[float], mdd: float) -> float:
    """
    Calmar Ratio (Terry Young 1991).

    calmar = annualized_return / abs(MDD)
    annualized_return = mean(returns) * 252

    Sanity Tests (RR-016 §2.1 A5):
      S1: %30 yıllık getiri, MDD=%20 → Calmar = 1.5
      S2: BIST 2024 proxy: +%20 nominal, MDD ~%15 → Calmar ≈ 1.33

    Args:
        returns: Günlük getiri serisi (örn. [0.001, -0.002, ...]).
        mdd: Maksimum drawdown (pozitif kesir, örn. 0.15 = %15).

    Returns:
        Calmar Ratio (float). mdd == 0 veya seri boşsa 0.0.
    """
    if not returns or mdd == 0.0:
        return 0.0
    annual_return = sum(returns) / len(returns) * 252
    return float(annual_return / abs(mdd))


def compute_sortino_ratio(returns: Sequence[float], mar: float = 0.0) -> float:
    """
    Sortino Ratio.

    downside_dev = sqrt( (1/N) × Σ min(r_i − MAR, 0)² )   [N = tüm örnekler]
    sortino = (mean(returns) − MAR) / downside_dev

    Sanity Test (RR-016 §8):
      Seri [5,3,-2,-4,6,1,-1,4,3,-3,2,5], MAR=0:
      DownDev = sqrt((4+16+1+9)/12) = 1.58
      Sortino = (19/12) / 1.58 ≈ 1.0

    Args:
        returns: Getiri serisi (herhangi bir birimde tutarlı olmalı).
        mar: Minimum Acceptable Return (varsayılan: 0.0).

    Returns:
        Sortino Ratio (float). downside_dev == 0 veya seri boşsa 0.0.
    """
    if not returns:
        return 0.0
    n = len(returns)
    mean_excess = sum(returns) / n - mar
    sq_sum = sum(min(r - mar, 0.0) ** 2 for r in returns)
    downside_dev = math.sqrt(sq_sum / n)
    if downside_dev == 0.0:
        return 0.0
    return float(mean_excess / downside_dev)


def compute_current_drawdown(equity_series: Sequence[float]) -> float:
    """
    Mevcut drawdown: (peak − current) / peak.

    Portföyün son değerinin, tarihsel tepe noktasından ne kadar uzakta olduğunu ölçer.

    Args:
        equity_series: Portföy değer serisi.

    Returns:
        Drawdown kesri (0.0–1.0). Seri boşsa 0.0.
    """
    if not equity_series:
        return 0.0
    series = list(equity_series)
    peak = max(series)
    current = series[-1]
    if peak == 0.0:
        return 0.0
    return float(max(0.0, (peak - current) / peak))
