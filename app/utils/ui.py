"""
ui.py — Shared UI components for LoanLens.

Rule: every st.markdown call must be a self-contained HTML fragment —
never open a tag in one call and close it in another, because Streamlit
renders each call inside its own isolated container.
Also: avoid <h1>/<p> inside st.markdown HTML; Streamlit's markdown parser
treats block-level HTML tags as markdown boundaries and breaks out of HTML
mode, causing the remainder to render as raw text. Use <div> everywhere.
"""

import streamlit as st


def page_header(
    title: str,
    subtitle: str,
    badge: str | None = None,
    badge_color: str = "#dbeafe",
    badge_text_color: str = "#1d4ed8",
) -> None:
    """Polished page-level header — replaces st.title + st.caption."""
    badge_html = (
        f"<span style='background:{badge_color};color:{badge_text_color};"
        f"font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;"
        f"letter-spacing:.05em;white-space:nowrap;'>{badge}</span>"
        if badge else ""
    )
    st.markdown(
        f"""<div style="margin-bottom:24px;padding-bottom:20px;
                        border-bottom:1px solid #f1f5f9;">
              <div style="display:flex;align-items:center;flex-wrap:wrap;
                          gap:10px;margin-bottom:6px;">
                <div style="font-size:26px;font-weight:800;color:#0f172a;
                            letter-spacing:-.03em;line-height:1.2;">{title}</div>
                {badge_html}
              </div>
              <div style="font-size:13.5px;color:#64748b;line-height:1.55;
                          max-width:700px;">{subtitle}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Section sub-heading with blue left-accent bar — replaces st.subheader."""
    sub = (
        f"<div style='font-size:12.5px;color:#94a3b8;margin-top:2px;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.markdown(
        f"""<div style="margin-bottom:14px;">
              <div style="border-left:3px solid #2563eb;padding-left:10px;">
                <div style="font-size:15px;font-weight:700;color:#1e293b;
                            letter-spacing:-.02em;">{title}</div>
                {sub}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sub: str = "", color: str = "#2563eb") -> None:
    """Styled metric tile for use inside st.columns()."""
    st.markdown(
        f"""<div style="background:#fff;border-radius:14px;padding:18px 20px;
                        box-shadow:0 0 0 1px rgba(15,23,42,.06),
                                   0 2px 8px rgba(15,23,42,.04);
                        position:relative;overflow:hidden;">
              <div style="position:absolute;top:0;left:0;right:0;height:3px;
                          background:{color};"></div>
              <div style="font-size:11px;font-weight:600;color:#94a3b8;
                          text-transform:uppercase;letter-spacing:.07em;
                          margin-bottom:8px;">{label}</div>
              <div style="font-size:24px;font-weight:700;color:#0f172a;
                          letter-spacing:-.025em;
                          font-variant-numeric:tabular-nums;
                          line-height:1.1;">{value}</div>
              <div style="font-size:12px;color:#64748b;margin-top:5px;">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )
