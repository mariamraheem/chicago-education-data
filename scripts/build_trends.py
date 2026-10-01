"""
Builds the compact JSON the site's trend pages read:

    site/api/trends/yrbs.json            YRBS indicators x geography x year x group
    site/api/trends/five_essentials.json 5Essentials school distributions, medians, school lookup
    site/api/trends/overview.json        plain-language takeaways for the home page

Inputs (committed by the domain pipelines):
    yrbs/data/clean/yrbs_prevalence_long.csv
    five_essentials/data/clean/5essentials_long_<year>.csv.gz
    five_essentials/data/clean/5essentials_schools.csv

Missing inputs are skipped; the pages show "no data yet" for that source.
Called from scripts/build_site_manifest.py, so the existing site workflow picks it up.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "site" / "api" / "trends"

YRBS_CSV = REPO_ROOT / "yrbs" / "data" / "clean" / "yrbs_prevalence_long.csv"
FE_DIR = REPO_ROOT / "five_essentials" / "data" / "clean"
FE_LONG = FE_DIR / "5essentials_long.csv"  # older single-file layout, still read if present
FE_SCHOOLS = REPO_ROOT / "five_essentials" / "data" / "clean" / "5essentials_schools.csv"

# ---------------------------------------------------------------- YRBS topics
# Topic by YRBS question number (CDC questionnaire order) or variable-name stem.
YRBS_TOPICS = [
    ("Mental health", ["qn25", "qn26", "qn27", "qn28", "qn29", "qn30", "qn81", "qn82",
                       "qnexpwttheraphy", "qnconcentrating"]),
    ("Safety & violence", ["qn11", "qn12", "qn13", "qn14", "qn15", "qn16", "qn17", "qn18",
                           "qn19", "qn20", "qn21", "qn22", "qn23", "qn24"]),
    ("School connection", ["qnclose2people", "qntalkadultace", "qnunfairlyace"]),
    ("Vaping & tobacco", ["qn31", "qn32", "qn33", "qn34", "qn35", "qn36", "qn37", "qn38", "qn39",
                          "qntb2", "qndaycig", "qnfrcig", "qndayevp", "qnfrevp", "qndaycgr",
                          "qnfrcgr", "qndayskl", "qnfrskl"]),
    ("Alcohol & drugs", ["qn40", "qn41", "qn42", "qn43", "qn44", "qn45", "qn46", "qn47", "qn48",
                         "qn49", "qn50", "qn51", "qn52", "qn53"]),
    ("Sexual health", ["qn54", "qn55", "qn56", "qn57", "qn58", "qn59", "qn60", "qn78", "qn79",
                       "qnbcnone", "qnconpp", "qniudimp", "qnothhpl"]),
    ("Home & basic needs", ["qn84", "qn85", "qn86", "qnfdinsc", "qnintviolenceace",
                            "qnphyabuseace"]),
    ("Health, food & activity", ["qnobese", "qnowt", "qn64", "qn65", "qn66", "qn67", "qn68", "qn69",
                                 "qn70", "qn71", "qn72", "qn73", "qn74", "qn75", "qn76", "qn77",
                                 "qn80", "qn83", "qnnodnt", "qnpa0day", "qnpa7day", "qndlype",
                                 "qnbk7day", "qnfruit1", "qnfruit2", "qnfruit3", "qnveg0", "qnveg1",
                                 "qnveg2", "qnveg3", "qnsoda1", "qnsoda2", "qnmusclestrength"]),
    ("Driving", ["qn7", "qn8", "qn9", "qn10"]),
]
# Indicators shown first on the home page and at the top of each topic.
YRBS_KEY = ["qn26", "qn27", "qn81", "qn13", "qn23", "qn15", "qn36", "qn41", "qn46", "qnclose2people"]
# Indicators where a higher % is the better outcome (everything else: higher = more risk).
YRBS_HIGHER_IS_BETTER = {"qnclose2people", "qntalkadultace", "qn59", "qn78", "qn79", "qn80",
                         "qn82", "qn83", "qn73", "qn74", "qn75", "qnpa7day", "qndlype", "qnbk7day",
                         "qnfruit1", "qnfruit2", "qnfruit3", "qnveg1", "qnveg2", "qnveg3", "qn71",
                         "qnconpp", "qniudimp", "qnothhpl", "qnmusclestrength"}
GEOS = ["Chicago", "Illinois", "United States"]


def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_yrbs() -> dict | None:
    if not YRBS_CSV.exists():
        return None
    topic_of = {q: t for t, qs in YRBS_TOPICS for q in qs}
    series: dict = defaultdict(lambda: defaultdict(dict))   # ind -> key -> year -> [pct, lo, hi, n]
    labels = {}
    with open(YRBS_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ind = r["indicator"]
            if ind not in topic_of:
                continue
            labels[ind] = r["indicator_label"]
            if r["suppress"] == "True":
                continue
            key = f'{r["geography"]}|{r["group_type"]}|{r["group"]}'
            series[ind][key][int(r["year"])] = [_num(r["pct"]), _num(r["ci_low"]), _num(r["ci_high"]), int(r["n"])]

    indicators = []
    for topic, qs in YRBS_TOPICS:
        for q in qs:
            if q not in series:
                continue
            chi = series[q].get("Chicago|Total|Total", {})
            if not chi:
                continue  # page is Chicago-first
            indicators.append({
                "id": q, "label": labels[q], "topic": topic,
                "key": q in YRBS_KEY,
                "higher_is_better": q in YRBS_HIGHER_IS_BETTER,
                "series": {k: {str(y): v for y, v in sorted(d.items())} for k, d in series[q].items()},
            })
    years = sorted({int(y) for i in indicators for s in i["series"].values() for y in s})
    return {"years": years, "geographies": GEOS, "topics": [t for t, _ in YRBS_TOPICS],
            "key_order": YRBS_KEY, "indicators": indicators,
            "notes": [
                "Weighted % of high school students, from CDC's combined YRBS datasets.",
                "Estimates based on fewer than 100 students are not shown.",
                "Chicago has no 2015 data. Chicago's 2025 sample is the smallest of any year (about 900 students); treat 2025 shifts with caution.",
            ]}


def yrbs_takeaways(y: dict) -> list[dict]:
    out = []
    by_id = {i["id"]: i for i in y["indicators"]}
    for q in YRBS_KEY:
        ind = by_id.get(q)
        if not ind:
            continue
        chi = ind["series"].get("Chicago|Total|Total", {})
        us = ind["series"].get("United States|Total|Total", {})
        yrs = sorted(chi, key=int)
        if len(yrs) < 2:
            continue
        last, prev = yrs[-1], yrs[-2]
        first = next((yy for yy in yrs if int(yy) >= int(last) - 10), yrs[0])
        out.append({
            "id": q, "label": ind["label"], "year": int(last),
            "chicago": chi[last][0], "prev_year": int(prev), "prev": chi[prev][0],
            "ten_year_base_year": int(first), "ten_year_base": chi[first][0],
            "us": us.get(last, [None])[0],
            "higher_is_better": ind["higher_is_better"],
        })
    return out


# ---------------------------------------------------------- 5Essentials
ESSENTIALS = [("overall", "5Essentials overall"), ("instruction", "Ambitious Instruction"),
              ("leaders", "Effective Leaders"), ("teachers", "Collaborative Teachers"),
              ("families", "Involved Families"), ("environment", "Supportive Environment")]
BANDS = ["Very Weak", "Weak", "Neutral", "Strong", "Very Strong"]
# The overall 5Essentials rating uses its own five labels in place of the bands.
ORG_LABELS = ["Not yet organized", "Partially organized", "Moderately organized", "Organized", "Well-organized"]


def _band(score: float) -> str:
    return BANDS[min(int(score // 20), 4)]


def build_five_essentials() -> dict | None:
    long_files = sorted(FE_DIR.glob("5essentials_long_*.csv.gz")) or ([FE_LONG] if FE_LONG.exists() else [])
    if not long_files:
        return None
    ess_slug = {name: slug for slug, name in ESSENTIALS}
    ess_scores = defaultdict(lambda: defaultdict(list))      # slug -> year -> [scores]
    meas_scores = defaultdict(lambda: defaultdict(list))     # measure -> year -> [scores]
    meas_meta = {}
    schools = defaultdict(lambda: {"n": "", "y": {}})
    def rows():
        for path in long_files:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", newline="", encoding="utf-8") as f:
                yield from csv.DictReader(f)

    if True:
        for r in rows():
            if r["group"] != "All respondents" or r["score_status"] != "reported":
                continue
            yr, sid, s = int(r["survey_year"]), r["school_id"], float(r["score"])
            sch = schools[sid]
            sch["n"] = r["school_name"]
            if r["level"] == "essential":
                slug = r["indicator_slug"] if r["indicator_slug"] in dict(ESSENTIALS) else ess_slug.get(r["indicator"])
                if not slug:
                    continue
                ess_scores[slug][yr].append(s)
                sch["y"].setdefault(str(yr), {})[slug] = s
            else:
                name = r["indicator"]
                meas_scores[name][yr].append(s)
                meas_meta[name] = {"essential": r["essential"], "respondent": r["respondent"]}

    types, overall_labels = {}, defaultdict(lambda: defaultdict(int))
    if FE_SCHOOLS.exists():
        with open(FE_SCHOOLS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                types[r["school_id"]] = r.get("school_type") or ""
                sch = schools.get(r["school_id"])
                if sch is not None:
                    sch["y"].setdefault(r["survey_year"], {})["sr"] = _num(r.get("student_response_rate"))
                    sch["y"][r["survey_year"]]["tr"] = _num(r.get("teacher_response_rate"))
                    lab = (r.get("overall_label") or "").strip()
                    lab = next((o for o in ORG_LABELS if o.lower() == lab.lower()), None)
                    if lab:
                        sch["y"][r["survey_year"]]["ol"] = lab
                        overall_labels[r["survey_year"]][lab] += 1
    for sid, sch in schools.items():
        sch["t"] = types.get(sid, "")

    years = sorted({y for d in ess_scores.values() for y in d})

    def summarize(vals):
        return {"n": len(vals), "median": round(statistics.median(vals), 1),
                "bands": [sum(1 for v in vals if _band(v) == b) for b in BANDS]}

    essentials = []
    for slug, name in ESSENTIALS:
        if not ess_scores.get(slug):
            continue
        by_year = {str(y): summarize(ess_scores[slug][y]) for y in years if ess_scores[slug].get(y)}
        # Some surveys (e.g. 2025) only reported part of the instrument; flag
        # years scored for under 60% of the usual number of schools.
        top = max(b["n"] for b in by_year.values())
        for b in by_year.values():
            b["partial"] = b["n"] < 0.6 * top
        essentials.append({"slug": slug, "name": name, "by_year": by_year})
    measures = []
    for name, d in meas_scores.items():
        by_year = {str(y): summarize(v) for y, v in sorted(d.items()) if len(v) >= 20}
        if by_year:
            measures.append({"name": name, **meas_meta[name], "by_year": by_year})
    measures.sort(key=lambda m: (m["essential"], m["name"]))
    return {"years": years, "bands": BANDS, "org_labels": ORG_LABELS, "essentials": essentials, "measures": measures,
            "overall_labels": {y: dict(c) for y, c in overall_labels.items()},
            "schools": schools,
            "notes": ["Scores are 1-99 (50 = 2013 CPS average). Bands: 0-19 Very Weak, 20-39 Weak, "
                      "40-59 Neutral, 60-79 Strong, 80-99 Very Strong.",
                      "Schools with too few survey responses get no score and are left out.",
                      "There was no survey in 2020. Years scored for far fewer schools than usual "
                      "(for example 2025, when the survey reported a shorter set of measures) are marked "
                      "as limited and left out of trend lines."]}


def fe_takeaways(fe: dict) -> dict:
    yrs = [str(y) for y in fe["years"]]
    last, first = yrs[-1], yrs[0]
    rows = []
    for e in fe["essentials"]:
        if e["slug"] == "overall":
            continue
        full = [y for y in yrs if y in e["by_year"] and not e["by_year"][y].get("partial")]
        if not full:
            continue
        a, b = e["by_year"][full[-1]], (e["by_year"][full[0]] if len(full) > 1 else None)
        strong = (a["bands"][3] + a["bands"][4]) / a["n"] * 100
        strong_first = ((b["bands"][3] + b["bands"][4]) / b["n"] * 100) if b else None
        rows.append({"slug": e["slug"], "name": e["name"], "year": int(full[-1]),
                     "first_year": int(full[0]), "median": a["median"],
                     "median_first": b["median"] if b else None,
                     "pct_strong": round(strong, 1),
                     "pct_strong_first": round(strong_first, 1) if strong_first is not None else None,
                     "n": a["n"]})
    return {"year": int(last), "first_year": int(first), "essentials": rows}


# ---------------------------------------------------------------- main
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overview = {"yrbs": None, "five_essentials": None}
    y = build_yrbs()
    if y:
        (OUT_DIR / "yrbs.json").write_text(json.dumps(y, separators=(",", ":")))
        overview["yrbs"] = {"years": [y["years"][0], y["years"][-1]], "takeaways": yrbs_takeaways(y)}
        print(f"yrbs.json: {len(y['indicators'])} indicators")
    fe = build_five_essentials()
    if fe:
        (OUT_DIR / "five_essentials.json").write_text(json.dumps(fe, separators=(",", ":")))
        overview["five_essentials"] = fe_takeaways(fe)
        print(f"five_essentials.json: {len(fe['schools'])} schools, years {fe['years']}")
    (OUT_DIR / "overview.json").write_text(json.dumps(overview, indent=1))


if __name__ == "__main__":
    main()
