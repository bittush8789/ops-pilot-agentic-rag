"""
conftest.py — Shared test fixtures for OpsPilot test suite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Customer, Ticket, Transaction, Incident, SystemEvent


# ── In-memory SQLite engine for tests ────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    """SQLite in-memory engine for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Provide a transactional test session that rolls back after each test."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ── Sample data fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_customer(db_session):
    """Create and return a test customer."""
    customer = Customer(
        customer_id="cust-45821",
        name="Rajesh Mehta",
        email="rajesh.mehta@techcorp.io",
        account_status="active",
        plan="enterprise",
        company="TechCorp Solutions",
        country="US",
    )
    db_session.add(customer)
    db_session.flush()
    return customer


@pytest.fixture
def sample_ticket(db_session, sample_customer):
    """Create and return a test ticket INC-1042."""
    ticket = Ticket(
        ticket_id="tick-1042",
        ticket_number="INC-1042",
        customer_id="cust-45821",
        title="Multiple payment failures — Customer 45821",
        description=(
            "Customer 45821 has experienced multiple payment failures in the last 30 minutes. "
            "Please investigate and recommend an action."
        ),
        category="payment_failure",
        priority="high",
        status="open",
    )
    db_session.add(ticket)
    db_session.flush()
    return ticket


@pytest.fixture
def sample_failed_transactions(db_session, sample_customer):
    """Create failed transactions for the test customer."""
    from datetime import datetime, timedelta
    txns = []
    for i in range(5):
        txn = Transaction(
            transaction_id=f"txn-test-{i:03d}",
            customer_id="cust-45821",
            amount=1299.00,
            currency="USD",
            status="failed",
            payment_method="credit_card",
            failure_reason="PAYMENT_GATEWAY_TIMEOUT",
            gateway="stripe-v2",
        )
        db_session.add(txn)
        txns.append(txn)
    db_session.flush()
    return txns


@pytest.fixture
def sample_incident(db_session, sample_customer):
    """Create a related incident."""
    incident = Incident(
        incident_id="inc-test-001",
        customer_id="cust-45821",
        incident_number="SINC-001",
        category="payment_gateway",
        severity="high",
        status="open",
        title="Payment gateway timeouts",
        description="Customer experiencing repeated payment gateway timeouts.",
        affected_service="stripe-payment-api",
    )
    db_session.add(incident)
    db_session.flush()
    return incident


@pytest.fixture
def sample_system_events(db_session):
    """Create payment-related system events."""
    events = []
    for i, (svc, etype, sev, msg) in enumerate([
        ("payment-api", "timeout", "high", "Gateway timeout: stripe-v2 connection timed out"),
        ("payment-api", "error", "high", "HTTP 504 from stripe-v2 /v1/charges"),
        ("payment-api", "critical", "critical", "Circuit breaker OPEN: stripe-v2"),
        ("alertmanager", "critical", "critical", "ALERT: PaymentGatewayCircuitBreakerOpen"),
    ]):
        event = SystemEvent(
            event_id=f"evt-test-{i:03d}",
            service=svc,
            event_type=etype,
            severity=sev,
            message=msg,
        )
        db_session.add(event)
        events.append(event)
    db_session.flush()
    return events
