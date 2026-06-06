# RR-Y1-005 Validation Engine — Operator Guide and Mathematical Model

> **Scope:** the `src/engine/` package — a general-purpose, tunable, post-hoc-auditable
> strategy-validation harness.
> **Design:** RR-Y1-005-TEST-MOTORU-TASARIM v0.2 (what/why) · **Math:** RR-Y1-005B-MATEMATIKSEL-SPEC v1.1 (formal core)
> **Version:** `src.engine.__version__` · **Author:** Cagan <!-- hygiene-allow -->

---

## 0. What does it do, in one sentence?

The engine takes a **prototype signal** and reports whether it is "real or overfit"
**without collapsing it to a single pass/fail bit** — as a **Section-7 output VECTOR**:

```
harness(panel, signal, split_spec, dial_config) -> EngineOutput
```

The output is not a decision but an **evidence board**: returns/cost, significance
(PBO/DSR/NW-t), conjugate agreement, regime breakdown, parameter plateau, and the
**confidence qualifier** of each measurement. A human reads it and decides; the engine
only produces honest numbers.

### Design principles (immutable)

| Principle | Meaning |
|-----------|---------|
| **Strangler** | The engine imports committed motors (`src/screening`, `src/backtest`) **read-only**; it touches no committed file and imports no lab code. |
| **Vector output** | `EngineOutput` is not a bit but a ~30-field vector. The pass/fail interpretation belongs to the reader. |
| **Partial-leg contract** | If a leg (Mod-A/B/C) cannot complete, the harness **never raises**; the corresponding fields stay `None` and the reason is recorded in `guard_messages`. |
| **PM-1 law** | The engine never evaluates a cash-gate signal. Idle = fully-invested equal-weight; a trigger re-tilts WITHIN the basket. |
| **Stage-0 freeze** | The hypothesis is frozen BEFORE measurement. When `stage0_path` is given, the engine **refuses to run** if the file is absent/drifted. |
| **Anti-slop golden** | The C12 real-data determinism anchor (NW-t gross 6.928414 / net -6.274774 @ lag10, n=1375) is reproduced byte-for-byte. |

---

## 1. Architecture and data flow

```
                         ┌─────────────────────────────────────────────┐
   data_adapter.load_panel ──► Panel  (close/tr_gross/tr_net/value_tl/   │
                         │            market/tufe/tlref, wide frames)    │
                         └─────────────────────────────────────────────┘
                                          │
   Signal (protocol: scores(panel,names,asof) -> Series)                 │
   SplitSpec  (split structure: mode, embargo, R, CPCV, holdout_start)   │
   DialConfig (8 tuning dials)                                           │
                                          ▼
                         ┌──────────────  harness()  ──────────────┐
                         │  dispatch by split_mode:                 │
                         │   A   -> run_moda  (name-split conjugate)│
                         │   B   -> run_modb  (temporal CPCV)       │
                         │   A+B -> both (PANEL)                     │
                         │   C   -> run_modc  (intra-regime holdout)│
                         │                                          │
                         │  + always: tradeable tilt returns/cost   │
                         │    (D-207 stack), benchmark floor        │
                         │    (TUFE/TLREF), per-regime, plateau     │
                         └──────────────────┬───────────────────────┘
                                            ▼
                                       EngineOutput  (Section-7 vector)
```

### Module map

| Module | Responsibility |
|--------|----------------|
| `contracts.py` | All types: enums, `Panel`, `SplitSpec`, `DialConfig`, `EngineOutput`. |
| `config.py` | Frozen structural constants + dial defaults (single source of truth). |
| `data_adapter.py` | `load_panel`, `liquid_names`, `forward_return` (forward return). |
| `stats.py` | The mathematical core: `rank_ic_series`, `ic_ir`, `nw_tstat` (Newey-West HAC). |
| `neutralizer.py` | `rolling_beta` (look-ahead-safe), `residualize`, `market_neutral_forward`. |
| `moda.py` | Mod-A: liquidity-stratified name-split conjugate core + residual correlation. |
| `modb.py` | Mod-B: temporal CPCV → OOS Sharpe distribution → PBO/DSR. |
| `modc.py` | Mod-C: intra-regime forward time-holdout persistence (RR-Y1-010). |
| `pbo.py` | Real CSCV median-rank PBO (Lopez de Prado) — the one the Mod-A core uses. |
| `dsr.py` | DSR trial-count deflation benchmark (Bailey-LdP E[max] order statistic). |
| `benchmark.py` | Real-return deflate + benchmark-floor: real return > max(TUFE, TLREF). |
| `confidence.py` | Mod-A confidence qualifier (`assess_agreement_confidence`). |
| `holdout_confidence.py` | Mod-C confidence qualifier (`assess_holdout_confidence`). |
| `signal_protocol.py` | The `Signal` protocol + `assert_pm1_compliant` (PM-1 guard). |
| `stage0_validator.py` | Stage-0 pre-registration: refuse-if-absent + snapshot content-hash guard. |
| `lockbox.py` | Single-shot held-out subset seal. |
| `harness.py` | The top-level assembler — the single entry point. |

