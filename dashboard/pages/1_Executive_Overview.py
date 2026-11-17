import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from common import CATEGORY_COLORS, PLOT_LAYOUT, disclaimer, money, setup, units  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk.financial_ratios import format_ratio  # noqa: E402
from corporaterisk.pipeline import company_assessment  # noqa: E402

a, company, year = setup("Executive Overview")
x = company_assessment(a, company, year)
s, r, u = x["score"], x["ratios"], units(a, company)

st.markdown(f"**{company}** | {x['meta']['sector']} | FY{year} | {x['meta']['statement_basis']} statements | "
            f"amounts in {u}")

c = st.columns(4)
c[0].metric("Financial health score", f"{s['health_score']:.1f} / 100",
            help="Illustrative, rule-based score. Not a credit rating or probability of default.")
c[1].metric("Risk category (illustrative)", s["risk_category"])
c[2].metric(f"Revenue ({u})", money(r["revenue"]))
c[3].metric(f"Net profit ({u})", money(r["net_profit"]))
c = st.columns(4)
c[0].metric(f"Interest-bearing debt ({u})", money(r["total_debt"]))
icr = "n/a (no interest)" if r["interest_coverage__status"] == "not_applicable" \
    else format_ratio("interest_coverage", r["interest_coverage"])
c[1].metric("Interest coverage (EBIT / interest)", icr)
z = x["altman"]
c[2].metric("Altman Z (distress screen)", f"{z['z_score']:.2f} - {z['zone']}" if z["status"] == "ok" else "n/a",
            help=z["variant_label"])
c[3].metric("Scoring weight assessed", f"{s['weight_coverage']:.0%}",
            help="Share of the scoring weight with enough data. Below 70% the score is flagged provisional.")

st.subheader("Executive summary")
st.write(x["commentary"])

left, right = st.columns([3, 2])
with left:
    dims = pd.DataFrame({"Dimension": C.DIMENSIONS, "Score": [s[f"score_{d}"] for d in C.DIMENSIONS],
                         "Weight": [C.ScoringConfig().weights[d] for d in C.DIMENSIONS]})
    fig = go.Figure(go.Bar(x=dims["Score"], y=dims["Dimension"], orientation="h",
                           marker_color=CATEGORY_COLORS.get(s["risk_category"], "#1f3a5f"),
                           text=[f"{v:.0f}" if pd.notna(v) else "n/a" for v in dims["Score"]],
                           textposition="outside", cliponaxis=False,
                           customdata=dims["Weight"], hovertemplate="%{y}: %{x:.1f} (weight %{customdata:.0%})"
                                                                    "<extra></extra>"))
    fig.update_layout(**PLOT_LAYOUT, height=300, title="Dimension scores (0-100)")
    fig.update_xaxes(range=[0, 108])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")
with right:
    st.markdown("**Multi-year warning signals**")
    if x["signals"]:
        for sig in x["signals"]:
            st.markdown(f"- **{sig['signal']}**: {sig['evidence']}")
    else:
        st.markdown("- None triggered for the period shown.")

disclaimer()
