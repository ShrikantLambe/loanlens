"""
generate_payments.py — Generates synthetic payment events (~180K rows).

Key fix vs previous version:
  - DPD was previously incremented by payment_interval (1 for daily, 7 for weekly).
    After 5 missed payments that reached only DPD=5 or DPD=35, never crossing
    the 90-DPD threshold in int_loan_status. Every "default" loan was silently
    classified as delinquent_30 or current. Zero defaults resulted.
  - Fix: DPD is now computed as calendar days since first missed payment, using
    three explicit missed-payment snapshots at 30, 60, and 90 DPD. Default loans
    now reliably cross the 90-DPD threshold.

  - SPV-level probability multipliers added so SPV-A stays within its covenant
    limit (~7% delinquency, 8% limit) while SPV-B and SPV-C breach theirs.

  - Vintage stress factor: 2022-H1 loans are 1.3× more likely to default/delinquent
    (macro stress narrative). 2024 loans that originate too late to accumulate 90 DPD
    before sim_end naturally produce lower default rates, creating realistic cohort curves.

Simulation targets (derived from probability tuning):
  Portfolio default rate        ~4-5%
  Portfolio delinquency rate    ~10-11%
  SPV-A delinquency             ~7%  (within 8% covenant)
  SPV-B delinquency             ~10% (over 7% covenant — breach)
  SPV-C delinquency             ~14% (over 6% covenant — severe breach)
  Cohort curves                 2022 vintages fully developed (~5-7%), 2024 early-stage

Run directly:  python data_gen/generate_payments.py
Or import:     from data_gen.generate_payments import generate_payments
"""

import logging
import uuid
from datetime import date, timedelta
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from data_gen.generate_loans import generate_loans

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "output"
SIM_END    = date(2025, 1, 1)   # simulation horizon


def _behaviour_probs(loan: pd.Series) -> tuple[float, float, float]:
    """
    Return (default_prob, delinquent_prob, prepay_prob) for a loan.

    Adjustments applied on top of UW-score base rates:
    - SPV multiplier   : SPV-A is lower risk; SPV-C is higher risk
    - Vintage stress   : 2022-H1 loans face macro stress (1.3×)
    """
    uw = int(loan["underwriting_score"])
    if uw < 40:
        base_d, base_q, base_p = 0.12, 0.10, 0.02
    elif uw > 70:
        base_d, base_q, base_p = 0.02, 0.05, 0.04
    else:
        base_d, base_q, base_p = 0.04, 0.09, 0.03

    # SPV-based multipliers (drives per-facility delinquency rates)
    spv = str(loan.get("spv_id", "SPV-B"))
    spv_d_mult = {"SPV-A": 0.80, "SPV-B": 1.00, "SPV-C": 1.40}.get(spv, 1.00)
    spv_q_mult = {"SPV-A": 0.70, "SPV-B": 1.10, "SPV-C": 1.60}.get(spv, 1.00)

    # Vintage stress: 2022-H1 loans are 30% more likely to have credit events
    orig = loan["origination_date"]
    if isinstance(orig, str):
        orig = date.fromisoformat(orig)
    vintage_stress = 1.30 if (orig.year == 2022 and orig.month <= 6) else 1.00

    default_prob    = min(base_d * spv_d_mult * vintage_stress, 0.30)
    delinquent_prob = min(base_q * spv_q_mult * vintage_stress, 0.35)
    prepay_prob     = base_p

    return default_prob, delinquent_prob, prepay_prob