---

## 2. Quick start

```python
import pandas as pd
from src.engine.contracts import (
    DialConfig, Frequency, Panel, SplitMode, SplitSpec,
)
from src.engine.data_adapter import load_panel
from src.engine.harness import harness

# 1) Load the panel (clean_universe + snapshots; NOT DataHub -- strangler)
panel = load_panel()                       # from config.PRICES_PARQUET

# 2) Define a prototype signal (zero-discretion cross-sectional scorer)
class MomentumSignal:
    name = "mom_12_1"
    construction_window = 21               # = Mod-B embargo h (Section 3.4)
    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        px = panel.close.loc[:asof, names]
        return (px.iloc[-1] / px.iloc[-self.construction_window] - 1.0)

# 3) Split structure + dials
spec = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY)
dials = DialConfig()                        # frozen v1.1 defaults

# 4) Run
out = harness(panel, MomentumSignal(), spec, dials)

print(out.agreement_pass, out.agreement_confidence)
print(out.net_active_ann, out.beats_benchmark_floor)
print(out.pbo, out.dsr, out.nw_t)
```

For a **pre-registered run**, pass `stage0_path`:

```python
out = harness(panel, sig, spec, dials, stage0_path="data/stage0/RR-Y1-XXX.json")
# If the file is absent or the snapshot content-hash has drifted -> Stage0Error (the engine refuses)
```

---

## 3. Contracts

### 3.1 `Panel` — loaded data

All frames are **wide**: index=date, columns=symbol.

| Field | Type | Description |
|-------|------|-------------|
| `close` | DataFrame | Adjusted close. |
| `tr_gross` / `tr_net` | DataFrame | Total-return index (dividends reinvested), gross/net. |
| `value_tl` | DataFrame | Daily traded value (liquidity proxy). |
| `membership` | dict | PIT index membership (`{"bist100": 0/1, ...}`). |
| `market` | Series | Market index level (XU100); returns = `pct_change`. |
| `tufe` / `tlref` | Series | CPI / TLREF level series (for the benchmark floor). |
| `frequency` | Frequency | `DAILY` (default) / `MONTHLY`. |

Helper properties: `panel.dates`, `panel.names`. `eq=False` because DataFrame `__eq__`
is element-wise (an auto-generated equality would raise "ambiguous truth value").

### 3.2 `SplitSpec` — split structure (frozen at Stage-0)

| Field | Default | Meaning |
|-------|---------|---------|
| `split_mode` | — | `A` / `B` / `A+B` / `C`. |
| `frequency` | — | `DAILY` / `MONTHLY`. |
| `embargo_h` | `1` | = the signal's construction-window (Section 3.4); `>= 1`. |
| `R` | `50` | Seed-fixed name-split count (Mod-A). |
| `seed` | `0` | Reproducibility seed. |
| `cpcv_n` / `cpcv_k` | `10` / `2` | Mod-B CPCV blocks; `k < n` required. |
| `split_arm_floor_tl` | `1e7` | Per-arm liquidity floor (ADV). |
| `sort_depth` | `TERCILE` | `tercile` / `decile` / `topN`. |
| `min_names_per_arm` | `50` | Section 3.3: each arm >= 50 names. |
| `name_split_method` | `LIQUIDITY` | `liquidity` (ADV-stratified) / `random`. |
| `holdout_start` | `None` | Mod-C boundary (ISO date). **Required** in `C` mode. |

`__post_init__` guards: `embargo_h >= 1`; `cpcv_k < cpcv_n`; `R >= 1`;
`holdout_start` required in `C` mode; **monthly → Mod-A only** (temporal-CPCV is
power-poor at monthly frequency, Section 3.6).

### 3.3 `DialConfig` — the 8 tuning dials (Section 5)

Dials 2 (split-mode), 4 (embargo) and 8 (arm-floor + sort-depth) live in `SplitSpec`
(they are split structure); the rest live here:

