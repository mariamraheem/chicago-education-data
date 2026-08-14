import unittest

from pipelines.common.manifests import create_run_manifest, validate_run_manifest


class ManifestTests(unittest.TestCase):
    def test_create_valid_manifest(self):
        manifest = create_run_manifest("monitor", "test-version", source_url="https://example.test/source")
        self.assertEqual(manifest["dataset_id"], "monitor")
        self.assertEqual(manifest["processing_status"], "pending")
        self.assertEqual(validate_run_manifest(manifest), [])

    def test_invalid_status_and_row_count_are_rejected(self):
        manifest = create_run_manifest("monitor", "test-version")
        manifest["processing_status"] = "unknown"
        manifest["row_count"] = -1
        errors = validate_run_manifest(manifest)
        self.assertIn("processing_status is not recognized", errors)
        self.assertIn("row_count must be a non-negative integer or null", errors)

    def test_source_file_provenance_is_a_list_of_mappings(self):
        manifest = create_run_manifest("monitor", "test-version", source_files=[{"source_file_name": "source.xlsx"}])
        self.assertEqual(validate_run_manifest(manifest), [])
        manifest["source_files"] = ["source.xlsx"]
        self.assertIn("source_files must be a list of mappings", validate_run_manifest(manifest))


if __name__ == "__main__":
    unittest.main()
