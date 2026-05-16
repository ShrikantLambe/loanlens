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

    /* ── Sidebar element spacing: flush all containers to zero margin ── */
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 2px !important;
        margin-top: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        width: 100% !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 2px !important;
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
        min-height: 36px !important;
        line-height: 1.4 !important;
        box-shadow: none !important;
        width: 100% !important;
        letter-spacing: .01em !important;
        transition: background .15s ease, color .15s ease !important;
        display: flex !important;
        align-items: center !important;
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
    # Brand
    st.html(
        "<div style='padding:8px 4px 20px;font-family:Inter,sans-serif;'>"
        "<div style='font-size:22px;font-weight:800;color:#f1f5f9;"
        "letter-spacing:-.03em;line-height:1;'>📊 LoanLens</div>"
        "<div style='font-size:11px;color:#475569;font-weight:500;"
        "letter-spacing:.06em;text-transform:uppercase;margin-top:5px;'>"
        "Portfolio Intelligence</div>"
        "</div>"
    )
    st.divider()

    # Navigation — active item rendered as a styled div (no split tags);
    # inactive items are st.buttons styled via global CSS.
    current = st.session_state["page"]
    for key, icon, label, is_ai in _PAGES:
        ai_badge = (
            "<span style='background:#7c3aed;color:#fff;font-size:9px;font-weight:700;"
            "padding:2px 6px;border-radius:8px;letter-spacing:.05em;margin-left:6px;"
            "vertical-align:middle;'>AI</span>"
            if is_ai else ""
        )
        display_label = f"{icon}&nbsp;&nbsp;{label}{ai_badge}"

        if current == key:
            st.html(
                f"<div style='background:rgba(37,99,235,.18);border-left:3px solid #3b82f6;"
                f"padding:9px 14px 9px 11px;border-radius:8px;color:#93c5fd;"
                f"font-size:13.5px;font-weight:600;margin:1px 0;cursor:default;"
                f"letter-spacing:.01em;font-family:Inter,sans-serif;'>"
                f"{display_label}</div>"
            )
        else:
            btn_label = f"{icon}  {label}{'  ✦' if is_ai else ''}"
            if st.button(btn_label, key=f"nav_{key}", use_container_width=True):
                st.session_state["page"] = key
                st.rerun()

    # Footer with external links (Prompt 18)
    st.divider()
    st.html(
        "<div style='font-family:Inter,sans-serif;padding:4px 0 48px;'>"
        "<div style='font-size:10px;color:#475569;font-weight:600;"
        "text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;'>"
        "Links</div>"
        "<div style='display:flex;flex-direction:column;gap:4px;'>"
        "<a href='https://github.com/ShrikantLambe/loanlens' target='_blank' "
        "style='font-size:12px;color:#64748b;text-decoration:none;'>"
        "⌥ GitHub — Source Code</a>"
        "<a href='https://shrikantlambe.github.io' target='_blank' "
        "style='font-size:12px;color:#64748b;text-decoration:none;'>"
        "◈ Portfolio — Shrikant Lambe</a>"
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

    # Build covenant chip
    if n_breach == 0:
        cov_bg, cov_fg, cov_txt = "#f0fdf4", "#15803d", "✓ All covenants OK"
        cov_nav = "spv"
    else:
        names = ", ".join(breaches["spv_id"].tolist())
        cov_bg, cov_fg, cov_txt = "#fee2e2", "#b91c1c", f"⚠ {names} in breach"
        cov_nav = "spv"

    # Recon chip
    if recon_pass is True:
        rec_bg, rec_fg, rec_txt = "#f0fdf4", "#15803d", "✓ Recon PASS"
    elif recon_pass is False:
        rec_bg, rec_fg, rec_txt = "#fee2e2", "#b91c1c", "✗ Recon FAIL"
    else:
        rec_bg, rec_fg, rec_txt = "#f1f5f9", "#64748b", "Recon n/a"

    chip = (
        "background:{bg};color:{fg};font-size:11px;font-weight:600;"
        "padding:3px 10px;border-radius:20px;white-space:nowrap;"
        "font-family:Inter,sans-serif;"
    )

    delinq_chip_style = chip.format(bg="#eff6ff", fg="#1d4ed8")
    default_chip_style = chip.format(bg="#eff6ff", fg="#1d4ed8")
    cov_chip_style = chip.format(bg=cov_bg, fg=cov_fg)
    rec_chip_style = chip.format(bg=rec_bg, fg=rec_fg)
    st.html(
        f"<div style='display:flex;gap:6px;align-items:center;flex-wrap:wrap;"
        f"padding:6px 0 12px;border-bottom:1px solid #f1f5f9;margin-bottom:4px;'>"
        f"<span style='background:#f1f5f9;color:#94a3b8;font-size:10px;font-weight:500;"
        f"padding:2px 8px;border-radius:12px;white-space:nowrap;"
        f"font-family:Inter,sans-serif;'>Demo · Synthetic data</span>"
        f"<span style='color:#e2e8f0;font-size:10px;'>|</span>"
        f"<span style='{cov_chip_style}'>{cov_txt}</span>"
        f"<span style='{delinq_chip_style}'>Delinquency {delinq:.2f}%</span>"
        f"<span style='{default_chip_style}'>Default {default:.2f}%</span>"
        f"<span style='{rec_chip_style}'>{rec_txt}</span>"
        f"</div>"
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
