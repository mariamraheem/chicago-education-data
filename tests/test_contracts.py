from pathlib import Path
import unittest

from pipelines.common.contracts import load_contract, validate_contract


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_membership_contract_loads(self):
        contract = load_contract(ROOT / "datasets" / "contracts" / "enrollment_20th_day_membership.yaml")
        self.assertEqual(contract["dataset_id"], "enrollment_20th_day_membership")
        self.assertEqual(contract["legacy_pipeline"]["cleaner_function"], "clean_general_files")

    def test_missing_contract_fields_are_reported(self):
        self.assertTrue(any("missing required" in error for error in validate_contract({"dataset_id": "example"})))


if __name__ == "__main__":
    unittest.main()
