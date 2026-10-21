"""
NAEP scraper (Nation's Report Card Data Service API).

Pulls average scale scores (stattype MN:MN) for math and reading, grades 4, 8
and 12, for the national samples, Illinois, the large-city average and every
TUDA district, broken out by the same student groups as the hand-built
NAEP_Compiled_Wide.xlsx used for the 2026 NAEP brief.

One API call per subject x grade x student-group variable x year, with all
jurisdictions in the same call. The API docs say to keep calls small to avoid
timeouts, so years are not batched. If a call errors, it's retried one
jurisdiction at a time so one bad district doesn't wipe out the rest.

Inputs:  none (API only). Docs: https://www.nationsreportcard.gov/api_documentation.aspx
Outputs: naep/data/raw/naep_<subject>_g<grade>_<variable>.json
         -- the API's "result" rows as returned, plus a log of every request
Run:     python naep/scripts/01_scrape.py            # skips files already present
         python naep/scripts/01_scrape.py --force    # re-download everything

NAEP releases every two years. When a new year comes out, add it to YEARS.
Note: NAEP says API results can change over time (revisions), so --force
re-pulls are the way to pick those up.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---- Config -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "naep" / "data" / "raw"

API_URL = "https://www.nationsreportcard.gov/DataService/GetAdhocData.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0) requests"}
SLEEP_BETWEEN_CALLS = 0.5  # seconds -- be nice to the API
TIMEOUT = 120

# assessment years in the hand-built workbook. 1990-1994 only exist without
# accommodations (R2); everything else uses the API default (R3).
YEARS = [1990, 1992, 1994, 1996, 1998, 2000, 2002, 2003, 2005, 2007, 2009,
         2011, 2013, 2015, 2017, 2019, 2022, 2024]
R2_ONLY_YEARS = {1990, 1992, 1994}

GRADES = [4, 8, 12]

# composite scale per subject. grade 12 math moved to the 2005 framework (MWPCM).
SUBSCALES = {
    ("mathematics", 4): "MRPCM",
    ("mathematics", 8): "MRPCM",
    ("mathematics", 12): "MWPCM",
    ("reading", 4): "RRPCM",
    ("reading", 8): "RRPCM",
    ("reading", 12): "RRPCM",
}

# student-group variables (codes from the API docs)
VARIABLES = {
    "TOTAL": "All students",
    "SDRACE": "Race/ethnicity",
    "GENDER": "Sex",
    "SLUNCH3": "Econ. disadvantage (NSLP)",
    "LEP": "English learner",
    "IEP": "Disability status",
}

# jurisdiction codes from the API docs -> names used in the brief/app
JURISDICTIONS = {
    "NT": "National",
    "NP": "National public",
    "NL": "Large city",
    "IL": "Illinois",
    "XQ": "Albuquerque",
    "XA": "Atlanta",
    "XU": "Austin",
    "XM": "Baltimore City",
    "XB": "Boston",
    "XT": "Charlotte",
    "XC": "Chicago",
    "XX": "Clark County (NV)",
    "XV": "Cleveland",
    "XS": "Dallas",
    "XY": "Denver",
    "XR": "Detroit",
    "XW": "District of Columbia (DCPS)",
    "XE": "Duval County (FL)",
    "XZ": "Fort Worth (TX)",
    "XF": "Fresno",
    "XG": "Guilford County (NC)",
    "XO": "Hillsborough County (FL)",
    "XH": "Houston",
    "XJ": "Jefferson County (KY)",
    "XL": "Los Angeles",
    "XI": "Miami-Dade",
    "XK": "Milwaukee",
    "XN": "New York City",
    "XP": "Philadelphia",
    "XD": "San Diego",
    "YA": "Shelby County (TN)",
    "YB": "Orange County (FL)",
}


# ---- Helpers ------------------------------------------------------------------

def year_param(year: int) -> str:
    """API year string -- R2 for the early no-accommodations years."""
    return f"{year}R2" if year in R2_ONLY_YEARS else str(year)


def call_api(subject: str, grade: int, variable: str, year: int, juris: list[str]) -> dict:
    """One GetAdhocData call. Returns the parsed JSON, or an error dict."""
    params = {
        "type": "data",
        "subject": subject,
        "grade": grade,
        "subscale": SUBSCALES[(subject, grade)],
        "variable": variable,
        "jurisdiction": ",".join(juris),
        "stattype": "MN:MN",
        "Year": year_param(year),
    }
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        # error bodies have raw line breaks in them, so they don't parse as strict json
        body = json.loads(r.text, strict=False)
    except (requests.RequestException, ValueError) as e:
        return {"status": None, "error": str(e), "params": params}
    if "status" not in body and "statusCode" in body:
        body["status"] = body["statusCode"]
    body["params"] = params
    return body


def pull_one(subject: str, grade: int, variable: str, year: int) -> tuple[list, list]:
    """All jurisdictions for one year. Falls back to one call per jurisdiction on error."""
    codes = list(JURISDICTIONS)
    body = call_api(subject, grade, variable, year, codes)
    if body.get("status") == 200 and isinstance(body.get("result"), list):
        return body["result"], [{"params": body["params"], "status": 200, "rows": len(body["result"])}]

    log = [{"params": body.get("params"), "status": body.get("status"),
            "error": str(body.get("error") or body.get("result"))[:300]}]

    # districts that weren't assessed come back as 999 / not displayable, not as
    # errors. a failed batch usually means the subject wasn't given that year at all
    # (e.g. math 2002 -> 400 "did not return exactly 1 framework"). check national
    # public first -- if that fails too, skip the year instead of trying all 32 codes.
    time.sleep(SLEEP_BETWEEN_CALLS)
    probe = call_api(subject, grade, variable, year, ["NP"])
    if probe.get("status") != 200:
        log.append({"params": probe.get("params"), "status": probe.get("status"), "rows": 0,
                    "note": "not assessed this year -- skipped"})
        return [], log

    # national public works, so go one by one so the rest still come through
    rows = []
    for code in codes:
        time.sleep(SLEEP_BETWEEN_CALLS)
        b = call_api(subject, grade, variable, year, [code])
        ok = b.get("status") == 200 and isinstance(b.get("result"), list)
        if ok:
            rows.extend(b["result"])
        log.append({"params": b.get("params"), "status": b.get("status"),
                    "rows": len(b["result"]) if ok else 0})
    return rows, log


# ---- Steps --------------------------------------------------------------------

def scrape_file(subject: str, grade: int, variable: str, dest: Path) -> int:
    """Pull every year for one subject/grade/variable and write the raw JSON."""
    all_rows, all_log = [], []
    for year in YEARS:
        rows, log = pull_one(subject, grade, variable, year)
        skipped = any(x.get("note", "").startswith("not assessed") for x in log)
        print(f"    {year}: {'not assessed' if skipped else f'{len(rows)} rows'}", flush=True)
        all_rows.extend(rows)
        all_log.extend(log)
        time.sleep(SLEEP_BETWEEN_CALLS)

    out = {
        "source": API_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subject": subject,
        "grade": grade,
        "variable": variable,
        "result": all_rows,
        "request_log": all_log,
    }
    # write to .part first so an interrupted run never leaves a half file behind
    tmp = dest.with_suffix(".part")
    tmp.write_text(json.dumps(out, indent=1))
    tmp.replace(dest)
    return len(all_rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files already present")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    written, skipped, empty = 0, 0, []

    for (subject, grade) in SUBSCALES:
        for variable in VARIABLES:
            dest = RAW_DIR / f"naep_{subject}_g{grade}_{variable.lower()}.json"
            if dest.exists() and dest.stat().st_size > 0 and not args.force:
                skipped += 1
                continue
            print(f"  {dest.name}", flush=True)
            n = scrape_file(subject, grade, variable, dest)
            print(f"  {dest.name}: {n} rows", flush=True)
            written += 1
            if n == 0:
                empty.append(dest.name)

    print(f"\nwrote {written} files, skipped {skipped} already present")
    if empty:
        # zero rows usually means the API changed or rejected every call -- check request_log
        print(f"WARNING: {len(empty)} files came back with 0 rows: {', '.join(empty)}")


if __name__ == "__main__":
    main()
