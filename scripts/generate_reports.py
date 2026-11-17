"""Generate PDF credit assessment reports and the Excel ratio workbook.

    python scripts/generate_reports.py            -> outputs/
    python scripts/generate_reports.py --sample   -> reports/sample_reports/ (bundled examples)

One PDF per company (latest available year) and one Excel workbook for all companies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corporaterisk import config as C  # noqa: E402
from corporaterisk.excel_export import export_excel  # noqa: E402
from corporaterisk.pipeline import run_analysis  # noqa: E402
from corporaterisk.report_generator import build_pdf  # noqa: E402


def slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_").replace("__", "_")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", action="store_true", help="write to reports/sample_reports/")
    args = ap.parse_args()
    C.ensure_dirs()
    out = C.SAMPLE_REPORTS_DIR if args.sample else C.OUTPUTS_DIR
    a = run_analysis()
    tag = "_SYNTHETIC" if a.synthetic else ""
    for company, g in a.data.groupby("company"):
        year = int(g["fiscal_year"].max())
        p = build_pdf(a, company, year, out / f"Credit_Assessment_{slug(company)}_FY{year}{tag}.pdf")
        print(f"wrote {p.relative_to(ROOT)}")
    p = export_excel(a, out / f"Financial_Ratio_Report{tag}.xlsx")
    print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
