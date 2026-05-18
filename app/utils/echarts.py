from __future__ import annotations
"""
utils/echarts.py — Apache ECharts rendering layer for LoanLens.

Single source of truth for every chart.  All pages import from here.
No Plotly or st.bar_chart calls remain after this module is wired in.

Key conventions:
  - All monetary values are passed in raw dollars (not millions).
  - Rate values are 0-1 (e.g. 0.08 = 8%) and converted to 0-100 internally.
  - Every builder returns a plain dict (ECharts option).
  - render() deep-merges onto BASE_OPTION and calls st_echarts().
  - JsCode strings use ES5 syntax for broad browser compat.
"""

import copy
import hashlib
import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

# ── JavaScript helper ──────────────────────────────────────────────────────────
# streamlit-echarts wraps JS callbacks in "--x_x--0_0--" sentinel markers so the
# frontend can distinguish them from plain strings and eval() them as functions.
# _js() does the same but is not JSON-serializable in Streamlit 1.35+.
# Using a plain string with the sentinels is identical to JsCode and IS serializable.
_P = "--x_x--0_0--"

def _js(code: str) -> str:
    """Wrap a JS function string so ECharts treats it as executable code."""
    return f"{_P}{code}{_P}"


# ── Design tokens ─────────────────────────────────────────────────────────────

PALETTE = {
    "primary":  "#2563eb",
    "success":  "#10b981",
    "danger":   "#ef4444",
    "amber":    "#f59e0b",
    "neutral":  "#8898aa",
    "purple":   "#6366f1",
    "platforms": {
        "doordash": "#ff3008",
        "amazon":   "#ff9900",
        "mindbody": "#00b5ad",
        "worldpay": "#1a56db",
        "shopify":  "#96bf48",
    },
}

_SERIES_COLORS = [
    PALETTE["primary"], PALETTE["success"], PALETTE["amber"],
    PALETTE["danger"],  PALETTE["purple"],  PALETTE["neutral"],
]

# ── Base option (inherited by every chart) ─────────────────────────────────────

BASE_OPTION: dict = {
    "color": _SERIES_COLORS,
    "backgroundColor": "transparent",
    "textStyle": {
        "fontFamily": "Inter, 'JetBrains Mono', system-ui, sans-serif",
        "color": "#3d4f63",
        "fontSize": 12,
    },
    "animation": True,
    "animationDuration": 600,
    "animationEasing": "cubicOut",
    "tooltip": {
        "trigger": "axis",
        "backgroundColor": "#0f172a",
        "borderColor": "#1e293b",
        "borderWidth": 1,
        "padding": [10, 14],
        "textStyle": {
            "color": "#f1f5f9",
            "fontSize": 12,
            "fontFamily": "Inter, system-ui",
        },
        "axisPointer": {
            "type": "cross",
            "label": {"backgroundColor": "#1e293b"},
            "crossStyle": {"color": "#334155"},
        },
    },
    # right: 52 clears the 2-icon toolbox (2×13 + 6 gap + 12 right = 44px) with buffer
    "legend": {
        "top": 8,
        "right": 52,
        "textStyle": {"color": "#5c6f85", "fontSize": 11},
        "itemHeight": 10,
        "itemGap": 12,
    },
    "grid": {"left": 60, "right": 24, "top": 52, "bottom": 60, "containLabel": True},
    # Toolbox: 2 icons only (save + dataView) so legend has room.
    # 2 × 13px + 1 × 6px gap + 12px right = ~44px total occupied at right edge.
    # Legend right is set to 52 below to stay clear.
    "toolbox": {
        "feature": {
            "saveAsImage": {
                "title": "Save PNG",
                "pixelRatio": 2,
            },
            "dataView": {
                "title": "Data",
                "readOnly": True,
                "lang": ["Data", "Close", "Refresh"],
                "textareaColor": "#f8fafc",
                "textColor": "#3d4f63",
                "buttonColor": "#2563eb",
            },
        },
        "itemSize": 13,
        "itemGap": 6,
        "right": 12,
        "top": 6,
        "iconStyle": {"borderColor": "#c8d4e4"},
        "emphasis": {"iconStyle": {"borderColor": "#2563eb"}},
    },
}


