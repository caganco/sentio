"""Pre-commit helper: run pytest only for tests that match staged files.

Tier-1 architecture tests always run (structural invariants, ~2-3s).
All other tests run only when their corresponding source file is staged.

Mapping convention:
  src/X/foo.py          → tests/test_foo.py          (stem match)
  tests/test_foo.py     → tests/test_foo.py           (direct)
  src/signals/engine.py → tests/test_signal_alert.py  (override)
  src/backtest/*.py     → tests/test_backtest.py       (override)

Full regression stays in CI — never run locally on every commit.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Always run — structural invariants that guard the whole codebase.
_ALWAYS: list[str] = ["tests/test_architecture.py"]

# Non-obvious stem → test file mappings (STEM: test-file, not module: test-file).
# Add a row whenever a module is renamed or tested by a non-matching file.
_OVERRIDES: dict[str, list[str]] = {
    "engine":              ["tests/test_signal_alert.py"],
    "thresholds":          ["tests/test_architecture.py"],
    "calculator":          ["tests/test_signal_alert.py"],
    "strategist":          ["tests/test_signal_alert.py"],
    "macro_regime_gate":   ["tests/test_signal_alert.py"],
    "local_macro_signals": ["tests/test_signal_alert.py"],
    "data_adapter":        ["tests/test_backtest.py"],
    "harness":             ["tests/test_backtest.py"],
    "moda":                ["tests/test_backtest.py"],
    "modb":                ["tests/test_backtest.py"],
    "modc":                ["tests/test_backtest.py"],
    "stats":               ["tests/test_backtest.py"],
    "neutralizer":         ["tests/test_backtest.py"],
    "dsr":                 ["tests/test_backtest.py"],
    "pbo":                 ["tests/test_backtest.py"],
    "clean_universe_builder": ["tests/test_backtest.py"],
}


def _staged_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--staged", "--name-only"], text=True
        )
        return out.splitlines()
    except subprocess.CalledProcessError:
        return []


def _map_to_tests(staged: list[str]) -> list[str]:
    tests: set[str] = set(_ALWAYS)
    for f in staged:
        p = Path(f)
        if p.suffix != ".py":
            continue

        # Staged file is itself a test → include directly
        if p.parts[0] in {"tests"} or str(p).startswith(("tests/", "tests\\")):
            if p.exists():
                tests.add(f)
            continue

        stem = p.stem

        # Explicit override mapping
        if stem in _OVERRIDES:
            tests.update(_OVERRIDES[stem])
            continue

        # Convention: any src/**/{stem}.py → tests/test_{stem}.py
        candidate = Path("tests") / f"test_{stem}.py"
        if candidate.exists():
            tests.add(str(candidate))
        # No match → Tier-1 (already in _ALWAYS) is the safety net

    return sorted(f for f in tests if Path(f).exists())


def main() -> int:
    staged = _staged_files()
    if not staged:
        return 0

    test_files = _map_to_tests(staged)
    if not test_files:
        return 0

    # Show which tests are running so the dev knows what's happening
    print(f"[affected] {' '.join(test_files)}", flush=True)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *test_files, "-q", "--tb=short"],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
