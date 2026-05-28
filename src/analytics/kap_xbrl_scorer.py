"""XBRL finansal surprise -> backtest L3 skoru. D-171.

Saf, stateless modul (side-effect yok). Pipeline:
    YoY surprise -> TUFE deflate -> cross-sectional rank -> [-40, +40]

Kullanim (backtest engine):
    from src.analytics.kap_xbrl_scorer import (
        build_universe_xbrl_snapshot, score_xbrl_surprise,
    )
    snap = build_universe_xbrl_snapshot(tickers, "2025-12-31", tufe_series)
    impact = score_xbrl_surprise("THYAO", "2025-12-31", snap)  # -40..+40
    kap_score = max(0.0, min(100.0, 50.0 + impact))

Dayanak: RR-012 §B14 (XBRL YoY = TOP-1), RR-018 (look-ahead guard),
RR-010 (cross-sectional rank normalizasyonu).
"""
from __future__ import annotations

import logging
import math
from typing import Any

import pandas as pd

from src.data.kap_historical_fetcher import fetch_fr_history
from src.data.short_interest_normalizer import compute_universe_percentiles

logger = logging.getLogger(__name__)

_SNAPSHOT_COLS = ["ticker", "metric", "real_surprise", "publication_date"]

# Enflasyon ortaminda GrossProfit, Revenue'dan guvenilir (RR-012 §B14).
_METRIC_PRIORITY = ("gross_profit", "net_income", "revenue")

_SURPRISE_CAP = 1.0          # |surprise| ust siniri (YoY orani)
_IMPACT_SPAN = 80.0          # (pct - 0.5) * span -> [-40, +40]
_IMPACT_CAP = 40.0
_MIN_UNIVERSE = 2            # cross-sectional rank icin min ticker sayisi


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_universe_xbrl_snapshot(
    tickers: list[str],
    as_of_date: str,
    tufe_series: "pd.Series | None",
) -> pd.DataFrame:
    """Tum universe icin as_of_date'e kadarki TUFE-deflate YoY surprise toplar.

    Args:
        tickers:     BIST ticker listesi.
        as_of_date:  "YYYY-MM-DD" backtest tarihi (look-ahead siniri).
        tufe_series: Gunluk DatetimeIndex TUFE serisi (fetch_tufe_series, D-169);
                     None ise deflation atlanir (nominal kullanilir).

    Returns:
        DataFrame[ticker, metric, real_surprise, publication_date].
        Hesaplanabilir surprise olmayan ticker'lar dahil edilmez.
        Veri/kimlik yoksa bos DataFrame.
    """
    as_of_year = int(as_of_date[:4])
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            hist = fetch_fr_history(ticker, as_of_year - 1, as_of_year)
        except Exception as exc:  # noqa: BLE001 - tek ticker hatasi tum snapshot'i bozmamali
            logger.debug("xbrl snapshot fetch hata: ticker=%s %s", ticker, exc)
            continue
        rec = _ticker_surprise(hist, as_of_date, tufe_series)
        if rec is not None:
            rec["ticker"] = ticker
            rows.append(rec)

    logger.debug(
        "xbrl snapshot: as_of=%s n_tickers_with_data=%d/%d",
        as_of_date, len(rows), len(tickers),
    )
    if not rows:
        return pd.DataFrame(columns=_SNAPSHOT_COLS)
    return pd.DataFrame(rows, columns=_SNAPSHOT_COLS)


