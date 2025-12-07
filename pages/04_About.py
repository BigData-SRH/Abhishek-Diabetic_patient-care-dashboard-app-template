import streamlit as st

# ----------------------------
# ABOUT PAGE
# ----------------------------

st.title("About This Dashboard")

st.write(
    """
This dashboard analyzes diabetic inpatient encounters, focusing specifically on  
**30-day readmissions**, **length of stay**, and **polypharmacy patterns** among patients.  
It provides an interactive environment to explore trends across demographics and  
clinical attributes using filters, KPI cards, and exploratory data analysis.

The aim is to support better understanding of readmission risks and medication burden  
within hospital settings.
"""
)

st.divider()

st.header("Project Information")

st.markdown(
    """
**Course:** Big Data and Business Intelligence  
**Cohort:** M.Tech Computer Science: Big Data and AI  
**University:** SRH University, Leipzig  
"""
)

st.divider()

st.header("Author")

st.markdown(
    """
**Name:** Abhishek Negi  
**Matriculation No.:** 100004670  
**Email:** abhishek.negi53@gmail.com  
"""
)

st.divider()

st.header("Dataset Source")

st.caption(
    "Dashboard data source: University of California Irvine (UCI) Machine Learning Repository — Diabetes 130-US Hospitals Dataset (Strack et al.)"
)

st.markdown(
    """
**APA Citation:**  
Strack, B., DeShazo, J. P., Gennings, C., Olmo, J. L., Ventura, S., Cios, K. J., & Clore, J. N. (2014).  
*Impact of HbA1c measurement on hospital readmission rates: Analysis of 70,000 clinical database patient records.*  
Journal of Clinical Medicine, 3(1), 1–12. https://doi.org/10.3390/jcm3010001
"""
)

st.success("Thank you for viewing this dashboard!")
