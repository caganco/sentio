"""Build the VIOP SSF OI signal panel (Stage-1 orchestrator).

Usage:
    python scripts/build_viop_signal_panel.py \\
        --start 2016-01 \\
        --end   YYYY-MM \\
        --out   data/processed/viop_signal_panel.parquet

Outputs:
    data/processed/viop_signal_panel.parquet    — engine input
    data/processed/viop_signal_metadata.json    — date range, N, excluded months

Requires STAGE0_VIOP_SSF_OI.json to exist (ölçüm kilidi); aborts otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("build_viop_signal_panel")

REPO_ROOT = Path(__file__).resolve().parents[1]
_STAGE0_PATH = REPO_ROOT / "docs" / "yol1" / "STAGE0_VIOP_SSF_OI.json"
_VIOP_DATA_DIR = REPO_ROOT / "data" / "viop"


class StageZeroMissingError(FileNotFoundError):
    """Stage-0 pre-registration JSON absent; measurement cannot begin."""


# ---------------------------------------------------------------------------
# Stage-0 integrity helpers
# ---------------------------------------------------------------------------

def _stage0_content_hash(path: Path) -> str:
    """sha256[:16] of canonical JSON sans the content_hash field (anti-tamper)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc_clean = {k: v for k, v in doc.items() if k != "content_hash"}
    canonical = json.dumps(doc_clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _verify_stage0(path: Path) -> dict[str, object]:
    """Load Stage-0, verify content_hash; return parsed doc."""
    if not path.exists():
        raise StageZeroMissingError(
            f"Stage-0 pre-registration absent: {path}\n"
            "Commit STAGE0_VIOP_SSF_OI.json BEFORE running any measurement (ölçüm kilidi)."
        )
    doc: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    stored_hash = str(doc.get("content_hash", ""))
    if stored_hash == "__PLACEHOLDER__" or not stored_hash:
        logger.warning(
            "Stage-0 content_hash is placeholder/empty — run with --fill-hash to lock it."
        )
    elif stored_hash != "__PLACEHOLDER__":
        computed = _stage0_content_hash(path)
        if computed != stored_hash:
            raise StageZeroMissingError(
                f"Stage-0 content_hash mismatch: expected {stored_hash!r}, got {computed!r}.\n"
                "Stage-0 was modified after hash was computed — integrity violated."
            )
        logger.info("Stage-0 integrity OK (hash %s)", computed)
    return doc


def _fill_stage0_hash(path: Path) -> None:
    """Compute and write the content_hash into the Stage-0 JSON (idempotent)."""
    computed = _stage0_content_hash(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["content_hash"] = computed
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Stage-0 content_hash written: %s", computed)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default="2016-01", help="First YYYY-MM to include (default: 2016-01)")
    p.add_argument("--end", default=None, help="Last YYYY-MM to include (default: latest available)")
    p.add_argument(
        "--out",
        default=str(REPO_ROOT / "data" / "processed" / "viop_signal_panel.parquet"),
        help="Output parquet path",
    )
    p.add_argument(
        "--viop-dir",
        default=str(_VIOP_DATA_DIR),
        help="Root directory of pre-downloaded 3208 files",
    )
    p.add_argument(
        "--fill-hash",
        action="store_true",
        help="Compute and write content_hash into Stage-0 JSON, then exit",
    )
    p.add_argument(
        "--skip-spot-join",
        action="store_true",
        help="Skip spot forward-return join (useful when panel parquet is absent)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # --fill-hash mode: compute hash, write, exit
    if args.fill_hash:
        if not _STAGE0_PATH.exists():
            logger.error("Stage-0 not found at %s", _STAGE0_PATH)
            return 1
        _fill_stage0_hash(_STAGE0_PATH)
        return 0

    # Step 1: Stage-0 guard
    _verify_stage0(_STAGE0_PATH)

    # Step 2: Load VIOP monthly panel
    from src.data.viop_loader import DataUnavailableError, EmptyFilterError, load_viop_monthly_panel

    viop_dir = Path(args.viop_dir)
    logger.info("Loading 3208 data from %s ...", viop_dir)
    try:
        viop_panel = load_viop_monthly_panel(viop_dir, start=args.start, end=args.end)
    except (DataUnavailableError, EmptyFilterError) as exc:
        logger.error("VIOP data load failed: %s", exc)
        return 1

    logger.info(
        "Panel loaded: %d tickers, %s .. %s",
        viop_panel.n_tickers,
        viop_panel.date_range[0],
        viop_panel.date_range[1],
    )
    if viop_panel.schema_log:
        logger.info("Schema transitions: %s", viop_panel.schema_log)

    # Step 3: Compute K2 signal
    from src.data.viop_loader import InsufficientDataError
    from src.signals.viop_k2 import SignalPanel, build_signal_panel

    logger.info("Computing K2 signal ...")
    try:
        if args.skip_spot_join:
            from src.signals.viop_k2 import compute_k2
            k2_df = compute_k2(viop_panel)
            signal = SignalPanel(
                data=k2_df,
                metadata={
                    "n_obs": len(k2_df),
                    "n_tickers": int(k2_df["ticker"].nunique()),
                    "n_valid_months": int(k2_df[k2_df["K2"].notna()]["date"].nunique()),
                    "breadth_excluded_months": int(k2_df[k2_df["breadth_excluded"]]["date"].nunique()),
                    "date_range": "spot-join-skipped",
                    "stage0_path": str(_STAGE0_PATH),
                },
            )
        else:
            signal = build_signal_panel(viop_panel)
    except InsufficientDataError as exc:
        logger.error("Breadth veto: %s", exc)
        return 1

    # Step 4: Write outputs
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    signal.data.to_parquet(out_path, index=False)
    logger.info("Signal panel written: %s (%d rows)", out_path, len(signal.data))

    meta_path = out_path.with_name("viop_signal_metadata.json")
    meta_path.write_text(
        json.dumps(signal.metadata, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    logger.info("Metadata written: %s", meta_path)

    # Step 5: Summary table
    data = signal.data
    print("\n=== VIOP Signal Panel Summary ===")
    print(f"  Date range       : {signal.metadata.get('date_range', 'N/A')}")
    print(f"  Valid months     : {signal.metadata.get('n_valid_months', 'N/A')}")
    print(f"  Tickers          : {signal.metadata.get('n_tickers', 'N/A')}")
    print(f"  Breadth-excluded : {signal.metadata.get('breadth_excluded_months', 'N/A')} months")
    print(f"  Total rows       : {len(data)}")
    if viop_panel.excluded_months:
        print(f"  Roll-excluded    : {len(viop_panel.excluded_months)} ticker-months")

    return 0


if __name__ == "__main__":
    sys.exit(main())
