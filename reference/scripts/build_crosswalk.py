"""
Build reference/schools/school_crosswalk.csv: one row per school with its
network, community area, ESB sub-district and location.

It flattens the three JSON lookups in reference/schools/ (kept as JSON because
the dashboards read them directly) into one CSV that's easy to join in R,
Python or Excel.

Inputs:
    reference/schools/school_groups.json     school_id -> {network, community_area}
    reference/schools/school_esb.json        school_id -> ESB sub-district ("10a")
    reference/schools/school_locations.json  school_id -> [latitude, longitude]

Output:
    reference/schools/school_crosswalk.csv
        school_id, network, community_area, esb_district, latitude, longitude

Run from the repo root:
    python reference/scripts/build_crosswalk.py
"""
import csv
import json
from pathlib import Path

# ---- Config -----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHOOLS_DIR = REPO_ROOT / "reference" / "schools"

GROUPS_FILE = SCHOOLS_DIR / "school_groups.json"
ESB_FILE = SCHOOLS_DIR / "school_esb.json"
LOCATIONS_FILE = SCHOOLS_DIR / "school_locations.json"
OUTPUT_FILE = SCHOOLS_DIR / "school_crosswalk.csv"

COLUMNS = ["school_id", "network", "community_area", "esb_district",
           "latitude", "longitude"]


# ---- Steps ------------------------------------------------------------------

def load_json(path):
    """Read one lookup file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_rows(groups, esb, locations):
    """One row per school that appears in any of the three lookups."""
    school_ids = sorted(set(groups) | set(esb) | set(locations), key=int)
    rows = []
    for sid in school_ids:
        group = groups.get(sid) or {}
        lat, lon = locations.get(sid) or (None, None)
        rows.append({
            "school_id": sid,
            "network": group.get("network"),
            "community_area": group.get("community_area"),
            "esb_district": esb.get(sid),
            "latitude": lat,
            "longitude": lon,
        })
    return rows


def write_csv(rows, path):
    """Write the crosswalk and report coverage, so gaps are visible."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.relative_to(REPO_ROOT)}: {len(rows)} schools")
    for col in COLUMNS[1:]:
        missing = sum(1 for r in rows if r[col] in (None, ""))
        print(f"  {col:<15} missing for {missing} schools")


# ---- Main -------------------------------------------------------------------

def main():
    groups = load_json(GROUPS_FILE)
    esb = load_json(ESB_FILE)
    locations = load_json(LOCATIONS_FILE)
    rows = build_rows(groups, esb, locations)
    write_csv(rows, OUTPUT_FILE)


if __name__ == "__main__":
    main()
