"""
test_agent.py — Integration tests for LangGraph workflow nodes.
Tests individual nodes and the policy engine without calling external APIs.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── State helpers ─────────────────────────────────────────────────

def make_minimal_state(**overrides):
    """Create a minimal OpsState for testing individual nodes."""
    base = {
        "ticket_id": "tick-1042",
        "run_id": "run-test-001",
        "trace_id": "OPS-TEST001",
        "ticket": {
            "ticket_id": "tick-1042",
            "ticket_number": "INC-1042",
            "customer_id": "cust-45821",
            "title": "Multiple payment failures",
            "description": "Customer 45821 has experienced multiple payment failures in the last 30 minutes.",
            "category": "payment_failure",
            "priority": "high",
            "status": "open",
        },
        "parsed_ticket": {
            "customer_id": "cust-45821",
            "issue_type": "payment_failure",
            "priority": "high",
            "summary": "Multiple payment gateway timeouts",
            "key_indicators": ["payment failure", "30 minutes"],
        },
        "investigation_plan": [],
        "customer": {
            "found": True,
            "customer_id": "cust-45821",
            "name": "Rajesh Mehta",
            "account_status": "active",
            "plan": "enterprise",
        },
        "transactions": [],
        "failed_transactions": {
            "total_failed": 5,
            "dominant_reason": "PAYMENT_GATEWAY_TIMEOUT",
            "failure_breakdown": {"PAYMENT_GATEWAY_TIMEOUT": 5},
            "failed_transactions": [],
        },
        "incidents": [],
        "system_events": [],
        "runbook_context": [
            {
                "source": "payment_gateway_timeout",
                "text": "Payment Gateway Timeout Runbook\n\nRecommended actions:\n- Create a high-priority incident",
                "score": 0.95,
            }
        ],
        "findings": {
            "summary": "5 payment failures due to gateway timeouts",
            "facts": ["5 PAYMENT_GATEWAY_TIMEOUT failures in 30 min"],
            "probable_cause": "Stripe payment gateway is timing out",
            "confidence": 0.9,
            "evidence_strength": "strong",
            "gaps": [],
        },
        "recommended_action": {
            "action_type": "CREATE_INCIDENT",
            "description": "Create a high-priority payment gateway incident",
            "reason": "5 consecutive failures with PAYMENT_GATEWAY_TIMEOUT",
            "risk_level": "medium",
            "requires_approval": True,
            "urgency": "immediate",
        },
        "validated_action": {},
        "approval_status": "pending",
        "approved_by": None,
        "approval_action_id": None,
        "execution_result": {},
        "current_node": "start",
        "node_durations": {},
        "errors": [],
        "workflow_status": "running",
    }
    base.update(overrides)
    return base


# ── Node: validate_action ─────────────────────────────────────────

class TestValidateActionNode:
    """Tests for the policy engine node."""

    def test_validate_applies_policy_to_create_incident(self):
        """CREATE_INCIDENT should have medium risk enforced."""
        from backend.agent import node_validate_action
        state = make_minimal_state(
            recommended_action={
                "action_type": "CREATE_INCIDENT",
                "description": "Create payment incident",
                "reason": "5 failures detected",
                "risk_level": "low",           # LLM says low — wrong
                "requires_approval": False,     # LLM says skip — wrong
            }
        )
        with patch("backend.agent._update_run_node"):
            result = node_validate_action(state)

        validated = result["validated_action"]
        assert validated["risk_level"] == "medium"
        assert validated["requires_approval"] is True
        assert validated["policy_applied"] is True

    def test_validate_add_note_no_approval(self):
        """ADD_TICKET_NOTE should not require approval."""
        from backend.agent import node_validate_action
        state = make_minimal_state(
            recommended_action={
                "action_type": "ADD_TICKET_NOTE",
                "description": "Add investigative note",
                "risk_level": "low",
                "requires_approval": False,
            }
        )
        with patch("backend.agent._update_run_node"):
            result = node_validate_action(state)

        validated = result["validated_action"]
        assert validated["risk_level"] == "low"
        assert validated["requires_approval"] is False


# ── Node: human_approval ──────────────────────────────────────────

class TestHumanApprovalNode:
    """Tests for the human-in-the-loop approval node."""

    def test_low_risk_skips_approval(self):
        """Low-risk actions should bypass the approval gate."""
        from backend.agent import node_human_approval
        state = make_minimal_state(
            validated_action={
                "action_type": "ADD_TICKET_NOTE",
                "risk_level": "low",
                "requires_approval": False,
                "description": "Add note",
                "reason": "Test",
            }
        )
        with patch("backend.agent._update_run_node"):
            result = node_human_approval(state)

        assert result["approval_status"] == "not_required"
        assert result["workflow_status"] == "running"

    def test_medium_risk_requires_approval(self):
        """Medium-risk actions should pause for approval."""
        from backend.agent import node_human_approval
        from unittest.mock import patch as p

        state = make_minimal_state(
            validated_action={
                "action_type": "CREATE_INCIDENT",
                "risk_level": "medium",
                "requires_approval": True,
                "description": "Create incident",
                "reason": "5 failures",
            }
        )

        mock_approval = {
            "action_id": "action-test-001",
            "run_id": "run-test-001",
        }

        with patch("backend.agent._update_run_node"), \
             patch("backend.agent.create_approval_request", return_value=mock_approval):
            result = node_human_approval(state)

        assert result["approval_status"] == "pending"
        assert result["workflow_status"] == "paused"
        assert result["approval_action_id"] == "action-test-001"


# ── Routing functions ─────────────────────────────────────────────

class TestRoutingFunctions:
    """Tests for LangGraph conditional routing."""

    def test_route_approved_goes_to_execute(self):
        """Approved status should route to execute_action."""
        from backend.agent import route_after_approval
        state = make_minimal_state(approval_status="approved")
        assert route_after_approval(state) == "execute_action"

    def test_route_rejected_goes_to_rejection_audit(self):
        """Rejected status should route to rejection_audit."""
        from backend.agent import route_after_approval
        state = make_minimal_state(approval_status="rejected")
        assert route_after_approval(state) == "rejection_audit"

    def test_route_not_required_goes_to_execute(self):
        """Not-required status should go to execute_action."""
        from backend.agent import route_after_approval
        state = make_minimal_state(approval_status="not_required")
        assert route_after_approval(state) == "execute_action"

    def test_route_pending_goes_to_rejection(self):
        """Pending (stuck) status should default to rejection_audit."""
        from backend.agent import route_after_approval
        state = make_minimal_state(approval_status="pending")
        # Pending means something went wrong — safe fallback
        assert route_after_approval(state) == "rejection_audit"


# ── Node: parse_ticket ────────────────────────────────────────────

class TestParseTicketNode:
    """Tests for the ticket parsing node."""

    def test_parse_ticket_fallback_on_llm_failure(self):
        """Node should use fallback parsing when LLM call fails."""
        from backend.agent import node_parse_ticket

        state = make_minimal_state()

        with patch("backend.agent._call_llm_json", side_effect=Exception("LLM unavailable")), \
             patch("backend.agent._update_run_node"), \
             patch("backend.agent.log_event"):
            result = node_parse_ticket(state)

        # Should not raise — should return fallback
        assert "parsed_ticket" in result
        assert result["current_node"] == "parse_ticket"
        parsed = result["parsed_ticket"]
        assert "customer_id" in parsed or "issue_type" in parsed

    def test_parse_ticket_strips_code_fences(self):
        """JSON stripping should handle markdown code blocks."""
        from backend.agent import _call_llm_json
        mock_response = MagicMock()
        mock_response.content = '```json\n{"key": "value"}\n```'

        with patch("backend.agent._get_llm") as mock_llm:
            mock_llm.return_value.invoke = MagicMock(return_value=mock_response)
            result = _call_llm_json("system", "user")

        assert result == {"key": "value"}


# ── Audit logging ─────────────────────────────────────────────────

class TestAuditLogging:
    """Tests for audit logging functions."""

    def test_log_event_doesnt_crash_on_db_failure(self):
        """Audit logging should never crash the main workflow."""
        with patch("backend.audit.get_db", side_effect=Exception("DB down")):
            from backend.audit import log_event
            # Should not raise
            result = log_event("test_event", ticket_id="tick-001")
            assert result is None  # Returns None on failure

    def test_audit_events_constants_exist(self):
        """All expected audit event types should be defined."""
        from backend.audit import AuditEvents
        required = [
            "TICKET_PARSED", "PLAN_CREATED", "TOOL_CALLED", "TOOL_RESULT",
            "ANALYSIS_COMPLETED", "ACTION_RECOMMENDED", "APPROVAL_REQUESTED",
            "APPROVAL_APPROVED", "APPROVAL_REJECTED", "ACTION_EXECUTED",
            "WORKFLOW_COMPLETED", "WORKFLOW_FAILED",
        ]
        for attr in required:
            assert hasattr(AuditEvents, attr), f"Missing audit event: {attr}"

    def test_get_audit_trail_returns_list(self):
        """get_audit_trail should return a list even when DB has no records."""
        with patch("backend.audit.get_db") as mock_get_db:
            mock_ctx = MagicMock()
            mock_session = MagicMock()
            mock_session.execute.return_value.scalars.return_value.all.return_value = []
            mock_ctx.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_get_db.return_value = mock_ctx

            from backend.audit import get_audit_trail
            result = get_audit_trail("tick-001")
            assert isinstance(result, list)
