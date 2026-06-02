"""BIST DataStore arsiv yardimcilari (D-199) -- saf, agsiz, test-edilebilir.

Bu modul HTTP yapmaz ve client'i (bist_datastore_client) top-level import
ETMEZ. Yalniz layout-cozumu, manifest IO, hashing, integrity ve hafif
survivorship-peek saglar. Orkestrasyon scripts/archive_datastore.py'de.

Zaman/hash konvansiyonu src/screening/snapshot.py ile ayni:
  hashlib.sha256(...).hexdigest()
  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

ASCII-only ciktilar (Windows cp1254 konsolu unicode'da coker).
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src.signals.thresholds import (
    DATASTORE_ARCHIVE_FREQUENCY,
    DATASTORE_ARCHIVE_LAYOUT,
    DATASTORE_ARCHIVE_MANIFEST,
    DATASTORE_ARCHIVE_ROOT,
)

SCHEMA_VERSION = 1
DIRECTIVE = "D-199"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_subdir(archive_root: str | Path, type_id: int) -> Path:
    """type_id -> arsiv alt-dizini (DATASTORE_ARCHIVE_LAYOUT). Bilinmeyen -> KeyError."""
    subfolder = DATASTORE_ARCHIVE_LAYOUT[type_id]
    return Path(archive_root) / subfolder


def sha256_file(path: str | Path, chunk: int = 65536) -> str:
    """Ham bayt streamed sha256 (zip/csv opak blob). snapshot.py deseni."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def check_integrity(path: str | Path) -> tuple[bool, str]:
    """Dosya butunlugu. zip->is_zipfile+testzip; csv->bos-degil & >1 satir; diger->size>0.

    Doner (ok, ascii_note).
    """
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        size = p.stat().st_size
    except OSError as exc:
        return False, f"stat failed: {exc}"

    if suffix == ".zip":
        if not zipfile.is_zipfile(p):
            return False, "not a valid zip"
        try:
            with zipfile.ZipFile(p) as zf:
                bad = zf.testzip()
        except zipfile.BadZipFile as exc:
            return False, f"bad zip: {exc}"
        if bad is not None:
            return False, f"crc fail: {bad}"
        return True, "zip ok"

    if suffix == ".csv":
        if size == 0:
            return False, "csv empty"
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                lines = 0
                for _ in fh:
                    lines += 1
                    if lines > 1:
                        break
        except OSError as exc:
            return False, f"read failed: {exc}"
        if lines <= 1:
            return False, "csv single-line"
        return True, "csv non-empty"

    if size > 0:
        return True, f"size {size} ok"
    return False, "empty file"


def manifest_path(archive_root: str | Path) -> Path:
    return Path(archive_root) / DATASTORE_ARCHIVE_MANIFEST


def _skeleton(archive_root: str | Path) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "directive": DIRECTIVE,
        "archive_root": str(archive_root),
        "timestamp_utc": _utc_now(),
        "types": {},
    }


def load_manifest(archive_root: str | Path = DATASTORE_ARCHIVE_ROOT) -> dict:
    """Manifest'i yukle; yoksa iskelet don."""
    mp = manifest_path(archive_root)
    if not mp.exists():
        return _skeleton(archive_root)
    with open(mp, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_manifest(manifest: dict, archive_root: str | Path = DATASTORE_ARCHIVE_ROOT) -> Path:
    """Manifest'i ASCII-guvenli JSON olarak yaz (cp1254-safe)."""
    manifest["timestamp_utc"] = _utc_now()
    mp = manifest_path(archive_root)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    return mp


def build_file_record(path: str | Path, data_date_iso: str | None) -> dict:
    """Tek dosya icin manifest kaydi (hash + integrity + boyut)."""
    p = Path(path)
    ok, note = check_integrity(p)
    return {
        "filename": p.name,
        "data_date": data_date_iso,
        "content_hash": sha256_file(p),
        "size_bytes": p.stat().st_size,
        "integrity_ok": ok,
        "integrity_note": note,
    }


def _coverage(records: list[dict]) -> dict:
    """data_date alanlarindan kapsama araligi (None'lar atlanir)."""
    dates = sorted(r["data_date"] for r in records if r.get("data_date"))
    return {
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
        "n_files": len(records),
    }


def update_type_entry(
    manifest: dict,
    type_id: int,
    subfolder: str,
    frequency: str,
    files: list[dict],
    survivorship: dict | None = None,
) -> dict:
    """Tip kaydini idempotent merge et (dosya-adina gore), coverage'i yeniden hesapla."""
    types = manifest.setdefault("types", {})
    key = str(type_id)
    existing = types.get(key, {})
    by_name: dict[str, dict] = {r["filename"]: r for r in existing.get("files", [])}
    for rec in files:
        by_name[rec["filename"]] = rec  # yeni/guncel kayit eskini ezer (idempotent)
    merged = sorted(by_name.values(), key=lambda r: r["filename"])

    entry = {
        "subfolder": subfolder,
        "frequency": frequency,
        "coverage": _coverage(merged),
        "acquired_at": _utc_now(),
        "files": merged,
    }
    if survivorship is not None:
        entry["survivorship"] = survivorship
    elif "survivorship" in existing:
        entry["survivorship"] = existing["survivorship"]

    types[key] = entry
    return entry


def scan_subdir_files(subdir: str | Path) -> list[Path]:
    """Alt-dizindeki gercek dosyalari listele (manifest'i disk-gerceginden kurar)."""
    p = Path(subdir)
    if not p.exists():
        return []
    return sorted(f for f in p.iterdir() if f.is_file())


def survivorship_peek(
    subdir: str | Path,
    known_delisted: tuple[str, ...],
    max_files: int = 3,
) -> dict:
    """En eski 1-3 PP_GUNSONUFIYATHACIM.M.*.csv'de bilinen-delisted token'i ARA.

    Duz substring; DataFrame/sema YOK. Doner:
      {delisted_present: "EVET"/"HAYIR", probed_files, examples_found, note}
    """
    p = Path(subdir)
    candidates = sorted(
        f for f in scan_subdir_files(p)
        if f.name.upper().startswith("PP_GUNSONUFIYATHACIM") and f.suffix.lower() == ".csv"
    )
    probed = candidates[:max_files]
    found: set[str] = set()
    for f in probed:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in known_delisted:
            if token in text:
                found.add(token)
    return {
        "delisted_present": "EVET" if found else "HAYIR",
        "probed_files": [f.name for f in probed],
        "examples_found": sorted(found),
        "note": "light peek: known-delisted tokens searched in csv bytes",
    }


def frequency_for(type_id: int) -> str:
    return DATASTORE_ARCHIVE_FREQUENCY.get(type_id, "unknown")
