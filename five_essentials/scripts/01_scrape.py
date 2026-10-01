"""
5Essentials (CPS) scraper: every school, every measure and essential, last N survey years.

Replaces the Selenium version. Each report page embeds its full data as JSON in
<script id="app_data" data-data="...">, so plain HTTP requests are enough: no browser,
no ChromeDriver.

Usage:
    python five_essentials/scripts/01_scrape.py                  # last 5 surveys (e.g. 2022-2026)
    python five_essentials/scripts/01_scrape.py --years 2024 2025 2026
    python five_essentials/scripts/01_scrape.py --workers 2
    python five_essentials/scripts/01_scrape.py --dictionary-only   # only the measure/question dictionary

Outputs (five_essentials/data/clean/ unless --out is given):
    5essentials_long_<year>.csv.gz  one row per school x indicator x student/teacher group (gzipped, per year)
    5essentials_scores_wide.csv     all-respondent scores, one row per school-year, one column per indicator
    5essentials_measures_dictionary.csv  each essential and measure: who is asked, description, question stem
    5essentials_questions.csv       every survey question behind each measure, with its answer choices
    5essentials_schools.csv         school metadata, overall rating label and response rates by year
Score codes: 1-99 = score; negative codes are the site's "no score" flags, decoded in
`score_status` (no_report, not_eligible, P).
"""
import argparse
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.5-essentials.org"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0) requests"}
STATUS = {-1000: "no_report", -1100: "no_report", -1200: "not_eligible", -1300: "P"}
RANGES = [(0, 20, "Very Weak"), (20, 40, "Weak"), (40, 60, "Neutral"),
          (60, 80, "Strong"), (80, 101, "Very Strong")]

session = requests.Session()
session.headers.update(HEADERS)


def get(url, tries=4):
    for i in range(tries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    raise RuntimeError(f"failed after {tries} tries: {url}")


def app_data(page):
    m = re.search(r'<script[^>]*id="app_data"[^>]*data-data="([^"]*)"', page)
    return json.loads(html.unescape(m.group(1))) if m else None


def school_ids(year):
    page = get(f"{BASE}/cps/5e/{year}/")
    if page is None:
        return []
    ids = set(re.findall(rf"/cps/5e/{year}/s/(\d+)/", html.unescape(page)))
    return sorted(ids)


def label(score):
    for lo, hi, name in RANGES:
        if lo <= score < hi:
            return name
    return None


def parse(j, year):
    """Flatten one school-year's app_data into long rows (current year only: index 0)."""
    t = j["target"]
    subjects = {int(k): v for k, v in j["other_config"]["subjects"].items()}
    # map group code -> (group_type, group_label)
    groups = {"all": ("All", "All respondents")}
    for gtype_label, _, members in j["comparisons"].get("measures", []):
        for glabel, gcode in members:
            groups[gcode] = (gtype_label, glabel)
    ess_names = {e["slug"]: e["name"] for e in j["essentials"]}

    rows = []
    for level, items in (("essential", j["essentials"]), ("measure", j["measures"])):
        for it in items:
            parent = it.get("parent_slug")
            for gcode, series in (it.get("data") or {}).items():
                if not series:
                    continue
                val, flag = series[0][0], series[0][1] if len(series[0]) > 1 else None
                ok = val is not None and val >= 0
                gtype, glabel = groups.get(gcode, ("Other", gcode))
                rows.append({
                    "survey_year": int(year),
                    "school_id": t["slug"],
                    "school_name": t["name"],
                    "level": level,
                    "indicator_slug": it["slug"],
                    "indicator": it["name"],
                    "essential": ess_names.get(parent, parent) if level == "measure" else it["name"],
                    "respondent": subjects.get(it.get("subject")) if level == "measure" else None,
                    "group_type": gtype,
                    "group": glabel,
                    "score": val if ok else None,
                    "performance": label(val) if ok else None,
                    "score_status": "reported" if ok else STATUS.get(val, "other"),
                    "flag": flag,
                })
    meta = {
        "survey_year": int(year),
        "school_year": next((s["school_year"] for s in j["survey"]["list"] if s["label"] == str(year)), None),
        "school_id": t["slug"], "school_name": t["name"], "school_type": t.get("type_description"),
        "address": t.get("full_address"),
        "student_response_rate": t.get("student_response_rate"),
        "teacher_response_rate": t.get("teacher_response_rate"),
        "parent_response_rate": t.get("parent_response_rate"),
        "overall_label": j.get("overall_long_label"),
    }
    return rows, meta


def scrape_one(year, sid):
    page = get(f"{BASE}/cps/5e/{year}/s/{sid}/measures/")
    j = app_data(page) if page else None
    if not j or not j.get("measures"):
        return [], None
    return parse(j, year)


def _strip_html(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(h or ""))).strip()


