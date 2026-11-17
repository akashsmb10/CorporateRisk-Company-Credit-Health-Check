"""Financial ratio calculations with explicit treatment of undefined cases.

Every ratio is returned together with a STATUS, so an undefined ratio is never
silently turned into zero:

    ok                 value is defined and meaningful
    missing_input      a required statement item is missing -> value is NaN
    zero_denominator   the denominator is zero -> value is NaN
    not_applicable     the ratio does not apply (e.g. debt ratios for a debt-free
                       company, interest cover with no interest) -> value is NaN
    adverse_undefined  the denominator is <= 0 for an adverse reason (negative
                       equity, EBITDA <= 0) -> value is NaN, and the scoring
                       engine treats it as the weakest possible outcome

Conventions
    Total interest-bearing debt = short-term + long-term borrowings (NOT total
    liabilities, which also include trade payables, provisions, etc.).
    Net debt = debt - cash and cash equivalents (negative = net cash).
    Free cash flow = operating cash flow - capital expenditure - lease principal
    repayments when provided; otherwise the before-lease basis is disclosed.
    ROA / ROE use the average of opening and closing balances when the prior
    year is available; otherwise the closing balance, and this is disclosed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

OK, MISSING, ZERO, NA, ADVERSE = "ok", "missing_input", "zero_denominator", "not_applicable", "adverse_undefined"

STATUS_TEXT = {
    MISSING: "not computable: a required input is missing",
    ZERO: "undefined: denominator is zero",
    NA: "not applicable",
    ADVERSE: "not meaningful: denominator is zero or negative for an adverse reason",
}


# --------------------------------------------------------------------------- #
# Scalar building block
# --------------------------------------------------------------------------- #
def safe_ratio(numerator: float, denominator: float) -> tuple[float, str]:
    """numerator / denominator with an explicit status. Never returns 0 for 'undefined'."""
    if pd.isna(numerator) or pd.isna(denominator):
        return np.nan, MISSING
    if denominator == 0:
        return np.nan, ZERO
    return float(numerator) / float(denominator), OK


def total_debt(short_term: float, long_term: float) -> float:
    """Interest-bearing debt. Missing if either component is missing (not assumed zero)."""
    if pd.isna(short_term) or pd.isna(long_term):
        return np.nan
    return float(short_term) + float(long_term)


def free_cash_flow(operating_cash_flow: float, capital_expenditure: float,
                   lease_principal_payments: float = np.nan) -> float:
    """Subtract positive capex and provided lease repayments; flag missing lease basis at table level."""
    if pd.isna(operating_cash_flow) or pd.isna(capital_expenditure):
        return np.nan
    fcf = float(operating_cash_flow) - float(capital_expenditure)
    return fcf if pd.isna(lease_principal_payments) else fcf - float(lease_principal_payments)


# --------------------------------------------------------------------------- #
# Liquidity
# --------------------------------------------------------------------------- #
def current_ratio(current_assets, current_liabilities):
    """Short-term assets available per rupee of short-term obligations."""
    return safe_ratio(current_assets, current_liabilities)


def quick_ratio(current_assets, inventory, current_liabilities):
    """Like the current ratio but excludes inventory, which may be slow to turn into cash."""
    if pd.isna(current_assets) or pd.isna(inventory):
        return np.nan, MISSING
    return safe_ratio(current_assets - inventory, current_liabilities)


def cash_ratio(cash, current_liabilities):
    """Most conservative liquidity test: cash alone versus short-term obligations."""
    return safe_ratio(cash, current_liabilities)


# --------------------------------------------------------------------------- #
# Leverage
# --------------------------------------------------------------------------- #
def debt_to_equity(debt, equity):
    """Interest-bearing debt per rupee of shareholders' funds."""
    if pd.isna(debt) or pd.isna(equity):
        return np.nan, MISSING
    if equity <= 0:
        return np.nan, ADVERSE  # negative equity: ratio sign flips and becomes misleading
    return float(debt) / float(equity), OK


def debt_to_assets(debt, total_assets):
    """Share of assets financed by interest-bearing debt."""
    return safe_ratio(debt, total_assets)


def liabilities_to_assets(total_liabilities, total_assets):
    """Share of assets financed by ALL liabilities (debt + payables + provisions + ...)."""
    return safe_ratio(total_liabilities, total_assets)


# --------------------------------------------------------------------------- #
# Profitability
# --------------------------------------------------------------------------- #
def net_profit_margin(net_profit, revenue):
    return safe_ratio(net_profit, revenue)


def operating_margin(ebit, revenue):
    return safe_ratio(ebit, revenue)


def return_on_assets(net_profit, average_total_assets):
    return safe_ratio(net_profit, average_total_assets)


def return_on_equity(net_profit, average_equity):
    if pd.isna(net_profit) or pd.isna(average_equity):
        return np.nan, MISSING
    if average_equity <= 0:
        return np.nan, ADVERSE
    return float(net_profit) / float(average_equity), OK


