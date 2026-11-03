"""
Extract the Academic Achievement tab's data: CPS (District 299) vs. Illinois
statewide trend in ELA/Math/Science proficiency, ELA/Math growth percentile,
and the IAR-specific ELA/Math proficiency rate, 2017-18 through 2025-26.

Why a dedicated script instead of reading the generic clean CSVs from
02_clean.py / 03_clean_categories.py: growth percentile in particular moves
sheet to sheet almost every year (ELA and Math -> ELA Math Science -> IAR
(2) -> IAR), and the statewide total row is dropped by both of those
scripts' district/school split (its Type/Level value is "Statewide", which
matches neither "District" nor "School" -- a real gap in that pipeline,
noted in the README; TODO fix there too). This script scans every sheet in
each year's workbook for columns that look like Proficiency/Growth metrics
rather than assuming a fixed sheet name, and reads the CPS + Statewide rows
directly by RCDTS/Level rather than going through the district/school split
at all.

Writes: illinois_report_card/data/dashboard/academic_achievement.json
  {
    "years": ["2017-2018", ..., "2025-2026"],
    "series": {
      "ela_proficiency": {"cps": [.. or null], "state": [..]},
      "math_proficiency": {...},
      "science_proficiency": {...},
      "ela_growth": {...},
      "math_growth": {...},
      "iar_ela_rate": {...},
      "iar_math_rate": {...},
      "dropout_rate": {...}
    },
    "subgroups_latest_year": "2025-2026",
    "subgroups": {
      "ela_proficiency": {"Total": .., "White": .., ...},   # latest-year snapshot, for the bar chart
      "math_proficiency": {...}
    },
    "subgroup_groups": {
      "race_ethnicity": ["White", "Black or African American", ...],
      "sex": [...], "el_status": [...], "income_disability": [...], "other_populations": [...]
    },
    "subgroup_trends": {
      "ela_proficiency": {
        "Total": {"cps": [.. 9 years ..], "state": [..]},
        "White": {"cps": [..], "state": [..]},
        ...  # every label in subgroup_groups, plus "Total"
      },
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

# metric key -> (column-name predicate, prefer-sheet-name-contains hints)
# Predicate matches the FULL column header text; we pick the first sheet
# (workbook sheet order) that has at least one match, then take the exact
# "Total" variant from that sheet.
METRICS: dict[str, list[str]] = {
    "ela_proficiency": ["% ELA Proficiency"],
    "math_proficiency": ["% Math Proficiency"],
    "science_proficiency": ["% Science Proficiency"],
    "ela_growth": ["ELA Growth Percentile", "ELA Growth All %"],
    "math_growth": ["Math Growth Percentile", "Math Growth  Percentile", "Math Growth All %"],
    "iar_ela_rate": ["IAR ELA Proficiency Rate"],
    "iar_math_rate": ["IAR Math Proficiency Rate"],
    "dropout_rate": ["High School Dropout Rate"],
}

# Subgroup label -> column suffix (as it appears after " - " in the
# ELAMathScience/ELA Math Science sheet's all-grades columns, e.g.
# "% ELA Proficiency - White"). Confirmed present/absent per year by direct
# header scan of 2017-18 (no breakdown at all), 2020-21, 2023-24 and 2025-26:
# "Non Binary" and "MENA" are not reportable until later years, "Youth in
# Care" starts 2023-24, "Former EL" starts 2025-26. find_subgroup_columns()
# only includes a label if its column actually exists in that year's sheet,
# so older years correctly come back with fewer subgroups rather than wrong
# data -- every group below degrades gracefully year to year.
#
# Grouped for the UI's "Breakdown" selector; group order here is display
# order. "Total" is kept out of every group (it's the main Trend view) but
# included separately below for the small-multiples panel set.
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
        "Children with Disabilities": "Children with Disabilities",
        "IEP": "IEP",
    },
    "other_populations": {
        "Youth in Care": "Youth in Care",
        "Homeless": "Homeless",
        "Migrant": "Migrant",
        "Military": "Military",
    },
}

# Flattened label -> suffix map used by find_subgroup_columns, plus "Total".
SUBGROUP_SUFFIXES: dict[str, str | None] = {"Total": None}
for _grp in SUBGROUP_GROUPS.values():
    SUBGROUP_SUFFIXES.update(_grp)

# A handful of ISBE column-name quirks that differ from the suffix spelling
# used everywhere else: the General sheet (dropout rate) spells "Non Binary"
# as "Non-binary", and in 2025-26 only, "- Homeless"/"- Migrant" lost their
# leading space ("Rate- Homeless" instead of "Rate - Homeless"). Tried in
# addition to the default "<alias> - <suffix>" / bare-alias form.
SUBGROUP_SUFFIX_ALT_COLUMNS: dict[str, list[str]] = {
    "Non Binary": ["{alias} - Non-binary"],
    "Homeless": ["{alias}- Homeless"],
    "Migrant": ["{alias}- Migrant"],
}

# The metrics we pull subgroup trends for (the ones with subgroup breakdown
# columns in the source sheets).
SUBGROUP_TREND_METRICS: dict[str, str] = {
    "ela_proficiency": "% ELA Proficiency",
    "math_proficiency": "% Math Proficiency",
    "dropout_rate": "High School Dropout Rate",
}


def find_metric_column(wb: openpyxl.Workbook, aliases: list[str]) -> tuple[str, int] | None:
    """Return (sheet_name, col_index) for the exact "Total" column of the
    first metric alias found in any sheet, searching sheets in workbook
    order. The "Total" variant is the bare alias (no " - <subgroup>" and no
    " Grade N" suffix) when subgroup columns exist, else just the alias
    itself (older years with no subgroup breakdown on this metric).
    """
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for alias in aliases:
            # exact match (no subgroup breakdown at all) or "<alias> - Total"
            if alias in header:
                return sheet_name, header.index(alias)
            total_variant = f"{alias} - Total"
            if total_variant in header:
                return sheet_name, header.index(total_variant)
    return None


def find_subgroup_columns(wb: openpyxl.Workbook, sheet_name: str, alias: str) -> dict[str, int]:
    """For the 2025-26 snapshot: map subgroup label -> column index within
    the given sheet, for every SUBGROUP_SUFFIXES entry that exists as
    "<alias> - <suffix>" (or bare <alias> for Total).
    """
    ws = wb[sheet_name]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    out: dict[str, int] = {}
    for label, suffix in SUBGROUP_SUFFIXES.items():
        if suffix is None:
            # Total: bare alias (older ELA/Math-style sheets) or "<alias> -
            # Total" (dropout rate, and newer sheets, always suffix Total
            # even though it has no other breakdown columns to disambiguate).
            if alias in header:
                out[label] = header.index(alias)
            elif f"{alias} - Total" in header:
                out[label] = header.index(f"{alias} - Total")
            continue
        candidates = [f"{alias} - {suffix}"]
        candidates += [tpl.format(alias=alias) for tpl in SUBGROUP_SUFFIX_ALT_COLUMNS.get(suffix, [])]
        for col_name in candidates:
            if col_name in header:
                out[label] = header.index(col_name)
                break
    return out


def read_rows(wb: openpyxl.Workbook, sheet_name: str, col_indices: dict[str, int]) -> dict[str, tuple[float | None, float | None]]:
    """Scan the sheet once for the CPS and Statewide rows, returning
    {label: (cps_value, state_value)} for every column in col_indices.
    """
    ws = wb[sheet_name]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    rcdts_idx = header.index("RCDTS")

    # RCDTS-only matching, no early break, no "District name contains Chicago
    # Public Schools" fallback: that fallback matched every individual CPS
    # SCHOOL row too (they share the district's name), so whichever school
    # row the scan happened to be on when it hit the break condition won --
    # silently wrong for any year where the Statewide row isn't near the top
    # of the sheet (confirmed on 2023-2024's ELAMathScience: Statewide
    # doesn't appear until row 1400+, so the "CPS" row kept being overwritten
    # by schools before Statewide was ever found). RCDTS is unique and
    # confirmed stable (dash and no-dash variants only) across all 9 years,
    # so exact match alone is reliable -- scan the whole sheet once.
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
    """ISBE stores these rate columns as a plain float in some years and as
    a string (e.g. "29.1") in others; suppressed/non-numeric cells use
    markers like "*" or "N/A". Normalize all of that to float | None.
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except ValueError:
            return None
    return None


