# Financial ratios explained (plain language)

All examples use one simple company: revenue 1,000; EBITDA 150; depreciation 30; EBIT 120; interest 24;
net profit 72; current assets 400 (of which cash 50 and inventory 100); current liabilities 200; borrowings
300; total liabilities 600; equity 400; total assets 1,000; operating cash flow 110; capex 40; lease principal repaid 30 when provided.

## The three statements in one paragraph
The **balance sheet** is a photo on one date: what the company owns (assets) and how that was financed
(liabilities and equity). Assets = liabilities + equity, always. The **profit and loss statement** is a video of
the year: revenue minus costs gives profit. The **cash flow statement** shows the cash that actually came in
and went out. Profit is not cash, because customers may not have paid yet and machines bought this year are
expensed slowly through depreciation.

## Liquidity: can it pay bills due within a year?
| Ratio | Formula | Example | Reading |
|---|---|---|---|
| Current | Current assets / current liabilities | 400/200 = 2.0x | Below 1.0x: short-term bills exceed short-term assets |
| Quick | (Current assets − inventory) / current liabilities | 300/200 = 1.5x | Ignores stock that may be slow to sell |
| Cash | Cash / current liabilities | 50/200 = 0.25x | Strictest test |

## Leverage: how much is borrowed?
| Ratio | Formula | Example | Reading |
|---|---|---|---|
| Debt-to-equity | Borrowings / equity | 300/400 = 0.75x | Borrowed money per rupee of owners' money |
| Debt-to-assets | Borrowings / total assets | 300/1000 = 30% | Share of assets funded by loans |
| Liabilities-to-assets | Total liabilities / total assets | 600/1000 = 60% | Includes payables, provisions etc. |

**Debt ≠ liabilities.** Debt is interest-bearing borrowing. Liabilities also include amounts owed to suppliers,
provisions and other obligations that carry no interest.

## Profitability: does the business make money?
| Ratio | Formula | Example |
|---|---|---|
| Net profit margin | Net profit / revenue | 72/1000 = 7.2% |
| Operating margin | EBIT / revenue | 120/1000 = 12% |
| ROA | Net profit / average total assets | 72/1000 = 7.2% (single year) |
| ROE | Net profit / average equity | 72/400 = 18% (single year) |

**EBIT vs EBITDA.** EBIT = earnings before interest and tax. EBITDA = EBIT + depreciation and amortisation:
a rough proxy for operating cash earnings. EBITDA ignores the cost of replacing assets, so it flatters
capital-heavy businesses.

## Debt servicing: can it pay its lenders?
| Ratio | Formula | Example | Reading |
|---|---|---|---|
| Interest coverage | EBIT / interest | 120/24 = 5.0x | Below 1x: operating profit cannot pay interest |
| Net debt / EBITDA | (Borrowings − cash) / EBITDA | 250/150 = 1.67x | ~Years of EBITDA to repay net debt |
| OCF / debt | Operating cash flow / borrowings | 110/300 = 37% | Share of debt one year's cash flow could repay |

## Cash-flow strength
| Measure | Formula | Example |
|---|---|---|
| OCF margin | OCF / revenue | 110/1000 = 11% |
| Free cash flow | OCF − capex | 110 − 40 = 70 |
| FCF / debt | FCF after provided lease payments / borrowings | 40/300 = 13.3% |

Lease principal repayments are financing cash outflows under Ind AS 116. Deduct the provided positive lease-payment figure from FCF, while OCF/debt stays unchanged. If lease principal is blank or absent, the example remains 110 ? 40 = 70, and ratio flags show **"FCF before lease repayments (lease principal not provided)"**; blank is not silently treated as a reported zero. Find the amount in the consolidated cash flow statement under financing activities, "Repayment/payment of principal portion of lease liabilities", and record PDF file/page. If only a combined principal-plus-interest line is printed, use it as printed and disclose the inclusion of interest without estimating a split. Preserve any net-of-incentives basis.

## Ratios with negative or zero denominators
* **Negative equity:** debt-to-equity would become negative and look "better" than a small positive value, which
  is the opposite of the truth. The software marks it "not meaningful (adverse)" and scores it as the worst case.
* **Negative EBITDA:** net debt / EBITDA turns negative and would look like a net-cash company. It is marked
  adverse for the same reason.
* **Zero interest or zero debt:** the ratio is "not applicable", not infinite. Debt-free companies are scored on
  the ratios that do apply.
