"""
Check the scraped NAEP scores against numbers we already published.

Compares naep_scores_wide.csv to:
  1. the 2026 NAEP brief's figure data (naep/data/reference/brief_figures/):
     fig 1 (Chicago, all students, 2003-2024) and figs 3-4 (all TUDAs, 2024).
     those are whole numbers, so scraped scores are rounded before comparing.
  2. optionally, the hand-built NAEP_Compiled_Wide.xlsx (pass --handbuilt).
     that one's on the shared drive, not in the repo. compared to 0.5 points.

Nothing is changed -- this only reports matches, mismatches and gaps. Exits
with an error if anything mismatches, so the GitHub Actions run goes red.

Inputs:  naep/data/clean/naep_scores_wide.csv, naep/data/reference/brief_figures/*.csv
Run:     python naep/scripts/03_validate.py
         python naep/scripts/03_validate.py --handbuilt "path/to/NAEP_Compiled_Wide.xlsx"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---- Config -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
WIDE = REPO_ROOT / "naep" / "data" / "clean" / "naep_scores_wide.csv"
FIG_DIR = REPO_ROOT / "naep" / "data" / "reference" / "brief_figures"
FIG1 = FIG_DIR / "fig1_chicago_scores_over_time.csv"
FIG_TUDA = [FIG_DIR / "fig3_tuda_grade4_2024.csv", FIG_DIR / "fig4_tuda_grade8_2024.csv"]

HANDBUILT_TOLERANCE = 0.5  # points
KEYS = ["Year", "Jurisdiction", "Subject", "Grade"]

# fig 1 column -> (subject, grade)
FIG1_COLUMNS = {
    "Grade 4 Math": ("Mathematics", 4),
    "Grade 4 Reading": ("Reading", 4),
    "Grade 8 Math": ("Mathematics", 8),
    "Grade 8 Reading": ("Reading", 8),
}


# ---- Steps --------------------------------------------------------------------

def load_scraped() -> pd.DataFrame:
    """Scraped wide table, all-students column only."""
    df = pd.read_csv(WIDE)
    return df[KEYS + ["All students"]]


def brief_targets() -> pd.DataFrame:
    """Published brief numbers in one long table: keys + expected whole-number score."""
    f1 = pd.read_csv(FIG1)
    rows = []
    for col, (subj, grade) in FIG1_COLUMNS.items():
        for _, r in f1.iterrows():
            rows.append({"Year": int(r["Year"]), "Jurisdiction": "Chicago",
                         "Subject": subj, "Grade": grade, "expected": r[col], "source": "fig 1"})
    for f in FIG_TUDA:
        t = pd.read_csv(f)
        t = t[t["Category"] == "All students"]
        for _, r in t.iterrows():
            rows.append({"Year": int(r["Year"]), "Jurisdiction": r["Jurisdiction"],
                         "Subject": r["Subject"], "Grade": int(r["Grade"]),
                         "expected": r["Average Scale Score"], "source": f.stem.split("_")[0]})
    return pd.DataFrame(rows)


def compare(scraped: pd.DataFrame, targets: pd.DataFrame, label: str, rounded: bool,
            tol: float) -> int:
    """Join on keys and report. Returns the number of mismatches + missing."""
    m = targets.merge(scraped, on=KEYS, how="left")
    # round half up like the published numbers -- pandas .round() rounds .5 to even
    got = np.floor(m["All students"] + 0.5) if rounded else m["All students"]
    missing = m["All students"].isna() & m["expected"].notna()
    bad = (~missing) & m["expected"].notna() & ((got - m["expected"]).abs() > tol)
    ok = len(m) - missing.sum() - bad.sum()

    print(f"\n{label}: {len(m)} checks -- {ok} match, {bad.sum()} differ, {missing.sum()} missing from scrape")
    if bad.any():
        print(m.loc[bad, KEYS + ["expected", "All students"]].head(25).to_string(index=False))
    if missing.any():
        print("missing:")
        print(m.loc[missing, KEYS].head(25).to_string(index=False))
    return int(bad.sum() + missing.sum())


def handbuilt_targets(path: Path) -> pd.DataFrame:
    """Hand-built workbook, all-students column, as expected values."""
    h = pd.read_excel(path)
    h["Subject"] = h["Subject"].str.strip()
    h = h[KEYS + ["All students"]].rename(columns={"All students": "expected"})
    h["source"] = "handbuilt"
    return h.dropna(subset=["expected"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handbuilt", type=Path, help="path to NAEP_Compiled_Wide.xlsx")
    args = ap.parse_args()

    scraped = load_scraped()
    print(f"scraped: {len(scraped):,} rows")
    problems = compare(scraped, brief_targets(), "2026 brief figures", rounded=True, tol=0)
    if args.handbuilt:
        problems += compare(scraped, handbuilt_targets(args.handbuilt), "hand-built workbook",
                            rounded=False, tol=HANDBUILT_TOLERANCE)

    if problems:
        sys.exit(f"\n{problems} checks didn't line up -- look before using the scraped file")
    print("\nall checks line up")


if __name__ == "__main__":
    main()
