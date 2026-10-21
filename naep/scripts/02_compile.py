"""
Compile the raw NAEP API pulls into tidy tables.

Reads every naep/data/raw/naep_*.json written by 01_scrape.py and writes:
  - naep_scores_long.csv: one row per year x jurisdiction x subject x grade x student group
  - naep_scores_wide.csv: same layout as the hand-built NAEP_Compiled_Wide.xlsx
    (Year, Jurisdiction, Subject, Grade, then one column per student group),
    so the Shiny app can read it without changes

Group labels are matched on the API's label text, not its numeric codes. Any label
we don't recognize stays in the long file (group = the API label) and is listed
at the end of the run, but is left out of the wide file.

Scores the API marks as not displayable (reporting standards not met) are left
blank -- never filled in.

Inputs:  naep/data/raw/naep_*.json
Outputs: naep/data/clean/naep_scores_long.csv, naep/data/clean/naep_scores_wide.csv
Run:     python naep/scripts/02_compile.py
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pandas as pd

# ---- Config -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "naep" / "data" / "raw"
CLEAN_DIR = REPO_ROOT / "naep" / "data" / "clean"
LONG_OUT = CLEAN_DIR / "naep_scores_long.csv"
WIDE_OUT = CLEAN_DIR / "naep_scores_wide.csv"

# fields we need in every API result row. the docs only promise "value" and
# "varValue", so check these up front instead of finding out from a column of NaNs.
REQUIRED_FIELDS = ["year", "jurisdiction", "varValue", "value"]

SUBJECT_NAMES = {"mathematics": "Mathematics", "reading": "Reading"}

GROUP_TYPES = {
    "TOTAL": "All students",
    "SDRACE": "Race/Ethnicity",
    "GENDER": "Sex",
    "SLUNCH3": "Econ. Disadvantage",
    "LEP": "English Learner",
    "IEP": "Disability Status",
}

# API label (lowercased) -> column name in the hand-built workbook / app.
# matched on label text on purpose. the label variants for LEP/IEP/SLUNCH3
# aren't in the API docs, so check the "unrecognized labels" printout after
# the first real run and add any missing ones here.
GROUP_LABELS = {
    "SDRACE": {
        "white": "White",
        "black": "Black",
        "hispanic": "Hispanic",
        "asian/pacific islander": "Asian/Pacific Islander",
        "american indian/alaska native": "American Indian/Alaska Native",
        "two or more races": "Two or more races",
    },
    "GENDER": {"male": "Male", "female": "Female"},
    "SLUNCH3": {
        "eligible": "Economically disadvantaged",
        "not eligible": "Not economically disadvantaged",
        "info not available": "Information not available",
        "information not available": "Information not available",
    },
    "LEP": {
        "ell": "ELL",
        "not ell": "Not ELL",
        "identified as english learners": "ELL",
        "not identified as english learners": "Not ELL",
    },
    "IEP": {
        "identified as students with disabilities": "Identified as students with disabilities",
        "not identified as students with disabilities": "Not identified as students with disabilities",
        "sd": "Identified as students with disabilities",
        "not sd": "Not identified as students with disabilities",
    },
}

# column order of the hand-built workbook
WIDE_COLUMNS = [
    "All students", "White", "Black", "Hispanic", "Asian/Pacific Islander",
    "American Indian/Alaska Native", "Two or more races", "Male", "Female",
    "Economically disadvantaged", "Not economically disadvantaged",
    "Information not available", "ELL", "Not ELL",
    "Identified as students with disabilities",
    "Not identified as students with disabilities",
]


# ---- Helpers ------------------------------------------------------------------

def load_jurisdictions() -> dict:
    """Jurisdiction code -> name, from 01_scrape.py so it lives in one place."""
    spec = importlib.util.spec_from_file_location("naep_scrape", Path(__file__).parent / "01_scrape.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.JURISDICTIONS


def parse_year(v) -> int | None:
    """API years can come back as 2024 or '2024R3' -- keep the 4-digit year."""
    m = re.match(r"(\d{4})", str(v))
    return int(m.group(1)) if m else None


def group_name(variable: str, label: str) -> tuple[str, bool]:
    """Map an API label to the workbook column name. Returns (name, recognized)."""
    if variable == "TOTAL":
        return "All students", True
    key = re.sub(r"\s+", " ", str(label).strip().lower())
    name = GROUP_LABELS.get(variable, {}).get(key)
    return (name, True) if name else (str(label).strip(), False)


# ---- Steps --------------------------------------------------------------------

def load_raw(juris: dict) -> pd.DataFrame:
    """Read every raw JSON file into one long table."""
    files = sorted(RAW_DIR.glob("naep_*.json"))
    if not files:
        raise SystemExit(f"no raw files in {RAW_DIR} -- run 01_scrape.py first")

    records = []
    for f in files:
        d = json.loads(f.read_text())
        rows = d.get("result", [])
        if not rows:
            print(f"  {f.name}: 0 rows (check request_log in the file)")
            continue
        missing = [k for k in REQUIRED_FIELDS if k not in rows[0]]
        if missing:
            raise SystemExit(f"{f.name}: API rows are missing {missing}. "
                             f"fields returned: {sorted(rows[0].keys())}")
        for r in rows:
            label = r.get("varValueLabel", r["varValue"])
            name, recognized = group_name(d["variable"], label)
            displayable = r.get("isStatDisplayable", 1)
            records.append({
                "year": parse_year(r["year"]),
                "jurisdiction_code": r["jurisdiction"],
                "jurisdiction": juris.get(r["jurisdiction"], r.get("jurisLabel", r["jurisdiction"])),
                "subject": SUBJECT_NAMES[d["subject"]],
                "grade": int(d["grade"]),
                "group_type": GROUP_TYPES[d["variable"]],
                "group": name,
                "api_variable": d["variable"],
                "api_value": r["varValue"],
                "api_label": label,
                "recognized_group": recognized,
                # not displayable = reporting standard not met -> leave blank
                "average_scale_score": r["value"] if displayable not in (0, "0", False) else None,
                "is_displayable": displayable,
                "error_flag": r.get("errorFlag"),
            })
        print(f"  {f.name}: {len(rows)} rows")
    return pd.DataFrame(records)


def check_long(df: pd.DataFrame) -> pd.DataFrame:
    """Sanity checks: duplicates, blanks, unrecognized labels."""
    keys = ["year", "jurisdiction", "subject", "grade", "group_type", "group"]
    dupes = df.duplicated(keys, keep=False)
    if dupes.any():
        # shouldn't happen -- would mean two API labels collapsed onto one group
        print(f"WARNING: {dupes.sum()} duplicate rows on {keys}; first few:")
        print(df.loc[dupes, keys + ["api_label", "average_scale_score"]].head(10).to_string())

    blank = df["average_scale_score"].isna().sum()
    print(f"\nlong table: {len(df):,} rows, {blank:,} blank (not displayable / not reported)")

    unrec = df.loc[~df["recognized_group"], ["api_variable", "api_label"]].drop_duplicates()
    if len(unrec):
        print("unrecognized group labels (kept in long file, left out of wide):")
        print(unrec.to_string(index=False))
    return df


def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to the hand-built workbook layout."""
    keep = df[df["recognized_group"]]
    wide = keep.pivot_table(index=["year", "jurisdiction", "subject", "grade"],
                            columns="group", values="average_scale_score", aggfunc="first")
    wide = wide.reindex(columns=WIDE_COLUMNS)
    wide = wide.dropna(how="all").reset_index()
    wide = wide.rename(columns={"year": "Year", "jurisdiction": "Jurisdiction",
                                "subject": "Subject", "grade": "Grade"})
    wide = wide.sort_values(["Year", "Jurisdiction", "Subject", "Grade"])
    print(f"wide table: {len(wide):,} rows "
          f"({wide['Jurisdiction'].nunique()} jurisdictions, {wide['Year'].min()}-{wide['Year'].max()})")
    return wide


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    juris = load_jurisdictions()
    long = check_long(load_raw(juris))
    long.sort_values(["year", "jurisdiction", "subject", "grade", "group_type", "group"]).to_csv(LONG_OUT, index=False)
    to_wide(long).to_csv(WIDE_OUT, index=False)
    print(f"\nwrote {LONG_OUT.relative_to(REPO_ROOT)} and {WIDE_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
