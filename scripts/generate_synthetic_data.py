"""Generate the SYNTHETIC demonstration dataset (fictional companies).

    python scripts/generate_synthetic_data.py

Why synthetic? The real-data path (data/raw/company_financials.csv, see
docs/data_sources.md) needs figures copied from annual reports. The demo set lets
the software, tests and dashboard run before that is done.

The statements are built from simple business drivers so that they are
internally consistent:
    EBITDA = revenue x EBITDA margin;  EBIT = EBITDA - D&A
    interest = closing debt x interest rate (simplification)
    PBT = EBIT - interest + other income;  tax = 25% of positive PBT
    retained earnings and equity roll forward with net profit - dividends
    total liabilities = borrowings + payables + other non-current liabilities
    total assets = total liabilities + total equity (identity holds exactly)
    OCF = EBITDA - tax - increase in working capital

These are FICTIONAL companies. Every company name ends in "(Synthetic)" and
every row has data_type = SYNTHETIC.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corporaterisk import config as C  # noqa: E402

YEARS = [2021, 2022, 2023, 2024, 2025]  # fiscal year ending 31 March of that year
TAX_RATE = 0.25

COMPANIES = {
    "Alpha Manufacturing (Synthetic)": {
        "sector": "Industrial Manufacturing", "share_capital": 100, "opening_retained": 700,
        "revenue": [1800, 2050, 2300, 2480, 2700], "margin": [0.16, 0.165, 0.17, 0.168, 0.172],
        "da": [70, 75, 82, 88, 95], "st_debt": [120, 110, 100, 95, 90], "lt_debt": [380, 360, 340, 320, 300],
        "rate": 0.085, "other_income": 15, "cash": [140, 170, 210, 240, 290],
        "inventory": [300, 330, 360, 380, 410], "receivables": [320, 350, 380, 400, 430],
        "payables": [260, 290, 320, 340, 370], "other_ncl": 60, "capex": [120, 140, 150, 160, 170],
        "wc_increase": [30, 25, 30, 20, 25], "dividends": [40, 50, 60, 70, 80],
        "market_cap": [3200, 3800, 4300, 4600, 5200],
    },
    "Kestrel Infrastructure (Synthetic)": {
        "sector": "Infrastructure", "share_capital": 150, "opening_retained": 600,
        "revenue": [1500, 1650, 1700, 1620, 1450], "margin": [0.22, 0.20, 0.17, 0.14, 0.10],
        "da": [90, 100, 110, 118, 124], "st_debt": [200, 260, 330, 420, 520],
        "lt_debt": [900, 1050, 1200, 1320, 1400], "rate": 0.10, "other_income": 10,
        "cash": [120, 100, 80, 60, 45], "inventory": [150, 170, 190, 210, 220],
        "receivables": [450, 520, 580, 620, 640], "payables": [300, 340, 380, 420, 460], "other_ncl": 80,
        "capex": [220, 260, 240, 180, 120], "wc_increase": [60, 70, 60, 40, 20], "dividends": [20, 20, 10, 0, 0],
        "market_cap": [None] * 5,
    },
    "Lotus Consumer Goods (Synthetic)": {
        "sector": "Consumer Goods", "share_capital": 50, "opening_retained": 900,
        "revenue": [2600, 2900, 3150, 3400, 3650], "margin": [0.19, 0.20, 0.205, 0.21, 0.215],
        "da": [45, 50, 55, 60, 65], "st_debt": [30, 20, 10, 0, 0], "lt_debt": [60, 40, 20, 0, 0],
        "rate": 0.08, "other_income": 30, "cash": [400, 480, 560, 650, 760],
        "inventory": [220, 240, 260, 280, 300], "receivables": [120, 130, 140, 150, 160],
        "payables": [520, 570, 620, 670, 720], "other_ncl": 50, "capex": [90, 100, 110, 115, 120],
        "wc_increase": [5, 5, 5, 5, 5], "dividends": [250, 300, 340, 380, 420], "market_cap": [None] * 5,
    },
    "Orbit Aviation Services (Synthetic)": {
        "sector": "Aviation Services", "share_capital": 400, "opening_retained": -300,
        "revenue": [600, 1100, 1500, 1450, 1300], "margin": [-0.15, 0.05, 0.10, 0.04, -0.02],
        "da": [110, 115, 118, 120, 122], "st_debt": [400, 450, 500, 560, 620],
        "lt_debt": [900, 950, 1000, 1050, 1100], "rate": 0.11, "other_income": 5,
        "cash": [90, 70, 60, 40, 30], "inventory": [30, 35, 40, 40, 38], "receivables": [80, 110, 140, 130, 120],
        "payables": [420, 450, 480, 520, 560], "other_ncl": 150, "capex": [60, 80, 90, 60, 40],
        "wc_increase": [-20, 10, 15, -10, -15], "dividends": [0] * 5, "market_cap": [None] * 5,
    },
}


def build() -> pd.DataFrame:
    rows = []
    for name, p in COMPANIES.items():
        retained = p["opening_retained"]
        for i, fy in enumerate(YEARS):
            rev = p["revenue"][i]
            ebitda = rev * p["margin"][i]
            ebit = ebitda - p["da"][i]
            debt = p["st_debt"][i] + p["lt_debt"][i]
            interest = debt * p["rate"]
            pbt = ebit - interest + p["other_income"]
            tax = TAX_RATE * pbt if pbt > 0 else 0.0
            net = pbt - tax
            retained = retained + net - p["dividends"][i]
            equity = p["share_capital"] + retained
            current_liab = p["st_debt"][i] + p["payables"][i]
            total_liab = debt + p["payables"][i] + p["other_ncl"]
            total_assets = total_liab + equity
            current_assets = p["cash"][i] + p["inventory"][i] + p["receivables"][i]
            if total_assets <= current_assets:
                raise ValueError(f"{name} FY{fy}: non-current assets would be non-positive; adjust drivers.")
            ocf = ebitda - tax - p["wc_increase"][i]
            rows.append({
                "company": name, "sector": p["sector"], "fiscal_year": fy, "fiscal_year_end": f"{fy}-03-31",
                "statement_basis": "consolidated", "currency": "INR", "units": "crore", "data_type": "SYNTHETIC",
                "current_assets": current_assets, "current_liabilities": current_liab,
                "cash_and_equivalents": p["cash"][i], "inventory": p["inventory"][i],
                "total_assets": total_assets, "total_liabilities": total_liab, "total_equity": equity,
                "short_term_borrowings": p["st_debt"][i], "long_term_borrowings": p["lt_debt"][i],
                "retained_earnings": retained, "revenue": rev, "ebitda": ebitda,
                "depreciation_amortisation": p["da"][i], "ebit": ebit, "interest_expense": interest,
                "profit_before_tax": pbt, "net_profit": net, "operating_cash_flow": ocf,
                "capital_expenditure": p["capex"][i], "market_capitalisation": p["market_cap"][i],
            })
    df = pd.DataFrame(rows)
    money = [c for c in C.ALL_ITEMS if c in df.columns]
    df[money] = df[money].astype(float).round(2)
    return df


def main() -> int:
    C.ensure_dirs()
    df = build()
    header = ("# SYNTHETIC DEMONSTRATION DATA - fictional companies generated by "
              "scripts/generate_synthetic_data.py. Not real company financials.\n")
    with open(C.SYNTHETIC_DATA_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        df.to_csv(f, index=False)
    print(f"wrote {C.SYNTHETIC_DATA_FILE.relative_to(ROOT)}  ({len(df)} rows, {df['company'].nunique()} companies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
