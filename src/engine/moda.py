"""Mod-A conjugate (cross-sectional) core (Section 3.2/4.1/4.2): the engine's
central claim.

Where Mod-B splits *time*, Mod-A splits *names* into two disjoint arms (X1, X2)
and asks: does a signal that ranks names in one half also rank the (different)
names in the other half, on MARKET-NEUTRALIZED returns? Three things are
computed and -- per the Section 4.3 mixing-ban -- kept strictly separate:

1. ``conjugate_agreement`` (want STRONG): per-arm residual rank-IC significance,
   cross-arm sign-consistency, and the real CSCV bucket-transfer PBO. PASS only
   if all three clear their Stage-0 bars (t > 2.0 both arms, sign >= 0.90,
   PBO < 0.50).
2. ``residual_arm_correlation`` (want LOW): a DIFFERENT computation -- the
   time-series co-movement of the two arms' active returns, flagged against a
   permutation null (not a fixed threshold).

The split itself is liquidity-stratified pair-randomization (default): rank
eligible names by look-ahead-safe trailing ADV, pair adjacent ranks, and let a
seed-driven coin send one of each pair to each arm. Every split is therefore
liquidity-balanced by construction, yet the split space (2^n_pairs) dwarfs R, so
R seeds sample a rich distribution rather than one near-degenerate point.

Beta is estimated on the FULL panel once and sliced per arm: because each name's
beta depends only on its own past and the market (``neutralizer.rolling_beta``
takes no arm argument), the name-split cannot change a residual -- arm
independence is structural, not promised (a unit test pins it).
"""
from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt
import pandas as pd

from . import config
from .confidence import assess_agreement_confidence
from .contracts import DialConfig, NameSplitMethod, Panel, SortDepth, SplitSpec
from .data_adapter import continuous_basket, forward_return
from .neutralizer import market_neutral_forward
from .pbo import cscv_pbo
from .signal_protocol import Signal, assert_pm1_compliant
from .stats import nw_tstat

_DEPTH_FRACTION: dict[SortDepth, float] = {
    SortDepth.TERCILE: 1.0 / 3.0,
    SortDepth.DECILE: 0.10,
}


# --------------------------------------------------------------------------- #
# small numeric helpers (NaN-robust without RuntimeWarnings)                  #
# --------------------------------------------------------------------------- #
def _finite(values: list[float]) -> npt.NDArray[np.float64]:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def _safe_median(values: list[float]) -> float:
    a = _finite(values)
    return float(np.median(a)) if a.size else float("nan")


def _safe_mean(values: list[float]) -> float:
    a = _finite(values)
    return float(np.mean(a)) if a.size else float("nan")


def _stack_mean(rows: list[npt.NDArray[np.float64]], n_buckets: int) -> npt.NDArray[np.float64]:
    """Column-wise time-mean of stacked per-date bucket rows, all-NaN columns -> NaN."""
    if not rows:
        return np.full(n_buckets, np.nan)
    mat = np.vstack(rows)
    out = np.full(n_buckets, np.nan)
    keep = ~np.all(np.isnan(mat), axis=0)
    if keep.any():
        out[keep] = np.nanmean(mat[:, keep], axis=0)
    return out


# --------------------------------------------------------------------------- #
# name-splitting (Section 3.2): liquidity-stratified pair-randomization        #
# --------------------------------------------------------------------------- #
def _trailing_adv(panel: Panel, names: list[str], asof: pd.Timestamp, *, trailing: int) -> pd.Series:
    """Look-ahead-safe trailing median traded value per name (knowable as-of ``asof``)."""
    window = panel.value_tl.loc[panel.value_tl.index <= asof, names].tail(trailing)
    return window.median(skipna=True)


def _eligible_names(
    panel: Panel,
    names: list[str],
    split_asof: pd.Timestamp,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    *,
    floor_tl: float,
    trailing: int,
) -> list[str]:
    """Names that clear the liquidity floor as-of the split AND trade continuously
    over the evaluation window (survivorship-honest)."""
    adv = _trailing_adv(panel, names, split_asof, trailing=trailing)
    liquid = [str(n) for n in adv[adv >= floor_tl].dropna().index]
    return continuous_basket(panel, d0, d1, names=liquid, min_cov=1.0)