# ── Core render helper ─────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override onto base; non-dict values replace."""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def render(option: dict, height: str = "420px", key: str | None = None) -> None:
    """Merge option onto BASE_OPTION and render via st_echarts."""
    merged = _deep_merge(BASE_OPTION, option)
    # Derive a stable key from the chart title if none given
    if key is None:
        title = option.get("title", {})
        if isinstance(title, list):
            title = title[0] if title else {}
        raw = str(title.get("text", id(option)))
        key = "ec_" + hashlib.md5(raw.encode()).hexdigest()[:8]
    st_echarts(options=merged, height=height, key=key)


# ── Chart builders ─────────────────────────────────────────────────────────────

def delinquency_trend_option(
    df: pd.DataFrame,
    covenant_limit: float | None = None,
) -> dict:
    """
    Smooth area line chart with:
    - Gradient blue fill under the delinquency series
    - 4-week rolling avg as a dashed amber line
    - Optional red markLine + faint markArea breach zone
    - dataZoom slider at bottom
    """
    df = df.copy()
    date_col = "week_date" if "week_date" in df.columns else "date_day"
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    df["rolling"] = df["delinquency_rate"].rolling(4, min_periods=1).mean()

    dates  = df[date_col].dt.strftime("%Y-%m-%d").tolist()
    actual = (df["delinquency_rate"] * 100).round(3).tolist()
    rolling = (df["rolling"] * 100).round(3).tolist()

    tooltip_fmt = _js(
        "function(params){"
        "var h='<div style=\"font-weight:700;margin-bottom:5px;\">'+params[0].name+'</div>';"
        "params.forEach(function(p){"
        "  h+=p.marker+' '+p.seriesName+': <strong>'+p.value.toFixed(2)+'%</strong><br/>';});"
        "return h;}"
    )

    actual_series: dict = {
        "name": "Delinquency Rate",
        "type": "line",
        "data": actual,
        "smooth": True,
        "symbol": "none",
        "lineStyle": {"width": 2.5, "color": PALETTE["primary"]},
        "areaStyle": {
            "color": {
                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                "colorStops": [
                    {"offset": 0, "color": "rgba(37,99,235,0.28)"},
                    {"offset": 1, "color": "rgba(37,99,235,0.02)"},
                ],
            }
        },
    }

    if covenant_limit is not None:
        limit_pct = round(covenant_limit * 100, 3)
        max_pct   = max(actual) * 1.2 if actual else limit_pct * 1.5
        actual_series["markLine"] = {
            "silent": True,
            "symbol": ["none", "none"],
            "data": [{"yAxis": limit_pct}],
            "lineStyle": {"type": "dashed", "color": PALETTE["danger"], "width": 2},
            "label": {
                "position": "insideEndTop",
                "formatter": f"Covenant {covenant_limit:.1%}",
                "color": PALETTE["danger"],
                "fontSize": 11,
                "fontWeight": "600",
            },
        }
        # Narrow band (3pp wide) above the covenant line — avoids flooding the chart
        # red when the data line is already far above the limit.
        actual_series["markArea"] = {
            "silent": True,
            "itemStyle": {"color": "rgba(239,68,68,0.08)"},
            "data": [[{"yAxis": limit_pct}, {"yAxis": limit_pct + 3.0}]],
        }

    return {
        "title": {
            "text": "Delinquency Rate — Rolling 12 Months",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
            "top": 0, "left": 0,
        },
        "tooltip": {"formatter": tooltip_fmt},
        "legend": {
            "data": ["Delinquency Rate", "4-wk Rolling Avg"],
            "top": 8,
            "right": 52,
        },
        "xAxis": {
            "type": "category",
            "data": dates,
            "boundaryGap": False,
            "axisLabel": {"color": "#8898aa", "fontSize": 10, "rotate": -20},
            "axisLine": {"lineStyle": {"color": "#e4e9f0"}},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {
                "color": "#8898aa",
                "formatter": _js("function(v){return v.toFixed(1)+'%'}"),
            },
            "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
        },
        "series": [
            actual_series,
            {
                "name": "4-wk Rolling Avg",
                "type": "line",
                "data": rolling,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"width": 2, "type": "dashed", "color": PALETTE["amber"]},
            },
        ],
        "dataZoom": [
            {
                "type": "slider",
                "start": 0, "end": 100,
                "bottom": 4, "height": 20,
                "borderColor": "#e4e9f0",
                "textStyle": {"color": "#8898aa", "fontSize": 10},
                "fillerColor": "rgba(37,99,235,0.1)",
            },
        ],
        "grid": {"left": 60, "right": 20, "top": 52, "bottom": 52, "containLabel": True},
    }


