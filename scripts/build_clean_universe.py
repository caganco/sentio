"""D-200: Survivorship-clean adjusted price panel builder CLI.

Kullanim:
  python scripts/build_clean_universe.py
  python scripts/build_clean_universe.py --force-rebuild
  python scripts/build_clean_universe.py --verify-only
  python scripts/build_clean_universe.py --start 2020-01-01 --end 2025-12-31

On kosul: FAZ-3 corp-action indirilmis olmali (archive_datastore.py --phase 3 --proceed-faz3).
3196 fiyat CSV'leri de indirilmis olmali (archive_datastore.py --type 3196).
ASCII-only cikti (Windows cp1254 uyumu).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from src.signals.thresholds import (
    CLEAN_UNIVERSE_END,
    CLEAN_UNIVERSE_ROOT,
    CLEAN_UNIVERSE_START,
    DATASTORE_ARCHIVE_ROOT,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="D-200 survivorship-clean adjusted panel builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--start", default=CLEAN_UNIVERSE_START, metavar="YYYY-MM-DD",
                   help=f"Baslangic tarihi (varsayilan: {CLEAN_UNIVERSE_START})")
    p.add_argument("--end", default=CLEAN_UNIVERSE_END, metavar="YYYY-MM-DD",
                   help=f"Bitis tarihi (varsayilan: {CLEAN_UNIVERSE_END})")
    p.add_argument("--archive-root", default=DATASTORE_ARCHIVE_ROOT,
                   help=f"DataStore arsiv koku (varsayilan: {DATASTORE_ARCHIVE_ROOT})")
    p.add_argument("--output-root", default=CLEAN_UNIVERSE_ROOT,
                   help=f"Cikti dizini (varsayilan: {CLEAN_UNIVERSE_ROOT})")
    p.add_argument("--force-rebuild", action="store_true",
                   help="Meta hash kontrolunu atla, her seferinde yeniden kur")
    p.add_argument("--verify-only", action="store_true",
                   help="Mevcut parquet'i dogrula, yeniden kurmadan")
    return p


def _parse_date(s: str, label: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        print(f"HATA: {label} formati YYYY-MM-DD olmali, verildi: {s!r}")
        sys.exit(1)


def main() -> None:
    args = _build_parser().parse_args()
    start_date = _parse_date(args.start, "--start")
    end_date = _parse_date(args.end, "--end")

    archive_root = Path(args.archive_root)
    prices_dir = archive_root / "prices_official"
    ca_dir = archive_root / "corporate_actions"
    output_root = Path(args.output_root)

    if args.verify_only:
        import json
        import pandas as pd
        from src.data.clean_universe_builder import content_hash
        from src.signals.thresholds import CLEAN_UNIVERSE_ADJ_PRICES, CLEAN_UNIVERSE_META
        meta_path = output_root / CLEAN_UNIVERSE_META
        prices_path = output_root / CLEAN_UNIVERSE_ADJ_PRICES
        if not meta_path.exists() or not prices_path.exists():
            print("HATA: Parquet veya meta bulunamadi. Once --force-rebuild ile olusturun.")
            sys.exit(1)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        df = pd.read_parquet(prices_path)
        chash = content_hash(df)
        if chash == meta.get("content_hash_prices"):
            print(f"[clean-universe] VERIFY OK: hash eslesme ({chash[:16]}...)")
        else:
            print(f"HATA: Hash uyumsuzlugu. Parquet bozulmus veya meta eski.")
            sys.exit(1)
        return

    from src.data.clean_universe_builder import build_and_freeze_adjusted_panel
    try:
        adj_panel, meta = build_and_freeze_adjusted_panel(
            prices_dir=prices_dir,
            ca_dir=ca_dir,
            output_root=output_root,
            start_date=start_date,
            end_date=end_date,
            force_rebuild=args.force_rebuild,
        )
    except RuntimeError as exc:
        print(f"HATA: {exc}")
        sys.exit(1)

    n_sym = meta["n_symbols"]
    n_d = meta["n_dates"]
    excl = meta["excluded_symbols_count"]
    print(f"[clean-universe] Tamamlandi: {n_sym} sembol x {n_d} gun")
    if excl:
        print(f"[clean-universe] DISLANAN: {excl} sembol (bedelli sub_price eksik)")
    print(f"[clean-universe] Cikti: {output_root}/")
    print(f"[clean-universe] Hash: {meta['content_hash_prices'][:32]}...")


if __name__ == "__main__":
    main()
