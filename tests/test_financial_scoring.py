"""Scoring engine: sub-score mapping, weights, missing data and categories."""

import numpy as np
import pandas as pd
import pytest
from conftest import make_row

from corporaterisk import config as C
from corporaterisk import financial_ratios as fr
from corporaterisk import financial_scoring as fs


def test_subscore_is_linear_and_clipped():
    cfg = C.ScoringConfig()                       # current ratio anchors (0.8, 2.0)
    assert fs.ratio_subscore("current_ratio", 1.4, fr.OK, cfg) == pytest.approx(50.0)
    assert fs.ratio_subscore("current_ratio", 5.0, fr.OK, cfg) == 100.0
    assert fs.ratio_subscore("current_ratio", 0.1, fr.OK, cfg) == 0.0


def test_lower_is_better_direction():
    cfg = C.ScoringConfig()                       # debt-to-equity anchors (3.0, 0.3)
    low = fs.ratio_subscore("debt_to_equity", 0.5, fr.OK, cfg)
    high = fs.ratio_subscore("debt_to_equity", 2.5, fr.OK, cfg)
    assert low > high


def test_adverse_scores_zero_and_missing_is_excluded():
    cfg = C.ScoringConfig()
    assert fs.ratio_subscore("debt_to_equity", np.nan, fr.ADVERSE, cfg) == 0.0
    assert np.isnan(fs.ratio_subscore("quick_ratio", np.nan, fr.MISSING, cfg))
    assert np.isnan(fs.ratio_subscore("interest_coverage", np.nan, fr.NA, cfg))


def test_weights_must_sum_to_one():
    cfg = C.ScoringConfig()
    cfg.weights["Liquidity"] = 0.5
    with pytest.raises(ValueError):
        cfg.validate()


def test_health_score_is_weighted_average_of_dimensions(one_year):
    r = fr.compute_ratios(one_year).iloc[0]
    s = fs.score_row(r)
    w = C.ScoringConfig().weights
    expected = sum(w[d] * s[f"score_{d}"] for d in C.DIMENSIONS)
    assert s["health_score"] == pytest.approx(expected)
    assert s["weight_coverage"] == pytest.approx(1.0) and not s["incomplete"]
    assert 0 <= s["health_score"] <= 100


def test_missing_dimension_rescales_weights_and_is_disclosed():
    df = pd.DataFrame([make_row(current_assets=np.nan, cash_and_equivalents=np.nan, inventory=np.nan)])
    s = fs.score_row(fr.compute_ratios(df).iloc[0])
    assert np.isnan(s["score_Liquidity"])                         # liquidity not scored
    # liquidity weight (20%) lost, and missing cash also blocks net debt / EBITDA (1 of 3 debt-servicing ratios)
    assert s["weight_coverage"] == pytest.approx(0.80 - 0.25 / 3)
    w = C.ScoringConfig().weights
    avail = [d for d in C.DIMENSIONS if not np.isnan(s[f"score_{d}"])]
    expected = sum(w[d] * s[f"score_{d}"] for d in avail) / sum(w[d] for d in avail)
    assert s["health_score"] == pytest.approx(expected)


def test_low_coverage_flagged_incomplete():
    df = pd.DataFrame([make_row(current_assets=np.nan, cash_and_equivalents=np.nan, inventory=np.nan,
                                short_term_borrowings=np.nan)])
    s = fs.score_row(fr.compute_ratios(df).iloc[0])
    # liquidity 0/3, leverage 1/3, profitability 4/4, debt servicing 1/3, cash flow 1/2 scored
    assert s["weight_coverage"] == pytest.approx(0.25 / 3 + 0.20 + 0.25 / 3 + 0.10 / 2)
    assert s["incomplete"]


def test_not_applicable_ratios_do_not_reduce_coverage():
    df = pd.DataFrame([make_row(short_term_borrowings=0.0, long_term_borrowings=0.0, interest_expense=0.0,
                                profit_before_tax=120.0, net_profit=90.0)])
    s = fs.score_row(fr.compute_ratios(df).iloc[0])
    assert s["weight_coverage"] == pytest.approx(1.0)


def test_negative_equity_lowers_score():
    good = fs.score_row(fr.compute_ratios(pd.DataFrame([make_row()])).iloc[0])
    bad = fs.score_row(fr.compute_ratios(pd.DataFrame([make_row(total_equity=-50.0, total_liabilities=1050.0)]))
                       .iloc[0])
    assert bad["score_Leverage"] < good["score_Leverage"]


@pytest.mark.parametrize("score,label", [(95, "Strong"), (80, "Strong"), (79.9, "Healthy"), (50, "Moderate Risk"),
                                         (40, "Elevated Risk"), (10, "High Risk"), (np.nan, "Not scored")])
def test_categories(score, label):
    assert fs.categorise(score, C.ScoringConfig()) == label


def test_sector_overrides_change_only_that_sector():
    base = C.scoring_config_for("Infrastructure", False)
    infra = C.scoring_config_for("Infrastructure", True)
    other = C.scoring_config_for("Industrial Manufacturing", True)
    assert infra.anchors["debt_to_equity"] != base.anchors["debt_to_equity"]
    assert other.anchors == base.anchors


def test_commentary_has_no_unsupported_claims(one_year):
    r = fr.compute_ratios(one_year).iloc[0]
    s = fs.score_row(r)
    st, wk = fs.strengths_and_weaknesses(r, s)
    text = fs.analyst_commentary("Test Co (Synthetic)", 2025, s, st, wk)
    assert "not a credit rating" in text and "probability" in text
