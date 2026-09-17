"""
main.py — FastAPI application for OpsPilot.

Serves:
  - REST API for tickets, agent runs, approvals, audit logs
  - Static frontend files
  - Health check endpoint
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.approval import (
    get_approval_by_id,
    get_pending_approvals,
    process_approval,
)
from backend.audit import get_audit_trail
from backend.config import settings
from backend.database import get_db_session, health_check, init_db
from backend.models import (
    AgentAction,
    AgentRun,
    AuditLog,
    Customer,
    Incident,
    SystemEvent,
    Ticket,
    Transaction,
)
from backend.schemas import (
    AgentActionOut,
    AgentRunOut,
    ApprovalRequest,
    ApprovalResponse,
    AuditLogOut,
    DashboardStats,
    HealthResponse,
    InvestigateRequest,
    InvestigateResponse,
    InvestigationStateOut,
    InvestigationStep,
    TicketListOut,
    TicketOut,
    TicketUpdate,
)

log = structlog.get_logger(__name__)

# ── Lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    log.info("OpsPilot starting up")
    try:
        init_db()
        log.info("Database initialized")
    except Exception as e:
        log.error("Database initialization failed", error=str(e))
    yield
    log.info("OpsPilot shutting down")


# ── App creation ──────────────────────────────────────────────────

app = FastAPI(
    title="OpsPilot API",
    description="AI Operations Workflow Agent — Automated ticket investigation and action",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Static frontend ───────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend SPA."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "OpsPilot API is running. Frontend not found."})


# ── Health ────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    db_ok = health_check()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database="connected" if db_ok else "unavailable",
        timestamp=datetime.utcnow(),
    )


# ── Dashboard ─────────────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats(db: Session = Depends(get_db_session)):
    """Get summary statistics for the dashboard."""
    open_tickets = db.execute(
        select(func.count(Ticket.ticket_id)).where(
            Ticket.status.in_(["open", "investigating"])
        )
    ).scalar() or 0

    pending_approvals = db.execute(
        select(func.count(AgentAction.action_id)).where(
            AgentAction.approval_status == "pending"
        )
    ).scalar() or 0

    completed_investigations = db.execute(
        select(func.count(AgentRun.run_id)).where(
            AgentRun.status.in_(["completed", "rejected"])
        )
    ).scalar() or 0

    successful_actions = db.execute(
        select(func.count(AgentAction.action_id)).where(
            AgentAction.execution_status == "success"
        )
    ).scalar() or 0

    total_tickets = db.execute(
        select(func.count(Ticket.ticket_id))
    ).scalar() or 0

    high_priority = db.execute(
        select(func.count(Ticket.ticket_id)).where(
            Ticket.priority.in_(["high", "critical"]),
            Ticket.status.in_(["open", "investigating"]),
        )
    ).scalar() or 0

    return DashboardStats(
        open_tickets=open_tickets,
        pending_approvals=pending_approvals,
        completed_investigations=completed_investigations,
        successful_actions=successful_actions,
        total_tickets=total_tickets,
        high_priority_tickets=high_priority,
    )


# ── Tickets ───────────────────────────────────────────────────────

@app.get("/tickets", response_model=list[TicketListOut], tags=["Tickets"])
async def list_tickets(
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List all tickets with optional filtering."""
    stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)

    if status:
        stmt = stmt.where(Ticket.status == status)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)

    tickets = db.execute(stmt).scalars().all()
    return tickets


@app.get("/tickets/{ticket_id}", response_model=TicketOut, tags=["Tickets"])
async def get_ticket(ticket_id: str, db: Session = Depends(get_db_session)):
    """Get a single ticket with customer details."""
    stmt = (
        select(Ticket)
        .options(joinedload(Ticket.customer))
        .where(Ticket.ticket_id == ticket_id)
    )
    ticket = db.execute(stmt).scalars().first()

    if not ticket:
        # Try by ticket_number
        stmt = (
            select(Ticket)
            .options(joinedload(Ticket.customer))
            .where(Ticket.ticket_number == ticket_id)
        )
        ticket = db.execute(stmt).scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketOut, tags=["Tickets"])
async def update_ticket_endpoint(
    ticket_id: str,
    update: TicketUpdate,
    db: Session = Depends(get_db_session),
):
    """Manually update a ticket."""
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if update.status:
        ticket.status = update.status
    if update.notes:
        ticket.notes = update.notes
    if update.assigned_to:
        ticket.assigned_to = update.assigned_to
    ticket.updated_at = datetime.utcnow()

    db.flush()
    return ticket


# ── Agent ─────────────────────────────────────────────────────────

