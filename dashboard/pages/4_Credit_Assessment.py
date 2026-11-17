import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from common import CATEGORY_COLORS, PLOT_LAYOUT, disclaimer, setup  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk.altman_zscore import COMPONENT_LABELS, VARIANTS  # noqa: E402
from corporaterisk.financial_ratios import format_ratio  # noqa: E402
from corporaterisk.pipeline import company_assessment  # noqa: E402

a, company, year = setup("Corporate Credit Assessment")
x = company_assessment(a, company, year)
s = x["score"]
cfg = C.ScoringConfig()

c = st.columns(3)
c[0].metric("Financial health score", f"{s['health_score']:.1f} / 100")
c[1].metric("Risk classification (illustrative)", s["risk_category"])
c[2].metric("Scoring weight assessed", f"{s['weight_coverage']:.0%}")
if s["incomplete"]:
    st.warning("Less than 70% of the scoring weight could be assessed; treat this score as provisional.")

left, right = st.columns([3, 2])
with left:
    rows = []
    for d in C.DIMENSIONS:
        for key, (name, dim, _) in C.RATIOS.items():
            if dim == d:
                sub = s.get(f"{key}__score")
                status = x["ratios"][f"{key}__status"]
                rows.append({"Dimension": d, "Ratio": name,
                             "Value": "n/m" if status == "adverse_undefined" else
                             ("n/a" if status != "ok" else format_ratio(key, x["ratios"][key])),
                             "Sub-score": "excluded" if pd.isna(sub) else f"{sub:.0f}"})
    st.markdown("**How the score is built**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=420)
with right:
    vals = [s[f"score_{d}"] for d in C.DIMENSIONS]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=C.DIMENSIONS + C.DIMENSIONS[:1], fill="toself",
                                    line_color=CATEGORY_COLORS.get(s["risk_category"], "#1f3a5f")))
    fig.update_layout(**{**PLOT_LAYOUT, "margin": dict(l=70, r=70, t=50, b=30)}, height=380,
                      title="Dimension profile", polar=dict(radialaxis=dict(range=[0, 100])))
    st.plotly_chart(fig, width="stretch")
    st.markdown("**Weights (illustrative)**  \n" + " | ".join(f"{d} {w:.0%}" for d, w in cfg.weights.items()))
    st.markdown("**Bands (illustrative)**  \n" + " | ".join(f"{lab} >= {lo:.0f}" for lo, lab in cfg.categories))

c1, c2 = st.columns(2)
with c1:
    st.subheader("Strengths")
    for t in x["strengths"] or ["No ratio reached the 'strong' range."]:
        st.markdown(f"- {t}")
with c2:
    st.subheader("Weaknesses")
    for t in x["weaknesses"] or ["No ratio fell into the 'weak' range."]:
        st.markdown(f"- {t}")

st.subheader("Warning indicators")
for sig in x["signals"] or [{"signal": "None", "evidence": "No multi-year warning signal triggered."}]:
    st.markdown(f"- **{sig['signal']}**: {sig['evidence']}")

st.subheader("Altman Z-score (financial distress screen)")
z = x["altman"]
if z["status"] == "ok":
    lo, hi = VARIANTS[z["variant"]]["zones"]
    st.markdown(f"**{z['variant_label']}**: Z = **{z['z_score']:.2f}** -> **{z['zone']}** zone "
                f"(distress < {lo}, grey {lo}-{hi}, safe > {hi}).")
    comp = pd.DataFrame([{"Component": f"{k}: {COMPONENT_LABELS[k]}", "Value": round(z[k], 3),
                          "Coefficient": VARIANTS[z["variant"]]["coef"][k],
                          "Contribution": round(z[k] * VARIANTS[z["variant"]]["coef"][k], 3)}
                         for k in VARIANTS[z["variant"]]["coef"]])
    st.dataframe(comp, hide_index=True, width="stretch")
    if z["note"]:
        st.caption(z["note"])
else:
    st.info(f"Z-score not computable: {z['note']}")
st.caption("The Z-score is a screening tool from historical samples. A distress-zone result is a prompt for "
           "deeper review, not a prediction of default.")

st.subheader("Credit analyst commentary")
st.write(x["commentary"])

val = a.validation[(a.validation["company"] == company) &
                   (a.validation["fiscal_year"].isin([year]) | a.validation["fiscal_year"].isna())]
if not val.empty:
    with st.expander(f"Data checks for this company ({len(val)})"):
        st.dataframe(val, hide_index=True, width="stretch")
disclaimer()
