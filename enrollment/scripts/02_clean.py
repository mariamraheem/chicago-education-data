"""
Clean and combine CPS GENERAL and RACE 20th-day enrollment files.

Adapted from Mariam Raheem's Cleaning_enrollment_data.ipynb (the final,
regex-normalized version of the RACE cleaning cell). Logic is preserved;
paths are now repo-relative and the deprecated
`DataFrame.groupby(axis=1)` call is replaced with the non-deprecated
`.T.groupby(...).sum().T` equivalent.

Reads:  enrollment/data/raw/RACE*.xls*, enrollment/data/raw/GENERAL*.xls*
Writes: enrollment/data/clean/enrollment_race_clean.csv
        enrollment/data/clean/enrollment_general_clean.csv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "enrollment" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "enrollment" / "data" / "clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def clean_columns(cols):
    """Normalize column names: to string, strip, collapse whitespace."""
    new_cols = []
    for c in cols:
        if pd.isna(c):
            c = ""
        else:
            c = str(c).replace("\n", " ").strip()
            c = re.sub(r"\s+", " ", c)
        new_cols.append(c)
    return new_cols


def flatten_header(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten a two-level (year-format) header into a single row."""
    new_cols = []
    for t, b in df.columns:
        top = t if str(t) != "nan" else b
        new_col = f"{top}_{b}" if b not in ("", "Total") else top
        new_cols.append(new_col.replace("\n", " ").strip())
    df.columns = new_cols
    return df


# --------------------------------------------------------------------------
# RACE files
# --------------------------------------------------------------------------

RACE_SHEET_CANDIDATES = ["Educational Units", "School", "Schools", "All_Schools"]

RACE_COLUMN_MAP = {
    "School ID": "School_ID",
    "School Information_School ID": "School_ID",
    "Unnamed: 1_level_0_School ID": "School_ID",
    "School Name": "School_Name",
    "School Information_School Name": "School_Name",
    "Network": "Network",
    "School Information_Network": "Network",
    "Unnamed: 0_level_0_Network": "Network",
    "Year": "Year",
    "White_No": "White_n", "White_N": "White_n",
    "White_Pct": "White_pct", "White_%": "White_pct",
    "African American_No": "Black_n", "African American_N": "Black_n",
    "African American_Pct": "Black_pct", "African American_%": "Black_pct",
    "African  American_No": "Black_n", "African  American_N": "Black_n",
    "African  American_Pct": "Black_pct", "African  American_%": "Black_pct",
    "Black/African American_No": "Black_n", "Black/African American_Pct": "Black_pct",
    "Asian_No": "Asian_n", "Asian_N": "Asian_n",
    "Asian_Pct": "Asian_pct", "Asian_%": "Asian_pct",
    "Asian Pacific Islander_No": "Asian_n", "Asian Pacific Islander_Pct": "Asian_pct",
    "Asian  Pacific Islander_No": "Asian_n", "Asian  Pacific Islander_Pct": "Asian_pct",
    "Asian Pacific Isldr_N": "Asian_n", "Asian Pacific Isldr_%": "Asian_pct",
    "Asian/ Pac Isldr_N": "Asian_n", "Asian/ Pac Isldr_%": "Asian_pct",
    "Asian/ Pac Islander_N": "Asian_n", "Asian/ Pac Islander_%": "Asian_pct",
    "Asian/ Pacific Isldr_N": "Asian_n", "Asian/ Pacific Isldr_%": "Asian_pct",
    "Asian/ Pacific Islander_No": "Asian_n", "Asian/ Pacific Islander_Pct": "Asian_pct",
    "Asian/ Pacific Islander (Retired)_No": "Asian/Pacific Islander (Retired)_n",
    "Asian/ Pacific Islander (Retired)_Pct": "Asian/Pacific Islander (Retired)_pct",
    "Hispanic_No": "Hispanic_n", "Hispanic_N": "Hispanic_n",
    "Hispanic_Pct": "Hispanic_pct", "Hispanic_%": "Hispanic_pct",
    "Latinx_No": "Hispanic_n", "Latinx_Pct": "Hispanic_pct",
    "Multi- Hispanic_N": "Hispanic_n", "Multi- Hispanic_%": "Hispanic_pct",
    "Multi Hispanic_N": "Hispanic_n", "Multi Hispanic_%": "Hispanic_pct",
    "Mexican_N": "Mexican_n", "Mexican_%": "Mexican_pct",
    "Puerto Rican_N": "PuertoRican_n", "Puerto Rican_%": "PuertoRican_pct",
    "Puerto  Rican_N": "PuertoRican_n", "Puerto  Rican_%": "PuertoRican_pct",
    "Cuban_N": "Cuban_n", "Cuban_%": "Cuban_pct",
    "Other Hispanic_N": "OtherHispanic_n", "Other Hispanic_%": "OtherHispanic_pct",
    "Multiracial_No": "Multiracial_n", "Multiracial_Pct": "Multiracial_pct",
    "Multi-Racial_No": "Multiracial_n", "Multi-Racial_Pct": "Multiracial_pct",
    "Multi-Racial_N": "Multiracial_n", "Multi-Racial_%": "Multiracial_pct",
    "Multi Racial_N": "Multiracial_n", "Multi Racial_%": "Multiracial_pct",
    "Mulit-Racial_No": "Multiracial_n", "Mulit-Racial_Pct": "Multiracial_pct",
    "Native American/ Alaskan_No": "NativeAmerican_n", "Native American/ Alaskan_Pct": "NativeAmerican_pct",
    "Native American_No": "NativeAmerican_n", "Native American_Pct": "NativeAmerican_pct",
    "Native  American_No": "NativeAmerican_n", "Native  American_Pct": "NativeAmerican_pct",
    "Native American_N": "NativeAmerican_n", "Native American_%": "NativeAmerican_pct",
    "Native American/  Alaskan_No": "NativeAmerican_n", "Native American/  Alaskan_Pct": "NativeAmerican_pct",
    "Native  American_N": "NativeAmerican_n", "Native  American_%": "NativeAmerican_pct",
    "Hawaiian/ Pacific Islander_No": "Hawaiian/Pacific Islander_n",
    "Hawaiian/ Pacific Islander_Pct": "Hawaiian/Pacific Islander_pct",
    "Hawaiian/  Pacific Islander_No": "Hawaiian/Pacific Islander_n",
    "Hawaiian/  Pacific Islander_Pct": "Hawaiian/Pacific Islander_pct",
    "Not Available_No": "Not Available_n", "Not Available_Pct": "Not Available_pct",
    "Not  Available_No": "Not Available_n", "Not  Available_Pct": "Not Available_pct",
    "Not   Available_No": "Not Available_n", "Not   Available_Pct": "Not Available_pct",
    "Middle Eastern/Northern African_No": "MENA_n",
    "Middle Eastern/Northern African_Pct": "MENA_pct",
}

