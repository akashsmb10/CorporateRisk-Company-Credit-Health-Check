import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from common import DIM_COLORS, PLOT_LAYOUT, disclaimer, setup  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk import data_loader as dl  # noqa: E402
from corporaterisk.company_comparison import SECTOR_CAVEAT, comparison_table, multiple_sectors  # noqa: E402

a, company, year = setup("Company Comparison")
all_companies = dl.companies(a.data)
chosen = st.multiselect("Companies to compare", all_companies, default=all_companies)
cyear = st.selectbox("Comparison year (latest available year up to this is used per company)",
                     dl.years(a.data)[::-1], format_func=lambda y: f"FY{y}")
if not chosen:
    st.info("Select at least one company.")
    st.stop()

table = comparison_table(a.ratios, a.scores, cyear, chosen, formatted=True)
if multiple_sectors(table):
    st.info(SECTOR_CAVEAT)
if st.session_state.get("sel_overrides"):
    st.caption("Sector-specific scoring anchors are ON, so scores are not on one common scale.")

st.dataframe(table, hide_index=True, width="stretch")

raw = comparison_table(a.ratios, a.scores, cyear, chosen)
fig = go.Figure()
for d, col in zip(C.DIMENSIONS, DIM_COLORS):
    fig.add_trace(go.Bar(name=d, x=raw["Company"], y=raw[f"{d} score"], marker_color=col))
fig.add_trace(go.Scatter(name="Health score", x=raw["Company"], y=raw["Health score"], mode="markers",
                         marker=dict(symbol="diamond", size=14, color="#f85149")))
fig.update_layout(**PLOT_LAYOUT, barmode="group", height=420, title="Dimension scores and overall health score",
                  legend=dict(orientation="h", yanchor="bottom", y=-0.35))
fig.update_yaxes(range=[0, 105])
st.plotly_chart(fig, width="stretch")
disclaimer()
