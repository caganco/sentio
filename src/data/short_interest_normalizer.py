"""Short interest universe percentile normalizer (D-058)."""
from __future__ import annotations

import numpy as np


def score_short_interest(short_ratio: float, universe_percentile: float) -> float:
    """
    Ters sinyale çevir: düşük short oranı = bullish = yüksek score.

    short_ratio        : Bu hissenin short oranı (% of free float)
    universe_percentile: Hissenin universe içindeki percentile rank (0–1)
    Returns            : score ∈ [0.0, 1.0]
    """
    raw_score = 1.0 - universe_percentile
    return float(np.clip(raw_score, 0.0, 1.0))


def compute_universe_percentiles(
    short_ratios: dict[str, float],
    mad_threshold: float = 2.5,
) -> dict[str, float]:
    """
    {symbol: short_ratio} → {symbol: percentile_rank}.
    MAD-based outlier clip (BIST kurtosis>6 nedeniyle Z-score yerine MAD).
    """
    if not short_ratios:
        return {}

    symbols = list(short_ratios.keys())
    values = np.array([short_ratios[s] for s in symbols], dtype=float)

    # MAD clip
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad > 0:
        lower = median - mad_threshold * mad
        upper = median + mad_threshold * mad
        values = np.clip(values, lower, upper)

    # Percentile rank [0, 1]
    ranks = np.argsort(np.argsort(values)) / max(len(values) - 1, 1)
    return dict(zip(symbols, ranks.tolist()))
