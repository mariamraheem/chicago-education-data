"""
Build the data file for the Student Well-being by District dashboard (State of CPS).

The dashboard shows the Student Well-being section's 5Essentials measures for every
Elected School Board (ESB) sub-district, with a picker for a one-district snapshot,
plus the section's YRBS indicators citywide (YRBS can't be split by district).

Standard library only, so it runs inside the Update Site workflow with no installs.
The page computes district medians itself from the school scores in this file, so it
can switch between the 20 sub-districts and the 10 full districts.

Inputs:
    five_essentials/data/clean/5essentials_long_<year>.csv.gz   (from 01_scrape.py)
    five_essentials/data/clean/5essentials_schools.csv
    five_essentials/data/clean/5essentials_measures_dictionary.csv
    reference/schools/school_crosswalk.csv                      school -> ESB sub-district
    reference/geo/esb_districts.geojson                         ESB sub-district boundaries
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
from pathlib import Path

# ---------------- Config ----------------
REPO_ROOT = Path(__file__).resolve().parents[2]
FE_DIR = REPO_ROOT / "five_essentials" / "data" / "clean"
CROSSWALK = REPO_ROOT / "reference" / "schools" / "school_crosswalk.csv"
ESB_GEO = REPO_ROOT / "reference" / "geo" / "esb_districts.geojson"
YRBS_FILE = REPO_ROOT / "yrbs" / "data" / "clean" / "yrbs_prevalence_long.csv"
OUT_FILE = REPO_ROOT / "five_essentials" / "dashboard" / "student-wellbeing" / "data.json"

FE_YEARS = 5                 # most recent 5Essentials surveys
YRBS_YEARS = 10              # YRBS years back from the latest survey (Chicago has no 2015)

# Themes and measures in the order the State of CPS Student Well-being section uses.
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
SHORT_NAMES = {
    "Human & Social Resources in the Community": "Human & Social Resources",
    "Parent Influence on Decision Making in Schools": "Parent Influence on Decisions",
}
YRBS_INDICATORS = ["qn17", "qn26", "qn81", "qn28"]   # witnessed violence, sad/hopeless, poor mental health, suicide plan
YRBS_GROUP_TYPES = {"Total", "Race/ethnicity"}


def measure_list():
    """All measures in theme order."""
    return [m for _, _, ms in THEMES for m in ms]


def load_school_scores(measures):
    """All-respondent school scores for the measures, last FE_YEARS surveys: {school: {year: {measure: score}}}."""
    scores, names, years = {}, {}, set()
    for path in sorted(glob.glob(str(FE_DIR / "5essentials_long_*.csv.gz"))):
        with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["group_type"] != "All" or r["indicator"] not in measures or not r["score"]:
                    continue
                y = int(r["survey_year"])
                years.add(y)
                scores.setdefault(r["school_id"], {}).setdefault(y, {})[r["indicator"]] = round(float(r["score"]))
                names[r["school_id"]] = r["school_name"]
    keep = sorted(years)[-FE_YEARS:]
    print(f"5Essentials: {len(scores)} schools, keeping years {keep}")
    return scores, names, keep


def load_school_info():
    """Latest school type and overall rating label per school."""
    info = {}
    with open(FE_DIR / "5essentials_schools.csv", newline="", encoding="utf-8") as f:
        for r in sorted(csv.DictReader(f), key=lambda r: r["survey_year"]):
            info[r["school_id"]] = {"type": r.get("school_type", ""), "label": r.get("overall_label", "")}
    return info


def load_esb():
    """School ID -> ESB sub-district (e.g. '4B')."""
    with open(CROSSWALK, newline="", encoding="utf-8") as f:
        return {r["school_id"]: r["esb_district"].upper() for r in csv.DictReader(f) if r["esb_district"]}


def load_descriptions(measures):
    """Latest dictionary description for each measure."""
    desc = {}
    with open(FE_DIR / "5essentials_measures_dictionary.csv", newline="", encoding="utf-8") as f:
        for r in sorted(csv.DictReader(f), key=lambda r: r["survey_year"]):
            if r["indicator"] in measures and r["description"] and not r["description"].startswith("[Template"):
                desc[r["indicator"]] = r["description"]
    return desc


def load_geo():
    """ESB sub-district outer rings, coordinates rounded to ~10 m: {'4B': [[[lon, lat], ...], ...]}."""
    fc = json.loads(ESB_GEO.read_text(encoding="utf-8"))
    geo = {}
    for ft in fc["features"]:
        g = ft["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        rings = [[[round(x, 4), round(y, 4)] for x, y in p[0]] for p in polys]
        geo.setdefault(ft["properties"]["sub"].upper(), []).extend(rings)
    return geo


def load_yrbs():
    """Chicago YRBS for the dashboard's indicators, total and by race/ethnicity, last YRBS_YEARS years."""
    with open(YRBS_FILE, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["geography"] == "Chicago"
                and r["indicator"] in YRBS_INDICATORS and r["group_type"] in YRBS_GROUP_TYPES and r["pct"]]
    latest = max(int(r["year"]) for r in rows)
    out, years = {}, set()
    for r in rows:
        y = int(r["year"])
        if y <= latest - YRBS_YEARS:
            continue
        years.add(y)
        ind = out.setdefault(r["indicator"], {"label": r["indicator_label"], "d": {}})
        ind["d"].setdefault(r["group"], {})[y] = [round(float(r["pct"]), 1), round(float(r["ci_low"]), 1),
                                                  round(float(r["ci_high"]), 1), int(r["n"]), r["suppress"] == "True"]
    print(f"YRBS: {len(out)} indicators, years {sorted(years)}")
    return {"order": YRBS_INDICATORS, "ind": out, "years": sorted(years)}


def assemble(measures, scores, names, years, info, esb, desc, geo, yrbs):
    """Put everything in the compact shape the page reads."""
    schools = []
    for sid, by_year in sorted(scores.items()):
        s = {str(y): [by_year.get(y, {}).get(m) for m in measures] for y in years if y in by_year}
        if not s:
            continue
        schools.append({"id": sid, "n": names[sid], "t": info.get(sid, {}).get("type", ""),
                        "e": esb.get(sid), "o": info.get(sid, {}).get("label", ""), "s": s})
    print(f"schools: {len(schools)} with scores, {sum(1 for s in schools if s['e'])} placed in an ESB sub-district")
    return {"years": years,
            "themes": [{"resp": r, "name": t, "m": ms} for r, t, ms in THEMES],
            "measures": [{"name": m, "short": SHORT_NAMES.get(m, m), "desc": desc.get(m, "")} for m in measures],
            "schools": schools, "geo": geo, "yrbs": yrbs}


def write(data):
    """Write the compact JSON next to the page."""
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} ({OUT_FILE.stat().st_size / 1e3:.0f} KB)")


def main():
    measures = measure_list()
    scores, names, years = load_school_scores(measures)
    data = assemble(measures, scores, names, years, load_school_info(), load_esb(),
                    load_descriptions(measures), load_geo(), load_yrbs())
    write(data)


if __name__ == "__main__":
    main()
