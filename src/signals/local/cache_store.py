"""SQLite cache backend for local macro signals."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


class LocalMacroCache:
    """SQLite backend for local macro signals (TCMB, CDS, BIST Foreign)."""

    def __init__(self, db_path: str = "data/local_macro.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Create tables if missing."""
        with self._conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS tcmb_decisions (
                id INTEGER PRIMARY KEY,
                decision_date TEXT NOT NULL UNIQUE,
                decision_type TEXT NOT NULL,
                rate_before REAL,
                rate_after REAL,
                source TEXT DEFAULT 'web_scrape',
                confidence REAL DEFAULT 1.0,
                fetched_at TEXT NOT NULL,
                UNIQUE(decision_date)
            );

            CREATE TABLE IF NOT EXISTS cds_data (
                id INTEGER PRIMARY KEY,
                data_date TEXT NOT NULL,
                cds_bps REAL NOT NULL,
                source TEXT DEFAULT 'world_bonds',
                confidence REAL DEFAULT 1.0,
                fetched_at TEXT NOT NULL,
                UNIQUE(data_date)
            );

            CREATE TABLE IF NOT EXISTS bist_foreign_weekly (
                id INTEGER PRIMARY KEY,
                week_ending_date TEXT NOT NULL UNIQUE,
                foreign_ownership_pct REAL NOT NULL,
                pct_change_weekly REAL,
                source TEXT DEFAULT 'evds_api',
                confidence REAL DEFAULT 0.9,
                fetched_at TEXT NOT NULL,
                UNIQUE(week_ending_date)
            );

            CREATE INDEX IF NOT EXISTS idx_tcmb_date ON tcmb_decisions(decision_date);
            CREATE INDEX IF NOT EXISTS idx_cds_date ON cds_data(data_date);
            CREATE INDEX IF NOT EXISTS idx_foreign_date ON bist_foreign_weekly(week_ending_date);
            """)

    @contextmanager
    def _conn(self):
        """Context manager for SQLite connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def store_tcmb(
        self,
        decision_date: str,
        decision_type: str,
        rate_before: Optional[float] = None,
        rate_after: Optional[float] = None,
        source: str = "web_scrape",
        confidence: float = 1.0,
    ):
        """Store TCMB decision (idempotent)."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tcmb_decisions
                (decision_date, decision_type, rate_before, rate_after, source, confidence, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_date,
                    decision_type,
                    rate_before,
                    rate_after,
                    source,
                    confidence,
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_latest_tcmb(self) -> Optional[dict]:
        """Get latest TCMB decision."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tcmb_decisions ORDER BY decision_date DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def store_cds(
        self,
        data_date: str,
        cds_bps: float,
        source: str = "world_bonds",
        confidence: float = 1.0,
    ):
        """Store CDS data (idempotent)."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cds_data
                (data_date, cds_bps, source, confidence, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (data_date, cds_bps, source, confidence, datetime.utcnow().isoformat()),
            )

    def get_latest_cds(self) -> Optional[dict]:
        """Get latest CDS data."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM cds_data ORDER BY data_date DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def store_bist_foreign(
        self,
        week_ending_date: str,
        foreign_ownership_pct: float,
        pct_change_weekly: Optional[float] = None,
        source: str = "evds_api",
        confidence: float = 0.9,
    ):
        """Store BIST foreign ownership weekly (idempotent)."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO bist_foreign_weekly
                (week_ending_date, foreign_ownership_pct, pct_change_weekly, source, confidence, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    week_ending_date,
                    foreign_ownership_pct,
                    pct_change_weekly,
                    source,
                    confidence,
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_latest_bist_foreign(self) -> Optional[dict]:
        """Get latest BIST foreign ownership weekly."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM bist_foreign_weekly ORDER BY week_ending_date DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_bist_foreign_last_2(self) -> list[dict]:
        """Get last 2 weeks for trend calculation."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM bist_foreign_weekly ORDER BY week_ending_date DESC LIMIT 2"
            ).fetchall()
            return [dict(row) for row in rows]
