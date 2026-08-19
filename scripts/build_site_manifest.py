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


def _safe_float(value: str | None) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def enrollment_headline(rows: list[dict]) -> str | None:
    """One-line year-over-year takeaway for the landing page card -- so a
    new data drop is worth something at a glance, before anyone opens the
    dashboard. Mirrors the enrollment dashboard's own Highlights math
    (sum "enrollment" per school_year, compare the latest two years)."""
    totals: dict[str, float] = {}
    for row in rows:
        year = row.get("school_year")
        if not year:
            continue
        totals[year] = totals.get(year, 0.0) + _safe_float(row.get("enrollment"))
    years = sorted(totals)
    if len(years) < 2:
        return None
    latest, prev = years[-1], years[-2]
    diff = totals[latest] - totals[prev]
    pct = (diff / totals[prev] * 100) if totals[prev] else 0.0
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "●"
    sign = "+" if diff > 0 else ""
    return f"{arrow} {sign}{diff:,.0f} students ({sign}{pct:.1f}%) vs {prev}"


def budget_headline(rows: list[dict]) -> str | None:
    """Same idea for Budget: unique schools budgeted, latest fiscal year
    vs. the one before it."""
    counts: dict[str, set[str]] = {}
    for row in rows:
        year = row.get("Year")
        name = row.get("School Name")
        if not year or not name:
            continue
        counts.setdefault(year, set()).add(name)
    years = sorted(counts)
    if len(years) < 2:
        return None
    latest, prev = years[-1], years[-2]
    diff = len(counts[latest]) - len(counts[prev])
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "●"
    sign = "+" if diff > 0 else ""
    return f"{arrow} {sign}{diff} schools budgeted vs FY{prev} (FY{latest}: {len(counts[latest])})"


HEADLINE_FUNCS = {
    "enrollment": enrollment_headline,
    "budget": budget_headline,
}


def build_domain(domain: Domain, generated_at: str) -> dict:
    out_dir = API_DIR / domain.id
    files_meta = []
    primary_row_count = None
    headline = None

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
            headline_fn = HEADLINE_FUNCS.get(domain.id)
            if headline_fn:
                try:
                    headline = headline_fn(rows)
                except Exception:
                    headline = None

    return {
        "id": domain.id,
        "label": domain.label,
        "headline": headline,
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
