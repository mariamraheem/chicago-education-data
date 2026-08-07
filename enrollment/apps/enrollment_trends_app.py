###################################
# Author: Mariam Raheem
# Purpose: Visualize and explore CPS enrollment trends
# Adapted for the repo: data path changed to enrollment/data/clean.
#
# NOTE ON enrollment_el_iep_clean.csv: this app expects a school-level clean
# EL/IEP file at that name, but no script in this repo produces it -
# 03_compile.py only produces the *network*-level aggregate
# (enrollment_network_el_iep_aggregate.csv). This mismatch existed in the
# original notebooks too (no shared script builds a school-level EL/IEP
# clean file). Until that cleaning step is written, this app's Tab 3 will
# error on a fresh run - see the README's "known gaps" section.
###################################

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# To run in VSCode: streamlit.runtime.scriptrunner helps by adding script context to threads
    # These threads can then safely interact with Streamlit components
    # Else, you might see errors like "RuntimeError: No script run context found"
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import time
from threading import Thread

class WorkerThread(Thread):
    def __init__(self, delay, target):
        super().__init__()
        self.delay = delay
        self.target = target

    def run(self):
        start_time = time.time()
        time.sleep(self.delay)
        end_time = time.time()
        self.target.write(f"start: {start_time}, end: {end_time}")

# ----------------------------
# Load Data
# ----------------------------
ENROLLMENT_ROOT = Path(__file__).resolve().parent.parent  # .../enrollment
output_dir = ENROLLMENT_ROOT / "data" / "clean"
output_dir.mkdir(parents=True, exist_ok=True)

df_general = pd.read_csv(output_dir / "enrollment_general_clean.csv")
df_race = pd.read_csv(output_dir / "enrollment_race_clean.csv")
df_el_iep = pd.read_csv(output_dir / "enrollment_el_iep_clean.csv")  # see NOTE above

numeric_cols = [col for col in df_el_iep.columns if col not in ["Year", "School ID", "School Name", "Networks"]]
df_el_iep[numeric_cols] = df_el_iep[numeric_cols].apply(pd.to_numeric, errors='raise')


# ----------------------------
# Rename columns (_ -> space) and reorder
# ----------------------------
def clean_df(df, string_cols):
    df.columns = [col.replace("_", " ") for col in df.columns]
    for col in df.columns:
        if col not in string_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    remaining_cols = [col for col in df.columns if col not in string_cols]
    df = df[string_cols + remaining_cols]
    return df

string_cols_general = ["Year", "School ID", "School Name"]
string_cols_race = ["Year", "School ID", "School Name"]

df_general = clean_df(df_general, string_cols_general)
df_race = clean_df(df_race, string_cols_race)

# ----------------------------
# Last 10 years
# ----------------------------
recent_years = sorted(df_general['Year'].unique(), reverse=True)[:10]
df_general = df_general[df_general['Year'].isin(recent_years)]
df_race = df_race[df_race['Year'].isin(recent_years)]


# ----------------------------
# CPS groups
# ----------------------------
cps_groups = {
    "Pre-K": ["PE", "PK"],
    "Kindergarten": ["K"],
    "Elementary": [f"Grade {i}" for i in range(1,6)],
    "Middle School": [f"Grade {i}" for i in range(6,9)],
    "High School": [f"Grade {i}" for i in range(9,13)]
}


# ----------------------------
# Summarize General Enrollment
# ----------------------------
all_cps_cols = [col for cols in cps_groups.values() for col in cols]
summary_df = df_general.groupby("Year").sum()[all_cps_cols].reset_index()

for group, cols in cps_groups.items():
    existing_cols = [c for c in cols if c in summary_df.columns]
    summary_df[group] = summary_df[existing_cols].sum(axis=1)
summary_df["Total"] = summary_df[list(cps_groups.keys())].sum(axis=1)

schools_per_year = df_general.groupby("Year")["School Name"].nunique().reset_index()
schools_per_year.rename(columns={"School Name": "Distinct Schools"}, inplace=True)
summary_df = summary_df.merge(schools_per_year, on="Year")
num_cols = summary_df.columns.difference(['Year'])
summary_df[num_cols] = summary_df[num_cols].apply(pd.to_numeric, errors='coerce')
summary_df = summary_df.sort_values("Year").reset_index(drop=True)

# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(layout="wide", page_title="CPS Enrollment Trends")
st.title("Chicago Public Schools Enrollment Trends")

tab1, tab2, tab3 = st.tabs(["Overall Enrollment", "Enrollment by Race", "Enrollment by EL/IEP Status"])

