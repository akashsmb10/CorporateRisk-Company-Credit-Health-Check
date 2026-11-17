"""Validate financial statements before any ratio is computed.

Checks fall into two severities:
    ERROR   - the data cannot be analysed reliably (e.g. mixed units for one company).
    WARNING - the data can be analysed but something needs the analyst's attention
              (e.g. an accounting identity does not hold within tolerance, a missing item).
Nothing is corrected silently: every finding is returned in a table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def _issue(rows: list, severity: str, company: str, year, check: str, detail: str) -> None:
    rows.append({"severity": severity, "company": company, "fiscal_year": year,
                 "check": check, "detail": detail})


def _close(a: float, b: float, tol: float = C.IDENTITY_TOLERANCE) -> bool:
    scale = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / scale <= tol


def validate_financials(df: pd.DataFrame) -> pd.DataFrame:
    """Return a table of validation findings (empty table = no issues)."""
    rows: list[dict] = []

    # --- Company-level consistency -------------------------------------------
    for company, g in df.groupby("company"):
        for col in ("currency", "units", "statement_basis", "sector", "data_type"):
            if g[col].nunique() > 1:
                _issue(rows, "ERROR", company, None, f"consistent_{col}",
                       f"{col} changes across years ({sorted(g[col].astype(str).unique())}); "
                       "do not mix standalone/consolidated figures or different units.")
        sector = str(g["sector"].iloc[0]).lower()
        if any(k in sector for k in C.EXCLUDED_SECTOR_KEYWORDS):
            _issue(rows, "ERROR", company, None, "non_financial_company",
                   f"Sector '{g['sector'].iloc[0]}' looks financial; ratios here are designed for "
                   "non-financial companies.")
        yrs = sorted(g["fiscal_year"].tolist())
        if len(yrs) != len(set(yrs)):
            _issue(rows, "ERROR", company, None, "duplicate_year", "Duplicate fiscal years.")
        if yrs and yrs != list(range(yrs[0], yrs[0] + len(yrs))):
            _issue(rows, "WARNING", company, None, "consecutive_years",
                   f"Fiscal years are not consecutive: {yrs}. Growth rates and averages need care.")

    # --- Row-level checks ---------------------------------------------------
    for _, r in df.iterrows():
        c, y = r["company"], int(r["fiscal_year"])
        for item in C.REQUIRED_ITEMS:
            if pd.isna(r[item]):
                _issue(rows, "WARNING", c, y, "missing_value",
                       f"{C.ITEM_LABELS[item]} is missing; ratios that need it will be reported "
                       "as not computable (never as zero).")
        if pd.notna(r["total_assets"]) and r["total_assets"] <= 0:
            _issue(rows, "ERROR", c, y, "positive_total_assets", "Total assets must be positive.")
        if pd.notna(r["revenue"]) and r["revenue"] < 0:
            _issue(rows, "ERROR", c, y, "non_negative_revenue", "Revenue cannot be negative.")
        for item in ("current_assets", "current_liabilities", "cash_and_equivalents", "inventory",
                     "short_term_borrowings", "long_term_borrowings", "interest_expense",
                     "capital_expenditure", "total_liabilities", "lease_principal_payments"):
            if pd.notna(r.get(item, np.nan)) and r[item] < 0:
                _issue(rows, "ERROR", c, y, "non_negative_item",
                       f"{C.ITEM_LABELS[item]} is negative; check the sign convention "
                       "(capital expenditure and lease principal repayments must be entered as positive outflows).")
        # Accounting identities.
        ta, tl, te = r["total_assets"], r["total_liabilities"], r["total_equity"]
        if pd.notna(ta) and pd.notna(tl) and pd.notna(te) and not _close(ta, tl + te):
            _issue(rows, "WARNING", c, y, "balance_sheet_identity",
                   f"Total assets ({ta:,.1f}) != total liabilities + equity ({tl + te:,.1f}).")
        if pd.notna(r["ebitda"]) and pd.notna(r["depreciation_amortisation"]) and pd.notna(r["ebit"]):
            if not _close(r["ebitda"] - r["depreciation_amortisation"], r["ebit"], 0.02):
                _issue(rows, "WARNING", c, y, "ebitda_bridge",
                       "EBIT differs from EBITDA - depreciation & amortisation by more than 2%; "
                       "check whether other income is included in one but not the other.")
        if pd.notna(r["current_assets"]):
            for part in ("cash_and_equivalents", "inventory"):
                if pd.notna(r[part]) and r[part] > r["current_assets"] * (1 + C.IDENTITY_TOLERANCE):
                    _issue(rows, "ERROR", c, y, "current_asset_components",
                           f"{C.ITEM_LABELS[part]} exceeds current assets.")
            if pd.notna(ta) and r["current_assets"] > ta * (1 + C.IDENTITY_TOLERANCE):
                _issue(rows, "ERROR", c, y, "current_assets_le_total", "Current assets exceed total assets.")
        debt = np.nansum([r["short_term_borrowings"], r["long_term_borrowings"]])
        if pd.notna(tl) and debt > tl * (1 + C.IDENTITY_TOLERANCE):
            _issue(rows, "ERROR", c, y, "debt_le_liabilities",
                   "Borrowings exceed total liabilities; debt is a subset of liabilities.")
        if pd.notna(r["net_profit"]) and pd.notna(r["profit_before_tax"]):
            if r["profit_before_tax"] > 0 and r["net_profit"] > r["profit_before_tax"] * 1.001:
                _issue(rows, "WARNING", c, y, "tax_sign",
                       "Net profit exceeds profit before tax (tax credit?); review.")
        if pd.notna(te) and te <= 0:
            _issue(rows, "WARNING", c, y, "negative_equity",
                   "Equity is zero or negative (accumulated losses exceed capital). Equity-based "
                   "ratios are not meaningful and are flagged, not computed.")

    return pd.DataFrame(rows, columns=["severity", "company", "fiscal_year", "check", "detail"])


def has_errors(findings: pd.DataFrame) -> bool:
    return bool((findings["severity"] == "ERROR").any())
