"""Stress testing recomputes statements consistently; trend signals and comparison."""

import pandas as pd
import pytest
from conftest import make_row

from corporaterisk import config as C
from corporaterisk import financial_ratios as fr
from corporaterisk import financial_scoring as fs
from corporaterisk import stress_testing as stt
from corporaterisk import trend_analysis as ta
from corporaterisk.company_comparison import comparison_table


def test_base_case_reproduces_reported_figures(one_year):
    res = stt.run_stress(one_year, "Test Co (Synthetic)", 2025, [C.DEFAULT_SCENARIOS[0]])
    r = res.iloc[0]
    assert r["revenue"] == 1000 and r["net_profit"] == pytest.approx(72)
    assert r["interest_coverage"] == pytest.approx(5.0)
    base_score = fs.score_row(fr.compute_ratios(one_year).iloc[0])["health_score"]
    assert r["health_score"] == pytest.approx(base_score)


def test_stress_arithmetic_by_hand():
    sc = C.StressScenario("t", revenue_change=-0.10, ebitda_margin_change=-0.02, interest_change=0.50)
    s = stt.stress_row(pd.Series(make_row()), sc)
    # revenue 900; margin 15% - 2pp = 13% -> EBITDA 117; EBIT 117 - 30 = 87; interest 36
    assert s["revenue"] == pytest.approx(900)
    assert s["ebitda"] == pytest.approx(117)
    assert s["ebit"] == pytest.approx(87)
    assert s["interest_expense"] == pytest.approx(36)
    # other items = PBT - (EBIT - I) = 96 - 96 = 0 -> PBT 51; tax rate 25% (24/96) -> NP 38.25
    assert s["profit_before_tax"] == pytest.approx(51)
    assert s["net_profit"] == pytest.approx(38.25)
    # OCF = 110 + (117 - 150) - (12.75 - 24) = 88.25
    assert s["operating_cash_flow"] == pytest.approx(88.25)
    # balance sheet held constant
    assert s["short_term_borrowings"] == 100 and s["total_assets"] == 1000 and s["total_equity"] == 400


def test_more_severe_scenario_never_improves_score(one_year):
    res = stt.run_stress(one_year, "Test Co (Synthetic)", 2025)
    hs = res["health_score"].tolist()
    assert hs[0] >= hs[1] >= hs[2]
    assert res["interest_coverage"].is_monotonic_decreasing


def test_losses_get_no_tax_credit():
    sc = C.StressScenario("deep", -0.5, -0.15, 1.0)
    s = stt.stress_row(pd.Series(make_row()), sc)
    assert s["profit_before_tax"] < 0 and s["net_profit"] == pytest.approx(s["profit_before_tax"])


def test_invalid_scenario_rejected():
    with pytest.raises(ValueError):
        stt.stress_row(pd.Series(make_row()), C.StressScenario("x", -1.0, 0, 0))


def test_deterioration_signals_detect_rising_leverage_and_falling_cover():
    rows = [make_row(fiscal_year=2023, short_term_borrowings=50.0, interest_expense=10.0),
            make_row(fiscal_year=2024, short_term_borrowings=150.0, interest_expense=30.0, total_liabilities=700.0,
                     total_assets=1100.0),
            make_row(fiscal_year=2025, short_term_borrowings=250.0, interest_expense=60.0, total_liabilities=800.0,
                     total_assets=1200.0)]
    df = pd.DataFrame(rows)
    r = fr.compute_ratios(df)
    s = fs.score_table(r)
    names = {x["signal"] for x in ta.deterioration_signals(r, s, "Test Co (Synthetic)", 2025)}
    assert "Increasing leverage" in names and "Declining interest coverage" in names


def test_growth_from_negative_base_is_nan():
    df = pd.DataFrame([make_row(fiscal_year=2024, net_profit=-10.0, profit_before_tax=-10.0), make_row()])
    g = ta.growth_table(fr.compute_ratios(df))
    assert pd.isna(g.loc[g["fiscal_year"] == 2025, "net_profit_yoy"]).all()


def test_comparison_uses_latest_available_year():
    a = make_row(company="A (Synthetic)")
    b = make_row(company="B (Synthetic)", fiscal_year=2024, fiscal_year_end="2024-03-31")
    df = pd.DataFrame([a, b])
    r = fr.compute_ratios(df)
    t = comparison_table(r, fs.score_table(r), 2025)
    assert dict(zip(t["Company"], t["Year used"])) == {"A (Synthetic)": 2025, "B (Synthetic)": 2024}
