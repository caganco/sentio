import re
from datetime import datetime
from typing import Any


def normalize_value(val: str | int | float) -> float | None:
    """Convert Turkish number format '1.234.567,89' → 1234567.89."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val != 0 or str(val) != "0" else float(val)

    val_str = str(val).strip()
    if not val_str or val_str == "-" or val_str == "N/A":
        return None

    is_negative = val_str.startswith("(") and val_str.endswith(")")
    val_str = val_str.strip("()")

    try:
        val_str = val_str.replace(".", "").replace(",", ".")
        result = float(val_str)
        return -result if is_negative else result
    except ValueError:
        return None


def detect_currency_unit(raw: dict) -> tuple[str, int]:
    """Detect currency and unit multiplier from raw disclosure data."""
    currency = raw.get("currency", "TRY").upper()
    unit_str = raw.get("unit", "") or raw.get("unit_multiplier", "")

    multiplier = 1
    if "million" in unit_str.lower() or "mn" in unit_str.lower():
        multiplier = 1000000
    elif "thousand" in unit_str.lower() or "bin" in unit_str.lower():
        multiplier = 1000

    return (currency, multiplier)


def parse_balance_sheet(raw: dict) -> dict[str, dict[str, float | None]]:
    """Extract balance sheet items from raw JSON."""
    result = {}
    tables = raw.get("tables", {})
    balance_data = tables.get("balance_sheet", [])

    if isinstance(balance_data, list):
        for item in balance_data:
            if isinstance(item, dict):
                account_name = item.get("account_name") or item.get("name") or ""
                periods = {}
                for key, val in item.items():
                    if key not in ("account_name", "name", "code"):
                        periods[key] = normalize_value(val)
                if account_name and periods:
                    result[account_name] = periods

    return result


def parse_income_statement(raw: dict) -> dict[str, dict[str, float | None]]:
    """Extract income statement items from raw JSON."""
    result = {}
    tables = raw.get("tables", {})
    income_data = tables.get("income_statement", [])

    if isinstance(income_data, list):
        for item in income_data:
            if isinstance(item, dict):
                account_name = item.get("account_name") or item.get("name") or ""
                periods = {}
                for key, val in item.items():
                    if key not in ("account_name", "name", "code"):
                        periods[key] = normalize_value(val)
                if account_name and periods:
                    result[account_name] = periods

    return result


def parse_cash_flow(raw: dict) -> dict[str, dict[str, float | None]]:
    """Extract cash flow statement from raw JSON."""
    result = {}
    tables = raw.get("tables", {})
    cf_data = tables.get("cash_flow", [])

    if isinstance(cf_data, list):
        for item in cf_data:
            if isinstance(item, dict):
                account_name = item.get("account_name") or item.get("name") or ""
                periods = {}
                for key, val in item.items():
                    if key not in ("account_name", "name", "code"):
                        periods[key] = normalize_value(val)
                if account_name and periods:
                    result[account_name] = periods

    return result


def parse_special_disclosure(raw: dict) -> dict[str, Any]:
    """Extract key fields from special disclosure notification."""
    return {
        "disclosure_id": raw.get("disclosure_id") or raw.get("id") or "",
        "ticker": raw.get("ticker") or raw.get("symbol") or "",
        "company_name": raw.get("company_name") or raw.get("issuer_name") or "",
        "title": raw.get("title") or raw.get("subject") or "",
        "summary": raw.get("summary") or raw.get("description") or None,
        "full_text": raw.get("full_text") or raw.get("content") or None,
        "disclosure_date": raw.get("disclosure_date") or raw.get("date") or None,
        "disclosure_type": raw.get("disclosure_type") or raw.get("type_code") or "",
        "is_material": raw.get("is_material", False),
    }
