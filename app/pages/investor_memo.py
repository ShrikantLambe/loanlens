"""
investor_memo.py — LLM-generated investor memo page.

Shows: Generate button, sentiment badge, commentary sections, anomaly alerts,
and a PDF download button.
"""

import io
import json
import logging

import pandas as pd
import streamlit as st

from app.utils import snowflake_conn as db


def _json_safe(obj):
    """Round-trip through JSON to convert all pandas/numpy types to plain Python."""
    return json.loads(json.dumps(obj, default=str))

logger = logging.getLogger(__name__)

SENTIMENT_CONFIG = {
    "positive": {"color": "#16a34a", "label": "POSITIVE", "icon": "🟢"},
    "cautious": {"color": "#d97706", "label": "CAUTIOUS", "icon": "🟡"},
    "concerning": {"color": "#dc2626", "label": "CONCERNING", "icon": "🔴"},
}

SEVERITY_COLOR = {
    "low": "#6b7280",
    "medium": "#d97706",
    "high": "#ea580c",
    "critical": "#dc2626",
}


@st.cache_data(ttl=300)
def _load_portfolio_data() -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Load all data needed for the AI layer."""
    summary_df = db.table("rpt_portfolio_summary")
    daily_df = db.table("fct_portfolio_daily")
    spv_df = db.table("fct_spv_allocation")

    summary = _json_safe(summary_df.iloc[0].to_dict() if not summary_df.empty else {})
    daily = _json_safe(daily_df.to_dict("records") if not daily_df.empty else [])
    spv_data = _json_safe(spv_df.to_dict("records") if not spv_df.empty else [])
    breaches = [s for s in spv_data if s.get("covenant_delinquency_breach")]
    return summary, daily, spv_data, breaches


def _generate_pdf(memo: dict) -> bytes:
    """Render memo to PDF bytes via WeasyPrint."""
    from weasyprint import HTML
    from ai_layer.memo_generator import memo_to_html

    html_content = memo_to_html(memo)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def render() -> None:
    """Render the Investor Memo (AI) page."""
    st.title("Investor Memo")
    st.caption(
        "LLM-generated investor-grade commentary powered by Claude. "
        "Reads live dbt model output and produces structured narrative, risk flags, and recommendations."
    )

    try:
        summary, daily, spv_data, breaches = _load_portfolio_data()
    except Exception as e:
        st.error(f"Failed to load portfolio data: {e}")
        return

    # Verify data is JSON-safe before passing to AI (catches stale cache edge cases)
    try:
        json.dumps(summary)
        json.dumps(spv_data[:1])
    except TypeError:
        _load_portfolio_data.clear()
        summary, daily, spv_data, breaches = _load_portfolio_data()

    st.divider()

    if st.button("Generate AI Commentary", type="primary", use_container_width=True):
        with st.spinner("Calling Claude... (~5–10 seconds)"):
            from ai_layer.memo_generator import build_memo
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
                err_str = str(e)
                if "usage limits" in err_str or "429" in err_str or "400" in err_str or "quota" in err_str.lower():
                    logger.warning("Anthropic API unavailable (%s) — falling back to demo mode.", e)
                    from ai_layer.demo_commentary import demo_portfolio_commentary, demo_anomalies
                    commentary = demo_portfolio_commentary(summary)
                    anomalies = demo_anomalies(spv_data)
                    demo_mode = True
                else:
                    st.error(f"AI generation failed: {e}")
                    logger.exception("AI generation error")
                    return

            memo = build_memo(commentary, anomalies, summary, spv_data)
            if demo_mode:
                memo["model_used"] = "demo-mode (API quota exceeded)"

            st.session_state["memo"] = memo
            st.session_state["commentary"] = commentary
            st.session_state["anomalies"] = anomalies
            st.session_state["demo_mode"] = demo_mode

    if "memo" not in st.session_state:
        st.info("Click 'Generate AI Commentary' to produce the investor memo.")
        return

    memo = st.session_state["memo"]
    commentary = st.session_state["commentary"]
    anomalies = st.session_state["anomalies"]
    demo_mode = st.session_state.get("demo_mode", False)

    if demo_mode:
        st.warning(
            "**Demo Mode** — Anthropic API quota exceeded. "
            "Commentary is pre-built from realistic mock data reflecting actual portfolio numbers. "
            "API access resumes 2026-05-01.",
            icon="⚠️",
        )

    # Sentiment badge
    sentiment = memo.get("sentiment", "cautious")
    cfg = SENTIMENT_CONFIG.get(sentiment, SENTIMENT_CONFIG["cautious"])
    st.markdown(
        f"<span style='background:{cfg['color']}; color:white; padding:4px 14px; "
        f"border-radius:4px; font-weight:bold; font-size:14px'>"
        f"{cfg['icon']} {cfg['label']}</span>",
        unsafe_allow_html=True,
    )
    st.caption(f"Period: {memo.get('period', 'N/A')}")

    st.divider()

    # Executive summary
    st.subheader("Executive Summary")
    st.write(memo.get("executive_summary", ""))

    # Key metrics narrative
    st.subheader("Portfolio Narrative")
    st.write(memo.get("narrative", ""))

    # Cohort observations
    st.subheader("Cohort Observations")
    st.write(memo.get("cohort_observations", ""))

    # Risk flags
    st.subheader("Risk Flags")
    risk_flags = memo.get("risk_flags", [])
    if risk_flags:
        for flag in risk_flags:
            st.warning(f"⚠️ {flag}")
    else:
        st.success("No material risk flags identified.")

    # Recommended actions
    st.subheader("Recommended Actions")
    for action in memo.get("recommended_actions", []):
        st.markdown(f"- {action}")

    # Anomaly alerts
    if anomalies:
        st.divider()
        st.subheader("Anomaly Alerts")
        for anomaly in anomalies:
            sev = anomaly.get("severity", "low")
            color = SEVERITY_COLOR.get(sev, "#6b7280")
            st.markdown(
                f"<div style='border-left: 4px solid {color}; padding: 8px 12px; "
                f"margin-bottom: 8px; background: #f9fafb;'>"
                f"<strong style='color:{color}'>[{sev.upper()}] {anomaly.get('anomaly_type', '')}</strong> "
                f"— {anomaly.get('affected_entity', '')}<br>"
                f"{anomaly.get('description', '')}<br>"
                f"<em>Action: {anomaly.get('recommended_action', '')}</em>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # SPV covenant table
    st.divider()
    st.subheader("SPV Covenant Status")
    covenant_rows = memo.get("covenant_status", [])
    if covenant_rows:
        cov_df = pd.DataFrame(covenant_rows)
        st.dataframe(cov_df, use_container_width=True, hide_index=True)

    # PDF download
    st.divider()
    if st.button("Generate PDF", use_container_width=False):
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = _generate_pdf(memo)
                st.download_button(
                    label="Download Investor Memo PDF",
                    data=pdf_bytes,
                    file_name=f"loanlens_memo_{memo.get('period', 'latest').replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except ImportError:
                st.error("WeasyPrint not installed. Run: pip install weasyprint")
            except Exception as e:
                st.error(f"PDF generation failed: {e}")

    # Footer
    st.divider()
    st.caption(
        f"Model: {memo.get('model_used', 'N/A')}  |  "
        f"Generated: {memo.get('generated_at', 'N/A')[:19]}  |  "
        f"{memo.get('disclaimer', '')}"
    )
