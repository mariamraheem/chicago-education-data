"""
Stage 3: compile district- and network-level enrollment aggregates.

This is the "roll it up" stage: it doesn't standardize raw files the way
02_clean.py does (that's row/school-level cleaning) - it takes raw and/or
cleaned data and builds the summarized tables used for reporting: EL/IEP
status by network, and race counts both district-wide (10-year comparison)
and by network. Two independent sections below, merged into one script
because they're both "compile" outputs (adapted from Mariam Raheem's
Compiling_el_iep_data.ipynb and Compiling_enrollment_race_aggregates.py).

Reads:  enrollment/data/raw/EL_IEP*.xls*, enrollment/data/raw/RACE*.xls*
Writes: enrollment/data/clean/enrollment_network_el_iep_aggregate.csv
        enrollment/data/clean/enrollment_race_aggregates_<MMDDYYYY>.csv
        enrollment/data/clean/enrollment_network_race_aggregates_<MMDDYYYY>.csv
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "enrollment" / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "enrollment" / "data" / "clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================================
# Section A: EL/IEP network-level aggregates
# ==========================================================================

def pct_to_decimal(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return pd.NA
    if isinstance(x, str):
        x = x.strip()
        if x == "" or x.lower() == "nan":
            return pd.NA
        if x.endswith("%"):
            try:
                return float(x.rstrip("%")) / 100
            except ValueError:
                return pd.NA
        try:
            return float(x)
        except ValueError:
            return pd.NA
    try:
        return float(x)
    except (ValueError, TypeError):
        return pd.NA


def combine_network_metrics_safe(input_dir: Path, prefix: str = "EL_IEP") -> pd.DataFrame:
    all_data = []
    files = sorted(input_dir.glob(f"{prefix}*.xls*"), key=lambda f: f.stem, reverse=True)

    for file in files:
        parts = file.stem.split("_")
        year = parts[2] if len(parts) >= 3 else parts[-1]
        xls = pd.ExcelFile(file)

        if "Networks" in xls.sheet_names:
            sheet_name = "Networks"
        elif "Network" in xls.sheet_names:
            sheet_name = "Network"
        else:
            candidates = [s for s in xls.sheet_names if "Network" in s]
            if not candidates:
                print(f"!! Skipping {file.name}: no Network sheet found")
                continue
            sheet_name = candidates[0]

        df = pd.read_excel(file, sheet_name=sheet_name, header=None)

        first_col_sample = df.iloc[:5, 0].astype(str).str.lower().tolist()
        if any("grade" in str(x).lower() for x in first_col_sample):
            print(f"!! Skipping {file.name}: grade-level data, not network data")
            continue

        mask = df.iloc[:, 0].astype(str).str.contains("^Network$", na=False, case=False, regex=True)
        header_row_idx = df.index[mask]
        if header_row_idx.empty:
            mask = df.iloc[:, 0].astype(str).str.contains("Network", na=False, case=False)
            header_row_idx = df.index[mask]
        if header_row_idx.empty:
            print(f"!! Skipping {file.name}: no 'Network' header row found")
            continue

        header_row = header_row_idx[0]
        if header_row < 1:
            print(f"!! Skipping {file.name}: no group row available")
            continue

        group_row = df.iloc[header_row - 1]
        metric_row = df.iloc[header_row]

        group_row_filled = []
        current_group = ""
        for col_idx in range(df.shape[1]):
            val = group_row.iloc[col_idx] if col_idx < len(group_row) else ""
            val_str = str(val).strip() if not pd.isna(val) else ""

            if val_str and not val_str.startswith("20th Day"):
                current_group = val_str
                group_row_filled.append(val_str)
            elif not val_str and col_idx < len(metric_row):
                metric_next = str(metric_row.iloc[col_idx]).strip() if not pd.isna(metric_row.iloc[col_idx]) else ""
                if metric_next in ["N", "%", "No", "Pct", "Percent"]:
                    group_row_filled.append(current_group)
                else:
                    group_row_filled.append("")
                    current_group = ""
            else:
                group_row_filled.append(val_str)
                if val_str and not val_str.startswith("20th Day"):
                    current_group = val_str

        standard_cols = []
        for col_idx in range(df.shape[1]):
            group_str = group_row_filled[col_idx] if col_idx < len(group_row_filled) else ""
            metric_val = metric_row.iloc[col_idx] if col_idx < len(metric_row) else ""
            metric_str = str(metric_val).strip() if not pd.isna(metric_val) else ""

            if col_idx == 0:
                col_name = "Network"
            elif "Total" in metric_str or "Total" in group_str:
                col_name = "Total_Enrollment"
            elif metric_str in ["N", "No", "Number"]:
                col_name = f'{group_str.replace(" ", "")}_N' if group_str else "Unknown_N"
            elif metric_str in ["%", "Pct", "Percent"] or "%" in metric_str:
                col_name = f'{group_str.replace(" ", "")}_Pct' if group_str else "Unknown_Pct"
            elif group_str and metric_str:
                col_name = f'{group_str.replace(" ", "")}_{metric_str}'
            elif metric_str:
                col_name = metric_str
            elif group_str:
                col_name = group_str.replace(" ", "")
            else:
                col_name = f"Col_{col_idx}"
            standard_cols.append(col_name)

        if len(standard_cols) != df.shape[1]:
            print(f"!! Skipping {file.name}: column count mismatch")
            continue

        df.columns = standard_cols
        if df.columns.duplicated().any():
            new_cols, seen = [], {}
            for col in df.columns:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}_{seen[col]}")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols

        df = df.iloc[header_row + 1:].reset_index(drop=True)
        df = df.dropna(how="all")
        df = df[df["Network"].notna()].copy()
        df["Year"] = year

        pct_cols = [c for c in df.columns if "_Pct" in c]
        for c in pct_cols:
            df[c] = [pct_to_decimal(val) for val in df[c]]

        n_cols = [c for c in df.columns if "_N" in c]
        for c in n_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

        if "Total_Enrollment" in df.columns:
            df["Total_Enrollment"] = pd.to_numeric(df["Total_Enrollment"], errors="coerce").astype("Int64")

        all_data.append(df)
        print(f"Processed {file.name} ({year}): {len(df)} rows")

    if not all_data:
        return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True, sort=False)


def harmonize_network_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Map all EL/SPED/economic-status column name variants to three standard names."""
    if df.empty:
        return df
    df = df.copy()

    column_map = {}
    for col in df.columns:
        if col in ["Network", "Year", "Total_Enrollment"]:
            column_map[col] = col
        elif col in ["StateEnglishLearners_N", "Bilingual_N", "EL_N"]:
            column_map[col] = "State English Learners_N"
        elif col in ["StateEnglishLearners_Pct", "Bilingual_Pct", "EL_Pct"]:
            column_map[col] = "State English Learners_Pct"
        elif col in ["StudentswithDisabilities_N", "StudentsWithDisabilities_N", "DiverseLearners_N", "SpED_N", "SPED_N"]:
            column_map[col] = "Students with Disabilities_N"
        elif col in ["StudentswithDisabilities_Pct", "StudentsWithDisabilities_Pct", "DiverseLearners_Pct", "SpED_Pct", "SPED_Pct"]:
            column_map[col] = "Students with Disabilities_Pct"
        elif col in ["EconomicallyDisadvantaged_N", "Free/ReducedLunch_N", "Free/Reduced\nLunch_N", "FreeLunch_N", "LowIncome_N"]:
            column_map[col] = "Economically Disadvantaged_N"
        elif col in ["EconomicallyDisadvantaged_Pct", "Free/ReducedLunch_Pct", "Free/Reduced\nLunch_Pct", "FreeLunch_Pct", "LowIncome_Pct"]:
            column_map[col] = "Economically Disadvantaged_Pct"
        else:
            print(f"  Unmapped column (kept as-is): {col}")
            column_map[col] = col

    df.rename(columns=column_map, inplace=True)

    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated(keep=False)].unique()
        final_df = df.loc[:, ~df.columns.duplicated(keep="first")].copy()
        for dup_col in duplicates:
            dup_data = df.loc[:, df.columns == dup_col]
            final_df[dup_col] = dup_data.bfill(axis=1).iloc[:, 0]
        return final_df

    return df


