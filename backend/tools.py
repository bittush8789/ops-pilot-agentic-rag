"""
tools.py — Controlled, validated agent tools for OpsPilot.

Architecture:
  LLM → Approved Tool → Validated Input → SQLAlchemy → MySQL

Rules:
  - All read tools are strictly read-only (SELECT only)
  - All write tools require validated inputs
  - No arbitrary SQL is passed from the LLM
  - All tool calls are audit-logged
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import structlog
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select, func

from backend.audit import audit_tool_call, audit_tool_result
from backend.database import get_db
from backend.models import (
    Customer,
    Incident,
    SystemEvent,
    Ticket,
    Transaction,
)
from backend.rag import search_runbook

log = structlog.get_logger(__name__)


# ── Tool input validation models ──────────────────────────────────

class GetCustomerInput(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=50)


class GetTransactionsInput(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=50)
    limit: int = Field(default=10, ge=1, le=100)
    hours: int = Field(default=24, ge=1, le=720)


class GetIncidentsInput(BaseModel):
    customer_id: Optional[str] = Field(default=None, max_length=50)
    category: Optional[str] = Field(default=None)
    severity: Optional[str] = Field(default=None)
    limit: int = Field(default=10, ge=1, le=50)


class GetSystemEventsInput(BaseModel):
    service: Optional[str] = Field(default=None, max_length=200)
    severity: Optional[str] = Field(default=None)
    hours: int = Field(default=2, ge=1, le=168)
    limit: int = Field(default=20, ge=1, le=100)


class SearchRunbookInput(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=4, ge=1, le=10)


class CreateIncidentInput(BaseModel):
    customer_id: Optional[str] = Field(default=None, max_length=50)
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    category: str = Field(default="payment_gateway")
    severity: str = Field(default="high")
    affected_service: Optional[str] = Field(default=None, max_length=200)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"low", "medium", "high", "critical"}
        if v not in valid:
            raise ValueError(f"severity must be one of {valid}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {
            "payment_gateway", "account_lockout", "service_degradation",
            "security_breach", "data_issue", "network", "general"
        }
        if v not in valid:
            return "general"
        return v


class UpdateTicketInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, max_length=50)
    status: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid = {"open", "investigating", "pending_approval", "resolved", "closed", "rejected"}
        if v not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v


class AddTicketNoteInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, max_length=50)
    note: str = Field(..., min_length=5, max_length=5000)
    author: str = Field(default="ops-agent")


# ── Read Tools (Investigation) ────────────────────────────────────

def get_customer(
    customer_id: str,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Retrieve customer profile by customer_id.

    Read-only. Returns customer information or error dict.
    """
    inputs = GetCustomerInput(customer_id=customer_id)
    audit_tool_call("get_customer", {"customer_id": customer_id}, ticket_id, trace_id)
    start = time.time()

    try:
        with get_db() as db:
            customer = db.get(Customer, inputs.customer_id)
            if not customer:
                result = {"error": f"Customer {customer_id} not found", "found": False}
            else:
                result = {
                    "found": True,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "email": customer.email,
                    "account_status": customer.account_status,
                    "plan": customer.plan,
                    "company": customer.company,
                    "country": customer.country,
                    "created_at": customer.created_at.isoformat(),
                }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "get_customer",
            f"Customer {'found' if result.get('found') else 'not found'}: {customer_id}",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("get_customer failed", customer_id=customer_id, error=str(e))
        return {"error": str(e), "found": False}


