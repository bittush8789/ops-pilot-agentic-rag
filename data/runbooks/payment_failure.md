# Payment Failure Investigation Runbook

**Document ID:** RB-PAY-002  
**Version:** 3.1  
**Owner:** Payment Operations Team  
**Last Updated:** 2024-01-20  
**Classification:** Internal Operations  

---

## Overview

This runbook provides the general framework for investigating any type of payment failure. For specific failure types, refer to the specialized runbooks listed in the Related Runbooks section.

---

## Payment Failure Categories

| Failure Reason | Root Cause | Responsible Party |
|----------------|------------|-------------------|
| `PAYMENT_GATEWAY_TIMEOUT` | Gateway connectivity or performance | Infrastructure/Gateway vendor |
| `INSUFFICIENT_FUNDS` | Customer account balance | Customer |
| `CARD_DECLINED` | Card issuer rejection | Customer/Card issuer |
| `EXPIRED_CARD` | Card expiration | Customer |
| `INVALID_CVV` | Data entry error or fraud | Customer/Fraud |
| `BANK_REJECT` | Bank policy rejection | Bank/Customer |
| `NETWORK_ERROR` | Internal network issue | Infrastructure |
| `DUPLICATE_TRANSACTION` | Double-submission | Application bug or customer |
| `FRAUD_SUSPECTED` | Fraud detection flag | Security team review |

---

## Initial Triage

When a payment failure ticket arrives:

1. **Identify the failure reason** from transaction records
2. **Count the failures** — single failure vs. pattern
3. **Check timing** — is this a new issue or recurring?
4. **Check customer status** — is the account in good standing?
5. **Check for existing incidents** — is there already an open incident?

### Failure Frequency Assessment

| Count in Last Hour | Classification | Priority |
|-------------------|----------------|----------|
| 1 failure | Isolated, likely customer issue | LOW |
| 2–4 failures | Emerging pattern, investigate | MEDIUM |
| 5+ failures | Active issue, immediate action | HIGH |
| Cross-customer | Systemic issue | CRITICAL |

---

## Investigation Procedure

### Phase 1: Customer Assessment

1. Retrieve customer profile — account_status, plan, history
2. Check if account is `active` — suspended accounts cannot process payments
3. Review customer's transaction history (last 90 days)
4. Calculate success rate: successful / total transactions

### Phase 2: Transaction Analysis

1. List all failed transactions with timestamps
2. Group by `failure_reason` — are all failures the same type?
3. Check if failures are for the same amount — possible retry loop
4. Check `payment_method` — is one method failing while others succeed?
5. Check `gateway` — is the failure gateway-specific?

### Phase 3: System Correlation

1. Search system events for the customer's transaction timestamps
2. Look for correlated events with the same timeframe
3. Check for infrastructure alerts that overlap the failure window
4. Review related incidents

### Phase 4: Runbook Selection

Based on the dominant `failure_reason`, apply the appropriate specialized runbook:

- `PAYMENT_GATEWAY_TIMEOUT` → `payment_gateway_timeout.md`
- `INSUFFICIENT_FUNDS` or `CARD_DECLINED` → Customer-side issue, notify customer
- `DUPLICATE_TRANSACTION` → `duplicate_payment.md`
- `FRAUD_SUSPECTED` → Escalate to security team immediately
- `NETWORK_ERROR` → Infrastructure investigation, check `service_degradation` incidents

---

## Communication Templates

### Customer Notification (Payment Failure — Customer Side)

```
Subject: Payment Issue — Action Required

We noticed your recent payment could not be processed.
Reason: [failure_reason in plain language]

Action Required:
[For INSUFFICIENT_FUNDS] Please ensure your account has sufficient funds.
[For CARD_DECLINED/EXPIRED] Please update your payment method.
[For BANK_REJECT] Please contact your bank for details.

You can update your payment method at: [billing portal URL]
If you need assistance, reply to this ticket.
```

### Customer Notification (System-Side Issue)

```
Subject: Payment Service Update — We Are Investigating

We are aware that your recent payment was not processed successfully.
This appears to be related to a temporary issue on our end.

Our team is actively investigating. You do not need to take any action at this time.
We recommend waiting [15–30] minutes before retrying.

We apologize for the inconvenience.
```

---

## Decision Tree

```
Payment failure received
         │
         ▼
Is failure_reason = PAYMENT_GATEWAY_TIMEOUT?
   YES → See payment_gateway_timeout.md
   NO  ↓
Is failure_reason = INSUFFICIENT_FUNDS or CARD_DECLINED?
   YES → Customer-side issue, notify customer
   NO  ↓
Is failure_reason = FRAUD_SUSPECTED?
   YES → Escalate to security team immediately
   NO  ↓
Is failure_reason = DUPLICATE_TRANSACTION?
   YES → See duplicate_payment.md
   NO  ↓
Is failure_reason = NETWORK_ERROR?
   YES → Infrastructure investigation
   NO  ↓
Unknown failure → Escalate to payment engineering
```

---

## Escalation Criteria

Escalate immediately when:

- 5 or more failures in 30 minutes for a single customer
- Failures affecting 3 or more customers simultaneously
- `FRAUD_SUSPECTED` on any high-value transaction
- Circuit breaker is OPEN
- Customer is enterprise tier with SLA obligations

---

## Related Runbooks

- `payment_gateway_timeout.md` — Gateway timeout specific procedures
- `duplicate_payment.md` — Duplicate transaction investigation
- `failed_refund.md` — Refund processing failures
- `account_lock.md` — Account suspension due to payment failures
- `incident_escalation.md` — Escalation procedures
