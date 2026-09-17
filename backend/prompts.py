"""
prompts.py — System prompts and structured output templates for all agent nodes.

Each prompt is designed to:
  1. Clearly scope what the LLM should do at each step
  2. Instruct the LLM to use provided data (never invent facts)
  3. Produce structured JSON output for reliable parsing
"""
from __future__ import annotations


# ── Node: parse_ticket ────────────────────────────────────────────

PARSE_TICKET_SYSTEM = """You are an operations triage system.
Your task is to extract structured information from an operations ticket description.

Rules:
- Extract ONLY information that is explicitly stated in the ticket
- Do NOT make assumptions about unstated information
- Return valid JSON only
- If customer_id is mentioned as a number (e.g. "Customer 45821"), prefix with "cust-"

Return JSON with this exact structure:
{
  "customer_id": "<extracted customer id with cust- prefix, or null>",
  "issue_type": "<one of: payment_failure, account_issue, service_outage, refund_request, duplicate_payment, security_alert, general>",
  "priority": "<one of: low, medium, high, critical>",
  "summary": "<one sentence summary of the issue>",
  "key_indicators": ["<extracted symptom 1>", "<extracted symptom 2>"]
}"""

PARSE_TICKET_USER = """Parse this operations ticket:

Ticket ID: {ticket_id}
Title: {title}
Description: {description}"""


# ── Node: create_investigation_plan ──────────────────────────────

CREATE_PLAN_SYSTEM = """You are an operations investigation planner.
Your task is to create a structured investigation plan for an operational issue.

Rules:
- Create a specific, ordered list of investigation steps
- Each step should be actionable and specific
- Base the plan on the parsed ticket information
- Do NOT include steps for information already provided

Return JSON with this exact structure:
{
  "plan": [
    {"step": 1, "action": "<action description>", "tool": "<tool name or null>", "rationale": "<why this step>"},
    ...
  ],
  "estimated_duration": "<estimated time in minutes>",
  "priority_focus": "<the most important thing to determine>"
}"""

CREATE_PLAN_USER = """Create an investigation plan for this issue:

Issue Type: {issue_type}
Customer ID: {customer_id}
Priority: {priority}
Summary: {summary}
Key Indicators: {key_indicators}

Available investigation tools:
- get_customer: Retrieve customer profile and account status
- get_recent_transactions: Get recent transactions (with time window)
- get_failed_transactions: Get only failed transactions
- get_related_incidents: Find related open incidents
- get_system_events: Check infrastructure and service events
- search_runbook: Search operational documentation"""


# ── Node: analyze_findings ────────────────────────────────────────

ANALYZE_FINDINGS_SYSTEM = """You are a senior operations analyst.
Your task is to analyze investigation findings and identify the probable cause.

CRITICAL RULES:
1. NEVER fabricate or invent database records, transaction IDs, or system events
2. Base ALL conclusions strictly on the provided evidence
3. Clearly distinguish between: FACTS (from data), PATTERNS (observed), INFERENCE (your analysis)
4. If evidence is insufficient, say so — do not fill gaps with assumptions
5. Cite specific transaction IDs, event IDs, or incident numbers when referencing evidence

Return JSON with this exact structure:
{
  "summary": "<concise summary of what was found>",
  "facts": [
    "<specific fact from data with reference>",
    ...
  ],
  "patterns": [
    "<observed pattern with supporting evidence>",
    ...
  ],
  "probable_cause": "<most likely root cause based on evidence>",
  "confidence": <0.0 to 1.0>,
  "evidence_strength": "<weak|moderate|strong>",
  "gaps": ["<important information that could not be determined>"]
}"""

ANALYZE_FINDINGS_USER = """Analyze the following investigation findings:

TICKET:
{ticket_summary}

CUSTOMER DATA:
{customer_data}

TRANSACTION DATA:
{transaction_data}

FAILED TRANSACTIONS:
{failed_transactions}

RELATED INCIDENTS:
{incidents_data}

SYSTEM EVENTS:
{system_events_data}

RUNBOOK GUIDANCE:
{runbook_context}

Analyze the evidence and identify the probable cause."""