def score_xbrl_surprise(
    ticker: str,
    as_of_date: str,
    universe_df: pd.DataFrame,
) -> float:
    """Ticker'in cross-sectional XBRL surprise impact'ini [-40, +40] dondurur.

    Veri yoksa 0.0 (exception firlatmaz). Tek veri noktasinda cross-sectional
    rank anlamsizdir -> 0.0 (n_tickers_with_data loglanir).
    """
    if universe_df is None or len(universe_df) == 0:
        return 0.0
    df = universe_df
    if "real_surprise" not in df.columns or "ticker" not in df.columns:
        return 0.0

    # Look-ahead guard (ikinci kademe): gelecekte yayimlanan satirlari ele.
    if "publication_date" in df.columns:
        before = len(df)
        df = df[df["publication_date"].notna()
                & (df["publication_date"].astype(str) <= as_of_date)]
        if len(df) < before:
            logger.debug(
                "xbrl look-ahead filtre: as_of=%s dropped=%d ticker=%s",
                as_of_date, before - len(df), ticker,
            )

    df = df.dropna(subset=["real_surprise"])
    tickers_with_data = set(df["ticker"])
    n = len(tickers_with_data)
    if ticker not in tickers_with_data:
        return 0.0
    if n < _MIN_UNIVERSE:
        logger.debug(
            "xbrl rank atlandi: n_tickers_with_data=%d (<%d) ticker=%s",
            n, _MIN_UNIVERSE, ticker,
        )
        return 0.0

    surprises = dict(zip(df["ticker"], df["real_surprise"].astype(float)))
    percentiles = compute_universe_percentiles(surprises)
    score = (percentiles[ticker] - 0.5) * _IMPACT_SPAN
    score = max(-_IMPACT_CAP, min(_IMPACT_CAP, score))
    logger.debug(
        "xbrl score: ticker=%s pct=%.3f score=%.1f n_tickers=%d",
        ticker, percentiles[ticker], score, n,
    )
    return float(score)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ticker_surprise(
    hist: "pd.DataFrame | None",
    as_of_date: str,
    tufe_series: "pd.Series | None",
) -> "dict[str, Any] | None":
    """Tek ticker icin TUFE-deflate YoY surprise. Hesaplanamazsa None."""
    if hist is None or len(hist) == 0:
        return None

    df = hist.copy()
    pub_col = "publication_date" if "publication_date" in df.columns else "date"
    df = df[df[pub_col].notna() & (df[pub_col].astype(str) <= as_of_date)]
    if len(df) == 0 or "year" not in df.columns:
        return None

    for metric in _METRIC_PRIORITY:
        if metric not in df.columns:
            continue
        sub = df[df[metric].notna()].copy()
        if sub["year"].apply(_as_int).nunique() < 2:
            continue
        sub = sub.sort_values(pub_col)
        latest = sub.iloc[-1]
        cur_year = _as_int(latest["year"])
        cur_period = latest.get("period")

        prior = sub[sub["year"].apply(_as_int) == cur_year - 1]
        if cur_period is not None and "period" in sub.columns:
            same_period = prior[prior["period"] == cur_period]
            if len(same_period) > 0:
                prior = same_period
        if len(prior) == 0:
            continue
        prior_row = prior.sort_values(pub_col).iloc[-1]

        real_cur = _deflate(float(latest[metric]), latest[pub_col], tufe_series)
        real_pri = _deflate(float(prior_row[metric]), prior_row[pub_col], tufe_series)
        if abs(real_pri) <= 0.0:
            continue

        surprise = (real_cur - real_pri) / abs(real_pri)
        surprise = max(-_SURPRISE_CAP, min(_SURPRISE_CAP, surprise))
        return {
            "metric": metric,
            "real_surprise": surprise,
            "publication_date": str(latest[pub_col])[:10],
        }
    return None


def _deflate(nominal: float, pub_date: Any, tufe_series: "pd.Series | None") -> float:
    """nominal / CPI(pub_date). TUFE yoksa/gecersizse nominal doner."""
    if tufe_series is None:
        return nominal
    try:
        cpi = float(tufe_series.asof(pd.Timestamp(str(pub_date)[:10])))
    except Exception:  # noqa: BLE001
        return nominal
    if math.isnan(cpi) or cpi <= 0.0:
        return nominal
    return nominal / cpi


def _as_int(value: Any) -> int:
    """Yil alanini guvenli int'e cevirir (str/float/int kabul eder)."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return -1
