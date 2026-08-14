# Dataset registry

The registry is the source of truth for the intended contract of each CPS
data product. It describes a dataset; it does not run a scraper, download a
source, or publish an output.

Every entry is YAML and has a stable `dataset_id`. Fields whose details have
not been verified are deliberately marked `placeholder` or `unverified`.
Those fields must be confirmed before an automated ingestion workflow relies
on them.

The initial entries document the repository's existing enrollment, budget,
and monitor systems without changing their behavior.