def kpi_sparkline_option(values: list[float], color: str = "#2563eb") -> dict:
    """Minimal sparkline for embedding below a KPI value. No axes, no grid."""
    _alpha = {
        "#2563eb": "rgba(37,99,235,0.2)",
        "#ef4444": "rgba(239,68,68,0.2)",
        "#10b981": "rgba(16,185,129,0.2)",
        "#f59e0b": "rgba(245,158,11,0.2)",
    }
    fill = _alpha.get(color, "rgba(37,99,235,0.15)")
    return {
        "animation": False,
        "grid":  {"left": 0, "right": 0, "top": 2, "bottom": 2},
        "xAxis": {"type": "category", "show": False},
        "yAxis": {"type": "value",    "show": False},
        "tooltip": {"show": False},
        "legend": {"show": False},
        "toolbox": {"show": False},
        "series": [{
            "type": "line",
            "data": [round(v, 4) for v in values],
            "smooth": True,
            "symbol": "none",
            "lineStyle": {"width": 1.5, "color": color},
            "areaStyle": {"color": fill},
        }],
    }


def origination_volume_option(df: pd.DataFrame) -> dict:
    """Stacked bars by platform + loan-count line on secondary y-axis."""
    df = df.copy()
    df["origination_month"] = pd.to_datetime(df["origination_month"])
    months = sorted(df["origination_month"].dt.strftime("%Y-%m").unique().tolist())
    platforms = sorted(df["platform"].unique().tolist())

    monthly_counts = (
        df.groupby(df["origination_month"].dt.strftime("%Y-%m"))["loan_count"]
        .sum().reindex(months, fill_value=0).tolist()
    )

    series: list[dict] = []
    for plat in platforms:
        sub = df[df["platform"] == plat]
        data = []
        for m in months:
            row = sub[sub["origination_month"].dt.strftime("%Y-%m") == m]
            data.append(round(float(row["origination_volume"].sum()), 2))
        series.append({
            "name": plat.title(),
            "type": "bar",
            "stack": "vol",
            "data": data,
            "itemStyle": {"color": PALETTE["platforms"].get(plat, PALETTE["neutral"])},
            "emphasis": {"focus": "series"},
        })

    series.append({
        "name": "Loan Count",
        "type": "line",
        "yAxisIndex": 1,
        "data": monthly_counts,
        "smooth": True,
        "symbol": "circle",
        "symbolSize": 4,
        "lineStyle": {"width": 2, "color": "#0f172a"},
        "itemStyle": {"color": "#0f172a"},
        "z": 10,
    })

    tooltip_fmt = _js(
        "function(params){"
        "var h='<div style=\"font-weight:700;margin-bottom:5px;\">'+params[0].name+'</div>';"
        "var tot=0;"
        "params.forEach(function(p){"
        "  if(p.seriesName!=='Loan Count'){h+=p.marker+' '+p.seriesName+': <strong>$'+(p.value/1e6).toFixed(2)+'M</strong><br/>';tot+=p.value||0;}"
        "});"
        "h+='<hr style=\"border:none;border-top:1px solid #334155;margin:5px 0\"/>';"
        "h+='<span style=\"color:#93c5fd\">Total: <strong>$'+(tot/1e6).toFixed(2)+'M</strong></span><br/>';"
        "params.forEach(function(p){if(p.seriesName==='Loan Count')h+='<span style=\"color:#93c5fd\">Loans: <strong>'+p.value.toLocaleString()+'</strong></span>';});"
        "return h;}"
    )

    return {
        "title": {
            "text": "Monthly Origination Volume by Platform",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
        },
        "tooltip": {"trigger": "axis", "formatter": tooltip_fmt},
        # 6 legend items (5 platforms + loan count) — bottom scrollable.
        # "top": "auto" MUST be set to override BASE_OPTION's "top": 8;
        # ECharts rules: when both top and bottom are present, top wins.
        "legend": {
            "data": [p.title() for p in platforms] + ["Loan Count"],
            "top": "auto",
            "bottom": 28,
            "type": "scroll",
            "pageTextStyle": {"color": "#8898aa", "fontSize": 10},
            "textStyle": {"color": "#5c6f85", "fontSize": 10},
            "itemHeight": 9,
            "itemGap": 8,
        },
        "xAxis": {
            "type": "category",
            "data": months,
            "axisLabel": {"rotate": -30, "color": "#8898aa", "fontSize": 10},
            "axisLine": {"lineStyle": {"color": "#e4e9f0"}},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Volume",
                "axisLabel": {
                    "formatter": _js("function(v){return '$'+(v/1e6).toFixed(0)+'M'}"),
                    "color": "#8898aa",
                },
                "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
                "nameTextStyle": {"color": "#8898aa"},
            },
            {
                "type": "value",
                "name": "Loans",
                "axisLabel": {
                    "formatter": _js("function(v){return v.toLocaleString()}"),
                    "color": "#8898aa",
                },
                "splitLine": {"show": False},
                "nameTextStyle": {"color": "#8898aa"},
            },
        ],
        "series": series,
        "dataZoom": [
            {
                "type": "slider",
                "start": 0, "end": 100,
                "bottom": 4, "height": 18,
                "borderColor": "#e4e9f0",
                "fillerColor": "rgba(37,99,235,0.1)",
                "textStyle": {"color": "#8898aa", "fontSize": 10},
            },
        ],
        "grid": {"left": 70, "right": 70, "top": 44, "bottom": 72, "containLabel": False},
    }


