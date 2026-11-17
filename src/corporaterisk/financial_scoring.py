"""Transparent financial health scoring (0-100). ILLUSTRATIVE, educational.

Method
    1. Each ratio is mapped linearly to a 0-100 sub-score between a "weak" anchor
       (score 0) and a "strong" anchor (score 100), clipped outside that range.
       For "lower is better" ratios the weak anchor is the larger number.
    2. A dimension score is the simple average of its available ratio sub-scores.
    3. The health score is the weighted average of the available dimension scores.

Undefined ratios (see financial_ratios.py) are handled explicitly:
    adverse_undefined  -> sub-score 0 (e.g. negative equity, EBITDA <= 0): the
                          weakest outcome, because the underlying fact is adverse.
    not_applicable     -> excluded (e.g. debt-service ratios for a debt-free firm).
    missing_input /
    zero_denominator   -> excluded.
When ratios or whole dimensions are excluded, the remaining dimension weights are
rescaled, and "coverage" reports how much was actually assessed: each dimension
contributes its weight times the share of its applicable ratios that were scored
(not-applicable ratios do not reduce coverage; missing ones do). Below the
configured minimum coverage the result is flagged "incomplete". Nothing is
silently filled in, so a company is neither rewarded nor penalised for gaps
without disclosure.

The score is NOT a credit rating, NOT a probability of default and NOT linked
to any regulatory risk weight.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .financial_ratios import ADVERSE, NA, OK, format_ratio


def ratio_subscore(key: str, value: float, status: str, cfg: C.ScoringConfig) -> float:
    """0-100 sub-score for one ratio, or NaN when the ratio is excluded."""
    if status == ADVERSE:
        return 0.0
    if status != OK or pd.isna(value):
        return np.nan
    weak, strong = cfg.anchors[key]
    score = (value - weak) / (strong - weak) * 100.0
    return float(np.clip(score, 0.0, 100.0))


def categorise(score: float, cfg: C.ScoringConfig) -> str:
    if pd.isna(score):
        return "Not scored"
    for lower, label in cfg.categories:
        if score >= lower:
            return label
    return cfg.categories[-1][1]


def score_row(row: pd.Series, cfg: C.ScoringConfig | None = None) -> dict:
    """Score one company-year (a row of compute_ratios output)."""
    cfg = cfg or C.ScoringConfig()
    cfg.validate()
    result: dict = {}
    dim_scores: dict[str, float] = {}
    coverage = 0.0
    for dim in C.DIMENSIONS:
        subs, applicable = [], 0
        for key, (_, d, _) in C.RATIOS.items():
            if d != dim:
                continue
            status = row[f"{key}__status"]
            s = ratio_subscore(key, row[key], status, cfg)
            result[f"{key}__score"] = s
            if status != NA:          # "not applicable" is not missing data
                applicable += 1
            if not pd.isna(s):
                subs.append(s)
        dim_scores[dim] = float(np.mean(subs)) if subs else np.nan
        result[f"{dim}__ratios_scored"] = len(subs)
        result[f"{dim}__ratios_applicable"] = applicable
        # Coverage counts each dimension's weight in proportion to the share of its
        # applicable ratios that could actually be scored.
        if applicable:
            coverage += cfg.weights[dim] * len(subs) / applicable

    available = {d: s for d, s in dim_scores.items() if not pd.isna(s)}
    avail_weight = sum(cfg.weights[d] for d in available)
    if avail_weight > 0:
        health = sum(cfg.weights[d] * s for d, s in available.items()) / avail_weight
    else:
        health = np.nan
    result.update({f"score_{d}": s for d, s in dim_scores.items()})
    result["health_score"] = health
    result["weight_coverage"] = coverage
    result["incomplete"] = coverage < cfg.min_weight_coverage
    result["risk_category"] = categorise(health, cfg)
    return result


def score_table(ratios: pd.DataFrame, cfg: C.ScoringConfig | None = None,
                use_sector_overrides: bool = False) -> pd.DataFrame:
    """Scores for every company-year.

    With use_sector_overrides=True each company is scored with its sector's
    anchors (config.SECTOR_ANCHOR_OVERRIDES); otherwise everyone shares `cfg`.
    """
    rows = []
    for _, r in ratios.iterrows():
        row_cfg = cfg or C.scoring_config_for(r["sector"], use_sector_overrides)
        s = score_row(r, row_cfg)
        s.update({"company": r["company"], "sector": r["sector"], "fiscal_year": r["fiscal_year"]})
        rows.append(s)
    cols = (["company", "sector", "fiscal_year", "health_score", "risk_category", "weight_coverage", "incomplete"]
            + [f"score_{d}" for d in C.DIMENSIONS])
    df = pd.DataFrame(rows)
    return df[cols + [c for c in df.columns if c not in cols]]


# --------------------------------------------------------------------------- #
# Plain-language strengths, weaknesses and commentary
# --------------------------------------------------------------------------- #
STRENGTH_TEXT = {
    "current_ratio": "comfortable short-term liquidity (current ratio {v})",
    "quick_ratio": "liquid assets cover short-term obligations without relying on inventory (quick ratio {v})",
    "cash_ratio": "strong cash buffer against short-term obligations (cash ratio {v})",
    "debt_to_equity": "conservative use of borrowings (debt-to-equity {v})",
    "debt_to_assets": "low share of assets funded by debt ({v})",
    "liabilities_to_assets": "assets largely funded by equity (liabilities-to-assets {v})",
    "net_profit_margin": "healthy net profit margin ({v})",
    "operating_margin": "strong operating margin ({v})",
    "return_on_assets": "good return on assets ({v})",
    "return_on_equity": "good return on equity ({v})",
    "interest_coverage": "operating profit covers interest comfortably ({v})",
    "net_debt_to_ebitda": "low net debt relative to EBITDA ({v})",
    "ocf_to_debt": "operating cash flow is large relative to debt ({v})",
    "ocf_margin": "strong cash conversion of revenue (OCF margin {v})",
    "fcf_to_debt": "free cash flow can retire debt quickly (FCF/debt {v})",
}
WEAKNESS_TEXT = {
    "current_ratio": "tight short-term liquidity (current ratio {v})",
    "quick_ratio": "dependence on inventory to meet short-term obligations (quick ratio {v})",
    "cash_ratio": "thin cash buffer (cash ratio {v})",
    "debt_to_equity": "high reliance on borrowings (debt-to-equity {v})",
    "debt_to_assets": "large share of assets funded by debt ({v})",
    "liabilities_to_assets": "assets heavily funded by liabilities ({v})",
    "net_profit_margin": "weak or negative net profit margin ({v})",
    "operating_margin": "weak operating margin ({v})",
    "return_on_assets": "weak return on assets ({v})",
    "return_on_equity": "weak return on equity ({v})",
    "interest_coverage": "limited ability of operating profit to cover interest ({v})",
    "net_debt_to_ebitda": "high net debt relative to EBITDA ({v})",
    "ocf_to_debt": "operating cash flow is small relative to debt ({v})",
    "ocf_margin": "weak cash conversion of revenue (OCF margin {v})",
    "fcf_to_debt": "free cash flow does not reduce debt (FCF/debt {v})",
}
ADVERSE_TEXT = {
    "debt_to_equity": "equity is zero or negative (accumulated losses exceed capital)",
    "return_on_equity": "equity is zero or negative, so return on equity is not meaningful",
    "net_debt_to_ebitda": "EBITDA is zero or negative, so the business is not generating operating earnings",
}


def strengths_and_weaknesses(ratio_row: pd.Series, score: dict, strong: float = 75.0,
                             weak: float = 30.0) -> tuple[list[str], list[str]]:
    """Ratio-level strengths (strongest first) and weaknesses (most severe first)."""
    strengths, weaknesses = [], []
    for key in C.RATIOS:
        s = score.get(f"{key}__score", np.nan)
        status = ratio_row[f"{key}__status"]
        if status == ADVERSE:
            weaknesses.append((-1.0, ADVERSE_TEXT.get(key, f"{C.RATIOS[key][0]} not meaningful")))
            continue
        if pd.isna(s):
            continue
        v = format_ratio(key, ratio_row[key])
        if s >= strong:
            strengths.append((s, STRENGTH_TEXT[key].format(v=v)))
        elif s <= weak:
            weaknesses.append((s, WEAKNESS_TEXT[key].format(v=v)))
    strengths.sort(key=lambda t: -t[0])
    weaknesses.sort(key=lambda t: t[0])
    # Drop duplicate texts (e.g. two adverse equity messages) while keeping order.
    seen, w_out = set(), []
    for _, t in weaknesses:
        if t not in seen:
            seen.add(t)
            w_out.append(t)
    return [t for _, t in strengths], w_out


def analyst_commentary(company: str, year: int, score: dict, strengths: list[str], weaknesses: list[str],
                       signals: list[str] | None = None) -> str:
    """Rule-based commentary. It only restates computed facts; it makes no forecast."""
    dims = {d: score.get(f"score_{d}") for d in C.DIMENSIONS}
    scored = {d: v for d, v in dims.items() if v is not None and not pd.isna(v)}
    best = max(scored, key=scored.get) if scored else None
    worst = min(scored, key=scored.get) if scored else None
    hs = score.get("health_score")
    text = [f"{company} (FY{year}) scores {hs:.0f}/100 on the illustrative health scale "
            f"({score.get('risk_category')})." if hs is not None and not pd.isna(hs)
            else f"{company} (FY{year}) could not be scored."]
    if best and worst and best != worst:
        text.append(f"Its strongest dimension is {best} ({scored[best]:.0f}) and its weakest is "
                    f"{worst} ({scored[worst]:.0f}).")
    if strengths:
        text.append("Positives include " + "; ".join(strengths[:3]) + ".")
    if weaknesses:
        text.append("Points for further review: " + "; ".join(weaknesses[:3]) + ".")
    if signals:
        text.append("Multi-year warning signals: " + "; ".join(signals[:3]) + ".")
    if score.get("incomplete"):
        text.append(f"Only {score.get('weight_coverage', 0):.0%} of the scoring weight could be assessed, "
                    "so the score is provisional.")
    text.append("This is a ratio-based screen, not a credit rating or a default-probability estimate; "
                "an analyst would also review management, industry, collateral and covenants.")
    return " ".join(text)
