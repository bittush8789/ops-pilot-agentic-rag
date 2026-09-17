"""
models.py — SQLAlchemy ORM models for OpsPilot.

Tables:
    customers, tickets, transactions, incidents,
    system_events, agent_runs, agent_actions, audit_logs
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ── Helper ────────────────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ── Customers ─────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    account_status: Mapped[str] = mapped_column(
        Enum("active", "suspended", "closed", "pending", name="account_status_enum"),
        default="active",
    )
    plan: Mapped[str] = mapped_column(
        Enum("free", "starter", "professional", "enterprise", name="plan_enum"),
        default="starter",
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), default="US")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="customer")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="customer")
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="customer")

    __table_args__ = (
        Index("ix_customers_email", "email"),
        Index("ix_customers_status", "account_status"),
    )


# ── Tickets ───────────────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        Enum("payment_failure", "account_issue", "service_outage", "refund_request",
             "duplicate_payment", "security_alert", "general", name="ticket_category_enum"),
        default="general",
    )
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="priority_enum"),
        default="medium",
    )
    status: Mapped[str] = mapped_column(
        Enum("open", "investigating", "pending_approval", "resolved", "closed", "rejected",
             name="ticket_status_enum"),
        default="open",
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="tickets")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="ticket")
    agent_actions: Mapped[list["AgentAction"]] = relationship("AgentAction", back_populates="ticket")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="ticket")

    __table_args__ = (
        Index("ix_tickets_customer_id", "customer_id"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_number", "ticket_number"),
    )


# ── Transactions ──────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(
        Enum("success", "failed", "pending", "refunded", "disputed", name="transaction_status_enum"),
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(
        Enum("credit_card", "debit_card", "bank_transfer", "paypal", "stripe", "wire",
             name="payment_method_enum"),
        default="credit_card",
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        Enum(
            "PAYMENT_GATEWAY_TIMEOUT",
            "INSUFFICIENT_FUNDS",
            "CARD_DECLINED",
            "EXPIRED_CARD",
            "INVALID_CVV",
            "BANK_REJECT",
            "NETWORK_ERROR",
            "DUPLICATE_TRANSACTION",
            "FRAUD_SUSPECTED",
            name="failure_reason_enum",
        )
    )
    gateway: Mapped[Optional[str]] = mapped_column(String(100))
    reference_id: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_customer_id", "customer_id"),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_created_at", "created_at"),
    )


# ── Incidents ─────────────────────────────────────────────────────

class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True
    )
    incident_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(
        Enum("payment_gateway", "account_lockout", "service_degradation", "security_breach",
             "data_issue", "network", "general", name="incident_category_enum"),
        default="general",
    )
    severity: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="incident_severity_enum"),
        default="medium",
    )
    status: Mapped[str] = mapped_column(
        Enum("open", "investigating", "mitigated", "resolved", "closed", name="incident_status_enum"),
        default="open",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_service: Mapped[Optional[str]] = mapped_column(String(200))
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="incidents")

    __table_args__ = (
        Index("ix_incidents_customer_id", "customer_id"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_category", "category"),
    )


# ── System Events ─────────────────────────────────────────────────

class SystemEvent(Base):
    __tablename__ = "system_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(
        Enum("error", "warning", "info", "critical", "timeout", "degradation",
             name="event_type_enum"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="event_severity_enum"),
        default="medium",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_ip: Mapped[Optional[str]] = mapped_column(String(50))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(200))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)

    __table_args__ = (
        Index("ix_system_events_service", "service"),
        Index("ix_system_events_severity", "severity"),
        Index("ix_system_events_timestamp", "timestamp"),
        Index("ix_system_events_event_type", "event_type"),
    )


# ── Agent Runs ────────────────────────────────────────────────────

class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(200))
    langsmith_run_id: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        Enum("running", "paused", "completed", "failed", "rejected", name="run_status_enum"),
        default="running",
    )
    current_node: Mapped[Optional[str]] = mapped_column(String(100))
    state_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="agent_runs")

    __table_args__ = (
        Index("ix_agent_runs_ticket_id", "ticket_id"),
        Index("ix_agent_runs_status", "status"),
    )


# ── Agent Actions ─────────────────────────────────────────────────

class AgentAction(Base):
    __tablename__ = "agent_actions"

    action_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("agent_runs.run_id", ondelete="SET NULL"), nullable=True
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(
        Enum(
            "ADD_TICKET_NOTE", "UPDATE_TICKET", "CREATE_INCIDENT",
            "NOTIFY_OPERATIONS", "RESTART_SERVICE", "DISABLE_ACCOUNT",
            name="action_type_enum",
        ),
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", name="risk_level_enum"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "not_required", name="approval_status_enum"),
        default="pending",
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(200))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    execution_status: Mapped[str] = mapped_column(
        Enum("pending", "executing", "success", "failed", "skipped", name="exec_status_enum"),
        default="pending",
    )
    execution_result: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="agent_actions")

    __table_args__ = (
        Index("ix_agent_actions_ticket_id", "ticket_id"),
        Index("ix_agent_actions_approval_status", "approval_status"),
    )


# ── Audit Logs ────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trace_id: Mapped[Optional[str]] = mapped_column(String(200))
    ticket_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tickets.ticket_id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Relationships
    ticket: Mapped[Optional["Ticket"]] = relationship("Ticket", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_ticket_id", "ticket_id"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_trace_id", "trace_id"),
    )
