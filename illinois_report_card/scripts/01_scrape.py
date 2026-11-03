"""
Illinois Report Card ("ILRC") Public Data Set scraper.

Scrapes ISBE's Illinois State Report Card Data page for "<YYYY> Report Card
Public Data Set" links, maps each to its school year (YYYY is the END year
of the covered school year, e.g. a page link labeled "2025 Report Card
Public Data Set" covers school year 2024-2025), and downloads any file not
already in illinois_report_card/data/raw/.

Adapted from Mariam Raheem's 01_ILRC data scraper.py (ILRC_FILE_NAME_DICT /
ILRC_BASE_URL). Behavior is preserved and extended:
  - Files are now discovered by scraping the live page instead of a
    hardcoded {year: filename} dict, so a new year's release is picked up
    automatically without a code change. (The 2025-2026 Public Data Set
    -- "2026-RC-Public-Data-Set.xlsx" -- is already in FALLBACK_FILES
    below; it turned out to be live sooner than the prior years' typical
    lag suggested.)
  - The original hardcoded dict is kept as FALLBACK_FILES in case ISBE
    changes its page markup and the scrape finds nothing for a year that
    is known to exist.
  - "Skip if already present" / "--overwrite" added, matching this repo's
    scraper convention (see docs/conventions.md).

Source page: https://www.isbe.net/pages/illinois-state-report-card-data.aspx
Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

ISBE_REPORT_CARD_PAGE = "https://www.isbe.net/pages/illinois-state-report-card-data.aspx"
ISBE_DOWNLOAD_BASE = "https://www.isbe.net/_layouts/Download.aspx?SourceUrl=/Documents/"

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "illinois_report_card" / "data" / "raw"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0; "
    "+https://github.com/) requests"
}
TIMEOUT = 60
RETRIES = 3

# Known-good mapping as of 10/2026 (from the original ILRC scraper). Used
# only as a fallback for a year the live scrape doesn't find -- the primary
# path is always the live page, since ISBE's filename convention is
# inconsistent year to year (full year, two-digit year, or no year at all
# in the filename itself) and can't be trusted on its own.
FALLBACK_FILES: dict[str, str] = {
    "2025-2026": "2026-RC-Public-Data-Set.xlsx",
    "2024-2025": "2025-Report-Card-Public-Data-Set.xlsx",
    "2023-2024": "24-RC-Pub-Data-Set.xlsx",
    "2022-2023": "23-RC-Pub-Data-Set.xlsx",
    "2021-2022": "2022-Report-Card-Public-Data-Set.xlsx",
    "2020-2021": "2021-RC-Pub-Data-Set.xlsx",
    "2019-2020": "2020-Report-Card-Public-Data-Set.xlsx",
    "2018-2019": "2019-Report-Card-Public-Data-Set.xlsx",
    "2017-2018": "Report-Card-Public-Data-Set.xlsx",
}

# Matches the link text ISBE uses for every year's entry, e.g.
# "2025 Report Card Public Data Set". The number is the END year of the
# school year it covers.
LABEL_RE = re.compile(r"\b(20\d{2})\s+Report\s+Card\s+Public\s+Data\s+Set\b", re.I)


# --------------------------------------------------------------------------
# Discover available files
# --------------------------------------------------------------------------

def get_report_card_files(base_url: str = ISBE_REPORT_CARD_PAGE) -> dict[str, str]:
    """Scrape the ISBE report card page for Public Data Set download links.

    Returns: { "<start_year>-<end_year>": full_file_url }, e.g.
    { "2024-2025": "https://www.isbe.net/_layouts/Download.aspx?..." }
    """
    resp = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    files: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        m = LABEL_RE.search(text)
        if not m:
            continue

        href = link["href"]
        if not href.lower().endswith(".xlsx"):
            # Older (pre-2017-18) sets are .xls or .zip; out of scope here,
            # same as the original scraper.
            continue

        end_year = int(m.group(1))
        school_year = f"{end_year - 1}-{end_year}"
        files[school_year] = urljoin(base_url, href)

    return files


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------

def download_file(url: str, save_dir: Path, file_name: str) -> Path:
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file_name

    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            file_path.write_bytes(resp.content)
            return file_path
        except requests.RequestException as e:
            last_err = e
            print(f"  attempt {attempt}/{RETRIES} failed for {url}: {e}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to download {url} after {RETRIES} attempts") from last_err


def download_report_cards(save_dir: Path = RAW_DIR, overwrite: bool = False) -> list[str]:
    """Scrape the ISBE page and download any Public Data Set not already
    in save_dir. Falls back to FALLBACK_FILES for a known year the scrape
    didn't turn up (e.g. ISBE reorganizes the page).

    Returns the list of newly-downloaded file names (empty if nothing
    changed, which is the common case on scheduled re-runs -- ISBE
    typically publishes one new Public Data Set per year, often many
    months after that school year ends).
    """
    save_dir.mkdir(parents=True, exist_ok=True)

    try:
        files = get_report_card_files()
    except requests.RequestException as e:
        print(f"Could not reach {ISBE_REPORT_CARD_PAGE} ({e}); using fallback list only.")
        files = {}

    # Fill in any known year the live scrape missed, without overwriting
    # a URL the scrape did find (the live page is the source of truth).
    for year, file_name in FALLBACK_FILES.items():
        files.setdefault(year, ISBE_DOWNLOAD_BASE + file_name)

    downloaded = []
    for year in sorted(files, reverse=True):
        url = files[year]
        file_name = f"{year}.xlsx"
        file_path = save_dir / file_name

        if file_path.exists() and not overwrite:
            print(f"Skipping {file_name} (already exists)")
            continue

        print(f"Downloading {file_name} ...")
        download_file(url, save_dir, file_name=file_name)
        downloaded.append(file_name)

    return downloaded


def write_status(new_files: list[str], save_dir: Path = RAW_DIR) -> Path:
    """Record that a scrape ran and what it found. This file's own
    last-modified time (and git history, once committed) is how to check
    *when this last ran* and whether it found anything new -- a scheduled
    run that finds nothing new still updates checked_at, it just leaves
    new_files empty, so "last checked" and "last updated" can be told
    apart. The dashboard's "data as of" tile reads this file.
    """
    status = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "new_files": new_files,
        "years_on_disk": sorted(p.stem for p in save_dir.glob("*.xlsx")),
    }
    status_path = save_dir / "_scrape_status.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    return status_path


if __name__ == "__main__":
    overwrite_flag = "--overwrite" in sys.argv
    new_files = download_report_cards(overwrite=overwrite_flag)
    status_path = write_status(new_files)
    if new_files:
        print(f"\n{len(new_files)} new file(s) downloaded:")
        for f in new_files:
            print(f"  - {f}")
    else:
        print("\nNo new files - raw data is already up to date.")
    print(f"Wrote {status_path}")
