from datetime import datetime

from pydantic import BaseModel


class FinancialDisclosure(BaseModel):
    disclosure_id: str
    ticker: str
    company_name: str
    period: str
    period_type: str
    disclosure_date: datetime
    financial_type: str
    url: str


class SpecialDisclosure(BaseModel):
    disclosure_id: str
    ticker: str
    company_name: str
    title: str
    summary: str | None
    full_text: str | None
    disclosure_date: datetime
    disclosure_type: str
    url: str
    is_material: bool


class FinancialTables(BaseModel):
    disclosure_id: str
    ticker: str
    period: str
    currency: str
    unit_multiplier: int
    balance_sheet: dict[str, dict[str, float | None]]
    income_statement: dict[str, dict[str, float | None]]
    cash_flow: dict[str, dict[str, float | None]]
    scraped_at: datetime
