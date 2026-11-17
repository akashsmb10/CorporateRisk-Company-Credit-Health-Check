# Methodology

## 1. Pipeline

```
CSV (one row per company-year) → data_validation → financial_ratios (value + status)
   → financial_scoring (0-100) → altman_zscore → trend_analysis → company_comparison
   → stress_testing (recomputes statements) → report_generator (PDF) / excel_export / dashboard
```
`pipeline.run_analysis()` runs these steps once, so the dashboard, the PDF, the Excel file and the processed
CSVs always show the same numbers.

## 2. Data validation
Errors stop the analysis: mixed units or bases for one company, a financial-sector company, negative
revenue/assets, borrowings larger than total liabilities, cash or inventory larger than current assets.
Warnings are reported but do not stop it: missing items, balance-sheet identity off by more than 1%, an EBITDA
bridge that does not reconcile, non-consecutive years, negative equity.

## 3. Ratios and undefined cases
Each ratio returns a value **and** a status (`ok`, `missing_input`, `zero_denominator`, `not_applicable`,
`adverse_undefined`). Undefined ratios are never replaced with zero.

* **Debt** = short-term + long-term borrowings. It is not the same as total liabilities, which also contain
  payables, provisions and other obligations.
* **Free cash flow after lease payments** = OCF - capex - `lease_principal_payments` when the optional lease figure is provided. Capex and lease repayments are positive outflows in the input units (INR crore for the real data). Lease principal is a financing cash flow under Ind AS 116, so it is deducted here; OCF and OCF/debt remain unchanged. If lease principal is blank or the column is absent, FCF remains OCF - capex and `ratio_flags` explicitly records: "FCF before lease repayments (lease principal not provided)". Missing lease principal is not silently recorded as zero.
* **Negative equity:** debt-to-equity and ROE are `adverse_undefined`. A negative denominator flips the sign,
  so a heavily indebted loss-making company could otherwise look "good".
* **EBITDA ≤ 0:** net debt / EBITDA is `adverse_undefined` (no earnings to repay debt).
* **No debt / no interest:** debt-service ratios are `not_applicable`.
* **ROA/ROE** use average opening and closing balances when the prior year exists, otherwise closing balances
  (disclosed as a basis note).

## 4. Financial health score (illustrative)
1. **Sub-score per ratio:** linear between a weak anchor (0) and a strong anchor (100), clipped outside.
   `score = (value − weak) / (strong − weak) × 100`. For "lower is better" ratios, the weak anchor is the larger number.
2. **Dimension score** = mean of available sub-scores in that dimension.
3. **Health score** = Σ wᵢ·Dᵢ / Σ wᵢ over the dimensions that could be scored.

| Dimension | Weight | Ratios |
|---|---|---|
| Liquidity | 20% | current, quick, cash |
| Leverage | 25% | debt/equity, debt/assets, liabilities/assets |
| Profitability | 20% | net margin, operating margin, ROA, ROE |
| Debt servicing | 25% | interest coverage, net debt/EBITDA, OCF/debt |
| Cash-flow strength | 10% | OCF margin, FCF/debt |

**Why these weights?** Lenders care first about whether debt can be serviced and how much debt there is
(50% together). Liquidity and profitability matter for near-term and sustainable repayment capacity. Cash-flow
strength overlaps with debt servicing, so it gets a smaller weight. These are judgement-based teaching values.

**Undefined ratios in the score:** `adverse_undefined` scores 0 (worst case). `not_applicable`, `missing_input`
and `zero_denominator` are excluded. **Coverage** = Σ over dimensions of weight × (scored ratios / applicable
ratios). It is shown with every score, and below 70% the score is flagged *provisional*.

**Bands:** Strong ≥ 80, Healthy ≥ 65, Moderate Risk ≥ 50, Elevated Risk ≥ 35, High Risk < 35. These are
educational labels, **not** agency ratings, **not** default probabilities and **not** linked to Basel risk weights.

**Sector anchors (optional):** `config.SECTOR_ANCHOR_OVERRIDES` loosens leverage anchors for infrastructure and
liquidity anchors for consumer goods. They are off by default so that all companies share one scale.

## 5. Altman Z-score
See `src/corporaterisk/altman_zscore.py`. Three variants (original, Z′, Z″) each have their own
coefficients, X4 definition and zones. The variant is chosen once per company: original for listed
manufacturers with market cap, Z′ for manufacturers without it, Z″ for everyone else. Missing inputs make
the score "not computable".

## 6. Trend signals
Rule-based over the last three years: debt-to-equity up two years running (or negative equity); interest
coverage down two years running (or below 1.5×); free cash flow negative in at least two years; current ratio
below 1.0× or down two years running; operating margin down two years running (or a net loss); health score
down by 10+ points.

## 7. Stress testing
See the docstring in `stress_testing.py` for every formula. Revenue, EBITDA margin and interest cost are shocked.
EBIT, PBT, tax (base-year effective rate, no tax credit on losses), net profit, OCF and FCF are recomputed, and
the same ratio and scoring functions are re-run. The balance sheet, D&A, capex, provided lease principal payments and working capital are held constant.

Lease-payment source: use the consolidated cash flow statement, financing activities, "Repayment/payment of principal portion of lease liabilities". Record the positive printed outflow and cite PDF file/page. If only a combined principal-plus-interest line is printed, use the printed amount and disclose that it includes interest; do not estimate a principal split. Preserve disclosed net-of-incentives wording.
