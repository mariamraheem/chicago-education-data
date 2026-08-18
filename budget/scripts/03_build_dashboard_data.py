"""
Stage 3: build the frontend-ready dataset for budget/dashboard/index.html.

Covers both budget workbooks CPS publishes each year -- District Managed
Schools and Charter/Contract/ALOP Schools -- already combined by
02_clean.py into one table with a common "School Name" column. Column names
beyond Year/Source_File/Source_Sheet/School Name are whatever CPS's actual
spreadsheets happen to contain, discovered fresh each run, so this script
stays generic: it doesn't assume any particular metric column exists, it
just republishes the cleaned table next to the dashboard under a stable
filename, drops any row that looks like a subtotal/grand-total line (any
text-ish column containing "total") the same way the enrollment pipeline
drops "District Total" / "Network Total" rows, and drops the legend/
definitions sheet rows (anything with no School Name).

This is the place to add budget-specific chart-ready aggregates (the way
enrollment's 05_build_demographics_data.py does for race/EL/IEP) once
there's a settled real schema to build them from -- check
budget/data/clean/_column_report.csv for what's actually available.

Reads:  budget/data/clean/budget_school_funding_clean.csv
Writes: budget/data/clean/budget_dashboard_data.csv
        budget/dashboard/budget_dashboard_data.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = REPO_ROOT / "budget" / "data" / "clean"
DASHBOARD_DIR = REPO_ROOT / "budget" / "dashboard"

SOURCE_FILE = CLEAN_DIR / "budget_school_funding_clean.csv"
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

    # The first real run showed each DISTRICT_MANAGED workbook also has a
    # legend/definitions sheet ("Overview" / "Overview Definitions") mixed
    # in alongside the real per-school sheets ("Traditional", "Alt-Spec").
    # It's just field-name -> description text, not budget data, and its
    # rows are blank everywhere else -- so it inflates the row count and
    # shows up as junk rows in the table. Sheet names could change year to
    # year, so rather than hardcode them: any row with no "School Name"
    # isn't describing a school, and gets dropped.
    if "School Name" in df.columns:
        df = df[df["School Name"].notna() & (df["School Name"].astype(str).str.strip() != "")]

    # The legend sheet's own header row sometimes gets auto-detected as
    # column names too (e.g. a "School Information" column full of
    # descriptive text) -- once its rows are gone those columns are 100%
    # blank, so drop any column that's now entirely empty rather than
    # leaving dead noise columns in the table / merge-tool dropdowns.
    df = df.dropna(axis=1, how="all")

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
