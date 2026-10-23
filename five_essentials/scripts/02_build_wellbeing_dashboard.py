"""
Build the data file for the Student Well-being dashboard (State of CPS).

The dashboard has three tabs:
    School climate   5Essentials trends for any ESB sub-district, community area or
                     network vs CPS, last 5 surveys
    Student health   Chicago YRBS trends vs Illinois and the U.S., by race, sex and
                     grade, last 10 years (YRBS can't be split below the district)
    Map              5Essentials by area for one measure and year

The page computes area medians itself from the school scores in this file, so any
grouping in the crosswalk can be added without re-running anything else.
Standard library only, so it runs inside the Update Site workflow with no installs.

Inputs:
    five_essentials/data/clean/5essentials_long_<year>.csv.gz   (from 01_scrape.py)
    five_essentials/data/clean/5essentials_schools.csv
    five_essentials/data/clean/5essentials_measures_dictionary.csv
    reference/schools/school_crosswalk.csv                      school -> network / community area / ESB
    reference/geo/{esb_districts,community_areas,networks}.geojson
    yrbs/data/clean/yrbs_prevalence_long.csv                    (from yrbs/scripts/02_compile.py)

Output:
    five_essentials/dashboard/student-wellbeing/data.json

Usage:
    python five_essentials/scripts/02_build_wellbeing_dashboard.py
"""
import csv
import glob
import gzip
import json
import math
from pathlib import Path

# ---------------- Config ----------------
REPO_ROOT = Path(__file__).resolve().parents[2]
FE_DIR = REPO_ROOT / "five_essentials" / "data" / "clean"
CROSSWALK = REPO_ROOT / "reference" / "schools" / "school_crosswalk.csv"
GEO_DIR = REPO_ROOT / "reference" / "geo"
YRBS_FILE = REPO_ROOT / "yrbs" / "data" / "clean" / "yrbs_prevalence_long.csv"
OUT_FILE = REPO_ROOT / "five_essentials" / "dashboard" / "student-wellbeing" / "data.json"

FE_YEARS = 5                 # most recent 5Essentials surveys
YRBS_YEARS = 10              # YRBS years back from the latest survey (Chicago has no 2015)
YRBS_MIN_WAVES = 3           # list an indicator only if Chicago asked it in this many surveys
MAP_TOLERANCE = 0.0007       # boundary simplification, in degrees (~70 m)
MAP_MIN_POINTS = 150         # rings smaller than this are kept as drawn (the ESB file is already coarse)

# The State of CPS Student Well-being measures, in the section's order. Every other
# essential and measure is included too, under "Other essentials and measures".
THEMES = [
    ("Student", "Safety", ["Safety", "School Safety"]),
    ("Student", "Belonging", ["Student-Teacher Trust", "Student Peer Relationships"]),
    ("Student", "Support beyond school", ["Parent Supportiveness", "School Connectedness"]),
    ("Student", "Wellbeing", ["Emotional Health", "Human & Social Resources in the Community"]),
    ("Student", "Study habits", ["Rigorous Study Habits"]),
    ("Teacher", "Classroom", ["Classroom Disruptions", "Collective Responsibility", "Student Responsibility"]),
    ("Teacher", "Family engagement", ["Parent Influence on Decision Making in Schools",
                                      "Teacher-Parent Trust", "Parent Involvement in School"]),
]
ESSENTIAL_RESPONDENT = {"Ambitious Instruction": "Student", "Supportive Environment": "Student",
                        "Collaborative Teachers": "Teacher", "Effective Leaders": "Teacher",
                        "Involved Families": "Teacher"}
SHORT_NAMES = {
    "Human & Social Resources in the Community": "Human & Social Resources",
    "Parent Influence on Decision Making in Schools": "Parent Influence on Decisions",
}
YRBS_FEATURED = ["qn17", "qn26", "qn81", "qn28"]   # the State of CPS indicators, shown first
YRBS_GEOS = ["Chicago", "Illinois", "United States"]
GEO_FILES = {"esb": ("esb_districts.geojson", "sub"),
             "ca": ("community_areas.geojson", "community_area"),
             "net": ("networks.geojson", "network")}


def load_scores():
    """All-respondent school scores for every essential and measure, last FE_YEARS surveys."""
    rows, years = [], set()
    for path in sorted(glob.glob(str(FE_DIR / "5essentials_long_*.csv.gz"))):
        with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["group_type"] == "All" and r["score"] and r["indicator"] != "5Essentials":
                    rows.append(r)
                    years.add(int(r["survey_year"]))
    keep = sorted(years)[-FE_YEARS:]
    rows = [r for r in rows if int(r["survey_year"]) in keep]
    print(f"5Essentials: {len(rows):,} school x indicator scores, years {keep}")
    return rows, keep


def build_indicators(rows):
    """One entry per essential or measure: respondent, essential, theme (if a well-being measure), description."""
    theme_of = {m: (resp, t) for resp, t, ms in THEMES for m in ms}
    latest = {}
    for r in sorted(rows, key=lambda r: r["survey_year"]):
        latest[r["indicator"]] = r
    desc = {}
    with open(FE_DIR / "5essentials_measures_dictionary.csv", newline="", encoding="utf-8") as f:
        for r in sorted(csv.DictReader(f), key=lambda r: r["survey_year"]):
            if r["description"] and not r["description"].startswith("[Template"):
                desc[r["indicator"]] = r["description"]
    inds = []
    for name, r in latest.items():
        is_ess = r["level"] == "essential"
        resp = ESSENTIAL_RESPONDENT.get(name) if is_ess else r["respondent"]
        inds.append({"name": name, "short": SHORT_NAMES.get(name, name), "resp": resp,
                     "kind": "essential" if is_ess else "measure", "essential": r["essential"],
                     "theme": theme_of.get(name, (None, None))[1], "desc": desc.get(name, "")})
    order = {m: i for i, m in enumerate(m for _, _, ms in THEMES for m in ms)}
    inds.sort(key=lambda i: (order.get(i["name"], 999), i["kind"] != "essential", i["name"]))
    print(f"indicators: {len(inds)} ({sum(1 for i in inds if i['theme'])} State of CPS well-being measures)")
    return inds


