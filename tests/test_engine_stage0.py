"""Tier-A tests for the Stage-0 pre-registration validator (Section 6)."""
from __future__ import annotations

import json

import pytest

from src.engine.stage0_validator import (
    Stage0Error,
    assert_snapshot_hash,
    hash16,
    load_stage0,
    require_stage0,
    validate_stage0,
)


def _valid_doc() -> dict:
    return {
        "prototip_id": "RR-Y1-007-toy",
        "hipotez": "toy edge",
        "tutunma_noktasi": "cross_sectional",
        "split_modu": "A",
        "psi": "rank_ic",
        "faktor_notrleme": ["market"],
        "embargo_h": "construction_window",
        "split_arm_floor": 1e7,
        "sort_depth": "tercile",
        "hedef_rejim": "agnostic",
        "frekans": "daily",
        "getiri_tabani": "total_return",
        "keep_bar": {"pbo_max": 0.5, "dsr_min": 0.95},
        "denenen_konfig_sayisi": 1,
        "frozen_before_results": True,
        "date_frozen": "2026-06-05",
        "snapshots_content_hash_sha256_prefix": "",
        "strangler_constraints": "committed-motorlar-dokunulmaz",
    }


class TestLoad:
    def test_absent_refuses_to_run(self, tmp_path):
        with pytest.raises(Stage0Error, match="REFUSES to run"):
            load_stage0(tmp_path / "nope.json")

    def test_bad_json_raises(self, tmp_path):
        p = tmp_path / "s.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(Stage0Error, match="not valid JSON"):
            load_stage0(p)


class TestValidate:
    def test_valid_doc(self):
        s = validate_stage0(_valid_doc())
        assert s.prototip_id == "RR-Y1-007-toy"
        assert s.faktor_notrleme == ("market",)
        assert s.frozen_before_results is True

    def test_missing_field(self):
        d = _valid_doc()
        del d["psi"]
        with pytest.raises(Stage0Error, match="missing required"):
            validate_stage0(d)

    def test_not_frozen_rejected(self):
        d = _valid_doc()
        d["frozen_before_results"] = False
        with pytest.raises(Stage0Error, match="frozen_before_results"):
            validate_stage0(d)

    def test_monthly_requires_mod_a(self):
        d = _valid_doc()
        d["frekans"] = "monthly"
        d["split_modu"] = "B"
        with pytest.raises(Stage0Error, match="monthly"):
            validate_stage0(d)

    def test_bad_hold_point(self):
        d = _valid_doc()
        d["tutunma_noktasi"] = "vibes"
        with pytest.raises(Stage0Error, match="tutunma_noktasi"):
            validate_stage0(d)

    def test_keep_bar_keys_required(self):
        d = _valid_doc()
        d["keep_bar"] = {"pbo_max": 0.5}
        with pytest.raises(Stage0Error, match="keep_bar"):
            validate_stage0(d)

    def test_empty_factors_rejected(self):
        d = _valid_doc()
        d["faktor_notrleme"] = []
        with pytest.raises(Stage0Error, match="faktor_notrleme"):
            validate_stage0(d)


class TestSnapshotHash:
    def test_hash16_deterministic_16_chars(self, tmp_path):
        f = tmp_path / "snap.parquet"
        f.write_bytes(b"abc123")
        assert hash16(f) == hash16(f)
        assert len(hash16(f)) == 16

    def test_drift_raises(self, tmp_path):
        f = tmp_path / "snap.parquet"
        f.write_bytes(b"abc123")
        d = _valid_doc()
        d["snapshots_content_hash_sha256_prefix"] = "deadbeefdeadbeef"
        with pytest.raises(Stage0Error, match="content-hash drift"):
            assert_snapshot_hash(validate_stage0(d), f)

    def test_match_ok(self, tmp_path):
        f = tmp_path / "snap.parquet"
        f.write_bytes(b"abc123")
        d = _valid_doc()
        d["snapshots_content_hash_sha256_prefix"] = hash16(f)
        assert_snapshot_hash(validate_stage0(d), f)  # no raise

    def test_empty_prefix_is_noop(self, tmp_path):
        f = tmp_path / "snap.parquet"
        f.write_bytes(b"abc")
        assert_snapshot_hash(validate_stage0(_valid_doc()), f)  # empty prefix -> guard off


class TestRequire:
    def test_end_to_end(self, tmp_path):
        snap = tmp_path / "snap.parquet"
        snap.write_bytes(b"xyz")
        d = _valid_doc()
        d["snapshots_content_hash_sha256_prefix"] = hash16(snap)
        p = tmp_path / "stage0.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        s = require_stage0(p, snap)
        assert s.split_modu == "A"


class TestLockboxFields:
    """RR-Y1-009 optional lockbox fields: present -> round-trip; absent -> default None."""

    def test_absent_lockbox_defaults_to_none(self):
        s = validate_stage0(_valid_doc())  # no lockbox keys -> backward compatible
        assert s.lockbox_spec is None
        assert s.lockbox_content_hash is None

    def test_present_lockbox_round_trips(self):
        d = _valid_doc()
        d["lockbox_spec"] = {"names": ["AKBNK", "GARAN"], "date_start": "2024-01-01", "date_end": None}
        d["lockbox_content_hash"] = "0123456789abcdef"
        s = validate_stage0(d)
        assert s.lockbox_spec == {"names": ["AKBNK", "GARAN"], "date_start": "2024-01-01", "date_end": None}
        assert s.lockbox_content_hash == "0123456789abcdef"

    def test_empty_hash_normalizes_to_none(self):
        d = _valid_doc()
        d["lockbox_content_hash"] = ""  # empty string -> guard disabled (None)
        assert validate_stage0(d).lockbox_content_hash is None
