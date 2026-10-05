# tests/

Unit tests for the shared helpers in `pipelines/` and `quality/`. They use the
standard library's `unittest` and small fixtures in `fixtures/`; no network.

```bash
python -m unittest discover tests
```

`test_registry.py` lists every expected `dataset_id`; update it when you add a
registry file.
