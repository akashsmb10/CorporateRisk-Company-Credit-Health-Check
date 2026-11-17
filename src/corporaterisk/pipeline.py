"""One entry point that runs the full analysis, used by the dashboard, reports and scripts.

Keeping this in one place guarantees that the dashboard, the PDF, the Excel file
and the processed CSVs all show the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import altman_zscore as az
from . import data_loader as dl
from . import data_validation as dv
from . import financial_ratios as fr
from . import financial_scoring as fs
from . import trend_analysis as ta


@dataclass
class Analysis:
    data: pd.DataFrame
    validation: pd.DataFrame
    ratios: pd.DataFrame
    scores: pd.DataFrame
    flags: pd.DataFrame
    altman: pd.DataFrame
    growth: pd.DataFrame
    synthetic: bool
    use_sector_overrides: bool = False


def run_analysis(df: pd.DataFrame | None = None, use_sector_overrides: bool = False,
                 strict: bool = True) -> Analysis:
    """Validate, compute ratios, scores, Z-scores and growth. Raises on data ERRORs if strict."""
    df = dl.load_financials() if df is None else df
    findings = dv.validate_financials(df)
    if strict and dv.has_errors(findings):
        errs = findings[findings["severity"] == "ERROR"]
        raise ValueError("Data validation failed:\n" + errs.to_string(index=False))
    ratios = fr.compute_ratios(df)
    scores = fs.score_table(ratios, use_sector_overrides=use_sector_overrides)
    return Analysis(data=df, validation=findings, ratios=ratios, scores=scores,
                    flags=fr.ratio_flags(ratios), altman=az.z_table(df), growth=ta.growth_table(ratios),
                    synthetic=dl.is_synthetic(df), use_sector_overrides=use_sector_overrides)


def company_assessment(a: Analysis, company: str, year: int) -> dict:
    """Everything needed to describe one company-year: score, drivers, signals, commentary."""
    rrow = a.ratios[(a.ratios["company"] == company) & (a.ratios["fiscal_year"] == year)]
    if rrow.empty:
        raise ValueError(f"No data for {company} FY{year}.")
    rrow = rrow.iloc[0]
    srow = a.scores[(a.scores["company"] == company) & (a.scores["fiscal_year"] == year)].iloc[0].to_dict()
    strengths, weaknesses = fs.strengths_and_weaknesses(rrow, srow)
    signals = ta.deterioration_signals(a.ratios, a.scores, company, year)
    commentary = fs.analyst_commentary(company, year, srow, strengths, weaknesses,
                                       [f"{s['signal'].lower()}" for s in signals])
    z = a.altman[(a.altman["company"] == company) & (a.altman["fiscal_year"] == year)].iloc[0].to_dict()
    return {"company": company, "year": year, "ratios": rrow, "score": srow, "strengths": strengths,
            "weaknesses": weaknesses, "signals": signals, "commentary": commentary, "altman": z,
            "meta": dl.company_meta(a.data, company)}