# ── Node: generate_recommendation ────────────────────────────────

GENERATE_RECOMMENDATION_SYSTEM = """You are a senior operations engineer.
Your task is to recommend the appropriate operational action based on the analysis.

Rules:
- Recommend EXACTLY ONE primary action
- The action must be justified by the evidence
- Be specific about WHY this action is needed
- Accurately assess the risk level
- Do NOT recommend destructive actions without very strong evidence

Available action types:
- ADD_TICKET_NOTE: Add an investigative note (low risk)
- UPDATE_TICKET: Change ticket status (low risk)
- CREATE_INCIDENT: Create a new operational incident (medium risk)
- NOTIFY_OPERATIONS: Notify the operations team (medium risk)
- RESTART_SERVICE: Restart a service (high risk, simulated in MVP)
- DISABLE_ACCOUNT: Disable customer account (high risk)

Risk levels:
- LOW: Informational only, no operational impact
- MEDIUM: Operational change, affects monitoring/tracking
- HIGH: Consequential action, significant operational impact

Return JSON with this exact structure:
{
  "action_type": "<ACTION_TYPE>",
  "description": "<clear description of what the action does>",
  "reason": "<why this action is recommended based on the evidence>",
  "risk_level": "<low|medium|high>",
  "requires_approval": <true|false>,
  "urgency": "<immediate|within_hour|within_day>",
  "expected_outcome": "<what we expect to happen if this action is taken>",
  "alternative_actions": ["<alternative 1>", "<alternative 2>"]
}"""

GENERATE_RECOMMENDATION_USER = """Based on this analysis, recommend the appropriate action:

ANALYSIS SUMMARY:
{analysis_summary}

PROBABLE CAUSE:
{probable_cause}

CONFIDENCE:
{confidence}

KEY FACTS:
{key_facts}

RUNBOOK GUIDANCE:
{runbook_guidance}

Ticket Priority: {priority}
Issue Type: {issue_type}"""


# ── Node: validate_action (Policy Engine) ────────────────────────

POLICY_RULES = {
    # action_type → {risk_level, requires_approval, allowed}
    "ADD_TICKET_NOTE":    {"risk_level": "low",    "requires_approval": False, "allowed": True},
    "UPDATE_TICKET":      {"risk_level": "low",    "requires_approval": False, "allowed": True},
    "CREATE_INCIDENT":    {"risk_level": "medium", "requires_approval": True,  "allowed": True},
    "NOTIFY_OPERATIONS":  {"risk_level": "medium", "requires_approval": True,  "allowed": True},
    "RESTART_SERVICE":    {"risk_level": "high",   "requires_approval": True,  "allowed": True},
    "DISABLE_ACCOUNT":    {"risk_level": "high",   "requires_approval": True,  "allowed": True},
}

# Risk threshold for requiring approval
APPROVAL_REQUIRED_FOR = {"medium", "high"}


def get_policy_for_action(action_type: str) -> dict:
    """Return the policy rules for the given action type."""
    return POLICY_RULES.get(
        action_type,
        {"risk_level": "high", "requires_approval": True, "allowed": False}
    )


def validate_action_policy(recommended_action: dict) -> dict:
    """
    Apply the policy engine to a recommended action.

    Returns updated action dict with policy-enforced approval requirements.
    The LLM CANNOT bypass this — it is applied in Python code, not by the LLM.
    """
    action_type = recommended_action.get("action_type", "")
    policy = get_policy_for_action(action_type)

    # Policy ALWAYS overrides LLM recommendation on approval requirement
    requires_approval = policy["risk_level"] in APPROVAL_REQUIRED_FOR

    return {
        **recommended_action,
        "risk_level": policy["risk_level"],           # enforce policy risk level
        "requires_approval": requires_approval,        # enforce approval requirement
        "policy_applied": True,
        "policy_risk_level": policy["risk_level"],
        "allowed": policy["allowed"],
    }
