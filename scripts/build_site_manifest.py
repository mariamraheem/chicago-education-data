"""
Builds the JSON "export API" and the manifest the landing page
(site-landing/index.html) reads for its "what was refreshed and when"
summary cards.

Run this LAST, after each domain's own build script(s) have produced their
dashboard-ready CSVs, and after the site/<domain>/ directories have been
populated (order between those two doesn't actually matter -- this script
creates whatever directories it needs).

For each domain listed in DOMAINS below, every file in `data_files` that
exists gets converted to plain JSON (list of row objects) under
site/api/<domain id>/<name>.json -- fetchable directly, no auth, from
anywhere (GitHub Pages serves static files with permissive CORS headers).
The first entry in `data_files` is treated as that domain's primary
dataset for the landing page's row-count stat.

Writes: site/api/manifest.json
        site/api/<domain id>/<name>.json (one per existing data file)
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
API_DIR = SITE_DIR / "api"


@dataclass
class DataFile:
    filename: str
    api_name: str
    label: str


@dataclass
class Domain:
    id: str
    label: str
    description: str
    tab_url: str
    refresh_workflow_url: str
    source_dir: Path
    data_files: list[DataFile]


DOMAINS = [
    Domain(
        id="enrollment",
        label="Enrollment",
        description="20th Day Membership, race, English Learners, Students with Disabilities.",
        tab_url="enrollment/index.html",
        refresh_workflow_url=(
            "https://github.com/mariamraheem/chicago-education-data/"
            "actions/workflows/update-enrollment.yml"
        ),
        source_dir=REPO_ROOT / "enrollment" / "dashboard",
        data_files=[
            DataFile("enrollment_dashboard_data.csv", "dashboard_data", "Enrollment by school/year/grade"),
            DataFile("enrollment_race_trend.csv", "race_trend", "District race trend"),
            DataFile("enrollment_network_race.csv", "network_race", "Network race breakdown"),
            DataFile("enrollment_network_demographics.csv", "network_demographics", "EL/SWD/Econ. Disadvantaged by network"),
        ],
    ),
    Domain(
        id="budget",
        label="Budget",
        description="District Managed Funds budget workbooks.",
        tab_url="budget/index.html",
        refresh_workflow_url=(
            "https://github.com/mariamraheem/chicago-education-data/"
            "actions/workflows/update-budget.yml"
        ),
        source_dir=REPO_ROOT / "budget" / "dashboard",
        data_files=[
            DataFile("budget_dashboard_data.csv", "dashboard_data", "District Managed Funds"),
        ],
    ),
]


def csv_to_json_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_domain(domain: Domain, generated_at: str) -> dict:
    out_dir = API_DIR / domain.id
    files_meta = []
    primary_row_count = None

    for i, data_file in enumerate(domain.data_files):
        source_path = domain.source_dir / data_file.filename
        if not source_path.exists():
            continue
        rows = csv_to_json_rows(source_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{data_file.api_name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f)
        files_meta.append({
            "label": data_file.label,
            "url": f"api/{domain.id}/{data_file.api_name}.json",
            "row_count": len(rows),
        })
        if i == 0:
            primary_row_count = len(rows)

    return {
        "id": domain.id,
        "label": domain.label,
        "description": domain.description,
        "tab_url": domain.tab_url,
        "refresh_workflow_url": domain.refresh_workflow_url,
        "last_refreshed": generated_at if files_meta else None,
        "row_count": primary_row_count,
        "has_data": primary_row_count not in (None, 0),
        "api": files_meta,
    }


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "generated_at": generated_at,
        "sources": [build_domain(d, generated_at) for d in DOMAINS],
    }
    API_DIR.mkdir(parents=True, exist_ok=True)
    with open(API_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {API_DIR / 'manifest.json'}")
    for source in manifest["sources"]:
        print(f"  {source['id']}: {len(source['api'])} file(s), row_count={source['row_count']}")


if __name__ == "__main__":
    main()
