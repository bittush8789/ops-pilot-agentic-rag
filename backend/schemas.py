"""
schemas.py — Pydantic request/response schemas for the API layer.
Kept separate from ORM models to maintain clean boundaries.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared ────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Customer ──────────────────────────────────────────────────────

class CustomerOut(OrmBase):
    customer_id: str
    name: str
    email: str
    account_status: str
    plan: str
    phone: Optional[str] = None
    company: Optional[str] = None
    country: str
    created_at: datetime


# ── Ticket ────────────────────────────────────────────────────────

class TicketOut(OrmBase):
    ticket_id: str
    ticket_number: str
    customer_id: Optional[str] = None
    title: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerOut] = None


class TicketListOut(OrmBase):
    ticket_id: str
    ticket_number: str
    title: str
    priority: str
    status: str
    category: str
    customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


# ── Transaction ───────────────────────────────────────────────────

class TransactionOut(OrmBase):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    status: str
    payment_method: str
    failure_reason: Optional[str] = None
    gateway: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime


# ── Incident ──────────────────────────────────────────────────────

class IncidentOut(OrmBase):
    incident_id: str
    customer_id: Optional[str] = None
    incident_number: str
    category: str
    severity: str
    status: str
    title: str
    description: str
    affected_service: Optional[str] = None
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IncidentCreate(BaseModel):
    customer_id: Optional[str] = None
    ticket_id: Optional[str] = None
    category: str
    severity: str
    title: str
    description: str
    affected_service: Optional[str] = None


# ── System Event ──────────────────────────────────────────────────

class SystemEventOut(OrmBase):
    event_id: str
    service: str
    event_type: str
    severity: str
    message: str
    timestamp: datetime


# ── Agent Run ─────────────────────────────────────────────────────

class AgentRunOut(OrmBase):
    run_id: str
    ticket_id: str
    trace_id: Optional[str] = None
    status: str
    current_node: Optional[str] = None
    state_snapshot: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class InvestigateRequest(BaseModel):
    """Request body for POST /agent/investigate/{ticket_id}"""
    initiated_by: str = Field(default="ops-dashboard", description="Who triggered the investigation")


class InvestigateResponse(BaseModel):
    run_id: str
    ticket_id: str
    trace_id: str
    status: str
    message: str


# ── Agent Action / Approval ───────────────────────────────────────

class AgentActionOut(OrmBase):
    action_id: str
    run_id: Optional[str] = None
    ticket_id: str
    action_type: str
    risk_level: str
    description: str
    reason: Optional[str] = None
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    execution_status: str
    execution_result: Optional[dict] = None
    created_at: datetime


class ApprovalRequest(BaseModel):
    approved_by: str = Field(default="ops-engineer", description="Name of the approver")
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    action_id: str
    approval_status: str
    execution_status: str
    message: str


# ── Audit Log ─────────────────────────────────────────────────────

class AuditLogOut(OrmBase):
    audit_id: str
    trace_id: Optional[str] = None
    ticket_id: Optional[str] = None
    event_type: str
    actor: str
    details: Optional[dict] = None
    timestamp: datetime


# ── Dashboard ─────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    open_tickets: int
    pending_approvals: int
    completed_investigations: int
    successful_actions: int
    total_tickets: int
    high_priority_tickets: int


# ── Health ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Investigation State (live progress) ───────────────────────────

class InvestigationStep(BaseModel):
    node: str
    label: str
    status: str  # pending | running | completed | error | skipped
    result_summary: Optional[str] = None
    duration_ms: Optional[int] = None


class InvestigationStateOut(BaseModel):
    run_id: str
    ticket_id: str
    status: str
    current_node: Optional[str] = None
    steps: list[InvestigationStep] = []
    recommendation: Optional[dict] = None
    pending_action: Optional[AgentActionOut] = None
    trace_id: Optional[str] = None
    error: Optional[str] = None
