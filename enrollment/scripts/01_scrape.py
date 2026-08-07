"""
CPS Demographics ("20th Day Enrollment") scraper.

Scrapes the CPS district-data demographics page for GENERAL / RACE / EL_IEP
report links (xls/xlsx/pdf), classifies them by category + school year, and
downloads new files into enrollment/data/raw/.

Adapted from Mariam Raheem's CPS_demographic_data_scraper.ipynb. Behavior is
preserved; only file locations changed (repo-relative instead of a personal
Google Drive / mapped network path) and a few robustness fixes were added
(request timeout/retries, a User-Agent header, and "skip if already present"
so re-runs don't re-download years that haven't changed).

Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CPS_DEMOGRAPHICS_URL = "https://www.cps.edu/about/district-data/demographics/"

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "enrollment" / "data" / "raw"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0; "
    "+https://github.com/) requests"
}
TIMEOUT = 60
RETRIES = 3


def extract_school_year(filename: str) -> str | None:
    fn = filename.lower()

    # 1) Explicit 4-digit - 4-digit (ensure not followed by another digit)
    m = re.search(r"(20\d{2})\s*[-_]\s*(20\d{2})(?!\d)", fn)
    if m:
        y1, y2 = int(m.group(1)), int(m.group(2))
        start, end = (y1, y2) if y1 <= y2 else (y2, y1)
        return f"{start}-{end}"

    # 2) 4-digit - 2-digit (e.g., "2014-15")
    m = re.search(r"(20\d{2})\s*[-_]\s*(\d{2})(?!\d)", fn)
    if m:
        start = int(m.group(1))
        end = 2000 + int(m.group(2))
        if end <= start:
            end = start + 1
        return f"{start}-{end}"

    # 3) syYYYY -> end year is YYYY -> return (YYYY-1)-YYYY
    m = re.search(r"sy(20\d{2})", fn)
    if m:
        end = int(m.group(1))
        return f"{end - 1}-{end}"

    # 4) Fiscal year style: "fy15" -> "2014-2015"
    # (?!\d) avoids misreading a 4-digit year like "fy2026" as "fy20")
    m = re.search(r"fy(\d{2})(?!\d)", fn)
    if m:
        yr = int(m.group(1))
        if yr <= 30:
            return f"{2000 + yr - 1}-{2000 + yr}"

    # 5) fallback: pick the largest 4-digit year present (likely school-year end)
    years = [int(y) for y in re.findall(r"(20\d{2})", fn) if 2000 <= int(y) <= 2035]
    if years:
        end = max(years)
        return f"{end - 1}-{end}"

    return None


def get_cps_reports(base_url: str = CPS_DEMOGRAPHICS_URL) -> dict[str, str]:
    """Scrape the CPS demographics page for report file links.

    Returns: { "<CATEGORY>_<YEAR>": full_file_url }
    """
    resp = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    reports: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not href.lower().endswith((".xls", ".xlsx", ".pdf")):
            continue

        file_url = urljoin(base_url, href)
        filename = Path(href).name
        year_label = extract_school_year(filename)

        fn_lower = filename.lower()
        category = "GENERAL"
        if any(word in fn_lower for word in ["lep", "elp", "iep", "sped"]):
            category = "EL_IEP"
        elif any(word in fn_lower for word in ["racial", "ethnic", "race"]):
            category = "RACE"

        key = f"{category}_{year_label}" if year_label else f"{category}_{filename}"
        reports[key] = file_url

    return reports


def download_file(url: str, save_dir: Path, file_name: str | None = None) -> Path:
    save_dir.mkdir(parents=True, exist_ok=True)
    file_name = file_name or url.split("/")[-1]
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


def download_cps_reports(save_dir: Path = RAW_DIR, overwrite: bool = False) -> list[str]:
    """Scrape the demographics page and download all reports not already present.

    Returns the list of newly-downloaded file names (empty if nothing changed,
    which is the common case on scheduled re-runs).
    """
    reports = get_cps_reports()
    save_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for key, url in reports.items():
        ext = Path(url).suffix
        file_name = f"{key}{ext}"
        file_path = save_dir / file_name

        if file_path.exists() and not overwrite:
            continue

        print(f"Downloading {file_name} ...")
        download_file(url, save_dir, file_name=file_name)
        downloaded.append(file_name)

    return downloaded


if __name__ == "__main__":
    overwrite_flag = "--overwrite" in sys.argv
    new_files = download_cps_reports(overwrite=overwrite_flag)
    if new_files:
        print(f"\n{len(new_files)} new file(s) downloaded:")
        for f in new_files:
            print(f"  - {f}")
    else:
        print("\nNo new files - raw data is already up to date.")
