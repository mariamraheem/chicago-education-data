# Run manifests and validation

## Run manifests

`datasets/manifests/run_manifest.schema.json` defines a portable record for
one ingestion or processing attempt. It records the run and dataset IDs,
time boundaries, source details, reporting period, processing and validation
statuses, row count, messages, output location, and code version.

The Phase 1 helper creates these records in memory only. Existing pipelines
do not write them yet.

## Validation statuses

- `not_run`: no validation was attempted.
- `passed`: all configured error-level checks passed.
- `warning`: processing completed, but a non-blocking threshold or review
  condition needs attention.
- `failed`: one or more error-level checks failed; the output should not be
  treated as a validated data product.

Generic checks currently cover required columns, non-null fields, composite
uniqueness, row-count thresholds, allowed values, and reporting-period
format. Thresholds remain unconfigured for existing datasets until real
baselines are reviewed.