def _simulate_loan_payments(loan: pd.Series) -> list[dict]:
    """
    Simulate payment events for a single loan.

    Args:
        loan: A row from the loans DataFrame.

    Returns:
        List of payment event dicts.
    """
    loan_id    = loan["loan_id"]
    orig_date  = loan["origination_date"]
    if isinstance(orig_date, str):
        orig_date = date.fromisoformat(orig_date)

    principal     = float(loan["principal_amount"])
    factor_rate   = float(loan["factor_rate"])
    term_days     = int(loan["term_days"])
    repayment_type = loan["repayment_type"]

    total_owed = principal * factor_rate

    default_prob, delinquent_prob, prepay_prob = _behaviour_probs(loan)

    rand = np.random.random()
    if rand < default_prob:
        behaviour = "default"
    elif rand < default_prob + delinquent_prob:
        behaviour = "delinquent_cure"
    elif rand < default_prob + delinquent_prob + prepay_prob:
        behaviour = "prepay"
    else:
        behaviour = "current"

    # Payment interval
    payment_interval = 7 if repayment_type == "weekly" else 1

    # Build scheduled payment dates up to min(term end, SIM_END)
    payment_dates: list[date] = []
    d        = orig_date + timedelta(days=payment_interval)
    term_end = orig_date + timedelta(days=term_days)
    while d <= min(term_end, SIM_END):
        payment_dates.append(d)
        d += timedelta(days=payment_interval)

    if not payment_dates:
        return []

    n_payments  = len(payment_dates)
    base_pmt    = total_owed / n_payments
    events: list[dict] = []
    cum_repaid  = 0.0

    # ── helpers ─────────────────────────────────────────────────────────────

    def _normal_pmt(pmt_date: date, variance: float = 0.03) -> dict:
        nonlocal cum_repaid
        amt = round(base_pmt * np.random.uniform(1 - variance, 1 + variance), 2)
        cum_repaid += amt
        return {
            "payment_id":       str(uuid.uuid4()),
            "loan_id":          loan_id,
            "payment_date":     pmt_date,
            "payment_amount":   amt,
            "payment_type":     "scheduled",
            "days_past_due":    0,
            "cumulative_repaid": round(cum_repaid, 2),
        }

    def _missed_pmt(pmt_date: date, dpd: int) -> dict:
        return {
            "payment_id":       str(uuid.uuid4()),
            "loan_id":          loan_id,
            "payment_date":     pmt_date,
            "payment_amount":   0.0,
            "payment_type":     "missed",
            "days_past_due":    dpd,
            "cumulative_repaid": round(cum_repaid, 2),
        }

    # ── prepay ──────────────────────────────────────────────────────────────

    if behaviour == "prepay":
        cutoff = int(n_payments * np.random.uniform(0.40, 0.70))
        for pmt_date in payment_dates[:cutoff]:
            events.append(_normal_pmt(pmt_date))
        remaining = max(total_owed - cum_repaid, 0.0)
        cum_repaid += remaining
        if cutoff < len(payment_dates):
            events.append({
                "payment_id":       str(uuid.uuid4()),
                "loan_id":          loan_id,
                "payment_date":     payment_dates[cutoff],
                "payment_amount":   round(remaining, 2),
                "payment_type":     "early_payoff",
                "days_past_due":    0,
                "cumulative_repaid": round(cum_repaid, 2),
            })

    # ── default ─────────────────────────────────────────────────────────────
    #
    # Fix: DPD was previously incremented by payment_interval (1 or 7).
    # After 5 missed daily payments: DPD = 5. Never hit the 90-DPD threshold.
    # Now: three explicit snapshots at 30, 60, and 90 calendar-days after first miss.
    # Loans that stop paying before SIM_END - 90 days will cross 90 DPD and be
    # correctly classified as "default" by int_loan_status.sql.

    elif behaviour == "default":
        stop_idx = int(n_payments * np.random.uniform(0.40, 0.70))
        for pmt_date in payment_dates[:stop_idx]:
            events.append(_normal_pmt(pmt_date))

        if stop_idx < len(payment_dates):
            first_miss = payment_dates[stop_idx]
            for dpd in [30, 60, 90]:
                miss_date = first_miss + timedelta(days=dpd)
                if miss_date <= SIM_END:
                    events.append(_missed_pmt(miss_date, dpd))

    # ── delinquent_cure ──────────────────────────────────────────────────────
    #
    # Loan goes 30–75 DPD then cures. Max DPD stays below 90 so the loan is
    # classified as delinquent_30 / delinquent_60 in int_loan_status — not default.

    elif behaviour == "delinquent_cure":
        delinq_start = int(n_payments * np.random.uniform(0.20, 0.60))
        peak_dpd     = int(np.random.choice([30, 45, 60, 75]))

        for i, pmt_date in enumerate(payment_dates):
            if i < delinq_start:
                events.append(_normal_pmt(pmt_date))
            elif i == delinq_start:
                # Emit the peak-DPD missed record (represents the delinquency event)
                miss_date = pmt_date + timedelta(days=peak_dpd)
                if miss_date <= SIM_END:
                    events.append(_missed_pmt(miss_date, peak_dpd))
                # Resume on-time payments after cure
                # (The loan still pays for remaining scheduled dates)
            else:
                events.append(_normal_pmt(pmt_date))

    # ── current ──────────────────────────────────────────────────────────────

    else:
        for pmt_date in payment_dates:
            events.append(_normal_pmt(pmt_date))

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
