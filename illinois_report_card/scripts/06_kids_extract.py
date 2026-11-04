"""
Extract the KIDS tab's data: CPS (District 299) vs. Illinois statewide trend
in kindergarten readiness (Kindergarten Individual Development Survey),
2023-24 through 2025-26 -- the only three years ISBE has published this.

Unlike every other tab, this data lives in exactly one sheet per year
("KIDS"), present only from 2023-24 on. 2023-24 has no statewide row at all
(ISBE didn't publish one that first year) -- CPS-only that year, same
null-for-unavailable convention as everywhere else in this dashboard.

Writes: illinois_report_card/data/dashboard/kids.json
  {
    "years": ["2023-2024", "2024-2025", "2025-2026"],
    "series": {
      "readiness_all_three": {"cps": [..3..], "state": [..3..]},
      "readiness_social_emotional": {...},
      "readiness_language_literacy": {...},
      "readiness_math": {...},
      "rated_rate": {...}
    },
    "subgroups_latest_year": "2025-2026",
    "subgroups": {
      "readiness_all_three": {"Total": .., "White": .., ...}   # CPS, latest year
    },
    "subgroup_groups": {
      "race_ethnicity": [...], "sex": [...], "income_disability": [...], "other_populations": [...]
    },
    "subgroup_trends": {
      "readiness_all_three": {
        "Total": {"cps": [..3..], "state": [..3..]},
        ...
      }
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

# Bare (no-subgroup) metric columns, stable across all 3 years.
METRICS: dict[str, str] = {
    "readiness_all_three": "Percent of Kindergartners Demonstrating Readiness in All Three Developmental Areas - Total",
    "readiness_zero": "Percent of Kindergartners Demonstrating Readiness in Zero Developmental Areas",
    "readiness_one": "Percent of Kindergartners Demonstrating Readiness in One Developmental Area",
    "readiness_two": "Percent of Kindergartners Demonstrating Readiness in Two Developmental Areas",
    "readiness_social_emotional": "Percent of Kindergartners Demonstrating Readiness in Social and Emotional Development",
    "readiness_language_literacy": "Percent of Kindergartners Demonstrating Readiness in Language and Literacy Development",
    "readiness_math": "Percent of Kindergartners Demonstrating Readiness in Math",
    "rated_rate": "Percent of Kindergartners Rated on 14 Required Measures",
}

# Demographic subgroup suffixes on "...All Three Developmental Areas - X".
# ISBE's own header truncates "Native Hawaiian or Other Pacific Islander" to
# "...Pacific Island" (missing the final "er") -- fixed here on the way in
# so the clean label is what the JSON (and the JS that reads it) ever sees.
SUBGROUP_GROUPS: dict[str, dict[str, str]] = {
    "race_ethnicity": {
        "White": "White",
        "Black or African American": "Black or African American",
        "Hispanic or Latino": "Hispanic or Latino",
        "Asian": "Asian",
        "American Indian or Alaska Native": "American Indian or Alaska Native",
        "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Island",
        "Two or More Races": "Two or More Races",
        "MENA": "MENA",
    },
    "sex": {
        "Female": "Female",
        "Male": "Male",
        "Non Binary": "Non Binary",
    },
    "income_disability": {
        "Low Income": "Low Income",
        "Children with Disabilities": "CWD",
        "IEP": "IEP",
        "EL": "EL",
    },
    "other_populations": {
        "Homeless": "Homeless",
    },
}
SUBGROUP_SUFFIXES: dict[str, str | None] = {"Total": None}
for _grp in SUBGROUP_GROUPS.values():
    SUBGROUP_SUFFIXES.update(_grp)

ALL_THREE_BASE = "Percent of Kindergartners Demonstrating Readiness in All Three Developmental Areas"


def read_rows(wb: openpyxl.Workbook, sheet_name: str, col_indices: dict[str, int]) -> dict[str, tuple[float | None, float | None]]:
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
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except ValueError:
            return None
    return None


def extract_kids(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_years = sorted(p.stem for p in input_dir.glob("*.xlsx"))
    years = [y for y in all_years if (input_dir / f"{y}.xlsx").exists()]
    # Only years whose workbook actually has a KIDS sheet.
    kids_years = []
    for year in years:
        wb = openpyxl.load_workbook(input_dir / f"{year}.xlsx", read_only=True)
        if "KIDS" in wb.sheetnames:
            kids_years.append(year)
        wb.close()

    series: dict[str, dict[str, list[float | None]]] = {
        key: {"cps": [], "state": []} for key in METRICS
    }
    subgroup_trends: dict[str, dict[str, list[float | None]]] = {
        label: {"cps": [], "state": []} for label in SUBGROUP_SUFFIXES
    }

    for year in kids_years:
        wb = openpyxl.load_workbook(input_dir / f"{year}.xlsx", read_only=True)
        ws = wb["KIDS"]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]

        col_indices = {k: header.index(v) for k, v in METRICS.items() if v in header}
        for key in METRICS:
            if key not in col_indices:
                series[key]["cps"].append(None)
                series[key]["state"].append(None)
        values = read_rows(wb, "KIDS", col_indices)
        for key, (cps_val, state_val) in values.items():
            series[key]["cps"].append(cps_val)
            series[key]["state"].append(state_val)
            print(f"[{year}] {key}: CPS={cps_val}, IL={state_val}")

        sub_col_indices: dict[str, int] = {}
        for label, suffix in SUBGROUP_SUFFIXES.items():
            # "Total" is always suffixed " - Total" in this sheet, same as
            # the bare alias always being ambiguous elsewhere in this repo --
            # try the bare base first (in case some year drops the suffix),
            # then "<base> - Total".
            candidates = [ALL_THREE_BASE] if suffix is None else [f"{ALL_THREE_BASE} - {suffix}"]
            if suffix is None:
                candidates.append(f"{ALL_THREE_BASE} - Total")
            for col_name in candidates:
                if col_name in header:
                    sub_col_indices[label] = header.index(col_name)
                    break
        sub_values = read_rows(wb, "KIDS", sub_col_indices)
        for label in SUBGROUP_SUFFIXES:
            cps_val, state_val = sub_values.get(label, (None, None))
            subgroup_trends[label]["cps"].append(cps_val)
            subgroup_trends[label]["state"].append(state_val)

        wb.close()

    latest_year = kids_years[-1]
    subgroup_snapshot: dict[str, float | None] = {
        label: trends["cps"][-1] for label, trends in subgroup_trends.items()
    }

    out = {
        "years": kids_years,
        "series": series,
        "subgroups_latest_year": latest_year,
        "subgroups": {"readiness_all_three": subgroup_snapshot},
        "subgroup_groups": {
            group_key: list(labels.keys()) for group_key, labels in SUBGROUP_GROUPS.items()
        },
        "subgroup_trends": {"readiness_all_three": subgroup_trends},
    }
    out_path = output_dir / "kids.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    extract_kids()
