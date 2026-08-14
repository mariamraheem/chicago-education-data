"""Read and validate declarative dataset-registry entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL_FIELDS = {
    "dataset_id", "title", "domain", "description", "source", "refresh",
    "ingestion", "schema", "quality", "public_output", "governance", "provenance",
}


def validate_registry_entry(entry: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors for one registry entry."""
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(entry))
    if missing:
        errors.append(f"missing required top-level fields: {', '.join(missing)}")
    if not isinstance(entry.get("dataset_id"), str) or not entry.get("dataset_id", "").strip():
        errors.append("dataset_id must be a non-empty string")
    for section in ("source", "refresh", "ingestion", "schema", "quality", "public_output", "governance", "provenance"):
        if section in entry and not isinstance(entry[section], dict):
            errors.append(f"{section} must be a mapping")
    if isinstance(entry.get("source"), dict):
        for key in ("url", "publisher", "source_type"):
            if not entry["source"].get(key):
                errors.append(f"source.{key} is required")
    if isinstance(entry.get("provenance"), dict) and not isinstance(entry["provenance"].get("fields"), list):
        errors.append("provenance.fields must be a list")
    return errors


def load_registry(registry_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Load all YAML entries and reject invalid or duplicate dataset IDs."""
    entries: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(registry_dir).glob("*.y*ml")):
        with path.open(encoding="utf-8") as handle:
            entry = yaml.safe_load(handle)
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: registry entry must be a mapping")
        errors = validate_registry_entry(entry)
        if errors:
            raise ValueError(f"{path}: {'; '.join(errors)}")
        dataset_id = entry["dataset_id"]
        if dataset_id in entries:
            raise ValueError(f"duplicate dataset_id: {dataset_id}")
        entries[dataset_id] = entry
    return entries
