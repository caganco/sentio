"""D-187 -- orchestrator. run_exposure_test is network-free (injectable).

DEC-039: measures + recommends; does not decide.
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.screening.exposure_backtest import (
    build_benchmarks,
    build_regime_switcher,
    build_static_barbell,
    compute_metrics,
    slice_metrics,
)
from src.screening.exposure_config import (
    EXPOSURE_END,
    EXPOSURE_START,
    STATIC_EQUITY_RATIOS,
    decision_slice_window,
)
from src.screening.exposure_null import random_switch_null

logger = logging.getLogger(__name__)
_RESULTS = Path(__file__).parent.parent.parent / "docs" / "exposure_test" / "exposure_results.json"


def _sa_verdict(sa_metrics: dict, b1_m: dict, b5_m: dict) -> dict:
    """S-A passes if best annual_real > B1 AND > B5 (in the full window)."""
    best_real = max((m.get("annual_real", float("-inf")) or float("-inf"))
                    for m in sa_metrics.values())
    b1_real = b1_m.get("annual_real", float("nan"))
    b5_real = b5_m.get("annual_real", float("nan"))
    passes = (
        pd.notna(best_real) and pd.notna(b1_real) and pd.notna(b5_real)
        and best_real > b1_real and best_real > b5_real
    )
    return {"passes": bool(passes), "best_sa_annual_real": round(float(best_real), 4),
            "b1_annual_real": round(float(b1_real), 4) if pd.notna(b1_real) else None,
            "b5_annual_real": round(float(b5_real), 4) if pd.notna(b5_real) else None}


def _sb_verdict(sb_real: float, best_sa_real: float, null_block: dict) -> dict:
    beats_barbell = pd.notna(sb_real) and pd.notna(best_sa_real) and sb_real > best_sa_real
    beats_null = bool(null_block.get("beats_random_95"))
    passes = beats_barbell and beats_null
    fails = []
    if not beats_barbell:
        fails.append("does_not_beat_static_barbell")
    if not beats_null:
        fails.append("fails_random_switch_null")
    return {"passes": bool(passes), "sb_annual_real": round(float(sb_real), 4) if pd.notna(sb_real) else None,
            "best_sa_annual_real": round(float(best_sa_real), 4) if pd.notna(best_sa_real) else None,
            "random_pctile": null_block.get("random_pctile"),
            "beats_random_95": beats_null, "failures": fails}


def run_exposure_test(
    xu100: pd.Series, tlref: pd.Series, tufe: pd.Series,
    gold: pd.Series | None = None,
) -> dict:
    """Core measurement -- network-free. Returns full results dict."""
    slice_lo, slice_hi = decision_slice_window()
    benchmarks = build_benchmarks(xu100, tlref, tufe, gold)
    b_metrics_full = {k: compute_metrics(v, tufe, EXPOSURE_START, EXPOSURE_END)
                      for k, v in benchmarks.items()}
    b_metrics_slice = {k: compute_metrics(v, tufe, slice_lo, slice_hi)
                       for k, v in benchmarks.items()}

    # S-A: static barbells
    sa_results: dict = {}
    sa_portfolios: dict[str, pd.Series] = {}
    sa_full_metrics: dict[str, dict] = {}
    for r in STATIC_EQUITY_RATIOS:
        key = f"SA_{int(r*100)}"
        res = build_static_barbell(xu100, tlref, r)
        m_full = compute_metrics(res["portfolio"], tufe, EXPOSURE_START, EXPOSURE_END)
        m_slice = compute_metrics(res["portfolio"], tufe, slice_lo, slice_hi)
        sa_results[key] = {"equity_ratio": r, "n_rebalances": res["n_rebalances"],
                           "total_cost": res["total_cost"], "max_drawdown_full": res["max_drawdown"],
                           "metrics_full": m_full, "metrics_disinflation": m_slice}
        sa_portfolios[key] = res["portfolio"]
        sa_full_metrics[key] = m_full

    sa_verdict = _sa_verdict(sa_full_metrics, b_metrics_full.get("B1_TLREF", {}),
                             b_metrics_full.get("B5_TUFE", {}))
    best_sa_real_full = sa_verdict["best_sa_annual_real"]

    # S-B: regime switcher
    sb_res = build_regime_switcher(xu100, tlref)
    sb_m_full = compute_metrics(sb_res["portfolio"], tufe, EXPOSURE_START, EXPOSURE_END)
    sb_m_slice = compute_metrics(sb_res["portfolio"], tufe, slice_lo, slice_hi)
    sb_slice_real = float(sb_m_slice.get("annual_real", float("nan")))
    # Null: in disinflation slice
    null_block = random_switch_null(xu100, tlref, tufe, sb_res["n_switches"],
                                    slice_lo, slice_hi, sb_slice_real)
    sb_verdict = _sb_verdict(sb_m_full.get("annual_real", float("nan")), best_sa_real_full, null_block)

    all_portfolios = {**sa_portfolios, "S_B": sb_res["portfolio"], **benchmarks}
    regime_metrics = slice_metrics(all_portfolios, tufe)

    return {
        "directive": "D-187", "config_version": "exposure-d187-v1",
        "window": {"start": EXPOSURE_START, "end": EXPOSURE_END},
        "caveats": {
            "xu100": "price-only (no dividends ~2-4%/yr); equity side DISADVANTAGED -> conservative",
            "disinflation_power": "~20 months -> low statistical power",
            "gold": "GC=F USD/oz * USDTRY / 32.1507 (troy oz to gram); diagnostic only"
        },
        "benchmarks_full": b_metrics_full, "benchmarks_disinflation": b_metrics_slice,
        "SA_results": sa_results, "SA_verdict_DEC045": sa_verdict,
        "SB_result": {"n_switches": sb_res["n_switches"], "total_cost": sb_res["total_cost"],
                      "max_drawdown_full": sb_res["max_drawdown"],
                      "metrics_full": sb_m_full, "metrics_disinflation": sb_m_slice,
                      "random_switch_null": null_block},
        "SB_verdict_DEC045": sb_verdict,
        "regime_slice_metrics": regime_metrics,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="D-187 exposure regime test")
    ap.add_argument("--out", default=str(_RESULTS))
    args = ap.parse_args()

    from src.screening.exposure_data import load_all_series
    data = load_all_series()
    results = run_exposure_test(data["xu100"], data["tlref"], data["tufe"], data["gold"])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("results -> %s", out)
    logger.info("SA_verdict: %s", results["SA_verdict_DEC045"])
    logger.info("SB_verdict: %s", results["SB_verdict_DEC045"])


if __name__ == "__main__":
    main()
