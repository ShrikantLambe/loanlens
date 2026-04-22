"""
memo_generator.py — Assembles AI output + structured data into an investor memo dict.

The memo dict is both rendered in Streamlit and exported as a PDF via WeasyPrint.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def build_memo(
    commentary: dict,
    anomalies: list[dict],
    summary: dict,
    spv_data: list[dict],
) -> dict[str, Any]:
    """
    Assemble AI commentary, anomaly flags, and portfolio data into a memo dict.

    Args:
        commentary: Output from portfolio_narrator.generate_portfolio_commentary().
        anomalies: Output from anomaly_agent.detect_anomalies().
        summary: Single-row dict from rpt_portfolio_summary.
        spv_data: List of rows from fct_spv_allocation.

    Returns:
        Structured memo dict ready for Streamlit rendering and PDF export.
    """
    high_severity_anomalies = [
        a["description"]
        for a in anomalies
        if a.get("severity") in ("high", "critical")
    ]

    covenant_status = [
        {
            "spv": s.get("spv_id", ""),
            "facility_name": s.get("facility_name", ""),
            "status": "BREACH" if s.get("covenant_delinquency_breach") else "OK",
            "delinquency_rate": s.get("delinquency_rate", 0),
            "limit": s.get("covenant_max_delinquency_pct", 0),
            "facility_utilization": s.get("facility_utilization", 0),
        }
        for s in spv_data
    ]

    memo = {
        "title": "Portfolio Performance Memo",
        "period": f"As of {summary.get('report_date', 'N/A')}",
        "executive_summary": commentary.get("executive_summary", ""),
        "sentiment": commentary.get("sentiment", "cautious"),
        "key_metrics": {
            "total_originated": summary.get("total_loans", 0),
            "outstanding_principal": summary.get("outstanding_principal", 0),
            "delinquency_rate": summary.get("delinquency_rate_pct", 0),
            "default_rate": summary.get("default_rate_pct", 0),
            "avg_underwriting_score": summary.get("avg_underwriting_score", 0),
            "paid_off_loans": summary.get("paid_off_loans", 0),
        },
        "narrative": commentary.get("key_metrics_narrative", ""),
        "risk_flags": commentary.get("risk_flags", []) + high_severity_anomalies,
        "cohort_observations": commentary.get("cohort_observations", ""),
        "recommended_actions": commentary.get("recommended_actions", []),
        "spv_summary": spv_data,
        "covenant_status": covenant_status,
        "anomalies": anomalies,
        "generated_at": datetime.now().isoformat(),
        "model_used": "claude-sonnet-4-20250514",
        "disclaimer": (
            "This report is generated from synthetic data for portfolio "
            "demonstration purposes only. Not for distribution."
        ),
    }

    logger.info(
        "Memo built. Sentiment=%s, risk_flags=%d, anomalies=%d",
        memo["sentiment"],
        len(memo["risk_flags"]),
        len(anomalies),
    )
    return memo


def memo_to_html(memo: dict[str, Any]) -> str:
    """
    Render a memo dict to an HTML string for WeasyPrint PDF export.

    Args:
        memo: Output from build_memo().

    Returns:
        HTML string suitable for WeasyPrint.
    """
    sentiment_color = {
        "positive": "#16a34a",
        "cautious": "#d97706",
        "concerning": "#dc2626",
    }.get(memo["sentiment"], "#6b7280")

    risk_flags_html = "".join(f"<li>{f}</li>" for f in memo["risk_flags"])
    actions_html = "".join(f"<li>{a}</li>" for a in memo["recommended_actions"])

    covenant_rows = "".join(
        f"""<tr>
            <td>{c['spv']}</td>
            <td>{c['facility_name']}</td>
            <td style="color: {'#dc2626' if c['status'] == 'BREACH' else '#16a34a'}; font-weight: bold;">{c['status']}</td>
            <td>{c['delinquency_rate']:.2%}</td>
            <td>{c['limit']:.2%}</td>
            <td>{c['facility_utilization']:.1%}</td>
        </tr>"""
        for c in memo["covenant_status"]
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt;
          color: #111; margin: 40px; line-height: 1.5; }}
  h1 {{ font-size: 18pt; border-bottom: 2px solid #111; padding-bottom: 6px; }}
  h2 {{ font-size: 13pt; margin-top: 24px; color: #1e3a5f; }}
  .meta {{ color: #555; font-size: 9pt; margin-bottom: 20px; }}
  .sentiment {{ display: inline-block; padding: 3px 10px; border-radius: 4px;
                color: white; background: {sentiment_color}; font-weight: bold;
                font-size: 10pt; text-transform: uppercase; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
                   margin: 16px 0; }}
  .metric-card {{ border: 1px solid #ddd; padding: 10px; border-radius: 4px; }}
  .metric-label {{ font-size: 8pt; color: #777; text-transform: uppercase; }}
  .metric-value {{ font-size: 16pt; font-weight: bold; color: #1e3a5f; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10pt; }}
  th {{ background: #1e3a5f; color: white; padding: 6px 8px; text-align: left; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #eee; }}
  ul {{ margin: 8px 0; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  .disclaimer {{ font-size: 8pt; color: #999; margin-top: 40px;
                 border-top: 1px solid #eee; padding-top: 8px; }}
</style>
</head>
<body>
<h1>{memo['title']}</h1>
<div class="meta">
  {memo['period']} &nbsp;|&nbsp;
  Generated: {memo['generated_at'][:19]} &nbsp;|&nbsp;
  Model: {memo['model_used']} &nbsp;|&nbsp;
  Sentiment: <span class="sentiment">{memo['sentiment']}</span>
</div>

<h2>Executive Summary</h2>
<p>{memo['executive_summary']}</p>

<h2>Key Metrics</h2>
<div class="metrics-grid">
  <div class="metric-card">
    <div class="metric-label">Total Loans Originated</div>
    <div class="metric-value">{memo['key_metrics']['total_originated']:,}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Outstanding Principal</div>
    <div class="metric-value">${memo['key_metrics']['outstanding_principal']:,.0f}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Delinquency Rate</div>
    <div class="metric-value">{memo['key_metrics']['delinquency_rate']:.2f}%</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Default Rate</div>
    <div class="metric-value">{memo['key_metrics']['default_rate']:.2f}%</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Avg Underwriting Score</div>
    <div class="metric-value">{memo['key_metrics']['avg_underwriting_score']:.1f}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Paid Off Loans</div>
    <div class="metric-value">{memo['key_metrics']['paid_off_loans']:,}</div>
  </div>
</div>

<h2>Portfolio Narrative</h2>
<p>{memo['narrative']}</p>

<h2>Cohort Observations</h2>
<p>{memo['cohort_observations']}</p>

<h2>Risk Flags</h2>
<ul>{risk_flags_html or '<li>No material risk flags identified.</li>'}</ul>

<h2>Recommended Actions</h2>
<ul>{actions_html or '<li>No actions required at this time.</li>'}</ul>

<h2>SPV Covenant Status</h2>
<table>
  <thead>
    <tr>
      <th>SPV</th><th>Facility</th><th>Status</th>
      <th>Delinquency Rate</th><th>Covenant Limit</th><th>Utilization</th>
    </tr>
  </thead>
  <tbody>{covenant_rows}</tbody>
</table>

<div class="disclaimer">{memo['disclaimer']}</div>
</body>
</html>"""
    return html
