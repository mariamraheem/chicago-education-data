# budget/ - CPS school budgets

School-level budget allocations from CPS's budget documents, starting with
District Managed Funds and charter/contract (ALOP) workbooks.

- **Source:** https://www.cps.edu/about/finance/budget/
- **Coverage:** FY2025 to FY2027 (raw files: `DISTRICT_MANAGED_<FY>.xlsx`, `CHARTER_CONTRACT_ALOP_<FY>.xlsx`)
- **Workflow:** `.github/workflows/update-budget.yml` (06:15 UTC on the 1st of each month)

## Steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | Crawls the budget pages and downloads new workbooks. `known_urls.yaml` is a manual fallback list. `--overwrite` re-downloads. | `data/raw/` |
| 2. Clean | `scripts/02_clean.py` | Auto-detects header rows and standardizes columns. | `data/clean/budget_school_funding_clean.csv`, `_column_report.csv` |
| 3. Dashboard data | `scripts/03_build_dashboard_data.py` | Frontend-ready table. | `budget_dashboard_data.csv` in `data/clean/` and `dashboard/` |

```bash
python budget/scripts/01_scrape.py
python budget/scripts/02_clean.py
python budget/scripts/03_build_dashboard_data.py
```

## Known gaps

- **`data/clean/district_managed_funds_clean.csv` is no longer written** by
  `02_clean.py` (it now writes `budget_school_funding_clean.csv`). It's a
  leftover from an earlier version; delete it once nothing reads it.
- **`02_clean.py` is a generic scaffold.** It was written before the real
  workbooks were opened, so it uses header auto-detection instead of CPS's
  actual column names. Check `data/clean/_column_report.csv` (every column
  found, by year and sheet) and tighten the column standardization the way
  `enrollment/scripts/02_clean.py` does.
- **Section-header columns leak into the clean files.** The first two columns
  of `budget_school_funding_clean.csv` and `district_managed_funds_clean.csv`
  are workbook section labels ("School Information", "Includes School Name...")
  rather than data.
- **Enrollment columns are named by fall year** (e.g. `Fall 2023 20th Day
  Enrollment`), so the same measure has a different column name each fiscal
  year. Rename to a fixed name plus a year column before comparing years.
- **`01_scrape.py`'s link classification is a best guess.** CPS's budget pages
  aren't uniform. Add any missed document to `known_urls.yaml`.

## Adding a budget category

When a second category is compiled alongside District Managed Funds (e.g.
student based budget, revenue), move the roll-up into `scripts/03_compile.py`,
like `enrollment/scripts/03_compile.py`. Keep `02_clean.py` to one tidy CSV per
raw file type.
