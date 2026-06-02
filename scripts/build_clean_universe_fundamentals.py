"""D-203 FAZ-0: Universal fundamentals freeze CLI.

Kullanim:
  python scripts/build_clean_universe_fundamentals.py
  python scripts/build_clean_universe_fundamentals.py --force-rebuild
  python scripts/build_clean_universe_fundamentals.py --verify-only

Kaynak: evrensel bist_datastore_archive/fundamental_ratios/degoran_M_*.zip (read-only).
Cikti: data/clean_universe/fundamentals_2019_2026.parquet + _meta_fundamentals.json
(junction'li tek kaynak, git-local, ASCII meta). 681 D-202 sembolune hizalanir.
"""
from __future__ import annotations

import argparse
import logging
import sys

from src.data.clean_universe_fundamentals import (
    build_and_freeze_fundamentals,
    verify_frozen_fundamentals,
)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="D-203 FAZ-0 universal fundamentals freeze")
    p.add_argument("--force-rebuild", action="store_true", help="mevcut donmus paneli yok say, yeniden uret")
    p.add_argument("--verify-only", action="store_true", help="mevcut parquet'i content-hash'e karsi dogrula")
    args = p.parse_args(argv)

    if args.verify_only:
        ok = verify_frozen_fundamentals()
        print(f"[clean-fund] verify: {'OK' if ok else 'MISMATCH'}")
        return 0 if ok else 1

    df, meta = build_and_freeze_fundamentals(force_rebuild=args.force_rebuild)
    print(f"[clean-fund] Tamamlandi: {meta['n_rows']} satir, {meta['n_months']} ay, "
          f"{meta['covered_n']}/{meta['universe_n']} sembol kapsandi "
          f"({meta['month_min']}..{meta['month_max']})")
    print(f"[clean-fund] Hash: {meta['content_hash_fundamentals'][:16]}...")
    print(f"[clean-fund] Eksik (fundamentals yok): {meta['missing_n']} sembol")
    return 0


if __name__ == "__main__":
    sys.exit(main())
