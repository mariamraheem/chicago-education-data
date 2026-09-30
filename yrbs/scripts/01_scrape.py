"""
YRBS (CDC Youth Risk Behavior Survey) scraper.

Downloads CDC's combined high school datasets ("SADC"), which hold every survey year
(1991 onward) in one fixed-width file per geography, and keeps:
  - Chicago rows (sitecode CH) from the combined district file
  - Illinois rows (sitecode IL) from the I-L state file
  - the full national file
plus CDC's SAS input/format programs (the column layout and labels).

Files land in yrbs/data/raw/. Re-runs skip files that are already present unless
--force is given. When CDC publishes a new release (every two years), bump RELEASE.

CDC's file server intermittently returns a 404 HTML page for files that exist, so
downloads retry and reject HTML responses.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

RELEASE = "2025"
BASE = f"https://www.cdc.gov/yrbs/files/sadc_{RELEASE}/"

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "yrbs" / "data" / "raw"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; K1C-data-pipeline/1.0) requests"}

# output name -> (source file, sitecode to keep or None for all rows)
DATA_FILES = {
    "yrbs_sadc_chicago.dat": (f"sadc_{RELEASE}_district.dat", "CH"),
    "yrbs_sadc_illinois.dat": (f"sadc_{RELEASE}_state_i_l.dat", "IL"),
    "yrbs_sadc_national.dat": (f"sadc_{RELEASE}_national.dat", None),
}
DOC_FILES = [f"{RELEASE}-SADC-SAS-Input-Program.sas", f"{RELEASE}-SADC-SAS-Formats-Program.sas"]


def fetch(url: str, tries: int = 10) -> requests.Response:
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
            if r.ok and "html" not in r.headers.get("content-type", ""):
                return r
            r.close()
        except requests.RequestException:
            pass
        time.sleep(min(3 * (i + 1), 20))
    raise RuntimeError(f"Could not download {url} after {tries} tries")


def download_filtered(src: str, dest: Path, sitecode: str | None) -> int:
    r = fetch(BASE + src)
    n = 0
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as out:
        buf = b""
        for chunk in r.iter_content(1 << 20):
            buf += chunk
            lines = buf.split(b"\n")
            buf = lines.pop()
            for ln in lines:
                if ln.strip() and (sitecode is None or ln[:5].strip().decode() == sitecode):
                    out.write(ln.rstrip(b"\r") + b"\n")
                    n += 1
        if buf.strip() and (sitecode is None or buf[:5].strip().decode() == sitecode):
            out.write(buf.rstrip(b"\r") + b"\n")
            n += 1
    tmp.replace(dest)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download files already present")
    args = ap.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for name in DOC_FILES:
        dest = RAW_DIR / name
        if dest.exists() and not args.force:
            print(f"skip {name} (present)")
            continue
        dest.write_bytes(fetch(BASE + name).content)
        print(f"saved {name}")

    for name, (src, site) in DATA_FILES.items():
        dest = RAW_DIR / name
        if dest.exists() and not args.force:
            print(f"skip {name} (present)")
            continue
        n = download_filtered(src, dest, site)
        print(f"saved {name}: {n:,} records from {src}")
        if n == 0:
            sys.exit(f"{name}: no records kept -- check the sitecode or file layout")


if __name__ == "__main__":
    main()
