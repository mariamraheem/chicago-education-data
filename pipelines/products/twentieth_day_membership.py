"""Wrap the existing GENERAL enrollment cleaner as a 20th Day Membership product.

This module deliberately does not scrape CPS and does not modify the legacy
enrollment scripts. It calls ``clean_general_files`` exactly as implemented,
then reshapes the resulting wide school-year table into a versioned,
grade-level product with validation, provenance, comparison, and manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pipelines.common.manifests import create_run_manifest, utc_now
from quality.checks import (
    check_non_null_required_fields,
    check_numeric_range,
    check_reporting_period_validity,
    check_required_columns,
    check_row_count_thresholds,
    check_uniqueness,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "enrollment_20th_day_membership"
SOURCE_URL = "https://www.cps.edu/about/district-data/demographics/"
RAW_DIR = REPO_ROOT / "enrollment" / "data" / "raw"
MANIFEST_DIR = REPO_ROOT / "datasets" / "manifests" / "runs"
PRODUCT_ROOT = REPO_ROOT / "data-products" / DATASET_ID
REQUIRED_COLUMNS = ["school_year", "school_id", "school_name", "grade", "enrollment"]
KEY_COLUMNS = ["school_year", "school_id", "grade"]
GRADE_COLUMNS = [("Total", "ALL"), ("PE", "PE"), ("PK", "PK"), ("K", "K")] + [
    (f"Grade {grade}", f"Grade {grade}") for grade in range(1, 13)
]


def _legacy_cleaner():
    """Load the legacy script by path without changing its source or behavior."""
    path = REPO_ROOT / "enrollment" / "scripts" / "02_clean.py"
    spec = importlib.util.spec_from_file_location("legacy_enrollment_cleaner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load legacy cleaner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_present(columns: pd.Index, candidates: list[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in columns), None)


def _normalize_school_id(value: Any) -> str | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") and text[:-2].isdigit() else text


def canonicalize_general_enrollment(wide: pd.DataFrame) -> pd.DataFrame:
    """Convert legacy GENERAL cleaner output to the documented long-form grain."""
    school_id_column = _first_present(wide.columns, ["School ID", "School_ID", "Unit"])
    school_name_column = _first_present(wide.columns, ["School Name", "School_Name", "School"])
    year_column = _first_present(wide.columns, ["Year"])
    missing = [name for name, column in {
        "school ID": school_id_column, "school name": school_name_column, "Year": year_column,
    }.items() if column is None]
    if missing:
        raise ValueError("legacy GENERAL output lacks required columns: " + ", ".join(missing))

    selected_grades = [(source, canonical) for source, canonical in GRADE_COLUMNS if source in wide.columns]
    if not selected_grades:
        raise ValueError("legacy GENERAL output has no recognized Total or grade columns")

    base = wide[[year_column, school_id_column, school_name_column] + [source for source, _ in selected_grades]].copy()
    base = base.rename(columns={year_column: "school_year", school_id_column: "school_id", school_name_column: "school_name"})
    long = base.melt(
        id_vars=["school_year", "school_id", "school_name"],
        value_vars=[source for source, _ in selected_grades],
        var_name="_source_grade",
        value_name="enrollment",
    )
    grade_map = dict(selected_grades)
    long["grade"] = long["_source_grade"].map(grade_map)
    long = long.drop(columns="_source_grade")
    long["school_year"] = long["school_year"].astype(str).str.strip()
    long["school_id"] = long["school_id"].map(_normalize_school_id)
    long["school_name"] = long["school_name"].astype("string").str.strip()
    long["enrollment"] = pd.to_numeric(long["enrollment"], errors="coerce")
    # A missing cell means that this grade was not reported in that workbook;
    # it is not converted to zero or fabricated as a record.
    long = long[long["enrollment"].notna()].copy()
    return long[REQUIRED_COLUMNS].sort_values(KEY_COLUMNS).reset_index(drop=True)


def source_provenance(reporting_period: str) -> list[dict[str, str]]:
    """Record reproducible local provenance for the existing raw source files."""
    records = []
    for path in sorted(RAW_DIR.glob(f"GENERAL_{reporting_period}*.xls*")):
        records.append({
            "source_url": SOURCE_URL,
            "source_file_name": path.name,
            "source_checksum_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "retrieval_timestamp": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "local_path": str(path.relative_to(REPO_ROOT)),
        })
    return records


def validate_membership(data: pd.DataFrame, previous_row_count: int | None = None, maximum_change_ratio: float = 0.5) -> tuple[str, list[str], list[str]]:
    """Return PASS/WARNING/FAIL, warnings, and errors for one reporting period."""
    errors = []
    for check in (
        check_required_columns(data, REQUIRED_COLUMNS),
        check_non_null_required_fields(data, ["school_year", "school_id", "school_name", "grade"]),
        check_uniqueness(data, KEY_COLUMNS),
        check_reporting_period_validity(data, "school_year"),
        check_numeric_range(data, "enrollment", minimum=0, integer_only=True),
    ):
        errors.extend(issue.message for issue in check if issue.severity == "error")
    warning_issues = check_row_count_thresholds(
        len(data), previous_count=previous_row_count, maximum_change_ratio=maximum_change_ratio,
    )
    warnings = [issue.message for issue in warning_issues]
    return ("FAIL" if errors else "WARNING" if warnings else "PASS"), warnings, errors


def compare_products(current: pd.DataFrame, previous: pd.DataFrame | None) -> dict[str, Any] | None:
    """Compare two canonical products; no comparison is invented when none exists."""
    if previous is None:
        return None
    current_indexed = current.set_index(KEY_COLUMNS)
    previous_indexed = previous.set_index(KEY_COLUMNS)
    new_keys = current_indexed.index.difference(previous_indexed.index)
    removed_keys = previous_indexed.index.difference(current_indexed.index)
    shared = current_indexed.index.intersection(previous_indexed.index)
    changed = [
        list(key) for key in shared
        if current_indexed.loc[key, "enrollment"] != previous_indexed.loc[key, "enrollment"]
    ]
    return {
        "previous_row_count": len(previous),
        "current_row_count": len(current),
        "row_count_difference": len(current) - len(previous),
        "new_identifiers": [list(key) for key in new_keys],
        "disappearing_identifiers": [list(key) for key in removed_keys],
        "changed_enrollment_values": changed,
        "reporting_year_difference": sorted(set(current["school_year"]) ^ set(previous["school_year"])),
    }


def _load_previous(reporting_period: str) -> pd.DataFrame | None:
    pointer = PRODUCT_ROOT / "latest.json"
    if not pointer.exists():
        return None
    latest = json.loads(pointer.read_text(encoding="utf-8"))
    if latest.get("reporting_period") != reporting_period:
        return None
    path = REPO_ROOT / latest["membership_csv"]
    return pd.read_csv(path) if path.exists() else None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _product_path(path: Path) -> str:
    """Use repository-relative locations in production and support isolated tests."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_manifest(manifest: dict[str, Any]) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    path = MANIFEST_DIR / f"{manifest['run_id']}.json"
    _write_json(path, manifest)
    return path


