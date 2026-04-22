"""
generate_spv.py — Generates spv_allocation.csv and control_totals.csv.

SPV facilities:
  SPV-A  Ribbit Capital Facility A    — small loans, early vintage
  SPV-B  Coatue Capital Facility B    — mid-size loans
  SPV-C  Bessemer Ventures Facility C — large loans, recent vintage

Also writes control_totals.csv, which acts as the source-of-truth for
rpt_reconciliation — simulating a servicing system control file.

Run directly:  python data_gen/generate_spv.py
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"

SPV_DATA = [
    {
        "spv_id": "SPV-A",
        "facility_name": "Ribbit Capital Facility A",
        "facility_limit": 50_000_000.0,
        "facility_drawn": 0.0,  # recalculated in dbt
        "covenant_max_delinquency_pct": 0.08,
        "covenant_min_yield": 0.18,
        "facility_inception_date": date(2022, 1, 1),
    },
    {
        "spv_id": "SPV-B",
        "facility_name": "Coatue Capital Facility B",
        "facility_limit": 120_000_000.0,
        "facility_drawn": 0.0,
        "covenant_max_delinquency_pct": 0.07,
        "covenant_min_yield": 0.20,
        "facility_inception_date": date(2022, 6, 1),
    },
    {
        "spv_id": "SPV-C",
        "facility_name": "Bessemer Ventures Facility C",
        "facility_limit": 200_000_000.0,
        "facility_drawn": 0.0,
        "covenant_max_delinquency_pct": 0.06,
        "covenant_min_yield": 0.22,
        "facility_inception_date": date(2023, 7, 1),
    },
]


def generate_spv() -> pd.DataFrame:
    """
    Return static SPV allocation DataFrame.

    Returns:
        DataFrame with one row per SPV facility.
    """
    return pd.DataFrame(SPV_DATA)


def generate_control_totals(loans: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a control_totals.csv that mirrors what a servicing system would report.
    Values are derived from the generated data so reconciliation passes.

    Args:
        loans: The loans DataFrame.
        payments: The payments DataFrame.

    Returns:
        DataFrame with metric_name and source_value columns.
    """
    scheduled_payments = payments[payments["payment_type"] != "missed"]
    total_repaid = scheduled_payments.groupby("loan_id")["payment_amount"].sum()

    # Build a simple status to identify defaults (max DPD >= 90)
    max_dpd = payments.groupby("loan_id")["days_past_due"].max()
    default_loan_ids = set(max_dpd[max_dpd >= 90].index)

    records = [
        {"metric_name": "origination_count", "source_value": float(len(loans))},
        {"metric_name": "origination_principal", "source_value": float(loans["principal_amount"].sum())},
        {"metric_name": "total_collected", "source_value": float(total_repaid.sum())},
        {"metric_name": "default_count", "source_value": float(len(default_loan_ids))},
    ]
    return pd.DataFrame(records)


def main() -> None:
    """Write spv_allocation.csv and control_totals.csv to data_gen/output/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = generate_spv()
    out_path = OUTPUT_DIR / "spv_allocation.csv"
    df.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(df), out_path)

    # Generate control totals if loans/payments already exist
    loans_path = OUTPUT_DIR / "loans.csv"
    payments_path = OUTPUT_DIR / "payments.csv"
    if loans_path.exists() and payments_path.exists():
        loans = pd.read_csv(loans_path)
        payments = pd.read_csv(payments_path)
        ct = generate_control_totals(loans, payments)
        ct_path = OUTPUT_DIR / "control_totals.csv"
        ct.to_csv(ct_path, index=False)
        logger.info("Wrote %s rows to %s", len(ct), ct_path)
    else:
        logger.warning(
            "loans.csv or payments.csv not found — skipping control_totals.csv generation. "
            "Run generate_loans.py and generate_payments.py first."
        )


if __name__ == "__main__":
    main()
