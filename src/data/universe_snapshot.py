"""BIST100 universe snapshot manager (DEC-015).

Saves month-end BIST100 component lists for survivorship-free IC calculation.
Faz 1: yfinance + manual override (current constituents only -- survivorship-biased).
Faz 1.5: manual historical CSV import for 2023-2026.
Faz 2: MKK API integration after KAP contract.

Storage: data/universe_snapshots/YYYY-MM.json
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from src.signals.thresholds import UNIVERSE_SNAPSHOT_PATH

logger = logging.getLogger(__name__)

# Known BIST30 constituents (manual approx -- update quarterly).
# Source: borsaistanbul.com/en/indices/bist-stock-indices/bist-30
_KNOWN_BIST30: list[str] = [
    "AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO", "ENKAI", "EREGL",
    "FROTO", "GARAN", "HALKB", "ISCTR", "KCHOL", "KOZAL", "LOGO",
    "MGROS", "ODAS", "PGSUS", "PETKM", "SAHOL", "SISE", "TAVHL",
    "THYAO", "TKFEN", "TOASO", "TTKOM", "TUPRS", "VAKBN", "YKBNK",
    "AKSEN", "KRDMD",
]


class UniverseSnapshot:
    """Load and save BIST100 universe snapshots keyed by year-month."""

    def __init__(self, base_path: str = UNIVERSE_SNAPSHOT_PATH) -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        as_of: date,
        bist100: list[str],
        bist30: list[str],
        source: str = "yahoo",
        warning: str | None = None,
    ) -> Path:
        key = f"{as_of.year}-{as_of.month:02d}"
        path = self._base / f"{key}.json"
        data = {
            "as_of": as_of.isoformat(),
            "source": source,
            "bist30": sorted(bist30),
            "bist100": sorted(bist100),
            "warning": warning,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("universe_snapshot: saved %s (%d BIST100, %d BIST30) source=%s",
                    key, len(bist100), len(bist30), source)
        return path

    def load(self, year: int, month: int) -> dict | None:
        path = self._base / f"{year}-{month:02d}.json"
        if not path.exists():
            logger.warning("universe_snapshot: %d-%02d not found -- survivorship warning",
                           year, month)
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_liquidity_tier(self, symbol: str, year: int, month: int) -> str:
        snap = self.load(year, month)
        if snap is None:
            return "Outside"
        if symbol in snap.get("bist30", []):
            return "BIST30"
        if symbol in snap.get("bist100", []):
            return "BIST100"
        return "Outside"

    def fetch_and_save_current(self) -> dict:
        """Fetch current BIST100 from config (yfinance-backed) and save.

        Faz 1 limitation: only captures TODAY's constituents -- historical
        snapshots must be manually imported or sourced from MKK API.
        """
        try:
            from src.data.fetcher import get_bist100_tickers
            raw = get_bist100_tickers()
            bist100 = [t.replace(".IS", "") for t in raw]
            bist30 = [t for t in _KNOWN_BIST30 if t in bist100]
            today = date.today()
            path = self.save(
                as_of=today,
                bist100=bist100,
                bist30=bist30,
                source="yahoo",
                warning="survivorship_bias_faz1",
            )
            return {"status": "ok", "path": str(path), "count": len(bist100)}
        except Exception as exc:
            logger.error("universe_snapshot: fetch failed: %s", exc)
            return {"status": "error", "error": str(exc)}
