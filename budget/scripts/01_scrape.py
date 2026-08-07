"""
CPS budget document scraper (district managed funds, student based budget,
revenue, etc.).

Unlike the enrollment/demographics page (a single static page listing every
report), CPS's budget pages are split into one hub page per fiscal year
(https://www.cps.edu/about/finance/budget/budget-<year>/) with several
sub-pages underneath (budget overview, schools and networks, revenue, fund
descriptions, reader's guide). This script:

  1. Reads the main budget index page to discover every "Budget <year>" hub
     page CPS has published.
  2. Crawls each year's hub page plus its known sub-pages for .xls/.xlsx
     links, classifying them by filename keywords.
  3. Always additionally attempts every URL listed in known_urls.yaml, a
     manually-maintained fallback list (some CPS budget documents are linked
     in a way this crawler doesn't reliably discover - see that file for
     why). Manual entries win if there's a naming conflict.
  4. Downloads anything not already present into budget/data/raw/.

Run from anywhere; paths are resolved relative to the repo root.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

BUDGET_INDEX_URL = "https://www.cps.edu/about/finance/budget/"

# Sub-pages checked under each https://www.cps.edu/about/finance/budget/budget-<year>/
SUBPAGE_TEMPLATES = [
    "",  # the hub page itself
    "budget-overview-{year}/",
    "schools-and-networks-{year}/",
    "revenue-{year}/",
    "fund-descriptions-{year}/",
    "readers-guide-{year}/",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "budget" / "data" / "raw"
KNOWN_URLS_FILE = REPO_ROOT / "budget" / "known_urls.yaml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0; "
    "+https://github.com/) requests"
}
TIMEOUT = 60
RETRIES = 3


def classify_filename(filename: str) -> str:
    fn = filename.lower()
    if "district" in fn and "manag" in fn:
        return "DISTRICT_MANAGED"
    if "student" in fn and ("based" in fn or "sbb" in fn):
        return "STUDENT_BASED"
    if "revenue" in fn:
        return "REVENUE"
    if "general" in fn or "overview" in fn:
        return "GENERAL"
    return "OTHER"


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        print(f"  ! could not fetch {url}: {e}")
        return None


def discover_budget_years(base_url: str = BUDGET_INDEX_URL) -> list[int]:
    soup = _fetch(base_url)
    if soup is None:
        return []

    years = set()
    for link in soup.find_all("a", href=True):
        m = re.search(r"/budget-(20\d{2})/?", link["href"])
        if m:
            years.add(int(m.group(1)))
    return sorted(years, reverse=True)


def get_budget_reports(years: list[int] | None = None) -> dict[str, str]:
    """Crawl each year's budget hub + sub-pages for xls/xlsx links.

    Returns: { "<CATEGORY>_<year>": file_url }
    """
    if years is None:
        years = discover_budget_years()

    reports: dict[str, str] = {}

    for year in years:
        hub_url = urljoin(BUDGET_INDEX_URL, f"budget-{year}/")
        for template in SUBPAGE_TEMPLATES:
            page_url = urljoin(hub_url, template.format(year=year))
            soup = _fetch(page_url)
            if soup is None:
                continue

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.lower().endswith((".xls", ".xlsx")):
                    continue

                file_url = urljoin(page_url, href)
                filename = Path(href).name
                category = classify_filename(filename)
                key = f"{category}_{year}"

                # Don't let a later, less-specific page (e.g. the bare hub)
                # stomp on a file already found on a more specific sub-page.
                reports.setdefault(key, file_url)

    return reports


def load_known_urls() -> dict[str, str]:
    if not KNOWN_URLS_FILE.exists():
        return {}
    with open(KNOWN_URLS_FILE) as f:
        data = yaml.safe_load(f) or {}
    # Ignore commented-out / null entries
    return {k: v for k, v in data.items() if v}


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


def download_budget_reports(save_dir: Path = RAW_DIR, overwrite: bool = False) -> list[str]:
    crawled = get_budget_reports()
    manual = load_known_urls()

    # Manual entries win on key conflicts (they exist specifically because
    # the crawler got something wrong or missed it).
    reports = {**crawled, **manual}

    print(f"Found {len(crawled)} link(s) via crawling, {len(manual)} manual override(s), "
          f"{len(reports)} total after merge.")

    downloaded = []
    for key, url in reports.items():
        ext = Path(url).suffix
        file_name = f"{key}{ext}"
        file_path = save_dir / file_name

        if file_path.exists() and not overwrite:
            continue

        print(f"Downloading {file_name} ...")
        try:
            download_file(url, save_dir, file_name=file_name)
            downloaded.append(file_name)
        except RuntimeError as e:
            print(f"!! {e}")

    return downloaded


if __name__ == "__main__":
    overwrite_flag = "--overwrite" in sys.argv
    new_files = download_budget_reports(overwrite=overwrite_flag)
    if new_files:
        print(f"\n{len(new_files)} new file(s) downloaded:")
        for f in new_files:
            print(f"  - {f}")
    else:
        print("\nNo new files - raw data is already up to date.")