# --------------------------------------------------------------------------- #
# Debt servicing
# --------------------------------------------------------------------------- #
def interest_coverage(ebit, interest_expense):
    """How many times operating profit covers the interest bill.

    A negative value is kept: it means operating profit cannot cover any interest.
    Zero interest makes the ratio not applicable (there is nothing to cover).
    """
    if pd.isna(ebit) or pd.isna(interest_expense):
        return np.nan, MISSING
    if interest_expense == 0:
        return np.nan, NA
    return float(ebit) / float(interest_expense), OK


def net_debt_to_ebitda(debt, cash, ebitda):
    """Years of EBITDA needed to repay net debt. Negative = net cash position."""
    if pd.isna(debt) or pd.isna(cash) or pd.isna(ebitda):
        return np.nan, MISSING
    if ebitda <= 0:
        return np.nan, ADVERSE
    return (float(debt) - float(cash)) / float(ebitda), OK


def ocf_to_debt(operating_cash_flow, debt):
    if pd.isna(operating_cash_flow) or pd.isna(debt):
        return np.nan, MISSING
    if debt == 0:
        return np.nan, NA
    return float(operating_cash_flow) / float(debt), OK


# --------------------------------------------------------------------------- #
# Cash flow
# --------------------------------------------------------------------------- #
def ocf_margin(operating_cash_flow, revenue):
    return safe_ratio(operating_cash_flow, revenue)


def fcf_to_debt(fcf, debt):
    if pd.isna(fcf) or pd.isna(debt):
        return np.nan, MISSING
    if debt == 0:
        return np.nan, NA
    return float(fcf) / float(debt), OK


# --------------------------------------------------------------------------- #
# Table-level computation
# --------------------------------------------------------------------------- #
def _average_with_prior(g: pd.DataFrame, col: str) -> tuple[pd.Series, pd.Series]:
    """Average of opening and closing balance within one company; basis label per row."""
    prior = g[col].shift(1)
    consecutive = g["fiscal_year"].diff() == 1
    use_avg = prior.notna() & g[col].notna() & consecutive
    avg = np.where(use_avg, (g[col] + prior) / 2.0, g[col])
    basis = np.where(use_avg, "average", "closing (no prior year)")
    return pd.Series(avg, index=g.index), pd.Series(basis, index=g.index)


def compute_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """All ratios for every company-year, with a <ratio>__status column for each ratio."""
    out = df.copy().sort_values(["company", "fiscal_year"]).reset_index(drop=True)
    out["total_debt"] = [total_debt(s, l) for s, l in zip(out["short_term_borrowings"], out["long_term_borrowings"])]
    out["net_debt"] = out["total_debt"] - out["cash_and_equivalents"]
    if "lease_principal_payments" not in out.columns:
        out["lease_principal_payments"] = np.nan
    out["free_cash_flow"] = [free_cash_flow(o, c, l) for o, c, l in
                             zip(out["operating_cash_flow"], out["capital_expenditure"],
                                 out["lease_principal_payments"])]
    out["working_capital"] = out["current_assets"] - out["current_liabilities"]

    avg_ta, avg_te, basis = [], [], []
    for _, g in out.groupby("company", sort=False):
        a, b = _average_with_prior(g, "total_assets")
        e, _ = _average_with_prior(g, "total_equity")
        avg_ta.append(a)
        avg_te.append(e)
        basis.append(b)
    out["average_total_assets"] = pd.concat(avg_ta).sort_index()
    out["average_total_equity"] = pd.concat(avg_te).sort_index()
    out["average_basis"] = pd.concat(basis).sort_index()

    calc = {
        "current_ratio": lambda r: current_ratio(r.current_assets, r.current_liabilities),
        "quick_ratio": lambda r: quick_ratio(r.current_assets, r.inventory, r.current_liabilities),
        "cash_ratio": lambda r: cash_ratio(r.cash_and_equivalents, r.current_liabilities),
        "debt_to_equity": lambda r: debt_to_equity(r.total_debt, r.total_equity),
        "debt_to_assets": lambda r: debt_to_assets(r.total_debt, r.total_assets),
        "liabilities_to_assets": lambda r: liabilities_to_assets(r.total_liabilities, r.total_assets),
        "net_profit_margin": lambda r: net_profit_margin(r.net_profit, r.revenue),
        "operating_margin": lambda r: operating_margin(r.ebit, r.revenue),
        "return_on_assets": lambda r: return_on_assets(r.net_profit, r.average_total_assets),
        "return_on_equity": lambda r: return_on_equity(r.net_profit, r.average_total_equity),
        "interest_coverage": lambda r: interest_coverage(r.ebit, r.interest_expense),
        "net_debt_to_ebitda": lambda r: net_debt_to_ebitda(r.total_debt, r.cash_and_equivalents, r.ebitda),
        "ocf_to_debt": lambda r: ocf_to_debt(r.operating_cash_flow, r.total_debt),
        "ocf_margin": lambda r: ocf_margin(r.operating_cash_flow, r.revenue),
        "fcf_to_debt": lambda r: fcf_to_debt(r.free_cash_flow, r.total_debt),
    }
    for key, fn in calc.items():
        res = [fn(r) for r in out.itertuples(index=False)]
        out[key] = [v for v, _ in res]
        out[f"{key}__status"] = [s for _, s in res]
    return out