def compile_el_iep() -> None:
    raw_df = combine_network_metrics_safe(INPUT_DIR)
    if raw_df.empty:
        print("No EL_IEP*.xls* files found in enrollment/data/raw - skipping.")
        return
    clean_df = harmonize_network_groups(raw_df)
    if "Network" in clean_df.columns:
        # Broad, case-insensitive "*total*" match -- drops aggregate rows
        # like "District Total", "Charter Total", "Regular School Totals",
        # etc. Legitimate values like "Regular Educational Units" don't
        # contain "total" and pass through.
        clean_df = clean_df[~clean_df["Network"].astype(str).str.contains("total", case=False, na=False)]
    out = OUTPUT_DIR / "enrollment_network_el_iep_aggregate.csv"
    clean_df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(clean_df)} rows)")


# ==========================================================================
# Section B: RACE district + network aggregates
# ==========================================================================

def combine_10_year_race_data(input_dir: Path, prefix="RACE") -> pd.DataFrame:
    files = sorted(input_dir.glob(f"{prefix}*.xls*"), key=lambda f: f.stem, reverse=True)[:10]

    all_data = []
    for file in files:
        year = file.stem.split("_")[1]
        try:
            df = pd.read_excel(file, sheet_name="Comparison", header=None)

            # The "Comparison" sheet's column layout shifts by a column
            # across years (older years put the race label in column 0 with
            # N/% in columns 2/3; newer years shift everything one column
            # right). A hardcoded df[[1, 4]] silently grabbed the "%" column
            # instead of "N" in newer years (e.g. 0.11 instead of 36693),
            # which get truncated to 0 once cast to int downstream -- that's
            # why the race charts were rendering with every count at zero.
            # Find the header row (the one containing literal "N" and "%"
            # cells) and locate those columns by content, not position.
            header_row_idx, n_col = None, None
            for i in range(min(10, len(df))):
                row = df.iloc[i].astype(str).str.strip()
                matches_n = row[row == "N"]
                matches_pct = row[row == "%"]
                if len(matches_n) and len(matches_pct):
                    header_row_idx = i
                    n_col = matches_n.index[0]
                    break
            if header_row_idx is None:
                print(f"!! {file.name}: couldn't find 'N'/'%' header on Comparison sheet, skipping")
                continue
            # The race-label column is consistently two columns to the left
            # of "N" (one blank spacer column in between) in every year seen
            # so far -- verified against both the old and new layouts.
            race_col = n_col - 2
            if race_col < 0:
                print(f"!! {file.name}: unexpected Comparison sheet layout, skipping")
                continue

            temp = df[[race_col, n_col]].iloc[header_row_idx + 1:]
            temp.columns = ["Race", "Count"]
            temp = temp.dropna(subset=["Race", "Count"])
            temp["Year"] = year
            temp["Count"] = pd.to_numeric(temp["Count"], errors="coerce")
            all_data.append(temp)
        except Exception as e:  # noqa: BLE001
            print(f"!! Error reading {file.name}: {e}")

    if not all_data:
        return pd.DataFrame(columns=["Race", "Count", "Year"])

    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df["Race"] = combined_df["Race"].str.strip().replace({
        # CPS relabels race categories over the years (verified against
        # the raw Comparison sheets): "African American" (2016-17 through
        # 2022-23) becomes "Black/African American" (2023-24) becomes just
        # "Black" (2024-25+); "Native American" (2016-17 only) becomes
        # "Native American/Alaskan" (2017-18+). Without normalizing these
        # to one canonical label, the same demographic group shows up as
        # multiple different chart series with gaps -- e.g. "African
        # American" plotting 2016-22 then flatlining at 0 while "Black"
        # picks up from 2023 on.
        "African American": "Black",
        "Black/African American": "Black",
        "Latinx": "Hispanic",
        "Multi-Racial": "Multiracial",
        "Native American": "NativeAmerican",
        "Native American/Alaskan": "NativeAmerican",
    })
    # "Asian/Pacific Islander (retired)" is a distinct legacy line CPS
    # keeps in every Comparison sheet alongside the real "Asian" row (not
    # a renamed version of it -- both appear in the same year with their
    # own counts, usually a token ~1-14). Relabeling it to "Asian" would
    # silently sum it into the real Asian count instead of representing a
    # separate (basically defunct) category, so it's dropped outright.
    combined_df = combined_df[combined_df["Race"] != "Asian/Pacific Islander (retired)"]
    # Broad, case-insensitive "*total*" match -- drops rows like "District
    # Total" / "Total" so they aren't charted as if they were a race group.
    combined_df = combined_df[~combined_df["Race"].astype(str).str.contains("total", case=False, na=False)]
    return combined_df


