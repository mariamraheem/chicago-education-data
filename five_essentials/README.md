# five_essentials/ - CPS 5Essentials survey

School-level 5Essentials results for every CPS school, for the latest five survey
years (e.g. 2022-2026), scraped from www.5-essentials.org (UChicago Impact).

- **Source:** https://www.5-essentials.org/cps/5e/
- **Workflow:** `.github/workflows/update-5essentials.yml` (07:00 UTC on the 1st of Jul-Oct, when new results post)
- **Run time:** about 650 schools x 5 years of page requests, 15-30 minutes

```bash
python five_essentials/scripts/01_scrape.py                    # latest 5 years
python five_essentials/scripts/01_scrape.py --years 2025 2026  # specific years
python five_essentials/scripts/01_scrape.py --workers 2        # gentler on the site
python five_essentials/scripts/01_scrape.py --dictionary-only  # only the measure/question dictionary
```

No browser needed: each report page embeds its data as JSON
(`<script id="app_data" data-data=...>`), which the scraper reads directly.

## Folder

```
five_essentials/
  scripts/01_scrape.py        the scraper (writes data/clean/)
  data/clean/                 scraper outputs (below)
  apps/explorer/              Shiny app: trends by district, network, community
                              area, ESB sub-district and school, plus a map
```

## Outputs (`data/clean/`)

| File | Grain | Notes |
|---|---|---|
| `5essentials_long_<year>.csv.gz` | school x survey year x indicator x respondent group | Every essential, the overall rating and every measure, for all respondents, CPS and similar-school benchmarks, and breakouts (gender, grade, race/ethnicity, IEP, ELL, free/reduced lunch). One gzipped file per year. |
| `5essentials_scores_wide.csv` | school x survey year | All-respondent scores, one column per essential or measure. |
| `5essentials_schools.csv` | school x survey year | School type, address, overall rating label, student/teacher/parent response rates. |
| `5essentials_measures_dictionary.csv` | survey year x essential or measure | `level` (essential/measure), `essential`, `indicator`, `asked_of` (Student or Teacher), `description`, `question_stem`. |
| `5essentials_questions.csv` | survey year x measure x question | Question text, order, code and answer choices. |

Column notes:

- `score` is 1-99. `performance` is the site's band: Very Weak (1-19), Weak (20-39),
  Neutral (40-59), Strong (60-79), Very Strong (80-99).
- `score_status` explains a missing score: `no_report`, `not_eligible`, `P`.
- `flag` is the site's second value for each score, kept as-is.

In the dictionary, `asked_of` is what keeps teacher and student measures apart
in the explorer app. The five essentials and the overall rating combine both surveys, so their
`asked_of` is blank.

## Explorer app

See [apps/explorer/README.md](apps/explorer/README.md).

## Known data issues

- **Measure codes change between years** (e.g. `engg` became `engg24`); compare
  years by the `indicator` name, not the code.
- **2020 had no survey.**
- **Grit was only reported in 2022 and 2023.**
- **2025 is missing the overall 5Essentials score, Ambitious Instruction and six
  student measures** (Academic Engagement, Academic Personalism, Academic Press,
  Classroom Rigor, Course Clarity, Peer Support for Academic Work). Supportive Environment has scores for only 164 schools that year;
  teacher measures, Safety and Student Peer Relationships are complete. Check
  whether the site didn't report these or the scraper missed them.
- **The overall 5Essentials row in the dictionary** has a site template error
  as its description for 2022-2024; the explorer replaces it with its own text.
- **Student Peer Relationships is missing in 2024.**
- **High school Academic Engagement** has medians of 91-99 in 2022-2024, then
  about 70 in 2026. Worth checking for a scoring change.
- Scores are suppressed by the source when response rates are too low; check
  the response-rate columns in `5essentials_schools.csv` before comparing
  small schools.
