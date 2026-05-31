"""D-185 Trend-Motor Test -- per-trade event-study backtest + benchmarks.

PRIMARY evidence = post-cost per-trade EXPECTANCY (R-multiple), not Sharpe
(RR-039 / NRR-003: few trades). Entry at t+1 open; exit via initial stop +
20-day Donchian-low trailing (ratchet up only), capped at MAX_HOLD_DAYS. One
open position per ticker (no pyramiding).

Benchmarks: random-entry null (matched count + holding duration; the MOST
critical gate) and net-of-cost equal-weight buy-and-hold. Regime decomposition
(market state via XU100 200-MA + fixed inflation slices). Significance reuses
factor_ic_harness.newey_west_se (HAC) + a seeded bootstrap CI.

Survivors-only -> expectancy is an UPPER BOUND (see snapshot meta / report).

No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening import indicators as ind
from src.screening import trend_config as cfg
from src.screening.factor_ic_harness import newey_west_se
from src.screening.trend_signals import TradeSetup


# ---------------------------------------------------------------------------
# Regime labeling
# ---------------------------------------------------------------------------
def market_state_series(xu100: pd.Series, ma_window: int = cfg.REGIME_MA_WINDOW) -> pd.Series:
    """Per-date market state: bull / bear / sideways (XU100 200-MA + slope)."""
    ma = xu100.rolling(ma_window, min_periods=ma_window).mean()
    rising = ma.diff() > 0
    above = xu100 > ma
    state = pd.Series("sideways", index=xu100.index, dtype=object)
    state[above & rising] = "bull"
    state[(~above) & (~rising)] = "bear"
    state[ma.isna()] = "unknown"
    return state


def inflation_slice(date: pd.Timestamp) -> str:
    d = date.strftime("%Y-%m-%d")
    for label, lo, hi in cfg.INFLATION_REGIMES:
        if lo <= d <= hi:
            return label
    return "unknown"


# ---------------------------------------------------------------------------
# Single-trade simulation
# ---------------------------------------------------------------------------
def simulate_trade(ohlcv: pd.DataFrame, dlow_prior: pd.Series, setup: TradeSetup,
                   cost_frac: float) -> dict | None:
    dates = ohlcv.index
    sig = pd.Timestamp(setup.signal_date)
    if sig not in dates:
        return None
    pos = dates.get_loc(sig)
    ep = pos + 1
    last = len(dates) - 1
    if ep > last:
        return None
    entry = float(ohlcv["open"].iloc[ep])
    if not np.isfinite(entry) or entry <= 0:
        return None
    risk_frac = (entry - setup.stop_price) / entry
    if risk_frac <= 0:
        return None
    eff_stop = float(setup.stop_price)
    exit_price = None
    exit_pos = None
    reason = None
    for j in range(ep, last + 1):
        cand = dlow_prior.iloc[j]
        if np.isfinite(cand):
            eff_stop = max(eff_stop, float(cand))
        lo = float(ohlcv["low"].iloc[j])
        op = float(ohlcv["open"].iloc[j])
        if lo <= eff_stop:
            exit_price = op if op <= eff_stop else eff_stop
            exit_pos, reason = j, "stop_trail"
            break
        if (j - ep + 1) >= cfg.MAX_HOLD_DAYS:
            exit_price, exit_pos, reason = float(ohlcv["close"].iloc[j]), j, "max_hold"
            break
        if j == last:
            exit_price, exit_pos, reason = float(ohlcv["close"].iloc[j]), j, "data_end"
            break
    gross = exit_price / entry - 1.0
    net = gross - cost_frac
    return {
        "ticker": setup.ticker, "variant": setup.variant,
        "entry_date": dates[ep].strftime("%Y-%m-%d"),
        "exit_date": dates[exit_pos].strftime("%Y-%m-%d"),
        "entry": entry, "exit": float(exit_price),
        "gross_return": float(gross), "net_return": float(net),
        "net_R": float(net / risk_frac), "risk_frac": float(risk_frac),
        "bars_held": int(exit_pos - ep + 1), "exit_reason": reason,
        "entry_pos": int(ep), "exit_pos": int(exit_pos),
    }


def backtest_variant(setups_by_ticker: dict[str, list[TradeSetup]],
                     prices: dict[str, pd.DataFrame], cost_bps: float) -> list[dict]:
    """Run all setups (one open position per ticker). Returns trade dicts."""
    cost_frac = cost_bps / 10_000.0
    trades: list[dict] = []
    for ticker, setups in setups_by_ticker.items():
        o = prices.get(ticker)
        if o is None or o.empty:
            continue
        dlow = ind.donchian_lower_prior(o["low"], cfg.A_TRAIL_DONCHIAN_N)
        open_until = -1
        for s in sorted(setups, key=lambda x: x.signal_date):
            sig = pd.Timestamp(s.signal_date)
            if sig not in o.index:
                continue
            if o.index.get_loc(sig) + 1 <= open_until:
                continue  # a position is still open
            tr = simulate_trade(o, dlow, s, cost_frac)
            if tr is not None:
                trades.append(tr)
                open_until = tr["exit_pos"]
    return trades


# ---------------------------------------------------------------------------
# Expectancy + significance
# ---------------------------------------------------------------------------
def expectancy_stats(trades: list[dict], seed: int = cfg.BOOTSTRAP_SEED) -> dict:
    n = len(trades)
    if n == 0:
        return {"n_trades": 0, "expectancy_R": float("nan"), "win_rate": float("nan"),
                "avg_win_R": float("nan"), "avg_loss_R": float("nan"),
                "mean_net_return": float("nan"), "t_naive": float("nan"),
                "t_hac": float("nan"), "ci95_low_R": float("nan"), "ci95_high_R": float("nan")}
    ordered = sorted(trades, key=lambda t: t["entry_date"])
    R = np.array([t["net_R"] for t in ordered], dtype=float)
    ret = np.array([t["net_return"] for t in ordered], dtype=float)
    wins, losses = R[R > 0], R[R <= 0]
    win_rate = len(wins) / n
    avg_win = float(np.mean(wins)) if len(wins) else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) else 0.0
    expectancy_R = float(np.mean(R))
    std_ret = float(np.std(ret, ddof=1)) if n > 1 else 0.0
    t_naive = float(np.mean(ret) / (std_ret / np.sqrt(n))) if std_ret > 0 else 0.0
    se_hac = newey_west_se(ret, cfg.NW_LAGS) if n >= cfg.NW_LAGS + 2 else float("nan")
    t_hac = float(np.mean(ret) / se_hac) if se_hac and np.isfinite(se_hac) and se_hac > 0 else float("nan")
    rng = np.random.default_rng(seed)
    boot = np.array([np.mean(rng.choice(R, size=n, replace=True)) for _ in range(cfg.BOOTSTRAP_N)])
    return {
        "n_trades": n, "expectancy_R": round(expectancy_R, 4),
        "win_rate": round(win_rate, 4), "avg_win_R": round(avg_win, 4),
        "avg_loss_R": round(avg_loss, 4), "mean_net_return": round(float(np.mean(ret)), 5),
        "t_naive": round(t_naive, 3), "t_hac": round(t_hac, 3) if np.isfinite(t_hac) else None,
        "ci95_low_R": round(float(np.percentile(boot, 2.5)), 4),
        "ci95_high_R": round(float(np.percentile(boot, 97.5)), 4),
    }


def sequential_equity_max_dd(trades: list[dict]) -> dict:
    if not trades:
        return {"total_net_return": float("nan"), "max_drawdown": float("nan")}
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for t in sorted(trades, key=lambda x: x["exit_date"]):
        eq *= (1.0 + t["net_return"])
        peak = max(peak, eq)
        mdd = max(mdd, (peak - eq) / peak)
    return {"total_net_return": round(eq - 1.0, 4), "max_drawdown": round(mdd, 4)}


# ---------------------------------------------------------------------------
# Regime decomposition
# ---------------------------------------------------------------------------
def regime_breakdown(trades: list[dict], state: pd.Series) -> dict:
    """Per market-state and per inflation-slice expectancy + PnL share."""
    by_state: dict[str, list[dict]] = {}
    by_infl: dict[str, list[dict]] = {}
    total_pnl = sum(t["net_return"] for t in trades) or float("nan")
    for t in trades:
        d = pd.Timestamp(t["entry_date"])
        st = str(state.get(d, "unknown")) if len(state) else "unknown"
        by_state.setdefault(st, []).append(t)
        by_infl.setdefault(inflation_slice(d), []).append(t)

    def _slice(group: dict[str, list[dict]]) -> dict:
        out = {}
        for k, ts in group.items():
            pnl = sum(t["net_return"] for t in ts)
            out[k] = {
                "n_trades": len(ts),
                "expectancy_R": round(float(np.mean([t["net_R"] for t in ts])), 4),
                "mean_net_return": round(float(np.mean([t["net_return"] for t in ts])), 5),
                "pnl_share": round(pnl / total_pnl, 4) if np.isfinite(total_pnl) and total_pnl != 0 else None,
            }
        return out

    states = {k: v for k, v in _slice(by_state).items() if k in ("bull", "bear", "sideways")}
    positive_states = sum(1 for v in states.values() if v["expectancy_R"] > 0)
    shares = [abs(v["pnl_share"]) for v in {**_slice(by_state), **_slice(by_infl)}.values()
              if v["pnl_share"] is not None]
    return {
        "by_market_state": _slice(by_state),
        "by_inflation_slice": _slice(by_infl),
        "positive_market_states": positive_states,
        "max_single_slice_pnl_share": round(max(shares), 4) if shares else None,
    }


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
def random_entry_null(prices: dict[str, pd.DataFrame], trades: list[dict],
                      cost_bps: float, seed: int = cfg.RANDOM_BENCHMARK_SEED,
                      n_resamples: int = cfg.RANDOM_BENCHMARK_N_RESAMPLES) -> dict:
    """Null distribution of mean net return for matched random entries."""
    n = len(trades)
    if n == 0:
        return {"strategy_mean_net": float("nan"), "random_pctile": float("nan"),
                "beats_random_95": False, "null_mean": float("nan"), "null_p95": float("nan")}
    durations = [t["bars_held"] for t in trades]
    strat_mean = float(np.mean([t["net_return"] for t in trades]))
    cost_frac = cost_bps / 10_000.0
    rng = np.random.default_rng(seed)
    tickers = [k for k, v in prices.items() if len(v) > max(durations) + 2]
    if not tickers:
        return {"strategy_mean_net": round(strat_mean, 5), "random_pctile": float("nan"),
                "beats_random_95": False, "null_mean": float("nan"), "null_p95": float("nan")}
    opens = {k: prices[k]["open"].to_numpy(dtype=float) for k in tickers}
    closes = {k: prices[k]["close"].to_numpy(dtype=float) for k in tickers}
    null_means = np.empty(n_resamples, dtype=float)
    for r in range(n_resamples):
        rets = np.empty(n, dtype=float)
        for k in range(n):
            tk = tickers[rng.integers(len(tickers))]
            dur = durations[rng.integers(n)]
            op, cl = opens[tk], closes[tk]
            hi = len(op) - dur - 1
            if hi <= 1:
                rets[k] = 0.0
                continue
            e = rng.integers(1, hi)
            entry, exit_ = op[e], cl[e + dur - 1]
            rets[k] = (exit_ / entry - 1.0 - cost_frac) if np.isfinite(entry) and entry > 0 and np.isfinite(exit_) else 0.0
        null_means[r] = np.mean(rets)
    pctile = float(np.mean(null_means < strat_mean))
    return {
        "strategy_mean_net": round(strat_mean, 5),
        "null_mean": round(float(np.mean(null_means)), 5),
        "null_p95": round(float(np.percentile(null_means, 95)), 5),
        "random_pctile": round(pctile, 4),
        "beats_random_95": bool(pctile >= cfg.GATE_RANDOM_PCTILE_MIN),
    }


def buy_and_hold(prices: dict[str, pd.DataFrame], cost_bps: float) -> dict:
    """Net-of-cost equal-weight buy-and-hold total return over the window."""
    cost_frac = cost_bps / 10_000.0
    rets = []
    for v in prices.values():
        c = v["close"].dropna()
        if len(c) < 2:
            continue
        rets.append(float(c.iloc[-1] / c.iloc[0] - 1.0 - cost_frac))
    if not rets:
        return {"ew_total_net_return": float("nan"), "n_names": 0}
    return {"ew_total_net_return": round(float(np.mean(rets)), 4), "n_names": len(rets)}


# ---------------------------------------------------------------------------
# Gating verdict
# ---------------------------------------------------------------------------
def gate_verdict(exp: dict, rnd: dict, regime: dict, dd: dict, bh: dict) -> dict:
    fails = []
    if not (exp["n_trades"] > 0 and np.isfinite(exp["expectancy_R"]) and exp["expectancy_R"] > cfg.GATE_EXPECTANCY_MIN_R):
        fails.append("expectancy<=0")
    t_hac = exp.get("t_hac")
    if t_hac is None or not (t_hac >= cfg.GATE_EXPECTANCY_T_MIN):
        fails.append("expectancy_not_significant")
    if not rnd.get("beats_random_95"):
        fails.append("fails_random_benchmark")
    if regime.get("positive_market_states", 0) < cfg.GATE_REGIME_MIN_POSITIVE_STATES:
        fails.append("regime_inconsistent")
    msh = regime.get("max_single_slice_pnl_share")
    if msh is not None and msh > cfg.GATE_SINGLE_REGIME_PNL_MAX:
        fails.append("single_regime_dependent")
    if np.isfinite(dd.get("max_drawdown", float("nan"))) and dd["max_drawdown"] > cfg.GATE_MAX_DD_FAIL:
        fails.append("max_dd_exceeded")
    if np.isfinite(bh.get("ew_total_net_return", float("nan"))) and np.isfinite(dd.get("total_net_return", float("nan"))):
        if dd["total_net_return"] <= bh["ew_total_net_return"]:
            fails.append("does_not_beat_buy_and_hold")
    return {"passes_gate": len(fails) == 0, "failures": fails}