def spv_bar_option(df: pd.DataFrame) -> dict:
    """Grouped bars: actual delinquency vs covenant limit per SPV, colored by breach state."""
    spv = df.sort_values("spv_id").copy()
    names    = spv["spv_id"].tolist()
    actual   = (spv["delinquency_rate"] * 100).round(2).tolist()
    limits   = (spv["covenant_max_delinquency_pct"] * 100).round(2).tolist()
    breaches = spv["covenant_delinquency_breach"].astype(bool).tolist()
    headrooms = [round(l - a, 2) for a, l in zip(actual, limits)]

    actual_data = []
    for a, b, h in zip(actual, breaches, headrooms):
        if b:
            color = PALETTE["danger"]
        elif h < 2.0:
            color = PALETTE["amber"]
        else:
            color = PALETTE["primary"]
        actual_data.append({"value": a, "itemStyle": {"color": color}})

    tooltip_fmt = _js(
        "function(params){"
        "var a=params[0]?params[0].value:0, l=params[1]?params[1].value:0;"
        "var h=l-a;"
        "var st=h<0?'🔴 BREACH':h<2?'🟡 WATCH':'✓ OK';"
        "return '<b>'+params[0].name+'</b> '+st+'<br/>'+"
        "params[0].marker+' Delinquency: <strong>'+a.toFixed(2)+'%</strong><br/>'+"
        "'<span style=\"color:#8898aa\">  Limit: '+l.toFixed(2)+'%  |  Headroom: '+(Math.max(h,0)).toFixed(2)+'%</span>';"
        "}"
    )

    return {
        "title": {
            "text": "Delinquency vs Covenant Limit",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
        },
        "tooltip": {"trigger": "axis", "formatter": tooltip_fmt},
        "legend": {"data": ["Actual Delinquency", "Covenant Limit"]},
        "xAxis": {
            "type": "category",
            "data": names,
            "axisLine": {"lineStyle": {"color": "#e4e9f0"}},
            "axisLabel": {"color": "#5c6f85", "fontSize": 12, "fontWeight": "600"},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {
                "formatter": _js("function(v){return v+'%'}"),
                "color": "#8898aa",
            },
            "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
        },
        "series": [
            {
                "name": "Actual Delinquency",
                "type": "bar",
                "data": actual_data,
                "barMaxWidth": 72,
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": _js("function(p){return p.value.toFixed(2)+'%'}"),
                    "color": "#3d4f63",
                    "fontSize": 12,
                    "fontWeight": "700",
                    "fontFamily": "'JetBrains Mono',monospace",
                },
            },
            {
                "name": "Covenant Limit",
                "type": "bar",
                "data": [
                    {"value": v, "itemStyle": {"color": "rgba(148,163,184,0.2)", "borderColor": "#94a3b8", "borderWidth": 1.5}}
                    for v in limits
                ],
                "barMaxWidth": 72,
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": _js("function(p){return p.value.toFixed(1)+'%'}"),
                    "color": "#8898aa",
                    "fontSize": 10,
                },
            },
        ],
        "grid": {"left": 56, "right": 20, "top": 52, "bottom": 40, "containLabel": True},
    }


