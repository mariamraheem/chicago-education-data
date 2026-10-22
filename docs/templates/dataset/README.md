# <dataset>/ - <one-line description>

<!--
how to use this template:
  1. copy docs/templates/dataset/ to a new top-level folder, named for the data
     (lowercase, underscores: report_card, not ReportCard)
  2. fill in every <...> below and delete sections that don't apply
  3. rename scripts/01_step_template.py to what it does (01_scrape.py, 02_clean.py ...)
  4. copy registry.yaml to datasets/registry/<dataset>.yaml and delete it from here
  5. delete this comment
rules behind all of this: docs/conventions.md
-->

<What the data is, who publishes it, and what we use it for. 2-4 sentences.>

- **Source:** <url>
- **Publisher:** <agency>
- **Coverage:** <years, geographies, grain e.g. school x year>
- **Refresh:** <when the source updates> -- workflow: `.github/workflows/update-<dataset>.yml` (or "manual")

## Steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | <downloads what, from where; skips files already present, `--force` re-pulls> | `data/raw/...` |
| 2. Clean | `scripts/02_clean.py` | <headers, names, types, suppression> | `data/clean/<dataset>_<what>_clean.csv` |
| 3. Validate | `scripts/03_validate.py` | <checks against which published number> | nothing |

```bash
python <dataset>/scripts/01_scrape.py
python <dataset>/scripts/02_clean.py
python <dataset>/scripts/03_validate.py
```

## Outputs

| File | One row per | Key columns | Years |
|---|---|---|---|
| `data/clean/<dataset>_<what>_clean.csv` | <school x year> | <`school_id`, `school_year`, ...> | <...> |

<Anything a user needs before using the numbers: suppression rules, what blank means.>

## Folder

```
<dataset>/
  README.md          this file
  scripts/           numbered steps, run in order from the repo root
  data/raw/          source files exactly as downloaded (never edited)
  data/clean/        outputs the scripts write
  data/reference/    hand-kept lookups or published numbers used for checks
  dashboard/         static files for the site (optional)
  apps/<name>/       Shiny / Streamlit apps (optional)
```

## Validation

<What published number(s) the output is checked against, and the result of the last check.>

## Known data issues

- **<short name>.** <what's wrong, what was checked, what's still open>