@app.post(
    "/agent/investigate/{ticket_id}",
    response_model=InvestigateResponse,
    tags=["Agent"],
)
async def start_investigation(
    ticket_id: str,
    request: InvestigateRequest = InvestigateRequest(),
    db: Session = Depends(get_db_session),
):
    """Start an AI investigation for a ticket."""
    # Check ticket exists
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        # Try by number
        stmt = select(Ticket).where(Ticket.ticket_number == ticket_id)
        ticket = db.execute(stmt).scalars().first()
        if ticket:
            ticket_id = ticket.ticket_id

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")

    # Check if there's already a running investigation
    existing_run = db.execute(
        select(AgentRun)
        .where(AgentRun.ticket_id == ticket.ticket_id)
        .where(AgentRun.status.in_(["running", "paused"]))
        .order_by(AgentRun.started_at.desc())
        .limit(1)
    ).scalars().first()

    if existing_run:
        return InvestigateResponse(
            run_id=existing_run.run_id,
            ticket_id=ticket.ticket_id,
            trace_id=existing_run.trace_id or "",
            status=existing_run.status,
            message=f"Investigation already {existing_run.status}",
        )

    # Start the investigation
    from backend.agent import run_investigation
    try:
        result = run_investigation(
            ticket_id=ticket.ticket_id,
            initiated_by=request.initiated_by,
        )
        return InvestigateResponse(
            run_id=result["run_id"],
            ticket_id=result["ticket_id"],
            trace_id=result["trace_id"],
            status=result["status"],
            message=result["message"],
        )
    except Exception as e:
        log.error("Failed to start investigation", ticket_id=ticket_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start investigation: {str(e)}")


@app.get("/agent/runs/{run_id}", response_model=AgentRunOut, tags=["Agent"])
async def get_agent_run(run_id: str, db: Session = Depends(get_db_session)):
    """Get details of an agent run."""
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@app.get("/agent/state/{run_id}", response_model=InvestigationStateOut, tags=["Agent"])
async def get_investigation_state(run_id: str, db: Session = Depends(get_db_session)):
    """
    Get the live investigation state for the frontend progress panel.
    Polls this endpoint to show real-time investigation progress.
    """
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    # Define all possible nodes in order
    all_nodes = [
        ("parse_ticket", "Ticket Parsed"),
        ("create_investigation_plan", "Investigation Plan Created"),
        ("investigate_customer", "Customer Lookup"),
        ("investigate_transactions", "Transaction Analysis"),
        ("investigate_incidents", "Incident Search"),
        ("investigate_system_events", "System Events Check"),
        ("retrieve_runbook", "Runbook Retrieved"),
        ("analyze_findings", "Findings Analyzed"),
        ("generate_recommendation", "Action Recommended"),
        ("validate_action", "Risk Validated"),
        ("human_approval", "Awaiting Approval"),
        ("execute_action", "Action Executed"),
        ("update_ticket", "Ticket Updated"),
        ("audit_result", "Audit Complete"),
    ]

    current_node = run.current_node or "start"
    node_order = [n[0] for n in all_nodes]
    current_idx = node_order.index(current_node) if current_node in node_order else -1

    steps = []
    for i, (node, label) in enumerate(all_nodes):
        if i < current_idx:
            status = "completed"
        elif i == current_idx:
            status = "running" if run.status == "running" else (
                "completed" if run.status in ("completed", "rejected") else "paused"
            )
        else:
            status = "pending"

        steps.append(InvestigationStep(
            node=node,
            label=label,
            status=status,
        ))

    # Get pending action if any
    pending_action = None
    if run.status == "paused":
        action_stmt = (
            select(AgentAction)
            .where(AgentAction.run_id == run_id)
            .where(AgentAction.approval_status == "pending")
            .order_by(AgentAction.created_at.desc())
            .limit(1)
        )
        action = db.execute(action_stmt).scalars().first()
        if action:
            pending_action = AgentActionOut.model_validate(action)

    # Get recommendation from state snapshot
    recommendation = None
    snapshot = run.state_snapshot or {}
    if snapshot:
        recommendation = snapshot

    return InvestigationStateOut(
        run_id=run_id,
        ticket_id=run.ticket_id,
        status=run.status,
        current_node=run.current_node,
        steps=steps,
        recommendation=recommendation,
        pending_action=pending_action,
        trace_id=run.trace_id,
        error=run.error_message,
    )


@app.get("/agent/runs", response_model=list[AgentRunOut], tags=["Agent"])
async def list_agent_runs(
    ticket_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_session),
):
    """List agent runs with optional filtering."""
    stmt = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if ticket_id:
        stmt = stmt.where(AgentRun.ticket_id == ticket_id)
    if status:
        stmt = stmt.where(AgentRun.status == status)
    runs = db.execute(stmt).scalars().all()
    return runs


# ── Approvals ─────────────────────────────────────────────────────

@app.get("/approvals", response_model=list[AgentActionOut], tags=["Approvals"])
async def list_pending_approvals():
    """Get all pending approval requests."""
    approvals = get_pending_approvals()
    return approvals


