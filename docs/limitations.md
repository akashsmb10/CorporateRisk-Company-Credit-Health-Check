# Limitations

1. **Not a credit rating or a probability of default.** The health score is a transparent, rule-based summary.
   Its weights, anchors and bands are educational assumptions and have not been calibrated against
   observed defaults. A real PD model needs a large labelled sample of defaulted and non-defaulted firms.
2. **Synthetic demonstration data.** The bundled companies are fictional. Results become meaningful only
   after real annual-report data is entered (see `data_sources.md`).
3. **Annual figures only.** Year-end ratios can be window-dressed and miss intra-year liquidity stress,
   seasonal working capital and events after the balance-sheet date.
4. **What ratios cannot see:** off-balance-sheet exposures, guarantees, contingent liabilities, covenant
   terms, collateral, refinancing schedules (debt maturity profile), group support, management quality,
   governance, industry outlook and accounting quality. Real credit appraisal covers all of these.
5. **Cross-sector comparison.** Normal ratio ranges differ by industry; the optional sector anchors are
   illustrative only.
6. **Altman Z-score.** It was estimated on historical, mostly US samples (the original on 66 manufacturers).
   Its zones are a screening prompt, not a validated forecast for Indian companies today.
7. **Stress testing.** User-chosen sensitivities, not a macroeconomic model. The balance sheet is held
   constant, so stressed leverage is understated, and the tax treatment is simplified.
8. **EBITDA and EBIT definitions.** Companies report differently (exceptional items, other income, leases
   under Ind AS 116). Keep one definition per company and record it in `data/sources.csv`.
9. **Not investment advice, not a lending recommendation, no regulatory compliance claimed.**
