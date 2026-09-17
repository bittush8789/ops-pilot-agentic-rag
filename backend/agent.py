"""
agent.py — LangGraph workflow for OpsPilot.

Implements a 14-node investigation and action workflow with:
  - Typed state (OpsState)
  - Groq LLM integration via LangChain
  - Tool-based investigation (no raw SQL from LLM)
  - Policy engine for risk validation
  - Human-in-the-loop approval pause
  - LangSmith tracing
  - Full audit logging
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional, TypedDict

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.audit import AuditEvents, audit_workflow_event, log_event
from backend.config import settings
from backend.database import get_db
from backend.approval import create_approval_request
from backend.models import AgentRun, Ticket
from backend.prompts import (
    ANALYZE_FINDINGS_SYSTEM,
    ANALYZE_FINDINGS_USER,
    CREATE_PLAN_SYSTEM,
    CREATE_PLAN_USER,
    GENERATE_RECOMMENDATION_SYSTEM,
    GENERATE_RECOMMENDATION_USER,
    PARSE_TICKET_SYSTEM,
    PARSE_TICKET_USER,
    validate_action_policy,
)
from backend.tools import (
    add_ticket_note,
    create_incident,
    get_customer,
    get_failed_transactions,
    get_related_incidents,
    get_system_events,
    search_runbook_tool,
    get_recent_transactions,
    update_ticket,
)

log = structlog.get_logger(__name__)

# ── LangSmith setup ───────────────────────────────────────────────
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


# ── LLM factory ───────────────────────────────────────────────────

def _get_llm() -> ChatGroq:
    """Return a configured Groq LLM instance."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,           # low temperature for consistent structured output
        max_tokens=4096,
        timeout=60,
    )


