# Incident Escalation Runbook

**Document ID:** RB-OPS-001  
**Version:** 3.0  
**Owner:** Operations Team  
**Last Updated:** 2024-01-22  
**Classification:** Internal Operations  

---

## Overview

This runbook defines the escalation procedures for operational incidents. Proper escalation ensures the right people are engaged quickly to minimize customer impact.

---

## Incident Severity Levels

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| LOW | Minor issue, no SLA impact, single customer affected | 4 hours | Single card decline |
| MEDIUM | Multiple customers affected or SLA at risk | 1 hour | Payment processing delays |
| HIGH | Significant customer impact, revenue at risk | 15 minutes | Gateway degradation, 10+ customers |
| CRITICAL | Service-wide outage, all payments affected | 5 minutes | Circuit breaker OPEN, full outage |

---

## Escalation Matrix

### Level 1 — Operations Engineer (You)

**Responsible for:**
- Ticket triage and initial investigation
- Running investigation runbooks
- LOW severity resolution
- Creating MEDIUM incidents
- Notifying Level 2 for HIGH/CRITICAL

**Tools:** This runbook system, operations dashboard, read-only database access

### Level 2 — Payment Operations On-Call

**Contact:** PagerDuty service `payment-operations` or ops-oncall@company.internal  
**Escalate when:** HIGH severity, unresolved MEDIUM after 30 minutes

**Responsible for:**
- Gateway vendor engagement
- Cross-team coordination
- Customer communication for enterprise accounts
- MEDIUM/HIGH incident management

### Level 3 — Payment Engineering Lead

**Contact:** Via PagerDuty, escalate from Level 2  
**Escalate when:** CRITICAL severity, code/infrastructure change required

**Responsible for:**
- Production code changes
- Gateway configuration changes
- Circuit breaker management
- Root cause analysis

### Level 4 — Engineering VP / CTO

**Contact:** Executive on-call rotation  
**Escalate when:** Extended outage (> 1 hour), data breach suspected, regulatory event

---

## Incident Creation Checklist

When creating an incident, ensure the following fields are populated:

- [ ] `title` — Clear, concise description of the issue
- [ ] `category` — Appropriate category (payment_gateway, account_lockout, etc.)
- [ ] `severity` — Based on severity matrix above
- [ ] `description` — What is happening, what has been tried
- [ ] `affected_service` — Which service is impacted
- [ ] `customer_id` — If customer-specific (leave blank for systemic)

### Incident Description Template

```
INCIDENT: [Brief title]
SEVERITY: [LOW/MEDIUM/HIGH/CRITICAL]
AFFECTED SERVICE: [service name]
AFFECTED CUSTOMERS: [count or "multiple"]

WHAT IS HAPPENING:
[Clear description of the problem]

EVIDENCE:
- [System event or finding 1]
- [System event or finding 2]
- [Transaction data summary]

CURRENT STATUS:
[What is being done right now]

NEXT STEPS:
[Planned actions]
```

---

## Communication Guidelines

### Status Page Updates

For HIGH/CRITICAL incidents, post status page updates within:
- 10 minutes: Initial "Investigating" post
- 30 minutes: Update with findings
- Every 30 minutes: Progress updates
- Resolution: Detailed resolution summary

### Enterprise Customer Communication

Enterprise customers (plan = enterprise) should receive:
- Direct email notification for HIGH/CRITICAL incidents
- Direct phone call if incident duration > 30 minutes
- Post-incident report within 48 hours

---

## Risk Levels and Approval Requirements

| Action | Risk Level | Approval Required |
|--------|------------|-------------------|
| Add ticket note | LOW | None |
| Update ticket status | LOW | None |
| Create incident | MEDIUM | Automatic (Operations Engineer) |
| Notify operations team | MEDIUM | Automatic (Operations Engineer) |
| Restart a service | HIGH | Engineering Lead approval |
| Disable customer account | HIGH | Operations Manager approval |
| Production config change | HIGH | Engineering Lead + Manager |
| Emergency gateway switch | CRITICAL | Engineering VP approval |

---

## Post-Incident Requirements

For any HIGH or CRITICAL incident:

1. **Within 24 hours:** Draft post-mortem document
2. **Within 48 hours:** Post-mortem review meeting
3. **Within 1 week:** Action items assigned and tracked
4. **Within 30 days:** Action items completed (or formally deferred)

Post-mortem template is available in Confluence: `OPS/Post-Mortem-Template`

---

## Related Runbooks

- `payment_gateway_timeout.md` — Payment gateway incidents
- `payment_failure.md` — General payment failures
- `account_lock.md` — Account suspension incidents