def covenant_gauge_option(actual: float, limit: float) -> dict:
    """
    Semi-circular gauge: needle at actual delinquency rate vs covenant limit.
    Color segments: green → amber (near limit) → red (breach zone).
    """
    a_pct   = round(actual * 100, 3)
    l_pct   = round(limit  * 100, 3)
    max_val = round(l_pct  * 1.4, 1)

    if actual >= limit:
        needle_color = PALETTE["danger"]
    elif (limit - actual) < 0.02:
        needle_color = PALETTE["amber"]
    else:
        needle_color = PALETTE["success"]

    # Normalised breakpoints for axisLine colorStops
    safe_end  = max(0, (l_pct - 2.0)) / max_val
    warn_end  = l_pct / max_val

    return {
        "animation": True,
        "animationDuration": 800,
        "series": [{
            "type": "gauge",
            "startAngle": 200,
            "endAngle": -20,
            "min": 0,
            "max": max_val,
            "splitNumber": 4,
            "radius": "92%",
            "center": ["50%", "62%"],
            "axisLine": {
                "lineStyle": {
                    "width": 14,
                    "color": [
                        [max(safe_end, 0.01), "#10b981"],
                        [max(warn_end, safe_end + 0.01), "#f59e0b"],
                        [1, "#ef4444"],
                    ],
                }
            },
            "pointer": {
                "length": "52%",
                "width": 5,
                "itemStyle": {"color": needle_color},
            },
            "axisTick": {"show": False},
            "splitLine": {
                "length": 8,
                "lineStyle": {"width": 1, "color": "#e4e9f0"},
            },
            "axisLabel": {
                "distance": 14,
                "color": "#8898aa",
                "fontSize": 9,
                "formatter": _js("function(v){return v.toFixed(0)+'%'}"),
            },
            "detail": {
                "valueAnimation": True,
                "formatter": _js("function(v){return v.toFixed(2)+'%'}"),
                "color": needle_color,
                "fontSize": 16,
                "fontWeight": "700",
                "fontFamily": "'JetBrains Mono',monospace",
                "offsetCenter": [0, "38%"],
            },
            "title": {
                "show": True,
                "offsetCenter": [0, "65%"],
                "color": "#8898aa",
                "fontSize": 9,
                "text": f"/ {limit:.1%} limit",
            },
            "data": [{"value": a_pct, "name": "Delinquency"}],
        }],
    }


