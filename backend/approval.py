"""
approval.py — Human-in-the-Loop approval workflow.

Manages approval requests: creation, retrieval, and processing.
The LangGraph agent pauses at the human_approval node and resumes
only after this module records a decision.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

import structlog

from backend.audit import AuditEvents, audit_approval_decision, audit_approval_requested, log_event
from backend.database import get_db
from backend.models import AgentAction, AgentRun, Ticket

log = structlog.get_logger(__name__)

# ── Thread-safe in-memory resume triggers ─────────────────────────
# Maps run_id → threading.Event — signaled when approval is processed
_resume_events: dict[str, threading.Event] = {}
_resume_lock = threading.Lock()


def _get_or_create_resume_event(run_id: str) -> threading.Event:
    with _resume_lock:
        if run_id not in _resume_events:
            _resume_events[run_id] = threading.Event()
        return _resume_events[run_id]


def _signal_resume(run_id: str) -> None:
    with _resume_lock:
        if run_id in _resume_events:
            _resume_events[run_id].set()


# ── Approval creation ─────────────────────────────────────────────

def create_approval_request(
    ticket_id: str,
    run_id: str,
    action_type: str,
    risk_level: str,
    description: str,
    reason: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Create an approval request in the database.
    Called by the LangGraph human_approval node.

    Returns the created action dict.
    """
    try:
        with get_db() as db:
            action = AgentAction(
                run_id=run_id,
                ticket_id=ticket_id,
                action_type=action_type,
                risk_level=risk_level,
                description=description,
                reason=reason,
                approval_status="pending",
                execution_status="pending",
            )
            db.add(action)
            db.flush()

            # Update ticket status to pending_approval
            ticket = db.get(Ticket, ticket_id)
            if ticket:
                ticket.status = "pending_approval"
                ticket.updated_at = datetime.utcnow()

            # Update agent run status
            run = db.get(AgentRun, run_id)
            if run:
                run.status = "paused"
                run.current_node = "human_approval"

            action_id = action.action_id

        # Audit the approval request
        audit_approval_requested(
            action_id=action_id,
            action_type=action_type,
            risk_level=risk_level,
            ticket_id=ticket_id,
            trace_id=trace_id,
        )

        log.info(
            "Approval request created",
            action_id=action_id,
            ticket_id=ticket_id,
            action_type=action_type,
            risk_level=risk_level,
        )

        # Ensure a resume event exists for this run
        _get_or_create_resume_event(run_id)

        return {
            "action_id": action_id,
            "run_id": run_id,
            "ticket_id": ticket_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "description": description,
            "reason": reason,
            "approval_status": "pending",
        }

    except Exception as e:
        log.error("Failed to create approval request", error=str(e))
        raise


# ── Approval retrieval ─────────────────────────────────────────────

def get_pending_approvals() -> list[dict]:
    """Return all pending approval requests."""
    try:
        with get_db() as db:
            from sqlalchemy import select
            stmt = (
                select(AgentAction)
                .where(AgentAction.approval_status == "pending")
                .order_by(AgentAction.created_at.desc())
            )
            actions = db.execute(stmt).scalars().all()
            return [_action_to_dict(a) for a in actions]
    except Exception as e:
        log.error("Failed to get pending approvals", error=str(e))
        return []


def get_approval_by_id(action_id: str) -> Optional[dict]:
    """Return a specific approval request by action_id."""
    try:
        with get_db() as db:
            action = db.get(AgentAction, action_id)
            if not action:
                return None
            return _action_to_dict(action)
    except Exception as e:
        log.error("Failed to get approval", action_id=action_id, error=str(e))
        return None


# ── Approval processing ───────────────────────────────────────────

def process_approval(
    action_id: str,
    decision: str,          # "approved" or "rejected"
    approved_by: str = "ops-engineer",
    notes: Optional[str] = None,
) -> dict:
    """
    Record a human approval decision.

    Args:
        action_id: The AgentAction to approve/reject
        decision: 'approved' or 'rejected'
        approved_by: Name/ID of the approver
        notes: Optional notes from the approver

    Returns:
        Updated action dict
    """
    if decision not in ("approved", "rejected"):
        raise ValueError(f"Invalid decision '{decision}'. Must be 'approved' or 'rejected'.")

    try:
        with get_db() as db:
            action = db.get(AgentAction, action_id)
            if not action:
                raise ValueError(f"Action {action_id} not found")
            if action.approval_status != "pending":
                raise ValueError(
                    f"Action {action_id} is already {action.approval_status}"
                )

            now = datetime.utcnow()
            action.approval_status = decision
            action.approved_by = approved_by
            action.approved_at = now
            action.updated_at = now

            if decision == "rejected":
                action.execution_status = "skipped"

            run_id = action.run_id
            ticket_id = action.ticket_id
            action_type = action.action_type

            # Update agent run status
            if run_id:
                run = db.get(AgentRun, run_id)
                if run:
                    run.status = "running" if decision == "approved" else "rejected"
                    run.current_node = "execute_action" if decision == "approved" else "audit_result"

            action_dict = _action_to_dict(action)

        # Audit the decision
        with get_db() as db:
            # fetch trace_id from agent run
            run = db.get(AgentRun, run_id) if run_id else None
            trace_id = run.trace_id if run else None

        audit_approval_decision(
            action_id=action_id,
            decision=decision,
            approved_by=approved_by,
            notes=notes,
            ticket_id=ticket_id,
            trace_id=trace_id,
        )

        log.info(
            "Approval decision recorded",
            action_id=action_id,
            decision=decision,
            approved_by=approved_by,
        )

        # Signal the waiting LangGraph thread to resume
        if run_id:
            _signal_resume(run_id)

        return action_dict

    except Exception as e:
        log.error("Failed to process approval", action_id=action_id, error=str(e))
        raise


# ── Helpers ───────────────────────────────────────────────────────

def _action_to_dict(action: AgentAction) -> dict:
    return {
        "action_id": action.action_id,
        "run_id": action.run_id,
        "ticket_id": action.ticket_id,
        "action_type": action.action_type,
        "risk_level": action.risk_level,
        "description": action.description,
        "reason": action.reason,
        "approval_status": action.approval_status,
        "approved_by": action.approved_by,
        "approved_at": action.approved_at.isoformat() if action.approved_at else None,
        "execution_status": action.execution_status,
        "execution_result": action.execution_result,
        "created_at": action.created_at.isoformat(),
    }


def wait_for_approval(run_id: str, timeout_seconds: int = 3600) -> bool:
    """
    Block the calling thread until approval is granted or timeout.

    Args:
        run_id: The agent run waiting for approval
        timeout_seconds: Maximum wait time (default 1 hour)

    Returns:
        True if signaled (approval received), False if timed out
    """
    event = _get_or_create_resume_event(run_id)
    return event.wait(timeout=timeout_seconds)
