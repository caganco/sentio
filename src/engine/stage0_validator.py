"""Stage-0 pre-registration validator (Section 6; recon S3).

The engine REFUSES to run unless a typed Stage-0 file is present, schema-valid,
frozen-before-results, and (optionally) matches a content-hash of the frozen
snapshot. This mirrors the committed ``d213`` precedent (refuse-if-absent +
sha256[:16] snapshot guard) and is the anti-slop, post-hoc-lock primitive.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS: tuple[str, ...] = (
    "prototip_id",
    "hipotez",
    "tutunma_noktasi",
    "split_modu",
    "psi",
    "faktor_notrleme",
    "embargo_h",
    "split_arm_floor",
    "sort_depth",
    "hedef_rejim",
    "frekans",
    "getiri_tabani",
    "keep_bar",
    "denenen_konfig_sayisi",
    "frozen_before_results",
    "date_frozen",
    "snapshots_content_hash_sha256_prefix",
    "strangler_constraints",
)

_VALID_HOLD = frozenset({"cross_sectional", "timing", "panel"})
_VALID_SPLIT = frozenset({"A", "B", "A+B"})
_VALID_FREQ = frozenset({"daily", "monthly"})


class Stage0Error(RuntimeError):
    """Raised when Stage-0 is absent, malformed, not frozen, or drifts from its snapshot."""


@dataclass(frozen=True)
class Stage0:
    """Typed view of the Section 6 pre-registration document."""

    prototip_id: str
    hipotez: str
    tutunma_noktasi: str
    split_modu: str
    psi: str
    faktor_notrleme: tuple[str, ...]
    embargo_h: str | int
    split_arm_floor: float
    sort_depth: str
    hedef_rejim: str
    frekans: str
    getiri_tabani: str
    keep_bar: dict[str, Any]
    denenen_konfig_sayisi: int
    frozen_before_results: bool
    date_frozen: str
    snapshots_content_hash_sha256_prefix: str
    strangler_constraints: str
    # held-out iteration lockbox (RR-Y1-009) -- OPTIONAL. When declared, the harness
    # refuses to score against the sealed subset unless its content-hash matches, and
    # records a single-shot consumed-marker. Absent fields -> fully backward compatible.
    lockbox_spec: dict[str, Any] | None = None
    lockbox_content_hash: str | None = None


def hash16(path: str | Path) -> str:
    """sha256 hex digest, first 16 chars -- the d213 snapshot-guard convention."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def load_stage0(path: str | Path) -> dict[str, Any]:
    """Read the Stage-0 JSON. Absent file -> the engine refuses to run."""
    p = Path(path)
    if not p.exists():
        raise Stage0Error(
            f"Stage-0 pre-registration absent: {p} -- engine REFUSES to run "
            "(freeze the hypothesis BEFORE measuring; d213 precedent)."
        )
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Stage0Error(f"Stage-0 file is not valid JSON: {p} ({exc})") from exc


def validate_stage0(doc: dict[str, Any]) -> Stage0:
    """Schema-check the Stage-0 doc and return a typed ``Stage0``.

    Enforces: all required fields present; ``frozen_before_results`` is true;
    enum fields valid; monthly frequency => Mod-A (Section 3.6); ``keep_bar`` has
    ``pbo_max`` / ``dsr_min`` keys.
    """
    missing = [k for k in REQUIRED_FIELDS if k not in doc]
    if missing:
        raise Stage0Error(f"Stage-0 missing required field(s): {missing}")

    if doc["frozen_before_results"] is not True:
        raise Stage0Error(
            "Stage-0 frozen_before_results must be true -- a doc frozen AFTER seeing "
            "results is post-hoc (Section 5 post-hoc-lock)."
        )

    if doc["tutunma_noktasi"] not in _VALID_HOLD:
        raise Stage0Error(
            f"tutunma_noktasi must be one of {sorted(_VALID_HOLD)} (got {doc['tutunma_noktasi']!r})"
        )
    if doc["split_modu"] not in _VALID_SPLIT:
        raise Stage0Error(
            f"split_modu must be one of {sorted(_VALID_SPLIT)} (got {doc['split_modu']!r})"
        )
    if doc["frekans"] not in _VALID_FREQ:
        raise Stage0Error(
            f"frekans must be one of {sorted(_VALID_FREQ)} (got {doc['frekans']!r})"
        )
    if doc["frekans"] == "monthly" and doc["split_modu"] != "A":
        raise Stage0Error(
            "monthly frequency requires split_modu 'A' (temporal-CPCV is power-poor "
            "at monthly frequency; Section 3.6)."
        )

    keep_bar = doc["keep_bar"]
    if not isinstance(keep_bar, dict) or "pbo_max" not in keep_bar or "dsr_min" not in keep_bar:
        raise Stage0Error("keep_bar must be an object with 'pbo_max' and 'dsr_min' keys.")

    factors = doc["faktor_notrleme"]
    if not isinstance(factors, list | tuple) or not factors:
        raise Stage0Error("faktor_notrleme must be a non-empty list (market is the minimum).")

    return Stage0(
        prototip_id=str(doc["prototip_id"]),
        hipotez=str(doc["hipotez"]),
        tutunma_noktasi=str(doc["tutunma_noktasi"]),
        split_modu=str(doc["split_modu"]),
        psi=str(doc["psi"]),
        faktor_notrleme=tuple(str(f) for f in factors),
        embargo_h=doc["embargo_h"],
        split_arm_floor=float(doc["split_arm_floor"]),
        sort_depth=str(doc["sort_depth"]),
        hedef_rejim=str(doc["hedef_rejim"]),
        frekans=str(doc["frekans"]),
        getiri_tabani=str(doc["getiri_tabani"]),
        keep_bar=dict(keep_bar),
        denenen_konfig_sayisi=int(doc["denenen_konfig_sayisi"]),
        frozen_before_results=bool(doc["frozen_before_results"]),
        date_frozen=str(doc["date_frozen"]),
        snapshots_content_hash_sha256_prefix=str(doc["snapshots_content_hash_sha256_prefix"]),
        strangler_constraints=str(doc["strangler_constraints"]),
        lockbox_spec=(dict(doc["lockbox_spec"]) if doc.get("lockbox_spec") is not None else None),
        lockbox_content_hash=(
            str(doc["lockbox_content_hash"]) if doc.get("lockbox_content_hash") else None
        ),
    )


def assert_snapshot_hash(stage0: Stage0, snapshot_path: str | Path) -> None:
    """Guard against frozen-data drift: the snapshot's content-hash must match
    the prefix recorded at freeze time. Empty prefix -> guard disabled (no-op)."""
    expected = stage0.snapshots_content_hash_sha256_prefix
    if not expected:
        return
    got = hash16(snapshot_path)
    if got != expected:
        raise Stage0Error(
            f"snapshot content-hash drift: expected {expected!r}, got {got!r} for "
            f"{Path(snapshot_path).name} -- the frozen data changed under the pre-registration."
        )


def require_stage0(path: str | Path, snapshot_path: str | Path | None = None) -> Stage0:
    """Convenience: load + validate (+ optional snapshot-hash guard) in one call."""
    stage0 = validate_stage0(load_stage0(path))
    if snapshot_path is not None:
        assert_snapshot_hash(stage0, snapshot_path)
    return stage0
