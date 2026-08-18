"""
Clean and combine CPS school budget workbooks -- both "District Managed"
schools and "Charter, Contract, ALOP" schools, CPS's two per-year budget
overview files.

This cleaner uses a generic, defensive approach rather than assuming any
particular CPS column layout up front:

  1. For every sheet in every DISTRICT_MANAGED_*.xlsx / CHARTER_CONTRACT_ALOP_*.xlsx
     file, auto-detect the header row as the row (within the first 15) with
     the most non-blank cells - a reasonable heuristic for government
     spreadsheets that start with a title/note row or two.
  2. Flatten any multi-level header pandas detects, normalize column names.
  3. Tag every row with its source Year, source file, and sheet name so nothing
     is silently conflated across years/sheets that may not actually line up.
  4. Concatenate everything into one long table.
  5. Coalesce the school-identifier column: district-managed sheets call it
     "School Name", charter/contract/ALOP sheets call it "Name" -- both get
     folded into a single "School Name" column so downstream filtering
     (03_build_dashboard_data.py) and the dashboard table treat every school
     the same way regardless of which workbook it came from.

Each workbook also contains a legend/definitions sheet ("Overview" /
"Overview Definitions") that's just field-name -> description text, not
budget data -- 03_build_dashboard_data.py drops those rows (anything with no
School Name) rather than this script, so _column_report.csv still shows you
everything that was actually found, legend sheet included.

Reads:  budget/data/raw/DISTRICT_MANAGED_*.xls*
        budget/data/raw/CHARTER_CONTRACT_ALOP_*.xls*
Writes: budget/data/clean/budget_school_funding_clean.csv
        budget/data/clean/_column_report.csv (what columns were found, by year/sheet)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "budget" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "budget" / "data" / "clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_HEADER_SCAN_ROWS = 15


def clean_columns(cols) -> list[str]:
    new_cols = []
    for c in cols:
        if pd.isna(c):
            c = ""
        else:
            c = str(c).replace("\n", " ").strip()
            c = re.sub(r"\s+", " ", c)
        new_cols.append(c)
    return new_cols


def flatten_if_multiindex(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        new_cols = []
        for tup in df.columns:
            parts = [str(p).strip() for p in tup if str(p).strip() and str(p) != "nan"]
            new_cols.append("_".join(parts) if parts else "")
        df.columns = new_cols
    return df


def detect_header_row(file: Path, sheet_name) -> int:
    """Pick the row (within the first N) with the most non-blank cells."""
    preview = pd.read_excel(file, sheet_name=sheet_name, header=None, nrows=MAX_HEADER_SCAN_ROWS)
    non_blank_counts = preview.notna().sum(axis=1)
    return int(non_blank_counts.idxmax())


def extract_year(filename: str) -> str:
    m = re.search(r"(20\d{2})", filename)
    return m.group(1) if m else "Unknown"


def read_budget_workbook(file: Path) -> list[pd.DataFrame]:
    year = extract_year(file.stem)
    frames = []

    try:
        xl = pd.ExcelFile(file)
    except Exception as e:  # noqa: BLE001
        print(f"!! Could not open {file.name}: {e}")
        return frames

    for sheet_name in xl.sheet_names:
        try:
            header_row = detect_header_row(file, sheet_name)
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_row)
            df = flatten_if_multiindex(df)
            df.columns = clean_columns(df.columns)

            # Drop fully-blank columns/rows that often survive header detection
            df = df.dropna(axis=1, how="all")
            df = df.dropna(axis=0, how="all")

            if df.empty:
                continue

            df["Year"] = year
            df["Source_File"] = file.name
            df["Source_Sheet"] = sheet_name
            frames.append(df)
        except Exception as e:  # noqa: BLE001
            print(f"!! Error reading {file.name} [{sheet_name}]: {e}")

    return frames


def build_column_report(frames: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for df in frames:
        year = df["Year"].iloc[0] if "Year" in df.columns and len(df) else "Unknown"
        sheet = df["Source_Sheet"].iloc[0] if "Source_Sheet" in df.columns and len(df) else "Unknown"
        src = df["Source_File"].iloc[0] if "Source_File" in df.columns and len(df) else "Unknown"
        for col in df.columns:
            if col in ("Year", "Source_File", "Source_Sheet"):
                continue
            rows.append({"Year": year, "Source_File": src, "Sheet": sheet, "Column": col})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    all_frames = []
    files = sorted(INPUT_DIR.glob("DISTRICT_MANAGED_*.xls*")) + sorted(
        INPUT_DIR.glob("CHARTER_CONTRACT_ALOP_*.xls*")
    )
    for file in files:
        print(f"Reading {file.name} ...")
        all_frames.extend(read_budget_workbook(file))

    if not all_frames:
        print("No DISTRICT_MANAGED_*.xls* or CHARTER_CONTRACT_ALOP_*.xls* files "
              "found in budget/data/raw - skipping.")
    else:
        combined = pd.concat(all_frames, ignore_index=True, sort=False)

        # Charter/Contract/ALOP sheets call the school-identifier column
        # "Name" instead of "School Name" -- fold them into one column so a
        # school isn't split across two differently-named columns depending
        # on which workbook it came from.
        if "Name" in combined.columns:
            if "School Name" in combined.columns:
                combined["School Name"] = combined["School Name"].fillna(combined["Name"])
            else:
                combined["School Name"] = combined["Name"]
            combined = combined.drop(columns=["Name"])

        out = OUTPUT_DIR / "budget_school_funding_clean.csv"
        combined.to_csv(out, index=False)
        print(f"Wrote {out} ({len(combined)} rows, {len(combined.columns)} columns)")

        report = build_column_report(all_frames)
        report_out = OUTPUT_DIR / "_column_report.csv"
        report.to_csv(report_out, index=False)
        print(f"Wrote {report_out} - review this to see what columns were actually "
              f"found per year/sheet, then tighten the standardization above.")
