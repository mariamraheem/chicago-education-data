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
  scripts/02_build_wellbeing_dashboard.py
                              data for the student well-being dashboard (below)
  data/clean/                 scraper outputs (below)
  dashboard/student-wellbeing/
                              State of CPS student well-being by board district
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

## Student well-being dashboard

Live at `/student-wellbeing/` on the GitHub Pages site, built in the style of the NAEP
dashboard. Three tabs:

- **School Climate (5Essentials):** pick a view (board district, community area or
  network) and an area to follow any essential or measure over the last 5 surveys
  against the CPS median, with an optional comparison area. Below the main chart,
  small trend charts show every State of CPS well-being measure for that area, and
  an "every area over time" chart shows where it sits among the rest.
- **Student Health (YRBS):** Chicago trends for the last 10 years against Illinois and
  the U.S., or by race/ethnicity, sex or grade. YRBS has no school or location, so it
  can't be split by area.
- **Map View:** any measure and year by area, colored by gap to CPS or change since
  the first survey, with a ranked list. Clicking an area opens its trends.

How it's built:

- **Data:** `scripts/02_build_wellbeing_dashboard.py` writes `dashboard/student-wellbeing/data.json`
  (school scores for every essential and measure, simplified boundaries, YRBS).
  Standard library only. The Update Site workflow re-runs it on every deploy.
- **Method:** an area's score is the average (mean) of its schools' scores, as in the
  State of CPS report, with a toggle to switch to the median. Each school counts once;
  "CPS" is the average (or median) of all scored schools, calculated the same way.
  Areas with fewer than 5 scored schools are flagged and left out of rankings.
- **5Essentials levels:** scores are labelled Very Weak (1-19), Weak (20-39), Neutral
  (40-59), Strong (60-79) or Very Strong (80-99), the same cutoffs 5-essentials.org
  uses, classified on the rounded score shown. Trend charts shade these bands, the map's
  ranked list sits on the scale, and the map can also be colored by level.
- **Rating changes:** the School Climate tab shows whether an area's rating moved
  (e.g. Weak to Neutral) since the first survey, not just the point change: in the
  summary, the KPI card, a "Did the rating change?" table for every well-being measure,
  the small trend charts, and a chart of how many areas sit at each level by year.
  Themes, featured YRBS indicators and year limits are set in the script's config block.
- **Links:** `#esb-4B`, `#ca-Austin` (spaces as `_`, e.g. `#ca-West_Town`) or `#net-Network_9`
  open an area on the School Climate tab; `#health` and `#map` open those tabs.
- **Embedding** (for example on kidsfirstchicago.org):

  ```html
  <iframe id="k1c-wellbeing" src="https://mariamraheem.github.io/chicago-education-data/student-wellbeing/"
          title="Student well-being by school board district" style="width:100%;height:1800px;border:0" loading="lazy"></iframe>
  <script>
    // Optional: resize the iframe to fit its content (the page posts its height).
    addEventListener("message", e => {
      if (e.data && e.data.type === "k1c-embed-height") document.getElementById("k1c-wellbeing").style.height = e.data.height + "px";
    });
  </script>
  ```