def get_recent_transactions(
    customer_id: str,
    limit: int = 10,
    hours: int = 24,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Get recent transactions for a customer within the last N hours.

    Read-only. Ordered by created_at descending.
    """
    inputs = GetTransactionsInput(customer_id=customer_id, limit=limit, hours=hours)
    audit_tool_call(
        "get_recent_transactions",
        {"customer_id": customer_id, "limit": limit, "hours": hours},
        ticket_id, trace_id,
    )
    start = time.time()

    try:
        cutoff = datetime.utcnow() - timedelta(hours=inputs.hours)
        with get_db() as db:
            stmt = (
                select(Transaction)
                .where(
                    and_(
                        Transaction.customer_id == inputs.customer_id,
                        Transaction.created_at >= cutoff,
                    )
                )
                .order_by(Transaction.created_at.desc())
                .limit(inputs.limit)
            )
            transactions = db.execute(stmt).scalars().all()

            result = {
                "customer_id": customer_id,
                "period_hours": hours,
                "total": len(transactions),
                "transactions": [
                    {
                        "transaction_id": t.transaction_id,
                        "amount": t.amount,
                        "currency": t.currency,
                        "status": t.status,
                        "payment_method": t.payment_method,
                        "failure_reason": t.failure_reason,
                        "gateway": t.gateway,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in transactions
                ],
            }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "get_recent_transactions",
            f"{result['total']} transactions in last {hours}h for {customer_id}",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("get_recent_transactions failed", customer_id=customer_id, error=str(e))
        return {"error": str(e), "transactions": [], "total": 0}


def get_failed_transactions(
    customer_id: str,
    hours: int = 24,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Get all failed transactions for a customer within the last N hours.

    Read-only. Groups by failure_reason.
    """
    audit_tool_call(
        "get_failed_transactions",
        {"customer_id": customer_id, "hours": hours},
        ticket_id, trace_id,
    )
    start = time.time()

    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with get_db() as db:
            stmt = (
                select(Transaction)
                .where(
                    and_(
                        Transaction.customer_id == customer_id,
                        Transaction.status == "failed",
                        Transaction.created_at >= cutoff,
                    )
                )
                .order_by(Transaction.created_at.desc())
            )
            failed_txns = db.execute(stmt).scalars().all()

            # Group by failure_reason
            by_reason: dict[str, int] = {}
            for t in failed_txns:
                reason = t.failure_reason or "UNKNOWN"
                by_reason[reason] = by_reason.get(reason, 0) + 1

            result = {
                "customer_id": customer_id,
                "period_hours": hours,
                "total_failed": len(failed_txns),
                "failure_breakdown": by_reason,
                "dominant_reason": max(by_reason, key=by_reason.get) if by_reason else None,
                "failed_transactions": [
                    {
                        "transaction_id": t.transaction_id,
                        "amount": t.amount,
                        "status": t.status,
                        "failure_reason": t.failure_reason,
                        "gateway": t.gateway,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in failed_txns
                ],
            }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "get_failed_transactions",
            f"{result['total_failed']} failed transactions for {customer_id}",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("get_failed_transactions failed", customer_id=customer_id, error=str(e))
        return {"error": str(e), "failed_transactions": [], "total_failed": 0}


def get_related_incidents(
    customer_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 10,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Get incidents related to a customer or category.

    Read-only. Returns open/investigating incidents ordered by severity.
    """
    audit_tool_call(
        "get_related_incidents",
        {"customer_id": customer_id, "category": category},
        ticket_id, trace_id,
    )
    start = time.time()

    try:
        with get_db() as db:
            conditions = [
                Incident.status.in_(["open", "investigating", "mitigated"])
            ]
            if customer_id:
                conditions.append(Incident.customer_id == customer_id)
            if category:
                conditions.append(Incident.category == category)
            if severity:
                conditions.append(Incident.severity == severity)

            stmt = (
                select(Incident)
                .where(and_(*conditions))
                .order_by(Incident.created_at.desc())
                .limit(limit)
            )
            incidents = db.execute(stmt).scalars().all()

            result = {
                "total": len(incidents),
                "incidents": [
                    {
                        "incident_id": i.incident_id,
                        "incident_number": i.incident_number,
                        "category": i.category,
                        "severity": i.severity,
                        "status": i.status,
                        "title": i.title,
                        "description": i.description[:300],
                        "affected_service": i.affected_service,
                        "created_at": i.created_at.isoformat(),
                    }
                    for i in incidents
                ],
            }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "get_related_incidents",
            f"{result['total']} related incidents",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("get_related_incidents failed", error=str(e))
        return {"error": str(e), "incidents": [], "total": 0}


def get_system_events(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    hours: int = 2,
    limit: int = 20,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Get recent system events, optionally filtered by service and severity.

    Read-only. Useful for correlating infrastructure events with customer issues.
    """
    audit_tool_call(
        "get_system_events",
        {"service": service, "severity": severity, "hours": hours},
        ticket_id, trace_id,
    )
    start = time.time()

    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with get_db() as db:
            conditions = [SystemEvent.timestamp >= cutoff]
            if service:
                conditions.append(SystemEvent.service.ilike(f"%{service}%"))
            if severity:
                conditions.append(SystemEvent.severity == severity)

            stmt = (
                select(SystemEvent)
                .where(and_(*conditions))
                .order_by(SystemEvent.timestamp.desc())
                .limit(limit)
            )
            events = db.execute(stmt).scalars().all()

            result = {
                "period_hours": hours,
                "total": len(events),
                "events": [
                    {
                        "event_id": e.event_id,
                        "service": e.service,
                        "event_type": e.event_type,
                        "severity": e.severity,
                        "message": e.message,
                        "correlation_id": e.correlation_id,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in events
                ],
            }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "get_system_events",
            f"{result['total']} system events in last {hours}h",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("get_system_events failed", error=str(e))
        return {"error": str(e), "events": [], "total": 0}


def search_runbook_tool(
    query: str,
    top_k: int = 4,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Search the operational runbook knowledge base for relevant guidance.

    Uses Pinecone vector search with sentence-transformer embeddings.
    """
    inputs = SearchRunbookInput(query=query, top_k=top_k)
    audit_tool_call("search_runbook", {"query": query[:100]}, ticket_id, trace_id)
    start = time.time()

    try:
        from backend.rag import search_runbook
        results = search_runbook(inputs.query, inputs.top_k)

        result = {
            "query": query,
            "total_results": len(results),
            "runbook_chunks": results,
        }

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "search_runbook",
            f"{len(results)} runbook sections found for '{query[:50]}'",
            duration_ms, ticket_id, trace_id,
        )
        return result

    except Exception as e:
        log.error("search_runbook_tool failed", error=str(e))
        return {"error": str(e), "runbook_chunks": [], "total_results": 0}


# ── Write Tools (Actions) ─────────────────────────────────────────

def create_incident(
    title: str,
    description: str,
    category: str = "payment_gateway",
    severity: str = "high",
    customer_id: Optional[str] = None,
    affected_service: Optional[str] = None,
    ticket_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Create a new operational incident.

    WRITE TOOL — requires prior approval for medium/high risk actions.
    """
    inputs = CreateIncidentInput(
        customer_id=customer_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        affected_service=affected_service,
    )
    audit_tool_call(
        "create_incident",
        {"title": title[:100], "severity": severity, "category": category},
        ticket_id, trace_id,
    )
    start = time.time()

    try:
        with get_db() as db:
            # Generate incident number
            count = db.execute(func.count(Incident.incident_id)).scalar() or 0
            incident_number = f"SINC-{count + 100:04d}"

            incident = Incident(
                customer_id=inputs.customer_id,
                incident_number=incident_number,
                category=inputs.category,
                severity=inputs.severity,
                status="open",
                title=inputs.title,
                description=inputs.description,
                affected_service=inputs.affected_service,
            )
            db.add(incident)
            db.flush()
            incident_id = incident.incident_id

        from backend.audit import log_event, AuditEvents
        log_event(
            event_type=AuditEvents.INCIDENT_CREATED,
            actor="ops-agent",
            ticket_id=ticket_id,
            trace_id=trace_id,
            details={
                "incident_id": incident_id,
                "incident_number": incident_number,
                "severity": severity,
                "category": category,
            },
        )

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "create_incident",
            f"Created incident {incident_number} severity={severity}",
            duration_ms, ticket_id, trace_id,
        )

        return {
            "success": True,
            "incident_id": incident_id,
            "incident_number": incident_number,
            "title": title,
            "severity": severity,
            "category": category,
            "status": "open",
        }

    except Exception as e:
        log.error("create_incident failed", error=str(e))
        return {"success": False, "error": str(e)}


def update_ticket(
    ticket_id_target: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict:
    """
    Update ticket status or notes.

    WRITE TOOL — records audit event.
    """
    inputs = UpdateTicketInput(ticket_id=ticket_id_target, status=status, notes=notes)
    audit_tool_call(
        "update_ticket",
        {"ticket_id": ticket_id_target, "status": status},
        ticket_id_target, trace_id,
    )
    start = time.time()

    try:
        with get_db() as db:
            ticket = db.get(Ticket, inputs.ticket_id)
            if not ticket:
                return {"success": False, "error": f"Ticket {ticket_id_target} not found"}

            if inputs.status:
                ticket.status = inputs.status
            if inputs.notes:
                existing = ticket.notes or ""
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                ticket.notes = f"{existing}\n\n[{timestamp}] {inputs.notes}".strip()
            ticket.updated_at = datetime.utcnow()

        from backend.audit import log_event, AuditEvents
        log_event(
            event_type=AuditEvents.TICKET_UPDATED,
            actor="ops-agent",
            ticket_id=ticket_id_target,
            trace_id=trace_id,
            details={"status": status, "has_notes": bool(notes)},
        )

        duration_ms = int((time.time() - start) * 1000)
        audit_tool_result(
            "update_ticket",
            f"Ticket {ticket_id_target} updated: status={status}",
            duration_ms, ticket_id_target, trace_id,
        )
        return {"success": True, "ticket_id": ticket_id_target, "new_status": status}

    except Exception as e:
        log.error("update_ticket failed", ticket_id=ticket_id_target, error=str(e))
        return {"success": False, "error": str(e)}


def add_ticket_note(
    ticket_id_target: str,
    note: str,
    author: str = "ops-agent",
    trace_id: Optional[str] = None,
) -> dict:
    """
    Append a note to a ticket.

    WRITE TOOL — lower risk than update_ticket.
    """
    inputs = AddTicketNoteInput(ticket_id=ticket_id_target, note=note, author=author)
    start = time.time()

    try:
        with get_db() as db:
            ticket = db.get(Ticket, inputs.ticket_id)
            if not ticket:
                return {"success": False, "error": f"Ticket {ticket_id_target} not found"}

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            existing = ticket.notes or ""
            ticket.notes = f"{existing}\n\n[{timestamp}] [{author}] {inputs.note}".strip()
            ticket.updated_at = datetime.utcnow()

        return {"success": True, "ticket_id": ticket_id_target}

    except Exception as e:
        log.error("add_ticket_note failed", ticket_id=ticket_id_target, error=str(e))
        return {"success": False, "error": str(e)}
