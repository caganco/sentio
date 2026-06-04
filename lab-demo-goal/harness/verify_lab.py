"""lab-demo-goal: DISCIPLINE-INTEGRITY checker (READ-ONLY, no new data, no edge).

Asserts the lab's auditability invariants so a future reader/session can confirm nothing
drifted from the disciplined, pre-registered, honest-null program:

  1. Every results/*.json references a stage0 file that EXISTS.
  2. Every stage0 has frozen_before_results == true (pre-registration intact).
  3. Every results verdict is HONESTLY NON-DEPLOYABLE (no leg claims a tradeable edge):
     a non-deployable marker is present AND every known deploy-counter is zero/empty.
  4. Every L-track harness guards on Stage-0 (contains require_stage0).
  5. Every committed lab text file is ASCII and carries no machine-absolute path.

Exits non-zero on any failure. Run:
  PYTHONPATH=. python lab-demo-goal/harness/verify_lab.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
RES = LAB / "results"
STAGE0 = LAB / "stage0"
HARNESS = LAB / "harness"

NONDEPLOY_MARKERS = ("not a deployable", "not-tradeable", "no deployable",
                     "no edge", "synthesis", "descriptive")
DEPLOY_COUNTER_FIELDS = ("deploy_candidates", "deployable_windows",
                         "deploy_candidates_NO_WALL", "n_deploy_candidates_NO_WALL")
ABS_PATH_NEEDLE = "C:" + chr(92) + "Users"


def _norm(p: str) -> Path:
    return ROOT / p.replace("\\", "/")


def check_results() -> list[str]:
    fails = []
    res_files = sorted(RES.glob("*.json"))
    if not res_files:
        return ["NO results/*.json found"]
    for f in res_files:
        d = json.loads(f.read_text(encoding="utf-8"))
        # (1) stage0 reference exists
        s0_ref = d.get("stage0")
        if not s0_ref:
            fails.append(f"{f.name}: missing 'stage0' field")
            continue
        s0_path = _norm(s0_ref)
        if not s0_path.exists():
            fails.append(f"{f.name}: stage0 '{s0_ref}' does not exist")
            continue
        # (2) stage0 frozen
        s0 = json.loads(s0_path.read_text(encoding="utf-8"))
        if not s0.get("frozen_before_results"):
            fails.append(f"{f.name}: stage0 not frozen_before_results=true")
        # (3) verdict honestly non-deployable
        v = d.get("verdict", {})
        vstr = (v.get("verdict", "") if isinstance(v, dict) else str(v)).lower()
        if not any(m in vstr for m in NONDEPLOY_MARKERS):
            fails.append(f"{f.name}: verdict lacks a non-deployable marker -> '{vstr[:60]}'")
        # any deploy counter must be zero/empty wherever present
        for scope in (v if isinstance(v, dict) else {}, d.get("summary", {}) or {}):
            for fld in DEPLOY_COUNTER_FIELDS:
                if fld in scope:
                    val = scope[fld]
                    empty = (val in (0, None) or (isinstance(val, (list, dict)) and len(val) == 0))
                    if not empty:
                        fails.append(f"{f.name}: deploy-counter '{fld}'={val!r} is non-zero")
    return fails


def check_harness_guards() -> list[str]:
    fails = []
    for f in sorted(HARNESS.glob("l*_*.py")):  # L-track harnesses (excludes verify_lab.py)
        txt = f.read_text(encoding="utf-8")
        if "require_stage0" not in txt:
            fails.append(f"{f.name}: no require_stage0 Stage-0 guard")
    return fails


def check_ascii_and_paths() -> list[str]:
    fails = []
    text_ext = {".json", ".md", ".py"}
    for f in sorted(LAB.rglob("*")):
        if not f.is_file() or f.suffix not in text_ext:
            continue
        raw = f.read_bytes()
        nonascii = [i for i, b in enumerate(raw) if b > 127]
        if nonascii:
            fails.append(f"{f.relative_to(LAB)}: {len(nonascii)} non-ASCII byte(s)")
        if ABS_PATH_NEEDLE in raw.decode("utf-8", errors="replace"):
            fails.append(f"{f.relative_to(LAB)}: contains machine-absolute path")
    return fails


def main() -> int:
    n_res = len(list(RES.glob("*.json")))
    n_s0 = len(list(STAGE0.glob("*.json")))
    print(f"lab-demo-goal integrity check:  results={n_res}  stage0={n_s0}")

    sections = {
        "results<->stage0 pairing + frozen + honest-verdict": check_results(),
        "harness Stage-0 guards": check_harness_guards(),
        "ASCII + no-absolute-path": check_ascii_and_paths(),
    }
    total_fail = 0
    for name, fails in sections.items():
        if fails:
            total_fail += len(fails)
            print(f"  [FAIL] {name}: {len(fails)} issue(s)")
            for msg in fails:
                print(f"         - {msg}")
        else:
            print(f"  [PASS] {name}")

    if total_fail == 0:
        print("RESULT: PASS -- lab discipline invariants intact "
              "(pre-registered, honest-null, no deployable edge claimed, ASCII, no leaked paths).")
        return 0
    print(f"RESULT: FAIL -- {total_fail} invariant violation(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