| Dial | Field | Default | Role |
|------|-------|---------|------|
| 1 | `psi` | `spearman` | Cross-sectional rank-IC type. |
| 3 | `neutralization` | `("market",)` | Neutralization factors (`market` is the minimum, mandatory for Mod-A). |
| — | `return_basis` | `tr_index_gross` | Gross/net total-return basis. |
| 7 | `cut_policies` | anchored/rolling/expanding | Cut-family (not wired in Faz-3). |
| 5 | `use_pbo` | `True` | Whether the PBO gate is on. |
| 6 | `use_dsr` | `True` | Whether the DSR gate is on. |
| — | `nw_lag` | `None` | `None` → resolved from frequency (daily 5 / monthly 3). |
| — | `winsorize` | `(0.01, 0.99)` | Winsorize bounds. |
| — | `beta_window` | `126` | Beta estimation window (days). |
| — | `agreement_t_min` | `2.0` | Conjugate t threshold. |
| — | `sign_consistency_min` | `0.90` | Sign-consistency floor. |
| — | `pbo_max` | `0.50` | Real CSCV PBO ceiling. |
| — | `dsr_min` | `0.95` | DSR floor. |
| — | `residual_corr_null_pctile` | `95` | Residual correlation null percentile. |

`requires_market_neutralization(mode)`: raises if `market` neutralization is absent in
Mod-A / PANEL. `nw_lag_for(frequency)`: returns daily=5 / monthly=3 when `nw_lag` is None.

### 3.4 `EngineOutput` — the Section-7 output vector

Every field defaults to `None`/empty; even a partial run is a valid object.

| Group | Fields |
|-------|--------|
| **Returns** | `gross_active_ann`, `net_active_ann`, `cost_ann`, `tax_ann`, `mean_rt_bps` |
| **Fair-null** (None in Faz-3) | `null_percentile`, `mirror_active_ann` |
| **Benchmark floor** | `real_active_ann`, `benchmark_floor_ann`, `beats_benchmark_floor` |
| **Significance** | `pbo`, `deflated_oos_t` (None), `dsr`, `dsr_n_trials`, `nw_t` |
| **Conjugate (Mod-A)** | `agreement_pass`, `agreement_t_cross_median`, `sign_consistency`, `residual_cross_sectional_corr`, `residual_corr_flag` |
| **Mod-A confidence** | `agreement_confidence`, `agreement_confidence_reasons` |
| **Holdout (Mod-C)** | `holdout_persistence_pass`, `holdout_ic_t/mean`, `train_ic_t/mean`, `holdout_sign_consistent`, `n_holdout_obs`, `n_train_obs`, `holdout_confidence`, `holdout_confidence_reasons` |
| **Regime & plateau** | `per_regime`, `plateau_map` |
| **Guards** | `pm1_guard_raised`, `guard_messages` |
| **Provenance** | `n_obs`, `n_names`, `split_mode`, `notes` |

---

## 4. Mathematical model

The notation below is in exact correspondence with `src/engine/stats.py`,
`neutralizer.py`, `moda.py`, `pbo.py`, `dsr.py`, `benchmark.py`.

### 4.1 Cross-sectional rank-IC and its significance

For each date `t`, the **Spearman rank correlation** between the signal scores `s_{i,t}`
and the forward residual returns `r_{i,t}` is computed over the eligible name set:

```
IC_t = corr_spearman( rank(s_{·,t}), rank(r_{·,t}) ),   |{i: both finite}| >= 30
```

(`MIN_NAMES_CROSS_SECTION = 30`; a date that fails the floor is skipped.) This gives the
daily IC series `{IC_t}` (`rank_ic_series`).

**Information Ratio** (`ic_ir`): the signal-to-noise ratio of the IC series,

```
IR = mean_t(IC) / std_t(IC),   std ddof=1
```

**Newey-West HAC t-statistic** (`nw_tstat`) — the autocorrelation-robust t-value of the
IC series mean. HAC variance with a Bartlett kernel (POPULATION-variance convention,
consistent with the C12 golden):

```
e   = IC - mean(IC)
γ_0 = (e·e) / n
γ_k = (e[k:]·e[:-k]) / n,                k = 1..L
s   = γ_0 + 2 · Σ_{k=1}^{L} (1 - k/(L+1)) · γ_k         (Bartlett weights)
t   = mean(IC) / sqrt(s / n)
```

Guards:
- `n < L + 3` → `NaN` (insufficient sample for HAC).
- **FAZ-4 near-zero-variance floor:** `s <= eps · mean^2` (eps = `1e-12`) → `NaN`.
  A numerically-constant input can have a tiny-but-positive HAC variance (`s ~ 1e-32`)
  from FP rounding that slips past the `s <= 0` guard and yields an explosive spurious t.
  The relative-variance floor fires only on degenerate input; the C12 golden
  (~1e2 relative variance) and the d211/d213 equivalence never trip it.

