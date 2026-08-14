"""Create and validate lightweight, machine-readable run manifests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


PROCESSING_STATUSES = {"pending", "running", "succeeded", "failed", "skipped"}
VALIDATION_STATUSES = {"not_run", "passed", "warning", "failed"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_run_manifest(dataset_id: str, code_version: str, **overrides: Any) -> dict[str, Any]:
    """Create a manifest without performing ingestion or filesystem writes."""
    manifest = {
        "run_id": str(uuid4()),
        "dataset_id": dataset_id,
        "started_at": utc_now(),
        "ended_at": None,
        "source_url": None,
        "source_file_name": None,
        "source_checksum_or_etag": None,
        "source_files": [],
        "reporting_period": None,
        "processing_status": "pending",
        "validation_status": "not_run",
        "row_count": None,
        "warnings": [],
        "errors": [],
        "processed_output": None,
        "comparison": None,
        "code_version": code_version,
    }
    manifest.update(overrides)
    errors = validate_run_manifest(manifest)
    if errors:
        raise ValueError("invalid run manifest: " + "; ".join(errors))
    return manifest


def validate_run_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return validation errors instead of raising, for workflow-friendly use."""
    errors: list[str] = []
    for field in ("run_id", "dataset_id", "started_at", "processing_status", "validation_status", "code_version"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"{field} must be a non-empty string")
    if manifest.get("processing_status") not in PROCESSING_STATUSES:
        errors.append("processing_status is not recognized")
    if manifest.get("validation_status") not in VALIDATION_STATUSES:
        errors.append("validation_status is not recognized")
    if manifest.get("row_count") is not None and (not isinstance(manifest["row_count"], int) or manifest["row_count"] < 0):
        errors.append("row_count must be a non-negative integer or null")
    for field in ("warnings", "errors"):
        if not isinstance(manifest.get(field), list) or not all(isinstance(item, str) for item in manifest.get(field, [])):
            errors.append(f"{field} must be a list of strings")
    if not isinstance(manifest.get("source_files"), list) or not all(isinstance(item, dict) for item in manifest.get("source_files", [])):
        errors.append("source_files must be a list of mappings")
    if manifest.get("comparison") is not None and not isinstance(manifest["comparison"], dict):
        errors.append("comparison must be a mapping or null")
    return errors
