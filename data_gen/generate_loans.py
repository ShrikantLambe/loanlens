"""
generate_loans.py — Generates synthetic loan tape (10,000 rows).

Run directly:  python data_gen/generate_loans.py
Or import:     from data_gen.generate_loans import generate_loans
"""

import logging
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "output"

# Platform distribution: 60% DoorDash, 20% Amazon, 10% Mindbody, 5% WorldPay, 5% Shopify
PLATFORMS = ["doordash", "amazon", "mindbody", "worldpay", "shopify"]
PLATFORM_WEIGHTS = [0.60, 0.20, 0.10, 0.05, 0.05]

REPAYMENT_TYPES = ["daily_revenue_share", "fixed_daily", "weekly"]
TERM_DAYS = [90, 180, 270, 365]


def _origination_date_sample(n: int, start: date, end: date) -> list[date]:
    """Sample origination dates with 8% MoM growth trend."""
    total_days = (end - start).days
    # Build month-level weights with 8% MoM growth
    months = []
    d = date(start.year, start.month, 1)
    while d <= end:
        months.append(d)
        # Advance month
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)

    raw_weights = np.array([1.08 ** i for i in range(len(months))])
    raw_weights /= raw_weights.sum()

    # Assign each sample to a month, then pick a random day within that month
    month_choices = np.random.choice(len(months), size=n, p=raw_weights)
    dates = []
    for idx in month_choices:
        m_start = months[idx]
        if m_start.month == 12:
            m_end = date(m_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            m_end = date(m_start.year, m_start.month + 1, 1) - timedelta(days=1)
        m_end = min(m_end, end)
        day_range = (m_end - m_start).days
        offset = np.random.randint(0, max(day_range, 1))
        dates.append(m_start + timedelta(days=int(offset)))
    return dates


def _assign_spv(row: pd.Series) -> str:
    """SPV-A: <$25K pre-2023-07-01; SPV-B: $25K–$75K; SPV-C: >$75K or post-2023-07-01."""
    cutoff = date(2023, 7, 1)
    if row["origination_date"] >= cutoff or row["principal_amount"] > 75_000:
        return "SPV-C"
    elif row["principal_amount"] <= 25_000:
        return "SPV-A"
    else:
        return "SPV-B"


def generate_loans(n: int = 10_000) -> pd.DataFrame:
    """
    Generate a synthetic loan tape with realistic distributions.

    Args:
        n: Number of loans to generate.

    Returns:
        DataFrame with loan tape schema.
    """
    logger.info("Generating %d loans...", n)

    start_date = date(2022, 1, 1)
    end_date = date(2024, 12, 31)

    origination_dates = _origination_date_sample(n, start_date, end_date)

    platforms = np.random.choice(PLATFORMS, size=n, p=PLATFORM_WEIGHTS)

    # Principal: $2,500–$150,000 rounded to nearest $500
    raw_principal = np.random.uniform(2_500, 150_000, size=n)
    principal = (np.round(raw_principal / 500) * 500).clip(2_500, 150_000)

    # Factor rate: 1.10–1.45
    factor_rates = np.round(np.random.uniform(1.10, 1.45, size=n), 4)

    # Underwriting score: 1–100
    uw_scores = np.random.randint(1, 101, size=n)

    # Repayment type
    repayment_types = np.random.choice(REPAYMENT_TYPES, size=n, p=[0.50, 0.35, 0.15])

    # Revenue share pct (only for daily_revenue_share loans)
    revenue_share = np.where(
        repayment_types == "daily_revenue_share",
        np.round(np.random.uniform(5.0, 20.0, size=n), 2),
        np.nan,
    )

    term_days = np.random.choice(TERM_DAYS, size=n)

    df = pd.DataFrame(
        {
            "loan_id": [str(uuid.uuid4()) for _ in range(n)],
            "merchant_id": [str(uuid.uuid4()) for _ in range(n)],
            "platform": platforms,
            "origination_date": origination_dates,
            "principal_amount": principal,
            "term_days": term_days,
            "factor_rate": factor_rates,
            "repayment_type": repayment_types,
            "revenue_share_pct": revenue_share,
            "underwriting_score": uw_scores,
        }
    )

    # Assign SPV
    df["spv_id"] = df.apply(_assign_spv, axis=1)

    # Status placeholder (will be recalculated in dbt)
    df["status"] = "current"

    logger.info("Loans generated. Shape: %s", df.shape)
    return df


def main() -> None:
    """Write loans.csv to data_gen/output/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_loans()
    out_path = OUTPUT_DIR / "loans.csv"
    df.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(df), out_path)


if __name__ == "__main__":
    main()
