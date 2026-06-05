"""Held-out iteration lockbox: single-shot enforcement (RR-Y1-009).

The intended research workflow is: discover/iterate a prototype on a discovery
set, FREEZE it, then evaluate ONCE on independent data. Stage-0 already freezes
the *design*; the lockbox additionally seals a held-out data subset (by name, by
time block, or both) and lets the engine refuse to score the frozen prototype
against it unless: Stage-0 is present, ``frozen_before_results`` is true, and the
lockbox content-hash matches the registered one -- then records the evaluation as
consumed so the sealed set can never be re-used as a tuning surface.

This constrains *when* a statistic may be computed, never the statistic itself.
It is OPTIONAL: a Stage-0 that declares no lockbox runs exactly as before
(backward compatible). When declared, it is mechanically enforced.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import Panel
from .stage0_validator import Stage0, Stage0Error


def lockbox_fingerprint(
    panel: Panel,
    *,
    names: list[str] | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
) -> str:
    """``sha256[:16]`` over a canonical byte serialization of the sealed subset's
    ACTUAL values (strong anti-tamper, the d213 ``hash16`` 16-char convention).

    ``names`` / ``date_start`` / ``date_end`` narrow the panel; omitting them seals
    the whole passed panel. The payload is order-invariant (names sorted, dates
    sorted) and binds the exact float values, so any edit to the sealed data --
    not just its coordinates -- changes the hash.

    Used by the researcher at FREEZE time (to register ``lockbox_content_hash`` in
    Stage-0) and by the engine at EVAL time (to verify the panel presented is the
    sealed set). Deterministic and shared.
    """
    close = panel.close
    if date_start is not None or date_end is not None:
        close = close.loc[date_start:date_end]
    sel_names = sorted(names) if names is not None else sorted(str(c) for c in close.columns)
    close = close.loc[:, sel_names].sort_index()
    dates = pd.DatetimeIndex(close.index).strftime("%Y-%m-%d")
    payload = b"|".join(
        [
            ",".join(sel_names).encode("ascii"),
            ",".join(dates).encode("ascii"),
            np.ascontiguousarray(close.to_numpy(dtype="float64")).tobytes(),
        ]
    )
    return hashlib.sha256(payload).hexdigest()[:16]


def marker_path_for(stage0_path: str | Path) -> Path:
    """Sibling of the Stage-0 file: ``{stem}.lockbox-consumed.json``.

    NOT git-ignored -- a COMMITTED audit-trail (same commit-pattern as the Stage-0
    JSONs themselves). The single-shot guard works identically off a committed
    marker: after a fresh ``git checkout`` the marker is present, so a second run
    is refused -- non-repudiable discipline.
    """
    p = Path(stage0_path)
    return p.with_name(f"{p.stem}.lockbox-consumed.json")


def assert_lockbox(stage0: Stage0, panel: Panel, marker_path: str | Path) -> None:
    """Refuse to score the frozen prototype against the lockbox unless the seal
    holds. Raises ``Stage0Error`` if the lockbox is declared but Stage-0 is not
    frozen, if the presented panel's fingerprint != the registered hash, or if the
    lockbox was already consumed (single-shot).

    No-op when no lockbox is declared (``lockbox_content_hash`` empty/None).
    """
    expected = stage0.lockbox_content_hash
    if not expected:
        return
    if stage0.frozen_before_results is not True:
        raise Stage0Error(
            "lockbox declared but Stage-0 frozen_before_results is not true -- a "
            "held-out set may only be scored under a pre-registered freeze."
        )
    got = lockbox_fingerprint(panel)
    if got != expected:
        raise Stage0Error(
            f"lockbox-hash mismatch: expected {expected!r}, got {got!r} -- the panel "
            "presented is not the sealed held-out subset registered at freeze time."
        )
    marker = Path(marker_path)
    if marker.exists():
        try:
            prev = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev = {}
        if prev.get("lockbox_hash_prefix") == expected:
            raise Stage0Error(
                f"lockbox already consumed: {marker.name} records hash {expected!r}. "
                "A sealed held-out set is single-shot -- to evaluate again, register a "
                "NEW lockbox (different subset -> different hash). Re-using it as a "
                "tuning surface is forbidden (RR-Y1-009)."
            )


def consume_lockbox(stage0: Stage0, marker_path: str | Path) -> None:
    """Record the lockbox evaluation as consumed (single-shot).

    Writes the marker JSON. The marker is DESIGNED TO BE COMMITTED -- it is the
    non-repudiable audit record of the one allowed evaluation (production location
    = Stage-0 sibling via ``marker_path_for``; ``tmp_path`` is used only by tests).
    It carries NO real data: only ``prototip_id``, the 16-char
    ``lockbox_hash_prefix``, ``denenen_konfig_sayisi`` (the honest trial count fed
    to DSR deflation), and a UTC ``consumed_at`` timestamp.

    No-op when no lockbox is declared.
    """
    if not stage0.lockbox_content_hash:
        return
    record = {
        "prototip_id": stage0.prototip_id,
        "lockbox_hash_prefix": stage0.lockbox_content_hash,
        "denenen_konfig_sayisi": stage0.denenen_konfig_sayisi,
        "consumed_at": datetime.now(UTC).isoformat(),
    }
    Path(marker_path).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
