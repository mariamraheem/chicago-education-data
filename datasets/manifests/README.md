# Run manifests

Each ingestion or processing attempt should create one JSON manifest in
`runs/`. A manifest records provenance and validation outcomes even when a
run finds no new source data or fails before publishing an output.

Phase 1 defines the format and helpers only. No existing pipeline writes
these manifests yet.
