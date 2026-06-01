"""Thin runner for the value-only REGIME-RESILIENCE backtest (D-Y1-001).

Delegates to src.screening.value_only_regime. One mode:
  --run   run the measurement from frozen snapshots (offline, default)

Equivalent to: python -m src.screening.value_only_regime --run
"""
from __future__ import annotations

import sys

from src.screening.value_only_regime import _main

if __name__ == "__main__":
    if len(sys.argv) == 1:           # default action: run from frozen snapshots
        sys.argv.append("--run")
    _main()
