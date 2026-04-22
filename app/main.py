"""
main.py — LoanLens Streamlit entry point.

Run: streamlit run app/main.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path so imports work from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="LoanLens | Portfolio Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
st.sidebar.title("LoanLens")
st.sidebar.caption("Portfolio Intelligence Stack")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    [
        "Portfolio Overview",
        "Cohort Analysis",
        "SPV Reporting",
        "Reconciliation Audit",
        "Investor Memo (AI)",
    ],
)

st.sidebar.divider()
st.sidebar.caption("10,000 loans · 180K payment events · 3 SPVs")

# --- Page routing ---
if page == "Portfolio Overview":
    from app.pages.overview import render
    render()

elif page == "Cohort Analysis":
    from app.pages.cohort_analysis import render
    render()

elif page == "SPV Reporting":
    from app.pages.spv_reporting import render
    render()

elif page == "Reconciliation Audit":
    from app.pages.reconciliation import render
    render()

elif page == "Investor Memo (AI)":
    from app.pages.investor_memo import render
    render()
