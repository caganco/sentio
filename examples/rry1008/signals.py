"""RR-Y1-008 -- VALIDATOR-VALIDATION / RED-TEAM signal definitions.

Cross-sectional Signal objects (engine ``Signal`` protocol: ``name``,
``construction_window``, ``scores(panel, names, asof)``) that reproduce the three
known-DEAD graveyard factors and one tunable mom-variant family. The signals return
RAW per-name factor values; the engine does neutralization / winsorize / rank-IC
internally (psi="spearman").

CRITICAL coupling (moda.py:427): ``h = int(signal.construction_window)`` and the Mod-A
IC is computed against the h-period-FORWARD return. So ``construction_window`` is the
IC forward-return HORIZON, NOT the signal's internal lookback. We pin
``construction_window = 21`` (~1 month) on every signal so the IC horizon matches the
~1-month-holding tests that produced the known verdicts; each factor's own lookback
(mom120=120d, hi52=252d, value=last fundamentals month) lives INSIDE ``scores()`` and
is independent. This dual-role coupling is benign for these monthly factors (monthly
signal -> monthly return) but is declared explicitly here and in the Stage-0 JSONs and
RR report: a future prototype whose construction_window != holding-horizon would
otherwise silently pick the wrong IC horizon.

Factor formulas mirror src/screening/d203_clean_universe_test.py (read-only reuse):
  value-static: bm = book-to-market (equity/mktval), latest fundamentals month
                <= asof - 1 publication-lag month. Higher = cheaper = long.
  mom120:       close[asof-21d] / close[asof-120d] - 1 (120d lookback, skip recent 21d).
  hi52:         close[asof] / rolling-252d-max(close). Proximity to 52-week high in (0,1].

ASCII-only by repo convention.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.engine import config
from src.engine.contracts import Panel

# Frozen factor parameters (match d203_config.py).
IC_HORIZON_H = 21  # construction_window == Mod-A IC forward-return horizon (see module docstring)
MOM_LOOKBACK = 120
MOM_SKIP = 21
HI52_LOOKBACK = 252
VALUE_PUBLICATION_LAG_MONTHS = 1
FUND_FILENAME = "fundamentals_2019_2026.parquet"


class _CachedFactorSignal:
    """Base: compute the full date x name factor panel once, then slice per asof.

    The engine calls ``scores`` once per panel date (~1850 calls); precomputing the
    whole factor panel on first call keeps that O(dates) instead of O(dates * window).
    """

    construction_window = IC_HORIZON_H

    def __init__(self, name: str) -> None:
        self.name = name
        self._cache: pd.DataFrame | None = None

    def _compute(self, panel: Panel) -> pd.DataFrame:  # pragma: no cover - overridden
        raise NotImplementedError

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        if self._cache is None:
            self._cache = self._compute(panel)
        if asof not in self._cache.index:
            return pd.Series(np.nan, index=names, dtype=float)
        return self._cache.loc[asof].reindex(names)


class Mom120Signal(_CachedFactorSignal):
    """120-day price momentum skipping the most recent 21 days (reversal control)."""

    def __init__(self) -> None:
        super().__init__("mom120")

    def _compute(self, panel: Panel) -> pd.DataFrame:
        close = panel.close
        return close.shift(MOM_SKIP) / close.shift(MOM_LOOKBACK) - 1.0


class Hi52Signal(_CachedFactorSignal):
    """52-week-high proximity = close / trailing-252d max, in (0, 1]; higher = nearer high."""

    def __init__(self) -> None:
        super().__init__("hi52")

    def _compute(self, panel: Panel) -> pd.DataFrame:
        close = panel.close
        roll_max = close.rolling(HI52_LOOKBACK, min_periods=HI52_LOOKBACK // 2).max()
        return close / roll_max.replace(0.0, np.nan)


class ValueStaticSignal(_CachedFactorSignal):
    """Static book-to-market (bm = equity / mktval). Higher = cheaper = long.

    Reads the monthly fundamentals parquet directly (the engine ``Panel`` carries no
    fundamentals). Applies a 1-month publication lag: a fundamentals month M is only
    usable from the first day of month M+1 (look-ahead-safe).
    """

    def __init__(self, data_root: str | Path | None = None) -> None:
        super().__init__("value_static")
        root = Path(data_root) if data_root is not None else config.REPO_ROOT
        self._fund_path = root / "data" / "clean_universe" / FUND_FILENAME

    def _compute(self, panel: Panel) -> pd.DataFrame:
        fund = pd.read_parquet(self._fund_path)
        month = pd.to_datetime(fund["month"].astype(str)).dt.to_period("M")
        bm = (
            fund.assign(month=month)
            .pivot_table(index="month", columns="symbol", values="bm", aggfunc="last")
            .sort_index()
        )
        # publication lag: month M knowable from the start of month M+1.
        eff_date = (bm.index + VALUE_PUBLICATION_LAG_MONTHS).to_timestamp(how="start")
        bm.index = eff_date
        bm = bm[~bm.index.duplicated(keep="last")]
        daily = bm.reindex(panel.close.index, method="ffill")
        return daily.reindex(columns=panel.close.columns)


class MomVariantSignal(_CachedFactorSignal):
    """Tunable momentum variant for the Part-2 adversarial K-family.

    factor = sign * (close[-skip] / close[-lookback] - 1), optionally cross-sectionally
    winsorized per date. ``sign`` = +1 (continuation) or -1 (reversal).
    """

    def __init__(
        self,
        lookback: int,
        *,
        skip: int = MOM_SKIP,
        sign: int = 1,
        winsorize: tuple[float, float] | None = None,
    ) -> None:
        tag = f"mom{lookback}_{'cont' if sign > 0 else 'rev'}"
        if winsorize is not None:
            tag += f"_w{winsorize[0]:g}-{winsorize[1]:g}"
        super().__init__(tag)
        self.lookback = int(lookback)
        self.skip = int(skip)
        self.sign = int(sign)
        self.winsorize = winsorize

    def _compute(self, panel: Panel) -> pd.DataFrame:
        close = panel.close
        raw = self.sign * (close.shift(self.skip) / close.shift(self.lookback) - 1.0)
        if self.winsorize is not None:
            lo_q, hi_q = self.winsorize
            lo = raw.quantile(lo_q, axis=1)
            hi = raw.quantile(hi_q, axis=1)
            raw = raw.clip(lower=lo, upper=hi, axis=0)
        return raw


def mom_variant_family() -> list[MomVariantSignal]:
    """The pre-fixed Part-2 K-family: lookback x sign x winsorize = 6 x 2 x 2 = 24.

    K is frozen here BEFORE any measurement -- it is the honest tried-config count N
    fed to DSR deflation (Stage-0 denenen_konfig_sayisi = 24).
    """
    lookbacks = (20, 40, 60, 120, 180, 240)
    signs = (1, -1)
    winsors: tuple[tuple[float, float] | None, ...] = (None, (0.05, 0.95))
    family = [
        MomVariantSignal(lb, sign=sg, winsorize=w)
        for lb in lookbacks
        for sg in signs
        for w in winsors
    ]
    assert len(family) == 24, f"K-family must be 24, got {len(family)}"
    return family
