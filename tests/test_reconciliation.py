"""
test_reconciliation.py — Tests for data pipeline integrity via reconciliation.

These tests verify that generated data is internally consistent — the same
totals that go into the warehouse match the control totals file.
They do NOT connect to Snowflake; they work entirely from generated CSVs.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

OUTPUT_DIR = Path(__file__).parent.parent / "data_gen" / "output"


def _load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load loans, payments, and control_totals from CSV files."""
    loans = pd.read_csv(OUTPUT_DIR / "loans.csv")
    payments = pd.read_csv(OUTPUT_DIR / "payments.csv")
    control = pd.read_csv(OUTPUT_DIR / "control_totals.csv")
    return loans, payments, control


@pytest.fixture(scope="module")
def data():
    """Load generated output CSVs."""
    if not (OUTPUT_DIR / "loans.csv").exists():
        pytest.skip("Generated CSV files not found. Run `make seed` first.")
    return _load_outputs()


def test_origination_count_matches_control(data) -> None:
    """Warehouse loan count must match control total within 0.1%."""
    loans, _, control = data
    expected = float(control.loc[control["metric_name"] == "origination_count", "source_value"].iloc[0])
    actual = float(len(loans))
    delta_pct = abs(actual - expected) / max(expected, 1) * 100
    assert delta_pct < 0.1, f"origination_count delta: {delta_pct:.4f}%"


def test_origination_principal_matches_control(data) -> None:
    """Total principal must match control total within 0.1%."""
    loans, _, control = data
    expected = float(control.loc[control["metric_name"] == "origination_principal", "source_value"].iloc[0])
    actual = float(loans["principal_amount"].sum())
    delta_pct = abs(actual - expected) / max(expected, 1) * 100
    assert delta_pct < 0.1, f"origination_principal delta: {delta_pct:.4f}%"


def test_total_collected_matches_control(data) -> None:
    """Total collected payments must match control total within 0.1%."""
    loans, payments, control = data
    expected = float(control.loc[control["metric_name"] == "total_collected", "source_value"].iloc[0])
    scheduled = payments[payments["payment_type"] != "missed"]
    actual = float(scheduled.groupby("loan_id")["payment_amount"].sum().sum())
    delta_pct = abs(actual - expected) / max(expected, 1) * 100
    assert delta_pct < 0.1, f"total_collected delta: {delta_pct:.4f}%"


def test_all_payments_reference_valid_loans(data) -> None:
    """Every payment must reference a loan_id that exists in loans.csv."""
    loans, payments, _ = data
    orphaned = ~payments["loan_id"].isin(loans["loan_id"])
    assert not orphaned.any(), f"{orphaned.sum()} payments reference unknown loan_ids"


def test_no_negative_principal(data) -> None:
    """No loan should have principal <= 0."""
    loans, _, _ = data
    assert (loans["principal_amount"] > 0).all()


def test_no_negative_payment_amounts_for_scheduled(data) -> None:
    """Scheduled payments must have positive amounts."""
    _, payments, _ = data
    scheduled = payments[payments["payment_type"] == "scheduled"]
    assert (scheduled["payment_amount"] > 0).all()


def test_reconciliation_delta_within_tolerance(data) -> None:
    """
    Comprehensive: all control metrics must reconcile within 0.1%.
    This is the Python equivalent of assert_reconciliation_delta_lt_threshold.sql.
    """
    loans, payments, control = data
    scheduled = payments[payments["payment_type"] != "missed"]
    total_repaid = scheduled.groupby("loan_id")["payment_amount"].sum()

    max_dpd = payments.groupby("loan_id")["days_past_due"].max()
    default_loan_ids = set(max_dpd[max_dpd >= 90].index)

    warehouse = {
        "origination_count": float(len(loans)),
        "origination_principal": float(loans["principal_amount"].sum()),
        "total_collected": float(total_repaid.sum()),
        "default_count": float(len(default_loan_ids)),
    }

    for _, row in control.iterrows():
        metric = row["metric_name"]
        source_val = float(row["source_value"])
        warehouse_val = warehouse.get(metric, 0.0)
        delta_pct = abs(warehouse_val - source_val) / max(source_val, 1) * 100
        assert delta_pct < 0.1, (
            f"Reconciliation failure on '{metric}': "
            f"warehouse={warehouse_val:,.2f}, source={source_val:,.2f}, delta={delta_pct:.4f}%"
        )
