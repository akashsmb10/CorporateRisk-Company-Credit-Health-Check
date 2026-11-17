"""Validate the input data and write processed analysis tables.

    python scripts/prepare_data.py            (Windows: called by setup_project.bat)

Uses data/raw/company_financials.csv if you have created it (real companies),
otherwise the synthetic demonstration set in data/sample/ (generated if absent).

Writes to data/processed/:
    validation_report.csv, ratios.csv, ratio_flags.csv, health_scores.csv,
    altman_zscores.csv, growth.csv
Exit codes: 0 = success, 1 = data validation errors (see validation_report.csv).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from corporaterisk import config as C  # noqa: E402
from corporaterisk import data_loader as dl  # noqa: E402
from corporaterisk import data_validation as dv  # noqa: E402
from corporaterisk.pipeline import run_analysis  # noqa: E402


def main() -> int:
    C.ensure_dirs()
    if not C.REAL_DATA_FILE.exists() and not C.SYNTHETIC_DATA_FILE.exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py")], check=True)
    path = C.active_data_file()
    df = dl.load_financials(path)
    kind = "SYNTHETIC demonstration data" if dl.is_synthetic(df) else "REAL company data"
    print(f"Input : {path.relative_to(ROOT)}  ({kind})")
    print(f"        {df['company'].nunique()} companies, {len(df)} company-years, "
          f"FY{df['fiscal_year'].min()}-FY{df['fiscal_year'].max()}")

    findings = dv.validate_financials(df)
    findings.to_csv(C.PROCESSED_DIR / "validation_report.csv", index=False)
    n_err = int((findings["severity"] == "ERROR").sum())
    n_warn = int((findings["severity"] == "WARNING").sum())
    print(f"Checks: {n_err} errors, {n_warn} warnings  -> data/processed/validation_report.csv")
    if n_err:
        print(findings[findings["severity"] == "ERROR"].to_string(index=False))
        print("Fix the errors above, then run this script again.")
        return 1

    a = run_analysis(df)
    a.ratios.to_csv(C.PROCESSED_DIR / "ratios.csv", index=False)
    a.flags.to_csv(C.PROCESSED_DIR / "ratio_flags.csv", index=False)
    a.scores.to_csv(C.PROCESSED_DIR / "health_scores.csv", index=False)
    a.altman.to_csv(C.PROCESSED_DIR / "altman_zscores.csv", index=False)
    a.growth.to_csv(C.PROCESSED_DIR / "growth.csv", index=False)
    latest = a.scores.sort_values("fiscal_year").groupby("company").tail(1)
    print("\nLatest-year illustrative health scores:")
    for _, r in latest.iterrows():
        print(f"  {r['company']:<40} FY{r['fiscal_year']}  {r['health_score']:5.1f}  {r['risk_category']}")
    print("\nProcessed tables written to data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