def _call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Call the LLM and parse the response as JSON.

    Returns a dict. On parse failure, returns {"error": ..., "raw": ...}.
    """
    llm = _get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        content = response.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json.loads(content)

    except json.JSONDecodeError as e:
        log.warning("LLM returned non-JSON response", error=str(e))
        return {"error": f"JSON parse error: {e}", "raw": content if 'content' in dir() else ""}
    except Exception as e:
        log.error("LLM call failed", error=str(e))
        return {"error": str(e)}


# ── LangGraph State ───────────────────────────────────────────────

class OpsState(TypedDict):
    # Core identifiers
    ticket_id: str
    run_id: str
    trace_id: str

    # Ticket data
    ticket: dict
    parsed_ticket: dict

    # Investigation data
    investigation_plan: list
    customer: dict
    transactions: list
    failed_transactions: dict
    incidents: list
    system_events: list
    runbook_context: list

    # Analysis
    findings: dict
    recommended_action: dict
    validated_action: dict

    # Approval
    approval_status: str          # pending | approved | rejected | not_required
    approved_by: Optional[str]
    approval_action_id: Optional[str]

    # Execution
    execution_result: dict

    # Workflow tracking
    current_node: str
    node_durations: dict          # node_name → duration_ms
    errors: list
    workflow_status: str          # running | paused | completed | failed | rejected


# ── Node implementations ──────────────────────────────────────────

def _update_run_node(run_id: str, node: str, state_snapshot: dict) -> None:
    """Update the AgentRun.current_node in the database."""
    try:
        with get_db() as db:
            run = db.get(AgentRun, run_id)
            if run:
                run.current_node = node
                run.state_snapshot = state_snapshot
    except Exception as e:
        log.warning("Failed to update run node", error=str(e))


def node_parse_ticket(state: OpsState) -> dict:
    """Parse the ticket and extract structured information."""
    log.info("Node: parse_ticket", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "parse_ticket", {})
    start = datetime.utcnow()

    ticket = state["ticket"]
    log_event(
        AuditEvents.TICKET_PARSED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={"ticket_number": ticket.get("ticket_number")},
    )

    try:
        parsed = _call_llm_json(
            PARSE_TICKET_SYSTEM,
            PARSE_TICKET_USER.format(
                ticket_id=ticket.get("ticket_number", state["ticket_id"]),
                title=ticket.get("title", ""),
                description=ticket.get("description", ""),
            ),
        )
    except Exception as e:
        log.error("parse_ticket node failed", error=str(e))
        parsed = {
            "customer_id": ticket.get("customer_id"),
            "issue_type": ticket.get("category", "general"),
            "priority": ticket.get("priority", "medium"),
            "summary": ticket.get("title", ""),
            "key_indicators": [],
        }

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "parsed_ticket": parsed,
        "current_node": "parse_ticket",
        "node_durations": {**state.get("node_durations", {}), "parse_ticket": duration_ms},
    }


def node_create_investigation_plan(state: OpsState) -> dict:
    """Create an ordered investigation plan."""
    log.info("Node: create_investigation_plan", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "create_investigation_plan", {})
    start = datetime.utcnow()

    parsed = state.get("parsed_ticket", {})

    try:
        plan_data = _call_llm_json(
            CREATE_PLAN_SYSTEM,
            CREATE_PLAN_USER.format(
                issue_type=parsed.get("issue_type", "general"),
                customer_id=parsed.get("customer_id", "unknown"),
                priority=parsed.get("priority", "medium"),
                summary=parsed.get("summary", ""),
                key_indicators=json.dumps(parsed.get("key_indicators", [])),
            ),
        )
        plan = plan_data.get("plan", [])
    except Exception as e:
        log.error("create_investigation_plan node failed", error=str(e))
        plan = [
            {"step": 1, "action": "Retrieve customer information", "tool": "get_customer"},
            {"step": 2, "action": "Check recent transactions", "tool": "get_recent_transactions"},
            {"step": 3, "action": "Check failed transactions", "tool": "get_failed_transactions"},
            {"step": 4, "action": "Check related incidents", "tool": "get_related_incidents"},
            {"step": 5, "action": "Check system events", "tool": "get_system_events"},
            {"step": 6, "action": "Search runbook", "tool": "search_runbook"},
        ]

    log_event(
        AuditEvents.PLAN_CREATED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={"steps": len(plan)},
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "investigation_plan": plan,
        "current_node": "create_investigation_plan",
        "node_durations": {**state.get("node_durations", {}), "create_investigation_plan": duration_ms},
    }


def node_investigate_customer(state: OpsState) -> dict:
    """Retrieve customer information."""
    log.info("Node: investigate_customer", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "investigate_customer", {})
    start = datetime.utcnow()

    parsed = state.get("parsed_ticket", {})
    # Use customer_id from parsed ticket, or from ticket data
    customer_id = (
        parsed.get("customer_id")
        or state["ticket"].get("customer_id")
    )

    customer = get_customer(
        customer_id=customer_id or "",
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "customer": customer,
        "current_node": "investigate_customer",
        "node_durations": {**state.get("node_durations", {}), "investigate_customer": duration_ms},
    }


def node_investigate_transactions(state: OpsState) -> dict:
    """Retrieve recent and failed transactions."""
    log.info("Node: investigate_transactions", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "investigate_transactions", {})
    start = datetime.utcnow()

    customer_id = state.get("customer", {}).get("customer_id", "")

    recent = get_recent_transactions(
        customer_id=customer_id,
        limit=10,
        hours=48,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )
    failed = get_failed_transactions(
        customer_id=customer_id,
        hours=48,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "transactions": recent.get("transactions", []),
        "failed_transactions": failed,
        "current_node": "investigate_transactions",
        "node_durations": {**state.get("node_durations", {}), "investigate_transactions": duration_ms},
    }


def node_investigate_incidents(state: OpsState) -> dict:
    """Retrieve related incidents."""
    log.info("Node: investigate_incidents", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "investigate_incidents", {})
    start = datetime.utcnow()

    customer_id = state.get("customer", {}).get("customer_id")
    parsed = state.get("parsed_ticket", {})
    issue_type = parsed.get("issue_type", "")

    # Map issue_type to incident category
    category_map = {
        "payment_failure": "payment_gateway",
        "account_issue": "account_lockout",
        "service_outage": "service_degradation",
    }
    category = category_map.get(issue_type)

    incidents_data = get_related_incidents(
        customer_id=customer_id,
        category=category,
        limit=10,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "incidents": incidents_data.get("incidents", []),
        "current_node": "investigate_incidents",
        "node_durations": {**state.get("node_durations", {}), "investigate_incidents": duration_ms},
    }


def node_investigate_system_events(state: OpsState) -> dict:
    """Retrieve relevant system events."""
    log.info("Node: investigate_system_events", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "investigate_system_events", {})
    start = datetime.utcnow()

    events_data = get_system_events(
        service="payment",     # Focus on payment-related services
        hours=2,
        limit=20,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "system_events": events_data.get("events", []),
        "current_node": "investigate_system_events",
        "node_durations": {**state.get("node_durations", {}), "investigate_system_events": duration_ms},
    }


def node_retrieve_runbook(state: OpsState) -> dict:
    """Search the runbook knowledge base."""
    log.info("Node: retrieve_runbook", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "retrieve_runbook", {})
    start = datetime.utcnow()

    parsed = state.get("parsed_ticket", {})
    failed = state.get("failed_transactions", {})

    # Build a specific search query from the evidence
    dominant_reason = failed.get("dominant_reason", "")
    issue_type = parsed.get("issue_type", "payment failure")
    query = f"{issue_type} {dominant_reason}".strip()

    runbook_data = search_runbook_tool(
        query=query,
        top_k=4,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
    )

    log_event(
        AuditEvents.RUNBOOK_RETRIEVED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={"query": query, "results": runbook_data.get("total_results", 0)},
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "runbook_context": runbook_data.get("runbook_chunks", []),
        "current_node": "retrieve_runbook",
        "node_durations": {**state.get("node_durations", {}), "retrieve_runbook": duration_ms},
    }


def node_analyze_findings(state: OpsState) -> dict:
    """Analyze all collected evidence."""
    log.info("Node: analyze_findings", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "analyze_findings", {})
    start = datetime.utcnow()

    ticket = state["ticket"]
    customer = state.get("customer", {})
    transactions = state.get("transactions", [])
    failed_txns = state.get("failed_transactions", {})
    incidents = state.get("incidents", [])
    events = state.get("system_events", [])
    runbook = state.get("runbook_context", [])

    # Format runbook context (truncated for prompt)
    runbook_text = "\n\n".join([
        f"[{r.get('source', 'unknown')}]\n{r.get('text', '')[:500]}"
        for r in runbook[:2]
    ]) or "No runbook context retrieved."

    try:
        findings = _call_llm_json(
            ANALYZE_FINDINGS_SYSTEM,
            ANALYZE_FINDINGS_USER.format(
                ticket_summary=f"{ticket.get('title', '')} — {ticket.get('description', '')[:200]}",
                customer_data=json.dumps(customer, indent=2)[:800],
                transaction_data=json.dumps(transactions[:5], indent=2)[:800],
                failed_transactions=json.dumps(failed_txns, indent=2)[:800],
                incidents_data=json.dumps(incidents[:3], indent=2)[:600],
                system_events_data=json.dumps(events[:5], indent=2)[:600],
                runbook_context=runbook_text[:1000],
            ),
        )
    except Exception as e:
        log.error("analyze_findings node failed", error=str(e))
        failed_count = failed_txns.get("total_failed", 0)
        findings = {
            "summary": f"Investigation found {failed_count} failed transactions",
            "facts": [f"{failed_count} payment failures detected"],
            "patterns": ["Recurring failures within short timeframe"],
            "probable_cause": "Payment gateway connectivity issue",
            "confidence": 0.7,
            "evidence_strength": "moderate",
            "gaps": [],
        }

    log_event(
        AuditEvents.ANALYSIS_COMPLETED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={
            "probable_cause": findings.get("probable_cause", ""),
            "confidence": findings.get("confidence", 0),
        },
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "findings": findings,
        "current_node": "analyze_findings",
        "node_durations": {**state.get("node_durations", {}), "analyze_findings": duration_ms},
    }


def node_generate_recommendation(state: OpsState) -> dict:
    """Generate a structured action recommendation."""
    log.info("Node: generate_recommendation", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "generate_recommendation", {})
    start = datetime.utcnow()

    findings = state.get("findings", {})
    ticket = state["ticket"]
    parsed = state.get("parsed_ticket", {})
    runbook = state.get("runbook_context", [])

    runbook_guidance = "\n".join([
        r.get("text", "")[:400] for r in runbook[:1]
    ]) or "Follow standard payment failure procedures."

    try:
        recommendation = _call_llm_json(
            GENERATE_RECOMMENDATION_SYSTEM,
            GENERATE_RECOMMENDATION_USER.format(
                analysis_summary=findings.get("summary", ""),
                probable_cause=findings.get("probable_cause", ""),
                confidence=findings.get("confidence", 0),
                key_facts=json.dumps(findings.get("facts", []), indent=2)[:600],
                runbook_guidance=runbook_guidance[:600],
                priority=parsed.get("priority", ticket.get("priority", "medium")),
                issue_type=parsed.get("issue_type", "payment_failure"),
            ),
        )
    except Exception as e:
        log.error("generate_recommendation node failed", error=str(e))
        recommendation = {
            "action_type": "CREATE_INCIDENT",
            "description": "Create a high-priority payment gateway incident",
            "reason": "Multiple payment failures detected with gateway timeout errors",
            "risk_level": "medium",
            "requires_approval": True,
            "urgency": "immediate",
            "expected_outcome": "Incident created for ops team investigation",
        }

    log_event(
        AuditEvents.ACTION_RECOMMENDED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={
            "action_type": recommendation.get("action_type"),
            "risk_level": recommendation.get("risk_level"),
        },
    )

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "recommended_action": recommendation,
        "current_node": "generate_recommendation",
        "node_durations": {**state.get("node_durations", {}), "generate_recommendation": duration_ms},
    }


def node_validate_action(state: OpsState) -> dict:
    """Apply the policy engine to the recommended action."""
    log.info("Node: validate_action", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "validate_action", {})

    recommended = state.get("recommended_action", {})

    # Policy engine runs in Python — LLM cannot bypass this
    validated = validate_action_policy(recommended)

    log.info(
        "Action validated by policy",
        action_type=validated.get("action_type"),
        risk_level=validated.get("risk_level"),
        requires_approval=validated.get("requires_approval"),
    )

    return {
        "validated_action": validated,
        "current_node": "validate_action",
    }


def node_human_approval(state: OpsState) -> dict:
    """
    Create an approval request and pause the workflow.

    The workflow will be resumed externally via the approval API endpoint.
    """
    log.info("Node: human_approval", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "human_approval", {})

    validated = state.get("validated_action", {})

    if not validated.get("requires_approval", True):
        # Low-risk action — no approval needed
        log.info("Action does not require approval, proceeding automatically")
        return {
            "approval_status": "not_required",
            "current_node": "human_approval",
            "workflow_status": "running",
        }

    # Create the approval request
    try:
        approval = create_approval_request(
            ticket_id=state["ticket_id"],
            run_id=state["run_id"],
            action_type=validated.get("action_type", ""),
            risk_level=validated.get("risk_level", "medium"),
            description=validated.get("description", ""),
            reason=validated.get("reason"),
            trace_id=state["trace_id"],
        )
        action_id = approval.get("action_id")
    except Exception as e:
        log.error("Failed to create approval request", error=str(e))
        action_id = None

    # Pause the workflow — it will be resumed by the approval API
    log.info("Workflow paused — awaiting human approval", action_id=action_id)

    return {
        "approval_status": "pending",
        "approval_action_id": action_id,
        "current_node": "human_approval",
        "workflow_status": "paused",
    }


def node_execute_action(state: OpsState) -> dict:
    """Execute the approved action."""
    log.info("Node: execute_action", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "execute_action", {})
    start = datetime.utcnow()

    validated = state.get("validated_action", {})
    action_type = validated.get("action_type", "")
    findings = state.get("findings", {})
    customer = state.get("customer", {})

    result = {"success": False, "message": "Unknown action type"}

    try:
        if action_type == "CREATE_INCIDENT":
            result = create_incident(
                title=validated.get("description", "Payment Gateway Incident"),
                description=(
                    f"{findings.get('summary', '')}\n\n"
                    f"Probable Cause: {findings.get('probable_cause', '')}\n"
                    f"Confidence: {findings.get('confidence', 0):.0%}"
                ),
                category="payment_gateway",
                severity="high",
                customer_id=customer.get("customer_id"),
                affected_service="stripe-payment-api",
                ticket_id=state["ticket_id"],
                trace_id=state["trace_id"],
            )

        elif action_type == "ADD_TICKET_NOTE":
            note = (
                f"Agent Investigation Summary:\n"
                f"{findings.get('summary', '')}\n\n"
                f"Probable Cause: {findings.get('probable_cause', '')}\n"
                f"Recommended Action: {validated.get('description', '')}"
            )
            result = add_ticket_note(
                ticket_id_target=state["ticket_id"],
                note=note,
                author="ops-agent",
                trace_id=state["trace_id"],
            )

        elif action_type == "UPDATE_TICKET":
            result = update_ticket(
                ticket_id_target=state["ticket_id"],
                status="investigating",
                notes=findings.get("summary", ""),
                trace_id=state["trace_id"],
            )

        elif action_type in ("NOTIFY_OPERATIONS", "RESTART_SERVICE", "DISABLE_ACCOUNT"):
            # Simulated in MVP
            result = {
                "success": True,
                "simulated": True,
                "message": f"[SIMULATED] {action_type} would be executed in production",
                "action_type": action_type,
            }

        # Update the AgentAction execution status
        action_id = state.get("approval_action_id")
        if action_id:
            with get_db() as db:
                from backend.models import AgentAction
                action = db.get(AgentAction, action_id)
                if action:
                    action.execution_status = "success" if result.get("success") else "failed"
                    action.execution_result = result

        log_event(
            AuditEvents.ACTION_EXECUTED if result.get("success") else AuditEvents.ACTION_FAILED,
            ticket_id=state["ticket_id"],
            trace_id=state["trace_id"],
            details=result,
        )

    except Exception as e:
        log.error("execute_action node failed", error=str(e))
        result = {"success": False, "error": str(e)}

    duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    return {
        "execution_result": result,
        "current_node": "execute_action",
        "node_durations": {**state.get("node_durations", {}), "execute_action": duration_ms},
    }


def node_update_ticket(state: OpsState) -> dict:
    """Update the ticket status after action execution."""
    log.info("Node: update_ticket", ticket_id=state["ticket_id"])
    _update_run_node(state["run_id"], "update_ticket", {})

    execution = state.get("execution_result", {})
    findings = state.get("findings", {})

    status = "resolved" if execution.get("success") else "investigating"
    note = (
        f"Investigation complete.\n"
        f"Action taken: {state.get('validated_action', {}).get('description', '')}\n"
        f"Result: {'Success' if execution.get('success') else 'Failed'}\n"
        f"Summary: {findings.get('summary', '')}"
    )

    update_ticket(
        ticket_id_target=state["ticket_id"],
        status=status,
        notes=note,
        trace_id=state["trace_id"],
    )

    log_event(
        AuditEvents.TICKET_UPDATED,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={"new_status": status},
    )

    return {"current_node": "update_ticket"}


def node_audit_result(state: OpsState) -> dict:
    """Final audit node — record workflow completion."""
    log.info("Node: audit_result", ticket_id=state["ticket_id"])

    approval_status = state.get("approval_status", "unknown")
    execution = state.get("execution_result", {})

    if approval_status == "rejected":
        final_status = "rejected"
        event_type = AuditEvents.WORKFLOW_COMPLETED
    elif execution.get("success"):
        final_status = "completed"
        event_type = AuditEvents.WORKFLOW_COMPLETED
    else:
        final_status = "completed"
        event_type = AuditEvents.WORKFLOW_COMPLETED

    log_event(
        event_type=event_type,
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={
            "final_status": final_status,
            "approval_status": approval_status,
            "action_type": state.get("validated_action", {}).get("action_type"),
            "execution_success": execution.get("success", False),
            "node_durations": state.get("node_durations", {}),
        },
    )

    # Update agent run to completed
    try:
        with get_db() as db:
            run = db.get(AgentRun, state["run_id"])
            if run:
                run.status = final_status if final_status in ("completed", "rejected") else "completed"
                run.completed_at = datetime.utcnow()
                run.current_node = "audit_result"
                run.state_snapshot = {
                    "approval_status": approval_status,
                    "action_type": state.get("validated_action", {}).get("action_type"),
                    "execution_success": execution.get("success", False),
                }
    except Exception as e:
        log.error("Failed to update agent run on completion", error=str(e))

    return {
        "workflow_status": final_status,
        "current_node": "audit_result",
    }


def node_rejection_audit(state: OpsState) -> dict:
    """Audit node for rejected actions."""
    log.info("Node: rejection_audit", ticket_id=state["ticket_id"])

    log_event(
        AuditEvents.APPROVAL_REJECTED,
        actor=state.get("approved_by", "ops-engineer"),
        ticket_id=state["ticket_id"],
        trace_id=state["trace_id"],
        details={
            "action_type": state.get("validated_action", {}).get("action_type"),
            "reason": "Human operator rejected the recommended action",
        },
    )

    # Update ticket status back to open/investigating
    update_ticket(
        ticket_id_target=state["ticket_id"],
        status="open",
        notes="Agent recommendation was rejected by operator. Manual investigation required.",
        trace_id=state["trace_id"],
    )

    # Update agent run
    try:
        with get_db() as db:
            run = db.get(AgentRun, state["run_id"])
            if run:
                run.status = "rejected"
                run.completed_at = datetime.utcnow()
                run.current_node = "rejection_audit"
    except Exception as e:
        log.error("Failed to update agent run on rejection", error=str(e))

    return {
        "workflow_status": "rejected",
        "current_node": "rejection_audit",
    }


# ── Conditional routing functions ─────────────────────────────────

def route_after_validation(state: OpsState) -> str:
    """Route to human_approval (always — the node itself decides if skip is needed)."""
    return "human_approval"


def route_after_approval(state: OpsState) -> str:
    """
    Route after human_approval based on approval status.

    This is called AFTER the workflow is externally resumed.
    The run's current approval_status determines the route.
    """
    approval_status = state.get("approval_status", "pending")

    if approval_status == "not_required":
        return "execute_action"
    elif approval_status == "approved":
        return "execute_action"
    elif approval_status == "rejected":
        return "rejection_audit"
    else:
        # Still pending — this shouldn't happen in normal flow
        # but handle gracefully
        return "rejection_audit"


def route_after_execution(state: OpsState) -> str:
    """Always proceed to update_ticket after execution."""
    return "update_ticket"


# ── Graph construction ────────────────────────────────────────────

def build_graph() -> CompiledStateGraph:
    """Build and compile the LangGraph workflow."""
    builder = StateGraph(OpsState)

    # Add all nodes
    builder.add_node("parse_ticket", node_parse_ticket)
    builder.add_node("create_investigation_plan", node_create_investigation_plan)
    builder.add_node("investigate_customer", node_investigate_customer)
    builder.add_node("investigate_transactions", node_investigate_transactions)
    builder.add_node("investigate_incidents", node_investigate_incidents)
    builder.add_node("investigate_system_events", node_investigate_system_events)
    builder.add_node("retrieve_runbook", node_retrieve_runbook)
    builder.add_node("analyze_findings", node_analyze_findings)
    builder.add_node("generate_recommendation", node_generate_recommendation)
    builder.add_node("validate_action", node_validate_action)
    builder.add_node("human_approval", node_human_approval)
    builder.add_node("execute_action", node_execute_action)
    builder.add_node("update_ticket", node_update_ticket)
    builder.add_node("audit_result", node_audit_result)
    builder.add_node("rejection_audit", node_rejection_audit)

    # Linear edges through investigation
    builder.add_edge(START, "parse_ticket")
    builder.add_edge("parse_ticket", "create_investigation_plan")
    builder.add_edge("create_investigation_plan", "investigate_customer")
    builder.add_edge("investigate_customer", "investigate_transactions")
    builder.add_edge("investigate_transactions", "investigate_incidents")
    builder.add_edge("investigate_incidents", "investigate_system_events")
    builder.add_edge("investigate_system_events", "retrieve_runbook")
    builder.add_edge("retrieve_runbook", "analyze_findings")
    builder.add_edge("analyze_findings", "generate_recommendation")
    builder.add_edge("generate_recommendation", "validate_action")

    # Conditional edge after validation → always human_approval
    builder.add_conditional_edges(
        "validate_action",
        route_after_validation,
        {"human_approval": "human_approval"},
    )

    # Conditional edge after approval
    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "execute_action": "execute_action",
            "rejection_audit": "rejection_audit",
        },
    )

    builder.add_edge("execute_action", "update_ticket")
    builder.add_edge("update_ticket", "audit_result")
    builder.add_edge("audit_result", END)
    builder.add_edge("rejection_audit", END)

    return builder.compile()


# ── Workflow runner ───────────────────────────────────────────────

# Singleton compiled graph
_graph: Optional[CompiledStateGraph] = None


def get_graph() -> CompiledStateGraph:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_investigation(ticket_id: str, initiated_by: str = "ops-dashboard") -> dict:
    """
    Start an investigation workflow for a ticket.

    This function:
    1. Creates an AgentRun record
    2. Retrieves the ticket from DB
    3. Invokes the LangGraph workflow in a background thread
    4. Returns the run_id immediately (non-blocking)

    The workflow will pause at human_approval and wait for API input.
    """
    import threading

    run_id = str(uuid.uuid4())
    trace_id = f"OPS-{str(uuid.uuid4())[:8].upper()}"

    # Fetch ticket
    with get_db() as db:
        ticket = db.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "ticket_number": ticket.ticket_number,
            "customer_id": ticket.customer_id,
            "title": ticket.title,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
        }

        # Create AgentRun record
        agent_run = AgentRun(
            run_id=run_id,
            ticket_id=ticket_id,
            trace_id=trace_id,
            status="running",
            current_node="start",
        )
        db.add(agent_run)

        # Update ticket to investigating
        ticket.status = "investigating"

    log_event(
        AuditEvents.WORKFLOW_STARTED,
        actor=initiated_by,
        ticket_id=ticket_id,
        trace_id=trace_id,
        details={"run_id": run_id, "ticket_number": ticket_data.get("ticket_number")},
    )

    # Initial state
    initial_state: OpsState = {
        "ticket_id": ticket_id,
        "run_id": run_id,
        "trace_id": trace_id,
        "ticket": ticket_data,
        "parsed_ticket": {},
        "investigation_plan": [],
        "customer": {},
        "transactions": [],
        "failed_transactions": {},
        "incidents": [],
        "system_events": [],
        "runbook_context": [],
        "findings": {},
        "recommended_action": {},
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

    def _run_graph():
        """Run graph in background thread."""
        try:
            graph = get_graph()
            log.info("Starting graph execution", run_id=run_id, ticket_id=ticket_id)

            # Run until the workflow pauses (at human_approval) or completes
            for event in graph.stream(initial_state, stream_mode="values"):
                current = event.get("current_node", "")
                workflow_status = event.get("workflow_status", "running")
                log.debug("Graph step", node=current, status=workflow_status)

                if workflow_status == "paused":
                    log.info("Workflow paused for human approval", run_id=run_id)
                    break

        except Exception as e:
            log.error("Graph execution failed", run_id=run_id, error=str(e))
            log_event(
                AuditEvents.WORKFLOW_FAILED,
                ticket_id=ticket_id,
                trace_id=trace_id,
                details={"run_id": run_id, "error": str(e)},
            )
            try:
                with get_db() as db:
                    run = db.get(AgentRun, run_id)
                    if run:
                        run.status = "failed"
                        run.error_message = str(e)
                        run.completed_at = datetime.utcnow()
            except Exception:
                pass

    # Run the graph in a background thread (non-blocking)
    thread = threading.Thread(target=_run_graph, daemon=True)
    thread.start()

    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "trace_id": trace_id,
        "status": "running",
        "message": "Investigation started",
    }


def resume_investigation(run_id: str, approval_decision: str, approved_by: str = "ops-engineer") -> dict:
    """
    Resume a paused investigation after approval decision.

    Fetches the current state from DB and continues graph execution
    from the human_approval node with the approval decision applied.
    """
    import threading

    # Get the current state snapshot
    with get_db() as db:
        run = db.get(AgentRun, run_id)
        if not run:
            raise ValueError(f"AgentRun {run_id} not found")
        if run.status not in ("paused", "running"):
            raise ValueError(f"Run {run_id} is in status '{run.status}', cannot resume")

        ticket_id = run.ticket_id
        trace_id = run.trace_id

        ticket = db.get(Ticket, ticket_id)
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "ticket_number": ticket.ticket_number,
            "customer_id": ticket.customer_id,
            "title": ticket.title,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
        } if ticket else {}

        # Get the pending action
        from sqlalchemy import select
        from backend.models import AgentAction
        stmt = (
            select(AgentAction)
            .where(AgentAction.run_id == run_id)
            .order_by(AgentAction.created_at.desc())
            .limit(1)
        )
        action = db.execute(stmt).scalars().first()
        action_data = {}
        action_id = None
        if action:
            action_id = action.action_id
            action_data = {
                "action_type": action.action_type,
                "risk_level": action.risk_level,
                "description": action.description,
                "reason": action.reason,
                "requires_approval": True,
                "policy_applied": True,
            }

    def _resume_graph():
        """Resume graph from human_approval with decision applied."""
        try:
            graph = get_graph()

            # Build resumed state
            resumed_state: OpsState = {
                "ticket_id": ticket_id,
                "run_id": run_id,
                "trace_id": trace_id,
                "ticket": ticket_data,
                "parsed_ticket": {},
                "investigation_plan": [],
                "customer": {},
                "transactions": [],
                "failed_transactions": {},
                "incidents": [],
                "system_events": [],
                "runbook_context": [],
                "findings": {},
                "recommended_action": {},
                "validated_action": action_data,
                "approval_status": approval_decision,
                "approved_by": approved_by,
                "approval_action_id": action_id,
                "execution_result": {},
                "current_node": "human_approval",
                "node_durations": {},
                "errors": [],
                "workflow_status": "running",
            }

            # Determine next node based on approval
            if approval_decision == "approved":
                # Execute the action
                exec_result = node_execute_action(resumed_state)
                resumed_state.update(exec_result)

                # Update ticket
                node_update_ticket(resumed_state)

                # Audit result
                node_audit_result(resumed_state)

            else:
                # Rejection path
                node_rejection_audit(resumed_state)

            log.info("Resumed workflow completed", run_id=run_id, decision=approval_decision)

        except Exception as e:
            log.error("Resumed graph execution failed", run_id=run_id, error=str(e))
            try:
                with get_db() as db:
                    run = db.get(AgentRun, run_id)
                    if run:
                        run.status = "failed"
                        run.error_message = str(e)
                        run.completed_at = datetime.utcnow()
            except Exception:
                pass

    thread = threading.Thread(target=_resume_graph, daemon=True)
    thread.start()

    return {
        "run_id": run_id,
        "status": "resuming",
        "approval_decision": approval_decision,
        "message": f"Workflow resuming with decision: {approval_decision}",
    }
