"""Tests for src/data/kap_scheduler.py."""

import json
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.data.kap_parser import KapEvent
from src.data.kap_scheduler import write_kap_json


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(
    index="100",
    symbol="THYAO",
    category="ozel_durum",
    subject="Ozel Durum Aciklamasi",
    published_at=None,
):
    return KapEvent(
        disclosure_index=index,
        symbol=symbol,
        published_at=published_at or datetime(2026, 5, 13, 9, 0),
        fetched_at=datetime(2026, 5, 13, 17, 0),
        subject=subject,
        category=category,
        summary="Ozet metin.",
        url=f"https://www.kap.org.tr/tr/Bildirim/{index}",
    )


# ---------------------------------------------------------------------------
# write_kap_json
# ---------------------------------------------------------------------------

class TestWriteKapJson:

    def test_creates_file(self, tmp_path):
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        assert os.path.exists(path)

    def test_filename_matches_date(self, tmp_path):
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        assert "kap_2026-05-13.json" in path

    def test_json_schema_valid(self, tmp_path):
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "date" in data
        assert "events" in data
        assert "high_priority_flags" in data
        assert "total_events" in data
        assert "summary" in data

    def test_event_source_type_in_output(self, tmp_path):
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["events"][0]["source_type"] == "kap_official"

    def test_holiday_produces_empty_json(self, tmp_path):
        path = write_kap_json([], date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["total_events"] == 0
        assert data["events"] == []

    def test_high_priority_flags_two_ozel_durum_same_symbol(self, tmp_path):
        ev1 = _make_event(index="1", symbol="THYAO", category="ozel_durum")
        ev2 = _make_event(index="2", symbol="THYAO", category="ozel_durum")
        path = write_kap_json([ev1, ev2], date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "THYAO" in data["high_priority_flags"]

    def test_high_priority_not_set_for_single_ozel_durum(self, tmp_path):
        ev = _make_event(index="1", symbol="AKBNK", category="ozel_durum")
        path = write_kap_json([ev], date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert "AKBNK" not in data["high_priority_flags"]

    def test_overwrite_existing_file(self, tmp_path):
        ev1 = _make_event(index="1")
        path1 = write_kap_json([ev1], date(2026, 5, 13), tmp_path)
        # Write again — should overwrite without error
        ev2 = _make_event(index="2")
        path2 = write_kap_json([ev2], date(2026, 5, 13), tmp_path)
        assert path1 == path2
        data = json.loads(Path(path2).read_text(encoding="utf-8"))
        assert data["total_events"] == 1

    def test_category_summary_counts(self, tmp_path):
        events = [
            _make_event(index="1", category="ozel_durum"),
            _make_event(index="2", category="temettu"),
            _make_event(index="3", category="temettu"),
        ]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["summary"]["ozel_durum"] == 1
        assert data["summary"]["temettu"] == 2

    def test_output_dir_created_if_missing(self, tmp_path):
        nested = tmp_path / "new_subdir" / "deeper"
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), nested)
        assert os.path.exists(path)

    def test_pipeline_run_id_is_uuid(self, tmp_path):
        import uuid
        events = [_make_event()]
        path = write_kap_json(events, date(2026, 5, 13), tmp_path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        run_id = data.get("pipeline_run_id", "")
        uuid.UUID(run_id)  # raises ValueError if not valid UUID


# ---------------------------------------------------------------------------
# upsert_kap_events via database
# ---------------------------------------------------------------------------

class TestUpsertKapEvents:

    def test_inserts_and_deduplicates(self, tmp_path):
        import os
        os.environ["DB_PATH"] = str(tmp_path / "test_kap.db")
        from src.data.database import initialize_db, upsert_kap_events

        initialize_db()
        ev = _make_event(index="dedupe-001")
        n1 = upsert_kap_events([ev])
        n2 = upsert_kap_events([ev])
        assert n1 == 1
        assert n2 == 0

        del os.environ["DB_PATH"]

    def test_empty_list_returns_zero(self, tmp_path):
        import os
        os.environ["DB_PATH"] = str(tmp_path / "test_kap_empty.db")
        from src.data.database import initialize_db, upsert_kap_events

        initialize_db()
        n = upsert_kap_events([])
        assert n == 0

        del os.environ["DB_PATH"]
