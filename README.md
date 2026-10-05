# Chicago Education Data

One place for the public education data Kids First Chicago uses: where it comes
from, the code that collects and cleans it, the cleaned files, and the dashboards
built on top. Every dataset follows the same pattern, so once you know one
folder you know them all.

**Live site:** GitHub Pages (home page, enrollment and budget dashboards, CPS file
monitor, JSON API). It is rebuilt by `update-dashboard.yml` whenever a data
workflow finishes.

## What's here

| Folder | Data | Source | Years | Refresh | Docs |
|---|---|---|---|---|---|
| [`enrollment/`](enrollment/) | 20th-day enrollment by school, grade, race, EL/IEP | CPS demographics reports | 1999-2000 to now | Monthly check (Actions) | [README](enrollment/README.md) |
| [`five_essentials/`](five_essentials/) | 5Essentials survey scores by school, essential and measure | UChicago Impact (5-essentials.org) | Latest 5 surveys | Jul-Oct (Actions) | [README](five_essentials/README.md) |
| [`yrbs/`](yrbs/) | Youth Risk Behavior Survey, Chicago / Illinois / U.S. | CDC (SADC files) | 1991 to now | Quarterly check (Actions) | [README](yrbs/README.md) |
| [`budget/`](budget/) | School budgets (District Managed Funds, charter/contract) | CPS budget pages | FY2025 to now | Monthly check (Actions) | [README](budget/README.md) |
| [`monitor/`](monitor/) | Inventory of every downloadable file on cps.edu, and what changed | cps.edu, api.cps.edu | Rolling | Weekly (Actions) | [README](monitor/README.md) |
| [`reference/`](reference/) | Shared lookups: school to network / community area / ESB district, school locations, boundaries | CPS reports and Chicago Data Portal | Current | When boundaries change | [README](reference/README.md) |

Supporting folders:

| Folder | What it does |
|---|---|
| [`docs/`](docs/) | Data catalog, conventions, roadmap, operations notes. Start at [docs/README.md](docs/README.md). |
| [`datasets/`](datasets/) | Registry (one YAML per dataset), contracts and run manifests. |
| [`pipelines/`](pipelines/), [`quality/`](quality/) | Shared Python helpers: registry loading, validation checks, data products. |
| [`scripts/`](scripts/) | Site-wide builds: JSON API, manifest and trend summaries for the home page. |
| [`site-landing/`](site-landing/) | The home page and Explore page of the GitHub Pages site. |
| [`tests/`](tests/) | Unit tests for the shared helpers. |
| `.github/workflows/` | Scheduled GitHub Actions, one per dataset plus the site build. |

## How every dataset folder is laid out

```
<dataset>/
  README.md          what it is, how to run it, outputs, caveats
  scripts/           numbered steps: 01_scrape.py, 02_clean.py, 03_compile.py ...
  data/raw/          source files exactly as downloaded (committed, never edited)
  data/clean/        tidy outputs the scripts write (committed)
  data/reference/    hand-maintained lookups for this dataset only (optional)
  dashboard/         static dashboard files published to the site (optional)
  apps/              interactive apps, e.g. Shiny or Streamlit (optional)
```

The rules behind this (naming, script structure, what to commit) are in
[docs/conventions.md](docs/conventions.md). Every output file is listed in
[docs/data-catalog.md](docs/data-catalog.md).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run any dataset's steps in order, from the repo root
python enrollment/scripts/01_scrape.py
python enrollment/scripts/02_clean.py
python enrollment/scripts/03_compile.py

python five_essentials/scripts/01_scrape.py
python yrbs/scripts/01_scrape.py && python yrbs/scripts/02_compile.py
python budget/scripts/01_scrape.py && python budget/scripts/02_clean.py

# Tests for the shared helpers
python -m unittest discover tests
```

Apps:

```bash
streamlit run enrollment/apps/enrollment_trends_app.py
Rscript five_essentials/apps/explorer/update_data.R
R -e 'shiny::runApp("five_essentials/apps/explorer")'
```

## Automation

Each dataset has a GitHub Actions workflow that runs its scripts on a schedule
and commits any new data to `main`. Most scheduled runs find nothing new; that's
expected. Any workflow can be run by hand from the **Actions** tab. Details,
schedules and one-time setup are in
[docs/operations/automation.md](docs/operations/automation.md).

## Related repo

[`cps-enrollment-dashboard`](https://github.com/mariamraheem/cps-enrollment-dashboard)
is a separate, still-active enrollment dashboard with its own weekly pipeline.
Its school groupings, locations and map boundaries are copied into
[`reference/`](reference/). The plan for bringing it into this repo, while
keeping it live until then, is in [docs/roadmap.md](docs/roadmap.md).

## Adding a new dataset

1. Make a folder with the layout above and a README (copy an existing one).
2. Add a registry entry in `datasets/registry/` (see its README).
3. Add a workflow in `.github/workflows/` modeled on an existing `update-*.yml`.
4. Add its outputs to [docs/data-catalog.md](docs/data-catalog.md) and the table above.
