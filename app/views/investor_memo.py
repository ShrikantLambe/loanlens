"""
investor_memo.py — LLM-generated investor memo page.

Shows: Generate button, sentiment badge, card-based commentary sections,
anomaly alerts, covenant table, and a PDF download button.
"""

import io
import json
import logging

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db
from app.utils.ui import page_header, section_header

logger = logging.getLogger(__name__)

SENTIMENT_CONFIG = {
    "positive": {"bg": "#dcfce7", "border": "#16a34a", "text": "#15803d", "label": "POSITIVE", "icon": "▲"},
    "cautious":  {"bg": "#fef9c3", "border": "#d97706", "text": "#b45309", "label": "CAUTIOUS",  "icon": "●"},
    "concerning":{"bg": "#fee2e2", "border": "#dc2626", "text": "#b91c1c", "label": "CONCERNING","icon": "▼"},
}

SEVERITY_COLOR = {
    "low":      "#6b7280",
    "medium":   "#d97706",
    "high":     "#ea580c",
    "critical": "#dc2626",
}

_CARD_CSS = (
    "background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; "
    "padding:20px 22px; margin-bottom:16px;"
)
_CARD_TITLE = "font-size:13px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:.05em; margin-bottom:10px;"
_CARD_BODY  = "font-size:15px; color:#1e293b; line-height:1.65;"


def _card(title: str, body: str) -> None:
    st.html(
        f"<div style='{_CARD_CSS}'>"
        f"<div style='{_CARD_TITLE}'>{title}</div>"
        f"<div style='{_CARD_BODY}'>{body}</div>"
        f"</div>"
    )


def _json_safe(obj):
    """Round-trip through JSON to convert all pandas/numpy types to plain Python."""
    return json.loads(json.dumps(obj, default=str))


