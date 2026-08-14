import unittest

from quality.checks.validation import (
    check_allowed_values,
    check_non_null_required_fields,
    check_numeric_range,
    check_reporting_period_validity,
    check_required_columns,
    check_row_count_thresholds,
    check_uniqueness,
)


ROWS = [
    {"school_id": "1", "year": "2024-2025", "status": "open"},
    {"school_id": "2", "year": "2024-2025", "status": "closed"},
]


class ValidationTests(unittest.TestCase):
    def test_required_columns_and_non_null_fields(self):
        self.assertEqual(check_required_columns(ROWS, ["school_id", "year"]), [])
        self.assertEqual(len(check_required_columns(ROWS, ["missing"])), 1)
        self.assertEqual(check_non_null_required_fields(ROWS, ["school_id"]), [])
        self.assertEqual(len(check_non_null_required_fields([{ "school_id": None}], ["school_id"])), 1)

    def test_uniqueness_and_allowed_values(self):
        self.assertEqual(check_uniqueness(ROWS, ["school_id", "year"]), [])
        self.assertEqual(len(check_uniqueness(ROWS + [ROWS[0]], ["school_id", "year"])), 1)
        self.assertEqual(check_allowed_values(ROWS, "status", ["open", "closed"]), [])
        self.assertEqual(len(check_allowed_values(ROWS, "status", ["open"])), 1)

    def test_row_count_and_reporting_period(self):
        self.assertEqual(check_row_count_thresholds(10, minimum=1, maximum=20), [])
        self.assertEqual(len(check_row_count_thresholds(2, previous_count=10, maximum_change_ratio=0.5)), 1)
        self.assertEqual(check_reporting_period_validity(ROWS, "year"), [])
        self.assertEqual(len(check_reporting_period_validity([{ "year": "2025-2027"}], "year")), 1)

    def test_numeric_range_rejects_invalid_enrollment_values(self):
        self.assertEqual(check_numeric_range([{ "enrollment": 12}], "enrollment", minimum=0, integer_only=True), [])
        self.assertEqual(len(check_numeric_range([{ "enrollment": -1}, {"enrollment": 1.5}], "enrollment", minimum=0, integer_only=True)), 1)


if __name__ == "__main__":
    unittest.main()
