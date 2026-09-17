"""
audit.py — Centralized audit logging for all significant OpsPilot events.

Every consequential operation (tool call, approval, action execution, etc.)
must be recorded here for compliance and traceability.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import structlog

from backend.database import get_db
from backend.models import AuditLog

log = structlog.get_logger(__name__)

# ── Audit Event Types ─────────────────────────────────────────────
class AuditEvents:
    TICKET_RECEIVED          = "ticket_received"
    TICKET_PARSED            = "ticket_parsed"
    PLAN_CREATED             = "plan_created"
    TOOL_CALLED              = "tool_call"
    TOOL_RESULT              = "tool_result"
    TOOL_ERROR               = "tool_error"
    ANALYSIS_COMPLETED       = "analysis_completed"
    ACTION_RECOMMENDED       = "action_recommended"
    APPROVAL_REQUESTED       = "approval_requested"
    APPROVAL_APPROVED        = "approval_approved"
    APPROVAL_REJECTED        = "approval_rejected"
    ACTION_EXECUTED          = "action_executed"
    ACTION_FAILED            = "action_failed"
    TICKET_UPDATED           = "ticket_updated"
    INCIDENT_CREATED         = "incident_created"
    WORKFLOW_STARTED         = "workflow_started"
    WORKFLOW_COMPLETED       = "workflow_completed"
    WORKFLOW_FAILED          = "workflow_failed"
    WORKFLOW_PAUSED          = "workflow_paused"
    RUNBOOK_RETRIEVED        = "runbook_retrieved"
    CUSTOMER_QUERIED         = "customer_queried"
    TRANSACTIONS_QUERIED     = "transactions_queried"
    INCIDENTS_QUERIED        = "incidents_queried"
    SYSTEM_EVENTS_QUERIED    = "system_events_queried"


# ── Core logging function ─────────────────────────────────────────

def log_event(
    event_type: str,
    actor: str = "ops-agent",
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> Optional[str]:
    """
    Write an audit event to the audit_logs table.

    Args:
        event_type: One of AuditEvents constants
        actor: Who/what triggered this event (e.g., 'ops-agent', 'ops-engineer')
        ticket_id: Related ticket ID if applicable
        trace_id: LangGraph trace ID for correlation
        details: Arbitrary JSON-serializable details dict

    Returns:
        audit_id of the created record, or None on failure
    """
    try:
        with get_db() as db:
            audit_entry = AuditLog(
                trace_id=trace_id,
                ticket_id=ticket_id,
                event_type=event_type,
                actor=actor,
                details=details or {},
                timestamp=datetime.utcnow(),
            )
            db.add(audit_entry)
            db.flush()
            audit_id = audit_entry.audit_id

        log.info(
            "Audit event recorded",
            event_type=event_type,
            actor=actor,
            ticket_id=ticket_id,
            trace_id=trace_id,
            audit_id=audit_id,
        )
        return audit_id

    except Exception as e:
        # Never let audit logging crash the main workflow
        log.error(
            "Failed to write audit log",
            event_type=event_type,
            error=str(e),
        )
        return None


# ── Convenience helpers ───────────────────────────────────────────

def audit_tool_call(
    tool_name: str,
    inputs: dict,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Log a tool invocation."""
    log_event(
        event_type=AuditEvents.TOOL_CALLED,
        actor="ops-agent",
        ticket_id=ticket_id,
        trace_id=trace_id,
        details={"tool": tool_name, "inputs": inputs},
    )


def audit_tool_result(
    tool_name: str,
    result_summary: str,
    duration_ms: int,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Log a tool result."""
    log_event(
        event_type=AuditEvents.TOOL_RESULT,
        actor="ops-agent",
        ticket_id=ticket_id,
        trace_id=trace_id,
        details={
            "tool": tool_name,
            "result_summary": result_summary,
            "duration_ms": duration_ms,
        },
    )


def audit_approval_requested(
    action_id: str,
    action_type: str,
    risk_level: str,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Log approval request creation."""
    log_event(
        event_type=AuditEvents.APPROVAL_REQUESTED,
        actor="ops-agent",
        ticket_id=ticket_id,
        trace_id=trace_id,
        details={
            "action_id": action_id,
            "action_type": action_type,
            "risk_level": risk_level,
        },
    )


def audit_approval_decision(
    action_id: str,
    decision: str,
    approved_by: str,
    notes: Optional[str] = None,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Log approval approve/reject."""
    event_type = (
        AuditEvents.APPROVAL_APPROVED
        if decision == "approved"
        else AuditEvents.APPROVAL_REJECTED
    )
    log_event(
        event_type=event_type,
        actor=approved_by,
        ticket_id=ticket_id,
        trace_id=trace_id,
        details={
            "action_id": action_id,
            "decision": decision,
            "notes": notes,
        },
    )


def audit_workflow_event(
    event_type: str,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Log a workflow lifecycle event."""
    log_event(
        event_type=event_type,
        actor="ops-agent",
        ticket_id=ticket_id,
        trace_id=trace_id,
        details=details,
    )


def get_audit_trail(ticket_id: str) -> list[dict]:
    """
    Retrieve all audit events for a ticket, ordered by timestamp.

    Args:
        ticket_id: The ticket to retrieve audit trail for

    Returns:
        List of audit event dicts
    """
    try:
        with get_db() as db:
            from sqlalchemy import select
            stmt = (
                select(AuditLog)
                .where(AuditLog.ticket_id == ticket_id)
                .order_by(AuditLog.timestamp.asc())
            )
            results = db.execute(stmt).scalars().all()
            return [
                {
                    "audit_id": r.audit_id,
                    "trace_id": r.trace_id,
                    "event_type": r.event_type,
                    "actor": r.actor,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in results
            ]
    except Exception as e:
        log.error("Failed to retrieve audit trail", ticket_id=ticket_id, error=str(e))
        return []
