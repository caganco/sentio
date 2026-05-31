"""D-185 Trend-Motor Test -- orchestrator (run_faz0 analogue).

Freezes the OHLCV snapshot, generates each variant's setups once (signals are
cost-independent), then evaluates post-cost expectancy + random/B&H benchmarks
+ regime decomposition + gate verdict across the frozen cost scenarios.

run_trend_test(prices, xu100, ...) is network-free -> unit tests drive it on
synthetic panels. main() handles the (network) snapshot freeze + JSON output.

DEC-039: recommends; does not decide. Survivors-only -> UPPER BOUND.
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.screening import trend_backtest as bt
from src.screening import trend_config as cfg
from src.screening import trend_signals as sig
from src.screening import trend_snapshot as snap

logger = logging.getLogger(__name__)

_RESULTS_PATH = Path(__file__).parent.parent.parent / "docs" / "trend_test" / "trend_test_results.json"


def run_trend_test(prices: dict[str, pd.DataFrame], xu100: pd.Series,
                   cost_scenarios=cfg.COST_SCENARIOS_BPS) -> dict:
    """Core measurement. No network. Returns the full results dict."""
    state = bt.market_state_series(xu100) if len(xu100) else pd.Series(dtype=object)
    out: dict = {}
    summary: list[dict] = []
    for variant in cfg.VARIANTS:
        out[variant] = {}
        for mode in cfg.FILTER_MODES:
            parab = (mode == "parabolic_on")
            setups_by_ticker: dict[str, list] = {}
            n_setups = 0
            for tk, o in prices.items():
                s = sig.generate_signals(variant, tk, o, parab)
                if s:
                    setups_by_ticker[tk] = s
                    n_setups += len(s)
            by_cost: dict[str, dict] = {}
            for cb in cost_scenarios:
                trades = bt.backtest_variant(setups_by_ticker, prices, cb)
                exp = bt.expectancy_stats(trades)
                dd = bt.sequential_equity_max_dd(trades)
                regime = bt.regime_breakdown(trades, state)
                rnd = bt.random_entry_null(prices, trades, cb)
                bh = bt.buy_and_hold(prices, cb)
                gate = bt.gate_verdict(exp, rnd, regime, dd, bh)
                by_cost[str(cb)] = {
                    "n_trades": exp["n_trades"], "expectancy": exp,
                    "drawdown": dd, "regime": regime, "random_benchmark": rnd,
                    "buy_and_hold": bh, "gate": gate,
                }
                if cb == cfg.PRIMARY_COST_BPS:
                    summary.append({
                        "variant": variant, "filter": mode, "cost_bps": cb,
                        "n_trades": exp["n_trades"], "expectancy_R": exp["expectancy_R"],
                        "t_hac": exp.get("t_hac"), "beats_random_95": rnd.get("beats_random_95"),
                        "max_dd": dd["max_drawdown"], "passes_gate": gate["passes_gate"],
                        "failures": gate["failures"],
                    })
            out[variant][mode] = {"n_setups": n_setups, "by_cost": by_cost}
    return {
        "directive": "D-185", "config_version": cfg.CONFIG_VERSION,
        "cost_scenarios_bps": list(cost_scenarios),
        "primary_cost_bps": cfg.PRIMARY_COST_BPS,
        "survivorship_framing": ("survivors-only -> expectancy is an UPPER BOUND; "
                                 "failing the random benchmark post-cost here is conclusive."),
        "results": out, "primary_summary": summary,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="D-185 trend-motor test")
    ap.add_argument("--out", default=str(_RESULTS_PATH))
    args = ap.parse_args()

    long_df, meta = snap.freeze_ohlcv_snapshot(list(cfg.TREND_UNIVERSE))
    prices, xu100 = snap.to_ohlcv_panels(long_df)
    logger.info("loaded %d tickers, XU100 %d obs", len(prices), len(xu100))
    results = run_trend_test(prices, xu100)
    results["snapshot_meta"] = meta
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("results -> %s", out_path)
    for row in results["primary_summary"]:
        logger.info("VERDICT %s/%s cost=%dbps n=%d expR=%s tHAC=%s rand95=%s gate=%s %s",
                    row["variant"], row["filter"], row["cost_bps"], row["n_trades"],
                    row["expectancy_R"], row["t_hac"], row["beats_random_95"],
                    row["passes_gate"], row["failures"])


if __name__ == "__main__":
    main()
