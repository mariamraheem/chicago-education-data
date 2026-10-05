# datasets/ - registry, contracts and run manifests

Descriptions of each dataset, kept separate from the code that builds it.
Reading these files never downloads or writes anything.

| Folder | What's in it |
|---|---|
| [`registry/`](registry/) | One YAML file per dataset: source, refresh cadence, grain, keys, output location, public-use notes. Every dataset folder should have one. |
| [`contracts/`](contracts/) | Stricter, versioned rules for a publishable output (fields, types, allowed values, thresholds). Only `enrollment_20th_day_membership` has one so far. |
| [`manifests/`](manifests/) | Schema for run manifests: a record of one pipeline run (inputs, row counts, validation result). Runs land in `manifests/runs/`. |

Fields that haven't been checked against real data are marked `placeholder`
or `unverified` rather than guessed.

`python -m unittest tests.test_registry` checks that every registry file has the
required sections (see `pipelines/common/registry.py`). When you add a registry
file, add its `dataset_id` to the expected set in `tests/test_registry.py`.

Background: [docs/datasets/data-products.md](../docs/datasets/data-products.md).
