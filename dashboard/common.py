"""Shared dashboard helpers: data loading, sidebar selections, styling, formatting."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # works without `pip install -e .`
    sys.path.insert(0, str(ROOT / "src"))

from corporaterisk import config as C  # noqa: E402
from corporaterisk import data_loader as dl  # noqa: E402
from corporaterisk.pipeline import Analysis, run_analysis  # noqa: E402

NAVY = "#5b9bd5"  # primary chart colour, readable on the dark background
CATEGORY_COLORS = {"Strong": "#3fb950", "Healthy": "#7cc47f", "Moderate Risk": "#e3b341",
                   "Elevated Risk": "#f0883e", "High Risk": "#f85149", "Not scored": "#8b949e"}
DIM_COLORS = ["#2f6fb3", "#4a8ad0", "#6ba5e3", "#94c0ee", "#c2dbf6"]
PLOT_LAYOUT = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(l=10, r=10, t=40, b=10),
                   font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=13))

CSS = """
<style>
  .block-container {padding-top: 1.4rem; max-width: 1350px;}
  div[data-testid="stMetric"] {background:#1a1f2b; border:1px solid #2d3545; border-radius:6px; padding:10px 14px;}
  div[data-testid="stMetricLabel"] p {color:#9aa4b2; font-size:0.82rem;}
  .cr-note {color:#9aa4b2; font-size:0.85rem;}
</style>
"""


@st.cache_data(show_spinner=False)
def load(use_sector_overrides: bool) -> Analysis:
    return run_analysis(use_sector_overrides=use_sector_overrides)


def setup(title: str) -> tuple[Analysis, str, int]:
    """Page header, data-status banner and the shared sidebar selection."""
    st.markdown(CSS, unsafe_allow_html=True)
    ss = st.session_state
    try:
        path = C.active_data_file()
        if not path.exists():
            raise FileNotFoundError(path)
        # Widget state is not kept when switching pages, so selections are mirrored
        # into plain session keys (sel_*) that persist across the whole session.
        overrides = ss.get("w_overrides", ss.get("sel_overrides", False))
        a = load(overrides)
    except FileNotFoundError:
        st.error("No financial data found. Run `setup_project.bat` (or `python scripts/prepare_data.py`) "
                 "from the project folder, then refresh this page.")
        st.stop()
    except ValueError as e:
        st.error(f"The input data failed validation, so it is not analysed:\n\n```\n{e}\n```")
        st.stop()

    companies = dl.companies(a.data)
    if ss.get("sel_company") not in companies:
        ss["sel_company"] = companies[0]
    with st.sidebar:
        st.markdown("### Selection")
        company = st.selectbox("Company", companies, index=companies.index(ss["sel_company"]), key="w_company")
        ss["sel_company"] = company
        yrs = dl.years(a.data, company)[::-1]
        if ss.get("sel_year") not in yrs:
            ss["sel_year"] = yrs[0]
        year = st.selectbox("Financial year", yrs, index=yrs.index(ss["sel_year"]), key=f"w_year_{company}",
                            format_func=lambda y: f"FY{y} (ended Mar {y})")
        ss["sel_year"] = year
        ss["sel_overrides"] = st.checkbox(
            "Use sector-specific scoring anchors", value=overrides, key="w_overrides",
            help="Off: every company is scored on one common scale. On: illustrative sector "
                 "adjustments from config.SECTOR_ANCHOR_OVERRIDES are applied.")
        st.caption(f"Data file: `{C.active_data_file().relative_to(C.PROJECT_ROOT)}`")
    st.title(title)
    if a.synthetic:
        st.warning("**SYNTHETIC DEMONSTRATION DATA.** These are fictional companies generated to test the "
                   "software. No result here describes a real company. Add real data via "
                   "`data/raw/company_financials.csv` (see docs/data_sources.md).")
    return a, company, int(year)


def units(a: Analysis, company: str) -> str:
    m = dl.company_meta(a.data, company)
    return f"{m['currency']} {m['units']}"


def money(v: float) -> str:
    return "n/a" if pd.isna(v) else f"{v:,.1f}"


def disclaimer() -> None:
    st.caption(C.DISCLAIMER)
