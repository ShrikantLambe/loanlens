"""
main.py — LoanLens Streamlit entry point.

Run: streamlit run app/main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="LoanLens | Portfolio Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Global CSS ---
st.markdown(
    """
    <style>
    /* Metric card lift */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricLabel"] { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .04em; }
    [data-testid="stMetricValue"] { font-size: 26px; font-weight: 700; color: #1e293b; }
    /* Sidebar branding */
    section[data-testid="stSidebar"] { background: #1e293b; }
    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stRadio label { font-size: 14px; padding: 6px 0; }
    section[data-testid="stSidebar"] hr { border-color: #334155; }
    /* Page title */
    h1 { font-weight: 800; letter-spacing: -.02em; }
    /* Divider */
    hr { border-color: #e2e8f0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- First-run DB init (Streamlit Community Cloud) ---
from app.init_db import ensure_initialized
ensure_initialized()

# --- Sidebar ---
with st.sidebar:
    st.markdown(
        "<h2 style='margin:0; font-size:22px; font-weight:800; letter-spacing:-.02em'>📊 LoanLens</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Portfolio Intelligence Stack")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠  Portfolio Overview",
            "📈  Cohort Analysis",
            "🏦  SPV Reporting",
            "🔍  Reconciliation Audit",
            "🤖  Investor Memo (AI)",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("10,000 loans · 180K events · 3 SPVs")

# --- Page routing ---
if "Portfolio Overview" in page:
    from app.pages.overview import render
    render()

elif "Cohort Analysis" in page:
    from app.pages.cohort_analysis import render
    render()

elif "SPV Reporting" in page:
    from app.pages.spv_reporting import render
    render()

elif "Reconciliation Audit" in page:
    from app.pages.reconciliation import render
    render()

elif "Investor Memo" in page:
    from app.pages.investor_memo import render
    render()