REORDER_COLUMNS = [
    "Year", "Network", "School_ID", "School_Name",
    "White_n", "White_pct", "Black_n", "Black_pct", "Asian_n", "Asian_pct",
    "NativeAmerican_n", "NativeAmerican_pct", "Hispanic_n", "Hispanic_pct",
    "Mexican_n", "Mexican_pct", "PuertoRican_n", "PuertoRican_pct",
    "Cuban_n", "Cuban_pct", "OtherHispanic_n", "OtherHispanic_pct",
    "MENA_n", "MENA_pct", "Multiracial_n", "Multiracial_pct",
    "Hawaiian/Pacific Islander_n", "Hawaiian/Pacific Islander_pct",
    "Asian/Pacific Islander (Retired)_n", "Asian/Pacific Islander (Retired)_pct",
    "Not Available_n", "Not Available_pct",
]


def detect_race_sheet(file: Path, sheet_names=None):
    xl = pd.ExcelFile(file)
    for s in xl.sheet_names:
        if sheet_names and any(sn.lower() in s.lower() for sn in sheet_names):
            return s
    return None


def read_race(file: Path, sheet_names=None) -> pd.DataFrame:
    parts = file.stem.split("_")
    year = parts[1] if len(parts) >= 2 else "Unknown"
    sheet = detect_race_sheet(file, sheet_names)

    first_row = pd.read_excel(file, nrows=1, header=None)
    first_cell = str(first_row.iloc[0, 0]).strip() if not pd.isna(first_row.iloc[0, 0]) else ""
    header_rows = [1, 2] if first_cell.startswith("* Data was revised") else [0, 1]

    df = pd.read_excel(file, sheet_name=sheet, header=header_rows)
    df = flatten_header(df)
    df.columns = clean_columns(df.columns)
    df.ffill(axis=0, inplace=True)
    df["Year"] = year
    return df


def standardize_race_columns(cols):
    new_cols, keep_cols = [], []
    for c in cols:
        c_norm = re.sub(r"\s+", " ", c).strip()
        for key, val in RACE_COLUMN_MAP.items():
            if c_norm == re.sub(r"\s+", " ", key).strip():
                new_cols.append(val)
                keep_cols.append(c)
                break
    return keep_cols, new_cols


