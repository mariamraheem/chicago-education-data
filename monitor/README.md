# monitor/ - CPS file monitor

A broad, shallow watch over cps.edu. It doesn't clean or compile anything: it
crawls cps.edu from a seed list plus the api.cps.edu service directory, records
every downloadable file it finds (with Last-Modified, ETag and size), and
publishes a dashboard of what changed since the last run. Use it to spot new
CPS data drops, then wire the useful ones into a dataset folder.

- **Workflow:** `.github/workflows/update-monitor.yml` (Mondays 07:00 UTC)
- **Published at:** `/monitor/` on the site (built by `update-dashboard.yml`)

## Steps

| Step | Script | What it does |
|---|---|---|
| 1. Scan | `01_scan.py` | Crawls cps.edu from `known_urls.yaml`, checks every file's HTTP headers, diffs against `data/state.json`. |
| 2. Export API | `02_export_api.py` | Writes a static JSON (and one CSV) API of the inventory to `monitor/site/api/`. |
| 3. Render | `03_render_dashboard.py` | Builds the static dashboard in `monitor/site/`. |

```bash
pip install -r monitor/requirements.txt
python monitor/01_scan.py
python monitor/02_export_api.py
python monitor/03_render_dashboard.py
open monitor/site/index.html
```

`data/state.json`, `data/run_log.jsonl` and `data/diffs/` are committed, so the
history of what CPS published and when is kept. `monitor/site/` is not
committed; it's rebuilt on every site deploy.

`monitor/update-monitor.yml` is an older copy of the workflow. The live one is
`.github/workflows/update-monitor.yml`.

## What it doesn't catch yet

- **Google Sheets.** Some current-year CPS Metrics reports link to
  docs.google.com. The monitor flags when those links appear or disappear but
  can't see content changes without a Google Drive API key (there's a hook noted
  in `01_scan.py`).
- **API data.** It hashes each api.cps.edu service's docs page, so it notices
  when an API's shape changes, not when its data changes. Add an
  endpoint-specific check (query, hash, diff) for any API you care about.
- **Pages outside the crawl.** The crawl is bounded (`MAX_PAGES` in
  `01_scan.py`) and follows only the path prefixes in `known_urls.yaml`. Add a
  missed data page to `seed_pages` there.
