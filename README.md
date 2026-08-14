# CPS Data Pipeline

Automated scraping, cleaning, and compiling of public Chicago Public Schools
data, currently covering two domains:

- **enrollment/** - 20th day enrollment / demographics (GENERAL, RACE, EL_IEP
  reports), adapted from Mariam Raheem's existing local notebooks.
- **budget/** - CPS budget documents (starting with District Managed Funds).

Each domain follows the same three-stage shape:

1. **Scrape** (`01_scrape.py`) - check the relevant CPS web page(s) for new
   source files and download anything not already in `data/raw/`.
2. **Clean** (`02_clean.py`) - standardize the raw workbooks (detect header
   rows, flatten multi-level headers, normalize column names) into tidy CSVs
   in `data/clean/`.
3. **Compile** (`03_compile.py`, enrollment only for now) - roll cleaned/raw
   data up into district- and network-level summary tables.

A fourth, informal stage - **present** - lives in `enrollment/apps/` as two
Streamlit dashboards that read from `data/clean/`.

## Automation

Two GitHub Actions workflows (`.github/workflows/update-enrollment.yml` and
`update-budget.yml`) run the full scrape -> clean -> compile chain for each
domain on a monthly schedule (1st of the month) and commit any resulting
data changes straight to `main`. Since CPS only updates these sources a few
times a year, most scheduled runs will find nothing new and commit nothing -
that's expected, not a bug.

You can also trigger either workflow on demand from the repo's **Actions**
tab -> select the workflow -> **Run workflow**. This is the easiest way to
do an initial backfill right after this repo is created, since the raw/clean
folders start out empty (only the code is pushed - GitHub's runners have
normal internet access, so the very first run downloads everything CPS
currently publishes, going back to 1999-2000 for enrollment).

Because raw source files are committed to the repo (not just the cleaned
CSVs), the full history of every workbook CPS has ever published stays
available here even if CPS reorganizes or removes something from their site
later.

- **monitor/** - broad, shallow, site-wide watch. Not a domain scraper like
  enrollment/ or budget/ -- it doesn't clean or compile anything. It crawls
  cps.edu from a seed list plus the api.cps.edu service directory, and
  publishes a live dashboard of every downloadable file it finds (with
  Last-Modified/ETag/size) and what's changed since the last run. Use it to
  spot new CPS data drops, then wire the interesting ones into enrollment/
  or budget/ (or a new domain) once you know they're worth cleaning.

### monitor/ stages

Two stages instead of three, since there's no cleaning to do here:

1. **Scan** (`01_scan.py`) - crawl cps.edu from `monitor/known_urls.yaml`,
   check every downloadable file's HTTP headers, diff against
   `monitor/data/state.json` from the previous run.
2. **Render** (`02_render.py`) - build the static dashboard
   (`monitor/site/index.html`) from the current state + recent diffs.

```bash
pip install -r monitor/requirements.txt
python monitor/01_scan.py
python monitor/02_render.py
open monitor/site/index.html   # preview locally
```

`monitor/data/` (state.json, run_log.jsonl, diffs/) is committed to the
repo the same way raw source files are for enrollment/budget, so you get
full history of what CPS published and when, even after they reorganize.
`monitor/site/` is NOT committed -- it's rebuilt fresh each run and
published straight to GitHub Pages via `actions/deploy-pages`.

**One-time manual setup:** in the repo's Settings -> Pages, set
**Source: GitHub Actions** (instead of "Deploy from a branch"). After that,
`update-monitor.yml` runs weekly (Monday 07:00 UTC) and on-demand via the
Actions tab, same as `update-enrollment.yml`/`update-budget.yml`.

### What it doesn't catch (yet)

- **Google Sheets.** Several of CPS's current-year Metrics reports (e.g.
  the 2025-method attendance/dropout/graduation rates) are linked out to
  `docs.google.com` instead of hosted as files. The dashboard flags when
  these links appear/disappear, but can't tell you when the sheet content
  itself changes without a Google Drive API key (`files.get(fileId,
  fields="modifiedTime")`) -- there's a hook for this noted in
  `01_scan.py` if you want to add it later.
- **API data.** `api.cps.edu`'s 10 services are live APIs, not files.
  `01_scan.py` only hashes each service's docs/swagger page, so it'll
  tell you if the API *surface* changes but not if e.g. School Profile
  API adds a new school. If you want that, add an endpoint-specific check
  (query it, hash/diff the JSON response) the same way `compute_diff()`
  handles files.
- **Full site coverage.** It's a bounded crawl (`MAX_PAGES` in
  `01_scan.py`, and only follows links under the path prefixes in
  `known_urls.yaml`). If a data hub page goes unfound, add its URL to
  `seed_pages` in `monitor/known_urls.yaml`.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Enrollment
python enrollment/scripts/01_scrape.py
python enrollment/scripts/02_clean.py
python enrollment/scripts/03_compile.py

# Budget
python budget/scripts/01_scrape.py
python budget/scripts/02_clean.py

# Dashboards
streamlit run enrollment/apps/enrollment_trends_app.py
streamlit run enrollment/apps/enrollment_decline_app.py
```

Add `--overwrite` to either `01_scrape.py` to force re-downloading files
that already exist in `data/raw/` (useful if CPS revises a file in place
without renaming it).

## Known gaps / things to validate on first run

This repo was assembled without being able to reach cps.edu directly (the
environment it was built in only has network access to package registries),
so a few things are best-effort and should be checked once the Actions
workflows actually run with real internet access:

- **`budget/scripts/02_clean.py` is a generic scaffold.** The FY2026/FY2027
  district managed funds workbooks were never actually opened while writing
  this - the cleaner uses a defensive header-auto-detection heuristic
  instead of hardcoded CPS column names (unlike the enrollment cleaners,
  which were adapted from notebooks that *had* seen the real files). After
  the first real run, check `budget/data/clean/_column_report.csv` (lists
  every column found, by year/sheet) and `district_managed_funds_clean.csv`,
  and tighten the column-name standardization the same way
  `enrollment/scripts/02_clean.py` does once the real headers are known.
- **`budget/scripts/01_scrape.py`'s page-crawling is unverified.** CPS's
  budget pages aren't as uniformly structured as the demographics page, and
  the crawler's classification of links (district managed vs. student based
  vs. revenue, etc.) is a best guess. `budget/known_urls.yaml` is a manual
  fallback list seeded with the two URLs already confirmed to work
  (FY2026 and FY2027 district managed funds) - add a line there any time you
  spot a document the crawler misses.
- **`enrollment/apps/enrollment_trends_app.py` expects a file that doesn't
  get produced yet:** `enrollment_el_iep_clean.csv` (a school-level clean
  EL/IEP file). This mismatch existed in the original notebooks too - only
  a *network*-level EL/IEP aggregate is currently compiled
  (`enrollment_network_el_iep_aggregate.csv`, via `03_compile.py`). The app's
  "Enrollment by EL/IEP Status" tab will error until a school-level EL/IEP
  cleaning step is added to `02_clean.py`.
- **The network/school-level analysis notebooks** (`Network_analysis.ipynb`,
  `Schoollevel_Enrollment_Declines_20250116.ipynb`) aren't included in this
  repo yet - they depend on an external ARA-region / school-ID crosswalk
  file that isn't sourced from cps.edu and would need to be supplied
  separately (or re-derived) before they could run as part of this pipeline.

## Adding a new budget document category

Once there's a second budget category to compile alongside district managed
funds (e.g. student based budget, revenue), split the roll-up logic out into
`budget/scripts/03_compile.py`, mirroring how `enrollment/scripts/03_compile.py`
combines EL/IEP and RACE aggregation - `02_clean.py` should stay focused on
standardizing each raw file type into a tidy CSV; save cross-category
combining for the compile stage.