def build_dictionary(years, out, sample=8):
    """Measure descriptions and survey questions for each year.

    Each school's report carries the definitions of every measure, and the
    report's "$measure-items" endpoint lists the questions behind a measure.
    Elementary and high schools see slightly different measures, so a spread
    of schools is sampled per year and the results are combined."""
    meas_rows, item_rows, seen_items = {}, [], set()
    for year in years:
        ids = school_ids(year)
        if not ids:
            continue
        step = max(1, len(ids) // sample)
        for sid in ids[::step][:sample]:
            page = get(f"{BASE}/cps/5e/{year}/s/{sid}/measures/")
            j = app_data(page) if page else None
            if not j or not j.get("measures"):
                continue
            subjects = {int(k): v for k, v in j["other_config"]["subjects"].items()}
            ess_names = {e["slug"]: e["name"] for e in j["essentials"]}
            for e in j["essentials"]:
                key = (year, "essential", e["slug"])
                if key not in meas_rows:
                    text = _strip_html(((e.get("text") or {}).get("overview") or {}).get("__html"))
                    meas_rows[key] = {
                        "survey_year": year, "level": "essential", "essential": e["name"],
                        "indicator_slug": e["slug"], "indicator": e["name"], "asked_of": "",
                        "description": text[len(e["name"]):].strip() if text.startswith(e["name"]) else text,
                        "question_stem": "",
                    }
            for m in j["measures"]:
                key = (year, "measure", m["slug"])
                if m["slug"] == "all":
                    continue
                if key not in meas_rows:
                    text = _strip_html(((m.get("text") or {}).get("overview") or {}).get("__html"))
                    parent = m.get("parent_slug")
                    meas_rows[key] = {
                        "survey_year": year, "level": "measure",
                        "essential": "Supplemental measures" if parent == "_supplemental" else ess_names.get(parent, parent),
                        "indicator_slug": m["slug"], "indicator": m["name"],
                        "asked_of": subjects.get(m.get("subject"), ""),
                        "description": text[len(m["name"]):].strip() if text.startswith(m["name"]) else text,
                        "question_stem": m.get("stem") or "",
                    }
                if (year, m["slug"]) in seen_items:
                    continue
                try:
                    r = session.get(f"{BASE}/cps/5e/{year}/s/{sid}/$measure-items", params={"m": m["slug"]}, timeout=30)
                    items = r.json().get("items") if r.ok else None
                except (requests.RequestException, ValueError):
                    items = None
                if not items:
                    continue
                seen_items.add((year, m["slug"]))
                row = meas_rows[key]
                for n, it in enumerate(items, 1):
                    choices = it.get("choices") or {}
                    item_rows.append({
                        "survey_year": year, "essential": row["essential"], "indicator_slug": m["slug"],
                        "indicator": m["name"], "asked_of": row["asked_of"], "question_stem": row["question_stem"],
                        "question_order": n, "question_code": it.get("slug"),
                        "question": (it.get("prompt") or "").strip(),
                        "answer_choices": " | ".join(choices[k] for k in sorted(choices, key=lambda x: int(x))),
                    })
        print(f"dictionary {year}: {sum(1 for k in meas_rows if k[0] == year)} indicators, "
              f"{sum(1 for r in item_rows if r['survey_year'] == year)} questions", flush=True)
    if meas_rows:
        pd.DataFrame(meas_rows.values()).sort_values(["survey_year", "level", "essential", "indicator"]) \
          .to_csv(out / "5essentials_measures_dictionary.csv", index=False)
    if item_rows:
        pd.DataFrame(item_rows).sort_values(["survey_year", "essential", "indicator", "question_order"]) \
          .to_csv(out / "5essentials_questions.csv", index=False)


def main():
    this_year = date.today().year
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int,
                    help="survey years to pull (default: the latest 5 published)")
    ap.add_argument("--n-years", type=int, default=5)
    ap.add_argument("--out", default=str(REPO_ROOT / "five_essentials" / "data" / "clean"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dictionary-only", action="store_true",
                    help="only build the measure/question dictionary, skip school scores")
    args = ap.parse_args()
    if not args.years:
        latest = next(y for y in range(this_year + 1, this_year - 3, -1) if get(f"{BASE}/cps/5e/{y}/"))
        args.years = list(range(latest - args.n_years + 1, latest + 1))
    print("survey years:", args.years, flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    build_dictionary(args.years, out)
    if args.dictionary_only:
        return

    rows, metas = [], []
    for year in args.years:
        ids = school_ids(year)
        print(f"{year}: {len(ids)} schools", flush=True)
        if not ids:
            continue
        done = 0
        with ThreadPoolExecutor(args.workers) as pool:
            futs = {pool.submit(scrape_one, year, sid): sid for sid in ids}
            for f in as_completed(futs):
                try:
                    r, m = f.result()
                except Exception as e:  # keep going; report at the end
                    print(f"  ! {year}/{futs[f]}: {e}", file=sys.stderr)
                    continue
                rows += r
                if m:
                    metas.append(m)
                done += 1
                if done % 100 == 0:
                    print(f"  {done}/{len(ids)}", flush=True)

    if not rows:
        sys.exit("No data scraped. Check the years and that www.5-essentials.org is reachable.")

    df = pd.DataFrame(rows)
    # The full long file is ~300 MB (every subgroup breakout), over GitHub's 100 MB
    # file limit, so it is written as one gzipped file per survey year (~10 MB each).
    df = df.sort_values(["survey_year", "school_id", "level", "indicator", "group_type", "group"])
    for yr, part in df.groupby("survey_year"):
        part.to_csv(out / f"5essentials_long_{yr}.csv.gz", index=False, compression="gzip")
    stale = out / "5essentials_long.csv"
    if stale.exists():
        stale.unlink()
    pd.DataFrame(metas).sort_values(["survey_year", "school_id"]) \
      .to_csv(out / "5essentials_schools.csv", index=False)

    allr = df[df.group == "All respondents"]
    wide = allr.pivot_table(index=["survey_year", "school_id", "school_name"],
                            columns="indicator", values="score", aggfunc="first").reset_index()
    wide.columns.name = None
    wide.to_csv(out / "5essentials_scores_wide.csv", index=False)
    print(f"Saved {len(df):,} rows | {df.school_id.nunique()} schools | years {sorted(df.survey_year.unique())} -> {out}")


if __name__ == "__main__":
    main()
