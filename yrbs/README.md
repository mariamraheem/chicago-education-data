# yrbs/ — Youth Risk Behavior Survey (CDC)

Historic high school YRBS results for **Chicago** (district), **Illinois** (state) and
the **United States**, 1991 to the latest release, compiled from CDC's combined
datasets ("SADC").

| Step | Script | Output |
|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | `data/raw/`: Chicago, Illinois and national fixed-width files + CDC's SAS layout programs |
| 2. Compile | `scripts/02_compile.py` | `data/clean/`: student-level records and weighted prevalence tables |

```bash
python yrbs/scripts/01_scrape.py      # add --force to re-download
python yrbs/scripts/02_compile.py
```

## Outputs (`data/clean/`)

- `yrbs_prevalence_long.csv`: weighted % with SE and 95% CI for every yes/no indicator
  (`qn*` variables), by geography, year and group (Total, Sex, Grade, Race/ethnicity).
  `suppress = True` marks estimates based on fewer than 100 students (CDC's rule).
- `yrbs_prevalence_total_wide.csv`: overall % only, one column per year (Flourish-ready).
- `yrbs_microdata_1991_2025.parquet`: student-level records, all three geographies.
- `yrbs_microdata_chicago.csv`, `yrbs_microdata_illinois.csv`: student-level records.

## Method

Prevalence is weighted with CDC's survey weight. Standard errors use Taylor
linearization with CDC's stratum and PSU variables (strata nested in year); 95% CIs
are logit-transformed with t degrees of freedom = PSUs − strata. National results
match CDC's published estimates (e.g. "felt sad or hopeless": 42.3% in 2021, 39.7%
in 2023).

## Notes

- Chicago has no 2015 data. Not every question was asked every year or everywhere;
  those cells are blank.
- Chicago 2025 has the smallest sample of any year (892 students), and its rates drop
  sharply from 2023. Verify against CDC's YRBS Explorer before citing.
- Raw `.dat` files are stored with Git LFS (the national file is ~210 MB).
- CDC's file server sometimes returns a 404 page for files that exist; the scraper retries.
- New release every two years: bump `RELEASE` in `01_scrape.py`, then run with `--force`.
