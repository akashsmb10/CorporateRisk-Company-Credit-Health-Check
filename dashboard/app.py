"""CorporateRisk dashboard (multi-page).

    streamlit run dashboard/app.py        (Windows: run_project.bat)
Then open http://localhost:8501
"""

from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="CorporateRisk - Company Credit Health Check", page_icon="🏢", layout="wide")

pages = [
    st.Page(HERE / "pages" / "1_Executive_Overview.py", title="Executive Overview", default=True),
    st.Page(HERE / "pages" / "2_Financial_Ratios.py", title="Financial Ratio Analysis"),
    st.Page(HERE / "pages" / "3_Financial_Trends.py", title="Financial Trends"),
    st.Page(HERE / "pages" / "4_Credit_Assessment.py", title="Corporate Credit Assessment"),
    st.Page(HERE / "pages" / "5_Company_Comparison.py", title="Company Comparison"),
    st.Page(HERE / "pages" / "6_Stress_Testing.py", title="Stress Testing"),
    st.Page(HERE / "pages" / "7_Download_Reports.py", title="Download Reports"),
]
st.navigation(pages).run()