`L` (lag) is resolved from frequency: daily=5, monthly=3 (`NW_LAG_DAILY/MONTHLY`).

### 4.2 Market-beta neutralization (look-ahead-safe)

For a factor to be meaningful, the market-beta effect is removed (Section 3.5, **mandatory**
in Mod-A). `rolling_beta` **never leaks the future**: a `shift(1)` is applied before the
window, so the beta on day `t` rests only on `t-1` and earlier.

```
β_{i,t} = Cov_{W}( r^{daily}_{i}, r^{daily}_{mkt} ) / Var_{W}( r^{daily}_{mkt} )
```

W = `BETA_WINDOW_DAYS = 126`, at least `0.8·W` observations (`BETA_MIN_COVERAGE`),
population variance. Residualization (no intercept):

```
r̃_{i,t} = r_{i,t} - β_{i,t} · r_{mkt,t}            (residualize)
```

**Forward direction** (`market_neutral_forward`): a beta estimated from PAST daily returns
is applied to the FORWARD market move → the forward residual return `resid_fwd`. This is the
series on which Mod-A and Mod-C compute the IC.

### 4.3 The Conjugate-Universes Model (formal)

This is the formal underpinning of Mod-A: rather than splitting *time*, the **investable
universe is split into two disjoint name-arms** and we ask whether a signal that ranks the
names in one half also ranks the (different) names in the other half, on market-neutralized
returns.

**Eligible universe.** At split-time `t_split`, the eligible set is

```
N = { i : ADV_i(t_split) >= F_liq  AND  i trades continuously over [d0, d1] }
```

where `ADV_i(t_split)` is the look-ahead-safe trailing median traded value and
`F_liq = split_arm_floor_tl = 1e7`:

```
ADV_i(t_split) = median{ V_{i,τ} : τ <= t_split, last L_adv observations },   L_adv = 63
```

**Liquidity-stratified pair-randomization.** Order `N` by descending ADV,
`π = (π_1, ..., π_n)` with `ADV_{π_1} >= ADV_{π_2} >= ...`, and form adjacent pairs
`P_p = {π_{2p-1}, π_{2p}}`, `p = 1..⌊n/2⌋` (the odd leftover — the least-liquid name — is
dropped to keep balance). For split `r` (an independent seed-derived RNG stream), draw
coins `c_p^{(r)} ~ Bernoulli(1/2)` iid and assign:

```
X_1^{(r)} = { π_{2p-1} if c_p=0 else π_{2p}   :  p = 1..⌊n/2⌋ }
X_2^{(r)} = { π_{2p}   if c_p=0 else π_{2p-1} :  p = 1..⌊n/2⌋ }
```

By construction the two arms are **disjoint, equal-sized, and liquidity-balanced**:

```
X_1^{(r)} ∩ X_2^{(r)} = ∅,    |X_1^{(r)}| = |X_2^{(r)}| = ⌊n/2⌋
```

so an `X_1 ↔ X_2` difference can never be a liquidity artifact. The split space has
cardinality `2^{⌊n/2⌋} ≫ R`, so the `R` seeds sample a rich distribution rather than one
near-degenerate point. Alphabetical/ordered assignment is FORBIDDEN; both supported methods
(`LIQUIDITY`, `RANDOM`) shuffle.

**Structural arm independence.** The market-neutral forward residual `r̃_{i,t}` (§4.2) is the
SAME for a name regardless of arm: beta is estimated once on the full panel and sliced per
arm (`rolling_beta` takes no arm argument), so the name-split cannot change a residual — arm
independence is structural, not promised (a unit test pins it).

**The conjugate read.** For each arm `a ∈ {X_1, X_2}` and date `t`, the within-arm
cross-sectional rank-IC and its per-arm, per-split Newey-West t-stat are

```
IC_t^{(a)} = corr_spearman( s_{·,t}|_a , r̃_{·,t}|_a ),   |{i ∈ a : finite}| >= 30
T_a^{(r)}  = nw_tstat( {IC_t^{(a)}}_t , L )
```

For a zero-discretion (parameter-free) scorer, "fit in `X_1` / evaluate in `X_2`" reduces
to the IC realized in the evaluation arm, since there are no fitted parameters to carry —
the conjugacy lives in the disjoint name partition, not in a re-estimation. Aggregated over
the `R` splits:

```
τ_cross = min( median_r T_{X_1}^{(r)},  median_r T_{X_2}^{(r)} )                       (cross-direction median t)
κ       = (1/R) Σ_r 1[ sign(mean_t IC^{(X_1,r)}) == sign(mean_t IC^{(X_2,r)}) ≠ 0 ]    (sign consistency)
```

