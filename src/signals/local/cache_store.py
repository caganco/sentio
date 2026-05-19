"""SQLite cache backend for local macro signals."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


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

            CREATE TABLE IF NOT EXISTS dxy_data (
                id INTEGER PRIMARY KEY,
                data_date TEXT NOT NULL UNIQUE,
                close REAL NOT NULL,
                weekly_change_pct REAL NOT NULL,
                fetched_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tcmb_date ON tcmb_decisions(decision_date);
            CREATE INDEX IF NOT EXISTS idx_cds_date ON cds_data(data_date);
            CREATE INDEX IF NOT EXISTS idx_foreign_date ON bist_foreign_weekly(week_ending_date);
            CREATE INDEX IF NOT EXISTS idx_dxy_date ON dxy_data(data_date);
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
        rate_before: float | None = None,
        rate_after: float | None = None,
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

    def get_latest_tcmb(self) -> dict | None:
        """Get latest TCMB decision."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tcmb_decisions ORDER BY decision_date DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_tcmb_history(self, n: int = 15) -> list[dict]:
        """Get last n TCMB decisions ordered most-recent-first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tcmb_decisions ORDER BY decision_date DESC LIMIT ?", (n,)
            ).fetchall()
            return [dict(row) for row in rows]

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

    def get_latest_cds(self) -> dict | None:
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
        pct_change_weekly: float | None = None,
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

    def get_latest_bist_foreign(self) -> dict | None:
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

    def store_dxy(
        self,
        data_date: str,
        close: float,
        weekly_change_pct: float,
    ):
        """Store DXY snapshot (idempotent, one row per date)."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dxy_data
                (data_date, close, weekly_change_pct, fetched_at)
                VALUES (?, ?, ?, ?)
                """,
                (data_date, close, weekly_change_pct, datetime.utcnow().isoformat()),
            )

    def get_latest_dxy(self) -> dict | None:
        """Get latest DXY snapshot."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM dxy_data ORDER BY data_date DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def load_from_yaml_fallback(self, yaml_path: str = "src/signals/local/data/local_macro_fallback.yaml") -> None:
        """Load fallback data from YAML into cache (idempotent)."""
        from pathlib import Path

        import yaml

        fallback_file = Path(yaml_path)
        if not fallback_file.exists():
            return

        with open(fallback_file, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        # Load TCMB decisions
        if "tcmb" in data and "decisions" in data["tcmb"]:
            for decision in data["tcmb"]["decisions"]:
                # Check if already exists before inserting
                with self._conn() as conn:
                    existing = conn.execute(
                        "SELECT 1 FROM tcmb_decisions WHERE decision_date = ?",
                        (decision["decision_date"],),
                    ).fetchone()
                if not existing:
                    self.store_tcmb(
                        decision_date=decision["decision_date"],
                        decision_type=decision["decision_type"],
                        rate_before=decision.get("rate_before"),
                        rate_after=decision.get("rate_after"),
                        source=decision.get("source", "yaml_fallback"),
                    )

        # Load CDS data
        if "cds" in data:
            cds_data = data["cds"]
            with self._conn() as conn:
                existing = conn.execute("SELECT 1 FROM cds_data").fetchone()
            if not existing:
                self.store_cds(
                    data_date=cds_data.get("last_fetch", datetime.utcnow().isoformat())[:10],
                    cds_bps=cds_data["last_value"],
                    source=cds_data.get("source", "yaml_fallback"),
                )

        # Load BIST foreign ownership
        if "bist_foreign_weekly" in data:
            for record in data["bist_foreign_weekly"]:
                with self._conn() as conn:
                    existing = conn.execute(
                        "SELECT 1 FROM bist_foreign_weekly WHERE week_ending_date = ?",
                        (record["week_ending_date"],),
                    ).fetchone()
                if not existing:
                    self.store_bist_foreign(
                        week_ending_date=record["week_ending_date"],
                        foreign_ownership_pct=record["foreign_ownership_pct"],
                        pct_change_weekly=record["pct_change_weekly"],
                        source=record.get("source", "yaml_fallback"),
                    )
