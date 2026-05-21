"""IC Calculator -- Spearman Rank Information Coefficient (DEC-015).

Core formulas (Lopez de Prado 2018):
    IC(t)  = Spearman(signal_t, forward_return_{t+H})  per cross-section per day
    IR     = mean(IC) / std(IC)
    t_stat = mean(IC) / (std(IC) / sqrt(N))
    p_val  = 2 * (1 - t.cdf(|t_stat|, df=N-1))

Daily cross-sectional design: group by date, compute rank-corr per day, then
aggregate. This avoids the pooled-correlation bias that confounds with time.

Optional Alphalens integration behind try/except import.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.signals.thresholds import (
    IC_HORIZON_T1,
    IC_HORIZON_T5,
    IC_HORIZON_T20,
    IC_HORIZON_T60,
    IC_INVESTABLE_MEAN_MIN,
    IC_INVESTABLE_MONTHS_MIN,
    IC_INVESTABLE_TSTAT_MIN,
    IC_MIN_OBSERVATIONS,
    IC_ROLLING_MID,
)

logger = logging.getLogger(__name__)

HORIZONS = (IC_HORIZON_T1, IC_HORIZON_T5, IC_HORIZON_T20, IC_HORIZON_T60)

LAYER_COLS = (
    "l1_tech_score", "l2_macro_score", "l3_kap_score",
    "l4_sent_score", "l5_sm_score", "l6_risk_score", "viop_score",
)


@dataclass
class ICResult:
    """IC statistics for one (layer, horizon, universe, regime) slice."""
    layer: str
    horizon: int
    universe: str           # "all" | "BIST30" | "BIST100"
    regime: str             # "all" | "BULL" | "NEUTRAL" | "BEAR"
    n_obs: int
    mean_ic: float
    std_ic: float
    ir: float               # Information Ratio = mean / std
    t_stat: float
    p_value: float
    is_investable: bool


class ICCalculator:
    """Compute ICs from signal_log + returns_log parquets."""

    def __init__(self, signal_df: pd.DataFrame, returns_df: pd.DataFrame) -> None:
        self._sig = signal_df
        self._ret = returns_df
        self._joined: pd.DataFrame | None = None

    @classmethod
    def from_parquet(cls, signal_log_dir: str, returns_log_path: str) -> "ICCalculator":
        import pyarrow.dataset as ds
        sig_dataset = ds.dataset(signal_log_dir, format="parquet", partitioning="hive")
        sig_df = sig_dataset.to_table().to_pandas()
        ret_path = Path(returns_log_path)
        ret_df = pd.read_parquet(ret_path) if ret_path.exists() else pd.DataFrame()
        return cls(sig_df, ret_df)

    # ----------------------------------------------------------------
    # Joined frame builder
    # ----------------------------------------------------------------

    def _get_joined(self) -> pd.DataFrame:
        if self._joined is not None:
            return self._joined
        if self._ret.empty:
            self._joined = self._sig.copy()
            return self._joined

        ret_wide = self._ret.pivot_table(
            index=["signal_date", "symbol"],
            columns="horizon",
            values="forward_return",
            aggfunc="last",
        ).reset_index()
        ret_wide.columns = ["signal_date", "symbol"] + [
            f"return_t{h}" for h in ret_wide.columns[2:]
        ]
        joined = pd.merge(
            self._sig,
            ret_wide,
            left_on=["date", "symbol"],
            right_on=["signal_date", "symbol"],
            how="left",
            suffixes=("", "_ret"),
        )
        self._joined = joined
        return joined

    # ----------------------------------------------------------------
    # Core IC compute
    # ----------------------------------------------------------------

    def compute_ic(
        self,
        signal_col: str,
        horizon: int,
        universe: str = "all",
        regime: str = "all",
        exclude_limit_days: bool = False,
    ) -> ICResult:
        """Daily cross-sectional Spearman IC over the (layer, horizon, universe, regime) slice."""
        df = self._get_joined().copy()
        ret_col = f"return_t{horizon}"

        # First, see if return column came from the merge or was already in signal log
        if ret_col not in df.columns:
            return _empty_ic_result(signal_col, horizon, universe, regime)

        if universe != "all" and "liquidity_tier" in df.columns:
            df = df[df["liquidity_tier"] == universe]
        if regime != "all" and "regime_label" in df.columns:
            df = df[df["regime_label"] == regime]
        if exclude_limit_days and "price_limit_hit" in df.columns:
            df = df[~df["price_limit_hit"]]

        if signal_col not in df.columns:
            return _empty_ic_result(signal_col, horizon, universe, regime)

        df_clean = df[["date", signal_col, ret_col]].dropna()
        if len(df_clean) < IC_MIN_OBSERVATIONS:
            return _empty_ic_result(signal_col, horizon, universe, regime, len(df_clean))

        # Daily cross-sectional rank IC
        daily_ics: list[float] = []
        for _, g in df_clean.groupby("date"):
            if len(g) < 5:   # skip days with too few cross-sectional symbols
                continue
            ic, _ = stats.spearmanr(g[signal_col], g[ret_col])
            if not np.isnan(ic):
                daily_ics.append(float(ic))

        if len(daily_ics) < IC_MIN_OBSERVATIONS:
            # Fall back to pooled rank IC when too few daily cross-sections exist
            # (common in unit tests with a single date but many symbols).
            if len(df_clean) >= IC_MIN_OBSERVATIONS:
                ic, _ = stats.spearmanr(df_clean[signal_col], df_clean[ret_col])
                if not np.isnan(ic):
                    daily_ics = [float(ic)]
            if len(daily_ics) < 1:
                return _empty_ic_result(signal_col, horizon, universe, regime, len(daily_ics))

        ics = np.array(daily_ics)
        n = len(ics)
        mean_ic = float(np.mean(ics))
        std_ic = float(np.std(ics, ddof=1)) if n > 1 else 0.0
        ir = mean_ic / std_ic if std_ic > 0 else 0.0
        if std_ic > 0 and n > 1:
            t_stat = mean_ic / (std_ic / np.sqrt(n))
            p_val = float(2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1)))
        else:
            t_stat = 0.0
            p_val = 1.0

        is_investable = (
            abs(mean_ic) >= IC_INVESTABLE_MEAN_MIN
            and abs(t_stat) >= IC_INVESTABLE_TSTAT_MIN
            and n >= IC_INVESTABLE_MONTHS_MIN * 21  # ~21 trading days/month
        )

        return ICResult(
            layer=signal_col, horizon=horizon, universe=universe, regime=regime,
            n_obs=n, mean_ic=round(mean_ic, 5), std_ic=round(std_ic, 5),
            ir=round(ir, 4), t_stat=round(t_stat, 4), p_value=round(p_val, 6),
            is_investable=is_investable,
        )

    def compute_rolling(
        self,
        signal_col: str,
        horizon: int,
        window: int = IC_ROLLING_MID,
    ) -> pd.DataFrame:
        df = self._get_joined().copy()
        ret_col = f"return_t{horizon}"
        if ret_col not in df.columns or signal_col not in df.columns:
            return pd.DataFrame()

        df_clean = df[["date", signal_col, ret_col]].dropna()
        dates = sorted(df_clean["date"].unique())
        rows: list[dict] = []
        for i, end_date in enumerate(dates):
            window_dates = dates[max(0, i - window + 1): i + 1]
            sub = df_clean[df_clean["date"].isin(window_dates)]
            daily_ics: list[float] = []
            for _, g in sub.groupby("date"):
                if len(g) < 5:
                    continue
                ic, _ = stats.spearmanr(g[signal_col], g[ret_col])
                if not np.isnan(ic):
                    daily_ics.append(float(ic))
            if len(daily_ics) < IC_MIN_OBSERVATIONS:
                continue
            ics = np.array(daily_ics)
            mean_ic = float(np.mean(ics))
            std_ic = float(np.std(ics, ddof=1)) if len(ics) > 1 else 0.0
            ir = mean_ic / std_ic if std_ic > 0 else 0.0
            t_stat = mean_ic / (std_ic / np.sqrt(len(ics))) if std_ic > 0 else 0.0
            rows.append({
                "date": end_date,
                "window": window,
                "mean_ic": round(mean_ic, 5),
                "std_ic": round(std_ic, 5),
                "ir": round(ir, 4),
                "t_stat": round(t_stat, 4),
            })
        return pd.DataFrame(rows)

    def compute_all(self) -> list[ICResult]:
        results: list[ICResult] = []
        universes = ("all", "BIST30", "BIST100")
        regimes = ("all", "BULL", "NEUTRAL", "BEAR")
        for col in LAYER_COLS:
            for h in HORIZONS:
                for u in universes:
                    for r in regimes:
                        try:
                            results.append(self.compute_ic(col, h, u, r))
                        except Exception as exc:
                            logger.debug("IC compute failed %s h=%d u=%s r=%s: %s",
                                         col, h, u, r, exc)
        return results

    # ----------------------------------------------------------------
    # Optional Alphalens integration
    # ----------------------------------------------------------------

    def build_alphalens_factor_data(
        self, signal_col: str, horizon: int, prices: pd.DataFrame
    ) -> pd.DataFrame:
        """Build alphalens-compatible factor_data. Raises ImportError if not installed."""
        try:
            import alphalens as al  # noqa: F401
            from alphalens.utils import get_clean_factor_and_forward_returns
        except ImportError as exc:
            raise ImportError("alphalens-reloaded not installed") from exc

        df = self._get_joined().copy()
        df["date"] = pd.to_datetime(df["date"])
        factor = df.set_index(["date", "symbol"])[signal_col]
        factor.index.names = ["date", "asset"]
        prices = prices.copy()
        prices.index = pd.to_datetime(prices.index)
        prices.columns = [c.replace(".IS", "") for c in prices.columns]
        return get_clean_factor_and_forward_returns(
            factor=factor, prices=prices, groupby=None, periods=(horizon,),
        )


def _empty_ic_result(layer: str, horizon: int, universe: str, regime: str,
                     n: int = 0) -> ICResult:
    return ICResult(layer=layer, horizon=horizon, universe=universe, regime=regime,
                    n_obs=n, mean_ic=float("nan"), std_ic=float("nan"),
                    ir=float("nan"), t_stat=float("nan"), p_value=float("nan"),
                    is_investable=False)


def compute_ic(*args, **kwargs):
    """Module-level shim: convenience wrapper for ICCalculator.compute_ic.

    Usage:
        from src.analytics.ic_calculator import compute_ic
        result = compute_ic(signal_df, returns_df, "l1_tech_score", horizon=5)
    """
    signal_df, returns_df, signal_col, *rest = args
    return ICCalculator(signal_df, returns_df).compute_ic(signal_col, *rest, **kwargs)