def _pair_randomize(ranked: list[str], rng: np.random.Generator) -> tuple[list[str], list[str]]:
    """Adjacent-pair coin split of an ADV-ranked list -> two liquidity-balanced arms."""
    n_pairs = len(ranked) // 2
    coins = rng.integers(0, 2, size=n_pairs)
    x1: list[str] = []
    x2: list[str] = []
    for p in range(n_pairs):
        a, b = ranked[2 * p], ranked[2 * p + 1]
        if coins[p] == 0:
            x1.append(a)
            x2.append(b)
        else:
            x1.append(b)
            x2.append(a)
    return sorted(x1), sorted(x2)  # leftover odd (least-liquid) name dropped to keep balance


def _random_halves(pool: list[str], rng: np.random.Generator) -> tuple[list[str], list[str]]:
    """Plain seed-fixed random halves (the ``RANDOM`` alternative / the corr null)."""
    perm = rng.permutation(np.asarray(pool, dtype=object))
    half = len(perm) // 2
    return sorted(perm[:half].tolist()), sorted(perm[half:].tolist())


def name_splits(
    panel: Panel,
    eligible: list[str],
    *,
    spec: SplitSpec,
    split_asof: pd.Timestamp,
) -> list[tuple[list[str], list[str]]]:
    """The R disjoint name-splits for the conjugate test.

    ``LIQUIDITY`` (default): ADV-stratified pair-randomization -- every arm is
    liquidity-balanced by construction so an X1<->X2 difference cannot be a
    liquidity artifact. ``RANDOM``: seed-fixed halves. Alphabetical/ordered
    assignment is FORBIDDEN (both paths shuffle). Splits share one parent seed so
    the whole set is reproducible; the children are independent streams. The ADV
    ranking is taken as-of ``split_asof`` (look-ahead-safe)."""
    adv = _trailing_adv(panel, eligible, split_asof, trailing=config.LIQUID_TRAILING_DAYS)
    ranked = [str(n) for n in adv.sort_values(ascending=False).dropna().index]
    children = np.random.SeedSequence(spec.seed).spawn(spec.R)
    splits: list[tuple[list[str], list[str]]] = []
    for child in children:
        rng = np.random.default_rng(child)
        if spec.name_split_method is NameSplitMethod.RANDOM:
            splits.append(_random_halves(eligible, rng))
        else:
            splits.append(_pair_randomize(ranked, rng))
    return splits


# --------------------------------------------------------------------------- #
# per-arm primitives (residual returns sliced from the full-panel neutralizer) #
# --------------------------------------------------------------------------- #
def _arm_active_series(
    scores: pd.DataFrame,
    resid_fwd: pd.DataFrame,
    arm: list[str],
    frac: float,
    *,
    name: str,
    min_names: int,
) -> pd.Series:
    """Per-date arm active return = (top-tilt EW) - (arm EW), on residual returns.

    Vectorized over dates: a per-date cross-sectional rank picks the top ``frac``
    of the arm; the tilt is a fully-invested long-only EW re-tilt (PM-1 compliant
    by construction, asserted once on a representative date), and the arm-EW
    subtraction is a benchmark, not a short leg."""
    sc = scores.reindex(columns=arm)
    fr = resid_fwd.reindex(columns=arm)
    mask = sc.notna() & fr.notna()
    counts = mask.sum(axis=1)
    valid = counts >= min_names
    if not bool(valid.any()):
        return pd.Series(dtype=float)

    sc_v, fr_v, mask_v, cnt_v = sc[valid], fr[valid], mask[valid], counts[valid]
    ranks = sc_v.where(mask_v).rank(axis=1, ascending=False, method="first")
    k = (cnt_v * frac).apply(lambda c: max(1, int(c)))
    is_top = ranks.le(k, axis=0) & mask_v

    first = is_top.index[0]
    top0 = is_top.columns[is_top.loc[first].to_numpy()]
    assert_pm1_compliant(pd.Series(1.0 / len(top0), index=top0), name=name)

    port = fr_v.where(is_top).mean(axis=1)
    bench = fr_v.where(mask_v).mean(axis=1)
    return (port - bench).dropna().sort_index()