def clean_race_files() -> pd.DataFrame:
    race_dfs = []
    for file in sorted(INPUT_DIR.glob("RACE*.xls*")):
        try:
            race_dfs.append(read_race(file, sheet_names=RACE_SHEET_CANDIDATES))
        except Exception as e:  # noqa: BLE001
            print(f"!! Error processing {file.name}: {e}")

    if not race_dfs:
        print("No RACE*.xls* files found in enrollment/data/raw - skipping.")
        return pd.DataFrame()

    df_race = pd.concat(race_dfs, ignore_index=True)
    df_race.columns = [re.sub(r"\s+", " ", c).strip() for c in df_race.columns]

    keep_cols, new_cols = standardize_race_columns(df_race.columns)
    df_race_clean = df_race[keep_cols].copy()
    df_race_clean.columns = new_cols

    # Collapse duplicate standardized column names (different years map to the
    # same target name) by summing across them, without the deprecated
    # groupby(axis=1) call.
    df_race_clean = df_race_clean.T.groupby(level=0).sum(min_count=1).T

    df_race_clean = df_race_clean[~df_race_clean["School_Name"].astype(str).str.contains(
        "District Total", case=False, na=False)]
    df_race_clean = df_race_clean[~df_race_clean["Network"].astype(str).str.contains(
        "Total", case=False, na=False)]

    current_cols = [c for c in REORDER_COLUMNS if c in df_race_clean.columns]
    df_race_clean = df_race_clean[current_cols]
    return df_race_clean


# --------------------------------------------------------------------------
# GENERAL files
# --------------------------------------------------------------------------

YEAR_RENAME_MAP = {
    "2006-2007": {"Unit": "School_ID", "School": "School_Name", "02'": "2"},
    "2007-2008": {"Unit": "School_ID", "School": "School_Name"},
}

GENERAL_COLS_TO_KEEP = [
    "Year", "School ID", "School Name", "Network", "Governance", "School Type",
    "Community Area", "Unit", "School", "Total", "PE", "PK", "K",
]


def detect_header(file: Path, n: int = 10) -> int:
    """Find the row containing both 'School ID' and 'School Name'."""
    for i in range(n):
        df = pd.read_excel(file, nrows=1, header=None, skiprows=i)
        row = [str(c).strip() if not pd.isna(c) else "" for c in df.iloc[0]]
        if "School ID" in row and "School Name" in row:
            return i
    return 0


def clean_general_files() -> pd.DataFrame:
    general_dfs = []
    for file in sorted(INPUT_DIR.glob("GENERAL*.xls*")):
        try:
            header_row = detect_header(file)
            df = pd.read_excel(file, header=header_row)
            df.columns = clean_columns(df.columns)
            df.columns = [str(int(c)) if str(c).isdigit() else c for c in df.columns]

            year = file.stem.split("_")[1]
            df["Year"] = year

            if year in YEAR_RENAME_MAP:
                df.rename(columns=YEAR_RENAME_MAP[year], inplace=True)

            general_dfs.append(df)
        except Exception as e:  # noqa: BLE001
            print(f"!! Error processing {file.name}: {e}")

    if not general_dfs:
        print("No GENERAL*.xls* files found in enrollment/data/raw - skipping.")
        return pd.DataFrame()

    df_general = pd.concat(general_dfs, ignore_index=True)

    grade_map = {str(i): f"Grade {i}" for i in range(1, 13)}
    df_general.rename(columns=grade_map, inplace=True)

    cols_to_keep = list(GENERAL_COLS_TO_KEEP) + list(grade_map.values())
    df_general_clean = df_general[[c for c in cols_to_keep if c in df_general.columns]]
    df_general_clean = df_general_clean[~df_general_clean["School Name"].astype(str).str.contains(
        "District Total", case=False, na=False)]
    return df_general_clean


if __name__ == "__main__":
    race_clean = clean_race_files()
    general_clean = clean_general_files()

    if not race_clean.empty:
        out = OUTPUT_DIR / "enrollment_race_clean.csv"
        race_clean.to_csv(out, index=False)
        print(f"Wrote {out} ({len(race_clean)} rows)")

    if not general_clean.empty:
        out = OUTPUT_DIR / "enrollment_general_clean.csv"
        general_clean.to_csv(out, index=False)
        print(f"Wrote {out} ({len(general_clean)} rows)")
