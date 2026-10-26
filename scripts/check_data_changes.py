"""
Check every cleaned data file for changes since the last check, and log what changed.

For each file it records a fingerprint (size, SHA-256) and, for CSVs, the row count
and column names. It compares that with the snapshot from the previous run and
reports files that were added, removed or changed, including row-count changes and
added or dropped columns. Standard library only.

Run monthly by .github/workflows/backup-data.yml, which also copies the data to S3
and opens a GitHub issue when something changed. Safe to run locally any time.

Inputs:
    <dataset>/data/clean/*        every dataset's cleaned outputs (found automatically)
    reference/**                  shared lookups (crosswalk, boundaries)
    datasets/changes/snapshot.json   fingerprints from the last run (if any)

Outputs (datasets/changes/):
    snapshot.json      fingerprints from this run (the next run compares against it)
    CHANGELOG.md       one dated section per run that found changes, newest first
    latest_summary.md  this run's summary (used for the GitHub issue and job summary)

Exit code is 0 either way; the workflow reads `changed=true|false` from
$GITHUB_OUTPUT when it is set.

Usage:
    python scripts/check_data_changes.py
"""
import csv
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# ---------------- Config ----------------
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "datasets" / "changes"
SNAPSHOT = OUT_DIR / "snapshot.json"
CHANGELOG = OUT_DIR / "CHANGELOG.md"
SUMMARY = OUT_DIR / "latest_summary.md"

WATCH_GLOBS = ["*/data/clean/*", "reference/**/*"]   # relative to the repo root
SKIP_NAMES = {".gitkeep", "README.md"}
SKIP_SUFFIXES = {".py", ".pyc"}
LFS_POINTER_PREFIX = b"version https://git-lfs"      # a pointer, not the real file


def list_files():
    """Every watched data file, as repo-relative POSIX paths."""
    files = set()
    for pattern in WATCH_GLOBS:
        for p in REPO_ROOT.glob(pattern):
            if p.is_file() and p.name not in SKIP_NAMES and p.suffix not in SKIP_SUFFIXES:
                files.add(p.relative_to(REPO_ROOT).as_posix())
    return sorted(files)


def fingerprint(rel):
    """Size, hash and (for CSVs) row count and columns for one file."""
    path = REPO_ROOT / rel
    raw = path.read_bytes()
    fp = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if raw.startswith(LFS_POINTER_PREFIX):
        fp["lfs_pointer"] = True          # real content not checked out; hash is of the pointer
        return fp
    if rel.endswith((".csv", ".csv.gz")):
        opener = gzip.open if rel.endswith(".gz") else open
        with opener(path, "rt", newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            fp["columns"] = header
            fp["rows"] = sum(1 for _ in reader)
    return fp


def load_previous():
    """Fingerprints from the last run, or {} on the first run."""
    if SNAPSHOT.exists():
        return json.loads(SNAPSHOT.read_text(encoding="utf-8")).get("files", {})
    return {}


def compare(prev, curr):
    """Lists of added, removed and changed files, with what changed in each."""
    added = sorted(set(curr) - set(prev))
    removed = sorted(set(prev) - set(curr))
    changed = []
    for rel in sorted(set(prev) & set(curr)):
        a, b = prev[rel], curr[rel]
        if a["sha256"] == b["sha256"]:
            continue
        notes = []
        if "rows" in a and "rows" in b and a["rows"] != b["rows"]:
            notes.append(f"rows {a['rows']:,} → {b['rows']:,} ({b['rows'] - a['rows']:+,})")
        if "columns" in a and "columns" in b:
            gained = [c for c in b["columns"] if c not in a["columns"]]
            dropped = [c for c in a["columns"] if c not in b["columns"]]
            if gained:
                notes.append("new columns: " + ", ".join(gained))
            if dropped:
                notes.append("dropped columns: " + ", ".join(dropped))
        if not notes:
            notes.append(f"values changed (size {a['bytes']:,} → {b['bytes']:,} bytes)")
        changed.append((rel, notes))
    return added, removed, changed


def describe(rel, fp):
    """Short description of a new file."""
    if "rows" in fp:
        return f"{fp['rows']:,} rows, {len(fp['columns'])} columns"
    return f"{fp['bytes']:,} bytes"


def write_outputs(curr, added, removed, changed, first_run, now):
    """Write the new snapshot, this run's summary, and prepend to the changelog."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"checked_at": now, "files": curr}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    lfs = [r for r, fp in curr.items() if fp.get("lfs_pointer")]
    lines = [f"## Data check, {now[:10]}", ""]
    if first_run:
        lines += [f"First run: recorded a baseline for {len(curr)} files. Future runs report changes against it.", ""]
    elif not (added or removed or changed):
        lines += [f"No changes in {len(curr)} watched files since the last check.", ""]
    else:
        lines += [f"{len(changed)} changed, {len(added)} added, {len(removed)} removed (of {len(curr)} watched files).", ""]
        if changed:
            lines += ["**Changed**", ""] + [f"- `{r}`: {'; '.join(n)}" for r, n in changed] + [""]
        if added:
            lines += ["**Added**", ""] + [f"- `{r}` ({describe(r, curr[r])})" for r in added] + [""]
        if removed:
            lines += ["**Removed**", ""] + [f"- `{r}`" for r in removed] + [""]
    if lfs:
        lines += [f"_Note: {len(lfs)} Git LFS file(s) were not downloaded, so only their pointers were checked: "
                  + ", ".join(f"`{r}`" for r in lfs) + "._", ""]
    summary = "\n".join(lines)
    SUMMARY.write_text(summary, encoding="utf-8")
    if first_run or added or removed or changed:
        old = CHANGELOG.read_text(encoding="utf-8").split("\n", 2)[2] if CHANGELOG.exists() else ""
        CHANGELOG.write_text("# Data change log\n\n" + summary + "\n" + old, encoding="utf-8")
    return summary


def report(changed_flag, summary):
    """Print the summary and hand the result to GitHub Actions if running there."""
    print(summary)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if changed_flag else 'false'}\n")


def main():
    prev = load_previous()
    curr = {rel: fingerprint(rel) for rel in list_files()}
    added, removed, changed = compare(prev, curr)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = write_outputs(curr, added, removed, changed, not prev, now)
    report(bool(prev) and bool(added or removed or changed), summary)


if __name__ == "__main__":
    main()
