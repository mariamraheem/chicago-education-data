# CPS 20th Day Membership

This data product wraps the existing `GENERAL` 20th-day enrollment path. It
does not replace or modify the existing scraper or cleaner.

## Source and existing logic

The existing scraper reads the CPS demographics page and classifies linked
workbooks as `GENERAL`, `RACE`, or `EL_IEP`. This product uses only `GENERAL`
workbooks. `enrollment/scripts/02_clean.py::clean_general_files` detects the
header row, derives the school year from the source filename, handles two
historical column variations, normalizes grades 1–12, and excludes District
Total rows.

Race, EL, and IEP fields are intentionally excluded because they are separate
existing report paths and do not belong to the GENERAL membership definition.

## Canonical schema and grain

One record represents one `school_year`, `school_id`, and `grade`. The fields
are `school_year`, `school_id`, `school_name`, `grade`, and `enrollment`.
`grade=ALL` is the source's reported Total; it must not be summed with grade
records.

## Validation and versioning

The wrapper checks required fields, non-null identifiers, composite-key
uniqueness, `YYYY-YYYY` school years, and non-negative integer enrollment.
A row-count change over the provisional 50% threshold produces WARNING. Both
WARNING and FAIL write a run manifest but do not publish an output.

PASS writes immutable files to
`data-products/enrollment_20th_day_membership/<school_year>/<run_id>/`:
`membership.csv`, `summary.json`, `schools.json`, and `comparison.json`.
`latest.json` is only a pointer to the latest approved immutable output.

## Known limitations

No GENERAL workbook is currently checked into this branch. The first real run
cannot compare against an earlier version, and the 50% row-count threshold is
provisional. The existing pipeline does not persist individual source-file
URLs, so the wrapper records the known CPS landing page plus local filename,
SHA-256, and observed filesystem timestamp.