def extract_academic_achievement(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    years = sorted(p.stem for p in input_dir.glob("*.xlsx"))
    series: dict[str, dict[str, list[float | None]]] = {
        key: {"cps": [], "state": []} for key in METRICS
    }
    # subgroup_trends[metric_key][subgroup_label] = {"cps": [...9 years...], "state": [...]}
    subgroup_trends: dict[str, dict[str, dict[str, list[float | None]]]] = {
        metric_key: {label: {"cps": [], "state": []} for label in SUBGROUP_SUFFIXES}
        for metric_key in SUBGROUP_TREND_METRICS
    }

    for year in years:
        wb = openpyxl.load_workbook(input_dir / f"{year}.xlsx", read_only=True)
        print(f"[{year}] scanning {len(wb.sheetnames)} sheets for metric columns...")

        # Group metrics that happen to land on the same sheet into one scan.
        by_sheet: dict[str, dict[str, int]] = {}
        sheet_for_metric: dict[str, str] = {}
        for metric_key, aliases in METRICS.items():
            found = find_metric_column(wb, aliases)
            if found is None:
                series[metric_key]["cps"].append(None)
                series[metric_key]["state"].append(None)
                print(f"  {metric_key}: not found")
                continue
            sheet_name, col_idx = found
            by_sheet.setdefault(sheet_name, {})[metric_key] = col_idx
            sheet_for_metric[metric_key] = sheet_name

        for sheet_name, col_indices in by_sheet.items():
            values = read_rows(wb, sheet_name, col_indices)
            for metric_key, (cps_val, state_val) in values.items():
                series[metric_key]["cps"].append(cps_val)
                series[metric_key]["state"].append(state_val)
                print(f"  {metric_key} (sheet '{sheet_name}'): CPS={cps_val}, IL={state_val}")

        # Subgroup trends for this year: reuse the sheet already located
        # above for ela_proficiency / math_proficiency (same sheet as the
        # bare-Total column, since subgroup columns live alongside it).
        for metric_key, alias in SUBGROUP_TREND_METRICS.items():
            sheet_name = sheet_for_metric.get(metric_key)
            if sheet_name is None:
                for label in SUBGROUP_SUFFIXES:
                    subgroup_trends[metric_key][label]["cps"].append(None)
                    subgroup_trends[metric_key][label]["state"].append(None)
                continue
            col_indices = find_subgroup_columns(wb, sheet_name, alias)
            values = read_rows(wb, sheet_name, col_indices)
            for label in SUBGROUP_SUFFIXES:
                cps_val, state_val = values.get(label, (None, None))
                subgroup_trends[metric_key][label]["cps"].append(cps_val)
                subgroup_trends[metric_key][label]["state"].append(state_val)

        wb.close()

    # 2025-26 subgroup snapshot (most recent year) for the existing bar chart
    # -- just the last element of each subgroup_trends series, no re-read needed.
    latest_year = years[-1]
    subgroup_snapshot: dict[str, dict[str, float | None]] = {
        metric_key: {label: trends["cps"][-1] for label, trends in by_label.items()}
        for metric_key, by_label in subgroup_trends.items()
    }

    out = {
        "years": years,
        "series": series,
        "subgroups_latest_year": latest_year,
        "subgroups": subgroup_snapshot,
        "subgroup_groups": {
            group_key: list(labels.keys()) for group_key, labels in SUBGROUP_GROUPS.items()
        },
        "subgroup_trends": subgroup_trends,
    }
    out_path = output_dir / "academic_achievement.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    extract_academic_achievement()
