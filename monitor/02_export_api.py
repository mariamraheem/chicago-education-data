#!/usr/bin/env python3
"""
monitor/02_export_api.py

Turns monitor/data/state.json + run_log.jsonl + diffs/ into a small set of
plain, standardized JSON (and one CSV) files under monitor/site/api/ -- a
static "API" that anything can pull without cloning this repo or running a
server: curl, a spreadsheet's "get data from web" import, another script,
or 03_render_dashboard.py's own React app.

GitHub Pages serves these as plain files with Access-Control-Allow-Origin:
* by default, so they're fetchable cross-origin from anywhere too -- no
auth, no rate limit, no CORS config needed.

monitor/site/ is rebuilt fresh every run (see 03_render_dashboard.py's
docstring) -- api/ lives inside it for the same reason: it always reflects
the latest scrape, not full repo history. api/runs.json and api/changes/
carry a rolling window (RUNS_HISTORY_SHOWN); the complete history still
lives in monitor/data/diffs/ and run_log.jsonl in git if you need to go
back further.

Run this AFTER 01_scan.py and BEFORE 03_render_dashboard.py.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "run_log.jsonl")
DIFFS_DIR = os.path.join(DATA_DIR, "diffs")
SITE_DIR = os.path.join(HERE, "site")
API_DIR = os.path.join(SITE_DIR, "api")

RUNS_HISTORY_SHOWN = 52  # ~1 year of weekly runs


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_run_log():
    if not os.path.exists(LOG_FILE):
        return []
    runs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [skip] run_log.jsonl line {lineno} is not valid JSON ({e})")
    return runs


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def format_group(fmt):
    """Same grouping logic as the dashboard uses client-side -- kept here
    too so files.json's format_group field is self-consistent even if
    someone consumes the API without loading the dashboard at all."""
    f = (fmt or "").lower()
    if any(k in f for k in ("spreadsheet", "csv", "tsv", "sheet")):
        return "spreadsheet"
    if "pdf" in f:
        return "pdf"
    if "document" in f and "google" not in f:
        return "document"
    if "presentation" in f and "google" not in f:
        return "presentation"
    if "google" in f:
        return "google"
    if "json" in f:
        return "json"
    if "archive" in f:
        return "archive"
    return "other"


def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def standardize_records(state):
    scrape_id = state.get("scrape_id")
    records = []
    for url, meta in state.get("files", {}).items():
        records.append({
            "source_type": "file",
            "url": url,
            "filename": meta.get("filename"),
            "title": meta.get("title_guess"),
            "category": meta.get("category"),
            "format": meta.get("format"),
            "format_group": format_group(meta.get("format")),
            "year": meta.get("year_guess") or None,
            "last_modified": meta.get("last_modified"),
            "etag": meta.get("etag"),
            "size_bytes": _int_or_none(meta.get("content_length")),
            "content_type": meta.get("content_type"),
            "columns": meta.get("columns") or [],
            "sheet_names": meta.get("sheet_names") or [],
            "columns_error": meta.get("columns_error"),
            "http_error": meta.get("http_error"),
            "last_checked": meta.get("last_checked"),
            "scrape_id": scrape_id,
        })
    for url, meta in state.get("google_docs", {}).items():
        fmt = meta.get("format") or "Google Doc/Sheet (external)"
        records.append({
            "source_type": "google_doc",
            "url": url,
            "filename": None,
            "title": meta.get("title_guess"),
            "category": meta.get("category"),
            "format": fmt,
            "format_group": format_group(fmt),
            "year": None,
            "last_modified": None,
            "etag": None,
            "size_bytes": None,
            "content_type": None,
            "columns": meta.get("columns") or [],
            "sheet_names": [],
            "columns_error": meta.get("columns_error"),
            "http_error": None,
            "last_checked": meta.get("last_checked"),
            "scrape_id": scrape_id,
        })
    records.sort(key=lambda r: (r["category"] or "", r["title"] or ""))
    return records


def write_csv(records, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["category", "filename", "title", "format", "year", "last_modified",
              "size_bytes", "columns", "url", "source_type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["columns"] = "; ".join(r.get("columns") or [])
            writer.writerow(row)


def build_runs(run_log):
    keep = run_log[-RUNS_HISTORY_SHOWN:]
    return [{
        "run_number": r.get("run_number"),
        "scrape_id": r.get("scrape_id"),
        "run_time": r.get("scan_time"),
        "pages_visited": r.get("pages_visited"),
        "total_files": r.get("total_files"),
        "total_google_docs": r.get("total_google_docs"),
        "new_files": r.get("new_files"),
        "changed_files": r.get("changed_files"),
        "removed_files": r.get("removed_files"),
        "new_google_docs": r.get("new_google_docs"),
        "changed_api_services": r.get("changed_api_services"),
    } for r in keep]


def build_latest(state, run_log):
    last_run = run_log[-1] if run_log else {}
    return {
        "scrape_id": state.get("scrape_id"),
        "run_time": state.get("last_scan"),
        "run_number": state.get("run_number", last_run.get("run_number")),
        "counts": {
            "files": len(state.get("files", {})),
            "google_docs": len(state.get("google_docs", {})),
            "api_services": len(state.get("api_services", {})),
        },
        "last_run_changes": {
            "new_files": last_run.get("new_files", 0),
            "changed_files": last_run.get("changed_files", 0),
            "removed_files": last_run.get("removed_files", 0),
            "new_google_docs": last_run.get("new_google_docs", 0),
            "changed_api_services": last_run.get("changed_api_services", 0),
        },
    }


def copy_recent_diffs(api_dir):
    """Mirror the N most recent per-run diffs into api/changes/<scrape_id>.json
    -- filenames already match scrape_id since 01_scan.py names them that way.

    Tolerant of a messy diffs/ folder (empty files, non-.json files, a
    truncated file from an interrupted prior run) -- one bad file shouldn't
    take down the whole export, so we skip and warn instead of crashing."""
    changes_dir = os.path.join(api_dir, "changes")
    os.makedirs(changes_dir, exist_ok=True)
    if not os.path.isdir(DIFFS_DIR):
        return
    fnames = sorted(
        (f for f in os.listdir(DIFFS_DIR) if f.lower().endswith(".json")),
        reverse=True,
    )[:RUNS_HISTORY_SHOWN]
    copied = 0
    for fname in fnames:
        src = os.path.join(DIFFS_DIR, fname)
        if os.path.getsize(src) == 0:
            print(f"  [skip] {fname} is empty")
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                diff = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  [skip] {fname} is not valid JSON ({e})")
            continue
        save_json(os.path.join(changes_dir, fname), diff)
        copied += 1
    print(f"  copied {copied}/{len(fnames)} diff files into {changes_dir}")


def build_index(latest):
    return {
        "generated_at": latest.get("run_time"),
        "description": (
            "Static JSON export of the Chicago Education Data Monitor's latest "
            "scan. No auth, no rate limit -- these are just files served by "
            "GitHub Pages. Cross-origin GET works without any extra config."
        ),
        "endpoints": [
            {"name": "latest", "path": "api/latest.json",
             "description": "scrape_id, run_time, run_number, and counts for the most recent scrape."},
            {"name": "files", "path": "api/files.json",
             "description": "Standardized array of every tracked file and Google Doc/Sheet."},
            {"name": "files_csv", "path": "api/files.csv",
             "description": "Same inventory as files.json, flattened to CSV."},
            {"name": "api_services", "path": "api/api_services.json",
             "description": "Reachability status of each api.cps.edu service as of the latest scrape."},
            {"name": "runs", "path": "api/runs.json",
             "description": f"History of the last {RUNS_HISTORY_SHOWN} scan runs."},
            {"name": "changes", "path": "api/changes/{scrape_id}.json",
             "description": "Per-run diff (new/changed/removed). See runs.json for available scrape_ids."},
        ],
    }


def main():
    state = load_state()
    run_log = load_run_log()
    records = standardize_records(state)

    save_json(os.path.join(API_DIR, "files.json"), records)
    write_csv(records, os.path.join(API_DIR, "files.csv"))
    save_json(os.path.join(API_DIR, "api_services.json"), state.get("api_services", {}))
    save_json(os.path.join(API_DIR, "runs.json"), build_runs(run_log))

    latest = build_latest(state, run_log)
    save_json(os.path.join(API_DIR, "latest.json"), latest)
    save_json(os.path.join(API_DIR, "index.json"), build_index(latest))
    copy_recent_diffs(API_DIR)

    print(f"Wrote API export to {API_DIR} ({len(records)} records, "
          f"scrape_id={latest['scrape_id']}, run_number={latest['run_number']})")


if __name__ == "__main__":
    main()
