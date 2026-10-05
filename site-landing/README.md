# site-landing/ - website home page

Static pages copied to the root of the GitHub Pages site by
`update-dashboard.yml`:

- `index.html` - home page: overview, student health (YRBS), school climate
  (5Essentials), and cards showing when each dataset was last refreshed.
- `explore/index.html` - Explore page.

They read JSON from `/api/` (built by `scripts/build_site_manifest.py` and
`scripts/build_trends.py`), so they show "no data yet" for a dataset until its
files exist. Dataset dashboards (`enrollment/dashboard/`, `budget/dashboard/`)
are published to their own paths alongside these pages.
