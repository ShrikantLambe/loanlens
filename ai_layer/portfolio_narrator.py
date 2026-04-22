"""
portfolio_narrator.py — Calls Claude to generate investor-grade portfolio commentary.

The narrator reads rpt_portfolio_summary and fct_portfolio_daily and returns
structured JSON with executive_summary, risk_flags, sentiment, and more.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import anthropic


class _SafeEncoder(json.JSONEncoder):
    """Serialize pandas Timestamps, numpy types, and dates to plain strings."""
    def default(self, obj):
        try:
            return obj.isoformat()          # Timestamp, date, datetime
        except AttributeError:
            pass
        try:
            return obj.item()               # numpy scalar → Python scalar
        except AttributeError:
            pass
        return str(obj)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "portfolio_summary.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text()

MODEL = "claude-sonnet-4-20250514"


def generate_portfolio_commentary(
    summary: dict,
    recent_trend: list[dict],
    spv_data: list[dict],
    covenant_breaches: list[dict],
    prior_commentary: Optional[str] = None,
) -> dict:
    """
    Call Claude to generate structured investor-ready portfolio commentary.

    Args:
        summary: Single-row dict from rpt_portfolio_summary.
        recent_trend: List of daily rows from fct_portfolio_daily (last 30–90 days).
        spv_data: List of rows from fct_spv_allocation.
        covenant_breaches: Subset of spv_data where covenant_delinquency_breach = True.
        prior_commentary: Optional previous commentary for continuity context.

    Returns:
        Dict with keys: executive_summary, key_metrics_narrative, risk_flags,
        cohort_observations, recommended_actions, sentiment.
    """
    client = anthropic.Anthropic()

    breach_text = json.dumps(covenant_breaches) if covenant_breaches else "None detected."

    user_message = f"""
Here is the current portfolio data. Generate investor-grade commentary.

PORTFOLIO SUMMARY (as of {summary.get('report_date', 'N/A')}):
- Total loans originated: {summary.get('total_loans', 0):,}
- Outstanding principal: ${summary.get('outstanding_principal', 0):,.0f}
- Delinquency rate: {summary.get('delinquency_rate_pct', 0)}%
- Default rate: {summary.get('default_rate_pct', 0)}%
- Avg underwriting score: {summary.get('avg_underwriting_score', 0)}
- Current loans: {summary.get('current_loans', 0):,}
- Defaulted loans: {summary.get('defaulted_loans', 0):,}
- Paid off loans: {summary.get('paid_off_loans', 0):,}

30-DAY TREND (delinquency rate, most recent last):
{json.dumps([round(float(r.get('delinquency_rate', 0)), 4) for r in recent_trend[-30:]])}

SPV STATUS:
{json.dumps(spv_data, indent=2, cls=_SafeEncoder)}

COVENANT BREACHES:
{breach_text}

Respond ONLY with a JSON object. No preamble, no markdown.
Schema: {{
  "executive_summary": "string (2-3 sentences, board-level)",
  "key_metrics_narrative": "string (paragraph discussing originations, yield, delinquency trend)",
  "risk_flags": ["list of strings, each a specific risk observation"],
  "cohort_observations": "string (paragraph on cohort performance trends)",
  "recommended_actions": ["list of strings, each an actionable recommendation"],
  "sentiment": "positive | cautious | concerning"
}}
"""

    logger.info("Calling Claude for portfolio commentary (model=%s)...", MODEL)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    logger.info("Commentary generated. Input tokens=%d", response.usage.input_tokens)
    return json.loads(raw)
