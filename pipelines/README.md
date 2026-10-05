# pipelines/ - shared Python helpers

Code used across datasets. Dataset-specific steps live in each dataset's
`scripts/` folder, not here.

| Module | What it does |
|---|---|
| `common/registry.py` | `load_registry(dir)` reads `datasets/registry/*.yaml` and checks required sections. |
| `common/contracts.py` | `load_contract(path)`, `validate_contract(contract)` for `datasets/contracts/`. |
| `common/manifests.py` | `create_run_manifest(dataset_id, code_version, ...)` builds a run record. |
| `products/twentieth_day_membership.py` | Wraps the enrollment GENERAL cleaner into the validated, versioned 20th Day Membership product. Run with `python -m pipelines.products.twentieth_day_membership`. |

Validation checks are in [`quality/`](../quality/). Tests are in [`tests/`](../tests/).
