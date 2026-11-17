import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from common import NAVY, PLOT_LAYOUT, disclaimer, setup, units  # noqa: E402

from corporaterisk.trend_analysis import TREND_METRICS, deterioration_signals, trend_frame  # noqa: E402

a, company, year = setup("Financial Trends")
u = units(a, company)
tf = trend_frame(a.ratios, a.scores, company)
tf = tf[tf["fiscal_year"] <= year]
x = [f"FY{y}" for y in tf["fiscal_year"]]


def line(cols: list[str], title: str, pct: bool = False, money: bool = False) -> go.Figure:
    fig = go.Figure()
    for col, color in zip(cols, [NAVY, "#f85149", "#94c0ee", "#e3b341"]):
        fig.add_trace(go.Scatter(x=x, y=tf[col] * (100 if pct else 1), mode="lines+markers",
                                 name=TREND_METRICS[col], line=dict(color=color, width=2.5)))
    fig.add_hline(y=0, line_color="#6e7681", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, height=320, title=title,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.3))
    if pct:
        fig.update_yaxes(ticksuffix="%")
    return fig


c1, c2 = st.columns(2)
c1.plotly_chart(line(["revenue", "net_profit"], f"Revenue and net profit ({u})"), width="stretch")
c2.plotly_chart(line(["operating_cash_flow", "free_cash_flow"], f"Operating and free cash flow ({u})"),
                width="stretch")
c1, c2 = st.columns(2)
c1.plotly_chart(line(["operating_margin", "net_profit_margin"], "Profitability (%)", pct=True), width="stretch")
c2.plotly_chart(line(["interest_coverage"], "Interest coverage (x)"), width="stretch")
c1, c2 = st.columns(2)
c1.plotly_chart(line(["debt_to_equity", "current_ratio"], "Leverage and liquidity (x)"), width="stretch")
c2.plotly_chart(line(["health_score"], "Illustrative financial health score"), width="stretch")
st.caption("Gaps in a line mean the ratio was not meaningful or not applicable in that year "
           "(e.g. debt-to-equity when equity is negative).")

st.subheader("Year-by-year table")
show = tf.copy()
show.insert(0, "Year", x)
show = show.drop(columns="fiscal_year").rename(columns=TREND_METRICS)
st.dataframe(show.round(3), hide_index=True, width="stretch")

g = a.growth[(a.growth["company"] == company) & (a.growth["fiscal_year"] <= year)]
st.subheader("Growth")
gr = pd.DataFrame({"Year": [f"FY{y}" for y in g["fiscal_year"]],
                   "Revenue growth": g["revenue_yoy"].map(lambda v: "n/a" if pd.isna(v) else f"{v:+.1%}"),
                   "Net profit growth": g["net_profit_yoy"].map(lambda v: "n/a" if pd.isna(v) else f"{v:+.1%}"),
                   "Debt growth": g["total_debt_yoy"].map(lambda v: "n/a" if pd.isna(v) else f"{v:+.1%}")})
st.dataframe(gr, hide_index=True, width="stretch")
st.caption("Growth from a zero or negative base (e.g. a prior-year loss) is shown as n/a, not as a number.")

st.subheader("Deterioration signals")
sig = deterioration_signals(a.ratios, a.scores, company, year)
for s_ in sig or [{"signal": "None", "evidence": "No rule-based warning signal triggered."}]:
    st.markdown(f"- **{s_['signal']}**: {s_['evidence']}")
st.caption("Signals describe what changed in the reported figures. They do not establish causes and do not "
           "predict default.")
disclaimer()
