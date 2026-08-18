"""
Stage 3: build the frontend-ready dataset for budget/dashboard/index.html.

Unlike enrollment, 02_clean.py's budget output has never been checked
against a real CPS budget workbook (see that script's docstring) -- its
column names beyond Year/Source_File/Source_Sheet are whatever CPS's actual
spreadsheets happen to contain, discovered fresh each run. So this script
stays generic: it doesn't assume any particular metric column exists, it
just republishes the cleaned table next to the dashboard under a stable
filename, and drops any row that looks like a subtotal/grand-total line
(any text-ish column containing "total") the same way the enrollment
pipeline drops "District Total" / "Network Total" rows.

Once a real run has produced budget/data/clean/_column_report.csv and
you've seen what CPS's actual columns are called, this is the place to add
budget-specific chart-ready aggregates (the way enrollment's
05_build_demographics_data.py does for race/EL/IEP), matching this file's
real schema rather than guessing at it.

Reads:  budget/data/clean/district_managed_funds_clean.csv
Writes: budget/data/clean/budget_dashboard_data.csv
        budget/dashboard/budget_dashboard_data.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = REPO_ROOT / "budget" / "data" / "clean"
DASHBOARD_DIR = REPO_ROOT / "budget" / "dashboard"

SOURCE_FILE = CLEAN_DIR / "district_managed_funds_clean.csv"
OUTPUT_FILENAME = "budget_dashboard_data.csv"

# Metadata columns 02_clean.py always adds -- never treated as a "name"
# column to check for "total" rows.
METADATA_COLUMNS = {"Year", "Source_File", "Source_Sheet"}


def build_dashboard_data(source_file: Path = SOURCE_FILE) -> pd.DataFrame:
    if not source_file.exists():
        print(f"{source_file} not found -- run 01_scrape.py/02_clean.py first. Skipping.")
        return pd.DataFrame()

    df = pd.read_csv(source_file)
    if df.empty:
        print(f"{source_file} is empty. Nothing to build.")
        return df

    # Checked via astype(str) rather than filtering to "object"/string dtype
    # columns first -- pandas' string dtype varies by version (plain
    # "object" vs a dedicated string dtype), and a numeric column converted
    # to text will never accidentally contain "total" anyway, so it's safe
    # to just check every non-metadata column.
    for col in df.columns:
        if col in METADATA_COLUMNS:
            continue
        df = df[~df[col].astype(str).str.contains("total", case=False, na=False)]

    return df.reset_index(drop=True)


if __name__ == "__main__":
    result = build_dashboard_data()
    if result.empty:
        print("Nothing to write.")
    else:
        CLEAN_DIR.mkdir(parents=True, exist_ok=True)
        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        clean_out = CLEAN_DIR / OUTPUT_FILENAME
        dashboard_out = DASHBOARD_DIR / OUTPUT_FILENAME
        result.to_csv(clean_out, index=False)
        result.to_csv(dashboard_out, index=False)
        print(f"Wrote {clean_out} and {dashboard_out} ({len(result)} rows)")
