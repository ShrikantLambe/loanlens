"""
test_ai_layer.py — Unit tests for the AI layer.

Uses mocked Anthropic API responses — does not make real API calls.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

MOCK_SUMMARY = {
    "report_date": "2024-12-01",
    "total_loans": 10_000,
    "outstanding_principal": 85_000_000.0,
    "delinquency_rate_pct": 4.2,
    "default_rate_pct": 3.1,
    "avg_underwriting_score": 68.4,
    "current_loans": 7_500,
    "defaulted_loans": 310,
    "paid_off_loans": 1_500,
}

MOCK_COMMENTARY = {
    "executive_summary": "The portfolio demonstrated stable performance in Q4 2024.",
    "key_metrics_narrative": "Originations grew 8% MoM through Q3 before normalising in Q4.",
    "risk_flags": ["SPV-B delinquency approaching covenant limit of 7%."],
    "cohort_observations": "2022 cohorts show full recovery curves; 2024 cohorts remain early-stage.",
    "recommended_actions": ["Monitor SPV-B weekly.", "Tighten underwriting for score < 40."],
    "sentiment": "cautious",
}

MOCK_ANOMALIES = [
    {
        "anomaly_type": "delinquency_spike",
        "severity": "medium",
        "description": "Delinquency rate increased 1.2pp over 14 days.",
        "affected_entity": "SPV-B",
        "detected_date": "2024-11-15",
        "recommended_action": "Increase monitoring frequency.",
    }
]


def _mock_message(content: str) -> MagicMock:
    """Build a mock anthropic.Message with given text content."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    msg.usage = MagicMock(input_tokens=500)
    return msg


class TestPortfolioNarrator:
    @patch("anthropic.Anthropic")
    def test_narrator_returns_required_keys(self, mock_anthropic_cls: MagicMock) -> None:
        """Commentary dict must contain all required keys."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_COMMENTARY))

        from ai_layer.portfolio_narrator import generate_portfolio_commentary

        result = generate_portfolio_commentary(MOCK_SUMMARY, [], [], [])
        required = [
            "executive_summary", "key_metrics_narrative",
            "risk_flags", "cohort_observations", "recommended_actions", "sentiment",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    @patch("anthropic.Anthropic")
    def test_sentiment_valid_values(self, mock_anthropic_cls: MagicMock) -> None:
        """Sentiment must be one of three valid values."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_COMMENTARY))

        from ai_layer.portfolio_narrator import generate_portfolio_commentary

        result = generate_portfolio_commentary(MOCK_SUMMARY, [], [], [])
        assert result["sentiment"] in ("positive", "cautious", "concerning")

    @patch("anthropic.Anthropic")
    def test_risk_flags_is_list(self, mock_anthropic_cls: MagicMock) -> None:
        """risk_flags must be a list."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_COMMENTARY))

        from ai_layer.portfolio_narrator import generate_portfolio_commentary

        result = generate_portfolio_commentary(MOCK_SUMMARY, [], [], [])
        assert isinstance(result["risk_flags"], list)

    @patch("anthropic.Anthropic")
    def test_recommended_actions_is_list(self, mock_anthropic_cls: MagicMock) -> None:
        """recommended_actions must be a list."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_COMMENTARY))

        from ai_layer.portfolio_narrator import generate_portfolio_commentary

        result = generate_portfolio_commentary(MOCK_SUMMARY, [], [], [])
        assert isinstance(result["recommended_actions"], list)


class TestAnomalyAgent:
    @patch("anthropic.Anthropic")
    def test_detect_anomalies_returns_list(self, mock_anthropic_cls: MagicMock) -> None:
        """detect_anomalies must return a list."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_ANOMALIES))

        from ai_layer.anomaly_agent import detect_anomalies

        result = detect_anomalies(daily_data=[], spv_data=[])
        assert isinstance(result, list)

    @patch("anthropic.Anthropic")
    def test_no_anomalies_returns_empty_list(self, mock_anthropic_cls: MagicMock) -> None:
        """Empty anomaly response must return empty list."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message("[]")

        from ai_layer.anomaly_agent import detect_anomalies

        result = detect_anomalies(daily_data=[], spv_data=[])
        assert result == []

    @patch("anthropic.Anthropic")
    def test_anomaly_severity_values(self, mock_anthropic_cls: MagicMock) -> None:
        """Anomaly severities must be valid values."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _mock_message(json.dumps(MOCK_ANOMALIES))

        from ai_layer.anomaly_agent import detect_anomalies

        results = detect_anomalies(daily_data=[], spv_data=[])
        valid_severities = {"low", "medium", "high", "critical"}
        for anomaly in results:
            assert anomaly.get("severity") in valid_severities


class TestMemoGenerator:
    def test_build_memo_required_keys(self) -> None:
        """build_memo must produce all required memo keys."""
        from ai_layer.memo_generator import build_memo

        memo = build_memo(
            commentary=MOCK_COMMENTARY,
            anomalies=MOCK_ANOMALIES,
            summary=MOCK_SUMMARY,
            spv_data=[],
        )
        required = [
            "title", "period", "executive_summary", "sentiment",
            "key_metrics", "narrative", "risk_flags", "recommended_actions",
            "covenant_status", "generated_at", "model_used", "disclaimer",
        ]
        for key in required:
            assert key in memo, f"Missing key: {key}"

    def test_high_severity_anomalies_in_risk_flags(self) -> None:
        """High/critical anomaly descriptions must be included in risk_flags."""
        from ai_layer.memo_generator import build_memo

        high_anomaly = {**MOCK_ANOMALIES[0], "severity": "high"}
        memo = build_memo(
            commentary=MOCK_COMMENTARY,
            anomalies=[high_anomaly],
            summary=MOCK_SUMMARY,
            spv_data=[],
        )
        assert high_anomaly["description"] in memo["risk_flags"]

    def test_low_severity_anomalies_not_in_risk_flags(self) -> None:
        """Low severity anomaly descriptions must NOT be merged into risk_flags."""
        from ai_layer.memo_generator import build_memo

        low_anomaly = {**MOCK_ANOMALIES[0], "severity": "low", "description": "Minor drift."}
        memo = build_memo(
            commentary={"risk_flags": [], "recommended_actions": [], "sentiment": "cautious",
                        "executive_summary": "", "key_metrics_narrative": "", "cohort_observations": ""},
            anomalies=[low_anomaly],
            summary=MOCK_SUMMARY,
            spv_data=[],
        )
        assert low_anomaly["description"] not in memo["risk_flags"]

    def test_memo_to_html_contains_key_sections(self) -> None:
        """HTML output must include executive summary and covenant table headers."""
        from ai_layer.memo_generator import build_memo, memo_to_html

        memo = build_memo(MOCK_COMMENTARY, [], MOCK_SUMMARY, [])
        html = memo_to_html(memo)
        assert "Executive Summary" in html
        assert "SPV Covenant Status" in html
        assert "Portfolio Narrative" in html
