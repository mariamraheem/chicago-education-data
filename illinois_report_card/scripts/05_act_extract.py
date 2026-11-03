"""
Extract the ACT tab's data: CPS (District 299) vs. Illinois statewide trend
in the Grade 11 HS assessment ELA/Math/Science proficiency rate, plus the
ACT and SAT average scores each test era actually reports, 2017-18 through
2025-26.

Same rationale as 04_academic_achievement_extract.py for reading the raw
workbooks directly instead of the generic clean CSVs: the statewide total
row (Type/Level == "Statewide") is dropped by 02_clean.py / 03_clean_
categories.py's district/school split (matches neither "District" nor
"School" -- the same gap noted there). This script scans the SAT sheet
(2017-18 to 2023-24) and ACT sheet (2024-25 to 2025-26) for the CPS +
Statewide rows directly by RCDTS.

ISBE swapped the HS assessment from SAT to ACT starting 2024-25. The
proficiency RATE columns carry different names across that swap ("SAT ELA
Proficiency Rate" vs "HS Assessment ELA Proficiency Rate") but are the same
0-100% scale measuring the same thing (% of 11th graders proficient on
whichever HS assessment is current), so ela_proficiency/math_proficiency
are treated as one continuous series with an era split at the swap, same
pattern as the IAR/PARCC cut-score reset on the Academic Achievement tab.
The average SCORE columns ("SAT Reading/Math Average Score" vs "ACT
ELA/Math/Science Average Score") are NOT comparable across the swap --
different scales entirely (SAT ~200-800 per section, ACT ~1-36) -- so each
is kept as its own metric, present only in the years its own test existed
(None elsewhere), never spliced into one "score" series.

Writes: illinois_report_card/data/dashboard/act.json
  {
    "years": ["2017-2018", ..., "2025-2026"],
    "era_break_index": 6,            # index of first ACT-era year (2024-2025)
    "series": {
      "ela_proficiency": {"cps": [.. or null], "state": [..]},   # continuous, era-split
      "math_proficiency": {...},
      "science_proficiency": {...},   # ACT-era only, None before
      "sat_reading_score": {...},     # SAT-era only, None after
      "sat_math_score": {...},
      "act_ela_score": {...},         # ACT-era only, None before
      "act_math_score": {...},
      "act_science_score": {...}
    },
    "subgroups_latest_year": "2025-2026",
    "subgroups": {
      "ela_proficiency": {"Total": .., "White": .., ...},   # latest-year snapshot
      "math_proficiency": {...}
    },
    "subgroup_groups": {
      "race_ethnicity": [...], "sex": [...], "el_status": [...],
      "income_disability": [...], "other_populations": [...]
    },
    "subgroup_trends": {
      "ela_proficiency": {"Total": {"cps": [.. 9 years ..], "state": [..]}, "White": {...}, ...},
      "math_proficiency": {...}
    }
  }

Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

import json
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "illinois_report_card" / "data" / "dashboard"

CPS_RCDTS_CANDIDATES = {"15-016-2990-25-0000", "150162990250000"}
STATEWIDE_RCDTS_CANDIDATES = {"65-000-0000-80-0000", "650000000800000"}

# metric key -> list of aliases to try (first sheet/alias found wins). The
# proficiency-rate metrics list BOTH the SAT-era and ACT-era column name so
# the same metric key resolves across the assessment swap; the score
# metrics list only their own era's name, so they come back None outside it.
METRICS: dict[str, list[str]] = {
    "ela_proficiency": ["SAT ELA Proficiency Rate", "HS Assessment ELA Proficiency Rate"],
    "math_proficiency": ["SAT Math Proficiency Rate", "HS Assessment Math Proficiency Rate"],
    "science_proficiency": ["HS Assessment Science Proficiency Rate"],
    # 2018-19 uses "SAT Reading/Math Average" (no "Score" suffix); every
    # later SAT year uses "...Average Score". 2017-18's SAT sheet reports
    # only performance-level percentages (Level 1-4), no average score at
    # all -- a genuine gap in that first year, not a naming drift, so no
    # alias recovers it and it correctly comes back None.
    "sat_reading_score": ["SAT Reading Average Score", "SAT Reading Average"],
    "sat_math_score": ["SAT Math Average Score", "SAT Math Average"],
    "act_ela_score": ["ACT ELA Average Score - Grade 11"],
    "act_math_score": ["ACT Math Average Score - Grade 11"],
    "act_science_score": ["ACT Science Average Score - Grade 11"],
}

# Subgroup label -> column suffix, as it appears after " - " on the
# proficiency-rate columns. Confirmed present/absent by direct header scan
# of the SAT sheet (2023-24) and ACT sheet (2025-26): SAT has no "Former
# EL", "Non Binary" or "MENA" breakout -- those are ACT-era additions, same
# as on Academic Achievement. find_subgroup_columns() only includes a label
# if its column actually exists that year, so this degrades gracefully.
SUBGROUP_GROUPS: dict[str, dict[str, str]] = {
    "race_ethnicity": {
        "White": "White",
        "Black or African American": "Black or African American",
        "Hispanic or Latino": "Hispanic or Latino",
        "Asian": "Asian",
        "American Indian or Alaska Native": "American Indian or Alaska Native",
        "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Islander",
        "Two or More Races": "Two or More Races",
        "MENA": "MENA",
    },
    "sex": {
        "Male": "Male",
        "Female": "Female",
        "Non Binary": "Non Binary",
    },
    "el_status": {
        "EL": "EL",
        "Former EL": "Former EL",
    },
    "income_disability": {
        "Low Income": "Low Income",
        "CWD": "CWD",
        "IEP": "IEP",
    },
    "other_populations": {
        "Youth In Care": "Youth In Care",
        "Homeless": "Homeless",
        "Migrant": "Migrant",
        "Military": "Military",
    },
}

SUBGROUP_SUFFIXES: dict[str, str | None] = {"Total": None}
for _grp in SUBGROUP_GROUPS.values():
    SUBGROUP_SUFFIXES.update(_grp)

# The two metrics we pull subgroup trends for -- the only ones with
# subgroup breakdown columns in both the SAT and ACT sheets. Values are the
# SAME alias lists as in METRICS (not a single fixed alias) because the
# column name itself changes across the assessment swap.
SUBGROUP_TREND_METRICS: dict[str, list[str]] = {
    "ela_proficiency": METRICS["ela_proficiency"],
    "math_proficiency": METRICS["math_proficiency"],
}


def find_metric_column(wb: openpyxl.Workbook, aliases: list[str]) -> tuple[str, int, str] | None:
    """Return (sheet_name, col_index, matched_alias) for the exact "Total"
    column of the first metric alias found in any sheet, searching sheets
    in workbook order. The "Total" variant is the bare alias (no " - Total"
    needed) when the column has no subgroup breakdown, else "<alias> -
    Total". matched_alias is returned (not just the sheet) because a
    metric's alias list can span an assessment swap -- the caller needs to
    know which alias actually matched to look up subgroup columns correctly.
    """
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for alias in aliases:
            if alias in header:
                return sheet_name, header.index(alias), alias
            total_variant = f"{alias} - Total"
            if total_variant in header:
                return sheet_name, header.index(total_variant), alias
    return None


def find_subgroup_columns(wb: openpyxl.Workbook, sheet_name: str, alias: str) -> dict[str, int]:
    """Map subgroup label -> column index within the given sheet, for every
    SUBGROUP_SUFFIXES entry that exists as "<alias> - <suffix>" (or bare
    <alias> for Total).
    """
    ws = wb[sheet_name]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    out: dict[str, int] = {}
    for label, suffix in SUBGROUP_SUFFIXES.items():
        if suffix is None:
            # "Total": try the bare alias first (years/sheets with no
            # subgroup breakdown at all use this), then "<alias> - Total"
            # (years with a breakdown still carry a separate Total column
            # under that suffixed name rather than duplicating the bare one
            # -- true for the ACT/SAT sheets, unlike ELAMathScience/IAR).
            if alias in header:
                out[label] = header.index(alias)
            elif f"{alias} - Total" in header:
                out[label] = header.index(f"{alias} - Total")
            continue
        col_name = f"{alias} - {suffix}"
        if col_name in header:
            out[label] = header.index(col_name)
    return out


def read_rows(wb: openpyxl.Workbook, sheet_name: str, col_indices: dict[str, int]) -> dict[str, tuple[float | None, float | None]]:
    """Scan the sheet once for the CPS and Statewide rows, returning
    {label: (cps_value, state_value)} for every column in col_indices.
    RCDTS-only matching (no name-contains fallback) -- see
    04_academic_achievement_extract.py's read_rows for why that fallback is
    unsafe (every CPS school row shares the district's name).
    """
    ws = wb[sheet_name]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    rcdts_idx = header.index("RCDTS")

    cps_row, state_row = None, None
    for row in ws.iter_rows(min_row=2, values_only=True):
        rcdts = str(row[rcdts_idx]) if row[rcdts_idx] is not None else ""
        if rcdts in CPS_RCDTS_CANDIDATES:
            cps_row = row
        elif rcdts in STATEWIDE_RCDTS_CANDIDATES:
            state_row = row

    out = {}
    for label, idx in col_indices.items():
        cps_val = cps_row[idx] if cps_row is not None else None
        state_val = state_row[idx] if state_row is not None else None
        out[label] = (_to_float(cps_val), _to_float(state_val))
    return out


def _to_float(val: object) -> float | None:
    """ISBE stores these rate/score columns as a plain float in some years
    and as a string in others; suppressed/non-numeric cells use markers
    like "*" or "N/A". Normalize all of that to float | None.
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except ValueError:
            return None
    return None


def extract_act(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    years = sorted(p.stem for p in input_dir.glob("*.xlsx"))
    # Index of the LAST pre-break year (2023-2024) -- the break falls
    # between this index and the next, same convention as Academic
    # Achievement's eraBreakIndex (not the first post-break year).
    era_break_index = next(i for i, y in enumerate(years) if y >= "2024-2025") - 1

    series: dict[str, dict[str, list[float | None]]] = {
        key: {"cps": [], "state": []} for key in METRICS
    }
    subgroup_trends: dict[str, dict[str, dict[str, list[float | None]]]] = {
        metric_key: {label: {"cps": [], "state": []} for label in SUBGROUP_SUFFIXES}
        for metric_key in SUBGROUP_TREND_METRICS
    }

    for year in years:
        wb = openpyxl.load_workbook(input_dir / f"{year}.xlsx", read_only=True)
        print(f"[{year}] scanning {len(wb.sheetnames)} sheets for metric columns...")

        by_sheet: dict[str, dict[str, int]] = {}
        sheet_for_metric: dict[str, tuple[str, str]] = {}  # metric_key -> (sheet_name, matched_alias)
        for metric_key, aliases in METRICS.items():
            found = find_metric_column(wb, aliases)
            if found is None:
                series[metric_key]["cps"].append(None)
                series[metric_key]["state"].append(None)
                print(f"  {metric_key}: not found")
                continue
            sheet_name, col_idx, matched_alias = found
            by_sheet.setdefault(sheet_name, {})[metric_key] = col_idx
            sheet_for_metric[metric_key] = (sheet_name, matched_alias)

        for sheet_name, col_indices in by_sheet.items():
            values = read_rows(wb, sheet_name, col_indices)
            for metric_key, (cps_val, state_val) in values.items():
                series[metric_key]["cps"].append(cps_val)
                series[metric_key]["state"].append(state_val)
                print(f"  {metric_key} (sheet '{sheet_name}'): CPS={cps_val}, IL={state_val}")

        for metric_key in SUBGROUP_TREND_METRICS:
            found = sheet_for_metric.get(metric_key)
            if found is None:
                for label in SUBGROUP_SUFFIXES:
                    subgroup_trends[metric_key][label]["cps"].append(None)
                    subgroup_trends[metric_key][label]["state"].append(None)
                continue
            sheet_name, matched_alias = found
            col_indices = find_subgroup_columns(wb, sheet_name, matched_alias)
            values = read_rows(wb, sheet_name, col_indices)
            for label in SUBGROUP_SUFFIXES:
                cps_val, state_val = values.get(label, (None, None))
                subgroup_trends[metric_key][label]["cps"].append(cps_val)
                subgroup_trends[metric_key][label]["state"].append(state_val)

        wb.close()

    latest_year = years[-1]
    subgroup_snapshot: dict[str, dict[str, float | None]] = {
        metric_key: {label: trends["cps"][-1] for label, trends in by_label.items()}
        for metric_key, by_label in subgroup_trends.items()
    }

    out = {
        "years": years,
        "era_break_index": era_break_index,
        "series": series,
        "subgroups_latest_year": latest_year,
        "subgroups": subgroup_snapshot,
        "subgroup_groups": {
            group_key: list(labels.keys()) for group_key, labels in SUBGROUP_GROUPS.items()
        },
        "subgroup_trends": subgroup_trends,
    }
    out_path = output_dir / "act.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    extract_act()
