# illinois_report_card/ - Illinois Report Card (ISBE) Public Data Set

District- and school-level data from ISBE's annual Illinois Report Card
Public Data Set: enrollment and demographics, summative designations,
academic proficiency and growth, ACT/SAT, CTE, discipline, finance, KIDS
kindergarten readiness, special education, and teacher out-of-field
assignment, for every Illinois public school and district. Scraped directly
from ISBE (not from Mariam's Google Drive `K1C DATA GOVERNANCE/
StateOfEducation/Data/ILRC [temp]` copies, which were used only to discover
the schema while building this).

- **Source:** https://www.isbe.net/pages/illinois-state-report-card-data.aspx
- **Coverage:** 2017-2018 to 2025-2026 (one workbook per school year, all 9
  pulled directly from ISBE)
- **Workflow:** `.github_workflow/update-illinois-report-card.yml` (monthly
  cron; not yet installed into `.github/workflows/` -- see Known gaps)

## Sheets covered

Sheet names drift year to year -- see **Known data issues** below. Each row
is the canonical output tag, the years it's actually present (not every
sheet exists every year), and what it covers.

| Tag | Years present | Covers |
|---|---|---|
| `general` / `general2` | 2017-18 to 2025-26 / 2024-25 to 2025-26 | Enrollment, demographics, summative designations, attendance, dropout, graduation (4/5/6-yr), teacher retention/experience/salary, class size, AP/IB/dual-credit, Five Essentials survey, CRDC rates (suspension, expulsion, arrests, chronic absenteeism, PreK, advanced coursework access), gifted education |
| `elamathscience` / `elamathscience2` | 2017-18 to 2025-26 / 2024-25 to 2025-26 | ELA/Math/Science proficiency AND student growth percentile, total + by grade (3-8) + full subgroup set, including Former EL starting 2025-26 |
| `iar` / `iar2` | 2018-19 to 2025-26 / 2021-22 to 2023-24 | IAR-specific ELA/Math proficiency rate (differs slightly from the `elamathscience` rate -- see Known data issues) |
| `parcc` | 2017-18 only | Predecessor to IAR |
| `act` | 2024-25 to 2025-26 | ACT/PreACT 9/PreACT 10 scores, HS Assessment ELA/Math participation and proficiency by subgroup |
| `sat` | 2017-18 to 2023-24 | SAT scores and participation/proficiency -- the HS assessment ACT replaced in 2024-25 |
| `isa` | 2017-18 to 2025-26 | Illinois Science Assessment (grade 5/8/11) |
| `dlm` / `dlm2` | 2017-18 to 2025-26 / 2021-22 to 2025-26 | Alternate assessment for students with significant cognitive disabilities (Dynamic Learning Maps) |
| `cte` / `cte2` | 2021-22 to 2025-26 / 2024-25 to 2025-26 | Career & Technical Education: Perkins accountability, participants/concentrators by career cluster |
| `discipline` | 2022-23 to 2025-26 | Incidents by action, subgroup, offense type, duration |
| `finance` | 2017-18 to 2025-26 | Per-pupil spending, revenue by source, expenditure by function, EBF tier |
| `kids` | 2023-24 to 2025-26 | Kindergarten Individual Development Survey readiness rates |
| `sped` | 2024-25 to 2025-26 | Placement/LRE rates, State Performance Plan indicators |
| `teacher_oof` | 2022-23 to 2023-24 | Out-of-field teachers by poverty level (folded into `general` from 2024-25 on -- see table above) |

## Steps

| Step | Script | What it does | Writes |
|---|---|---|---|
| 1. Scrape | `scripts/01_scrape.py` | Scrapes the ISBE report card page for "`<year>` Report Card Public Data Set" links and downloads any not already in `data/raw/`. `--overwrite` re-downloads. | `data/raw/<school_year>.xlsx` |
| 2. Clean (General) | `scripts/02_clean.py` | Splits `General`/`General (2)` into district-level and school-level rows (see **Known data issues**), tags with `school_year`, combines across years. | `data/clean/illinois_report_card_general*_clean.csv` |
| 3. Clean (everything else) | `scripts/03_clean_categories.py` | Same split/tag/combine logic (shared with `02_clean.py`) for every other sheet in the table above, resolving each year's sheet-name drift via an alias list. | `data/clean/illinois_report_card_<tag>_{district,school}_clean.csv` |

```bash
python illinois_report_card/scripts/01_scrape.py
python illinois_report_card/scripts/02_clean.py
python illinois_report_card/scripts/03_clean_categories.py
```

Raw workbooks are committed (large ones through Git LFS, see
`.gitattributes`), so every Public Data Set ISBE has published stays
available here even if ISBE reorganizes its page or retires an old link.

## Outputs

Each clean file is wide -- columns are whatever that year's sheet had, and
column sets differ year to year (ISBE adds, removes, and renames fields
most years). Combining years with `pd.concat` keeps every column seen in
any year, filled with blanks where a given year didn't have it -- nothing
is harmonized into a single fixed schema yet (see Known gaps). The
dashboard build picks specific columns per chart rather than relying on a
fixed schema across years.

See [docs/data-catalog.md](../docs/data-catalog.md) once an entry is added
there (not yet done -- see Known gaps).

## Known data issues

- **District-vs-school split column isn't consistent year to year.** Most
  years have an exact `Type` column (`Statewide` / `District` / `School`).
  Starting 2024-2025, ISBE added a `Level` column instead, that also
  serves as an authoritative discriminator -- both clean scripts share one
  `find_split_column()` that prefers `Type`, then `Level`, before falling
  back to any column whose name merely contains "type" (e.g. `District
  Type`), because that fallback is only safe when it's a true
  `Type`-equivalent and not e.g. a district's own governance category,
  which every one of that district's own school rows also carries.
- **Two different ELA/Math proficiency rates exist and don't match
  exactly**: the `elamathscience` sheet's `% ELA/Math Proficiency` vs. the
  `iar` sheet's `IAR ELA/Math Proficiency Rate - Total`. Spot-checked on
  one district: 39.7% vs. 40.00% ELA, 23.9% vs. 24.10% Math. ISBE doesn't
  document the exact reconciliation. Open question for State of CPS: which
  to treat as primary, or show both with a note.
- **Column sets are not harmonized across years.** Both clean scripts
  concatenate each year's raw columns as-is; a given metric may have a
  different column name in different years and isn't mapped to one
  canonical name yet, unlike `enrollment/`'s `RACE_COLUMN_MAP`. Anyone
  joining across years should check column names per year first.
- **Former EL** is a real assessment subgroup (not just an enrollment
  count) starting 2025-26 only -- present in `elamathscience`, `iar`, and
  `act`. Earlier years only report it as an enrollment count, in `general`.

## Known gaps

- **No compile/dashboard-data step yet** (no `04_build_dashboard_data.py`),
  and no registry or data-catalog entry -- this is scrape + clean only. The
  dashboard site (separate from this pipeline) reads these clean CSVs
  directly for now.
- **Not yet installed as a scheduled workflow.** The workflow file exists
  at `.github_workflow/update-illinois-report-card.yml` (monthly cron,
  same cadence as `enrollment/update-enrollment.yml`) but needs to be moved
  into `.github/workflows/` in the actual repo to take effect.
- **No school-ID crosswalk join.** RCDTS (ISBE's school/district identifier)
  isn't mapped to CPS's own `school_id` yet; that would let this join to
  `enrollment/` and `five_essentials/` via `reference/`.
- **CTE/Discipline/Finance/KIDS/SPED/ACT only cover the years each sheet
  has existed** (see the coverage table above) -- these are genuinely new
  ISBE reporting additions in most cases, not gaps in this pipeline.