### 4.4 Conjugate agreement — Mod-A's 3-part PASS bar

Section 4.1. PASS requires **all three conditions** to hold (the third, PBO, is §4.6):

```
(1)  median_R( t_IC^{cross} )  >  2.0      in BOTH directions (X_1→X_2 and X_2→X_1)
(2)  sign_consistency          >= 0.90     (κ: cross-arm consistency of the IC sign)
(3)  PBO_CSCV                  <  0.50      (real median-rank PBO; NOT the proxy)
```

```
agreement_pass = [median_r T_{X_1} > 2.0] ∧ [median_r T_{X_2} > 2.0] ∧ [κ >= 0.90] ∧ [PBO < 0.50]
```

(`AGREEMENT_CROSS_IC_T_MIN=2.0`, `SIGN_CONSISTENCY_MIN=0.90`, `PBO_THRESHOLD=0.50`.)

### 4.5 Residual cross-sectional correlation (SEPARATE computation, Section 4.2)

Kept **deliberately separate** from conjugate agreement (the 4.3 mixing-ban). The two arms'
active-return co-movement is flagged against a **permutation null**: if the observed arm
correlation exceeds the `RESIDUAL_CORR_NULL_PCTILE=95`-th percentile of the null
distribution built from `RESIDUAL_NULL_RESAMPLES=200` random re-splits, `residual_corr_flag=True`.
This is the "are the arms driven by a shared common-factor?" detector (the same machine that
caught RR-Y1-008's hi52 confound).

### 4.6 Real CSCV PBO (Bailey & Lopez de Prado) — `pbo.py`

The simple proxy (`P(OOS Sharpe < 0)`) **cannot see** overfit: a strategy can post a positive
OOS Sharpe and still be the IS-luckiest of many candidates. The real CSCV is mapped to the
conjugate context as follows:
- The "configs" being selected among are **cross-sectional sort-buckets** (deciles,
  `PBO_N_BUCKETS=10`), not the splits. (If configs were the splits, a real factor would make
  every split good, the ranking among them would be noise, and PBO → 0.5 — falsely failing
  the embedded-factor fixture. Buckets-as-config avoids that.)
- The combinatorial resampling = the `R` name-splits.
- IS = arm `X_1`, OOS = arm `X_2` (and the symmetric direction; the caller averages).

For each split, the logit of the IS-best bucket `b*`'s OOS relative rank:

```
ω      = avg_rank(b* OOS value) / (n_valid + 1)            (Bailey-LdP average-rank)
λ      = log( ω / (1 - ω) )
PBO    = fraction of splits with λ < 0
```

Pure noise → ~0.5; a bucket order that transfers IS→OOS → ~0; an inverted order → ~1. At
least 2 jointly-valid buckets are required; degenerate buckets (below `MIN_NAMES_PER_BUCKET=3`)
arrive as NaN and are excluded.

### 4.7 Deflated Sharpe Ratio — trial-count deflation (`dsr.py`)

Multiple-test / search-overfit is caught by the DSR's **N-deflation** (NOT by bucket-PBO,
which measures single-prototype-internal overfit; a different layer). The honest tried-config
count `N` (Stage-0 `denenen_konfig_sayisi`) feeds the Bailey-LdP `E[max]` order statistic:

```
E[max_N] = (1 - γ)·Φ^{-1}(1 - 1/N) + γ·Φ^{-1}(1 - 1/(N·e)),   γ = Euler-Mascheroni
```

`N <= 1 → E[max]=0` (a single trial carries no multiple-test inflation; the DSR is
byte-identical to the pre-FAZ-4 call). The deflation benchmark:

```
denom² = 1 - skew·SR + (kurt-1)/4 · SR²
se_SR  = sqrt( denom² / (T-1) )
benchmark_sr = se_SR · E[max_N]
```

Fed to the committed `compute_dsr` as `benchmark_sr`, this yields exactly the canonical
deflated DSR `Φ(SR/se_SR - E[max_N])`. **Strangler:** the committed estimator is REUSED,
never rewritten. `DSR_MIN = 0.95`.

### 4.8 Benchmark floor — real-return threshold (`benchmark.py`, Section 6)

Frozen rule:
- **Real-deflate:** always TUFE (CPI, 2019+, finite throughout the panel).
- **Benchmark-floor:** pre-2022-07 = TUFE-only; 2022-07+ = `max(TUFE, TLREF)`.
- **Silent-NaN trap (d213 precedent):** the clean TLREF series is NaN before 2022-07. If the
  floor window reaches into that region, the NaN is NOT allowed to silently collapse the
  `max` — guard-RAISE (the message is recorded) and fall back to TUFE-only for that window.

