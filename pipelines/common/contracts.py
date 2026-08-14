"""Read declarative data-product contracts without performing pipeline work."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_CONTRACT_FIELDS = {
    "dataset_id", "registry_dataset_id", "title", "version", "grain",
    "primary_keys", "time_field", "fields", "source", "legacy_pipeline", "public_output",
}


def validate_contract(contract: dict[str, Any]) -> list[str]:
    """Return contract errors while allowing explicitly documented limitations."""
    errors: list[str] = []
    missing = sorted(REQUIRED_CONTRACT_FIELDS - set(contract))
    if missing:
        errors.append(f"missing required contract fields: {', '.join(missing)}")
    if not isinstance(contract.get("dataset_id"), str) or not contract.get("dataset_id", "").strip():
        errors.append("dataset_id must be a non-empty string")
    if not isinstance(contract.get("primary_keys"), list) or not contract.get("primary_keys"):
        errors.append("primary_keys must be a non-empty list")
    if not isinstance(contract.get("fields"), list) or not contract.get("fields"):
        errors.append("fields must be a non-empty list")
    else:
        for field in contract["fields"]:
            if not isinstance(field, dict) or not field.get("name") or not field.get("type"):
                errors.append("each field requires name and type")
                break
    if not isinstance(contract.get("legacy_pipeline"), dict):
        errors.append("legacy_pipeline must be a mapping")
    return errors


def load_contract(path: str | Path) -> dict[str, Any]:
    """Load one contract and reject malformed content before it is used."""
    contract_path = Path(path)
    with contract_path.open(encoding="utf-8") as handle:
        contract = yaml.safe_load(handle)
    if not isinstance(contract, dict):
        raise ValueError(f"{contract_path}: contract must be a mapping")
    errors = validate_contract(contract)
    if errors:
        raise ValueError(f"{contract_path}: {'; '.join(errors)}")
    return contract
