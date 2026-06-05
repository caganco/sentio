"""Typed contracts for the harness signature (Section 9).

    harness(panel, sinyal, split_spec, dial_config) -> EngineOutput

- ``Panel``       : loaded wide data frames (data_adapter output).
- ``SplitSpec``   : how the universe is split + frozen split params (Stage-0).
- ``DialConfig``  : the 8 tunable dials (Section 5); defaults = config.py (v1.1 Section 8).
- ``EngineOutput``: the Section 7 output-vector (a vector, NOT a pass/fail bit).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd

from . import config


class HoldPoint(StrEnum):
    """Where the prototype "holds" -> selects the split mode (Section 3.7)."""

    CROSS_SECTIONAL = "cross_sectional"
    TIMING = "timing"
    PANEL = "panel"


class SplitMode(StrEnum):
    NAME = "A"  # Mod A: name-split (cross-sectional)
    TEMPORAL = "B"  # Mod B: temporal CPCV (purge + embargo)
    PANEL = "A+B"  # combined


class Frequency(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"


class SortDepth(StrEnum):
    TERCILE = "tercile"
    TOPN = "topN"
    DECILE = "decile"


class NameSplitMethod(StrEnum):
    """How Mod-A partitions the universe into arms (Section 3.2). Alphabetical/
    ordered assignment is FORBIDDEN -- both options below are balance-preserving."""

    LIQUIDITY = "liquidity"  # default: ADV-stratified pair-randomization (equal liquidity/arm)
    RANDOM = "random"  # plain seed-fixed random halves


class RegimeTarget(StrEnum):
    REGIME_R = "regime_R"
    AGNOSTIC = "agnostic"


class ReturnBasis(StrEnum):
    TR_GROSS = "tr_index_gross"
    TR_NET = "tr_index_net"


class CutPolicy(StrEnum):
    ANCHORED = "anchored"
    ROLLING = "rolling"
    EXPANDING = "expanding"


@dataclass(frozen=True, eq=False)
class Panel:
    """Loaded data panel. All frames are wide: index=date, columns=symbol.

    ``eq=False`` because DataFrame ``__eq__`` is element-wise (an auto-generated
    ``__eq__`` would raise "ambiguous truth value").
    """

    close: pd.DataFrame  # adjusted_close
    tr_gross: pd.DataFrame  # tr_index_gross (total-return, dividends reinvested)
    tr_net: pd.DataFrame  # tr_index_net
    value_tl: pd.DataFrame  # daily traded value (liquidity proxy)
    membership: dict[str, pd.DataFrame]  # {"bist100": 0/1 flags, "bist30": ...} PIT
    market: pd.Series  # market index level (xu100); returns = pct_change
    tufe: pd.Series  # CPI level
    tlref: pd.Series  # TLREF
    frequency: Frequency = Frequency.DAILY

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index  # type: ignore[return-value]

    @property
    def names(self) -> list[str]:
        return list(self.close.columns)


@dataclass(frozen=True)
class SplitSpec:
    """Split structure frozen at Stage-0 (dials 2, 4, 8). Section 3."""

    split_mode: SplitMode
    frequency: Frequency
    embargo_h: int = 1  # = signal construction-window (Section 3.4); h >= 1
    R: int = config.SPLIT_R_MIN  # seed-fixed name-splits (Mod-A)
    seed: int = 0
    cpcv_n: int = config.CPCV_DAILY_N  # Mod-B temporal CPCV blocks
    cpcv_k: int = config.CPCV_DAILY_K
    split_arm_floor_tl: float = config.LIQUID_ADV_MIN_TL
    sort_depth: SortDepth = SortDepth.TERCILE
    min_names_per_arm: int = config.MIN_NAMES_PER_ARM
    name_split_method: NameSplitMethod = NameSplitMethod.LIQUIDITY  # Mod-A only (Section 3.2)

    def __post_init__(self) -> None:
        if self.embargo_h < 1:
            raise ValueError(f"embargo_h must be >= 1 (got {self.embargo_h})")
        if self.cpcv_k >= self.cpcv_n:
            raise ValueError(f"cpcv_k ({self.cpcv_k}) must be < cpcv_n ({self.cpcv_n})")
        if self.R < 1:
            raise ValueError(f"R must be >= 1 (got {self.R})")
        # Section 3.6 / 8: monthly temporal-CPCV is power-poor -> Mod-A mandatory.
        if (
            config.MONTHLY_TEMPORAL_CPCV_FORBIDDEN
            and self.frequency is Frequency.MONTHLY
            and self.split_mode is not SplitMode.NAME
        ):
            raise ValueError(
                "monthly frequency requires split_mode A (name-split); "
                "temporal-CPCV is power-poor at monthly frequency (Section 3.6)."
            )


@dataclass(frozen=True)
class DialConfig:
    """The 8 tunable dials (Section 5). Defaults = frozen v1.1 Section 8.

    Dials 2 (split-mode), 4 (embargo) and 8 (arm-floor + sort-depth) live in
    ``SplitSpec`` (they are split structure); the rest live here.
    """

    psi: str = config.IC_TYPE  # dial 1
    neutralization: tuple[str, ...] = config.NEUTRALIZATION_FACTORS_DEFAULT  # dial 3
    return_basis: ReturnBasis = ReturnBasis.TR_GROSS
    cut_policies: tuple[CutPolicy, ...] = (
        CutPolicy.ANCHORED,
        CutPolicy.ROLLING,
        CutPolicy.EXPANDING,
    )  # dial 7
    use_pbo: bool = True  # dial 5
    use_dsr: bool = True  # dial 6
    nw_lag: int | None = None  # resolved from frequency when None
    winsorize: tuple[float, float] = (config.WINSORIZE_LOWER, config.WINSORIZE_UPPER)
    beta_window: int = config.BETA_WINDOW_DAYS
    agreement_t_min: float = config.AGREEMENT_CROSS_IC_T_MIN
    sign_consistency_min: float = config.SIGN_CONSISTENCY_MIN
    pbo_max: float = config.PBO_THRESHOLD
    dsr_min: float = config.DSR_MIN
    residual_corr_null_pctile: int = config.RESIDUAL_CORR_NULL_PCTILE

    def __post_init__(self) -> None:
        if not self.neutralization:
            raise ValueError("neutralization must list >= 1 factor (market is the minimum)")
        unknown = set(self.neutralization) - config.ALLOWED_FACTORS
        if unknown:
            raise ValueError(f"unknown neutralization factor(s): {sorted(unknown)}")
        lo, hi = self.winsorize
        if not (0.0 <= lo < hi <= 1.0):
            raise ValueError(f"winsorize bounds invalid: {self.winsorize}")

    def nw_lag_for(self, frequency: Frequency) -> int:
        if self.nw_lag is not None:
            return self.nw_lag
        return config.NW_LAG_DAILY if frequency is Frequency.DAILY else config.NW_LAG_MONTHLY

    def requires_market_neutralization(self, split_mode: SplitMode) -> None:
        """Section 3.5: market-beta neutralization is mandatory for Mod-A."""
        if split_mode in (SplitMode.NAME, SplitMode.PANEL) and "market" not in self.neutralization:
            raise ValueError(
                "Mod-A (name-split) requires at least market-beta neutralization "
                "(Section 3.5); add 'market' to dial_config.neutralization."
            )


@dataclass
class EngineOutput:
    """Section 7 output-vector. Populated incrementally across Faz-1..3; every
    field defaults to None/empty so a partial run is still a valid object."""

    # returns -- total-return based (bullets 1-2)
    gross_active_ann: float | None = None
    net_active_ann: float | None = None
    cost_ann: float | None = None
    tax_ann: float | None = None
    mean_rt_bps: float | None = None
    # fair-null + mirror (bullet 3)
    null_percentile: float | None = None
    mirror_active_ann: float | None = None
    # relative benchmark (bullet 4): real return vs max(TUFE, TLREF)
    real_active_ann: float | None = None
    benchmark_floor_ann: float | None = None
    beats_benchmark_floor: bool | None = None
    # significance (bullet 5): PBO, cut-family deflated OOS-t, DSR
    pbo: float | None = None
    deflated_oos_t: float | None = None
    dsr: float | None = None
    nw_t: float | None = None
    # conjugate agreement + residual corr (bullet 6; Section 4.1/4.2 -- kept SEPARATE)
    agreement_pass: bool | None = None
    agreement_t_cross_median: float | None = None  # min over both directions
    sign_consistency: float | None = None
    residual_cross_sectional_corr: float | None = None
    residual_corr_flag: bool | None = None  # red flag if > null pctile
    # per-regime breakdown (bullet 7; manual label)
    per_regime: dict[str, dict[str, float]] = field(default_factory=dict)
    # parameter plateau / sensitivity (bullet 8)
    plateau_map: dict[str, float] = field(default_factory=dict)
    # PM-1 + guards (Section 10)
    pm1_guard_raised: bool = False
    guard_messages: tuple[str, ...] = ()
    # provenance
    n_obs: int | None = None
    n_names: int | None = None
    split_mode: str | None = None
    notes: tuple[str, ...] = ()
