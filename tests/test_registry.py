from pathlib import Path
import unittest

from pipelines.common.registry import load_registry, validate_registry_entry


ROOT = Path(__file__).resolve().parents[1]


class RegistryTests(unittest.TestCase):
    def test_existing_registry_entries_load(self):
        registry = load_registry(ROOT / "datasets" / "registry")
        self.assertEqual(set(registry), {"enrollment", "enrollment_20th_day_membership", "budget", "monitor"})

    def test_missing_required_fields_are_reported(self):
        errors = validate_registry_entry({"dataset_id": "example"})
        self.assertTrue(any("missing required" in error for error in errors))

    def test_source_metadata_is_required(self):
        entry = {field: {} for field in (
            "source", "refresh", "ingestion", "schema", "quality", "public_output", "governance", "provenance"
        )}
        entry.update({"dataset_id": "example", "title": "Example", "domain": "test", "description": "Test"})
        errors = validate_registry_entry(entry)
        self.assertIn("source.url is required", errors)


if __name__ == "__main__":
    unittest.main()