def _arm_bucket_means(
    scores: pd.DataFrame,
    resid_fwd: pd.DataFrame,
    arm: list[str],
    *,
    n_buckets: int,
    min_per_bucket: int,
) -> npt.NDArray[np.float64]:
    """Time-mean residual active return per WITHIN-ARM signal decile.

    Each date the arm's names are ranked by the signal and cut into ``n_buckets``
    equal-count buckets; a bucket's active return is its EW residual minus the arm
    EW, and the per-bucket series is averaged over time. A bucket that cannot
    field ``min_per_bucket`` names on a date is NaN there (the degenerate-bucket
    guard -- the cross-sectional analog of the NW near-zero-variance guard).

    Buckets are formed INDEPENDENTLY in each arm: decile ``k`` is the k-th
    signal-rank region of THAT arm, so comparability across arms is by rank-region
    (which is exactly what transfers for a real signal) -- NOT by shared name
    membership. A global union bucketing would instead split one decile into two
    complementary arm-subsets, injecting a spurious negative IS<->OOS coupling
    (under the null PBO climbs to ~0.85 instead of the ~0.5 the noise fixture
    pins); independent per-arm buckets keep the arms' bucket series independent
    under the null, which is the CSCV construction.
    """
    sc = scores.reindex(columns=arm)
    fr = resid_fwd.reindex(columns=arm)
    mask_df = sc.notna() & fr.notna()
    mask = mask_df.to_numpy()
    n_valid = mask.sum(axis=1)
    ranks = sc.where(mask_df).rank(axis=1, method="first").to_numpy()  # 1..n_valid, NaN if masked
    nv = np.where(n_valid > 0, n_valid, 1).astype(float)[:, None]
    bfloat = (ranks - 1.0) * n_buckets / nv
    bucket = np.where(np.isfinite(bfloat), np.minimum(np.floor(bfloat), n_buckets - 1), -1.0)
    bucket = bucket.astype(np.intp)
    resid = fr.to_numpy(dtype=float)

    with np.errstate(invalid="ignore", divide="ignore"):
        arm_ew = np.where(mask, resid, 0.0).sum(axis=1) / np.where(n_valid > 0, n_valid, np.nan)

    rows: list[npt.NDArray[np.float64]] = []
    for k in range(n_buckets):
        sel = mask & (bucket == k)
        cnt = sel.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            bmean = np.where(sel, resid, 0.0).sum(axis=1) / np.where(cnt > 0, cnt, np.nan)
        rows.append(np.where(cnt >= min_per_bucket, bmean - arm_ew, np.nan))
    # rows is column-per-bucket; transpose to per-date rows for the time-mean.
    return _stack_mean(list(np.vstack(rows).T), n_buckets)


