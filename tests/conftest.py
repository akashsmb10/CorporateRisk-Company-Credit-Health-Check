"""Small, clearly labelled SYNTHETIC fixtures for unit tests (not real companies)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def make_row(**overrides) -> dict:
    """One internally consistent synthetic company-year (INR crore).

    Balance sheet: assets 1000 = liabilities 600 + equity 400.
    Debt 300 (100 short-term + 200 long-term); cash 50; EBITDA 150 - D&A 30 = EBIT 120.
    """
    row = {
        "company": "Test Co (Synthetic)", "sector": "Industrial Manufacturing", "fiscal_year": 2025,
        "fiscal_year_end": "2025-03-31", "statement_basis": "consolidated", "currency": "INR", "units": "crore",
        "data_type": "SYNTHETIC",
        "current_assets": 400.0, "current_liabilities": 200.0, "cash_and_equivalents": 50.0, "inventory": 100.0,
        "total_assets": 1000.0, "total_liabilities": 600.0, "total_equity": 400.0,
        "short_term_borrowings": 100.0, "long_term_borrowings": 200.0, "retained_earnings": 250.0,
        "revenue": 1000.0, "ebitda": 150.0, "depreciation_amortisation": 30.0, "ebit": 120.0,
        "interest_expense": 24.0, "profit_before_tax": 96.0, "net_profit": 72.0,
        "operating_cash_flow": 110.0, "capital_expenditure": 40.0, "market_capitalisation": 900.0,
    }
    row.update(overrides)
    return row


@pytest.fixture
def one_year() -> pd.DataFrame:
    return pd.DataFrame([make_row()])


@pytest.fixture
def two_years() -> pd.DataFrame:
    """FY2024 and FY2025 so that average balances can be tested."""
    y1 = make_row(fiscal_year=2024, fiscal_year_end="2024-03-31", total_assets=800.0,
                  total_liabilities=500.0, total_equity=300.0)
    return pd.DataFrame([y1, make_row()])
