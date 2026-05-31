"""D-186 orchestrator -- re-measures the D-185 trades with fixed metrics.

Reuses the SAME frozen OHLCV snapshot + UNCHANGED signals/trades (trend_signals,
trend_backtest). Only the metrics change: real portfolio DD (FIX1), XU100-relative
(+ best-effort real-CPI) returns (FIX2), fair null + CS significance (FIX3). Produces
the frozen DEC-044 verdict per variant x filter.

run_d186(prices, xu100, cpi) is network-free (cpi injectable) -> unit-testable.
main() handles the frozen-snapshot load + best-effort EVDS TUFE + JSON output.

DEC-039: recommends; does not decide. No composite / conviction / engine imports.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.screening import trend_d186 as d186
from src.screening import trend_d186_config as cfg
from src.screening import trend_portfolio as port
from src.screening import trend_signals as tsig
from src.screening.trend_backtest import backtest_variant
from src.screening.trend_config import INFLATION_REGIMES, TREND_UNIVERSE
from src.screening.trend_snapshot import freeze_ohlcv_snapshot, to_ohlcv_panels

logger = logging.getLogger(__name__)

_RESULTS_PATH = Path(__file__).parent.parent.parent / "docs" / "trend_test" / "d186_results.json"


def _try_load_cpi(start: str, end: str) -> pd.Series | None:
    """Best-effort EVDS TUFE (TP.FG.J0). None if no key/network (relative decides)."""
    try:
        from src.data.macro_sources import fetch_tufe_series
        s = fetch_tufe_series(start, end)
        if s is not None and len(s) > 0:
            logger.info("TUFE loaded: %d obs (real-CPI confirmatory enabled)", len(s))
            return s
    except Exception as e:  # noqa: BLE001 (best-effort)
        logger.warning("TUFE fetch failed (%s) -> XU100-relative decides alone", e)
    logger.info("No TUFE -> XU100-relative is the sole decisive basis")
    return None


def run_d186(prices: dict[str, pd.DataFrame], xu100: pd.Series, cpi: pd.Series | None,
             cost_bps: float = cfg.PRIMARY_COST_BPS) -> dict:
    """Core re-measurement (network-free). Returns the full D-186 results dict."""
    slice_lo, slice_hi = cfg.decision_slice_window()
    out: dict = {}
    summary: list[dict] = []
    for variant in cfg.VARIANTS:
        out[variant] = {}
        for mode in cfg.FILTER_MODES:
            parab = (mode == "parabolic_on")
            setups_by_ticker: dict[str, list] = {}
            n_setups = 0
            for tk, o in prices.items():
                s = tsig.generate_signals(variant, tk, o, parab)
                if s:
                    setups_by_ticker[tk] = s
                    n_setups += len(s)
            trades = backtest_variant(setups_by_ticker, prices, cost_bps)
            d186.add_relative_returns(trades, xu100, cost_bps)
            d186.add_real_returns(trades, cpi)

            pf = port.build_portfolio(trades, prices)
            # per-slice descriptive (relative + real + nominal)
            by_slice: dict[str, dict] = {}
            for label, lo, hi in INFLATION_REGIMES:
                st = d186.slice_trades(trades, lo, hi)
                by_slice[label] = {
                    "n_trades": len(st),
                    "mean_nominal_net": round(d186.mean_key(st, "net_return"), 5),
                    "mean_rel_net": round(d186.mean_key(st, "rel_net_return"), 5),
                    "mean_real_net": (round(d186.mean_key(st, "real_net_return"), 5)
                                      if cpi is not None else None),
                }
            # decision slice (disinflation): fair null + CS significance + verdict
            strat_slice = d186.slice_trades(trades, slice_lo, slice_hi)
            n_target = sum(1 for t in strat_slice if t.get("rel_net_return") is not None)
            mean_rel = d186.mean_key(strat_slice, "rel_net_return")
            null_block = d186.fair_random_null(prices, xu100, mean_rel, n_target,
                                               slice_lo, slice_hi, parab, cost_bps)
            cs_block = d186.cs_significance(strat_slice, "rel_net_return")
            verdict = d186.d186_verdict(null_block, pf["max_drawdown"], cs_block)

            out[variant][mode] = {
                "n_setups": n_setups, "n_trades": len(trades),
                "full_window_mean_nominal_net": round(d186.mean_key(trades, "net_return"), 5),
                "full_window_mean_rel_net": round(d186.mean_key(trades, "rel_net_return"), 5),
                "portfolio": {k: pf[k] for k in
                              ("max_drawdown", "final_equity", "n_admitted", "n_skipped")},
                "by_inflation_slice": by_slice,
                "decision_slice": {"slice": cfg.DECISION_SLICE, "window": [slice_lo, slice_hi],
                                   "fair_null": null_block, "cs_significance": cs_block},
                "verdict_DEC044": verdict,
            }
            summary.append({
                "variant": variant, "filter": mode,
                "disinflation_mean_rel": round(mean_rel, 5) if pd.notna(mean_rel) else None,
                "fair_random_pctile": null_block.get("random_pctile"),
                "beats_fair_random_95": null_block.get("beats_fair_random_95"),
                "portfolio_max_dd": pf["max_drawdown"],
                "passes_DEC044": verdict["passes_DEC044"], "failures": verdict["failures"],
            })
    return {
        "directive": "D-186", "config_version": cfg.D186_CONFIG_VERSION,
        "cost_bps": cost_bps, "decisive_basis": cfg.RETURN_BASIS_DECISIVE,
        "real_cpi_available": cpi is not None,
        "decision_rule_DEC044": ("disinflation slice + XU100-relative + fair null (matched "
                                 "exit+prefilter) beats random >=95 pctile AND portfolio max_dd<=0.35"),
        "results": out, "primary_summary": summary,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="D-186 trend-motor fix round")
    ap.add_argument("--out", default=str(_RESULTS_PATH))
    args = ap.parse_args()

    long_df, meta = freeze_ohlcv_snapshot(list(TREND_UNIVERSE))
    prices, xu100 = to_ohlcv_panels(long_df)
    logger.info("loaded %d tickers, XU100 %d obs (snapshot hash %s)",
                len(prices), len(xu100), meta.get("content_hash", "")[:12])
    cpi = _try_load_cpi(meta["window"]["start"], meta["window"]["end"])
    results = run_d186(prices, xu100, cpi)
    results["snapshot_meta"] = {"content_hash": meta.get("content_hash"),
                                "window": meta.get("window"),
                                "loaded_universe_n": meta.get("loaded_universe_n")}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("results -> %s", out_path)
    for row in results["primary_summary"]:
        logger.info("DEC044 %s/%s relDisinf=%s rand_pctile=%s beats=%s maxDD=%s PASS=%s %s",
                    row["variant"], row["filter"], row["disinflation_mean_rel"],
                    row["fair_random_pctile"], row["beats_fair_random_95"],
                    row["portfolio_max_dd"], row["passes_DEC044"], row["failures"])


if __name__ == "__main__":
    main()