def _arm_rank_ic(
    scores: pd.DataFrame,
    resid_fwd: pd.DataFrame,
    arm: list[str],
    *,
    min_names: int,
) -> npt.NDArray[np.float64]:
    """Vectorized per-date cross-sectional Spearman rank-IC within one arm.

    Spearman rho is Pearson correlation on average-tie ranks; here it is computed
    for ALL dates at once (pandas row-rank + a masked per-row Pearson) instead of
    a per-date ``scipy.stats.spearmanr`` call -- mathematically identical, but it
    turns the 2*R per-date scipy loop (the dominant cost) into a handful of array
    ops. A date with fewer than ``min_names`` jointly-finite names yields NaN (the
    same drop rule as ``stats.rank_ic_series``); ``nw_tstat`` ignores the NaNs.
    Rank order follows the (sorted) date index, so the NW autocovariance lags line
    up exactly as in the per-date series.
    """
    sc = scores.reindex(columns=arm)
    fr = resid_fwd.reindex(columns=arm)
    joint = sc.notna() & fr.notna()
    n_valid = joint.to_numpy().sum(axis=1)
    rsc = sc.where(joint).rank(axis=1).to_numpy(dtype=float)  # NaN-positions stay NaN
    rfr = fr.where(joint).rank(axis=1).to_numpy(dtype=float)
    with np.errstate(invalid="ignore"):
        a = rsc - np.nanmean(rsc, axis=1, keepdims=True)
        b = rfr - np.nanmean(rfr, axis=1, keepdims=True)
    a = np.where(np.isfinite(a), a, 0.0)
    b = np.where(np.isfinite(b), b, 0.0)
    num = np.sum(a * b, axis=1)
    den = np.sqrt(np.sum(a * a, axis=1) * np.sum(b * b, axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        ic = num / den
    return np.where((n_valid >= min_names) & (den > 0.0), ic, np.nan)


# --------------------------------------------------------------------------- #
# Section 4.1 -- conjugate agreement (want STRONG)                            #
# --------------------------------------------------------------------------- #
def conjugate_agreement(
    scores: pd.DataFrame,
    resid_fwd: pd.DataFrame,
    splits: list[tuple[list[str], list[str]]],
    *,
    lag: int,
    n_buckets: int = config.PBO_N_BUCKETS,
    min_per_bucket: int = config.MIN_NAMES_PER_BUCKET,
    min_names: int = config.MIN_NAMES_CROSS_SECTION,
    t_min: float = config.AGREEMENT_CROSS_IC_T_MIN,
    sign_min: float = config.SIGN_CONSISTENCY_MIN,
    pbo_max: float = config.PBO_THRESHOLD,
) -> dict[str, object]:
    """The Section 4.1 three-part PASS bar on market-neutralized residual returns.

    For each split & arm: the residual cross-sectional rank-IC series -> NW t.
    Aggregated over the R splits:
    - ``agreement_t_cross_median`` = min over the two directions of median_R(t_IC)
      (per-arm OOS significance; for a parameter-free signal "build in X1 /
      evaluate in X2" reduces to the IC realized in the evaluation arm),
    - ``sign_consistency`` = frac_R(sign(meanIC_X1) == sign(meanIC_X2)),
    - ``pbo`` = mean over both directions of the real CSCV bucket-transfer PBO.
    PASS = all three clear their bars.
    """
    if not splits:
        return _agreement_guard()

    t_x1: list[float] = []
    t_x2: list[float] = []
    sign_agree: list[float] = []
    m_is_a: list[npt.NDArray[np.float64]] = []  # direction X1->X2 (IS=X1)
    m_oos_a: list[npt.NDArray[np.float64]] = []
    m_is_b: list[npt.NDArray[np.float64]] = []  # direction X2->X1 (IS=X2)
    m_oos_b: list[npt.NDArray[np.float64]] = []

    for x1, x2 in splits:
        ic1 = _arm_rank_ic(scores, resid_fwd, x1, min_names=min_names)
        ic2 = _arm_rank_ic(scores, resid_fwd, x2, min_names=min_names)
        t_x1.append(nw_tstat(ic1, lag=lag))
        t_x2.append(nw_tstat(ic2, lag=lag))
        m1 = float(np.nanmean(ic1)) if np.isfinite(ic1).any() else 0.0
        m2 = float(np.nanmean(ic2)) if np.isfinite(ic2).any() else 0.0
        s1, s2 = float(np.sign(m1)), float(np.sign(m2))
        sign_agree.append(1.0 if (s1 != 0.0 and s1 == s2) else 0.0)
        mx1 = _arm_bucket_means(scores, resid_fwd, x1, n_buckets=n_buckets, min_per_bucket=min_per_bucket)
        mx2 = _arm_bucket_means(scores, resid_fwd, x2, n_buckets=n_buckets, min_per_bucket=min_per_bucket)
        m_is_a.append(mx1)
        m_oos_a.append(mx2)
        m_is_b.append(mx2)
        m_oos_b.append(mx1)

    median_t_x1 = _safe_median(t_x1)
    median_t_x2 = _safe_median(t_x2)
    agreement_t_cross_median = (
        float(min(median_t_x1, median_t_x2))
        if math.isfinite(median_t_x1) and math.isfinite(median_t_x2)
        else float("nan")
    )
    sign_consistency = _safe_mean(sign_agree)
    pbo = _safe_mean(
        [cscv_pbo(np.vstack(m_is_a), np.vstack(m_oos_a)), cscv_pbo(np.vstack(m_is_b), np.vstack(m_oos_b))]
    )

    agreement_pass = bool(
        (median_t_x1 > t_min)
        and (median_t_x2 > t_min)
        and (sign_consistency >= sign_min)
        and (pbo < pbo_max)
    )
    return {
        "agreement_pass": agreement_pass,
        "agreement_t_cross_median": agreement_t_cross_median,
        "median_t_x1": median_t_x1,
        "median_t_x2": median_t_x2,
        "sign_consistency": sign_consistency,
        "pbo": pbo,
    }


def _agreement_guard() -> dict[str, object]:
    return {
        "agreement_pass": False,
        "agreement_t_cross_median": float("nan"),
        "median_t_x1": float("nan"),
        "median_t_x2": float("nan"),
        "sign_consistency": float("nan"),
        "pbo": float("nan"),
    }


# --------------------------------------------------------------------------- #
# Section 4.2 -- residual arm correlation (want LOW) -- SEPARATE computation   #
# --------------------------------------------------------------------------- #
def arm_active_correlation(a_x1: pd.Series, a_x2: pd.Series) -> float:
    """Pearson correlation of two arms' active-return series on shared dates."""
    joined = pd.concat([a_x1, a_x2], axis=1, join="inner").dropna()
    if len(joined) < 3:
        return float("nan")
    return float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))