def _publish(reporting_period: str, run_id: str, data: pd.DataFrame, comparison: dict[str, Any] | None) -> Path:
    output_dir = PRODUCT_ROOT / reporting_period / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    membership = output_dir / "membership.csv"
    data.to_csv(membership, index=False)
    summary = data.groupby("grade", dropna=False)["enrollment"].sum().reset_index().to_dict("records")
    schools = data[["school_id", "school_name"]].drop_duplicates().sort_values(["school_name", "school_id"]).to_dict("records")
    _write_json(output_dir / "summary.json", {"dataset_id": DATASET_ID, "reporting_period": reporting_period, "enrollment_by_grade": summary})
    _write_json(output_dir / "schools.json", schools)
    _write_json(output_dir / "comparison.json", comparison)
    _write_json(PRODUCT_ROOT / "latest.json", {
        "dataset_id": DATASET_ID,
        "reporting_period": reporting_period,
        "run_id": run_id,
        "approved_at": utc_now(),
        "membership_csv": _product_path(membership),
        "summary_json": _product_path(output_dir / "summary.json"),
        "schools_json": _product_path(output_dir / "schools.json"),
    })
    return membership


def process_general_membership(wide: pd.DataFrame, reporting_period: str, *, code_version: str = "working-tree", maximum_change_ratio: float = 0.5) -> dict[str, Any]:
    """Process one already-cleaned GENERAL table and always write a manifest."""
    product = canonicalize_general_enrollment(wide)
    product = product[product["school_year"] == reporting_period].copy()
    previous = _load_previous(reporting_period)
    comparison = compare_products(product, previous)
    status, warnings, errors = validate_membership(product, len(previous) if previous is not None else None, maximum_change_ratio)
    sources = source_provenance(reporting_period)
    manifest = create_run_manifest(
        DATASET_ID, code_version,
        source_url=SOURCE_URL,
        source_file_name=sources[0]["source_file_name"] if len(sources) == 1 else None,
        source_checksum_or_etag=sources[0]["source_checksum_sha256"] if len(sources) == 1 else None,
        source_files=sources,
        reporting_period=reporting_period,
        processing_status="succeeded" if status in {"PASS", "WARNING"} else "failed",
        validation_status={"PASS": "passed", "WARNING": "warning", "FAIL": "failed"}[status],
        row_count=len(product),
        warnings=warnings,
        errors=errors,
        comparison=comparison,
        ended_at=utc_now(),
    )
    if status == "PASS":
        output = _publish(reporting_period, manifest["run_id"], product, comparison)
        manifest["processed_output"] = _product_path(output)
    else:
        manifest["warnings"].append("Dataset was not published because validation did not PASS.")
    manifest_path = _write_manifest(manifest)
    return {"status": status, "manifest": manifest_path, "output": manifest["processed_output"], "comparison": comparison}


def run_existing_pipeline(reporting_period: str | None = None, *, code_version: str = "working-tree") -> list[dict[str, Any]]:
    """Call the unchanged legacy cleaner and wrap each available school year."""
    wide = _legacy_cleaner().clean_general_files()
    if wide.empty:
        manifest = create_run_manifest(
            DATASET_ID, code_version, source_url=SOURCE_URL, processing_status="skipped",
            validation_status="not_run", warnings=["No GENERAL raw workbooks were available; no CPS download was attempted."], ended_at=utc_now(),
        )
        return [{"status": "SKIPPED", "manifest": _write_manifest(manifest), "output": None, "comparison": None}]
    periods = [reporting_period] if reporting_period else sorted(str(value) for value in wide["Year"].dropna().unique())
    return [process_general_membership(wide, period, code_version=code_version) for period in periods]


def main() -> None:
    parser = argparse.ArgumentParser(description="Wrap existing GENERAL enrollment output as a 20th Day Membership data product.")
    parser.add_argument("--school-year", help="Optional YYYY-YYYY period to process; defaults to all legacy-cleaner periods.")
    parser.add_argument("--code-version", default="working-tree")
    args = parser.parse_args()
    for result in run_existing_pipeline(args.school_year, code_version=args.code_version):
        print(json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in result.items()}, default=str))


if __name__ == "__main__":
    main()
