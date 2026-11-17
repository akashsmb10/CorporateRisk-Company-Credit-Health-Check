"""Illustrative stress testing at financial-statement level.

The shocks are applied to statement line items and every ratio and the health
score are then RECOMPUTED with the same functions used for reported figures.
No score is adjusted by an arbitrary percentage.

What changes (for the selected year)
    Revenue          R' = R x (1 + revenue_change)
    EBITDA margin    m' = EBITDA/R + ebitda_margin_change      EBITDA' = R' x m'
    EBIT             EBIT' = EBITDA' - D&A                     (D&A held constant)
    Interest         I' = I x (1 + interest_change)
    Other items      PBT - (EBIT - I) is held constant (other income, exceptional items)
    Profit before tax PBT' = EBIT' - I' + other
    Tax              tax' = t x max(PBT', 0), with t the base-year effective rate
                     (fallback rate if it cannot be derived); no tax credit on losses
    Net profit       NP' = PBT' - tax'
    Operating CF     OCF' = OCF + (EBITDA' - EBITDA) - (tax' - tax)
                     (interest is treated as a financing cash flow, as is common
                     for non-financial companies under Ind AS 7; working capital
                     held constant)
    Free cash flow   FCF' = OCF' - capex - lease principal when provided

What is held constant
    The whole balance sheet (assets, liabilities, equity, debt, cash), D&A,
    capital expenditure, provided lease principal payments and working capital. In reality losses would reduce
    equity and cash, so the stressed balance-sheet ratios are, if anything,
    optimistic. All scenario results are ILLUSTRATIVE.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .financial_ratios import compute_ratios
from .financial_scoring import score_row

STRESS_OUTPUT_ITEMS = ["revenue", "ebitda", "ebit", "interest_expense", "profit_before_tax",
                       "net_profit", "operating_cash_flow", "free_cash_flow"]
STRESS_OUTPUT_RATIOS = ["interest_coverage", "net_debt_to_ebitda", "operating_margin",
                        "net_profit_margin", "ocf_to_debt", "fcf_to_debt"]


def effective_tax_rate(pbt: float, net_profit: float) -> float:
    """Base-year effective tax rate, or the fallback when it cannot be derived."""
    if pd.isna(pbt) or pd.isna(net_profit) or pbt <= 0 or net_profit > pbt:
        return C.FALLBACK_TAX_RATE
    return float(np.clip((pbt - net_profit) / pbt, 0.0, 0.5))


def stress_row(base: pd.Series, scenario: C.StressScenario) -> pd.Series:
    """Apply one scenario to one company-year of raw statement data."""
    if scenario.revenue_change <= -1:
        raise ValueError("Revenue change must be greater than -100%.")
    if scenario.interest_change < -1:
        raise ValueError("Interest change cannot be below -100%.")
    s = base.copy()
    R, E, DA, I = base["revenue"], base["ebitda"], base["depreciation_amortisation"], base["interest_expense"]
    pbt, np_ = base["profit_before_tax"], base["net_profit"]
    if any(pd.isna(v) for v in (R, E, DA, I, pbt, np_)) or R <= 0:
        raise ValueError("Stress test needs revenue (> 0), EBITDA, D&A, interest, PBT and net profit.")
    t = effective_tax_rate(pbt, np_)
    tax_base = pbt - np_
    other = pbt - (base["ebit"] - I)

    R2 = R * (1 + scenario.revenue_change)
    m2 = E / R + scenario.ebitda_margin_change
    E2 = R2 * m2
    EBIT2 = E2 - DA
    I2 = I * (1 + scenario.interest_change)
    PBT2 = EBIT2 - I2 + other
    tax2 = t * max(PBT2, 0.0)
    NP2 = PBT2 - tax2

    s["revenue"], s["ebitda"], s["ebit"] = R2, E2, EBIT2
    s["interest_expense"], s["profit_before_tax"], s["net_profit"] = I2, PBT2, NP2
    if not pd.isna(base["operating_cash_flow"]):
        s["operating_cash_flow"] = base["operating_cash_flow"] + (E2 - E) - (tax2 - tax_base)
    s["stress_tax_rate"] = t
    return s


def run_stress(df: pd.DataFrame, company: str, year: int,
               scenarios: list[C.StressScenario] | None = None,
               cfg: C.ScoringConfig | None = None) -> pd.DataFrame:
    """Results for each scenario: stressed items, key ratios and the recomputed health score.

    The company's full history is kept so that ROA/ROE averages use the same
    opening balances as in the base case.
    """
    scenarios = scenarios or C.DEFAULT_SCENARIOS
    hist = df[df["company"] == company].sort_values("fiscal_year").reset_index(drop=True)
    if year not in hist["fiscal_year"].values:
        raise ValueError(f"{company} has no data for FY{year}.")
    idx = hist.index[hist["fiscal_year"] == year][0]
    rows = []
    for sc in scenarios:
        h = hist.copy()
        stressed = stress_row(hist.loc[idx], sc)
        for col in C.ALL_ITEMS:
            h.at[idx, col] = stressed.get(col, np.nan)
        r = compute_ratios(h).iloc[idx]
        sc_score = score_row(r, cfg)
        out = {"scenario": sc.name, "revenue_change": sc.revenue_change,
               "ebitda_margin_change": sc.ebitda_margin_change, "interest_change": sc.interest_change,
               "tax_rate_used": stressed["stress_tax_rate"]}
        out.update({k: r[k] for k in STRESS_OUTPUT_ITEMS})
        out.update({k: r[k] for k in STRESS_OUTPUT_RATIOS})
        out.update({f"{k}__status": r[f"{k}__status"] for k in STRESS_OUTPUT_RATIOS})
        out["health_score"] = sc_score["health_score"]
        out["risk_category"] = sc_score["risk_category"]
        out.update({f"score_{d}": sc_score[f"score_{d}"] for d in C.DIMENSIONS})
        rows.append(out)
    res = pd.DataFrame(rows)
    res["health_score_change"] = res["health_score"] - res["health_score"].iloc[0]
    return res
