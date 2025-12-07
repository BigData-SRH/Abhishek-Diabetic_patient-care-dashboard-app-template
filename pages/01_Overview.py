import streamlit as st
from core import (
    get_theme,
    apply_theme_css,
    get_filtered_data,
    compute_kpis,
    show_overview,
)

theme = get_theme(False)
apply_theme_css(theme)

df = get_filtered_data()
kpis = compute_kpis(df)

show_overview(theme, df, kpis)
