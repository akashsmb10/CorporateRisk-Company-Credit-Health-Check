"""Altman Z-score family: financial-distress SCREENING (not default probability).

Three published variants are implemented separately. Coefficients, input
definitions and zone thresholds are never mixed between variants.

    original  (Altman 1968)      public MANUFACTURING companies
        Z  = 1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 1.0 X5
        X4 = market value of equity / total liabilities
        zones: Z > 2.99 safe | 1.81-2.99 grey | < 1.81 distress

    z_prime   (Altman 1983)      PRIVATE manufacturing companies (no market price)
        Z' = 0.717 X1 + 0.847 X2 + 3.107 X3 + 0.420 X4 + 0.998 X5
        X4 = book value of equity / total liabilities
        zones: Z' > 2.90 safe | 1.23-2.90 grey | < 1.23 distress

    z_double_prime (Altman 1995) NON-MANUFACTURING and emerging-market companies
        Z'' = 6.56 X1 + 3.26 X2 + 6.72 X3 + 1.05 X4
        X4 = book value of equity / total liabilities   (no sales/assets term,
             because asset turnover varies too much across industries)
        zones: Z'' > 2.60 safe | 1.10-2.60 grey | < 1.10 distress

Common inputs
    X1 = working capital / total assets            (short-term liquidity)
    X2 = retained earnings / total assets          (cumulative profitability, firm age)
    X3 = EBIT / total assets                       (operating productivity of assets)
    X5 = sales / total assets                      (asset turnover)

The zones come from samples of (mostly US) companies decades ago. A "distress"
zone is a prompt for deeper review, not a prediction that a company will default.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VARIANTS = {
    "original": {
        "label": "Altman Z (1968) - public manufacturers",
        "coef": {"X1": 1.2, "X2": 1.4, "X3": 3.3, "X4": 0.6, "X5": 1.0},
        "x4": "market",
        "zones": (1.81, 2.99),
    },
    "z_prime": {
        "label": "Altman Z' (1983) - private manufacturers",
        "coef": {"X1": 0.717, "X2": 0.847, "X3": 3.107, "X4": 0.420, "X5": 0.998},
        "x4": "book",
        "zones": (1.23, 2.90),
    },
    "z_double_prime": {
        "label": "Altman Z'' (1995) - non-manufacturing / emerging markets",
        "coef": {"X1": 6.56, "X2": 3.26, "X3": 6.72, "X4": 1.05},
        "x4": "book",
        "zones": (1.10, 2.60),
    },
}

COMPONENT_LABELS = {
    "X1": "Working capital / total assets",
    "X2": "Retained earnings / total assets",
    "X3": "EBIT / total assets",
    "X4": "Equity / total liabilities",
    "X5": "Sales / total assets",
}

MANUFACTURING_KEYWORDS = ["manufactur", "industrial", "automobile", "auto ", "steel", "cement",
                          "chemical", "engineering", "textile", "metals", "capital goods"]


@dataclass
class ZResult:
    variant: str
    label: str
    z: float = np.nan
    zone: str = "Not computable"
    components: dict = field(default_factory=dict)
    status: str = "ok"
    note: str = ""


def is_manufacturing(sector: str) -> bool:
    s = f" {str(sector).lower()} "
    return any(k in s for k in MANUFACTURING_KEYWORDS)


def choose_variant(sector: str, market_cap_available: bool) -> str:
    """Pick the variant whose assumptions fit the company."""
    if is_manufacturing(sector):
        return "original" if market_cap_available else "z_prime"
    return "z_double_prime"


def zone(z: float, variant: str) -> str:
    if pd.isna(z):
        return "Not computable"
    lo, hi = VARIANTS[variant]["zones"]
    if z > hi:
        return "Safe"
    if z >= lo:
        return "Grey"
    return "Distress"


def compute_z(row: pd.Series | dict, variant: str | None = None) -> ZResult:
    """Z-score for one company-year. Missing inputs -> 'not computable' (never invented)."""
    r = dict(row)
    mcap = r.get("market_capitalisation", np.nan)
    if variant is None:
        variant = choose_variant(r.get("sector", ""), not pd.isna(mcap))
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant '{variant}'. Choose from {list(VARIANTS)}.")
    spec = VARIANTS[variant]
    res = ZResult(variant=variant, label=spec["label"])

    needed = ["current_assets", "current_liabilities", "retained_earnings", "ebit", "total_assets",
              "total_liabilities"]
    needed += ["market_capitalisation"] if spec["x4"] == "market" else ["total_equity"]
    if "X5" in spec["coef"]:
        needed.append("revenue")
    missing = [k for k in needed if pd.isna(r.get(k, np.nan))]
    if missing:
        res.status = "not computable"
        res.note = "Missing input(s): " + ", ".join(missing)
        return res
    ta, tl = float(r["total_assets"]), float(r["total_liabilities"])
    if ta <= 0 or tl <= 0:
        res.status = "not computable"
        res.note = "Total assets and total liabilities must be positive."
        return res

    x = {
        "X1": (r["current_assets"] - r["current_liabilities"]) / ta,
        "X2": r["retained_earnings"] / ta,
        "X3": r["ebit"] / ta,
        "X4": (r["market_capitalisation"] if spec["x4"] == "market" else r["total_equity"]) / tl,
    }
    if "X5" in spec["coef"]:
        x["X5"] = r["revenue"] / ta
    res.components = {k: float(v) for k, v in x.items()}
    res.z = float(sum(spec["coef"][k] * x[k] for k in spec["coef"]))
    res.zone = zone(res.z, variant)
    if spec["x4"] == "book" and r.get("total_equity", 0) <= 0:
        res.note = "Equity is negative, so X4 is negative; this pushes the score down, as intended."
    return res


def z_table(df: pd.DataFrame, variant: str | None = None) -> pd.DataFrame:
    """Z-scores for every company-year.

    Unless forced, the variant is chosen ONCE per company (not per year), so a
    company's Z-score trend never switches formula between years. The original
    model is used only if market capitalisation is available for every year.
    """
    rows = []
    chosen = {}
    for company, g in df.groupby("company"):
        has_mcap = "market_capitalisation" in g and g["market_capitalisation"].notna().all()
        chosen[company] = variant or choose_variant(g["sector"].iloc[0], bool(has_mcap))
    for _, r in df.iterrows():
        res = compute_z(r, chosen[r["company"]])
        rows.append({"company": r["company"], "fiscal_year": r["fiscal_year"], "variant": res.variant,
                     "variant_label": res.label, "z_score": res.z, "zone": res.zone, "status": res.status,
                     "note": res.note, **{k: res.components.get(k, np.nan) for k in COMPONENT_LABELS}})
    return pd.DataFrame(rows)
