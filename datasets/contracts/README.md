# Dataset contracts

A dataset contract turns a registry description into an enforceable agreement
for one publishable output. Contracts are intentionally not assigned to the
existing enrollment or budget outputs in Phase 1: their source schemas still
need validation against real files.

When a contract is added, it should define the dataset version, grain,
primary key, fields and types, required fields, allowed values, reporting
period convention, validation thresholds, and public output location. A
contract must reference one `dataset_id` from `datasets/registry/`.