def cohort_ranking_option(df: pd.DataFrame, top_n: int | None = None) -> dict:
    """
    Horizontal bar chart with visualMap (green/amber/red) + markLines at 3% and 6%.
    dataZoom inside so all cohorts exist but ~12 show; user scrolls in the chart.
    """
    summary = (
        df.groupby("cohort_label")
        .agg(rate=("cumulative_default_rate", "max"))
        .reset_index()
        .sort_values("rate", ascending=True)  # ascending = worst at top after yAxis flip
    )
    if top_n is not None:
        summary = summary.nlargest(top_n, "rate").sort_values("rate", ascending=True)

    labels = summary["cohort_label"].tolist()
    values = (summary["rate"] * 100).round(3).tolist()
    max_v  = max(values) if values else 20

    return {
        "title": {
            "text": "Peak Default Rate by Cohort",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": _js(
                "function(p){return '<b>'+p[0].name+'</b><br/>Default: <strong>'+p[0].value.toFixed(2)+'%</strong>';}"
            ),
        },
        "visualMap": {
            "type": "piecewise",
            "pieces": [
                {"lt": 3,              "color": "#10b981", "label": "< 3%"},
                {"gte": 3, "lt": 6,    "color": "#f59e0b", "label": "3 – 6%"},
                {"gte": 6,             "color": "#ef4444", "label": "> 6%"},
            ],
            "orient": "horizontal",
            "top": 4, "right": 10,
            "textStyle": {"color": "#8898aa", "fontSize": 10},
            "show": True,
            "dimension": 0,
            "seriesIndex": 0,
            "outOfRange": {"color": "#8898aa"},
        },
        "xAxis": {
            "type": "value",
            "max": round(max_v * 1.15, 1),
            "axisLabel": {
                "formatter": _js("function(v){return v+'%'}"),
                "color": "#8898aa",
                "fontFamily": "'JetBrains Mono',monospace",
            },
            "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
        },
        "yAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": "#5c6f85", "fontSize": 10},
            "axisLine": {"lineStyle": {"color": "#e4e9f0"}},
            "inverse": False,
        },
        "series": [{
            "type": "bar",
            "data": values,
            "barMaxWidth": 18,
            "label": {
                "show": True,
                "position": "right",
                "formatter": _js("function(p){return p.value.toFixed(1)+'%'}"),
                "color": "#3d4f63",
                "fontSize": 10,
                "fontFamily": "'JetBrains Mono',monospace",
            },
            "markLine": {
                "silent": True,
                "symbol": ["none", "none"],
                "data": [
                    {
                        "xAxis": 3,
                        "lineStyle": {"color": "#f59e0b", "type": "dashed", "width": 1.5},
                        "label": {"formatter": "3%", "color": "#f59e0b", "fontSize": 10},
                    },
                    {
                        "xAxis": 6,
                        "lineStyle": {"color": "#ef4444", "type": "dashed", "width": 1.5},
                        "label": {"formatter": "6%", "color": "#ef4444", "fontSize": 10},
                    },
                ],
            },
        }],
        "dataZoom": [
            {
                "type": "inside",
                "yAxisIndex": 0,
                "startValue": max(0, len(labels) - 12),
                "endValue": len(labels) - 1,
            },
            {
                "type": "slider",
                "yAxisIndex": 0,
                "startValue": max(0, len(labels) - 12),
                "endValue": len(labels) - 1,
                "right": 4,
                "width": 16,
                "fillerColor": "rgba(37,99,235,0.1)",
                "borderColor": "#e4e9f0",
            },
        ],
        "grid": {"left": 80, "right": 64, "top": 52, "bottom": 20, "containLabel": False},
    }


def cohort_heatmap_option(df: pd.DataFrame) -> dict:
    """Cumulative default rate heatmap: cohort × months-on-book."""
    df = df.copy()
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    recent_cohorts = (
        df.groupby("cohort_label")["cohort_month"]
        .max().sort_values(ascending=False).head(18).index.tolist()
    )
    df = df[df["cohort_label"].isin(recent_cohorts)]

    pivot = df.pivot_table(
        index="cohort_label",
        columns="months_on_book",
        values="cumulative_default_rate",
        aggfunc="mean",
    ).sort_index(ascending=False)

    cohorts = pivot.index.tolist()
    months  = [int(c) for c in pivot.columns.tolist()]
    data    = []
    for ci, cohort in enumerate(cohorts):
        for mi, month in enumerate(months):
            val = pivot.at[cohort, month]
            if pd.notna(val):
                data.append([mi, ci, round(float(val) * 100, 3)])

    return {
        "title": {
            "text": "Vintage Heatmap — Default Rate by Months on Book",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
        },
        "tooltip": {
            "trigger": "item",
            "formatter": _js(
                "function(p){return 'Cohort: <b>'+p.name+'</b><br/>Month '+p.data[0]+': <strong>'+p.data[2].toFixed(2)+'%</strong>';}"
            ),
        },
        "visualMap": {
            "min": 0, "max": 20,
            "calculable": True,
            "orient": "horizontal",
            "left": "right",
            "top": 4,
            "inRange": {"color": ["#f0fdf4", "#fef9c3", "#fed7aa", "#ef4444"]},
            "textStyle": {"color": "#8898aa", "fontSize": 10},
            "text": ["High", "Low"],
        },
        "xAxis": {
            "type": "category",
            "data": [f"Mo {m}" for m in months],
            "splitArea": {"show": True, "areaStyle": {"color": ["rgba(240,244,248,0.5)", "#fff"]}},
            "axisLabel": {"color": "#8898aa", "fontSize": 9},
        },
        "yAxis": {
            "type": "category",
            "data": cohorts,
            "splitArea": {"show": True, "areaStyle": {"color": ["rgba(240,244,248,0.5)", "#fff"]}},
            "axisLabel": {"color": "#5c6f85", "fontSize": 10},
        },
        "series": [{
            "type": "heatmap",
            "data": data,
            "label": {"show": False},
            "emphasis": {
                "itemStyle": {"shadowBlur": 8, "shadowColor": "rgba(0,0,0,0.3)"},
            },
        }],
        "grid": {"left": 90, "right": 100, "top": 52, "bottom": 24},
    }


