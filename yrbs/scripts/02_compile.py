"""
Step 2 of the YRBS pipeline: compile historic YRBS data (CDC combined high school "SADC" datasets, 2025 release,
covering 1991-2025) for Chicago (district), Illinois (state) and the United States.

Inputs  (yrbs/data/raw/, from 01_scrape.py):
  yrbs_sadc_chicago.dat, yrbs_sadc_illinois.dat, yrbs_sadc_national.dat
  2025-SADC-SAS-Input-Program.sas   (CDC's column layout + variable labels)

Outputs (yrbs/data/clean/):
  yrbs_microdata_1991_2025.parquet       student-level records, all three geographies
  yrbs_microdata_chicago.csv             student-level records, Chicago
  yrbs_microdata_illinois.csv            student-level records, Illinois
  yrbs_prevalence_long.csv               weighted % + 95% CI by geography/year/indicator/subgroup
  yrbs_prevalence_total_wide.csv         overall %, one column per year (Flourish-ready)

Method: weighted prevalence of each dichotomous qn* variable (1 = yes, 2 = no).
SEs by Taylor linearization using stratum/PSU (strata nested within year; single-PSU
strata contribute zero). 95% CIs are logit-transformed with t df = PSUs - strata.
Estimates based on fewer than 100 students are flagged suppress = True (CDC rule).
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import t as tdist
except ImportError:
    tdist = None

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "yrbs" / "data" / "raw"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "yrbs" / "data" / "clean"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- column layout from CDC's SAS input program ----------
sas = (RAW / "2025-SADC-SAS-Input-Program.sas").read_text(errors="replace")
inp = sas[re.search(r"^\s*input\s*$", sas, re.I | re.M).end():]
inp = inp[: inp.index(";")]
LAYOUT = [(m[1].lower(), bool(m[2]), int(m[3]) - 1, int(m[4]))
          for m in re.finditer(r"([A-Za-z_]\w*)\s+(\$?)\s*(\d+)\s*-\s*(\d+)", inp)]
LABELS = {m[1].lower(): m[2].strip()
          for m in re.finditer(r"\b(\w+)\s*=\s*\"([^\"]*)\"", sas)}
WIDTH = max(b for *_, b in LAYOUT)


def read_fixed(path, geo):
    """Memory-light fixed-width reader: slices a byte matrix instead of pandas read_fwf."""
    lines = Path(path).read_bytes().replace(b"\r", b"").split(b"\n")
    lines = [ln.ljust(WIDTH)[:WIDTH] for ln in lines if ln.strip()]
    buf = np.frombuffer(b"".join(lines), dtype="S1").reshape(len(lines), WIDTH)
    data = {"geography": np.full(len(lines), geo, dtype=object)}
    for name, is_char, a, b in LAYOUT:
        col = np.ascontiguousarray(buf[:, a:b]).view(f"S{b - a}").ravel()
        s = pd.Series(np.char.strip(col).astype(str))
        if is_char:
            s = s.replace({"": None, ".": None})
            data[name] = s.astype("category") if name.startswith("q") else s
        else:
            data[name] = pd.to_numeric(s.replace({"": None, ".": None}), errors="coerce").astype("float32") \
                if name.startswith("qn") else pd.to_numeric(s.replace({"": None, ".": None}), errors="coerce")
    return pd.DataFrame(data)


FILES = {"Chicago": "yrbs_sadc_chicago.dat",
         "Illinois": "yrbs_sadc_illinois.dat",
         "United States": "yrbs_sadc_national.dat"}

QN = [n for n, is_char, *_ in LAYOUT if n.startswith("qn") and not is_char]
GROUPS = [("Total", "Total", None)] + \
    [("Sex", g, ("sex", v)) for g, v in [("Female", 1), ("Male", 2)]] + \
    [("Grade", g, ("grade", v)) for g, v in [("9th", 1), ("10th", 2), ("11th", 3), ("12th", 4)]] + \
    [("Race/ethnicity", g, ("race4", v)) for g, v in
     [("White", 1), ("Black or African American", 2), ("Hispanic/Latino", 3), ("All other races", 4)]]


def estimate(d):
    """Weighted prevalence + linearized SE for every qn* indicator in one geography-year."""
    d = d[np.isfinite(d["weight"]) & (d["weight"] > 0)]
    w = d["weight"].to_numpy(float)
    strat = d["stratum"].fillna(-1).to_numpy()
    psu = d["psu"].to_numpy(float)
    if np.isnan(psu).all():                       # no design info -> each student is a PSU
        psu = np.arange(len(d), dtype=float)
    psu = np.where(np.isnan(psu), -np.arange(1, len(d) + 1), psu)
    key, uniq = pd.factorize(pd.MultiIndex.from_arrays([strat, psu]))
    psu_strat = np.asarray(uniq.get_level_values(0))
    strata = [np.flatnonzero(psu_strat == h) for h in np.unique(psu_strat)]
    Yraw = d[QN].to_numpy(float)
    V = np.isin(Yraw, (1, 2))
    Y = (Yraw == 1).astype(float)
    out = []
    for gtype, gname, rule in GROUPS:
        dom = np.ones(len(d), bool) if rule is None else (d[rule[0]].to_numpy() == rule[1])
        M = V & dom[:, None]
        n = M.sum(0)
        WM = w[:, None] * M
        sw = WM.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            p = (WM * Y).sum(0) / sw
            Z = np.nan_to_num(WM * (Y - p) / sw)
        T = np.zeros((len(uniq), Z.shape[1]))
        np.add.at(T, key, Z)
        var = np.zeros(Z.shape[1]); npsu = nstr = 0
        for idx in strata:
            if len(idx) < 2:
                continue
            Th = T[idx]
            var += len(idx) / (len(idx) - 1) * ((Th - Th.mean(0)) ** 2).sum(0)
            npsu += len(idx); nstr += 1
        se = np.sqrt(var)
        tc = tdist.ppf(0.975, max(npsu - nstr, 1)) if tdist else 1.96
        with np.errstate(invalid="ignore", divide="ignore"):
            lg, sl = np.log(p / (1 - p)), se / (p * (1 - p))
            lo, hi = 1 / (1 + np.exp(-(lg - tc * sl))), 1 / (1 + np.exp(-(lg + tc * sl)))
        interior = (p > 0) & (p < 1)
        for j in np.flatnonzero(n > 0):
            out.append((QN[j], gtype, gname, int(n[j]), 100 * p[j], 100 * se[j],
                        100 * lo[j] if interior[j] else np.nan,
                        100 * hi[j] if interior[j] else np.nan))
    return out


def main():
    frames, rows = [], []
    for geo, fname in FILES.items():
        df = read_fixed(RAW / fname, geo)
        print(f"{geo}: {len(df):,} records, years {int(df.year.min())}-{int(df.year.max())}", flush=True)
        if geo != "United States":
            df.to_csv(OUT / f"yrbs_microdata_{geo.lower()}.csv", index=False)
        for y, d in df.groupby("year"):
            rows += [(geo, int(y)) + r for r in estimate(d)]
        frames.append(df)

    pd.concat(frames, ignore_index=True).to_parquet(OUT / "yrbs_microdata_1991_2025.parquet", index=False)

    prev = pd.DataFrame(rows, columns=["geography", "year", "indicator", "group_type", "group",
                                       "n", "pct", "se", "ci_low", "ci_high"])
    prev.insert(3, "indicator_label", prev.indicator.map(LABELS))
    prev["suppress"] = prev.n < 100
    prev[["pct", "se", "ci_low", "ci_high"]] = prev[["pct", "se", "ci_low", "ci_high"]].round(1)
    prev = prev.sort_values(["geography", "indicator", "group_type", "group", "year"])
    prev.to_csv(OUT / "yrbs_prevalence_long.csv", index=False)

    tot = prev[(prev.group == "Total") & ~prev.suppress]
    wide = tot.pivot_table(index=["geography", "indicator", "indicator_label"],
                           columns="year", values="pct").reset_index()
    wide.columns = [str(c) for c in wide.columns]
    wide.to_csv(OUT / "yrbs_prevalence_total_wide.csv", index=False)
    print(f"prevalence rows: {len(prev):,} | indicators: {prev.indicator.nunique()}")


if __name__ == "__main__":
    main()
