import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from common import NAVY, PLOT_LAYOUT, disclaimer, money, setup, units  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk.financial_ratios import format_ratio  # noqa: E402
from corporaterisk.stress_testing import run_stress  # noqa: E402

a, company, year = setup("Stress Testing (illustrative)")
u = units(a, company)
st.caption("Shocks change revenue, EBITDA margin and interest cost. EBIT, profit, tax, operating and free cash "
           "flow and every ratio are then recomputed. The balance sheet, D&A, capex and working capital are held "
           "constant, so stressed balance-sheet ratios are if anything optimistic.")

scen = [C.DEFAULT_SCENARIOS[0]]
cols = st.columns(2)
for col, base in zip(cols, C.DEFAULT_SCENARIOS[1:]):
    with col:
        st.markdown(f"**{base.name}**")
        rc = st.slider("Revenue change (%)", -60, 20, int(round(base.revenue_change * 100)), 1, key=f"r_{base.name}")
        mc = st.slider("EBITDA margin change (pp)", -15, 5, int(round(base.ebitda_margin_change * 100)), 1,
                       key=f"m_{base.name}")
        ic = st.slider("Interest cost change (%)", -20, 150, int(round(base.interest_change * 100)), 5,
                       key=f"i_{base.name}")
        scen.append(C.StressScenario(base.name, rc / 100, mc / 100, ic / 100))

try:
    res = run_stress(a.data, company, year, scen)
except ValueError as e:
    st.error(f"Stress test cannot run for this company-year: {e}")
    st.stop()


def fmt(key: str, r: pd.Series) -> str:
    status = r.get(f"{key}__status", "ok")
    if status == "adverse_undefined":
        return "n/m"
    if status == "not_applicable":
        return "n/a"
    return format_ratio(key, r[key])


k = st.columns(3)
for col, (_, r) in zip(k, res.iterrows()):
    delta = None if r["health_score_change"] == 0 else f"{r['health_score_change']:+.1f} pts"
    col.metric(f"{r['scenario']} - health score", f"{r['health_score']:.1f} ({r['risk_category']})", delta)

table = pd.DataFrame({
    "Scenario": res["scenario"],
    f"Revenue ({u})": res["revenue"].map(money),
    f"EBITDA ({u})": res["ebitda"].map(money),
    f"Net profit ({u})": res["net_profit"].map(money),
    f"Free cash flow ({u})": res["free_cash_flow"].map(money),
    "Interest coverage": [fmt("interest_coverage", r) for _, r in res.iterrows()],
    "Net debt / EBITDA": [fmt("net_debt_to_ebitda", r) for _, r in res.iterrows()],
    "Operating margin": [fmt("operating_margin", r) for _, r in res.iterrows()],
    "Net margin": [fmt("net_profit_margin", r) for _, r in res.iterrows()],
    "Tax rate used": res["tax_rate_used"].map(lambda v: f"{v:.0%}"),
})
st.dataframe(table, hide_index=True, width="stretch")

c1, c2 = st.columns(2)
fig = go.Figure(go.Bar(x=res["scenario"], y=res["health_score"], marker_color=NAVY,
                       text=res["health_score"].round(1), textposition="outside", cliponaxis=False))
fig.update_layout(**PLOT_LAYOUT, height=330, title="Health score by scenario")
fig.update_yaxes(range=[0, 105])
c1.plotly_chart(fig, width="stretch")
icr = res["interest_coverage"].where(res["interest_coverage__status"] == "ok")
fig = go.Figure(go.Bar(x=res["scenario"], y=icr, marker_color="#f85149",
                       text=[fmt("interest_coverage", r) for _, r in res.iterrows()], textposition="outside",
                       cliponaxis=False))
fig.add_hline(y=1.5, line_dash="dot", annotation_text="1.5x", line_color="#8b949e")
fig.update_layout(**PLOT_LAYOUT, height=330, title="Interest coverage by scenario (x)")
c2.plotly_chart(fig, width="stretch")
st.caption("All scenario results are ILLUSTRATIVE sensitivities chosen by the user, not forecasts and not a "
           "regulatory stress test.")
disclaimer()
