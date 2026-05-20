from __future__ import annotations

import streamlit as st

# Compact stack tags shown only in the sidebar footer / architecture page.
# Removed from every page_header to eliminate visual noise.
_STACK_BADGES = [
    ("10K loans",   "#f1f5f9", "#475569"),
    ("1.3M events", "#f1f5f9", "#475569"),
    ("3 SPVs",      "#f1f5f9", "#475569"),
    ("dbt 1.8",     "#ede9fe", "#6d28d9"),
    ("DuckDB",      "#e0f2fe", "#0369a1"),
    ("Claude AI",   "#faf5ff", "#7c3aed"),
]


def page_header(
    title: str,
    subtitle: str,
    badge: str | None = None,
    badge_color: str = "#dbeafe",
    badge_text_color: str = "#1d4ed8",
) -> None:
    """Page-level header — title, subtitle, optional status badge."""
    badge_html = (
        f"<span style='background:{badge_color};color:{badge_text_color};"
        f"font-size:10.5px;font-weight:700;padding:3px 11px;border-radius:20px;"
        f"letter-spacing:.06em;white-space:nowrap;border:1px solid {badge_color};'>"
        f"{badge}</span>"
        if badge else ""
    )
    st.html(
        f"<div style='margin-bottom:10px;font-family:Inter,sans-serif;'>"
        f"<div style='display:flex;align-items:center;flex-wrap:wrap;"
        f"gap:10px;margin-bottom:4px;'>"
        f"<div style='font-size:26px;font-weight:800;color:#060d1f;"
        f"letter-spacing:-.04em;line-height:1.1;'>{title}</div>"
        f"{badge_html}"
        f"</div>"
        f"<div style='font-size:13.5px;color:#5c6f85;line-height:1.55;"
        f"max-width:760px;'>{subtitle}</div>"
        f"</div>"
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Section sub-heading with a vivid left-accent bar."""
    sub = (
        f"<div style='font-size:12px;color:#8898aa;margin-top:3px;"
        f"font-weight:400;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.html(
        f"<div style='margin-bottom:16px;font-family:Inter,sans-serif;'>"
        f"<div style='display:flex;align-items:stretch;gap:0;'>"
        f"<div style='width:4px;min-height:100%;border-radius:4px;"
        f"background:linear-gradient(180deg,#2563eb,#6366f1);"
        f"flex-shrink:0;margin-right:12px;'></div>"
        f"<div>"
        f"<div style='font-size:14.5px;font-weight:700;color:#0f1f36;"
        f"letter-spacing:-.025em;line-height:1.3;'>{title}</div>"
        f"{sub}"
        f"</div>"
        f"</div>"
        f"</div>"
    )


def metric_card(
    label: str,
    value: str,
    sub: str = "",
    color: str = "#2563eb",
) -> None:
    """
    Styled KPI tile — left 4px accent border (color arg), JetBrains Mono value.
    Drop inside st.columns() for a metric row.
    """
    st.html(
        f"<div style='background:#fff;border-radius:16px;"
        f"border:1px solid #e4e9f0;border-left:4px solid {color};"
        f"padding:18px 20px 16px;"
        f"box-shadow:0 1px 4px rgba(15,23,42,.05);"
        f"font-family:Inter,sans-serif;"
        f"transition:box-shadow .18s,transform .18s;'>"
        f"<div style='font-size:10.5px;font-weight:700;color:#8898aa;"
        f"text-transform:uppercase;letter-spacing:.09em;"
        f"margin-bottom:10px;'>{label}</div>"
        f"<div style=\"font-family:'JetBrains Mono',monospace;"
        f"font-size:26px;font-weight:600;color:#060d1f;"
        f"letter-spacing:-.03em;font-variant-numeric:tabular-nums;"
        f"line-height:1.1;\">{value}</div>"
        f"<div style='font-size:11.5px;color:#7a8fa8;margin-top:7px;"
        f"font-weight:500;'>{sub}</div>"
        f"</div>"
    )
