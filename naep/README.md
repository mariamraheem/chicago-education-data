# naep/ - NAEP (Nation's Report Card) average scale scores

Average scale scores in math and reading, grades 4, 8 and 12, for Chicago, every
other TUDA district, the large-city average, Illinois and the nation, by student
group. Pulled from NCES's NAEP Data Service API. This replaces the hand-built
`NAEP_Compiled_Wide.xlsx` behind the 2026 NAEP brief and the Chicago NAEP Explorer
(Shared drive: K1C DATA GOVERNANCE/NAEP).

- **Source:** https://www.nationsreportcard.gov/api_documentation.aspx
- **Coverage:** 1990 to 2024 (national); TUDA districts from the year each joined
- **Workflow:** `.github/workflows/update-naep.yml` (quarterly; NAEP releases every two years)

## Steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | One API call per subject x grade x student group x year, all jurisdictions at once (falls back to one jurisdiction at a time if a call errors). Skips files already present; `--force` re-pulls. | `data/raw/naep_<subject>_g<grade>_<variable>.json` |
| 2. Compile | `scripts/02_compile.py` | Maps API labels to student groups, blanks scores NAEP marks as not reportable, pivots to the workbook layout. | `data/clean/naep_scores_long.csv`, `naep_scores_wide.csv` |
| 3. Validate | `scripts/03_validate.py` | Checks scraped scores against the 2026 brief's figure data (and the hand-built workbook with `--handbuilt`). Fails if anything doesn't line up. | nothing |

```bash
python naep/scripts/01_scrape.py
python naep/scripts/02_compile.py
python naep/scripts/03_validate.py
python naep/scripts/03_validate.py --handbuilt "path/to/NAEP_Compiled_Wide.xlsx"
```

## Outputs

| File | One row per | Notes |
|---|---|---|
| `data/clean/naep_scores_long.csv` | year x jurisdiction x subject x grade x student group | `average_scale_score`, `is_displayable`, `error_flag`, plus the API's own codes and labels |
| `data/clean/naep_scores_wide.csv` | year x jurisdiction x subject x grade | same columns as the hand-built workbook, one column per student group |

Student groups: all students; race/ethnicity (`SDRACE`); sex; NSLP eligibility
(`SLUNCH3`, shown as economically disadvantaged); English learner (`LEP`);
disability status (`IEP`, includes 504 plans).

## Reference data

`data/reference/brief_figures/` holds the figure data from the 2026 NAEP brief
(fig 1: Chicago 2003-2024; figs 3-4: all TUDAs, 2024). `03_validate.py` checks
against these. The hand-built workbook matches all 128 of those values.

## Apps

- `apps/explorer/app.R` - Chicago's NAEP Story Shiny app (companion to the brief).
  It reads `NAEP_Compiled_Wide.xlsx` from its own folder. `apps/explorer/update_data.R`
  writes that file from `naep_scores_wide.csv`; the copy is git-ignored.
  The shinyapps.io `manifest.json` stays on the shared drive.

## Known data issues

- **Not run against the live API yet.** The scripts were tested against mock API
  responses built from the hand-built workbook. The first real run (in GitHub
  Actions) needs checking: `02_compile.py` prints any student-group labels it
  doesn't recognize, and `03_validate.py` must pass before the app switches over.
- **Label text for `SLUNCH3`, `LEP` and `IEP` isn't in the API docs.** The
  mapping in `02_compile.py` (`GROUP_LABELS`) covers the likely variants; add any
  the first run reports.
- **NAEP revises results.** The API docs say results can change over time, so
  re-pull with `--force` before a new publication rather than trusting old raw files.
- **No significance testing.** These are point estimates. Use NAEP's Data Explorer
  for significance tests between jurisdictions or years.
- **Grade 12** has national data only (no TUDA or state samples), and math uses
  the 2005 framework scale (`MWPCM`).
