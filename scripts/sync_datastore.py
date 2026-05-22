"""BIST DataStore dosya senkronizasyon CLI (D-130).

Kullanim:
  python scripts/sync_datastore.py --check
  python scripts/sync_datastore.py --product 3153 --output data/bist_datastore/foreign_monthly/
  python scripts/sync_datastore.py --all --output data/bist_datastore/
  python scripts/sync_datastore.py --product 3153 --since 2026-01-01 --output data/...
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BIST DataStore dosya senkronizasyonu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--check", action="store_true",
                     help="Session gecerliligini ve dosya sayisini kontrol et")
    grp.add_argument("--product", type=int, metavar="ID",
                     help="Belirli urun tipi ID'sini indir (orn: 3153)")
    grp.add_argument("--all", dest="all_products", action="store_true",
                     help="Yabanci (3153) + Aciga satis (3155) indir")

    p.add_argument("--output", default="data/bist_datastore/",
                   help="Hedef dizin (varsayilan: data/bist_datastore/)")
    p.add_argument("--since", metavar="YYYY-MM-DD",
                   help="Bu tarihten sonraki dosyalari indir")
    p.add_argument("--session", default=None,
                   help="Session dosyasi yolu (varsayilan: datastore_session.json)")
    return p


def _load_session(session_path: str | None):
    from src.data.bist_datastore_client import DatastoreSession, DatastoreSessionExpiredError
    try:
        return DatastoreSession.load(session_path)
    except FileNotFoundError as exc:
        print(f"[DataStore] HATA: {exc}")
        sys.exit(1)


def _check(session) -> None:
    from src.data.bist_datastore_client import DatastoreFileIndex
    from src.signals.thresholds import (
        DATASTORE_PRODUCT_FOREIGN,
        DATASTORE_PRODUCT_PRICES,
        DATASTORE_PRODUCT_SHORT,
    )

    captured = session._captured_at
    exp = session._token_exp

    valid = session.is_valid()
    status_str = "gecerli" if valid else "GECERSIZ"
    age_days = (
        __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ) - (
            captured.replace(tzinfo=__import__("datetime").timezone.utc)
            if captured.tzinfo is None else captured
        )
    ).days

    print(f"[DataStore] Session: {status_str} ({age_days} gun eski)")
    if exp:
        print(f"[DataStore] JWT bitis: {exp.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        print("[DataStore] JWT bitis: belirlenemedi")

    if not valid:
        print("[DataStore] Cozum: python scripts/capture_datastore_session.py")
        sys.exit(1)

    index = DatastoreFileIndex(session)
    for pid, label in [
        (DATASTORE_PRODUCT_FOREIGN, "Yabanci (3153)"),
        (DATASTORE_PRODUCT_SHORT, "Aciga Satis (3155)"),
        (DATASTORE_PRODUCT_PRICES, "Fiyatlar (3156)"),
    ]:
        try:
            files = index.list_files(pid)
            print(f"[DataStore] Urun {pid} ({label}): {len(files)} dosya")
        except Exception as exc:
            print(f"[DataStore] Urun {pid} ({label}): HATA — {exc}")


def _sync_product(
    session,
    product_id: int,
    output_dir: Path,
    since_date: date | None,
) -> None:
    from src.data.bist_datastore_client import DatastoreDownloader, DatastoreSessionExpiredError

    print(f"[DataStore] Urun {product_id} indiriliyor -> {output_dir}")
    downloader = DatastoreDownloader(session)
    try:
        paths = downloader.download_product(product_id, output_dir, since_date=since_date)
    except DatastoreSessionExpiredError as exc:
        print(f"[DataStore] HATA: {exc}")
        sys.exit(1)

    downloaded = sum(1 for p in paths if p.exists())
    print(f"[DataStore] Tamamlandi: {len(paths)} dosya hazir (urun {product_id})")


def main() -> None:
    args = _build_parser().parse_args()

    since_date: date | None = None
    if args.since:
        try:
            since_date = date.fromisoformat(args.since)
        except ValueError:
            print(f"[DataStore] HATA: --since formati YYYY-MM-DD olmali, verildi: {args.since!r}")
            sys.exit(1)

    session = _load_session(args.session)

    if args.check:
        _check(session)
        return

    if not session.is_valid():
        print(
            "[DataStore] HATA: Session gecersiz (JWT suresi dolmus veya cok eski).\n"
            "  Cozum: python scripts/capture_datastore_session.py\n"
            "  (Tarayici acilir, giris yapin, CAPTCHA cozun)"
        )
        sys.exit(1)

    output_base = Path(args.output)

    from src.signals.thresholds import DATASTORE_PRODUCT_FOREIGN, DATASTORE_PRODUCT_SHORT

    if args.all_products:
        for pid in (DATASTORE_PRODUCT_FOREIGN, DATASTORE_PRODUCT_SHORT):
            _sync_product(session, pid, output_base / str(pid), since_date)
    else:
        _sync_product(session, args.product, output_base, since_date)


if __name__ == "__main__":
    main()
