# Graveyard: VIOP SSF OI Growth (K2)

**Thread:** VIOP-SSF-OI  
**Stage-0:** `docs/yol1/STAGE0_VIOP_SSF_OI.json` (hash: `34d312edf5b3c27b`)  
**Verdict date:** 2026-06-08  
**Keep-bar result:** FAIL  

---

## Keep-bar Decision

| Metric | Threshold | Result |
|--------|-----------|--------|
| NW-t (tilt active return) | > 2.0 | **-0.073** ❌ |

Signal K2 = (OI_t - OI_{t-1}) / OI_{t-1} shows no cross-sectional predictive power for next-month spot return. NW-t is essentially zero (noise), not just below threshold.

---

## Harness Configuration (Stage-2)

- **Signal:** `viop_k2_oi_growth`, construction_window=21 (≈1 month), OI_prev floor=500
- **Panel:** Daily spot (2019-01-02 .. 2026-05-26), restricted to 63 VIOP×spot tickers
- **Split:** Mod-A name-split, frequency=daily, embargo_h=21, R=50, seed=42
- **N obs:** 51 valid monthly evaluation dates
- **Mod-A leg:** Failed (KeyError in moda.py on daily-dates index); agreement_pass=None, PBO=None
- **Per-regime:** pre-2022 active_ann≈+1.82 (n=17), post-2022 active_ann≈−1.02 (n=34) — regime-inconsistent, no edge

---

## Why K2 Does Not Work

1. **OI measures contract demand, not informed flow direction.** A rising OI could reflect hedgers adding risk *or* speculators going long/short — the signal is unsigned by construction.
2. **Thin cross-section.** Only 63 VIOP SSF tickers, restricted to panel overlap. Monthly breadth veto passes, but effective cross-section after OI_prev floor is marginal for a rank-IC signal.
3. **Front-month exclusion removes the most liquid contracts.** The roll-exclusion in Stage-0 (exclude expiring month) filters the period with highest OI/liquidity, leaving the informational content of remaining contracts in doubt.
4. **Post-2022 regime flip.** Pre-2022 tilt shows weak positive bias; post-2022 is mildly negative. The signal is not regime-stable — consistent with noise rather than alpha.

---

## Graveyard Commitment (Stage-0)

> "Bu thread tek koşuluyla kapanır. K2 fail ederse post-hoc varyant zinciri açılamaz. Sonuç ne olursa olsun kaydedilir."

**This thread is permanently closed.** No post-hoc variant chain (K2-basis, K2-direction, K2-size-adjusted, etc.) may be opened. K1 and K3 characterization signals are blocked.

---

## Output Reference

- Engine output JSON: `data/processed/viop_k2_engine_output.json` (git-ignored)
- Stage-2 harness: `scripts/run_viop_k2_harness.py`
- Data: `data/processed/viop_signal_panel.parquet` (git-ignored)
