"""
Clean and combine CPS "District Managed Funds" budget workbooks.

IMPORTANT - read this before relying on the output:
This cleaner was written without ever being able to open a real CPS budget
workbook (the sandbox that built this pipeline can't reach cps.edu, so the
actual FY2026/FY2027 "district managed" files were never inspected). Rather
than guess at CPS's exact column names the way the enrollment cleaners can
(those were adapted from Mariam's own notebooks, which *had* seen the real
files), this script uses a generic, defensive approach:

  1. For every sheet in every DISTRICT_MANAGED_*.xlsx file, auto-detect the
     header row as the row (within the first 15) with the most non-blank
     cells - a reasonable heuristic for government spreadsheets that start
     with a title/note row or two.
  2. Flatten any multi-level header pandas detects, normalize column names.
  3. Tag every row with its source Year, source file, and sheet name so nothing
     is silently conflated across years/sheets that may not actually line up.
  4. Concatenate everything into one long table for a first look.

Treat enrollment/data/clean output as ground truth quality (it mirrors
Mariam's validated notebooks); treat this budget cleaner's output as a
first-pass scaffold. After the first real GitHub Actions run downloads and
processes the actual files, inspect
budget/data/clean/district_managed_funds_clean.csv and
budget/data/clean/_column_report.csv (also written below) and tighten the
column-name standardization the same way enrollment/scripts/clean_general_race.py
does, once the real headers are known.

Reads:  budget/data/raw/DISTRICT_MANAGED_*.xls*
Writes: budget/data/clean/district_managed_funds_clean.csv
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


def read_district_managed_file(file: Path) -> list[pd.DataFrame]:
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
    for file in sorted(INPUT_DIR.glob("DISTRICT_MANAGED_*.xls*")):
        print(f"Reading {file.name} ...")
        all_frames.extend(read_district_managed_file(file))

    if not all_frames:
        print("No DISTRICT_MANAGED_*.xls* files found in budget/data/raw - skipping.")
    else:
        combined = pd.concat(all_frames, ignore_index=True, sort=False)
        out = OUTPUT_DIR / "district_managed_funds_clean.csv"
        combined.to_csv(out, index=False)
        print(f"Wrote {out} ({len(combined)} rows, {len(combined.columns)} columns)")

        report = build_column_report(all_frames)
        report_out = OUTPUT_DIR / "_column_report.csv"
        report.to_csv(report_out, index=False)
        print(f"Wrote {report_out} - review this to see what columns were actually "
              f"found per year/sheet, then tighten the standardization above.")