def ratio_flags(ratios: pd.DataFrame) -> pd.DataFrame:
    """Long table of undefined ratios and calculation-basis notes."""
    rows = []
    for _, r in ratios.iterrows():
        for key, (name, dim, _) in C.RATIOS.items():
            status = r[f"{key}__status"]
            if status == OK:
                continue
            detail = STATUS_TEXT[status]
            if key in ("debt_to_equity", "return_on_equity") and status == ADVERSE:
                detail = "not meaningful: equity is zero or negative (treated as weakest outcome in scoring)"
            elif key == "net_debt_to_ebitda" and status == ADVERSE:
                detail = "not meaningful: EBITDA is zero or negative (treated as weakest outcome in scoring)"
            elif key == "interest_coverage" and status == NA:
                detail = "not applicable: no interest expense reported"
            elif key in ("ocf_to_debt", "fcf_to_debt") and status == NA:
                detail = "not applicable: the company has no interest-bearing debt"
            rows.append({"company": r["company"], "fiscal_year": r["fiscal_year"], "ratio": name,
                         "dimension": dim, "status": status, "explanation": detail})
    for _, r in ratios.iterrows():
        if pd.isna(r.get("lease_principal_payments", np.nan)):
            rows.append({"company": r["company"], "fiscal_year": r["fiscal_year"],
                         "ratio": C.RATIOS["fcf_to_debt"][0], "dimension": "Cash Flow Strength",
                         "status": "basis_note",
                         "explanation": "FCF before lease repayments (lease principal not provided)"})
        if r["average_basis"] != "average":
            rows.append({"company": r["company"], "fiscal_year": r["fiscal_year"], "ratio": "ROA / ROE",
                         "dimension": "Profitability", "status": "basis_note",
                         "explanation": "uses closing balances because the prior year is not available"})
    return pd.DataFrame(rows, columns=["company", "fiscal_year", "ratio", "dimension", "status", "explanation"])


RATIO_DEFINITIONS = {
    "current_ratio": ("Current assets / Current liabilities",
                      "Can short-term assets (cash, receivables, inventory) pay obligations due within a year? "
                      "Below 1.0x means short-term obligations exceed short-term assets."),
    "quick_ratio": ("(Current assets - Inventory) / Current liabilities",
                    "Liquidity without relying on selling inventory, which can be slow or sold at a discount."),
    "cash_ratio": ("Cash and cash equivalents / Current liabilities",
                   "The strictest liquidity test: cash alone against short-term obligations."),
    "debt_to_equity": ("Interest-bearing debt / Total equity",
                       "How much the company borrowed per rupee of owners' money. Uses borrowings only, not "
                       "payables or provisions. Not meaningful when equity is zero or negative."),
    "debt_to_assets": ("Interest-bearing debt / Total assets",
                       "Share of the asset base financed by borrowings."),
    "liabilities_to_assets": ("Total liabilities / Total assets",
                              "Share of assets financed by ALL obligations (borrowings plus payables, provisions, "
                              "leases, etc.). Above 100% means equity is negative."),
    "net_profit_margin": ("Net profit / Revenue", "Profit kept from each rupee of sales after all costs and tax."),
    "operating_margin": ("EBIT / Revenue",
                         "Profit from operations per rupee of sales, before interest and tax; shows business "
                         "profitability independent of how it is financed."),
    "return_on_assets": ("Net profit / Average total assets", "How productively the asset base generates profit."),
    "return_on_equity": ("Net profit / Average total equity",
                         "Return earned on owners' money. Not meaningful when average equity is zero or negative."),
    "interest_coverage": ("EBIT / Interest expense",
                          "How many times operating profit covers the interest bill. Below 1.0x means operating "
                          "profit cannot pay interest; lenders often look for well above 1.5-2x."),
    "net_debt_to_ebitda": ("(Interest-bearing debt - Cash) / EBITDA",
                           "Roughly how many years of EBITDA would repay net debt. Negative means net cash. Not "
                           "meaningful when EBITDA is zero or negative."),
    "ocf_to_debt": ("Operating cash flow / Interest-bearing debt",
                    "Share of debt that one year of operating cash flow could repay."),
    "ocf_margin": ("Operating cash flow / Revenue",
                   "Cash actually generated from operations per rupee of sales; checks that profit turns into cash."),
    "fcf_to_debt": ("(Operating cash flow - Capital expenditure - Lease principal repaid when provided) / Interest-bearing debt",
                    "Cash left after investment and provided lease repayments that could reduce debt. "
                    "Missing lease principal uses the before-lease basis, disclosed in ratio flags. Negative means the company needs new "
                    "funding to sustain investment."),
}


def format_ratio(key: str, value: float) -> str:
    """Display helper: percentages for share-type ratios, 'x' multiples for the rest."""
    if pd.isna(value):
        return "n/a"
    if key in C.PERCENT_RATIOS:
        return f"{value * 100:.1f}%"
    return f"{value:.2f}x"
