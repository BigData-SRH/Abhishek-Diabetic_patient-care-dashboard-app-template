import streamlit as st

# This MUST be the first Streamlit command in the whole app
st.set_page_config(
    page_title="Diabetes Care Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Diabetes Care Performance Dashboard")
st.write(
    "Use the navigation in the left sidebar to open **Overview**, "
    "**Data Explorer**, **EDA**, and **About** pages."
)
