"""
Stage 5: build stable-filename demographic trend data for the dashboard's
race / English Learner / Students with Disabilities / Economically
Disadvantaged visuals.

03_compile.py's outputs are exactly what these charts need, but two of them
carry a run-date suffix (enrollment_race_aggregates_<MMDDYYYY>.csv,
enrollment_network_race_aggregates_<MMDDYYYY>.csv) so history doesn't get
clobbered. That's right for archival, but a static dashboard needs a fixed
filename to fetch() -- this script picks the most recent dated file of each
kind and republishes it under a stable name next to the dashboard, the same
pattern 04_build_dashboard_data.py uses for enrollment_general_clean.csv.

Also applies the same "drop aggregate rows" rule 04 does (any District/
Network/Race value containing "total") so a summary row never gets charted
as if it were real data.

Reads:  enrollment/data/clean/enrollment_network_el_iep_aggregate.csv
        enrollment/data/clean/enrollment_race_aggregates_*.csv (newest)
        enrollment/data/clean/enrollment_network_race_aggregates_*.csv (newest)
Writes: enrollment/dashboard/enrollment_network_demographics.csv
          (network, school_year, metric, pct, n)
        enrollment/dashboard/enrollment_race_trend.csv
          (school_year, race, count)
        enrollment/dashboard/enrollment_network_race.csv
          (school_year, network, race, count, pct)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DIR = REPO_ROOT / "enrollment" / "data" / "clean"
DASHBOARD_DIR = REPO_ROOT / "enrollment" / "dashboard"

EL_IEP_FILE = CLEAN_DIR / "enrollment_network_el_iep_aggregate.csv"

# (metric label shown in the UI) -> (source _Pct column, source _N column)
EL_IEP_METRICS = {
    "English Learners": ("State English Learners_Pct", "State English Learners_N"),
    "Students with Disabilities": ("Students with Disabilities_Pct", "Students with Disabilities_N"),
    "Economically Disadvantaged": ("Economically Disadvantaged_Pct", "Economically Disadvantaged_N"),
}


def _is_total(series: pd.Series) -> pd.Series:
    return series.astype(str).str.contains("total", case=False, na=False)


def _newest(pattern: str) -> Path | None:
    files = sorted(CLEAN_DIR.glob(pattern))
    return files[-1] if files else None


def build_network_demographics() -> pd.DataFrame:
    if not EL_IEP_FILE.exists():
        print(f"{EL_IEP_FILE} not found -- run 03_compile.py first. Skipping network demographics.")
        return pd.DataFrame()

    df = pd.read_csv(EL_IEP_FILE)
    if "Network" in df.columns:
        df = df[~_is_total(df["Network"])]

    rows = []
    for metric, (pct_col, n_col) in EL_IEP_METRICS.items():
        if pct_col not in df.columns:
            continue
        for _, row in df.iterrows():
            pct = pd.to_numeric(row.get(pct_col), errors="coerce")
            n = pd.to_numeric(row.get(n_col), errors="coerce") if n_col in df.columns else pd.NA
            if pd.isna(pct):
                continue
            rows.append({
                "school_year": row.get("Year"),
                "network": row.get("Network"),
                "metric": metric,
                "pct": round(float(pct), 4),
                "n": int(n) if pd.notna(n) else None,
            })
    return pd.DataFrame(rows)


def build_race_trend() -> pd.DataFrame:
    source = _newest("enrollment_race_aggregates_*.csv")
    if source is None:
        print("No enrollment_race_aggregates_*.csv found -- run 03_compile.py first. Skipping race trend.")
        return pd.DataFrame()

    df = pd.read_csv(source)
    if "Race" in df.columns:
        df = df[~_is_total(df["Race"])]
    df = df.dropna(subset=["Count"])
    df["Count"] = pd.to_numeric(df["Count"], errors="coerce")
    df = df.dropna(subset=["Count"])
    df["Count"] = df["Count"].astype(int)

    out = df.rename(columns={"Year": "school_year", "Race": "race", "Count": "count"})
    return out[["school_year", "race", "count"]].sort_values(["school_year", "race"]).reset_index(drop=True)


def build_network_race() -> pd.DataFrame:
    source = _newest("enrollment_network_race_aggregates_*.csv")
    if source is None:
        print("No enrollment_network_race_aggregates_*.csv found -- run 03_compile.py first. Skipping network race.")
        return pd.DataFrame()

    df = pd.read_csv(source)
    for col in ("Network", "Race", "Race_clean"):
        if col in df.columns:
            df = df[~_is_total(df[col])]

    race_col = "Race_clean" if "Race_clean" in df.columns else "Race"
    rename = {"Year": "school_year", "Network": "network", race_col: "race", "No": "count", "Pct": "pct"}
    cols = [c for c in rename if c in df.columns]
    out = df[cols].rename(columns=rename)
    if "count" in out.columns:
        out["count"] = pd.to_numeric(out["count"], errors="coerce")
    if "pct" in out.columns:
        out["pct"] = pd.to_numeric(out["pct"], errors="coerce")
    return out.dropna(subset=[c for c in ("network", "race") if c in out.columns]).reset_index(drop=True)


def _write(df: pd.DataFrame, filename: str) -> None:
    if df.empty:
        print(f"Nothing to write for {filename}.")
        return
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    out = DASHBOARD_DIR / filename
    df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")


if __name__ == "__main__":
    _write(build_network_demographics(), "enrollment_network_demographics.csv")
    _write(build_race_trend(), "enrollment_race_trend.csv")
    _write(build_network_race(), "enrollment_network_race.csv")