# ----------------------------
# Tab 1: Overall Enrollment
# ----------------------------
with tab1:
    st.header("Overall Enrollment Trends")
    view_by = st.radio("View by:", ["CPS Groups", "Grade Levels"], horizontal=True)

    if view_by == "CPS Groups":
        groups_to_use = list(cps_groups.keys())
        title_suffix = "CPS Groups"
    else:
        pre_k_main = [g for g in cps_groups["Pre-K"] if g not in ["Head Start", "Other PK"]]
        pre_k_extra = [g for g in cps_groups["Pre-K"] if g in ["Head Start", "Other PK"]]
        grade_order = pre_k_main + [f"Grade {i}" for i in range(1,13)] + pre_k_extra
        grade_cols = [c for c in summary_df.columns if c in grade_order]
        groups_to_use = grade_cols
        title_suffix = "Grade Levels"

    # ---------------- KPIs + Year Selector ----------------
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([2,2,2,1])
    with kpi_col4:
        years_desc = sorted(summary_df["Year"].unique(), reverse=True)
        kpi_year = st.selectbox("Year", years_desc, index=0, key="kpi_year")

    current_row = summary_df[summary_df["Year"] == kpi_year].iloc[0]
    prev_idx = years_desc.index(kpi_year) + 1 if (years_desc.index(kpi_year)+1) < len(years_desc) else None
    if prev_idx is not None:
        prev_year = years_desc[prev_idx]
        previous_row = summary_df[summary_df["Year"] == prev_year].iloc[0]
    else:
        prev_year, previous_row = None, None

    pct_total = ((current_row["Total"] - previous_row["Total"]) / previous_row["Total"] * 100) if previous_row is not None else 0
    kpi_col1.metric("Total Enrollment",
                    f"{int(current_row['Total']):,}",
                    f"{pct_total:.2f}% vs. {prev_year}" if prev_year else "N/A")

    top_group = current_row[groups_to_use].idxmax()
    excluded = ["Head Start", "Other PK"] if view_by == "Grade Levels" else []
    filtered_groups = [g for g in groups_to_use if g not in excluded]
    min_group = current_row[filtered_groups].idxmin()

    pct_top = ((current_row[top_group] - previous_row[top_group]) / previous_row[top_group] * 100) if previous_row is not None else 0
    pct_min = ((current_row[min_group] - previous_row[min_group]) / previous_row[min_group] * 100) if previous_row is not None else 0

    kpi_col2.metric(f"Largest {title_suffix} ({top_group})",
                    f"{int(current_row[top_group]):,}",
                    f"{pct_top:.2f}% vs. {prev_year}" if prev_year else "N/A")
    kpi_col3.metric(f"Smallest {title_suffix} ({min_group})",
                    f"{int(current_row[min_group]):,}",
                    f"{pct_min:.2f}% vs. {prev_year}" if prev_year else "N/A")

    # ---------------- Line plot ----------------
    metrics_for_line = groups_to_use + ["Total"]
    default_index = metrics_for_line.index("Total") if "Total" in metrics_for_line else 0
    metric = st.selectbox("Select metric for line plot:", metrics_for_line, index=default_index)

    fig_line = px.line(summary_df, x="Year", y=metric, markers=True,
                       labels={"Year":"School Year", metric:"Students"},
                       title=f"{metric} Enrollment Over Last 10 Years",
                       hover_data={metric: ":,"})
    fig_line.update_layout(template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

    # ---------------- YoY % Change Bars ----------------
    yoy_col1, yoy_col2 = st.columns([4, 1])
    with yoy_col2:
        yoy_years_desc = sorted(summary_df["Year"].tolist(), reverse=True)
        selected_year = st.selectbox("Year", yoy_years_desc, index=0, key = "selected_year")

    latest_idx = yoy_years_desc.index(selected_year)
    if latest_idx < len(yoy_years_desc) - 1:
        prev_year = yoy_years_desc[latest_idx + 1]
        latest = summary_df[summary_df["Year"] == selected_year].iloc[0]
        previous = summary_df[summary_df["Year"] == prev_year].iloc[0]

        yoy_values = ((latest[groups_to_use] - previous[groups_to_use]) / previous[groups_to_use] * 100)
        yoy_df = pd.DataFrame({
            "Level": groups_to_use,
            "YoY %": yoy_values,
            "Current": latest[groups_to_use].values,
            "Previous": previous[groups_to_use].values
        })
        yoy_df["Level"] = pd.Categorical(yoy_df["Level"], categories=groups_to_use, ordered=True)

        fig_yoy = px.bar(
            yoy_df,
            x="Level",
            y="YoY %",
            text=yoy_df["YoY %"].apply(lambda x: f"{x:+.2f}%"),
            color=["#1A5D38" if v>0 else "#B0B0B0" for v in yoy_df["YoY %"]],
            category_orders={"Level": groups_to_use},
            color_discrete_map="identity",
            title=f"Year-on-Year % change ({selected_year} vs. {prev_year})"
        )
        fig_yoy.update_traces(
            hovertemplate="<b>%{x}</b><br>YoY %: %{y:+.2f}%<br>Current: %{customdata[0]:,}<br>Previous: %{customdata[1]:,}<extra></extra>",
            customdata=yoy_df[["Current","Previous"]].values,
            textposition="outside"
        )
        fig_yoy.update_layout(template="plotly_white", yaxis=dict(range=[-15,15]), showlegend=False)

        with yoy_col1:
            st.plotly_chart(fig_yoy, use_container_width=True)

    # ---------------- Summary Table ----------------
    table_cols = ["Year"] + groups_to_use + ["Total"]
    st.dataframe(summary_df[table_cols].sort_values("Year", ascending=False))

# ----------------------------
# Tab 2: Enrollment by Race
 # ----------------------------
with tab2:
    st.header("Enrollment by Race")

    # Define fixed categories + order
    fixed_order = [
        "White", "Black", "Asian", "NativeAmerican",
        "Hispanic", "MENA", "Multiracial",
        "Hawaiian/Pacific Islander", "Not Available", "Other"
    ]

    # Identify all " n" columns
    race_cols_n = [col for col in df_race.columns if col.endswith(" n")]

    # Map current columns to simplified categories
    def standardize_race_cols(df):
        df_copy = df.copy()
        df_copy[race_cols_n] = df_copy[race_cols_n].apply(pd.to_numeric, errors='coerce')

        # Extract base names (remove " n")
        base_names = [c.replace(" n","") for c in race_cols_n]

        # Predefined mapping: keep if in fixed list, else -> "Other"
        mapping = {}
        for name in base_names:
            if name in ["White","Black","Asian","NativeAmerican","Hispanic","MENA","Multiracial","Hawaiian/Pacific Islander","Not Available"]:
                mapping[name] = name
            else:
                mapping[name] = "Other"

        # Collapse into standardized categories
        collapsed = df_copy.groupby("Year").sum().reset_index()[["Year"]].copy()
        for cat in fixed_order:
            relevant_cols = [col+" n" for col, mapped in mapping.items() if mapped == cat]
            if relevant_cols:
                collapsed[cat] = df_copy.groupby("Year")[relevant_cols].sum().reset_index()[relevant_cols].sum(axis=1)
            else:
                collapsed[cat] = 0
        return collapsed

    race_summary = standardize_race_cols(df_race)

    # ---------------- KPIs Year Selector ----------------
    race_metric = st.selectbox("Select Race/Ethnicity:", fixed_order, index=fixed_order.index("Hispanic"))

    # Trend line
    fig_race_line = px.line(
        race_summary, x="Year", y=race_metric, markers=True,
        labels={race_metric: f"{race_metric} (n)", "Year":"School Year"},
        title=f"{race_metric} Enrollment Over Last 10 Years",
        hover_data={race_metric: ":,"}
    )
    fig_race_line.update_layout(template="plotly_white")
    st.plotly_chart(fig_race_line, use_container_width=True)

    # ---------------- YoY % Change Bars ----------------
    race_col1, race_col2 = st.columns([4, 1])
    with race_col2:
        race_yoy_years_desc = sorted(race_summary["Year"].tolist(), reverse=True)
        selected_race_year = st.selectbox("Year", race_yoy_years_desc, index=0, key="selected_race_year")

    race_idx = race_yoy_years_desc.index(selected_race_year)
    if race_idx < len(race_yoy_years_desc) - 1:
        prev_race_year = race_yoy_years_desc[race_idx + 1]
        latest = race_summary[race_summary["Year"] == selected_race_year].iloc[0]
        previous = race_summary[race_summary["Year"] == prev_race_year].iloc[0]

        race_yoy = pd.DataFrame({
            "Level": fixed_order,
            "YoY %": ((latest[fixed_order].values - previous[fixed_order].values) / previous[fixed_order].values * 100),
            "Current": latest[fixed_order].values,
            "Previous": previous[fixed_order].values
        })
        race_yoy["Color"] = race_yoy["YoY %"].apply(lambda x: "#1A5D38" if x>0 else "#B0B0B0")

        fig_race_yoy = px.bar(
            race_yoy,
            x="Level", y="YoY %",
            text=race_yoy["YoY %"].apply(lambda x: f"{x:+.2f}%"),
            color="Color",
            category_orders={"Level": fixed_order},
            color_discrete_map="identity",
            title=f"Year-on-Year % change ({selected_race_year} vs. {prev_race_year})"
        )
        fig_race_yoy.update_traces(
            hovertemplate="<b>%{x}</b><br>YoY %: %{y:+.2f}%<br>Current: %{customdata[0]:,}<br>Previous: %{customdata[1]:,}<extra></extra>",
            customdata=race_yoy[["Current","Previous"]].values,
            textposition="outside"
        )
        fig_race_yoy.update_layout(template="plotly_white", yaxis=dict(range=[-15,15]), showlegend=False)

        with race_col1:
            st.plotly_chart(fig_race_yoy, use_container_width=True)

    # ---------------- Stacked Area & Summary Table ----------------
    race_summary["Total"] = race_summary[fixed_order].sum(axis=1)

    df_stacked = race_summary.melt(id_vars="Year", var_name="Race", value_name="Count")
    df_stacked["Race"] = pd.Categorical(df_stacked["Race"], categories=fixed_order, ordered=True)

    fig_stacked = px.area(
        df_stacked, x="Year", y="Count", color="Race",
        labels={"Count":"Number of Students"},
        title="Racial Composition Over Time (Counts)",
        hover_data={"Count": ":,"},
        category_orders={"Race": fixed_order}
    )
    fig_stacked.update_layout(template="plotly_white")
    st.plotly_chart(fig_stacked, use_container_width=True)

    # Final summary table in logical order
    st.dataframe(race_summary[["Year"] + ["Total"] +fixed_order].sort_values("Year", ascending=False))


# ----------------------------
# Tab 3: English Learners & IEP
# ----------------------------
with tab3:
    st.header("English Learner (EL), Special Education, and Economically Disadvantaged Trends")

    # Define metrics and clean labels
    el_iep_metrics = {
        "state_english_learner_n": "English Learners",
        "special_education_n": "Special Education",
        "economically_disadvantaged_n": "Economically Disadvantaged"
    }

    # Summarize counts by Year
    el_iep_summary = df_el_iep.groupby("Year")[list(el_iep_metrics.keys())].sum().reset_index()

    # Line plot for all metrics
    df_melted = el_iep_summary.melt(id_vars="Year", var_name="Metric", value_name="Count")
    df_melted["Metric"] = df_melted["Metric"].map(el_iep_metrics)

    fig_el_iep_line = px.line(
        df_melted, x="Year", y="Count", color="Metric", markers=True,
        labels={"Count": "Number of Students", "Year": "School Year"},
        title="Trends over 10 Years",
        hover_data={"Count": ":,"}
    )
    fig_el_iep_line.update_layout(template="plotly_white")
    st.plotly_chart(fig_el_iep_line, use_container_width=True)

    # Year-on-Year % Change (vertical bars)
    el_iep_col1, el_iep_col2 = st.columns([4,1])
    with el_iep_col2:
        el_iep_years_desc = sorted(el_iep_summary["Year"].tolist(), reverse=True)
        selected_year = st.selectbox("Year", el_iep_years_desc, index=0, key="selected_el_iep_year")

    latest_idx = el_iep_years_desc.index(selected_year)
    if latest_idx < len(el_iep_years_desc) - 1:
        prev_year = el_iep_years_desc[latest_idx + 1]
        latest = el_iep_summary[el_iep_summary["Year"] == selected_year].iloc[0]
        previous = el_iep_summary[el_iep_summary["Year"] == prev_year].iloc[0]

        yoy_values = ((latest[list(el_iep_metrics.keys())] - previous[list(el_iep_metrics.keys())]) / previous[list(el_iep_metrics.keys())] * 100)
        yoy_df = pd.DataFrame({
            "Metric": [el_iep_metrics[m] for m in el_iep_metrics.keys()],
            "YoY %": yoy_values.values,
            "Current": latest[list(el_iep_metrics.keys())].values,
            "Previous": previous[list(el_iep_metrics.keys())].values
        })
        yoy_df["Color"] = yoy_df["YoY %"].apply(lambda x: "#1A5D38" if x > 0 else "#B0B0B0")

        fig_el_iep_yoy = px.bar(
            yoy_df,
            x="Metric",
            y="YoY %",
            text=yoy_df["YoY %"].apply(lambda x: f"{x:+.2f}%"),
            color="Color",
            color_discrete_map="identity",
            title=f"Year-on-Year % Change ({selected_year} vs {prev_year})"
        )
        fig_el_iep_yoy.update_traces(
            hovertemplate="<b>%{x}</b><br>YoY %: %{y:+.2f}%<br>Current: %{customdata[0]:,.2f}<br>Previous: %{customdata[1]:,.2f}<extra></extra>",
            customdata=yoy_df[["Current","Previous"]].values,
            textposition="outside"
        )
        fig_el_iep_yoy.update_layout(template="plotly_white", showlegend=False)

        with el_iep_col1:
            st.plotly_chart(fig_el_iep_yoy, use_container_width=True)

    # Summary Table
    st.dataframe(el_iep_summary.rename(columns=el_iep_metrics).sort_values("Year", ascending=False))
