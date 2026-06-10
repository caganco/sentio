"""IC Dashboard Tier 1 -- CLI + JSON (DEC-015).

Daily output format:

  =========================================================================
   Sentio -- Alpha Attribution Dashboard  | 2026-05-20 | Regime: BULL
  -------------------------------------------------------------------------
   Layer            IC(t+5)    IR  t-stat  LOO dIC   Status
   L1 Technical     0.0421   0.65    1.80  +0.0030   WATCH
   L2 Macro         0.0612   1.10    2.40  +0.0050   INVEST
   ...
  =========================================================================

JSON dump: data/analytics/ic_report_<YYYY-MM-DD>.json

Signal data is read from flat data/signal_logs/YYYY-MM-DD.parquet files
(written by alpha_attribution.write_daily_snapshot). Bypasses the Hive
dataset scanner to avoid schema collisions with returns.parquet.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

LAYER_DISPLAY: dict[str, str] = {
    "l1_tech_score":  "L1 Technical",
    "l2_macro_score": "L2 Macro",
    "l3_kap_score":   "L3 KAP",
    "l4_sent_score":  "L4 Sentiment",
    "l5_sm_score":    "L5 SmartMoney",
    "l6_risk_score":  "L6 Risk/Kelly",
    "viop_score":     "VIOP (stub)",
}


class ICDashboard:
    """Render Tier-1 CLI + JSON from ICCalculator + LayerAttributor results."""

    def __init__(
        self,
        ic_results,
        loo_results=None,
        regime: str = "unknown",
        signal_count: int = 0,
        decay_data: "dict[str, dict] | None" = None,   # D-140: {layer: compute_decay result}
    ) -> None:
        # Filter to horizon=5, universe="all", regime="all" for the headline row
        self._ics = {
            r.layer: r for r in (ic_results or [])
            if r.horizon == 5 and r.universe == "all" and r.regime == "all"
        }
        self._loo = {r.layer: r for r in (loo_results or [])}
        self._regime = regime
        self._today = date.today()
        self._signal_count = signal_count
        self._decay = decay_data or {}

    def print_cli(self) -> None:
        sep = "=" * 90
        print()
        print(sep)
        print(f"  Sentio -- Alpha Attribution Dashboard  |  {self._today}  |  Regime: {self._regime}")
        print(sep)
        print(f"  {'Layer':<18} {'IC(t+5)':>9} {'IR':>7} {'t-stat':>8} "
              f"{'LOO dIC':>10} {'Decay30d':>11} {'Status':>10}")
        print("-" * 90)
        for col, display in LAYER_DISPLAY.items():
            ic_r = self._ics.get(col)
            loo_r = self._loo.get(col)
            # D-140: decay slope string
            decay = self._decay.get(col, {})
            d30 = decay.get("slope_30d", float("nan"))
            dstatus = decay.get("status", "ok")
            if np.isnan(d30):
                d_str = "--"
            else:
                flag = "!!" if dstatus == "review" else ("!" if dstatus == "warn" else "")
                d_str = f"{d30:+.4f}{flag}"
            if ic_r is None or np.isnan(ic_r.mean_ic):
                # Show COLLECTING when signals exist but returns not yet accumulated
                status = f"COLLECTING({self._signal_count})" if self._signal_count > 0 else "NO DATA"
                print(f"  {display:<18} {'--':>9} {'--':>7} {'--':>8} {'--':>10} "
                      f"{d_str:>11} {status:>10}")
                continue
            loo_str = f"{loo_r.marginal_ic:+.4f}" if loo_r else "--"
            status = _status_label(ic_r.t_stat, ic_r.is_investable)
            print(f"  {display:<18} {ic_r.mean_ic:>9.4f} {ic_r.ir:>7.3f} "
                  f"{ic_r.t_stat:>8.2f} {loo_str:>10} {d_str:>11} {status:>10}")
        print(sep)
        print(f"  PBO estimate: [pending Faz 3]")
        print(f"  Survivorship: Faz 2 -- delisted tickers filter active (D-140)")
        print()

    def dump_json(self, path: str) -> None:
        report = {
            "date": str(self._today),
            "regime": self._regime,
            "layers": {},
        }
        if self._signal_count > 0:
            report["status"] = "ok"
            report["record_count"] = self._signal_count
        for col, ic_r in self._ics.items():
            loo_r = self._loo.get(col)
            decay = self._decay.get(col, {})
            d30 = decay.get("slope_30d", float("nan"))
            d60 = decay.get("slope_60d", float("nan"))
            report["layers"][col] = {
                "display_name": LAYER_DISPLAY.get(col, col),
                "horizon_t5_ic": (ic_r.mean_ic if not np.isnan(ic_r.mean_ic) else None),
                "ir":     (ic_r.ir if not np.isnan(ic_r.ir) else None),
                "t_stat": (ic_r.t_stat if not np.isnan(ic_r.t_stat) else None),
                "p_value": ic_r.p_value,
                "n_obs":   ic_r.n_obs,
                "is_investable": ic_r.is_investable,
                "loo_delta_ic": (loo_r.marginal_ic if loo_r else None),
                "status": _status_label(ic_r.t_stat, ic_r.is_investable),
                "decay_slope_30d": (None if np.isnan(d30) else d30),
                "decay_slope_60d": (None if np.isnan(d60) else d60),
                "decay_status": decay.get("status", "ok"),
            }
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        logger.info("ic_dashboard: JSON report written to %s", out_path)


def _status_label(t_stat: float, is_investable: bool) -> str:
    if t_stat is None or (isinstance(t_stat, float) and np.isnan(t_stat)):
        return "NO_DATA"
    if is_investable:
        return "INVEST"
    if t_stat >= 2.0:
        return "NEAR"
    if t_stat >= 1.5:
        return "WATCH"
    if t_stat >= 1.0:
        return "WEAK"
    return "LOW"


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main() -> int:
    from src.signals.thresholds import RETURNS_LOG_PATH, SIGNAL_LOG_BASE_PATH

    parser = argparse.ArgumentParser(description="Sentio IC Dashboard")
    parser.add_argument("--tier", type=int, default=1, help="Dashboard tier (1=CLI summary)")
    parser.add_argument("--json", type=str, default=None,
                        help="Optional explicit JSON output path")
    args = parser.parse_args()

    sig_dir = SIGNAL_LOG_BASE_PATH
    ret_path = RETURNS_LOG_PATH

    from src.reporting.alpha_attribution import count_flat_signals, read_flat_signals

    signal_count = count_flat_signals(sig_dir)

    if signal_count == 0 and not any(Path(sig_dir).rglob("*.parquet")):
        # Empty state -- render NO DATA rows gracefully (preserves 69-byte JSON format)
        dash = ICDashboard(ic_results=[], loo_results=[], regime="unknown")
        dash.print_cli()
        out = args.json or f"data/analytics/ic_report_{date.today()}.json"
        dash.dump_json(out)
        print(f"  (empty state -- no signal log data yet; JSON written to {out})")
        return 0

    from src.analytics.ic_calculator import ICCalculator
    from src.analytics.layer_attribution import LayerAttributor
    import pandas as pd

    ic_results: list = []
    loo_results: list = []
    regime = "unknown"

    decay_data: dict = {}
    try:
        # Read flat daily parquets directly — avoids schema collision with returns.parquet
        sig_df = read_flat_signals(sig_dir)
        ret_df = pd.read_parquet(ret_path) if Path(ret_path).exists() else pd.DataFrame()
        calc = ICCalculator(sig_df, ret_df)
        ic_results = calc.compute_all()
        loo_results = LayerAttributor(calc._sig, calc._ret).compute_loo(horizon=5)
        if "regime_label" in sig_df.columns and not sig_df.empty:
            from collections import Counter
            regime = Counter(sig_df["regime_label"].dropna()).most_common(1)[0][0]
        # D-140: compute IC decay for each layer at horizon 5
        from src.analytics.ic_calculator import FDR_LAYER_COLS
        for col in FDR_LAYER_COLS:
            try:
                decay_data[col] = calc.compute_decay(col, 5)
            except Exception as dec_exc:
                logger.debug("ic_dashboard: decay compute failed %s: %s", col, dec_exc)
    except Exception as exc:
        logger.warning("ic_dashboard: compute failed, rendering empty: %s", exc)

    dash = ICDashboard(ic_results, loo_results, regime=regime,
                       signal_count=signal_count, decay_data=decay_data)
    dash.print_cli()
    out = args.json or f"data/analytics/ic_report_{date.today()}.json"
    dash.dump_json(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
