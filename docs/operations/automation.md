# Automation (GitHub Actions)

Each dataset has a workflow that runs its scripts and commits new data to
`main`. A separate workflow builds and deploys the website. All of them can
also be started by hand: **Actions** tab, pick the workflow, **Run workflow**.

## Schedules

| Workflow | Runs | Steps | Commits |
|---|---|---|---|
| `update-enrollment.yml` | 06:00 UTC, 1st of every month | `enrollment/scripts/01`-`05` | `enrollment/data`, `enrollment/dashboard` |
| `update-budget.yml` | 06:15 UTC, 1st of every month | `budget/scripts/01`-`03` | `budget/data`, `budget/dashboard` |
| `update-yrbs.yml` | 06:30 UTC, 1st of Jan/Apr/Jul/Oct | `yrbs/scripts/01`, `02` (manual run can force re-download) | `yrbs/data` |
| `update-5essentials.yml` | 07:00 UTC, 1st of Jul-Oct | `five_essentials/scripts/01_scrape.py` (manual run can pick years) | `five_essentials/data` |
| `update-monitor.yml` | 07:00 UTC Mondays | `monitor/01_scan.py` | `monitor/data` |
| `update-dashboard.yml` | After any workflow above finishes, on pushes to site/data paths, or by hand | Assembles the site, builds the monitor page and JSON API | Deploys to GitHub Pages (no commit) |

07:00 UTC is 2:00 am Chicago time in summer (CDT) and 1:00 am in winter (CST).

Most scheduled runs find nothing new and commit nothing. That's expected:
CPS posts enrollment in the fall, budgets in the summer, 5Essentials results in
late summer, and CDC releases YRBS every two years.

## The website

`update-dashboard.yml` is the only workflow that deploys Pages. It builds:

| Path | From |
|---|---|
| `/` and `/explore/` | `site-landing/` |
| `/enrollment/` | `enrollment/dashboard/` |
| `/budget/` | `budget/dashboard/` |
| `/monitor/` | `monitor/02_export_api.py` and `03_render_dashboard.py` |
| `/api/` | `scripts/build_site_manifest.py` (JSON copies of the dashboard data, a manifest, and trend summaries from `scripts/build_trends.py`) |

One-time setup: repo **Settings, Pages, Source: GitHub Actions**.

## When a run fails

1. Open the failed run in the Actions tab and read the step that failed.
   Scripts print what they downloaded, skipped and wrote.
2. Source site changes are the usual cause (a renamed link, a new workbook
   layout). Fix the scraper or cleaner, then run the workflow by hand.
3. Push conflicts: the data workflows retry `git pull --rebase` a few times.
   If two finish at once and both fail, re-run one.

## Running locally instead

Every workflow step is a plain script you can run from the repo root (see each
dataset's README). Pull first; the bots commit to `main` often.
