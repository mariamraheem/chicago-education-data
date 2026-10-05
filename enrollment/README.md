# enrollment/ - CPS 20th-day enrollment and demographics

School-level enrollment for every CPS school, from CPS's public 20th-day
demographic reports: totals by grade, race/ethnicity, and English learner /
special education / economically disadvantaged status. Adapted from Mariam's
original local notebooks.

- **Source:** https://www.cps.edu/about/district-data/demographics/
- **Report families:** `GENERAL_*` (grades and totals), `RACE_*`, `EL_IEP_*`
- **Coverage:** RACE from 1999-2000, GENERAL from 2005-2006, EL/IEP from 2011-2012
- **Workflow:** `.github/workflows/update-enrollment.yml` (06:00 UTC on the 1st of each month)

## Steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | Finds report files on the CPS demographics page and downloads any not already in `data/raw/`. `--overwrite` re-downloads. | `data/raw/` |
| 2. Clean | `scripts/02_clean.py` | Detects header rows, flattens multi-level headers, normalizes column names. | `data/clean/enrollment_general_clean.csv`, `enrollment_race_clean.csv` |
| 3. Compile | `scripts/03_compile.py` | Rolls cleaned files up to district and network level. | `data/clean/enrollment_*_aggregates_<date>.csv`, `enrollment_network_el_iep_aggregate.csv` |
| 4. Dashboard data | `scripts/04_build_dashboard_data.py` | Long school x grade table for the dashboard. | `enrollment_dashboard_data.csv` in both `data/clean/` and `dashboard/` |
| 5. Demographics data | `scripts/05_build_demographics_data.py` | Race and EL/IEP trend tables for the dashboard. | `dashboard/enrollment_race_trend.csv`, `enrollment_network_race.csv`, `enrollment_network_demographics.csv` |

```bash
python enrollment/scripts/01_scrape.py
python enrollment/scripts/02_clean.py
python enrollment/scripts/03_compile.py
python enrollment/scripts/04_build_dashboard_data.py
python enrollment/scripts/05_build_demographics_data.py
```

Raw workbooks are committed, so every file CPS has ever published stays
available here even if CPS reorganizes its site.

## Outputs

See [docs/data-catalog.md](../docs/data-catalog.md#enrollment) for every file's
grain, columns and years.

The `20th Day Membership` data product (`pipelines/products/twentieth_day_membership.py`)
wraps the GENERAL cleaner with validation and versioned outputs. See
[docs/datasets/enrollment-20th-day-membership.md](../docs/datasets/enrollment-20th-day-membership.md).

## Apps

- `dashboard/index.html` - static dashboard published to the site at `/enrollment/`.
- `apps/enrollment_trends_app.py`, `apps/enrollment_decline_app.py` - Streamlit apps
  (`streamlit run enrollment/apps/enrollment_trends_app.py`).

## Known gaps

- **Dated aggregate files pile up.** `03_compile.py` writes a new
  `*_aggregates_<MMDDYYYY>.csv` each run (three identical copies exist now).
  Consider writing one undated file and relying on git history.
- **`enrollment_trends_app.py` expects `enrollment_el_iep_clean.csv`**, a
  school-level EL/IEP file that isn't produced yet. Only the network-level
  aggregate exists, so the app's EL/IEP tab errors until a school-level EL/IEP
  cleaning step is added to `02_clean.py`.
- **Network and school-level decline notebooks** (`Network_analysis.ipynb`,
  `Schoollevel_Enrollment_Declines_20250116.ipynb`) aren't here yet. They need
  an ARA-region / school ID crosswalk; [`reference/`](../reference/) is where
  that should live.
- **Overlap with `cps-enrollment-dashboard`.** That repo runs its own weekly
  enrollment pipeline. See [docs/roadmap.md](../docs/roadmap.md) for the plan
  to merge them.