def combine_race_networks(input_dir: Path, prefix="RACE") -> pd.DataFrame:
    files = sorted(input_dir.glob(f"{prefix}*.xls*"), key=lambda f: f.stem, reverse=True)
    all_data = []

    for file in files:
        year = file.stem.split("_")[1]
        try:
            df = pd.read_excel(file, sheet_name="Networks", header=None)

            header_row = df.index[df.iloc[:, 0].astype(str).str.contains("Network", na=False)]
            if len(header_row) == 0:
                print(f"Skipping {file.name}: No 'Network' header found")
                continue
            header_row = header_row[0]

            # The race-name row is Excel merged cells -- "White" only
            # appears in the leftmost cell of its No/Pct pair, with the
            # cell above "Pct" blank. Forward-filling before doing a
            # positional (same-index) lookup keeps each No/Pct pair matched
            # to the right race. The previous version used a single shared
            # iterator advanced once per No/Pct cell regardless of column
            # position, which silently shifted every race's numbers onto
            # the wrong column (e.g. Asian's count ending up on the row
            # labeled "Not Available") once there was a title cell (like
            # "20th Day 2025-2026") occupying column 0.
            races = df.iloc[header_row - 1].ffill().tolist()
            headers = df.iloc[header_row].tolist()

            clean_cols = []
            for i, col in enumerate(headers):
                col_str = str(col).strip()
                race_label = str(races[i]).strip() if i < len(races) and pd.notna(races[i]) else ""
                if col_str in ["Network", "Total"]:
                    clean_cols.append(col_str)
                elif col_str == "No":
                    clean_cols.append(f"{race_label}_No")
                elif col_str == "Pct":
                    clean_cols.append(f"{race_label}_Pct")
                else:
                    clean_cols.append(col_str)

            df.columns = clean_cols
            df = df.iloc[header_row + 1:].reset_index(drop=True)
            df["Year"] = year

            df_melted = df.melt(
                id_vars=["Year", "Network", "Total"],
                var_name="Race_Stat",
                value_name="Value",
            )

            if df_melted["Race_Stat"].str.contains("_").any():
                df_melted[["Race", "Stat"]] = df_melted["Race_Stat"].str.rsplit("_", n=1, expand=True)
            else:
                df_melted["Race"], df_melted["Stat"] = df_melted["Race_Stat"], "No"

            df_melted = df_melted.drop(columns=["Race_Stat"])

            df_clean = df_melted.pivot_table(
                index=["Year", "Network", "Total", "Race"],
                columns="Stat",
                values="Value",
                aggfunc="first",
            ).reset_index()

            all_data.append(df_clean)
        except Exception as e:  # noqa: BLE001
            print(f"Error reading {file.name}: {e}")

    if not all_data:
        return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)