@app.get("/approvals/{action_id}", response_model=AgentActionOut, tags=["Approvals"])
async def get_approval(action_id: str):
    """Get a specific approval request."""
    approval = get_approval_by_id(action_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@app.post("/approvals/{action_id}/approve", response_model=ApprovalResponse, tags=["Approvals"])
async def approve_action(
    action_id: str,
    request: ApprovalRequest = ApprovalRequest(),
):
    """Approve an agent action recommendation."""
    try:
        action = process_approval(
            action_id=action_id,
            decision="approved",
            approved_by=request.approved_by,
            notes=request.notes,
        )

        # Resume the workflow
        run_id = action.get("run_id")
        if run_id:
            from backend.agent import resume_investigation
            resume_investigation(
                run_id=run_id,
                approval_decision="approved",
                approved_by=request.approved_by,
            )

        return ApprovalResponse(
            action_id=action_id,
            approval_status="approved",
            execution_status="executing",
            message="Action approved and execution started",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Approval failed", action_id=action_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Approval processing failed: {str(e)}")


@app.post("/approvals/{action_id}/reject", response_model=ApprovalResponse, tags=["Approvals"])
async def reject_action(
    action_id: str,
    request: ApprovalRequest = ApprovalRequest(),
):
    """Reject an agent action recommendation."""
    try:
        action = process_approval(
            action_id=action_id,
            decision="rejected",
            approved_by=request.approved_by,
            notes=request.notes,
        )

        # Resume the workflow (rejection path)
        run_id = action.get("run_id")
        if run_id:
            from backend.agent import resume_investigation
            resume_investigation(
                run_id=run_id,
                approval_decision="rejected",
                approved_by=request.approved_by,
            )

        return ApprovalResponse(
            action_id=action_id,
            approval_status="rejected",
            execution_status="skipped",
            message="Action rejected — workflow ended",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Rejection failed", action_id=action_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Rejection processing failed: {str(e)}")


# ── Audit ─────────────────────────────────────────────────────────

@app.get("/audit/{ticket_id}", response_model=list[AuditLogOut], tags=["Audit"])
async def get_ticket_audit(ticket_id: str):
    """Get the complete audit trail for a ticket."""
    trail = get_audit_trail(ticket_id)
    return trail


@app.get("/audit", response_model=list[AuditLogOut], tags=["Audit"])
async def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    """Get recent audit logs."""
    stmt = (
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    logs = db.execute(stmt).scalars().all()
    return logs


# ── AI Assistant (Agentic RAG) ──────────────────────────────────

from pydantic import BaseModel, Field

class AssistantChatRequest(BaseModel):
    message: str = Field(..., description="User question or operational query")
    history: Optional[list[dict]] = Field(default=None, description="Prior conversation turns")
    ticket_id: Optional[str] = Field(default=None, description="Optional ticket context")

class AssistantStepOut(BaseModel):
    step_name: str
    status: str
    details: str
    icon: str = "⚡"

class AssistantCitationOut(BaseModel):
    source: str
    filename: str
    relevance: float
    badge: str

class AssistantChatResponse(BaseModel):
    answer: str
    steps: list[AssistantStepOut]
    citations: list[AssistantCitationOut]
    suggested_actions: list[str]
    query_plan: dict

@app.post("/api/assistant/chat", response_model=AssistantChatResponse, tags=["AI Assistant"])
async def assistant_chat(req: AssistantChatRequest):
    """
    Agentic RAG Assistant endpoint.
    Performs query decomposition, runbook vector retrieval, self-RAG relevance grading,
    and grounded operational synthesis with reasoning traces.
    """
    from backend.agentic_rag import agentic_rag_service
    clean_msg = req.message.strip()
    if not clean_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        result = await agentic_rag_service.answer_query(
            message=clean_msg,
            history=req.history,
            ticket_id=req.ticket_id,
        )
        return result
    except Exception as e:
        log.error("AI Assistant chat failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Assistant error: {str(e)}")

@app.get("/api/assistant/prompts", tags=["AI Assistant"])
async def get_assistant_prompts():
    """Return curated quick-start prompts for the OpsPilot Copilot widget."""
    return [
        {"title": "Gateway Timeout", "prompt": "How do I troubleshoot a payment gateway timeout incident?", "category": "Payments"},
        {"title": "Duplicate Charges", "prompt": "What is the runbook procedure when a customer reports duplicate charges?", "category": "Integrity"},
        {"title": "Customer 45821 Status", "prompt": "What runbook applies to Customer 45821 payment timeout failures?", "category": "Customer"},
        {"title": "Failed Refund", "prompt": "What steps are required when a Stripe card refund fails?", "category": "Refunds"},
        {"title": "Account Unlock Policy", "prompt": "What are the mandatory approval rules before unlocking an account?", "category": "Security"},
    ]


# ── Seed endpoint (dev only) ──────────────────────────────────────

@app.post("/admin/seed", tags=["Admin"], include_in_schema=settings.app_env == "development")
async def run_seed():
    """Run the database seed (development only)."""
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Seed endpoint disabled in production")

    try:
        from backend.seed import run_seed as _run_seed
        result = _run_seed()
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level="info",
    )
