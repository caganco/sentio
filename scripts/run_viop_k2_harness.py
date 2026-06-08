"""Run the VIOP K2 harness (Stage-2): Mod-A name-split on monthly SSF OI-growth.

Mod-A is the ONLY valid mode for monthly-frequency signals (SplitSpec enforces
MONTHLY_TEMPORAL_CPCV_FORBIDDEN; Mod-B/C raise ValueError at SplitSpec construction).

Stage-0: docs/yol1/STAGE0_VIOP_SSF_OI.json (custom format — verified via
_verify_stage0(); NOT passed to harness() to avoid incompatible 18-field validator).

Keep-bar: nw_t > 2.0 (NW-HAC t-statistic on tradeable tilt active-return series).
PASS  -> K1/K3 characterization spec openable.
FAIL  -> graveyard entry required; thread permanently closed.

Usage:
    python scripts/run_viop_k2_harness.py
    python scripts/run_viop_k2_harness.py --out data/processed/viop_k2_engine_output.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("run_viop_k2_harness")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.engine.contracts import (
    DialConfig,
    Frequency,
    NameSplitMethod,
    Panel,
    SortDepth,
    SplitMode,
    SplitSpec,
)
from src.engine.data_adapter import load_panel
from src.engine.harness import harness
from src.signals.viop_k2_split import ViOpK2Signal, compute_liquidity_split

_STAGE0_PATH = REPO_ROOT / "docs" / "yol1" / "STAGE0_VIOP_SSF_OI.json"
_K2_PARQUET = REPO_ROOT / "data" / "processed" / "viop_signal_panel.parquet"
_KEEP_BAR_NW_T = 2.0
_OI_PREV_FLOOR = 500


# ---------------------------------------------------------------------------
# Stage-0 integrity
# ---------------------------------------------------------------------------

def _stage0_content_hash(path: Path) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc_clean = {k: v for k, v in doc.items() if k != "content_hash"}
    canonical = json.dumps(doc_clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _verify_stage0(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Stage-0 absent: {path}\n"
            "Freeze hypothesis BEFORE running harness (Stage-0 lock)."
        )
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stored = str(doc.get("content_hash", ""))
    if stored and stored != "__PLACEHOLDER__":
        computed = _stage0_content_hash(path)
        if computed != stored:
            raise RuntimeError(
                f"Stage-0 content_hash mismatch: expected {stored!r}, got {computed!r}. "
                "Stage-0 was modified after hash lock — integrity violated."
            )
        logger.info("Stage-0 integrity OK (hash %s)", computed)
    else:
        logger.warning("Stage-0 content_hash placeholder/empty — hash not verified.")
    return doc


# ---------------------------------------------------------------------------
# Monthly Panel construction
# ---------------------------------------------------------------------------

def _build_monthly_panel(daily_panel: Panel) -> Panel:
    """Resample daily Panel to month-end dates (Frequency.MONTHLY).

    close/tr_gross/tr_net/value_tl resampled to last trading day of each month.
    Membership flags resampled to last value of each month.
    Market/TUFE/TLREF resampled to last value of each month.
    """
    def _me_last(df: pd.DataFrame) -> pd.DataFrame:
        return df.resample("ME").last().dropna(how="all")

    close_m = _me_last(daily_panel.close)
    tr_gross_m = _me_last(daily_panel.tr_gross)
    tr_net_m = _me_last(daily_panel.tr_net)
    value_tl_m = daily_panel.value_tl.resample("ME").sum()

    membership_m = {k: _me_last(v) for k, v in daily_panel.membership.items()}

    market_m = daily_panel.market.resample("ME").last().dropna()
    tufe_m = daily_panel.tufe.resample("ME").last().dropna()
    tlref_m = daily_panel.tlref.resample("ME").last().dropna()

    return Panel(
        close=close_m,
        tr_gross=tr_gross_m,
        tr_net=tr_net_m,
        value_tl=value_tl_m,
        membership=membership_m,
        market=market_m,
        tufe=tufe_m,
        tlref=tlref_m,
        frequency=Frequency.MONTHLY,
    )


# ---------------------------------------------------------------------------
# EngineOutput serialisation
# ---------------------------------------------------------------------------

def _engine_output_to_dict(out: Any) -> dict[str, Any]:
    """Convert EngineOutput to a JSON-serialisable dict."""
    import dataclasses
    d: dict[str, Any] = {}
    for f in dataclasses.fields(out):
        val = getattr(out, f.name)
        if isinstance(val, tuple):
            val = list(val)
        elif hasattr(val, "value"):
            val = str(val)  # StrEnum
        d[f.name] = val
    return d


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(out_path: Path) -> None:
    # Step 1: Stage-0 integrity check
    logger.info("Verifying Stage-0 pre-registration ...")
    stage0_doc = _verify_stage0(_STAGE0_PATH)
    logger.info("Stage-0 thread_id: %s", stage0_doc.get("thread_id"))

    # Step 2: Load K2 panel
    if not _K2_PARQUET.exists():
        raise FileNotFoundError(
            f"K2 parquet not found: {_K2_PARQUET}\n"
            "Run: python scripts/build_viop_signal_panel.py --start 2016-01 --end 2026-05 "
            "--out data/processed/viop_signal_panel.parquet"
        )
    logger.info("Loading K2 panel from %s ...", _K2_PARQUET)
    k2_df = pd.read_parquet(_K2_PARQUET)
    logger.info(
        "K2 panel: %d rows, %d tickers, date range %s .. %s",
        len(k2_df),
        k2_df["ticker"].nunique(),
        k2_df["date"].min().date(),
        k2_df["date"].max().date(),
    )

    # Step 3: Liquidity split diagnostic
    split = compute_liquidity_split(k2_df)
    logger.info(
        "Liquidity split — high: %d tickers, low: %d tickers",
        len(split.high_liq),
        len(split.low_liq),
    )

    # Step 4: Load daily spot Panel and restrict to VIOP×spot intersection.
    # We use a DAILY panel so that:
    #   - beta warm-up (beta_window=126 days) works correctly
    #   - h=21 trading days ≈ 1-month forward return
    # The signal produces scores only at month-end dates; harness masks all other
    # dates as NaN automatically (mask = scores.notna() & fwd.notna()).
    logger.info("Loading daily spot panel ...")
    daily_panel = load_panel()
    logger.info(
        "Daily panel: %d dates (%s .. %s), %d names",
        len(daily_panel.dates),
        daily_panel.dates[0].date(),
        daily_panel.dates[-1].date(),
        len(daily_panel.names),
    )

    # Step 5: Restrict Panel to VIOP×spot intersection
    # (harness._tilt_active cannot handle NaN in is_top for tickers absent from signal)
    viop_tickers = set(k2_df["ticker"].unique())
    panel_tickers = set(daily_panel.names)
    common_tickers = sorted(viop_tickers & panel_tickers)
    logger.info(
        "VIOP×spot intersection: %d tickers (VIOP=%d, panel=%d)",
        len(common_tickers),
        len(viop_tickers),
        len(panel_tickers),
    )
    if len(common_tickers) < 10:
        raise RuntimeError(
            f"Too few common tickers ({len(common_tickers)}). "
            "Check that clean_universe contains BIST SSF underlyings."
        )
    restricted_panel = Panel(
        close=daily_panel.close[common_tickers],
        tr_gross=daily_panel.tr_gross[common_tickers],
        tr_net=daily_panel.tr_net[common_tickers],
        value_tl=daily_panel.value_tl[common_tickers],
        membership={k: v[v.columns.intersection(common_tickers)] for k, v in daily_panel.membership.items()},
        market=daily_panel.market,
        tufe=daily_panel.tufe,
        tlref=daily_panel.tlref,
        frequency=Frequency.DAILY,
    )
    logger.info("Daily panel restricted to %d VIOP tickers", len(restricted_panel.names))

    # Step 5b: Build ViOpK2Signal
    # construction_window=21 → h=21 trading days ≈ 1-month forward return on daily panel
    signal = ViOpK2Signal(k2_df, oi_prev_floor=_OI_PREV_FLOOR)
    logger.info("ViOpK2Signal built — OI_prev floor: %d, construction_window: %d", _OI_PREV_FLOOR, signal.construction_window)

    # Step 6: SplitSpec — Mod-A, daily frequency
    # (MONTHLY_TEMPORAL_CPCV_FORBIDDEN only restricts Frequency.MONTHLY; daily is unrestricted)
    split_spec = SplitSpec(
        split_mode=SplitMode.NAME,
        frequency=Frequency.DAILY,
        embargo_h=21,  # = construction_window (1 month)
        R=50,
        seed=42,
        sort_depth=SortDepth.TERCILE,
        name_split_method=NameSplitMethod.LIQUIDITY,
    )
    logger.info("SplitSpec: mode=%s, frequency=%s, embargo_h=%d, R=%d",
                split_spec.split_mode, split_spec.frequency, split_spec.embargo_h, split_spec.R)

    # Step 7: DialConfig — market neutralization (Mod-A mandatory)
    dial_config = DialConfig(
        neutralization=("market",),
    )

    # Step 8: Run harness (no stage0_path — VIOP Stage-0 uses custom format)
    logger.info("Running harness (Mod-A) ...")
    output = harness(restricted_panel, signal, split_spec, dial_config)

    # Step 9: Keep-bar verdict
    nw_t = output.nw_t
    keep_bar_pass = nw_t is not None and nw_t > _KEEP_BAR_NW_T
    verdict = "PASS" if keep_bar_pass else "FAIL"
    logger.info(
        "Keep-bar verdict: %s (NW-t=%.4f, threshold=%.1f)",
        verdict,
        nw_t if nw_t is not None else float("nan"),
        _KEEP_BAR_NW_T,
    )
    if not keep_bar_pass:
        logger.warning(
            "FAIL: K2 thread closed — no post-hoc variant chain openable. "
            "Graveyard entry required: docs/yol1/graveyard/VIOP_SSF_OI.md"
        )
    else:
        logger.info("PASS: K1/K3 characterisation spec may be opened.")

    # Step 10: Serialise output
    result: dict[str, Any] = {
        "stage0_thread_id": stage0_doc.get("thread_id"),
        "keep_bar_threshold": _KEEP_BAR_NW_T,
        "keep_bar_verdict": verdict,
        "oi_prev_floor": _OI_PREV_FLOOR,
        "liquidity_split": {
            "high_liq_n": len(split.high_liq),
            "low_liq_n": len(split.low_liq),
            "high_liq_tickers": split.high_liq,
            "low_liq_tickers": split.low_liq,
        },
        "engine_output": _engine_output_to_dict(output),
        "notes_design": (
            "Daily panel used (construction_window=21 ≈ 1-month forward return). "
            "Signal scores only at K2 month-end dates; other dates masked as NaN. "
            "Mod-B/C not evaluated: Mod-A (name-split) is the primary conjugate gate."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info("Output written to %s", out_path)

    # Summary
    print("\n--- VIOP K2 Harness Stage-2 Summary ---")
    print(f"Keep-bar verdict : {verdict}")
    print(f"NW-t             : {nw_t:.4f}" if nw_t is not None else "NW-t             : N/A")
    print(f"Gross active ann : {output.gross_active_ann:.4f}" if output.gross_active_ann is not None else "Gross active ann : N/A")
    print(f"Net active ann   : {output.net_active_ann:.4f}" if output.net_active_ann is not None else "Net active ann   : N/A")
    print(f"N obs            : {output.n_obs}")
    print(f"Agreement pass   : {output.agreement_pass}")
    print(f"PBO              : {output.pbo:.4f}" if output.pbo is not None else "PBO              : N/A")
    if output.guard_messages:
        print("Guards:")
        for g in output.guard_messages:
            print(f"  - {g}")
    print(f"Output JSON      : {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run VIOP K2 Stage-2 harness")
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data" / "processed" / "viop_k2_engine_output.json",
        help="Output JSON path (git-ignored)",
    )
    args = ap.parse_args()
    run(args.out)


if __name__ == "__main__":
    main()
