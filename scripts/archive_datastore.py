"""BIST DataStore fazli arsiv orkestratoru (D-199).

Mevcut client'i (bist_datastore_client) REUSE eder; saf yardimcilari
(datastore_archive) cagirir. KOD: fetch + manifest-uretici. Veri-ISLEME YOK.

Kullanim:
  python scripts/archive_datastore.py --phase 1 --since 2026-01-01
  python scripts/archive_datastore.py --type 3196 --since 2026-01-01
  python scripts/archive_datastore.py --phase 2 --proceed-faz2
  python scripts/archive_datastore.py --verify-only --phase 1

STOP-gate: --phase 2/3 acik bayrak (--proceed-faz2/3) olmadan baslamaz (exit 2).
Session expiry mid-run: kismi manifest kaydedilir, re-login talimati, exit 1.

ASCII-only cikti (Windows cp1254 konsolu unicode'da coker).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from src.data.datastore_archive import (
    build_file_record,
    frequency_for,
    load_manifest,
    resolve_subdir,
    save_manifest,
    scan_subdir_files,
    survivorship_peek,
)
from src.signals.thresholds import (
    DATASTORE_ARCHIVE_LAYOUT,
    DATASTORE_ARCHIVE_ROOT,
    DATASTORE_PHASE_1,
    DATASTORE_PHASE_2,
    DATASTORE_PHASE_3,
    DATASTORE_SURVIVORSHIP_KNOWN_DELISTED,
    DATASTORE_SURVIVORSHIP_PROBE_TYPE,
)

_PHASE_TYPES = {1: DATASTORE_PHASE_1, 2: DATASTORE_PHASE_2, 3: DATASTORE_PHASE_3}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BIST DataStore fazli arsiv orkestratoru (D-199)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--phase", type=int, choices=(1, 2, 3),
                     help="Faz tiplerini topluca edin (1/2/3)")
    grp.add_argument("--type", type=int, metavar="ID",
                     help="Tek urun tipi edin (orn: 3196)")

    p.add_argument("--archive-root", default=DATASTORE_ARCHIVE_ROOT,
                   help=f"Arsiv koku (varsayilan: {DATASTORE_ARCHIVE_ROOT})")
    p.add_argument("--since", metavar="YYYY-MM-DD",
                   help="Bu tarihten sonraki dosyalari edin")
    p.add_argument("--session", default=None,
                   help="Session dosyasi yolu (varsayilan: datastore_session.json)")
    p.add_argument("--proceed-faz2", action="store_true",
                   help="FAZ-2 onay bayragi (STOP-gate acar)")
    p.add_argument("--proceed-faz3", action="store_true",
                   help="FAZ-3 onay bayragi (STOP-gate acar)")
    p.add_argument("--verify-only", action="store_true",
                   help="Ag cagrisi yapma; mevcut diski tarayip manifest'i yeniden kur")
    return p


def _check_stop_gate(phase: int, args) -> None:
    """FAZ-2/3 acik bayrak gerektirir; yoksa ASCII red + exit 2."""
    if phase == 2 and not args.proceed_faz2:
        print("HATA: FAZ-2 onay gerektirir. FAZ-1 ciktilarini dogrulayin, "
              "sonra --proceed-faz2 ekleyin.")
        sys.exit(2)
    if phase == 3 and not args.proceed_faz3:
        print("HATA: FAZ-3 onay gerektirir. FAZ-2 ciktilarini dogrulayin, "
              "sonra --proceed-faz3 ekleyin.")
        sys.exit(2)


def _load_session(session_path: str | None):
    from src.data.bist_datastore_client import DatastoreSession
    try:
        return DatastoreSession.load(session_path)
    except FileNotFoundError as exc:
        print(f"HATA: {exc}")
        sys.exit(1)


def _records_for_subdir(subdir: Path) -> list[dict]:
    from src.data.bist_datastore_client import _extract_date_from_name
    records = []
    for f in scan_subdir_files(subdir):
        d = _extract_date_from_name(f.name)
        iso = d.isoformat() if d else None
        records.append(build_file_record(f, iso))
    return records


def _acquire_type(session, type_id: int, archive_root: str, since_date: date | None,
                  verify_only: bool, manifest: dict) -> None:
    """Tek tip: list_free -> add_library -> download -> scan -> manifest."""
    from src.data.bist_datastore_client import (
        DatastoreAcquirer,
        DatastoreCatalog,
        DatastoreDownloader,
        DatastoreProductTypeMismatchError,
    )

    subdir = resolve_subdir(archive_root, type_id)
    subdir.mkdir(parents=True, exist_ok=True)
    freq = frequency_for(type_id)
    subfolder = DATASTORE_ARCHIVE_LAYOUT[type_id]

    if not verify_only:
        catalog = DatastoreCatalog(session)
        free = catalog.list_free_products(type_id, since_date=since_date)
        if free:
            print(f"[arsiv] Tip {type_id}: {len(free)} ucretsiz dosya kutuphaneye ekleniyor...")
            acquirer = DatastoreAcquirer(session)
            try:
                added = acquirer.add_free_to_library(free)
                print(f"[arsiv] {added} dosya kutuphaneye eklendi (basket-order + add-library 204).")
            except DatastoreProductTypeMismatchError as exc:
                print(f"[arsiv] UYARI: Tip {type_id} ATLANDI - {exc}")
                print(f"[arsiv] Tip {type_id}: listeleme/sepet product-type ayrismasi; "
                      f"bu tip mevcut akisla edinilemez. Diger tipler devam ediyor.")
                return
        else:
            print(f"[arsiv] Tip {type_id}: eklenecek yeni ucretsiz dosya yok.")

        print(f"[arsiv] Tip {type_id} indiriliyor -> {subdir}")
        downloader = DatastoreDownloader(session)
        downloader.download_product(type_id, subdir, since_date=since_date)
    else:
        print(f"[arsiv] Tip {type_id}: verify-only, ag cagrisi yok, disk taraniyor.")

    records = _records_for_subdir(subdir)
    surv = None
    if type_id == DATASTORE_SURVIVORSHIP_PROBE_TYPE:
        surv = survivorship_peek(subdir, DATASTORE_SURVIVORSHIP_KNOWN_DELISTED)

    from src.data.datastore_archive import update_type_entry
    entry = update_type_entry(manifest, type_id, subfolder, freq, records, survivorship=surv)

    cov = entry["coverage"]
    bad = sum(1 for r in records if not r["integrity_ok"])
    print(f"[arsiv] Tip {type_id} ({subfolder}/{freq}): {cov['n_files']} dosya, "
          f"kapsam {cov['start']}..{cov['end']}, integrity-fail {bad}")
    if surv is not None:
        print(f"[arsiv] Survivorship (tip {type_id}): delisted-iceriyor={surv['delisted_present']} "
              f"(probed={surv['probed_files']}, found={surv['examples_found']})")


def main() -> None:
    args = _build_parser().parse_args()

    since_date: date | None = None
    if args.since:
        try:
            since_date = date.fromisoformat(args.since)
        except ValueError:
            print(f"HATA: --since formati YYYY-MM-DD olmali, verildi: {args.since!r}")
            sys.exit(1)

    if args.phase is not None:
        _check_stop_gate(args.phase, args)
        type_ids = list(_PHASE_TYPES[args.phase])
    else:
        if args.type not in DATASTORE_ARCHIVE_LAYOUT:
            print(f"HATA: bilinmeyen tip {args.type}. Gecerli: "
                  f"{sorted(DATASTORE_ARCHIVE_LAYOUT)}")
            sys.exit(1)
        type_ids = [args.type]

    archive_root = args.archive_root
    manifest = load_manifest(archive_root)

    session = None
    if not args.verify_only:
        session = _load_session(args.session)
        if not session.is_valid():
            print("HATA: Session gecersiz (JWT suresi dolmus veya cok eski).")
            print("  Cozum: python scripts/capture_datastore_session.py")
            sys.exit(1)

    from src.data.bist_datastore_client import DatastoreSessionExpiredError
    try:
        for tid in type_ids:
            _acquire_type(session, tid, archive_root, since_date, args.verify_only, manifest)
    except DatastoreSessionExpiredError as exc:
        save_manifest(manifest, archive_root)
        print(f"HATA: Session sure-doldu calisma sirasinda: {exc}")
        print("  Kismi manifest kaydedildi (ilerleme kaybi yok).")
        print("  Cozum: python scripts/capture_datastore_session.py, sonra komutu tekrarlayin.")
        sys.exit(1)

    mp = save_manifest(manifest, archive_root)
    label = f"FAZ-{args.phase}" if args.phase is not None else f"tip-{args.type}"
    print(f"[arsiv] {label} tamamlandi. Manifest -> {mp}")


if __name__ == "__main__":
    main()
