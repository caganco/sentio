"""Tests for orchestrator.generate_decisions_file — SPEC 2."""
import os
import pytest
from pathlib import Path

from agents.orchestrator import generate_decisions_file

FIXTURE_SAMPLE = Path("tests/fixtures/final_decision_sample.md")
FIXTURE_EMPTY = Path("tests/fixtures/empty_decision.md")


class TestGenerateDecisionsFile:

    def test_file_is_created(self, tmp_path):
        path = generate_decisions_file(str(FIXTURE_SAMPLE), output_dir=str(tmp_path))
        assert os.path.exists(path)

    def test_filename_contains_decisions(self, tmp_path):
        path = generate_decisions_file(str(FIXTURE_SAMPLE), output_dir=str(tmp_path))
        assert "decisions_" in path
        assert path.endswith(".md")

    def test_date_override_in_filename(self, tmp_path):
        path = generate_decisions_file(
            str(FIXTURE_SAMPLE),
            output_dir=str(tmp_path),
            date_override="2026-01-01",
        )
        assert "decisions_2026-01-01.md" in path

    def test_content_has_trading_decisions_header(self, tmp_path):
        path = generate_decisions_file(str(FIXTURE_SAMPLE), output_dir=str(tmp_path))
        content = open(path, encoding="utf-8").read()
        assert "Trading Decisions" in content

    def test_content_has_pipeline_run_id(self, tmp_path):
        path = generate_decisions_file(str(FIXTURE_SAMPLE), output_dir=str(tmp_path))
        content = open(path, encoding="utf-8").read()
        assert "pipeline_run_id" in content

    def test_empty_input_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="Empty final_decision"):
            generate_decisions_file(str(FIXTURE_EMPTY), output_dir=str(tmp_path))

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_decisions_file("nonexistent_file.md", output_dir=str(tmp_path))

    def test_creates_output_directory_if_missing(self, tmp_path):
        new_dir = tmp_path / "new_subdir"
        assert not new_dir.exists()
        generate_decisions_file(str(FIXTURE_SAMPLE), output_dir=str(new_dir))
        assert new_dir.is_dir()

    def test_bad_date_override_raises(self, tmp_path):
        with pytest.raises(ValueError, match="date_override must be YYYY-MM-DD"):
            generate_decisions_file(
                str(FIXTURE_SAMPLE),
                output_dir=str(tmp_path),
                date_override="13-05-2026",
            )

    def test_overwrite_same_day(self, tmp_path):
        path1 = generate_decisions_file(
            str(FIXTURE_SAMPLE), output_dir=str(tmp_path), date_override="2026-06-01"
        )
        path2 = generate_decisions_file(
            str(FIXTURE_SAMPLE), output_dir=str(tmp_path), date_override="2026-06-01"
        )
        assert path1 == path2
        assert os.path.exists(path2)
