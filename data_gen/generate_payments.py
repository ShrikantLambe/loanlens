"""
generate_payments.py — Generates synthetic payment events (~180,000 rows).

Simulation rules:
  88% pay on schedule with minor variance
   7% go 30+ DPD at some point but eventually cure
   5% default (stop paying after 40–70% repaid)
   ~3% prepay early (full payoff before term)

Run directly:  python data_gen/generate_payments.py
Or import:     from data_gen.generate_payments import generate_payments
"""

import logging
import uuid
from datetime import date, timedelta
from pathlib import Path

import sys
from pathlib import Path as _Path

# Ensure the project root (loanlens/) is on sys.path when run directly
sys.path.insert(0, str(_Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from data_gen.generate_loans import generate_loans

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "output"


def _simulate_loan_payments(loan: pd.Series) -> list[dict]:
    """
    Simulate payment events for a single loan.

    Args:
        loan: A row from the loans DataFrame.

    Returns:
        List of payment event dicts.
    """
    loan_id = loan["loan_id"]
    origination_date: date = loan["origination_date"]
    if isinstance(origination_date, str):
        origination_date = date.fromisoformat(origination_date)

    principal = float(loan["principal_amount"])
    factor_rate = float(loan["factor_rate"])
    term_days = int(loan["term_days"])
    repayment_type = loan["repayment_type"]

    total_owed = principal * factor_rate
    uw_score = int(loan["underwriting_score"])

    # Determine loan behaviour bucket
    rand = np.random.random()
    if uw_score < 40:
        default_prob, delinquent_prob, prepay_prob = 0.12, 0.10, 0.02
    elif uw_score > 70:
        default_prob, delinquent_prob, prepay_prob = 0.02, 0.05, 0.04
    else:
        default_prob, delinquent_prob, prepay_prob = 0.05, 0.07, 0.03

    if rand < default_prob:
        behaviour = "default"
    elif rand < default_prob + delinquent_prob:
        behaviour = "delinquent_cure"
    elif rand < default_prob + delinquent_prob + prepay_prob:
        behaviour = "prepay"
    else:
        behaviour = "current"

    # Build payment schedule based on repayment type
    if repayment_type == "daily_revenue_share" or repayment_type == "fixed_daily":
        payment_interval = 1  # daily
    elif repayment_type == "weekly":
        payment_interval = 7
    else:
        payment_interval = 1

    payment_dates = []
    d = origination_date + timedelta(days=payment_interval)
    today = date(2025, 1, 1)  # simulate up to end of 2024
    end_date = origination_date + timedelta(days=term_days)
    while d <= min(end_date, today):
        payment_dates.append(d)
        d += timedelta(days=payment_interval)

    if not payment_dates:
        return []

    # Spread total_owed evenly across payment dates
    n_payments = len(payment_dates)
    base_payment = total_owed / n_payments

    events = []
    cumulative_repaid = 0.0

    if behaviour == "prepay":
        # Full payoff at 40–70% through the term
        prepay_idx = int(n_payments * np.random.uniform(0.40, 0.70))
        for i, pmt_date in enumerate(payment_dates[:prepay_idx]):
            variance = np.random.uniform(0.92, 1.08)
            amount = round(base_payment * variance, 2)
            cumulative_repaid += amount
            events.append({
                "payment_id": str(uuid.uuid4()),
                "loan_id": loan_id,
                "payment_date": pmt_date,
                "payment_amount": amount,
                "payment_type": "scheduled",
                "days_past_due": 0,
                "cumulative_repaid": round(cumulative_repaid, 2),
            })
        # Early payoff event
        remaining = max(total_owed - cumulative_repaid, 0.0)
        cumulative_repaid += remaining
        events.append({
            "payment_id": str(uuid.uuid4()),
            "loan_id": loan_id,
            "payment_date": payment_dates[prepay_idx],
            "payment_amount": round(remaining, 2),
            "payment_type": "early_payoff",
            "days_past_due": 0,
            "cumulative_repaid": round(cumulative_repaid, 2),
        })

    elif behaviour == "default":
        # Stop paying after 40–70% repaid
        default_idx = int(n_payments * np.random.uniform(0.40, 0.70))
        for i, pmt_date in enumerate(payment_dates[:default_idx]):
            variance = np.random.uniform(0.90, 1.10)
            amount = round(base_payment * variance, 2)
            cumulative_repaid += amount
            events.append({
                "payment_id": str(uuid.uuid4()),
                "loan_id": loan_id,
                "payment_date": pmt_date,
                "payment_amount": amount,
                "payment_type": "scheduled",
                "days_past_due": 0,
                "cumulative_repaid": round(cumulative_repaid, 2),
            })
        # Missed payments from default point
        dpd = 0
        for pmt_date in payment_dates[default_idx:default_idx + 5]:
            dpd += payment_interval
            events.append({
                "payment_id": str(uuid.uuid4()),
                "loan_id": loan_id,
                "payment_date": pmt_date,
                "payment_amount": 0.0,
                "payment_type": "missed",
                "days_past_due": dpd,
                "cumulative_repaid": round(cumulative_repaid, 2),
            })

    elif behaviour == "delinquent_cure":
        # Go 30–90 DPD at some mid-point, then cure
        delinquent_start = int(n_payments * np.random.uniform(0.20, 0.60))
        delinquent_length = np.random.randint(2, 6)
        dpd_accumulator = 0
        for i, pmt_date in enumerate(payment_dates):
            if delinquent_start <= i < delinquent_start + delinquent_length:
                dpd_accumulator += payment_interval
                events.append({
                    "payment_id": str(uuid.uuid4()),
                    "loan_id": loan_id,
                    "payment_date": pmt_date,
                    "payment_amount": 0.0,
                    "payment_type": "missed",
                    "days_past_due": dpd_accumulator,
                    "cumulative_repaid": round(cumulative_repaid, 2),
                })
            else:
                variance = np.random.uniform(0.92, 1.08)
                amount = round(base_payment * variance, 2)
                cumulative_repaid += amount
                events.append({
                    "payment_id": str(uuid.uuid4()),
                    "loan_id": loan_id,
                    "payment_date": pmt_date,
                    "payment_amount": amount,
                    "payment_type": "scheduled",
                    "days_past_due": 0,
                    "cumulative_repaid": round(cumulative_repaid, 2),
                })

    else:  # current — on schedule with minor variance
        for pmt_date in payment_dates:
            variance = np.random.uniform(0.95, 1.05)
            amount = round(base_payment * variance, 2)
            cumulative_repaid += amount
            events.append({
                "payment_id": str(uuid.uuid4()),
                "loan_id": loan_id,
                "payment_date": pmt_date,
                "payment_amount": amount,
                "payment_type": "scheduled",
                "days_past_due": 0,
                "cumulative_repaid": round(cumulative_repaid, 2),
            })

    return events


def generate_payments(loans: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate payment events for all loans.

    Args:
        loans: DataFrame from generate_loans().

    Returns:
        DataFrame of payment events.
    """
    logger.info("Simulating payments for %d loans...", len(loans))
    all_events: list[dict] = []
    for _, loan in loans.iterrows():
        all_events.extend(_simulate_loan_payments(loan))

    df = pd.DataFrame(all_events)
    logger.info("Generated %d payment events.", len(df))
    return df


def main() -> None:
    """Write payments.csv to data_gen/output/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loans_path = OUTPUT_DIR / "loans.csv"
    if not loans_path.exists():
        from data_gen.generate_loans import main as gen_loans
        gen_loans()
    loans = pd.read_csv(loans_path)
    loans["origination_date"] = pd.to_datetime(loans["origination_date"]).dt.date
    df = generate_payments(loans)
    out_path = OUTPUT_DIR / "payments.csv"
    df.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(df), out_path)


if __name__ == "__main__":
    main()
