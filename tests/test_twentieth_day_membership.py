from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from pipelines.products import twentieth_day_membership as membership


ROOT = Path(__file__).resolve().parents[1]


class TwentiethDayMembershipTests(unittest.TestCase):
    def setUp(self):
        self.wide = pd.read_csv(ROOT / "tests" / "fixtures" / "general_enrollment_sample.csv")
        self.wide["Year"] = "2024-2025"

    def test_representative_general_fixture_becomes_canonical_grade_records(self):
        product = membership.canonicalize_general_enrollment(self.wide)
        self.assertEqual(list(product.columns), membership.REQUIRED_COLUMNS)
        self.assertEqual(len(product), 12)
        self.assertIn("ALL", set(product["grade"]))
        self.assertEqual(product.loc[(product["school_id"] == "1001") & (product["grade"] == "Grade 1"), "enrollment"].iloc[0], 12)

    def test_required_fields_uniqueness_enrollment_and_school_year_validation(self):
        product = membership.canonicalize_general_enrollment(self.wide)
        status, _, errors = membership.validate_membership(product)
        self.assertEqual(status, "PASS")
        duplicate = pd.concat([product, product.iloc[[0]]], ignore_index=True)
        self.assertEqual(membership.validate_membership(duplicate)[0], "FAIL")
        invalid_enrollment = product.copy()
        invalid_enrollment.loc[0, "enrollment"] = -1
        self.assertEqual(membership.validate_membership(invalid_enrollment)[0], "FAIL")
        invalid_year = product.copy()
        invalid_year.loc[0, "school_year"] = "2024-2026"
        self.assertEqual(membership.validate_membership(invalid_year)[0], "FAIL")
        self.assertEqual(errors, [])

    def test_pass_writes_versioned_product_and_manifest(self):
        original_root, original_manifest_dir = membership.PRODUCT_ROOT, membership.MANIFEST_DIR
        try:
            with TemporaryDirectory() as temp:
                membership.PRODUCT_ROOT = Path(temp) / "products"
                membership.MANIFEST_DIR = Path(temp) / "manifests"
                result = membership.process_general_membership(self.wide, "2024-2025", code_version="test")
                self.assertEqual(result["status"], "PASS")
                self.assertTrue((Path(temp) / result["output"]).exists())
                self.assertTrue(result["manifest"].exists())
                self.assertTrue((membership.PRODUCT_ROOT / "latest.json").exists())
        finally:
            membership.PRODUCT_ROOT, membership.MANIFEST_DIR = original_root, original_manifest_dir

    def test_row_count_change_is_a_warning_and_does_not_publish(self):
        product = membership.canonicalize_general_enrollment(self.wide)
        status, warnings, errors = membership.validate_membership(product, previous_row_count=100, maximum_change_ratio=0.5)
        self.assertEqual(status, "WARNING")
        self.assertTrue(warnings)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
