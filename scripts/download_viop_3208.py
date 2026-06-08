"""Download DataStore 3208 (VIOP daily) files into data/viop/.

Akış: catalog → add_free_to_library → download_product

Usage:
    python scripts/download_viop_3208.py                        # all files
    python scripts/download_viop_3208.py --since 2016-01-01     # from date
    python scripts/download_viop_3208.py --dry-run              # list only, no download

Requires: datastore_session.json (local, git-ignored). Re-login if expired:
    python scripts/capture_datastore_session.py
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger("download_viop_3208")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

_PRODUCT_ID = 3208
_OUT_DIR = REPO_ROOT / "data" / "viop"
_CAPTURE_SCRIPT = REPO_ROOT / "scripts" / "capture_datastore_session.py"


def _ensure_valid_session() -> "DatastoreSession":
    """Load session; if missing/expired auto-launch capture script, then reload."""
    from src.data.bist_datastore_client import DatastoreSession

    def _load() -> "DatastoreSession | None":
        try:
            return DatastoreSession()
        except FileNotFoundError:
            return None

    session = _load()
    if session is not None and session.is_valid():
        return session

    if session is None:
        logger.info("datastore_session.json bulunamadi — tarayici aciliyor, giris yap...")
    else:
        logger.info("Session suresi dolmus — tarayici aciliyor, giris yap...")

    subprocess.run([sys.executable, str(_CAPTURE_SCRIPT)], check=True)

    session = DatastoreSession()
    if not session.is_valid():
        raise RuntimeError("Session yenilendi ama hala gecersiz — lutfen tekrar deneyin.")
    logger.info("Session yenilendi.")
    return session


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--since", default=None, help="Only process files on or after YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="List files without downloading")
    p.add_argument("--out-dir", default=str(_OUT_DIR), help="Destination directory (default: data/viop/)")
    args = p.parse_args(argv)

    from src.data.bist_datastore_client import (
        DatastoreAcquirer,
        DatastoreCatalog,
        DatastoreDownloader,
        DatastoreSessionExpiredError,
    )

    since: date | None = None
    if args.since:
        since = date.fromisoformat(args.since)

    try:
        session = _ensure_valid_session()
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    out_dir = Path(args.out_dir)

    # Step 1: List available products from catalog
    catalog = DatastoreCatalog(session)
    all_products = catalog.list_products(_PRODUCT_ID)
    logger.info("Catalog: %d products found for type %d", len(all_products), _PRODUCT_ID)

    # Step 2: Apply date filter
    products = [
        pr for pr in all_products
        if since is None or (pr.data_date is not None and pr.data_date >= since)
    ]
    logger.info("After date filter: %d products (since=%s)", len(products), since or "all")

    if args.dry_run:
        already_in_lib = sum(1 for pr in products if pr.in_library)
        already_downloaded = sum(1 for pr in products if (out_dir / _product_filename(pr)).exists())
        logger.info(
            "  %d in library, %d already on disk",
            already_in_lib, already_downloaded,
        )
        for pr in products:
            fname = _product_filename(pr)
            on_disk = (out_dir / fname).exists()
            status = "EXISTS" if on_disk else ("LIB" if pr.in_library else "PENDING")
            print(f"  [{status}] {fname}  ({pr.data_date})")
        return 0

    # Step 3: Add to library (only those not yet in library)
    to_add = [pr for pr in products if not pr.in_library]
    if to_add:
        logger.info("Adding %d products to library ...", len(to_add))
        acquirer = DatastoreAcquirer(session)
        added = acquirer.add_free_to_library(to_add)
        logger.info("  %d added", added)
    else:
        logger.info("All %d products already in library", len(products))

    # Step 4: Download from library (idempotent — skips existing files)
    out_dir.mkdir(parents=True, exist_ok=True)
    downloader = DatastoreDownloader(session)
    downloaded = downloader.download_product(_PRODUCT_ID, out_dir, since_date=since)
    logger.info("Done — %d file(s) in %s", len(downloaded), out_dir)
    return 0


def _product_filename(product: object) -> str:
    """Best-effort filename for display (dry-run only)."""
    name = getattr(product, "type_name", None) or ""
    dt = getattr(product, "data_date", None)
    ref = getattr(product, "reference_id", "?")
    return f"{name}_{dt}.csv" if (name and dt) else str(ref)


if __name__ == "__main__":
    sys.exit(main())
