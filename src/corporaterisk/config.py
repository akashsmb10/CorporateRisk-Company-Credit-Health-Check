"""Central configuration: paths, data schema and every ILLUSTRATIVE assumption.

All paths are derived from this file's location, so the project runs from any
working directory on Windows, macOS or Linux (no hard-coded absolute paths).

Anything marked ILLUSTRATIVE is an educational assumption chosen to make the
methodology concrete. It is not an official rating criterion, not a regulatory
parameter and not estimated from default data. Change it here, in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SAMPLE_REPORTS_DIR = PROJECT_ROOT / "reports" / "sample_reports"

REAL_DATA_FILE = RAW_DIR / "company_financials.csv"          # you create this (see docs/data_sources.md)
REAL_DATA_TEMPLATE = RAW_DIR / "company_financials_TEMPLATE.csv"
SYNTHETIC_DATA_FILE = SAMPLE_DIR / "synthetic_financials.csv"
SOURCES_FILE = DATA_DIR / "sources.csv"


def active_data_file() -> Path:
    """Real company data if the user has supplied it, otherwise the synthetic demo set."""
    return REAL_DATA_FILE if REAL_DATA_FILE.exists() else SYNTHETIC_DATA_FILE


# --------------------------------------------------------------------------- #
# Data schema
# --------------------------------------------------------------------------- #
ID_COLUMNS = ["company", "sector", "fiscal_year", "fiscal_year_end", "statement_basis",
              "currency", "units", "data_type"]

# Financial items. All monetary values are in the same currency and units per company.
# capital_expenditure is entered as a POSITIVE number (cash spent on fixed assets).
REQUIRED_ITEMS = [
    # Balance sheet
    "current_assets", "current_liabilities", "cash_and_equivalents", "inventory",
    "total_assets", "total_liabilities", "total_equity",
    "short_term_borrowings", "long_term_borrowings", "retained_earnings",
    # Income statement
    "revenue", "ebitda", "depreciation_amortisation", "ebit", "interest_expense",
    "profit_before_tax", "net_profit",
    # Cash flow statement
    "operating_cash_flow", "capital_expenditure",
]
OPTIONAL_ITEMS = ["market_capitalisation", "lease_principal_payments"]
ALL_ITEMS = REQUIRED_ITEMS + OPTIONAL_ITEMS

ITEM_LABELS = {
    "current_assets": "Current assets", "current_liabilities": "Current liabilities",
    "cash_and_equivalents": "Cash and cash equivalents", "inventory": "Inventory",
    "total_assets": "Total assets", "total_liabilities": "Total liabilities",
    "total_equity": "Total equity", "short_term_borrowings": "Short-term borrowings",
    "long_term_borrowings": "Long-term borrowings", "retained_earnings": "Retained earnings",
    "revenue": "Revenue", "ebitda": "EBITDA", "depreciation_amortisation": "Depreciation & amortisation",
    "ebit": "EBIT", "interest_expense": "Interest expense", "profit_before_tax": "Profit before tax",
    "net_profit": "Net profit", "operating_cash_flow": "Cash flow from operations",
    "capital_expenditure": "Capital expenditure", "market_capitalisation": "Market capitalisation",
    "lease_principal_payments": "Lease principal repaid",
}

# Non-financial companies only: bank / NBFC / insurer ratios need different interpretation.
EXCLUDED_SECTOR_KEYWORDS = ["bank", "nbfc", "insurance", "finance company"]

# Validation tolerance for accounting identities (relative).
IDENTITY_TOLERANCE = 0.01


# --------------------------------------------------------------------------- #
# Ratio catalogue (key -> display name, dimension, direction)
# --------------------------------------------------------------------------- #
RATIOS = {
    "current_ratio": ("Current ratio", "Liquidity", "higher"),
    "quick_ratio": ("Quick ratio", "Liquidity", "higher"),
    "cash_ratio": ("Cash ratio", "Liquidity", "higher"),
    "debt_to_equity": ("Debt-to-equity", "Leverage", "lower"),
    "debt_to_assets": ("Debt-to-assets", "Leverage", "lower"),
    "liabilities_to_assets": ("Liabilities-to-assets", "Leverage", "lower"),
    "net_profit_margin": ("Net profit margin", "Profitability", "higher"),
    "operating_margin": ("Operating (EBIT) margin", "Profitability", "higher"),
    "return_on_assets": ("Return on assets", "Profitability", "higher"),
    "return_on_equity": ("Return on equity", "Profitability", "higher"),
    "interest_coverage": ("Interest coverage (EBIT / interest)", "Debt Servicing", "higher"),
    "net_debt_to_ebitda": ("Net debt / EBITDA", "Debt Servicing", "lower"),
    "ocf_to_debt": ("Operating cash flow / debt", "Debt Servicing", "higher"),
    "ocf_margin": ("Operating cash flow margin", "Cash Flow Strength", "higher"),
    "fcf_to_debt": ("Free cash flow / debt", "Cash Flow Strength", "higher"),
}
PERCENT_RATIOS = {"debt_to_assets", "liabilities_to_assets", "net_profit_margin", "operating_margin",
                  "return_on_assets", "return_on_equity", "ocf_to_debt", "ocf_margin", "fcf_to_debt"}
DIMENSIONS = ["Liquidity", "Leverage", "Profitability", "Debt Servicing", "Cash Flow Strength"]


# --------------------------------------------------------------------------- #
# Scoring assumptions — ILLUSTRATIVE
# --------------------------------------------------------------------------- #
@dataclass
class ScoringConfig:
    # Dimension weights (must sum to 1.0). ILLUSTRATIVE.
    weights: dict = field(default_factory=lambda: {
        "Liquidity": 0.20, "Leverage": 0.25, "Profitability": 0.20,
        "Debt Servicing": 0.25, "Cash Flow Strength": 0.10,
    })
    # Each ratio is mapped linearly to 0..100 between a "weak" anchor (score 0)
    # and a "strong" anchor (score 100), and clipped outside. ILLUSTRATIVE,
    # broadly in line with textbook rules of thumb for non-financial corporates.
    anchors: dict = field(default_factory=lambda: {
        "current_ratio": (0.8, 2.0),
        "quick_ratio": (0.5, 1.5),
        "cash_ratio": (0.05, 0.50),
        "debt_to_equity": (3.0, 0.3),
        "debt_to_assets": (0.60, 0.10),
        "liabilities_to_assets": (0.90, 0.40),
        "net_profit_margin": (-0.05, 0.15),
        "operating_margin": (0.0, 0.20),
        "return_on_assets": (-0.02, 0.10),
        "return_on_equity": (0.0, 0.20),
        "interest_coverage": (1.0, 8.0),
        "net_debt_to_ebitda": (5.0, 0.0),
        "ocf_to_debt": (0.0, 0.50),
        "ocf_margin": (0.0, 0.20),
        "fcf_to_debt": (-0.10, 0.30),
    })
    # Score bands (lower bound inclusive). ILLUSTRATIVE educational categories,
    # NOT credit ratings and NOT mapped to default probabilities.
    categories: list = field(default_factory=lambda: [
        (80.0, "Strong"), (65.0, "Healthy"), (50.0, "Moderate Risk"),
        (35.0, "Elevated Risk"), (0.0, "High Risk"),
    ])
    # If less than this share of total weight could be scored, the result is
    # flagged as "Incomplete" (disclosed, never silently filled).
    min_weight_coverage: float = 0.70

    def validate(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Dimension weights must sum to 1.0 (got {total:.4f}).")
        if set(self.weights) != set(DIMENSIONS):
            raise ValueError(f"Weights must cover exactly these dimensions: {DIMENSIONS}")
        for k, (weak, strong) in self.anchors.items():
            if weak == strong:
                raise ValueError(f"Anchors for {k} must differ.")
        bounds = [b for b, _ in self.categories]
        if bounds != sorted(bounds, reverse=True) or bounds[-1] != 0.0:
            raise ValueError("Category bounds must be descending and end at 0.")


# Optional sector-specific anchor overrides — ILLUSTRATIVE. Normal ratio ranges
# differ by sector (capital-intensive infrastructure carries more debt; consumer
# goods firms run with low working capital). Off by default so that every company
# is scored on one common scale unless the user opts in.
SECTOR_ANCHOR_OVERRIDES = {
    "Infrastructure": {"debt_to_equity": (4.0, 0.5), "net_debt_to_ebitda": (6.0, 1.0),
                       "debt_to_assets": (0.70, 0.20)},
    "Consumer Goods": {"current_ratio": (0.6, 1.5), "quick_ratio": (0.3, 1.0)},
}


def scoring_config_for(sector: str, use_sector_overrides: bool = False) -> "ScoringConfig":
    cfg = ScoringConfig()
    if use_sector_overrides and sector in SECTOR_ANCHOR_OVERRIDES:
        cfg.anchors.update(SECTOR_ANCHOR_OVERRIDES[sector])
    return cfg


# --------------------------------------------------------------------------- #
# Stress scenarios — ILLUSTRATIVE
# --------------------------------------------------------------------------- #
@dataclass
class StressScenario:
    name: str
    revenue_change: float          # e.g. -0.10 = revenue falls 10%
    ebitda_margin_change: float    # absolute change in EBITDA margin, e.g. -0.02 = -2 pp
    interest_change: float         # relative change in interest expense, e.g. +0.20 = +20%
    description: str = ""


DEFAULT_SCENARIOS = [
    StressScenario("Base case", 0.0, 0.0, 0.0, "Reported figures, no shock."),
    StressScenario("Moderate stress", -0.10, -0.02, 0.20,
                   "ILLUSTRATIVE: revenue -10%, EBITDA margin -2 pp, interest cost +20%."),
    StressScenario("Severe stress", -0.25, -0.05, 0.50,
                   "ILLUSTRATIVE: revenue -25%, EBITDA margin -5 pp, interest cost +50%."),
]

# Tax rate used under stress when the base-year effective rate cannot be derived
# (e.g. a loss year). ILLUSTRATIVE, close to the Indian new-regime corporate rate.
FALLBACK_TAX_RATE = 0.25

DISCLAIMER = ("Educational analysis only. The financial health score is a transparent, rule-based "
              "summary of ratios using illustrative weights and thresholds. It is not a credit rating, "
              "not a probability of default, not investment advice and not a regulatory measure.")
SYNTHETIC_NOTICE = ("SYNTHETIC DEMONSTRATION DATA - fictional companies generated to test the software. "
                    "These results do not describe any real company.")


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, SAMPLE_DIR, OUTPUTS_DIR, SAMPLE_REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
