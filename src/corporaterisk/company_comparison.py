"""Side-by-side comparison of companies for one fiscal year.

Cross-sector comparisons can mislead: a debt-to-equity of 2x may be normal for a
toll-road operator and alarming for a software company. The comparison table
therefore always carries each company's sector and the year actually used.
"""

from __future__ import annotations

import pandas as pd

from . import config as C
from .financial_ratios import format_ratio

COMPARISON_RATIOS = ["current_ratio", "quick_ratio", "debt_to_equity", "net_debt_to_ebitda",
                     "operating_margin", "return_on_equity", "interest_coverage", "ocf_to_debt",
                     "ocf_margin", "fcf_to_debt"]

SECTOR_CAVEAT = ("Companies in different sectors have different normal ratio ranges (capital "
                 "intensity, working-capital cycle, typical leverage). Compare within a sector where "
                 "possible, and read cross-sector differences with care.")


def comparison_table(ratios: pd.DataFrame, scores: pd.DataFrame, year: int,
                     companies: list[str] | None = None, formatted: bool = False) -> pd.DataFrame:
    """One row per company: the latest year <= `year`, key ratios and the health score."""
    rows = []
    sel = companies or sorted(ratios["company"].unique())
    for company in sel:
        g = ratios[(ratios["company"] == company) & (ratios["fiscal_year"] <= year)]
        if g.empty:
            continue
        r = g.sort_values("fiscal_year").iloc[-1]
        s = scores[(scores["company"] == company) & (scores["fiscal_year"] == r["fiscal_year"])].iloc[0]
        row = {"Company": company, "Sector": r["sector"], "Year used": int(r["fiscal_year"])}
        for key in COMPARISON_RATIOS:
            name = C.RATIOS[key][0]
            if not formatted:
                row[name] = r[key]
            elif r[f"{key}__status"] == "adverse_undefined":
                row[name] = "n/m (adverse)"
            elif r[f"{key}__status"] == "not_applicable":
                row[name] = "n/a (no debt/interest)"
            else:
                row[name] = format_ratio(key, r[key])
        for d in C.DIMENSIONS:
            row[f"{d} score"] = round(s[f"score_{d}"], 1) if pd.notna(s[f"score_{d}"]) else None
        row["Health score"] = round(s["health_score"], 1) if pd.notna(s["health_score"]) else None
        row["Category"] = s["risk_category"]
        rows.append(row)
    return pd.DataFrame(rows)


def multiple_sectors(table: pd.DataFrame) -> bool:
    return table["Sector"].nunique() > 1 if not table.empty else False