def residual_arm_correlation(
    observed_corr: float,
    null_corrs: npt.ArrayLike,
    *,
    pctile: int = config.RESIDUAL_CORR_NULL_PCTILE,
) -> tuple[float, bool]:
    """Flag the observed arm co-movement against a PERMUTATION null (not a fixed
    threshold). ``residual_corr_flag = observed > null_pctile``; without a usable
    null (or a non-finite observed) the flag is False (cannot reject)."""
    null = _finite(list(np.asarray(null_corrs, dtype=float)))
    if null.size == 0 or not math.isfinite(observed_corr):
        return (observed_corr, False)
    threshold = float(np.percentile(null, pctile))
    return (observed_corr, bool(observed_corr > threshold))


# --------------------------------------------------------------------------- #
# orchestration                                                               #
# --------------------------------------------------------------------------- #
def _returns_basis(panel: Panel, dial: DialConfig) -> pd.DataFrame:
    return panel.tr_gross if str(dial.return_basis) == "tr_index_gross" else panel.tr_net


def run_moda(
    panel: Panel, signal: Signal, spec: SplitSpec, dial: DialConfig
) -> dict[str, object]:
    """Run the Mod-A conjugate core and return a result dict (Section 4.1/4.2).

    Pipeline: enforce market-neutralization -> market-neutral forward residuals
    (beta once on the full panel, sliced per arm) -> R liquidity-stratified
    name-splits -> ``conjugate_agreement`` (want STRONG) + ``residual_arm_correlation``
    (want LOW, permutation null). The two verdicts live in separate fields
    (Section 4.3 mixing-ban). A degenerate universe raises a guard message and
    returns ``agreement_pass=False`` rather than a misleading number.
    """
    dial.requires_market_neutralization(spec.split_mode)
    guards: list[str] = []
    dates = panel.dates
    h = int(signal.construction_window)
    lag = dial.nw_lag_for(panel.frequency)
    frac = _DEPTH_FRACTION.get(spec.sort_depth, 1.0 / 3.0)
    mn = config.MIN_NAMES_CROSS_SECTION

    tr = _returns_basis(panel, dial)
    daily_ret = tr.pct_change()
    mkt = panel.market.reindex(dates)
    daily_mkt = mkt.pct_change()
    fwd = forward_return(panel, h, basis=str(dial.return_basis))
    fwd_mkt = mkt.shift(-h) / mkt - 1.0
    resid_fwd = market_neutral_forward(
        fwd, fwd_mkt, daily_ret, daily_mkt, window=dial.beta_window, min_coverage=config.BETA_MIN_COVERAGE
    )

    scores = pd.DataFrame.from_dict(
        {asof: signal.scores(panel, panel.names, asof) for asof in dates}, orient="index"
    )

    eval_mask = resid_fwd.notna().sum(axis=1) >= mn
    eval_dates = resid_fwd.index[eval_mask]
    if eval_dates.empty:
        guards.append("no evaluation date clears the cross-section floor after beta warm-up")
        return _guard_result(guards)
    d0, d1 = eval_dates[0], eval_dates[-1]
    scores_e = scores.loc[eval_dates]
    resid_e = resid_fwd.loc[eval_dates]

    eligible = _eligible_names(
        panel, panel.names, split_asof=d0, d0=d0, d1=d1,
        floor_tl=spec.split_arm_floor_tl, trailing=config.LIQUID_TRAILING_DAYS,
    )
    if len(eligible) < 2 * spec.min_names_per_arm:
        guards.append(
            f"only {len(eligible)} eligible names; need >= {2 * spec.min_names_per_arm} "
            f"for two arms of {spec.min_names_per_arm} (Section 3.3)"
        )
        return _guard_result(guards)

    splits = name_splits(panel, eligible, spec=spec, split_asof=d0)
    agreement = conjugate_agreement(
        scores_e, resid_e, splits, lag=lag,
        t_min=dial.agreement_t_min, sign_min=dial.sign_consistency_min, pbo_max=dial.pbo_max,
    )

    obs_corrs = [
        arm_active_correlation(
            _arm_active_series(scores_e, resid_e, x1, frac, name=signal.name, min_names=mn),
            _arm_active_series(scores_e, resid_e, x2, frac, name=signal.name, min_names=mn),
        )
        for x1, x2 in splits
    ]
    observed_corr = _safe_mean(obs_corrs)

    null_children = np.random.SeedSequence(spec.seed + 1_000_000).spawn(config.RESIDUAL_NULL_RESAMPLES)
    null_corrs: list[float] = []
    for child in null_children:
        nx1, nx2 = _random_halves(eligible, np.random.default_rng(child))
        a1 = _arm_active_series(scores_e, resid_e, nx1, frac, name=signal.name, min_names=mn)
        a2 = _arm_active_series(scores_e, resid_e, nx2, frac, name=signal.name, min_names=mn)
        null_corrs.append(arm_active_correlation(a1, a2))
    resid_corr, resid_flag = residual_arm_correlation(
        observed_corr, null_corrs, pctile=dial.residual_corr_null_pctile
    )

    arm_sizes = [len(x1) for x1, _ in splits] + [len(x2) for _, x2 in splits]
    min_arm = int(min(arm_sizes)) if arm_sizes else 0
    # RR-Y1-009 verdict-confidence: data-driven single-regime detection (eval window
    # entirely on one side of the frozen REGIME_SPLIT boundary). Gameable-proof -- it
    # would have flagged RR-Y1-008's 2024+ window even though its hedef_rejim said "all".
    regime_split = pd.Timestamp(config.REGIME_SPLIT)
    single_regime = bool(d1 < regime_split or d0 >= regime_split)
    confidence, confidence_reasons = assess_agreement_confidence(
        min_arm_size=min_arm,
        n_splits=len(splits),
        residual_corr_flag=bool(resid_flag),
        single_regime=single_regime,
        arm_floor=config.AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE,
        r_floor=config.AGREEMENT_MIN_R_FOR_HIGH_CONFIDENCE,
    )
    return {
        **agreement,
        "residual_cross_sectional_corr": resid_corr,
        "residual_corr_flag": resid_flag,
        "agreement_confidence": confidence,
        "agreement_confidence_reasons": confidence_reasons,
        "n_splits": len(splits),
        "min_arm_size": min_arm,
        "n_eligible": len(eligible),
        "n_eval_dates": int(eval_dates.size),
        "split_method": str(spec.name_split_method),
        "nw_lag": int(lag),
        "guard_messages": tuple(guards),
    }


def _guard_result(guards: list[str]) -> dict[str, object]:
    """Uniform degenerate-universe result: every verdict False/NaN + the reasons."""
    # A degenerate universe never formed valid arms -> the same helper, fed the
    # zero-breadth inputs, naturally grades it 'low' (arm=0/R=0). No special-casing.
    confidence, confidence_reasons = assess_agreement_confidence(
        min_arm_size=0,
        n_splits=0,
        residual_corr_flag=False,
        single_regime=False,
        arm_floor=config.AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE,
        r_floor=config.AGREEMENT_MIN_R_FOR_HIGH_CONFIDENCE,
    )
    return {
        **_agreement_guard(),
        "residual_cross_sectional_corr": float("nan"),
        "residual_corr_flag": False,
        "agreement_confidence": confidence,
        "agreement_confidence_reasons": confidence_reasons,
        "n_splits": 0,
        "min_arm_size": 0,
        "guard_messages": tuple(guards),
    }
