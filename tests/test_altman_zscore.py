"""Altman Z variants: hand-computed values, variant selection, zones, missing inputs."""

import numpy as np
import pandas as pd
import pytest
from conftest import make_row

from corporaterisk import altman_zscore as az

# Fixture: WC = 400-200 = 200, TA 1000, RE 250, EBIT 120, TL 600, equity 400, MVE 900, sales 1000
X1, X2, X3, X5 = 0.2, 0.25, 0.12, 1.0


def test_original_z_by_hand():
    res = az.compute_z(make_row(), "original")
    expected = 1.2 * X1 + 1.4 * X2 + 3.3 * X3 + 0.6 * (900 / 600) + 1.0 * X5
    assert res.z == pytest.approx(expected)                         # 2.886
    assert res.zone == "Grey"


def test_z_double_prime_by_hand_has_no_sales_term():
    res = az.compute_z(make_row(), "z_double_prime")
    expected = 6.56 * X1 + 3.26 * X2 + 6.72 * X3 + 1.05 * (400 / 600)
    assert res.z == pytest.approx(expected)
    assert "X5" not in res.components


def test_z_prime_uses_book_equity():
    res = az.compute_z(make_row(), "z_prime")
    expected = 0.717 * X1 + 0.847 * X2 + 3.107 * X3 + 0.420 * (400 / 600) + 0.998 * X5
    assert res.z == pytest.approx(expected)


def test_variant_selection():
    assert az.choose_variant("Industrial Manufacturing", True) == "original"
    assert az.choose_variant("Industrial Manufacturing", False) == "z_prime"
    assert az.choose_variant("Infrastructure", True) == "z_double_prime"


def test_zone_thresholds_not_mixed():
    assert az.zone(2.0, "original") == "Grey"          # 1.81-2.99
    assert az.zone(2.0, "z_double_prime") == "Grey"    # 1.10-2.60
    assert az.zone(2.8, "z_double_prime") == "Safe"
    assert az.zone(2.8, "original") == "Grey"
    assert az.zone(1.0, "z_double_prime") == "Distress"


def test_missing_market_value_means_not_computable():
    res = az.compute_z(make_row(market_capitalisation=np.nan), "original")
    assert res.status == "not computable" and np.isnan(res.z) and "market_capitalisation" in res.note


def test_variant_fixed_per_company_across_years():
    df = pd.DataFrame([make_row(fiscal_year=2024, market_capitalisation=np.nan), make_row()])
    t = az.z_table(df)
    assert t["variant"].nunique() == 1 and t["variant"].iloc[0] == "z_prime"
