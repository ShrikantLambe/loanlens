from __future__ import annotations

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

# ── Open Graph / social metadata ─────────────────────────────────────────────
st.markdown(
    """
    <meta property="og:title"       content="LoanLens — AI-powered loan portfolio intelligence"/>
    <meta property="og:description" content="Streamlit + dbt + DuckDB + Claude. 10K loans, 1.3M servicing events, 3 SPVs. Covenant monitoring, vintage cohort analysis, AI-generated investor memos."/>
    <meta property="og:image"       content="https://raw.githubusercontent.com/ShrikantLambe/loanlens/main/assets/og-image.png"/>
    <meta property="og:url"         content="https://loanlens-agentic.streamlit.app"/>
    <meta property="og:type"        content="website"/>
    <meta name="twitter:card"       content="summary_large_image"/>
    <meta name="twitter:title"      content="LoanLens — AI-powered loan portfolio intelligence"/>
    <meta name="twitter:description"content="Streamlit + dbt + DuckDB + Claude. 10K loans, 1.3M servicing events, 3 SPVs. Covenant monitoring, vintage cohort analysis, AI-generated investor memos."/>
    """,
    unsafe_allow_html=True,
)

# ── Global design system ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── 1. Fonts: Inter (UI) + JetBrains Mono (numbers) ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stMarkdown, .stText, button, input, select, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* ── 2. Strip Streamlit chrome ── */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }
    .stDeployButton          { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* ── 3. Canvas ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background: #f0f4f8 !important;
    }
    .main, section[data-testid="stMain"] {
        background: #f0f4f8 !important;
    }
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 0.75rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1380px !important;
    }

    /* ── 4. Metric cards — left-accent (Bloomberg/Stripe pattern) ── */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border-radius: 16px !important;
        padding: 20px 22px 18px !important;
        border: 1px solid #e4e9f0 !important;
        border-left: 4px solid #2563eb !important;
        box-shadow: 0 1px 4px rgba(15,23,42,.05) !important;
        position: relative !important;
        transition: box-shadow .18s ease, transform .18s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 6px 20px rgba(37,99,235,.10), 0 1px 4px rgba(15,23,42,.06) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stMetric"]::before { display: none !important; }
    div[data-testid="stMetricLabel"] > div,
    div[data-testid="stMetricLabel"] label {
        font-size: 10.5px !important;
        font-weight: 700 !important;
        color: #8898aa !important;
        text-transform: uppercase !important;
        letter-spacing: .09em !important;
    }
    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricValue"] p {
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 28px !important;
        font-weight: 600 !important;
        color: #0a0f1e !important;
        letter-spacing: -.03em !important;
        font-variant-numeric: tabular-nums !important;
        line-height: 1.15 !important;
        margin-top: 8px !important;
    }
    div[data-testid="stMetricDelta"] > div,
    div[data-testid="stMetricDelta"] p {
        font-size: 12px !important;
        font-weight: 600 !important;
        margin-top: 6px !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* ── 5. Typography scale ── */
    h1 {
        font-weight: 800 !important;
        font-size: 28px !important;
        color: #060d1f !important;
        letter-spacing: -.04em !important;
        line-height: 1.15 !important;
    }
    h2 {
        font-weight: 700 !important;
        font-size: 15px !important;
        color: #1e293b !important;
        letter-spacing: -.02em !important;
    }
    h3 {
        font-weight: 600 !important;
        font-size: 13.5px !important;
        color: #334155 !important;
    }
    p { font-size: 14px !important; line-height: 1.7 !important; color: #3d4f63 !important; }

    /* ── 6. Caption ── */
    [data-testid="stCaptionContainer"] p {
        font-size: 12.5px !important;
        color: #94a3b8 !important;
        line-height: 1.55 !important;
    }

    /* ── 7. Divider ── */
    hr {
        border: none !important;
        border-top: 1px solid #e8edf3 !important;
        margin: 2rem 0 !important;
    }

    /* ── 8. Sidebar ── */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"] {
        background: linear-gradient(175deg, #060d1f 0%, #0d1a30 60%, #0a1628 100%) !important;
        border-right: 1px solid rgba(99,130,200,.1) !important;
    }
    section[data-testid="stSidebar"] * { color: #7a8fa8 !important; }
    section[data-testid="stSidebar"] hr {
        border-top: 1px solid rgba(255,255,255,.06) !important;
        margin: .6rem 0 !important;
    }
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 1px !important;
        margin-top: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 1px !important;
    }

    /* Sidebar nav buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        align-items: center !important;
        color: #556070 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 9px 14px !important;
        border-radius: 10px !important;
        height: 38px !important;
        line-height: 38px !important;
        box-shadow: none !important;
        width: 100% !important;
        letter-spacing: .005em !important;
        transition: background .14s ease, color .14s ease !important;
        display: flex !important;
        vertical-align: middle !important;
    }
    /* Zero Streamlit's inner wrapper so only button padding governs position */
    section[data-testid="stSidebar"] .stButton > button > p,
    section[data-testid="stSidebar"] .stButton > button > div,
    section[data-testid="stSidebar"] .stButton > button > span {
        padding: 0 !important;
        margin: 0 !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(99,130,200,.1) !important;
        color: #c8d8f0 !important;
        transform: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] .stButton > button:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    /* ── 9. Main-area buttons ── */
    .main .stButton > button[kind="primary"],
    .main .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: .02em !important;
        color: #fff !important;
        box-shadow: 0 2px 8px rgba(37,99,235,.3), 0 1px 2px rgba(37,99,235,.2) !important;
        transition: all .16s ease !important;
        height: 40px !important;
    }
    .main .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #4338ca 100%) !important;
        box-shadow: 0 6px 20px rgba(37,99,235,.38) !important;
        transform: translateY(-1px) !important;
    }
    .main .stButton > button:not([kind="primary"]):not([disabled]) {
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        transition: all .14s ease !important;
        height: 40px !important;
        border: 1px solid #d1d9e6 !important;
    }

    /* ── 10. Alerts ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        padding: 14px 18px !important;
        border: none !important;
    }
    [data-testid="stAlert"][kind="success"],
    [data-testid="stAlert"][data-baseweb="notification"][kind="positive"] {
        background: #f0fdf4 !important;
        border-left: 4px solid #10b981 !important;
    }
    [data-testid="stAlert"][kind="error"] {
        background: #fff1f2 !important;
        border-left: 4px solid #ef4444 !important;
    }
    [data-testid="stAlert"][kind="warning"] {
        background: #fffbeb !important;
        border-left: 4px solid #f59e0b !important;
    }
    [data-testid="stAlert"][kind="info"] {
        background: #eff6ff !important;
        border-left: 4px solid #3b82f6 !important;
    }

    /* ── 11. Plotly chart container ── */
    [data-testid="stPlotlyChart"],
    div[data-testid="stPlotlyChart"] > div {
        background: #ffffff !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid #e4e9f0 !important;
        box-shadow: 0 1px 4px rgba(15,23,42,.04) !important;
    }

    /* ── 12. DataFrame ── */
    [data-testid="stDataFrame"] {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid #e4e9f0 !important;
        box-shadow: 0 1px 4px rgba(15,23,42,.04) !important;
    }
    [data-testid="stDataFrame"] table {
        font-size: 13px !important;
        font-variant-numeric: tabular-nums !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── 13. Expander ── */
    [data-testid="stExpander"] {
        background: #fff !important;
        border: 1px solid #e4e9f0 !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 3px rgba(15,23,42,.03) !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        font-size: 13.5px !important;
        color: #1e293b !important;
        padding: 14px 18px !important;
    }

    /* ── 14. Form inputs ── */
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stSelectbox"] > div > div {
        border-radius: 10px !important;
        font-size: 13px !important;
        border-color: #d1d9e6 !important;
    }

    /* ── 15. Spinner ── */
    [data-testid="stSpinner"] { color: #2563eb !important; }

    /* ── 16. Progress bar ── */
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #2563eb, #6366f1) !important;
        border-radius: 6px !important;
    }

    /* ── 17. Subheader accent (Streamlit native h2) ── */
    [data-testid="stHeadingWithActionElements"] h2 {
        padding-left: 12px !important;
        border-left: 4px solid #2563eb !important;
        margin-top: 0 !important;
    }

    /* ── 18. Tab bar ── */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid #e4e9f0 !important;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #2563eb !important;
        border-bottom: 2px solid #2563eb !important;
        font-weight: 600 !important;
    }

    /* ── 19. KPI card + sparkline unification ──────────────────────────────────
       Streamlit column data-testid is "stColumn", NOT "column".
       Using the wrong selector was why min-height had no effect.             */

    [data-testid="stColumn"] [data-testid="stMetric"],
    [data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
        border-left: 1px solid #e4e9f0 !important;
        border-radius: 14px 14px 0 0 !important;
        border-bottom: 0 !important;
        padding-bottom: 6px !important;
        margin-bottom: 0 !important;
        /* Equal height: tallest card (with delta) is ~120px; 130px floors all cards */
        min-height: 130px !important;
    }
    [data-testid="stColumn"] .element-container:has([data-testid="stMetric"]),
    [data-testid="stHorizontalBlock"] .element-container:has([data-testid="stMetric"]) {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    [data-testid="stColumn"] .element-container:has([data-testid="stMetric"]) + .element-container,
    [data-testid="stHorizontalBlock"] .element-container:has([data-testid="stMetric"]) + .element-container {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    [data-testid="stColumn"] .element-container:has([data-testid="stMetric"]) + .element-container iframe,
    [data-testid="stHorizontalBlock"] .element-container:has([data-testid="stMetric"]) + .element-container iframe {
        border: 1px solid #e4e9f0 !important;
        border-top: 0 !important;
        border-radius: 0 0 14px 14px !important;
        background: #ffffff !important;
        display: block !important;
    }

    /* ── 20. ECharts component container ── */
    [data-testid="stCustomComponentV1"] { border-radius: 16px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── First-run DB init ─────────────────────────────────────────────────────────
from app.init_db import ensure_initialized
ensure_initialized()

# ── Page registry — ordered by analyst workflow ───────────────────────────────
# 1. Overview (where am I?) → 2. SPV (am I at risk of losing facility access?)
# → 3. Cohort (is underwriting holding up?) → 4. Recon (do I trust the data?)
# → 5. Memo (export the story)
_PAGES = [
    ("overview", "🏠", "Portfolio Overview",      False),
    ("spv",      "🏦", "SPV Reporting",           False),
    ("cohort",   "📈", "Cohort Analysis",         False),
    ("recon",    "🔍", "Reconciliation Audit",    False),
    ("memo",     "🤖", "Investor Memo",           True),   # True = show AI badge
    ("arch",     "⚙",  "Architecture",            False),
]

if "page" not in st.session_state:
    st.session_state["page"] = "overview"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Brand ─────────────────────────────────────────────────────────────────
    st.html(
        "<div style='padding:20px 12px 18px;font-family:Inter,sans-serif;'>"
        # Glow disc behind icon
        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
        "<div style='width:36px;height:36px;border-radius:10px;"
        "background:linear-gradient(135deg,#2563eb,#6366f1);"
        "display:flex;align-items:center;justify-content:center;"
        "font-size:18px;box-shadow:0 0 16px rgba(99,102,241,.4);'>📊</div>"
        "<div>"
        "<div style='font-size:18px;font-weight:800;"
        "background:linear-gradient(90deg,#93c5fd,#c4b5fd);-webkit-background-clip:text;"
        "-webkit-text-fill-color:transparent;background-clip:text;"
        "letter-spacing:-.04em;line-height:1;'>LoanLens</div>"
        "<div style='font-size:9.5px;color:#334466;font-weight:600;"
        "letter-spacing:.12em;text-transform:uppercase;margin-top:2px;'>"
        "Portfolio Intelligence</div>"
        "</div>"
        "</div>"
        "</div>"
    )
    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    current = st.session_state["page"]
    for key, icon, label, is_ai in _PAGES:
        ai_badge = (
            "<span style='background:linear-gradient(135deg,#7c3aed,#6366f1);"
            "color:#fff;font-size:8.5px;font-weight:700;"
            "padding:2px 6px;border-radius:6px;letter-spacing:.06em;"
            "margin-left:6px;vertical-align:middle;'>AI</span>"
            if is_ai else ""
        )
        display_label = f"{icon}&nbsp;&nbsp;{label}{ai_badge}"

        if current == key:
            # Active pill — padding:9px 12px 9px 14px matches inactive button padding
            # No dot prefix so text aligns with inactive items
            st.html(
                f"<div style='"
                f"background:linear-gradient(135deg,rgba(37,99,235,.22),rgba(99,102,241,.14));"
                f"border:1px solid rgba(99,130,245,.28);"
                f"padding:0 14px;height:38px;border-radius:10px;color:#93c5fd;"
                f"font-size:13px;font-weight:600;margin:1px 0;cursor:default;"
                f"letter-spacing:.005em;font-family:Inter,sans-serif;"
                f"box-shadow:0 2px 10px rgba(37,99,235,.12);"
                f"display:flex;align-items:center;'>"
                f"{display_label}</div>"
            )
        else:
            #   = non-breaking space (same as &nbsp; in active pill HTML)
            # Two regular spaces collapse to one in HTML rendering, causing misalignment
            btn_label = f"{icon}  {label}{'  ✦' if is_ai else ''}"
            if st.button(btn_label, key=f"nav_{key}", use_container_width=True):
                st.session_state["page"] = key
                st.rerun()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.html(
        "<div style='font-family:Inter,sans-serif;padding:2px 4px 48px;'>"
        "<div style='font-size:9px;color:#253045;font-weight:700;"
        "text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px;'>"
        "Resources</div>"
        "<div style='display:flex;flex-direction:column;gap:6px;'>"
        "<a href='https://github.com/ShrikantLambe/loanlens' target='_blank' "
        "style='display:flex;align-items:center;gap:8px;font-size:12px;"
        "color:#4a6080;text-decoration:none;padding:6px 8px;border-radius:8px;"
        "transition:background .14s;'>"
        "<span style='font-size:13px;'>⌥</span> GitHub — Source Code</a>"
        "<a href='https://shrikantlambe.github.io' target='_blank' "
        "style='display:flex;align-items:center;gap:8px;font-size:12px;"
        "color:#4a6080;text-decoration:none;padding:6px 8px;border-radius:8px;'>"
        "<span style='font-size:13px;'>◈</span> Portfolio — Shrikant Lambe</a>"
        "</div>"
        "</div>"
    )

# ── Persistent health strip ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _load_health_data():
    """Load the minimal data needed for the global health strip."""
    from app.utils import snowflake_conn as db
    try:
        spv     = db.table("fct_spv_allocation")
        summary = db.table("rpt_portfolio_summary")
        recon   = db.table("rpt_reconciliation")
        return spv, summary, recon
    except Exception:
        return None, None, None


def _health_strip() -> None:
    """
    Thin persistent bar shown above every page.
    Shows: covenant status · delinquency · default · recon status
    Tappable chips navigate to the relevant page.
    """
    spv, summary, recon = _load_health_data()
    if spv is None or summary is None:
        return

    row     = summary.iloc[0] if not summary.empty else {}
    delinq  = float(row.get("delinquency_rate_pct", 0))
    default = float(row.get("default_rate_pct",     0))

    breaches   = spv[spv["covenant_delinquency_breach"].astype(bool)]
    n_breach   = len(breaches)
    recon_pass = (
        all(r == "PASS" for r in recon["reconciliation_status"])
        if recon is not None and not recon.empty else None
    )

    # ── Covenant chip ──────────────────────────────────────────────────────────
    if n_breach == 0:
        cov_dot = "#10b981"
        cov_chip_css = "background:rgba(16,185,129,.15);color:#6ee7b7"
        cov_txt = "All covenants OK"
    else:
        names = ", ".join(breaches["spv_id"].tolist())
        cov_dot = "#ef4444"
        cov_chip_css = "background:rgba(239,68,68,.18);color:#fca5a5"
        cov_txt = f"{names} in breach"

    # ── Recon chip ─────────────────────────────────────────────────────────────
    if recon_pass is True:
        rec_dot, rec_chip_css, rec_txt = "#10b981", "background:rgba(16,185,129,.15);color:#6ee7b7", "Recon PASS"
    elif recon_pass is False:
        rec_dot, rec_chip_css, rec_txt = "#ef4444", "background:rgba(239,68,68,.18);color:#fca5a5", "Recon FAIL"
    else:
        rec_dot, rec_chip_css, rec_txt = "#64748b", "background:rgba(100,116,139,.15);color:#94a3b8", "Recon n/a"

    num_chip_css = "background:rgba(37,99,235,.18);color:#93c5fd"
    dem_chip_css = "background:rgba(100,116,139,.12);color:#475569"
    _b = (  # base pill style
        "display:inline-flex;align-items:center;gap:6px;"
        "font-size:11.5px;font-weight:600;padding:5px 12px;"
        "border-radius:20px;white-space:nowrap;font-family:Inter,sans-serif;"
        "letter-spacing:.01em;"
    )

    def _dot(color: str) -> str:
        return (
            f"<span style='width:6px;height:6px;border-radius:50%;"
            f"background:{color};flex-shrink:0;display:inline-block;"
            f"box-shadow:0 0 5px {color};'></span>"
        )

    st.html(
        "<div style='"
        "background:linear-gradient(135deg,#0c1a30,#111f3a);"
        "border:1px solid rgba(99,130,200,.14);"
        "border-radius:14px;"
        "padding:10px 16px;"
        "margin-bottom:18px;"
        "display:flex;gap:6px;align-items:center;flex-wrap:wrap;"
        "box-shadow:0 2px 12px rgba(8,15,35,.18);"
        "font-family:Inter,sans-serif;'>"
        # Demo badge — neutral grey
        f"<span style='{_b}{dem_chip_css}'>"
        f"{_dot('#475569')}Demo · Synthetic data</span>"
        # Covenant
        f"<span style='{_b}{cov_chip_css}'>{_dot(cov_dot)}{cov_txt}</span>"
        # Delinquency
        f"<span style='{_b}{num_chip_css}'>{_dot('#60a5fa')}Delinquency {delinq:.2f}%</span>"
        # Default
        f"<span style='{_b}{num_chip_css}'>{_dot('#60a5fa')}Default {default:.2f}%</span>"
        # Recon
        f"<span style='{_b}{rec_chip_css}'>{_dot(rec_dot)}{rec_txt}</span>"
        "</div>"
    )


# ── Route ─────────────────────────────────────────────────────────────────────
page = st.session_state["page"]

_health_strip()   # persistent across all pages

if page == "overview":
    from app.views.overview import render
    render()
elif page == "spv":
    from app.views.spv_reporting import render
    render()
elif page == "cohort":
    from app.views.cohort_analysis import render
    render()
elif page == "recon":
    from app.views.reconciliation import render
    render()
elif page == "memo":
    from app.views.investor_memo import render
    render()
elif page == "arch":
    from app.views.architecture import render
    render()
