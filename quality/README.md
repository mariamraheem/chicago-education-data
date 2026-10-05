# quality/ - reusable validation checks

`quality/checks/validation.py` has small checks that work on a pandas DataFrame
or a list of row dicts, each returning a list of issues (empty means it passed):

- `check_required_columns`, `check_non_null_required_fields`
- `check_uniqueness` (composite keys)
- `check_row_count_thresholds` (min, max, change from last run)
- `check_allowed_values`, `check_numeric_range`
- `check_reporting_period_validity` (`YYYY-YYYY` school years)

Used by `pipelines/products/twentieth_day_membership.py`. Status meanings are in
[docs/operations/run-manifests-and-validation.md](../docs/operations/run-manifests-and-validation.md).
