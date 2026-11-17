"""Ratio formulas, worked by hand on the synthetic fixture, plus edge cases."""

import math

import numpy as np
import pandas as pd
import pytest
from conftest import make_row

from corporaterisk import data_validation as dv
from corporaterisk import financial_ratios as fr


def test_current_quick_cash_ratios():
    assert fr.current_ratio(400, 200) == (2.0, fr.OK)
    assert fr.quick_ratio(400, 100, 200) == (1.5, fr.OK)          # (400-100)/200
    assert fr.cash_ratio(50, 200) == (0.25, fr.OK)


def test_debt_to_equity_uses_borrowings_not_total_liabilities(one_year):
    r = fr.compute_ratios(one_year).iloc[0]
    assert r["total_debt"] == 300
    assert r["debt_to_equity"] == pytest.approx(300 / 400)         # 0.75, not 600/400
    assert r["liabilities_to_assets"] == pytest.approx(0.6)
    assert r["debt_to_assets"] == pytest.approx(0.3)


def test_interest_coverage_and_net_debt_to_ebitda():
    assert fr.interest_coverage(120, 24) == (5.0, fr.OK)
    v, s = fr.net_debt_to_ebitda(300, 50, 150)
    assert s == fr.OK and v == pytest.approx(250 / 150)


def test_negative_interest_coverage_is_kept():
    v, s = fr.interest_coverage(-30, 20)
    assert s == fr.OK and v == pytest.approx(-1.5)


def test_free_cash_flow_and_cash_flow_ratios(one_year):
    r = fr.compute_ratios(one_year).iloc[0]
    assert r["free_cash_flow"] == 70                               # 110 - 40
    assert r["ocf_margin"] == pytest.approx(0.11)
    assert r["fcf_to_debt"] == pytest.approx(70 / 300)
    assert r["ocf_to_debt"] == pytest.approx(110 / 300)
    assert fr.free_cash_flow(np.nan, 40) != fr.free_cash_flow(np.nan, 40)   # NaN, not 0


def test_free_cash_flow_after_lease_principal(one_year):
    df = one_year.assign(lease_principal_payments=30.0)
    ratios = fr.compute_ratios(df)
    r = ratios.iloc[0]
    assert r["free_cash_flow"] == 40                              # 110 - 40 - 30
    assert r["fcf_to_debt"] == pytest.approx(40 / 300)
    assert r["ocf_to_debt"] == pytest.approx(110 / 300)            # OCF unchanged
    assert not fr.ratio_flags(ratios)["explanation"].str.contains("FCF before lease repayments").any()
    findings = dv.validate_financials(df.assign(lease_principal_payments=-30.0))
    assert "non_negative_item" in set(findings["check"])
    assert dv.validate_financials(df.assign(lease_principal_payments=0.0)).empty


def test_free_cash_flow_without_lease_principal_has_basis_note(one_year):
    for df in (one_year, one_year.assign(lease_principal_payments=np.nan)):
        ratios = fr.compute_ratios(df)
        assert ratios.iloc[0]["free_cash_flow"] == 70              # 110 - 40
        flags = fr.ratio_flags(ratios)
        notes = flags[flags["explanation"] ==
                      "FCF before lease repayments (lease principal not provided)"]
        assert len(notes) == 1 and notes.iloc[0]["status"] == "basis_note"
        assert pd.isna(ratios.iloc[0]["lease_principal_payments"])


def test_roa_roe_use_average_balances(two_years):
    r = fr.compute_ratios(two_years)
    fy25 = r[r["fiscal_year"] == 2025].iloc[0]
    assert fy25["average_basis"] == "average"
    assert fy25["return_on_assets"] == pytest.approx(72 / ((800 + 1000) / 2))
    assert fy25["return_on_equity"] == pytest.approx(72 / ((300 + 400) / 2))
    fy24 = r[r["fiscal_year"] == 2024].iloc[0]
    assert fy24["average_basis"] == "closing (no prior year)"
    assert fy24["return_on_assets"] == pytest.approx(72 / 800)


def test_zero_denominators_are_nan_not_zero():
    for value, status in (fr.current_ratio(100, 0), fr.net_profit_margin(10, 0), fr.cash_ratio(5, 0)):
        assert math.isnan(value) and status == fr.ZERO


def test_negative_equity_is_adverse_not_negative_ratio():
    v, s = fr.debt_to_equity(500, -100)
    assert math.isnan(v) and s == fr.ADVERSE
    v, s = fr.return_on_equity(-50, -100)                          # would be +0.5: misleading
    assert math.isnan(v) and s == fr.ADVERSE


def test_negative_ebitda_is_adverse():
    v, s = fr.net_debt_to_ebitda(300, 50, -20)
    assert math.isnan(v) and s == fr.ADVERSE


def test_debt_free_company_ratios_not_applicable():
    df = pd.DataFrame([make_row(short_term_borrowings=0.0, long_term_borrowings=0.0, interest_expense=0.0,
                                profit_before_tax=120.0, net_profit=90.0)])
    r = fr.compute_ratios(df).iloc[0]
    assert r["debt_to_equity"] == 0 and r["debt_to_equity__status"] == fr.OK
    assert r["interest_coverage__status"] == fr.NA
    assert r["ocf_to_debt__status"] == fr.NA and r["fcf_to_debt__status"] == fr.NA
    assert r["net_debt_to_ebitda"] < 0                             # net cash


def test_missing_input_is_flagged():
    df = pd.DataFrame([make_row(inventory=np.nan, short_term_borrowings=np.nan)])
    r = fr.compute_ratios(df).iloc[0]
    assert r["quick_ratio__status"] == fr.MISSING and math.isnan(r["quick_ratio"])
    assert r["debt_to_equity__status"] == fr.MISSING             # debt not assumed to be zero
    flags = fr.ratio_flags(fr.compute_ratios(df))
    assert (flags["status"] == fr.MISSING).sum() >= 2


def test_format_ratio():
    assert fr.format_ratio("current_ratio", 1.234) == "1.23x"
    assert fr.format_ratio("net_profit_margin", 0.0712) == "7.1%"
    assert fr.format_ratio("current_ratio", np.nan) == "n/a"


def test_validation_detects_problems():
    bad = pd.DataFrame([
        make_row(total_assets=1200.0),                              # identity broken
        make_row(fiscal_year=2026, units="lakh"),                   # unit change
        make_row(fiscal_year=2027, capital_expenditure=-5.0, cash_and_equivalents=500.0),
    ])
    f = dv.validate_financials(bad)
    checks = set(f["check"])
    assert {"balance_sheet_identity", "consistent_units", "non_negative_item",
            "current_asset_components"} <= checks
    assert dv.has_errors(f)


def test_validation_rejects_financial_sector():
    f = dv.validate_financials(pd.DataFrame([make_row(sector="Private Bank")]))
    assert "non_financial_company" in set(f["check"])


def test_clean_fixture_passes_validation(one_year):
    assert dv.validate_financials(one_year).empty
