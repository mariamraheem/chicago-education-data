# 5Essentials Explorer (Shiny)

Interactive trends and maps of 5Essentials scores, styled like the
"Chicago's NAEP Story" dashboard.

| Tab | Shows |
|---|---|
| Overview | What the survey is and how to read the app |
| Map | One measure for one year by network, community area, ESB sub-district or school, colored by 5Essentials band (or a relative scale). Click an area or school to see its trend against all CPS schools. |
| District | Median (or mean) of all CPS school scores, 2022-2026 |
| Network / Community Area / ESB Sub-district | The same for one group of schools |
| School | One school's scores and its survey response rate |

Every chart shows measures from **one respondent group only** (Teacher survey,
Student survey, or the composite Essential scores), so teacher and student
measures are never mixed. Definitions come from the measures dictionary.

## Run it

From the repo root:

```bash
Rscript five_essentials/apps/explorer/update_data.R   # copy current data in
R -e 'shiny::runApp("five_essentials/apps/explorer")'
```

R packages: `shiny`, `bslib`, `dplyr`, `tidyr`, `plotly`, `ggplot2`, `ggrepel`,
`stringr`, `jsonlite`.

```r
install.packages(c("shiny", "bslib", "dplyr", "tidyr", "plotly", "ggplot2",
                   "ggrepel", "stringr", "jsonlite"))
```

## Where its data comes from

The app reads only from its own `data/` and `www/geo/` folders, so the folder can
be deployed on its own. `update_data.R` fills them from the repo:

| App file | Copied from |
|---|---|
| `data/5essentials_scores_wide.csv`, `5essentials_schools.csv`, `5essentials_measures_dictionary.csv` | `five_essentials/data/clean/` (scraper output) |
| `data/school_groups.json`, `school_esb.json`, `school_locations.json` | `reference/schools/` |
| `www/geo/*.geojson` | `reference/geo/` |

`data/` and `www/geo/` are git-ignored because they're copies. Run
`update_data.R` after a fresh clone, after the scraper runs, or when
`reference/` changes.

## Deploy to shinyapps.io

```r
rsconnect::deployApp("five_essentials/apps/explorer", appName = "5essentials")
```

Run `update_data.R` first so the deployed copy has current data.

## Settings worth knowing (top of `app.R`)

- `GROUP_LEVELS` - which grouping tabs appear. Add a column to the school
  crosswalk and a line here to add a new grouping.
- `EXCLUDE_INDICATORS` - measures to leave out (none right now). Known data
  gaps are listed in [../../README.md](../../README.md#known-data-issues).
- `MAX_SERIES` - most lines in one chart (6).
- `SCORE_BANDS`, `BAND_COLORS` - map colors.
- `MAP_STYLE` - basemap (`carto-positron`, no token needed).
- Optional logo: put `k1c_logo.png` in `www/`.

## How the numbers are built

- Group views take the median (or mean) of the school scores in the group for
  each year, with the number of schools shown on hover and in the table. A
  school-type filter limits which schools count.
- Network, community area and ESB sub-district come from
  `reference/schools/`, the same assignments the enrollment dashboard uses.
  Charter, ISP, Options and Contract are citywide networks with no boundary,
  so the map lists them under it instead of drawing them.
- A gap in a line means the measure wasn't reported that year.
