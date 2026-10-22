"""
<What this step does, in one or two lines.>

<Anything non-obvious about the source: quirks, why it's done this way.>

Inputs:  <url or <dataset>/data/raw/...>
Outputs: <dataset>/data/<raw|clean>/...
Run:     python <dataset>/scripts/01_<step>.py            # skips files already present
         python <dataset>/scripts/01_<step>.py --force    # redo everything
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# ---- Config -------------------------------------------------------------------
# paths, urls, years, thresholds -- everything you'd change lives here

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "<dataset>"
RAW_DIR = DATASET_DIR / "data" / "raw"
CLEAN_DIR = DATASET_DIR / "data" / "clean"

SOURCE_URL = "<url>"
YEARS = []  # e.g. [2024, 2025, 2026]


# ---- Steps --------------------------------------------------------------------

def load(path: Path) -> pd.DataFrame:
    """Read one source file."""
    df = pd.read_csv(path)
    print(f"  {path.name}: {len(df):,} rows")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy one file: names, types, suppression."""
    # blanks stay blank -- never fill or carry forward
    return df


def export(df: pd.DataFrame, out: Path) -> None:
    """Write the output and say what was written."""
    out.parent.mkdir(parents=True, exist_ok=True)
    # write to .part first so an interrupted run never leaves a half file behind
    tmp = out.with_suffix(".part")
    df.to_csv(tmp, index=False)
    tmp.replace(out)
    print(f"wrote {out.relative_to(REPO_ROOT)} ({len(df):,} rows)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="redo files already present")
    args = ap.parse_args()

    # read like a table of contents: load -> clean -> export
    ...


if __name__ == "__main__":
    main()