def load_crosswalk():
    """School ID -> network, community area and ESB sub-district."""
    with open(CROSSWALK, newline="", encoding="utf-8") as f:
        return {r["school_id"]: {"net": r["network"] or None,
                                 "ca": r["community_area"].title() if r["community_area"] else None,
                                 "esb": r["esb_district"].upper() if r["esb_district"] else None}
                for r in csv.DictReader(f)}


def build_schools(rows, inds, years, crosswalk):
    """One entry per school: name, type, groups and a score array per year aligned to the indicators."""
    idx = {i["name"]: k for k, i in enumerate(inds)}
    info = {}
    with open(FE_DIR / "5essentials_schools.csv", newline="", encoding="utf-8") as f:
        for r in sorted(csv.DictReader(f), key=lambda r: r["survey_year"]):
            info[r["school_id"]] = r.get("school_type", "")
    schools = {}
    for r in rows:
        s = schools.setdefault(r["school_id"], {"id": r["school_id"], "n": r["school_name"],
                                                "t": info.get(r["school_id"], ""),
                                                **(crosswalk.get(r["school_id"]) or {"net": None, "ca": None, "esb": None}),
                                                "s": {}})
        arr = s["s"].setdefault(r["survey_year"], [None] * len(inds))
        arr[idx[r["indicator"]]] = round(float(r["score"]))
    out = sorted(schools.values(), key=lambda s: s["id"])
    print(f"schools: {len(out)}; matched to ESB {sum(1 for s in out if s['esb'])}, "
          f"community area {sum(1 for s in out if s['ca'])}, network {sum(1 for s in out if s['net'])}")
    return out


def simplify(points, tol):
    """Douglas-Peucker line simplification."""
    if len(points) < 3:
        return points
    (ax, ay), (bx, by) = points[0], points[-1]
    length = math.hypot(bx - ax, by - ay) or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        d = abs((by - ay) * px - (bx - ax) * py + bx * ay - by * ax) / length
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        return simplify(points[:idx + 1], tol)[:-1] + simplify(points[idx:], tol)
    return [points[0], points[-1]]


def load_geo():
    """Simplified outer rings per area for each grouping: {'esb': {'4B': [ring, ...]}, ...}."""
    geo = {}
    for key, (fname, prop) in GEO_FILES.items():
        fc = json.loads((GEO_DIR / fname).read_text(encoding="utf-8"))
        areas = {}
        for ft in fc["features"]:
            name = ft["properties"][prop]
            name = name.upper() if key == "esb" else name.title() if key == "ca" else name
            g = ft["geometry"]
            for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
                ring, half = poly[0], len(poly[0]) // 2
                pts = ring if len(ring) < MAP_MIN_POINTS else \
                    simplify(ring[:half + 1], MAP_TOLERANCE)[:-1] + simplify(ring[half:], MAP_TOLERANCE)
                if len(pts) >= 4:
                    areas.setdefault(name, []).append([[round(x, 4), round(y, 4)] for x, y in pts])
        geo[key] = areas
    return geo


def num(v):
    """Round a CSV number to one decimal; blank stays None."""
    return round(float(v), 1) if v else None


def load_yrbs():
    """Weighted % with 95% CI for Chicago (total and by group) and Illinois / U.S. totals, last YRBS_YEARS years."""
    with open(YRBS_FILE, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["geography"] in YRBS_GEOS and r["pct"]]
    latest = max(int(r["year"]) for r in rows if r["geography"] == "Chicago")
    rows = [r for r in rows if int(r["year"]) > latest - YRBS_YEARS
            and (r["geography"] == "Chicago" or r["group_type"] == "Total")]
    waves = {}
    for r in rows:
        if r["geography"] == "Chicago" and r["group_type"] == "Total":
            waves.setdefault(r["indicator"], set()).add(r["year"])
    keep = {k for k, v in waves.items() if len(v) >= YRBS_MIN_WAVES}
    inds, years = {}, set()
    for r in rows:
        if r["indicator"] not in keep:
            continue
        y = int(r["year"])
        years.add(y)
        key = f"{r['geography']}|{r['group_type']}|{r['group']}"
        ind = inds.setdefault(r["indicator"], {"id": r["indicator"], "label": r["indicator_label"], "d": {}})
        ind["d"].setdefault(key, {})[y] = [num(r["pct"]), num(r["ci_low"]), num(r["ci_high"]),
                                           int(r["n"]), r["suppress"] == "True"]
    featured = [inds[k] for k in YRBS_FEATURED if k in inds]
    others = sorted((v for k, v in inds.items() if k not in YRBS_FEATURED), key=lambda v: v["label"])
    print(f"YRBS: {len(inds)} indicators, years {sorted(years)}")
    return {"years": sorted(years), "featured": YRBS_FEATURED, "indicators": featured + others}


def write(data):
    """Write the compact JSON next to the page."""
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} ({OUT_FILE.stat().st_size / 1e3:.0f} KB)")


def main():
    rows, years = load_scores()
    inds = build_indicators(rows)
    schools = build_schools(rows, inds, years, load_crosswalk())
    write({"years": years, "themes": [{"resp": r, "name": t, "m": ms} for r, t, ms in THEMES],
           "indicators": inds, "schools": schools, "geo": load_geo(), "yrbs": load_yrbs()})


if __name__ == "__main__":
    main()