TUFE/TLREF are **level** series, so annualization is a calendar-day CAGR (via `asof`, robust
to the snapshots' monthly index):

```
CAGR = (level(d1) / level(d0)) ^ (365.25 / days) - 1
real_active = (1 + nominal_active) / (1 + TUFE_ann) - 1
beats = real_active > max(TUFE_ann, TLREF_ann)
```

### 4.9 Mod-C — intra-regime forward time-holdout persistence (RR-Y1-010)

Answers the core research question directly: freeze a cross-sectional factor on a TRAINING
time-window, measure its forward rank-IC on a LATER held-out window WITHIN THE SAME regime,
with an **embargo** (= the forward-return horizon) purged between them so no construction-period
return leaks across the boundary.

```
boundary  = holdout_start
holdout   = eval_dates[ >= boundary ]
pre       = eval_dates[ < boundary ]
train     = pre[ : len(pre) - embargo_h ]              (embargo purge)
```

Persistence PASS **reuses the existing bar** (NO new tunable):

```
persistence_pass = (holdout_ic_t > agreement_t_min[=2.0])  AND  sign(holdout_IC) == sign(train_IC)
```

Honesty about power is carried not by softening the bar but by the **separate holdout
confidence qualifier** (§5). A degenerate split (boundary outside the eval window, or
train/holdout `< lag+3`) → `holdout_persistence_pass=None` + a guard message, never a
misleading number.

---

## 5. Confidence qualifiers

Both are **additive only**: they NEVER alter the pass/fail flags and are orthogonal to the
keep-bars (DEC-049 untouched). They qualify whether the **preconditions** for a trustworthy
measurement held. The precedence in both is: **confounded > low > high**.

### 5.1 Mod-A — `assess_agreement_confidence` (RR-Y1-009)

| Grade | Trigger |
|-------|---------|
| `CONFOUNDED` | `residual_corr_flag` (shared common-factor) **OR** a single-regime eval window. |
| `LOW` | arm < `AGREEMENT_MIN_ARM_FOR_HIGH_CONFIDENCE=50` **OR** R < `AGREEMENT_MIN_R_FOR_HIGH_CONFIDENCE=50`. |
| `HIGH` | none tripped. |

The gap RR-Y1-008 closed: a known-dead momentum-proxy produced `agreement_pass=True` on a
small-arm, single-regime window. The conjugate's narrow question ("no name-specific overfit")
was answered correctly, but the result was a within-regime common-factor artifact.

### 5.2 Mod-C — `assess_holdout_confidence` (RR-Y1-010)

| Grade | Trigger |
|-------|---------|
| `CONFOUNDED` | the holdout crosses `REGIME_SPLIT` **OR** a residual flag fires on the holdout window. |
| `LOW` | `n_holdout_obs < HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE=60`. |
| `HIGH` | none tripped. |

**Opposite-but-consistent regime semantics (the critical nuance):**
- **Mod-A:** a single-regime eval window is SUSPECT (a within-regime common-factor artifact
  can fake a clean conjugate PASS).
- **Mod-C:** single-regime is the DESIGN, not a confound (the question is precisely "does it
  persist forward WITHIN one regime"). The confound here is the holdout window CROSSING
  `REGIME_SPLIT` (2022-01-01) — if train sits in one regime and the holdout spills into
  another, the same-regime-persistence question is polluted.

That is why these are two separate enums (`AgreementConfidence` vs `HoldoutConfidence`), not a
single "single-regime → confounded" rule.

---

## 6. Pre-registration discipline (Stage-0 + Lockbox)

### 6.1 Stage-0 — freeze the hypothesis BEFORE measurement (`stage0_validator.py`)

When `harness(..., stage0_path=...)` is given, `require_stage0` enforces that the file is
PRESENT, schema-valid, `frozen_before_results is True`, and (optionally) the frozen snapshot's
content-hash (`sha256[:16]`, d213 precedent) matches. If the file is absent → it **refuses to
run** (post-hoc-lock, Section 5).

Required fields (`REQUIRED_FIELDS`, 18): `prototip_id`, `hipotez`, `tutunma_noktasi`
(`cross_sectional`/`timing`/`panel`), `split_modu` (`A`/`B`/`A+B`), `psi`, `faktor_notrleme`
(non-empty list, `market` minimum), `embargo_h`, `split_arm_floor`, `sort_depth`, `hedef_rejim`,
`frekans` (`daily`/`monthly`), `getiri_tabani`, `keep_bar` (`pbo_max` + `dsr_min` keys
required), `denenen_konfig_sayisi` (→ DSR deflation N), `frozen_before_results`, `date_frozen`,
`snapshots_content_hash_sha256_prefix`, `strangler_constraints`. **monthly → split_modu 'A'**
required.

Optional fields (None when absent, backward compatible): lockbox (`lockbox_spec`,
`lockbox_content_hash`) and the Mod-C record (`eval_window_start`, `eval_window_end`,
`holdout_start`).

### 6.2 Lockbox — single-shot held-out seal (`lockbox.py`)

The workflow: iterate on the discovery set → FREEZE → evaluate ONCE on independent data.
Stage-0 freezes the *design*; the lockbox additionally seals a held-out data subset (by name,
by time block, or both) and refuses to score unless: Stage-0 is present + frozen +
`lockbox_fingerprint(panel)` == the registered hash. It then marks the evaluation as
**consumed** — the sealed set can never again become a tuning surface.

```
lockbox_fingerprint = sha256( names_sorted | dates_sorted | close_float64_bytes )[:16]
```

The marker file (`{stem}.lockbox-consumed.json`) is **designed to be committed** — NOT
git-ignored. After a fresh `git checkout` the marker is present, so a second run is refused
(non-repudiable discipline). The marker carries no real data: only `prototip_id`, the 16-char
hash, `denenen_konfig_sayisi`, and a UTC `consumed_at`. Consumption is the harness's LAST
action BEFORE returning — a crash mid-run does not burn the lockbox.

---

## 7. Usage examples by mode

### 7.1 Mod-A — name-split conjugate (cross-sectional factor)

```python
spec = SplitSpec(split_mode=SplitMode.NAME, frequency=Frequency.DAILY,
                 R=50, sort_depth=SortDepth.TERCILE)
out  = harness(panel, sig, spec, DialConfig())
assert out.agreement_pass in (True, False)
# Read: agreement_pass + agreement_confidence (HIGH/LOW/CONFOUNDED) + pbo
```

### 7.2 Mod-B — temporal CPCV (timing signal)

```python
spec = SplitSpec(split_mode=SplitMode.TEMPORAL, frequency=Frequency.DAILY,
                 cpcv_n=10, cpcv_k=2, embargo_h=sig.construction_window)
out  = harness(panel, sig, spec, DialConfig())
# Read: dsr, dsr_n_trials, pbo (proxy -- see the note), pooled OOS NW-t
```

### 7.3 Mod-C — intra-regime forward time-holdout (RR-Y1-010)

```python
spec = SplitSpec(split_mode=SplitMode.TIME_HOLDOUT, frequency=Frequency.DAILY,
                 holdout_start="2024-09-01", embargo_h=sig.construction_window)
out  = harness(panel, sig, spec, DialConfig())
# Read: holdout_persistence_pass + holdout_confidence + (train_ic_t vs holdout_ic_t)
```

### 7.4 PANEL — A+B together

```python
spec = SplitSpec(split_mode=SplitMode.PANEL, frequency=Frequency.DAILY)
out  = harness(panel, sig, spec, DialConfig())
# Both agreement_* (Mod-A) and dsr (Mod-B) populate. Mod-C does NOT join PANEL (by design).
```

---

## 8. Reading the output

The engine does not decide; the following **joint-reading** logic is recommended:

1. **Is it tradeable?** `net_active_ann > 0` **and** `beats_benchmark_floor is True` (does
   the real return beat max(TUFE,TLREF)). Gross positive but net negative → cost-killed.
2. **Is it statistically real?** `nw_t` large, `pbo < 0.50`, `dsr >= 0.95`.
3. **Not overfit (Mod-A)?** `agreement_pass is True` **and** `agreement_confidence is HIGH`.
   If `CONFOUNDED`/`LOW`, do not trust the PASS — read `agreement_confidence_reasons`.
4. **Does it persist forward (Mod-C)?** `holdout_persistence_pass is True` **and**
   `holdout_confidence is HIGH`.
5. **Regime-stable?** Does `per_regime` carry the same sign pre/post 2022 in both arms.
6. **Not curve-fit?** Is `plateau_map` stable across neighboring (sort_depth × horizon) points.
7. **Guards:** are `guard_messages` and `notes` empty — if not, which field is `None` and why?

> **Golden rule:** `None` is not a failure but an honest "not produced". For example, in a
> Mod-A-only run `dsr` is None (DSR is Mod-B's temporal-Sharpe measure); `null_percentile` and
> `deflated_oos_t` are not produced by the legs in Faz-3.

---

## 9. Frozen constants (single source of truth: `config.py`)

| Constant | Value | Role |
|----------|-------|------|
| `IC_TYPE` | `spearman` | Cross-sectional rank-IC. |
| `MIN_NAMES_CROSS_SECTION` | `30` | Min names for IC. |
| `NW_LAG_DAILY` / `NW_LAG_MONTHLY` | `5` / `3` | HAC bandwidth. |
| `NW_VAR_FLOOR_EPS` | `1e-12` | Near-zero-variance NaN floor. |
| `BETA_WINDOW_DAYS` | `126` | Beta window. |
| `BETA_MIN_COVERAGE` | `0.8` | Min beta coverage. |
| `SPLIT_R_MIN` | `50` | Mod-A name-split count. |
| `MIN_NAMES_PER_ARM` | `50` | Min names per arm. |
| `AGREEMENT_CROSS_IC_T_MIN` | `2.0` | Conjugate t threshold. |
| `SIGN_CONSISTENCY_MIN` | `0.90` | Sign consistency. |
| `PBO_THRESHOLD` | `0.50` | Real CSCV PBO ceiling. |
| `PBO_N_BUCKETS` | `10` | PBO decile count (DECOUPLED from sort_depth). |
| `MIN_NAMES_PER_BUCKET` | `3` | Degenerate-bucket guard. |
| `RESIDUAL_CORR_NULL_PCTILE` | `95` | Residual correlation null percentile. |
| `RESIDUAL_NULL_RESAMPLES` | `200` | Permutation null re-splits. |
| `CPCV_DAILY_N` / `CPCV_DAILY_K` | `10` / `2` | Mod-B CPCV blocks. |
| `DSR_MIN` | `0.95` | DSR floor. |
| `DSR_DEFAULT_N_TRIALS` | `1` | No Stage-0 → no deflation. |
| `EULER_MASCHERONI` | `0.5772156649` | E[max] order statistic. |
| `AGREEMENT_MIN_ARM/R_FOR_HIGH_CONFIDENCE` | `50` / `50` | Mod-A confidence floor. |
| `HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE` | `60` | Mod-C confidence floor (directional, NOT deployable). |
| `REGIME_SPLIT` | `2022-01-01` | Manual regime boundary. |
| `BENCHMARK_TLREF_FROM` | `2022-07` | Date TLREF enters the floor. |
| `LIQUID_ADV_MIN_TL` | `1e7` | Liquidity floor (ADV-TL). |
| `TRADING_DAYS_YR` | `252.0` | Return-series annualization. |

**C12 golden anchor:** `C12_GOLDEN_GROSS_NWT=6.928414`, `C12_GOLDEN_NET_NWT=-6.274774`
@ `C12_GOLDEN_NW_LAG=10`, `C12_GOLDEN_N_POOLED=1375`. This is the byte-reproduction test that
proves the engine deterministic on real data; it is NOT the proof of methodological correctness
(that rests on the 3 synthetic Mod-A fixtures + the synthetic-null).

---

## 10. Guarantees and limits

**Guarantees:**
- **Zero regression:** new fields/modes default to `None`; existing modes are byte-unchanged.
- **PM-1 compliance:** every weight vector passes `assert_pm1_compliant`; a cash-gate RAISES.
- **Look-ahead-safe:** beta rests on the past via `shift(1)`; Mod-B/Mod-C purge an embargo.
- **Determinism:** seed-fixed (`seed`); the C12 golden is reproduced byte-for-byte.
- **Strangler:** committed motors are read-only; `test_engine_no_lab_import.py` forbids lab imports.

**Honest limits:**
- **Mod-C is structurally power-poor on BIST 2019-2026** (few non-overlapping within-regime
  forward holdouts). `HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE=60` is a directional floor, not a
  deployable-confidence threshold. The value = the conceptually-correct instrument + readiness
  for the 2026-2027 forward period.
- **Fields not produced in Faz-3:** `null_percentile`, `mirror_active_ann` (the fair-null
  resampler is out of scope), `deflated_oos_t` (cut-family deflation not wired). All `None` +
  a note, never fabricated.
- **The Mod-B PBO is a simplified proxy** (`pbo_is_simplified_proxy=True`); the real CSCV
  median-rank PBO belongs to the Mod-A core.

---

## 11. Related documents

- Design: `RR-Y1-005-TEST-MOTORU-TASARIM` v0.2
- Math: `RR-Y1-005B-MATEMATIKSEL-SPEC` v1.1
- Mod-C verdict: `docs/research/RR-Y1-010-intra-regime-time-holdout.md`
- Confidence qualifier (Mod-A): `docs/research/RR-Y1-009-*`
- Registry: `docs/RESEARCH_REGISTRY.md`
- Decision history: `docs/DECISIONS.md`
