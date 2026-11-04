"""
Extract the SPED & Teacher Assignment tab's data: CPS (District 299) vs.
Illinois statewide trend in special-education enrollment/inclusion and
teacher qualification/assignment metrics, 2017-18 through 2025-26.

Same scanning approach as 04_academic_achievement_extract.py: columns move
sheet to sheet across years (General -> General + SPED -> General +
TeacherOutofField/TeacherOF), and some columns are renamed mid-series
("Student Enrollment - IEP %" -> "% Student Enrollment - IEP"; "% Students
with IEP served in..." -> "% School Age Students with IEP served in...").
This script tries every known alias per metric and reads the CPS + Statewide
rows directly by RCDTS, same null-for-unavailable-years convention as the
Academic Achievement script.

Writes: illinois_report_card/data/dashboard/sped_teacher.json
  {
    "years": [...],
    "series": {
      "iep_rate": {"cps": [..9..], "state": [..9..]},
      "inclusion_rate": {...},          # 2018-19+
      "teacher_retention_rate": {...},
      "provisional_license_rate": {...},
      "out_of_field_rate": {...},       # 2022-23+
      "pupil_teacher_ratio_elem": {...},
      "pupil_teacher_ratio_hs": {...}
    },
    "subgroups_latest_year": "2025-2026",
    "subgroups": {
      "disability_mix": {"Autism": .., "Specific Learning Disability": .., ...}  # CPS, latest year
    },
    "subgroup_groups": {
      "disability_category": ["Autism", "Deafness", ...]
    },
    "subgroup_trends": {
      "disability_mix": {
        "Autism": {"cps": [..9, pre-2018-19 null..], "state": [..]},
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

# metric key -> list of aliases tried in order (first sheet/alias match wins).
# Each alias is the bare "Total" column text (no subgroup suffix).
METRICS: dict[str, list[str]] = {
    "iep_rate": ["% Student Enrollment - IEP", "Student Enrollment - IEP %"],
    "inclusion_rate": [
        "% School Age Students with IEP served in Gen. Ed. Room 80% or more of day",
        "% Students with IEP served in Gen. Ed. Room 80% or more of day",
    ],
    "separate_facility_rate": [
        "% School Age Students with IEP served in Separate Facility",
        "% Students with IEP served in Separate Facility",
    ],
    "teacher_retention_rate": ["Teacher Retention Rate"],
    "provisional_license_rate": ["% Teachers with Short-Term or Provisional License"],
    "out_of_field_rate": ["% Out-of-Field Teachers"],
    "pupil_teacher_ratio_elem": ["Pupil Teacher Ratio - Elementary"],
    "pupil_teacher_ratio_hs": ["Pupil Teacher Ratio - High School"],
}

# Disability categories as they appear after "% All Students with IEP - " in
# every year 2018-19 through 2025-26 (confirmed stable naming; absent
# entirely in 2017-18, before ISBE broke IEP counts out by category).
DISABILITY_CATEGORIES: list[str] = [
    "Autism",
    "Deafness",
    "Deaf-Blindness",
    "Developmental Delay",
    "Emotional Disability",
    "Hearing Impairment",
    "Intellectual Disability",
    "Multiple Disabilities",
    "Orthopedic Impairment",
    "Other Health Impairment",
    "Specific Learning Disability",
    "Speech or Language Impairment",
    "Traumatic Brain Injury",
    "Visual Impairment",
]
DISABILITY_ALIAS_PREFIX = "% All Students with IEP - "


def find_metric_column(wb: openpyxl.Workbook, aliases: list[str]) -> tuple[str, int] | None:
    """Return (sheet_name, col_index) for the first alias found in any sheet
    (workbook order), trying the bare alias and "<alias> - Total"."""
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        for alias in aliases:
            if alias in header:
                return sheet_name, header.index(alias)
            total_variant = f"{alias} - Total"
            if total_variant in header:
                return sheet_name, header.index(total_variant)
    return None


def find_disability_sheet(wb: openpyxl.Workbook) -> str | None:
    """Return the sheet name holding the "% All Students with IEP - X"
    disability-category columns, or None if this year has none (2017-18)."""
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        if any(h and str(h).startswith(DISABILITY_ALIAS_PREFIX) for h in header):
            return sheet_name
    return None


def read_rows(wb: openpyxl.Workbook, sheet_name: str, col_indices: dict[str, int]) -> dict[str, tuple[float | None, float | None]]:
    """Scan the sheet once for the CPS and Statewide rows, returning
    {label: (cps_value, state_value)} for every column in col_indices."""
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


def extract_sped_teacher(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    years = sorted(p.stem for p in input_dir.glob("*.xlsx"))
    series: dict[str, dict[str, list[float | None]]] = {
        key: {"cps": [], "state": []} for key in METRICS
    }
    subgroup_trends: dict[str, dict[str, list[float | None]]] = {
        label: {"cps": [], "state": []} for label in DISABILITY_CATEGORIES
    }

    for year in years:
        wb = openpyxl.load_workbook(input_dir / f"{year}.xlsx", read_only=True)
        print(f"[{year}] scanning {len(wb.sheetnames)} sheets for metric columns...")

        by_sheet: dict[str, dict[str, int]] = {}
        for metric_key, aliases in METRICS.items():
            found = find_metric_column(wb, aliases)
            if found is None:
                series[metric_key]["cps"].append(None)
                series[metric_key]["state"].append(None)
                print(f"  {metric_key}: not found")
                continue
            sheet_name, col_idx = found
            by_sheet.setdefault(sheet_name, {})[metric_key] = col_idx

        for sheet_name, col_indices in by_sheet.items():
            values = read_rows(wb, sheet_name, col_indices)
            for metric_key, (cps_val, state_val) in values.items():
                series[metric_key]["cps"].append(cps_val)
                series[metric_key]["state"].append(state_val)
                print(f"  {metric_key} (sheet '{sheet_name}'): CPS={cps_val}, IL={state_val}")

        # Disability category mix for this year.
        dis_sheet = find_disability_sheet(wb)
        if dis_sheet is None:
            for label in DISABILITY_CATEGORIES:
                subgroup_trends[label]["cps"].append(None)
                subgroup_trends[label]["state"].append(None)
            print("  disability categories: not found")
        else:
            col_indices = {
                label: None for label in DISABILITY_CATEGORIES
            }
            ws = wb[dis_sheet]
            header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
            for label in DISABILITY_CATEGORIES:
                col_name = f"{DISABILITY_ALIAS_PREFIX}{label}"
                if col_name in header:
                    col_indices[label] = header.index(col_name)
            present = {k: v for k, v in col_indices.items() if v is not None}
            values = read_rows(wb, dis_sheet, present)
            for label in DISABILITY_CATEGORIES:
                cps_val, state_val = values.get(label, (None, None))
                subgroup_trends[label]["cps"].append(cps_val)
                subgroup_trends[label]["state"].append(state_val)

        wb.close()

    latest_year = years[-1]
    disability_snapshot: dict[str, float | None] = {
        label: trends["cps"][-1] for label, trends in subgroup_trends.items()
    }

    out = {
        "years": years,
        "series": series,
        "subgroups_latest_year": latest_year,
        "subgroups": {"disability_mix": disability_snapshot},
        "subgroup_groups": {"disability_category": DISABILITY_CATEGORIES},
        "subgroup_trends": {"disability_mix": subgroup_trends},
    }
    out_path = output_dir / "sped_teacher.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    extract_sped_teacher()
