"""Persistent IC time-series writer (D-139, SPEC_IC_FRAMEWORK_1 K-04).

ICHistoryWriter appends daily Information Coefficient statistics to an
append-only parquet (`data/analytics/ic_history.parquet`). Unlike the existing
per-day JSON snapshot, this keeps a continuous time series so later phases
(decay monitor, ICIR, Bayesian weight calibration) have history to read.

Architecture: this module is part of src/analytics/ and MUST NOT import
src.signals.engine or src.signals.layers (import-linter / test_architecture
K-08/K-09 invariant). It depends only on thresholds, ic_calculator, pandas,
pyarrow.

Faz 1 writes the FDR panel (ic, p_value, p_adj, significant, n_obs). The
decay/ICIR columns are present in the schema but left NaN; Faz 2 (D-134)
populates them.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.analytics.ic_calculator import FDR_HORIZONS, FDR_LAYER_COLS, ICCalculator
from src.signals.thresholds import (
    IC_HISTORY_PATH,
    RETURNS_LOG_PATH,
    SIGNAL_LOG_BASE_PATH,
)

logger = logging.getLogger(__name__)


IC_HISTORY_SCHEMA = pa.schema([
    pa.field("date",            pa.date32()),
    pa.field("layer",           pa.string()),
    pa.field("horizon",         pa.int32()),
    pa.field("ic",              pa.float32()),
    pa.field("p_value",         pa.float32()),
    pa.field("p_adj",           pa.float32()),
    pa.field("significant",     pa.bool_()),
    pa.field("n_obs",           pa.int32()),
    pa.field("group_adjust",    pa.bool_()),
    pa.field("icir_120d",       pa.float32()),   # Faz 2 (D-134) doldurur
    pa.field("decay_slope_30d", pa.float32()),   # Faz 2
    pa.field("decay_slope_60d", pa.float32()),   # Faz 2
])


class ICHistoryWriter:
    """Compute daily IC + BH-FDR panel and append to ic_history.parquet."""

    def __init__(
        self,
        history_path: str = IC_HISTORY_PATH,
        signal_log_dir: str = SIGNAL_LOG_BASE_PATH,
        returns_path: str = RETURNS_LOG_PATH,
    ) -> None:
        self._path = Path(history_path)
        self._signal_log_dir = signal_log_dir
        self._returns_path = returns_path

    def run_daily(self, today: date, calc: ICCalculator | None = None) -> int:
        """Compute today's IC panel and append it. Returns rows written.

        `calc` may be injected (tests); otherwise built from parquet. Missing or
        empty signal logs -> NO_DATA, nothing written (non-fatal at call site).
        """
        if calc is None:
            calc = self._load_calculator()
            if calc is None:
                logger.info("ic_history: NO_DATA (no signal logs) - skip %s", today)
                return 0

        rows = self._build_rows(calc, today)
        if not rows:
            logger.info("ic_history: no computable IC cells - skip %s", today)
            return 0
        return self._append(rows, today)

    def _load_calculator(self) -> ICCalculator | None:
        if not Path(self._signal_log_dir).exists():
            return None
        try:
            return ICCalculator.from_parquet(self._signal_log_dir, self._returns_path)
        except Exception as exc:
            logger.debug("ic_history: from_parquet failed: %s", exc)
            return None

    def _build_rows(self, calc: ICCalculator, today: date) -> list[dict]:
        """Build K-04 rows from the FDR panel (+ per-cell n_obs). Skips all-empty."""
        panel = calc.compute_fdr_panel(today)
        # n_obs per (layer, horizon) from a direct IC pass.
        n_obs_map: dict[tuple[str, int], int] = {}
        for layer in FDR_LAYER_COLS:
            for horizon in FDR_HORIZONS:
                n_obs_map[(layer, horizon)] = calc.compute_ic(
                    layer, horizon, universe="all", regime="all",
                ).n_obs

        rows: list[dict] = []
        any_data = False
        for r in panel.results:
            n_obs = int(n_obs_map.get((r["layer"], r["horizon"]), 0))
            if n_obs > 0:
                any_data = True
            rows.append({
                "date": today,
                "layer": r["layer"],
                "horizon": int(r["horizon"]),
                "ic": r["ic"],
                "p_value": r["p_raw"],
                "p_adj": r["p_adj"],
                "significant": bool(r["significant"]),
                "n_obs": n_obs,
                "group_adjust": False,         # Faz 1: raw IC (sector-neutral = Faz 2)
                "icir_120d": float("nan"),     # Faz 2
                "decay_slope_30d": float("nan"),
                "decay_slope_60d": float("nan"),
            })
        return rows if any_data else []

    def _append(self, rows: list[dict], today: date) -> int:
        """Append rows to ic_history.parquet. Idempotent on `date == today`."""
        new_df = pd.DataFrame(rows)
        table = pa.Table.from_pandas(new_df, schema=IC_HISTORY_SCHEMA, safe=False)

        if self._path.exists():
            existing = pq.read_table(self._path)
            existing_df = existing.to_pandas()
            if (existing_df["date"].astype(str) == str(today)).any():
                logger.debug("ic_history: %s already written - skip", today)
                return 0
            combined = pa.concat_tables([existing, table])
            pq.write_table(combined, self._path, compression="snappy")
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, self._path, compression="snappy")

        logger.info("ic_history: wrote %d rows for %s", len(rows), today)
        return len(rows)
