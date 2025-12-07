import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from io import BytesIO
from datetime import datetime

# PDF export (for KPI report)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# ------------------------------
# DATA PATH & ADMISSION LABELS
# ------------------------------
DATA_PATH = Path("data/diabetic_data.csv")

# Mapping from admission_type_id to readable labels
ADMISSION_TYPE_LABELS = {
    1: "Emergency",
    2: "Urgent",
    3: "Elective",
    4: "Newborn",
    5: "Not Available",
    6: "Other",
    7: "Trauma Center / Other",
    8: "Not Mapped",
    9: "Unknown",
}


# ------------------------------
# DATA LOADING
# ------------------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Ensure num_medications is numeric
    if "num_medications" not in df.columns:
        raise ValueError("Expected 'num_medications' column not found in CSV.")
    df["num_medications"] = pd.to_numeric(df["num_medications"], errors="coerce")

    # Age groups are already bucketed in this dataset
    df["age_group"] = df["age"].astype(str)

    return df


df_raw = load_data(DATA_PATH)


# ------------------------------
# THEME (LIGHT ONLY) + CSS
# ------------------------------
def get_theme(dark_mode: bool = False) -> dict:
    """Return theme colors. We always use the light theme."""
    return {
        "APP_BG": "#f3f4f6",
        "TEXT_COLOR": "#111827",
        "CARD_GRADIENT": "linear-gradient(135deg, #ffffff 0%, #f3f4f6 100%)",
        "BORDER": "#e5e7eb",
        "SUBTXT": "#6b7280",
    }


def apply_theme_css(theme: dict) -> None:
    """Inject CSS for the light theme."""
    APP_BG = theme["APP_BG"]
    TEXT_COLOR = theme["TEXT_COLOR"]

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {APP_BG};
            color: {TEXT_COLOR};
            font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}
        .kpi-card {{
            transition: transform 0.2s ease-out, box-shadow 0.2s ease-out;
        }}
        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 30px rgba(15,23,42,0.15);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------
# FILTERS (USED BY ALL PAGES)
# ------------------------------
def get_filtered_data() -> pd.DataFrame:
    """Draw sidebar filters and return filtered dataframe."""
    st.sidebar.markdown("## Filters")

    # Reset filters
    if st.sidebar.button("Reset All Filters"):
        for key in list(st.session_state.keys()):
            if key.startswith(("age_", "gender_", "adm_", "all_")):
                st.session_state.pop(key)
        st.rerun()

    # --- Age Group filter ---
    with st.sidebar.expander("Age Group", expanded=False):
        age_groups = sorted(df_raw["age_group"].dropna().unique())
        all_age = st.checkbox("Select All", value=True, key="all_age")
        if all_age:
            age_selected = age_groups
        else:
            age_selected = [a for a in age_groups if st.checkbox(a, key=f"age_{a}")]

    # --- Gender filter ---
    with st.sidebar.expander("Gender", expanded=False):
        genders = sorted(df_raw["gender"].dropna().unique())
        all_gender = st.checkbox("Select All", value=True, key="all_gender")
        if all_gender:
            gender_selected = genders
        else:
            gender_selected = [
                g for g in genders if st.checkbox(g, key=f"gender_{g}")
            ]

    # --- Admission Type filter (with labels) ---
    with st.sidebar.expander("Admission Type", expanded=False):
        adm_types = sorted(df_raw["admission_type_id"].dropna().unique())
        all_adm = st.checkbox("Select All", value=True, key="all_adm")
        if all_adm:
            adm_selected = adm_types
        else:
            adm_selected = []
            for a in adm_types:
                label = ADMISSION_TYPE_LABELS.get(int(a), str(a))
                if st.checkbox(label, key=f"adm_{a}"):
                    adm_selected.append(a)

    # Apply filters
    df = df_raw[
        df_raw["age_group"].isin(age_selected)
        & df_raw["gender"].isin(gender_selected)
        & df_raw["admission_type_id"].isin(adm_selected)
    ].copy()

    return df


