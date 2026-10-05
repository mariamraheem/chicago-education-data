# Roadmap: one home for Chicago education data

Goal: every public education dataset K1C uses lives in this repo, with the same
layout, shared school lookups, a catalog, and documentation, so anyone can find
a number, see where it came from, and reuse it.

Status key: **Done**, **Next**, **Later**.

## Phase 1: Document and share (Done, 2026-10-05)

- **Done:** Front-door README with a table of every dataset.
- **Done:** READMEs for `enrollment/`, `budget/`, `monitor/`, `reference/`,
  `five_essentials/apps/explorer/`, and the support folders.
- **Done:** [data-catalog.md](data-catalog.md), [conventions.md](conventions.md),
  [operations/automation.md](operations/automation.md).
- **Done:** `reference/` folder with the school crosswalk (network, community
  area, ESB sub-district, location) and map boundaries, copied from
  `cps-enrollment-dashboard`, plus `reference/scripts/build_crosswalk.py`.
- **Done:** 5Essentials Explorer Shiny app moved to
  `five_essentials/apps/explorer/`, reading repo outputs through `update_data.R`.
- **Done:** Registry entries for `five_essentials` and `yrbs` completed so the
  registry tests pass; `reference_schools` entry added.

## Phase 2: Fold in `cps-enrollment-dashboard` (Next)

That repo stays live and on its weekly schedule the whole time. Nothing there
is turned off until this repo publishes the same dashboard.

1. **Compare the two enrollment pipelines.** Both scrape the same CPS
   demographics page. Check that district totals match year by year
   (`docs/data/summary.json` there vs. `enrollment/data/clean/` here) and note
   where each handles old layouts better (that repo parses totals back to
   2005-06 and grade bands from 2016-17).
2. **Move its builders in** as numbered steps in `enrollment/scripts/`
   (e.g. `06_build_summary.py`, `07_build_schools.py`), reading the raw files
   already here so CPS is scraped once.
3. **Move its geography steps** (`fetch_geo.py`, `build_geo.py`) to
   `reference/scripts/`, so `reference/` rebuilds itself instead of being
   copied.
4. **Publish its dashboard** at `/enrollment/` on this repo's site (or
   `/enrollment-v2/` while both exist).
5. **Then decide** whether to archive the old repo or keep it as a redirect.

## Phase 3: Make shared data self-updating (Later)

- **School locations:** record where `school_locations.json` came from, or
  rebuild it from the CPS school profile API (`api.cps.edu`), which also has
  official names.
- **ESB sub-districts:** add a script that assigns schools to ESB
  sub-districts by point-in-polygon from `reference/geo/esb_districts.geojson`.
- **Historical networks:** build a school x year network table from
  `enrollment_general_clean.csv`, so analyses of past years can use the network
  a school was in at the time.
- **Budget school IDs:** add `school_id` to the budget clean files (by matching
  names to the crosswalk) so budget joins to enrollment and 5Essentials.

## Phase 4: Data quality (Later)

- **5Essentials:** investigate the 2025 gaps and high school Academic
  Engagement (see [five_essentials/README.md](../five_essentials/README.md#known-data-issues)).
- **Enrollment:** stop writing dated duplicate aggregate files; add the
  school-level EL/IEP clean file the Streamlit app expects.
- **Budget:** replace the generic cleaner with column names from the real
  workbooks; drop the section-header columns.
- **Registry and contracts:** add contracts and validation thresholds for
  5Essentials and YRBS, like the one for 20th Day Membership.

## Ideas, not yet planned

- More datasets: Illinois Report Card (ISBE), NAEP, attendance and graduation
  metrics from CPS's School Data pages.
- One `analysis/` area for one-off notebooks and briefs that read from the
  clean files, so analysis code doesn't end up inside pipeline folders.
