"""
Stage 4: build the frontend-ready dataset for enrollment/dashboard/index.html.

02_clean.py's enrollment_general_clean.csv is "wide" -- one row per
school+year with a separate column per grade (PE, PK, K, Grade 1 ... Grade
12) plus a Total column. The dashboard, however, is written against a
"tidy"/long shape: one row per school+year+grade, with a single enrollment
count column. This script does that reshape and writes the result next to
both the pipeline's other clean outputs and the dashboard itself, so the
dashboard's relative fetch() always finds it whether it's opened straight
out of the repo or served from the deployed GitHub Pages copy.

Column names on the way out (school_id, school_name, network, school_year,
grade, enrollment) are chosen to match what enrollment/dashboard/index.html
already looks for -- see initializeFilters()/updateKPIs()/renderChart() in
that file. If you rename columns here, update those lookups too.

Reads:  enrollment/data/clean/enrollment_general_clean.csv
Writes: enrollment/data/clean/enrollment_dashboard_data.csv
        enrollment/dashboard/enrollment_dashboard_data.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = REPO_ROOT / "enrollment" / "data" / "clean"
DASHBOARD_DIR = REPO_ROOT / "enrollment" / "dashboard"

SOURCE_FILE = CLEAN_DIR / "enrollment_general_clean.csv"
OUTPUT_FILENAME = "enrollment_dashboard_data.csv"

# Grade-level columns to melt into rows. Deliberately excludes "Total" --
# Total = the sum of these, so including it too would double-count the
# dashboard's enrollment KPI/chart (which just sums the "enrollment" column
# across every row).
GRADE_COLUMNS = ["PE", "PK", "K"] + [f"Grade {i}" for i in range(1, 13)]

ID_COLUMN_MAP = {
    "Year": "school_year",
    "School ID": "school_id",
    "School Name": "school_name",
    "Network": "network",
}


def build_dashboard_data(source_file: Path = SOURCE_FILE) -> pd.DataFrame:
    if not source_file.exists():
        print(f"{source_file} not found -- run 02_clean.py first. Skipping.")
        return pd.DataFrame()

    df = pd.read_csv(source_file)

    # Drop any aggregate row -- "District Total", "Network Total", "Total",
    # etc. -- so it isn't mistaken for an individual school. 02_clean.py
    # already drops exact "District Total" rows, but this catches any
    # "*total*" variant that slips through (case-insensitive).
    if "School Name" in df.columns:
        df = df[~df["School Name"].astype(str).str.contains("total", case=False, na=False)]

    id_cols = [c for c in ID_COLUMN_MAP if c in df.columns]
    grade_cols = [c for c in GRADE_COLUMNS if c in df.columns]
    if not grade_cols:
        print(f"No grade-level columns found in {source_file} -- skipping.")
        return pd.DataFrame()

    long_df = df.melt(
        id_vars=id_cols,
        value_vars=grade_cols,
        var_name="grade",
        value_name="enrollment",
    )
    long_df.rename(columns=ID_COLUMN_MAP, inplace=True)

    long_df["enrollment"] = pd.to_numeric(long_df["enrollment"], errors="coerce")
    long_df = long_df.dropna(subset=["enrollment"])
    long_df = long_df[long_df["enrollment"] != 0]
    long_df["enrollment"] = long_df["enrollment"].astype(int)

    grade_order = {g: i for i, g in enumerate(GRADE_COLUMNS)}
    sort_cols = [c for c in ["school_year", "school_id"] if c in long_df.columns]
    long_df["_grade_sort"] = long_df["grade"].map(grade_order)
    long_df = long_df.sort_values(sort_cols + ["_grade_sort"]).drop(columns="_grade_sort")

    return long_df.reset_index(drop=True)


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
