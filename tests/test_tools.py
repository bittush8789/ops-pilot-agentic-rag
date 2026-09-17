"""
test_tools.py — Unit tests for agent tools.
Tests read tools with mocked database sessions.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# ── Ticket parsing tests ──────────────────────────────────────────

class TestTicketParsing:
    """Tests for structured ticket parsing."""

    def test_policy_low_risk(self):
        """ADD_TICKET_NOTE should be low risk, no approval required."""
        from backend.prompts import get_policy_for_action, APPROVAL_REQUIRED_FOR
        policy = get_policy_for_action("ADD_TICKET_NOTE")
        assert policy["risk_level"] == "low"
        assert policy["risk_level"] not in APPROVAL_REQUIRED_FOR

    def test_policy_medium_risk_requires_approval(self):
        """CREATE_INCIDENT is medium risk and requires approval."""
        from backend.prompts import get_policy_for_action, APPROVAL_REQUIRED_FOR
        policy = get_policy_for_action("CREATE_INCIDENT")
        assert policy["risk_level"] == "medium"
        assert policy["risk_level"] in APPROVAL_REQUIRED_FOR

    def test_policy_high_risk_requires_approval(self):
        """RESTART_SERVICE is high risk and requires approval."""
        from backend.prompts import get_policy_for_action, APPROVAL_REQUIRED_FOR
        policy = get_policy_for_action("RESTART_SERVICE")
        assert policy["risk_level"] == "high"
        assert policy["risk_level"] in APPROVAL_REQUIRED_FOR

    def test_validate_action_enforces_policy(self):
        """Policy engine must override LLM-supplied risk level."""
        from backend.prompts import validate_action_policy
        # LLM incorrectly says CREATE_INCIDENT is low risk
        recommended = {
            "action_type": "CREATE_INCIDENT",
            "description": "Create incident",
            "risk_level": "low",           # LLM wrong
            "requires_approval": False,     # LLM wrong
        }
        validated = validate_action_policy(recommended)
        # Policy engine corrects it
        assert validated["risk_level"] == "medium"
        assert validated["requires_approval"] is True
        assert validated["policy_applied"] is True

    def test_unknown_action_defaults_to_high_risk(self):
        """Unknown action types should default to high risk."""
        from backend.prompts import validate_action_policy
        validated = validate_action_policy({"action_type": "UNKNOWN_ACTION"})
        assert validated["risk_level"] == "high"
        assert validated["requires_approval"] is True


# ── Customer tool tests ───────────────────────────────────────────

class TestCustomerTool:
    """Tests for get_customer tool."""

    def test_customer_not_found_returns_error_dict(self, db_session):
        """Tool should return error dict (not raise) when customer not found."""
        with patch("backend.tools.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.tools import get_customer
            result = get_customer("nonexistent-customer-id")

            assert result["found"] is False

    def test_customer_found(self, db_session, sample_customer):
        """Tool should return customer data when found."""
        with patch("backend.tools.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.tools import get_customer
            result = get_customer("cust-45821")

            assert result["found"] is True
            assert result["name"] == "Rajesh Mehta"
            assert result["account_status"] == "active"
            assert result["plan"] == "enterprise"

    def test_customer_input_validation_rejects_empty(self):
        """Tool should raise ValidationError for empty customer_id."""
        from pydantic import ValidationError
        from backend.tools import GetCustomerInput

        with pytest.raises(ValidationError):
            GetCustomerInput(customer_id="")


# ── Transaction tool tests ────────────────────────────────────────

class TestTransactionTools:
    """Tests for transaction retrieval tools."""

    def test_failed_transactions_count(self, db_session, sample_customer, sample_failed_transactions):
        """Should correctly count and group failed transactions."""
        with patch("backend.tools.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.tools import get_failed_transactions
            result = get_failed_transactions(
                customer_id="cust-45821",
                hours=48,
            )

            assert result["total_failed"] == 5
            assert result["dominant_reason"] == "PAYMENT_GATEWAY_TIMEOUT"
            assert "PAYMENT_GATEWAY_TIMEOUT" in result["failure_breakdown"]

    def test_transaction_input_validation(self):
        """Limit must be within bounds."""
        from pydantic import ValidationError
        from backend.tools import GetTransactionsInput

        with pytest.raises(ValidationError):
            GetTransactionsInput(customer_id="cust-001", limit=9999)


# ── Incident tool tests ───────────────────────────────────────────

class TestIncidentTool:
    """Tests for get_related_incidents tool."""

    def test_get_incidents_by_customer(self, db_session, sample_customer, sample_incident):
        """Should return incidents for the customer."""
        with patch("backend.tools.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.tools import get_related_incidents
            result = get_related_incidents(customer_id="cust-45821")

            assert result["total"] >= 1
            assert any(
                i["incident_number"] == "SINC-001"
                for i in result["incidents"]
            )

    def test_get_incidents_returns_empty_for_unknown_customer(self, db_session):
        """Should return empty list for unknown customer (not raise)."""
        with patch("backend.tools.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.tools import get_related_incidents
            result = get_related_incidents(customer_id="nonexistent-cust")

            assert result["total"] == 0
            assert result["incidents"] == []


# ── Policy engine tests ───────────────────────────────────────────

class TestPolicyEngine:
    """Tests ensuring the policy engine cannot be bypassed."""

    @pytest.mark.parametrize("action_type,expected_risk,expected_approval", [
        ("ADD_TICKET_NOTE",   "low",    False),
        ("UPDATE_TICKET",     "low",    False),
        ("CREATE_INCIDENT",   "medium", True),
        ("NOTIFY_OPERATIONS", "medium", True),
        ("RESTART_SERVICE",   "high",   True),
        ("DISABLE_ACCOUNT",   "high",   True),
    ])
    def test_all_action_policies(self, action_type, expected_risk, expected_approval):
        """Each action type has the correct risk level and approval requirement."""
        from backend.prompts import validate_action_policy
        action = {
            "action_type": action_type,
            "description": "Test action",
            "risk_level": "low",           # Always try to inject low risk
            "requires_approval": False,     # Always try to bypass approval
        }
        validated = validate_action_policy(action)
        assert validated["risk_level"] == expected_risk
        assert validated["requires_approval"] == expected_approval

    def test_policy_is_deterministic(self):
        """Same action always produces same policy result."""
        from backend.prompts import validate_action_policy
        action = {"action_type": "CREATE_INCIDENT", "description": "x"}
        result1 = validate_action_policy(action)
        result2 = validate_action_policy(action)
        assert result1["risk_level"] == result2["risk_level"]
        assert result1["requires_approval"] == result2["requires_approval"]


# ── Create incident tool tests ────────────────────────────────────

class TestCreateIncidentTool:
    """Tests for create_incident write tool."""

    def test_create_incident_input_validation(self):
        """Severity must be a valid enum value."""
        from pydantic import ValidationError
        from backend.tools import CreateIncidentInput

        with pytest.raises(ValidationError):
            CreateIncidentInput(
                title="Test Incident",
                description="Test description",
                severity="extreme",       # Invalid
            )

    def test_create_incident_invalid_category_defaults(self):
        """Unknown category should default to 'general'."""
        from backend.tools import CreateIncidentInput
        inp = CreateIncidentInput(
            title="Test Incident",
            description="Test description",
            category="unknown_category",
        )
        assert inp.category == "general"


# ── Approval workflow tests ───────────────────────────────────────

class TestApprovalWorkflow:
    """Tests for the human-in-the-loop approval system."""

    def test_approval_required_for_medium_risk(self):
        """Medium risk actions must always require approval."""
        from backend.prompts import APPROVAL_REQUIRED_FOR
        assert "medium" in APPROVAL_REQUIRED_FOR

    def test_approval_required_for_high_risk(self):
        """High risk actions must always require approval."""
        from backend.prompts import APPROVAL_REQUIRED_FOR
        assert "high" in APPROVAL_REQUIRED_FOR

    def test_no_approval_for_low_risk(self):
        """Low risk actions should not require approval."""
        from backend.prompts import APPROVAL_REQUIRED_FOR
        assert "low" not in APPROVAL_REQUIRED_FOR

    def test_process_approval_invalid_decision(self, db_session):
        """Invalid decision value should raise ValueError."""
        with patch("backend.approval.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=db_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.approval import process_approval
            with pytest.raises(ValueError, match="Invalid decision"):
                process_approval("action-001", "maybe")
