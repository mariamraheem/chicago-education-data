"""
Clean Illinois Report Card ("ILRC") Public Data Set workbooks.

Reads the "General" and "General (2)" sheets of every workbook in
illinois_report_card/data/raw/, splits each into district-level and
school-level rows, tags each with school_year, and writes one combined
clean CSV per sheet x grain across all years.

Reads:  illinois_report_card/data/raw/<school_year>.xlsx
Writes: illinois_report_card/data/clean/illinois_report_card_general_district_clean.csv
        illinois_report_card/data/clean/illinois_report_card_general_school_clean.csv
        illinois_report_card/data/clean/illinois_report_card_general2_district_clean.csv
        illinois_report_card/data/clean/illinois_report_card_general2_school_clean.csv

Adapted from Mariam Raheem's 02_ILRC general cleaning.py / 03_ILRC general
combining.py (merged into one step here, matching this repo's "one clean
step, one compile step" convention -- see docs/conventions.md). Two
substantive fixes from the original, both found while porting this:

  1. District/School split. The original detects the split column by
     taking the FIRST column whose name contains "type" (case-insensitive)
     and checking whether its value contains "District" vs "School". That
     happens to work for years with a column literally named "Type" (e.g.
     2022-2023: Type in {Statewide, District, School}) -- but "Type" isn't
     always the first "type"-ish column. In 2024-2025 the first match is
     "District Type" (the district's own governance category, e.g. "Unit
     District"), which every SCHOOL row also carries (its parent district's
     type) -- so the original logic misclassifies nearly all 2024-2025
     school rows as district rows (verified against the raw file: 4,675
     rows end up in "district" vs. the real 864; only 238 of 3,827 real
     school rows end up in "school"). This version instead prefers an
     exact "Type" column, then an exact "Level" column (ISBE added "Level"
     starting 2024-2025, with values Statewide/District/School -- it's
     the authoritative split for the years that have it), and only falls
     back to the fuzzy "contains 'type'" search for anything else.
  2. "General (2)" sheet doesn't exist in every workbook (e.g. it's absent
     in 2022-2023). The original reads it unconditionally for every file
     with no guard, which would raise on any year lacking it. This version
     skips a missing sheet and prints that it did.

Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "clean"

SHEETS = {
    "General": "general",
    "General (2)": "general2",
}

# Columns that only make sense for the other grain, dropped after the
# split (same intent as the original's drop_for_district / drop_for_school).
DROP_FOR_DISTRICT = ["Type", "Level", "School Name", "School Type", "Entity Type"]
DROP_FOR_SCHOOL = ["Type", "Level", "District Type", "District Size", "Entity Type"]


# --------------------------------------------------------------------------
# District / School split
# --------------------------------------------------------------------------

def find_split_column(columns: list[str]) -> str | None:
    """Pick the column that reliably distinguishes district vs. school rows.

    Prefers an exact "Type" column, then an exact "Level" column (ISBE's
    2024-2025+ addition), and only then the first column whose name merely
    contains "type" -- see the module docstring for why that fallback is
    unreliable on its own.
    """
    if "Type" in columns:
        return "Type"
    if "Level" in columns:
        return "Level"
    type_ish = [c for c in columns if "type" in c.lower()]
    return type_ish[0] if type_ish else None


def split_district_school(raw_df: pd.DataFrame, school_year: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split one sheet's raw rows into (district_df, school_df)."""
    split_col = find_split_column(list(raw_df.columns))

    if split_col is None:
        print(f"  [{school_year}] no Type/Level column found -- treating all rows as school-level")
        district_df = pd.DataFrame()
        school_df = raw_df.copy()
    else:
        values = raw_df[split_col].astype(str)
        district_df = raw_df[values.str.contains("District", case=False, na=False)].copy()
        school_df = raw_df[values.str.contains("School", case=False, na=False)].copy()

    district_df = district_df.drop(columns=[c for c in DROP_FOR_DISTRICT if c in district_df.columns])
    school_df = school_df.drop(columns=[c for c in DROP_FOR_SCHOOL if c in school_df.columns])

    if not district_df.empty:
        district_df.insert(0, "school_year", school_year)
    if not school_df.empty:
        school_df.insert(0, "school_year", school_year)

    return district_df, school_df


# --------------------------------------------------------------------------
# Run across all years
# --------------------------------------------------------------------------

def clean_illinois_report_cards(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    """Clean every raw workbook and write one combined CSV per sheet x grain."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    raw_files = sorted(input_dir.glob("*.xlsx"), key=lambda f: f.stem, reverse=True)
    if not raw_files:
        raise ValueError(f"No .xlsx files in {input_dir}")

    for sheet_name, output_tag in SHEETS.items():
        district_frames, school_frames = [], []

        for file_path in raw_files:
            school_year = file_path.stem  # e.g. "2024-2025"

            wb = openpyxl.load_workbook(file_path, read_only=True)
            if sheet_name not in wb.sheetnames:
                print(f"  [{school_year}] no '{sheet_name}' sheet -- skipping")
                wb.close()
                continue
            wb.close()

            raw_df = pd.read_excel(file_path, sheet_name=sheet_name)
            district_df, school_df = split_district_school(raw_df, school_year)

            print(
                f"  [{school_year}] {sheet_name}: "
                f"{len(district_df)} district row(s), {len(school_df)} school row(s)"
            )

            if not district_df.empty:
                district_frames.append(district_df)
            if not school_df.empty:
                school_frames.append(school_df)

        if district_frames:
            out = output_dir / f"illinois_report_card_{output_tag}_district_clean.csv"
            pd.concat(district_frames, ignore_index=True).to_csv(out, index=False)
            print(f"Wrote {out}")
        if school_frames:
            out = output_dir / f"illinois_report_card_{output_tag}_school_clean.csv"
            pd.concat(school_frames, ignore_index=True).to_csv(out, index=False)
            print(f"Wrote {out}")


if __name__ == "__main__":
    clean_illinois_report_cards()
