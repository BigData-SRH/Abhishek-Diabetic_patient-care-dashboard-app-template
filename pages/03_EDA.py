import streamlit as st
import altair as alt
from core import get_theme, apply_theme_css, get_filtered_data

theme = get_theme(False)
apply_theme_css(theme)

st.title("Exploratory Data Analysis (EDA)")

df = get_filtered_data()

if df.empty:
    st.info("No data for the current filter selection.")
else:
    st.subheader("Distribution of Length of Stay")
    los_chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("time_in_hospital:Q", bin=alt.Bin(maxbins=20), title="LOS (days)"),
            y=alt.Y("count():Q", title="Count"),
        )
    )
    st.altair_chart(los_chart, use_container_width=True)

    st.subheader("Distribution of Number of Medications")
    meds_chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("num_medications:Q", bin=alt.Bin(maxbins=30), title="Number of Medications"),
            y=alt.Y("count():Q", title="Count"),
        )
    )
    st.altair_chart(meds_chart, use_container_width=True)

    st.subheader("Readmission Rate by Age Group")
    age_readmit = (
        df.assign(readmitted_30=lambda d: d["readmitted"] == "<30")
        .groupby("age_group")["readmitted_30"]
        .mean()
        .reset_index()
    )
    age_readmit["readmitted_30"] *= 100
    age_chart = (
        alt.Chart(age_readmit)
        .mark_bar()
        .encode(
            x=alt.X("age_group:N", title="Age Group", sort=None),
            y=alt.Y("readmitted_30:Q", title="30-Day Readmission Rate (%)"),
        )
    )
    st.altair_chart(age_chart, use_container_width=True)
