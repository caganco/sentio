"""RR-Y1-005 conjugate-universe validation engine (Yol-1 infrastructure, DEC-045).

LIVE v2 infrastructure -- NOT a graveyard artifact. A general-purpose, tunable,
post-hoc-auditable strategy-validation harness:

    harness(panel, sinyal, split_spec, dial_config) -> output-vector

Built PARALLEL to the committed motors (strangler): it imports committed
primitives read-only and touches no committed file. Single-universe (X) and
conjugate (X_1 / X_2) tests run on one core; conjugate is just a split-mode.

Design   : RR-Y1-005-TEST-MOTORU-TASARIM v0.2 (what/why)
Math      : RR-Y1-005B-MATEMATIKSEL-SPEC v1.1 (formal core)
Discipline: PM-1 law, Stage-0 freeze, anti-slop golden-fixture + synthetic-null.
"""
from __future__ import annotations

__version__ = "0.1.0"  # Faz-0 scaffold (data_adapter + Stage-0 + contracts)
