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

# ── Global design system ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── 1. Typography: Inter from Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"], .stMarkdown, .stText, button, input, select, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* ── 2. Strip Streamlit chrome ── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }
    .stDeployButton         { display: none !important; }
    [data-testid="stToolbar"]{ display: none !important; }

    /* ── 3. Page background: very faint blue-gray ── */
    .main { background: #f8fafc !important; }
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1320px !important;
    }

    /* ── 4. Metric cards ── */
    [data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px 22px 18px !important;
        box-shadow:
            0 0 0 1px rgba(15,23,42,.06),
            0 2px 8px rgba(15,23,42,.04);
        position: relative;
        overflow: hidden;
        transition: box-shadow .2s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow:
            0 0 0 1px rgba(37,99,235,.15),
            0 4px 16px rgba(15,23,42,.08);
    }
    /* gradient accent stripe */
    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
    }
    [data-testid="stMetricLabel"] > div {
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        text-transform: uppercase !important;
        letter-spacing: .07em !important;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        letter-spacing: -.025em !important;
        font-variant-numeric: tabular-nums !important;
        line-height: 1.1 !important;
        margin-top: 6px !important;
    }
    [data-testid="stMetricDelta"] > div {
        font-size: 12px !important;
        font-weight: 500 !important;
        margin-top: 4px !important;
    }

    /* ── 5. Typography scale ── */
    h1 {
        font-weight: 800 !important;
        font-size: 26px !important;
        color: #0f172a !important;
        letter-spacing: -.03em !important;
        line-height: 1.2 !important;
        margin-bottom: 2px !important;
    }
    h2 {
        font-weight: 700 !important;
        font-size: 16px !important;
        color: #1e293b !important;
        letter-spacing: -.02em !important;
    }
    h3 {
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #334155 !important;
    }
    p { font-size: 14px !important; line-height: 1.65 !important; color: #374151 !important; }

    /* ── 6. Caption ── */
    [data-testid="stCaptionContainer"] p {
        font-size: 13px !important;
        color: #94a3b8 !important;
        line-height: 1.5 !important;
    }

    /* ── 7. Divider ── */
    hr {
        border: none !important;
        border-top: 1px solid #f1f5f9 !important;
        margin: 1.75rem 0 !important;
    }

    /* ── 8. Sidebar: deep navy ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1527 0%, #111827 100%) !important;
        border-right: 1px solid rgba(255,255,255,.05) !important;
    }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] hr {
        border-top: 1px solid rgba(255,255,255,.07) !important;
        margin: .75rem 0 !important;
    }

    /* Nav buttons in sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        color: #64748b !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        padding: 9px 14px !important;
        border-radius: 8px !important;
        height: auto !important;
        min-height: 0 !important;
        line-height: 1.4 !important;
        box-shadow: none !important;
        width: 100% !important;
        letter-spacing: .01em !important;
        transition: background .15s ease, color .15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,.07) !important;
        color: #e2e8f0 !important;
        transform: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    /* Active nav item: set via .nav-active class on parent div */
    .nav-active .stButton > button {
        background: rgba(37,99,235,.18) !important;
        color: #93c5fd !important;
        font-weight: 600 !important;
        border-left: 3px solid #3b82f6 !important;
        padding-left: 11px !important;
    }

    /* ── 9. Primary button (outside sidebar) ── */
    .main .stButton > button[kind="primary"],
    .main .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: .01em !important;
        color: #fff !important;
        box-shadow: 0 1px 3px rgba(37,99,235,.35) !important;
        transition: all .15s ease !important;
        height: 38px !important;
    }
    .main .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,.4) !important;
        transform: translateY(-1px) !important;
    }
    .main .stButton > button:not([kind="primary"]):not([disabled]) {
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        transition: all .15s ease !important;
        height: 38px !important;
    }

    /* ── 10. Alert / status boxes ── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 12px 16px !important;
    }

    /* ── 11. Plotly chart container ── */
    [data-testid="stPlotlyChart"] {
        background: #ffffff;
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 0 0 1px rgba(15,23,42,.06), 0 2px 8px rgba(15,23,42,.03) !important;
    }

    /* ── 12. DataFrame ── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 0 0 1px rgba(15,23,42,.06) !important;
    }
    [data-testid="stDataFrame"] table {
        font-size: 13px !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* ── 13. Expander ── */
    [data-testid="stExpander"] {
        background: #fff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        font-size: 13.5px !important;
        color: #374151 !important;
        padding: 14px 16px !important;
    }

    /* ── 14. Multiselect ── */
    [data-testid="stMultiSelect"] > div > div {
        border-radius: 8px !important;
        font-size: 13px !important;
    }

    /* ── 15. Spinner ── */
    [data-testid="stSpinner"] { color: #2563eb !important; }

    /* ── 16. Info box ── */
    .stInfo {
        background: #eff6ff !important;
        border-left: 4px solid #3b82f6 !important;
        border-radius: 8px !important;
    }

    /* ── 17. Progress bar ── */
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #2563eb, #7c3aed) !important;
        border-radius: 4px !important;
    }

    /* ── 18. Subheader left-accent ── */
    [data-testid="stHeadingWithActionElements"] h2 {
        padding-left: 10px !important;
        border-left: 3px solid #2563eb !important;
        margin-top: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── First-run DB init ─────────────────────────────────────────────────────────
from app.init_db import ensure_initialized
ensure_initialized()

# ── Page registry ─────────────────────────────────────────────────────────────
_PAGES = [
    ("overview", "🏠", "Portfolio Overview"),
    ("cohort",   "📈", "Cohort Analysis"),
    ("spv",      "🏦", "SPV Reporting"),
    ("recon",    "🔍", "Reconciliation Audit"),
    ("memo",     "🤖", "Investor Memo (AI)"),
]

if "page" not in st.session_state:
    st.session_state["page"] = "overview"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown(
        """
        <div style="padding: 8px 4px 20px;">
            <div style="font-size:22px; font-weight:800; color:#f1f5f9;
                        letter-spacing:-.03em; line-height:1;">
                📊 LoanLens
            </div>
            <div style="font-size:11px; color:#475569; font-weight:500;
                        letter-spacing:.06em; text-transform:uppercase;
                        margin-top:5px;">
                Portfolio Intelligence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Navigation — buttons styled as nav items via CSS; active item gets .nav-active wrapper
    current = st.session_state["page"]
    for key, icon, label in _PAGES:
        is_active = current == key
        # Wrap active button in a div with the .nav-active class
        if is_active:
            st.markdown("<div class='nav-active'>", unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state["page"] = key
            st.rerun()
        if is_active:
            st.markdown("</div>", unsafe_allow_html=True)

    # Footer
    st.markdown(
        """
        <div style="position:fixed; bottom:0; left:0; width:256px;
                    padding:16px 20px; border-top:1px solid rgba(255,255,255,.06);
                    background: linear-gradient(180deg, transparent, rgba(12,21,39,.95));">
            <div style="font-size:11px; color:#334155; font-weight:500; line-height:1.8;">
                10,000 loans · 180K events<br/>
                3 SPVs · dbt + DuckDB + Claude<br/>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Route ─────────────────────────────────────────────────────────────────────
page = st.session_state["page"]

if page == "overview":
    from app.views.overview import render
    render()
elif page == "cohort":
    from app.views.cohort_analysis import render
    render()
elif page == "spv":
    from app.views.spv_reporting import render
    render()
elif page == "recon":
    from app.views.reconciliation import render
    render()
elif page == "memo":
    from app.views.investor_memo import render
    render()