@st.cache_data(ttl=300)
def _load_portfolio_data() -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Load all data needed for the AI layer."""
    summary_df = db.table("rpt_portfolio_summary")
    daily_df   = db.table("fct_portfolio_daily")
    spv_df     = db.table("fct_spv_allocation")

    summary  = _json_safe(summary_df.iloc[0].to_dict() if not summary_df.empty else {})
    daily    = _json_safe(daily_df.to_dict("records") if not daily_df.empty else [])
    spv_data = _json_safe(spv_df.to_dict("records") if not spv_df.empty else [])
    breaches = [s for s in spv_data if s.get("covenant_delinquency_breach")]
    return summary, daily, spv_data, breaches


def _generate_pdf(memo: dict) -> bytes:
    """Render memo to PDF bytes via WeasyPrint."""
    from weasyprint import HTML
    from ai_layer.memo_generator import memo_to_html
    return HTML(string=memo_to_html(memo)).write_pdf()


def render() -> None:
    """Render the Investor Memo (AI) page."""
    page_header(
        "Investor Memo",
        "Claude reads live dbt output and writes structured investor-grade commentary — "
        "sentiment rating, risk flags, anomaly alerts, and recommended actions.",
        badge="AI Generated",
        badge_color="#faf5ff",
        badge_text_color="#7c3aed",
    )

    try:
        summary, daily, spv_data, breaches = _load_portfolio_data()
    except Exception as e:
        st.error(f"Failed to load portfolio data: {e}")
        return

    # Verify JSON-safety (clears stale cache edge cases)
    try:
        json.dumps(summary); json.dumps(spv_data[:1])
    except TypeError:
        _load_portfolio_data.clear()
        summary, daily, spv_data, breaches = _load_portfolio_data()

    # --- Snapshot stats row ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Loans", f"{summary.get('total_loans', 0):,}")
    with c2:
        st.metric("Delinquency Rate", f"{summary.get('delinquency_rate_pct', 0):.2f}%")
    with c3:
        st.metric("Default Rate", f"{summary.get('default_rate_pct', 0):.2f}%")

    st.divider()

    # --- Buttons: layout differs by state ---
    has_memo = "memo" in st.session_state
    if not has_memo:
        # State 1: prominent single CTA with description
        st.html(
            "<div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;"
            "padding:20px 24px;margin-bottom:16px;font-family:Inter,sans-serif;'>"
            "<div style='font-size:15px;font-weight:700;color:#1e40af;margin-bottom:6px;'>"
            "Generate AI-powered investor commentary</div>"
            "<div style='font-size:13px;color:#3b82f6;line-height:1.5;'>"
            "Claude will read the live portfolio data and write structured output: "
            "executive summary, risk flags, cohort observations, and recommended actions — "
            "ready to export as a PDF memo."
            "</div></div>"
        )
        generate = st.button(
            "Generate AI Commentary →", type="primary", use_container_width=True
        )
        pdf_btn = False
    else:
        # State 2: Regenerate (secondary) + Download PDF (primary)
        col_regen, col_pdf = st.columns([1, 1])
        with col_regen:
            generate = st.button(
                "↻ Regenerate", use_container_width=True,
                help="Call Claude again to refresh the commentary.",
            )
        with col_pdf:
            pdf_btn = st.button(
                "⬇ Download PDF", type="primary", use_container_width=True,
                help="Export this memo as a PDF report.",
            )

    if generate:
        with st.spinner("Calling Claude… (~5–10 seconds)"):
            demo_mode = False
            try:
                from ai_layer.portfolio_narrator import generate_portfolio_commentary
                from ai_layer.anomaly_agent import detect_anomalies

                commentary = generate_portfolio_commentary(
                    summary=summary,
                    recent_trend=daily,
                    spv_data=spv_data,
                    covenant_breaches=breaches,
                )
                anomalies = detect_anomalies(daily_data=daily, spv_data=spv_data)

            except Exception as e:
                err = str(e)
                if any(k in err for k in ("usage limits", "429", "400", "quota")):
                    logger.warning("Anthropic API unavailable (%s) — demo mode.", e)
                    from ai_layer.demo_commentary import demo_portfolio_commentary, demo_anomalies
                    commentary = demo_portfolio_commentary(summary)
                    anomalies  = demo_anomalies(spv_data)
                    demo_mode  = True
                else:
                    st.error(f"AI generation failed: {e}")
                    logger.exception("AI generation error")
                    return

            from ai_layer.memo_generator import build_memo
            memo = build_memo(commentary, anomalies, summary, spv_data)
            if demo_mode:
                memo["model_used"] = "demo-mode (API quota exceeded)"

            st.session_state["memo"]        = memo
            st.session_state["commentary"]  = commentary
            st.session_state["anomalies"]   = anomalies
            st.session_state["demo_mode"]   = demo_mode

    # --- PDF download (triggered separately so it doesn't re-run generation) ---
    if pdf_btn and "memo" in st.session_state:
        with st.spinner("Generating PDF…"):
            try:
                pdf_bytes = _generate_pdf(st.session_state["memo"])
                period = st.session_state["memo"].get("period", "latest").replace(" ", "_")
                st.download_button(
                    label="⬇ Download Investor Memo PDF",
                    data=pdf_bytes,
                    file_name=f"loanlens_memo_{period}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

    if "memo" not in st.session_state:
        return   # State 1 already rendered above — nothing more to show

    memo       = st.session_state["memo"]
    commentary = st.session_state["commentary"]
    anomalies  = st.session_state["anomalies"]
    demo_mode  = st.session_state.get("demo_mode", False)

    # --- CRITICAL / HIGH anomalies — clearly marked as point-in-time snapshot ---
    gen_ts = str(memo.get("generated_at", ""))[:19]
    urgent = [a for a in anomalies if a.get("severity") in ("critical", "high")]
    if urgent:
        section_header(
            "⚠ Active Alerts",
            f"Snapshot at memo generation · {gen_ts} — see Portfolio Overview for real-time status",
        )
        for a in urgent:
            sev   = a.get("severity", "high")
            color = SEVERITY_COLOR.get(sev, "#ea580c")
            st.html(
    f"<div style='border-left:4px solid {color}; padding:10px 14px; "
                f"background:#fff7ed; border-radius:0 8px 8px 0; margin-bottom:10px;'>"
                f"<div style='font-weight:700; color:{color}; font-size:13px'>"
                f"[{sev.upper()}] {a.get('anomaly_type','').replace('_',' ').title()}"
                f" — {a.get('affected_entity','')}</div>"
                f"<div style='color:#1e293b; margin:4px 0'>{a.get('description','')}</div>"
                f"<div style='color:#64748b; font-size:13px'>"
                f"<em>Recommended action: {a.get('recommended_action','')}</em></div>"
                f"</div>"
)
        st.divider()

    if demo_mode:
        st.warning(
            "**Demo Mode** — API quota exceeded. Commentary is built from pre-computed mock data "
            "reflecting actual portfolio figures.",
            icon="⚠️",
        )

    # --- Sentiment badge ---
    sentiment = memo.get("sentiment", "cautious")
    cfg = SENTIMENT_CONFIG.get(sentiment, SENTIMENT_CONFIG["cautious"])
    st.html(
    f"<div style='display:inline-block; background:{cfg['bg']}; border:2px solid {cfg['border']}; "
        f"color:{cfg['text']}; padding:6px 18px; border-radius:6px; font-weight:800; font-size:15px; "
        f"letter-spacing:.04em; margin-bottom:4px'>"
        f"{cfg['icon']} {cfg['label']}"
        f"</div>"
        f"<span style='color:#94a3b8; font-size:13px; margin-left:12px'>{memo.get('period','')}</span>"
)

    st.divider()

    # --- Commentary cards ---
    _card("Executive Summary", memo.get("executive_summary", ""))
    _card("Portfolio Narrative", memo.get("narrative", ""))
    _card("Cohort Observations", memo.get("cohort_observations", ""))

    # Risk flags
    risk_flags = memo.get("risk_flags", [])
    if risk_flags:
        flags_html = "".join(
            f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:8px'>"
            f"<span style='color:#dc2626; font-size:14px; margin-top:2px'>⚠</span>"
            f"<span>{f}</span></div>"
            for f in risk_flags
        )
        _card("Risk Flags", flags_html)
    else:
        _card("Risk Flags", "<span style='color:#16a34a'>✓ No material risk flags identified.</span>")

    # Recommended actions
    actions = memo.get("recommended_actions", [])
    if actions:
        actions_html = "".join(
            f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:8px'>"
            f"<span style='color:#2563eb; font-weight:700'>→</span>"
            f"<span>{a}</span></div>"
            for a in actions
        )
        _card("Recommended Actions", actions_html)

    # --- Anomaly alerts ---
    if anomalies:
        st.divider()
        section_header("Anomaly Alerts")
        for anomaly in anomalies:
            sev   = anomaly.get("severity", "low")
            color = SEVERITY_COLOR.get(sev, "#6b7280")
            st.html(
    f"<div style='border-left:4px solid {color}; padding:10px 14px; "
                f"background:#f8fafc; border-radius:0 8px 8px 0; margin-bottom:10px;'>"
                f"<div style='font-weight:700; color:{color}; font-size:13px'>"
                f"[{sev.upper()}] {anomaly.get('anomaly_type','').replace('_',' ').title()}"
                f" &mdash; {anomaly.get('affected_entity','')}</div>"
                f"<div style='color:#1e293b; margin:4px 0'>{anomaly.get('description','')}</div>"
                f"<div style='color:#64748b; font-size:13px'><em>Action: {anomaly.get('recommended_action','')}</em></div>"
                f"</div>"
)

    # --- SPV covenant table ---
    covenant_rows = memo.get("covenant_status", [])
    if covenant_rows:
        st.divider()
        section_header("SPV Covenant Status")
        cov_df = pd.DataFrame(covenant_rows)
        st.dataframe(cov_df, use_container_width=True, hide_index=True)

    # --- Footer ---
    st.divider()
    model = memo.get("model_used", "N/A")
    gen_at = str(memo.get("generated_at", "N/A"))[:19]
    disclaimer = memo.get("disclaimer", "")
    st.caption(f"Model: {model}  ·  Generated: {gen_at}  ·  {disclaimer}")
