"""
demo_commentary.py — Pre-built realistic mock responses for demo / API-unavailable mode.

Used when the Anthropic API is unreachable or over quota. Commentary is written
to reflect plausible portfolio conditions so the demo remains meaningful.
"""

from datetime import date


def demo_portfolio_commentary(summary: dict) -> dict:
    """
    Return a realistic mock commentary dict matching the portfolio_narrator schema.

    Args:
        summary: Single-row dict from rpt_portfolio_summary (used to inject real numbers).

    Returns:
        Dict with the same keys as generate_portfolio_commentary().
    """
    total = summary.get("total_loans", 10000)
    principal = summary.get("outstanding_principal", 85_000_000)
    delinq = summary.get("delinquency_rate_pct", 4.2)
    default = summary.get("default_rate_pct", 3.1)
    score = summary.get("avg_underwriting_score", 68.4)

    if delinq > 10 or default > 8:
        sentiment = "concerning"
    elif delinq > 5 or default > 4:
        sentiment = "cautious"
    else:
        sentiment = "positive"

    return {
        "executive_summary": (
            f"The portfolio of {total:,} originated loans maintains ${principal:,.0f} "
            f"in outstanding principal as of {summary.get('report_date', date.today())}. "
            f"Delinquency stands at {delinq:.2f}%, {'approaching' if delinq > 6 else 'within'} "
            f"facility covenant thresholds. "
            f"The average underwriting score of {score:.1f} reflects a "
            f"{'below-median' if score < 50 else 'moderate'} risk cohort."
        ),
        "key_metrics_narrative": (
            f"Origination volume has grown consistently since portfolio inception, driven "
            f"primarily by DoorDash merchants (60% of book). The weighted-average factor "
            f"rate of approximately 1.28 implies a gross yield well above the 18–22% "
            f"covenant minimums across all three SPV facilities. "
            f"Total collected repayments are tracking ahead of schedule for 2022–2023 "
            f"vintages, though 2024 cohorts remain in early repayment phases. "
            f"The {delinq:.2f}% delinquency rate reflects {'elevated stress' if delinq > 8 else 'manageable levels'} "
            f"in the daily revenue-share segment, where payment variance is highest."
        ),
        "risk_flags": [
            f"Delinquency rate of {delinq:.2f}% exceeds 6% covenant threshold on SPV-C."
            if delinq > 6 else
            f"Delinquency at {delinq:.2f}% — monitor weekly for covenant headroom on SPV-C (6% limit).",
            "SPV-C facility utilization materially exceeds 100%; additional originations require new facility capacity.",
            f"Underwriting score concentration below 50 ({100 - int(score)}% of book) warrants tighter origination criteria.",
            "DoorDash revenue-share dependency creates platform concentration risk — single-platform events could spike DPD.",
        ],
        "cohort_observations": (
            "Early 2022 cohorts (MV-2022-01 through MV-2022-06) have largely seasoned, "
            "with repayment rates above 90% and default curves plateauing at current levels. "
            "Mid-2023 cohorts are performing in line with underwriting projections, showing "
            "stable 12-month cumulative default rates. The 2024 vintage is too early to assess "
            "definitively, but months 1–4 loss emergence is consistent with prior cohorts at "
            "equivalent seasoning. No structural deterioration in cohort performance is evident."
        ),
        "recommended_actions": [
            "Increase SPV-C delinquency monitoring to daily frequency given covenant proximity.",
            "Initiate conversations with Bessemer Ventures to expand SPV-C facility limit or establish SPV-D.",
            "Apply a temporary 10-point underwriting score floor to reduce new origination risk concentration.",
            "Conduct DoorDash platform revenue stress test: model portfolio impact of a 20% GMV decline.",
            "Prepare covenant cure notice template for SPV-C to reduce response latency if breach is confirmed.",
        ],
        "sentiment": sentiment,
    }


def demo_anomalies(spv_data: list[dict]) -> list[dict]:
    """
    Return realistic mock anomaly flags for demo mode.

    Args:
        spv_data: List of SPV rows from fct_spv_allocation.

    Returns:
        List of anomaly dicts matching the anomaly_agent schema.
    """
    anomalies = []

    for spv in spv_data:
        spv_id = spv.get("spv_id", "")
        delinq = float(spv.get("delinquency_rate", 0))
        limit = float(spv.get("covenant_max_delinquency_pct", 0.08))
        util = float(spv.get("facility_utilization", 0))

        if delinq > limit:
            anomalies.append({
                "anomaly_type": "covenant_breach_risk",
                "severity": "critical" if delinq > limit * 1.5 else "high",
                "description": (
                    f"{spv_id} delinquency rate ({delinq:.2%}) exceeds covenant maximum "
                    f"({limit:.2%}) by {(delinq - limit) * 100:.1f}pp."
                ),
                "affected_entity": spv_id,
                "detected_date": str(date.today()),
                "recommended_action": (
                    f"Notify {spv.get('facility_name', spv_id)} lender immediately. "
                    f"Halt new originations into {spv_id} pending cure plan."
                ),
            })

        if util > 0.90:
            anomalies.append({
                "anomaly_type": "origination_drop",
                "severity": "medium",
                "description": (
                    f"{spv_id} facility utilization at {util:.1%} — "
                    f"headroom of ${float(spv.get('facility_limit', 0)) * (1 - util):,.0f} remaining."
                ),
                "affected_entity": spv_id,
                "detected_date": str(date.today()),
                "recommended_action": (
                    f"Pause new {spv_id} allocations until facility expansion is confirmed "
                    f"or utilization decreases through repayments."
                ),
            })

    return anomalies
