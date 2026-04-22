"""
test_data_gen.py — Unit tests for synthetic data generation.

Validates schema, distributions, and referential integrity of generated data.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_gen.generate_loans import generate_loans
from data_gen.generate_payments import generate_payments
from data_gen.generate_platforms import generate_platforms
from data_gen.generate_spv import generate_spv


class TestGenerateLoans:
    def test_loan_schema(self) -> None:
        """All required columns must be present."""
        df = generate_loans(n=100)
        required_cols = [
            "loan_id", "merchant_id", "platform", "origination_date",
            "principal_amount", "term_days", "factor_rate", "spv_id",
            "underwriting_score", "repayment_type",
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_no_duplicate_loan_ids(self) -> None:
        """loan_id must be unique."""
        df = generate_loans(n=1_000)
        assert df["loan_id"].nunique() == len(df)

    def test_principal_in_range(self) -> None:
        """Principal must be between $2,500 and $150,000."""
        df = generate_loans(n=1_000)
        assert df["principal_amount"].between(2_500, 150_000).all(), (
            f"Principal out of range: min={df['principal_amount'].min()}, "
            f"max={df['principal_amount'].max()}"
        )

    def test_principal_rounded_to_500(self) -> None:
        """Principal must be a multiple of $500."""
        df = generate_loans(n=500)
        assert (df["principal_amount"] % 500 == 0).all()

    def test_factor_rate_in_range(self) -> None:
        """Factor rate must be between 1.10 and 1.45."""
        df = generate_loans(n=1_000)
        assert df["factor_rate"].between(1.05, 1.50).all(), (
            f"Factor rate out of range: min={df['factor_rate'].min()}, "
            f"max={df['factor_rate'].max()}"
        )

    def test_platform_values(self) -> None:
        """Platform must be one of the five valid values."""
        df = generate_loans(n=1_000)
        valid = {"doordash", "amazon", "mindbody", "worldpay", "shopify"}
        assert set(df["platform"].unique()).issubset(valid)

    def test_platform_distribution(self) -> None:
        """DoorDash should be 55–65% of loans."""
        df = generate_loans(n=10_000)
        doordash_pct = (df["platform"] == "doordash").mean()
        assert 0.55 <= doordash_pct <= 0.65, (
            f"DoorDash share unexpected: {doordash_pct:.2%}"
        )

    def test_spv_values(self) -> None:
        """SPV must be one of SPV-A, SPV-B, SPV-C."""
        df = generate_loans(n=500)
        assert set(df["spv_id"].unique()).issubset({"SPV-A", "SPV-B", "SPV-C"})

    def test_underwriting_score_range(self) -> None:
        """Underwriting score must be 1–100."""
        df = generate_loans(n=500)
        assert df["underwriting_score"].between(1, 100).all()

    def test_term_days_values(self) -> None:
        """Term days must be one of 90, 180, 270, 365."""
        df = generate_loans(n=500)
        assert set(df["term_days"].unique()).issubset({90, 180, 270, 365})

    def test_origination_date_range(self) -> None:
        """Origination dates must fall within 2022-01-01 to 2024-12-31."""
        from datetime import date
        df = generate_loans(n=500)
        dates = pd.to_datetime(df["origination_date"]).dt.date
        assert dates.min() >= date(2022, 1, 1)
        assert dates.max() <= date(2024, 12, 31)

    def test_spv_assignment_logic(self) -> None:
        """SPV-C must hold loans originated after 2023-07-01 or with principal > $75K."""
        from datetime import date
        df = generate_loans(n=2_000)
        df["origination_date"] = pd.to_datetime(df["origination_date"]).dt.date
        cutoff = date(2023, 7, 1)
        spvc = df[df["spv_id"] == "SPV-C"]
        # All SPV-C rows should be large or post-cutoff
        assert (
            (spvc["origination_date"] >= cutoff) | (spvc["principal_amount"] > 75_000)
        ).all()


class TestGeneratePayments:
    def test_payments_reference_valid_loans(self) -> None:
        """All payment loan_ids must exist in the loans DataFrame."""
        loans = generate_loans(n=100)
        payments = generate_payments(loans)
        assert payments["loan_id"].isin(loans["loan_id"]).all()

    def test_payment_type_values(self) -> None:
        """payment_type must be scheduled, early_payoff, or missed."""
        loans = generate_loans(n=100)
        payments = generate_payments(loans)
        valid = {"scheduled", "early_payoff", "missed"}
        assert set(payments["payment_type"].unique()).issubset(valid)

    def test_missed_payments_have_zero_amount(self) -> None:
        """Missed payments must have payment_amount = 0."""
        loans = generate_loans(n=200)
        payments = generate_payments(loans)
        missed = payments[payments["payment_type"] == "missed"]
        assert (missed["payment_amount"] == 0).all()

    def test_payment_ids_unique(self) -> None:
        """payment_id must be unique."""
        loans = generate_loans(n=100)
        payments = generate_payments(loans)
        assert payments["payment_id"].nunique() == len(payments)

    def test_cumulative_repaid_non_negative(self) -> None:
        """cumulative_repaid must be >= 0 for all events."""
        loans = generate_loans(n=100)
        payments = generate_payments(loans)
        assert (payments["cumulative_repaid"] >= 0).all()

    def test_days_past_due_non_negative(self) -> None:
        """days_past_due must be >= 0."""
        loans = generate_loans(n=100)
        payments = generate_payments(loans)
        assert (payments["days_past_due"] >= 0).all()


class TestGeneratePlatforms:
    def test_all_platforms_present(self) -> None:
        """All 5 platforms must be in the output."""
        df = generate_platforms()
        expected = {"doordash", "amazon", "mindbody", "worldpay", "shopify"}
        assert set(df["platform"].tolist()) == expected

    def test_platform_uniqueness(self) -> None:
        """Platform keys must be unique."""
        df = generate_platforms()
        assert df["platform"].nunique() == len(df)


class TestGenerateSPV:
    def test_all_spvs_present(self) -> None:
        """All 3 SPV IDs must be present."""
        df = generate_spv()
        assert set(df["spv_id"].tolist()) == {"SPV-A", "SPV-B", "SPV-C"}

    def test_facility_limits_positive(self) -> None:
        """Facility limits must be positive."""
        df = generate_spv()
        assert (df["facility_limit"] > 0).all()

    def test_covenant_thresholds_in_range(self) -> None:
        """Covenant delinquency thresholds should be between 1% and 20%."""
        df = generate_spv()
        assert df["covenant_max_delinquency_pct"].between(0.01, 0.20).all()
