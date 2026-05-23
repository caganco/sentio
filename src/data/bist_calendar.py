"""BIST holiday calendar. Prevents scraper on market closed days."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BISTCalendar:
    """
    BIST holiday calendar. Blocks KAP scraping on market-closed days.

    Holidays include fixed (New Year, national days) and lunar (Ramadan, Eids).
    Update annually via update_holidays() or config.
    """

    # 2026 BIST holidays: fixed + lunar estimates
    HOLIDAYS_2026 = {
        "2026-01-01",  # New Year's Day
        "2026-04-23",  # National Sovereignty Day
        "2026-05-01",  # Labour Day
        "2026-07-15",  # Democracy Day (2-day holiday starts)
        "2026-07-16",  # Democracy Day (cont.)
        "2026-08-30",  # Victory Day
        "2026-10-29",  # Republic Day
        # Lunar holidays (Ramadan/Eids) — dates approximate, marked ±1 day
        "2026-03-30",  # Ramadan Eve
        "2026-03-31",  # Ramadan starts (approx)
        "2026-04-01",  # Ramadan (cont)
        "2026-05-10",  # Eid al-Fitr Eve (approx)
        "2026-05-11",  # Eid al-Fitr (3-day)
        "2026-05-12",  # Eid al-Fitr (cont.)
        "2026-07-29",  # Eid al-Adha Eve (approx)
        "2026-07-30",  # Eid al-Adha (4-day)
        "2026-07-31",  # Eid al-Adha (cont.)
        "2026-08-01",  # Eid al-Adha (cont.)
    }

    def __init__(self):
        """Initialize calendar with 2026 holidays."""
        self.holidays = set(self.HOLIDAYS_2026)
        self.last_update_year = 2026

    @property
    def is_today_holiday(self) -> bool:
        """Check if today is BIST holiday."""
        today = datetime.now().date().isoformat()
        return today in self.holidays

    def is_holiday(self, date_str: str) -> bool:
        """
        Check if date_str (YYYY-MM-DD) is BIST holiday.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            bool: True if holiday, False otherwise
        """
        return date_str in self.holidays

    def update_holidays(self, year: int, holidays: list[str]) -> None:
        """
        Update holiday list for a new year.

        Args:
            year: Year being updated
            holidays: List of dates in YYYY-MM-DD format
        """
        if year <= self.last_update_year:
            logger.warning(
                f"Holiday update for year {year}, but last update was {self.last_update_year}. "
                f"Proceeding anyway (assuming future calendar correction)."
            )

        self.holidays = set(holidays)
        self.last_update_year = year
        logger.info(f"BIST holiday calendar updated for {year} ({len(holidays)} days)")
