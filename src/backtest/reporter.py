"""Backtest output: equity curve PNG, trades CSV, summary JSON, sensitivity JSON."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = "reports/backtest"


def _ensure_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_summary_json(metrics: dict[str, Any], output_dir: str = _DEFAULT_OUTPUT_DIR) -> str:
    """Write summary.json with all metrics and pass/fail evaluation."""
    out = _ensure_dir(output_dir) / "summary.json"
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Summary: {out}")
    return str(out)


def save_trades_csv(trades: list[dict], output_dir: str = _DEFAULT_OUTPUT_DIR) -> str:
    """Write trades.csv with one row per completed (SELL) trade."""
    out = _ensure_dir(output_dir) / "trades.csv"
    sell_trades = [t for t in trades if t.get("type") == "SELL"]
    if not sell_trades:
        out.write_text("symbol,date,price,shares,entry_price,entry_date,pnl,pnl_pct,commission\n",
                       encoding="utf-8")
        return str(out)

    fieldnames = ["symbol", "type", "date", "price", "shares", "entry_price",
                  "entry_date", "pnl", "pnl_pct", "commission"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for t in sell_trades:
            row = dict(t)
            for k in ("date", "entry_date"):
                if k in row and hasattr(row[k], "date"):
                    row[k] = str(row[k].date())
            for k in ("pnl", "pnl_pct", "commission"):
                if k in row:
                    row[k] = round(float(row[k]), 4)
            writer.writerow(row)
    logger.info(f"Trades: {out} ({len(sell_trades)} rows)")
    return str(out)


def save_equity_curve_png(
    equity_curve: list[float],
    dates: list,
    benchmark_series: pd.Series | None,
    initial_capital: float,
    output_dir: str = _DEFAULT_OUTPUT_DIR,
) -> str:
    """Save equity curve PNG comparing system vs XU100.IS benchmark."""
    out = _ensure_dir(output_dir) / "equity_curve.png"
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(14, 6))
        date_vals = [d.date() if hasattr(d, "date") else d for d in dates]

        ax.plot(date_vals, equity_curve, label="System", linewidth=2, color="#2196F3")

        if benchmark_series is not None and not benchmark_series.empty:
            # Normalize benchmark to initial capital
            bmark_start = float(benchmark_series.iloc[0])
            if bmark_start > 0:
                bmark_norm = [initial_capital * (float(v) / bmark_start)
                              for v in benchmark_series.reindex(
                                  pd.DatetimeIndex(dates), method="ffill"
                              ).fillna(method="ffill")]
                ax.plot(date_vals, bmark_norm, label="XU100.IS B&H",
                        linewidth=2, color="#FF5722", linestyle="--")

        ax.axhline(y=initial_capital, color="gray", linestyle=":", linewidth=1, label="Initial capital")
        ax.set_title("Backtest: System vs. BIST100 (XU100.IS)", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Portfolio Value (TL)")
        ax.legend()
        ax.grid(alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(str(out), dpi=150)
        plt.close(fig)
        logger.info(f"Equity curve: {out}")
    except ImportError:
        logger.warning("matplotlib not installed — skipping equity_curve.png")
    except Exception as exc:
        logger.warning(f"Equity curve generation failed: {exc}")
    return str(out)


def save_sensitivity_json(
    sensitivity: dict[str, Any],
    output_dir: str = _DEFAULT_OUTPUT_DIR,
) -> str:
    """Write Kelly fraction sensitivity analysis to sensitivity_analysis.json."""
    out = _ensure_dir(output_dir) / "sensitivity_analysis.json"
    out.write_text(json.dumps(sensitivity, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Sensitivity: {out}")
    return str(out)
