"""Load company financial statements from CSV (one row per company and fiscal year)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config as C


def load_financials(path: Path | str | None = None) -> pd.DataFrame:
    """Read the financial-statement table and return it sorted by company and year.

    Missing numeric cells stay NaN: they are never filled with zero, because a
    missing value and a true zero mean different things in credit analysis.
    """
    path = Path(path) if path is not None else C.active_data_file()
    if not path.exists():
        raise FileNotFoundError(
            f"Financial data not found at {path}.\n"
            "Run scripts/prepare_data.py (Windows: setup_project.bat), or add your own file at "
            f"{C.REAL_DATA_FILE} using the template in data/raw/."
        )
    df = pd.read_csv(path, comment="#")
    missing_cols = [c for c in C.ID_COLUMNS + C.REQUIRED_ITEMS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"{path.name} is missing required columns: {missing_cols}")
    for col in C.OPTIONAL_ITEMS:
        if col not in df.columns:
            df[col] = float("nan")
    for col in C.ALL_ITEMS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    return df.sort_values(["company", "fiscal_year"]).reset_index(drop=True)


def is_synthetic(df: pd.DataFrame) -> bool:
    """True if any row is labelled as synthetic demonstration data."""
    return bool(df["data_type"].astype(str).str.upper().str.contains("SYNTHETIC").any())


def companies(df: pd.DataFrame) -> list[str]:
    return sorted(df["company"].unique().tolist())


def years(df: pd.DataFrame, company: str | None = None) -> list[int]:
    d = df if company is None else df[df["company"] == company]
    return sorted(d["fiscal_year"].unique().tolist())


def company_meta(df: pd.DataFrame, company: str) -> dict:
    """Sector, units, currency, basis and data type for one company."""
    row = df[df["company"] == company].iloc[-1]
    return {k: row[k] for k in ("sector", "currency", "units", "statement_basis", "data_type")}


def load_sources(path: Path | str = C.SOURCES_FILE) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["company", "fiscal_year", "source", "url_or_reference", "notes"])
    return pd.read_csv(path)
