# L23 -- VIOP single-stock-futures FUNDING-BASIS cross-sectional (REAL DATA, NOT-TRADEABLE)

Stage-0 (frozen before results): `lab-demo-goal/stage0/STAGE0_L23_viop_ss_basis.json`
Results: `lab-demo-goal/results/l23_viop_ss_basis_results.json`
Harness: `lab-demo-goal/harness/l23_viop_ss_basis.py`

## Axis (genuinely new)

The per-stock futures-implied FUNDING/BORROW BASIS LEVEL: the annualized premium of a name's
nearest single-stock-future settlement over its raw spot close. This is the natural complement to
L22's BIST30 index term-structure -- but here the SPOT leg IS available offline per stock (raw
`close`), the exact leg that data-blocked L22 at the index level. Distinct from every prior track,
including L21 (single-stock-futures OPEN-INTEREST GROWTH = a positioning FLOW) and L22 (index-level
curve). Not in the L1-L22 set.

## Signal (single pre-registered definition)

basis_ann(symbol, month-end m) = ln(F_front.settle / S_raw_close) / (dte_front / 365), where
F_front = that underlying's SSF contract with the smallest days-to-expiry that is still >= 10 days,
S_raw_close = raw spot close on the same last trading day. Cross-sectional tercile each month.

PRE-REGISTERED NEGATIVE SIGN: HIGH basis (rich future / crowded longs / costly shorting) ->
subsequent SPOT UNDERperformance, so LONG the LOW-basis tercile. Look-ahead-safe (basis at end of m
-> forward spot return m+1; skip-month m+2 robustness). Market-relative (carry-immune). Net of 40bp
round-trip * turnover. NW HAC lag 6, regime split 2022-01-01, T_SIG 2.0.

## Data

- Front SSF contract observations: 3906; months: 89 (2019-01..2026-05); underlyings: 63.
- Basis observations after same-day spot match: 3906 (matches the frozen feasibility probe).
- Descriptive basis: median 0.2921/yr, p25 ~0.18, p75 ~0.38, 93.9% positive (contango).
  The LEVEL tracks the large TL risk-free carry (NOT a dividend yield ~0.02-0.05), confirming the
  basis level is common-carry-dominated; the tercile spread isolates the per-name component.

## Result (LOW-basis = LONG; market-relative, net)

| scope / variant      | long_rel_net mean | NW-t  | ls_net mean | ls NW-t | regime stable | cost bps | breakeven bps |
|----------------------|-------------------|-------|-------------|---------|---------------|----------|---------------|
| ALL / m+1            | -0.00786          | -3.21 | -0.00787    | -1.60   | True          | 23.46    | -93.98        |
| ALL / m+2 (skip)     | -0.00883          | -3.38 | -0.01315    | -3.45   | True          | 23.54    | -110.06       |
| LIQUID / m+1 (GATE)  | -0.00144          | -0.36 | +0.00359    | +0.40   | False         | 27.31    | +18.88        |
| LIQUID / m+2 (skip)  | -0.01733          | -6.34 | -0.02236    | -4.06   | False         | 27.41    | -212.92       |

## Reading

1. PRIMARY keep-bar (LIQUID, m+1) FAILS on all three conditions: the LOW-basis long leg has a
   NEGATIVE market-relative net mean (-0.0014), it is INSIGNIFICANT (NW-t=-0.36), and it is regime
   sign-UNSTABLE across the 2022 break. No deployable edge.

2. OPPOSITE-SIGN finding (two-sided law). In the wider ALL scope the LOW-basis long leg is
   SIGNIFICANTLY NEGATIVE (NW-t=-3.2 / -3.4): i.e. LOW-basis names UNDERperform and HIGH-basis names
   OUTperform -- the OPPOSITE of the pre-registered NEGATIVE-basis thesis (this looks like
   rich-future continuation and/or the Q2 dividend-calendar seasonal contaminating the LOW-basis
   leg). Per the frozen two-sided law, an opposite-sign result is NOT the pre-registered edge: it
   would require a fresh, separate pre-registration and is NEVER claimed here. It is logged as an
   opposite-sign observation only.

3. The ALL-vs-LIQUID divergence, the regime instability in the liquid (deployable) universe, and the
   sign reversal versus the thesis together confirm there is no robust, deployable per-stock
   futures-basis structure on this data. Exactly the significance-wall / wrong-sign / regime-unstable
   outcome pre-declared as most likely.

## Verdict

VIOP-SS-BASIS-XS-NOT-TRADEABLE -- no deployable edge. The pre-registered (LOW-basis long) leg is
insignificant and regime-unstable in the liquid universe; the only significant effect is OPPOSITE in
sign to the thesis (not claimable). Clean-archived. This honestly CLOSES the per-stock
futures-funding-basis axis -- the complement to L22's index basis, and (unlike L22) with the spot
leg present, so this is a genuine measured null, not a feasibility block.
