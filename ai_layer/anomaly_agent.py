"""
anomaly_agent.py — Calls Claude to detect anomalies in portfolio time-series data.

Returns a list of flagged anomalies with severity, description, affected entity,
and recommended action. Returns empty list if no anomalies are detected.
"""

import json
import logging
from pathlib import Path

import anthropic


class _SafeEncoder(json.JSONEncoder):
    """Serialize pandas Timestamps, numpy types, and dates to plain strings."""
    def default(self, obj):
        try:
            return obj.isoformat()
        except AttributeError:
            pass
        try:
            return obj.item()
        except AttributeError:
            pass
        return str(obj)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "anomaly_detection.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

MODEL = "claude-sonnet-4-20250514"


def detect_anomalies(
    daily_data: list[dict],
    spv_data: list[dict],
) -> list[dict]:
    """
    Call Claude to identify anomalies in portfolio time-series and SPV data.

    Args:
        daily_data: List of daily rows from fct_portfolio_daily (last 60+ days).
        spv_data: List of rows from fct_spv_allocation.

    Returns:
        List of anomaly dicts, each with:
          anomaly_type, severity, description, affected_entity,
          detected_date, recommended_action.
        Empty list if no anomalies detected.
    """
    client = anthropic.Anthropic()

    user_message = f"""
Analyze the following portfolio time series and SPV data.
Identify any anomalies, sudden changes, or covenant breach risks.

DAILY DELINQUENCY RATES (last 60 days, most recent last):
{json.dumps([
    {"date": str(r.get("date_day", "")), "rate": round(float(r.get("delinquency_rate", 0)), 4)}
    for r in daily_data[-60:]
])}

DAILY DEFAULT RATES (last 60 days):
{json.dumps([
    {"date": str(r.get("date_day", "")), "rate": round(float(r.get("default_rate", 0)), 4)}
    for r in daily_data[-60:]
])}

SPV COVENANT STATUS:
{json.dumps(spv_data, indent=2, cls=_SafeEncoder)}

Return ONLY a JSON array. Each item:
{{
  "anomaly_type": "delinquency_spike | covenant_breach_risk | origination_drop | default_cluster",
  "severity": "low | medium | high | critical",
  "description": "string",
  "affected_entity": "string (e.g. SPV-B or platform name or 'portfolio')",
  "detected_date": "YYYY-MM-DD",
  "recommended_action": "string"
}}

If no anomalies detected, return an empty array [].
"""

    logger.info("Calling Claude for anomaly detection (model=%s)...", MODEL)
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    logger.info("Anomaly detection complete. Input tokens=%d", response.usage.input_tokens)
    result = json.loads(raw)
    return result if isinstance(result, list) else []