def compile_race_aggregates() -> None:
    combined_race_df = combine_10_year_race_data(INPUT_DIR)
    df_raw = combine_race_networks(INPUT_DIR)

    if not df_raw.empty:
        # Note: errors="coerce" (not "raise" as in the original notebook) so
        # a single malformed year doesn't fail the whole scheduled run.
        df_raw["No"] = pd.to_numeric(df_raw["No"], errors="coerce").fillna(0)
        df_raw["Pct"] = pd.to_numeric(df_raw["Pct"], errors="coerce").fillna(0)

        # Broad, case-insensitive "*total*" match -- not just the exact
        # phrase "district total" -- so rows like "Charter Total", "Regular
        # School Totals", "Charter Schools Totals", etc. are dropped too.
        df_raw = df_raw[~df_raw["Network"].astype(str).str.contains("total", case=False, na=False)]
        df_raw = df_raw[~df_raw["Race"].astype(str).str.contains("20th", case=False, na=False)]

        df_networks_clean = df_raw.copy()
        df_networks_clean["Race_clean"] = df_networks_clean["Race"].fillna("Not Available")
        df_networks_clean["Race_clean"] = df_networks_clean["Race_clean"].replace(r"^\s*$", "Not Available", regex=True)
        df_networks_clean["Race_clean"] = df_networks_clean["Race_clean"].replace({"Not \n Available": "Not Available"})
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)black|african", na=False), "Race_clean"] = "Black/African American"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)hispanic|latinx", na=False), "Race_clean"] = "Hispanic/Latino"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)multiracial|multi-racial|mulit-racial", na=False), "Race_clean"] = "Multiracial"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)native", na=False), "Race_clean"] = "Native American/Alaskan"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)hawaiian", na=False), "Race_clean"] = "Hawaiian/Pacific Islander"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.contains(r"(?i)asian.*pacific.*retired", na=False), "Race_clean"] = "Asian/Pacific Islander (Retired)"
        df_networks_clean.loc[df_networks_clean["Race_clean"].str.match(r"(?i)^asian$", na=False), "Race_clean"] = "Asian"
        df_networks_clean["Race_clean"] = df_networks_clean["Race_clean"].fillna("Not Available")

        date_suffix = date.today().strftime("%m%d%Y")
        out = OUTPUT_DIR / f"enrollment_network_race_aggregates_{date_suffix}.csv"
        df_networks_clean.to_csv(out, index=False)
        print(f"Wrote {out} ({len(df_networks_clean)} rows)")
    else:
        print("No RACE*.xls* Networks data found in enrollment/data/raw - skipping network race aggregates.")

    date_suffix = date.today().strftime("%m%d%Y")
    out = OUTPUT_DIR / f"enrollment_race_aggregates_{date_suffix}.csv"
    combined_race_df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(combined_race_df)} rows)")


if __name__ == "__main__":
    compile_el_iep()
    compile_race_aggregates()
