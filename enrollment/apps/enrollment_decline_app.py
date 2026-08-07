###################################
# Author: Mariam Raheem
# Purpose: School-level enrollment decline analysis
# Adapted for the repo: only the data path changed (was a personal Google
# Drive path, now repo-relative to enrollment/data/clean).
###################################

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ----------------------------
# Streamlit Config -- following the same setup as original app
# ----------------------------
st.set_page_config(
    layout="wide",
    page_title="CPS School-Level Enrollment Declines"
)

st.title("Chicago Public Schools: School-Level Enrollment Declines")

# ----------------------------
# Load Data
# ----------------------------
ENROLLMENT_ROOT = Path(__file__).resolve().parent.parent  # .../enrollment
data_dir = ENROLLMENT_ROOT / "data" / "clean"

df_general = pd.read_csv(data_dir / "enrollment_general_clean.csv")

# ----------------------------
# CPS Grade Groups -- original classification
# ----------------------------
cps_groups = {
    "PE": ["PE"],
    "Pre-K": ["PK"],
    "Kindergarten": ["K"],
    "Elementary": [f"Grade {i}" for i in range(1,6)],
    "Middle School": [f"Grade {i}" for i in range(6,9)],
    "High School": [f"Grade {i}" for i in range(9,13)]
}

all_cps_cols = [col for cols in cps_groups.values() for col in cols]

# ---------------------------------
# Making sure all year/school_ids are numeric
# ----------------------------
id_cols = ["Year", "School ID"]

for col in all_cps_cols:
    if col in df_general.columns:
        df_general[col] = pd.to_numeric(df_general[col], errors="coerce")

# ----------------------------
# School-Year Total Enrollment
# ----------------------------
school_year_totals = (
    df_general
    .groupby(id_cols, as_index=False)
    .sum(numeric_only=True)
)

school_year_totals["Total Enrollment"] = (
    school_year_totals[all_cps_cols].sum(axis=1)
)

# Drop rows with zero or missing enrollment
school_year_totals = school_year_totals[
    school_year_totals["Total Enrollment"] > 0
]

# ----------------------------
# Sidebar Controls
# ----------------------------
st.sidebar.header("Analysis Controls")

years_sorted = sorted(school_year_totals["Year"].unique())

base_year = st.sidebar.selectbox(
    "Base Year",
    years_sorted,
    index=0
)

compare_year = st.sidebar.selectbox(
    "Compare To",
    years_sorted,
    index=len(years_sorted) - 1
)


top_n = st.sidebar.slider(
    "Number of schools to show",
    min_value=5,
    max_value=50,
    value=20
)

# ----------------------------
# Compute Declines
# ----------------------------
base_df = school_year_totals[
    school_year_totals["Year"] == base_year
][["School ID", "School Name", "Total Enrollment"]].rename(
    columns={"Total Enrollment": "Base Enrollment"}
)

compare_df = school_year_totals[
    school_year_totals["Year"] == compare_year
][["School ID", "School Name", "Total Enrollment"]].rename(
    columns={"Total Enrollment": "Compare Enrollment"}
)

declines_df = base_df.merge(
    compare_df,
    on=["School ID", "School Name"],
    how="inner"
)

declines_df["Absolute Change"] = (
    declines_df["Compare Enrollment"] - declines_df["Base Enrollment"]
)

declines_df["Percent Change"] = (
    declines_df["Absolute Change"] / declines_df["Base Enrollment"] * 100
)

declines_df = declines_df.sort_values("Absolute Change")

# ----------------------------
# Summary Metrics
# ----------------------------
total_schools = declines_df.shape[0]
declining = (declines_df["Absolute Change"] < 0).sum()

col1, col2, col3 = st.columns(3)
col1.metric("Schools Analyzed", total_schools)
col2.metric("Schools with Declines", declining)
col3.metric(
    "Median % Change",
    f"{declines_df['Percent Change'].median():+.2f}%"
)

# ----------------------------
# Declines Table
# ----------------------------
st.subheader(
    f"Largest Enrollment Declines ({base_year} → {compare_year})"
)

display_df = declines_df.head(top_n)[[
    "School Name",
    "Base Enrollment",
    "Compare Enrollment",
    "Absolute Change",
    "Percent Change"
]]

st.dataframe(
    display_df.style.format({
        "Base Enrollment": "{:,.0f}",
        "Compare Enrollment": "{:,.0f}",
        "Absolute Change": "{:+,.0f}",
        "Percent Change": "{:+.2f}%"
    }),
    use_container_width=True
)

# ----------------------------
# School Selector
# ----------------------------
st.subheader("School Enrollment Trend")

selected_school = st.selectbox(
    "Select a school",
    display_df["School Name"]
)

school_trend = (
    school_year_totals[
        school_year_totals["School Name"] == selected_school
    ]
    .sort_values("Year")
)

# ----------------------------
# Trend Line
# ----------------------------
fig_line = px.line(
    school_trend,
    x="Year",
    y="Total Enrollment",
    markers=True,
    title=f"{selected_school}: Enrollment Over Time",
    labels={
        "Total Enrollment": "Number of Students",
        "Year": "School Year"
    },
    hover_data={"Total Enrollment": ":,"}
)

fig_line.update_layout(template="plotly_white")
st.plotly_chart(fig_line, use_container_width=True)

# ----------------------------
# YoY % Change for Selected School
# ----------------------------
school_trend = school_trend.copy()
school_trend["YoY % Change"] = (
    school_trend["Total Enrollment"].pct_change() * 100
)

fig_yoy = px.bar(
    school_trend.dropna(),
    x="Year",
    y="YoY % Change",
    text=school_trend["YoY % Change"].dropna().apply(lambda x: f"{x:+.2f}%"),
    title=f"{selected_school}: Year-on-Year % Change"
)

fig_yoy.update_traces(textposition="outside")
fig_yoy.update_layout(
    template="plotly_white",
    showlegend=False
)

st.plotly_chart(fig_yoy, use_container_width=True)
