"""PDF and Excel generation on the bundled synthetic demonstration data."""

import pandas as pd
import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from corporaterisk import config as C
from corporaterisk.data_loader import load_financials
from corporaterisk.excel_export import export_excel
from corporaterisk.pipeline import run_analysis
from corporaterisk.report_generator import build_pdf


@pytest.fixture(scope="module")
def analysis():
    return run_analysis(load_financials(C.SYNTHETIC_DATA_FILE))


def test_pdf_contains_required_sections(analysis, tmp_path):
    company = "Kestrel Infrastructure (Synthetic)"
    p = build_pdf(analysis, company, 2025, tmp_path / "r.pdf")
    reader = PdfReader(str(p))
    text = " ".join(page.extract_text() for page in reader.pages)
    for section in ("Executive summary", "Financial ratios", "Financial trends", "Key strengths",
                    "Key financial risks", "Stress testing summary", "Limitations", "Data sources", "Report date"):
        assert section in text, section
    assert "SYNTHETIC" in text and company in text
    assert "not a credit rating" in text


def test_pdf_for_negative_equity_company(analysis, tmp_path):
    p = build_pdf(analysis, "Orbit Aviation Services (Synthetic)", 2025, tmp_path / "o.pdf")
    text = " ".join(page.extract_text() for page in PdfReader(str(p)).pages)
    assert "n/m (adverse)" in text


def test_excel_workbook_sheets_and_values(analysis, tmp_path):
    p = export_excel(analysis, tmp_path / "x.xlsx")
    wb = load_workbook(p)
    expected = {"About", "Raw_Financial_Data", "Calculated_Ratios", "Ratio_Flags", "Health_Scores", "Altman_Z",
                "Company_Comparison", "Stress_Testing", "Validation"}
    assert expected <= set(wb.sheetnames)
    assert "SYNTHETIC" in str(wb["Raw_Financial_Data"]["A1"].value)
    ratios = pd.read_excel(p, sheet_name="Calculated_Ratios", header=1)
    a = analysis.ratios
    row = a[(a["company"] == "Alpha Manufacturing (Synthetic)") & (a["fiscal_year"] == 2025)].iloc[0]
    xrow = ratios[(ratios["company"] == "Alpha Manufacturing (Synthetic)") & (ratios["fiscal_year"] == 2025)].iloc[0]
    assert xrow["current_ratio"] == pytest.approx(row["current_ratio"])
    stress = pd.read_excel(p, sheet_name="Stress_Testing", header=1)
    assert set(stress["scenario"]) == {s.name for s in C.DEFAULT_SCENARIOS}


def test_input_file_not_modified(tmp_path, analysis):
    before = C.SYNTHETIC_DATA_FILE.read_bytes()
    export_excel(analysis, tmp_path / "y.xlsx")
    assert C.SYNTHETIC_DATA_FILE.read_bytes() == before