def repayment_curves_option(df: pd.DataFrame, cohorts: list[str]) -> dict:
    """Line per cohort showing avg repayment progress (0 → 100%)."""
    filtered = df[df["cohort_label"].isin(cohorts)].copy()
    colors   = _SERIES_COLORS

    series: list[dict] = []
    for i, cohort in enumerate(cohorts):
        cdf = filtered[filtered["cohort_label"] == cohort].sort_values("months_on_book")
        data = [
            [int(row["months_on_book"]), round(float(row["avg_pct_repaid"]) * 100, 2)]
            for _, row in cdf.iterrows()
        ]
        series.append({
            "name": cohort,
            "type": "line",
            "data": data,
            "smooth": True,
            "symbol": "circle",
            "symbolSize": 5,
            "lineStyle": {"width": 2, "color": colors[i % len(colors)]},
            "itemStyle": {"color": colors[i % len(colors)]},
            "markLine": (
                {
                    "silent": True,
                    "symbol": ["none", "none"],
                    "data": [{"yAxis": 100}],
                    "lineStyle": {"type": "dashed", "color": "#10b981", "width": 1, "opacity": 0.6},
                    "label": {
                        "formatter": "Fully repaid",
                        "position": "insideEndTop",
                        "color": "#10b981",
                        "fontSize": 10,
                    },
                }
                if i == 0 else {}
            ),
        })

    return {
        "title": {
            "text": "Repayment Progress by Cohort",
            "textStyle": {"fontSize": 15, "fontWeight": "700", "color": "#060d1f"},
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": _js(
                "function(params){"
                "var h='<b>Month '+params[0].data[0]+'</b><br/>';"
                "params.forEach(function(p){if(p.data&&p.data.length)h+=p.marker+' '+p.seriesName+': <strong>'+p.data[1].toFixed(1)+'%</strong><br/>';});"
                "return h;}"
            ),
        },
        "xAxis": {
            "type": "value",
            "name": "Months on Book",
            "nameTextStyle": {"color": "#8898aa"},
            "axisLabel": {"color": "#8898aa"},
            "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
        },
        "yAxis": {
            "type": "value",
            "min": 0, "max": 115,
            "axisLabel": {
                "formatter": _js("function(v){return v+'%'}"),
                "color": "#8898aa",
            },
            "splitLine": {"lineStyle": {"color": "#eaeff5", "type": "dashed"}},
        },
        "series": series,
    }


def recon_ring_option(passed: int, total: int) -> dict:
    """Ring gauge showing N/total checks passed — green ring on full PASS, red on FAIL."""
    pct   = (passed / total * 100) if total else 0
    color = PALETTE["success"] if passed == total else PALETTE["danger"]
    label = "PASSED" if passed == total else "FAILED"

    return {
        "animation": True,
        "animationDuration": 1200,
        "animationEasing": "elasticOut",
        "series": [{
            "type": "gauge",
            "startAngle": 90,
            "endAngle": -270,
            "radius": "78%",
            "pointer": {"show": False},
            "progress": {
                "show": True,
                "overlap": False,
                "roundCap": True,
                "clip": False,
                "itemStyle": {"color": color},
            },
            "axisLine": {
                "lineStyle": {"width": 18, "color": [[1, "rgba(228,233,240,0.7)"]]}
            },
            "splitLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {"show": False},
            "data": [{"value": pct}],
            "detail": {
                "valueAnimation": True,
                "formatter": _js(
                    f"function(){{return '{passed}/{total}\\n{label}';}}"
                ),
                "color": color,
                "fontSize": 22,
                "fontWeight": "800",
                "lineHeight": 30,
                "fontFamily": "Inter, sans-serif",
                "offsetCenter": [0, 0],
            },
        }],
    }
