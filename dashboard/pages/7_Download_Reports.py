import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402
from common import disclaimer, setup  # noqa: E402

from corporaterisk import config as C  # noqa: E402
from corporaterisk.excel_export import export_excel  # noqa: E402
from corporaterisk.report_generator import build_pdf  # noqa: E402

a, company, year = setup("Download Reports")
slug = company.replace(" ", "_").replace("(", "").replace(")", "")
tag = "_SYNTHETIC" if a.synthetic else ""

st.markdown(f"Reports are generated on demand for **{company}, FY{year}** from the same calculations shown in "
            "this dashboard.")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**PDF credit assessment report**")
    if st.button("Generate PDF", key="pdf"):
        with tempfile.TemporaryDirectory() as td:
            p = build_pdf(a, company, year, Path(td) / "report.pdf")
            st.session_state["pdf_bytes"] = p.read_bytes()
            st.session_state["pdf_name"] = f"Credit_Assessment_{slug}_FY{year}{tag}.pdf"
    if "pdf_bytes" in st.session_state:
        st.download_button("Download PDF", st.session_state["pdf_bytes"], st.session_state["pdf_name"],
                           mime="application/pdf")
with c2:
    st.markdown("**Excel financial ratio report** (all companies)")
    if st.button("Generate Excel", key="xlsx"):
        with tempfile.TemporaryDirectory() as td:
            p = export_excel(a, Path(td) / "ratios.xlsx")
            st.session_state["xlsx_bytes"] = p.read_bytes()
    if "xlsx_bytes" in st.session_state:
        st.download_button("Download Excel", st.session_state["xlsx_bytes"], f"Financial_Ratio_Report{tag}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with c3:
    st.markdown("**CSV financial ratio data** (all companies)")
    cols = ["company", "sector", "fiscal_year"] + [c for k in C.RATIOS for c in (k, f"{k}__status")]
    st.download_button("Download CSV", a.ratios[cols].to_csv(index=False).encode("utf-8"),
                       f"financial_ratios{tag}.csv", mime="text/csv")
disclaimer()