# ------------------------------
# KPI / METRIC HELPERS
# ------------------------------
def gauge_style(pct: float, color: str) -> str:
    """Create a CSS conic-gradient for KPI donut gauge."""
    pct = max(0, min(100, pct))
    deg = pct * 3.6
    return f"background: conic-gradient({color} {deg}deg, #e5e7eb 0deg);"


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute all main KPIs and return as a dict."""

    if len(df) > 0:
        readmission_rate = (df["readmitted"] == "<30").mean() * 100
    else:
        readmission_rate = 0.0
    readmission_rate = round(readmission_rate, 1)

    readmitted_df = df[df["readmitted"].isin(["<30", ">30"])]

    if len(readmitted_df) > 0:
        avg_los_readmitted = round(readmitted_df["time_in_hospital"].mean(), 1)
        polypharmacy_rate = (
            readmitted_df["num_medications"] >= 10
        ).mean() * 100
    else:
        avg_los_readmitted = 0.0
        polypharmacy_rate = 0.0

    polypharmacy_rate = round(polypharmacy_rate, 1)

    return {
        "readmission_rate": readmission_rate,
        "avg_los_readmitted": avg_los_readmitted,
        "polypharmacy_rate": polypharmacy_rate,
        "readmitted_df": readmitted_df,
    }


def build_kpi_excel(
    df: pd.DataFrame, readmitted_df: pd.DataFrame, kpis: dict
) -> BytesIO:
    """Create an Excel file with KPI summary."""
    data = {
        "Metric": [
            "30-Day Readmission Rate (<30 / all encounters)",
            "Average LOS (days, readmitted only)",
            "Polypharmacy (≥10 meds, readmitted only)",
            "Filtered Encounters",
            "Filtered Readmitted Encounters",
        ],
        "Value": [
            f"{kpis['readmission_rate']} %",
            kpis["avg_los_readmitted"],
            f"{kpis['polypharmacy_rate']} %",
            len(df),
            len(readmitted_df),
        ],
    }
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(data).to_excel(writer, index=False, sheet_name="KPI Summary")
    out.seek(0)
    return out


def build_pdf(
    df: pd.DataFrame, readmitted_df: pd.DataFrame, kpis: dict
) -> BytesIO | None:
    """Create a simple PDF KPI report (if reportlab is installed)."""
    if not REPORTLAB_AVAILABLE:
        return None

    readmission_rate = kpis["readmission_rate"]
    avg_los_readmitted = kpis["avg_los_readmitted"]
    polypharmacy_rate = kpis["polypharmacy_rate"]

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 40, "Diabetes Care Performance Report")
    c.setFont("Helvetica", 10)
    c.drawString(
        40,
        height - 60,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 90, "Key Performance Indicators")
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 110, f"30-Day Readmission Rate: {readmission_rate}%")
    c.drawString(
        60,
        height - 125,
        f"Average LOS (readmitted): {avg_los_readmitted} days",
    )
    c.drawString(
        60,
        height - 140,
        f"Polypharmacy (≥10 meds, readmitted): {polypharmacy_rate}%",
    )
    c.drawString(60, height - 160, f"Filtered Encounters: {len(df)}")
    c.drawString(60, height - 175, f"Filtered Readmitted Encounters: {len(readmitted_df)}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ------------------------------
# PAGE RENDERERS (from old app)
# ------------------------------
def show_overview(theme: dict, df: pd.DataFrame, kpis: dict) -> None:
    """Render the Overview page (UI copied from original single-file app)."""
    TEXT_COLOR = theme["TEXT_COLOR"]
    SUBTXT = theme["SUBTXT"]
    CARD_GRADIENT = theme["CARD_GRADIENT"]
    BORDER = theme["BORDER"]

    readmission_rate = kpis["readmission_rate"]
    avg_los_readmitted = kpis["avg_los_readmitted"]
    polypharmacy_rate = kpis["polypharmacy_rate"]
    readmitted_df = kpis["readmitted_df"]

    # KPI colors
    readmit_color = "#22c55e" if readmission_rate < 12 else "#ef4444"
    los_color = "#3b82f6" if avg_los_readmitted <= 5 else "#f97316"
    poly_color = "#22c55e" if polypharmacy_rate < 75 else "#ef4444"

    header_left, header_right = st.columns([3, 2])

    with header_left:
        st.markdown(
            f"""
            <h2 style='margin-bottom:-6px; color:{TEXT_COLOR};'>
                Diabetes Care Performance Dashboard
            </h2>
            <p style='color:{SUBTXT};'>Readmitted Patient Statistics</p>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔍 About This Dashboard"):
            st.session_state["show_about"] = not st.session_state.get("show_about", False)

    with header_right:
        st.download_button(
            "Download KPI Summary (Excel)",
            data=build_kpi_excel(df, readmitted_df, kpis),
            file_name="kpi_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if REPORTLAB_AVAILABLE:
            pdf_bytes = build_pdf(df, readmitted_df, kpis)
            st.download_button(
                "Download KPI Report (PDF)",
                data=pdf_bytes,
                file_name="kpi_report.pdf",
                mime="application/pdf",
            )
        else:
            st.info("Install `reportlab` to enable PDF export (pip install reportlab).")

    # About panel under header
    if st.session_state.get("show_about", False):
        st.markdown(
            f"""
            <div style='background:{CARD_GRADIENT}; padding:1rem 1.2rem; border-radius:12px;
                        border:1px solid {BORDER}; margin-top:0.8rem;'>
                <h3>About This Dashboard</h3>
                <p>
                This dashboard presents a targeted analysis of <b>readmitted diabetic inpatient encounters</b>
                using structured hospital data that includes demographics, admission characteristics,
                length of stay, medication counts, and readmission outcomes. By isolating readmitted cases,
                the dashboard provides clinically meaningful performance metrics:
                </p>
                <ul>
                    <li>30-day readmission rate</li>
                    <li>Average length of stay for readmitted patients</li>
                    <li>Polypharmacy rate (patients receiving 10 or more medications)</li>
                </ul>
                <p>
                Interactive filters enable stratified analysis across age groups, gender, and admission types.
                The tool is intended to help healthcare teams evaluate readmission patterns, identify
                high-burden patient groups, and design evidence-based interventions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # KPI CARDS
    k1, k2, k3 = st.columns(3)

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card" style='background:{CARD_GRADIENT}; padding:1.5rem;
                        border-radius:20px; border:1px solid {BORDER}; text-align:center;'>
                <div style='width:90px; height:90px; margin:auto; border-radius:50%;
                            {gauge_style(readmission_rate, readmit_color)}'>
                    <div style='width:70px; height:70px; margin:10px auto; border-radius:50%;
                                background:rgba(255,255,255,0.7);
                                display:flex; align-items:center; justify-content:center;
                                font-weight:700; font-size:1.4rem; color:{TEXT_COLOR};'>
                        {readmission_rate}<span style='font-size:0.75rem;'>%</span>
                    </div>
                </div>
                <h4 style='margin-top:10px;'>30-Day Readmission Rate</h4>
                <p style='color:{SUBTXT}; font-size:0.9rem;'>
                    Percentage of encounters readmitted within 30 days.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card" style='background:{CARD_GRADIENT}; padding:1.5rem;
                        border-radius:20px; border:1px solid {BORDER}; text-align:center;'>
                <div style='width:90px; height:90px; margin:auto; border-radius:50%;
                            {gauge_style(avg_los_readmitted * 7, los_color)}'>
                    <div style='width:70px; height:70px; margin:10px auto; border-radius:50%;
                                background:rgba(255,255,255,0.7);
                                display:flex; align-items:center; justify-content:center;
                                font-weight:700; font-size:1.4rem; color:{TEXT_COLOR};'>
                        {avg_los_readmitted}<span style='font-size:0.75rem;'> days</span>
                    </div>
                </div>
                <h4 style='margin-top:10px;'>Average Length of Stay (Readmitted)</h4>
                <p style='color:{SUBTXT}; font-size:0.9rem;'>
                    Average inpatient stay duration (days) for readmitted encounters.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card" style='background:{CARD_GRADIENT}; padding:1.5rem;
                        border-radius:20px; border:1px solid {BORDER}; text-align:center;'>
                <div style='width:90px; height:90px; margin:auto; border-radius:50%;
                            {gauge_style(polypharmacy_rate, poly_color)}'>
                    <div style='width:70px; height:70px; margin:10px auto; border-radius:50%;
                                background:rgba(255,255,255,0.7);
                                display:flex; align-items:center; justify-content:center;
                                font-weight:700; font-size:1.4rem; color:{TEXT_COLOR};'>
                        {polypharmacy_rate}<span style='font-size:0.75rem;'>%</span>
                    </div>
                </div>
                <h4 style='margin-top:10px;'>Polypharmacy (Readmitted)</h4>
                <p style='color:{SUBTXT}; font-size:0.9rem;'>
                    Percentage of readmitted patients (&#60;30 or &#62;30 days)
                    receiving 10+ medications.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Quick summary
    st.markdown("### Quick Summary")
    st.markdown(
        f"""
        - **Filtered encounters:** {len(df):,}  
        - **Filtered readmitted encounters (&#60;30 or &#62;30):** {len(readmitted_df):,}  
        - **30-day readmission rate:** {readmission_rate}%  
        - **Average LOS for readmitted patients:** {avg_los_readmitted} days  
        - **Polypharmacy among readmitted patients:** {polypharmacy_rate}%  
        """,
    )
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    # Charts
    st.markdown("## 📊 Metrics Visualizations")
    tab1, tab2, tab3 = st.tabs(
        ["📉 Readmission", "🏥 LOS", "💊 Polypharmacy (Readmitted)"]
    )

    with tab1:
        if len(df) > 0:
            dist = (
                df["readmitted"]
                .replace({"NO": "No Readmission", "<30": "<30 Days", ">30": ">30 Days"})
                .value_counts(normalize=True)
                .mul(100)
                .reset_index()
            )
            dist.columns = ["Category", "Percent"]
            chart = (
                alt.Chart(dist)
                .mark_bar(color="#ef4444")
                .encode(
                    x=alt.X("Category:N", title=None),
                    y=alt.Y("Percent:Q", title="Percentage (%)"),
                    tooltip=["Category", alt.Tooltip("Percent:Q", format=".1f")],
                )
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data available for current filters.")

    with tab2:
        if len(df) > 0:
            los_bins = pd.cut(
                df["time_in_hospital"],
                bins=[0, 2, 4, 6, 8, 10, 20],
                labels=["1–2", "3–4", "5–6", "7–8", "9–10", "10+"],
            )
            los_dist = los_bins.value_counts().sort_index().reset_index()
            los_dist.columns = ["LOS", "Count"]
            chart2 = (
                alt.Chart(los_dist)
                .mark_bar(color="#3b82f6")
                .encode(
                    x=alt.X("LOS:N", title="LOS (days)"),
                    y=alt.Y("Count:Q", title="Count"),
                    tooltip=["LOS", "Count"],
                )
            )
            st.altair_chart(chart2, use_container_width=True)
        else:
            st.info("No data available for current filters.")

    with tab3:
        if len(readmitted_df) > 0:
            poly_bins = pd.cut(
                readmitted_df["num_medications"],
                bins=[0, 5, 10, 15, 20, 30, 50],
                labels=["0–4", "5–9", "10–14", "15–19", "20–29", "30+"],
            )
            poly_dist = poly_bins.value_counts().sort_index().reset_index()
            poly_dist.columns = ["Med Bin", "Count"]
            chart3 = (
                alt.Chart(poly_dist)
                .mark_bar(color="#22c55e")
                .encode(
                    x=alt.X("Med Bin:N", title="Number of Medications (Readmitted)"),
                    y=alt.Y("Count:Q", title="Count"),
                    tooltip=["Med Bin", "Count"],
                )
            )
            st.altair_chart(chart3, use_container_width=True)
        else:
            st.info("No readmitted patients in current filters.")

    # Odds ratio section
    with st.expander("Polypharmacy & 30-Day Readmission (Odds Ratio)", expanded=False):
        if len(df) > 0:
            temp = df.copy()
            temp["polypharmacy"] = temp["num_medications"] >= 10
            temp["readmitted_30_flag"] = temp["readmitted"] == "<30"

            a = ((temp["polypharmacy"]) & (temp["readmitted_30_flag"])).sum()
            b = ((temp["polypharmacy"]) & (~temp["readmitted_30_flag"])).sum()
            c = ((~temp["polypharmacy"]) & (temp["readmitted_30_flag"])).sum()
            d = ((~temp["polypharmacy"]) & (~temp["readmitted_30_flag"])).sum()

            def adj(x: int) -> float:
                return x if x > 0 else 0.5

            a_adj, b_adj, c_adj, d_adj = map(adj, [a, b, c, d])
            odds_ratio = (a_adj * d_adj) / (b_adj * c_adj)
            or_rounded = round(odds_ratio, 2)

            st.subheader("Odds of 30-Day Readmission (Polypharmacy vs Non-Polypharmacy)")
            st.metric("Odds Ratio", f"{or_rounded}×")
            st.caption(
                "An odds ratio > 1 indicates higher odds of 30-day readmission among "
                "patients receiving 10+ medications compared with those on fewer than 10."
            )

            cont_df = pd.DataFrame(
                {
                    "Polypharmacy (≥10 meds)": [a, b],
                    "No Polypharmacy (<10 meds)": [c, d],
                },
                index=["Readmitted <30 days", "Not readmitted <30 days"],
            )
            st.table(cont_df)
        else:
            st.info("Not enough data for odds ratio calculation under current filters.")

    # Download filtered data
    st.download_button(
        "Download Filtered Dataset (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        "filtered_data_overview.csv",
        "text/csv",
    )

    # Dynamic insights
    st.markdown("## 🔎 Key Insights & Recommendations")

    if readmission_rate >= 12:
        readmit_level = "elevated"
    elif readmission_rate >= 8:
        readmit_level = "moderate"
    else:
        readmit_level = "relatively low"

    if avg_los_readmitted > 5:
        los_level = "high"
    elif avg_los_readmitted >= 3.5:
        los_level = "moderate"
    else:
        los_level = "short"

    if polypharmacy_rate >= 80:
        poly_level = "very high"
    elif polypharmacy_rate >= 60:
        poly_level = "elevated"
    else:
        poly_level = "moderate"

    in1, in2, in3 = st.tabs(
        ["30-Day Readmission", "LOS (Readmitted)", "Polypharmacy (Readmitted)"]
    )

    with in1:
        st.markdown(
            f"""
            **Current Performance**  
            The 30-day readmission rate is **{readmission_rate}%**, which is **{readmit_level}** for the
            current filtered population.

            **Implications**  
            This level of readmission suggests that there may be opportunities to strengthen discharge
            planning and post-discharge support.

            **Recommendations**  
            • Standardize discharge summaries and patient education.  
            • Implement follow-up calls or appointments for high-risk patients.  
            • Use risk scoring to proactively identify patients likely to be readmitted.  
            """,
            unsafe_allow_html=True,
        )

    with in2:
        st.markdown(
            f"""
            **Current Performance**  
            Among readmitted patients, the average length of stay is **{avg_los_readmitted} days**, which
            can be considered **{los_level}** given the complexity of this population.

            **Implications**  
            LOS patterns may reflect both clinical complexity and process inefficiencies in care delivery.

            **Recommendations**  
            • Review care pathways for common diagnoses driving readmissions.  
            • Initiate discharge planning early during the inpatient stay.  
            • Coordinate with post-acute care providers to ensure smooth transitions.  
            """,
            unsafe_allow_html=True,
        )

    with in3:
        st.markdown(
            f"""
            **Current Performance**  
            Among readmitted patients, **{polypharmacy_rate}%** receive 10 or more medications, which is
            **{poly_level}** and indicates a substantial medication burden.

            **Implications**  
            High medication burden is associated with adverse drug events, poor adherence, and increased
            readmission risk.

            **Recommendations**  
            • Implement pharmacist-led medication reconciliation for readmitted patients.  
            • Develop deprescribing protocols targeting low-value or duplicate therapies.  
            • Educate patients on medication use, side effects, and interactions.  
            """,
            unsafe_allow_html=True,
        )

    # Executive summary
    st.markdown("## 🧩 Executive Summary")
    st.markdown(
        f"""
        - The dashboard highlights a **{readmission_rate}% 30-day readmission rate**, indicating that a
          non-trivial share of diabetic encounters return shortly after discharge.  
        - Readmitted patients stay for an average of **{avg_los_readmitted} days**, reflecting 
          {los_level} LOS for this high-risk group.  
        - Polypharmacy is a major concern, with **{polypharmacy_rate}%** of readmitted patients receiving
          10 or more medications. The odds of 30-day readmission are higher in the polypharmacy group
          than in patients on fewer medications.  
        """
    )


def show_data_explorer(df: pd.DataFrame, kpis: dict) -> None:
    readmitted_df = kpis["readmitted_df"]

    st.title("Data Explorer")

    search = st.text_input("Global search", placeholder="Search across all columns...")
    df_view = df.copy()
    if search:
        mask = df_view.apply(
            lambda col: col.astype(str).str.contains(search, case=False, na=False)
        )
        df_view = df_view[mask.any(axis=1)]

    st.write(f"Showing **{len(df_view)}** rows after filters and search.")
    st.download_button(
        "Download Filtered CSV",
        df_view.to_csv(index=False).encode("utf-8"),
        "filtered_data.csv",
        "text/csv",
    )

    st.dataframe(df_view, use_container_width=True)

    st.markdown("### Readmitted Patient Profile Explorer")
    if len(readmitted_df) > 0:
        sample_cols = [
            "encounter_id",
            "patient_nbr",
            "age_group",
            "gender",
            "admission_type_id",
            "time_in_hospital",
            "num_medications",
            "readmitted",
        ]
        profile_df = readmitted_df[sample_cols].copy()
        patient_ids = profile_df["patient_nbr"].astype(str).unique()
        selected_patient = st.selectbox(
            "Select a patient number (readmitted only):",
            patient_ids,
        )
        selected_rows = profile_df[
            profile_df["patient_nbr"].astype(str) == selected_patient
        ]
        st.write("Selected patient encounters:")
        st.dataframe(selected_rows, use_container_width=True)
    else:
        st.info(
            "No readmitted patients in the current filter selection for profile exploration."
        )


def show_about_page() -> None:
    st.title("About This Dashboard")

    st.markdown(
        """
    ### Overview  
    This dashboard provides an interactive analysis of **readmitted diabetic inpatient encounters**, 
    focusing on three core performance indicators essential for evaluating care quality:

    - **30-Day Readmission Rate**  
    - **Average Length of Stay (LOS) among readmitted patients**  
    - **Polypharmacy prevalence (10+ medications)**  

    The dashboard enables users to explore how readmission patterns vary across demographics such as  
    **age group**, **gender**, and **admission type**, while also providing actionable insights 
    and data-driven interpretations.

    ---

    ### Dataset Information  
    This dashboard uses the publicly available **Diabetes 130-US Hospitals for Years 1999–2008** dataset,  
    which contains more than **100,000 inpatient encounters** collected from **130 U.S. hospitals**.  
    The dataset includes:

    - Demographics  
    - Diagnoses  
    - Procedures  
    - Medication counts  
    - Encounter details  
    - Readmission outcomes  

    **Dataset link:**  
    👉 https://archive.ics.uci.edu/dataset/296/diabetes+130+us+hospitals+for+years+1999+2008  

    ---

    ### APA 7th Edition Dataset Citation  

    UCI Machine Learning Repository. (2014). *Diabetes 130-US hospitals for years 1999–2008* [Data set].  
    University of California, Irvine. https://archive.ics.uci.edu/dataset/296/diabetes+130+us+hospitals+for+years+1999+2008  

    ---

    ### Purpose  
    This dashboard is intended to support:

    - Quality improvement initiatives  
    - Clinical decision-making  
    - Care coordination  
    - Resource planning for diabetic readmissions  

    The insights aim to help healthcare teams identify high-risk patterns, optimize discharge planning, 
    and improve patient outcomes.
    """
    )
