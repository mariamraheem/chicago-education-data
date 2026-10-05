# reference/ - shared lookups used by every dataset

Files that describe schools and places rather than any one dataset. Anything
that groups or maps schools (networks, community areas, ESB sub-districts,
locations, boundaries) should read from here, so every dashboard and analysis
uses the same assignments.

## Files

### `schools/`

| File | Key | Contents |
|---|---|---|
| `school_crosswalk.csv` | `school_id` | One row per school: `network`, `community_area`, `esb_district`, `latitude`, `longitude`. Flat version of the three JSON files below, for R / Python / Excel. |
| `school_groups.json` | `school_id` | `{"network": "Network 9", "community_area": "WASHINGTON PARK"}` |
| `school_esb.json` | `school_id` | Elected School Board sub-district, lowercase (`"10a"`) |
| `school_locations.json` | `school_id` | `[latitude, longitude]` |

`school_id` is CPS's 6-digit school ID as a string (e.g. `"609727"`). Some
charter campuses use 7-digit IDs (e.g. `4001151`).

Networks include CPS's citywide networks (`Charter`, `ISP`, `Options`,
`Contract`, `AUSL`, `SLA`) as well as geographic Networks 1-17. Only the
geographic ones have a boundary.

### `geo/`

| File | One feature per | Name property |
|---|---|---|
| `networks.geojson` | Network 1-17 (elementary 1-13, high school 14-17) | `network` (plus `network_name` for 1-13) |
| `community_areas.geojson` | Chicago's 77 community areas | `community_area` (uppercase), `area_num` |
| `esb_districts.geojson` | 20 ESB sub-districts (1a-10b) | `sub`, plus `district`, `name`, centroid `cx`/`cy` |

## Where these came from

Copied on 2026-10-05 from the
[`cps-enrollment-dashboard`](https://github.com/mariamraheem/cps-enrollment-dashboard)
repo (`docs/data/` and `docs/data/geo/`).

| File | How it's made in that repo |
|---|---|
| `school_groups.json` | Network and community area from CPS's 20th-day enrollment workbooks; gaps filled by a point-in-polygon join of school location against the boundaries (`scripts/build_geo.py`). |
| `networks.geojson`, `community_areas.geojson` | Chicago Data Portal downloads (`scripts/fetch_geo.py`: community areas `igwz-8jzy`, elementary networks `pnta-kuqa`, plus high school networks), simplified by `scripts/build_geo.py`. |
| `school_locations.json` | **Not built by a script** in that repo; source not recorded. |
| `school_esb.json`, `esb_districts.geojson` | **Not built by a script.** Mariam's ESB sub-district mapping. |

Two to-dos follow from this (both on the [roadmap](../docs/roadmap.md)):
record where the school locations came from, and add a script that rebuilds
the ESB assignment from the boundaries so it can be refreshed.

Until that repo is folded into this one, refresh these by copying its
`docs/data/school_groups.json`, `school_esb.json`, `school_locations.json`,
`docs/data/geo/networks.geojson`, `docs/data/geo/community_areas.geojson` and
`docs/data/esb_districts.json` (saved here as `esb_districts.geojson`), then
rebuild the flat file:

```bash
python reference/scripts/build_crosswalk.py
```

## Caveats

- These are **current** assignments. Schools change networks over time, so
  applying today's network to 2022 scores answers "how are today's Network 9
  schools doing", not "how did Network 9 do in 2022". The enrollment
  workbooks carry the network per year (`enrollment_general_clean.csv`) if
  you need the historical version.
- Community area names are uppercase here (`"MCKINLEY PARK"`).
