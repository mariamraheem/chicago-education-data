# scripts/ - site-wide builds

Scripts that combine several datasets for the website. Dataset steps live in
each dataset's own `scripts/` folder.

| Script | What it does | Writes |
|---|---|---|
| `build_site_manifest.py` | Converts each dataset's dashboard files to JSON, writes the manifest the home page reads ("what was refreshed and when"), and calls `build_trends.py`. Datasets are listed in `DOMAINS` at the top. | `site/api/manifest.json`, `site/api/<dataset>/*.json` |
| `build_trends.py` | Compact trend summaries for the home page (YRBS indicators, 5Essentials distributions and medians, overview takeaways). Missing inputs are skipped. | `site/api/trends/*.json` |

Both run in `update-dashboard.yml`. To add a dataset to the site, add it to
`DOMAINS` in `build_site_manifest.py`.
