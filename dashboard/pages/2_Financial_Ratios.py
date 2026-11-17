import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from common import disclaimer, setup  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk.financial_ratios import RATIO_DEFINITIONS, STATUS_TEXT, format_ratio  # noqa: E402

a, company, year = setup("Financial Ratio Analysis")
hist = a.ratios[(a.ratios["company"] == company) & (a.ratios["fiscal_year"] <= year)] \
    .sort_values("fiscal_year").tail(3)
yrs = hist["fiscal_year"].tolist()
st.caption("Ratios for the selected year and up to two prior years. 'n/m' = not meaningful (adverse "
           "denominator, scored as weakest); 'n/a' = not applicable (excluded from scoring).")


def cell(key: str, row: pd.Series) -> str:
    status = row[f"{key}__status"]
    if status == "adverse_undefined":
        return "n/m"
    if status != "ok":
        return "n/a"
    return format_ratio(key, row[key])


for dim in C.DIMENSIONS:
    st.subheader(dim)
    rows = []
    for key, (name, d, direction) in C.RATIOS.items():
        if d != dim:
            continue
        rec = {"Ratio": name, "Better when": direction}
        for _, h in hist.iterrows():
            rec[f"FY{h['fiscal_year']}"] = cell(key, h)
        latest = hist.iloc[-1]
        rec["Status (latest)"] = "ok" if latest[f"{key}__status"] == "ok" else STATUS_TEXT[latest[f"{key}__status"]]
        rows.append(rec)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander(f"How the {dim.lower()} ratios are calculated and read"):
        for key, (name, d, _) in C.RATIOS.items():
            if d == dim:
                formula, meaning = RATIO_DEFINITIONS[key]
                st.markdown(f"**{name}** = {formula}  \n{meaning}")

flags = a.flags[(a.flags["company"] == company) & (a.flags["fiscal_year"] == year)]
if not flags.empty:
    st.subheader("Ratio notes for this year")
    st.dataframe(flags[["ratio", "dimension", "status", "explanation"]], hide_index=True, width="stretch")
disclaimer()
