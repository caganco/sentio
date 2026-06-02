"""Tests for D-199: BIST DataStore arsiv yardimcilari + orkestrator.

No network calls -- pure helpers test edilir, orkestratorde client mock'lanir.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from src.data import datastore_archive as da
from src.signals.thresholds import (
    DATASTORE_ARCHIVE_FREQUENCY,
    DATASTORE_ARCHIVE_LAYOUT,
    DATASTORE_PHASE_1,
    DATASTORE_PHASE_2,
    DATASTORE_PHASE_3,
)


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def _write_zip(path: Path, payload: bytes = b"hello", inner: str = "a.txt") -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(inner, payload)
    return path


def _write_csv(path: Path, lines: int = 3) -> Path:
    rows = ["col1,col2"] + [f"v{i},w{i}" for i in range(lines)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# resolve_subdir / layout
# ---------------------------------------------------------------------------

class TestResolveSubdir:
    def test_routes_each_layout_id(self, tmp_path):
        for type_id, subfolder in DATASTORE_ARCHIVE_LAYOUT.items():
            got = da.resolve_subdir(tmp_path, type_id)
            assert got == tmp_path / subfolder

    def test_unknown_id_raises_keyerror(self, tmp_path):
        with pytest.raises(KeyError):
            da.resolve_subdir(tmp_path, 999999)


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------

class TestSha256:
    def test_stable_same_content(self, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"deterministic-bytes")
        assert da.sha256_file(p) == da.sha256_file(p)

    def test_differs_on_one_byte_change(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(b"payload-A")
        b.write_bytes(b"payload-B")
        assert da.sha256_file(a) != da.sha256_file(b)


# ---------------------------------------------------------------------------
# check_integrity
# ---------------------------------------------------------------------------

class TestCheckIntegrity:
    def test_good_zip(self, tmp_path):
        ok, note = da.check_integrity(_write_zip(tmp_path / "g.zip"))
        assert ok is True
        assert "zip" in note

    def test_corrupt_zip(self, tmp_path):
        p = tmp_path / "bad.zip"
        p.write_bytes(b"this is not a zip file at all")
        ok, _ = da.check_integrity(p)
        assert ok is False

    def test_csv_non_empty(self, tmp_path):
        ok, note = da.check_integrity(_write_csv(tmp_path / "d.csv"))
        assert ok is True
        assert "csv" in note

    def test_csv_empty(self, tmp_path):
        p = tmp_path / "e.csv"
        p.write_text("", encoding="utf-8")
        ok, _ = da.check_integrity(p)
        assert ok is False

    def test_csv_single_line(self, tmp_path):
        p = tmp_path / "s.csv"
        p.write_text("only-header\n", encoding="utf-8")
        ok, _ = da.check_integrity(p)
        assert ok is False


# ---------------------------------------------------------------------------
# manifest roundtrip
# ---------------------------------------------------------------------------

class TestManifestIO:
    def test_load_skeleton_when_missing(self, tmp_path):
        m = da.load_manifest(tmp_path)
        assert m["schema_version"] == da.SCHEMA_VERSION
        assert m["directive"] == "D-199"
        assert m["types"] == {}

    def test_roundtrip_ascii_safe(self, tmp_path):
        m = da.load_manifest(tmp_path)
        m["types"]["3196"] = {"note": "Turkce karakter testi: islem gunu"}
        da.save_manifest(m, tmp_path)
        raw = (tmp_path / "_manifest.json").read_bytes()
        raw.decode("ascii")  # cp1254-safe: must be pure ASCII
        again = da.load_manifest(tmp_path)
        assert again["types"]["3196"]["note"] == m["types"]["3196"]["note"]


# ---------------------------------------------------------------------------
# build_file_record / coverage / update_type_entry
# ---------------------------------------------------------------------------

class TestRecordsAndEntry:
    def test_build_file_record_fields(self, tmp_path):
        z = _write_zip(tmp_path / "yabanci201601.zip")
        rec = da.build_file_record(z, "2016-01-01")
        assert rec["filename"] == "yabanci201601.zip"
        assert rec["data_date"] == "2016-01-01"
        assert rec["integrity_ok"] is True
        assert rec["size_bytes"] > 0
        assert len(rec["content_hash"]) == 64

    def test_coverage_range(self, tmp_path):
        recs = [
            da.build_file_record(_write_zip(tmp_path / "yabanci199612.zip"), "1996-12-01"),
            da.build_file_record(_write_zip(tmp_path / "yabanci202604.zip"), "2026-04-01"),
            da.build_file_record(_write_zip(tmp_path / "yabanci201001.zip"), "2010-01-01"),
        ]
        m = da.load_manifest(tmp_path)
        entry = da.update_type_entry(m, 3153, "foreign_flow", "monthly", recs)
        assert entry["coverage"]["start"] == "1996-12-01"
        assert entry["coverage"]["end"] == "2026-04-01"
        assert entry["coverage"]["n_files"] == 3

    def test_idempotent_merge(self, tmp_path):
        z = _write_zip(tmp_path / "yabanci199612.zip")
        rec = da.build_file_record(z, "1996-12-01")
        m = da.load_manifest(tmp_path)
        da.update_type_entry(m, 3153, "foreign_flow", "monthly", [rec])
        da.update_type_entry(m, 3153, "foreign_flow", "monthly", [rec])
        files = m["types"]["3153"]["files"]
        assert len(files) == 1  # no duplicate
        assert files[0]["content_hash"] == rec["content_hash"]

    def test_survivorship_preserved_on_reupdate(self, tmp_path):
        m = da.load_manifest(tmp_path)
        surv = {"delisted_present": "EVET", "probed_files": [], "examples_found": [], "note": "x"}
        da.update_type_entry(m, 3196, "prices_official", "daily", [], survivorship=surv)
        da.update_type_entry(m, 3196, "prices_official", "daily", [])  # no surv passed
        assert m["types"]["3196"]["survivorship"]["delisted_present"] == "EVET"


# ---------------------------------------------------------------------------
# scan_subdir_files / survivorship_peek
# ---------------------------------------------------------------------------

class TestScanAndSurvivorship:
    def test_scan_lists_files_sorted(self, tmp_path):
        (tmp_path / "b.csv").write_text("x\ny\n", encoding="utf-8")
        (tmp_path / "a.csv").write_text("x\ny\n", encoding="utf-8")
        names = [p.name for p in da.scan_subdir_files(tmp_path)]
        assert names == ["a.csv", "b.csv"]

    def test_scan_empty_dir(self, tmp_path):
        assert da.scan_subdir_files(tmp_path / "nope") == []

    def test_survivorship_evet(self, tmp_path):
        p = tmp_path / "PP_GUNSONUFIYATHACIM.M.198712.csv"
        p.write_text("date,ticker,close\n1987-12-01,KOZAA,10\n1987-12-01,IPEKE,5\n",
                     encoding="utf-8")
        out = da.survivorship_peek(tmp_path, ("KOZAA", "IPEKE", "TRALT"))
        assert out["delisted_present"] == "EVET"
        assert "KOZAA" in out["examples_found"]

    def test_survivorship_hayir(self, tmp_path):
        p = tmp_path / "PP_GUNSONUFIYATHACIM.M.202601.csv"
        p.write_text("date,ticker,close\n2026-01-01,GARAN,100\n", encoding="utf-8")
        out = da.survivorship_peek(tmp_path, ("KOZAA", "IPEKE"))
        assert out["delisted_present"] == "HAYIR"
        assert out["examples_found"] == []


# ---------------------------------------------------------------------------
# thresholds invariants
# ---------------------------------------------------------------------------

class TestThresholdsInvariants:
    def test_layout_covers_all_phase_ids(self):
        all_phase = set(DATASTORE_PHASE_1) | set(DATASTORE_PHASE_2) | set(DATASTORE_PHASE_3)
        assert all_phase <= set(DATASTORE_ARCHIVE_LAYOUT)

    def test_layout_keys_equal_frequency_keys(self):
        assert set(DATASTORE_ARCHIVE_LAYOUT) == set(DATASTORE_ARCHIVE_FREQUENCY)


# ---------------------------------------------------------------------------
# orchestrator (client mocked)
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_acquire_type_verify_only_no_network(self, tmp_path, monkeypatch):
        """verify-only: ag cagrisi yok, disk taranir, manifest dolar."""
        import scripts.archive_datastore as orch

        subdir = da.resolve_subdir(tmp_path, 3196)
        subdir.mkdir(parents=True)
        _write_csv(subdir / "PP_GUNSONUFIYATHACIM.M.198712.csv")

        # Guard: any client construction would fail the test.
        manifest = da.load_manifest(tmp_path)
        orch._acquire_type(None, 3196, str(tmp_path), None, True, manifest)

        entry = manifest["types"]["3196"]
        assert entry["subfolder"] == "prices_official"
        assert entry["coverage"]["n_files"] == 1
        assert entry["files"][0]["content_hash"]
        assert "survivorship" in entry  # 3196 always probed

    def test_acquire_type_download_routes_to_subfolder(self, tmp_path, monkeypatch):
        """Mock client: indirilen dosyalar dogru alt-klasore + manifest subfolder dogru."""
        import scripts.archive_datastore as orch

        class _Cat:
            def __init__(self, *_a, **_k):
                pass

            def list_free_products(self, *_a, **_k):
                return []

        class _Down:
            def __init__(self, *_a, **_k):
                pass

            def download_product(self, type_id, output_dir, since_date=None):
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                _write_zip(out / "exsrk1999.zip")
                return [out / "exsrk1999.zip"]

        import src.data.bist_datastore_client as client
        monkeypatch.setattr(client, "DatastoreCatalog", _Cat)
        monkeypatch.setattr(client, "DatastoreDownloader", _Down)

        manifest = da.load_manifest(tmp_path)
        orch._acquire_type(object(), 3184, str(tmp_path), None, False, manifest)

        assert (tmp_path / "index_components" / "exsrk1999.zip").exists()
        entry = manifest["types"]["3184"]
        assert entry["subfolder"] == "index_components"
        assert entry["frequency"] == "yearly"
        assert entry["coverage"]["n_files"] == 1
