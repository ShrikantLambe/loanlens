from __future__ import annotations
"""
ui.py — Shared UI components for LoanLens.

All complex HTML uses st.html() (Streamlit 1.36+) which bypasses the
markdown tokeniser and renders the HTML fragment directly. Never use
st.markdown(html, unsafe_allow_html=True) for content HTML — the markdown
parser breaks out of HTML mode at block-level tags and newlines, causing
closing tags and attribute strings to appear as raw visible text.
"""

import streamlit as st


_STACK_BADGES = [
    ("10K loans",   "#f1f5f9", "#475569"),
    ("1.3M events", "#f1f5f9", "#475569"),
    ("3 SPVs",      "#f1f5f9", "#475569"),
    ("dbt 1.8",     "#ede9fe", "#6d28d9"),
    ("DuckDB",      "#e0f2fe", "#0369a1"),
    ("Claude AI",   "#faf5ff", "#7c3aed"),
]

_STACK_HTML = " ".join(
    f"<span style='background:{bg};color:{fg};font-size:10px;font-weight:600;"
    f"padding:2px 8px;border-radius:12px;white-space:nowrap;'>{label}</span>"
    for label, bg, fg in _STACK_BADGES
)


def page_header(
    title: str,
    subtitle: str,
    badge: str | None = None,
    badge_color: str = "#dbeafe",
    badge_text_color: str = "#1d4ed8",
) -> None:
    """Polished page-level header with optional badge and persistent stack pills."""
    badge_html = (
        f"<span style='background:{badge_color};color:{badge_text_color};"
        f"font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;"
        f"letter-spacing:.05em;white-space:nowrap;'>{badge}</span>"
        if badge else ""
    )
    st.html(
        f"<div style='margin-bottom:20px;padding-bottom:16px;"
        f"border-bottom:1px solid #f1f5f9;font-family:Inter,sans-serif;'>"
        f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px;'>"
        f"<div style='font-size:26px;font-weight:800;color:#0f172a;"
        f"letter-spacing:-.03em;line-height:1.2;'>{title}</div>"
        f"{badge_html}"
        f"</div>"
        f"<div style='font-size:13.5px;color:#64748b;line-height:1.55;"
        f"max-width:700px;margin-bottom:10px;'>{subtitle}</div>"
        f"<div style='display:flex;gap:5px;flex-wrap:wrap;align-items:center;'>"
        f"<span style='font-size:10px;color:#94a3b8;font-weight:500;margin-right:2px;'>Built with</span>"
        f"{_STACK_HTML}"
        f"</div>"
        f"</div>"
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Section sub-heading with blue left-accent bar."""
    sub = (
        f"<div style='font-size:12.5px;color:#94a3b8;margin-top:2px;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.html(
        f"<div style='margin-bottom:14px;font-family:Inter,sans-serif;'>"
        f"<div style='border-left:3px solid #2563eb;padding-left:10px;'>"
        f"<div style='font-size:15px;font-weight:700;color:#1e293b;"
        f"letter-spacing:-.02em;'>{title}</div>"
        f"{sub}"
        f"</div>"
        f"</div>"
    )


def metric_card(label: str, value: str, sub: str = "", color: str = "#2563eb") -> None:
    """Styled metric tile for use inside st.columns()."""
    st.html(
        f"<div style='background:#fff;border-radius:14px;padding:18px 20px;"
        f"box-shadow:0 0 0 1px rgba(15,23,42,.06),0 2px 8px rgba(15,23,42,.04);"
        f"position:relative;overflow:hidden;font-family:Inter,sans-serif;'>"
        f"<div style='position:absolute;top:0;left:0;right:0;height:3px;"
        f"background:{color};'></div>"
        f"<div style='font-size:11px;font-weight:600;color:#94a3b8;"
        f"text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;'>{label}</div>"
        f"<div style='font-size:24px;font-weight:700;color:#0f172a;"
        f"letter-spacing:-.025em;font-variant-numeric:tabular-nums;"
        f"line-height:1.1;'>{value}</div>"
        f"<div style='font-size:12px;color:#64748b;margin-top:5px;'>{sub}</div>"
        f"</div>"
    )
