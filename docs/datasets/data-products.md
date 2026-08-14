# CPS data products

A data product is a documented, repeatable public dataset rather than an
ad-hoc source file. It has a stable identifier, a known source, an explicit
grain and schema, validation rules, provenance, a refresh policy, and a
published output contract.

Phase 1 only establishes these definitions. The current enrollment, budget,
and monitor pipelines continue to operate exactly as they do today.

## Registry

`datasets/registry/` contains one YAML entry per existing system. Entries
describe confirmed behavior and label unverified details as placeholders.
The registry is intentionally descriptive: reading it must have no network,
filesystem-write, or deployment side effects.

## Adding a future dataset

1. Confirm the source, publisher, terms, expected volume, and refresh policy.
2. Add a registry entry with placeholders for every unverified field.
3. Define a versioned contract in `datasets/contracts/`.
4. Add reusable validation configuration before enabling any scheduled run.
5. Trial the pipeline with bounded, approved input.
6. Publish only after provenance and validation results are recorded in a run
   manifest and the public-use assessment is complete.
