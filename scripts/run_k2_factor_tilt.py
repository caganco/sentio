"""Thin runner for the K2 factor-tilt backtest (D-191).

Delegates to src.screening.k2_factor_tilt. Two modes:
  --discover-itemcodes   live MaliTablo discovery (Faz B, freeze profit itemCodes)
  --run                  run the backtest from frozen snapshots (default)

Equivalent to: python -m src.screening.k2_factor_tilt --run
"""
from __future__ import annotations

import sys

from src.screening.k2_factor_tilt import _main

if __name__ == "__main__":
    if len(sys.argv) == 1:           # default action: run from frozen snapshots
        sys.argv.append("--run")
    _main()
