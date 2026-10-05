# Conventions

How code and data are organized here, so any folder is easy to pick up.

## Folder layout

One top-level folder per dataset (named for the data, lowercase with
underscores: `five_essentials`, not `5E`):

```
<dataset>/
  README.md          required
  scripts/           numbered steps, run in order from the repo root
  data/raw/          source files exactly as downloaded
  data/clean/        outputs the scripts write
  data/reference/    hand-maintained lookups for this dataset only
  dashboard/         static files published to the site
  apps/<name>/       interactive apps (Shiny, Streamlit), one folder each
```

Lookups used by more than one dataset (school crosswalks, boundaries) go in
[`reference/`](../reference/), not inside a dataset folder.

## Scripts

- **Numbered by step:** `01_scrape.py`, `02_clean.py`, `03_compile.py`,
  `04_build_dashboard_data.py`. Each step reads the previous step's output
  from disk, so any step can be re-run on its own.
- **Run from the repo root** (`python enrollment/scripts/02_clean.py`). Build
  paths from `REPO_ROOT = Path(__file__).resolve().parents[2]`, never from the
  current directory.
- **Same shape in every script** (Python or R):
  1. A docstring at the top: what it does, inputs, outputs, how to run it.
  2. Config and constants next (paths, URLs, years, thresholds), so changes
     happen in one place.
  3. One function per step, each with a one-line docstring.
  4. A short `main()` that calls the steps in order.
- **Scrapers skip files they already have** and take `--overwrite` (or
  `--force`) to re-download.
- **Say what happened.** Print what was downloaded, written, skipped or
  missing, with counts, so a GitHub Actions log is enough to debug a run.

## Data

- **Raw files are committed and never edited.** If CPS changes or removes a
  file, the history stays here. Large binaries go through Git LFS (see
  `.gitattributes`).
- **Clean files are committed too**, so dashboards and the site can read them
  without re-running the pipeline.
- **File names:** `<dataset>_<what>_clean.csv` for cleaned tables,
  `<dataset>_<what>_long.csv` / `_wide.csv` when both shapes exist. Avoid dates
  in file names; git history already records when a file changed.
- **Column names:** `snake_case`. Use these names for shared keys in new code:
  `school_id` (string), `school_name`, `school_year` (`"2025-2026"`) or
  `survey_year` (`2026`), `network`, `community_area`, `esb_district`.
- **Missing is missing.** Leave a blank rather than guessing or carrying a
  value forward, and say in the README why it's missing.
- **Every output goes in [data-catalog.md](data-catalog.md).**

## Documentation

- Every folder that holds code has a README: what it is, how to run it, what
  it writes, known issues.
- Known data problems go in the dataset README under **Known data issues**,
  with what was checked and what's still open.
- Every dataset has a registry entry in `datasets/registry/` (see its README).

## Apps

- An app folder holds everything it needs to run, so it can be deployed on its
  own. If it needs repo data, add an `update_data` script that copies it in, and
  git-ignore the copies.
- Settings (colors, thresholds, which tabs appear) go at the top of the app
  file, the same as scripts.

## Working copy

- **Keep the repo out of iCloud Drive.** A git repo inside an iCloud-synced
  folder (like `~/Documents` with "Desktop & Documents Folders" turned on) can
  have files evicted to the cloud, which breaks git and scripts with errors like
  `Resource deadlock avoided`. Clone into a folder iCloud doesn't sync, such as
  `~/code/`.
- `git pull` before starting work. The Actions bots commit data to `main`
  often, so a stale copy will conflict.
