# five_essentials/ — CPS 5Essentials survey

School-level 5Essentials results for every CPS school, for the latest five survey
years (e.g. 2022–2026), scraped from www.5-essentials.org.

```bash
python five_essentials/scripts/01_scrape.py                    # latest 5 years
python five_essentials/scripts/01_scrape.py --years 2025 2026  # specific years
```

No browser needed: each report page embeds its data as JSON
(`<script id="app_data" data-data=...>`), which the scraper reads directly.

## Outputs (`data/clean/`)

- `5essentials_long.csv`: one row per school × survey year × indicator × group.
  Covers the 5 essentials, the overall rating and every measure, for all respondents,
  CPS and similar-school benchmarks, and the site's breakouts (gender, grade,
  race/ethnicity, IEP, ELL, free/reduced lunch). `score` is 1–99; `performance` is the
  site's band (Very Weak … Very Strong); `score_status` explains missing scores
  (`no_report`, `not_eligible`, `P`). `flag` is the site's second value for each score,
  kept as-is.
- `5essentials_scores_wide.csv`: all-respondent scores, one row per school-year and one
  column per essential or measure.
- `5essentials_schools.csv`: school type, address and student/teacher/parent response
  rates by year.

## Notes

- Measure codes change between years (e.g. `engg` became `engg24`); use the
  `indicator` name to compare across years.
- 2020 had no survey.
- A full run is roughly 650 schools × 5 years of page requests; it takes 15–30 minutes.
