"""BIST Datastore aylik yabanci islem .xls loader (D-129).

Elle indirilen .xls dosyalarini parse edip foreign_monthly.db'ye yazar.

Kullanim:
    python scripts/load_datastore_xls.py data/bist_datastore/foreign_monthly/*.xls
    python scripts/load_datastore_xls.py file1.xls file2.xls
    python scripts/load_datastore_xls.py --check        # DB durumu ozeti
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.bist_datastore_parser import ForeignMonthlyDBWriter, parse_foreign_monthly
from src.utils.logger import setup_logger

logger = setup_logger("load_datastore_xls")


def cmd_load(paths: list[str]) -> int:
    writer = ForeignMonthlyDBWriter()
    total_rows = 0
    files_ok = 0
    for p in paths:
        try:
            df = parse_foreign_monthly(p)
            n = writer.upsert(df)
            total_rows += n
            files_ok += 1
            logger.info("Loaded %s: %d satir", p, n)
        except Exception as exc:  # noqa: BLE001 - per-file graceful
            logger.error("Parse/load hatasi (%s): %s", p, exc)
    counts = writer.ticker_counts()
    print(f"Datastore load: {files_ok}/{len(paths)} dosya, {total_rows} satir, {len(counts)} ticker")
    return 0


def cmd_check() -> int:
    counts = ForeignMonthlyDBWriter().ticker_counts()
    if not counts:
        print("foreign_monthly.db bos (henuz veri yok).")
        return 0
    print(f"foreign_monthly.db: {len(counts)} ticker")
    for ticker, n in list(counts.items())[:50]:
        print(f"  {ticker}: {n} ay")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BIST Datastore aylik yabanci islem loader (D-129)")
    parser.add_argument("paths", nargs="*", help=".xls dosya yollari (shell glob)")
    parser.add_argument("--check", action="store_true", help="DB durumu ozeti")
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    if not args.paths:
        parser.error("En az bir .xls yolu ver (veya --check).")
    return cmd_load(args.paths)


if __name__ == "__main__":
    sys.exit(main())
