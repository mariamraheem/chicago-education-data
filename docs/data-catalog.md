# Data catalog

Every output file in the repo: what one row is, the key columns, the years
covered and where it comes from. Row counts and years are as of 2026-10-05.

To add a file: add a row to its dataset's table when you add the script that
writes it.

## Enrollment

Source: CPS 20th-day demographic reports. Folder: [`enrollment/`](../enrollment/).

| File | One row per | Key columns | Years | Rows |
|---|---|---|---|---|
| `data/clean/enrollment_general_clean.csv` | school x year | `Year`, `School ID`, `School Name`, `Network`, `Governance`, `School Type`, `Community Area`, `Total`, `PE`, `PK`, `K`, `Grade 1`-`Grade 12` | 2005-06 to 2025-26 | 13,984 |
| `data/clean/enrollment_race_clean.csv` | school x year | `Year`, `Network`, `School_ID`, `School_Name`, `<race>_n`, `<race>_pct` | 1999-00 to 2025-26 | 12,681 |
| `data/clean/enrollment_network_el_iep_aggregate.csv` | network x year | `Year`, `Network`, `Total_Enrollment`, EL / students with disabilities / economically disadvantaged `_N` and `_Pct` | 2011-12 to 2025-26 | 215 |
| `data/clean/enrollment_network_race_aggregates_<date>.csv` | network x year x race | `Year`, `Network`, `Race`, `No`, `Pct` | 2014-15 to 2025-26 | 2,262 |
| `data/clean/enrollment_race_aggregates_<date>.csv` | year x race (district) | `Year`, `Race`, `Count` | 2016-17 to 2025-26 | 81 |
| `data/clean/enrollment_dashboard_data.csv` (also in `dashboard/`) | school x year x grade | `school_year`, `school_id`, `school_name`, `network`, `grade`, `enrollment` | 2005-06 to 2025-26 | 112,941 |
| `dashboard/enrollment_race_trend.csv` | year x race | `school_year`, `race`, `count` | 2016-17 to 2025-26 | 81 |
| `dashboard/enrollment_network_race.csv` | network x year x race | `school_year`, `network`, `race`, `count`, `pct` | 2014-15 to 2025-26 | 2,262 |
| `dashboard/enrollment_network_demographics.csv` | network x year x metric | `school_year`, `network`, `metric`, `pct`, `n` | 2011-12 to 2025-26 | 615 |

Notes: `grade = ALL` in the dashboard file is CPS's reported total; don't add it
to the grade rows. The dated aggregate files are repeated copies from separate
runs.

## 5Essentials

Source: UChicago Impact, www.5-essentials.org. Folder: [`five_essentials/`](../five_essentials/).

| File | One row per | Key columns | Years |
|---|---|---|---|
| `data/clean/5essentials_long_<year>.csv.gz` | school x indicator x respondent group | `survey_year`, `school_id`, `level`, `indicator_slug`, `indicator`, `group_type`, `group`, `score`, `performance`, `score_status` | latest 5 |
| `data/clean/5essentials_scores_wide.csv` | school x year | `survey_year`, `school_id`, `school_name`, one column per essential/measure | latest 5 |
| `data/clean/5essentials_schools.csv` | school x year | `survey_year`, `school_id`, `school_name`, `school_type`, `address`, `student_/teacher_/parent_response_rate`, `overall_label` | latest 5 |
| `data/clean/5essentials_measures_dictionary.csv` | year x essential or measure | `survey_year`, `level`, `essential`, `indicator`, `asked_of`, `description` | 2022-2026 |
| `data/clean/5essentials_questions.csv` | year x measure x question | `survey_year`, `indicator`, `asked_of`, `question_code`, `question`, `answer_choices` | 2022-2026 |

Scores are 1-99. See [the 5Essentials README](../five_essentials/README.md#known-data-issues)
for known gaps (2025 in particular).

## YRBS

Source: CDC combined (SADC) datasets. Folder: [`yrbs/`](../yrbs/).

| File | One row per | Key columns | Years |
|---|---|---|---|
| `data/clean/yrbs_prevalence_long.csv` | geography x year x indicator x group | `geography`, `year`, `indicator`, `group_type`, `group`, weighted %, SE, 95% CI, `suppress` | 1991 to latest |
| `data/clean/yrbs_prevalence_total_wide.csv` | indicator x geography | overall % with one column per year (Flourish-ready) | 1991 to latest |
| `data/clean/yrbs_microdata_1991_2025.parquet` | student | all three geographies | 1991-2025 |
| `data/clean/yrbs_microdata_chicago.csv`, `_illinois.csv` | student | | 1991-2025 |

Don't report estimates where `suppress = True` (fewer than 100 students).
Chicago has no 2015 data.

## Budget

Source: CPS budget documents. Folder: [`budget/`](../budget/).

| File | One row per | Key columns | Years | Rows |
|---|---|---|---|---|
| `data/clean/budget_school_funding_clean.csv` | school x fiscal year x sheet | `Year`, `Source_File`, `Source_Sheet`, `School Name`, `School Type`, `Community Area`, `Network`, `Opportunity Index`, enrollment and allocation columns | FY2025-FY2027 | 1,936 |
| `data/clean/budget_dashboard_data.csv` (also in `dashboard/`) | school x fiscal year | same, trimmed for the dashboard | FY2025-FY2027 | 1,875 |
| `data/clean/_column_report.csv` | year x sheet x column | `Year`, `Source_File`, `Sheet`, `Column` | FY2025-FY2027 | 382 |
| `data/clean/district_managed_funds_clean.csv` | school x fiscal year | older output, no longer written | FY2026-FY2027 | 1,068 |

Budget files have no `school_id` column yet, so they join to other data by
school name. Adding the ID is on the [roadmap](roadmap.md).

## Monitor

Folder: [`monitor/`](../monitor/).

| File | What it is |
|---|---|
| `data/state.json` | Latest inventory: every file found on cps.edu with Last-Modified, ETag, size |
| `data/run_log.jsonl` | One line per scan |
| `data/diffs/` | What changed in each scan |

## Reference (shared)

Folder: [`reference/`](../reference/).

| File | One row per | Key columns |
|---|---|---|
| `schools/school_crosswalk.csv` | school | `school_id`, `network`, `community_area`, `esb_district`, `latitude`, `longitude` |
| `schools/school_groups.json`, `school_esb.json`, `school_locations.json` | school (JSON keyed by `school_id`) | same fields as the CSV |
| `geo/networks.geojson` | Network 1-17 | `network` |
| `geo/community_areas.geojson` | community area (77) | `community_area`, `area_num` |
| `geo/esb_districts.geojson` | ESB sub-district (20) | `sub` |

## Joining datasets

`school_id` is the common key for enrollment, 5Essentials and the reference
crosswalk. It's spelled differently in older enrollment files (`School ID`,
`School_ID`), and it's numeric in some files and text in others, so convert it
to text before joining.
