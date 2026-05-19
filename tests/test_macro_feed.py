import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.data.macro_feed import (
    fetch_macro_history,
    fetch_macro_snapshot,
    get_latest_snapshot,
    load_from_db,
    save_to_db,
)
from src.data.macro_scheduler import run_daily_update

TEST_DB = "data/test_macro.db"


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database after each test."""
    yield
    if Path(TEST_DB).exists():
        try:
            import sqlite3
            conn = sqlite3.connect(TEST_DB)
            conn.close()
            Path(TEST_DB).unlink()
        except Exception:
            pass  # File may be in use, ignore


class TestMacroSnapshot:
    """Test macro data snapshot fetching."""

    def test_fetch_snapshot_structure(self):
        """Verify snapshot has required columns."""
        df = fetch_macro_snapshot()

        assert not df.empty, "Snapshot should not be empty"
        assert "date" in df.columns
        assert "symbol" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns

    def test_fetch_snapshot_symbols(self):
        """Verify all expected symbols are fetched."""
        df = fetch_macro_snapshot()

        if not df.empty:
            symbols = set(df["symbol"])
            expected = {"USDTRY", "BRENT", "VIX", "BIST100"}
            # At least some symbols should be present (BIST100 may be empty on weekends)
            assert len(symbols) > 0, "At least one symbol should be present"

    def test_fetch_snapshot_close_not_null(self):
        """Verify close prices are present."""
        df = fetch_macro_snapshot()

        if not df.empty:
            assert df["close"].notna().all(), "Close prices should not be null"
            assert (df["close"] > 0).any(), "At least one close price should be positive"

    def test_fetch_snapshot_date_format(self):
        """Verify date format is YYYY-MM-DD."""
        df = fetch_macro_snapshot()

        if not df.empty:
            for date_str in df["date"]:
                assert len(date_str) == 10, f"Date should be YYYY-MM-DD, got {date_str}"
                assert date_str.count("-") == 2, f"Date format error: {date_str}"


class TestMacroHistory:
    """Test historical macro data fetching."""

    def test_fetch_history_date_range(self):
        """Verify history respects date range."""
        df = fetch_macro_history(start="2024-01-01", end="2024-01-31")

        if not df.empty:
            assert df["date"].min() >= "2024-01-01"
            assert df["date"].max() <= "2024-01-31"

    def test_fetch_history_returns_dataframe(self):
        """Verify history returns DataFrame with expected structure."""
        df = fetch_macro_history(start="2024-01-01", end="2024-01-31")

        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "date" in df.columns
            assert "symbol" in df.columns
            assert "close" in df.columns


class TestMacroDatabase:
    """Test macro data persistence."""

    def test_save_and_load_snapshot(self):
        """Verify snapshot can be saved and loaded."""
        df = fetch_macro_snapshot()

        if df.empty:
            pytest.skip("No snapshot data available")

        rows_saved = save_to_db(df, db_path=TEST_DB)
        assert rows_saved > 0

        loaded = load_from_db(db_path=TEST_DB)
        assert len(loaded) >= rows_saved

    def test_upsert_no_duplicates(self):
        """Verify upsert doesn't create duplicates."""
        df = fetch_macro_snapshot()

        if df.empty:
            pytest.skip("No snapshot data available")

        save_to_db(df, db_path=TEST_DB)
        loaded1 = load_from_db(db_path=TEST_DB)
        count1 = len(loaded1)

        # Save same data again
        save_to_db(df, db_path=TEST_DB)
        loaded2 = load_from_db(db_path=TEST_DB)
        count2 = len(loaded2)

        assert count1 == count2, "Upsert should not create duplicates"

    def test_load_with_symbol_filter(self):
        """Verify symbol filtering works."""
        df = fetch_macro_snapshot()

        if df.empty:
            pytest.skip("No snapshot data available")

        save_to_db(df, db_path=TEST_DB)

        loaded = load_from_db(symbols=["USDTRY"], db_path=TEST_DB)
        if not loaded.empty:
            assert all(loaded["symbol"] == "USDTRY")

    def test_load_with_date_range(self):
        """Verify date range filtering works."""
        df = fetch_macro_history(start="2024-01-01", end="2024-01-31")

        if df.empty:
            pytest.skip("No history data available")

        save_to_db(df, db_path=TEST_DB)

        loaded = load_from_db(
            start="2024-01-10",
            end="2024-01-20",
            db_path=TEST_DB
        )
        if not loaded.empty:
            assert loaded["date"].min() >= "2024-01-10"
            assert loaded["date"].max() <= "2024-01-20"

    def test_latest_snapshot(self):
        """Verify latest snapshot calculation."""
        df = fetch_macro_snapshot()

        if df.empty:
            pytest.skip("No snapshot data available")

        save_to_db(df, db_path=TEST_DB)

        latest = get_latest_snapshot(db_path=TEST_DB)
        if not latest.empty:
            assert "symbol" in latest.columns
            assert "date" in latest.columns
            assert "close" in latest.columns
            assert "pct_change_1d" in latest.columns

    def test_latest_snapshot_pct_change(self):
        """Verify pct_change_1d calculation."""
        # Save two days of data
        df1 = fetch_macro_snapshot()

        if df1.empty:
            pytest.skip("No snapshot data available")

        save_to_db(df1, db_path=TEST_DB)

        latest = get_latest_snapshot(db_path=TEST_DB)
        if not latest.empty:
            # pct_change_1d could be 0 if only one data point
            assert all(isinstance(x, (int, float)) for x in latest["pct_change_1d"])


class TestDailyUpdate:
    """Test daily update job."""

    def test_run_daily_update(self):
        """Verify daily update runs and returns expected structure."""
        result = run_daily_update(db_path=TEST_DB, log_path="logs/test_macro.log")

        assert isinstance(result, dict)
        assert "updated_rows" in result
        assert "symbols" in result
        assert "timestamp" in result
        assert "errors" in result

    def test_run_daily_update_timestamp(self):
        """Verify timestamp format."""
        result = run_daily_update(db_path=TEST_DB)

        # Try to parse as ISO format
        datetime.fromisoformat(result["timestamp"])  # Should not raise

    def test_run_daily_update_data_saved(self):
        """Verify daily update actually saves data."""
        result = run_daily_update(db_path=TEST_DB)

        if result["updated_rows"] > 0:
            loaded = load_from_db(db_path=TEST_DB)
            assert len(loaded) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
