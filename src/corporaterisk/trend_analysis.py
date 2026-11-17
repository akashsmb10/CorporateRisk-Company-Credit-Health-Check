"""Multi-year trend analysis and rule-based deterioration signals.

Signals are evidence-based observations ("interest coverage fell in each of the
last two years: 4.1x -> 3.0x -> 1.8x"). They do not establish causation and do
not predict that a company will default.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .financial_ratios import ADVERSE, format_ratio

TREND_METRICS = {
    "revenue": "Revenue",
    "net_profit": "Net profit",
    "operating_margin": "Operating (EBIT) margin",
    "net_profit_margin": "Net profit margin",
    "total_debt": "Interest-bearing debt",
    "debt_to_equity": "Debt-to-equity",
    "current_ratio": "Current ratio",
    "interest_coverage": "Interest coverage",
    "operating_cash_flow": "Operating cash flow",
    "free_cash_flow": "Free cash flow",
    "health_score": "Financial health score",
}


def growth_table(ratios: pd.DataFrame) -> pd.DataFrame:
    """Year-on-year growth in revenue, net profit and debt, plus revenue CAGR per company."""
    out = []
    for company, g in ratios.sort_values("fiscal_year").groupby("company"):
        g = g.copy()
        for col in ("revenue", "net_profit", "total_debt", "operating_cash_flow"):
            prev = g[col].shift(1)
            # Growth from a zero or negative base is not meaningful -> NaN (not 0).
            g[f"{col}_yoy"] = np.where(prev > 0, g[col] / prev - 1, np.nan)
        first, last = g.iloc[0], g.iloc[-1]
        n = last["fiscal_year"] - first["fiscal_year"]
        cagr = (last["revenue"] / first["revenue"]) ** (1 / n) - 1 if n > 0 and first["revenue"] > 0 else np.nan
        g["revenue_cagr_period"] = cagr
        out.append(g[["company", "fiscal_year", "revenue_yoy", "net_profit_yoy", "total_debt_yoy",
                      "operating_cash_flow_yoy", "revenue_cagr_period"]])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def _consecutive_moves(values: list[float], n: int, direction: str) -> bool:
    """True if the last n changes all move in `direction` ('up' or 'down')."""
    v = [x for x in values if not pd.isna(x)]
    if len(v) < n + 1:
        return False
    tail = v[-(n + 1):]
    diffs = np.diff(tail)
    return bool(np.all(diffs > 0)) if direction == "up" else bool(np.all(diffs < 0))


def _path(key: str, values: list[float]) -> str:
    return " -> ".join(format_ratio(key, v) for v in values)


def deterioration_signals(ratios: pd.DataFrame, scores: pd.DataFrame, company: str,
                          year: int, lookback: int = 3) -> list[dict]:
    """Warning signals for one company using data up to and including `year`."""
    g = ratios[(ratios["company"] == company) & (ratios["fiscal_year"] <= year)].sort_values("fiscal_year")
    g = g.tail(lookback)
    if g.empty:
        return []
    s = scores[(scores["company"] == company) & (scores["fiscal_year"].isin(g["fiscal_year"]))] \
        .sort_values("fiscal_year")
    last = g.iloc[-1]
    sig: list[dict] = []

    de = g["debt_to_equity"].tolist()
    if last["debt_to_equity__status"] == ADVERSE:
        sig.append({"signal": "Negative equity", "evidence": "Equity is zero or negative in the latest year."})
    elif _consecutive_moves(de, 2, "up"):
        sig.append({"signal": "Increasing leverage",
                    "evidence": f"Debt-to-equity rose in each of the last two years ({_path('debt_to_equity', de[-3:])})."})

    icr = g["interest_coverage"].tolist()
    if _consecutive_moves(icr, 2, "down"):
        sig.append({"signal": "Declining interest coverage",
                    "evidence": f"Interest coverage fell in each of the last two years ({_path('interest_coverage', icr[-3:])})."})
    elif not pd.isna(last["interest_coverage"]) and last["interest_coverage"] < 1.5:
        sig.append({"signal": "Weak interest coverage",
                    "evidence": f"EBIT covers interest only {format_ratio('interest_coverage', last['interest_coverage'])} "
                                "in the latest year (below 1.5x)."})

    fcf = g["free_cash_flow"].dropna()
    if len(fcf) >= 2 and (fcf < 0).sum() >= 2:
        sig.append({"signal": "Persistent negative free cash flow",
                    "evidence": f"Free cash flow was negative in {(fcf < 0).sum()} of the last {len(fcf)} years."})

    cr = g["current_ratio"].tolist()
    if not pd.isna(last["current_ratio"]) and last["current_ratio"] < 1.0:
        sig.append({"signal": "Weak liquidity",
                    "evidence": f"Current ratio is {format_ratio('current_ratio', last['current_ratio'])} "
                                "(short-term obligations exceed short-term assets)."})
    elif _consecutive_moves(cr, 2, "down"):
        sig.append({"signal": "Weakening liquidity",
                    "evidence": f"Current ratio fell in each of the last two years ({_path('current_ratio', cr[-3:])})."})

    om = g["operating_margin"].tolist()
    if not pd.isna(last["net_profit"]) and last["net_profit"] < 0:
        sig.append({"signal": "Loss-making", "evidence": "Net profit is negative in the latest year."})
    elif _consecutive_moves(om, 2, "down"):
        sig.append({"signal": "Falling profitability",
                    "evidence": f"Operating margin fell in each of the last two years ({_path('operating_margin', om[-3:])})."})

    hs = s["health_score"].tolist()
    if len(hs) >= 2 and not pd.isna(hs[0]) and not pd.isna(hs[-1]) and hs[-1] - hs[0] <= -10:
        sig.append({"signal": "Falling health score",
                    "evidence": f"Health score fell from {hs[0]:.0f} to {hs[-1]:.0f} over the period shown."})
    return sig


def trend_frame(ratios: pd.DataFrame, scores: pd.DataFrame, company: str) -> pd.DataFrame:
    """Key metrics by year for one company (for charts and tables)."""
    g = ratios[ratios["company"] == company].merge(
        scores[["company", "fiscal_year", "health_score"]], on=["company", "fiscal_year"], how="left")
    return g[["fiscal_year"] + list(TREND_METRICS)].sort_values("fiscal_year").reset_index(drop=True)
