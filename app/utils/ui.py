"""
ui.py — Shared UI components for consistent page-level design.
"""

import streamlit as st


def page_header(
    title: str,
    subtitle: str,
    badge: str | None = None,
    badge_color: str = "#dbeafe",
    badge_text_color: str = "#1d4ed8",
) -> None:
    """
    Renders a polished page header with title, subtitle, and an optional badge.
    Replaces the bare st.title() + st.caption() pattern.
    """
    badge_html = ""
    if badge:
        badge_html = (
            f"<span style='background:{badge_color}; color:{badge_text_color}; "
            f"font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; "
            f"letter-spacing:.05em; vertical-align:middle; margin-left:10px;'>"
            f"{badge}</span>"
        )

    st.markdown(
        f"""
        <div style="margin-bottom:24px; padding-bottom:20px;
                    border-bottom:1px solid #f1f5f9;">
            <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;
                        margin-bottom:6px;">
                <h1 style="margin:0; padding:0; font-size:26px; font-weight:800;
                           color:#0f172a; letter-spacing:-.03em; line-height:1.2;">
                    {title}
                </h1>
                {badge_html}
            </div>
            <p style="margin:0; font-size:13.5px; color:#64748b; line-height:1.55;
                      max-width:680px;">
                {subtitle}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """
    A section-level sub-heading with a blue left-accent bar and optional caption.
    Use instead of st.subheader() for consistent visual weight.
    """
    sub_html = (
        f"<p style='margin:2px 0 0; font-size:12.5px; color:#94a3b8; "
        f"line-height:1.4;'>{subtitle}</p>"
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div style="margin-bottom:14px;">
            <div style="border-left:3px solid #2563eb; padding-left:10px;">
                <div style="font-size:15px; font-weight:700; color:#1e293b;
                            letter-spacing:-.02em;">{title}</div>
                {sub_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_callout(label: str, value: str, sub: str, color: str = "#2563eb") -> None:
    """
    A standalone KPI tile — use inside st.columns() for callout rows
    that aren't standard Streamlit metrics (e.g. text-based highlights).
    """
    st.markdown(
        f"""
        <div style="background:#fff; border-radius:14px; padding:18px 20px;
                    box-shadow:0 0 0 1px rgba(15,23,42,.06),0 2px 8px rgba(15,23,42,.04);
                    position:relative; overflow:hidden;">
            <div style="position:absolute; top:0; left:0; right:0; height:3px;
                        background:{color};"></div>
            <div style="font-size:11px; font-weight:600; color:#94a3b8;
                        text-transform:uppercase; letter-spacing:.07em;
                        margin-bottom:8px;">{label}</div>
            <div style="font-size:24px; font-weight:700; color:#0f172a;
                        letter-spacing:-.025em; font-variant-numeric:tabular-nums;
                        line-height:1.1;">{value}</div>
            <div style="font-size:12px; color:#64748b; margin-top:5px;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_chip(label: str, status: str) -> str:
    """
    Returns an inline HTML chip string.
    status: 'ok' | 'warning' | 'danger' | 'neutral'
    """
    colors = {
        "ok":      ("#dcfce7", "#15803d"),
        "warning": ("#fef9c3", "#b45309"),
        "danger":  ("#fee2e2", "#b91c1c"),
        "neutral": ("#f1f5f9", "#475569"),
    }
    bg, fg = colors.get(status, colors["neutral"])
    return (
        f"<span style='background:{bg}; color:{fg}; font-size:11px; font-weight:700; "
        f"padding:3px 8px; border-radius:20px; white-space:nowrap;'>{label}</span>"
    )
