import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logger import setup_logger
from src.scrapers.kap_models import (
    FinancialDisclosure,
    SpecialDisclosure,
    FinancialTables,
)
from src.scrapers.kap_parser import (
    parse_balance_sheet,
    parse_income_statement,
    parse_cash_flow,
    parse_special_disclosure,
    detect_currency_unit,
)

logger = setup_logger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


class KAPScraper:
    BASE_URL = "https://www.kap.org.tr"
    API_URL = "https://www.kap.org.tr/tr/api"

    def __init__(self, delay: float = 1.5, timeout: int = 30, max_retries: int = 3):
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time = 0

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        self._company_cache = None

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self) -> None:
        """Enforce rate limit between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def _request(self, url: str, params: dict | None = None) -> dict:
        """Rate-limited GET request with retry logic."""
        self._rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as je:
                logger.error(f"Invalid JSON response from {url}")
                raise requests.exceptions.RequestException(f"Invalid JSON: {je}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} — {e}")
            raise

    def _save_raw(self, data: dict, category: str, filename: str) -> str:
        """Save raw data to data/raw/{category}/{filename}.json"""
        cat_dir = RAW_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / f"{filename}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug(f"Saved raw data: {path}")
        return str(path)

    def get_company_list(self) -> list[dict]:
        """Fetch all BIST companies."""
        if self._company_cache:
            return self._company_cache

        logger.info("Fetching BIST company list...")
        url = f"{self.API_URL}/memberDisclosureQuery"
        params = {
            "exchange": "BIST",
            "pageSize": 1000,
            "pageIndex": 0,
        }

        try:
            data = self._request(url, params)
            companies = data.get("companies", []) or data.get("result", [])
            self._company_cache = [
                {
                    "ticker": c.get("ticker") or c.get("symbol"),
                    "name": c.get("name") or c.get("company_name"),
                    "kap_id": c.get("kap_id") or c.get("member_id"),
                }
                for c in companies
                if c.get("ticker") or c.get("symbol")
            ]
            logger.info(f"Loaded {len(self._company_cache)} companies")
            return self._company_cache
        except Exception as e:
            logger.warning(f"Failed to load company list from KAP API: {e}")
            logger.info("Using fallback company list")
            return self._get_fallback_companies()

    def _get_fallback_companies(self) -> list[dict]:
        """Fallback company list for testing when API is unavailable."""
        fallback = [
            {"ticker": "THYAO", "name": "TÜRK HAVA YOLLARI A.O.", "kap_id": "thyao"},
            {"ticker": "AKBNK", "name": "AKBANK T.A.Ş.", "kap_id": "akbnk"},
            {"ticker": "GARAN", "name": "GARANTİ BANKASI A.Ş.", "kap_id": "garan"},
            {"ticker": "KCHOL", "name": "KOÇ HOLDİNG A.Ş.", "kap_id": "kchol"},
            {"ticker": "ENERY", "name": "ENERJISA AYGAZ A.Ş.", "kap_id": "enery"},
            {"ticker": "TTKOM", "name": "TÜRK TELEKOM A.Ş.", "kap_id": "ttkom"},
            {"ticker": "ASELS", "name": "ASELSAN ELEKTRONİK SANAYİ VE TİC. A.Ş.", "kap_id": "asels"},
            {"ticker": "SISE", "name": "ŞIŞECAM (İŞ GÖZÜ) A.Ş.", "kap_id": "sise"},
        ]
        self._company_cache = fallback
        return fallback

    def _get_company_kap_id(self, ticker: str) -> str | None:
        """Resolve ticker → KAP member ID."""
        companies = self.get_company_list()
        for c in companies:
            if c["ticker"] == ticker.upper():
                return c.get("kap_id")
        return None

    def get_financial_disclosures(
        self,
        ticker: str,
        year: int | None = None,
        period: str | None = None,
        limit: int = 10,
    ) -> list[FinancialDisclosure]:
        """Fetch financial disclosure announcements for a ticker."""
        logger.info(f"Fetching financial disclosures for {ticker}...")
        kap_id = self._get_company_kap_id(ticker)
        if not kap_id:
            logger.warning(f"KAP ID not found for {ticker}")
            return []

        url = f"{self.API_URL}/memberDisclosureQuery"
        params = {
            "memberId": kap_id,
            "disclosureType": "FINANCIALS",
            "pageSize": limit,
            "pageIndex": 0,
        }
        if year:
            params["year"] = year
        if period:
            params["period"] = period

        try:
            data = self._request(url, params)
            items = data.get("disclosures", [])
            results = []

            for item in items:
                try:
                    disc = FinancialDisclosure(
                        disclosure_id=item.get("disclosure_id") or item.get("id"),
                        ticker=ticker.upper(),
                        company_name=item.get("company_name") or "",
                        period=item.get("period") or item.get("reporting_period") or "",
                        period_type=item.get("period_type") or "annual",
                        disclosure_date=datetime.fromisoformat(
                            item.get("disclosure_date", datetime.now().isoformat())
                        ),
                        financial_type=item.get("financial_type") or "consolidated",
                        url=f"{self.BASE_URL}/tr/Bildirim/{item.get('disclosure_id')}",
                    )
                    results.append(disc)
                except Exception as e:
                    logger.debug(f"Failed to parse disclosure: {e}")
                    continue

            logger.info(f"Found {len(results)} financial disclosures for {ticker}")
            return results
        except Exception as e:
            logger.error(f"Failed to fetch financial disclosures: {e}")
            return []

    def get_special_disclosures(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
    ) -> list[SpecialDisclosure]:
        """Fetch special situation announcements."""
        logger.info(f"Fetching special disclosures for {ticker}...")
        kap_id = self._get_company_kap_id(ticker)
        if not kap_id:
            logger.warning(f"KAP ID not found for {ticker}")
            return []

        url = f"{self.API_URL}/memberDisclosureQuery"
        params = {
            "memberId": kap_id,
            "disclosureType": "SPECIAL",
            "pageSize": limit,
            "pageIndex": 0,
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        try:
            data = self._request(url, params)
            items = data.get("disclosures", [])
            results = []

            for item in items:
                try:
                    parsed = parse_special_disclosure(item)
                    disc = SpecialDisclosure(
                        disclosure_id=parsed["disclosure_id"],
                        ticker=ticker.upper(),
                        company_name=parsed["company_name"],
                        title=parsed["title"],
                        summary=parsed["summary"],
                        full_text=parsed["full_text"],
                        disclosure_date=datetime.fromisoformat(parsed["disclosure_date"])
                        if isinstance(parsed["disclosure_date"], str)
                        else parsed["disclosure_date"] or datetime.now(),
                        disclosure_type=parsed["disclosure_type"],
                        url=f"{self.BASE_URL}/tr/Bildirim/{parsed['disclosure_id']}",
                        is_material=parsed["is_material"],
                    )
                    results.append(disc)
                except Exception as e:
                    logger.debug(f"Failed to parse special disclosure: {e}")
                    continue

            logger.info(f"Found {len(results)} special disclosures for {ticker}")
            return results
        except Exception as e:
            logger.error(f"Failed to fetch special disclosures: {e}")
            return []

    def get_financial_tables(self, disclosure_id: str) -> FinancialTables | None:
        """Fetch detailed financial tables for a specific disclosure."""
        logger.info(f"Fetching financial tables for disclosure {disclosure_id}...")
        url = f"{self.API_URL}/disclosureDetail"
        params = {"disclosureId": disclosure_id}

        try:
            raw = self._request(url, params)
            self._save_raw(raw, "financials", f"disclosure_{disclosure_id}")

            ticker = raw.get("ticker", "UNKNOWN")
            period = raw.get("period", "UNKNOWN")
            currency, multiplier = detect_currency_unit(raw)

            tables = FinancialTables(
                disclosure_id=disclosure_id,
                ticker=ticker,
                period=period,
                currency=currency,
                unit_multiplier=multiplier,
                balance_sheet=parse_balance_sheet(raw),
                income_statement=parse_income_statement(raw),
                cash_flow=parse_cash_flow(raw),
                scraped_at=datetime.now(),
            )

            logger.info(f"Extracted tables for {ticker} period {period}")
            return tables
        except Exception as e:
            logger.error(f"Failed to fetch financial tables: {e}")
            return None
