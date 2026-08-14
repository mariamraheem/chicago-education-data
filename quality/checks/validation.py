"""Generic, in-memory checks usable with records or pandas-like tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    message: str
    severity: str = "error"


def _records(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        return list(data.to_dict("records"))
    return [dict(row) for row in data]


def _columns(data: Any) -> set[str]:
    if hasattr(data, "columns"):
        return {str(column) for column in data.columns}
    return {key for row in _records(data) for key in row}


def check_required_columns(data: Any, required_columns: Iterable[str]) -> list[ValidationIssue]:
    missing = sorted(set(required_columns) - _columns(data))
    return [ValidationIssue("required_columns", f"missing required columns: {', '.join(missing)}")] if missing else []


def check_non_null_required_fields(data: Any, required_fields: Iterable[str]) -> list[ValidationIssue]:
    issues = []
    for field in required_fields:
        null_rows = [index for index, row in enumerate(_records(data)) if row.get(field) is None or row.get(field) == ""]
        if null_rows:
            issues.append(ValidationIssue("non_null_required_fields", f"{field} is null or empty in {len(null_rows)} row(s)"))
    return issues


def check_uniqueness(data: Any, key_fields: Sequence[str]) -> list[ValidationIssue]:
    seen: set[tuple[Any, ...]] = set()
    duplicates = 0
    for row in _records(data):
        key = tuple(row.get(field) for field in key_fields)
        if key in seen:
            duplicates += 1
        seen.add(key)
    if duplicates:
        return [ValidationIssue("uniqueness", f"{duplicates} duplicate row(s) for key: {', '.join(key_fields)}")]
    return []


def check_row_count_thresholds(row_count: int, *, minimum: int | None = None, maximum: int | None = None, previous_count: int | None = None, maximum_change_ratio: float | None = None) -> list[ValidationIssue]:
    issues = []
    if minimum is not None and row_count < minimum:
        issues.append(ValidationIssue("row_count", f"row count {row_count} is below minimum {minimum}"))
    if maximum is not None and row_count > maximum:
        issues.append(ValidationIssue("row_count", f"row count {row_count} exceeds maximum {maximum}"))
    if previous_count is not None and previous_count > 0 and maximum_change_ratio is not None:
        ratio = abs(row_count - previous_count) / previous_count
        if ratio > maximum_change_ratio:
            issues.append(ValidationIssue("row_count", f"row-count change ratio {ratio:.3f} exceeds {maximum_change_ratio:.3f}", "warning"))
    return issues


def check_allowed_values(data: Any, field: str, allowed_values: Iterable[Any]) -> list[ValidationIssue]:
    allowed = set(allowed_values)
    invalid = sorted({row.get(field) for row in _records(data) if row.get(field) is not None and row.get(field) not in allowed}, key=str)
    if invalid:
        return [ValidationIssue("allowed_values", f"{field} contains disallowed values: {invalid}")]
    return []


def check_numeric_range(data: Any, field: str, *, minimum: float | None = None, maximum: float | None = None, integer_only: bool = False) -> list[ValidationIssue]:
    """Check that a numeric field is finite, within range, and optionally integral."""
    invalid = 0
    for row in _records(data):
        value = row.get(field)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            invalid += 1
            continue
        if numeric != numeric or numeric in (float("inf"), float("-inf")):
            invalid += 1
        elif minimum is not None and numeric < minimum:
            invalid += 1
        elif maximum is not None and numeric > maximum:
            invalid += 1
        elif integer_only and not numeric.is_integer():
            invalid += 1
    if invalid:
        return [ValidationIssue("numeric_range", f"{field} has {invalid} invalid numeric value(s)")]
    return []


_YEAR = re.compile(r"^\d{4}$")
_SCHOOL_YEAR = re.compile(r"^(\d{4})-(\d{4})$")


def is_valid_reporting_period(value: Any) -> bool:
    """Accept a calendar year, consecutive school-year range, or ISO date."""
    if isinstance(value, int):
        return 1900 <= value <= 2999
    if not isinstance(value, str):
        return False
    if _YEAR.fullmatch(value):
        return 1900 <= int(value) <= 2999
    match = _SCHOOL_YEAR.fullmatch(value)
    if match:
        return int(match.group(2)) == int(match.group(1)) + 1
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def check_reporting_period_validity(data: Any, field: str) -> list[ValidationIssue]:
    invalid = [row.get(field) for row in _records(data) if not is_valid_reporting_period(row.get(field))]
    if invalid:
        return [ValidationIssue("reporting_period", f"{field} has {len(invalid)} invalid reporting period value(s)")]
    return []
