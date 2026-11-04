"""
Clean the remaining Illinois Report Card ("ILRC") Public Data Set sheets --
everything beyond General / General (2), which 02_clean.py already handles.

Covers: ELA/Math/Science proficiency + student growth percentile (both live
as columns within the ELAMathScience sheet -- no separate extraction needed),
the IAR-specific proficiency rate, PARCC (2017-18 predecessor to IAR), ACT,
SAT (the HS assessment ACT replaced in 2024-25), ISA, DLM / DLM-AA (alternate
assessment), CTE, Discipline, Finance, KIDS, SPED, and Teacher Out-of-Field.

Same convention as 02_clean.py: one combined CSV per sheet x grain
(district/school) across all years, school_year tagged, wide columns kept
as-is (no subgroup reshaping -- the dashboard picks columns at chart time).
Reuses 02_clean.py's split-column detection and drop-column logic so both
scripts treat "District" vs "School" rows identically.

Sheet names drift year to year (documented in the README and the Plan doc),
so each canonical category below lists its known aliases in priority order;
the first alias present in a given year's workbook is used, and a year
missing a sheet entirely is skipped (printed, not an error) -- most
categories are genuinely new (e.g. CTE starts 2021-22, KIDS starts 2023-24,
SPED/ACT as standalone sheets start 2024-25).

Reads:  illinois_report_card/data/raw/<school_year>.xlsx
Writes: illinois_report_card/data/clean/illinois_report_card_<tag>_district_clean.csv
        illinois_report_card/data/clean/illinois_report_card_<tag>_school_clean.csv

Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module

_clean02 = import_module("02_clean")
find_split_column = _clean02.find_split_column
DROP_FOR_DISTRICT = _clean02.DROP_FOR_DISTRICT
DROP_FOR_SCHOOL = _clean02.DROP_FOR_SCHOOL

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "clean"

# canonical output tag -> sheet-name aliases to try, in priority order.
# First alias found in a given year's workbook wins; a year with none of
# them is skipped for that tag.
SHEET_ALIASES: dict[str, list[str]] = {
    "elamathscience": ["ELAMathScience", "ELA Math Science", "ELA and Math"],
    "elamathscience2": ["ELAMathScience (2)", "ELA Math Science (2)"],
    "iar": ["IAR"],
    "iar2": ["IAR (2)"],
    "parcc": ["PARCC"],
    "act": ["ACT"],
    "sat": ["SAT"],
    "isa": ["ISA"],
    "dlm": ["DLM", "DLM-AA"],
    "dlm2": ["DLM (2)", "DLM-AA (2)"],
    "cte": ["CTE"],
    "cte2": ["CTE (2)"],
    "discipline": ["Discipline"],
    "finance": ["Finance", "Financial"],
    "kids": ["KIDS"],
    "sped": ["SPED"],
    "teacher_oof": ["TeacherOutofField", "TeacherOF"],
}


def resolve_sheet(wb_sheetnames: list[str], aliases: list[str]) -> str | None:
    for alias in aliases:
        if alias in wb_sheetnames:
            return alias
    return None


def split_district_school(raw_df: pd.DataFrame, school_year: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Same logic as 02_clean.py's split, duplicated here (not imported) so
    this script's behavior doesn't silently change if 02_clean.py's internal
    split function signature changes -- only the column lists/finder are
    shared.
    """
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


def clean_categories(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    raw_files = sorted(input_dir.glob("*.xlsx"), key=lambda f: f.stem, reverse=True)
    if not raw_files:
        raise ValueError(f"No .xlsx files in {input_dir}")

    summary: dict[str, list[str]] = {}

    for tag, aliases in SHEET_ALIASES.items():
        district_frames, school_frames = [], []
        years_found: list[str] = []

        for file_path in raw_files:
            school_year = file_path.stem  # e.g. "2024-2025"

            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheet_name = resolve_sheet(wb.sheetnames, aliases)
            if sheet_name is None:
                wb.close()
                continue
            wb.close()

            raw_df = pd.read_excel(file_path, sheet_name=sheet_name)
            district_df, school_df = split_district_school(raw_df, school_year)

            print(
                f"  [{school_year}] {tag} (sheet '{sheet_name}'): "
                f"{len(district_df)} district row(s), {len(school_df)} school row(s)"
            )
            years_found.append(school_year)

            if not district_df.empty:
                district_frames.append(district_df)
            if not school_df.empty:
                school_frames.append(school_df)

        if not years_found:
            print(f"[{tag}] none of {aliases} found in any year -- skipping")
            continue

        summary[tag] = years_found

        if district_frames:
            out = output_dir / f"illinois_report_card_{tag}_district_clean.csv"
            pd.concat(district_frames, ignore_index=True).to_csv(out, index=False)
            print(f"Wrote {out}")
        if school_frames:
            out = output_dir / f"illinois_report_card_{tag}_school_clean.csv"
            pd.concat(school_frames, ignore_index=True).to_csv(out, index=False)
            print(f"Wrote {out}")

    print("\n--- Coverage summary ---")
    for tag, years in summary.items():
        years_sorted = sorted(years)
        print(f"  {tag}: {years_sorted[0]} to {years_sorted[-1]} ({len(years_sorted)} year(s))")


if __name__ == "__main__":
    clean_categories()
