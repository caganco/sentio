"""UniverseSnapshot tests (D-107, SPEC_ALPHA_INFRASTRUCTURE_1 Phase 2)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.data.universe_snapshot import UniverseSnapshot


class TestUniverseSnapshot:

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        snap = UniverseSnapshot(base_path=str(tmp_path))
        bist100 = ["AKBNK", "GARAN", "THYAO", "ASELS"]
        bist30 = ["AKBNK", "GARAN", "THYAO"]
        snap.save(as_of=date(2026, 5, 31), bist100=bist100, bist30=bist30,
                  source="manual", warning=None)
        loaded = snap.load(2026, 5)
        assert loaded is not None
        assert loaded["source"] == "manual"
        assert set(loaded["bist100"]) == set(bist100)
        assert set(loaded["bist30"]) == set(bist30)

    def test_liquidity_tier_bist30(self, tmp_path: Path) -> None:
        snap = UniverseSnapshot(base_path=str(tmp_path))
        snap.save(as_of=date(2026, 5, 31), bist100=["AKBNK", "XXXXX"],
                  bist30=["AKBNK"], source="manual")
        assert snap.get_liquidity_tier("AKBNK", 2026, 5) == "BIST30"
        assert snap.get_liquidity_tier("XXXXX", 2026, 5) == "BIST100"

    def test_liquidity_tier_unknown_returns_outside(self, tmp_path: Path) -> None:
        snap = UniverseSnapshot(base_path=str(tmp_path))
        snap.save(as_of=date(2026, 5, 31), bist100=["AKBNK"], bist30=["AKBNK"],
                  source="manual")
        assert snap.get_liquidity_tier("ZZZZZ", 2026, 5) == "Outside"

    def test_missing_snapshot_returns_none(self, tmp_path: Path) -> None:
        snap = UniverseSnapshot(base_path=str(tmp_path))
        # No snapshot saved for 2018-01
        assert snap.load(2018, 1) is None
        # Liquidity tier query on missing snapshot -> "Outside"
        assert snap.get_liquidity_tier("AKBNK", 2018, 1) == "Outside"
