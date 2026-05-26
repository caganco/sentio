"""EEM ETF ve EM Relative Strength fetch yardimcisi (D-154, RR-022 §B).

Kullanim:
    from src.data.macro_sources import fetch_em_relative_strength
    em_rs = fetch_em_relative_strength()   # returns float in [-1, +1] or None

Formula:
    ratio_today = XU100.IS_close / EEM_close
    ratio_lookback = same ratio N trading days ago
    em_rs = (ratio_today / ratio_lookback - 1) / EM_RELSTRENGTH_SCALE

Normalize edilmis deger: +1.0 = BIST EM'i guclu sekilde geciyor,
-1.0 = BIST EM'in guclu sekilde gerisinde.

Production path: daily_update.py bu fonksiyonu cagirir, sonucu macro_data
dict'ine "EM_RELSTRENGTH" key'i ile ekler, score_macro()'ya iletir.
"""
from __future__ import annotations

import logging

import pandas as pd

from src.signals.thresholds import EM_RELSTRENGTH_LOOKBACK, EM_RELSTRENGTH_SCALE

logger = logging.getLogger(__name__)

_BIST100_TICKER = "XU100.IS"
_EEM_TICKER = "EEM"


def fetch_em_relative_strength(
    lookback_days: int = EM_RELSTRENGTH_LOOKBACK,
    scale: float = EM_RELSTRENGTH_SCALE,
) -> float | None:
    """BIST100/EEM ratio N-gunluk momentum hesaplar.

    Returns:
        float in [-1.0, +1.0] — normalized EM relative strength score.
        None if download fails or insufficient history.

    Formula:
        ratio = XU100.IS / EEM (price ratio)
        em_rs = (ratio_today / ratio_N_days_ago - 1) / scale
        clipped to [-1.0, +1.0]
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — cannot fetch EM relative strength")
        return None

    n_download = lookback_days + 10  # buffer for weekends/holidays
    try:
        bist = yf.download(
            _BIST100_TICKER,
            period=f"{n_download}d",
            auto_adjust=True,
            progress=False,
        )
        eem = yf.download(
            _EEM_TICKER,
            period=f"{n_download}d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        logger.warning("fetch_em_relative_strength: download error — %s", exc)
        return None

    # Flatten MultiIndex if present (newer yfinance versions)
    if isinstance(bist.columns, pd.MultiIndex):
        bist = bist.droplevel(1, axis=1)
    if isinstance(eem.columns, pd.MultiIndex):
        eem = eem.droplevel(1, axis=1)

    if bist.empty or "Close" not in bist.columns:
        logger.warning("fetch_em_relative_strength: BIST100 data empty")
        return None
    if eem.empty or "Close" not in eem.columns:
        logger.warning("fetch_em_relative_strength: EEM data empty")
        return None

    # Align on common dates
    ratio: pd.Series = (bist["Close"] / eem["Close"]).dropna()

    if len(ratio) < lookback_days + 1:
        logger.warning(
            "fetch_em_relative_strength: insufficient history (%d rows, need %d)",
            len(ratio), lookback_days + 1,
        )
        return None

    ratio_today = float(ratio.iloc[-1])
    ratio_prev = float(ratio.iloc[-(lookback_days + 1)])

    if ratio_prev == 0:
        logger.warning("fetch_em_relative_strength: ratio_prev is zero")
        return None

    raw = (ratio_today / ratio_prev) - 1.0
    normalized = float(max(-1.0, min(1.0, raw / scale)))
    logger.debug(
        "EM RS: ratio_today=%.4f ratio_%dd=%.4f raw=%.4f normalized=%.4f",
        ratio_today, lookback_days, ratio_prev, raw, normalized,
    )
    return normalized
