"""Tier-A tests for the held-out iteration lockbox (RR-Y1-009).

The lockbox seals a held-out subset by a content-hash registered at Stage-0 freeze
time and lets the engine refuse to score the frozen prototype against it unless the
seal holds; the evaluation is then recorded as consumed (single-shot). These tests
pin: fingerprint determinism + value-sensitivity + subset selection; the
hash-mismatch / not-frozen refusals; the single-shot guard off a committed-style
marker; and the marker carries NO real data (only id / hash-prefix / trial-count /
timestamp). No-lockbox Stage-0 stays a perfect no-op.
"""
from __future__ import annotations

import dataclasses
import json

import numpy as np
import pandas as pd
import pytest

from src.engine.contracts import Frequency, Panel
from src.engine.lockbox import (
    assert_lockbox,
    consume_lockbox,
    lockbox_fingerprint,
    marker_path_for,
)
from src.engine.stage0_validator import Stage0, Stage0Error, validate_stage0


def _panel(*, n_names: int = 8, n_dates: int = 40, seed: int = 0) -> Panel:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    names = [f"S{i:03d}" for i in range(n_names)]
    close = pd.DataFrame(
        100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, size=(n_dates, n_names)), axis=0),
        index=dates, columns=names,
    )
    value_tl = pd.DataFrame(1e8, index=dates, columns=names)
    one = pd.Series(1.0, index=dates)
    return Panel(
        close=close, tr_gross=close.copy(), tr_net=close.copy(), value_tl=value_tl,
        membership={}, market=one * 100.0, tufe=one, tlref=one, frequency=Frequency.DAILY,
    )


def _stage0(lockbox_hash: str | None) -> Stage0:
    doc = {
        "prototip_id": "RR-Y1-009-toy",
        "hipotez": "toy lockbox",
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
        "denenen_konfig_sayisi": 7,
        "frozen_before_results": True,
        "date_frozen": "2026-06-05",
        "snapshots_content_hash_sha256_prefix": "",
        "strangler_constraints": "committed-motorlar-dokunulmaz",
        "lockbox_spec": {"names": None, "date_start": None, "date_end": None},
        "lockbox_content_hash": lockbox_hash,
    }
    return validate_stage0(doc)


class TestFingerprint:
    def test_deterministic_16_chars(self):
        p = _panel()
        a = lockbox_fingerprint(p)
        assert a == lockbox_fingerprint(_panel())  # same construction -> same hash
        assert len(a) == 16

    def test_value_sensitive(self):
        p = _panel()
        before = lockbox_fingerprint(p)
        p.close.iloc[0, 0] += 1e-6  # a single edit to the sealed values
        after = lockbox_fingerprint(p)
        assert before != after

    def test_order_invariant_in_columns(self):
        p = _panel()
        shuffled = dataclasses.replace(p, close=p.close.iloc[:, ::-1])
        assert lockbox_fingerprint(p) == lockbox_fingerprint(shuffled)

    def test_name_subset_changes_hash(self):
        p = _panel()
        whole = lockbox_fingerprint(p)
        subset = lockbox_fingerprint(p, names=["S000", "S001", "S002"])
        assert whole != subset

    def test_date_window_changes_hash(self):
        p = _panel()
        whole = lockbox_fingerprint(p)
        windowed = lockbox_fingerprint(p, date_start="2021-01-11", date_end="2021-01-29")
        assert whole != windowed


class TestMarkerPath:
    def test_sibling_consumed_suffix(self, tmp_path):
        s0 = tmp_path / "rry1009.stage0.json"
        marker = marker_path_for(s0)
        assert marker.parent == s0.parent
        assert marker.name == "rry1009.stage0.lockbox-consumed.json"


class TestAssertLockbox:
    def test_no_lockbox_is_noop(self, tmp_path):
        p = _panel()
        assert_lockbox(_stage0(None), p, tmp_path / "m.json")  # no raise, no file

    def test_matching_hash_passes(self, tmp_path):
        p = _panel()
        s0 = _stage0(lockbox_fingerprint(p))
        assert_lockbox(s0, p, tmp_path / "m.json")  # seal holds, no marker yet

    def test_hash_mismatch_raises(self, tmp_path):
        p = _panel()
        s0 = _stage0("deadbeefdeadbeef")  # not the sealed subset's fingerprint
        with pytest.raises(Stage0Error, match="lockbox-hash"):
            assert_lockbox(s0, p, tmp_path / "m.json")

    def test_wrong_panel_presented_raises(self, tmp_path):
        sealed = _panel(seed=0)
        other = _panel(seed=1)  # different values -> different fingerprint
        s0 = _stage0(lockbox_fingerprint(sealed))
        with pytest.raises(Stage0Error, match="lockbox-hash"):
            assert_lockbox(s0, other, tmp_path / "m.json")

    def test_not_frozen_raises(self, tmp_path):
        p = _panel()
        s0 = dataclasses.replace(_stage0(lockbox_fingerprint(p)), frozen_before_results=False)
        with pytest.raises(Stage0Error, match="frozen"):
            assert_lockbox(s0, p, tmp_path / "m.json")


class TestSingleShot:
    def test_consume_then_second_assert_refuses(self, tmp_path):
        p = _panel()
        s0 = _stage0(lockbox_fingerprint(p))
        marker = tmp_path / "rry1009.stage0.lockbox-consumed.json"
        assert_lockbox(s0, p, marker)  # first evaluation proceeds
        consume_lockbox(s0, marker)
        assert marker.exists()
        # a committed marker (present after git-checkout) blocks the second run.
        with pytest.raises(Stage0Error, match="already consumed"):
            assert_lockbox(s0, p, marker)

    def test_marker_carries_no_real_data(self, tmp_path):
        p = _panel()
        s0 = _stage0(lockbox_fingerprint(p))
        marker = tmp_path / "m.json"
        consume_lockbox(s0, marker)
        rec = json.loads(marker.read_text(encoding="utf-8"))
        assert set(rec) == {
            "prototip_id", "lockbox_hash_prefix", "denenen_konfig_sayisi", "consumed_at",
        }
        assert rec["prototip_id"] == "RR-Y1-009-toy"
        assert rec["lockbox_hash_prefix"] == lockbox_fingerprint(p)
        assert rec["denenen_konfig_sayisi"] == 7

    def test_consume_is_noop_without_lockbox(self, tmp_path):
        marker = tmp_path / "m.json"
        consume_lockbox(_stage0(None), marker)
        assert not marker.exists()
